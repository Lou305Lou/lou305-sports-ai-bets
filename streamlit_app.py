import io
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Sports Betting AI Dashboard V31.2", layout="wide")

APP_TITLE = "🔥 Sports Betting AI Dashboard V31.2"
APP_SUBTITLE = "Dynamic Consensus + Best Price Optimizer"
BET_LOG_PATH = Path("bet_log.csv")
LEARNING_PROFILE_PATH = Path("learning_profile.csv")
SNAPSHOT_PATH = Path("snapshot.csv")

MIN_ACTIVE_EDGE = 1.75
MAX_BEST_BETS = 3
MAX_TIER_A = 3
MAX_ACTIVE_PLAYS = 3
MAX_TOTAL_UNITS = 3.5
SCORE_CAP = 100.0
ADAPTIVE_MIN_SAMPLE = 10
HOT_STREAK_BONUS = 0.20
COLD_STREAK_PENALTY = 0.20
DEFAULT_MAX_SINGLE_BET = 1.15
LOW_BOOK_THRESHOLD = 3
STRONG_BOOK_THRESHOLD = 4
PRICE_EDGE_STRONG_THRESHOLD = 1.25
DISPERSION_ALERT_THRESHOLD = 3.0
PROMOTION_MIN_BOOKS = 2
PROMOTION_MIN_PRICE_EDGE = 1.50
PROMOTION_MIN_EDGE = 1.50
PROMOTION_MIN_SCORE = 78.0



# -----------------------------
# Math helpers
# -----------------------------
def safe_float(x, default=0.0):
    try:
        if x is None or x == "":
            return default
        return float(x)
    except Exception:
        return default


def display_num(x, digits=2, suffix=""):
    try:
        val = float(x)
        if pd.isna(val):
            return "—"
        return f"{val:.{digits}f}{suffix}"
    except Exception:
        return "—"


def american_to_prob(odds):
    try:
        odds = float(odds)
        if odds < 0:
            return (-odds) / ((-odds) + 100)
        return 100 / (odds + 100)
    except Exception:
        return np.nan


def prob_to_american(prob):
    try:
        prob = float(prob)
        if prob <= 0 or prob >= 1:
            return np.nan
        if prob >= 0.5:
            return -round((prob / (1 - prob)) * 100)
        return round(((1 - prob) / prob) * 100)
    except Exception:
        return np.nan


def price_edge_from_market(current_odds, market_odds):
    """
    Positive means current price is better than the market consensus.
    """
    current_prob = american_to_prob(current_odds)
    market_prob = american_to_prob(market_odds)
    if pd.isna(current_prob) or pd.isna(market_prob):
        return np.nan
    return (market_prob - current_prob) * 100.0


def market_average_american(odds_series):
    probs = pd.to_numeric(pd.Series(odds_series), errors="coerce").dropna().apply(american_to_prob).dropna()
    if probs.empty:
        return np.nan
    return prob_to_american(probs.mean())


def best_odds_in_series(odds_series):
    s = pd.to_numeric(pd.Series(odds_series), errors="coerce").dropna()
    if s.empty:
        return np.nan
    probs = s.apply(american_to_prob)
    return float(s.loc[probs.idxmin()])


def implied_prob_dispersion(odds_series):
    probs = pd.to_numeric(pd.Series(odds_series), errors="coerce").dropna().apply(american_to_prob).dropna()
    if probs.empty:
        return np.nan
    return (probs.max() - probs.min()) * 100.0


def implied_edge(model_prob, odds):
    market_prob = american_to_prob(odds)
    if pd.isna(model_prob) or pd.isna(market_prob):
        return np.nan
    return (float(model_prob) - float(market_prob)) * 100.0


def clv_hit(bet_odds, closing_odds):
    try:
        bo = american_to_prob(bet_odds)
        co = american_to_prob(closing_odds)
        if pd.isna(bo) or pd.isna(co):
            return np.nan
        return 1 if co > bo else 0
    except Exception:
        return np.nan


def expected_value_proxy(row):
    edge = max(0.0, safe_float(row.get("edge_pct")))
    clv = max(0.0, safe_float(row.get("clv_projection")))
    confidence = str(row.get("confidence", ""))
    conf_boost = {"Elite": 4.0, "High": 2.0, "Medium": 0.5}.get(confidence, 0.0)
    adaptive = safe_float(row.get("adaptive_adj"), 0.0)
    price_edge = max(0.0, safe_float(row.get("price_edge_pct")))
    consensus = safe_float(row.get("consensus_strength"), 0.0) / 100.0
    return round(edge * 0.46 + price_edge * 0.28 + consensus * 8.0 * 0.14 + adaptive * 0.07 + clv * 0.05 + conf_boost, 3)


def odds_bucket(odds):
    try:
        o = float(odds)
    except Exception:
        return "unknown"
    if -115 <= o <= 105:
        return "coinflip"
    if o > 105:
        return "dog_live" if o <= 150 else "dog_long"
    return "fav_std" if o >= -175 else "fav_heavy"


def consensus_bucket(n):
    try:
        n = int(n)
    except Exception:
        return "lt3"
    if n >= 5:
        return "5of5"
    if n == 4:
        return "4of5"
    if n == 3:
        return "3of5"
    return "lt3"




def build_adaptive_context(log_df):
    context = {
        "market_map": {},
        "bucket_map": {},
        "clv_map": {},
        "streak": 0,
        "recent_win_rate": 0.0,
        "recent_clv_hit_rate": 0.0,
        "risk_label": "Neutral",
        "edge_multiplier": 1.0,
        "unit_multiplier": 1.0,
        "max_total_units": MAX_TOTAL_UNITS,
        "max_single_bet": DEFAULT_MAX_SINGLE_BET,
    }
    if log_df is None or log_df.empty:
        return context

    temp = log_df.copy()
    temp["result"] = temp["result"].astype(str).str.lower()
    temp["market"] = temp["market"].fillna("unknown").astype(str)
    temp["odds_bucket"] = temp["bet_odds"].apply(odds_bucket)
    temp["consensus_bucket"] = temp["consensus_count"].apply(consensus_bucket)
    temp["clv_hit"] = temp.apply(lambda r: clv_hit(r.get("bet_odds"), r.get("closing_odds")), axis=1)
    settled = temp[temp["result"].isin(["win", "loss", "push"])].copy()
    if settled.empty:
        return context

    settled["is_win"] = settled["result"].eq("win").astype(int)

    market_perf = (
        settled.groupby("market", dropna=False)
        .agg(
            bets=("result", "count"),
            win_rate=("is_win", "mean"),
            clv_hit_rate=("clv_hit", "mean"),
        )
        .reset_index()
    )
    for _, row in market_perf.iterrows():
        bets = safe_float(row["bets"])
        if bets < ADAPTIVE_MIN_SAMPLE:
            context["market_map"][str(row["market"])] = 0.0
            continue
        win_adj = (safe_float(row["win_rate"]) - 0.50) * 14.0
        clv_adj = (safe_float(row["clv_hit_rate"]) - 0.50) * 8.0
        context["market_map"][str(row["market"])] = round(win_adj + clv_adj, 3)

    bucket_perf = (
        settled.groupby(["market", "odds_bucket", "consensus_bucket"], dropna=False)
        .agg(
            bets=("result", "count"),
            win_rate=("is_win", "mean"),
            clv_hit_rate=("clv_hit", "mean"),
        )
        .reset_index()
    )
    for _, row in bucket_perf.iterrows():
        key = (str(row["market"]), str(row["odds_bucket"]), str(row["consensus_bucket"]))
        bets = safe_float(row["bets"])
        if bets < ADAPTIVE_MIN_SAMPLE:
            context["bucket_map"][key] = 0.0
            context["clv_map"][key] = 0.0
            continue
        win_adj = (safe_float(row["win_rate"]) - 0.50) * 18.0
        clv_adj = (safe_float(row["clv_hit_rate"]) - 0.50) * 10.0
        context["bucket_map"][key] = round(win_adj, 3)
        context["clv_map"][key] = round(clv_adj, 3)

    settled["timestamp_dt"] = pd.to_datetime(settled["timestamp"], errors="coerce")
    settled = settled.sort_values("timestamp_dt").copy()
    recent = settled.tail(12)
    context["recent_win_rate"] = round(float(recent["is_win"].mean()), 3) if not recent.empty else 0.0
    context["recent_clv_hit_rate"] = round(float(recent["clv_hit"].dropna().mean()), 3) if recent["clv_hit"].notna().any() else 0.0

    streak = 0
    for result in reversed(settled["result"].tolist()):
        if result == "push":
            continue
        if streak == 0:
            streak = 1 if result == "win" else -1
            continue
        if (streak > 0 and result == "win") or (streak < 0 and result == "loss"):
            streak = streak + 1 if streak > 0 else streak - 1
        else:
            break
    context["streak"] = streak

    if streak >= 3:
        context["risk_label"] = "Hot"
        context["edge_multiplier"] = 0.97
        context["unit_multiplier"] = 1.04
        context["max_total_units"] = round(MAX_TOTAL_UNITS * (1 + HOT_STREAK_BONUS), 2)
    elif streak <= -3:
        context["risk_label"] = "Cold"
        context["edge_multiplier"] = 1.10
        context["unit_multiplier"] = 0.80
        context["max_total_units"] = round(MAX_TOTAL_UNITS * (1 - COLD_STREAK_PENALTY), 2)
        context["max_single_bet"] = 0.85

    if context["recent_win_rate"] >= 0.60 and recent.shape[0] >= ADAPTIVE_MIN_SAMPLE:
        context["unit_multiplier"] *= 1.03
    elif context["recent_win_rate"] <= 0.42 and recent.shape[0] >= ADAPTIVE_MIN_SAMPLE:
        context["unit_multiplier"] *= 0.92

    if context["recent_clv_hit_rate"] >= 0.58 and recent["clv_hit"].notna().sum() >= ADAPTIVE_MIN_SAMPLE:
        context["edge_multiplier"] *= 0.98
    elif context["recent_clv_hit_rate"] <= 0.45 and recent["clv_hit"].notna().sum() >= ADAPTIVE_MIN_SAMPLE:
        context["edge_multiplier"] *= 1.04

    context["max_single_bet"] = round(min(DEFAULT_MAX_SINGLE_BET, context["max_single_bet"]), 2)
    context["unit_multiplier"] = round(context["unit_multiplier"], 3)
    context["edge_multiplier"] = round(context["edge_multiplier"], 3)
    return context


    temp = log_df.copy()
    temp["result"] = temp["result"].astype(str).str.lower()
    settled = temp[temp["result"].isin(["win", "loss", "push"])].copy()
    if settled.empty:
        return context

    # Market and bucket performance maps
    settled["odds_bucket"] = settled["bet_odds"].apply(odds_bucket)
    settled["consensus_bucket"] = settled["consensus_count"].apply(consensus_bucket)
    settled["is_win"] = settled["result"].eq("win").astype(int)

    market_perf = (
        settled.groupby("market", dropna=False)
        .agg(bets=("result", "count"), win_rate=("is_win", "mean"))
        .reset_index()
    )
    for _, row in market_perf.iterrows():
        adj = 0.0
        if safe_float(row["bets"]) >= ADAPTIVE_MIN_SAMPLE:
            adj = (safe_float(row["win_rate"]) - 0.50) * 12.0
        context["market_map"][str(row["market"])] = round(adj, 3)

    bucket_perf = (
        settled.groupby(["market", "odds_bucket", "consensus_bucket"], dropna=False)
        .agg(bets=("result", "count"), win_rate=("is_win", "mean"))
        .reset_index()
    )
    for _, row in bucket_perf.iterrows():
        key = (str(row["market"]), str(row["odds_bucket"]), str(row["consensus_bucket"]))
        adj = 0.0
        if safe_float(row["bets"]) >= ADAPTIVE_MIN_SAMPLE:
            adj = (safe_float(row["win_rate"]) - 0.50) * 16.0
        context["bucket_map"][key] = round(adj, 3)

    # Streak detection from latest graded bets
    settled["timestamp_dt"] = pd.to_datetime(settled["timestamp"], errors="coerce")
    settled = settled.sort_values("timestamp_dt").copy()
    recent = settled.tail(8)
    context["recent_win_rate"] = round(float(recent["is_win"].mean()), 3) if not recent.empty else 0.0

    streak = 0
    for result in reversed(settled["result"].tolist()):
        if result == "push":
            continue
        if streak == 0:
            streak = 1 if result == "win" else -1
            continue
        if (streak > 0 and result == "win") or (streak < 0 and result == "loss"):
            streak = streak + 1 if streak > 0 else streak - 1
        else:
            break
    context["streak"] = streak

    if streak >= 3:
        context["risk_label"] = "Hot"
        context["edge_multiplier"] = 0.96
        context["unit_multiplier"] = 1.06
        context["max_total_units"] = round(MAX_TOTAL_UNITS * (1 + HOT_STREAK_BONUS), 2)
    elif streak <= -3:
        context["risk_label"] = "Cold"
        context["edge_multiplier"] = 1.08
        context["unit_multiplier"] = 0.82
        context["max_total_units"] = round(MAX_TOTAL_UNITS * (1 - COLD_STREAK_PENALTY), 2)
        context["max_single_bet"] = 0.90
    else:
        context["risk_label"] = "Neutral"

    return context


# -----------------------------
# Data loading
# -----------------------------
def load_csv(file, fallback_df):
    try:
        if file is None:
            return fallback_df.copy()
        return pd.read_csv(file)
    except Exception:
        return fallback_df.copy()


def default_live_rows():
    return pd.DataFrame(
        [
            {
                "game": "Warriors vs Lakers",
                "market": "moneyline",
                "selection": "Warriors",
                "line": np.nan,
                "book": "FanDuel",
                "odds": -110,
                "consensus_price": -118,
                "consensus_count": 3,
                "sharp_score": 39.5,
                "model_prob": 0.542,
                "book_disagreement": 1,
                "clv_projection": 8.0,
                "prev_odds": -115,
                "closing_odds": -110,
            },
            {
                "game": "Warriors vs Lakers",
                "market": "moneyline",
                "selection": "Lakers",
                "line": np.nan,
                "book": "Caesars",
                "odds": 110,
                "consensus_price": 102,
                "consensus_count": 3,
                "sharp_score": 40.3,
                "model_prob": 0.492,
                "book_disagreement": 1,
                "clv_projection": 6.0,
                "prev_odds": 105,
                "closing_odds": 110,
            },
            {
                "game": "Warriors vs Lakers",
                "market": "total",
                "selection": "Over",
                "line": 229.5,
                "book": "DraftKings",
                "odds": -102,
                "consensus_price": -109,
                "consensus_count": 3,
                "sharp_score": 39.9,
                "model_prob": 0.521,
                "book_disagreement": 0,
                "clv_projection": 5.0,
                "prev_odds": -106,
                "closing_odds": -102,
            },
            {
                "game": "Warriors vs Lakers",
                "market": "spread",
                "selection": "Warriors",
                "line": -3.5,
                "book": "FanDuel",
                "odds": -105,
                "consensus_price": -110,
                "consensus_count": 3,
                "sharp_score": 40.2,
                "model_prob": 0.517,
                "book_disagreement": 0,
                "clv_projection": 3.0,
                "prev_odds": -108,
                "closing_odds": -105,
            },
            {
                "game": "Warriors vs Lakers",
                "market": "total",
                "selection": "Under",
                "line": 229.5,
                "book": "FanDuel",
                "odds": -110,
                "consensus_price": -108,
                "consensus_count": 3,
                "sharp_score": 41.9,
                "model_prob": 0.497,
                "book_disagreement": 0,
                "clv_projection": -1.0,
                "prev_odds": -110,
                "closing_odds": -110,
            },
            {
                "game": "Warriors vs Lakers",
                "market": "spread",
                "selection": "Lakers",
                "line": 3.5,
                "book": "DraftKings",
                "odds": -108,
                "consensus_price": -106,
                "consensus_count": 3,
                "sharp_score": 41.7,
                "model_prob": 0.496,
                "book_disagreement": 0,
                "clv_projection": 0.0,
                "prev_odds": -108,
                "closing_odds": -108,
            },
            {
                "game": "Celtics vs Heat",
                "market": "spread",
                "selection": "Celtics",
                "line": -5.5,
                "book": "FanDuel",
                "odds": -110,
                "consensus_price": -122,
                "consensus_count": 4,
                "sharp_score": 59.2,
                "model_prob": 0.585,
                "book_disagreement": 1,
                "clv_projection": 16.0,
                "prev_odds": -118,
                "closing_odds": -110,
            },
            {
                "game": "Celtics vs Heat",
                "market": "total",
                "selection": "Under",
                "line": 221.5,
                "book": "Caesars",
                "odds": -105,
                "consensus_price": -111,
                "consensus_count": 4,
                "sharp_score": 54.8,
                "model_prob": 0.551,
                "book_disagreement": 0,
                "clv_projection": 10.0,
                "prev_odds": -109,
                "closing_odds": -105,
            },
            {
                "game": "Nuggets vs Suns",
                "market": "moneyline",
                "selection": "Nuggets",
                "line": np.nan,
                "book": "DraftKings",
                "odds": -132,
                "consensus_price": -145,
                "consensus_count": 5,
                "sharp_score": 62.4,
                "model_prob": 0.615,
                "book_disagreement": 1,
                "clv_projection": 20.0,
                "prev_odds": -138,
                "closing_odds": -132,
            },
            {
                "game": "Nuggets vs Suns",
                "market": "spread",
                "selection": "Suns",
                "line": 4.5,
                "book": "FanDuel",
                "odds": -102,
                "consensus_price": -108,
                "consensus_count": 4,
                "sharp_score": 48.2,
                "model_prob": 0.515,
                "book_disagreement": 0,
                "clv_projection": 2.0,
                "prev_odds": -104,
                "closing_odds": -102,
            },
            {
                "game": "Rangers vs Bruins",
                "market": "moneyline",
                "selection": "Bruins",
                "line": np.nan,
                "book": "FanDuel",
                "odds": 118,
                "consensus_price": 105,
                "consensus_count": 4,
                "sharp_score": 57.5,
                "model_prob": 0.492,
                "book_disagreement": 1,
                "clv_projection": 12.0,
                "prev_odds": 112,
                "closing_odds": 118,
            },
        ]
    )


# -----------------------------
# Board building
# -----------------------------
def selection_market_key(row):
    line = row.get("line")
    if pd.isna(line):
        line = "ML"
    return f"{row.get('game')}|{row.get('market')}|{line}"



def enrich_market_context(df):
    df = df.copy()
    if df.empty:
        return df

    df["selection_market_key"] = df.apply(selection_market_key, axis=1)

    available_map = df.groupby("selection_market_key")["book"].nunique(dropna=True).to_dict()
    avg_odds_map = df.groupby("selection_market_key")["odds"].apply(market_average_american).to_dict()
    best_odds_map = df.groupby("selection_market_key")["odds"].apply(best_odds_in_series).to_dict()
    dispersion_map = df.groupby("selection_market_key")["odds"].apply(implied_prob_dispersion).to_dict()

    best_book_map = {}
    for key, grp in df.groupby("selection_market_key", dropna=False):
        grp = grp.copy()
        grp["price_edge_tmp"] = grp.apply(
            lambda r: price_edge_from_market(r.get("odds"), avg_odds_map.get(key, np.nan)),
            axis=1,
        )
        grp = grp.sort_values(["price_edge_tmp", "odds"], ascending=[False, False])
        best_book_map[key] = grp.iloc[0].get("book", "") if not grp.empty else ""

    df["available_books_count"] = df["selection_market_key"].map(available_map).fillna(0).astype(int)
    df["market_avg_odds"] = df["selection_market_key"].map(avg_odds_map)
    df["best_market_odds"] = df["selection_market_key"].map(best_odds_map)
    df["price_dispersion"] = df["selection_market_key"].map(dispersion_map)
    df["best_book"] = df["selection_market_key"].map(best_book_map)

    # Preserve API-reported signal count, but score and display consensus using real unique books.
    df["signal_count"] = pd.to_numeric(df.get("consensus_count"), errors="coerce").fillna(0).astype(int)
    df["consensus_count"] = np.minimum(
        df["signal_count"],
        df["available_books_count"].where(df["available_books_count"] > 0, df["signal_count"]),
    ).astype(int)

    df["price_edge_pct"] = df.apply(
        lambda r: price_edge_from_market(r.get("odds"), r.get("consensus_price", r.get("market_avg_odds"))),
        axis=1,
    )
    fallback_market_odds = df["market_avg_odds"].where(df["market_avg_odds"].notna(), df["consensus_price"])
    df["market_avg_odds"] = fallback_market_odds
    df["best_price_flag"] = (
        (df["best_book"].astype(str) == df["book"].astype(str))
        | (pd.to_numeric(df["best_market_odds"], errors="coerce") == pd.to_numeric(df["odds"], errors="coerce"))
    )

    real_books = df["available_books_count"].replace(0, np.nan)
    df["consensus_strength"] = (df["consensus_count"] / real_books) * 100.0
    df.loc[df["available_books_count"] < 2, "consensus_strength"] = np.nan
    df["consensus_strength"] = df["consensus_strength"].round(1)

    df["low_book_warning"] = (
        (df["available_books_count"].fillna(0) < 2)
        | (df["consensus_count"].fillna(0) < 2)
    )
    df["consensus_quality"] = np.where(
        df["available_books_count"].fillna(0) < 2,
        "Thin",
        np.where(
            (df["available_books_count"].fillna(0) >= 4) & (df["consensus_count"].fillna(0) >= 3),
            "Strong",
            "Fair",
        ),
    )

    # Dispersion only means something when multiple books are actually available.
    df.loc[df["available_books_count"] < 2, "price_dispersion"] = np.nan

    df["market_depth_score"] = (
        np.clip(df["available_books_count"].fillna(0), 0, 5) * 4.0
        + np.clip(df["consensus_count"].fillna(0), 0, 5) * 1.6
    )
    df["price_edge_score"] = np.clip(df["price_edge_pct"].fillna(0), -2.5, 3.5) * 8.0
    df["best_price_boost"] = np.where(df["best_price_flag"], 5.0, 0.0)
    df["dispersion_penalty"] = np.clip(df["price_dispersion"].fillna(0) - DISPERSION_ALERT_THRESHOLD, 0, 8) * 0.9
    df["thin_market_penalty"] = np.where(
        df["available_books_count"].fillna(0) < 2,
        14.0,
        np.where(df["available_books_count"].fillna(0) < 3, 6.0, 0.0),
    )
    df["disagreement_signal"] = (
        df["book_disagreement"].fillna(0) * 4.0
        + np.clip(df["price_dispersion"].fillna(0), 0, 8) * 0.8
    )
    return df


def prepare_rows(df, adaptive_context=None):
    df = df.copy()
    adaptive_context = adaptive_context or {}
    if df.empty:
        return df

    for col in [
        "line", "consensus_price", "consensus_count", "sharp_score", "model_prob",
        "book_disagreement", "clv_projection", "prev_odds", "closing_odds", "book", "odds"
    ]:
        if col not in df.columns:
            df[col] = np.nan

    df = enrich_market_context(df)
    df["edge_pct"] = df.apply(lambda r: implied_edge(r.get("model_prob"), r.get("odds")), axis=1)
    df["odds_bucket"] = df["odds"].apply(odds_bucket)
    df["consensus_bucket"] = df["consensus_count"].apply(consensus_bucket)
    df["market_priority"] = df["market"].map({"moneyline": 3, "spread": 2, "total": 1}).fillna(0)
    df["consensus_boost"] = np.where(
        df["consensus_count"].fillna(0) >= 4, 10,
        np.where(df["consensus_count"].fillna(0) >= 3, 6, np.where(df["consensus_count"].fillna(0) >= 2, 2, -4))
    )
    df["depth_boost"] = np.where(
        df["available_books_count"].fillna(0) >= 5, 10,
        np.where(df["available_books_count"].fillna(0) >= 4, 7, np.where(df["available_books_count"].fillna(0) >= 3, 3, np.where(df["available_books_count"].fillna(0) >= 2, 0, -8)))
    )
    df["clv_boost"] = np.clip(df["clv_projection"].fillna(0), -5, 20) * 0.18
    df["disagreement_boost"] = df["disagreement_signal"].fillna(0)
    df["sharp_component"] = np.clip((df["sharp_score"].fillna(0) - 35) * 1.25, 0, 36)
    df["edge_component"] = np.clip(df["edge_pct"].fillna(0) * 11.0, -20, 45)
    df["consensus_strength_boost"] = np.clip((df["consensus_strength"].fillna(0) - 50) / 10.0, -5, 5) * 2.2
    df["raw_score"] = (
        24
        + df["edge_component"]
        + df["sharp_component"]
        + df["consensus_boost"]
        + df["depth_boost"]
        + df["consensus_strength_boost"]
        + df["price_edge_score"].fillna(0)
        + df["best_price_boost"].fillna(0)
        + df["clv_boost"]
        + df["disagreement_boost"]
        - df["dispersion_penalty"].fillna(0)
        - df["thin_market_penalty"].fillna(0)
    )
    df["market_adaptive_adj"] = df["market"].astype(str).map(adaptive_context.get("market_map", {})).fillna(0.0)
    df["bucket_key"] = list(zip(df["market"].astype(str), df["odds_bucket"].astype(str), df["consensus_bucket"].astype(str)))
    df["bucket_adaptive_adj"] = df["bucket_key"].map(adaptive_context.get("bucket_map", {})).fillna(0.0)
    df["clv_adaptive_adj"] = df["bucket_key"].map(adaptive_context.get("clv_map", {})).fillna(0.0)
    df["adaptive_adj"] = (df["market_adaptive_adj"] + df["bucket_adaptive_adj"] + df["clv_adaptive_adj"]).round(3)
    df["raw_score"] = df["raw_score"] + df["adaptive_adj"]

    max_raw = max(float(df["raw_score"].max()), 1.0)
    min_raw = float(df["raw_score"].min())
    spread = max(max_raw - min_raw, 1.0)
    normalized = 35 + ((df["raw_score"] - min_raw) / spread) * 65
    df["score"] = np.clip(normalized, 0, SCORE_CAP).round(1)

    def conflict_key(row):
        line = row.get("line")
        if pd.isna(line):
            line = "ML"
        return f"{row.get('game')}|{row.get('market')}|{line}"

    df["conflict_key"] = df.apply(conflict_key, axis=1)
    df["selection_label"] = df.apply(
        lambda r: f"{r['selection']} {r['line']}" if pd.notna(r.get("line")) and str(r.get("market")) != "moneyline" else str(r["selection"]),
        axis=1,
    )
    df["market_win_rate_adj"] = df["market"].astype(str).map(adaptive_context.get("market_map", {})).fillna(0.0)
    df["market_clv_hit_rate"] = np.where(
        df["bucket_key"].map(adaptive_context.get("clv_map", {})).fillna(0.0) > 0,
        0.60,
        np.where(df["bucket_key"].map(adaptive_context.get("clv_map", {})).fillna(0.0) < 0, 0.40, 0.50),
    )
    df["adaptive_flag"] = np.where(df["adaptive_adj"] > 1.5, "Boosted", np.where(df["adaptive_adj"] < -1.5, "Cautious", "Neutral"))
    return df

def assign_tier(row):
    edge = safe_float(row.get("edge_pct"))
    score = safe_float(row.get("score"))
    consensus = safe_float(row.get("consensus_count"))
    books = safe_float(row.get("available_books_count"))
    price_edge = safe_float(row.get("price_edge_pct"))
    if edge >= 3.0 and score >= 86 and consensus >= 3 and books >= 3:
        return "A"
    if (
        ((edge >= 1.5 and score >= 74) or (price_edge >= PROMOTION_MIN_PRICE_EDGE and score >= PROMOTION_MIN_SCORE))
        and consensus >= 2 and books >= 2
    ):
        return "B"
    if edge >= 1.0 and score >= 62:
        return "C"
    return "Watch"

def correlation_tag(row):
    market = str(row.get("market", ""))
    selection = str(row.get("selection", "")).lower()
    line = row.get("line")

    if market == "total":
        return "Neutral"
    if market == "spread":
        if (not pd.isna(line)) and safe_float(line) < 0:
            return "Favorite side"
        if (not pd.isna(line)) and safe_float(line) > 0:
            return "Dog side"
    if market == "moneyline":
        odds = safe_float(row.get("odds"))
        return "Favorite side" if odds < 0 else "Dog side"
    return "Neutral"




def confidence_label(row):
    score = safe_float(row.get("score"))
    books = safe_float(row.get("available_books_count"))
    label = "Low"
    if score >= 90:
        label = "Elite"
    elif score >= 75:
        label = "High"
    elif score >= 60:
        label = "Medium"

    if books < 2 and label in {"Elite", "High"}:
        return "Medium"
    if books < 3 and label == "Elite":
        return "High"
    return label

def explainability(row):
    reasons = []
    books = safe_float(row.get("available_books_count"))
    support = safe_float(row.get("consensus_count"))
    if safe_float(row.get("edge_pct")) >= 2.0:
        reasons.append("model edge")
    if safe_float(row.get("price_edge_pct")) >= PRICE_EDGE_STRONG_THRESHOLD:
        reasons.append("best price edge")
    if bool(row.get("best_price_flag")):
        reasons.append("best available price")
    if books >= 4 and support >= 3:
        reasons.append("solid market depth")
    elif books >= 2 and support >= 2:
        reasons.append("usable consensus")
    if safe_float(row.get("sharp_score")) >= 55:
        reasons.append("sharp support")
    if safe_float(row.get("book_disagreement")) >= 1 or safe_float(row.get("price_dispersion")) >= DISPERSION_ALERT_THRESHOLD:
        reasons.append("market disagreement")
    if books < 2:
        reasons.append("thin book pool")
    if not reasons:
        reasons.append("watch only")
    return " • ".join(reasons[:4])

def compute_stackable(df):
    df = df.copy()
    df["stackable"] = True
    for _, grp in df.groupby("conflict_key"):
        if len(grp) > 1:
            df.loc[grp.index, "stackable"] = False
    return df


def smart_promotable(row):
    books = safe_float(row.get("available_books_count"))
    support = safe_float(row.get("consensus_count"))
    price_edge = safe_float(row.get("price_edge_pct"))
    edge = safe_float(row.get("edge_pct"))
    score = safe_float(row.get("score"))
    consensus_quality = str(row.get("consensus_quality", ""))
    skip_game = bool(row.get("skip_game", False))
    if skip_game:
        return False
    if books < PROMOTION_MIN_BOOKS or support < 2:
        return False
    if consensus_quality not in {"Fair", "Strong"}:
        return False
    if score < PROMOTION_MIN_SCORE:
        return False
    return (price_edge >= PROMOTION_MIN_PRICE_EDGE) or (edge >= PROMOTION_MIN_EDGE)


def final_rank_score(row):
    edge = max(0.0, safe_float(row.get("edge_pct")))
    consensus = min(5.0, max(0.0, safe_float(row.get("consensus_count"))))
    books = min(5.0, max(0.0, safe_float(row.get("available_books_count"))))
    adaptive = safe_float(row.get("adaptive_adj"), 0.0)
    clv_hit_rate = safe_float(row.get("market_clv_hit_rate"), 0.5)
    win_rate_adj = safe_float(row.get("market_win_rate_adj"), 0.0)
    price_edge = max(-2.5, min(3.5, safe_float(row.get("price_edge_pct"), 0.0)))
    consensus_strength = safe_float(row.get("consensus_strength"), 0.0) / 100.0
    best_price = 1.0 if bool(row.get("best_price_flag")) else 0.0
    low_book_penalty = -0.45 if bool(row.get("low_book_warning", False)) else 0.0
    score = (
        (edge * 0.36)
        + (price_edge * 0.22)
        + (consensus * 0.10)
        + (books * 0.08)
        + (consensus_strength * 0.12 * 10.0)
        + (best_price * 0.40)
        + (adaptive * 0.07)
        + ((clv_hit_rate - 0.5) * 10.0 * 0.03)
        + (win_rate_adj * 0.04)
        + low_book_penalty
    )
    return round(score, 3)

def apply_correlation_risk_adjustment(df):
    df = df.copy()
    active_idx = df.index[df["status"].eq("Active")].tolist()
    if not active_idx:
        return df

    for game, grp in df.loc[active_idx].groupby("game", dropna=False):
        if len(grp) <= 1:
            continue
        positive_mask = grp["correlation"].isin(["Favorite side", "Dog side"])
        if positive_mask.any():
            idxs = grp.index[positive_mask]
            df.loc[idxs, "units"] = (df.loc[idxs, "units"] * 0.80).round(2)
            df.loc[idxs, "why"] = df.loc[idxs, "why"].astype(str) + " • correlation risk adjusted"
    return df


def apply_variance_control(df, max_total_units=MAX_TOTAL_UNITS):
    df = df.copy()
    active_mask = df["status"].eq("Active")
    total_units = safe_float(df.loc[active_mask, "units"].sum())
    if total_units > max_total_units and total_units > 0:
        scale = max_total_units / total_units
        df.loc[active_mask, "units"] = (df.loc[active_mask, "units"] * scale).round(2)
        df.loc[active_mask, "why"] = df.loc[active_mask, "why"].astype(str) + " • variance scaled"
    return df


def dynamic_units(row, adaptive_context=None):
    adaptive_context = adaptive_context or {}
    tier = str(row.get("tier"))
    status = str(row.get("status"))
    edge = safe_float(row.get("edge_pct"))
    score = safe_float(row.get("score"))

    if status != "Active":
        return 0.05 if edge > 0 else 0.00

    if tier == "A":
        units = 0.75 + min(0.50, max(0.0, (edge - 3.0) * 0.12) + max(0.0, (score - 86.0) * 0.01))
        units = min(adaptive_context.get("max_single_bet", DEFAULT_MAX_SINGLE_BET), units * adaptive_context.get("unit_multiplier", 1.0))
        return round(min(1.25, units), 2)
    if tier == "B":
        units = 0.40 + min(0.35, max(0.0, (edge - 1.8) * 0.10) + max(0.0, (score - 74.0) * 0.008))
        units = min(adaptive_context.get("max_single_bet", DEFAULT_MAX_SINGLE_BET), units * adaptive_context.get("unit_multiplier", 1.0))
        return round(min(0.75, units), 2)
    if tier == "C":
        units = 0.10 + min(0.30, max(0.0, (edge - 1.0) * 0.08) + max(0.0, (score - 62.0) * 0.006))
        units = min(adaptive_context.get("max_single_bet", DEFAULT_MAX_SINGLE_BET), units * adaptive_context.get("unit_multiplier", 1.0))
        return round(min(0.40, units), 2)
    return 0.00


def resolve_board(
    df,
    aggressive=True,
    keep_per_game=2,
    best_bet_cap=MAX_BEST_BETS,
    max_tier_a=MAX_TIER_A,
    skip_games_without_ab=True,
    elite_only=False,
    max_active_plays=MAX_ACTIVE_PLAYS,
    max_total_units=MAX_TOTAL_UNITS,
    adaptive_context=None,
):
    adaptive_context = adaptive_context or {}
    df = prepare_rows(df, adaptive_context=adaptive_context)
    if df.empty:
        return df

    df["tier"] = df.apply(assign_tier, axis=1)
    tier_a_rank = df[df["tier"].eq("A")].sort_values(["score", "edge_pct", "consensus_count"], ascending=False)
    if len(tier_a_rank) > max_tier_a:
        demote_idxs = tier_a_rank.iloc[max_tier_a:].index
        df.loc[demote_idxs, "tier"] = "B"

    df["why"] = df.apply(explainability, axis=1)
    df["correlation"] = df.apply(correlation_tag, axis=1)
    df = compute_stackable(df)
    df["final_rank"] = df.apply(final_rank_score, axis=1)
    df["status"] = "Watch"
    df["best_bet_tag"] = ""
    df["skip_game"] = False

    effective_min_edge = MIN_ACTIVE_EDGE * safe_float(adaptive_context.get("edge_multiplier"), 1.0)
    candidate_mask = (
        (df["tier"].isin(["A", "B"]))
        & (df["edge_pct"].fillna(-999) >= effective_min_edge)
    ) | df.apply(smart_promotable, axis=1)
    candidates = df[candidate_mask].copy()
    if elite_only:
        candidates = candidates[candidates["tier"].isin(["A", "B"]) & (candidates["score"] >= 75)].copy()

    max_per_game = keep_per_game if aggressive else 1
    chosen = []

    for game, grp in candidates.groupby("game", dropna=False):
        grp = grp.sort_values(["final_rank", "score", "price_edge_pct", "edge_pct", "consensus_count", "market_priority"], ascending=False)

        promo_mask = grp.apply(smart_promotable, axis=1)
        game_has_ab = grp["tier"].isin(["A", "B"]).any()
        game_has_promotable = bool(promo_mask.any())
        max_game_books = safe_float(grp["available_books_count"].max())
        max_game_consensus = safe_float(grp["consensus_count"].max())
        if skip_games_without_ab and (not game_has_ab) and (not game_has_promotable):
            df.loc[df["game"].eq(game), "skip_game"] = True
            df.loc[df["game"].eq(game), "why"] = "skip game • weak game quality"
            continue
        if skip_games_without_ab and (max_game_books < 2 or max_game_consensus < 2):
            df.loc[df["game"].eq(game), "skip_game"] = True
            df.loc[df["game"].eq(game), "why"] = "skip game • thin market"
            continue

        used_conflicts = set()
        game_selected = []
        for idx, row in grp.iterrows():
            if len(game_selected) >= max_per_game:
                break
            if row["conflict_key"] in used_conflicts:
                continue
            if row["tier"] == "C" and not smart_promotable(row):
                continue
            game_selected.append(idx)
            used_conflicts.add(row["conflict_key"])

        chosen.extend(game_selected)

    if chosen:
        ranked_all = df.loc[chosen].sort_values(["final_rank", "score", "edge_pct", "clv_projection", "consensus_count"], ascending=False)
        chosen = ranked_all.head(max_active_plays).index.tolist()

    df.loc[chosen, "status"] = "Active"

    if chosen:
        best_pool = df.loc[chosen].sort_values(["final_rank", "score", "edge_pct", "clv_projection", "consensus_count"], ascending=False)
        for idx in best_pool.head(best_bet_cap).index:
            df.loc[idx, "best_bet_tag"] = "🏆 Best Bet"

    df.loc[df["edge_pct"].fillna(-999) < effective_min_edge, "status"] = "Watch"
    df.loc[df["skip_game"], "status"] = "Watch"

    df["units"] = df.apply(lambda r: dynamic_units(r, adaptive_context=adaptive_context), axis=1)
    df = apply_correlation_risk_adjustment(df)
    variance_cap = min(max_total_units, safe_float(adaptive_context.get("max_total_units"), max_total_units))
    df = apply_variance_control(df, max_total_units=variance_cap)
    df["confidence"] = df.apply(confidence_label, axis=1)
    boost_mask = df["adaptive_flag"].eq("Boosted")
    caution_mask = df["adaptive_flag"].eq("Cautious")
    df.loc[boost_mask, "why"] = df.loc[boost_mask, "why"].astype(str) + " • adaptive boost"
    df.loc[caution_mask, "why"] = df.loc[caution_mask, "why"].astype(str) + " • adaptive caution"

    watch_mask = df["status"].eq("Watch")
    df.loc[watch_mask & (df["why"] == "watch only"), "why"] = "watch only"

    tier_sort = {"A": 0, "B": 1, "C": 2, "Watch": 3}
    df["tier_sort"] = df["tier"].map(tier_sort).fillna(9)
    df["status_sort"] = np.where(df["status"].eq("Active"), 0, 1)
    df = df.sort_values(["status_sort", "tier_sort", "final_rank", "score", "edge_pct"], ascending=[True, True, False, False, False]).drop(columns=["tier_sort", "status_sort"])
    return df.reset_index(drop=True)




def parlay_payout_multiplier(odds):
    odds = safe_float(odds, 0)
    if odds > 0:
        return 1 + (odds / 100.0)
    if odds < 0:
        return 1 + (100.0 / abs(odds))
    return 1.0


def payout_to_american(mult):
    mult = safe_float(mult, 1.0)
    if mult <= 1:
        return 0
    profit = mult - 1
    if profit >= 1:
        return int(round(profit * 100))
    return int(round(-100 / profit))



def build_ai_bet_slip(board_df):
    active = board_df[
        (board_df["status"] == "Active")
        & (board_df["tier"].isin(["A", "B"]))
        & ((board_df["price_edge_pct"].fillna(0) >= 0.75) | (board_df["best_price_flag"]))
    ].copy()
    if active.empty:
        return None

    active["ev_proxy"] = active.apply(expected_value_proxy, axis=1)
    active = active.sort_values(["ev_proxy", "price_edge_pct", "final_rank", "score"], ascending=False)

    rows = [r for _, r in active.iterrows()]
    best_combo = None
    best_combo_score = -1e9

    # evaluate singles and pairs
    import itertools
    for r in rows:
        combo = [r]
        combo_score = safe_float(r.get("ev_proxy")) + safe_float(r.get("final_rank")) * 0.45 + max(0.0, safe_float(r.get("price_edge_pct"))) * 0.8
        if combo_score > best_combo_score:
            best_combo_score = combo_score
            best_combo = combo

    for r1, r2 in itertools.combinations(rows, 2):
        if r1["game"] == r2["game"]:
            continue
        if r1["conflict_key"] == r2["conflict_key"]:
            continue
        if not bool(r1.get("stackable", False)) or not bool(r2.get("stackable", False)):
            continue
        corr_penalty = 0.0
        if str(r1.get("correlation")) == str(r2.get("correlation")) and str(r1.get("correlation")) != "Neutral":
            corr_penalty = 1.0
        combo_score = (
            safe_float(r1.get("ev_proxy")) + safe_float(r2.get("ev_proxy"))
            + safe_float(r1.get("final_rank")) * 0.35 + safe_float(r2.get("final_rank")) * 0.35
            - corr_penalty
        )
        if combo_score > best_combo_score:
            best_combo_score = combo_score
            best_combo = [r1, r2]

    if not best_combo:
        return None

    mult = 1.0
    min_score = 999.0
    for row in best_combo:
        mult *= parlay_payout_multiplier(row["odds"])
        min_score = min(min_score, safe_float(row["score"], 0))

    parlay_odds = payout_to_american(mult) if len(best_combo) >= 2 else int(safe_float(best_combo[0]["odds"], 0))

    if min_score >= 90:
        slip_conf = "Elite"
    elif min_score >= 75:
        slip_conf = "High"
    elif min_score >= 60:
        slip_conf = "Medium"
    else:
        slip_conf = "Low"

    risk_level = "Controlled" if len(best_combo) >= 2 else ("Low" if all(bool(r.get("best_price_flag")) for r in best_combo) else "Medium")
    return {
        "picks": best_combo,
        "parlay_odds": parlay_odds,
        "confidence": slip_conf,
        "stackable_ok": len(best_combo) >= 2,
        "risk_level": risk_level,
        "ev_proxy": round(best_combo_score, 2),
    }

# -----------------------------
# Persistence
# -----------------------------
def ensure_bet_log():
    cols = [
        "timestamp", "game", "market", "selection", "line", "book", "bet_odds", "prev_odds",
        "consensus_price", "consensus_count", "closing_odds", "result", "units", "tier",
        "score", "edge_pct", "status", "why", "adaptive_adj", "adaptive_flag", "clv_hit", "clv_value", "available_books_count", "market_avg_odds", "best_book", "best_market_odds", "price_edge_pct", "price_dispersion", "consensus_strength", "best_price_flag", "low_book_warning", "auto_logged"
    ]
    if BET_LOG_PATH.exists():
        try:
            return pd.read_csv(BET_LOG_PATH)
        except Exception:
            pass
    return pd.DataFrame(columns=cols)


def save_bet_log(df):
    df.to_csv(BET_LOG_PATH, index=False)


def auto_log_active_plays(board_df):
    log_df = ensure_bet_log()
    key_cols = ["game", "market", "selection", "book", "bet_odds"]
    existing = set()
    if not log_df.empty:
        existing = set(log_df[key_cols].fillna("NA").astype(str).agg("|".join, axis=1).tolist())

    rows_to_add = []
    for _, row in board_df[board_df["status"] == "Active"].iterrows():
        key = "|".join([
            str(row.get("game", "NA")),
            str(row.get("market", "NA")),
            str(row.get("selection", "NA")),
            str(row.get("book", "NA")),
            str(row.get("odds", "NA")),
        ])
        if key in existing:
            continue
        rows_to_add.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "game": row.get("game"),
            "market": row.get("market"),
            "selection": row.get("selection"),
            "line": row.get("line"),
            "book": row.get("book"),
            "bet_odds": row.get("odds"),
            "prev_odds": row.get("prev_odds"),
            "consensus_price": row.get("consensus_price"),
            "consensus_count": row.get("consensus_count"),
            "closing_odds": row.get("closing_odds"),
            "result": None,
            "units": row.get("units"),
            "tier": row.get("tier"),
            "score": row.get("score"),
            "edge_pct": row.get("edge_pct"),
            "status": row.get("status"),
            "why": row.get("why"),
            "adaptive_adj": row.get("adaptive_adj"),
            "adaptive_flag": row.get("adaptive_flag"),
            "clv_hit": clv_hit(row.get("odds"), row.get("closing_odds")),
            "clv_value": (american_to_prob(row.get("closing_odds")) - american_to_prob(row.get("odds"))) * 100 if pd.notna(american_to_prob(row.get("closing_odds"))) and pd.notna(american_to_prob(row.get("odds"))) else np.nan,
            "available_books_count": row.get("available_books_count"),
            "market_avg_odds": row.get("market_avg_odds"),
            "best_book": row.get("best_book"),
            "best_market_odds": row.get("best_market_odds"),
            "price_edge_pct": row.get("price_edge_pct"),
            "price_dispersion": row.get("price_dispersion"),
            "consensus_strength": row.get("consensus_strength"),
            "best_price_flag": row.get("best_price_flag"),
            "low_book_warning": row.get("low_book_warning"),
            "auto_logged": True,
        })

    if rows_to_add:
        log_df = pd.concat([log_df, pd.DataFrame(rows_to_add)], ignore_index=True)
        save_bet_log(log_df)
    return log_df, len(rows_to_add)


def profit_from_row(row):
    result = str(row.get("result", "")).lower()
    units = safe_float(row.get("units"), 0)
    odds = safe_float(row.get("bet_odds"), 0)
    if result not in {"win", "loss", "push"}:
        return np.nan
    if result == "push":
        return 0.0
    if result == "loss":
        return -units
    if odds > 0:
        return units * (odds / 100)
    return units * (100 / abs(odds)) if odds != 0 else 0.0


def build_learning_profile(log_df):
    if log_df.empty:
        return pd.DataFrame(columns=["market", "odds_bucket", "consensus_bucket", "bets", "wins", "win_rate"])

    temp = log_df.copy()
    temp["market"] = temp["market"].fillna("unknown")
    temp["odds_bucket"] = temp["bet_odds"].apply(odds_bucket)
    temp["consensus_bucket"] = temp["consensus_count"].apply(consensus_bucket)
    temp["is_win"] = temp["result"].astype(str).str.lower().eq("win").astype(int)
    settled = temp[temp["result"].astype(str).str.lower().isin(["win", "loss", "push"])].copy()

    if settled.empty:
        grouped = temp.groupby(["market", "odds_bucket", "consensus_bucket"], dropna=False).size().reset_index(name="bets")
        grouped["wins"] = 0
        grouped["win_rate"] = 0.0
        return grouped.sort_values(["market", "consensus_bucket", "odds_bucket"]).reset_index(drop=True)

    grouped = (
        settled.groupby(["market", "odds_bucket", "consensus_bucket"], dropna=False)
        .agg(bets=("result", "count"), wins=("is_win", "sum"))
        .reset_index()
    )
    grouped["win_rate"] = np.where(grouped["bets"] > 0, grouped["wins"] / grouped["bets"], 0.0)
    return grouped.sort_values(["market", "consensus_bucket", "odds_bucket"]).reset_index(drop=True)


# -----------------------------
# UI helpers
# -----------------------------


def render_daily_performance(log_df):
    settled = pd.DataFrame() if log_df is None or log_df.empty else log_df[log_df["result"].astype(str).str.lower().isin(["win", "loss", "push"])].copy()
    if settled.empty:
        st.markdown(
            """
            <div class='summary-card'>
                <div class='summary-title'>📊 Daily Performance</div>
                <div class='stat-label'>Settled Bets: <b>0</b></div>
                <div class='stat-label'>Win Rate: <b>0.0%</b></div>
                <div class='stat-label'>CLV Hit Rate: <b>—</b></div>
                <div class='stat-label'>Net Units: <b>0.00u</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    settled["profit"] = settled.apply(profit_from_row, axis=1)
    settled["clv_hit"] = settled.apply(lambda r: clv_hit(r.get("bet_odds"), r.get("closing_odds")), axis=1)
    win_rate = settled["result"].astype(str).str.lower().eq("win").mean() * 100
    clv_hits = settled["clv_hit"].dropna()
    clv_rate = clv_hits.mean() * 100 if not clv_hits.empty else np.nan
    net_units = safe_float(settled["profit"].sum())
    st.markdown(
        f"""
        <div class='summary-card'>
            <div class='summary-title'>📊 Daily Performance</div>
            <div class='stat-label'>Settled Bets: <b>{len(settled)}</b></div>
            <div class='stat-label'>Win Rate: <b>{win_rate:.1f}%</b></div>
            <div class='stat-label'>CLV Hit Rate: <b>{'—' if pd.isna(clv_rate) else f'{clv_rate:.1f}%'} </b></div>
            <div class='stat-label'>Net Units: <b>{net_units:.2f}u</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_risk_summary(board_df, adaptive_context):
    active = board_df[board_df["status"].eq("Active")].copy()
    total_units = safe_float(active["units"].sum()) if not active.empty else 0.0
    games = int(active["game"].nunique()) if not active.empty else 0
    streak = int(adaptive_context.get("streak", 0))
    risk_label = adaptive_context.get("risk_label", "Neutral")
    if total_units >= 3.0:
        exposure = "High"
    elif total_units >= 1.75:
        exposure = "Medium"
    else:
        exposure = "Low"
    st.markdown(
        f"""
        <div class='summary-card'>
            <div class='summary-title'>💰 Daily Risk Summary</div>
            <div class='stat-label'>Total Units: <b>{total_units:.2f}u</b></div>
            <div class='stat-label'>Games Involved: <b>{games}</b></div>
            <div class='stat-label'>Risk Level: <b>{exposure}</b></div>
            <div class='stat-label'>Adaptive State: <b>{risk_label}</b> {'(streak ' + str(streak) + ')' if streak else ''}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def inject_css():
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.3rem; padding-bottom: 2rem; max-width: 1100px;}
        .summary-card, .play-card {
            border: 1px solid rgba(49,51,63,0.18);
            border-radius: 20px;
            padding: 16px 18px;
            margin-bottom: 14px;
            background: rgba(255,255,255,0.02);
        }
        .summary-title {font-size: 1.05rem; font-weight: 700; margin-bottom: 8px;}
        .stat-label {font-size: 0.95rem; opacity: 0.8;}
        .stat-value {font-size: 1.2rem; font-weight: 700;}
        .play-title {font-size: 1.18rem; font-weight: 800; margin-bottom: 2px;}
        .play-sub {font-size: 0.98rem; opacity: 0.85; margin-bottom: 10px;}
        .pill {
            display:inline-block; padding: 4px 10px; border-radius: 999px;
            font-size: 0.9rem; font-weight: 700; margin-right: 6px; margin-bottom: 4px;
            background: rgba(120,120,120,0.12);
        }
        .pill-a {background: rgba(16,185,129,0.16);}
        .pill-b {background: rgba(59,130,246,0.14);}
        .pill-c {background: rgba(245,158,11,0.14);}
        .pill-watch {background: rgba(148,163,184,0.18);}
        .pill-active {background: rgba(245,158,11,0.16);}
        .pill-best {background: rgba(168,85,247,0.16);}
        .why {font-size: 0.95rem; opacity: 0.82; margin-top: 8px;}
        .section-h {font-size: 2.0rem; font-weight: 800; margin-top: 18px; margin-bottom: 12px;}
        @media (max-width: 768px) {
            .section-h {font-size: 1.4rem;}
            .play-title {font-size: 1.05rem;}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def pill_class(value):
    return {"A": "pill-a", "B": "pill-b", "C": "pill-c", "Watch": "pill-watch"}.get(str(value), "pill-watch")


def render_summary(board_df, mode_label):
    live_rows = len(board_df)
    qualified = int(((board_df["status"] == "Active") & (board_df["tier"] != "Watch")).sum()) if not board_df.empty else 0
    watchlist = int((board_df["status"] != "Active").sum()) if not board_df.empty else 0
    tier_counts = board_df["tier"].value_counts().to_dict() if not board_df.empty else {}
    avg_edge = board_df.loc[board_df["status"] == "Active", "edge_pct"].mean() if not board_df.empty else 0

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f"""
            <div class='summary-card'>
                <div class='summary-title'>Market Snapshot</div>
                <div class='stat-label'>Live Rows: <span class='stat-value'>{live_rows}</span></div>
                <div class='stat-label'>Watchlist: <span class='stat-value'>{watchlist}</span></div>
                <div class='stat-label'>Qualified: <span class='stat-value'>{qualified}</span></div>
                <div class='stat-label'>Mode: <span class='stat-value'>{mode_label}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
            <div class='summary-card'>
                <div class='summary-title'>Tier Summary</div>
                <div class='stat-label'>Tier A: <span class='stat-value'>{tier_counts.get('A', 0)}</span></div>
                <div class='stat-label'>Tier B: <span class='stat-value'>{tier_counts.get('B', 0)}</span></div>
                <div class='stat-label'>Tier C: <span class='stat-value'>{tier_counts.get('C', 0)}</span></div>
                <div class='stat-label'>Avg Edge: <span class='stat-value'>{0 if pd.isna(avg_edge) else avg_edge:.2f}%</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_play_cards(df, title):
    st.markdown(f"<div class='section-h'>{title}</div>", unsafe_allow_html=True)
    if df.empty:
        st.info("No rows to show.")
        return

    for i, (_, row) in enumerate(df.iterrows(), start=1):
        badge_html = (
            f"<span class='pill {pill_class(row['tier'])}'>Tier {row['tier']}</span>"
            f"<span class='pill {'pill-active' if row['status']=='Active' else 'pill-watch'}'>{row['status']}</span>"
        )
        if row.get("best_bet_tag"):
            badge_html += f"<span class='pill pill-best'>{row['best_bet_tag']}</span>"

        st.markdown(
            f"""
            <div class='play-card'>
                <div>{badge_html}</div>
                <div class='play-title'>#{i} {row['selection_label']}</div>
                <div class='play-sub'>{row['game']}</div>
                <div style='display:grid;grid-template-columns:1fr 1fr;gap:8px;'>
                    <div>Book: <b>{row['book']}</b></div>
                    <div>Odds: <b>{int(row['odds']) if not pd.isna(row['odds']) else ''}</b></div>
                    <div>Units: <b>{safe_float(row['units']):.2f}u</b></div>
                    <div>Score: <b>{safe_float(row['score']):.1f}</b></div>
                    <div>Sharp: <b>{safe_float(row['sharp_score']):.1f}</b></div>
                    <div>Edge: <b>{safe_float(row['edge_pct']):.2f}%</b></div>
                    <div>Books Seen: <b>{int(safe_float(row['available_books_count']))}</b></div>
                    <div>Support: <b>{int(safe_float(row['consensus_count']))} books</b></div>
                    <div>Best Book: <b>{row['best_book'] if str(row.get('best_book', '')) else row['book']}</b></div>
                    <div>Price Edge: <b>{display_num(row.get('price_edge_pct'), 2, '%')}</b></div>
                    <div>Consensus: <b>{row.get('consensus_quality', 'Thin')}</b></div>
                    <div>Dispersion: <b>{display_num(row.get('price_dispersion'), 2, '%')}</b></div>
                    <div>Confidence: <b>{row['confidence']}</b></div>
                    <div>Correlation: <b>{row['correlation']}</b></div>
                    <div>Best Price: <b>{'Yes' if bool(row.get('best_price_flag', False)) else 'No'}</b></div>
                    <div>Thin Market: <b>{'Yes' if bool(row.get('low_book_warning', False)) else 'No'}</b></div>
                    <div>Stackable: <b>{'Yes' if bool(row['stackable']) else 'No'}</b></div>
                    <div>Skip Game: <b>{'Yes' if bool(row.get('skip_game', False)) else 'No'}</b></div>
                </div>
                <div class='why'>{row['why']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# -----------------------------
# App
# -----------------------------
inject_css()
st.title(APP_TITLE)
st.caption(APP_SUBTITLE)

with st.sidebar:
    st.header("V31.1 Controls")
    aggressive = st.toggle("Aggressive mode", value=True)
    auto_log = st.toggle("Auto-log active plays", value=True)
    elite_only = st.toggle("Elite plays only", value=False)
    keep_per_game = st.selectbox("Max active plays per game", [1, 2, 3], index=1)
    max_active_plays = st.selectbox("Max total active plays", [2, 3, 4, 5], index=1)
    best_bet_cap = st.selectbox("Max best bets on slate", [1, 2, 3], index=1)
    max_tier_a = st.selectbox("Max Tier A plays", [1, 2, 3, 4], index=2)
    max_total_units = st.selectbox("Max total slate units", [2.5, 3.0, 3.5, 4.0], index=2)
    skip_games_without_ab = st.toggle("Skip weak games", value=True)
    st.caption("Upload a CSV with live rows to replace the demo feed.")
    upload = st.file_uploader("Live rows CSV", type=["csv"])

bet_log_df = ensure_bet_log()
adaptive_context = build_adaptive_context(bet_log_df)
raw_df = load_csv(upload, default_live_rows())
board_df = resolve_board(raw_df, aggressive=aggressive, keep_per_game=keep_per_game, best_bet_cap=best_bet_cap, max_tier_a=max_tier_a, skip_games_without_ab=skip_games_without_ab, elite_only=elite_only, max_active_plays=max_active_plays, max_total_units=max_total_units, adaptive_context=adaptive_context)

render_summary(board_df, "Aggressive" if aggressive else "Standard")
render_risk_summary(board_df, adaptive_context)
render_daily_performance(bet_log_df)

with st.expander("🎛️ Adaptive Thresholds"):
    st.write(f"• Minimum active edge: {MIN_ACTIVE_EDGE:.2f}%")
    st.write(f"• Best bet cap: {best_bet_cap}")
    st.write(f"• Max Tier A plays: {max_tier_a}")
    st.write(f"• Max active plays: {max_active_plays}")
    st.write(f"• Max total units: {max_total_units:.1f}u")
    st.write(f"• Elite only mode: {'On' if elite_only else 'Off'}")
    st.write(f"• Adaptive state: {adaptive_context.get('risk_label', 'Neutral')}")
    st.write("• Ranking weights: edge • best price • consensus strength • market depth • adaptive")
    st.write(f"• Adaptive learning minimum sample: {ADAPTIVE_MIN_SAMPLE} graded bets per bucket")
    st.write("• Positive same-game correlation triggers unit reduction")
    st.write(f"• Skip weak games: {'On' if skip_games_without_ab else 'Off'}")

active_df = board_df[(board_df["status"] == "Active") & (board_df["tier"] != "Watch")].copy()
watch_df = board_df[board_df["status"] != "Active"].copy()

render_play_cards(active_df, "🎯 Compact Top Plays")
render_play_cards(watch_df, "👀 Compact Watchlist")


slip = build_ai_bet_slip(board_df)
if slip:
    st.markdown("<div class='section-h'>🎯 AI Bet Slip</div>", unsafe_allow_html=True)
    lines = []
    for i, row in enumerate(slip["picks"], start=1):
        lines.append(f"{i}. {row['selection_label']} ({row['game']})")
    slip_text = "<br>".join(lines)
    parlay_display = f"+{slip['parlay_odds']}" if slip['parlay_odds'] > 0 else str(slip['parlay_odds'])
    st.markdown(f"""
        <div class='summary-card'>
            <div class='summary-title'>Recommended Slip</div>
            <div class='stat-label'>{slip_text}</div>
            <div class='stat-label' style='margin-top:8px;'>Projected Odds: <span class='stat-value'>{parlay_display}</span></div>
            <div class='stat-label'>Confidence: <span class='stat-value'>{slip['confidence']}</span></div>
            <div class='stat-label'>Type: <span class='stat-value'>{'Parlay' if slip['stackable_ok'] else 'Single best bet'}</span></div>
            <div class='stat-label'>Risk Level: <span class='stat-value'>{slip['risk_level']}</span></div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<div class='section-h'>✅ Quick Table</div>", unsafe_allow_html=True)
quick_cols = [
    "tier", "status", "game", "market", "selection_label", "book", "odds", "units",
    "score", "final_rank", "edge_pct", "price_edge_pct", "available_books_count", "consensus_count", "consensus_strength", "best_book", "confidence", "best_bet_tag", "stackable", "correlation", "skip_game"
]
st.dataframe(board_df[quick_cols].rename(columns={"selection_label": "selection"}), use_container_width=True, hide_index=True)

with st.expander("📊 Full Scored Rows"):
    st.dataframe(board_df, use_container_width=True, hide_index=True)

with st.expander("🛰️ Raw Live Rows"):
    st.dataframe(raw_df, use_container_width=True, hide_index=True)

if auto_log:
    bet_log_df, added_count = auto_log_active_plays(board_df)
    if added_count:
        st.success(f"Auto-logged {added_count} new active play(s).")

st.markdown("<div class='section-h'>📝 Bet Log + Grading</div>", unsafe_allow_html=True)

with st.form("manual_bet_form"):
    c1, c2 = st.columns(2)
    with c1:
        game = st.text_input("Game", value="")
        market = st.selectbox("Market", ["moneyline", "spread", "total"], index=0)
        selection = st.text_input("Selection", value="")
        line = st.text_input("Line", value="")
        units = st.number_input("Units", min_value=0.0, step=0.05, value=0.0)
    with c2:
        book = st.text_input("Book", value="DraftKings")
        bet_odds = st.number_input("Bet Odds", step=1, value=-110)
        prev_odds = st.number_input("Previous Odds", step=1, value=-110)
        consensus_price = st.number_input("Consensus Price", step=1, value=-110)
        consensus_count = st.slider("Consensus Count", 1, 5, 3)
        closing_odds = st.number_input("Closing Odds", step=1, value=-110)
        result = st.selectbox("Result", ["", "win", "loss", "push"], index=0)

    submitted = st.form_submit_button("Add / Grade Bet")
    if submitted:
        new_row = pd.DataFrame([
            {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "game": game,
                "market": market,
                "selection": selection,
                "line": line if line != "" else np.nan,
                "book": book,
                "bet_odds": bet_odds,
                "prev_odds": prev_odds,
                "consensus_price": consensus_price,
                "consensus_count": consensus_count,
                "closing_odds": closing_odds,
                "result": result if result else None,
                "units": units,
                "tier": None,
                "score": None,
                "edge_pct": None,
                "status": "Manual",
                "why": "manual entry",
                "available_books_count": np.nan,
                "market_avg_odds": consensus_price,
                "best_book": book,
                "best_market_odds": bet_odds,
                "price_edge_pct": price_edge_from_market(bet_odds, consensus_price),
                "price_dispersion": np.nan,
                "consensus_strength": np.nan,
                "best_price_flag": True,
                "low_book_warning": consensus_count < LOW_BOOK_THRESHOLD,
                "auto_logged": False,
            }
        ])
        bet_log_df = pd.concat([bet_log_df, new_row], ignore_index=True)
        save_bet_log(bet_log_df)
        st.success("Bet added to log.")

if not bet_log_df.empty:
    bet_log_df["profit"] = bet_log_df.apply(profit_from_row, axis=1)
    settled = bet_log_df[bet_log_df["result"].astype(str).str.lower().isin(["win", "loss", "push"])].copy()
    settled_bets = len(settled)
    wins = int(settled["result"].astype(str).str.lower().eq("win").sum()) if settled_bets else 0
    win_rate = (wins / settled_bets) if settled_bets else 0.0
    net_units = settled["profit"].sum() if settled_bets else 0.0
    clv_vals = []
    for _, r in settled.iterrows():
        bo = safe_float(r.get("bet_odds"), np.nan)
        co = safe_float(r.get("closing_odds"), np.nan)
        if not pd.isna(bo) and not pd.isna(co):
            clv_vals.append(american_to_prob(bo) - american_to_prob(co))
    avg_clv = (np.nanmean(clv_vals) * 100) if clv_vals else np.nan
else:
    settled_bets = 0
    win_rate = 0.0
    net_units = 0.0
    avg_clv = np.nan

clv_hit_vals = [clv_hit(r.get("bet_odds"), r.get("closing_odds")) for _, r in settled.iterrows()] if "settled" in locals() else []
clv_hit_rate = np.nanmean(clv_hit_vals) * 100 if len([x for x in clv_hit_vals if not pd.isna(x)]) else np.nan
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Settled Bets", settled_bets)
m2.metric("Win Rate", f"{win_rate * 100:.1f}%")
m3.metric("Net Units", f"{net_units:.2f}u")
m4.metric("Avg CLV", "—" if pd.isna(avg_clv) else f"{avg_clv:.2f}%")
m5.metric("CLV Hit Rate", "—" if pd.isna(clv_hit_rate) else f"{clv_hit_rate:.1f}%")

st.dataframe(bet_log_df, use_container_width=True, hide_index=True)

profile_df = build_learning_profile(bet_log_df)
profile_df.to_csv(LEARNING_PROFILE_PATH, index=False)
board_df.to_csv(SNAPSHOT_PATH, index=False)

st.markdown("<div class='section-h'>🧠 Adaptive Learning Profile</div>", unsafe_allow_html=True)
st.dataframe(profile_df, use_container_width=True, hide_index=True)

st.markdown("<div class='section-h'>💾 Export</div>", unsafe_allow_html=True)

bet_buf = io.BytesIO()
profile_buf = io.BytesIO()
snap_buf = io.BytesIO()

bet_log_df.to_csv(bet_buf, index=False)
profile_df.to_csv(profile_buf, index=False)
board_df.to_csv(snap_buf, index=False)

st.download_button("Download Bet Log CSV", bet_buf.getvalue(), file_name="bet_log.csv", mime="text/csv")
st.download_button("Download Learning Profile CSV", profile_buf.getvalue(), file_name="learning_profile.csv", mime="text/csv")
st.download_button("Download Snapshot CSV", snap_buf.getvalue(), file_name="snapshot.csv", mime="text/csv")

st.caption(
    "V31.2 adds smart promotion logic so high-quality fair-depth markets can surface as top plays without overpromoting weak games."
)
