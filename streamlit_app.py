
# streamlit_app_v26.py
# V26 Adaptive Engine
#
# Upgrade focus:
# - adaptive live thresholds
# - qualification tiers (A / B / C / Watchlist)
# - dynamic threshold tuning by market conditions
# - softer live ranking so the app always shows best opportunities
# - sharper movement / disagreement scoring
# - optional auto refresh
#
# Notes:
# - Works with The Odds API style odds data if you provide a key.
# - Falls back to realistic test data if no key is provided.
# - Uses local CSV persistence for bet logs, learning profile, and odds snapshots.

import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
import streamlit as st

# ------------------------------------------------------------
# Page setup
# ------------------------------------------------------------
st.set_page_config(page_title="Sports Betting AI Dashboard V26 Adaptive Engine", layout="wide")
st.title("🔥 Sports Betting AI Dashboard V26")
st.caption("Adaptive Engine: fetch → compare → detect → rank → tier → track")

DATA_DIR = Path(".")
BET_LOG_PATH = DATA_DIR / "bet_log_v26.csv"
PROFILE_PATH = DATA_DIR / "learning_profile_v26.csv"
SNAPSHOT_PATH = DATA_DIR / "odds_snapshot_v26.csv"


# ------------------------------------------------------------
# Generic helpers
# ------------------------------------------------------------
def safe_read_csv(path: Path, fallback: pd.DataFrame) -> pd.DataFrame:
    try:
        if path.exists():
            return pd.read_csv(path)
    except Exception:
        pass
    return fallback.copy()


def safe_save_csv(df: pd.DataFrame, path: Path) -> None:
    try:
        df.to_csv(path, index=False)
    except Exception:
        pass


def american_to_implied_prob(odds: float) -> float:
    try:
        o = float(odds)
        if o > 0:
            return 100.0 / (o + 100.0)
        return abs(o) / (abs(o) + 100.0)
    except Exception:
        return np.nan


def american_to_decimal(odds: float) -> float:
    try:
        o = float(odds)
        if o > 0:
            return 1.0 + o / 100.0
        return 1.0 + 100.0 / abs(o)
    except Exception:
        return np.nan


def normalize_0_100(value: float, min_v: float, max_v: float) -> float:
    if max_v <= min_v:
        return 50.0
    pct = (value - min_v) / (max_v - min_v)
    return float(np.clip(pct * 100.0, 0.0, 100.0))


def odds_bucket(odds: float) -> str:
    try:
        odds = float(odds)
    except Exception:
        return "unknown"
    if odds <= -200:
        return "fav_heavy"
    if -199 <= odds <= -121:
        return "fav_std"
    if -120 <= odds <= 100:
        return "coinflip"
    if 101 <= odds <= 150:
        return "dog_live"
    return "dog_long"


def consensus_bucket(consensus_count: int) -> str:
    try:
        c = int(consensus_count)
    except Exception:
        return "unknown"
    if c >= 5:
        return "5of5"
    if c == 4:
        return "4of5"
    if c == 3:
        return "3of5"
    return "lt3"


def kelly_fraction(win_prob: float, odds: float) -> float:
    dec = american_to_decimal(odds)
    if np.isnan(dec):
        return 0.0
    b = dec - 1.0
    p = float(win_prob)
    q = 1.0 - p
    if b <= 0:
        return 0.0
    raw = (b * p - q) / b
    return max(0.0, raw)


def clv_from_odds(bet_odds: float, closing_odds: float) -> float:
    try:
        return (american_to_implied_prob(closing_odds) - american_to_implied_prob(bet_odds)) * 100.0
    except Exception:
        return 0.0


def format_selection(market: str, selection: str, point) -> str:
    try:
        if pd.notna(point):
            if market == "spreads":
                return f"{selection} {float(point):+g}"
            if market == "totals":
                return f"{selection} {float(point):g}"
    except Exception:
        pass
    return str(selection)


def row_key(r: pd.Series) -> str:
    point = "" if pd.isna(r.get("point", np.nan)) else str(r.get("point"))
    return " | ".join([
        str(r.get("event_id", "")),
        str(r.get("market", "")),
        str(r.get("selection", "")),
        point,
        str(r.get("book", "")),
    ])


def market_group_key(r: pd.Series) -> str:
    point = "" if pd.isna(r.get("point", np.nan)) else str(r.get("point"))
    return " | ".join([
        str(r.get("event_id", "")),
        str(r.get("market", "")),
        str(r.get("selection", "")),
        point,
    ])


# ------------------------------------------------------------
# Defaults
# ------------------------------------------------------------
def default_bet_log() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "date", "sport", "game", "market", "selection", "point", "book",
        "odds", "prev_odds", "consensus_price", "consensus_count",
        "line_movement", "sharp_score", "inefficiency_score", "edge_pct",
        "final_score", "adaptive_tier", "recommended_units", "result",
        "closing_odds", "clv"
    ])


def default_profile() -> pd.DataFrame:
    rows = []
    for market in ["moneyline", "spreads", "totals"]:
        for ob in ["fav_heavy", "fav_std", "coinflip", "dog_live", "dog_long"]:
            for cb in ["5of5", "4of5", "3of5", "lt3"]:
                rows.append({
                    "market": market,
                    "odds_bucket": ob,
                    "consensus_bucket": cb,
                    "bets": 0,
                    "wins": 0,
                    "roi_units": 0.0,
                    "weight": 1.0,
                })
    return pd.DataFrame(rows)


def default_snapshot() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "snapshot_time", "event_id", "sport", "game", "market", "selection",
        "point", "book", "odds", "commence_time"
    ])


def fallback_live_rows() -> pd.DataFrame:
    rows = [
        ["evt1", "basketball_nba", "Warriors vs Lakers", "2026-03-22T23:00:00Z", "moneyline", "Warriors", np.nan, "DraftKings", -118],
        ["evt1", "basketball_nba", "Warriors vs Lakers", "2026-03-22T23:00:00Z", "moneyline", "Warriors", np.nan, "FanDuel", -110],
        ["evt1", "basketball_nba", "Warriors vs Lakers", "2026-03-22T23:00:00Z", "moneyline", "Warriors", np.nan, "Caesars", -121],
        ["evt1", "basketball_nba", "Warriors vs Lakers", "2026-03-22T23:00:00Z", "moneyline", "Lakers", np.nan, "DraftKings", 104],
        ["evt1", "basketball_nba", "Warriors vs Lakers", "2026-03-22T23:00:00Z", "moneyline", "Lakers", np.nan, "FanDuel", 100],
        ["evt1", "basketball_nba", "Warriors vs Lakers", "2026-03-22T23:00:00Z", "moneyline", "Lakers", np.nan, "Caesars", 110],
        ["evt1", "basketball_nba", "Warriors vs Lakers", "2026-03-22T23:00:00Z", "spreads", "Warriors", -3.5, "DraftKings", -112],
        ["evt1", "basketball_nba", "Warriors vs Lakers", "2026-03-22T23:00:00Z", "spreads", "Warriors", -3.5, "FanDuel", -105],
        ["evt1", "basketball_nba", "Warriors vs Lakers", "2026-03-22T23:00:00Z", "spreads", "Warriors", -3.5, "Caesars", -110],
        ["evt1", "basketball_nba", "Warriors vs Lakers", "2026-03-22T23:00:00Z", "spreads", "Lakers", 3.5, "DraftKings", -108],
        ["evt1", "basketball_nba", "Warriors vs Lakers", "2026-03-22T23:00:00Z", "spreads", "Lakers", 3.5, "FanDuel", -115],
        ["evt1", "basketball_nba", "Warriors vs Lakers", "2026-03-22T23:00:00Z", "spreads", "Lakers", 3.5, "Caesars", -110],
        ["evt1", "basketball_nba", "Warriors vs Lakers", "2026-03-22T23:00:00Z", "totals", "Over", 229.5, "DraftKings", -102],
        ["evt1", "basketball_nba", "Warriors vs Lakers", "2026-03-22T23:00:00Z", "totals", "Over", 229.5, "FanDuel", -110],
        ["evt1", "basketball_nba", "Warriors vs Lakers", "2026-03-22T23:00:00Z", "totals", "Over", 229.5, "Caesars", -108],
        ["evt1", "basketball_nba", "Warriors vs Lakers", "2026-03-22T23:00:00Z", "totals", "Under", 229.5, "DraftKings", -118],
        ["evt1", "basketball_nba", "Warriors vs Lakers", "2026-03-22T23:00:00Z", "totals", "Under", 229.5, "FanDuel", -110],
        ["evt1", "basketball_nba", "Warriors vs Lakers", "2026-03-22T23:00:00Z", "totals", "Under", 229.5, "Caesars", -112],

        ["evt2", "icehockey_nhl", "Panthers vs Leafs", "2026-03-22T23:30:00Z", "moneyline", "Panthers", np.nan, "DraftKings", -135],
        ["evt2", "icehockey_nhl", "Panthers vs Leafs", "2026-03-22T23:30:00Z", "moneyline", "Panthers", np.nan, "FanDuel", -128],
        ["evt2", "icehockey_nhl", "Panthers vs Leafs", "2026-03-22T23:30:00Z", "moneyline", "Panthers", np.nan, "Caesars", -140],
        ["evt2", "icehockey_nhl", "Panthers vs Leafs", "2026-03-22T23:30:00Z", "moneyline", "Leafs", np.nan, "DraftKings", 118],
        ["evt2", "icehockey_nhl", "Panthers vs Leafs", "2026-03-22T23:30:00Z", "moneyline", "Leafs", np.nan, "FanDuel", 112],
        ["evt2", "icehockey_nhl", "Panthers vs Leafs", "2026-03-22T23:30:00Z", "moneyline", "Leafs", np.nan, "Caesars", 124],
        ["evt2", "icehockey_nhl", "Panthers vs Leafs", "2026-03-22T23:30:00Z", "totals", "Under", 6.5, "DraftKings", 105],
        ["evt2", "icehockey_nhl", "Panthers vs Leafs", "2026-03-22T23:30:00Z", "totals", "Under", 6.5, "FanDuel", 100],
        ["evt2", "icehockey_nhl", "Panthers vs Leafs", "2026-03-22T23:30:00Z", "totals", "Under", 6.5, "Caesars", -102],
        ["evt2", "icehockey_nhl", "Panthers vs Leafs", "2026-03-22T23:30:00Z", "totals", "Over", 6.5, "DraftKings", -125],
        ["evt2", "icehockey_nhl", "Panthers vs Leafs", "2026-03-22T23:30:00Z", "totals", "Over", 6.5, "FanDuel", -120],
        ["evt2", "icehockey_nhl", "Panthers vs Leafs", "2026-03-22T23:30:00Z", "totals", "Over", 6.5, "Caesars", -118],

        ["evt3", "soccer_epl", "Arsenal vs Spurs", "2026-03-23T12:30:00Z", "moneyline", "Arsenal", np.nan, "DraftKings", 126],
        ["evt3", "soccer_epl", "Arsenal vs Spurs", "2026-03-23T12:30:00Z", "moneyline", "Arsenal", np.nan, "FanDuel", 118],
        ["evt3", "soccer_epl", "Arsenal vs Spurs", "2026-03-23T12:30:00Z", "moneyline", "Arsenal", np.nan, "Caesars", 130],
    ]
    return pd.DataFrame(rows, columns=[
        "event_id", "sport", "game", "commence_time", "market",
        "selection", "point", "book", "odds"
    ])


# ------------------------------------------------------------
# API
# ------------------------------------------------------------
SPORT_OPTIONS = {
    "NBA": "basketball_nba",
    "NHL": "icehockey_nhl",
    "NFL": "americanfootball_nfl",
    "MLB": "baseball_mlb",
    "EPL": "soccer_epl",
}


def fetch_odds_from_the_odds_api(
    api_key: str,
    sport_key: str,
    regions: str,
    markets: str,
    bookmakers: Optional[str] = None,
) -> Tuple[pd.DataFrame, str]:
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
    params = {
        "apiKey": api_key,
        "regions": regions,
        "markets": markets,
        "oddsFormat": "american",
        "dateFormat": "iso",
    }
    if bookmakers:
        params["bookmakers"] = bookmakers

    resp = requests.get(url, params=params, timeout=25)
    resp.raise_for_status()
    data = resp.json()

    rows: List[Dict] = []
    for event in data:
        event_id = event.get("id", "")
        commence_time = event.get("commence_time", "")
        home_team = event.get("home_team", "")
        away_team = event.get("away_team", "")
        game = f"{away_team} vs {home_team}" if away_team and home_team else event_id

        for bookmaker in event.get("bookmakers", []):
            book_title = bookmaker.get("title", bookmaker.get("key", "Unknown"))
            for market in bookmaker.get("markets", []):
                market_key = market.get("key", "")
                if market_key == "h2h":
                    mkt_name = "moneyline"
                elif market_key == "spreads":
                    mkt_name = "spreads"
                elif market_key == "totals":
                    mkt_name = "totals"
                else:
                    continue

                for outcome in market.get("outcomes", []):
                    rows.append({
                        "event_id": event_id,
                        "sport": sport_key,
                        "game": game,
                        "commence_time": commence_time,
                        "market": mkt_name,
                        "selection": outcome.get("name", ""),
                        "point": outcome.get("point", np.nan),
                        "book": book_title,
                        "odds": outcome.get("price", np.nan),
                        "book_last_update": bookmaker.get("last_update", ""),
                    })
    return pd.DataFrame(rows), resp.headers.get("x-requests-remaining", "")


# ------------------------------------------------------------
# Snapshot / movement
# ------------------------------------------------------------
def attach_previous_snapshot(current_df: pd.DataFrame, snapshot_df: pd.DataFrame) -> pd.DataFrame:
    df = current_df.copy()
    if df.empty:
        df["prev_odds"] = np.nan
        df["line_movement"] = 0.0
        return df

    df["row_key"] = df.apply(row_key, axis=1)
    prev = snapshot_df.copy()
    if prev.empty:
        df["prev_odds"] = np.nan
        df["line_movement"] = 0.0
        return df.drop(columns=["row_key"], errors="ignore")

    prev["row_key"] = (
        prev["event_id"].astype(str) + " | " + prev["market"].astype(str) + " | " +
        prev["selection"].astype(str) + " | " + prev["point"].astype(str) + " | " +
        prev["book"].astype(str)
    )
    prev = prev.sort_values("snapshot_time").drop_duplicates("row_key", keep="last")
    prev = prev[["row_key", "odds"]].rename(columns={"odds": "prev_odds"})

    df = df.merge(prev, how="left", on="row_key")
    df["prev_odds"] = pd.to_numeric(df["prev_odds"], errors="coerce")
    df["odds"] = pd.to_numeric(df["odds"], errors="coerce")
    df["line_movement"] = df["prev_odds"] - df["odds"]
    return df.drop(columns=["row_key"], errors="ignore")


def update_snapshot_store(current_df: pd.DataFrame, snapshot_df: pd.DataFrame) -> pd.DataFrame:
    now = pd.Timestamp.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    add = current_df[["event_id", "sport", "game", "market", "selection", "point", "book", "odds", "commence_time"]].copy()
    add["snapshot_time"] = now
    add = add[["snapshot_time", "event_id", "sport", "game", "market", "selection", "point", "book", "odds", "commence_time"]]
    out = pd.concat([snapshot_df, add], ignore_index=True)
    if len(out) > 7000:
        out = out.tail(7000).copy()
    return out


# ------------------------------------------------------------
# Consensus / learning
# ------------------------------------------------------------
def attach_market_consensus(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if out.empty:
        out["consensus_price"] = np.nan
        out["consensus_count"] = 0
        out["best_price_flag"] = False
        out["disagreement_abs"] = 0.0
        return out

    out["group_key"] = out.apply(market_group_key, axis=1)
    grouped = (
        out.groupby("group_key", dropna=False)
        .agg(
            consensus_price=("odds", "median"),
            consensus_count=("odds", "size"),
            price_std=("odds", lambda s: float(pd.Series(s).std()) if len(s) > 1 else 0.0),
        )
        .reset_index()
    )
    out = out.merge(grouped, how="left", on="group_key")
    out["disagreement_abs"] = (out["odds"] - out["consensus_price"]).abs()
    out["best_price_flag"] = out.groupby("group_key")["odds"].transform("max") == out["odds"]
    return out.drop(columns=["group_key"], errors="ignore")


def update_profile_from_bet_log(bet_log: pd.DataFrame, profile: pd.DataFrame) -> pd.DataFrame:
    prof = profile.copy()
    settled = bet_log[bet_log["result"].isin(["win", "loss"])].copy()
    if settled.empty:
        return prof

    settled["odds_bucket"] = settled["odds"].apply(odds_bucket)
    settled["consensus_bucket"] = settled["consensus_count"].apply(consensus_bucket)

    def pnl_units(r):
        if r["result"] == "win":
            dec = american_to_decimal(r["odds"])
            return (dec - 1.0) if not np.isnan(dec) else 0.0
        if r["result"] == "loss":
            return -1.0
        return 0.0

    settled["roi_units_single"] = settled.apply(pnl_units, axis=1)

    grouped = (
        settled.groupby(["market", "odds_bucket", "consensus_bucket"], dropna=False)
        .agg(
            bets=("result", "size"),
            wins=("result", lambda s: (s == "win").sum()),
            roi_units=("roi_units_single", "sum"),
        )
        .reset_index()
    )

    merged = prof.drop(columns=["bets", "wins", "roi_units", "weight"], errors="ignore").merge(
        grouped,
        on=["market", "odds_bucket", "consensus_bucket"],
        how="left",
    )
    merged["bets"] = merged["bets"].fillna(0).astype(int)
    merged["wins"] = merged["wins"].fillna(0).astype(int)
    merged["roi_units"] = merged["roi_units"].fillna(0.0)

    weights = []
    for _, r in merged.iterrows():
        bets = int(r["bets"])
        wins = int(r["wins"])
        roi = float(r["roi_units"])
        if bets < 5:
            weight = 1.0
        else:
            wr = wins / bets if bets else 0.5
            roi_per = roi / bets if bets else 0.0
            weight = 1.0 + (wr - 0.5) * 1.1 + roi_per * 0.8
            weight = float(np.clip(weight, 0.70, 1.35))
        weights.append(weight)
    merged["weight"] = weights
    return merged


def attach_profile_weight(df: pd.DataFrame, profile: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["odds_bucket"] = out["odds"].apply(odds_bucket)
    out["consensus_bucket"] = out["consensus_count"].apply(consensus_bucket)
    small = profile[["market", "odds_bucket", "consensus_bucket", "weight"]].copy()
    out = out.merge(small, how="left", on=["market", "odds_bucket", "consensus_bucket"])
    out["weight"] = out["weight"].fillna(1.0)
    return out


# ------------------------------------------------------------
# Adaptive engine
# ------------------------------------------------------------
def compute_sharp_score(row: pd.Series) -> float:
    try:
        current_odds = float(row.get("odds", np.nan))
        prev_odds = float(row.get("prev_odds", np.nan))
        consensus_price = float(row.get("consensus_price", np.nan))
        consensus_count = float(row.get("consensus_count", 1))
        disagreement_abs = float(row.get("disagreement_abs", 0.0))
    except Exception:
        return 50.0

    movement = 0.0 if np.isnan(prev_odds) else (prev_odds - current_odds)
    movement_score = normalize_0_100(abs(movement), 0, 35) * 0.34
    direction_bonus = 18.0 if movement > 0 else 0.0

    # Deviation from consensus plus best-price value can identify inefficiency.
    # Smaller disagreement helps "sharp confirmation"; bigger disagreement helps inefficiency.
    consensus_alignment = 100 - normalize_0_100(abs(current_odds - consensus_price), 0, 35)
    agreement_component = consensus_alignment * 0.16
    depth_component = normalize_0_100(consensus_count, 1, 10) * 0.14

    # disagreement boost if movement is favorable and this price is still attractive
    disagreement_boost = 0.0
    if movement > 0 and disagreement_abs >= 8:
        disagreement_boost = 8.0

    raw = 24 + movement_score + direction_bonus + agreement_component + depth_component + disagreement_boost
    return float(np.clip(raw, 0, 100))


def compute_market_inefficiency(row: pd.Series) -> Tuple[float, float]:
    try:
        price = float(row.get("odds", np.nan))
        consensus = float(row.get("consensus_price", np.nan))
        disagreement_abs = float(row.get("disagreement_abs", 0.0))
        best_flag = bool(row.get("best_price_flag", False))
    except Exception:
        return 0.0, 0.0

    p_book = american_to_implied_prob(price)
    p_cons = american_to_implied_prob(consensus)
    if np.isnan(p_book) or np.isnan(p_cons):
        return 0.0, 0.0

    edge_pct = (p_cons - p_book) * 100.0
    best_bonus = 10 if best_flag else 0
    score = np.clip(abs(edge_pct) * 14.0 + disagreement_abs * 0.8 + best_bonus, 0.0, 100.0)
    return float(score), float(edge_pct)


def compute_dynamic_thresholds(
    scored_df: pd.DataFrame,
    base_min_books: int,
    base_min_sharp: float,
    base_min_edge: float,
    base_min_score: float,
) -> Dict[str, float]:
    live_rows = len(scored_df)
    unique_games = int(scored_df["event_id"].nunique()) if ("event_id" in scored_df.columns and not scored_df.empty) else 0
    avg_consensus = float(scored_df["consensus_count"].mean()) if not scored_df.empty else float(base_min_books)
    avg_disagreement = float(scored_df["disagreement_abs"].mean()) if ("disagreement_abs" in scored_df.columns and not scored_df.empty) else 0.0

    # More games = more opportunities, keep thresholds firmer.
    # Fewer games = loosen a bit so the user still gets actionable watchlist tiers.
    loosen = 0.0
    if live_rows <= 20:
        loosen += 4.0
    if unique_games <= 2:
        loosen += 3.0
    if avg_disagreement >= 8:
        loosen += 2.5

    min_books = max(2, int(round(base_min_books - (1 if avg_consensus < base_min_books else 0))))
    min_sharp = max(50.0, base_min_sharp - loosen)
    min_edge = max(0.5, base_min_edge - loosen * 0.18)
    min_score = max(62.0, base_min_score - loosen)

    return {
        "min_books": float(min_books),
        "min_sharp": float(min_sharp),
        "min_edge": float(min_edge),
        "min_score": float(min_score),
        "live_rows": float(live_rows),
        "unique_games": float(unique_games),
        "avg_consensus": float(avg_consensus),
        "avg_disagreement": float(avg_disagreement),
    }


def score_live_candidates(df: pd.DataFrame, bankroll: float, max_units: float) -> pd.DataFrame:
    out = df.copy()
    sharp_scores = []
    ineff_scores = []
    edge_pcts = []
    final_scores = []
    units = []
    reasons = []

    for _, r in out.iterrows():
        sharp = compute_sharp_score(r)
        ineff, edge_pct = compute_market_inefficiency(r)
        weight = float(r.get("weight", 1.0))
        consensus_count = int(r.get("consensus_count", 1))
        movement = float(r.get("line_movement", 0.0))
        best_flag = bool(r.get("best_price_flag", False))
        disagreement_abs = float(r.get("disagreement_abs", 0.0))

        market_prob = american_to_implied_prob(float(r.get("consensus_price", r.get("odds", -110))))
        own_prob = market_prob + max(edge_pct, 0) / 100.0

        consensus_bonus = {5: 13, 4: 9, 3: 5}.get(consensus_count, 0)
        best_bonus = 9 if best_flag else 0
        movement_bonus = np.clip(abs(movement) * 0.45, 0, 8)
        disagreement_bonus = np.clip(disagreement_abs * 0.30, 0, 8)

        raw = (
            sharp * 0.33 +
            ineff * 0.29 +
            weight * 18.0 +
            consensus_bonus +
            best_bonus +
            movement_bonus +
            disagreement_bonus
        )
        final_score = float(np.clip(raw, 0, 100))

        kf = kelly_fraction(min(max(own_prob, 0.01), 0.99), float(r.get("odds", -110)))
        recommended_units = bankroll * kf * 0.22 / 100.0
        recommended_units = float(np.clip(recommended_units, 0, max_units))

        rb = []
        if best_flag:
            rb.append("best market price")
        if consensus_count >= 4:
            rb.append(f"{consensus_count}/book agreement")
        if sharp >= 70:
            rb.append("strong movement")
        if disagreement_abs >= 8:
            rb.append("book disagreement")
        if edge_pct >= 1.5:
            rb.append(f"+{edge_pct:.1f}% edge")
        if not rb:
            rb.append("watchlist")

        sharp_scores.append(round(sharp, 1))
        ineff_scores.append(round(ineff, 1))
        edge_pcts.append(round(edge_pct, 2))
        final_scores.append(round(final_score, 1))
        units.append(round(recommended_units, 2))
        reasons.append(" • ".join(rb))

    out["sharp_score"] = sharp_scores
    out["inefficiency_score"] = ineff_scores
    out["edge_pct"] = edge_pcts
    out["final_score"] = final_scores
    out["recommended_units"] = units
    out["decision_reason"] = reasons
    return out


def assign_adaptive_tier(row: pd.Series, thresholds: Dict[str, float]) -> str:
    score = float(row.get("final_score", 0))
    edge = float(row.get("edge_pct", 0))
    sharp = float(row.get("sharp_score", 0))
    books = int(row.get("consensus_count", 0))

    # Adaptive tiers use dynamic thresholds as center points.
    tier_a_score = max(82, thresholds["min_score"] + 10)
    tier_b_score = max(75, thresholds["min_score"] + 3)
    tier_c_score = max(68, thresholds["min_score"] - 4)

    tier_a_edge = max(3.5, thresholds["min_edge"] + 1.5)
    tier_b_edge = max(2.0, thresholds["min_edge"] + 0.5)
    tier_c_edge = max(1.0, thresholds["min_edge"] - 0.5)

    if score >= tier_a_score and edge >= tier_a_edge and sharp >= max(72, thresholds["min_sharp"] + 6) and books >= max(4, int(thresholds["min_books"])):
        return "A"
    if score >= tier_b_score and edge >= tier_b_edge and sharp >= max(62, thresholds["min_sharp"] - 2) and books >= int(thresholds["min_books"]):
        return "B"
    if score >= tier_c_score and edge >= tier_c_edge and sharp >= max(56, thresholds["min_sharp"] - 8):
        return "C"
    return "Watch"


def apply_adaptive_filter(df: pd.DataFrame, thresholds: Dict[str, float]) -> pd.DataFrame:
    out = df.copy()
    out["adaptive_tier"] = out.apply(lambda r: assign_adaptive_tier(r, thresholds), axis=1)
    out["auto_qualified"] = out["adaptive_tier"].isin(["A", "B", "C"])
    return out


# ------------------------------------------------------------
# Load session state
# ------------------------------------------------------------
if "bet_log_v26" not in st.session_state:
    st.session_state.bet_log_v26 = safe_read_csv(BET_LOG_PATH, default_bet_log())
if "profile_v26" not in st.session_state:
    st.session_state.profile_v26 = safe_read_csv(PROFILE_PATH, default_profile())
if "snapshot_v26" not in st.session_state:
    st.session_state.snapshot_v26 = safe_read_csv(SNAPSHOT_PATH, default_snapshot())
if "current_live_df_v26" not in st.session_state:
    st.session_state.current_live_df_v26 = fallback_live_rows()

bet_log = st.session_state.bet_log_v26.copy()
profile = st.session_state.profile_v26.copy()
snapshot_df = st.session_state.snapshot_v26.copy()


# ------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------
st.sidebar.header("⚙️ Adaptive Controls")

api_key_default = os.getenv("ODDS_API_KEY", "")
api_key = st.sidebar.text_input("Odds API Key", value=api_key_default, type="password")
sport_label = st.sidebar.selectbox("Sport", list(SPORT_OPTIONS.keys()), index=0)
sport_key = SPORT_OPTIONS[sport_label]

regions = st.sidebar.text_input("Regions", value="us")
markets_list = st.sidebar.multiselect("Markets", ["h2h", "spreads", "totals"], default=["h2h", "spreads", "totals"])
bookmakers = st.sidebar.text_input("Specific bookmakers (optional)", value="")

bankroll = st.sidebar.number_input("Bankroll ($)", min_value=100, value=1000, step=100)
max_units = st.sidebar.number_input("Max Units", min_value=0.25, value=2.0, step=0.25)

base_min_books = st.sidebar.slider("Base Min Book Consensus", 2, 10, 3)
base_min_sharp = st.sidebar.slider("Base Min Sharp Score", 0, 100, 62)
base_min_edge = st.sidebar.slider("Base Min Edge %", 0.0, 10.0, 1.5, 0.5)
base_min_score = st.sidebar.slider("Base Min Final Score", 0, 100, 70)

auto_save = st.sidebar.checkbox("Auto-save tiered plays to bet log", value=False)
show_watchlist = st.sidebar.checkbox("Show Watchlist plays", value=True)

auto_refresh = st.sidebar.checkbox("Auto refresh every 45s", value=False)
fetch_live = st.sidebar.button("📡 Fetch / Refresh Live Odds", use_container_width=True)
refresh_learning = st.sidebar.button("🧠 Refresh Learning Profile", use_container_width=True)
reset_snapshot = st.sidebar.button("🧹 Reset Snapshot History", use_container_width=True)

if refresh_learning:
    profile = update_profile_from_bet_log(bet_log, profile)
    st.session_state.profile_v26 = profile.copy()
    safe_save_csv(profile, PROFILE_PATH)
    st.sidebar.success("Learning profile refreshed")

if reset_snapshot:
    snapshot_df = default_snapshot()
    st.session_state.snapshot_v26 = snapshot_df.copy()
    safe_save_csv(snapshot_df, SNAPSHOT_PATH)
    st.sidebar.success("Snapshot history reset")


# ------------------------------------------------------------
# Data acquisition
# ------------------------------------------------------------
live_status = ""
requests_remaining = ""

if fetch_live or auto_refresh:
    if api_key.strip():
        try:
            live_df, requests_remaining = fetch_odds_from_the_odds_api(
                api_key=api_key.strip(),
                sport_key=sport_key,
                regions=regions.strip(),
                markets=",".join(markets_list),
                bookmakers=bookmakers.strip() or None,
            )
            if live_df.empty:
                live_status = "Live fetch succeeded, but no rows were returned."
            else:
                live_status = "Live odds fetched successfully."
            st.session_state.current_live_df_v26 = live_df.copy()
        except Exception as e:
            live_status = f"Live fetch failed. Using fallback data. Error: {e}"
            st.session_state.current_live_df_v26 = fallback_live_rows()
    else:
        live_status = "No API key provided. Using fallback live test dataset."
        st.session_state.current_live_df_v26 = fallback_live_rows()

current_live_df = st.session_state.current_live_df_v26.copy()
current_live_df = current_live_df[current_live_df["sport"] == sport_key].copy()

if current_live_df.empty:
    current_live_df = fallback_live_rows()
    current_live_df = current_live_df[current_live_df["sport"] == sport_key].copy()

if live_status:
    st.info(live_status)
if requests_remaining:
    st.caption(f"API requests remaining: {requests_remaining}")


# ------------------------------------------------------------
# Process / score
# ------------------------------------------------------------
profile = update_profile_from_bet_log(bet_log, profile)
st.session_state.profile_v26 = profile.copy()
safe_save_csv(profile, PROFILE_PATH)

current_live_df = attach_previous_snapshot(current_live_df, snapshot_df)
current_live_df = attach_market_consensus(current_live_df)
current_live_df = attach_profile_weight(current_live_df, profile)
scored_df = score_live_candidates(current_live_df, bankroll=bankroll, max_units=max_units)

adaptive_thresholds = compute_dynamic_thresholds(
    scored_df=scored_df,
    base_min_books=base_min_books,
    base_min_sharp=base_min_sharp,
    base_min_edge=base_min_edge,
    base_min_score=base_min_score,
)

scored_df = apply_adaptive_filter(scored_df, adaptive_thresholds)
scored_df = scored_df.sort_values(
    ["auto_qualified", "adaptive_tier", "final_score", "edge_pct"],
    ascending=[False, True, False, False]
).reset_index(drop=True)

qualified_df = scored_df[scored_df["auto_qualified"]].copy()
watch_df = scored_df[scored_df["adaptive_tier"] == "Watch"].copy()

snapshot_df = update_snapshot_store(current_live_df, snapshot_df)
st.session_state.snapshot_v26 = snapshot_df.copy()
safe_save_csv(snapshot_df, SNAPSHOT_PATH)


# ------------------------------------------------------------
# KPI block
# ------------------------------------------------------------
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Live Rows", len(scored_df))
k2.metric("Tiered Plays", len(qualified_df))
k3.metric("Avg Tiered Score", f"{qualified_df['final_score'].mean():.1f}" if len(qualified_df) else "—")
k4.metric("Avg Tiered Edge", f"{qualified_df['edge_pct'].mean():.2f}%" if len(qualified_df) else "—")
k5.metric("Watchlist", len(watch_df))

with st.expander("🧠 Adaptive Thresholds In Use", expanded=False):
    st.write({
        "min_books": int(adaptive_thresholds["min_books"]),
        "min_sharp": round(adaptive_thresholds["min_sharp"], 1),
        "min_edge": round(adaptive_thresholds["min_edge"], 2),
        "min_score": round(adaptive_thresholds["min_score"], 1),
        "live_rows": int(adaptive_thresholds["live_rows"]),
        "unique_games": int(adaptive_thresholds["unique_games"]),
        "avg_consensus": round(adaptive_thresholds["avg_consensus"], 2),
        "avg_disagreement": round(adaptive_thresholds["avg_disagreement"], 2),
    })


# ------------------------------------------------------------
# Tier summaries
# ------------------------------------------------------------
tier_counts = scored_df["adaptive_tier"].value_counts().to_dict()
a_cnt = tier_counts.get("A", 0)
b_cnt = tier_counts.get("B", 0)
c_cnt = tier_counts.get("C", 0)
w_cnt = tier_counts.get("Watch", 0)

s1, s2, s3, s4 = st.columns(4)
s1.metric("Tier A", a_cnt)
s2.metric("Tier B", b_cnt)
s3.metric("Tier C", c_cnt)
s4.metric("Watch", w_cnt)


# ------------------------------------------------------------
# Top plays
# ------------------------------------------------------------
st.subheader("🎯 V26 Adaptive Top Plays")

display_df = qualified_df.copy()
if display_df.empty and show_watchlist:
    display_df = scored_df.head(5).copy()
    st.warning("No A/B/C plays right now. Showing best live watchlist opportunities instead.")

if display_df.empty:
    st.warning("No live rows available.")
else:
    for i, row in display_df.head(8).iterrows():
        with st.container(border=True):
            title = format_selection(row["market"], row["selection"], row.get("point", np.nan))
            tier = row.get("adaptive_tier", "Watch")
            tier_emoji = {"A": "🟢", "B": "🟡", "C": "🔵", "Watch": "⚪"}.get(tier, "⚪")
            st.markdown(f"### #{i+1} {tier_emoji} Tier {tier} — {title}")

            a, b, c, d = st.columns(4)
            a.metric("Game", row["game"])
            b.metric("Book", row["book"])
            c.metric("Odds", f"{int(row['odds'])}" if pd.notna(row["odds"]) else "—")
            d.metric("Units", f"{row['recommended_units']:.2f}u")

            e, f, g, h = st.columns(4)
            e.metric("Final Score", f"{row['final_score']:.1f}")
            f.metric("Sharp Score", f"{row['sharp_score']:.1f}")
            g.metric("Edge", f"{row['edge_pct']:.2f}%")
            h.metric("Consensus", f"{int(row['consensus_count'])} books")

            st.caption(f"Reason: {row['decision_reason']}")


# ------------------------------------------------------------
# Tables
# ------------------------------------------------------------
st.subheader("✅ Adaptive Plays")
play_cols = [
    "adaptive_tier", "sport", "game", "market", "selection", "point", "book", "odds",
    "prev_odds", "consensus_price", "consensus_count", "line_movement",
    "sharp_score", "inefficiency_score", "edge_pct", "final_score",
    "recommended_units", "decision_reason"
]
st.dataframe(qualified_df[play_cols], use_container_width=True, hide_index=True)

if show_watchlist:
    with st.expander("👀 Watchlist Plays", expanded=False):
        st.dataframe(watch_df[play_cols], use_container_width=True, hide_index=True)

with st.expander("📊 View All Scored Live Rows", expanded=False):
    st.dataframe(scored_df[play_cols + ["auto_qualified"]], use_container_width=True, hide_index=True)

with st.expander("🛰️ Raw Live Rows", expanded=False):
    st.dataframe(current_live_df, use_container_width=True, hide_index=True)


# ------------------------------------------------------------
# Auto-save
# ------------------------------------------------------------
if auto_save and not qualified_df.empty:
    existing_keys = set(
        (
            bet_log["game"].astype(str) + " | " + bet_log["market"].astype(str) + " | " +
            bet_log["selection"].astype(str) + " | " + bet_log["point"].astype(str) + " | " +
            bet_log["book"].astype(str) + " | " + bet_log["odds"].astype(str)
        ).tolist()
    )

    add_rows = []
    for _, r in qualified_df.iterrows():
        key = " | ".join([
            str(r["game"]), str(r["market"]), str(r["selection"]), str(r["point"]),
            str(r["book"]), str(r["odds"])
        ])
        if key not in existing_keys:
            add_rows.append({
                "date": pd.Timestamp.now().strftime("%Y-%m-%d"),
                "sport": r["sport"],
                "game": r["game"],
                "market": r["market"],
                "selection": r["selection"],
                "point": r["point"],
                "book": r["book"],
                "odds": r["odds"],
                "prev_odds": r["prev_odds"],
                "consensus_price": r["consensus_price"],
                "consensus_count": r["consensus_count"],
                "line_movement": r["line_movement"],
                "sharp_score": r["sharp_score"],
                "inefficiency_score": r["inefficiency_score"],
                "edge_pct": r["edge_pct"],
                "final_score": r["final_score"],
                "adaptive_tier": r["adaptive_tier"],
                "recommended_units": r["recommended_units"],
                "result": "",
                "closing_odds": np.nan,
                "clv": np.nan,
            })

    if add_rows:
        bet_log = pd.concat([bet_log, pd.DataFrame(add_rows)], ignore_index=True)
        st.session_state.bet_log_v26 = bet_log.copy()
        safe_save_csv(bet_log, BET_LOG_PATH)
        st.success(f"Auto-saved {len(add_rows)} adaptive play(s) to the bet log.")


# ------------------------------------------------------------
# Bet log / grading
# ------------------------------------------------------------
st.subheader("📒 Bet Log + Grading")

with st.form("bet_log_form_v26"):
    c1, c2, c3 = st.columns(3)
    game = c1.text_input("Game")
    market = c2.selectbox("Market", ["moneyline", "spreads", "totals"])
    selection = c3.text_input("Selection")

    d1, d2, d3, d4 = st.columns(4)
    point = d1.number_input("Point (0 if N/A)", value=0.0, step=0.5)
    book = d2.text_input("Book", value="DraftKings")
    odds = d3.number_input("Bet Odds", value=-110)
    prev_odds = d4.number_input("Previous Odds", value=-110)

    e1, e2, e3, e4 = st.columns(4)
    consensus_price = e1.number_input("Consensus Price", value=-110)
    consensus_count = e2.slider("Consensus Count", 1, 10, 3)
    closing_odds = e3.number_input("Closing Odds", value=-110)
    result = e4.selectbox("Result", ["", "win", "loss"])

    submitted = st.form_submit_button("Add / Grade Bet")
    if submitted:
        temp = pd.Series({
            "odds": odds,
            "prev_odds": prev_odds,
            "consensus_price": consensus_price,
            "consensus_count": consensus_count,
            "disagreement_abs": abs(odds - consensus_price),
            "best_price_flag": odds >= consensus_price,
            "line_movement": prev_odds - odds,
        })
        sharp_score = compute_sharp_score(temp)
        ineff_score, edge_pct = compute_market_inefficiency(temp)

        temp_score_df = pd.DataFrame([{
            "odds": odds,
            "prev_odds": prev_odds,
            "consensus_price": consensus_price,
            "consensus_count": consensus_count,
            "disagreement_abs": abs(odds - consensus_price),
            "best_price_flag": odds >= consensus_price,
            "line_movement": prev_odds - odds,
            "weight": 1.0,
        }])
        temp_score_df = score_live_candidates(temp_score_df, bankroll=bankroll, max_units=max_units)
        final_score = float(temp_score_df.iloc[0]["final_score"])
        recommended_units = float(temp_score_df.iloc[0]["recommended_units"])

        temp_series = pd.Series({
            "final_score": final_score,
            "edge_pct": edge_pct,
            "sharp_score": sharp_score,
            "consensus_count": consensus_count,
        })
        adaptive_tier = assign_adaptive_tier(temp_series, adaptive_thresholds)
        clv = clv_from_odds(odds, closing_odds)

        add = pd.DataFrame([{
            "date": pd.Timestamp.now().strftime("%Y-%m-%d"),
            "sport": sport_key,
            "game": game,
            "market": market,
            "selection": selection,
            "point": np.nan if point == 0 else point,
            "book": book,
            "odds": odds,
            "prev_odds": prev_odds,
            "consensus_price": consensus_price,
            "consensus_count": consensus_count,
            "line_movement": prev_odds - odds,
            "sharp_score": round(sharp_score, 1),
            "inefficiency_score": round(ineff_score, 1),
            "edge_pct": round(edge_pct, 2),
            "final_score": round(final_score, 1),
            "adaptive_tier": adaptive_tier,
            "recommended_units": round(recommended_units, 2),
            "result": result,
            "closing_odds": closing_odds,
            "clv": round(clv, 2),
        }])

        bet_log = pd.concat([bet_log, add], ignore_index=True)
        st.session_state.bet_log_v26 = bet_log.copy()
        safe_save_csv(bet_log, BET_LOG_PATH)
        st.success("Bet log updated.")

st.dataframe(bet_log, use_container_width=True, hide_index=True)

settled = bet_log[bet_log["result"].isin(["win", "loss"])].copy()
wins = int((settled["result"] == "win").sum())
losses = int((settled["result"] == "loss").sum())
win_rate = (wins / len(settled) * 100.0) if len(settled) else 0.0

def pnl_units(r):
    if r["result"] == "win":
        dec = american_to_decimal(r["odds"])
        return (dec - 1.0) if not np.isnan(dec) else 0.0
    if r["result"] == "loss":
        return -1.0
    return 0.0

net_units = settled.apply(pnl_units, axis=1).sum() if len(settled) else 0.0
avg_clv = settled["clv"].mean() if len(settled) else np.nan

m1, m2, m3, m4 = st.columns(4)
m1.metric("Settled Bets", len(settled))
m2.metric("Win Rate", f"{win_rate:.1f}%")
m3.metric("Net Units", f"{net_units:.2f}u")
m4.metric("Avg CLV", f"{avg_clv:.2f}" if len(settled) else "—")


# ------------------------------------------------------------
# Learning profile
# ------------------------------------------------------------
st.subheader("🧠 Adaptive Learning Profile")
st.dataframe(
    profile.sort_values(["market", "consensus_bucket", "odds_bucket"]).reset_index(drop=True),
    use_container_width=True,
    hide_index=True,
)

if len(settled):
    view = (
        settled.assign(
            odds_bucket=settled["odds"].apply(odds_bucket),
            consensus_bucket=settled["consensus_count"].apply(consensus_bucket),
            pnl_units=settled.apply(pnl_units, axis=1),
        )
        .groupby(["market", "adaptive_tier"], dropna=False)
        .agg(
            bets=("result", "size"),
            wins=("result", lambda s: (s == "win").sum()),
            net_units=("pnl_units", "sum"),
            avg_clv=("clv", "mean"),
        )
        .reset_index()
    )
    st.dataframe(view, use_container_width=True, hide_index=True)
else:
    st.info("Add settled bets to activate adaptive learning analytics.")


# ------------------------------------------------------------
# Export
# ------------------------------------------------------------
st.subheader("💾 Export")

x1, x2, x3 = st.columns(3)
with x1:
    st.download_button(
        "Download Bet Log CSV",
        data=bet_log.to_csv(index=False).encode("utf-8"),
        file_name="bet_log_v26.csv",
        mime="text/csv",
        use_container_width=True,
    )
with x2:
    st.download_button(
        "Download Learning Profile CSV",
        data=profile.to_csv(index=False).encode("utf-8"),
        file_name="learning_profile_v26.csv",
        mime="text/csv",
        use_container_width=True,
    )
with x3:
    st.download_button(
        "Download Snapshot CSV",
        data=snapshot_df.to_csv(index=False).encode("utf-8"),
        file_name="odds_snapshot_v26.csv",
        mime="text/csv",
        use_container_width=True,
    )

st.caption(
    "V26 Adaptive Engine adds tiered A/B/C qualification, dynamic thresholds, watchlist support, "
    "and smoother live ranking so the dashboard keeps surfacing the best current opportunities."
)

if auto_refresh:
    st.caption("Auto refresh is on. The page will rerun in about 45 seconds.")
    time.sleep(45)
    st.rerun()
