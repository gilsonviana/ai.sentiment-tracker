import datetime
import re
import time

import httpx
import pandas as pd
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


def patch_entry(entry_id: str, payload: dict) -> dict:
    with httpx.Client(base_url=API_BASE, timeout=10.0) as client:
        r = client.patch(f"/entries/{entry_id}", json=payload)
        r.raise_for_status()
        return r.json()


def generate_reflection(start: str | None = None, end: str | None = None) -> dict:
    params = {}
    if start:
        params["start"] = start
    if end:
        params["end"] = end
    with httpx.Client(base_url=API_BASE, timeout=180.0) as client:
        r = client.post("/reflect", params=params)
        r.raise_for_status()
        return r.json()


def fetch_reflections() -> list[dict]:
    with httpx.Client(base_url=API_BASE, timeout=10.0) as client:
        r = client.get("/reflect")
        r.raise_for_status()
        return r.json()


def ask_question(question: str) -> dict:
    with httpx.Client(base_url=API_BASE, timeout=180.0) as client:
        r = client.post("/chat", json={"question": question})
        r.raise_for_status()
        return r.json()


def fetch_mood_data(month: str) -> dict:
    with httpx.Client(base_url=API_BASE, timeout=10.0) as client:
        r = client.get(f"/mood/{month}")
        r.raise_for_status()
        return r.json()


def check_health() -> dict:
    with httpx.Client(base_url=API_BASE, timeout=5.0) as client:
        r = client.get("/health")
        r.raise_for_status()
        return r.json()


# ── Reusable display components ───────────────────────────────────────────────

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


def render_mood_badge(avg_mood: float) -> None:
    if avg_mood >= 0.2:
        color, label = "green", "Positive"
    elif avg_mood <= -0.2:
        color, label = "red", "Negative"
    else:
        color, label = "orange", "Neutral"
    st.markdown(f"**Avg mood:** :{color}[{label}] `{avg_mood:+.2f}`")


# ── App layout ────────────────────────────────────────────────────────────────

st.set_page_config(page_title="AI Sentiment Tracker", layout="wide")
st.title("AI Sentiment Tracker")

# Session state
for key, default in [
    ("submitted_entry_id", None),
    ("analysis_result", None),
    ("poll_error", None),
    ("reflection_result", None),
    ("reflection_error", None),
    ("chat_answer", None),
    ("chat_sources", 0),
    ("chat_error", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

tab_write, tab_browse, tab_reflect, tab_chat, tab_insights, tab_health = st.tabs(
    ["Write Entry", "Browse Entries", "Reflection", "Chat", "Insights", "API Health"]
)


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
        st.markdown("&nbsp;", unsafe_allow_html=True)
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

                st.divider()
                with st.form(key=f"edit_{entry['id']}"):
                    st.markdown("**Edit Entry**")
                    new_content = st.text_area(
                        "Content",
                        value=entry["content"],
                        max_chars=5000,
                        height=150,
                    )
                    new_date = st.date_input(
                        "Entry date",
                        value=datetime.date.fromisoformat(entry_date_str),
                    )
                    st.caption(f"{len(new_content)} / 5000 characters")
                    if st.form_submit_button("Save Changes", type="primary"):
                        content_changed = new_content.strip() != entry["content"]
                        date_changed = new_date.isoformat() != entry_date_str
                        if not content_changed and not date_changed:
                            st.warning("No changes made.")
                        else:
                            try:
                                update_payload: dict = {}
                                if content_changed:
                                    update_payload["content"] = new_content.strip()
                                if date_changed:
                                    update_payload["entry_date"] = new_date.isoformat()
                                patch_entry(entry["id"], update_payload)
                                st.success(
                                    "Entry updated — re-analysis queued."
                                    if content_changed else "Entry date updated."
                                )
                                st.rerun()
                            except httpx.HTTPStatusError as e:
                                try:
                                    detail = e.response.json().get("detail", str(e))
                                except Exception:
                                    detail = str(e)
                                st.error(f"Update failed: {detail}")
                            except Exception as e:
                                st.error(f"Update failed: {e}")


# ── Tab 3: Reflection ─────────────────────────────────────────────────────────

with tab_reflect:
    st.subheader("Generate Reflection")
    st.caption(
        "Leave the date range blank to use the last 7 days, or specify a custom window."
    )

    col_start, col_end = st.columns(2)
    with col_start:
        reflect_start = st.date_input(
            "From (optional)", value=None, key="reflect_start"
        )
    with col_end:
        reflect_end = st.date_input(
            "To (optional)", value=None, key="reflect_end"
        )

    if st.button("Generate Reflection", type="primary"):
        st.session_state.reflection_result = None
        st.session_state.reflection_error = None
        with st.spinner("Generating reflection with Ollama… this may take a minute."):
            try:
                result = generate_reflection(
                    start=reflect_start.isoformat() if reflect_start else None,
                    end=reflect_end.isoformat() if reflect_end else None,
                )
                st.session_state.reflection_result = result
            except httpx.HTTPStatusError as e:
                try:
                    detail = e.response.json().get("detail", str(e))
                except Exception:
                    detail = str(e)
                st.session_state.reflection_error = detail
            except Exception as e:
                st.session_state.reflection_error = str(e)

    if st.session_state.reflection_error:
        st.error(st.session_state.reflection_error)
    elif st.session_state.reflection_result:
        r = st.session_state.reflection_result
        col_l, col_r = st.columns([3, 1])
        with col_r:
            render_mood_badge(r["avg_mood"])
            st.caption(f"{r['entry_count']} entries · {r['window_start']} → {r['window_end']}")
        with col_l:
            st.markdown(r["narrative"])

    st.divider()
    st.subheader("Past Reflections")

    if st.button("Load History", key="load_reflections"):
        try:
            past = fetch_reflections()
            if not past:
                st.info("No reflections saved yet.")
            else:
                for ref in past:
                    ts = ref["generated_at"][:10]
                    header = f"{ts} · {ref['window_start']} → {ref['window_end']} · {ref['entry_count']} entries"
                    with st.expander(header):
                        render_mood_badge(ref["avg_mood"])
                        st.markdown(ref["narrative"])
        except Exception as e:
            st.error(f"Could not load reflections: {e}")


# ── Tab 4: Chat ───────────────────────────────────────────────────────────────

with tab_chat:
    st.subheader("Ask Your Journal")
    st.caption(
        'Ask questions about your entries — e.g. "How did I feel about work this month?"'
    )

    question = st.text_input(
        "Your question",
        placeholder="How have I been feeling lately?",
        key="chat_question",
        max_chars=1000,
    )

    ask_disabled = not question.strip()

    if st.button("Ask", type="primary", disabled=ask_disabled):
        st.session_state.chat_answer = None
        st.session_state.chat_error = None
        st.session_state.chat_sources = 0
        with st.spinner("Thinking…"):
            try:
                result = ask_question(question.strip())
                st.session_state.chat_answer = result["answer"]
                st.session_state.chat_sources = result["sources_used"]
            except httpx.HTTPStatusError as e:
                try:
                    detail = e.response.json().get("detail", str(e))
                except Exception:
                    detail = str(e)
                st.session_state.chat_error = detail
            except Exception as e:
                st.session_state.chat_error = str(e)

    if st.session_state.chat_error:
        st.error(st.session_state.chat_error)
    elif st.session_state.chat_answer:
        st.markdown(st.session_state.chat_answer)
        st.caption(f"Based on {st.session_state.chat_sources} journal entr{'y' if st.session_state.chat_sources == 1 else 'ies'}.")


# ── Tab 5: Insights ───────────────────────────────────────────────────────────

with tab_insights:
    st.subheader("Mood Chart")

    default_month = datetime.date.today().strftime("%Y-%m")
    insight_month = st.text_input(
        "Month", value=default_month, placeholder="YYYY-MM", key="insight_month"
    )

    if st.button("Load Chart", type="primary"):
        if not re.match(r"^\d{4}-\d{2}$", insight_month.strip()):
            st.error("Invalid format. Use YYYY-MM (e.g. 2026-05).")
        else:
            try:
                mood_data = fetch_mood_data(insight_month.strip())

                st.markdown(f"**{mood_data['entry_count']} entries**")
                render_mood_badge(mood_data["avg_mood"])
                st.divider()

                df = pd.DataFrame(mood_data["entries"])
                df["date"] = pd.to_datetime(df["date"])
                df = df.set_index("date").sort_index()

                st.line_chart(df["score"], use_container_width=True)
                st.caption("Composite mood score (−1 = very negative, +1 = very positive)")

                st.divider()
                st.markdown("**Entry breakdown:**")
                for _, row in df.reset_index().iterrows():
                    color = {"positive": "green", "neutral": "orange", "negative": "red"}.get(
                        row["label"], "gray"
                    )
                    st.markdown(
                        f"`{str(row['date'])[:10]}` — :{color}[{row['label'].upper()}] "
                        f"`{row['score']:+.3f}`"
                    )
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    st.info(f"No processed entries found for {insight_month.strip()}.")
                else:
                    st.error(f"API error: {e}")
            except Exception as e:
                st.error(f"Could not load mood data: {e}")


# ── Tab 6: API Health ─────────────────────────────────────────────────────────

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
| `PATCH` | `/entries/{id}` | Edit entry content or date |
| `GET` | `/entries/{id}/analysis` | Fetch sentiment scores and entities |
| `POST` | `/reflect` | Generate reflection (optional `?start=&end=`) |
| `GET` | `/reflect` | List past reflections |
| `POST` | `/chat` | Ask a question about your journal (RAG) |
| `GET` | `/mood/{month}` | Monthly mood report for charting |
"""
    )
