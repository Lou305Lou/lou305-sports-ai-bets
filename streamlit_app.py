
# V23 - Self-Learning AI + Sharp Money Detection + Market Inefficiency Scanner

import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Sports AI V23", layout="wide")

st.title("🔥 Sports Betting AI Dashboard V23")

# --- Session State ---
if "bet_log" not in st.session_state:
    st.session_state.bet_log = pd.DataFrame(columns=[
        "game", "market", "odds", "result", "clv", "model_score"
    ])

# --- Self-Learning Weights ---
if "model_weights" not in st.session_state:
    st.session_state.model_weights = {
        "model_1": 1.0,
        "model_2": 1.0,
        "model_3": 1.0,
        "model_4": 1.0,
        "model_5": 1.0,
    }

st.header("🧠 Self-Learning Engine")

if st.button("Update Model Weights Based on Results"):
    df = st.session_state.bet_log
    if not df.empty:
        win_rate = df[df["result"] == "win"].shape[0] / len(df)
        for k in st.session_state.model_weights:
            st.session_state.model_weights[k] *= (1 + win_rate)
    st.success("Model weights updated!")

st.write(st.session_state.model_weights)

# --- Sharp Money Detection ---
st.header("💰 Sharp Money Detection")

line_open = st.number_input("Opening Line", value=-110)
line_current = st.number_input("Current Line", value=-120)
public_pct = st.slider("Public Betting %", 0, 100, 70)

if line_current < line_open and public_pct > 60:
    st.success("Sharp money detected (reverse line movement)")
else:
    st.warning("No strong sharp signal")

# --- Market Inefficiency Scanner ---
st.header("📊 Market Inefficiency Scanner")

book_a = st.number_input("Book A Odds", value=+120)
book_b = st.number_input("Book B Odds", value=-110)

if abs(book_a - book_b) > 20:
    st.success("Market inefficiency detected!")
else:
    st.info("Market fairly efficient")

# --- Bet Tracker ---
st.header("📒 Bet Tracker")

with st.form("add_bet"):
    game = st.text_input("Game")
    market = st.text_input("Market")
    odds = st.number_input("Odds", value=-110)
    result = st.selectbox("Result", ["pending", "win", "loss"])
    clv = st.number_input("CLV", value=0.0)
    model_score = st.slider("Model Score", 0, 100, 50)

    submitted = st.form_submit_button("Add Bet")
    if submitted:
        new_row = pd.DataFrame([[game, market, odds, result, clv, model_score]],
                               columns=st.session_state.bet_log.columns)
        st.session_state.bet_log = pd.concat([st.session_state.bet_log, new_row], ignore_index=True)

st.dataframe(st.session_state.bet_log)

# --- Simple Analytics ---
st.header("📈 Performance")

if not st.session_state.bet_log.empty:
    wins = st.session_state.bet_log[st.session_state.bet_log["result"] == "win"].shape[0]
    total = len(st.session_state.bet_log)
    st.metric("Win Rate", f"{(wins/total)*100:.2f}%")
