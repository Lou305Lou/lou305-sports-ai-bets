
# ================================
# Sports AI Betting Dashboard V8.1 Mobile Pro
# ================================

import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Sports AI Betting Dashboard V8.1", layout="wide")

# -------------------------------
# Sample Data (replace with your pipeline)
# -------------------------------
def load_data():
    return pd.DataFrame([
        {"player":"Stephen Curry","team":"GSW","market":"points","bet_side":"Over","line":27,"projection":32,"odds":-115,"minutes":35,"starter":True},
        {"player":"LeBron James","team":"LAL","market":"pra","bet_side":"Over","line":38,"projection":44,"odds":-115,"minutes":36,"starter":True},
        {"player":"Anthony Davis","team":"LAL","market":"rebounds","bet_side":"Over","line":11.5,"projection":13.2,"odds":-105,"minutes":35,"starter":True},
    ])

def compute(df):
    df = df.copy()
    df["hit_prob"] = 0.65
    df["true_edge"] = 0.20
    df["ev"] = 0.27
    df["score"] = 88
    df["stake"] = 1.25
    df["script_type"] = "Track meet"
    df["variance"] = "High-upside"
    return df.sort_values("ev", ascending=False)

# -------------------------------
# UI
# -------------------------------
st.title("🏀 Sports AI Betting Dashboard V8.1")

df = compute(load_data())

# Compact filters (mobile friendly)
with st.expander("⚙️ Filters", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        starters_only = st.toggle("Starters only", value=True)
    with col2:
        min_minutes = st.slider("Min minutes", 0, 40, 0)

    odds_range = st.selectbox(
        "Odds Range",
        ["All", "-300 to +200", "-200 to +150", "Plus Money Only"]
    )

# Apply filters
if starters_only:
    df = df[df["starter"] == True]
df = df[df["minutes"] >= min_minutes]

# -------------------------------
# Best Bet (Top Card)
# -------------------------------
best = df.iloc[0]

st.subheader("🔥 Best Bet")

st.markdown(f"### {best['player']} — {best['bet_side']} {best['line']} {best['market']}")
st.markdown(f"**Odds:** {best['odds']} | **EV:** {best['ev']*100:.1f}%")

col1, col2, col3 = st.columns(3)
col1.metric("Hit %", f"{best['hit_prob']*100:.0f}%")
col2.metric("Edge", f"{best['true_edge']*100:.1f}%")
col3.metric("Stake", f"{best['stake']}u")

st.progress(best["hit_prob"])

with st.expander("📊 Why This Play"):
    st.write(f"Projection Edge: +{best['projection'] - best['line']:.1f}")
    st.write(f"Game Script: {best['script_type']}")
    st.write(f"Risk Profile: {best['variance']}")

# -------------------------------
# Remaining Plays (Condensed)
# -------------------------------
st.subheader("📋 Other Plays")

for _, row in df.iloc[1:].iterrows():
    with st.container():
        st.markdown(f"**{row['player']} — {row['bet_side']} {row['line']} {row['market']}**")
        st.caption(f"Odds {row['odds']} | EV {row['ev']*100:.1f}% | Stake {row['stake']}u")
        st.divider()

# -------------------------------
# Bankroll Summary
# -------------------------------
st.subheader("💰 Bankroll")

col1, col2, col3 = st.columns(3)
col1.metric("Top Stake", "1.25u")
col2.metric("Parlay Stake", "1.00u")
col3.metric("ROI", "37.3%")
