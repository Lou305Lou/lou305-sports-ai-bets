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
    defaults = {
        "points": 8.5,
        "rebounds": 4.0,
        "assists": 3.6,
        "pra": 9.0,
        "threes": 2.4,
        "3pm": 2.4,
    }
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

    out["implied_prob"] = out["odds"].apply(american_to_implied_prob)
    out["true_edge"] = (out["hit_prob"] - out["implied_prob"]).round(4)

    dec = out["odds"].apply(american_to_decimal)
    out["raw_ev"] = (out["hit_prob"] * (dec - 1)) - (1 - out["hit_prob"])
    out["raw_ev_pct"] = (out["raw_ev"] * 100).round(2)

    # Conservative realism haircut
    out["realistic_hit_prob"] = (
        out["hit_prob"]
        - np.where(out["true_edge"] > 0.08, 0.03, 0.0)
        - np.where(out["true_edge"] > 0.12, 0.03, 0.0)
        - np.where(out["starter"], 0.0, 0.02)
    ).clip(lower=0.01, upper=0.95)

    out["realistic_ev"] = (out["realistic_hit_prob"] * (dec - 1)) - (1 - out["realistic_hit_prob"])
    out["realistic_ev_pct"] = (out["realistic_ev"] * 100).round(2)

    out["consensus_score"] = (
        out["hit_pct"] * 0.35
        + out["true_edge"].clip(lower=-0.05, upper=0.15) * 180
        + out["realistic_ev_pct"].clip(lower=-10, upper=20) * 0.8
        + np.where(out["starter"], 4, -8)
        + np.where(out["minutes"].fillna(0) >= 33, 4, np.where(out["minutes"].fillna(0) >= 28, 1, -4))
        - np.where(abs(out["spread"].fillna(0)) >= 10, 4, 0)
    ).clip(0, 100).round(1)

    out["model_agreement_pct"] = np.select(
        [out["consensus_score"] >= 78, out["consensus_score"] >= 70, out["consensus_score"] >= 63],
        [80, 60, 40],
        default=20
    )

    def action(row):
        if row["true_edge"] <= 0:
            return "Pass"
        if row["consensus_score"] >= 78 and row["model_agreement_pct"] >= 60:
            return "Bet"
        if row["consensus_score"] >= 66 and row["true_edge"] >= 0.025:
            return "Lean"
        return "Pass"

    out["consensus_action"] = out.apply(action, axis=1)

    def variance_note(row):
        std = infer_market_std(row)
        market = str(row.get("market", "")).lower()
        if "three" in market or "3pm" in market:
            return "High variance"
        if std >= 8.5:
            return "High-upside profile"
        if std <= 2.8:
            return "Lower variance"
        return "Neutral variance"

    out["variance_note"] = out.apply(variance_note, axis=1)
    return out


# ============================================================
# Pool + singles
# ============================================================
def approved_pool(df: pd.DataFrame) -> pd.DataFrame:
    primary = df[
        (
            (df["consensus_action"] == "Bet") |
            ((df["consensus_action"] == "Lean") & (df["model_agreement_pct"] >= 60))
        ) &
        (df["true_edge"] >= 0.02) &
        (df["realistic_ev_pct"] >= 2.0)
    ].copy()

    if len(primary) < 2:
        fallback = df[
            (df["consensus_action"].isin(["Bet", "Lean"])) &
            (df["true_edge"] >= 0.015) &
            (df["consensus_score"] >= 62)
        ].copy()
        fallback["fallback_flag"] = True
        return fallback

    primary["fallback_flag"] = False
    return primary


def best_single(df: pd.DataFrame, mode: str) -> pd.Series:
    if df.empty:
        return pd.Series(dtype=object)
    if mode == "ev":
        return df.sort_values(["realistic_ev_pct", "true_edge", "consensus_score"], ascending=False).iloc[0]
    if mode == "safe":
        return df.sort_values(["realistic_hit_prob", "consensus_score", "true_edge"], ascending=False).iloc[0]
    return df.sort_values(["true_edge", "realistic_ev_pct", "consensus_score"], ascending=False).iloc[0]


# ============================================================
# Correlation + parlays
# ============================================================
def same_game(a: pd.Series, b: pd.Series) -> bool:
    a_match = str(a.get("matchup", ""))
    b_match = str(b.get("matchup", ""))
    if a_match == b_match:
        return True
    a_team, a_opp = str(a.get("team", "")), str(a.get("opponent", ""))
    b_team, b_opp = str(b.get("team", "")), str(b.get("opponent", ""))
    return (a_team == b_opp and a_opp == b_team and a_team != "" and a_opp != "")


def same_team(a: pd.Series, b: pd.Series) -> bool:
    return str(a.get("team", "")) == str(b.get("team", ""))


def pair_corr_penalty(a: pd.Series, b: pd.Series) -> float:
    pen = 0.0
    same_g = same_game(a, b)
    same_t = same_team(a, b)

    if not same_g:
        return 0.0

    market_a = str(a.get("market", "")).lower()
    market_b = str(b.get("market", "")).lower()
    side_a = str(a.get("bet_side", "")).lower()
    side_b = str(b.get("bet_side", "")).lower()

    pen += 0.12

    if same_t:
        pen += 0.08

    if side_a == "over" and side_b == "over":
        if any(k in market_a for k in ["points", "pra", "assists"]) and any(k in market_b for k in ["points", "pra", "assists"]):
            pen += 0.08
        elif ("points" in market_a and "rebounds" in market_b) or ("rebounds" in market_a and "points" in market_b):
            pen += 0.04

    if side_a != side_b and same_t:
        pen -= 0.03

    return max(0.0, pen)


def combo_corr_penalty(rows: List[pd.Series]) -> float:
    total = 0.0
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            total += pair_corr_penalty(rows[i], rows[j])
    return total


# ============================================================
# Bankroll optimizer
# ============================================================
def kelly_fraction(prob: float, decimal_odds: float) -> float:
    if decimal_odds <= 1 or prob <= 0 or prob >= 1:
        return 0.0
    b = decimal_odds - 1
    q = 1 - prob
    frac = (b * prob - q) / b
    return max(0.0, frac)


def stake_from_kelly(prob: float, decimal_odds: float, parlay_type: str, bankroll: float, max_fraction: float) -> Dict:
    raw = kelly_fraction(prob, decimal_odds)
    type_mult = {"Safe": 0.35, "Balanced": 0.22, "Aggressive": 0.10}.get(parlay_type, 0.15)
    frac = min(raw * type_mult, max_fraction)
    dollars = bankroll * frac
    units = dollars / (bankroll * 0.01) if bankroll > 0 else 0
    return {
        "kelly_raw_pct": raw * 100,
        "kelly_bet_pct": frac * 100,
        "stake_$": dollars,
        "stake_u": units,
    }


# ============================================================
# Parlay engine
# ============================================================
def tag_parlay_type(metrics: Dict) -> str:
    hp = metrics["hit_pct"]
    ev = metrics["ev_pct"]
    odds = metrics["combined_american"]

    if hp >= 42 and odds <= 300:
        return "Safe"
    if hp >= 28 and ev >= 6:
        return "Balanced"
    return "Aggressive"


def build_parlay_metrics(rows: List[pd.Series], bankroll: float, max_fraction: float) -> Dict:
    decs = [american_to_decimal(r["odds"]) for r in rows]
    probs = [r["realistic_hit_prob"] for r in rows]

    if any(pd.isna(x) for x in decs) or any(pd.isna(x) for x in probs):
        return {}

    combined_dec = float(np.prod(decs))
    combined_amer = decimal_to_american(combined_dec)

    p_ind = float(np.prod(probs))
    corr_pen = combo_corr_penalty(rows)
    p_adj = clamp01(p_ind * (1 - corr_pen))

    ev = p_adj * (combined_dec - 1) - (1 - p_adj)
    ev_pct = ev * 100

    # Conservative quality filters
    if p_adj < 0.12:
        return {}
    if ev_pct < 2.0:
        return {}

    base = {
        "legs": rows,
        "combined_decimal": combined_dec,
        "combined_american": combined_amer,
        "hit_prob": p_adj,
        "hit_pct": p_adj * 100,
        "ev": ev,
        "ev_pct": ev_pct,
        "corr_pen": corr_pen,
    }
    base["parlay_type"] = tag_parlay_type(base)
    base.update(stake_from_kelly(base["hit_prob"], base["combined_decimal"], base["parlay_type"], bankroll, max_fraction))
    return base


def generate_parlays(df: pd.DataFrame, k: int, bankroll: float, max_fraction: float, max_results: int = 30) -> List[Dict]:
    rows = [r[1] for r in df.iterrows()]
    results = []
    for combo in itertools.combinations(rows, k):
        metrics = build_parlay_metrics(list(combo), bankroll, max_fraction)
        if not metrics:
            continue
        results.append(metrics)

    results = sorted(results, key=lambda x: (x["ev_pct"], x["hit_pct"]), reverse=True)
    return results[:max_results]


def select_best_by_type(parlays: List[Dict]) -> Dict[str, Dict]:
    buckets = {"Safe": None, "Balanced": None, "Aggressive": None}
    for t in buckets:
        subset = [p for p in parlays if p["parlay_type"] == t]
        if subset:
            if t == "Safe":
                subset = sorted(subset, key=lambda x: (x["hit_pct"], x["ev_pct"]), reverse=True)
            elif t == "Balanced":
                subset = sorted(subset, key=lambda x: (x["ev_pct"] + x["hit_pct"] * 0.25), reverse=True)
            else:
                subset = sorted(subset, key=lambda x: (x["combined_american"], x["ev_pct"]), reverse=True)
            buckets[t] = subset[0]
    return buckets


def apply_total_exposure_cap(parlays: List[Dict], bankroll: float, exposure_cap_pct: float) -> List[Dict]:
    remaining = bankroll * exposure_cap_pct
    approved = []
    for p in parlays:
        if p["stake_$"] <= remaining + 1e-9:
            approved.append(p)
            remaining -= p["stake_$"]
    return approved


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


def render_single_card(row: pd.Series, title: str):
    if row.empty:
        return
    st.markdown(f"### {title}")
    metric_cards([
        ("Player", row["player"]),
        ("Action", row["consensus_action"]),
        ("Score", f"{row['consensus_score']:.1f}"),
        ("Agreement", f"{int(row['model_agreement_pct'])}%"),
    ])
    metric_cards([
        ("Hit %", f"{row['realistic_hit_prob']*100:.1f}%"),
        ("True Edge", f"{row['true_edge']*100:.1f}%"),
        ("Realistic EV", f"{row['realistic_ev_pct']:.1f}%"),
        ("Odds", f"{int(row['odds']) if not pd.isna(row['odds']) else '—'}"),
    ])
    st.write(f"**{row['player']} — {row['bet_side']} {row['line']} {row['market']}**")
    st.write(f"{row['matchup']} • {row['book']} • {row['variance_note']}")
    st.markdown("---")


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
        ("Kelly Raw", f"{p['kelly_raw_pct']:.1f}%"),
        ("Bet %", f"{p['kelly_bet_pct']:.2f}%"),
    ])
    metric_cards([
        ("Corr Penalty", f"{p['corr_pen']:.2f}"),
        ("Stake", f"{p['stake_u']:.2f}u"),
        ("Stake $", f"${p['stake_$']:.2f}"),
        ("Odds", f"{int(p['combined_american']) if not pd.isna(p['combined_american']) else '—'}"),
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
        {"player": "Stephen Curry", "team": "GSW", "opponent": "LAL", "matchup": "Warriors vs Lakers", "market": "points", "bet_side": "Over", "line": 27.0, "projection": 32.2, "odds": -115, "book": "DraftKings", "starter": True, "minutes": 35, "spread": -2.5},
        {"player": "LeBron James", "team": "LAL", "opponent": "GSW", "matchup": "Lakers vs Warriors", "market": "pra", "bet_side": "Over", "line": 38.0, "projection": 43.8, "odds": -115, "book": "DraftKings", "starter": True, "minutes": 36, "spread": 2.5},
        {"player": "Anthony Davis", "team": "LAL", "opponent": "GSW", "matchup": "Lakers vs Warriors", "market": "rebounds", "bet_side": "Over", "line": 11.5, "projection": 13.1, "odds": -105, "book": "FanDuel", "starter": True, "minutes": 35, "spread": 2.5},
        {"player": "Austin Reaves", "team": "LAL", "opponent": "GSW", "matchup": "Lakers vs Warriors", "market": "assists", "bet_side": "Under", "line": 6.5, "projection": 5.2, "odds": -102, "book": "BetMGM", "starter": True, "minutes": 34, "spread": 2.5},
        {"player": "Jordan Poole", "team": "WAS", "opponent": "BKN", "matchup": "Wizards vs Nets", "market": "points", "bet_side": "Over", "line": 21.5, "projection": 24.4, "odds": 102, "book": "Caesars", "starter": True, "minutes": 33, "spread": 5.0},
        {"player": "Bench Example", "team": "MIA", "opponent": "BOS", "matchup": "Heat vs Celtics", "market": "points", "bet_side": "Over", "line": 10.5, "projection": 13.2, "odds": -110, "book": "DraftKings", "starter": False, "minutes": 24, "spread": 9.5},
    ])


@st.cache_data(show_spinner=False)
def load_csv(file) -> pd.DataFrame:
    return pd.read_csv(file)


# ============================================================
# App
# ============================================================
st.title("🏀 Sports AI Betting Dashboard")
st.caption("V7.5 Conservative / Sharp Mode: true edge filters, realistic EV, stronger correlation penalties, and exposure controls.")

with st.sidebar:
    uploaded = st.file_uploader("Upload CSV", type=["csv"])
    use_sample = st.toggle("Use sample data", value=uploaded is None)
    parlay_size = st.selectbox("Parlay size", [2, 3], index=0)
    max_results = st.slider("Max parlay combos", 5, 40, 20)
    bankroll = st.number_input("Bankroll ($)", min_value=100, max_value=100000, value=1000, step=50)
    max_bet_pct = st.slider("Max bankroll % per parlay", 0.25, 3.0, 1.0, 0.25) / 100.0
    exposure_cap_pct = st.slider("Total parlay exposure cap %", 1.0, 10.0, 3.0, 0.5) / 100.0

if uploaded:
    df = ensure_columns(load_csv(uploaded))
else:
    df = ensure_columns(sample_data())

df = compute_scores(df)
pool = approved_pool(df)

st.markdown("## Approved Pool")
if pool.empty:
    st.warning("No plays qualify for Sharp Mode approved pool.")
    st.stop()

if "fallback_flag" in pool.columns and pool["fallback_flag"].any():
    st.warning("⚠️ Sharp Mode could not find enough elite plays, so it is using a fallback pool.")

st.dataframe(
    pool[[
        "player", "matchup", "market", "bet_side", "line", "odds",
        "true_edge", "realistic_ev_pct", "consensus_score", "model_agreement_pct", "consensus_action"
    ]],
    use_container_width=True,
    hide_index=True,
)

st.markdown("---")
st.markdown("## 🔍 Top Plays Panel")
render_single_card(best_single(pool, "ev"), "🔥 Best Single (EV)")
render_single_card(best_single(pool, "safe"), "🔒 Safest Play")
render_single_card(best_single(pool, "edge"), "⚡ Highest Edge Play")

if len(pool) < 2:
    st.warning("Not enough approved plays to build parlays.")
    st.stop()

all_parlays = generate_parlays(pool, k=parlay_size, bankroll=float(bankroll), max_fraction=float(max_bet_pct), max_results=max_results)
parlays = apply_total_exposure_cap(all_parlays, float(bankroll), float(exposure_cap_pct))
best = select_best_by_type(parlays)

st.markdown("## 🛡️ Best Conservative Parlay")
metric_cards([
    ("Approved Plays", f"{len(pool)}"),
    ("Parlay Size", f"{parlay_size}-leg"),
    ("Bankroll", f"${float(bankroll):,.0f}"),
    ("Exposure Cap", f"{exposure_cap_pct*100:.1f}%"),
])

if not parlays:
    st.info("Sharp Mode did not find any parlays that passed the quality and exposure rules.")
else:
    if best["Safe"] is not None:
        render_parlay_card(best["Safe"], "🟢 Safe Parlay")
    elif best["Balanced"] is not None:
        render_parlay_card(best["Balanced"], "🟡 Balanced Parlay")
    elif best["Aggressive"] is not None:
        render_parlay_card(best["Aggressive"], "🔴 Aggressive Parlay")

st.markdown("## All Approved Parlays")
if parlays:
    rows = []
    for i, p in enumerate(parlays, 1):
        rows.append({
            "rank": i,
            "type": p["parlay_type"],
            "combined_odds": int(p["combined_american"]) if not pd.isna(p["combined_american"]) else np.nan,
            "hit_pct": round(p["hit_pct"], 1),
            "ev_pct": round(p["ev_pct"], 1),
            "kelly_raw_pct": round(p["kelly_raw_pct"], 2),
            "bet_pct": round(p["kelly_bet_pct"], 2),
            "stake_u": round(p["stake_u"], 2),
            "stake_$": round(p["stake_$"], 2),
            "corr_penalty": round(p["corr_pen"], 2),
            "legs": " | ".join([f"{x['player']} {x['bet_side']} {x['line']}" for x in p["legs"]]),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
else:
    st.info("No parlays survived the conservative Sharp Mode rules.")

st.markdown("---")
st.caption("Next upgrade: same-game parlay mode, live odds, and slate-level exposure controls.")
