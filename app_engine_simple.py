#!/usr/bin/env python3

# ============================
# SIMPLE ENGINE UI (SAFE SANDBOX)
# ============================

import os
from datetime import datetime

import pandas as pd
import streamlit as st

from engine import (
    init_db,
    refresh_all_sports,
    analyze_cards_with_qwen,
)

# ----------------------------
# Page config
# ----------------------------
st.set_page_config(
    page_title="Sports AI Engine – Simple",
    layout="wide",
)

st.title("Sports AI Bets – Engine Control (Simple App)")

st.caption(
    "This is a clean, minimal UI wired directly to engine.py.\n"
    "Your big V34 dashboard is untouched. You can keep using it separately."
)

# ----------------------------
# Initialize DB
# ----------------------------
init_db()

# ----------------------------
# Session state
# ----------------------------
if "last_ai_result" not in st.session_state:
    st.session_state["last_ai_result"] = None

if "last_run_time" not in st.session_state:
    st.session_state["last_run_time"] = ""

# ----------------------------
# Helper to render AI result
# ----------------------------
def render_ai_result(result):
    if not result:
        st.warning("No AI result available yet.")
        return

    engine_state = result.get("engine_state", "unknown")
    notes = result.get("notes", "")
    strong_cards = result.get("strong_cards", [])
    parlays = result.get("parlay_suggestions", [])

    st.subheader("Engine State")
    st.write(engine_state)

    if notes:
        st.subheader("Notes")
        st.write(notes)

    st.subheader("Strong Cards")
    if strong_cards:
        st.dataframe(pd.DataFrame(strong_cards))
    else:
        st.info("No strong cards returned.")

    st.subheader("Parlay Suggestions")
    if parlays:
        st.dataframe(pd.DataFrame(parlays))
    else:
        st.info("No parlay suggestions returned.")

# ----------------------------
# Main controls
# ----------------------------
st.markdown("### Controls")

col1, col2 = st.columns(2)

with col1:
    if st.button("Refresh Odds + Run AI", type="primary"):
        with st.spinner("Refreshing odds and running AI selection..."):
            # 1) Refresh odds (all sports)
            refresh_all_sports()

            # 2) Run AI selection
            result = analyze_cards_with_qwen()

            st.session_state["last_ai_result"] = result
            st.session_state["last_run_time"] = datetime.utcnow().strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            )

        if result:
            st.success("Done: odds refreshed and AI selection completed.")
        else:
            st.warning("Odds refreshed, but AI did not return a result.")

with col2:
    if st.button("Show Last AI Result"):
        if st.session_state["last_ai_result"] is None:
            st.info("No AI result stored yet. Run 'Refresh Odds + Run AI' first.")
        else:
            st.success("Showing last stored AI result below.")

# ----------------------------
# Status + last run
# ----------------------------
st.markdown("---")
st.markdown("### Status")

if st.session_state["last_run_time"]:
    st.write(f"**Last engine run:** {st.session_state['last_run_time']}")
else:
    st.write("Engine has not been run yet in this session.")

st.markdown("---")
st.markdown("### AI Output")

render_ai_result(st.session_state["last_ai_result"])
