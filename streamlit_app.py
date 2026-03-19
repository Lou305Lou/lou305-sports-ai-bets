import math
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
import requests
import streamlit as st


st.set_page_config(
    page_title="Sports AI Betting Dashboard V7.2",
    page_icon="🏀",
    layout="wide",
)

st.title("🏀 Sports AI Betting Dashboard V7.2")
st.caption("Full Props Production Build • The Odds API + SportsDataIO + Projection CSV")


DEFAULT_TIMEOUT = 20
THE_ODDS_API_HOST = "https://api.the-odds-api.com"

SPORT_KEY_MAP = {
    "NBA": "basketball_nba",
    "WNBA": "basketball_wnba",
    "NHL": "icehockey_nhl",
    "MLB": "baseball_mlb",
    "NFL": "americanfootball_nfl",
}

PLAYER_PROP_MARKETS = {
    "NBA": [
        "player_points", "player_points_q1",
        "player_rebounds", "player_rebounds_q1",
        "player_assists", "player_assists_q1",
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
        "player_points", "player_points_q1",
        "player_rebounds", "player_rebounds_q1",
        "player_assists", "player_assists_q1",
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


def current_ts_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def add_missing_cols(df, defaults):
    for col, default in defaults.items():
        if col not in df.columns:
            df[col] = default
    return df


def american_to_decimal(odds):
    try:
        odds = float(odds)
        return 1 + (odds / 100) if odds > 0 else 1 + (100 / abs(odds))
    except Exception:
        return np.nan


def implied_prob_american(odds):
    try:
        odds = float(odds)
        return 100 / (odds + 100) if odds > 0 else abs(odds) / (abs(odds) + 100)
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


def edge_bucket(score):
    if score >= 86:
        return "🟢 A"
    if score >= 76:
        return "🟢 B"
    if score >= 66:
        return "🟡 C"
    return "🔴 Pass"


def chunk_list(items, chunk_size):
    if chunk_size <= 0:
        return [items]
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def clean_market_name(x):
    x = normalize_text(x)
    mapping = {
        "h2h": "moneyline",
        "moneyline": "moneyline",
        "spreads": "spreads",
        "totals": "totals",
    }
    return mapping.get(x, x)


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
def get_json(url: str, headers: Optional[dict] = None, params: Optional[dict] = None):
    if not url:
        return None, "Missing URL"
    try:
        response = requests.get(
            url,
            headers=headers or {"Accept": "application/json"},
            params=params or {},
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        return response.json(), None
    except Exception as e:
        return None, str(e)


def the_odds_get(path: str, api_key: str, params: Optional[dict] = None):
    url = f"{THE_ODDS_API_HOST}{path}"
    merged = dict(params or {})
    merged["apiKey"] = api_key
    return get_json(url, headers={"Accept": "application/json"}, params=merged)


@st.cache_data(ttl=60, show_spinner=False)
def fetch_featured_odds_from_the_odds_api(
    api_key: str,
    sport_key: str,
    regions: str,
    bookmakers: str,
    odds_format: str,
):
    params = {
        "regions": regions,
        "markets": "h2h,spreads,totals",
        "oddsFormat": odds_format,
    }
    if bookmakers:
        params["bookmakers"] = bookmakers
    return the_odds_get(f"/v4/sports/{sport_key}/odds", api_key=api_key, params=params)


@st.cache_data(ttl=60, show_spinner=False)
def fetch_event_props_from_the_odds_api(
    api_key: str,
    sport_key: str,
    event_id: str,
    markets_csv: str,
    regions: str,
    bookmakers: str,
    odds_format: str,
):
    params = {
        "regions": regions,
        "markets": markets_csv,
        "oddsFormat": odds_format,
    }
    if bookmakers:
        params["bookmakers"] = bookmakers
    return the_odds_get(
        f"/v4/sports/{sport_key}/events/{event_id}/odds",
        api_key=api_key,
        params=params,
    )


def parse_featured_odds_payload(payload, sport_title_fallback: str):
    rows = []
    events = payload if isinstance(payload, list) else []

    for event in events:
        sport_title = event.get("sport_title", sport_title_fallback)
        event_id = event.get("id", "")
        home_team = event.get("home_team", "")
        away_team = event.get("away_team", "")
        commence_time = event.get("commence_time", "")

        for book in event.get("bookmakers", []) or []:
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

    for book in payload.get("bookmakers", []) or []:
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

                if not desc or pd.isna(point) or name not in ["Over", "Under"]:
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
                    "projection": np.nan,
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
                })

    return pd.DataFrame(rows)


def fetch_live_the_odds_bundle(
    api_key: str,
    sport_name: str,
    regions: str,
    bookmakers: str,
    odds_format: str,
    include_props: bool,
):
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
        prop_chunks = chunk_list(PLAYER_PROP_MARKETS.get(sport_name, []), 5)
        event_ids = [e.get("id", "") for e in featured_payload if e.get("id")] if isinstance(featured_payload, list) else []
        parts = []

        for event_id in event_ids:
            for chunk in prop_chunks:
                payload, _ = fetch_event_props_from_the_odds_api(
                    api_key=api_key,
                    sport_key=sport_key,
                    event_id=event_id,
                    markets_csv=",".join(chunk),
                    regions=regions,
                    bookmakers=bookmakers,
                    odds_format=odds_format,
                )
                if payload is not None:
                    parsed = parse_event_props_payload(payload, sport_name)
                    if not parsed.empty:
                        parts.append(parsed)

        if parts:
            props_df = pd.concat(parts, ignore_index=True).drop_duplicates()

    return odds_df, props_df, None
    def pull_first_list(payload):
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ["data", "results", "items", "rows", "players", "projections", "injuries", "lineups"]:
            if key in payload and isinstance(payload[key], list):
                return payload[key]
    return []


@st.cache_data(ttl=90, show_spinner=False)
def fetch_sportsdataio_json(url: str, api_key: str, auth_mode: str, api_key_header_name: str, api_key_query_name: str):
    if not url:
        return None, "Missing SportsDataIO URL"

    params = {}
    headers = {"Accept": "application/json"}

    if auth_mode == "header_custom":
        if api_key and api_key_header_name:
            headers[api_key_header_name] = api_key
    elif auth_mode == "query_param":
        if api_key and api_key_query_name:
            params[api_key_query_name] = api_key
    else:
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

    return get_json(url, headers=headers, params=params)


def parse_sportsdataio_injuries_payload(payload, sport_name: str):
    rows = []
    for item in pull_first_list(payload):
        rows.append({
            "sport": sport_name,
            "team": item.get("Team") or item.get("team") or "",
            "player": item.get("Name") or item.get("PlayerName") or item.get("player") or item.get("name") or "",
            "injury_status": str(item.get("InjuryStatus") or item.get("Status") or item.get("status") or "unknown").strip().lower(),
            "starter_status": normalize_text(item.get("StartingStatus", item.get("starter_status", "unknown"))),
            "injury_note": item.get("InjuryNotes") or item.get("InjuryNote") or item.get("News") or item.get("note") or "",
            "source_time": current_ts_str(),
        })
    return pd.DataFrame(rows)


def parse_sportsdataio_lineups_payload(payload, sport_name: str):
    rows = []
    for item in pull_first_list(payload):
        status = normalize_text(item.get("Status", item.get("StartingStatus", item.get("starter_status", "confirmed"))))
        rows.append({
            "sport": sport_name,
            "player": item.get("Name") or item.get("PlayerName") or item.get("player") or item.get("name") or "",
            "is_starter": 1 if bool(item.get("IsStarter", item.get("is_starter", True))) else 0,
            "starter_status": status,
            "starter_confirmed": 1 if status in ["confirmed", "starting", "expected", "probable"] else 0,
            "team": item.get("Team") or item.get("team") or "",
        })
    return pd.DataFrame(rows)


def load_csv_or_empty(uploaded_file):
    if uploaded_file is None:
        return pd.DataFrame()
    try:
        if str(uploaded_file.name).lower().endswith(".csv"):
            return pd.read_csv(uploaded_file)
        return pd.read_excel(uploaded_file)
    except Exception:
        return pd.DataFrame()


def sample_full_props_projection_template():
    rows = [
        ["NBA", "Jalen Brunson", "points", "full_game", 30.4, 36, 31.1, 1.04, 1.02, "Knicks"],
        ["NBA", "Jalen Brunson", "assists", "full_game", 7.8, 36, 7.2, 1.04, 1.02, "Knicks"],
        ["NBA", "Jalen Brunson", "3pt_made", "full_game", 2.9, 36, 2.7, 1.04, 1.02, "Knicks"],
        ["NBA", "Jalen Brunson", "pra", "full_game", 44.6, 36, 43.0, 1.04, 1.02, "Knicks"],
        ["NBA", "Stephen Curry", "points", "1q", 8.2, 10, 7.7, 1.03, 1.01, "Warriors"],
        ["NBA", "Stephen Curry", "3pt_made", "1q", 1.7, 10, 1.5, 1.03, 1.01, "Warriors"],
    ]
    return pd.DataFrame(rows, columns=[
        "sport", "player", "prop_type", "game_segment", "projection",
        "minutes_projection", "recent_avg", "pace_factor", "matchup_factor", "team"
    ])


def prepare_odds_df(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=["sport", "event_id", "team_a", "team_b", "book", "market", "point", "total", "selection", "odds"])
    out = df.copy()
    out["market"] = out["market"].apply(clean_market_name)
    out["odds"] = pd.to_numeric(out["odds"], errors="coerce")
    out["point"] = pd.to_numeric(out.get("point", np.nan), errors="coerce")
    out["total"] = pd.to_numeric(out.get("total", np.nan), errors="coerce")
    out["dec_odds"] = out["odds"].apply(american_to_decimal)
    out["imp_prob"] = out["odds"].apply(implied_prob_american)
    return out


def prepare_props_df(df):
    defaults = {
        "sport": "", "event_id": "", "player": "", "team": "", "opponent": "",
        "is_starter": 1, "starter_status": "unknown", "starter_confirmed": 0,
        "prop_type": "", "line": np.nan, "projection": np.nan,
        "minutes_projection": np.nan, "recent_avg": np.nan, "last_5_games": 5,
        "pace_factor": 1.0, "matchup_factor": 1.0, "odds": np.nan,
        "game_segment": "full_game", "book": "Unknown",
        "recommended_side_from_book": "", "source_time": "",
        "injury_status": "unknown", "injury_note": "",
        "proj_edge": np.nan, "proj_edge_abs": np.nan,
        "recommended_side": "", "hit_prob_over": np.nan,
        "hit_prob_under": np.nan, "hit_probability": np.nan,
        "book_implied_prob": np.nan, "model_fair_odds": np.nan,
        "expected_value_edge": np.nan, "edge_score": np.nan,
        "bet_grade": "", "confidence_warning": "",
        "confidence_status": "", "odds_move": np.nan,
    }

    if df is None or df.empty:
        return pd.DataFrame(columns=list(defaults.keys()))

    out = df.copy()
    out.columns = [c.strip().lower() for c in out.columns]
    out = add_missing_cols(out, defaults)

    for col in ["is_starter", "starter_confirmed", "line", "projection", "minutes_projection", "recent_avg", "last_5_games", "pace_factor", "matchup_factor", "odds"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    for col in ["sport", "event_id", "player", "team", "opponent", "starter_status", "prop_type", "game_segment", "book", "recommended_side_from_book", "source_time", "injury_status", "injury_note", "recommended_side", "bet_grade", "confidence_warning", "confidence_status"]:
        out[col] = out[col].fillna("").astype(str)

    out["prop_type"] = out["prop_type"].apply(normalize_text)
    out["game_segment"] = out["game_segment"].apply(normalize_text)
    out["starter_status"] = out["starter_status"].apply(normalize_text)
    out["injury_status"] = out["injury_status"].apply(normalize_text)
    return out


def prepare_injuries_df(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=["sport", "team", "player", "injury_status", "starter_status", "injury_note", "source_time"])
    out = df.copy()
    out.columns = [c.strip().lower() for c in out.columns]
    out = add_missing_cols(out, {
        "sport": "", "team": "", "player": "", "injury_status": "unknown",
        "starter_status": "unknown", "injury_note": "", "source_time": current_ts_str(),
    })
    for col in ["sport", "team", "player", "injury_status", "starter_status", "injury_note", "source_time"]:
        out[col] = out[col].fillna("").astype(str)
    out["injury_status"] = out["injury_status"].apply(normalize_text)
    out["starter_status"] = out["starter_status"].apply(normalize_text)
    return out


def prepare_lineups_df(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=["sport", "player", "is_starter", "starter_status", "starter_confirmed", "team"])
    out = df.copy()
    out.columns = [c.strip().lower() for c in out.columns]
    out = add_missing_cols(out, {
        "sport": "", "player": "", "is_starter": np.nan,
        "starter_status": "unknown", "starter_confirmed": np.nan, "team": "",
    })
    for col in ["is_starter", "starter_confirmed"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    for col in ["sport", "player", "starter_status", "team"]:
        out[col] = out[col].fillna("").astype(str)
    out["starter_status"] = out["starter_status"].apply(normalize_text)
    return out
    def prepare_projection_overlay_df(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=["sport", "player", "prop_type", "game_segment", "projection", "minutes_projection", "recent_avg", "pace_factor", "matchup_factor", "team"])
    out = df.copy()
    out.columns = [c.strip().lower() for c in out.columns]
    out = add_missing_cols(out, {
        "sport": "", "player": "", "prop_type": "", "game_segment": "full_game",
        "projection": np.nan, "minutes_projection": np.nan, "recent_avg": np.nan,
        "pace_factor": np.nan, "matchup_factor": np.nan, "team": "",
    })
    for col in ["projection", "minutes_projection", "recent_avg", "pace_factor", "matchup_factor"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    for col in ["sport", "player", "prop_type", "game_segment", "team"]:
        out[col] = out[col].fillna("").astype(str)
    out["prop_type"] = out["prop_type"].apply(normalize_text)
    out["game_segment"] = out["game_segment"].apply(normalize_text)
    return out


def apply_projection_overlay(props_df, overlay_df):
    if props_df.empty or overlay_df.empty:
        return props_df.copy()

    keys = ["player", "prop_type", "game_segment"]
    overlay = overlay_df.drop_duplicates(subset=keys, keep="last")
    merged = props_df.merge(overlay, on=keys, how="left", suffixes=("", "_overlay"))

    for col in ["projection", "minutes_projection", "recent_avg", "pace_factor", "matchup_factor", "team"]:
        overlay_col = f"{col}_overlay"
        if overlay_col in merged.columns:
            if merged[col].dtype == object:
                merged[col] = np.where(
                    merged[overlay_col].fillna("").astype(str).str.len() > 0,
                    merged[overlay_col],
                    merged[col],
                )
            else:
                merged[col] = np.where(~pd.isna(merged[overlay_col]), merged[overlay_col], merged[col])

    return merged.drop(columns=[c for c in merged.columns if c.endswith("_overlay")])


def apply_lineups(props_df, lineups_df):
    if props_df.empty or lineups_df.empty:
        return props_df.copy()

    lineup_small = lineups_df.drop_duplicates(subset=["player"], keep="last")
    merged = props_df.merge(
        lineup_small[["player", "is_starter", "starter_status", "starter_confirmed", "team"]],
        on="player",
        how="left",
        suffixes=("", "_lineup"),
    )

    for col in ["is_starter", "starter_confirmed"]:
        if f"{col}_lineup" in merged.columns:
            merged[col] = np.where(~pd.isna(merged[f"{col}_lineup"]), merged[f"{col}_lineup"], merged[col])

    for col in ["starter_status", "team"]:
        if f"{col}_lineup" in merged.columns:
            merged[col] = np.where(
                merged[f"{col}_lineup"].fillna("").astype(str).str.len() > 0,
                merged[f"{col}_lineup"],
                merged[col],
            )

    return merged.drop(columns=[c for c in merged.columns if c.endswith("_lineup")])


def apply_injuries(props_df, injuries_df):
    if props_df.empty:
        return props_df.copy()

    out = props_df.copy()
    if injuries_df.empty:
        out["injury_status"] = "unknown"
        out["injury_note"] = ""
        return out

    inj_small = injuries_df.drop_duplicates(subset=["player"], keep="last")
    merged = out.merge(
        inj_small[["player", "injury_status", "starter_status", "injury_note"]],
        on="player",
        how="left",
        suffixes=("", "_inj"),
    )

    merged["injury_status"] = merged["injury_status"].fillna("unknown")
    merged["injury_note"] = merged["injury_note"].fillna("")
    merged["starter_status"] = np.where(
        merged["starter_status_inj"].fillna("").astype(str).str.len() > 0,
        merged["starter_status_inj"],
        merged["starter_status"],
    )

    return merged.drop(columns=[c for c in merged.columns if c.endswith("_inj")])


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


def build_odds_move_from_snapshots(old_df, new_df):
    if old_df.empty or new_df.empty:
        return pd.DataFrame()
    keys = ["player", "prop_type", "game_segment", "book", "line", "recommended_side_from_book"]
    old_small = old_df[keys + ["odds"]].rename(columns={"odds": "old_odds"})
    new_small = new_df[keys + ["odds"]].rename(columns={"odds": "new_odds"})
    merged = new_small.merge(old_small, on=keys, how="left")
    merged["odds_move"] = merged["new_odds"] - merged["old_odds"]
    return merged


def apply_odds_move(props_df, movement_df):
    if props_df.empty:
        return props_df.copy()
    out = props_df.copy()
    if movement_df.empty:
        out["odds_move"] = np.nan
        return out
    keys = ["player", "prop_type", "game_segment", "book", "line", "recommended_side_from_book"]
    return out.merge(movement_df[keys + ["odds_move"]], on=keys, how="left")


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
    def hit_probability_from_edge(row):
    prop_type = normalize_text(row.get("prop_type", "points"))
    line = safe_float(row.get("line"))
    proj = safe_float(row.get("projection"))
    minutes = safe_float(row.get("minutes_projection"))
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
    sigma_map_1q = {"points": 2.6, "rebounds": 1.4, "assists": 1.5, "3pt_made": 0.9}
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
    out = prepare_props_df(df)
    if out.empty:
        return out

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
        np.clip((out["minutes_projection"] / 36) * 18, 0, 18),
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
        default=4,
    )

    caution_penalty = np.select(
        [
            out["starter_confirmed"] < 1,
            out["injury_status"].fillna("").astype(str).str.lower().isin(["questionable", "doubtful"]),
            out["minutes_projection"] < np.where(out["game_segment"] == "1q", 8, 26),
        ],
        [6, 5, 4],
        default=0,
    )

    out["edge_score"] = (
        minutes_score + edge_score_component + recent_score + starter_score +
        confirmed_bonus + pace_score + matchup_score + price_score +
        probability_score + ev_score - caution_penalty
    ).round(1)

    out["edge_score"] = np.clip(out["edge_score"], 0, 100)
    out["bet_grade"] = out["edge_score"].apply(edge_bucket)
    out["confidence_warning"] = out.apply(confidence_warning_label, axis=1)
    out["confidence_status"] = out.apply(confidence_status, axis=1)

    return out


def best_line_shop(df):
    out = prepare_props_df(df)
    if out.empty:
        return out

    rows = []
    group_cols = ["player", "prop_type", "game_segment", "recommended_side"]
    for _, group in out.groupby(group_cols, dropna=False):
        group = group.copy()
        side = group["recommended_side"].iloc[0]
        if side == "Over":
            group = group.sort_values(["line", "odds", "edge_score", "expected_value_edge"], ascending=[True, False, False, False])
        else:
            group = group.sort_values(["line", "odds", "edge_score", "expected_value_edge"], ascending=[False, False, False, False])
        rows.append(group.iloc[0])

    return pd.DataFrame(rows).reset_index(drop=True).sort_values(
        ["edge_score", "expected_value_edge", "hit_probability"],
        ascending=[False, False, False],
    )


def filter_props_base(df, sport="All", segment="All", starters_only=True, confirmed_only=False, min_odds=-300, max_odds=200, min_edge=60, min_hit_prob=50, min_ev=-5, book="All", prop_type="All"):
    out = prepare_props_df(df)

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
        ascending=[False, False, False, False],
    )


def build_best_bets_dashboard(df):
    out = prepare_props_df(df)
    cols = [
        "player", "opponent", "book", "game_segment", "prop_type", "recommended_side",
        "line", "odds", "projection", "proj_edge", "hit_probability",
        "expected_value_edge", "edge_score", "bet_grade", "confidence_status",
        "odds_move", "source_time",
    ]
    if out.empty:
        return pd.DataFrame(columns=cols)
    return out.sort_values(
        ["edge_score", "expected_value_edge", "hit_probability"],
        ascending=[False, False, False],
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
        unsafe_allow_html=True,
    )
    st.sidebar.header("Provider 1: The Odds API")

the_odds_api_key = ""
try:
    the_odds_api_key = st.secrets.get("THE_ODDS_API_KEY", "")
except Exception:
    pass

if not the_odds_api_key:
    try:
        the_odds_api_key = st.secrets.get("ODDS_API_KEY", "")
    except Exception:
        pass

the_odds_api_key = st.sidebar.text_input("The Odds API key", value=the_odds_api_key, type="password")
sport_name = st.sidebar.selectbox("Sport", list(SPORT_KEY_MAP.keys()), index=0)
regions = st.sidebar.text_input("Regions", value="us")
bookmakers = st.sidebar.text_input("Bookmakers (optional)", value="")
odds_format = st.sidebar.selectbox("Odds format", ["american", "decimal"], index=0)
include_props = st.sidebar.checkbox("Pull event props", value=True)
best_shop_only = st.sidebar.checkbox("Best line shop only", value=True)

st.sidebar.markdown("### Provider 2: SportsDataIO")
sportsdataio_api_key = ""
sportsdataio_auth_mode = "query_param"
sportsdataio_api_key_header = "Ocp-Apim-Subscription-Key"
sportsdataio_api_key_query = "key"
injuries_url = ""
lineups_url = ""

try:
    sportsdataio_api_key = st.secrets.get("SPORTSDATAIO_API_KEY", "")
    injuries_url = st.secrets.get("SPORTSDATAIO_INJURIES_URL", "")
    lineups_url = st.secrets.get("SPORTSDATAIO_LINEUPS_URL", "")
    sportsdataio_auth_mode = st.secrets.get("SPORTSDATAIO_AUTH_MODE", "query_param")
    sportsdataio_api_key_header = st.secrets.get("SPORTSDATAIO_API_KEY_HEADER", "Ocp-Apim-Subscription-Key")
    sportsdataio_api_key_query = st.secrets.get("SPORTSDATAIO_API_KEY_QUERY", "key")
except Exception:
    pass

sportsdataio_api_key = st.sidebar.text_input("SportsDataIO key", value=sportsdataio_api_key, type="password")
sportsdataio_auth_mode = st.sidebar.selectbox("SportsDataIO auth mode", ["query_param", "header_custom", "bearer"], index=["query_param", "header_custom", "bearer"].index(sportsdataio_auth_mode if sportsdataio_auth_mode in ["query_param", "header_custom", "bearer"] else "query_param"))
sportsdataio_api_key_header = st.sidebar.text_input("Custom header name", value=sportsdataio_api_key_header)
sportsdataio_api_key_query = st.sidebar.text_input("Query key name", value=sportsdataio_api_key_query)
injuries_url = st.sidebar.text_input("Injuries endpoint URL", value=injuries_url)
lineups_url = st.sidebar.text_input("Lineups endpoint URL", value=lineups_url)

st.sidebar.markdown("### Full Props Projection CSV")
projection_file = st.sidebar.file_uploader(
    "Upload full props projections (CSV/XLSX)",
    type=["csv", "xlsx"],
    help="Use player + prop_type + game_segment + projection as the core columns.",
)

if st.sidebar.button("Refresh cached provider data"):
    st.cache_data.clear()

if st.sidebar.button("Save current props snapshot"):
    if "latest_props_live" in st.session_state and not st.session_state["latest_props_live"].empty:
        snap_name = f"v72_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        save_snapshot_to_session(snap_name, append_snapshot(st.session_state["latest_props_live"], snap_name))
        st.sidebar.success(f"Saved {snap_name}")
    else:
        st.sidebar.warning("No props loaded yet.")


provider1_ok = bool(the_odds_api_key)
if provider1_ok:
    raw_odds, raw_props, provider1_error = fetch_live_the_odds_bundle(
        the_odds_api_key, sport_name, regions, bookmakers, odds_format, include_props
    )
else:
    raw_odds = pd.DataFrame()
    raw_props = pd.DataFrame()
    provider1_error = "Missing The Odds API key."

inj_payload, inj_err = fetch_sportsdataio_json(
    injuries_url, sportsdataio_api_key, sportsdataio_auth_mode, sportsdataio_api_key_header, sportsdataio_api_key_query
) if injuries_url else (None, "No injuries URL")

lineups_payload, lineups_err = fetch_sportsdataio_json(
    lineups_url, sportsdataio_api_key, sportsdataio_auth_mode, sportsdataio_api_key_header, sportsdataio_api_key_query
) if lineups_url else (None, "No lineups URL")

odds_df = prepare_odds_df(raw_odds)
props_df = prepare_props_df(raw_props)
injuries_df = prepare_injuries_df(parse_sportsdataio_injuries_payload(inj_payload, sport_name))
lineups_df = prepare_lineups_df(parse_sportsdataio_lineups_payload(lineups_payload, sport_name))
proj_df = prepare_projection_overlay_df(load_csv_or_empty(projection_file))

props_df = apply_projection_overlay(props_df, proj_df)
props_df = apply_lineups(props_df, lineups_df)
props_df = apply_injuries(props_df, injuries_df)
props_scored = compute_prop_scores(props_df)

previous_snapshot = get_snapshot_from_session("latest_props_live")
movement_df = build_odds_move_from_snapshots(previous_snapshot, props_scored)
props_live = apply_odds_move(props_scored, movement_df)
props_shop = best_line_shop(props_live)

st.session_state["latest_props_live"] = append_snapshot(props_scored, "latest_props_live")

source_status = pd.DataFrame([
    ["Provider 1", "The Odds API", "Connected" if provider1_ok and provider1_error is None else f"Not connected: {provider1_error}"],
    ["Provider 2", "SportsDataIO", "Configured" if bool(sportsdataio_api_key) else "Key missing"],
    ["Odds Rows", len(odds_df), "Live"],
    ["Props Rows", len(props_live), "Live" if include_props else "Skipped"],
    ["Injuries Rows", len(injuries_df), "Loaded" if inj_payload is not None else f"Not loaded: {inj_err}"],
    ["Lineups Rows", len(lineups_df), "Loaded" if lineups_payload is not None else f"Not loaded: {lineups_err}"],
    ["Projection CSV Rows", len(proj_df), "Loaded" if not proj_df.empty else "Not loaded"],
], columns=["Feed", "Value", "Status"])

tab_home, tab_best, tab_sections, tab_arb, tab_inj, tab_template = st.tabs([
    "Home", "Best Bets", "Prop Sections", "Arbitrage", "Injuries / Starters", "Projection Template"
])

with tab_home:
    st.subheader("V7.2 Home")
    c1, c2, c3 = st.columns(3)
    c1.metric("Odds Rows", len(odds_df))
    c2.metric("Props Rows", len(props_live))
    c3.metric("Books", max(odds_df["book"].nunique() if not odds_df.empty else 0, props_live["book"].nunique() if not props_live.empty else 0))
    st.markdown("### Feed status")
    st.dataframe(source_status, use_container_width=True)

with tab_best:
    st.subheader("Auto Best Bets Board")

    sport_opts = ["All"] + sorted(props_shop["sport"].dropna().astype(str).unique().tolist()) if not props_shop.empty else ["All"]
    segment_opts = ["All"] + sorted(props_shop["game_segment"].dropna().astype(str).unique().tolist()) if not props_shop.empty else ["All"]
    prop_opts = ["All"] + sorted(props_shop["prop_type"].dropna().astype(str).unique().tolist()) if not props_shop.empty else ["All"]
    book_opts = ["All"] + sorted(props_shop["book"].dropna().astype(str).unique().tolist()) if not props_shop.empty else ["All"]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        selected_sport = st.selectbox("Sport", sport_opts)
    with c2:
        selected_segment = st.selectbox("Segment", segment_opts)
    with c3:
        selected_prop = st.selectbox("Prop Type", prop_opts)
    with c4:
        selected_book = st.selectbox("Book", book_opts)

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
        base_df, selected_sport, selected_segment, starters_only, confirmed_only,
        min_odds, max_odds, min_edge, min_hit, min_ev, selected_book, selected_prop
    )

    if filtered.empty:
        st.warning("No props match the current filters")
    else:
        for idx, (_, row) in enumerate(filtered.head(10).iterrows(), start=1):
            render_top_play_card(row, idx)
        st.dataframe(format_props_table(build_best_bets_dashboard(filtered)), use_container_width=True)

with tab_sections:
    st.subheader("Prop Sections")
    if props_live.empty:
        st.info("No props loaded.")
    else:
        table_cols = [
            "player", "opponent", "book", "game_segment", "recommended_side",
            "line", "projection", "proj_edge", "odds", "hit_probability",
            "expected_value_edge", "edge_score", "bet_grade", "confidence_status",
            "odds_move", "source_time",
        ]
        for title, prop_key, seg in [
            ("Points", "points", None),
            ("Rebounds", "rebounds", None),
            ("Assists", "assists", None),
            ("3PT Made", "3pt_made", None),
            ("Blocks", "blocks", None),
            ("Steals", "steals", None),
            ("Turnovers", "turnovers", None),
            ("PRA", "pra", None),
            ("PR", "pr", None),
            ("PA", "pa", None),
            ("RA", "ra", None),
            ("1Q Only", None, "1q"),
        ]:
            section = props_live.copy()
            if prop_key is not None:
                section = section[section["prop_type"] == prop_key]
            if seg is not None:
                section = section[section["game_segment"] == seg]
            st.markdown(f"### {title}")
            if section.empty:
                st.info(f"No {title.lower()} props loaded.")
            else:
                st.dataframe(format_props_table(section[table_cols]), use_container_width=True)

with tab_arb:
    st.subheader("Moneyline Arbitrage")
    sports = ["All"] + sorted(odds_df["sport"].dropna().astype(str).unique().tolist()) if not odds_df.empty else ["All"]
    selected_arb_sport = st.selectbox("Sport for arb", sports)
    arb_base = odds_df.copy()
    if selected_arb_sport != "All":
        arb_base = arb_base[arb_base["sport"] == selected_arb_sport]
    arb_results = find_moneyline_arbs(arb_base)
    if arb_results.empty:
        st.warning("No moneyline arbitrage opportunities detected.")
    else:
        st.dataframe(arb_results, use_container_width=True)

with tab_inj:
    st.subheader("Injuries / Starters")
    left, right = st.columns(2)
    with left:
        st.markdown("### Injuries")
        st.dataframe(injuries_df, use_container_width=True)
    with right:
        st.markdown("### Starting lineups")
        st.dataframe(lineups_df, use_container_width=True)

with tab_template:
    st.subheader("Projection Template")
    template_df = sample_full_props_projection_template()
    st.dataframe(template_df, use_container_width=True)
    csv_bytes = template_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download projection template CSV",
        data=csv_bytes,
        file_name="full_props_projection_template.csv",
        mime="text/csv",
    )
