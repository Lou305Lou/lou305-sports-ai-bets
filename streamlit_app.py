import math
from typing import Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st


# ============================================================
# Sports AI Betting Dashboard — Clean Rebuild
# Version: Full App with NBA Player Props V2 + Scoring Fix
# ============================================================

st.set_page_config(page_title="Sports AI Betting Dashboard", layout="wide")


# -----------------------------
# Helpers
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


def normal_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def prob_over_normal(mean_proj: float, line: float, std_dev: float) -> float:
    if std_dev <= 0:
        return 0.5
    z = (mean_proj - line) / std_dev
    return normal_cdf(z)


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def safe_float(x, default=np.nan):
    try:
        if pd.isna(x):
            return default
        return float(x)
    except Exception:
        return default


def safe_bool(x) -> bool:
    if isinstance(x, bool):
        return x
    if pd.isna(x):
        return False
    s = str(x).strip().lower()
    return s in {"1", "true", "yes", "y", "starter", "starting"}


def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    aliases = {
        "player_name": "player",
        "name": "player",
        "sportsbook": "book",
        "sports_book": "book",
        "team_name": "team",
        "opp": "opponent",
        "market_type": "market",
        "bet_type": "bet_side",
        "selection": "bet_side",
        "odds_american": "odds",
        "american_odds": "odds",
        "proj": "projection",
        "projected": "projection",
        "prop_line": "line",
        "is_starter": "starter",
        "starts": "starter",
        "game": "matchup",
    }

    for old, new in aliases.items():
        if old in df.columns and new not in df.columns:
            df[new] = df[old]

    defaults = {
        "player": "",
        "team": "",
        "opponent": "",
        "matchup": "",
        "market": "",
        "bet_side": "",
        "line": np.nan,
        "projection": np.nan,
        "odds": np.nan,
        "book": "",
        "starter": False,
        "minutes": np.nan,
        "std_dev": np.nan,
        "game_total": np.nan,
        "spread": np.nan,
        "game_time": "",
    }

    for col, val in defaults.items():
        if col not in df.columns:
            df[col] = val

    for c in ["player", "team", "opponent", "matchup", "market", "bet_side", "book", "game_time"]:
        df[c] = df[c].fillna("").astype(str).str.strip()

    for c in ["line", "projection", "odds", "minutes", "std_dev", "game_total", "spread"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df["starter"] = df["starter"].apply(safe_bool)

    if (df["matchup"] == "").any():
        auto_matchup = df["team"].fillna("") + np.where(df["opponent"].fillna("") != "", " vs " + df["opponent"].fillna(""), "")
        df.loc[df["matchup"] == "", "matchup"] = auto_matchup[df["matchup"] == ""]

    return df


def infer_market_std(row: pd.Series) -> float:
    market = str(row.get("market", "")).lower()
    supplied = safe_float(row.get("std_dev"), np.nan)
    if not np.isnan(supplied) and supplied > 0:
        return supplied

    defaults = {
        "points": 8.0,
        "rebounds": 3.6,
        "assists": 3.2,
        "pra": 8.5,
        "threes": 2.0,
        "3pm": 2.0,
        "blocks": 1.2,
        "steals": 1.3,
        "pts+reb+ast": 8.5,
    }
    for key, val in defaults.items():
        if key in market:
            return val
    return 7.0


def infer_bet_side(row: pd.Series) -> str:
    side = str(row.get("bet_side", "")).strip().title()
    if side in {"Over", "Under"}:
        return side

    projection = safe_float(row.get("projection"), np.nan)
    line = safe_float(row.get("line"), np.nan)
    if np.isnan(projection) or np.isnan(line):
        return "Over"
    return "Over" if projection >= line else "Under"


def calculate_hit_probability(row: pd.Series) -> float:
    projection = safe_float(row.get("projection"), np.nan)
    line = safe_float(row.get("line"), np.nan)
    if np.isnan(projection) or np.isnan(line):
        return np.nan

    std_dev = infer_market_std(row)
    side = infer_bet_side(row)

    p_over = prob_over_normal(projection, line, std_dev)
    if side == "Under":
        return clamp01(1 - p_over)
    return clamp01(p_over)


def bounded_component(x: pd.Series, low: float, high: float, max_points: float) -> pd.Series:
    clipped = x.clip(lower=low, upper=high)
    return ((clipped - low) / (high - low) * max_points).clip(lower=0, upper=max_points)


def grade_from_score(score: float) -> str:
    if score >= 85:
        return "🟢 A"
    if score >= 77:
        return "🟢 B"
    if score >= 69:
        return "🟡 C"
    if score >= 60:
        return "🟠 D"
    return "🔴 F"


def tier_from_score(score: float) -> str:
    if score >= 85:
        return "🟢 Tier 1"
    if score >= 75:
        return "🟡 Tier 2"
    if score >= 65:
        return "⚪ Tier 3"
    return "⚫ Pass"


def unit_size_from_score(score: float) -> float:
    if score >= 87:
        return 1.00
    if score >= 80:
        return 0.75
    if score >= 72:
        return 0.50
    if score >= 65:
        return 0.25
    return 0.00


def variance_label(std_dev: float, market: str) -> str:
    market = str(market).lower()
    if std_dev >= 8:
        return "High-upside profile"
    if "three" in market or "3pm" in market:
        return "High variance"
    if std_dev <= 2.5:
        return "Lower variance"
    return "Neutral variance"


def matchup_label(row: pd.Series) -> str:
    total = safe_float(row.get("game_total"), np.nan)
    spread = abs(safe_float(row.get("spread"), np.nan))
    minutes = safe_float(row.get("minutes"), np.nan)

    if not np.isnan(total) and total >= 235 and (np.isnan(spread) or spread <= 8):
        return "Strong matchup"
    if not np.isnan(minutes) and minutes >= 34:
        return "Stable role"
    if not np.isnan(spread) and spread >= 12:
        return "Blowout risk"
    return "Neutral matchup"


def portfolio_flag(score: float, ev_edge: float, hit_pct: float) -> str:
    if score >= 72 and ev_edge >= 3 and hit_pct >= 56:
        return "Selected"
    return "Pass"


def compute_edges(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    out["bet_side"] = out.apply(infer_bet_side, axis=1)
    out["std_dev_used"] = out.apply(infer_market_std, axis=1)
    out["hit_prob"] = out.apply(calculate_hit_probability, axis=1)
    out["hit_pct"] = (out["hit_prob"] * 100).round(1)

    out["implied_prob"] = out["odds"].apply(american_to_implied_prob)
    out["projection_edge"] = (out["projection"] - out["line"]).round(2)
    under_mask = out["bet_side"].eq("Under")
    out.loc[under_mask, "projection_edge"] = (out.loc[under_mask, "line"] - out.loc[under_mask, "projection"]).round(2)

    dec = out["odds"].apply(american_to_decimal)
    out["ev"] = (out["hit_prob"] * (dec - 1)) - (1 - out["hit_prob"])
    out["ev_edge_pct"] = (out["ev"] * 100).round(2)

    # -----------------------------
    # SCORING FIX
    # -----------------------------
    # Designed to create actual separation instead of everything scoring 99.9.
    hit_component = bounded_component(out["hit_pct"], 52, 70, 28)
    ev_component = bounded_component(out["ev_edge_pct"], 0, 20, 22)
    edge_component = bounded_component(out["projection_edge"], 0.5, 5.0, 18)

    starter_bonus = np.where(out["starter"], 4.0, 0.0)
    minutes_bonus = bounded_component(out["minutes"].fillna(0), 28, 36, 8)
    matchup_bonus = np.where(out["game_total"].fillna(0) >= 235, 3.0, np.where(out["game_total"].fillna(0) >= 228, 1.5, 0.0))
    price_bonus = np.where((out["odds"] >= -135) & (out["odds"] <= 125), 2.0, 0.0)

    blowout_penalty = np.where(abs(out["spread"].fillna(0)) >= 12, 5.0, np.where(abs(out["spread"].fillna(0)) >= 9, 2.5, 0.0))
    nonstarter_penalty = np.where(~out["starter"], 8.0, 0.0)
    low_minutes_penalty = np.where(out["minutes"].fillna(0) < 28, 6.0, 0.0)

    out["score"] = (
        28
        + hit_component
        + ev_component
        + edge_component
        + starter_bonus
        + minutes_bonus
        + matchup_bonus
        + price_bonus
        - blowout_penalty
        - nonstarter_penalty
        - low_minutes_penalty
    ).clip(lower=0, upper=99.9).round(1)

    out["grade"] = out["score"].apply(grade_from_score)
    out["tier"] = out["score"].apply(tier_from_score)
    out["model_size_u"] = out["score"].apply(unit_size_from_score)
    out["portfolio_size_u"] = np.where(
        out["score"] >= 85, out["model_size_u"] + 0.10,
        np.where(out["score"] >= 75, out["model_size_u"] + 0.05, out["model_size_u"])
    ).round(2)
    out["matchup_note"] = out.apply(matchup_label, axis=1)
    out["variance_note"] = out.apply(lambda r: variance_label(r["std_dev_used"], r["market"]), axis=1)
    out["portfolio_status"] = out.apply(lambda r: portfolio_flag(r["score"], r["ev_edge_pct"], r["hit_pct"]), axis=1)

    return out


def find_arbitrage_and_middles(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    work = df.copy()
    work["key"] = (
        work["matchup"].astype(str) + " | " +
        work["player"].astype(str) + " | " +
        work["market"].astype(str)
    )

    arb_rows = []
    mid_rows = []

    arb_group = work.groupby(["key", "line"], dropna=False)
    for (key, line), g in arb_group:
        overs = g[g["bet_side"].str.lower() == "over"]
        unders = g[g["bet_side"].str.lower() == "under"]

        for _, o in overs.iterrows():
            for _, u in unders.iterrows():
                total_implied = american_to_implied_prob(o["odds"]) + american_to_implied_prob(u["odds"])
                if total_implied < 1:
                    arb_rows.append({
                        "matchup": o["matchup"],
                        "player": o["player"],
                        "market": o["market"],
                        "line": line,
                        "over_book": o["book"],
                        "over_odds": o["odds"],
                        "under_book": u["book"],
                        "under_odds": u["odds"],
                        "combined_implied_pct": round(total_implied * 100, 2),
                        "arb_margin_pct": round((1 - total_implied) * 100, 2),
                    })

    mid_group = work.groupby(["key"], dropna=False)
    for key, g in mid_group:
        overs = g[g["bet_side"].str.lower() == "over"].copy()
        unders = g[g["bet_side"].str.lower() == "under"].copy()
        if overs.empty or unders.empty:
            continue

        for _, o in overs.iterrows():
            for _, u in unders.iterrows():
                if pd.notna(o["line"]) and pd.notna(u["line"]) and o["line"] < u["line"]:
                    gap = u["line"] - o["line"]
                    if gap >= 1:
                        mid_rows.append({
                            "matchup": o["matchup"],
                            "player": o["player"],
                            "market": o["market"],
                            "over_line": o["line"],
                            "over_book": o["book"],
                            "over_odds": o["odds"],
                            "under_line": u["line"],
                            "under_book": u["book"],
                            "under_odds": u["odds"],
                            "middle_window": f"{o['line']} to {u['line']}",
                            "gap": round(gap, 2),
                        })

    arb_df = pd.DataFrame(arb_rows).drop_duplicates()
    mid_df = pd.DataFrame(mid_rows).drop_duplicates()
    return arb_df, mid_df


def format_best_bet_cards(df: pd.DataFrame, top_n: int = 10):
    if df.empty:
        st.info("No bets match the current filters.")
        return

    top = df.sort_values(["score", "ev_edge_pct", "hit_pct"], ascending=False).head(top_n).reset_index(drop=True)

    for idx, row in top.iterrows():
        st.markdown(
            f"""
**#{idx + 1} {row['player']} — {row['bet_side']} {row['line']} {row['market'].title()}**  
{row['matchup']} • FULL_GAME • {row['book'] if row['book'] else 'Book N/A'}  
Projection: {row['projection']:.2f} | Edge: {row['projection_edge']:.2f} | Odds: {int(row['odds']) if pd.notna(row['odds']) else 'N/A'} | Hit %: {row['hit_pct']:.1f}% | EV Edge: {row['ev_edge_pct']:.2f}% | Score: {row['score']:.1f} ({row['grade']})  
Tier: {row['tier']} | Model Size: {row['model_size_u']:.2f}u | Portfolio Size: {row['portfolio_size_u']:.2f}u  
Matchup: {row['matchup_note']} | Variance: {row['variance_note']} | Portfolio: {row['portfolio_status']}
---
"""
        )


def sample_data() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "player": "Stephen Curry", "team": "GSW", "opponent": "LAL", "matchup": "Warriors vs Lakers",
            "market": "points", "bet_side": "Over", "line": 27.0, "projection": 32.2, "odds": -115,
            "book": "DraftKings", "starter": True, "minutes": 35, "std_dev": 8.0, "game_total": 238.5, "spread": -2.5,
        },
        {
            "player": "LeBron James", "team": "LAL", "opponent": "GSW", "matchup": "Lakers vs Warriors",
            "market": "pra", "bet_side": "Over", "line": 38.0, "projection": 43.8, "odds": -115,
            "book": "DraftKings", "starter": True, "minutes": 36, "std_dev": 8.8, "game_total": 238.5, "spread": 2.5,
        },
        {
            "player": "Anthony Davis", "team": "LAL", "opponent": "GSW", "matchup": "Lakers vs Warriors",
            "market": "rebounds", "bet_side": "Over", "line": 11.5, "projection": 13.1, "odds": -105,
            "book": "FanDuel", "starter": True, "minutes": 35, "std_dev": 3.5, "game_total": 238.5, "spread": 2.5,
        },
        {
            "player": "Austin Reaves", "team": "LAL", "opponent": "GSW", "matchup": "Lakers vs Warriors",
            "market": "assists", "bet_side": "Under", "line": 6.5, "projection": 5.2, "odds": -102,
            "book": "BetMGM", "starter": True, "minutes": 34, "std_dev": 2.8, "game_total": 238.5, "spread": 2.5,
        },
        {
            "player": "Jordan Poole", "team": "WAS", "opponent": "BKN", "matchup": "Wizards vs Nets",
            "market": "points", "bet_side": "Over", "line": 21.5, "projection": 24.4, "odds": +102,
            "book": "Caesars", "starter": True, "minutes": 33, "std_dev": 7.8, "game_total": 229.0, "spread": 5.0,
        },
        {
            "player": "Bench Example", "team": "MIA", "opponent": "BOS", "matchup": "Heat vs Celtics",
            "market": "points", "bet_side": "Over", "line": 10.5, "projection": 13.2, "odds": -110,
            "book": "DraftKings", "starter": False, "minutes": 24, "std_dev": 5.5, "game_total": 220.5, "spread": 9.5,
        },
    ])


@st.cache_data(show_spinner=False)
def load_csv(file) -> pd.DataFrame:
    return pd.read_csv(file)


st.title("🏀 Sports AI Betting Dashboard")
st.caption("Scoring fix applied: sharper separation between elite, strong, playable, and pass-level bets.")

with st.sidebar:
    st.header("Data")
    uploaded = st.file_uploader("Upload your bets CSV", type=["csv"])
    use_sample = st.toggle("Use sample data", value=uploaded is None)

    st.markdown("### Expected CSV columns")
    st.code(
        "player, team, opponent, matchup, market, bet_side, line, projection, odds, book, starter, minutes, std_dev, game_total, spread",
        language="text"
    )

if uploaded is not None:
    try:
        raw_df = load_csv(uploaded)
        source_label = f"Uploaded file: {uploaded.name}"
    except Exception as e:
        st.error(f"Could not read file: {e}")
        st.stop()
elif use_sample:
    raw_df = sample_data()
    source_label = "Built-in sample data"
else:
    st.warning("Upload a CSV or turn on sample data.")
    st.stop()

df = ensure_columns(raw_df)
model_df = compute_edges(df)

st.success(f"Loaded source: {source_label}")

c1, c2, c3, c4 = st.columns(4)
with c1:
    books = sorted([b for b in model_df["book"].dropna().unique().tolist() if b != ""])
    selected_books = st.multiselect("Sportsbooks", books, default=books)
with c2:
    markets = sorted([m for m in model_df["market"].dropna().unique().tolist() if m != ""])
    selected_markets = st.multiselect("Markets", markets, default=markets)
with c3:
    only_starters_global = st.toggle("Starters only (global)", value=False)
with c4:
    min_score = st.slider("Minimum score", 0, 95, 60)

filtered = model_df.copy()
if selected_books:
    filtered = filtered[filtered["book"].isin(selected_books)]
if selected_markets:
    filtered = filtered[filtered["market"].isin(selected_markets)]
if only_starters_global:
    filtered = filtered[filtered["starter"] == True]
filtered = filtered[filtered["score"] >= min_score].copy()

m1, m2, m3, m4 = st.columns(4)
m1.metric("Bets Loaded", f"{len(model_df)}")
m2.metric("Filtered Bets", f"{len(filtered)}")
m3.metric("Avg Hit %", f"{filtered['hit_pct'].mean():.1f}%" if not filtered.empty else "N/A")
m4.metric("Avg EV Edge", f"{filtered['ev_edge_pct'].mean():.2f}%" if not filtered.empty else "N/A")

tabs = st.tabs(["🔥 Best Bets", "🧠 NBA Player Props V2", "⚡ Arbitrage & Middles", "📦 Portfolio", "🗂️ Raw Data"])

with tabs[0]:
    st.subheader("Top Best Bets")
    left, right = st.columns([1, 2])

    with left:
        top_n = st.slider("Show top N bets", 5, 25, 10)
        min_hit = st.slider("Minimum hit %", 50, 80, 56)
        min_ev = st.slider("Minimum EV edge %", -10, 30, 3)
        display_df = filtered[
            (filtered["hit_pct"] >= min_hit) &
            (filtered["ev_edge_pct"] >= min_ev)
        ].copy()

    with right:
        if not display_df.empty:
            ranked = display_df.sort_values(["score", "ev_edge_pct", "hit_pct"], ascending=False)
            st.dataframe(
                ranked[[
                    "player", "matchup", "market", "bet_side", "line", "projection", "projection_edge",
                    "odds", "hit_pct", "ev_edge_pct", "score", "grade", "tier",
                    "model_size_u", "portfolio_size_u", "book", "starter"
                ]],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No bets meet the Best Bets filters.")

    st.markdown("### Card View")
    format_best_bet_cards(display_df, top_n=top_n)

with tabs[1]:
    st.subheader("NBA Player Props V2 — Starters Only")

    prop_df = filtered.copy()

    l1, l2, l3, l4 = st.columns(4)
    with l1:
        starters_only = st.toggle("Only starters", value=True)
    with l2:
        odds_min, odds_max = st.slider("Odds range", -300, 200, (-300, 200))
    with l3:
        prop_markets = st.multiselect(
            "Prop markets",
            options=sorted(prop_df["market"].dropna().astype(str).unique().tolist()),
            default=[m for m in sorted(prop_df["market"].dropna().astype(str).unique().tolist()) if m.lower() in {"points", "pra", "rebounds", "assists"}] or sorted(prop_df["market"].dropna().astype(str).unique().tolist())
        )
    with l4:
        min_minutes = st.slider("Minimum minutes", 0, 40, 28)

    if starters_only:
        prop_df = prop_df[prop_df["starter"] == True]
    prop_df = prop_df[
        (prop_df["odds"] >= odds_min) &
        (prop_df["odds"] <= odds_max) &
        (prop_df["minutes"].fillna(0) >= min_minutes)
    ]
    if prop_markets:
        prop_df = prop_df[prop_df["market"].isin(prop_markets)]

    prop_df = prop_df.sort_values(["score", "ev_edge_pct", "hit_pct"], ascending=False).copy()

    st.markdown("### Top Prop Targets")
    st.dataframe(
        prop_df[[
            "player", "team", "matchup", "market", "bet_side", "line", "projection",
            "projection_edge", "odds", "hit_pct", "ev_edge_pct", "score", "grade",
            "tier", "minutes", "book", "matchup_note", "variance_note", "portfolio_status"
        ]],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### Featured Props")
    format_best_bet_cards(prop_df, top_n=8)

with tabs[2]:
    st.subheader("Arbitrage & Middles Scanner")
    arb_df, mid_df = find_arbitrage_and_middles(model_df)

    a1, a2 = st.columns(2)
    with a1:
        st.markdown("### Arbitrage Opportunities")
        if arb_df.empty:
            st.info("No arbitrage opportunity detected.")
        else:
            st.dataframe(arb_df.sort_values("arb_margin_pct", ascending=False), use_container_width=True, hide_index=True)

    with a2:
        st.markdown("### Middle Opportunities")
        if mid_df.empty:
            st.info("No middle found.")
        else:
            st.dataframe(mid_df.sort_values("gap", ascending=False), use_container_width=True, hide_index=True)

with tabs[3]:
    st.subheader("Portfolio Engine Snapshot")

    port = filtered.copy()
    port = port[
        (port["portfolio_status"] == "Selected") &
        (port["score"] >= 72) &
        (port["ev_edge_pct"] >= 3)
    ].sort_values(["score", "ev_edge_pct"], ascending=False)

    bankroll = st.number_input("Bankroll ($)", min_value=50, max_value=100000, value=1000, step=50)
    unit_pct = st.slider("1 unit as % of bankroll", 0.25, 5.0, 1.0, 0.25)

    dollar_per_unit = bankroll * (unit_pct / 100.0)
    port["stake_$"] = (port["portfolio_size_u"] * dollar_per_unit).round(2)

    k1, k2, k3 = st.columns(3)
    k1.metric("Selected Bets", f"{len(port)}")
    k2.metric("Total Units", f"{port['portfolio_size_u'].sum():.2f}u" if not port.empty else "0.00u")
    k3.metric("Total Stake", f"${port['stake_$'].sum():,.2f}" if not port.empty else "$0.00")

    st.dataframe(
        port[[
            "player", "matchup", "market", "bet_side", "line", "odds", "hit_pct",
            "ev_edge_pct", "score", "tier", "model_size_u", "portfolio_size_u", "stake_$", "book"
        ]],
        use_container_width=True,
        hide_index=True,
    )

with tabs[4]:
    st.subheader("Model Data")
    st.dataframe(model_df, use_container_width=True, hide_index=True)

    csv = model_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download scored bets CSV",
        data=csv,
        file_name="scored_bets.csv",
        mime="text/csv",
    )

st.markdown("---")
st.caption("Scoring V2 is live. Elite scores should now be rare instead of every bet showing as 99.9.")
