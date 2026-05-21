import datetime
import re
import time

import httpx
import streamlit as st

API_BASE = "http://localhost:8000"
POLL_INTERVAL = 1.5
MAX_POLLS = 40


# ── API helpers ───────────────────────────────────────────────────────────────

def post_entry(content: str, entry_date: str) -> dict:
    with httpx.Client(base_url=API_BASE, timeout=10.0) as client:
        r = client.post("/entries", json={"content": content, "entry_date": entry_date})
        r.raise_for_status()
        return r.json()


def poll_until_done(entry_id: str) -> dict:
    with httpx.Client(base_url=API_BASE, timeout=10.0) as client:
        for _ in range(MAX_POLLS):
            r = client.get(f"/entries/{entry_id}")
            r.raise_for_status()
            entry = r.json()
            if entry["status"] != "pending":
                return entry
            time.sleep(POLL_INTERVAL)
    raise RuntimeError(
        f"Timed out after {MAX_POLLS * POLL_INTERVAL:.0f}s waiting for entry {entry_id}"
    )


def fetch_analysis(entry_id: str) -> dict:
    with httpx.Client(base_url=API_BASE, timeout=10.0) as client:
        r = client.get(f"/entries/{entry_id}/analysis")
        r.raise_for_status()
        return r.json()


def fetch_all_entries(month: str | None = None) -> list[dict]:
    params = {"month": month} if month else {}
    with httpx.Client(base_url=API_BASE, timeout=10.0) as client:
        r = client.get("/entries", params=params)
        r.raise_for_status()
        return r.json()


def check_health() -> dict:
    with httpx.Client(base_url=API_BASE, timeout=5.0) as client:
        r = client.get("/health")
        r.raise_for_status()
        return r.json()


# ── Reusable display component ────────────────────────────────────────────────

def render_analysis(analysis: dict) -> None:
    label = analysis["label"]
    color = {"positive": "green", "neutral": "orange", "negative": "red"}.get(label, "gray")
    st.markdown(f"**Sentiment:** :{color}[{label.upper()}]")

    col1, col2, col3 = st.columns(3)
    col1.metric("VADER", f"{analysis['vader_score']:+.3f}")
    col2.metric("RoBERTa", f"{analysis['roberta_score']:+.3f}")
    col3.metric("Composite", f"{analysis['composite_score']:+.3f}")

    entities = analysis.get("entities", [])
    if entities:
        st.markdown("**Named Entities:**")
        tags_html = " ".join(
            f'<span style="background:#e8e8e8;padding:3px 10px;border-radius:12px;'
            f'font-size:0.85em;margin:2px">{e}</span>'
            for e in entities
        )
        st.markdown(tags_html, unsafe_allow_html=True)
    else:
        st.caption("No named entities detected.")

    if analysis.get("analysed_at"):
        st.caption(f"Analysed at: {analysis['analysed_at'][:19].replace('T', ' ')} UTC")


# ── App layout ────────────────────────────────────────────────────────────────

st.set_page_config(page_title="AI Sentiment Tracker", layout="wide")
st.title("AI Sentiment Tracker")

# Session state
for key, default in [
    ("submitted_entry_id", None),
    ("analysis_result", None),
    ("poll_error", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

tab_write, tab_browse, tab_health = st.tabs(["Write Entry", "Browse Entries", "API Health"])


# ── Tab 1: Write Entry ────────────────────────────────────────────────────────

with tab_write:
    entry_date = st.date_input("Entry date", value=datetime.date.today())
    content = st.text_area(
        label="Journal entry",
        max_chars=5000,
        height=200,
        placeholder="Write what's on your mind...",
        key="entry_input",
    )
    char_count = len(content)
    st.caption(f"{char_count} / 5000 characters")

    has_letter = bool(re.search(r"[a-zA-Z]", content.strip()))
    submit_disabled = char_count == 0 or not has_letter

    if st.button("Submit Entry", disabled=submit_disabled, type="primary"):
        st.session_state.submitted_entry_id = None
        st.session_state.analysis_result = None
        st.session_state.poll_error = None
        try:
            entry = post_entry(content, entry_date.isoformat())
            st.session_state.submitted_entry_id = entry["id"]
        except Exception as e:
            st.error(f"Failed to submit: {e}")

    if st.session_state.submitted_entry_id:
        entry_id = st.session_state.submitted_entry_id
        st.info(f"Entry ID: `{entry_id}`")

        if st.session_state.analysis_result is None and st.session_state.poll_error is None:
            with st.spinner("Analysing your entry..."):
                try:
                    final_entry = poll_until_done(entry_id)
                    if final_entry["status"] == "processed":
                        st.session_state.analysis_result = fetch_analysis(entry_id)
                    else:
                        st.session_state.poll_error = "Analysis failed on the server."
                except RuntimeError as e:
                    st.session_state.poll_error = str(e)
                except Exception as e:
                    st.session_state.poll_error = f"Unexpected error: {e}"

        if st.session_state.poll_error:
            st.error(st.session_state.poll_error)
        elif st.session_state.analysis_result:
            st.success("Analysis complete")
            st.divider()
            render_analysis(st.session_state.analysis_result)


# ── Tab 2: Browse Entries ─────────────────────────────────────────────────────

with tab_browse:
    col_month, col_filter, col_search, col_refresh = st.columns([1, 1, 2, 1])
    with col_month:
        month_filter = st.text_input("Month", placeholder="YYYY-MM")
    with col_filter:
        status_filter = st.selectbox(
            "Status",
            options=["All", "processed", "pending", "failed"],
            index=0,
        )
    with col_search:
        search_term = st.text_input("Search content", placeholder="Filter by keyword...")
    with col_refresh:
        st.markdown("&nbsp;", unsafe_allow_html=True)  # vertical alignment spacer
        refresh = st.button("Refresh", key="refresh_browse")

    try:
        entries = fetch_all_entries(month=month_filter.strip() or None)
    except Exception as e:
        st.error(f"Could not load entries: {e}")
        entries = []

    if status_filter != "All":
        entries = [e for e in entries if e["status"] == status_filter]
    if search_term:
        entries = [e for e in entries if search_term.lower() in e["content"].lower()]

    if not entries:
        st.info("No entries match the current filters.")
    else:
        count = len(entries)
        st.markdown(f"**{count} entr{'y' if count == 1 else 'ies'}**")
        st.divider()

        for entry in entries:
            badge_color = {"processed": "green", "pending": "orange", "failed": "red"}.get(
                entry["status"], "gray"
            )
            badge = f":{badge_color}[{entry['status'].upper()}]"
            entry_date_str = entry.get("entry_date", "")[:10]
            preview = entry["content"][:80] + ("…" if len(entry["content"]) > 80 else "")
            header = f"{badge}  ·  {entry_date_str}  ·  {preview}"

            with st.expander(header):
                st.markdown(f"**ID:** `{entry['id']}`")
                st.markdown(f"**Entry date:** {entry_date_str}")
                st.markdown(f"**Content:**\n\n{entry['content']}")
                st.divider()

                if entry["status"] == "processed":
                    try:
                        analysis = fetch_analysis(entry["id"])
                        render_analysis(analysis)
                    except Exception as e:
                        st.warning(f"Could not load analysis: {e}")
                elif entry["status"] == "pending":
                    st.info("Still processing — refresh to check again.")
                else:
                    st.error("Analysis failed for this entry.")


# ── Tab 3: API Health ─────────────────────────────────────────────────────────

with tab_health:
    st.subheader("API Health")
    st.markdown(f"**Base URL:** `{API_BASE}`")

    if st.button("Check Health", type="primary"):
        try:
            result = check_health()
            st.success(f"API is up — status: **{result.get('status', 'unknown')}**")
        except Exception as e:
            st.error(f"API is unreachable: {e}")

    st.divider()
    st.markdown("**Endpoints exercised by this UI:**")
    st.markdown(
        """
| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Liveness check |
| `POST` | `/entries` | Submit new entry |
| `GET` | `/entries` | List all entries |
| `GET` | `/entries/{id}` | Poll processing status |
| `GET` | `/entries/{id}/analysis` | Fetch sentiment scores and entities |
"""
    )
