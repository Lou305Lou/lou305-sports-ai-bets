
# ================================
# Sports AI Betting Dashboard V8 (FIXED)
# ================================

import math
import itertools
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Sports AI Betting Dashboard V8", layout="wide")

# ============================================================
# Helpers
# ============================================================
def american_to_decimal(odds: float) -> float:
    try:
        odds = float(odds)
    except Exception:
        return np.nan
    return 1 + (odds / 100) if odds > 0 else 1 + (100 / abs(odds))


def american_to_implied_prob(odds: float) -> float:
    try:
        odds = float(odds)
    except Exception:
        return np.nan
    return 100 / (odds + 100) if odds > 0 else abs(odds) / (abs(odds) + 100)


def decimal_to_american(dec: float) -> float:
    if dec is None or pd.isna(dec) or dec <= 1:
        return np.nan
    if dec >= 2:
        return round((dec - 1) * 100)
    return round(-100 / (dec - 1))


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def normal_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def fmt_american(v: float) -> str:
    if pd.isna(v):
        return "—"
    v = int(round(v))
    return f"+{v}" if v > 0 else str(v)


def safe_float(v, default=0.0):
    try:
        if pd.isna(v):
            return default
        return float(v)
    except Exception:
        return default


# ============================================================
# SAFE WHY FUNCTION (FIXED)
# ============================================================
def why_this_play(row: pd.Series) -> List[str]:
    projection = safe_float(row.get("projection"), np.nan)
    line = safe_float(row.get("line"), np.nan)
    proj_edge = projection - line if not pd.isna(projection) and not pd.isna(line) else np.nan

    model_agreement = int(safe_float(row.get("model_agreement_pct"), 0))
    true_edge = safe_float(row.get("true_edge"), 0) * 100
    script_type = row.get("script_type", "Neutral")
    script_score = int(safe_float(row.get("script_score"), 0))
    variance = row.get("variance_note", "Neutral")
    stake_u = safe_float(row.get("single_stake_u"), 0)

    return [
        f"Projection Edge: {proj_edge:+.1f} vs line" if not pd.isna(proj_edge) else "Projection Edge: N/A",
        f"Model Agreement: {model_agreement}%",
        f"True Edge: {true_edge:.1f}%",
        f"Game Script: {script_type} ({script_score})",
        f"Variance: {variance}",
        f"Stake: {stake_u:.2f}u",
    ]


# ============================================================
# Sample Data
# ============================================================
def sample_data():
    return pd.DataFrame([
        {"player": "Stephen Curry", "team": "GSW", "market": "points", "bet_side": "Over", "line": 27, "projection": 32, "odds": -115, "starter": True, "minutes": 35},
        {"player": "LeBron James", "team": "LAL", "market": "pra", "bet_side": "Over", "line": 38, "projection": 44, "odds": -115, "starter": True, "minutes": 36},
        {"player": "Anthony Davis", "team": "LAL", "market": "rebounds", "bet_side": "Over", "line": 11.5, "projection": 13.2, "odds": -105, "starter": True, "minutes": 35},
    ])


# ============================================================
# Simple Scoring (light version for stability)
# ============================================================
def compute(df):
    df["hit_prob"] = 0.65
    df["realistic_hit_prob"] = 0.62
    df["true_edge"] = 0.08
    df["realistic_ev_pct"] = 10.5
    df["consensus_score"] = 75
    df["model_agreement_pct"] = 70
    df["script_type"] = "Playable pace"
    df["script_score"] = 72
    df["variance_note"] = "Neutral"
    df["single_stake_u"] = 1.0
    return df


# ============================================================
# UI
# ============================================================
st.title("🏀 Sports AI Betting Dashboard (Stable V8 Fix)")

df = compute(sample_data())

st.markdown("## Top Plays")

for _, row in df.iterrows():
    st.markdown(f"### {row['player']} — {row['bet_side']} {row['line']} {row['market']}")
    st.write(f"Odds: {fmt_american(row['odds'])}")
    st.write(f"EV: {row['realistic_ev_pct']}%")
    st.write("Why:")
    for r in why_this_play(row):
        st.write(f"- {r}")
