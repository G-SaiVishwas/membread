# pyright: reportMissingImports=false, reportMissingModuleSource=false, reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportReturnType=false, reportUnknownArgumentType=false, reportMissingTypeArgument=false, reportUnknownParameterType=false
"""
Membread — Interactive Knowledge Graph Dashboard
===================================================

A premium Streamlit dashboard for exploring the bi-temporal
knowledge graph.  Five pages: Overview · Time-Travel · Entity History
· Live Knowledge Graph · Chat with Memory.

Launch:
    streamlit run ui/dashboard.py

Requires: streamlit, streamlit-agraph, requests, plotly, pandas
"""

from __future__ import annotations

import os
import json
import datetime
import time
import requests
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_BASE = os.getenv("MEMBREAD_API", "http://localhost:8000")

# ---------------------------------------------------------------------------
# Custom CSS — dark glassmorphism theme
# ---------------------------------------------------------------------------

CUSTOM_CSS = """
<style>
/* ── Global font ─────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

:root {
    --bg-primary: #0a0a0f;
    --bg-secondary: #12121a;
    --bg-card: rgba(255,255,255,0.04);
    --bg-card-hover: rgba(255,255,255,0.08);
    --border-glass: rgba(255,255,255,0.08);
    --text-primary: #e4e4e7;
    --text-secondary: #a1a1aa;
    --accent: #8b5cf6;
    --accent-glow: rgba(139,92,246,0.25);
    --success: #22c55e;
    --warning: #f59e0b;
    --danger: #ef4444;
    --info: #3b82f6;
}

html, body, [data-testid="stAppViewContainer"] {
    font-family: 'Inter', sans-serif !important;
}

/* ── Glass cards ─────────────────────────────────────────────────── */
.glass-card {
    background: var(--bg-card);
    border: 1px solid var(--border-glass);
    border-radius: 16px;
    padding: 1.5rem;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    transition: all 0.3s ease;
}
.glass-card:hover {
    background: var(--bg-card-hover);
    border-color: rgba(139,92,246,0.3);
    box-shadow: 0 0 30px var(--accent-glow);
}

/* ── Metric cards ────────────────────────────────────────────────── */
.metric-card {
    background: linear-gradient(135deg, rgba(139,92,246,0.12), rgba(59,130,246,0.08));
    border: 1px solid var(--border-glass);
    border-radius: 16px;
    padding: 1.25rem 1.5rem;
    text-align: center;
}
.metric-card .metric-value {
    font-size: 2.25rem;
    font-weight: 700;
    background: linear-gradient(135deg, #8b5cf6, #3b82f6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1.2;
}
.metric-card .metric-label {
    font-size: 0.85rem;
    color: var(--text-secondary);
    margin-top: 0.25rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* ── Hero badge ──────────────────────────────────────────────────── */
.hero-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: linear-gradient(135deg, rgba(139,92,246,0.15), rgba(59,130,246,0.1));
    border: 1px solid rgba(139,92,246,0.3);
    border-radius: 999px;
    padding: 0.35rem 1rem;
    font-size: 0.8rem;
    color: #c4b5fd;
    letter-spacing: 0.03em;
}

/* ── Timeline hit card ───────────────────────────────────────────── */
.hit-card {
    background: var(--bg-card);
    border: 1px solid var(--border-glass);
    border-radius: 12px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.75rem;
    transition: all 0.2s ease;
}
.hit-card:hover {
    border-color: rgba(139,92,246,0.4);
    box-shadow: 0 0 20px var(--accent-glow);
}
.hit-score {
    display: inline-block;
    background: linear-gradient(135deg, #8b5cf6, #6366f1);
    color: white;
    font-size: 0.7rem;
    font-weight: 600;
    padding: 0.15rem 0.6rem;
    border-radius: 999px;
    margin-right: 0.5rem;
}
.hit-meta {
    font-size: 0.78rem;
    color: var(--text-secondary);
    margin-top: 0.4rem;
}

/* ── Version card (entity history) ───────────────────────────────── */
.version-card {
    background: var(--bg-card);
    border-left: 3px solid #8b5cf6;
    border-radius: 0 12px 12px 0;
    padding: 1rem 1.25rem;
    margin-bottom: 0.75rem;
}
.version-card.superseded {
    border-left-color: #f59e0b;
    opacity: 0.7;
}

/* ── Status dot ──────────────────────────────────────────────────── */
.status-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 6px;
    animation: pulse 2s infinite;
}
.status-dot.green { background: var(--success); box-shadow: 0 0 8px var(--success); }
.status-dot.red { background: var(--danger); box-shadow: 0 0 8px var(--danger); }

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

/* ── Footer ──────────────────────────────────────────────────────── */
.footer {
    text-align: center;
    padding: 2rem 0 1rem;
    font-size: 0.78rem;
    color: var(--text-secondary);
    border-top: 1px solid var(--border-glass);
    margin-top: 3rem;
}
.footer a { color: #8b5cf6; text-decoration: none; }
.footer a:hover { text-decoration: underline; }

/* ── Sidebar polish ──────────────────────────────────────────────── */
section[data-testid="stSidebar"] > div:first-child {
    background: var(--bg-secondary);
    border-right: 1px solid var(--border-glass);
}

/* ── Primary button override ─────────────────────────────────────── */
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {
    background: linear-gradient(135deg, #8b5cf6, #6366f1) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    border-radius: 10px !important;
    padding: 0.5rem 1.5rem !important;
    transition: all 0.2s ease !important;
}
.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="baseButton-primary"]:hover {
    box-shadow: 0 0 25px var(--accent-glow) !important;
    transform: translateY(-1px) !important;
}

/* ── Info tooltip icon ───────────────────────────────────────────── */
.tooltip-icon {
    display: inline-block;
    cursor: help;
    background: rgba(139,92,246,0.2);
    color: #c4b5fd;
    border-radius: 50%;
    width: 18px;
    height: 18px;
    font-size: 0.7rem;
    text-align: center;
    line-height: 18px;
    margin-left: 4px;
}
</style>
"""

# ---------------------------------------------------------------------------
# Confetti JS — fires once per browser session
# ---------------------------------------------------------------------------

CONFETTI_JS = """
<script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js"></script>
<script>
if (!sessionStorage.getItem('tg_confetti_done')) {
    setTimeout(function(){
        confetti({particleCount:120, spread:80, origin:{y:0.6},
                  colors:['#8b5cf6','#3b82f6','#22c55e','#f59e0b']});
        sessionStorage.setItem('tg_confetti_done','1');
    }, 600);
}
</script>
"""


# ---------------------------------------------------------------------------
# API helpers  (all safe — return fallback on error)
# ---------------------------------------------------------------------------

def _token() -> str:
    return st.session_state.get("jwt_token", "")


def _headers() -> dict[str, str]:
    t = _token()
    return {"Authorization": f"Bearer {t}"} if t else {}


def api_health() -> dict:
    try:
        r = requests.get(f"{API_BASE}/health", timeout=3)
        return r.json()
    except Exception as e:
        return {"status": "unreachable", "error": str(e)}


def api_store(observation: str, metadata: dict | None = None) -> dict:
    payload = {"observation": observation, "metadata": metadata or {}}
    r = requests.post(
        f"{API_BASE}/api/memory/store", json=payload,
        headers=_headers(), timeout=15,
    )
    r.raise_for_status()
    return r.json()


def api_recall(query: str, max_tokens: int = 2000) -> dict:
    payload = {"query": query, "max_tokens": max_tokens}
    r = requests.post(
        f"{API_BASE}/api/memory/recall", json=payload,
        headers=_headers(), timeout=15,
    )
    r.raise_for_status()
    return r.json()


def api_temporal_search(
    query: str, as_of: str | None = None, limit: int = 10,
) -> dict:
    payload: dict[str, object] = {"query": query, "limit": limit}
    if as_of:
        payload["as_of"] = as_of
    r = requests.post(
        f"{API_BASE}/api/memory/search/temporal", json=payload,
        headers=_headers(), timeout=15,
    )
    r.raise_for_status()
    return r.json()


def api_entity_history(entity_name: str) -> dict:
    payload = {"entity_name": entity_name}
    r = requests.post(
        f"{API_BASE}/api/memory/entity/history", json=payload,
        headers=_headers(), timeout=15,
    )
    r.raise_for_status()
    return r.json()


def api_graph_data(limit: int = 200) -> dict:
    r = requests.get(
        f"{API_BASE}/api/memory/graph", params={"limit": limit},
        headers=_headers(), timeout=15,
    )
    r.raise_for_status()
    return r.json()


def api_memory_count() -> int:
    try:
        r = requests.get(
            f"{API_BASE}/api/memory/count",
            headers=_headers(), timeout=5,
        )
        return r.json().get("count", 0)
    except Exception:
        return 0


def api_memory_list(limit: int = 50) -> list[dict]:
    try:
        r = requests.get(
            f"{API_BASE}/api/memory/list",
            params={"limit": limit},
            headers=_headers(), timeout=10,
        )
        r.raise_for_status()
        return r.json().get("items", [])
    except Exception:
        return []


def api_generate_token(
    tenant_id: str = "demo", user_id: str = "dashboard",
) -> str | None:
    try:
        r = requests.post(
            f"{API_BASE}/api/auth/token",
            json={"tenant_id": tenant_id, "user_id": user_id},
            timeout=5,
        )
        r.raise_for_status()
        return r.json().get("token")
    except Exception:
        return None


def api_capture(episodes: list[dict], source: str = "dashboard") -> dict:
    payload = {"conversation": episodes, "source": source}
    r = requests.post(
        f"{API_BASE}/api/capture", json=payload,
        headers=_headers(), timeout=30,
    )
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------

def _render_metric(label: str, value: str | int, icon: str = ""):
    """Render a single glassmorphism metric card."""
    st.markdown(
        f"""<div class="metric-card">
            <div class="metric-value">{icon} {value}</div>
            <div class="metric-label">{label}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def _render_footer():
    st.markdown(
        """<div class="footer">
            Built with 💜 by
            <a href="https://github.com/membread" target="_blank">Membread</a>
            &nbsp;·&nbsp; Powered by
            <a href="https://github.com/getzep/graphiti" target="_blank">Graphiti</a>
            +
            <a href="https://www.falkordb.com/" target="_blank">FalkorDB</a>
            &nbsp;·&nbsp; 100 % local &amp; open-source
        </div>""",
        unsafe_allow_html=True,
    )


def _dark_plotly(fig: go.Figure) -> go.Figure:
    """Apply the dark transparent theme to any Plotly figure."""
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#a1a1aa",
        title_font_color="#e4e4e7",
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(font=dict(color="#a1a1aa")),
    )
    return fig


# =========================================================================
#  PAGE 1 — Overview
# =========================================================================

def page_overview():
    st.markdown(CONFETTI_JS, unsafe_allow_html=True)

    # Hero
    st.markdown(
        '<div class="hero-badge">'
        '🧠 Membread v0.1.1 — Bi-Temporal Knowledge Graph'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown("## System Overview")

    # ── Health ────────────────────────────────────────────────────
    health = api_health()
    is_up = health.get("status") == "healthy"
    dot = "green" if is_up else "red"
    status_label = "Online" if is_up else "Offline"

    # Metrics row
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f"""<div class="metric-card">
                <div class="metric-value">
                    <span class="status-dot {dot}"></span>{status_label}
                </div>
                <div class="metric-label">API Status</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with c2:
        _render_metric("Version", health.get("version", "—"))
    with c3:
        count = api_memory_count()
        _render_metric("Total Memories", f"{count:,}")
    with c4:
        _render_metric("Graph Backend", "FalkorDB")

    st.markdown("")

    # ── Quick Actions ─────────────────────────────────────────────
    st.markdown("### ⚡ Quick Actions")
    qa1, qa2 = st.columns(2)

    with qa1:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("**Store a Memory**")
        obs = st.text_area(
            "Observation",
            placeholder="e.g. Alice joined the ML infra team…",
            key="ov_store_obs",
            label_visibility="collapsed",
        )
        src = st.text_input(
            "Source (optional)",
            placeholder="slack, email, meeting…",
            key="ov_store_src",
        )
        if st.button("💾  Store", type="primary", key="ov_btn_store") and obs:
            with st.spinner("Storing…"):
                try:
                    meta = {"source": src} if src else {}
                    result = api_store(obs, meta)
                    st.success(
                        f"Stored!  ID `{result['observation_id'][:12]}…`  ·  "
                        f"{result.get('nodes_created', 0)} graph nodes  ·  "
                        f"{result.get('conflicts_resolved', 0)} conflicts resolved"
                    )
                except Exception as e:
                    st.error(f"Store failed: {e}")
        st.markdown("</div>", unsafe_allow_html=True)

    with qa2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("**Recall Context**")
        q = st.text_input(
            "Query",
            placeholder="What happened with Project Phoenix?",
            key="ov_recall_q",
            label_visibility="collapsed",
        )
        if st.button("🔍  Recall", key="ov_btn_recall") and q:
            with st.spinner("Recalling…"):
                try:
                    result = api_recall(q)
                    st.markdown(result["context"])
                    st.caption(
                        f"📎 Sources: {', '.join(result['sources'])}  ·  "
                        f"🔢 {result['token_count']} tokens  ·  "
                        f"{'🗜️ Compressed' if result['compressed'] else '📄 Raw'}"
                    )
                except Exception as e:
                    st.error(f"Recall failed: {e}")
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Memory timeline chart ─────────────────────────────────────
    st.markdown("### 📈 Memory Timeline")
    memories = api_memory_list(limit=50)
    if memories:
        rows: list[dict] = []
        for m in memories:
            ts = (
                m.get("metadata", {}).get("event_time")
                or m.get("metadata", {}).get("created_at")
            )
            source = m.get("metadata", {}).get("source", "unknown")
            if ts:
                try:
                    rows.append({"date": pd.to_datetime(ts).date(), "source": source})
                except Exception:
                    pass
        if rows:
            df = pd.DataFrame(rows)
            agg = (
                df.groupby(["date", "source"])
                .size()
                .reset_index(name="count")
            )
            fig = px.bar(
                agg, x="date", y="count", color="source",
                title="Memories ingested over time",
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            _dark_plotly(fig)
            fig.update_layout(xaxis_title="", yaxis_title="Count", legend_title_text="Source")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No timestamped memories yet — store some or load the demo data.")
    else:
        st.info(
            "No memories found. Store your first memory above, or run:\n\n"
            "```\npython scripts/seed_demo.py\n```"
        )

    _render_footer()


# =========================================================================
#  PAGE 2 — Temporal Time-Travel
# =========================================================================

def page_temporal():
    st.markdown("## 🕰️ Temporal Time-Travel")
    st.markdown(
        "Search what the system **knew at a specific point in time**.  "
        '<span class="tooltip-icon" title="event_time = when the fact '
        'happened.  ingestion_time = when it was recorded.  as_of filters '
        'by ingestion.">?</span>',
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns([3, 2, 1])
    with c1:
        query = st.text_input(
            "Search query",
            placeholder="Alice's role changes",
            key="ts_query",
        )
    with c2:
        as_of = st.date_input(
            "As-of date", value=datetime.date.today(), key="ts_as_of",
        )
    with c3:
        limit = st.number_input(
            "Limit", min_value=1, max_value=100, value=15, key="ts_limit",
        )

    travel_back = st.checkbox(
        "🔮 Enable time-travel (use as-of filter)", key="ts_enable",
    )

    if st.button("⏳  Search", type="primary", key="btn_ts") and query:
        as_of_str = as_of.isoformat() if travel_back else None
        with st.spinner("Searching the temporal index…"):
            try:
                result = api_temporal_search(query, as_of=as_of_str, limit=limit)
                hits = result.get("results", [])
                if not hits:
                    st.info("No results. Try a broader query or different date.")
                    _render_footer()
                    return

                if result.get("as_of"):
                    st.markdown(f"**Showing knowledge as of `{result['as_of']}`**")

                # Result cards
                for hit in hits:
                    score_pct = (
                        f"{hit['score']:.1%}"
                        if hit["score"] <= 1
                        else f"{hit['score']:.3f}"
                    )
                    text_preview = hit["text"][:120]
                    ellipsis = "…" if len(hit["text"]) > 120 else ""
                    st.markdown(
                        f"""<div class="hit-card">
                            <span class="hit-score">{score_pct}</span>
                            <strong>{text_preview}{ellipsis}</strong>
                            <div class="hit-meta">
                                📅 Event: {hit.get('event_time', '—')}
                                &nbsp;·&nbsp;
                                🕐 Ingested: {hit.get('ingestion_time', '—')}
                                &nbsp;·&nbsp;
                                📂 Source: {hit.get('source', '—')}
                                &nbsp;·&nbsp;
                                🕸️ Graph: {hit.get('graph_score', 0):.3f}
                            </div>
                        </div>""",
                        unsafe_allow_html=True,
                    )

                # ── Plotly scatter — results on timeline ──────
                tl_rows: list[dict] = []
                for h in hits:
                    if h.get("event_time"):
                        try:
                            tl_rows.append({
                                "event_time": pd.to_datetime(h["event_time"]),
                                "text": h["text"][:60],
                                "score": h["score"],
                                "source": h.get("source", "?"),
                            })
                        except Exception:
                            pass
                if tl_rows:
                    df = pd.DataFrame(tl_rows)
                    fig = px.scatter(
                        df, x="event_time", y="score", size="score",
                        hover_data=["text", "source"],
                        color="source",
                        title="Search results on timeline",
                        color_discrete_sequence=px.colors.qualitative.Vivid,
                    )
                    _dark_plotly(fig)
                    fig.update_layout(
                        xaxis_title="Event Time", yaxis_title="Relevance",
                    )
                    st.plotly_chart(fig, use_container_width=True)

            except Exception as e:
                st.error(f"Search failed: {e}")

    _render_footer()


# =========================================================================
#  PAGE 3 — Entity History
# =========================================================================

def page_entity_history():
    st.markdown("## 📜 Entity History")
    st.markdown(
        "View every recorded **version** of a named entity over time."
    )

    entity = st.text_input(
        "Entity Name",
        placeholder="Alice, Project Phoenix, Kubernetes…",
        key="eh_entity",
    )

    examples = ["Alice", "Bob", "Project Phoenix", "Project Falcon", "Kubernetes"]
    st.caption(f"Try: {' · '.join(examples)}")

    if st.button("🔎  Trace History", type="primary", key="btn_eh") and entity:
        with st.spinner(f"Tracing `{entity}` through time…"):
            try:
                result = api_entity_history(entity)
                versions = result.get("versions", [])

                if not versions:
                    st.warning(
                        f"No versions found for **{entity}**.  "
                        "Has it been mentioned in any stored memories?"
                    )
                    _render_footer()
                    return

                st.success(
                    f"Found **{len(versions)}** version(s) of "
                    f"**{result['entity_name']}**"
                )

                # ── Plotly timeline ───────────────────────────
                tl_rows: list[dict] = []
                for v in versions:
                    start = pd.to_datetime(v["valid_from"])
                    end = (
                        pd.to_datetime(v["valid_until"])
                        if v.get("valid_until")
                        else pd.Timestamp.now()
                    )
                    label = (
                        f"{v['name']}: "
                        f"{json.dumps(v.get('properties', {}))[:60]}"
                    )
                    tl_rows.append({
                        "Version": label,
                        "Start": start,
                        "End": end,
                        "Name": v["name"],
                    })

                if tl_rows:
                    df_tl = pd.DataFrame(tl_rows)
                    fig = px.timeline(
                        df_tl, x_start="Start", x_end="End", y="Version",
                        color="Name",
                        title=f'Timeline of "{entity}" versions',
                        color_discrete_sequence=[
                            "#8b5cf6", "#3b82f6", "#22c55e",
                            "#f59e0b", "#ef4444",
                        ],
                    )
                    _dark_plotly(fig)
                    fig.update_layout(
                        yaxis_title="", xaxis_title="", showlegend=False,
                    )
                    st.plotly_chart(fig, use_container_width=True)

                # ── Version cards ─────────────────────────────
                for v in versions:
                    is_current = v.get("valid_until") is None
                    css = (
                        "version-card" if is_current
                        else "version-card superseded"
                    )
                    badge = "🟢 Current" if is_current else "🟡 Superseded"
                    props_str = json.dumps(
                        v.get("properties", {}), indent=2,
                    )

                    valid_range = (
                        f"Valid from <code>{v['valid_from']}</code>"
                    )
                    if v.get("valid_until"):
                        valid_range += (
                            f" → <code>{v['valid_until']}</code>"
                        )
                    else:
                        valid_range += " → present"

                    st.markdown(
                        f"""<div class="{css}">
                            <strong>{v['name']}</strong>
                            &nbsp; <small>{badge}</small><br/>
                            <small style="color:#a1a1aa">{valid_range}</small>
                            <pre style="background:rgba(0,0,0,0.2);
                                        padding:0.5rem;
                                        border-radius:8px;
                                        margin-top:0.5rem;
                                        font-size:0.8rem;
                                        overflow-x:auto;">{props_str}</pre>
                        </div>""",
                        unsafe_allow_html=True,
                    )

            except Exception as e:
                st.error(f"Entity history failed: {e}")

    _render_footer()


# =========================================================================
#  PAGE 4 — Live Knowledge Graph
# =========================================================================

TYPE_COLORS = {
    "person": "#8b5cf6",
    "project": "#3b82f6",
    "technology": "#22c55e",
    "organization": "#f59e0b",
    "event": "#ef4444",
    "concept": "#ec4899",
}
DEFAULT_NODE_COLOR = "#6366f1"


def page_graph():
    st.markdown("## 🕸️ Live Knowledge Graph")
    st.markdown(
        "Interactive node-edge visualisation of the temporal graph."
    )

    c1, c2, c3 = st.columns([2, 2, 2])
    with c1:
        limit = st.slider("Max nodes", 10, 500, 150, key="graph_limit")
    with c2:
        physics = st.checkbox("Enable physics", value=True, key="graph_phys")
    with c3:
        auto_refresh = st.checkbox("Auto-refresh (30 s)", key="graph_auto")

    try:
        from streamlit_agraph import agraph, Node, Edge, Config as AgraphConfig  # type: ignore

        with st.spinner("Loading graph data…"):
            data = api_graph_data(limit=limit)

        nodes_data = data.get("nodes", [])
        edges_data = data.get("edges", [])

        if not nodes_data:
            st.info(
                "No graph data yet.  "
                "Store some memories to see the knowledge graph!"
            )
            _render_footer()
            return

        st.caption(
            f"Showing **{len(nodes_data)}** nodes · "
            f"**{len(edges_data)}** edges"
        )

        nodes_list = []
        for n in nodes_data:
            ntype = n.get("type", "").lower()
            color = TYPE_COLORS.get(ntype, DEFAULT_NODE_COLOR)
            label = n.get("label", n["id"][:10])
            nodes_list.append(
                Node(
                    id=n["id"],
                    label=label,
                    size=22,
                    color=color,
                    font={"color": "#e4e4e7", "size": 12},
                )
            )

        edges_list = [
            Edge(
                source=e["source"],
                target=e["target"],
                label=e.get("label", ""),
                color="#4a4a5a",
            )
            for e in edges_data
        ]

        agraph_config = AgraphConfig(
            width="100%",
            height=620,
            directed=True,
            physics=physics,
            hierarchical=False,
            nodeHighlightBehavior=True,
            highlightColor="#8b5cf6",
            node={"labelProperty": "label"},
        )

        agraph(nodes=nodes_list, edges=edges_list, config=agraph_config)

        # Legend
        legend_html = " &nbsp;·&nbsp; ".join(
            f'<span style="color:{c}">●</span> {t.title()}'
            for t, c in TYPE_COLORS.items()
        )
        st.markdown(
            f'<div style="text-align:center; font-size:0.8rem; '
            f'color:#a1a1aa; margin-top:0.5rem;">{legend_html}</div>',
            unsafe_allow_html=True,
        )

        # Export
        with st.expander("📥 Export Graph Data (JSON)"):
            st.json(data)

    except ImportError:
        st.warning(
            "Install `streamlit-agraph` for the interactive graph:\n\n"
            "```\npip install streamlit-agraph\n```"
        )
        data = api_graph_data(limit=limit)
        st.json(data)

    # Auto-refresh
    if auto_refresh:
        time.sleep(30)
        st.rerun()

    _render_footer()


# =========================================================================
#  PAGE 5 — Chat with Memory
# =========================================================================

def page_chat():
    st.markdown("## 💬 Chat with Memory")
    st.markdown(
        "Ask natural-language questions — the system recalls context "
        "from the knowledge graph."
    )

    # Init
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Render history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("meta"):
                st.caption(msg["meta"])

    # Chat input
    if prompt := st.chat_input("Ask anything about your memories…"):
        st.session_state.chat_history.append(
            {"role": "user", "content": prompt},
        )
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Searching memory…"):
                try:
                    result = api_recall(prompt, max_tokens=3000)
                    context = result.get("context", "No relevant context found.")
                    sources = result.get("sources", [])
                    token_count = result.get("token_count", 0)
                    compressed = result.get("compressed", False)

                    st.markdown(context)
                    meta = (
                        f"📎 {len(sources)} sources  ·  "
                        f"🔢 {token_count} tokens  ·  "
                        f"{'🗜️ Compressed' if compressed else '📄 Raw'}"
                    )
                    st.caption(meta)

                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": context,
                        "meta": meta,
                    })
                except Exception as e:
                    err = f"Could not recall: {e}"
                    st.error(err)
                    st.session_state.chat_history.append(
                        {"role": "assistant", "content": f"⚠️ {err}"},
                    )

    # Clear button
    if st.button("🗑️ Clear Chat", key="btn_clear_chat"):
        st.session_state.chat_history = []
        st.rerun()

    _render_footer()


# =========================================================================
#  Sidebar
# =========================================================================

def render_sidebar():
    with st.sidebar:
        st.markdown("# 🧠 Membread")
        st.caption("Bi-temporal knowledge graph for AI agents")
        st.divider()

        # ── Authentication ────────────────────────────────────────
        st.markdown("**🔑 Authentication**")
        token = st.text_input(
            "JWT Token",
            value=st.session_state.get("jwt_token", ""),
            type="password",
            key="sidebar_token",
            help="Paste a JWT or click Auto-generate below",
        )
        if token != st.session_state.get("jwt_token", ""):
            st.session_state.jwt_token = token

        if st.button("🔄 Auto-generate Token", key="btn_gen_token"):
            with st.spinner("Generating…"):
                new_token = api_generate_token()
                if new_token:
                    st.session_state.jwt_token = new_token
                    st.success("Token generated!")
                    st.rerun()
                else:
                    st.error("Could not generate — is the API running?")

        st.divider()

        # ── Connection status ─────────────────────────────────────
        health = api_health()
        is_up = health.get("status") == "healthy"
        dot = "green" if is_up else "red"
        label = "Connected" if is_up else "Disconnected"
        st.markdown(
            f'<span class="status-dot {dot}"></span> API: **{label}**',
            unsafe_allow_html=True,
        )
        st.caption(f"Endpoint: `{API_BASE}`")

        st.divider()

        # ── Links ─────────────────────────────────────────────────
        st.markdown("**📚 Resources**")
        st.markdown(
            "[GitHub](https://github.com/membread) · "
            "[Docs](https://github.com/membread) · "
            "[API Spec](http://localhost:8000/docs)"
        )

        st.divider()
        st.markdown(
            '<div style="font-size:0.75rem; color:#71717a; '
            'text-align:center;">100% local · open-source · MIT<br/>'
            "v0.1.1</div>",
            unsafe_allow_html=True,
        )


# =========================================================================
#  App shell
# =========================================================================

def main():
    st.set_page_config(
        page_title="Membread Dashboard",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Inject CSS
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    # Init session state
    if "jwt_token" not in st.session_state:
        st.session_state.jwt_token = os.getenv("MEMBREAD_TOKEN", "")

    render_sidebar()

    # Navigation
    page = st.sidebar.radio(
        "Navigate",
        [
            "📊 Overview",
            "🕰️ Time-Travel",
            "📜 Entity History",
            "🕸️ Knowledge Graph",
            "💬 Chat",
        ],
        label_visibility="collapsed",
    )

    if page == "📊 Overview":
        page_overview()
    elif page == "🕰️ Time-Travel":
        page_temporal()
    elif page == "📜 Entity History":
        page_entity_history()
    elif page == "🕸️ Knowledge Graph":
        page_graph()
    elif page == "💬 Chat":
        page_chat()


if __name__ == "__main__":
    main()
