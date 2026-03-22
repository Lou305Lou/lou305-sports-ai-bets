
# streamlit_app_v25.py
# V25 Live Engine
#
# Live odds + scoring pipeline for Streamlit.
# Designed to work with The Odds API v4 if you provide an API key.
# Falls back to built-in sample live-like data if no key is provided.
#
# Features:
# - live odds fetch
# - multi-book parsing for moneyline / spreads / totals
# - market consensus price comparison
# - snapshot storage for line movement
# - sharp score using movement + market agreement
# - inefficiency score + edge estimate
# - auto-qualified top plays
# - optional auto-save to bet log
# - settled-bet learning profile
#
# Notes:
# - This version does not depend on private APIs.
# - Player props are not included in the live fetch parser here because book/market
#   coverage varies a lot by sport and provider configuration.
# - If no API key is provided, the app uses a realistic fallback dataset so you can test the UI.

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
import streamlit as st

# ------------------------------------------------------------
# App setup
# ------------------------------------------------------------
st.set_page_config(page_title="Sports Betting AI Dashboard V25 Live Engine", layout="wide")
st.title("🔥 Sports Betting AI Dashboard V25")
st.caption("Live Engine: fetch → compare books → detect movement → score → qualify → track")

DATA_DIR = Path(".")
BET_LOG_PATH = DATA_DIR / "bet_log_v25.csv"
PROFILE_PATH = DATA_DIR / "learning_profile_v25.csv"
SNAPSHOT_PATH = DATA_DIR / "odds_snapshot_v25.csv"


# ------------------------------------------------------------
# Utilities
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


def implied_prob_to_american(prob: float) -> float:
    try:
        p = float(prob)
        if p <= 0 or p >= 1:
            return np.nan
        if p >= 0.5:
            return -(p / (1 - p)) * 100.0
        return ((1 - p) / p) * 100.0
    except Exception:
        return np.nan


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


def normalize_0_100(value: float, min_v: float, max_v: float) -> float:
    if max_v <= min_v:
        return 50.0
    v = (value - min_v) / (max_v - min_v)
    return float(np.clip(v * 100.0, 0.0, 100.0))


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


def row_key(r: pd.Series) -> str:
    point = "" if pd.isna(r.get("point", np.nan)) else str(r.get("point"))
    return " | ".join([
        str(r.get("event_id", "")),
        str(r.get("market", "")),
        str(r.get("selection", "")),
        str(point),
        str(r.get("book", "")),
    ])


def market_group_key(r: pd.Series) -> str:
    point = "" if pd.isna(r.get("point", np.nan)) else str(r.get("point"))
    return " | ".join([
        str(r.get("event_id", "")),
        str(r.get("market", "")),
        str(r.get("selection", "")),
        str(point),
    ])


# ------------------------------------------------------------
# Defaults
# ------------------------------------------------------------
def default_bet_log() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "date", "sport", "game", "market", "selection", "point", "book",
        "odds", "prev_odds", "consensus_price", "consensus_count",
        "line_movement", "sharp_score", "inefficiency_score", "edge_pct",
        "final_score", "recommended_units", "result", "closing_odds", "clv"
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
    # Simulated live-like rows so the app is testable without an API key.
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
    df = pd.DataFrame(rows, columns=[
        "event_id", "sport", "game", "commence_time", "market",
        "selection", "point", "book", "odds"
    ])
    return df


# ------------------------------------------------------------
# API fetch
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
                        "market_last_update": market.get("last_update", ""),
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
        prev["event_id"].astype(str) + " | " + prev["market"].astype(str) + " | "
        + prev["selection"].astype(str) + " | " + prev["point"].astype(str) + " | "
        + prev["book"].astype(str)
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

    # Keep only latest ~5000 rows for app size sanity
    if len(out) > 5000:
        out = out.tail(5000).copy()

    return out


# ------------------------------------------------------------
# Consensus / scoring
# ------------------------------------------------------------
def attach_market_consensus(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if out.empty:
        out["consensus_price"] = np.nan
        out["consensus_count"] = 0
        out["best_price_flag"] = False
        return out

    out["group_key"] = out.apply(market_group_key, axis=1)

    grp = (
        out.groupby("group_key", dropna=False)
        .agg(
            consensus_price=("odds", "median"),
            consensus_count=("odds", "size"),
            best_dog_price=("odds", "max"),
            best_fav_price=("odds", "max"),
        )
        .reset_index()
    )

    out = out.merge(grp[["group_key", "consensus_price", "consensus_count"]], on="group_key", how="left")
    out["best_price_flag"] = out.groupby("group_key")["odds"].transform("max") == out["odds"]
    return out.drop(columns=["group_key"], errors="ignore")


def compute_sharp_score(row: pd.Series) -> float:
    # Sharp logic here is pragmatic for live odds:
    # - favorable movement from previous snapshot
    # - consensus depth
    # - price disagreement between this book and consensus
    try:
        current_odds = float(row.get("odds", np.nan))
        prev_odds = float(row.get("prev_odds", np.nan))
        consensus_price = float(row.get("consensus_price", np.nan))
        count = float(row.get("consensus_count", 1))
    except Exception:
        return 50.0

    movement = 0.0 if np.isnan(prev_odds) else (prev_odds - current_odds)
    movement_score = normalize_0_100(abs(movement), 0, 35) * 0.45
    direction_bonus = 18.0 if movement > 0 else 0.0

    market_agreement = 100 - normalize_0_100(abs(current_odds - consensus_price), 0, 40)
    agreement_component = market_agreement * 0.20
    depth_component = normalize_0_100(count, 1, 10) * 0.15

    raw = 20 + movement_score + direction_bonus + agreement_component + depth_component
    return float(np.clip(raw, 0, 100))


def compute_market_inefficiency(row: pd.Series) -> Tuple[float, float]:
    # Edge is relative to the market consensus price.
    try:
        price = float(row.get("odds", np.nan))
        consensus = float(row.get("consensus_price", np.nan))
    except Exception:
        return 0.0, 0.0

    p_book = american_to_implied_prob(price)
    p_cons = american_to_implied_prob(consensus)
    if np.isnan(p_book) or np.isnan(p_cons):
        return 0.0, 0.0

    edge_pct = (p_cons - p_book) * 100.0
    score = np.clip(abs(edge_pct) * 15.0, 0.0, 100.0)
    return float(score), float(edge_pct)


def update_profile_from_bet_log(bet_log: pd.DataFrame, profile: pd.DataFrame) -> pd.DataFrame:
    prof = profile.copy()
    settled = bet_log[bet_log["result"].isin(["win", "loss"])].copy()
    if settled.empty:
        return prof

    settled["odds_bucket"] = settled["odds"].apply(odds_bucket)
    settled["consensus_bucket"] = settled["consensus_count"].apply(consensus_bucket)

    def units_result(r):
        if r["result"] == "win":
            dec = american_to_decimal(r["odds"])
            return (dec - 1.0) if not np.isnan(dec) else 0.0
        if r["result"] == "loss":
            return -1.0
        return 0.0

    settled["roi_units_single"] = settled.apply(units_result, axis=1)

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
        grouped, on=["market", "odds_bucket", "consensus_bucket"], how="left"
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
            w = 1.0
        else:
            wr = wins / bets if bets else 0.5
            roi_per = roi / bets if bets else 0.0
            w = 1.0 + (wr - 0.5) * 1.2 + roi_per * 0.9
            w = float(np.clip(w, 0.70, 1.35))
        weights.append(w)
    merged["weight"] = weights
    return merged


def attach_profile_weight(df: pd.DataFrame, profile: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["odds_bucket"] = out["odds"].apply(odds_bucket)
    out["consensus_bucket"] = out["consensus_count"].apply(consensus_bucket)
    small = profile[["market", "odds_bucket", "consensus_bucket", "weight"]].copy()
    out = out.merge(small, on=["market", "odds_bucket", "consensus_bucket"], how="left")
    out["weight"] = out["weight"].fillna(1.0)
    return out


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
        learning_weight = float(r.get("weight", 1.0))
        consensus_count = int(r.get("consensus_count", 1))
        movement = float(r.get("line_movement", 0.0))
        best_flag = bool(r.get("best_price_flag", False))

        # Since this live engine does not yet have model projections by default,
        # we infer a cautious market-based probability advantage.
        market_prob = american_to_implied_prob(float(r.get("consensus_price", r.get("odds", -110))))
        own_prob = market_prob + max(edge_pct, 0) / 100.0

        consensus_bonus = {5: 14, 4: 9, 3: 4}.get(consensus_count, -6)
        best_price_bonus = 8 if best_flag else 0
        move_bonus = np.clip(abs(movement) * 0.5, 0, 8)

        raw = (
            sharp * 0.38
            + ineff * 0.28
            + learning_weight * 18.0
            + consensus_bonus
            + best_price_bonus
            + move_bonus
        )
        final_score = float(np.clip(raw, 0, 100))

        kf = kelly_fraction(min(max(own_prob, 0.01), 0.99), float(r.get("odds", -110)))
        recommended_units = bankroll * kf * 0.25 / 100.0
        recommended_units = float(np.clip(recommended_units, 0, max_units))

        rb = []
        if best_flag:
            rb.append("best market price")
        if consensus_count >= 4:
            rb.append(f"{consensus_count}/book agreement")
        if sharp >= 70:
            rb.append("strong movement")
        if edge_pct >= 2:
            rb.append(f"+{edge_pct:.1f}% edge")
        if not rb:
            rb.append("borderline")

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


def filter_live_auto(df: pd.DataFrame, min_books: int, min_sharp: float, min_edge: float, min_score: float) -> pd.DataFrame:
    out = df.copy()
    out["auto_qualified"] = (
        (out["consensus_count"] >= min_books)
        & (out["sharp_score"] >= min_sharp)
        & (out["edge_pct"] >= min_edge)
        & (out["final_score"] >= min_score)
        & (out["recommended_units"] > 0)
    )
    return out


def clv_from_odds(bet_odds: float, closing_odds: float) -> float:
    try:
        return (american_to_implied_prob(closing_odds) - american_to_implied_prob(bet_odds)) * 100.0
    except Exception:
        return 0.0


# ------------------------------------------------------------
# Load state
# ------------------------------------------------------------
if "bet_log_v25" not in st.session_state:
    st.session_state.bet_log_v25 = safe_read_csv(BET_LOG_PATH, default_bet_log())

if "profile_v25" not in st.session_state:
    st.session_state.profile_v25 = safe_read_csv(PROFILE_PATH, default_profile())

if "snapshot_v25" not in st.session_state:
    st.session_state.snapshot_v25 = safe_read_csv(SNAPSHOT_PATH, default_snapshot())

bet_log = st.session_state.bet_log_v25.copy()
profile = st.session_state.profile_v25.copy()
snapshot_df = st.session_state.snapshot_v25.copy()


# ------------------------------------------------------------
# Sidebar controls
# ------------------------------------------------------------
st.sidebar.header("⚙️ Live Engine Controls")

api_key_default = os.getenv("ODDS_API_KEY", "")
api_key = st.sidebar.text_input("Odds API Key", value=api_key_default, type="password")
sport_label = st.sidebar.selectbox("Sport", list(SPORT_OPTIONS.keys()), index=0)
sport_key = SPORT_OPTIONS[sport_label]

regions = st.sidebar.text_input("Regions", value="us")
markets_list = st.sidebar.multiselect("Markets", ["h2h", "spreads", "totals"], default=["h2h", "spreads", "totals"])
bookmakers = st.sidebar.text_input("Specific bookmakers (optional)", value="")
bankroll = st.sidebar.number_input("Bankroll ($)", min_value=100, value=1000, step=100)
max_units = st.sidebar.number_input("Max Units", min_value=0.25, value=2.0, step=0.25)
min_books = st.sidebar.slider("Min Book Consensus", 2, 10, 3)
min_sharp = st.sidebar.slider("Min Sharp Score", 0, 100, 62)
min_edge = st.sidebar.slider("Min Edge %", 0.0, 10.0, 1.5, 0.5)
min_score = st.sidebar.slider("Min Final Score", 0, 100, 70)
auto_save = st.sidebar.checkbox("Auto-save qualified plays to bet log", value=False)

fetch_live = st.sidebar.button("📡 Fetch Live Odds", use_container_width=True)
refresh_learning = st.sidebar.button("🧠 Refresh Learning Profile", use_container_width=True)
reset_snapshot = st.sidebar.button("🧹 Reset Snapshot History", use_container_width=True)

if reset_snapshot:
    snapshot_df = default_snapshot()
    st.session_state.snapshot_v25 = snapshot_df.copy()
    safe_save_csv(snapshot_df, SNAPSHOT_PATH)
    st.sidebar.success("Snapshot history reset")

if refresh_learning:
    profile = update_profile_from_bet_log(bet_log, profile)
    st.session_state.profile_v25 = profile.copy()
    safe_save_csv(profile, PROFILE_PATH)
    st.sidebar.success("Learning profile refreshed")


# ------------------------------------------------------------
# Live data acquisition
# ------------------------------------------------------------
live_status = ""
requests_remaining = ""

if "current_live_df_v25" not in st.session_state:
    st.session_state.current_live_df_v25 = fallback_live_rows()

if fetch_live:
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
            st.session_state.current_live_df_v25 = live_df.copy()
        except Exception as e:
            live_status = f"Live fetch failed. Using fallback data. Error: {e}"
            st.session_state.current_live_df_v25 = fallback_live_rows()
    else:
        live_status = "No API key provided. Using fallback test dataset."
        st.session_state.current_live_df_v25 = fallback_live_rows()

current_live_df = st.session_state.current_live_df_v25.copy()

# Keep sport filter aligned even when using fallback
current_live_df = current_live_df[current_live_df["sport"] == sport_key].copy()
if current_live_df.empty:
    current_live_df = fallback_live_rows()
    current_live_df = current_live_df[current_live_df["sport"] == sport_key].copy()

if live_status:
    st.info(live_status)
if requests_remaining:
    st.caption(f"API requests remaining (header): {requests_remaining}")


# ------------------------------------------------------------
# Process live rows
# ------------------------------------------------------------
current_live_df = attach_previous_snapshot(current_live_df, snapshot_df)
current_live_df = attach_market_consensus(current_live_df)
profile = update_profile_from_bet_log(bet_log, profile)
st.session_state.profile_v25 = profile.copy()
safe_save_csv(profile, PROFILE_PATH)

current_live_df = attach_profile_weight(current_live_df, profile)
scored_df = score_live_candidates(current_live_df, bankroll=bankroll, max_units=max_units)
scored_df = filter_live_auto(scored_df, min_books=min_books, min_sharp=min_sharp, min_edge=min_edge, min_score=min_score)
scored_df = scored_df.sort_values(["auto_qualified", "final_score", "edge_pct"], ascending=[False, False, False]).reset_index(drop=True)
qualified_df = scored_df[scored_df["auto_qualified"]].copy()

# Snapshot update happens after scoring so current rows can compare to the previous fetch
snapshot_df = update_snapshot_store(current_live_df, snapshot_df)
st.session_state.snapshot_v25 = snapshot_df.copy()
safe_save_csv(snapshot_df, SNAPSHOT_PATH)


# ------------------------------------------------------------
# KPIs
# ------------------------------------------------------------
k1, k2, k3, k4 = st.columns(4)
k1.metric("Live Rows", len(scored_df))
k2.metric("Qualified Plays", len(qualified_df))
k3.metric("Avg Qualified Score", f"{qualified_df['final_score'].mean():.1f}" if len(qualified_df) else "—")
k4.metric("Avg Qualified Edge", f"{qualified_df['edge_pct'].mean():.2f}%" if len(qualified_df) else "—")


# ------------------------------------------------------------
# Top plays
# ------------------------------------------------------------
st.subheader("🎯 V25 Live Top Plays")

if qualified_df.empty:
    st.warning("No live plays met the current thresholds.")
else:
    for i, row in qualified_df.head(8).iterrows():
        with st.container(border=True):
            title = row["selection"]
            if pd.notna(row.get("point", np.nan)):
                if row["market"] == "spreads":
                    title = f"{row['selection']} {row['point']:+g}"
                elif row["market"] == "totals":
                    title = f"{row['selection']} {row['point']:g}"
            st.markdown(f"### #{i+1} {title}")

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
# Qualified plays
# ------------------------------------------------------------
st.subheader("✅ Qualified Live Plays")
show_cols = [
    "sport", "game", "market", "selection", "point", "book", "odds", "prev_odds",
    "consensus_price", "consensus_count", "line_movement", "sharp_score",
    "inefficiency_score", "edge_pct", "final_score", "recommended_units", "decision_reason"
]
st.dataframe(qualified_df[show_cols], use_container_width=True, hide_index=True)

if auto_save and not qualified_df.empty:
    existing_keys = set(
        (
            bet_log["game"].astype(str) + " | " + bet_log["market"].astype(str) + " | "
            + bet_log["selection"].astype(str) + " | " + bet_log["point"].astype(str) + " | "
            + bet_log["book"].astype(str) + " | " + bet_log["odds"].astype(str)
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
                "recommended_units": r["recommended_units"],
                "result": "",
                "closing_odds": np.nan,
                "clv": np.nan,
            })

    if add_rows:
        bet_log = pd.concat([bet_log, pd.DataFrame(add_rows)], ignore_index=True)
        st.session_state.bet_log_v25 = bet_log.copy()
        safe_save_csv(bet_log, BET_LOG_PATH)
        st.success(f"Auto-saved {len(add_rows)} live play(s) to the bet log.")


with st.expander("📊 View All Live Scored Rows", expanded=False):
    st.dataframe(scored_df[show_cols + ["auto_qualified"]], use_container_width=True, hide_index=True)

with st.expander("🛰️ Raw Live Rows", expanded=False):
    st.dataframe(current_live_df, use_container_width=True, hide_index=True)


# ------------------------------------------------------------
# Bet log and grading
# ------------------------------------------------------------
st.subheader("📒 Bet Log + Grading")

with st.form("bet_log_form"):
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
        line_movement = prev_odds - odds
        sharp_score = compute_sharp_score(pd.Series({
            "odds": odds,
            "prev_odds": prev_odds,
            "consensus_price": consensus_price,
            "consensus_count": consensus_count,
        }))
        ineff, edge_pct = compute_market_inefficiency(pd.Series({
            "odds": odds,
            "consensus_price": consensus_price,
        }))
        learning_weight = 1.0
        final_score = float(np.clip(
            sharp_score * 0.40 + ineff * 0.30 + learning_weight * 18 + {5:14,4:9,3:4}.get(consensus_count, -6),
            0, 100
        ))
        market_prob = american_to_implied_prob(consensus_price)
        own_prob = market_prob + max(edge_pct, 0) / 100.0
        units = float(np.clip(bankroll * kelly_fraction(min(max(own_prob, 0.01), 0.99), odds) * 0.25 / 100.0, 0, max_units))
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
            "line_movement": line_movement,
            "sharp_score": round(sharp_score, 1),
            "inefficiency_score": round(ineff, 1),
            "edge_pct": round(edge_pct, 2),
            "final_score": round(final_score, 1),
            "recommended_units": round(units, 2),
            "result": result,
            "closing_odds": closing_odds,
            "clv": round(clv, 2),
        }])
        bet_log = pd.concat([bet_log, add], ignore_index=True)
        st.session_state.bet_log_v25 = bet_log.copy()
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
st.subheader("🧠 Live Learning Profile")
st.dataframe(profile.sort_values(["market", "consensus_bucket", "odds_bucket"]).reset_index(drop=True), use_container_width=True, hide_index=True)

if len(settled):
    view = (
        settled.assign(
            odds_bucket=settled["odds"].apply(odds_bucket),
            consensus_bucket=settled["consensus_count"].apply(consensus_bucket),
            pnl_units=settled.apply(pnl_units, axis=1),
        )
        .groupby(["market", "consensus_count"], dropna=False)
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
    st.info("Add settled bets to activate adaptive live-learning analytics.")


# ------------------------------------------------------------
# Export
# ------------------------------------------------------------
st.subheader("💾 Export")
x1, x2, x3 = st.columns(3)
with x1:
    st.download_button(
        "Download Bet Log CSV",
        data=bet_log.to_csv(index=False).encode("utf-8"),
        file_name="bet_log_v25.csv",
        mime="text/csv",
        use_container_width=True,
    )
with x2:
    st.download_button(
        "Download Learning Profile CSV",
        data=profile.to_csv(index=False).encode("utf-8"),
        file_name="learning_profile_v25.csv",
        mime="text/csv",
        use_container_width=True,
    )
with x3:
    st.download_button(
        "Download Snapshot CSV",
        data=snapshot_df.to_csv(index=False).encode("utf-8"),
        file_name="odds_snapshot_v25.csv",
        mime="text/csv",
        use_container_width=True,
    )

st.caption(
    "This live engine is wired for The Odds API v4-style odds responses and stores its own snapshots so the app can measure movement between refreshes. "
    "The Odds API docs describe the v4 odds endpoint, the api.the-odds-api.com host, American odds formatting, and sport keys such as basketball_nba and icehockey_nhl. "
    "Moneyline, spreads, and totals are requested via markets like h2h, spreads, and totals. citeturn955092search1turn955092search3turn955092search6"
)
