import math
import itertools
from typing import List, Tuple

import numpy as np
import pandas as pd
import streamlit as st


# ============================================================
# Sports AI Betting Dashboard — V7.2
# Multi-AI + Parlay Optimizer Engine
# ============================================================

st.set_page_config(page_title="Sports AI Betting Dashboard", layout="wide")


# -----------------------------
# Helpers (odds / probs)
# -----------------------------
def american_to_decimal(odds: float) -> float:
    try:
        odds = float(odds)
    except Exception:
        return np.nan
    if odds > 0:
        return 1 + (odds / 100)
    return 1 + (100 / abs(odds))


def american_to_implied_prob(odds: float) -> float:
    try:
        odds = float(odds)
    except Exception:
        return np.nan
    if odds > 0:
        return 100 / (odds + 100)
    return abs(odds) / (abs(odds) + 100)


def decimal_to_american(dec: float) -> float:
    if dec is None or np.isnan(dec) or dec <= 1:
        return np.nan
    if dec >= 2:
        return round((dec - 1) * 100)
    return round(-100 / (dec - 1))


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


# -----------------------------
# Data prep (same core as V7.1, minimal)
# -----------------------------
def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    aliases = {
        "player_name": "player", "name": "player",
        "sportsbook": "book", "sports_book": "book",
        "team_name": "team", "opp": "opponent",
        "market_type": "market", "bet_type": "bet_side",
        "selection": "bet_side",
        "odds_american": "odds", "american_odds": "odds",
        "proj": "projection", "projected": "projection",
        "prop_line": "line", "is_starter": "starter",
        "starts": "starter", "game": "matchup",
    }
    for old, new in aliases.items():
        if old in df.columns and new not in df.columns:
            df[new] = df[old]

    defaults = {
        "player": "", "team": "", "opponent": "", "matchup": "",
        "market": "", "bet_side": "", "line": np.nan, "projection": np.nan,
        "odds": np.nan, "book": "", "starter": False, "minutes": np.nan,
        "std_dev": np.nan, "game_total": np.nan, "spread": np.nan,
    }
    for col, val in defaults.items():
        if col not in df.columns:
            df[col] = val

    for c in ["player", "team", "opponent", "matchup", "market", "bet_side", "book"]:
        df[c] = df[c].fillna("").astype(str).str.strip()

    for c in ["line", "projection", "odds", "minutes", "std_dev", "game_total", "spread"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df["starter"] = df["starter"].fillna(False).astype(bool)

    if (df["matchup"] == "").any():
        auto_matchup = df["team"].fillna("") + np.where(df["opponent"].fillna("") != "", " vs " + df["opponent"].fillna(""), "")
        df.loc[df["matchup"] == "", "matchup"] = auto_matchup[df["matchup"] == ""]

    return df


def normal_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def infer_market_std(row: pd.Series) -> float:
    supplied = row.get("std_dev")
    if pd.notna(supplied) and supplied > 0:
        return float(supplied)
    market = str(row.get("market", "")).lower()
    defaults = {"points": 8.5, "rebounds": 4.0, "assists": 3.6, "pra": 9.0}
    for k, v in defaults.items():
        if k in market:
            return v
    return 7.5


def infer_bet_side(row: pd.Series) -> str:
    side = str(row.get("bet_side", "")).title()
    if side in {"Over", "Under"}:
        return side
    p = row.get("projection")
    l = row.get("line")
    if pd.isna(p) or pd.isna(l):
        return "Over"
    return "Over" if p >= l else "Under"


def calculate_hit_probability(row: pd.Series) -> float:
    p = row.get("projection")
    l = row.get("line")
    if pd.isna(p) or pd.isna(l):
        return np.nan
    std = infer_market_std(row)
    side = infer_bet_side(row)
    z = (p - l) / std if std > 0 else 0
    p_over = normal_cdf(z)
    return clamp01(1 - p_over if side == "Under" else p_over)


def compute_basic_scores(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["bet_side"] = out.apply(infer_bet_side, axis=1)
    out["hit_prob"] = out.apply(calculate_hit_probability, axis=1)
    out["hit_pct"] = (out["hit_prob"] * 100).round(1)

    out["implied_prob"] = out["odds"].apply(american_to_implied_prob)
    dec = out["odds"].apply(american_to_decimal)
    out["ev"] = (out["hit_prob"] * (dec - 1)) - (1 - out["hit_prob"])
    out["ev_edge_pct"] = (out["ev"] * 100).round(2)

    # Simple consensus (already built in prior step, here approximated for demo)
    out["consensus_score"] = (out["hit_pct"] * 0.5 + out["ev_edge_pct"] * 0.5).clip(0, 100).round(1)
    out["model_agreement_pct"] = np.where(out["consensus_score"] >= 70, 80, np.where(out["consensus_score"] >= 60, 60, 40))

    def action(r):
        if r["consensus_score"] >= 75 and r["model_agreement_pct"] >= 60:
            return "Bet"
        if r["consensus_score"] >= 60:
            return "Lean"
        return "Pass"

    out["consensus_action"] = out.apply(action, axis=1)
    return out


# -----------------------------
# Parlay Optimizer
# -----------------------------
def same_game(a: pd.Series, b: pd.Series) -> bool:
    return str(a.get("matchup")) == str(b.get("matchup"))


def same_team(a: pd.Series, b: pd.Series) -> bool:
    return str(a.get("team")) == str(b.get("team"))


def side_conflict(a: pd.Series, b: pd.Series) -> bool:
    # simplistic: opposing sides on same market/player (not present here) or team-based conflict
    return False


def pair_correlation_penalty(a: pd.Series, b: pd.Series) -> float:
    pen = 0.0
    if same_game(a, b):
        pen += 0.12  # 12% penalty for same game
        if same_team(a, b):
            pen += 0.08  # extra if same team
    return pen


def combo_correlation_penalty(rows: List[pd.Series]) -> float:
    pen = 0.0
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            pen += pair_correlation_penalty(rows[i], rows[j])
    return pen


def build_parlay_metrics(rows: List[pd.Series]) -> dict:
    decs = [american_to_decimal(r["odds"]) for r in rows]
    probs = [r["hit_prob"] for r in rows]

    if any(pd.isna(d) for d in decs) or any(pd.isna(p) for p in probs):
        return {}

    # combined
    combined_dec = float(np.prod(decs))
    combined_amer = decimal_to_american(combined_dec)

    # naive independent prob
    p_ind = float(np.prod(probs))

    # apply correlation penalty
    corr_pen = combo_correlation_penalty(rows)
    p_adj = clamp01(p_ind * (1 - corr_pen))

    # EV
    ev = p_adj * (combined_dec - 1) - (1 - p_adj)
    ev_pct = ev * 100

    # simple stake suggestion
    stake_u = 0.25 if len(rows) == 2 else (0.20 if len(rows) == 3 else 0.10)

    return {
        "legs": rows,
        "combined_decimal": combined_dec,
        "combined_american": combined_amer,
        "hit_prob": p_adj,
        "hit_pct": p_adj * 100,
        "ev": ev,
        "ev_pct": ev_pct,
        "corr_pen": corr_pen,
        "stake_u": stake_u,
    }


def generate_parlays(df: pd.DataFrame, k: int, max_out: int = 5) -> List[dict]:
    rows = [r[1] for r in df.iterrows()]
    combos = list(itertools.combinations(rows, k))

    results = []
    for combo in combos:
        m = build_parlay_metrics(list(combo))
        if not m:
            continue
        # basic filters
        if m["hit_prob"] <= 0:
            continue
        results.append(m)

    # rank by EV then hit prob
    results = sorted(results, key=lambda x: (x["ev"], x["hit_prob"]), reverse=True)
    return results[:max_out]


def approved_pool(df: pd.DataFrame) -> pd.DataFrame:
    return df[
        (df["consensus_action"] == "Bet") |
        ((df["consensus_action"] == "Lean") & (df["model_agreement_pct"] >= 60))
    ].copy()


# -----------------------------
# UI
# -----------------------------
def render_parlay_card(p: dict, title: str):
    st.markdown(f"### {title}")
    cols = st.columns(4)
    cols[0].metric("Combined Odds", f"{int(p['combined_american']) if not np.isnan(p['combined_american']) else '—'}")
    cols[1].metric("Hit %", f"{p['hit_pct']:.1f}%")
    cols[2].metric("EV %", f"{p['ev_pct']:.1f}%")
    cols[3].metric("Stake", f"{p['stake_u']:.2f}u")

    st.write("**Legs**")
    for r in p["legs"]:
        st.write(f"- {r['player']} — {r['bet_side']} {r['line']} {r['market']} ({r['odds']})")


def sample_data() -> pd.DataFrame:
    return pd.DataFrame([
        {"player": "Stephen Curry", "team": "GSW", "opponent": "LAL", "matchup": "Warriors vs Lakers",
         "market": "points", "bet_side": "Over", "line": 27.0, "projection": 32.2, "odds": -115, "book": "DraftKings"},
        {"player": "LeBron James", "team": "LAL", "opponent": "GSW", "matchup": "Lakers vs Warriors",
         "market": "pra", "bet_side": "Over", "line": 38.0, "projection": 43.8, "odds": -115, "book": "DraftKings"},
        {"player": "Anthony Davis", "team": "LAL", "opponent": "GSW", "matchup": "Lakers vs Warriors",
         "market": "rebounds", "bet_side": "Over", "line": 11.5, "projection": 13.1, "odds": -105, "book": "FanDuel"},
        {"player": "Austin Reaves", "team": "LAL", "opponent": "GSW", "matchup": "Lakers vs Warriors",
         "market": "assists", "bet_side": "Under", "line": 6.5, "projection": 5.2, "odds": -102, "book": "BetMGM"},
        {"player": "Jordan Poole", "team": "WAS", "opponent": "BKN", "matchup": "Wizards vs Nets",
         "market": "points", "bet_side": "Over", "line": 21.5, "projection": 24.4, "odds": +102, "book": "Caesars"},
    ])


@st.cache_data(show_spinner=False)
def load_csv(file) -> pd.DataFrame:
    return pd.read_csv(file)


st.title("🏀 Sports AI Betting Dashboard")
st.caption("V7.2: Parlay Optimizer built from Multi-AI consensus-approved pool.")

with st.sidebar:
    uploaded = st.file_uploader("Upload CSV", type=["csv"])
    use_sample = st.toggle("Use sample data", value=uploaded is None)

if uploaded:
    df = ensure_columns(load_csv(uploaded))
else:
    df = ensure_columns(sample_data())

df = compute_basic_scores(df)

pool = approved_pool(df)

st.markdown("## Approved Pool")
st.dataframe(pool[["player", "matchup", "market", "bet_side", "line", "odds", "consensus_score", "model_agreement_pct", "consensus_action"]], use_container_width=True)

if len(pool) < 2:
    st.warning("Not enough approved plays to build parlays.")
    st.stop()

st.markdown("---")
st.markdown("## 🔗 Parlay Optimizer")

col1, col2 = st.columns(2)
with col1:
    max_legs = st.selectbox("Parlay size", [2, 3, 4], index=0)
with col2:
    max_results = st.slider("Max results", 1, 10, 5)

parlays = generate_parlays(pool, k=max_legs, max_out=max_results)

if not parlays:
    st.info("No valid parlays found with current pool.")
else:
    for i, p in enumerate(parlays, start=1):
        render_parlay_card(p, f"Parlay #{i}")

st.markdown("---")
st.caption("Tip: diversify games to reduce correlation and improve true hit probability.")
