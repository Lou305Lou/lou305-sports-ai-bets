
# Simplified working version (stable reset)
import streamlit as st
import pandas as pd
from datetime import datetime

st.title("Sports AI Betting Dashboard")

if "ai_perf_df" not in st.session_state:
    st.session_state.ai_perf_df = pd.DataFrame()

st.write("App reset version working.")

if st.button("Test AI Save"):
    new_row = {
        "date": datetime.now(),
        "pick": "Test Pick",
        "confidence": 75
    }
    st.session_state.ai_perf_df = pd.concat(
        [st.session_state.ai_perf_df, pd.DataFrame([new_row])],
        ignore_index=True
    )

st.write(st.session_state.ai_perf_df)
