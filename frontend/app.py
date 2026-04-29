import os
import time

import requests
import streamlit as st

API_BASE = os.getenv("CINEBRAIN_API", "http://localhost:8000")

# must be the first streamlit call
st.set_page_config(
    page_title="CineBrain",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# all the custom styling — dark cinematic theme
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&display=swap');

:root {
    --bg:         #0b0d11;
    --surface:    #13161d;
    --surface2:   #1b1f2a;
    --border:     #272c3a;
    --accent:     #e8b84b;
    --accent2:    #d97c3a;
    --text:       #e8e8e8;
    --muted:      #7a8099;
    --pill-bg:    #1e2235;
    --radius:     12px;
}

html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'DM Sans', sans-serif !important;
}

[data-testid="stHeader"], footer, #MainMenu { display: none !important; }
[data-testid="stSidebar"]  { background: var(--surface) !important; }

.hero {
    text-align: center;
    padding: 3rem 1rem 1.5rem;
}
.hero h1 {
    font-family: 'DM Serif Display', serif;
    font-size: clamp(2.6rem, 6vw, 4.2rem);
    letter-spacing: -0.02em;
    background: linear-gradient(135deg, var(--accent) 0%, var(--accent2) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0;
}
.hero p {
    color: var(--muted);
    font-size: 1.05rem;
    margin-top: 0.5rem;
    font-weight: 300;
}

[data-testid="stTabs"] > div:first-child {
    border-bottom: 1px solid var(--border) !important;
    gap: 0 !important;
}
button[data-baseweb="tab"] {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.9rem !important;
    font-weight: 500 !important;
    color: var(--muted) !important;
    padding: 0.6rem 1.4rem !important;
    border-radius: var(--radius) var(--radius) 0 0 !important;
    background: transparent !important;
    transition: color 0.2s !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom: 2px solid var(--accent) !important;
}

[data-testid="stTextInput"] input,
[data-testid="stSelectbox"] div[data-baseweb="select"] {
    background: var(--surface2) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    color: var(--text) !important;
    font-family: 'DM Sans', sans-serif !important;
}
[data-testid="stTextArea"] textarea {
    background: var(--surface2) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    color: var(--text) !important;
    font-family: 'DM Sans', sans-serif !important;
}

[data-testid="stButton"] button {
    background: linear-gradient(135deg, var(--accent) 0%, var(--accent2) 100%) !important;
    color: #0b0d11 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    border: none !important;
    border-radius: var(--radius) !important;
    padding: 0.55rem 1.6rem !important;
    font-size: 0.95rem !important;
    transition: opacity 0.2s, transform 0.15s !important;
}
[data-testid="stButton"] button:hover { opacity: 0.88 !important; transform: translateY(-1px) !important; }

.movie-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
    transition: border-color 0.2s, box-shadow 0.2s;
    position: relative;
    overflow: hidden;
}
.movie-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    opacity: 0;
    transition: opacity 0.2s;
}
.movie-card:hover { border-color: #3a3f54; box-shadow: 0 4px 24px rgba(0,0,0,0.4); }
.movie-card:hover::before { opacity: 1; }

.card-header { display: flex; align-items: flex-start; gap: 0.75rem; margin-bottom: 0.5rem; }
.card-rank {
    font-family: 'DM Serif Display', serif;
    font-size: 1.6rem;
    color: var(--accent);
    opacity: 0.5;
    line-height: 1;
    min-width: 2rem;
}
.card-title {
    font-family: 'DM Serif Display', serif;
    font-size: 1.2rem;
    color: var(--text);
    line-height: 1.25;
}
.card-meta { display: flex; flex-wrap: wrap; gap: 0.45rem; margin-bottom: 0.65rem; }
.pill {
    background: var(--pill-bg);
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 0.18rem 0.75rem;
    font-size: 0.72rem;
    color: var(--muted);
    font-weight: 500;
    letter-spacing: 0.03em;
}
.pill.accent { background: rgba(232,184,75,0.1); border-color: rgba(232,184,75,0.3); color: var(--accent); }
.card-overview { font-size: 0.85rem; color: var(--muted); line-height: 1.65; }

.score-bar-wrap { display: flex; align-items: center; gap: 0.65rem; margin-top: 0.75rem; }
.score-bar-track {
    flex: 1; height: 4px; background: var(--border); border-radius: 999px; overflow: hidden;
}
.score-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    border-radius: 999px;
}
.score-label { font-size: 0.72rem; color: var(--muted); white-space: nowrap; }

.rag-box {
    background: linear-gradient(135deg, #13161d 0%, #1a1d28 100%);
    border: 1px solid rgba(232,184,75,0.25);
    border-radius: var(--radius);
    padding: 1.5rem 1.75rem;
    margin-top: 1.25rem;
    position: relative;
}
.rag-box::before {
    content: '✦ AI CURATOR';
    position: absolute;
    top: -0.6rem; left: 1.25rem;
    background: var(--bg);
    padding: 0 0.5rem;
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    color: var(--accent);
}
.rag-box p {
    font-size: 0.92rem;
    line-height: 1.8;
    color: #c8cad6;
    margin: 0;
    font-style: italic;
}

.section-divider {
    border: none;
    border-top: 1px solid var(--border);
    margin: 1.5rem 0;
}

.status-ok { color: #4ade80; font-size: 0.78rem; }
.status-err { color: #f87171; font-size: 0.78rem; }
[data-testid="stSpinner"] { color: var(--accent) !important; }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(ttl=600, show_spinner=False)
def fetch_titles() -> list[str]:
    # cache for 10 min, no reason to hit the API on every rerender
    try:
        r = requests.get(f"{API_BASE}/titles", timeout=60)
        r.raise_for_status()
        return r.json().get("titles", [])
    except Exception:
        return []


def call_recommend(endpoint: str, params: dict) -> dict | None:
    try:
        r = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=60)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("Can't reach the backend. Is the FastAPI server running?")
    except requests.exceptions.Timeout:
        st.error("Request timed out — the model might still be loading, try again in a moment.")
    except requests.exceptions.HTTPError as e:
        detail = ""
        try:
            detail = e.response.json().get("detail", "")
        except Exception:
            pass
        st.error(f"API error {e.response.status_code}: {detail or str(e)}")
    return None


def api_status() -> tuple[bool, str]:
    try:
        r = requests.get(f"{API_BASE}/health", timeout=60)
        r.raise_for_status()
        d = r.json()
        return True, f"{d.get('movies_loaded', '?')} movies · {d.get('faiss_vectors', '?')} FAISS vectors"
    except Exception as exc:
        return False, str(exc)


def genre_pills(genres_str: str) -> str:
    genres = [g.strip() for g in genres_str.replace("|", ",").split(",") if g.strip()]
    return "".join(f'<span class="pill">{g}</span>' for g in genres[:5])


def render_movie_card(rank: int, movie: dict) -> None:
    score = movie.get("hybrid_score", 0)
    bar_width = min(int(score * 100), 100)
    vote = movie.get("vote_average", 0)
    overview = movie.get("overview", "No synopsis available.")
    if len(overview) > 260:
        overview = overview[:257] + "…"

    html = f"""
<div class="movie-card">
  <div class="card-header">
    <span class="card-rank">#{rank}</span>
    <span class="card-title">{movie['title']}</span>
  </div>
  <div class="card-meta">
    {genre_pills(movie.get('genres', ''))}
    <span class="pill accent">★ {vote:.1f}</span>
  </div>
  <p class="card-overview">{overview}</p>
  <div class="score-bar-wrap">
    <div class="score-bar-track">
      <div class="score-bar-fill" style="width:{bar_width}%"></div>
    </div>
    <span class="score-label">Match {score:.3f}</span>
  </div>
</div>"""
    st.markdown(html, unsafe_allow_html=True)


def render_rag_box(text: str) -> None:
    st.markdown(f'<div class="rag-box"><p>{text}</p></div>', unsafe_allow_html=True)


def render_results(data: dict) -> None:
    results = data.get("results", [])
    if not results:
        st.warning("No results came back — that's unexpected.")
        return

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
    cols = st.columns(2, gap="medium")
    for i, movie in enumerate(results):
        with cols[i % 2]:
            render_movie_card(i + 1, movie)

    rag = data.get("rag_summary")
    if rag:
        render_rag_box(rag)


# page header
st.markdown(
    """
<div class="hero">
  <h1>CineBrain</h1>
  <p>Hybrid recommendations · Semantic search · AI curation</p>
</div>
""",
    unsafe_allow_html=True,
)

ok, msg = api_status()
status_cls = "status-ok" if ok else "status-err"
st.markdown(
    f'<p style="text-align:center" class="{status_cls}">{"●" if ok else "○"} {msg}</p>',
    unsafe_allow_html=True,
)
st.markdown("")

with st.sidebar:
    st.markdown("### Settings")
    top_n = st.slider("How many results", 3, 10, 5)
    use_rag = st.toggle("AI Curator summary", value=True)
    st.caption("Needs GROQ_API_KEY configured on the server.")
    st.markdown("---")
    st.markdown("**About**")
    st.caption(
        "Combines SBERT embeddings, metadata similarity (director/cast/genres), "
        "and IMDb Bayesian ratings. FAISS handles the vector search."
    )


tab_title, tab_vibe = st.tabs(["Search by Movie", "Search by Vibe"])


with tab_title:
    st.markdown("#### Find movies similar to one you already like")
    st.caption(
        "Blends **plot semantics** (SBERT + FAISS), **metadata** (director, cast, genres), "
        "and **IMDb Bayesian ratings** to rank results."
    )
    st.markdown("")

    titles = fetch_titles()
    if titles:
        selected = st.selectbox(
            "Pick a movie",
            options=[""] + sorted(titles),
            format_func=lambda x: "start typing to search..." if x == "" else x,
        )
    else:
        selected = st.text_input("Movie title (backend offline — type manually)")

    c1, _ = st.columns([1, 5])
    with c1:
        go_title = st.button("Recommend", key="btn_title")

    if go_title:
        if not selected:
            st.warning("Pick a movie first.")
        else:
            with st.spinner("Running the hybrid engine..."):
                t0 = time.time()
                data = call_recommend(
                    "/recommend/by-title",
                    {"title": selected, "top_n": top_n, "use_rag": use_rag},
                )
                elapsed = time.time() - t0

            if data:
                st.markdown(
                    f"<p style='color:var(--muted);font-size:0.78rem'>"
                    f"Results for <strong>{data['query']}</strong> · {elapsed:.2f}s</p>",
                    unsafe_allow_html=True,
                )
                render_results(data)


with tab_vibe:
    st.markdown("#### Describe a plot, mood, or vibe — doesn't have to be a real movie")
    st.caption(
        "Your text gets encoded by SBERT on the fly and matched against all movie embeddings via FAISS. "
        "No title needed."
    )
    st.markdown("")

    example_vibes = [
        "A heist gone wrong inside a museum at night",
        "Time loops, existential dread, and a convenience store",
        "Quiet grief in a rainy coastal town, slow cinema vibes",
        "AI becomes conscious and secretly befriends a child",
        "A spy who can't remember which side they're on",
    ]

    st.markdown("<p style='color:var(--muted);font-size:0.8rem'>Some examples to try:</p>", unsafe_allow_html=True)
    example_cols = st.columns(len(example_vibes))
    chosen_example = ""
    for i, ex in enumerate(example_vibes):
        with example_cols[i]:
            if st.button(ex[:28] + "…", key=f"ex_{i}", help=ex):
                chosen_example = ex

    vibe_text = st.text_area(
        "Describe your vibe",
        value=chosen_example,
        height=130,
        placeholder="e.g. A brilliant chemist who fakes his death and reinvents himself in a small town...",
    )

    c1, _ = st.columns([1, 5])
    with c1:
        go_vibe = st.button("Search", key="btn_vibe")

    if go_vibe:
        vibe_text = vibe_text.strip()
        if len(vibe_text) < 10:
            st.warning("Write a bit more — a sentence or two works best.")
        else:
            with st.spinner("Searching..."):
                t0 = time.time()
                data = call_recommend(
                    "/recommend/by-vibe",
                    {"vibe": vibe_text, "top_n": top_n, "use_rag": use_rag},
                )
                elapsed = time.time() - t0

            if data:
                st.markdown(
                    f"<p style='color:var(--muted);font-size:0.78rem'>Done · {elapsed:.2f}s</p>",
                    unsafe_allow_html=True,
                )
                render_results(data)