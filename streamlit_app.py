
# streamlit_app_v26_1.py
# V26.1 Mobile Compact UI
#
# Mobile-first refinement of V26:
# - compact top play cards
# - compact watchlist cards
# - tighter spacing for iPhone/mobile
# - quick-scan metrics
# - optional detail expansion
#
# Keeps:
# - adaptive tiers
# - live odds fetch / fallback data
# - learning profile
# - bet log / grading
# - export tools

import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Sports Betting AI Dashboard V26.1", layout="wide")
st.title("🔥 Sports Betting AI Dashboard V26.1")
st.caption("Mobile Compact UI: faster scanning, tighter play cards, cleaner phone layout")

DATA_DIR = Path(".")
BET_LOG_PATH = DATA_DIR / "bet_log_v26_1.csv"
PROFILE_PATH = DATA_DIR / "learning_profile_v26_1.csv"
SNAPSHOT_PATH = DATA_DIR / "odds_snapshot_v26_1.csv"

SPORT_OPTIONS = {
    "NBA": "basketball_nba",
    "NHL": "icehockey_nhl",
    "NFL": "americanfootball_nfl",
    "MLB": "baseball_mlb",
    "EPL": "soccer_epl",
}

# ------------------------------------------------------------
# Styling
# ------------------------------------------------------------
st.markdown("""
<style>
/* Tighten general spacing on mobile */
.block-container {
    padding-top: 1rem;
    padding-bottom: 2rem;
}

/* Compact custom cards */
.compact-card {
    border: 1px solid rgba(128,128,128,0.25);
    border-radius: 14px;
    padding: 12px 14px 10px 14px;
    margin-bottom: 10px;
    background: rgba(255,255,255,0.02);
}
.compact-title {
    font-size: 1.05rem;
    font-weight: 700;
    margin-bottom: 4px;
    line-height: 1.2;
}
.compact-sub {
    font-size: 0.92rem;
    opacity: 0.85;
    margin-bottom: 8px;
}
.compact-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px 12px;
    margin-bottom: 8px;
}
.compact-metric {
    font-size: 0.86rem;
    line-height: 1.15;
}
.compact-label {
    opacity: 0.72;
}
.compact-value {
    font-weight: 700;
}
.compact-reason {
    font-size: 0.83rem;
    opacity: 0.75;
    line-height: 1.2;
}
.tier-chip {
    display: inline-block;
    border-radius: 999px;
    padding: 2px 8px;
    font-size: 0.8rem;
    font-weight: 700;
    margin-right: 6px;
}
.tier-a { background: rgba(46, 204, 113, 0.15); }
.tier-b { background: rgba(241, 196, 15, 0.15); }
.tier-c { background: rgba(52, 152, 219, 0.15); }
.tier-watch { background: rgba(149, 165, 166, 0.15); }

/* Tighter metric cards */
[data-testid="stMetric"] {
    padding-top: 0.1rem;
    padding-bottom: 0.1rem;
}

/* Make expanders a little tighter */
.streamlit-expanderHeader {
    font-size: 1rem;
}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------
# Helpers
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
            return 1 + o / 100.0
        return 1 + 100.0 / abs(o)
    except Exception:
        return np.nan


def normalize_0_100(value: float, min_v: float, max_v: float) -> float:
    if max_v <= min_v:
        return 50.0
    x = (value - min_v) / (max_v - min_v)
    return float(np.clip(x * 100.0, 0.0, 100.0))


def kelly_fraction(win_prob: float, odds: float) -> float:
    dec = american_to_decimal(odds)
    if np.isnan(dec):
        return 0.0
    b = dec - 1.0
    p = float(win_prob)
    q = 1.0 - p
    if b <= 0:
        return 0.0
    frac = (b * p - q) / b
    return max(0.0, frac)


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


def row_key_from_parts(event_id, market, selection, point, book) -> str:
    point_str = "" if pd.isna(point) else str(point)
    return f"{event_id} | {market} | {selection} | {point_str} | {book}"


def market_group_key_from_parts(event_id, market, selection, point) -> str:
    point_str = "" if pd.isna(point) else str(point)
    return f"{event_id} | {market} | {selection} | {point_str}"


def clv_from_odds(bet_odds: float, closing_odds: float) -> float:
    try:
        return (american_to_implied_prob(closing_odds) - american_to_implied_prob(bet_odds)) * 100.0
    except Exception:
        return 0.0


def pnl_units_for_result(odds: float, result: str) -> float:
    if result == "win":
        dec = american_to_decimal(odds)
        return (dec - 1.0) if not np.isnan(dec) else 0.0
    if result == "loss":
        return -1.0
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


def compact_card_html(row: pd.Series, idx: int) -> str:
    tier = str(row.get("tier", "")).strip()
    if tier in {"A", "B", "C"}:
        tier_class = {"A": "tier-a", "B": "tier-b", "C": "tier-c"}[tier]
        tier_text = f"Tier {tier}"
    else:
        tier_class = "tier-watch"
        tier_text = "Watch"

    title = format_selection(row.get("market", ""), row.get("selection", ""), row.get("point", np.nan))
    odds_val = row.get("odds", "")
    odds_txt = f"{int(odds_val)}" if pd.notna(odds_val) else "—"
    units = float(row.get("recommended_units", 0) or 0)
    final_score = float(row.get("final_score", 0) or 0)
    sharp = float(row.get("sharp_score", 0) or 0)
    edge = float(row.get("edge_pct", 0) or 0)
    book = str(row.get("book", ""))
    game = str(row.get("game", ""))
    consensus = int(row.get("consensus_count", 0) or 0)
    reason = str(row.get("decision_reason", ""))

    return f"""
    <div class="compact-card">
      <div class="compact-title">
        #{idx} <span class="tier-chip {tier_class}">{tier_text}</span> {title}
      </div>
      <div class="compact-sub">{game}</div>
      <div class="compact-grid">
        <div class="compact-metric"><span class="compact-label">Book:</span> <span class="compact-value">{book}</span></div>
        <div class="compact-metric"><span class="compact-label">Odds:</span> <span class="compact-value">{odds_txt}</span></div>
        <div class="compact-metric"><span class="compact-label">Units:</span> <span class="compact-value">{units:.2f}u</span></div>
        <div class="compact-metric"><span class="compact-label">Score:</span> <span class="compact-value">{final_score:.1f}</span></div>
        <div class="compact-metric"><span class="compact-label">Sharp:</span> <span class="compact-value">{sharp:.1f}</span></div>
        <div class="compact-metric"><span class="compact-label">Edge:</span> <span class="compact-value">{edge:.2f}%</span></div>
        <div class="compact-metric"><span class="compact-label">Consensus:</span> <span class="compact-value">{consensus} books</span></div>
      </div>
      <div class="compact-reason">{reason}</div>
    </div>
    """


# ------------------------------------------------------------
# Defaults
# ------------------------------------------------------------
def default_bet_log() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "date", "sport", "game", "market", "selection", "point", "book",
        "odds", "prev_odds", "consensus_price", "consensus_count",
        "line_movement", "sharp_score", "inefficiency_score", "edge_pct",
        "pressure_score", "final_score", "tier", "recommended_units",
        "result", "closing_odds", "clv"
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
        "snapshot_time", "event_id", "sport", "game", "market",
        "selection", "point", "book", "odds", "commence_time"
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
    ]
    return pd.DataFrame(rows, columns=[
        "event_id", "sport", "game", "commence_time", "market",
        "selection", "point", "book", "odds"
    ])


# ------------------------------------------------------------
# API fetch
# ------------------------------------------------------------
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
                    })

    return pd.DataFrame(rows), resp.headers.get("x-requests-remaining", "")


# ------------------------------------------------------------
# Live processing
# ------------------------------------------------------------
def attach_previous_snapshot(current_df: pd.DataFrame, snapshot_df: pd.DataFrame) -> pd.DataFrame:
    df = current_df.copy()
    if df.empty:
        df["prev_odds"] = np.nan
        df["line_movement"] = 0.0
        return df

    df["row_key"] = df.apply(
        lambda r: row_key_from_parts(r["event_id"], r["market"], r["selection"], r["point"], r["book"]),
        axis=1,
    )

    if snapshot_df.empty:
        df["prev_odds"] = np.nan
        df["line_movement"] = 0.0
        return df.drop(columns=["row_key"], errors="ignore")

    prev = snapshot_df.copy()
    prev["row_key"] = prev.apply(
        lambda r: row_key_from_parts(r["event_id"], r["market"], r["selection"], r["point"], r["book"]),
        axis=1,
    )
    prev = prev.sort_values("snapshot_time").drop_duplicates("row_key", keep="last")
    prev = prev[["row_key", "odds"]].rename(columns={"odds": "prev_odds"})

    df = df.merge(prev, on="row_key", how="left")
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
    if len(out) > 5000:
        out = out.tail(5000).copy()
    return out


def attach_market_consensus(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if out.empty:
        out["consensus_price"] = np.nan
        out["consensus_count"] = 0
        out["best_price_flag"] = False
        return out

    out["group_key"] = out.apply(
        lambda r: market_group_key_from_parts(r["event_id"], r["market"], r["selection"], r["point"]),
        axis=1,
    )

    grp = (
        out.groupby("group_key", dropna=False)
        .agg(
            consensus_price=("odds", "median"),
            consensus_count=("odds", "size"),
            min_price=("odds", "min"),
            max_price=("odds", "max"),
            std_price=("odds", "std"),
        )
        .reset_index()
    )
    grp["std_price"] = grp["std_price"].fillna(0.0)
    out = out.merge(grp, on="group_key", how="left")
    out["best_price_flag"] = out["odds"] == out["max_price"]
    out["price_disagreement"] = out["max_price"] - out["min_price"]
    return out.drop(columns=["group_key"], errors="ignore")


def add_market_context(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if out.empty:
        out["event_row_count"] = 0
        out["game_count"] = 0
        out["hours_to_start"] = np.nan
        return out

    out["event_row_count"] = out.groupby("event_id")["event_id"].transform("size")
    out["game_count"] = out["event_id"].nunique()

    try:
        now = pd.Timestamp.utcnow()
        out["commence_ts"] = pd.to_datetime(out["commence_time"], utc=True, errors="coerce")
        out["hours_to_start"] = (out["commence_ts"] - now).dt.total_seconds() / 3600.0
    except Exception:
        out["hours_to_start"] = np.nan

    return out


# ------------------------------------------------------------
# Learning
# ------------------------------------------------------------
def update_profile_from_bet_log(bet_log: pd.DataFrame, profile: pd.DataFrame) -> pd.DataFrame:
    prof = profile.copy()
    settled = bet_log[bet_log["result"].isin(["win", "loss"])].copy()
    if settled.empty:
        return prof

    settled["odds_bucket"] = settled["odds"].apply(odds_bucket)
    settled["consensus_bucket"] = settled["consensus_count"].apply(consensus_bucket)
    settled["roi_units_single"] = settled.apply(lambda r: pnl_units_for_result(r["odds"], r["result"]), axis=1)

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


# ------------------------------------------------------------
# Scoring
# ------------------------------------------------------------
def compute_sharp_score(row: pd.Series) -> float:
    current_odds = float(row.get("odds", np.nan))
    prev_odds = float(row.get("prev_odds", np.nan)) if pd.notna(row.get("prev_odds", np.nan)) else np.nan
    consensus_price = float(row.get("consensus_price", np.nan))
    count = float(row.get("consensus_count", 1))
    disagreement = float(row.get("price_disagreement", 0))

    movement = 0.0 if np.isnan(prev_odds) else (prev_odds - current_odds)
    movement_score = normalize_0_100(abs(movement), 0, 35) * 0.42
    direction_bonus = 18.0 if movement > 0 else 0.0
    consensus_alignment = 100 - normalize_0_100(abs(current_odds - consensus_price), 0, 40)
    agreement_component = consensus_alignment * 0.20
    depth_component = normalize_0_100(count, 1, 10) * 0.15
    disagreement_component = normalize_0_100(disagreement, 0, 40) * 0.08

    raw = 18 + movement_score + direction_bonus + agreement_component + depth_component + disagreement_component
    return float(np.clip(raw, 0, 100))


def compute_market_inefficiency(row: pd.Series) -> Tuple[float, float]:
    price = float(row.get("odds", np.nan))
    consensus = float(row.get("consensus_price", np.nan))
    if np.isnan(price) or np.isnan(consensus):
        return 0.0, 0.0

    p_book = american_to_implied_prob(price)
    p_cons = american_to_implied_prob(consensus)
    if np.isnan(p_book) or np.isnan(p_cons):
        return 0.0, 0.0

    edge_pct = (p_cons - p_book) * 100.0
    disagreement = float(row.get("price_disagreement", 0))
    score = np.clip(abs(edge_pct) * 14.0 + normalize_0_100(disagreement, 0, 40) * 0.20, 0, 100)
    return float(score), float(edge_pct)


def compute_pressure_score(row: pd.Series) -> float:
    movement = float(row.get("line_movement", 0.0))
    disagreement = float(row.get("price_disagreement", 0))
    best_flag = bool(row.get("best_price_flag", False))
    hours_to_start = row.get("hours_to_start", np.nan)

    move_component = normalize_0_100(abs(movement), 0, 35) * 0.45
    disagreement_component = normalize_0_100(disagreement, 0, 40) * 0.35
    best_component = 15 if best_flag else 0

    time_component = 0
    if pd.notna(hours_to_start):
        if hours_to_start <= 3:
            time_component = 10
        elif hours_to_start <= 8:
            time_component = 6
        elif hours_to_start <= 24:
            time_component = 3

    raw = move_component + disagreement_component + best_component + time_component
    return float(np.clip(raw, 0, 100))


def compute_adaptive_thresholds(df: pd.DataFrame, mode: str) -> Dict[str, float]:
    game_count = int(df["event_id"].nunique()) if len(df) else 0
    avg_disagreement = float(df["price_disagreement"].mean()) if "price_disagreement" in df.columns and len(df) else 0.0
    avg_rows_per_event = float(df.groupby("event_id").size().mean()) if len(df) else 0.0

    min_books = 3
    a_score, b_score, c_score = 85.0, 78.0, 70.0
    a_edge, b_edge, c_edge = 4.0, 2.5, 1.5
    a_sharp, b_sharp, c_sharp = 75.0, 65.0, 55.0

    if game_count <= 2:
        a_score -= 3
        b_score -= 4
        c_score -= 4
        a_edge -= 0.5
        b_edge -= 0.5
        c_edge -= 0.5

    if avg_disagreement <= 10:
        a_score -= 2
        b_score -= 3
        c_score -= 3
        a_edge -= 0.5
        b_edge -= 0.5
        c_edge -= 0.5

    if avg_rows_per_event <= 10:
        min_books = 2

    if mode == "Aggressive":
        a_score -= 3
        b_score -= 4
        c_score -= 5
        a_edge -= 0.5
        b_edge -= 0.5
        c_edge -= 0.5
        a_sharp -= 3
        b_sharp -= 4
        c_sharp -= 5
    elif mode == "Conservative":
        a_score += 2
        b_score += 2
        c_score += 2
        a_edge += 0.5
        b_edge += 0.5
        c_edge += 0.5
        a_sharp += 3
        b_sharp += 3
        c_sharp += 3

    return {
        "min_books": int(np.clip(min_books, 2, 5)),
        "A_score": float(np.clip(a_score, 75, 92)),
        "B_score": float(np.clip(b_score, 68, 86)),
        "C_score": float(np.clip(c_score, 60, 80)),
        "A_edge": float(np.clip(a_edge, 2.0, 6.0)),
        "B_edge": float(np.clip(b_edge, 1.0, 4.0)),
        "C_edge": float(np.clip(c_edge, 0.5, 3.0)),
        "A_sharp": float(np.clip(a_sharp, 60, 85)),
        "B_sharp": float(np.clip(b_sharp, 50, 75)),
        "C_sharp": float(np.clip(c_sharp, 40, 65)),
    }


def assign_tier(row: pd.Series, thresholds: Dict[str, float]) -> str:
    cc = float(row.get("consensus_count", 0))
    fs = float(row.get("final_score", 0))
    ep = float(row.get("edge_pct", 0))
    ss = float(row.get("sharp_score", 0))

    if cc >= thresholds["min_books"] and fs >= thresholds["A_score"] and ep >= thresholds["A_edge"] and ss >= thresholds["A_sharp"]:
        return "A"
    if cc >= thresholds["min_books"] and fs >= thresholds["B_score"] and ep >= thresholds["B_edge"] and ss >= thresholds["B_sharp"]:
        return "B"
    if cc >= thresholds["min_books"] and fs >= thresholds["C_score"] and ep >= thresholds["C_edge"] and ss >= thresholds["C_sharp"]:
        return "C"
    return ""


def score_live_candidates(df: pd.DataFrame, bankroll: float, max_units: float) -> pd.DataFrame:
    out = df.copy()

    sharp_scores = []
    ineff_scores = []
    edge_pcts = []
    pressure_scores = []
    final_scores = []
    units = []
    reasons = []

    for _, r in out.iterrows():
        sharp = compute_sharp_score(r)
        ineff, edge_pct = compute_market_inefficiency(r)
        pressure = compute_pressure_score(r)

        learning_weight = float(r.get("weight", 1.0))
        consensus_count = int(r.get("consensus_count", 1))
        movement = float(r.get("line_movement", 0.0))
        best_flag = bool(r.get("best_price_flag", False))

        market_prob = american_to_implied_prob(float(r.get("consensus_price", r.get("odds", -110))))
        own_prob = market_prob + max(edge_pct, 0) / 100.0

        consensus_bonus = {5: 14, 4: 9, 3: 4, 2: 1}.get(consensus_count, -6)
        best_price_bonus = 8 if best_flag else 0
        move_bonus = np.clip(abs(movement) * 0.5, 0, 8)
        pressure_boost = pressure * 0.12

        raw = (
            sharp * 0.32
            + ineff * 0.24
            + pressure * 0.18
            + learning_weight * 16.0
            + consensus_bonus
            + best_price_bonus
            + move_bonus
            + pressure_boost
        )
        final_score = float(np.clip(raw, 0, 100))

        kf = kelly_fraction(min(max(own_prob, 0.01), 0.99), float(r.get("odds", -110)))
        recommended_units = bankroll * kf * 0.25 / 100.0
        recommended_units = float(np.clip(recommended_units, 0.0, max_units))

        rb = []
        if best_flag:
            rb.append("best market price")
        if consensus_count >= 4:
            rb.append(f"{consensus_count}/book agreement")
        if sharp >= 70:
            rb.append("strong movement")
        if pressure >= 60:
            rb.append("market pressure")
        if edge_pct >= 1.5:
            rb.append(f"+{edge_pct:.1f}% edge")
        if not rb:
            rb.append("watch only")

        sharp_scores.append(round(sharp, 1))
        ineff_scores.append(round(ineff, 1))
        edge_pcts.append(round(edge_pct, 2))
        pressure_scores.append(round(pressure, 1))
        final_scores.append(round(final_score, 1))
        units.append(round(recommended_units, 2))
        reasons.append(" • ".join(rb))

    out["sharp_score"] = sharp_scores
    out["inefficiency_score"] = ineff_scores
    out["edge_pct"] = edge_pcts
    out["pressure_score"] = pressure_scores
    out["final_score"] = final_scores
    out["recommended_units"] = units
    out["decision_reason"] = reasons
    return out


def qualify_with_tiers(df: pd.DataFrame, thresholds: Dict[str, float]) -> pd.DataFrame:
    out = df.copy()
    out["tier"] = out.apply(lambda r: assign_tier(r, thresholds), axis=1)
    out["auto_qualified"] = out["tier"].isin(["A", "B", "C"])
    return out


# ------------------------------------------------------------
# Session state
# ------------------------------------------------------------
if "bet_log_v26_1" not in st.session_state:
    st.session_state.bet_log_v26_1 = safe_read_csv(BET_LOG_PATH, default_bet_log())
if "profile_v26_1" not in st.session_state:
    st.session_state.profile_v26_1 = safe_read_csv(PROFILE_PATH, default_profile())
if "snapshot_v26_1" not in st.session_state:
    st.session_state.snapshot_v26_1 = safe_read_csv(SNAPSHOT_PATH, default_snapshot())
if "current_live_df_v26_1" not in st.session_state:
    st.session_state.current_live_df_v26_1 = fallback_live_rows()

bet_log = st.session_state.bet_log_v26_1.copy()
profile = st.session_state.profile_v26_1.copy()
snapshot_df = st.session_state.snapshot_v26_1.copy()

# ------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------
st.sidebar.header("⚙️ V26.1 Controls")
api_key_default = os.getenv("ODDS_API_KEY", "")
api_key = st.sidebar.text_input("Odds API Key", value=api_key_default, type="password")
sport_label = st.sidebar.selectbox("Sport", list(SPORT_OPTIONS.keys()), index=0)
sport_key = SPORT_OPTIONS[sport_label]

regions = st.sidebar.text_input("Regions", value="us")
markets_list = st.sidebar.multiselect("Markets", ["h2h", "spreads", "totals"], default=["h2h", "spreads", "totals"])
bookmakers = st.sidebar.text_input("Specific bookmakers (optional)", value="")
bankroll = st.sidebar.number_input("Bankroll ($)", min_value=100, value=1000, step=100)
max_units = st.sidebar.number_input("Max Units", min_value=0.25, value=2.0, step=0.25)
mode = st.sidebar.selectbox("Adaptive Mode", ["Balanced", "Aggressive", "Conservative"], index=0)
auto_save = st.sidebar.checkbox("Auto-save qualified plays to bet log", value=False)
show_watchlist = st.sidebar.checkbox("Show watchlist cards", value=True)
show_detail_expanders = st.sidebar.checkbox("Show detail expanders", value=False)

st.sidebar.markdown("---")
auto_refresh = st.sidebar.checkbox("Auto refresh every run", value=False)
refresh_seconds = st.sidebar.selectbox("Refresh seconds", [15, 30, 60, 120], index=1)

fetch_live = st.sidebar.button("📡 Fetch Live Odds", use_container_width=True)
refresh_learning = st.sidebar.button("🧠 Refresh Learning Profile", use_container_width=True)
reset_snapshot = st.sidebar.button("🧹 Reset Snapshot History", use_container_width=True)

if reset_snapshot:
    snapshot_df = default_snapshot()
    st.session_state.snapshot_v26_1 = snapshot_df.copy()
    safe_save_csv(snapshot_df, SNAPSHOT_PATH)
    st.sidebar.success("Snapshot history reset")

if refresh_learning:
    profile = update_profile_from_bet_log(bet_log, profile)
    st.session_state.profile_v26_1 = profile.copy()
    safe_save_csv(profile, PROFILE_PATH)
    st.sidebar.success("Learning profile refreshed")

# ------------------------------------------------------------
# Live fetch
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
                live_status = "Live fetch succeeded, but returned no rows. Fallback data loaded."
                live_df = fallback_live_rows()
            else:
                live_status = "Live odds fetched successfully."
            st.session_state.current_live_df_v26_1 = live_df.copy()
        except Exception as e:
            live_status = f"Live fetch failed. Using fallback data. Error: {e}"
            st.session_state.current_live_df_v26_1 = fallback_live_rows()
    else:
        live_status = "No API key provided. Using fallback test dataset."
        st.session_state.current_live_df_v26_1 = fallback_live_rows()

current_live_df = st.session_state.current_live_df_v26_1.copy()
current_live_df = current_live_df[current_live_df["sport"] == sport_key].copy()
if current_live_df.empty:
    current_live_df = fallback_live_rows()
    current_live_df = current_live_df[current_live_df["sport"] == sport_key].copy()

if live_status:
    st.info(live_status)
if requests_remaining:
    st.caption(f"API requests remaining: {requests_remaining}")

# ------------------------------------------------------------
# Process data
# ------------------------------------------------------------
current_live_df = attach_previous_snapshot(current_live_df, snapshot_df)
current_live_df = attach_market_consensus(current_live_df)
current_live_df = add_market_context(current_live_df)

profile = update_profile_from_bet_log(bet_log, profile)
st.session_state.profile_v26_1 = profile.copy()
safe_save_csv(profile, PROFILE_PATH)

current_live_df = attach_profile_weight(current_live_df, profile)
scored_df = score_live_candidates(current_live_df, bankroll=bankroll, max_units=max_units)

thresholds = compute_adaptive_thresholds(scored_df, mode=mode)
scored_df = qualify_with_tiers(scored_df, thresholds)

tier_order = {"A": 0, "B": 1, "C": 2, "": 3}
scored_df["tier_sort"] = scored_df["tier"].map(tier_order).fillna(3)
scored_df = scored_df.sort_values(
    ["auto_qualified", "tier_sort", "final_score", "edge_pct"],
    ascending=[False, True, False, False]
).reset_index(drop=True)

qualified_df = scored_df[scored_df["auto_qualified"]].copy()
watch_df = scored_df[~scored_df["auto_qualified"]].copy()

snapshot_df = update_snapshot_store(current_live_df, snapshot_df)
st.session_state.snapshot_v26_1 = snapshot_df.copy()
safe_save_csv(snapshot_df, SNAPSHOT_PATH)

# ------------------------------------------------------------
# KPIs
# ------------------------------------------------------------
k1, k2, k3, k4 = st.columns(4)
k1.metric("Live Rows", len(scored_df))
k2.metric("Qualified", len(qualified_df))
k3.metric("Watchlist", len(watch_df))
k4.metric("Mode", mode)

k5, k6, k7, k8 = st.columns(4)
k5.metric("Tier A", int((qualified_df["tier"] == "A").sum()) if len(qualified_df) else 0)
k6.metric("Tier B", int((qualified_df["tier"] == "B").sum()) if len(qualified_df) else 0)
k7.metric("Tier C", int((qualified_df["tier"] == "C").sum()) if len(qualified_df) else 0)
k8.metric("Avg Edge", f"{qualified_df['edge_pct'].mean():.2f}%" if len(qualified_df) else "—")

with st.expander("🎛️ Adaptive Thresholds", expanded=False):
    st.dataframe(pd.DataFrame([thresholds]), use_container_width=True, hide_index=True)

# ------------------------------------------------------------
# Compact cards
# ------------------------------------------------------------
st.subheader("🎯 Compact Top Plays")

if qualified_df.empty:
    st.warning("No A/B/C plays right now.")
else:
    for i, (_, row) in enumerate(qualified_df.head(10).iterrows(), start=1):
        st.markdown(compact_card_html(row, i), unsafe_allow_html=True)
        if show_detail_expanders:
            with st.expander(f"Details #{i}", expanded=False):
                st.dataframe(pd.DataFrame([row]), use_container_width=True, hide_index=True)

if show_watchlist:
    st.subheader("👀 Compact Watchlist")
    for i, (_, row) in enumerate(watch_df.head(10).iterrows(), start=1):
        st.markdown(compact_card_html(row, i), unsafe_allow_html=True)
        if show_detail_expanders:
            with st.expander(f"Watch Details #{i}", expanded=False):
                st.dataframe(pd.DataFrame([row]), use_container_width=True, hide_index=True)

# ------------------------------------------------------------
# Compact tables
# ------------------------------------------------------------
st.subheader("✅ Quick Table")
quick_cols = ["tier", "game", "selection", "book", "odds", "recommended_units", "final_score", "edge_pct"]
st.dataframe(scored_df[quick_cols], use_container_width=True, hide_index=True)

with st.expander("📊 Full Scored Rows", expanded=False):
    st.dataframe(
        scored_df[[
            "sport", "game", "market", "selection", "point", "book", "odds", "prev_odds",
            "consensus_price", "consensus_count", "price_disagreement", "line_movement",
            "sharp_score", "inefficiency_score", "edge_pct", "pressure_score",
            "final_score", "tier", "recommended_units", "auto_qualified"
        ]],
        use_container_width=True,
        hide_index=True,
    )

with st.expander("🛰️ Raw Live Rows", expanded=False):
    st.dataframe(current_live_df, use_container_width=True, hide_index=True)

# ------------------------------------------------------------
# Auto-save
# ------------------------------------------------------------
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
                "pressure_score": r["pressure_score"],
                "final_score": r["final_score"],
                "tier": r["tier"],
                "recommended_units": r["recommended_units"],
                "result": "",
                "closing_odds": np.nan,
                "clv": np.nan,
            })
    if add_rows:
        bet_log = pd.concat([bet_log, pd.DataFrame(add_rows)], ignore_index=True)
        st.session_state.bet_log_v26_1 = bet_log.copy()
        safe_save_csv(bet_log, BET_LOG_PATH)
        st.success(f"Auto-saved {len(add_rows)} qualified play(s) to bet log.")

# ------------------------------------------------------------
# Bet log + grading
# ------------------------------------------------------------
st.subheader("📒 Bet Log + Grading")

with st.form("bet_log_form"):
    a1, a2 = st.columns(2)
    game = a1.text_input("Game")
    market = a2.selectbox("Market", ["moneyline", "spreads", "totals"])

    b1, b2 = st.columns(2)
    selection = b1.text_input("Selection")
    point = b2.number_input("Point (0 if N/A)", value=0.0, step=0.5)

    c1, c2 = st.columns(2)
    book = c1.text_input("Book", value="DraftKings")
    odds = c2.number_input("Bet Odds", value=-110)

    d1, d2 = st.columns(2)
    prev_odds = d1.number_input("Previous Odds", value=-110)
    consensus_price = d2.number_input("Consensus Price", value=-110)

    e1, e2 = st.columns(2)
    consensus_count = e1.slider("Consensus Count", 1, 10, 3)
    closing_odds = e2.number_input("Closing Odds", value=-110)

    result = st.selectbox("Result", ["", "win", "loss"])
    submitted = st.form_submit_button("Add / Grade Bet")

    if submitted:
        line_movement = prev_odds - odds
        temp_row = pd.Series({
            "odds": odds,
            "prev_odds": prev_odds,
            "consensus_price": consensus_price,
            "consensus_count": consensus_count,
            "price_disagreement": abs(consensus_price - odds),
            "best_price_flag": True,
            "line_movement": line_movement,
            "hours_to_start": np.nan,
        })
        sharp_score = compute_sharp_score(temp_row)
        ineff, edge_pct = compute_market_inefficiency(temp_row)
        pressure_score = compute_pressure_score(temp_row)

        learning_weight = 1.0
        consensus_bonus = {5: 14, 4: 9, 3: 4, 2: 1}.get(consensus_count, -6)
        final_score = float(np.clip(
            sharp_score * 0.32
            + ineff * 0.24
            + pressure_score * 0.18
            + learning_weight * 16.0
            + consensus_bonus
            + 8
            + min(abs(line_movement) * 0.5, 8),
            0, 100
        ))

        market_prob = american_to_implied_prob(consensus_price)
        own_prob = market_prob + max(edge_pct, 0) / 100.0
        units = float(np.clip(bankroll * kelly_fraction(min(max(own_prob, 0.01), 0.99), odds) * 0.25 / 100.0, 0, max_units))

        temp_scored = pd.Series({
            "consensus_count": consensus_count,
            "final_score": final_score,
            "edge_pct": edge_pct,
            "sharp_score": sharp_score,
        })
        tier = assign_tier(temp_scored, thresholds)
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
            "pressure_score": round(pressure_score, 1),
            "final_score": round(final_score, 1),
            "tier": tier,
            "recommended_units": round(units, 2),
            "result": result,
            "closing_odds": closing_odds,
            "clv": round(clv, 2),
        }])

        bet_log = pd.concat([bet_log, add], ignore_index=True)
        st.session_state.bet_log_v26_1 = bet_log.copy()
        safe_save_csv(bet_log, BET_LOG_PATH)
        st.success("Bet log updated.")

st.dataframe(
    bet_log[["date", "game", "market", "selection", "book", "odds", "tier", "result", "clv"]],
    use_container_width=True,
    hide_index=True,
)

settled = bet_log[bet_log["result"].isin(["win", "loss"])].copy()
wins = int((settled["result"] == "win").sum())
win_rate = (wins / len(settled) * 100.0) if len(settled) else 0.0
net_units = settled.apply(lambda r: pnl_units_for_result(r["odds"], r["result"]), axis=1).sum() if len(settled) else 0.0
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

# ------------------------------------------------------------
# Export
# ------------------------------------------------------------
st.subheader("💾 Export")
e1, e2, e3 = st.columns(3)
with e1:
    st.download_button(
        "Download Bet Log CSV",
        data=bet_log.to_csv(index=False).encode("utf-8"),
        file_name="bet_log_v26_1.csv",
        mime="text/csv",
        use_container_width=True,
    )
with e2:
    st.download_button(
        "Download Learning Profile CSV",
        data=profile.to_csv(index=False).encode("utf-8"),
        file_name="learning_profile_v26_1.csv",
        mime="text/csv",
        use_container_width=True,
    )
with e3:
    st.download_button(
        "Download Snapshot CSV",
        data=snapshot_df.to_csv(index=False).encode("utf-8"),
        file_name="odds_snapshot_v26_1.csv",
        mime="text/csv",
        use_container_width=True,
    )

st.caption("V26.1 focuses on a compact mobile layout so iPhone users can compare more plays with less scrolling.")

# ------------------------------------------------------------
# Auto refresh
# ------------------------------------------------------------
if auto_refresh:
    st.caption(f"Auto refresh enabled: rerunning in {refresh_seconds} seconds.")
    time.sleep(refresh_seconds)
    st.rerun()
