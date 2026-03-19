
import math
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
import streamlit as st


# =========================================================
# PAGE SETUP
# =========================================================
st.set_page_config(
    page_title="Sports AI Betting Dashboard V6",
    page_icon="🏀",
    layout="wide",
)

st.title("🏀 Sports AI Betting Dashboard V6")
st.caption("Real Provider Integration • The Odds API • Featured Markets + Event Props • Snapshot Line Movement")


# =========================================================
# CONFIG
# =========================================================
DEFAULT_TIMEOUT = 20
THE_ODDS_API_HOST = "https://api.the-odds-api.com"

SPORT_KEY_MAP = {
    "NBA": "basketball_nba",
    "WNBA": "basketball_wnba",
    "NHL": "icehockey_nhl",
    "MLB": "baseball_mlb",
    "NFL": "americanfootball_nfl",
}

FEATURED_MARKETS_MAP = {
    "NBA": "h2h,spreads,totals",
    "WNBA": "h2h,spreads,totals",
    "NHL": "h2h,spreads,totals",
    "MLB": "h2h,spreads,totals",
    "NFL": "h2h,spreads,totals",
}

# Real The Odds API event-level player prop market keys
PLAYER_PROP_MARKETS = {
    "NBA": [
        "player_points",
        "player_points_q1",
        "player_rebounds",
        "player_rebounds_q1",
        "player_assists",
        "player_assists_q1",
        "player_threes",
        "player_blocks",
        "player_steals",
        "player_blocks_steals",
        "player_turnovers",
        "player_points_rebounds_assists",
        "player_points_rebounds",
        "player_points_assists",
        "player_rebounds_assists",
    ],
    "WNBA": [
        "player_points",
        "player_points_q1",
        "player_rebounds",
        "player_rebounds_q1",
        "player_assists",
        "player_assists_q1",
        "player_threes",
        "player_blocks",
        "player_steals",
        "player_blocks_steals",
        "player_turnovers",
        "player_points_rebounds_assists",
        "player_points_rebounds",
        "player_points_assists",
        "player_rebounds_assists",
    ],
    "NHL": [
        "player_points",
        "player_power_play_points",
        "player_assists",
        "player_blocked_shots",
        "player_shots_on_goal",
        "player_goals",
        "player_total_saves",
    ],
    "NFL": [
        "player_pass_yds",
        "player_pass_yds_q1",
        "player_pass_tds",
        "player_receptions",
        "player_reception_yds",
        "player_rush_yds",
        "player_rush_attempts",
        "player_assists",
        "player_sacks",
        "player_tackles_assists",
    ],
    "MLB": [
        "batter_hits",
        "batter_total_bases",
        "batter_rbis",
        "batter_runs_scored",
        "batter_walks",
        "batter_strikeouts",
        "pitcher_strikeouts",
        "pitcher_hits_allowed",
        "pitcher_walks",
        "pitcher_earned_runs",
        "pitcher_outs",
    ],
}


# =========================================================
# HELPERS
# =========================================================
def normalize_text(x):
    if pd.isna(x):
        return ""
    return str(x).strip().lower()


def safe_float(x):
    try:
        if pd.isna(x):
            return np.nan
        return float(x)
    except Exception:
        return np.nan


def american_to_decimal(odds):
    try:
        odds = float(odds)
        if odds > 0:
            return 1 + (odds / 100)
        return 1 + (100 / abs(odds))
    except Exception:
        return np.nan


def implied_prob_american(odds):
    try:
        odds = float(odds)
        if odds > 0:
            return 100 / (odds + 100)
        return abs(odds) / (abs(odds) + 100)
    except Exception:
        return np.nan


def prob_to_american(prob):
    try:
        prob = float(prob)
        if prob <= 0 or prob >= 1:
            return np.nan
        if prob >= 0.5:
            return int(round(-(prob / (1 - prob)) * 100))
        return int(round(((1 - prob) / prob) * 100))
    except Exception:
        return np.nan


def add_missing_cols(df, cols_with_defaults):
    for col, default in cols_with_defaults.items():
        if col not in df.columns:
            df[col] = default
    return df


def edge_bucket(score):
    if score >= 86:
        return "🟢 A"
    if score >= 76:
        return "🟢 B"
    if score >= 66:
        return "🟡 C"
    return "🔴 Pass"


def current_ts_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def chunk_list(items, chunk_size):
    if chunk_size <= 0:
        return [items]
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def market_to_prop_type(market_key: str) -> str:
    mapping = {
        "player_points": "points",
        "player_points_q1": "points",
        "player_rebounds": "rebounds",
        "player_rebounds_q1": "rebounds",
        "player_assists": "assists",
        "player_assists_q1": "assists",
        "player_threes": "3pt_made",
        "player_blocks": "blocks",
        "player_steals": "steals",
        "player_blocks_steals": "blocks_steals",
        "player_turnovers": "turnovers",
        "player_points_rebounds_assists": "pra",
        "player_points_rebounds": "pr",
        "player_points_assists": "pa",
        "player_rebounds_assists": "ra",
        "player_power_play_points": "power_play_points",
        "player_blocked_shots": "blocked_shots",
        "player_shots_on_goal": "shots_on_goal",
        "player_goals": "goals",
        "player_total_saves": "saves",
        "player_pass_yds": "pass_yds",
        "player_pass_yds_q1": "pass_yds",
        "player_pass_tds": "pass_tds",
        "player_receptions": "receptions",
        "player_reception_yds": "reception_yds",
        "player_rush_yds": "rush_yds",
        "player_rush_attempts": "rush_attempts",
        "player_sacks": "sacks",
        "player_tackles_assists": "tackles_assists",
        "batter_hits": "hits",
        "batter_total_bases": "total_bases",
        "batter_rbis": "rbis",
        "batter_runs_scored": "runs",
        "batter_walks": "walks",
        "batter_strikeouts": "batter_strikeouts",
        "pitcher_strikeouts": "pitcher_strikeouts",
        "pitcher_hits_allowed": "hits_allowed",
        "pitcher_walks": "pitcher_walks",
        "pitcher_earned_runs": "earned_runs",
        "pitcher_outs": "pitcher_outs",
    }
    return mapping.get(market_key, market_key)


def market_to_segment(market_key: str) -> str:
    return "1q" if market_key.endswith("_q1") else "full_game"


def build_headers():
    return {"Accept": "application/json"}


def clean_market_name(x):
    x = normalize_text(x)
    mapping = {
        "h2h": "moneyline",
        "moneyline": "moneyline",
        "spreads": "spreads",
        "totals": "totals",
    }
    return mapping.get(x, x)


# =========================================================
# SAMPLE FALLBACK DATA
# =========================================================
def sample_injuries_data():
    rows = [
        ["NBA", "Knicks", "Jalen Brunson", "available", "confirmed", "", current_ts_str()],
        ["NBA", "Pacers", "Tyrese Haliburton", "questionable", "expected", "ankle", current_ts_str()],
        ["NBA", "Warriors", "Stephen Curry", "available", "confirmed", "", current_ts_str()],
    ]
    return pd.DataFrame(rows, columns=[
        "sport", "team", "player", "injury_status", "starter_status", "injury_note", "source_time"
    ])


# =========================================================
# REAL PROVIDER: THE ODDS API
# =========================================================
def the_odds_get(path: str, api_key: str, params: Optional[dict] = None):
    url = f"{THE_ODDS_API_HOST}{path}"
    merged = dict(params or {})
    merged["apiKey"] = api_key
    try:
        response = requests.get(url, headers=build_headers(), params=merged, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        return response.json(), None
    except Exception as e:
        return None, str(e)


@st.cache_data(ttl=60, show_spinner=False)
def fetch_featured_odds_from_the_odds_api(api_key: str, sport_key: str, regions: str, bookmakers: str, odds_format: str):
    params = {
        "regions": regions,
        "markets": "h2h,spreads,totals",
        "oddsFormat": odds_format,
    }
    if bookmakers:
        params["bookmakers"] = bookmakers
    return the_odds_get(f"/v4/sports/{sport_key}/odds", api_key=api_key, params=params)


@st.cache_data(ttl=60, show_spinner=False)
def fetch_event_props_from_the_odds_api(api_key: str, sport_key: str, event_id: str, markets_csv: str, regions: str, bookmakers: str, odds_format: str):
    params = {
        "regions": regions,
        "markets": markets_csv,
        "oddsFormat": odds_format,
    }
    if bookmakers:
        params["bookmakers"] = bookmakers
    return the_odds_get(f"/v4/sports/{sport_key}/events/{event_id}/odds", api_key=api_key, params=params)


def parse_featured_odds_payload(payload, sport_title_fallback: str):
    rows = []
    events = payload if isinstance(payload, list) else []
    for event in events:
        sport_title = event.get("sport_title", sport_title_fallback)
        event_id = event.get("id", "")
        home_team = event.get("home_team", "")
        away_team = event.get("away_team", "")
        commence_time = event.get("commence_time", "")
        bookmakers = event.get("bookmakers", []) or []

        for book in bookmakers:
            book_title = book.get("title", book.get("key", "Unknown"))
            last_update = book.get("last_update", "")
            for market in book.get("markets", []) or []:
                market_key = market.get("key", "")
                for outcome in market.get("outcomes", []) or []:
                    rows.append({
                        "sport": sport_title,
                        "event_id": event_id,
                        "team_a": away_team,
                        "team_b": home_team,
                        "book": book_title,
                        "market": clean_market_name(market_key),
                        "point": outcome.get("point", np.nan) if market_key == "spreads" else np.nan,
                        "total": outcome.get("point", np.nan) if market_key == "totals" else np.nan,
                        "selection": outcome.get("name", ""),
                        "odds": outcome.get("price", np.nan),
                        "commence_time": commence_time,
                        "book_last_update": last_update,
                    })
    return pd.DataFrame(rows)


def parse_event_props_payload(payload, sport_title_fallback: str):
    rows = []
    if not isinstance(payload, dict):
        return pd.DataFrame()

    sport_title = payload.get("sport_title", sport_title_fallback)
    event_id = payload.get("id", "")
    home_team = payload.get("home_team", "")
    away_team = payload.get("away_team", "")
    commence_time = payload.get("commence_time", "")
    bookmakers = payload.get("bookmakers", []) or []

    for book in bookmakers:
        book_title = book.get("title", book.get("key", "Unknown"))
        book_last_update = book.get("last_update", "")
        for market in book.get("markets", []) or []:
            market_key = market.get("key", "")
            prop_type = market_to_prop_type(market_key)
            game_segment = market_to_segment(market_key)

            for outcome in market.get("outcomes", []) or []:
                desc = outcome.get("description", "")
                name = outcome.get("name", "")
                point = outcome.get("point", np.nan)
                price = outcome.get("price", np.nan)

                # Skip yes/no style markets without usable player names/lines
                if not desc:
                    continue
                if pd.isna(point):
                    continue
                if name not in ["Over", "Under"]:
                    continue

                rows.append({
                    "sport": sport_title,
                    "event_id": event_id,
                    "player": desc,
                    "team": "",
                    "opponent": f"{away_team} vs {home_team}",
                    "is_starter": 1,
                    "starter_status": "unknown",
                    "starter_confirmed": 0,
                    "prop_type": prop_type,
                    "line": point,
                    "projection": np.nan,   # user/model layer can overwrite later
                    "minutes_projection": np.nan,
                    "recent_avg": np.nan,
                    "last_5_games": 5,
                    "pace_factor": 1.00,
                    "matchup_factor": 1.00,
                    "odds": price,
                    "game_segment": game_segment,
                    "book": book_title,
                    "recommended_side_from_book": name,
                    "source_time": book_last_update or commence_time,
                    "commence_time": commence_time,
                })
    return pd.DataFrame(rows)


def fetch_full_odds_and_props(api_key: str, sport_name: str, regions: str, bookmakers: str, odds_format: str, include_props: bool):
    sport_key = SPORT_KEY_MAP[sport_name]
    featured_payload, featured_err = fetch_featured_odds_from_the_odds_api(
        api_key=api_key,
        sport_key=sport_key,
        regions=regions,
        bookmakers=bookmakers,
        odds_format=odds_format,
    )
    if featured_payload is None:
        return pd.DataFrame(), pd.DataFrame(), featured_err

    odds_df = parse_featured_odds_payload(featured_payload, sport_name)

    props_df = pd.DataFrame()
    if include_props:
        prop_markets = PLAYER_PROP_MARKETS.get(sport_name, [])
        if prop_markets:
            event_ids = []
            if isinstance(featured_payload, list):
                event_ids = [x.get("id", "") for x in featured_payload if x.get("id")]
            prop_rows = []

            # Chunk because event-level props can be very large and request-heavy
            market_chunks = chunk_list(prop_markets, 5)

            for event_id in event_ids:
                for chunk in market_chunks:
                    props_payload, _ = fetch_event_props_from_the_odds_api(
                        api_key=api_key,
                        sport_key=sport_key,
                        event_id=event_id,
                        markets_csv=",".join(chunk),
                        regions=regions,
                        bookmakers=bookmakers,
                        odds_format=odds_format,
                    )
                    if props_payload is not None:
                        parsed = parse_event_props_payload(props_payload, sport_name)
                        if not parsed.empty:
                            prop_rows.append(parsed)

            if prop_rows:
                props_df = pd.concat(prop_rows, ignore_index=True).drop_duplicates()

    return odds_df, props_df, None


# =========================================================
# CSV FALLBACK FOR USER MODEL DATA
# =========================================================
def load_csv_or_empty(uploaded_file):
    if uploaded_file is None:
        return pd.DataFrame()
    try:
        if str(uploaded_file.name).lower().endswith(".csv"):
            return pd.read_csv(uploaded_file)
        return pd.read_excel(uploaded_file)
    except Exception:
        return pd.DataFrame()


def prepare_model_overlay_df(df):
    """
    Optional user upload that adds projections / minutes / starter info by player+prop.
    Expected columns can include:
    player, prop_type, game_segment, projection, minutes_projection, recent_avg,
    is_starter, starter_status, starter_confirmed, pace_factor, matchup_factor, team, opponent
    """
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    df = add_missing_cols(df, {
        "player": "",
        "prop_type": "",
        "game_segment": "full_game",
        "projection": np.nan,
        "minutes_projection": np.nan,
        "recent_avg": np.nan,
        "is_starter": np.nan,
        "starter_status": "",
        "starter_confirmed": np.nan,
        "pace_factor": np.nan,
        "matchup_factor": np.nan,
        "team": "",
        "opponent": "",
    })
    for col in ["player", "prop_type", "game_segment", "starter_status", "team", "opponent"]:
        df[col] = df[col].fillna("").astype(str)
    for col in ["projection", "minutes_projection", "recent_avg", "is_starter", "starter_confirmed", "pace_factor", "matchup_factor"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["prop_type"] = df["prop_type"].apply(normalize_text)
    df["game_segment"] = df["game_segment"].apply(normalize_text)
    df["player"] = df["player"].astype(str)
    return df


def prepare_injuries_df(df):
    if df is None or df.empty:
        return sample_injuries_data()

    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    df = add_missing_cols(df, {
        "sport": "NBA",
        "team": "",
        "player": "",
        "injury_status": "unknown",
        "starter_status": "unknown",
        "injury_note": "",
        "source_time": current_ts_str(),
    })
    for col in ["sport", "team", "player", "injury_status", "starter_status", "injury_note", "source_time"]:
        df[col] = df[col].fillna("").astype(str)
    df["injury_status"] = df["injury_status"].apply(normalize_text)
    df["starter_status"] = df["starter_status"].apply(normalize_text)
    return df


# =========================================================
# PREP / MERGE
# =========================================================
def prepare_odds_df(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=["sport", "event_id", "team_a", "team_b", "book", "market", "point", "total", "selection", "odds"])
    df = df.copy()
    df["market"] = df["market"].apply(clean_market_name)
    df["odds"] = pd.to_numeric(df["odds"], errors="coerce")
    df["point"] = pd.to_numeric(df.get("point", np.nan), errors="coerce")
    df["total"] = pd.to_numeric(df.get("total", np.nan), errors="coerce")
    df["dec_odds"] = df["odds"].apply(american_to_decimal)
    df["imp_prob"] = df["odds"].apply(implied_prob_american)
    return df


def prepare_props_df(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=[
            "sport", "event_id", "player", "team", "opponent", "is_starter", "starter_status", "starter_confirmed",
            "prop_type", "line", "projection", "minutes_projection", "recent_avg", "last_5_games",
            "pace_factor", "matchup_factor", "odds", "game_segment", "book", "source_time"
        ])

    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    df = add_missing_cols(df, {
        "sport": "NBA",
        "event_id": "",
        "player": "",
        "team": "",
        "opponent": "",
        "is_starter": 1,
        "starter_status": "unknown",
        "starter_confirmed": 0,
        "prop_type": "",
        "line": np.nan,
        "projection": np.nan,
        "minutes_projection": np.nan,
        "recent_avg": np.nan,
        "last_5_games": 5,
        "pace_factor": 1.0,
        "matchup_factor": 1.0,
        "odds": np.nan,
        "game_segment": "full_game",
        "book": "Unknown",
        "source_time": "",
    })

    numeric_cols = [
        "is_starter", "starter_confirmed", "line", "projection", "minutes_projection",
        "recent_avg", "last_5_games", "pace_factor", "matchup_factor", "odds"
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ["sport", "event_id", "player", "team", "opponent", "starter_status", "prop_type", "game_segment", "book", "source_time"]:
        df[col] = df[col].fillna("").astype(str)

    df["prop_type"] = df["prop_type"].apply(normalize_text)
    df["game_segment"] = df["game_segment"].apply(normalize_text)
    df["starter_status"] = df["starter_status"].apply(normalize_text)

    return df


def apply_model_overlay(props_df, overlay_df):
    if props_df.empty or overlay_df.empty:
        return props_df.copy()

    base = props_df.copy()
    overlay = overlay_df.copy()

    keys = ["player", "prop_type", "game_segment"]
    overlay = overlay.drop_duplicates(subset=keys, keep="last")

    merged = base.merge(
        overlay[keys + [c for c in overlay.columns if c not in keys]],
        on=keys,
        how="left",
        suffixes=("", "_overlay")
    )

    replace_cols = [
        "projection", "minutes_projection", "recent_avg", "is_starter",
        "starter_status", "starter_confirmed", "pace_factor", "matchup_factor",
        "team", "opponent"
    ]
    for col in replace_cols:
        overlay_col = f"{col}_overlay"
        if overlay_col in merged.columns:
            if merged[col].dtype == object:
                merged[col] = np.where(merged[overlay_col].fillna("").astype(str).str.len() > 0, merged[overlay_col], merged[col])
            else:
                merged[col] = np.where(~pd.isna(merged[overlay_col]), merged[overlay_col], merged[col])

    drop_cols = [c for c in merged.columns if c.endswith("_overlay")]
    return merged.drop(columns=drop_cols)


def apply_injuries(props_df, injuries_df):
    if props_df.empty:
        return props_df.copy()
    if injuries_df.empty:
        out = props_df.copy()
        out["injury_status"] = "unknown"
        out["injury_note"] = ""
        return out

    inj = injuries_df[["player", "injury_status", "starter_status", "injury_note"]].drop_duplicates(subset=["player"], keep="last")
    merged = props_df.merge(inj, on="player", how="left", suffixes=("", "_inj"))
    merged["injury_status"] = merged["injury_status"].fillna("unknown")
    merged["injury_note"] = merged["injury_note"].fillna("")
    merged["starter_status"] = np.where(
        merged["starter_status_inj"].fillna("").astype(str).str.len() > 0,
        merged["starter_status_inj"],
        merged["starter_status"]
    )
    drop_cols = [c for c in merged.columns if c.endswith("_inj")]
    return merged.drop(columns=drop_cols)


# =========================================================
# SNAPSHOT LINE MOVEMENT
# =========================================================
def append_snapshot(df, label):
    if df.empty:
        return df.copy()
    snap = df.copy()
    snap["snapshot_label"] = label
    snap["snapshot_time"] = current_ts_str()
    return snap


def save_snapshot_to_session(name, df):
    if "snapshots" not in st.session_state:
        st.session_state["snapshots"] = {}
    st.session_state["snapshots"][name] = df.copy()


def get_snapshot_from_session(name):
    if "snapshots" not in st.session_state:
        return pd.DataFrame()
    return st.session_state["snapshots"].get(name, pd.DataFrame())


def build_line_movement_from_snapshots(old_df, new_df):
    if old_df.empty or new_df.empty:
        return pd.DataFrame()

    keys = ["player", "prop_type", "game_segment", "book", "line", "recommended_side_from_book"]
    old_small = old_df[keys + ["odds"]].copy().rename(columns={"odds": "old_odds"})
    new_small = new_df[keys + ["odds"]].copy().rename(columns={"odds": "new_odds"})

    merged = new_small.merge(old_small, on=keys, how="left")
    merged["odds_move"] = merged["new_odds"] - merged["old_odds"]
    return merged


def apply_movement_to_props(props_df, movement_df):
    if props_df.empty:
        return props_df.copy()
    out = props_df.copy()
    if movement_df.empty:
        out["odds_move"] = np.nan
        return out

    keys = ["player", "prop_type", "game_segment", "book", "line", "recommended_side_from_book"]
    small = movement_df[keys + ["odds_move"]].copy()
    return out.merge(small, on=keys, how="left")


# =========================================================
# ARBITRAGE
# =========================================================
def find_moneyline_arbs(df):
    ml = df[df["market"] == "moneyline"].copy()
    results = []
    if ml.empty:
        return pd.DataFrame()

    for keys, group in ml.groupby(["sport", "team_a", "team_b"], dropna=False):
        selections = group["selection"].dropna().unique()
        if len(selections) < 2:
            continue

        best_rows = []
        for selection in selections:
            sub = group[group["selection"] == selection].copy()
            if sub.empty:
                continue
            best_rows.append(sub.loc[sub["dec_odds"].idxmax()])

        if len(best_rows) != 2:
            continue

        r1, r2 = best_rows
        inv_sum = (1 / r1["dec_odds"]) + (1 / r2["dec_odds"])
        if inv_sum < 1:
            results.append({
                "sport": keys[0],
                "matchup": f"{keys[1]} vs {keys[2]}",
                "side_1": r1["selection"],
                "book_1": r1["book"],
                "odds_1": int(r1["odds"]),
                "side_2": r2["selection"],
                "book_2": r2["book"],
                "odds_2": int(r2["odds"]),
                "arb_profit_pct": round((1 - inv_sum) * 100, 2),
            })

    return pd.DataFrame(results).sort_values("arb_profit_pct", ascending=False) if results else pd.DataFrame()


# =========================================================
# PROP ENGINE
# =========================================================
def hit_probability_from_edge(row):
    prop_type = normalize_text(row.get("prop_type", "points"))
    line = safe_float(row.get("line"))
    proj = safe_float(row.get("projection"))
    minutes = safe_float(row.get("minutes_projection"))
    recent_avg = safe_float(row.get("recent_avg"))
    segment = normalize_text(row.get("game_segment", "full_game"))

    if pd.isna(line) or pd.isna(proj):
        return np.nan

    sigma_map_full = {
        "points": 6.5, "rebounds": 3.0, "assists": 3.2, "3pt_made": 1.6,
        "blocks": 1.2, "steals": 1.2, "blocks_steals": 1.8, "turnovers": 1.8,
        "pra": 8.4, "pr": 6.8, "pa": 7.0, "ra": 5.2,
        "shots_on_goal": 1.9, "goals": 0.8, "power_play_points": 0.8, "saves": 5.5,
        "pass_yds": 42.0, "pass_tds": 0.9, "receptions": 2.4, "reception_yds": 21.0,
        "rush_yds": 20.0, "rush_attempts": 4.5, "sacks": 0.8, "tackles_assists": 2.5,
        "hits": 0.8, "total_bases": 1.4, "rbis": 0.8, "runs": 0.8, "walks": 0.7,
        "batter_strikeouts": 0.8, "pitcher_strikeouts": 2.2, "hits_allowed": 1.8,
        "pitcher_walks": 1.0, "earned_runs": 1.2, "pitcher_outs": 3.0,
    }
    sigma_map_1q = {
        "points": 2.6, "rebounds": 1.4, "assists": 1.5, "3pt_made": 0.9,
    }

    sigma = (sigma_map_1q if segment == "1q" else sigma_map_full).get(prop_type, 5.5 if segment != "1q" else 2.3)

    if not pd.isna(minutes):
        if segment == "1q":
            if minutes < 8:
                sigma *= 1.10
            elif minutes >= 11:
                sigma *= 0.96
        else:
            if minutes < 24:
                sigma *= 1.18
            elif minutes < 30:
                sigma *= 1.08
            elif minutes >= 36:
                sigma *= 0.95

    if not pd.isna(recent_avg) and not pd.isna(proj):
        if abs(recent_avg - proj) <= 1:
            sigma *= 0.97

    z = (proj - line) / sigma if sigma > 0 else 0
    prob_over = 0.5 * (1 + math.erf(z / math.sqrt(2)))
    return max(0.01, min(0.99, prob_over))


def confidence_warning_label(row):
    warnings = []

    injury_status = normalize_text(row.get("injury_status", ""))
    starter_status = normalize_text(row.get("starter_status", ""))
    starter_confirmed = safe_float(row.get("starter_confirmed"))
    minutes = safe_float(row.get("minutes_projection"))
    projection = safe_float(row.get("projection"))
    line = safe_float(row.get("line"))
    segment = normalize_text(row.get("game_segment", ""))

    if injury_status in ["questionable", "doubtful", "out"]:
        warnings.append(f"Injury: {injury_status}")
    if segment == "1q":
        if not pd.isna(minutes) and minutes < 8:
            warnings.append("Low 1Q minutes")
    else:
        if not pd.isna(minutes) and minutes < 26:
            warnings.append("Low minutes")
    if starter_status not in ["confirmed", "expected", "probable", "starting"]:
        if pd.isna(starter_confirmed) or starter_confirmed < 1:
            warnings.append("Starter not confirmed")
    if not pd.isna(projection) and not pd.isna(line) and abs(projection - line) < 0.4:
        warnings.append("Thin model edge")

    return "Clear" if not warnings else " | ".join(warnings)


def confidence_status(row):
    note = confidence_warning_label(row)
    if note == "Clear":
        return "✅ Clear"
    if "Injury:" in note or "Starter not confirmed" in note:
        return "⚠️ Caution"
    return "🟡 Watch"


def compute_prop_scores(df):
    if df.empty:
        return df.copy()

    out = df.copy()

    # If user has not uploaded projections, derive a neutral placeholder from line so the table still works.
    out["projection"] = np.where(pd.isna(out["projection"]), out["line"], out["projection"])
    out["minutes_projection"] = np.where(pd.isna(out["minutes_projection"]), np.where(out["game_segment"] == "1q", 9, 30), out["minutes_projection"])
    out["recent_avg"] = np.where(pd.isna(out["recent_avg"]), out["line"], out["recent_avg"])
    out["pace_factor"] = np.where(pd.isna(out["pace_factor"]), 1.0, out["pace_factor"])
    out["matchup_factor"] = np.where(pd.isna(out["matchup_factor"]), 1.0, out["matchup_factor"])
    out["is_starter"] = np.where(pd.isna(out["is_starter"]), 1, out["is_starter"])
    out["starter_confirmed"] = np.where(pd.isna(out["starter_confirmed"]), 0, out["starter_confirmed"])

    out["proj_edge"] = out["projection"] - out["line"]
    out["proj_edge_abs"] = out["proj_edge"].abs()
    out["recommended_side"] = np.where(out["projection"] > out["line"], "Over", "Under")
    out["hit_prob_over"] = out.apply(hit_probability_from_edge, axis=1)
    out["hit_prob_under"] = 1 - out["hit_prob_over"]
    out["hit_probability"] = np.where(out["recommended_side"] == "Over", out["hit_prob_over"], out["hit_prob_under"])
    out["book_implied_prob"] = out["odds"].apply(implied_prob_american)
    out["model_fair_odds"] = out["hit_probability"].apply(prob_to_american)
    out["expected_value_edge"] = ((out["hit_probability"] - out["book_implied_prob"]) * 100).round(2)

    minutes_score = np.where(
        out["game_segment"] == "1q",
        np.clip((out["minutes_projection"] / 12) * 16, 0, 16),
        np.clip((out["minutes_projection"] / 36) * 18, 0, 18)
    )
    edge_score_component = np.clip(out["proj_edge_abs"] * 6, 0, 24)
    recent_gap = (out["recent_avg"] - out["line"]).abs()
    recent_score = np.clip(recent_gap * 2.0, 0, 12)
    starter_score = np.where(out["is_starter"] >= 1, 8, 0)
    confirmed_bonus = np.where(out["starter_confirmed"] >= 1, 6, 0)
    pace_score = np.clip((out["pace_factor"] - 1.0) * 100, -4, 10)
    matchup_score = np.clip((out["matchup_factor"] - 1.0) * 100, -4, 12)
    probability_score = np.clip((out["hit_probability"] - 0.50) * 100, 0, 14)
    ev_score = np.clip(out["expected_value_edge"], 0, 10)

    price_score = np.select(
        [
            (out["odds"] >= -125) & (out["odds"] <= 140),
            (out["odds"] >= -150) & (out["odds"] < -125),
            (out["odds"] > 140) & (out["odds"] <= 200),
        ],
        [10, 7, 8],
        default=4
    )

    caution_penalty = np.select(
        [
            out["starter_confirmed"] < 1,
            out["injury_status"].fillna("").astype(str).str.lower().isin(["questionable", "doubtful"]),
            out["minutes_projection"] < np.where(out["game_segment"] == "1q", 8, 26),
        ],
        [6, 5, 4],
        default=0
    )

    out["edge_score"] = (
        minutes_score + edge_score_component + recent_score + starter_score + confirmed_bonus +
        pace_score + matchup_score + price_score + probability_score + ev_score - caution_penalty
    ).round(1)

    out["edge_score"] = np.clip(out["edge_score"], 0, 100)
    out["bet_grade"] = out["edge_score"].apply(edge_bucket)
    out["confidence_warning"] = out.apply(confidence_warning_label, axis=1)
    out["confidence_status"] = out.apply(confidence_status, axis=1)
    return out


def best_line_shop(df):
    if df.empty:
        return df.copy()

    rows = []
    group_cols = ["player", "prop_type", "game_segment", "recommended_side"]
    for _, group in df.groupby(group_cols, dropna=False):
        group = group.copy()
        side = group["recommended_side"].iloc[0]
        if side == "Over":
            group = group.sort_values(["line", "odds", "edge_score", "expected_value_edge"], ascending=[True, False, False, False])
        else:
            group = group.sort_values(["line", "odds", "edge_score", "expected_value_edge"], ascending=[False, False, False, False])
        rows.append(group.iloc[0])

    return pd.DataFrame(rows).reset_index(drop=True).sort_values(
        ["edge_score", "expected_value_edge", "hit_probability"],
        ascending=[False, False, False]
    )


def filter_props_base(df, sport="All", segment="All", starters_only=True, confirmed_only=False,
                      min_odds=-300, max_odds=200, min_edge=60, min_hit_prob=50,
                      min_ev=-5, book="All", prop_type="All"):
    out = df.copy()
    if sport != "All":
        out = out[out["sport"] == sport]
    if segment != "All":
        out = out[out["game_segment"] == segment]
    if prop_type != "All":
        out = out[out["prop_type"] == prop_type]
    if starters_only:
        out = out[out["is_starter"] >= 1]
    if confirmed_only:
        out = out[out["starter_confirmed"] >= 1]
    if book != "All":
        out = out[out["book"] == book]

    out = out[(out["odds"] >= min_odds) & (out["odds"] <= max_odds)]
    out = out[out["edge_score"] >= min_edge]
    out = out[(out["hit_probability"] * 100) >= min_hit_prob]
    out = out[out["expected_value_edge"] >= min_ev]

    return out.sort_values(
        ["edge_score", "expected_value_edge", "hit_probability", "proj_edge_abs"],
        ascending=[False, False, False, False]
    )


def build_best_bets_dashboard(df):
    if df.empty:
        return pd.DataFrame()

    cols = [
        "player", "opponent", "book", "game_segment", "prop_type", "recommended_side",
        "line", "odds", "projection", "proj_edge", "hit_probability", "expected_value_edge",
        "edge_score", "bet_grade", "confidence_status", "odds_move", "source_time"
    ]
    return df.sort_values(
        ["edge_score", "expected_value_edge", "hit_probability"],
        ascending=[False, False, False]
    )[cols].head(20).copy()


def format_props_table(df):
    out = df.copy()
    if out.empty:
        return out
    if "hit_probability" in out.columns:
        out["hit_probability"] = (out["hit_probability"] * 100).round(1)
    if "book_implied_prob" in out.columns:
        out["book_implied_prob"] = (out["book_implied_prob"] * 100).round(1)
    return out


def render_top_play_card(row, rank_num):
    st.markdown(
        f"""
<div style="padding:14px;border:1px solid #333;border-radius:12px;margin-bottom:10px;">
  <div style="font-size:18px;font-weight:700;">#{rank_num} {row['player']} — {row['recommended_side']} {row['line']} {row['prop_type']}</div>
  <div style="margin-top:4px;">{row['opponent']} • {str(row['game_segment']).upper()} • {row['book']}</div>
  <div style="margin-top:8px;">
    <b>Projection:</b> {row['projection']:.2f} |
    <b>Edge:</b> {row['proj_edge']:.2f} |
    <b>Odds:</b> {int(row['odds']) if not pd.isna(row['odds']) else 'N/A'} |
    <b>Hit %:</b> {row['hit_probability']*100:.1f}% |
    <b>EV Edge:</b> {row['expected_value_edge']:.2f}% |
    <b>Score:</b> {row['edge_score']:.1f} ({row['bet_grade']})
  </div>
  <div style="margin-top:8px;">
    <b>Confidence:</b> {row['confidence_status']} |
    <b>Notes:</b> {row['confidence_warning']}
  </div>
  <div style="margin-top:8px;">
    <b>Odds Move:</b> {row.get('odds_move', np.nan)} |
    <b>Source:</b> {row.get('source_time', '')}
  </div>
</div>
""",
        unsafe_allow_html=True
    )


# =========================================================
# SIDEBAR
# =========================================================
st.sidebar.header("V6 Real Provider Integration")

default_api_key = ""
try:
    default_api_key = st.secrets.get("THE_ODDS_API_KEY", "")
except Exception:
    default_api_key = ""

api_key = st.sidebar.text_input("The Odds API key", value=default_api_key, type="password")
sport_name = st.sidebar.selectbox("Sport", list(SPORT_KEY_MAP.keys()), index=0)
regions = st.sidebar.text_input("Regions", value="us")
bookmakers = st.sidebar.text_input("Bookmakers (optional)", value="")
odds_format = st.sidebar.selectbox("Odds format", ["american", "decimal"], index=0)
include_props = st.sidebar.checkbox("Pull event props", value=True)
best_shop_only = st.sidebar.checkbox("Best line shop only", value=True)

st.sidebar.markdown("### Optional overlay uploads")
overlay_file = st.sidebar.file_uploader(
    "Upload projection overlay (CSV/XLSX)",
    type=["csv", "xlsx"],
    help="Optional model file to add projection, minutes, recent_avg, starter fields by player + prop_type + game_segment"
)
injury_file = st.sidebar.file_uploader(
    "Upload injury/starter file (CSV/XLSX)",
    type=["csv", "xlsx"],
    help="Optional file with player, injury_status, starter_status, injury_note"
)

if st.sidebar.button("Refresh cached API data"):
    st.cache_data.clear()

if st.sidebar.button("Save current props snapshot"):
    if "latest_props_live" in st.session_state and not st.session_state["latest_props_live"].empty:
        snap_name = f"the_odds_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        save_snapshot_to_session(snap_name, append_snapshot(st.session_state["latest_props_live"], snap_name))
        st.sidebar.success(f"Saved {snap_name}")
    else:
        st.sidebar.warning("No props loaded yet.")


# =========================================================
# LOAD DATA
# =========================================================
provider_ok = bool(api_key)

if provider_ok:
    raw_odds, raw_props, provider_error = fetch_full_odds_and_props(
        api_key=api_key,
        sport_name=sport_name,
        regions=regions,
        bookmakers=bookmakers,
        odds_format=odds_format,
        include_props=include_props,
    )
else:
    raw_odds = pd.DataFrame()
    raw_props = pd.DataFrame()
    provider_error = "Missing The Odds API key."

odds_df = prepare_odds_df(raw_odds)
props_df = prepare_props_df(raw_props)

overlay_df = prepare_model_overlay_df(load_csv_or_empty(overlay_file))
injuries_df = prepare_injuries_df(load_csv_or_empty(injury_file))

props_df = apply_model_overlay(props_df, overlay_df)
props_df = apply_injuries(props_df, injuries_df)
props_scored = compute_prop_scores(props_df)

previous_snapshot = get_snapshot_from_session("latest_props_live")
movement_df = build_line_movement_from_snapshots(previous_snapshot, props_scored)
props_live = apply_movement_to_props(props_scored, movement_df)
props_shop = best_line_shop(props_live)

st.session_state["latest_props_live"] = append_snapshot(props_scored, "latest_props_live")

source_status = pd.DataFrame([
    ["Provider", "The Odds API", "Connected" if provider_ok and provider_error is None else f"Not connected: {provider_error}"],
    ["Featured odds rows", len(odds_df), "Live"],
    ["Props rows", len(props_live), "Live" if include_props else "Skipped"],
    ["Projection overlay rows", len(overlay_df), "Upload" if not overlay_df.empty else "Not loaded"],
    ["Injury/starter rows", len(injuries_df), "Upload/sample"],
], columns=["Feed", "Value", "Status"])


# =========================================================
# TABS
# =========================================================
tab_home, tab_best, tab_sections, tab_arb, tab_inj, tab_provider = st.tabs([
    "Home",
    "Best Bets",
    "Prop Sections",
    "Arbitrage",
    "Injuries / Starters",
    "Provider",
])


# =========================================================
# HOME
# =========================================================
with tab_home:
    st.subheader("V6 Real Provider Build")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Odds Rows", len(odds_df))
    c2.metric("Props Rows", len(props_live))
    c3.metric("Books", max(odds_df["book"].nunique() if not odds_df.empty else 0, props_live["book"].nunique() if not props_live.empty else 0))
    c4.metric("Updated", current_ts_str())

    st.markdown("### Feed status")
    st.dataframe(source_status, use_container_width=True)

    if provider_error:
        st.warning(provider_error)

    st.markdown("### Notes")
    st.write("• Featured odds come directly from The Odds API.")
    st.write("• Event props come directly from The Odds API event endpoint when enabled.")
    st.write("• Projections, minutes, and starter confirmations can be layered in with your own upload.")
    st.write("• Injury/starter upload is optional and overrides default unknown status.")
    st.write("• Snapshot button saves the current prop board and computes odds movement on the next refresh.")


# =========================================================
# BEST BETS
# =========================================================
with tab_best:
    st.subheader("Auto Best Bets Board")

    sport_opts = ["All"] + sorted(props_shop["sport"].dropna().astype(str).unique().tolist()) if not props_shop.empty else ["All"]
    segment_opts = ["All"] + sorted(props_shop["game_segment"].dropna().astype(str).unique().tolist()) if not props_shop.empty else ["All"]
    prop_opts = ["All"] + sorted(props_shop["prop_type"].dropna().astype(str).unique().tolist()) if not props_shop.empty else ["All"]
    book_opts = ["All"] + sorted(props_shop["book"].dropna().astype(str).unique().tolist()) if not props_shop.empty else ["All"]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        selected_sport = st.selectbox("Sport", sport_opts, key="v6_sport")
    with c2:
        selected_segment = st.selectbox("Segment", segment_opts, key="v6_segment")
    with c3:
        selected_prop = st.selectbox("Prop Type", prop_opts, key="v6_prop")
    with c4:
        selected_book = st.selectbox("Book", book_opts, key="v6_book")

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        starters_only = st.checkbox("Starters Only", value=True)
    with c6:
        confirmed_only = st.checkbox("Confirmed Only", value=False)
    with c7:
        min_edge = st.slider("Min Edge Score", 0, 100, 60, 5)
    with c8:
        min_hit = st.slider("Min Hit %", 50, 95, 50, 1)

    c9, c10, c11 = st.columns(3)
    with c9:
        min_odds = st.slider("Min Odds", -300, 200, -300, 5)
    with c10:
        max_odds = st.slider("Max Odds", -300, 200, 200, 5)
    with c11:
        min_ev = st.slider("Min EV Edge %", -10, 25, -5, 1)

    base_df = props_shop.copy() if best_shop_only else props_live.copy()
    filtered = filter_props_base(
        base_df,
        sport=selected_sport,
        segment=selected_segment,
        starters_only=starters_only,
        confirmed_only=confirmed_only,
        min_odds=min_odds,
        max_odds=max_odds,
        min_edge=min_edge,
        min_hit_prob=min_hit,
        min_ev=min_ev,
        book=selected_book,
        prop_type=selected_prop,
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Props Found", len(filtered))
    m2.metric("A-Grade", int((filtered["edge_score"] >= 86).sum()) if not filtered.empty else 0)
    m3.metric("Avg Edge", round(filtered["edge_score"].mean(), 1) if not filtered.empty else 0)
    m4.metric("Avg Hit %", f"{round(filtered['hit_probability'].mean() * 100, 1) if not filtered.empty else 0}%")

    if filtered.empty:
        st.warning("No props match the current filters.")
    else:
        st.markdown("### Top play cards")
        for idx, (_, row) in enumerate(filtered.head(10).iterrows(), start=1):
            render_top_play_card(row, idx)

        st.markdown("### Best bets table")
        st.dataframe(format_props_table(build_best_bets_dashboard(filtered)), use_container_width=True)


# =========================================================
# PROP SECTIONS
# =========================================================
with tab_sections:
    st.subheader("Prop Sections by Market")
    if props_live.empty:
        st.info("No props loaded.")
    else:
        table_cols = [
            "player", "opponent", "book", "game_segment", "recommended_side",
            "line", "projection", "proj_edge", "odds", "hit_probability",
            "expected_value_edge", "edge_score", "bet_grade", "confidence_status",
            "odds_move", "source_time"
        ]

        for title, prop_key in [
            ("Points", "points"),
            ("Rebounds", "rebounds"),
            ("Assists", "assists"),
            ("3PT Made", "3pt_made"),
            ("PRA", "pra"),
            ("1Q Points", "points"),
        ]:
            section = props_live[props_live["prop_type"] == prop_key].copy()
            if title == "1Q Points":
                section = section[section["game_segment"] == "1q"]

            st.markdown(f"### {title}")
            if section.empty:
                st.info(f"No {title.lower()} props loaded.")
            else:
                st.dataframe(format_props_table(section[table_cols]), use_container_width=True)


# =========================================================
# ARBITRAGE
# =========================================================
with tab_arb:
    st.subheader("Moneyline Arbitrage")
    sports = ["All"] + sorted(odds_df["sport"].dropna().astype(str).unique().tolist()) if not odds_df.empty else ["All"]
    selected_arb_sport = st.selectbox("Sport", sports, key="v6_arb_sport")

    arb_base = odds_df.copy()
    if selected_arb_sport != "All":
        arb_base = arb_base[arb_base["sport"] == selected_arb_sport]

    arb_results = find_moneyline_arbs(arb_base)
    if arb_results.empty:
        st.warning("No moneyline arbitrage opportunities detected.")
    else:
        st.dataframe(arb_results, use_container_width=True)


# =========================================================
# INJURIES / STARTERS
# =========================================================
with tab_inj:
    st.subheader("Injury / Starter Layer")
    st.dataframe(injuries_df, use_container_width=True)

    st.markdown("### Props with caution flags")
    caution_df = props_live[props_live["confidence_status"] != "✅ Clear"].copy() if not props_live.empty else pd.DataFrame()
    if caution_df.empty:
        st.info("No caution flags.")
    else:
        cols = [
            "player", "book", "prop_type", "game_segment", "line", "odds",
            "injury_status", "starter_status", "starter_confirmed",
            "confidence_status", "confidence_warning", "edge_score"
        ]
        st.dataframe(caution_df[cols], use_container_width=True)


# =========================================================
# PROVIDER
# =========================================================
with tab_provider:
    st.subheader("The Odds API Integration Details")
    st.write("This build is wired for live featured markets and event props through The Odds API.")
    st.markdown("### Current live settings")
    st.write(f"Sport key: {SPORT_KEY_MAP[sport_name]}")
    st.write(f"Regions: {regions}")
    st.write(f"Bookmakers: {bookmakers if bookmakers else 'all in selected region'}")
    st.write(f"Props enabled: {'Yes' if include_props else 'No'}")

    st.markdown("### Streamlit secrets")
    st.code('THE_ODDS_API_KEY="your_real_key"', language="toml")

    st.markdown("### Optional overlay file columns")
    st.write("player, prop_type, game_segment, projection, minutes_projection, recent_avg, is_starter, starter_status, starter_confirmed, pace_factor, matchup_factor")

    if not props_live.empty:
        st.markdown("### Raw props preview")
        st.dataframe(props_live.head(50), use_container_width=True)


st.markdown("---")
st.caption("V6 full clean build — real The Odds API integration for featured odds and event props.")
