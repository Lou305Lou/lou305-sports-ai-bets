
# ===============================
# V11 MULTI-AI PREDICTION ENGINE
# ===============================

import math
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Sports AI Betting Dashboard V11", layout="wide")

# -----------------------------
# MODEL 1: PROJECTION MODEL
# -----------------------------
def model_projection(row):
    proj = row.get("projection", 0)
    line = row.get("line", 0)
    edge = proj - line
    return edge

# -----------------------------
# MODEL 2: MARKET MODEL
# -----------------------------
def model_market(row):
    open_odds = row.get("open_odds", row.get("odds"))
    current_odds = row.get("odds")
    if open_odds is None or current_odds is None:
        return 0
    move = current_odds - open_odds
    return -move  # better if odds shorten

# -----------------------------
# MODEL 3: CLV MODEL
# -----------------------------
def model_clv(row):
    edge = model_projection(row)
    return max(0, edge * 0.5)

# -----------------------------
# MODEL 4: GAME SCRIPT MODEL
# -----------------------------
def model_gamescript(row):
    spread = row.get("spread", 0)
    usage = row.get("usage", 0)
    return (usage * 0.1) + (abs(spread) * 0.05)

# -----------------------------
# MODEL 5: VARIANCE MODEL
# -----------------------------
def model_variance(row):
    minutes = row.get("minutes", 0)
    volatility = row.get("minutes_volatility", 2)
    return max(0, (minutes / 36) - (volatility * 0.2))

# -----------------------------
# CONSENSUS ENGINE
# -----------------------------
def multi_ai_score(row):
    scores = {
        "projection": model_projection(row),
        "market": model_market(row),
        "clv": model_clv(row),
        "gamescript": model_gamescript(row),
        "variance": model_variance(row),
    }

    weights = {
        "projection": 0.30,
        "market": 0.20,
        "clv": 0.20,
        "gamescript": 0.15,
        "variance": 0.15,
    }

    final_score = sum(scores[k] * weights[k] for k in scores)
    return final_score, scores

# -----------------------------
# SAMPLE DATA
# -----------------------------
def sample_data():
    return pd.DataFrame([
        {"player": "Stephen Curry", "market": "points", "line": 27, "projection": 32.2, "odds": -110, "open_odds": -102, "spread": -2.5, "usage": 31, "minutes": 35, "minutes_volatility": 2.1},
        {"player": "LeBron James", "market": "pra", "line": 38, "projection": 43.8, "odds": -115, "open_odds": -105, "spread": 2.5, "usage": 30, "minutes": 36, "minutes_volatility": 2.2},
        {"player": "Anthony Davis", "market": "rebounds", "line": 11.5, "projection": 13.1, "odds": -105, "open_odds": -104, "spread": 2.5, "usage": 27, "minutes": 35, "minutes_volatility": 2.6},
    ])

df = sample_data()

# -----------------------------
# RUN MODELS
# -----------------------------
results = []
for _, row in df.iterrows():
    score, breakdown = multi_ai_score(row)
    results.append({
        "player": row["player"],
        "market": row["market"],
        "score": round(score, 2),
        **{f"{k}_model": round(v,2) for k,v in breakdown.items()}
    })

results_df = pd.DataFrame(results).sort_values("score", ascending=False)

# -----------------------------
# UI
# -----------------------------
st.title("🧠 V11 Multi-AI Prediction Engine")

st.markdown("### 🏆 Final Rankings")
st.dataframe(results_df, use_container_width=True)

top = results_df.iloc[0]
st.markdown(f"## 🔥 Best AI Play: {top['player']} ({top['market']})")

st.markdown("### 📊 Model Breakdown")
st.write(top)
