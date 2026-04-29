# 🎬 CineBrain — Hybrid Movie Recommendation Engine

**Advanced CS Course Project** · FastAPI + Streamlit + FAISS + SBERT + Groq

---

## What Is This?

CineBrain is a movie recommendation engine I built for my advanced CS course. It's not just another "people who watched X also liked Y" system — I wanted to build something that actually understands movies the way a film nerd would: by plot, by feel, by who made it, and by whether it's genuinely well-regarded.

The result is a hybrid engine that combines three distinct signals:

- **Semantic plot similarity** — what the movie is actually about, using sentence embeddings
- **Metadata similarity** — director, cast, and genre overlap via CountVectorizer
- **Bayesian-adjusted ratings** — not just raw stars, but statistically honest scores that penalize films with too few votes

> **The star feature is Vibe Search.** Describe any mood, concept, or imaginary plot in plain English, and the engine finds real movies that match it. No need to know a title.

---

## Features at a Glance

| Feature | What you do | What happens |
|---|---|---|
| **Search by Movie** | Pick a movie you already love | Get 5 similar movies, ranked by plot + metadata + ratings |
| **Vibe / Plot Search** | Describe any mood, concept, or idea | SBERT finds the movies semantically closest to your description |
| **AI Curator** | Results come in automatically | Groq's Llama model explains *why* these specific films match you |

---

## How the Scoring Works

Every recommendation goes through the same formula:

```
hybrid_score = (plot_similarity × 0.5 + metadata_similarity × 0.5) × (1 + bayesian_score)
```

Breaking that down:

- **Plot similarity (50%)** — SBERT embeddings capture semantic meaning. Two movies about grief can score as similar even if they share zero keywords.
- **Metadata similarity (50%)** — Director, cast, and genre overlap via CountVectorizer. Helps surface films from the same creative circles.
- **Bayesian rating boost** — Multiplies the base score. A film with an honest 7.8 from 5,000 votes ranks above a suspicious 9.5 from 12 votes.

For Vibe Search, there's no source movie to compare metadata against, so it becomes pure semantic matching — just SBERT + FAISS finding the closest plots to whatever you typed.

---

## Tech Stack

**Backend**
- FastAPI — async-first, auto-generates Swagger docs at `/docs`
- Sentence-Transformers (`all-MiniLM-L6-v2`) — encodes plot summaries into semantic vectors
- FAISS `IndexFlatIP` — exact cosine similarity search on L2-normalized embeddings
- Pre-computed pickle files — similarity matrices loaded once at startup, never recomputed per request

**Frontend**
- Streamlit — two tabs (title search, vibe search), movie cards with scores, RAG summary panel
- Title list cached locally for 10 minutes — no unnecessary API spam

**AI Curator (RAG)**
- Groq API — Llama 3.1 8B, free tier, runs asynchronously so it doesn't block the UI
- Prompt is tuned to produce specific, engaging summaries — not generic recaps

---

## Getting It Running

You'll need Python 3.10 or later. Everything else installs via pip.

### 1. Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set Up Your Data Files

Drop these four pickle files into a `data/` folder in the project root:

- `movies_dict.pkl`
- `plot_embeddings.pkl`
- `meta_sim.pkl`
- `normalized_scores.pkl`

### 3. Add a Groq API Key *(optional)*

The AI Curator needs a Groq key. Grab one free at [groq.com](https://groq.com), then either:

- Create a `.env` file and add: `GROQ_API_KEY=your_key_here`
- Or paste it directly into the `GROQ_API_KEY` variable in `main.py`

> The rest of the app works fine without a key — you just won't get the AI-generated summaries.

### 4. Start the Servers

Open two terminals:

```bash
# Terminal 1 — backend
DATA_DIR=./data python -m uvicorn main:app --reload --port 8000

# Terminal 2 — frontend
CINEBRAIN_API=http://localhost:8000 streamlit run app.py
```

The API will be live at `http://localhost:8000` and the UI at `http://localhost:8501`. Swagger docs at `http://localhost:8000/docs`.

---

## How the Architecture Fits Together

The backend and frontend are fully decoupled — the Streamlit app is just an HTTP client that talks to FastAPI.

### On Startup

The backend loads everything into a shared `store` dict using FastAPI's `asynccontextmanager` lifespan. This happens once — no re-loading per request. What gets loaded:

- The SBERT model (for encoding incoming text)
- The FAISS index (pre-built from all plot embeddings)
- The metadata similarity matrix (pre-computed offline)
- Bayesian-weighted rating scores
- The full movie metadata DataFrame

### On a Title Search Request

1. Look up the source movie by title in the metadata store
2. Retrieve its pre-built SBERT embedding
3. Query FAISS for the 5 nearest neighbors by plot similarity
4. Pull metadata similarity scores from the pre-computed matrix
5. Blend scores with the hybrid formula and apply the Bayesian rating boost
6. Return the top 5 with scores

### On a Vibe Search Request

Same as above, except step 1 is replaced with encoding the user's free-text description on the fly. There's no source movie, so the metadata matrix step is skipped — it's pure semantic search.

### Why FAISS?

Naive cosine similarity over thousands of embeddings doesn't scale. FAISS handles exact nearest-neighbor search in near-constant time. Using `IndexFlatIP` on L2-normalized vectors is mathematically identical to cosine similarity, just much faster.

---

## Project Files

- **`main.py`** — FastAPI backend. All the ML logic lives here (model loading, scoring, endpoints). Heavily commented.
- **`app.py`** — Streamlit frontend. Handles UI rendering, HTTP calls to the backend, and the movie card layout.
- **`requirements.txt`** — All Python dependencies.
- **`data/`** — Your four pickle files. Kept out of version control since they're large binary files.

---

## Things Worth Improving

These are the upgrades I'd make with more time or a larger dataset:

- **Approximate Nearest Neighbors** — Swap `IndexFlatIP` for `IndexIVFFlat` if the movie catalog grows beyond ~100k entries. Much faster at scale, with minimal accuracy loss.
- **Request Caching** — Add Redis to cache results for frequently searched titles or common vibe patterns. The SBERT encoding step is the main bottleneck for vibe search.
- **Collaborative Filtering** — Layer in user interaction history (likes, saves, skips) to personalize recommendations over time. Right now it's purely content-based.
- **Fine-tuned Embeddings** — Train a custom SBERT model on movie-specific data. The general-purpose `all-MiniLM-L6-v2` is solid, but a domain-specific model would better understand film vocabulary.
- **Feedback Loop** — Let users rate their recommendations, then use that signal to retrain the Bayesian scores periodically.

---

## Deploying for a Demo

For a course presentation, running locally is fine. If you want it publicly accessible:

- **Backend** — Deploy to Render, Railway, or Heroku. All three handle FastAPI with minimal config.
- **Frontend** — Deploy to Streamlit Cloud (free, one-click setup from a GitHub repo).
- **Data** — Store the pickle files in object storage (S3 or GCS) and fetch them on startup. Don't commit large binary files to your repo.

> Remember to set `GROQ_API_KEY` and `DATA_DIR` as environment variables on whatever platform you use.

---

## What I Actually Learned Building This

Beyond the ML techniques, this project taught me things that don't always show up in coursework:

- **Backend/frontend separation matters** even in small projects — it keeps the ML logic testable and the UI swappable.
- **Pre-compute everything expensive.** The similarity matrices take a while to build offline, but requests are instant because we never recompute them at runtime.
- **FAISS vs. naive nearest neighbors** is a real engineering decision, not just a textbook exercise. The difference is measurable even at a few thousand movies.
- **Async patterns in Python** are worth learning early. The RAG step being non-blocking is what makes the UI feel responsive.
- **Bayesian rating adjustment is underrated.** It sounds like a small tweak but it completely changes which movies surface to the top.

---

