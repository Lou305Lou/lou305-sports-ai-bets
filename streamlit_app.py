import math
import itertools
from typing import List, Dict

import numpy as np
import pandas as pd
import streamlit as st


st.set_page_config(page_title="Sports AI Betting Dashboard", layout="wide")


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


def safe_float(x, default=np.nan):
    try:
        if pd.isna(x):
            return default
        return float(x)
    except Exception:
        return default


def normal_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


# ============================================================
# Data prep
# ============================================================
def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    aliases = {
        "player_name": "player", "name": "player",
        "sportsbook": "book", "sports_book": "book",
        "team_name": "team", "opp": "opponent",
        "market_type": "market", "bet_type": "bet_side",
        "selection": "bet_side", "odds_american": "odds",
        "american_odds": "odds", "proj": "projection",
        "projected": "projection", "prop_line": "line",
        "is_starter": "starter", "starts": "starter", "game": "matchup",
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
        auto_matchup = df["team"].fillna("") + np.where(
            df["opponent"].fillna("") != "", " vs " + df["opponent"].fillna(""), ""
        )
        df.loc[df["matchup"] == "", "matchup"] = auto_matchup[df["matchup"] == ""]

    return df


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
    p, l = row.get("projection"), row.get("line")
    if pd.isna(p) or pd.isna(l):
        return "Over"
    return "Over" if p >= l else "Under"


def calculate_hit_probability(row: pd.Series) -> float:
    p, l = row.get("projection"), row.get("line")
    if pd.isna(p) or pd.isna(l):
        return np.nan
    std = infer_market_std(row)
    z = (p - l) / std if std > 0 else 0
    p_over = normal_cdf(z)
    return clamp01(1 - p_over if infer_bet_side(row) == "Under" else p_over)


def compute_scores(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["bet_side"] = out.apply(infer_bet_side, axis=1)
    out["hit_prob"] = out.apply(calculate_hit_probability, axis=1)
    out["hit_pct"] = (out["hit_prob"] * 100).round(1)

    dec = out["odds"].apply(american_to_decimal)
    out["ev"] = (out["hit_prob"] * (dec - 1)) - (1 - out["hit_prob"])
    out["ev_pct"] = (out["ev"] * 100).round(2)

    # lightweight consensus proxy
    out["consensus_score"] = (
        out["hit_pct"] * 0.55
        + out["ev_pct"].clip(lower=-10, upper=20) * 1.1
        + np.where(out["starter"], 4, -6)
        + np.where(out["minutes"].fillna(0) >= 33, 4, 0)
    ).clip(0, 100).round(1)

    out["model_agreement_pct"] = np.select(
        [out["consensus_score"] >= 74, out["consensus_score"] >= 66, out["consensus_score"] >= 60],
        [80, 60, 40],
        default=20
    )

    def action(row):
        if row["consensus_score"] >= 76 and row["model_agreement_pct"] >= 60:
            return "Bet"
        if row["consensus_score"] >= 60:
            return "Lean"
        return "Pass"

    out["consensus_action"] = out.apply(action, axis=1)
    return out


# ============================================================
# Pool + correlation
# ============================================================
def approved_pool(df: pd.DataFrame) -> pd.DataFrame:
    primary = df[
        (df["consensus_action"] == "Bet") |
        ((df["consensus_action"] == "Lean") & (df["model_agreement_pct"] >= 60))
    ].copy()

    if len(primary) < 2:
        fallback = df[
            (df["consensus_action"].isin(["Bet", "Lean"])) &
            (df["consensus_score"] >= 60)
        ].copy()
        fallback["fallback_flag"] = True
        return fallback

    primary["fallback_flag"] = False
    return primary


def same_game(a: pd.Series, b: pd.Series) -> bool:
    return str(a.get("matchup", "")) == str(b.get("matchup", ""))


def same_team(a: pd.Series, b: pd.Series) -> bool:
    return str(a.get("team", "")) == str(b.get("team", ""))


def pair_corr_penalty(a: pd.Series, b: pd.Series) -> float:
    pen = 0.0
    if same_game(a, b):
        pen += 0.12
        if same_team(a, b):
            pen += 0.08
    return pen


def combo_corr_penalty(rows: List[pd.Series]) -> float:
    total = 0.0
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            total += pair_corr_penalty(rows[i], rows[j])
    return total


# ============================================================
# Parlay optimizer
# ============================================================
def build_parlay_metrics(rows: List[pd.Series]) -> Dict:
    decs = [american_to_decimal(r["odds"]) for r in rows]
    probs = [r["hit_prob"] for r in rows]

    if any(pd.isna(x) for x in decs) or any(pd.isna(x) for x in probs):
        return {}

    combined_dec = float(np.prod(decs))
    combined_amer = decimal_to_american(combined_dec)

    p_ind = float(np.prod(probs))
    corr_pen = combo_corr_penalty(rows)
    p_adj = clamp01(p_ind * (1 - corr_pen))
    ev = p_adj * (combined_dec - 1) - (1 - p_adj)

    return {
        "legs": rows,
        "combined_decimal": combined_dec,
        "combined_american": combined_amer,
        "hit_prob": p_adj,
        "hit_pct": p_adj * 100,
        "ev": ev,
        "ev_pct": ev * 100,
        "corr_pen": corr_pen,
    }


def tag_parlay_type(metrics: Dict) -> str:
    hp = metrics["hit_pct"]
    ev = metrics["ev_pct"]
    odds = metrics["combined_american"]

    if hp >= 22 and ev >= 6:
        return "Safe"
    if hp >= 12 and ev >= 10:
        return "Balanced"
    if odds >= 400 or ev >= 18:
        return "Aggressive"
    return "Balanced"


def suggested_stake(parlay_type: str) -> float:
    if parlay_type == "Safe":
        return 0.35
    if parlay_type == "Balanced":
        return 0.25
    return 0.10


def generate_parlays(df: pd.DataFrame, k: int = 2, max_results: int = 20) -> List[Dict]:
    rows = [r[1] for r in df.iterrows()]
    results = []
    for combo in itertools.combinations(rows, k):
        metrics = build_parlay_metrics(list(combo))
        if not metrics:
            continue
        metrics["parlay_type"] = tag_parlay_type(metrics)
        metrics["stake_u"] = suggested_stake(metrics["parlay_type"])
        results.append(metrics)

    results = sorted(results, key=lambda x: (x["ev_pct"], x["hit_pct"]), reverse=True)
    return results[:max_results]


def select_best_by_type(parlays: List[Dict]) -> Dict[str, Dict]:
    buckets = {"Safe": None, "Balanced": None, "Aggressive": None}
    for t in buckets:
        subset = [p for p in parlays if p["parlay_type"] == t]
        if subset:
            # Safe prioritize hit, Balanced EV+hit, Aggressive EV+odds
            if t == "Safe":
                subset = sorted(subset, key=lambda x: (x["hit_pct"], x["ev_pct"]), reverse=True)
            elif t == "Balanced":
                subset = sorted(subset, key=lambda x: (x["ev_pct"] + x["hit_pct"] * 0.2), reverse=True)
            else:
                subset = sorted(subset, key=lambda x: (x["ev_pct"], x["combined_american"]), reverse=True)
            buckets[t] = subset[0]
    return buckets


# ============================================================
# UI helpers
# ============================================================
def metric_cards(items: List[tuple]):
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items):
        with col:
            st.markdown(
                f"""
                <div style="
                    border:1px solid rgba(128,128,128,0.25);
                    border-radius:14px;
                    padding:12px;
                    background:rgba(250,250,250,0.75);
                    min-height:80px;">
                    <div style="font-size:12px;opacity:0.72;">{label}</div>
                    <div style="font-size:24px;font-weight:700;">{value}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_parlay_card(p: Dict, title: str):
    if not p:
        return
    color = {"Safe": "#16a34a", "Balanced": "#eab308", "Aggressive": "#dc2626"}[p["parlay_type"]]
    st.markdown(
        f"""
        <div style="
            border:2px solid {color};
            border-radius:16px;
            padding:14px;
            margin-bottom:14px;
            background:rgba(250,250,250,0.78);">
            <div style="font-size:24px;font-weight:800;margin-bottom:8px;">{title}</div>
            <div style="margin-bottom:8px;">
                <span style="display:inline-block;padding:4px 10px;border-radius:999px;background:{color};color:white;font-weight:700;margin-right:8px;">{p["parlay_type"]}</span>
                <span style="display:inline-block;padding:4px 10px;border-radius:999px;border:1px solid rgba(128,128,128,0.25);font-weight:700;margin-right:8px;">{int(p["combined_american"]) if not pd.isna(p["combined_american"]) else "—"}</span>
                <span style="display:inline-block;padding:4px 10px;border-radius:999px;border:1px solid rgba(128,128,128,0.25);font-weight:700;">{p["stake_u"]:.2f}u</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    metric_cards([
        ("Hit %", f"{p['hit_pct']:.1f}%"),
        ("EV %", f"{p['ev_pct']:.1f}%"),
        ("Corr Penalty", f"{p['corr_pen']:.2f}"),
        ("Stake", f"{p['stake_u']:.2f}u"),
    ])
    st.write("**Legs**")
    for leg in p["legs"]:
        st.write(f"- {leg['player']} — {leg['bet_side']} {leg['line']} {leg['market']} ({int(leg['odds']) if not pd.isna(leg['odds']) else 'N/A'})")
    st.markdown("---")


# ============================================================
# Sample data
# ============================================================
def sample_data() -> pd.DataFrame:
    return pd.DataFrame([
        {"player": "Stephen Curry", "team": "GSW", "opponent": "LAL", "matchup": "Warriors vs Lakers", "market": "points", "bet_side": "Over", "line": 27.0, "projection": 32.2, "odds": -115, "book": "DraftKings", "starter": True, "minutes": 35},
        {"player": "LeBron James", "team": "LAL", "opponent": "GSW", "matchup": "Lakers vs Warriors", "market": "pra", "bet_side": "Over", "line": 38.0, "projection": 43.8, "odds": -115, "book": "DraftKings", "starter": True, "minutes": 36},
        {"player": "Anthony Davis", "team": "LAL", "opponent": "GSW", "matchup": "Lakers vs Warriors", "market": "rebounds", "bet_side": "Over", "line": 11.5, "projection": 13.1, "odds": -105, "book": "FanDuel", "starter": True, "minutes": 35},
        {"player": "Austin Reaves", "team": "LAL", "opponent": "GSW", "matchup": "Lakers vs Warriors", "market": "assists", "bet_side": "Under", "line": 6.5, "projection": 5.2, "odds": -102, "book": "BetMGM", "starter": True, "minutes": 34},
        {"player": "Jordan Poole", "team": "WAS", "opponent": "BKN", "matchup": "Wizards vs Nets", "market": "points", "bet_side": "Over", "line": 21.5, "projection": 24.4, "odds": 102, "book": "Caesars", "starter": True, "minutes": 33},
        {"player": "Bench Example", "team": "MIA", "opponent": "BOS", "matchup": "Heat vs Celtics", "market": "points", "bet_side": "Over", "line": 10.5, "projection": 13.2, "odds": -110, "book": "DraftKings", "starter": False, "minutes": 24},
    ])


@st.cache_data(show_spinner=False)
def load_csv(file) -> pd.DataFrame:
    return pd.read_csv(file)


# ============================================================
# App
# ============================================================
st.title("🏀 Sports AI Betting Dashboard")
st.caption("V7.3: Smart Parlay Types — Safe, Balanced, and Aggressive.")

with st.sidebar:
    uploaded = st.file_uploader("Upload CSV", type=["csv"])
    use_sample = st.toggle("Use sample data", value=uploaded is None)
    parlay_size = st.selectbox("Parlay size", [2, 3, 4], index=0)
    max_results = st.slider("Max parlay combos", 5, 40, 20)

if uploaded:
    df = ensure_columns(load_csv(uploaded))
else:
    df = ensure_columns(sample_data())

df = compute_scores(df)
pool = approved_pool(df)

st.markdown("## Approved Pool")
if pool.empty:
    st.warning("No plays qualify for the approved pool.")
    st.stop()

if "fallback_flag" in pool.columns and pool["fallback_flag"].any():
    st.warning("⚠️ No elite plays found — using fallback pool (lower confidence).")

st.dataframe(
    pool[["player", "matchup", "market", "bet_side", "line", "odds", "consensus_score", "model_agreement_pct", "consensus_action"]],
    use_container_width=True,
    hide_index=True,
)

if len(pool) < 2:
    st.warning("Not enough approved plays to build parlays.")
    st.stop()

parlays = generate_parlays(pool, k=parlay_size, max_results=max_results)
best = select_best_by_type(parlays)

st.markdown("---")
st.markdown("## 🧠 Smart Parlay Types")

available = sum(1 for v in best.values() if v is not None)
metric_cards([
    ("Approved Plays", f"{len(pool)}"),
    ("Parlay Size", f"{parlay_size}-leg"),
    ("Parlay Types Found", f"{available}"),
])

if not any(best.values()):
    st.info("No valid parlays found.")
else:
    if best["Safe"] is not None:
        render_parlay_card(best["Safe"], "🟢 Safe Parlay")
    if best["Balanced"] is not None:
        render_parlay_card(best["Balanced"], "🟡 Balanced Parlay")
    if best["Aggressive"] is not None:
        render_parlay_card(best["Aggressive"], "🔴 Aggressive Parlay")

st.markdown("## All Ranked Parlays")
if parlays:
    rows = []
    for i, p in enumerate(parlays, 1):
        rows.append({
            "rank": i,
            "type": p["parlay_type"],
            "combined_odds": int(p["combined_american"]) if not pd.isna(p["combined_american"]) else np.nan,
            "hit_pct": round(p["hit_pct"], 1),
            "ev_pct": round(p["ev_pct"], 1),
            "corr_penalty": round(p["corr_pen"], 2),
            "stake_u": round(p["stake_u"], 2),
            "legs": " | ".join([f"{x['player']} {x['bet_side']} {x['line']}" for x in p["legs"]]),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
else:
    st.info("No parlays available.")

st.markdown("---")
st.caption("Next upgrade: bankroll optimizer + same-game parlay mode.")
