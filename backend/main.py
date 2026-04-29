import os
import pickle
import time
import logging
from contextlib import asynccontextmanager
from typing import Optional

import faiss
import numpy as np
import pandas as pd
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

DATA_DIR = os.getenv("DATA_DIR", "data")
SBERT_MODEL = os.getenv("SBERT_MODEL", "all-MiniLM-L6-v2")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TOP_N_DEFAULT = 5
HYBRID_ALPHA = 0.5  # plot similarity weight
HYBRID_BETA = 0.5   # metadata similarity weight
RATING_BOOST = 1.0  # how much the bayesian score affects the final ranking

# all the heavy stuff lives here after startup
store: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Loading models and data, this takes a sec...")
    t0 = time.perf_counter()

    def load_pickle(filename):
        with open(os.path.join(DATA_DIR, filename), "rb") as f:
            return pickle.load(f)

    movies_dict = load_pickle("movies_dict.pkl")
    plot_embeddings = load_pickle("plot_embeddings.pkl")
    meta_sim_matrix = load_pickle("meta_sim.pkl")

    # the normalized scores file might have different names depending on
    # which preprocessing script was run, so just handle both cases
    try:
        normalized_scores = load_pickle("normalized_scores.pkl")
    except FileNotFoundError:
        try:
            normalized_scores = load_pickle("ratings_score.pkl")
        except FileNotFoundError:
            # no scores file at all — fall back to zeros so nothing crashes
            log.warning("No ratings file found, defaulting to zero scores")
            normalized_scores = np.zeros(len(movies_dict["title"]), dtype=np.float32)

    movies_df = pd.DataFrame(movies_dict).reset_index(drop=True)

    # normalize embeddings so we can use inner product as cosine similarity
    plot_emb = np.array(plot_embeddings, dtype=np.float32)
    faiss.normalize_L2(plot_emb)

    dim = plot_emb.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(plot_emb)
    log.info("FAISS index ready: %d vectors at dim %d", index.ntotal, dim)

    # loading SBERT is the slow part
    sbert = SentenceTransformer(SBERT_MODEL)
    log.info("SBERT loaded: %s", SBERT_MODEL)

    title_to_idx = {
        t.lower().strip(): i for i, t in enumerate(movies_df["title"].tolist())
    }

    store.update(
        movies_df=movies_df,
        plot_emb=plot_emb,
        meta_sim_matrix=np.array(meta_sim_matrix, dtype=np.float32),
        normalized_scores=np.array(normalized_scores, dtype=np.float32),
        faiss_index=index,
        sbert=sbert,
        title_to_idx=title_to_idx,
    )

    log.info("Everything ready in %.2fs", time.perf_counter() - t0)
    yield
    store.clear()


app = FastAPI(title="CineBrain API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class MovieResult(BaseModel):
    title: str
    genres: str
    overview: str
    vote_average: float
    hybrid_score: float


class RecommendationResponse(BaseModel):
    query: str
    mode: str  # "title" or "vibe"
    results: list[MovieResult]
    rag_summary: Optional[str] = None


def build_movie_result(idx: int, score: float) -> MovieResult:
    row = store["movies_df"].iloc[idx]
    return MovieResult(
        title=str(row.get("title", "Unknown")),
        genres=str(row.get("genres", "")),
        overview=str(row.get("overview", "")),
        vote_average=float(row.get("vote_average", 0.0)),
        hybrid_score=round(float(score), 4),
    )


def compute_hybrid_scores(query_emb: np.ndarray, exclude_idx: Optional[int] = None) -> np.ndarray:
    n = len(store["movies_df"])

    q = query_emb.reshape(1, -1).astype(np.float32)
    faiss.normalize_L2(q)

    # FAISS returns results sorted by score, not by original index,
    # so we need to scatter them back into a full-length array
    distances, indices = store["faiss_index"].search(q, n)
    plot_sims = np.zeros(n, dtype=np.float32)
    plot_sims[indices[0]] = distances[0]

    if exclude_idx is not None:
        meta_sims = store["meta_sim_matrix"][exclude_idx]
    else:
        # vibe search has no source movie, so metadata similarity doesn't apply
        meta_sims = np.zeros(n, dtype=np.float32)

    alpha = HYBRID_ALPHA if exclude_idx is not None else 1.0
    beta = HYBRID_BETA if exclude_idx is not None else 0.0

    hybrid = (plot_sims * alpha + meta_sims * beta) * (1 + RATING_BOOST * store["normalized_scores"])
    return hybrid


def get_top_results(hybrid: np.ndarray, top_n: int, exclude_idx: Optional[int]) -> list[MovieResult]:
    results = []
    for idx in np.argsort(hybrid)[::-1]:
        if exclude_idx is not None and idx == exclude_idx:
            continue
        results.append(build_movie_result(int(idx), hybrid[idx]))
        if len(results) == top_n:
            break
    return results


async def call_groq_rag(query: str, mode: str, movies: list[MovieResult]) -> str:
    if not GROQ_API_KEY:
        return ""

    movie_list = "\n".join(
        f"  {i+1}. **{m.title}** (Genres: {m.genres}) — {m.overview[:180]}..."
        for i, m in enumerate(movies)
    )

    if mode == "title":
        context = f'The user loved the movie "{query}"'
    else:
        context = f'The user described this vibe/plot: "{query}"'

    prompt = f"""You are an AI Movie Curator. {context}.
We recommend these 5 movies:
{movie_list}
Write a short, engaging paragraph explaining why these match. Keep it professional."""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            if resp.status_code != 200:
                try:
                    error_msg = resp.json().get("error", {}).get("message", resp.text)
                except Exception:
                    error_msg = resp.text
                log.error("Groq error: %s", error_msg)
                return f"(RAG unavailable: {error_msg})"

            return resp.json()["choices"][0]["message"]["content"].strip()

    except Exception as exc:
        log.error("Groq request failed: %s", exc)
        return f"(RAG request failed: {exc})"


@app.get("/health")
def health():
    return {
        "status": "ok",
        "movies_loaded": len(store.get("movies_df", [])),
        "faiss_vectors": store["faiss_index"].ntotal if "faiss_index" in store else 0,
    }


@app.get("/titles")
def list_titles():
    return {"titles": store["movies_df"]["title"].tolist()}


@app.get("/recommend/by-title", response_model=RecommendationResponse)
async def recommend_by_title(
    title: str = Query(...),
    top_n: int = Query(TOP_N_DEFAULT),
    use_rag: bool = Query(True),
):
    idx = store["title_to_idx"].get(title.lower().strip())
    if idx is None:
        raise HTTPException(404, f"'{title}' not found. Check /titles for the full list.")

    hybrid = compute_hybrid_scores(store["plot_emb"][idx], exclude_idx=idx)
    results = get_top_results(hybrid, top_n, exclude_idx=idx)

    rag_text = ""
    if use_rag:
        rag_text = await call_groq_rag(store["movies_df"].iloc[idx]["title"], "title", results)

    return RecommendationResponse(
        query=store["movies_df"].iloc[idx]["title"],
        mode="title",
        results=results,
        rag_summary=rag_text or None,
    )


@app.get("/recommend/by-vibe", response_model=RecommendationResponse)
async def recommend_by_vibe(
    vibe: str = Query(...),
    top_n: int = Query(TOP_N_DEFAULT),
    use_rag: bool = Query(True),
):
    # encode the user's free-text description on the fly
    query_emb = store["sbert"].encode([vibe], convert_to_numpy=True)[0].astype(np.float32)

    hybrid = compute_hybrid_scores(query_emb, exclude_idx=None)
    results = get_top_results(hybrid, top_n, exclude_idx=None)

    rag_text = ""
    if use_rag:
        rag_text = await call_groq_rag(vibe, "vibe", results)

    return RecommendationResponse(
        query=vibe,
        mode="vibe",
        results=results,
        rag_summary=rag_text or None,
    )