# =========================================================
# IMPORTS (ADD THIS IF NOT ALREADY AT TOP)
# =========================================================
import re
import hashlib
import random
import time
from itertools import combinations
from datetime import datetime, timedelta

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Sports Betting AI Dashboard V34", layout="wide")

# =========================================================
# PERSISTENCE (BET LOG CSV)
# =========================================================
BET_LOG_FILE = "bet_log.csv"

def _normalize_category_text(value):
    if isinstance(value, list):
        cleaned = []
        for item in value:
            label = str(item).strip()
            if label and label not in cleaned:
                cleaned.append(label)
        return " | ".join(cleaned)

    raw = str(value).strip()
    if not raw:
        return ""

    cleaned = []
    for part in raw.split("|"):
        label = str(part).strip()
        if label and label not in cleaned:
            cleaned.append(label)

    return " | ".join(cleaned)


def _merge_duplicate_play_id_rows(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df.copy()

    working = df.copy()

    if "play_id" not in working.columns:
        working["play_id"] = ""

    if "log_category" not in working.columns:
        working["log_category"] = ""

    working["play_id"] = working["play_id"].astype(str).str.strip()
    working["log_category"] = working["log_category"].apply(_normalize_category_text)

    blank_mask = working["play_id"] == ""
    blank_rows = working[blank_mask].copy()
    id_rows = working[~blank_mask].copy()

    if id_rows.empty:
        return pd.concat([id_rows, blank_rows], ignore_index=True)

    merged_rows = []

    for _, group in id_rows.groupby("play_id", sort=False):
        group = group.copy()
        base_row = group.iloc[0].copy()

        # Merge categories across duplicates
        merged_categories = []
        for raw_cat in group["log_category"].tolist():
            for part in str(raw_cat).split("|"):
                label = part.strip()
                if label and label not in merged_categories:
                    merged_categories.append(label)

        base_row["log_category"] = " | ".join(merged_categories)

        # Preserve a settled result if any duplicate has one
        if "result" in group.columns:
            settled_mask = group["result"].astype(str).isin(["Win", "Loss", "Push"])
            settled_group = group[settled_mask].copy()

            if not settled_group.empty:
                settled_row = settled_group.iloc[-1]
                base_row["result"] = settled_row.get("result", base_row.get("result", "Pending"))

                if "profit" in group.columns:
                    base_row["profit"] = settled_row.get("profit", base_row.get("profit", 0.0))

        # Prefer the latest timestamp if available
        if "timestamp" in group.columns:
            non_blank_timestamps = group["timestamp"].astype(str).str.strip()
            non_blank_timestamps = non_blank_timestamps[non_blank_timestamps != ""]
            if not non_blank_timestamps.empty:
                base_row["timestamp"] = non_blank_timestamps.iloc[-1]

        merged_rows.append(base_row)

    merged_df = pd.DataFrame(merged_rows)
    cleaned_df = pd.concat([merged_df, blank_rows], ignore_index=True)

    return cleaned_df.reset_index(drop=True)


def load_bet_log():
    try:
        df = pd.read_csv(BET_LOG_FILE)

        if df is None or df.empty:
            return []

        cleaned_df = _merge_duplicate_play_id_rows(df)

        # Save cleaned version back to disk if duplicates/categories were normalized
        if not cleaned_df.equals(df):
            cleaned_df.to_csv(BET_LOG_FILE, index=False)

        return cleaned_df.to_dict("records")

    except FileNotFoundError:
        return []
    except Exception:
        return []


def save_bet_log():
    try:
        log_rows = st.session_state.get("bet_log", [])
        df = pd.DataFrame(log_rows)

        if df.empty:
            df.to_csv(BET_LOG_FILE, index=False)
            return

        cleaned_df = _merge_duplicate_play_id_rows(df)
        cleaned_df.to_csv(BET_LOG_FILE, index=False)

        # Keep session state synced with cleaned file
        st.session_state["bet_log"] = cleaned_df.to_dict("records")

    except Exception:
        pass


def build_logged_id_set(log_rows):
    ids = set()
    try:
        for row in log_rows or []:
            pid = str(row.get("play_id", "")).strip()
            if pid:
                ids.add(pid)
    except Exception:
        pass
    return ids


# =========================================================
# API CONFIG
# =========================================================
SPORTSDATA_BASES = {
    "nba": "https://api.sportsdata.io/v3/nba",
    "nhl": "https://api.sportsdata.io/v3/nhl",
    "mlb": "https://api.sportsdata.io/v3/mlb",
}

def get_sportsdata_key():
    possible_keys = [
        "SPORTSDATA_API_KEY",
        "SPORTSDATAIO_API_KEY",
        "SPORTS_DATA_API_KEY",
    ]
    for key_name in possible_keys:
        try:
            value = st.secrets.get(key_name, "")
            if value:
                return str(value).strip()
        except:
            pass
    return ""

SPORTSDATA_API_KEY = get_sportsdata_key()

ODDS_API_KEY = st.secrets.get("ODDS_API_KEY", "")
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"
ODDS_BOOKMAKERS = "draftkings,fanduel,betmgm,caesars,espnbet,betrivers"

# =========================================================
# SESSION STATE
# =========================================================
if "is_mobile" not in st.session_state:
    st.session_state["is_mobile"] = True

if "bet_log" not in st.session_state:
    st.session_state["bet_log"] = load_bet_log()

if "auto_logged_ids" not in st.session_state:
    st.session_state["auto_logged_ids"] = build_logged_id_set(st.session_state.get("bet_log", []))
else:
    # Re-sync on every app load so duplicates are blocked across restarts
    st.session_state["auto_logged_ids"] = build_logged_id_set(st.session_state.get("bet_log", []))

if "nav_choice" not in st.session_state:
    st.session_state["nav_choice"] = "Top Plays"
if "manual_results" not in st.session_state:
    st.session_state["manual_results"] = {}
if "odds_api_games" not in st.session_state:
    st.session_state["odds_api_games"] = []
if "last_successful_odds_games" not in st.session_state:
    st.session_state["last_successful_odds_games"] = []
if "sportsdata_cache" not in st.session_state:
    st.session_state["sportsdata_cache"] = {}
if "sportsdata_last_refresh" not in st.session_state:
    st.session_state["sportsdata_last_refresh"] = {}
if "sportsdata_enabled" not in st.session_state:
    st.session_state["sportsdata_enabled"] = True
if "api_mode" not in st.session_state:
    st.session_state["api_mode"] = "idle"
if "api_status_note" not in st.session_state:
    st.session_state["api_status_note"] = ""
if "last_refresh_error" not in st.session_state:
    st.session_state["last_refresh_error"] = ""
if "last_refresh_count" not in st.session_state:
    st.session_state["last_refresh_count"] = 0
if "last_api_pull_epoch" not in st.session_state:
    st.session_state["last_api_pull_epoch"] = 0.0
if "api_cooldown_seconds" not in st.session_state:
    st.session_state["api_cooldown_seconds"] = 90.0

# =========================================================
# SPORTS DATA FEED CONTROL
# =========================================================
SPORTSDATA_FEEDS = {
    "player_details": True,
    "depth_chart": True,
    "injured_players": True,
    "starting_lineups": True,
    "team_game_stats_by_date": True,
}

SPORTSDATA_CALL_LIMITS = {
    "player_details_hours": 24,
    "depth_chart_hours": 24,
    "injured_players_hours": 8,
    "starting_lineups_hours": 8,
    "team_game_stats_by_date_hours": 12,
}
# =========================================================
# CACHE + DATE HELPERS
# =========================================================
def today_str():
    return datetime.now().strftime("%Y-%m-%d")

def yesterday_str():
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

def cache_key(*parts):
    return "||".join([str(p) for p in parts])

def get_cached_data(key, max_age_hours=12):
    try:
        cache = st.session_state.get("sportsdata_cache", {})
        stamp_map = st.session_state.get("sportsdata_last_refresh", {})
        if key not in cache or key not in stamp_map:
            return None
        age = datetime.now() - stamp_map[key]
        if age.total_seconds() > max_age_hours * 3600:
            return None
        return cache[key]
    except:
        return None

def set_cached_data(key, data):
    try:
        st.session_state["sportsdata_cache"][key] = data
        st.session_state["sportsdata_last_refresh"][key] = datetime.now()
    except:
        pass

# =========================================================
# SPORTS DATA REQUESTS
# =========================================================
def sportsdata_headers():
    return {
        "Ocp-Apim-Subscription-Key": SPORTSDATA_API_KEY
    }

def safe_get_json(url, params=None, timeout=20):
    if not SPORTSDATA_API_KEY:
        return None
    try:
        r = requests.get(url, headers=sportsdata_headers(), params=params, timeout=timeout)
        if r.status_code != 200:
            return None
        return r.json()
    except:
        return None

def sportsdata_enabled():
    return bool(st.session_state.get("sportsdata_enabled", True) and SPORTSDATA_API_KEY)

def normalize_sport_for_sportsdata(sport_label):
    s = str(sport_label).lower()
    if "nba" in s or "basketball" in s:
        return "nba"
    if "nhl" in s or "hockey" in s:
        return "nhl"
    if "mlb" in s or "baseball" in s:
        return "mlb"
    return "nba"

# =========================================================
# SPORTSDATA FEED FUNCTIONS
# =========================================================
def fetch_player_details(sport="nba"):
    sport = normalize_sport_for_sportsdata(sport)
    key = cache_key("player_details", sport)
    cached = get_cached_data(key, SPORTSDATA_CALL_LIMITS["player_details_hours"])
    if cached is not None:
        return cached

    url = f"{SPORTSDATA_BASES[sport]}/scores/json/Players"
    data = safe_get_json(url)
    if data is None:
        return []
    set_cached_data(key, data)
    return data

def fetch_depth_chart(sport="nba"):
    sport = normalize_sport_for_sportsdata(sport)
    key = cache_key("depth_chart", sport)
    cached = get_cached_data(key, SPORTSDATA_CALL_LIMITS["depth_chart_hours"])
    if cached is not None:
        return cached

    url = f"{SPORTSDATA_BASES[sport]}/scores/json/DepthCharts"
    data = safe_get_json(url)
    if data is None:
        return []
    set_cached_data(key, data)
    return data

def fetch_injured_players(sport="nba"):
    sport = normalize_sport_for_sportsdata(sport)
    key = cache_key("injured_players", sport)
    cached = get_cached_data(key, SPORTSDATA_CALL_LIMITS["injured_players_hours"])
    if cached is not None:
        return cached

    url = f"{SPORTSDATA_BASES[sport]}/scores/json/InjuredPlayers"
    data = safe_get_json(url)
    if data is None:
        return []
    set_cached_data(key, data)
    return data

def fetch_starting_lineups_by_date(game_date=None, sport="nba"):
    sport = normalize_sport_for_sportsdata(sport)
    game_date = game_date or today_str()
    key = cache_key("starting_lineups", sport, game_date)
    cached = get_cached_data(key, SPORTSDATA_CALL_LIMITS["starting_lineups_hours"])
    if cached is not None:
        return cached

    url = f"{SPORTSDATA_BASES[sport]}/projections/json/StartingLineupsByDate/{game_date}"
    data = safe_get_json(url)
    if data is None:
        return []
    set_cached_data(key, data)
    return data

def fetch_team_game_stats_by_date(game_date=None, sport="nba"):
    sport = normalize_sport_for_sportsdata(sport)
    game_date = game_date or yesterday_str()
    key = cache_key("team_game_stats_by_date", sport, game_date)
    cached = get_cached_data(key, SPORTSDATA_CALL_LIMITS["team_game_stats_by_date_hours"])
    if cached is not None:
        return cached

    url = f"{SPORTSDATA_BASES[sport]}/stats/json/TeamGameStatsByDate/{game_date}"
    data = safe_get_json(url)
    if data is None:
        return []
    set_cached_data(key, data)
    return data

# =========================================================
# LOOKUP BUILDERS
# =========================================================
def build_injury_lookup(injuries):
    lookup = {}
    try:
        for row in injuries or []:
            name = str(row.get("Name", "")).strip().lower()
            team = str(row.get("Team", "")).strip().upper()
            status = str(row.get("Status", "")).strip()
            note = str(row.get("InjuryNotes", "")).strip()
            if name:
                lookup[name] = {
                    "team": team,
                    "status": status,
                    "note": note,
                    "raw": row,
                }
    except:
        pass
    return lookup

def build_player_lookup(players):
    lookup = {}
    try:
        for row in players or []:
            name = str(row.get("Name", "")).strip().lower()
            if name:
                lookup[name] = row
    except:
        pass
    return lookup

def build_lineup_lookup(lineups):
    lookup = {}
    try:
        for row in lineups or []:
            team = str(row.get("Team", "") or row.get("TeamName", "")).strip().upper()
            if not team:
                continue
            if team not in lookup:
                lookup[team] = []
            for slot in ["PG", "SG", "SF", "PF", "C", "G", "F"]:
                if row.get(slot):
                    lookup[team].append(str(row.get(slot)).strip())
    except:
        pass
    return lookup

def build_team_game_stats_lookup(team_stats):
    lookup = {}
    try:
        for row in team_stats or []:
            team = str(row.get("Team", "")).strip().upper()
            if team:
                lookup[team] = row
    except:
        pass
    return lookup

# =========================================================
# REAL DATA ENRICHMENT
# =========================================================
def enrich_plays_with_sportsdata(plays_df, sport="nba", game_date=None):
    if plays_df is None or len(plays_df) == 0:
        return plays_df

    if not sportsdata_enabled():
        if "injury_flag" not in plays_df.columns:
            plays_df["injury_flag"] = ""
        if "lineup_flag" not in plays_df.columns:
            plays_df["lineup_flag"] = ""
        if "context_score" not in plays_df.columns:
            plays_df["context_score"] = 0
        if "sportsdata_note" not in plays_df.columns:
            plays_df["sportsdata_note"] = ""
        return plays_df

    injuries = fetch_injured_players(sport)
    lineups = fetch_starting_lineups_by_date(game_date=game_date or today_str(), sport=sport)
    team_stats = fetch_team_game_stats_by_date(game_date=game_date or yesterday_str(), sport=sport)

    injury_lookup = build_injury_lookup(injuries)
    lineup_lookup = build_lineup_lookup(lineups)
    team_stats_lookup = build_team_game_stats_lookup(team_stats)

    out = plays_df.copy()
    out["injury_flag"] = ""
    out["lineup_flag"] = ""
    out["context_score"] = 0
    out["sportsdata_note"] = ""

    for idx, row in out.iterrows():
        player = str(row.get("player", "")).strip().lower()
        team = str(row.get("team", "")).strip().upper()
        opp = str(row.get("opponent", "")).strip().upper()

        context_score = 0
        notes = []

        injury = injury_lookup.get(player)
        if injury:
            status = str(injury.get("status", "")).lower()
            out.at[idx, "injury_flag"] = injury.get("status", "")
            notes.append(f"Injury: {injury.get('status', '')}")

            if any(tag in status for tag in ["out", "doubtful", "injured"]):
                context_score -= 45
            elif "questionable" in status:
                context_score -= 25
            elif any(tag in status for tag in ["probable", "day-to-day"]):
                context_score -= 10

        if team in lineup_lookup:
            starters = [str(x).strip().lower() for x in lineup_lookup.get(team, [])]
            if player and player in starters:
                out.at[idx, "lineup_flag"] = "Starting"
                notes.append("Confirmed/Projected Starter")
                context_score += 12
            elif player:
                out.at[idx, "lineup_flag"] = "Not in listed lineup"
                notes.append("Not in projected starting lineup")
                context_score -= 12

        if team in team_stats_lookup:
            team_row = team_stats_lookup[team]
            try:
                pts = float(team_row.get("Points", 0))
                context_score += min(8, max(0, (pts - 100) / 3))
            except:
                pass

        if opp in team_stats_lookup:
            opp_row = team_stats_lookup[opp]
            try:
                opp_pts_allowed = float(opp_row.get("PointsAllowed", 0))
                context_score += min(8, max(0, (opp_pts_allowed - 100) / 3))
            except:
                pass

        out.at[idx, "context_score"] = round(context_score, 1)
        out.at[idx, "sportsdata_note"] = " | ".join(notes)

        if "score" in out.columns:
            try:
                out.at[idx, "score"] = round(float(row.get("score", 0)) + context_score, 1)
            except:
                pass

    return out

# =========================================================
# ENGINE SETTINGS
# =========================================================
MIN_ACTIVE_EDGE = 4.00
MIN_WATCH_EDGE = 2.25
ACTIVE_EDGE_PROMOTION = 4.50

MIN_ACTIVE_TRUE_CONF = 70.0
MIN_WATCH_TRUE_CONF = 55.0

MIN_ACTIVE_BOOKS = 3
MIN_WATCH_BOOKS = 2

MAX_TOTAL_UNITS = 4.25
MAX_ACTIVE_PLAYS = 10
TOP_PLAYS_LIMIT = 10
WATCHLIST_LIMIT = 18

DEFAULT_ODDS_RANGE = (-200, 150)

MIN_PARLAY_LEGS = 2
MAX_PARLAY_LEGS = 3
MIN_PARLAY_ODDS = 200

SHARP_PARLAY_MIN_TRUE_CONF = 70.0
SHARP_PARLAY_MAX_PENALTY = 0.16
FALLBACK_PARLAY_MAX_PENALTY = 0.28

TEST_MODE = "Paper Test"
SINGLE_UNIT_MIN = 0.40
SINGLE_UNIT_MAX = 1.25
WATCH_UNIT_MIN = 0.25
WATCH_UNIT_MAX = 0.75
PARLAY_UNIT_SHARP = 0.60
PARLAY_UNIT_FALLBACK_2 = 0.35
PARLAY_UNIT_FALLBACK_3 = 0.20
TEST_DAILY_UNIT_CAP = 4.50

ENABLE_PLAYER_PROPS = False
PROPS_ONLY_STARTERS = True

PROP_TYPES = ["points", "rebounds", "assists", "pra"]
PROP_ODDS_RANGE = (-200, 150)
MAX_PROP_PLAYS_PER_GAME = 8

# =========================================================
# HELPERS
# =========================================================
def is_mobile():
    return bool(st.session_state.get("is_mobile", True))

def clamp(value, low, high):
    return max(low, min(high, value))

def safe_float(value, default=0.0):
    try:
        if value is None or str(value).strip() == "":
            return float(default)
        return float(value)
    except Exception:
        return float(default)

def safe_int(value, default=0):
    try:
        if value is None or str(value).strip() == "":
            return int(default)
        return int(float(value))
    except Exception:
        return int(default)

def american_to_int(odds_str):
    try:
        return int(str(odds_str).replace("+", "").strip())
    except Exception:
        return None

def in_allowed_odds_range(odds_str, min_odds=-200, max_odds=150):
    odds_val = american_to_int(odds_str)
    if odds_val is None:
        return False
    return min_odds <= odds_val <= max_odds

def american_to_decimal(odds_str):
    odds_val = american_to_int(odds_str)
    if odds_val is None:
        return None
    if odds_val > 0:
        return 1 + (odds_val / 100.0)
    return 1 + (100.0 / abs(odds_val))

def decimal_to_american(decimal_odds):
    if decimal_odds is None or decimal_odds <= 1:
        return None
    if decimal_odds >= 2:
        return int(round((decimal_odds - 1) * 100))
    return int(round(-100 / (decimal_odds - 1)))

def format_american(odds_val):
    if odds_val is None:
        return "N/A"
    if odds_val > 0:
        return f"+{int(odds_val)}"
    return str(int(odds_val))

def build_play_id(row_dict):
    raw = "|".join(
        [
            str(row_dict.get("game", "")),
            str(row_dict.get("market", "")),
            str(row_dict.get("selection", "")),
            str(row_dict.get("odds", "")),
        ]
    )
    return hashlib.md5(raw.encode()).hexdigest()

def confidence_bucket_from_true_conf(true_conf):
    tc = float(true_conf)
    if tc >= 75:
        return "Elite"
    if tc >= 70:
        return "High"
    if tc >= 65:
        return "Medium"
    return "Low"

def confidence_fill_and_color(true_conf):
    tc = float(true_conf)
    width = f"{int(clamp(tc, 0, 100))}%"
    if tc >= 75:
        return width, "#10b981", "Elite"
    if tc >= 70:
        return width, "#22c55e", "High"
    if tc >= 65:
        return width, "#f59e0b", "Medium"
    return width, "#ef4444", "Low"

def tier_colors(tier: str):
    t = str(tier).upper()
    if t == "A":
        return "#d1fae5", "#065f46"
    if t == "B":
        return "#dbeafe", "#1d4ed8"
    return "#fef3c7", "#92400e"

def quality_label_from_tier(tier: str):
    tier = str(tier).upper()
    if tier == "A":
        return "Elite"
    if tier == "B":
        return "Strong"
    return "Watch"

def american_profit(odds, stake):
    odds_int = american_to_int(odds)
    if odds_int is None:
        return 0.0
    stake = float(stake)
    if odds_int > 0:
        return round(stake * (odds_int / 100.0), 2)
    return round(stake * (100.0 / abs(odds_int)), 2)

def settle_result_pnl(odds, units, result):
    result = str(result).strip().lower()
    units = float(units)
    if result == "win":
        return american_profit(odds, units)
    if result == "loss":
        return round(-units, 2)
    return 0.0

def market_family(market):
    m = str(market).lower()
    if "moneyline" in m:
        return "moneyline"
    if "spread" in m:
        return "spread"
    if "total" in m:
        return "total"
    if "prop_" in m:
        return "prop"
    return "other"

# =========================================================
# SELF-LEARNING SETTINGS ACCESSORS
# =========================================================
def default_learning_settings():
    return {
        "min_active_edge": MIN_ACTIVE_EDGE,
        "min_watch_edge": MIN_WATCH_EDGE,
        "min_active_true_conf": MIN_ACTIVE_TRUE_CONF,
        "min_watch_true_conf": MIN_WATCH_TRUE_CONF,
        "unit_mult_low": 0.92,
        "unit_mult_medium": 1.00,
        "unit_mult_high": 1.00,
        "unit_mult_elite": 1.05,
    }

def get_learning_settings():
    defaults = default_learning_settings()
    saved = st.session_state.get("learning_settings", {})

    if not isinstance(saved, dict):
        return defaults

    out = defaults.copy()
    for k, v in saved.items():
        out[k] = v
    return out

def get_effective_min_active_edge():
    return float(get_learning_settings().get("min_active_edge", MIN_ACTIVE_EDGE))

def get_effective_min_watch_edge():
    return float(get_learning_settings().get("min_watch_edge", MIN_WATCH_EDGE))

def get_effective_min_active_true_conf():
    return float(get_learning_settings().get("min_active_true_conf", MIN_ACTIVE_TRUE_CONF))

def get_effective_min_watch_true_conf():
    return float(get_learning_settings().get("min_watch_true_conf", MIN_WATCH_TRUE_CONF))

def get_confidence_unit_multiplier(true_conf):
    bucket = confidence_bucket_from_true_conf(true_conf)
    learning = get_learning_settings()

    if bucket == "Elite":
        return float(learning.get("unit_mult_elite", 1.05))
    if bucket == "High":
        return float(learning.get("unit_mult_high", 1.00))
    if bucket == "Medium":
        return float(learning.get("unit_mult_medium", 1.00))
    return float(learning.get("unit_mult_low", 0.92))

def scale_single_units(row):
    true_conf = safe_float(row.get("true_confidence", 0))
    edge = safe_float(row.get("edge", 0))
    books_seen = safe_int(row.get("books_seen", 1), 1)

    base = (
        (true_conf * 0.55)
        + (edge * 6.5)
        + (books_seen * 3.0)
    ) / 55.0

    base = clamp(base, SINGLE_UNIT_MIN, SINGLE_UNIT_MAX)
    multiplier = get_confidence_unit_multiplier(true_conf)
    return round(clamp(base * multiplier, SINGLE_UNIT_MIN, SINGLE_UNIT_MAX), 2)

def scale_parlay_units(parlay):
    if not parlay:
        return 0.0

    approval_type = parlay.get("approval_type", "")
    leg_count = int(parlay.get("leg_count", 2))
    avg_true_conf = safe_float(parlay.get("avg_true_conf", 0))
    risk_label = str(parlay.get("risk_label", "Moderate"))

    if approval_type == "Sharp Approved":
        base_units = PARLAY_UNIT_SHARP
    elif leg_count == 2:
        base_units = PARLAY_UNIT_FALLBACK_2
    else:
        base_units = PARLAY_UNIT_FALLBACK_3

    if avg_true_conf >= 75:
        base_units += 0.10
    elif avg_true_conf < 68:
        base_units -= 0.08

    if risk_label == "Low":
        base_units += 0.05
    elif risk_label == "Elevated":
        base_units -= 0.10

    multiplier = get_confidence_unit_multiplier(avg_true_conf)
    return round(clamp(base_units * multiplier, 0.15, 0.75), 2)

def scale_watch_units(row):
    true_conf = safe_float(row.get("true_confidence", 0))
    edge = safe_float(row.get("edge", 0))
    books_seen = safe_int(row.get("books_seen", 1), 1)

    base = (
        (true_conf * 0.42)
        + (edge * 4.5)
        + (books_seen * 2.0)
    ) / 55.0

    base = clamp(base, WATCH_UNIT_MIN, WATCH_UNIT_MAX)
    multiplier = get_confidence_unit_multiplier(true_conf)
    return round(clamp(base * multiplier, WATCH_UNIT_MIN, WATCH_UNIT_MAX), 2)

def classify_watch_tier(row):
    tc = safe_float(row.get("true_confidence", 0))
    edge = safe_float(row.get("edge", 0))
    books = safe_int(row.get("books_seen", 0))
    consensus = str(row.get("consensus", "")).strip()

    if tc >= 68 and edge >= 4.0 and books >= 3 and consensus in ["Strong", "Fair"]:
        return "Near Active"
    if tc >= 62 and edge >= 3.4 and books >= 3:
        return "Monitor"
    return "Weak Watch"
# =========================================================
# TEAM NORMALIZATION (FULL NBA COVERAGE)
# =========================================================
def normalize_team_name(abbrev: str):
    raw = str(abbrev).strip()
    key = raw.upper()

    mapping = {
        "ATL": "Hawks", "ATLANTA HAWKS": "Hawks", "HAWKS": "Hawks",
        "BOS": "Celtics", "BOSTON CELTICS": "Celtics", "CELTICS": "Celtics",
        "BKN": "Nets", "BROOKLYN NETS": "Nets", "BROOKLYN": "Nets", "NETS": "Nets",
        "CHA": "Hornets", "CHARLOTTE HORNETS": "Hornets", "HORNETS": "Hornets",
        "CHI": "Bulls", "CHICAGO BULLS": "Bulls", "BULLS": "Bulls",
        "CLE": "Cavaliers", "CLEVELAND CAVALIERS": "Cavaliers", "CAVALIERS": "Cavaliers",
        "DET": "Pistons", "DETROIT PISTONS": "Pistons", "PISTONS": "Pistons",
        "IND": "Pacers", "INDIANA PACERS": "Pacers", "PACERS": "Pacers",
        "MIA": "Heat", "MIAMI HEAT": "Heat", "HEAT": "Heat",
        "MIL": "Bucks", "MILWAUKEE BUCKS": "Bucks", "BUCKS": "Bucks",
        "NYK": "Knicks", "NEW YORK KNICKS": "Knicks", "KNICKS": "Knicks",
        "ORL": "Magic", "ORLANDO MAGIC": "Magic", "MAGIC": "Magic",
        "PHI": "76ers", "PHILADELPHIA 76ERS": "76ers", "76ERS": "76ers", "SIXERS": "76ers",
        "TOR": "Raptors", "TORONTO RAPTORS": "Raptors", "RAPTORS": "Raptors",
        "WAS": "Wizards", "WASHINGTON WIZARDS": "Wizards", "WIZARDS": "Wizards",
        "DAL": "Mavericks", "DALLAS MAVERICKS": "Mavericks", "MAVERICKS": "Mavericks",
        "DEN": "Nuggets", "DENVER NUGGETS": "Nuggets", "NUGGETS": "Nuggets",
        "GSW": "Warriors", "GOLDEN STATE WARRIORS": "Warriors", "WARRIORS": "Warriors",
        "HOU": "Rockets", "HOUSTON ROCKETS": "Rockets", "ROCKETS": "Rockets",
        "LAC": "Clippers", "LOS ANGELES CLIPPERS": "Clippers", "CLIPPERS": "Clippers",
        "LAL": "Lakers", "LOS ANGELES LAKERS": "Lakers", "LAKERS": "Lakers",
        "MEM": "Grizzlies", "MEMPHIS GRIZZLIES": "Grizzlies", "GRIZZLIES": "Grizzlies",
        "MIN": "Timberwolves", "MINNESOTA TIMBERWOLVES": "Timberwolves", "TIMBERWOLVES": "Timberwolves", "WOLVES": "Timberwolves",
        "NOP": "Pelicans", "NEW ORLEANS PELICANS": "Pelicans", "PELICANS": "Pelicans",
        "OKC": "Thunder", "OKLAHOMA CITY THUNDER": "Thunder", "THUNDER": "Thunder",
        "PHX": "Suns", "PHOENIX SUNS": "Suns", "SUNS": "Suns",
        "POR": "Trail Blazers", "PORTLAND TRAIL BLAZERS": "Trail Blazers", "TRAIL BLAZERS": "Trail Blazers", "BLAZERS": "Trail Blazers",
        "SAC": "Kings", "SACRAMENTO KINGS": "Kings", "KINGS": "Kings",
        "SAS": "Spurs", "SAN ANTONIO SPURS": "Spurs", "SPURS": "Spurs",
        "UTA": "Jazz", "UTAH JAZZ": "Jazz", "JAZZ": "Jazz",
    }

    return mapping.get(key, raw.title())

def team_names_from_game(game: str):
    parts = str(game).split(" vs ")
    if len(parts) == 2:
        return normalize_team_name(parts[0]), normalize_team_name(parts[1])
    return "Away", "Home"

def starter_pool_for_team(team_name: str):
    normalized = normalize_team_name(team_name)

    starters_map = {
        "Knicks": ["Jalen Brunson", "Donte DiVincenzo", "Josh Hart", "OG Anunoby", "Julius Randle"],
        "Pelicans": ["CJ McCollum", "Brandon Ingram", "Herb Jones", "Zion Williamson", "Jonas Valanciunas"],
        "Magic": ["Jalen Suggs", "Franz Wagner", "Paolo Banchero", "Jonathan Isaac", "Wendell Carter Jr."],
        "Cavaliers": ["Darius Garland", "Donovan Mitchell", "Max Strus", "Evan Mobley", "Jarrett Allen"],
        "Nuggets": ["Jamal Murray", "Kentavious Caldwell-Pope", "Michael Porter Jr.", "Aaron Gordon", "Nikola Jokic"],
        "Suns": ["Bradley Beal", "Devin Booker", "Grayson Allen", "Kevin Durant", "Jusuf Nurkic"],
        "Spurs": ["Tre Jones", "Devin Vassell", "Keldon Johnson", "Jeremy Sochan", "Victor Wembanyama"],
        "Hornets": ["LaMelo Ball", "Terry Rozier", "Brandon Miller", "Miles Bridges", "Mark Williams"],
        "Lakers": ["D'Angelo Russell", "Austin Reaves", "LeBron James", "Rui Hachimura", "Anthony Davis"],
        "Warriors": ["Stephen Curry", "Klay Thompson", "Andrew Wiggins", "Draymond Green", "Jonathan Kuminga"],
        "Heat": ["Terry Rozier", "Tyler Herro", "Jimmy Butler", "Nikola Jovic", "Bam Adebayo"],
        "Celtics": ["Jrue Holiday", "Derrick White", "Jaylen Brown", "Jayson Tatum", "Kristaps Porzingis"],
    }

    if normalized in starters_map:
        return starters_map[normalized]

    return [
        f"{normalized} Starter 1",
        f"{normalized} Starter 2",
        f"{normalized} Starter 3",
        f"{normalized} Starter 4",
        f"{normalized} Starter 5",
    ]

def prop_line_for_type(prop_type: str):
    default_lines = {
        "points": [17.5, 19.5, 21.5, 23.5, 25.5, 27.5],
        "rebounds": [5.5, 6.5, 7.5, 8.5, 9.5, 10.5],
        "assists": [4.5, 5.5, 6.5, 7.5, 8.5],
        "pra": [28.5, 31.5, 34.5, 37.5, 40.5],
    }
    return random.choice(default_lines.get(prop_type, [10.5, 12.5]))

def build_prop_selection(player_name: str, prop_type: str):
    line = prop_line_for_type(prop_type)
    label_map = {
        "points": "Points",
        "rebounds": "Rebounds",
        "assists": "Assists",
        "pra": "PRA",
    }
    direction = random.choice(["Over", "Under"])
    return f"{player_name} {direction} {line} {label_map.get(prop_type, prop_type.title())}"

def is_prop_market(market: str):
    return str(market).lower().startswith("prop_")

def prop_market_label(market: str):
    m = str(market).lower()
    if m == "prop_points":
        return "Player Props • Points"
    if m == "prop_rebounds":
        return "Player Props • Rebounds"
    if m == "prop_assists":
        return "Player Props • Assists"
    if m == "prop_pra":
        return "Player Props • PRA"
    return str(market).replace("_", " ").title()

# =========================================================
# LIVE SLATE INPUT (V34.1 CLEAN)
# =========================================================
def parse_today_games(games_text: str):
    games = []

    for line in str(games_text).splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue

        # Flexible split (vs / v / VS / etc.)
        parts = re.split(r"\s+vs\s+|\s+v\s+", cleaned, flags=re.IGNORECASE)

        if len(parts) != 2:
            continue

        away = normalize_team_name(parts[0].strip())
        home = normalize_team_name(parts[1].strip())

        if away and home:
            games.append(f"{away} vs {home}")

    return games


# =========================================================
# SIDEBAR CONTROLS (V34.1 IMPROVED UX)
# =========================================================
st.sidebar.markdown("### 🗓️ Today's Slate")

st.sidebar.text_area(
    "Optional: Filter today's slate",
    key="today_games_text",
    height=180,
    placeholder="Examples:\nSAS vs CHA\nLAL vs BOS\nHeat vs Knicks\n\nLeave blank to use all live games",
)

# AUTO-UPPERCASE NORMALIZATION
if st.session_state.get("today_games_text"):
    st.session_state["today_games_text"] = st.session_state["today_games_text"].upper()

st.sidebar.caption(
    "Supports abbreviations, full team names, or nicknames (e.g., LAL, Lakers, Los Angeles Lakers)"
)

today_games = parse_today_games(st.session_state.get("today_games_text", ""))

# =========================================================
# SIDEBAR - SPORTSDATA CONTROLS
# =========================================================
st.sidebar.markdown("### 📡 SportsDataIO Controls")

st.session_state["sportsdata_enabled"] = st.sidebar.toggle(
    "Enable SportsDataIO Context",
    value=st.session_state.get("sportsdata_enabled", True)
)

selected_sportsdata_sport = "nba"
st.sidebar.caption("Sport: NBA (locked for V34 real-data mode)")

sportsdata_game_date = st.sidebar.text_input(
    "SportsData Game Date (YYYY-MM-DD)",
    value=today_str()
)

if SPORTSDATA_API_KEY:
    st.sidebar.success("SportsDataIO key loaded")
else:
    st.sidebar.warning("Missing SportsDataIO API key in Streamlit secrets")

# =========================================================
# LIVE ODDS FETCH (MANUAL REFRESH ONLY)
# =========================================================
def api_status_label():
    mode = st.session_state.get("api_mode", "idle")
    err = str(st.session_state.get("last_refresh_error", "")).lower()

    if mode == "live":
        return "LIVE", "#10b981", "#ecfdf5", "#065f46"
    if mode == "cached":
        return "CACHED", "#0ea5e9", "#eff6ff", "#075985"
    if not ODDS_API_KEY:
        return "NO KEY", "#f59e0b", "#fffbeb", "#92400e"
    if "401" in err or "unauthorized" in err:
        return "KEY ERROR", "#ef4444", "#fef2f2", "#991b1b"
    if "429" in err or "quota" in err or "usage" in err or "credits" in err or "out_of_usage_credits" in err:
        return "LIMIT HIT", "#f97316", "#fff7ed", "#9a3412"
    if err:
        return "OFFLINE", "#64748b", "#f8fafc", "#334155"

    return "IDLE", "#64748b", "#f8fafc", "#334155"

def get_effective_odds_games():
    live_games = st.session_state.get("odds_api_games", [])
    if live_games:
        return live_games

    cached_games = st.session_state.get("last_successful_odds_games", [])
    if cached_games:
        return cached_games

    return []

def fetch_live_nba_odds(force=False):
    now_ts = time.time()
    cooldown = float(st.session_state.get("api_cooldown_seconds", 90))
    last_pull = float(st.session_state.get("last_api_pull_epoch", 0.0))
    cached_games = st.session_state.get("last_successful_odds_games", [])

    if not ODDS_API_KEY:
        st.session_state["odds_api_games"] = []
        st.session_state["last_odds_refresh_ok"] = False
        st.session_state["last_refresh_error"] = "Missing ODDS_API_KEY in Streamlit secrets."
        st.session_state["last_refresh_count"] = 0
        st.session_state["api_mode"] = "fallback"
        st.session_state["api_status_note"] = "No API key found."
        return cached_games if cached_games else []

    if (not force) and cached_games and (now_ts - last_pull < cooldown):
        st.session_state["odds_api_games"] = cached_games
        st.session_state["last_odds_refresh_ok"] = True
        st.session_state["last_refresh_error"] = ""
        st.session_state["last_refresh_count"] = len(cached_games)
        st.session_state["api_mode"] = "cached"
        st.session_state["api_status_note"] = "Using cached odds to reduce API calls."
        return cached_games

    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american",
        "bookmakers": ODDS_BOOKMAKERS,
    }

    try:
        response = requests.get(ODDS_API_URL, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, list):
            data = []

        st.session_state["odds_api_games"] = data
        st.session_state["last_successful_odds_games"] = data
        st.session_state["last_odds_refresh_ok"] = True
        st.session_state["last_refresh_error"] = ""
        st.session_state["last_refresh_count"] = len(data)
        st.session_state["last_refresh_time"] = pd.Timestamp.now().strftime("%Y-%m-%d %I:%M:%S %p")
        st.session_state["last_api_pull_epoch"] = now_ts
        st.session_state["api_mode"] = "live"
        st.session_state["api_status_note"] = "Live odds loaded successfully."
        return data

    except requests.exceptions.HTTPError as e:
        status_code = getattr(e.response, "status_code", None)

        if status_code == 401:
            friendly_error = "401 Unauthorized — API key invalid, expired, or wrong."
        elif status_code == 429:
            friendly_error = "429 Rate limit / quota reached."
        else:
            friendly_error = f"HTTP error: {e}"

        st.session_state["last_odds_refresh_ok"] = False
        st.session_state["last_refresh_error"] = friendly_error
        st.session_state["last_refresh_count"] = 0

        if cached_games:
            st.session_state["odds_api_games"] = cached_games
            st.session_state["api_mode"] = "cached"
            st.session_state["api_status_note"] = "Live refresh failed. Using cached odds."
            return cached_games

        st.session_state["odds_api_games"] = []
        st.session_state["api_mode"] = "fallback"
        st.session_state["api_status_note"] = "Live refresh failed and no cache is available."
        return []

    except Exception as e:
        st.session_state["last_odds_refresh_ok"] = False
        st.session_state["last_refresh_error"] = str(e)
        st.session_state["last_refresh_count"] = 0

        if cached_games:
            st.session_state["odds_api_games"] = cached_games
            st.session_state["api_mode"] = "cached"
            st.session_state["api_status_note"] = "Refresh failed. Using cached odds."
            return cached_games

        st.session_state["odds_api_games"] = []
        st.session_state["api_mode"] = "fallback"
        st.session_state["api_status_note"] = "Refresh failed and no cached odds are available."
        return []

st.sidebar.markdown("### 📡 Live Odds Control")

if st.sidebar.button("🔄 Refresh Live Odds"):
    with st.sidebar:
        with st.spinner("Refreshing live odds..."):
            data = fetch_live_nba_odds(force=True)
            if st.session_state.get("api_mode") in ["live", "cached"] and len(data) > 0:
                if st.session_state.get("api_mode") == "live":
                    st.success(f"Loaded {len(data)} live game(s).")
                else:
                    st.warning(f"Using {len(data)} cached game(s).")
            else:
                st.error("Refresh failed.")

status_text, status_dot, status_bg, status_fg = api_status_label()

st.sidebar.markdown(
    f"""
    <div style="
        background:{status_bg};
        border:1px solid #e5e7eb;
        border-radius:14px;
        padding:10px 12px;
        margin-top:8px;
        margin-bottom:8px;">
        <div style="display:flex;align-items:center;gap:8px;font-weight:800;color:{status_fg};">
            <span style="
                width:10px;
                height:10px;
                border-radius:999px;
                background:{status_dot};
                display:inline-block;"></span>
            API Status: {status_text}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

status_note = st.session_state.get("api_status_note", "")
if status_note:
    st.sidebar.caption(status_note)

if st.session_state.get("last_refresh_time"):
    st.sidebar.caption(f"Last refresh: {st.session_state['last_refresh_time']}")

st.sidebar.caption(f"Games in memory: {len(get_effective_odds_games())}")

err = st.session_state.get("last_refresh_error", "")
if err:
    if "401" in err.lower() or "unauthorized" in err.lower():
        st.sidebar.warning("Your Odds API key is not being accepted right now.")
    elif "429" in err.lower() or "quota" in err.lower() or "usage" in err.lower() or "credits" in err.lower():
        st.sidebar.warning("Your Odds API usage limit appears to be reached.")
    else:
        st.sidebar.caption(f"Error: {err}")

# =========================================================
# SMART DECISION LAYER
# =========================================================
def american_odds_to_implied_prob_pct(odds):
    odds_val = american_to_int(odds)
    if odds_val is None:
        return 50.0

    if odds_val > 0:
        return round((100 / (odds_val + 100)) * 100, 2)

    return round((abs(odds_val) / (abs(odds_val) + 100)) * 100, 2)


def books_score(books_seen):
    try:
        books_seen = int(books_seen)
    except Exception:
        books_seen = 1

    if books_seen >= 4:
        return 1.00
    if books_seen == 3:
        return 0.82
    if books_seen == 2:
        return 0.56
    return 0.22


def consensus_score(consensus):
    consensus = str(consensus).strip().lower()
    if consensus == "strong":
        return 1.00
    if consensus == "fair":
        return 0.66
    return 0.30


def edge_score(edge):
    try:
        edge = float(edge)
    except Exception:
        edge = 0.0
    return clamp(edge / 10.0, 0.0, 1.0)


def price_edge_score(price_edge):
    try:
        price_edge = float(price_edge)
    except Exception:
        price_edge = 0.0
    return clamp(price_edge / 3.0, 0.0, 1.0)


def model_score(score):
    try:
        score = float(score)
    except Exception:
        score = 50.0
    return clamp((score - 78.0) / 22.0, 0.0, 1.0)


def confidence_numeric(confidence_value):
    raw = str(confidence_value).strip().lower()

    if raw == "elite":
        return 78.0
    if raw == "high":
        return 72.0
    if raw == "medium":
        return 66.0
    if raw == "low":
        return 58.0

    try:
        return float(confidence_value)
    except Exception:
        return 60.0


def estimate_true_probability_pct(row):
    score = float(row.get("score", 0))
    books_seen = int(row.get("books_seen", 1))
    consensus = str(row.get("consensus", "Thin"))
    price_edge = float(row.get("price_edge", 0))
    context_score = float(row.get("context_score", 0))
    market = str(row.get("market", "")).lower()
    odds = row.get("odds")

    ms = model_score(score)
    bs = books_score(books_seen)
    cs = consensus_score(consensus)
    ps = price_edge_score(price_edge)

    true_prob = (
        38.0
        + (ms * 20.0)
        + (bs * 8.0)
        + (cs * 10.0)
        + (ps * 12.0)
        + clamp(context_score, -20, 20) * 0.35
    )

    if market == "moneyline":
        true_prob += 1.0
    elif market == "spread":
        true_prob += 0.5
    elif market == "total":
        true_prob += 0.0
    elif market.startswith("prop_"):
        true_prob -= 2.5

    implied_prob = american_odds_to_implied_prob_pct(odds)
    true_prob = clamp(true_prob, 30.0, 82.0)
    edge = round(true_prob - implied_prob, 2)

    return round(true_prob, 1), round(implied_prob, 2), edge


def apply_true_probability_columns(df: pd.DataFrame):
    if df is None or df.empty:
        return df

    out = df.copy()

    true_probs = []
    implied_probs = []
    edges = []

    for _, row in out.iterrows():
        tp, ip, ed = estimate_true_probability_pct(row)
        true_probs.append(tp)
        implied_probs.append(ip)
        edges.append(ed)

    out["true_prob"] = true_probs
    out["implied_prob"] = implied_probs
    out["edge"] = edges

    return out


def detect_traps(row):
    penalties = 0.0
    trap_flags = []

    edge = float(row["edge"])
    books_seen = int(row["books_seen"])
    consensus = str(row["consensus"])
    price_edge = float(row["price_edge"])
    implied_prob = float(row.get("implied_prob", 50))
    true_prob = float(row.get("true_prob", 50))

    if edge < 2.0:
        penalties += 0.16
        trap_flags.append("weak value edge")
    elif edge < 4.0:
        penalties += 0.08
        trap_flags.append("thin value edge")

    if books_seen <= 1:
        penalties += 0.18
        trap_flags.append("single-book risk")
    elif books_seen == 2:
        penalties += 0.08
        trap_flags.append("limited book support")

    if consensus == "Thin":
        penalties += 0.14
        trap_flags.append("thin consensus")

    if price_edge < 1.0:
        penalties += 0.08
        trap_flags.append("weak price support")

    if implied_prob >= 65 and true_prob < implied_prob + 2.0:
        penalties += 0.08
        trap_flags.append("expensive favorite risk")

    return clamp(penalties, 0.0, 0.45), trap_flags


def compute_true_confidence(row):
    ms = model_score(row["score"])
    es = edge_score(row["edge"])
    ps = price_edge_score(row["price_edge"])
    bs = books_score(row["books_seen"])
    cs = consensus_score(row["consensus"])

    penalty, trap_flags = detect_traps(row)

    raw_quality = (
        ms * 0.28
        + es * 0.32
        + ps * 0.12
        + bs * 0.14
        + cs * 0.14
    )

    adjusted_quality = clamp(raw_quality - penalty, 0.0, 1.0)
    true_confidence = round(adjusted_quality * 100.0, 1)

    reasons = []
    if int(row["books_seen"]) >= 3:
        reasons.append("multi-book support")
    if str(row["consensus"]).lower() == "strong":
        reasons.append("strong consensus")
    elif str(row["consensus"]).lower() == "fair":
        reasons.append("usable consensus")
    if float(row["price_edge"]) >= 1.25:
        reasons.append("price support")
    if float(row["score"]) >= 88:
        reasons.append("strong model score")
    if float(row["edge"]) >= 4.0:
        reasons.append("true probability edge")
    if float(row.get("true_prob", 0)) >= 60:
        reasons.append("high true probability")
    reasons.extend(trap_flags)

    return true_confidence, adjusted_quality, reasons


def tier_from_true_conf(tc):
    if tc >= 78:
        return "A"
    if tc >= 65:
        return "B"
    return "C"

# =========================================================
# RECALCULATE AFTER SPORTSDATA (CRITICAL FIX)
# =========================================================
def recalculate_play_metrics(df: pd.DataFrame):
    if df is None or df.empty:
        return df

    out = df.copy()

    # Rebuild true probability + edge AFTER context/score adjustments
    out = apply_true_probability_columns(out)

    true_conf_list = []
    quality_score_list = []
    reasons_list = []

    for _, row in out.iterrows():
        tc, qs, reasons = compute_true_confidence(row)
        true_conf_list.append(tc)
        quality_score_list.append(qs)
        reasons_list.append(reasons)

    out["true_confidence"] = true_conf_list
    out["quality_score"] = quality_score_list
    out["decision_reasons"] = reasons_list
    out["confidence"] = out["true_confidence"].apply(confidence_bucket_from_true_conf)

    def refresh_tags(row):
        existing = list(row.get("ai_tags", [])) if isinstance(row.get("ai_tags", []), list) else []
        reasons = list(row.get("decision_reasons", [])) if isinstance(row.get("decision_reasons", []), list) else []
        merged = []
        for item in existing + reasons:
            if item and item not in merged:
                merged.append(item)
        return merged[:6]

    out["ai_tags"] = out.apply(refresh_tags, axis=1)

    active_edge_threshold = get_effective_min_active_edge()
    watch_edge_threshold = get_effective_min_watch_edge()
    active_true_conf_threshold = get_effective_min_active_true_conf()
    watch_true_conf_threshold = get_effective_min_watch_true_conf()

    def decide_status(row):
        if (
            float(row["edge"]) >= active_edge_threshold
            and float(row["true_confidence"]) >= active_true_conf_threshold
            and int(row["books_seen"]) >= MIN_ACTIVE_BOOKS
            and str(row["consensus"]) in ["Strong", "Fair"]
        ):
            return "Active"

        if (
            float(row["edge"]) >= watch_edge_threshold
            and float(row["true_confidence"]) >= watch_true_conf_threshold
            and int(row["books_seen"]) >= MIN_WATCH_BOOKS
        ):
            return "Watch"

        return "Discard"

    out["status"] = out.apply(decide_status, axis=1)
    out = out[out["status"] != "Discard"].copy()

    if out.empty:
        return out.reset_index(drop=True)

    out["watch_tier"] = out.apply(
        lambda r: classify_watch_tier(r) if str(r["status"]) == "Watch" else "",
        axis=1,
    )

    out["tier"] = out["true_confidence"].apply(tier_from_true_conf)
    out["quality_label"] = out["tier"].apply(quality_label_from_tier)

    out["units"] = out.apply(
        lambda r: scale_single_units(r) if str(r["status"]) == "Active" else scale_watch_units(r),
        axis=1,
    )

    out["rank_score"] = (
        out["true_confidence"] * 0.55
        + out["edge"] * 7.0
        + out["price_edge"] * 3.5
        + out["books_seen"] * 2.0
        + out["score"] * 0.08
    )

    out["play_id"] = out.apply(
        lambda r: build_play_id(
            {
                "game": r["game"],
                "market": r["market"],
                "selection": r["selection"],
                "odds": r["odds"],
            }
        ),
        axis=1,
    )

    active_local = (
        out[out["status"] == "Active"]
        .sort_values(["rank_score", "true_confidence"], ascending=False)
        .head(TOP_PLAYS_LIMIT)
        .copy()
    )

    watch_local = (
        out[out["status"] == "Watch"]
        .sort_values(["rank_score", "true_confidence"], ascending=False)
        .head(WATCHLIST_LIMIT)
        .copy()
    )

    active_rows = []
    running_units = 0.0

    for _, row in active_local.iterrows():
        proposed_units = float(row["units"])

        if len(active_rows) >= MAX_ACTIVE_PLAYS:
            row2 = row.copy()
            row2["status"] = "Watch"
            row2["watch_tier"] = classify_watch_tier(row2)
            row2["units"] = scale_watch_units(row2)
            watch_local = pd.concat([watch_local, pd.DataFrame([row2])], ignore_index=True)
            continue

        if running_units + proposed_units > MAX_TOTAL_UNITS:
            row2 = row.copy()
            row2["status"] = "Watch"
            row2["watch_tier"] = classify_watch_tier(row2)
            row2["units"] = scale_watch_units(row2)
            watch_local = pd.concat([watch_local, pd.DataFrame([row2])], ignore_index=True)
            continue

        active_rows.append(row)
        running_units += proposed_units

    active_final = pd.DataFrame(active_rows) if active_rows else pd.DataFrame(columns=out.columns)

    if not watch_local.empty:
        watch_priority = {"Near Active": 3, "Monitor": 2, "Weak Watch": 1}
        watch_local["watch_priority"] = watch_local["watch_tier"].map(watch_priority).fillna(0)
        watch_local = watch_local.sort_values(
            ["watch_priority", "rank_score", "true_confidence"],
            ascending=[False, False, False]
        ).drop(columns=["watch_priority"], errors="ignore")

    combined = pd.concat([active_final, watch_local], ignore_index=True)

    if combined.empty:
        return combined.reset_index(drop=True)

    status_order = {"Active": 0, "Watch": 1}
    combined["status_sort"] = combined["status"].map(status_order).fillna(9)

    return (
        combined.sort_values(["status_sort", "rank_score"], ascending=[True, False])
        .drop(columns=["status_sort"], errors="ignore")
        .reset_index(drop=True)
    )

# =========================================================
# DATA BUILD
# =========================================================
def generate_ai_plays():
    empty_cols = [
        "game",
        "market",
        "selection",
        "player",
        "team",
        "opponent",
        "odds",
        "implied_prob",
        "true_prob",
        "edge",
        "score",
        "units",
        "tier",
        "quality_label",
        "status",
        "watch_tier",
        "confidence",
        "books_seen",
        "best_price",
        "consensus",
        "price_edge",
        "ai_tags",
        "true_confidence",
        "quality_score",
        "decision_reasons",
        "rank_score",
        "play_id",
    ]

    live_games = get_effective_odds_games()
    if not live_games:
        return pd.DataFrame(columns=empty_cols)

    allowed_games = set(today_games) if today_games else None
    rows = []

    def normalize_outcome_name(name):
        return normalize_team_name(str(name).strip())

    def add_scored_row(row, base_tags):
        tp, ip, ed = estimate_true_probability_pct(row)
        row["true_prob"] = tp
        row["implied_prob"] = ip
        row["edge"] = ed

        tc, qs, reasons = compute_true_confidence(row)
        row["true_confidence"] = tc
        row["quality_score"] = qs
        row["decision_reasons"] = reasons
        row["confidence"] = confidence_bucket_from_true_conf(tc)

        tags = list(base_tags)
        for reason in reasons:
            if reason not in tags:
                tags.append(reason)
        row["ai_tags"] = tags[:6]

        rows.append(row)

    def get_best_market_outcome(bookmakers, market_key, target_name=None):
        best_price = None
        books_found = 0

        for book in bookmakers:
            markets = book.get("markets", [])
            for market in markets:
                if market.get("key") != market_key:
                    continue

                matched_this_book = False

                for outcome in market.get("outcomes", []):
                    outcome_name = str(outcome.get("name", "")).strip()
                    normalized_outcome_name = normalize_outcome_name(outcome_name)

                    if target_name is not None and normalized_outcome_name != target_name:
                        continue

                    price = outcome.get("price")
                    if price is None:
                        continue

                    try:
                        price = int(price)
                    except Exception:
                        continue

                    if not matched_this_book:
                        books_found += 1
                        matched_this_book = True

                    if best_price is None or price > best_price:
                        best_price = price

        return best_price, books_found

    def get_best_spread_outcome(bookmakers, target_name):
        best_price = None
        best_point = None
        books_found = 0

        for book in bookmakers:
            markets = book.get("markets", [])
            for market in markets:
                if market.get("key") != "spreads":
                    continue

                matched_this_book = False

                for outcome in market.get("outcomes", []):
                    outcome_name = str(outcome.get("name", "")).strip()
                    normalized_outcome_name = normalize_outcome_name(outcome_name)

                    if normalized_outcome_name != target_name:
                        continue

                    price = outcome.get("price")
                    point = outcome.get("point")

                    if price is None or point is None:
                        continue

                    try:
                        price = int(price)
                        point = float(point)
                    except Exception:
                        continue

                    if not matched_this_book:
                        books_found += 1
                        matched_this_book = True

                    if best_point is None:
                        best_point = point
                        best_price = price
                    else:
                        if point > best_point:
                            best_point = point
                            best_price = price
                        elif point == best_point and price > best_price:
                            best_price = price

        return best_point, best_price, books_found

    def get_best_total_outcome(bookmakers, over_under_name):
        best_price = None
        best_point = None
        books_found = 0

        for book in bookmakers:
            markets = book.get("markets", [])
            for market in markets:
                if market.get("key") != "totals":
                    continue

                matched_this_book = False

                for outcome in market.get("outcomes", []):
                    outcome_name = str(outcome.get("name", "")).strip()
                    if outcome_name != over_under_name:
                        continue

                    price = outcome.get("price")
                    point = outcome.get("point")

                    if price is None or point is None:
                        continue

                    try:
                        price = int(price)
                        point = float(point)
                    except Exception:
                        continue

                    if not matched_this_book:
                        books_found += 1
                        matched_this_book = True

                    if best_point is None:
                        best_point = point
                        best_price = price
                    else:
                        if over_under_name == "Over":
                            if point < best_point:
                                best_point = point
                                best_price = price
                            elif point == best_point and price > best_price:
                                best_price = price
                        else:
                            if point > best_point:
                                best_point = point
                                best_price = price
                            elif point == best_point and price > best_price:
                                best_price = price

        return best_point, best_price, books_found

    def game_context_from_market(away_team, home_team, bookmakers):
        away_spread, away_spread_price, away_books = get_best_spread_outcome(bookmakers, away_team)
        home_spread, home_spread_price, home_books = get_best_spread_outcome(bookmakers, home_team)

        over_total, over_price, total_books = get_best_total_outcome(bookmakers, "Over")
        under_total, under_price, under_books = get_best_total_outcome(bookmakers, "Under")

        total_line = None
        if over_total is not None and under_total is not None:
            total_line = over_total if total_books >= under_books else under_total
        elif over_total is not None:
            total_line = over_total
        elif under_total is not None:
            total_line = under_total

        favorite_team = None
        favorite_spread_abs = 0.0

        spread_candidates = []
        if away_spread is not None:
            spread_candidates.append((away_team, away_spread))
        if home_spread is not None:
            spread_candidates.append((home_team, home_spread))

        negative_spreads = [(team, spread) for team, spread in spread_candidates if spread < 0]
        if negative_spreads:
            favorite_team, fav_spread = sorted(negative_spreads, key=lambda x: x[1])[0]
            favorite_spread_abs = abs(float(fav_spread))

        total_tier = "neutral"
        if total_line is not None:
            if total_line >= 234:
                total_tier = "very_high"
            elif total_line >= 227:
                total_tier = "high"
            elif total_line <= 218:
                total_tier = "low"

        blowout_risk = "low"
        if favorite_spread_abs >= 10:
            blowout_risk = "high"
        elif favorite_spread_abs >= 7:
            blowout_risk = "moderate"

        tight_game = favorite_spread_abs <= 4 if favorite_team is not None else False

        return {
            "favorite_team": favorite_team,
            "favorite_spread_abs": round(favorite_spread_abs, 1),
            "total_line": total_line,
            "total_tier": total_tier,
            "blowout_risk": blowout_risk,
            "tight_game": tight_game,
            "spread_books": max(away_books, home_books),
            "total_books": max(total_books, under_books),
        }

    def context_adjust_prop(team_name, player_name, prop_type, context):
        score_boost = 0.0
        price_boost = 0.0
        tags = []

        total_tier = context.get("total_tier", "neutral")
        favorite_team = context.get("favorite_team")
        blowout_risk = context.get("blowout_risk", "low")
        tight_game = context.get("tight_game", False)

        is_favorite = favorite_team == team_name
        is_star = player_name in {
            "Stephen Curry", "LeBron James", "Anthony Davis", "Jayson Tatum",
            "Jaylen Brown", "Donovan Mitchell", "Nikola Jokic", "Kevin Durant",
            "Devin Booker", "Victor Wembanyama", "Paolo Banchero", "Jalen Brunson",
            "Zion Williamson", "Brandon Ingram", "LaMelo Ball", "Jimmy Butler",
            "Tyler Herro", "Bam Adebayo"
        }

        if total_tier == "very_high":
            if prop_type in ["points", "pra", "assists"]:
                score_boost += 4.0
                price_boost += 0.30
                tags.append("very high total boost")
            elif prop_type == "rebounds":
                score_boost += 1.0
                tags.append("high pace support")
        elif total_tier == "high":
            if prop_type in ["points", "pra"]:
                score_boost += 2.5
                price_boost += 0.18
                tags.append("high total boost")
            elif prop_type == "assists":
                score_boost += 1.8
                tags.append("offense environment boost")
        elif total_tier == "low":
            if prop_type in ["points", "pra"]:
                score_boost -= 2.2
                tags.append("low total drag")
            elif prop_type == "rebounds":
                score_boost += 0.8
                tags.append("rebound environment")

        if tight_game and prop_type in ["points", "pra", "assists"]:
            score_boost += 1.8
            tags.append("tight game boost")

        if blowout_risk == "high":
            if is_favorite and is_star and prop_type in ["points", "pra", "assists"]:
                score_boost -= 2.8
                tags.append("blowout risk")
            elif (not is_favorite) and prop_type in ["assists", "pra"]:
                score_boost -= 1.0
                tags.append("game script risk")
        elif blowout_risk == "moderate":
            if is_favorite and is_star and prop_type in ["points", "pra"]:
                score_boost -= 1.0
                tags.append("moderate blowout risk")

        if is_star and (tight_game or total_tier in ["high", "very_high"]) and prop_type in ["points", "pra"]:
            score_boost += 1.5
            tags.append("star usage boost")

        return score_boost, price_boost, tags

    def build_prop_rows_for_game(game, away_team, home_team, bookmakers):
        if not ENABLE_PLAYER_PROPS:
            return

        context = game_context_from_market(away_team, home_team, bookmakers)

        prop_books_seen = max(2, min(4, len(bookmakers)))
        prop_books_seen = max(prop_books_seen, int(context.get("total_books", 2) or 2))
        prop_consensus = "Strong" if prop_books_seen >= 4 else ("Fair" if prop_books_seen >= 2 else "Thin")

        game_prop_count = 0
        players_seen = set()

        for team_name in [away_team, home_team]:
            if game_prop_count >= MAX_PROP_PLAYS_PER_GAME:
                break

            player_pool = starter_pool_for_team(team_name)

            for player_name in player_pool:
                if game_prop_count >= MAX_PROP_PLAYS_PER_GAME:
                    break

                player_key = f"{game}::{player_name}"
                if player_key in players_seen:
                    continue

                prop_type = random.choice(PROP_TYPES)
                market_name = f"prop_{prop_type}"
                selection = build_prop_selection(player_name, prop_type)

                odds_val = random.choice([-135, -125, -120, -115, -110, -105, 100, 105, 110, 115, 120, 125])
                if not in_allowed_odds_range(format_american(odds_val), PROP_ODDS_RANGE[0], PROP_ODDS_RANGE[1]):
                    continue

                base_score = random.uniform(80.0, 96.8)
                base_price_edge = random.uniform(0.9, 2.4)

                score_boost, price_boost, context_tags = context_adjust_prop(
                    team_name, player_name, prop_type, context
                )

                score = round(clamp(base_score + score_boost, 76.0, 99.2), 1)
                price_edge = round(clamp(base_price_edge + price_boost, 0.5, 3.0), 2)

                row = {
                    "game": game,
                    "market": market_name,
                    "selection": selection,
                    "player": player_name,
                    "team": team_name,
                    "opponent": home_team if team_name == away_team else away_team,
                    "odds": format_american(odds_val),
                    "implied_prob": 0.0,
                    "true_prob": 0.0,
                    "edge": 0.0,
                    "score": score,
                    "units": 0.0,
                    "tier": "C",
                    "quality_label": "Watch",
                    "status": "Watch",
                    "watch_tier": "",
                    "confidence": "Low",
                    "books_seen": prop_books_seen,
                    "best_price": "Sim",
                    "consensus": prop_consensus,
                    "price_edge": price_edge,
                    "ai_tags": [],
                }

                prop_tags = [
                    "player prop",
                    "starters only" if PROPS_ONLY_STARTERS else "player pool",
                    prop_type,
                    "context aware",
                ]
                for tag in context_tags:
                    if tag not in prop_tags:
                        prop_tags.append(tag)

                add_scored_row(row, prop_tags[:6])

                players_seen.add(player_key)
                game_prop_count += 1

    for event in live_games:
        home_team = normalize_team_name(event.get("home_team", "Home"))
        away_team = normalize_team_name(event.get("away_team", "Away"))
        game = f"{away_team} vs {home_team}"

        if allowed_games and game not in allowed_games:
            continue

        bookmakers = event.get("bookmakers", [])
        if not bookmakers:
            continue

        for team_name in [away_team, home_team]:
            best_price, books_found = get_best_market_outcome(bookmakers, "h2h", team_name)
            if best_price is None or books_found == 0:
                continue
            if not in_allowed_odds_range(format_american(best_price), DEFAULT_ODDS_RANGE[0], DEFAULT_ODDS_RANGE[1]):
                continue

            score = round(min(99.0, 74.0 + (books_found * 3.8) + ((abs(best_price) < 140) * 3.5)), 1)
            price_edge = round(min(3.0, max(0.75, 0.65 + (books_found * 0.40))), 2)
            consensus = "Strong" if books_found >= 4 else ("Fair" if books_found >= 2 else "Thin")

            row = {
                "game": game,
                "market": "moneyline",
                "selection": team_name,
                "player": "",
                "team": team_name,
                "opponent": home_team if team_name == away_team else away_team,
                "odds": format_american(best_price),
                "implied_prob": 0.0,
                "true_prob": 0.0,
                "edge": 0.0,
                "score": score,
                "units": 0.0,
                "tier": "C",
                "quality_label": "Watch",
                "status": "Watch",
                "watch_tier": "",
                "confidence": "Low",
                "books_seen": books_found,
                "best_price": "Yes",
                "consensus": consensus,
                "price_edge": price_edge,
                "ai_tags": [],
            }
            add_scored_row(row, ["API live odds", "moneyline", "best price"])

        for team_name in [away_team, home_team]:
            best_point, best_price, books_found = get_best_spread_outcome(bookmakers, team_name)
            if best_point is None or best_price is None or books_found == 0:
                continue
            if not in_allowed_odds_range(format_american(best_price), DEFAULT_ODDS_RANGE[0], DEFAULT_ODDS_RANGE[1]):
                continue

            score = round(min(99.0, 74.0 + (books_found * 3.8) + ((abs(best_price) < 140) * 3.5)), 1)
            price_edge = round(min(3.0, max(0.75, 0.65 + (books_found * 0.40))), 2)
            consensus = "Strong" if books_found >= 4 else ("Fair" if books_found >= 2 else "Thin")

            point_str = f"+{best_point:g}" if best_point > 0 else f"{best_point:g}"

            row = {
                "game": game,
                "market": "spread",
                "selection": f"{team_name} {point_str}",
                "player": "",
                "team": team_name,
                "opponent": home_team if team_name == away_team else away_team,
                "odds": format_american(best_price),
                "implied_prob": 0.0,
                "true_prob": 0.0,
                "edge": 0.0,
                "score": score,
                "units": 0.0,
                "tier": "C",
                "quality_label": "Watch",
                "status": "Watch",
                "watch_tier": "",
                "confidence": "Low",
                "books_seen": books_found,
                "best_price": "Yes",
                "consensus": consensus,
                "price_edge": price_edge,
                "ai_tags": [],
            }
            add_scored_row(row, ["API live odds", "spread", "best line"])

        for side in ["Over", "Under"]:
            best_point, best_price, books_found = get_best_total_outcome(bookmakers, side)
            if best_point is None or best_price is None or books_found == 0:
                continue
            if not in_allowed_odds_range(format_american(best_price), DEFAULT_ODDS_RANGE[0], DEFAULT_ODDS_RANGE[1]):
                continue

            score = round(min(99.0, 74.0 + (books_found * 3.8) + ((abs(best_price) < 140) * 3.5)), 1)
            price_edge = round(min(3.0, max(0.75, 0.65 + (books_found * 0.40))), 2)
            consensus = "Strong" if books_found >= 4 else ("Fair" if books_found >= 2 else "Thin")

            row = {
                "game": game,
                "market": "total",
                "selection": f"{side} {best_point:g}",
                "player": "",
                "team": "",
                "opponent": "",
                "odds": format_american(best_price),
                "implied_prob": 0.0,
                "true_prob": 0.0,
                "edge": 0.0,
                "score": score,
                "units": 0.0,
                "tier": "C",
                "quality_label": "Watch",
                "status": "Watch",
                "watch_tier": "",
                "confidence": "Low",
                "books_seen": books_found,
                "best_price": "Yes",
                "consensus": consensus,
                "price_edge": price_edge,
                "ai_tags": [],
            }
            add_scored_row(row, ["API live odds", "total", "best line"])

        build_prop_rows_for_game(game, away_team, home_team, bookmakers)

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=empty_cols)

    if "selection" in df.columns:
        df = df.drop_duplicates(subset=["game", "market", "selection", "odds"]).copy()

    df["rank_score"] = (
        df["true_confidence"] * 0.55
        + df["edge"] * 7.0
        + df["price_edge"] * 3.5
        + df["books_seen"] * 2.0
        + df["score"] * 0.08
    )

    def decide_status(row):
        if (
            float(row["edge"]) >= MIN_ACTIVE_EDGE
            and float(row["true_confidence"]) >= MIN_ACTIVE_TRUE_CONF
            and int(row["books_seen"]) >= MIN_ACTIVE_BOOKS
            and str(row["consensus"]) in ["Strong", "Fair"]
        ):
            return "Active"

        if (
            float(row["edge"]) >= MIN_WATCH_EDGE
            and float(row["true_confidence"]) >= MIN_WATCH_TRUE_CONF
            and int(row["books_seen"]) >= MIN_WATCH_BOOKS
        ):
            return "Watch"

        return "Discard"

    df["status"] = df.apply(decide_status, axis=1)
    df = df[df["status"] != "Discard"].copy()

    if df.empty:
        return pd.DataFrame(columns=empty_cols)

    df["watch_tier"] = df.apply(
        lambda r: classify_watch_tier(r) if str(r["status"]) == "Watch" else "",
        axis=1,
    )

    df["tier"] = df["true_confidence"].apply(tier_from_true_conf)
    df["quality_label"] = df["tier"].apply(quality_label_from_tier)

    df["units"] = df.apply(
        lambda r: scale_single_units(r) if str(r["status"]) == "Active" else scale_watch_units(r),
        axis=1,
    )

    df["play_id"] = df.apply(
        lambda r: build_play_id(
            {
                "game": r["game"],
                "market": r["market"],
                "selection": r["selection"],
                "odds": r["odds"],
            }
        ),
        axis=1,
    )

    active_local = (
        df[df["status"] == "Active"]
        .sort_values(["rank_score", "true_confidence"], ascending=False)
        .head(TOP_PLAYS_LIMIT)
        .copy()
    )

    watch_local = (
        df[df["status"] == "Watch"]
        .sort_values(["rank_score", "true_confidence"], ascending=False)
        .head(WATCHLIST_LIMIT)
        .copy()
    )

    active_rows = []
    running_units = 0.0

    for _, row in active_local.iterrows():
        proposed_units = float(row["units"])

        if len(active_rows) >= MAX_ACTIVE_PLAYS:
            row2 = row.copy()
            row2["status"] = "Watch"
            row2["watch_tier"] = classify_watch_tier(row2)
            row2["units"] = scale_watch_units(row2)
            watch_local = pd.concat([watch_local, pd.DataFrame([row2])], ignore_index=True)
            continue

        if running_units + proposed_units > MAX_TOTAL_UNITS:
            row2 = row.copy()
            row2["status"] = "Watch"
            row2["watch_tier"] = classify_watch_tier(row2)
            row2["units"] = scale_watch_units(row2)
            watch_local = pd.concat([watch_local, pd.DataFrame([row2])], ignore_index=True)
            continue

        active_rows.append(row)
        running_units += proposed_units

    active_final = pd.DataFrame(active_rows) if active_rows else pd.DataFrame(columns=df.columns)

    if not watch_local.empty:
        watch_priority = {"Near Active": 3, "Monitor": 2, "Weak Watch": 1}
        watch_local["watch_priority"] = watch_local["watch_tier"].map(watch_priority).fillna(0)
        watch_local = watch_local.sort_values(
            ["watch_priority", "rank_score", "true_confidence"],
            ascending=[False, False, False]
        ).drop(columns=["watch_priority"], errors="ignore")

    combined = pd.concat([active_final, watch_local], ignore_index=True)

    if combined.empty:
        return pd.DataFrame(columns=empty_cols)

    status_order = {"Active": 0, "Watch": 1}
    combined["status_sort"] = combined["status"].map(status_order).fillna(9)

    return (
        combined.sort_values(["status_sort", "rank_score"], ascending=[True, False])
        .drop(columns=["status_sort"], errors="ignore")
        .reset_index(drop=True)
    )
# =========================================================
# PARLAY INTELLIGENCE
# =========================================================
def calculate_correlation_score(legs):
    score = 0.0
    for i in range(len(legs)):
        for j in range(i + 1, len(legs)):
            a = legs[i]
            b = legs[j]

            same_game = a.get("game") == b.get("game")
            market_a = market_family(a.get("market"))
            market_b = market_family(b.get("market"))

            if same_game:
                score -= 1.0
                if market_a == market_b:
                    score -= 0.5
            else:
                score += 0.5
    return score


def selections_conflict(row_a, row_b):
    if row_a["game"] != row_b["game"]:
        return False

    sel_a = str(row_a["selection"]).lower()
    sel_b = str(row_b["selection"]).lower()

    if row_a["market"] == row_b["market"] and row_a["selection"] != row_b["selection"]:
        return True
    if ("over" in sel_a and "under" in sel_b) or ("under" in sel_a and "over" in sel_b):
        return True

    return False


def pair_correlation_penalty(row_a, row_b):
    penalty = 0.0
    reasons = []

    if selections_conflict(row_a, row_b):
        return 1.0, ["conflicting legs"]

    if row_a["game"] == row_b["game"]:
        penalty += 0.22
        reasons.append("same-game correlation")

    return clamp(penalty, 0.0, 1.0), reasons


def score_parlay_combo(combo):
    total_penalty = 0.0
    penalty_reasons = []

    for a, b in combinations(combo, 2):
        penalty, reasons = pair_correlation_penalty(a, b)
        if penalty >= 1.0:
            return None
        total_penalty += penalty
        penalty_reasons.extend(reasons)

    decimal_odds = 1.0
    for leg in combo:
        dec = american_to_decimal(leg["odds"])
        if dec is None:
            return None
        decimal_odds *= dec

    combined_american = decimal_to_american(decimal_odds)
    if combined_american is None or combined_american < MIN_PARLAY_ODDS:
        return None

    avg_true_conf = sum(float(leg["true_confidence"]) for leg in combo) / len(combo)
    avg_edge = sum(float(leg["edge"]) for leg in combo) / len(combo)
    avg_books = sum(float(leg["books_seen"]) for leg in combo) / len(combo)

    distinct_games = len(set(leg["game"] for leg in combo))
    cross_game = distinct_games == len(combo)
    correlation_score = calculate_correlation_score(list(combo))

    score = (
        avg_true_conf * 0.65
        + avg_edge * 7.0
        + avg_books * 1.5
        + (4 if cross_game else -6)
        - (total_penalty * 35)
        + (correlation_score * 4)
    )

    if total_penalty <= 0.10 and avg_true_conf >= 74:
        risk_label = "Low"
    elif total_penalty <= 0.20 and avg_true_conf >= 70:
        risk_label = "Moderate"
    else:
        risk_label = "Elevated"

    reasons = []
    if cross_game:
        reasons.append("cross-game diversification")
    if avg_true_conf >= 72:
        reasons.append("strong true confidence")
    if avg_edge >= 4.2:
        reasons.append("sharp average edge")
    if avg_books >= 3:
        reasons.append("broad book support")
    reasons.extend(penalty_reasons)

    return {
        "legs": list(combo),
        "leg_count": len(combo),
        "combined_odds": format_american(combined_american),
        "combined_odds_int": combined_american,
        "avg_true_conf": round(avg_true_conf, 1),
        "avg_edge": round(avg_edge, 2),
        "avg_books": round(avg_books, 2),
        "total_penalty": round(total_penalty, 3),
        "cross_game": cross_game,
        "correlation_score": round(correlation_score, 2),
        "score": round(score, 1),
        "display_score": round(score, 1),
        "risk_label": risk_label,
        "reasons": reasons[:6],
    }


def build_all_parlay_candidates(active_df):
    if active_df.empty or len(active_df) < 2:
        return []

    rows = active_df.to_dict("records")
    candidates = []

    for leg_count in range(MIN_PARLAY_LEGS, min(MAX_PARLAY_LEGS, len(rows)) + 1):
        for combo in combinations(rows, leg_count):
            if any(float(leg["edge"]) < 4.0 for leg in combo):
                continue
            if any(float(leg["true_confidence"]) < 70.0 for leg in combo):
                continue
            if any(int(leg["books_seen"]) < 3 for leg in combo):
                continue

            scored = score_parlay_combo(combo)
            if scored is not None:
                candidates.append(scored)

    return candidates


def classify_parlay_candidates(candidates):
    sharp_candidates = []
    fallback_candidates = []

    for c in candidates:
        sharp_ok = (
            c["avg_true_conf"] >= SHARP_PARLAY_MIN_TRUE_CONF
            and c["total_penalty"] <= SHARP_PARLAY_MAX_PENALTY
            and c["cross_game"]
            and c["correlation_score"] >= 0
        )
        fallback_ok = (
            c["avg_true_conf"] >= 68
            and c["total_penalty"] <= FALLBACK_PARLAY_MAX_PENALTY
            and c["combined_odds_int"] >= MIN_PARLAY_ODDS
        )

        if sharp_ok:
            c1 = c.copy()
            c1["approval_type"] = "Sharp Approved"
            sharp_candidates.append(c1)

        if fallback_ok:
            c2 = c.copy()
            c2["approval_type"] = "Balanced Fallback"
            fallback_candidates.append(c2)

    sharp_candidates.sort(key=lambda x: (x["score"], x["avg_true_conf"]), reverse=True)
    fallback_candidates.sort(key=lambda x: (x["score"], x["avg_true_conf"]), reverse=True)
    return sharp_candidates, fallback_candidates


def choose_best_parlay(active_df):
    all_candidates = build_all_parlay_candidates(active_df)
    sharp_candidates, fallback_candidates = classify_parlay_candidates(all_candidates)

    if sharp_candidates:
        return sharp_candidates[0], sharp_candidates, fallback_candidates
    if fallback_candidates:
        return fallback_candidates[0], sharp_candidates, fallback_candidates
    return None, sharp_candidates, fallback_candidates

# =========================================================
# AUTO-LOG ACTIVE PLAYS (CATEGORY-AWARE)
# =========================================================
def normalize_log_categories(value):
    if isinstance(value, list):
        cleaned = []
        for item in value:
            label = str(item).strip()
            if label and label not in cleaned:
                cleaned.append(label)
        return cleaned

    raw = str(value).strip()
    if not raw:
        return []

    parts = [p.strip() for p in raw.split("|")]
    cleaned = []
    for part in parts:
        if part and part not in cleaned:
            cleaned.append(part)
    return cleaned


def format_log_categories_for_storage(categories):
    cleaned = normalize_log_categories(categories)
    return " | ".join(cleaned)


def add_category_to_logged_bet(existing_row, new_category):
    categories = normalize_log_categories(existing_row.get("log_category", ""))
    if new_category not in categories:
        categories.append(new_category)
    existing_row["log_category"] = format_log_categories_for_storage(categories)
    return existing_row


def find_logged_bet_index_by_exact_play_id(play_id):
    target = str(play_id).strip()
    if not target:
        return None

    for i, row in enumerate(st.session_state.get("bet_log", [])):
        if str(row.get("play_id", "")).strip() == target:
            return i

    return None


def find_logged_bet_index_by_suffix_play_id(play_id):
    target = str(play_id).strip()
    if not target:
        return None

    for i, row in enumerate(st.session_state.get("bet_log", [])):
        row_pid = str(row.get("play_id", "")).strip()
        if row_pid.startswith(f"{target}__"):
            return i

    return None


def find_logged_bet_index_by_base_play_id(play_id):
    target = str(play_id).strip()
    if not target:
        return None

    exact_idx = find_logged_bet_index_by_exact_play_id(target)
    if exact_idx is not None:
        return exact_idx

    return find_logged_bet_index_by_suffix_play_id(target)


def auto_log_active_plays(df: pd.DataFrame):
    if df is None or df.empty:
        return 0

    added = 0
    changed = False

    for _, row in df.iterrows():
        if str(row.get("status")) != "Active":
            continue

        pid = str(row.get("play_id", "")).strip()
        if not pid:
            continue

        exact_idx = find_logged_bet_index_by_exact_play_id(pid)

        if exact_idx is not None:
            existing_row = st.session_state["bet_log"][exact_idx]
            before_category = str(existing_row.get("log_category", "")).strip()

            updated_row = add_category_to_logged_bet(existing_row, "Top Play")
            after_category = str(updated_row.get("log_category", "")).strip()

            st.session_state["bet_log"][exact_idx] = updated_row
            st.session_state["auto_logged_ids"].add(pid)

            if before_category != after_category:
                changed = True

            continue

        suffix_idx = find_logged_bet_index_by_suffix_play_id(pid)

        new_bet = {
            "play_id": pid,
            "game": row.get("game"),
            "market": row.get("market"),
            "selection": row.get("selection"),
            "odds": row.get("odds"),
            "implied_prob": row.get("implied_prob"),
            "true_prob": row.get("true_prob"),
            "units": row.get("units"),
            "confidence": row.get("confidence"),
            "true_confidence": row.get("true_confidence"),
            "edge": row.get("edge"),
            "books_seen": row.get("books_seen"),
            "consensus": row.get("consensus"),
            "result": "Pending",
            "profit": 0.0,
            "mode": TEST_MODE,
            "log_category": "Top Play",
            "timestamp": datetime.now().isoformat(),
        }

        if suffix_idx is not None:
            suffix_row = st.session_state["bet_log"][suffix_idx]
            suffix_categories = normalize_log_categories(suffix_row.get("log_category", ""))
            merged_categories = ["Top Play"]

            for cat in suffix_categories:
                if cat not in merged_categories:
                    merged_categories.append(cat)

            new_bet["log_category"] = format_log_categories_for_storage(merged_categories)

            suffix_result = normalize_result_value(suffix_row.get("result", "Pending"))
            new_bet["result"] = suffix_result
            new_bet["profit"] = settle_result_pnl(new_bet["odds"], new_bet["units"], suffix_result)

        st.session_state["bet_log"].append(new_bet)
        st.session_state["auto_logged_ids"].add(pid)
        added += 1
        changed = True

    if changed:
        save_bet_log()

    return added


def log_ai_slip_pick(best_row):
    if best_row is None:
        return False

    pid = str(best_row.get("play_id", "")).strip()
    if not pid:
        return False

    exact_idx = find_logged_bet_index_by_exact_play_id(pid)
    if exact_idx is not None:
        existing_row = st.session_state["bet_log"][exact_idx]
        updated_row = add_category_to_logged_bet(existing_row, "AI Slip")
        st.session_state["bet_log"][exact_idx] = updated_row
        save_bet_log()
        return False

    suffix_idx = find_logged_bet_index_by_suffix_play_id(pid)
    if suffix_idx is not None:
        existing_row = st.session_state["bet_log"][suffix_idx]
        updated_row = add_category_to_logged_bet(existing_row, "AI Slip")
        st.session_state["bet_log"][suffix_idx] = updated_row
        save_bet_log()
        return False

    ai_slip_id = f"{pid}__ai_slip"

    new_row = {
        "play_id": ai_slip_id,
        "game": best_row.get("game"),
        "market": best_row.get("market"),
        "selection": best_row.get("selection"),
        "odds": best_row.get("odds"),
        "implied_prob": best_row.get("implied_prob"),
        "true_prob": best_row.get("true_prob"),
        "units": best_row.get("units"),
        "confidence": best_row.get("confidence"),
        "true_confidence": best_row.get("true_confidence"),
        "edge": best_row.get("edge"),
        "books_seen": best_row.get("books_seen"),
        "consensus": best_row.get("consensus"),
        "result": "Pending",
        "profit": 0.0,
        "mode": TEST_MODE,
        "log_category": "AI Slip",
        "timestamp": datetime.now().isoformat(),
    }

    st.session_state["bet_log"].append(new_row)
    save_bet_log()
    return True


def log_ai_parlay_pick(best_parlay):
    if best_parlay is None:
        return False

    parlay_key = "|".join(
        [str(leg.get("selection", "")).strip() for leg in best_parlay.get("legs", [])]
    )

    if not parlay_key:
        return False

    parlay_id = hashlib.md5(
        f"AI_PARLAY|{parlay_key}|{best_parlay.get('combined_odds')}".encode()
    ).hexdigest()

    existing_idx = find_logged_bet_index_by_exact_play_id(parlay_id)
    if existing_idx is not None:
        existing_row = st.session_state["bet_log"][existing_idx]
        updated_row = add_category_to_logged_bet(existing_row, "AI Parlay")
        st.session_state["bet_log"][existing_idx] = updated_row
        save_bet_log()
        return False

    new_row = {
        "play_id": parlay_id,
        "game": " | ".join(sorted(set([str(leg.get("game", "")) for leg in best_parlay.get("legs", [])]))),
        "market": "parlay",
        "selection": " | ".join([str(leg.get("selection", "")) for leg in best_parlay.get("legs", [])]),
        "odds": best_parlay.get("combined_odds"),
        "implied_prob": None,
        "true_prob": None,
        "units": scale_parlay_units(best_parlay),
        "confidence": "High" if float(best_parlay.get("avg_true_conf", 0)) >= 70 else "Medium",
        "true_confidence": best_parlay.get("avg_true_conf"),
        "edge": best_parlay.get("avg_edge"),
        "books_seen": best_parlay.get("avg_books"),
        "consensus": best_parlay.get("approval_type"),
        "result": "Pending",
        "profit": 0.0,
        "mode": TEST_MODE,
        "log_category": "AI Parlay",
        "timestamp": datetime.now().isoformat(),
    }

    st.session_state["bet_log"].append(new_row)
    save_bet_log()
    return True

# =========================================================
# PLAY CARD RENDER
# =========================================================
def render_play_card(row: pd.Series, show_best_badge: bool = False):
    badge_bg, badge_fg = tier_colors(row["tier"])
    is_active_play = str(row["status"]) == "Active"
    status_bg = "#f59e0b" if is_active_play else "#64748b"
    status_fg = "#111827" if is_active_play else "#f8fafc"
    best_display = "inline-flex" if show_best_badge else "none"

    fill_width, fill_color, conf_label = confidence_fill_and_color(row["true_confidence"])
    edge_color = "#4ade80" if float(row["edge"]) >= 4 else ("#fbbf24" if float(row["edge"]) >= 2 else "#f87171")

    watch_tier = row["watch_tier"] if "watch_tier" in row and pd.notna(row["watch_tier"]) else ""
    watch_display = "none"
    watch_bg = "#334155"
    watch_fg = "#e2e8f0"

    if not is_active_play and watch_tier:
        watch_display = "inline-flex"
        if watch_tier == "Near Active":
            watch_bg = "#fef3c7"
            watch_fg = "#92400e"
        elif watch_tier == "Monitor":
            watch_bg = "#dbeafe"
            watch_fg = "#1d4ed8"
        else:
            watch_bg = "#e5e7eb"
            watch_fg = "#374151"

    visible_tags = list(row["ai_tags"])[:3]
    tags_html = ""
    for tag in visible_tags:
        tags_html += f"""
        <span style="background:#1e2638;color:#d8e0ec;border:1px solid #2a3448;border-radius:999px;
        padding:3px 7px;font-size:10px;line-height:1;display:inline-block;margin-right:5px;margin-bottom:4px;white-space:nowrap;">{tag}</span>
        """

    injury_flag = str(row.get("injury_flag", "")).strip()
    lineup_flag = str(row.get("lineup_flag", "")).strip()
    sportsdata_note = str(row.get("sportsdata_note", "")).strip()
    context_score = row.get("context_score", 0)

    injury_html = ""
    if injury_flag:
        injury_html = f"""
        <span style="background:#7f1d1d;color:#fecaca;padding:4px 8px;border-radius:999px;font-size:10px;font-weight:800;">
            Injury: {injury_flag}
        </span>
        """

    lineup_html = ""
    if lineup_flag:
        lineup_bg = "#14532d" if lineup_flag == "Starting" else "#3f3f46"
        lineup_fg = "#dcfce7" if lineup_flag == "Starting" else "#e4e4e7"
        lineup_html = f"""
        <span style="background:{lineup_bg};color:{lineup_fg};padding:4px 8px;border-radius:999px;font-size:10px;font-weight:800;">
            {lineup_flag}
        </span>
        """

    context_html = ""
    try:
        context_val = float(context_score)
        context_color = "#22c55e" if context_val > 0 else ("#ef4444" if context_val < 0 else "#94a3b8")
        context_html = f"""
        <div><div style="color:#91a0b7;font-size:10px;">Context</div><div style="color:{context_color};font-weight:700;">{context_val:+.1f}</div></div>
        """
    except:
        pass

    note_html = ""
    if sportsdata_note:
        note_html = f"""
        <div style="margin-top:8px;padding:8px 10px;background:#111827;border:1px solid #243047;border-radius:12px;
        color:#d1d5db;font-size:11px;line-height:1.35;">
            <strong style="color:#93c5fd;">SportsData:</strong> {sportsdata_note}
        </div>
        """

    implied_prob = float(row.get("implied_prob", 0))
    true_prob = float(row.get("true_prob", 0))
    value_edge = float(row.get("edge", 0))

    html = f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1" /></head>
    <body style="margin:0;background:transparent;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
    <div style="background:linear-gradient(180deg, #151b29 0%, #0e1422 100%);
    border:1px solid #243047;border-radius:22px;padding:12px;color:#ffffff;box-sizing:border-box;">

        <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:7px;">
            <span style="background:{badge_bg};color:{badge_fg};padding:5px 9px;border-radius:999px;font-size:10px;font-weight:800;">Tier {row['tier']}</span>
            <span style="background:{status_bg};color:{status_fg};padding:5px 9px;border-radius:999px;font-size:10px;font-weight:800;">{row['status']}</span>
            <span style="background:{watch_bg};color:{watch_fg};padding:5px 9px;border-radius:999px;font-size:10px;font-weight:800;display:{watch_display};">{watch_tier}</span>
            <span style="background:#efe2ff;color:#6b21a8;padding:4px 8px;border-radius:999px;font-size:9px;font-weight:800;display:{best_display};">🏆 Best Bet</span>
            {injury_html}
            {lineup_html}
        </div>

        <div style="font-size:21px;font-weight:800;margin-bottom:5px;">{row['selection']}</div>
        <div style="color:#d4dbe8;font-size:12px;margin-bottom:8px;">{row['game']} • {prop_market_label(row['market']) if is_prop_market(row['market']) else str(row['market']).title()}</div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px 12px;margin-bottom:6px;">
            <div><div style="color:#91a0b7;font-size:10px;">Odds</div><div style="font-weight:700;">{row['odds']}</div></div>
            <div><div style="color:#91a0b7;font-size:10px;">AI Score</div><div style="color:#60a5fa;font-weight:700;">{row['score']}</div></div>
            <div><div style="color:#91a0b7;font-size:10px;">Implied Prob</div><div style="font-weight:700;">{implied_prob:.1f}%</div></div>
            <div><div style="color:#91a0b7;font-size:10px;">True Prob</div><div style="font-weight:700;">{true_prob:.1f}%</div></div>
            <div><div style="color:#91a0b7;font-size:10px;">Value Edge</div><div style="color:{edge_color};font-weight:700;">{value_edge:.2f}%</div></div>
            <div><div style="color:#91a0b7;font-size:10px;">Units</div><div style="font-weight:700;">{row['units']:.2f}u</div></div>
            <div><div style="color:#91a0b7;font-size:10px;">Consensus</div><div style="font-weight:700;">{row['consensus']}</div></div>
            <div><div style="color:#91a0b7;font-size:10px;">Books</div><div style="font-weight:700;">{row['books_seen']}</div></div>
            <div><div style="color:#91a0b7;font-size:10px;">True Conf</div><div style="font-weight:700;">{row['true_confidence']:.1f}</div></div>
            <div><div style="color:#91a0b7;font-size:10px;">Quality</div><div style="font-weight:700;">{row['quality_label']}</div></div>
            {context_html}
        </div>

        <div style="height:1px;background:#283550;margin:6px 0;"></div>

        <div style="color:#91a0b7;font-size:10px;">Confidence • {conf_label}</div>
        <div style="width:100%;height:5px;background:#24324b;border-radius:999px;">
            <div style="width:{fill_width};height:5px;background:{fill_color};border-radius:999px;"></div>
        </div>

        <div style="margin-top:6px;">{tags_html}</div>
        {note_html}

    </div></body></html>
    """

    components.html(html, height=390 if is_mobile() else 445, scrolling=False)
# =========================================================
# PARLAY CARD RENDER
# =========================================================
def render_parlay_card(parlay):
    if not parlay:
        st.info("No qualifying parlay available.")
        return

    risk_color = {
        "Low": "#10b981",
        "Moderate": "#f59e0b",
        "Elevated": "#ef4444",
    }.get(parlay["risk_label"], "#94a3b8")

    legs_html = ""
    for i, leg in enumerate(parlay["legs"], start=1):
        legs_html += f"""
        <div style="padding:6px 0;border-bottom:1px solid #243047;">
            <div style="font-weight:800;">{i}. {leg['selection']}</div>
            <div style="font-size:12px;color:#cbd5e1;">
                {leg['game']} • {prop_market_label(leg['market']) if is_prop_market(leg['market']) else "Team Market"} • {leg['odds']}
            </div>
        </div>
        """

    html = f"""
    <html>
    <body style="margin:0;font-family:sans-serif;">
        <div style="background:#0e1422;border-radius:20px;padding:12px;border:1px solid #243047;color:white;">
            <div style="font-weight:800;margin-bottom:6px;">🔥 AI PARLAY</div>
            <div style="margin-bottom:6px;">{parlay['approval_type']}</div>
            <div style="margin-bottom:6px;">Odds: {parlay['combined_odds']} | Conf: {parlay['avg_true_conf']}</div>
            <div style="color:{risk_color};font-weight:800;margin-bottom:10px;">Risk: {parlay['risk_label']}</div>
            {legs_html}
        </div>
    </body>
    </html>
    """

    components.html(html, height=260, scrolling=False)
# =========================================================
# TABLE RENDER HELPERS
# =========================================================
def render_parlay_table(candidates, title):
    st.markdown(f"**{title}**")

    if not candidates:
        st.info("No candidates.")
        return

    rows = []
    for p in candidates[:5]:
        rows.append(
            {
                "Legs": p.get("leg_count"),
                "Odds": p.get("combined_odds"),
                "Avg Conf": round(p.get("avg_true_conf", 0), 1),
                "Avg Edge": round(p.get("avg_edge", 0), 2),
                "Score": round(p.get("display_score", p.get("score", 0)), 1),
                "Risk": p.get("risk_label"),
            }
        )

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_table_desktop(df: pd.DataFrame):
    cols = [
        "tier",
        "quality_label",
        "status",
        "watch_tier",
        "game",
        "market",
        "selection",
        "odds",
        "implied_prob",
        "true_prob",
        "edge",
        "score",
        "context_score",
        "injury_flag",
        "lineup_flag",
        "sportsdata_note",
        "units",
        "confidence",
        "true_confidence",
        "books_seen",
        "best_price",
        "consensus",
        "price_edge",
    ]
    existing_cols = [c for c in cols if c in df.columns]

    table_df = df[existing_cols].copy()

    if "implied_prob" in table_df.columns:
        table_df["implied_prob"] = pd.to_numeric(table_df["implied_prob"], errors="coerce").round(1)
    if "true_prob" in table_df.columns:
        table_df["true_prob"] = pd.to_numeric(table_df["true_prob"], errors="coerce").round(1)
    if "edge" in table_df.columns:
        table_df["edge"] = pd.to_numeric(table_df["edge"], errors="coerce").round(2)
    if "true_confidence" in table_df.columns:
        table_df["true_confidence"] = pd.to_numeric(table_df["true_confidence"], errors="coerce").round(1)

    st.dataframe(table_df, use_container_width=True, hide_index=True)


def render_mobile_or_table(df: pd.DataFrame, best_first: bool = False):
    if df.empty:
        st.info("No plays available.")
        return

    if is_mobile():
        for idx, (_, row) in enumerate(df.iterrows()):
            render_play_card(row, show_best_badge=(best_first and idx == 0))
    else:
        render_table_desktop(df)


# =========================================================
# ROI CALCULATOR (CATEGORY-BASED)
# =========================================================
def build_roi_dashboard(log_df: pd.DataFrame):
    if log_df is None or log_df.empty:
        return pd.DataFrame()

    df = log_df.copy()

    if "log_category" not in df.columns:
        df["log_category"] = "Uncategorized"

    # Only settled bets
    df = df[df["result"].isin(["Win", "Loss", "Push"])].copy()
    if df.empty:
        return pd.DataFrame()

    df["units"] = pd.to_numeric(df.get("units", 0), errors="coerce").fillna(0.0)
    df["profit"] = pd.to_numeric(df.get("profit", 0), errors="coerce").fillna(0.0)

    expanded_rows = []

    for _, row in df.iterrows():
        categories = normalize_log_categories(row.get("log_category", ""))

        if not categories:
            categories = ["Uncategorized"]

        for category in categories:
            row_copy = row.copy()
            row_copy["category_bucket"] = category
            expanded_rows.append(row_copy)

    if not expanded_rows:
        return pd.DataFrame()

    expanded_df = pd.DataFrame(expanded_rows)

    rows = []

    for category, g in expanded_df.groupby("category_bucket"):
        total_bets = len(g)
        wins = (g["result"] == "Win").sum()
        losses = (g["result"] == "Loss").sum()
        pushes = (g["result"] == "Push").sum()

        units_risked = float(g["units"].sum())
        total_profit = float(g["profit"].sum())

        roi = (total_profit / units_risked * 100.0) if units_risked > 0 else 0.0
        win_rate = (wins / (wins + losses) * 100.0) if (wins + losses) > 0 else 0.0

        rows.append(
            {
                "Category": category,
                "Bets": total_bets,
                "Wins": int(wins),
                "Losses": int(losses),
                "Pushes": int(pushes),
                "Win Rate %": round(win_rate, 1),
                "Units Risked": round(units_risked, 2),
                "Profit": round(total_profit, 2),
                "ROI %": round(roi, 2),
            }
        )

    return (
        pd.DataFrame(rows)
        .sort_values(["ROI %", "Profit", "Bets"], ascending=False)
        .reset_index(drop=True)
    )

# =========================================================
# V33 SELF-LEARNING ENGINE
# =========================================================
LEARNING_MIN_SAMPLE = 8

def learning_bucket_edge(edge_value):
    edge_value = safe_float(edge_value, 0)
    if edge_value < 4.0:
        return "<4.0"
    if edge_value < 5.5:
        return "4.0-5.49"
    return "5.5+"

def learning_bucket_true_conf(tc):
    tc = safe_float(tc, 0)
    if tc < 65:
        return "<65"
    if tc < 70:
        return "65-69.9"
    if tc < 75:
        return "70-74.9"
    return "75+"

def build_learning_bucket_table(df: pd.DataFrame, bucket_col: str, label_col: str):
    if df is None or df.empty or bucket_col not in df.columns:
        return pd.DataFrame(columns=[label_col, "Bets", "Wins", "Losses", "Pushes", "Win Rate %", "Profit", "ROI %"])

    rows = []

    for bucket, g in df.groupby(bucket_col):
        wins = (g["result"] == "Win").sum()
        losses = (g["result"] == "Loss").sum()
        pushes = (g["result"] == "Push").sum()
        units_risked = safe_float(g["units"].sum(), 0)
        profit = safe_float(g["profit"].sum(), 0)

        win_rate = (wins / (wins + losses) * 100.0) if (wins + losses) > 0 else 0.0
        roi = (profit / units_risked * 100.0) if units_risked > 0 else 0.0

        rows.append(
            {
                label_col: bucket,
                "Bets": int(len(g)),
                "Wins": int(wins),
                "Losses": int(losses),
                "Pushes": int(pushes),
                "Win Rate %": round(win_rate, 1),
                "Profit": round(profit, 2),
                "ROI %": round(roi, 2),
            }
        )

    if not rows:
        return pd.DataFrame(columns=[label_col, "Bets", "Wins", "Losses", "Pushes", "Win Rate %", "Profit", "ROI %"])

    return pd.DataFrame(rows).sort_values(["ROI %", "Profit", "Bets"], ascending=False).reset_index(drop=True)

def build_self_learning_state(log_df: pd.DataFrame):
    defaults = default_learning_settings()

    state = {
        "sample_size": 0,
        "ai_sample_size": 0,
        "overall_roi": 0.0,
        "overall_profit": 0.0,
        "notes": [],
        "settings": defaults.copy(),
        "confidence_table": pd.DataFrame(),
        "edge_table": pd.DataFrame(),
        "market_table": pd.DataFrame(),
    }

    if log_df is None or log_df.empty:
        return state

    df = log_df.copy()

    if "result" not in df.columns:
        return state

    df = df[df["result"].isin(["Win", "Loss", "Push"])].copy()
    if df.empty:
        return state

    df["units"] = pd.to_numeric(df.get("units", 0), errors="coerce").fillna(0.0)
    df["profit"] = pd.to_numeric(df.get("profit", 0), errors="coerce").fillna(0.0)
    df["edge"] = pd.to_numeric(df.get("edge", None), errors="coerce")
    df["true_confidence"] = pd.to_numeric(df.get("true_confidence", None), errors="coerce")

    state["sample_size"] = int(len(df))
    state["overall_profit"] = round(float(df["profit"].sum()), 2)

    total_units = float(df["units"].sum())
    state["overall_roi"] = round((state["overall_profit"] / total_units * 100.0), 2) if total_units > 0 else 0.0

    ai_df = df.dropna(subset=["edge", "true_confidence"]).copy()
    state["ai_sample_size"] = int(len(ai_df))

    if ai_df.empty:
        return state

    ai_df["edge_bucket"] = ai_df["edge"].apply(learning_bucket_edge)
    ai_df["true_conf_bucket"] = ai_df["true_confidence"].apply(learning_bucket_true_conf)
    ai_df["market_bucket"] = ai_df["market"].apply(lambda x: market_family(x))

    state["confidence_table"] = build_learning_bucket_table(ai_df, "true_conf_bucket", "True Conf Bucket")
    state["edge_table"] = build_learning_bucket_table(ai_df, "edge_bucket", "Edge Bucket")
    state["market_table"] = build_learning_bucket_table(ai_df, "market_bucket", "Market")

    settings = defaults.copy()
    notes = []

    # -----------------------------------------------------
    # Threshold learning
    # -----------------------------------------------------
    edge_mid = ai_df[(ai_df["edge"] >= 4.0) & (ai_df["edge"] < 5.5)].copy()
    if len(edge_mid) >= LEARNING_MIN_SAMPLE:
        wins = (edge_mid["result"] == "Win").sum()
        losses = (edge_mid["result"] == "Loss").sum()
        units_risked = float(edge_mid["units"].sum())
        profit = float(edge_mid["profit"].sum())
        roi = (profit / units_risked * 100.0) if units_risked > 0 else 0.0
        win_rate = (wins / (wins + losses) * 100.0) if (wins + losses) > 0 else 0.0

        if roi < -8 or win_rate < 45:
            settings["min_active_edge"] = round(clamp(MIN_ACTIVE_EDGE + 0.50, MIN_ACTIVE_EDGE, 5.50), 2)
            notes.append("Raised active edge threshold because mid-edge bets are underperforming.")

    conf_mid = ai_df[(ai_df["true_confidence"] >= 70.0) & (ai_df["true_confidence"] < 75.0)].copy()
    if len(conf_mid) >= LEARNING_MIN_SAMPLE:
        wins = (conf_mid["result"] == "Win").sum()
        losses = (conf_mid["result"] == "Loss").sum()
        units_risked = float(conf_mid["units"].sum())
        profit = float(conf_mid["profit"].sum())
        roi = (profit / units_risked * 100.0) if units_risked > 0 else 0.0
        win_rate = (wins / (wins + losses) * 100.0) if (wins + losses) > 0 else 0.0

        if roi < -8 or win_rate < 45:
            settings["min_active_true_conf"] = round(clamp(MIN_ACTIVE_TRUE_CONF + 2.0, MIN_ACTIVE_TRUE_CONF, 76.0), 1)
            notes.append("Raised active true-confidence threshold because low-end active confidence bets are underperforming.")

    settings["min_watch_edge"] = round(max(MIN_WATCH_EDGE, settings["min_active_edge"] - 1.75), 2)
    settings["min_watch_true_conf"] = round(max(MIN_WATCH_TRUE_CONF, settings["min_active_true_conf"] - 15.0), 1)

    # -----------------------------------------------------
    # Unit-size learning by confidence bucket
    # -----------------------------------------------------
    conf_multipliers = {
        "Low": 0.92,
        "Medium": 1.00,
        "High": 1.00,
        "Elite": 1.05,
    }

    bucket_map = {
        "Low": ai_df[ai_df["true_confidence"] < 65],
        "Medium": ai_df[(ai_df["true_confidence"] >= 65) & (ai_df["true_confidence"] < 70)],
        "High": ai_df[(ai_df["true_confidence"] >= 70) & (ai_df["true_confidence"] < 75)],
        "Elite": ai_df[ai_df["true_confidence"] >= 75],
    }

    for bucket_name, bucket_df in bucket_map.items():
        if len(bucket_df) < LEARNING_MIN_SAMPLE:
            continue

        wins = (bucket_df["result"] == "Win").sum()
        losses = (bucket_df["result"] == "Loss").sum()
        units_risked = float(bucket_df["units"].sum())
        profit = float(bucket_df["profit"].sum())
        roi = (profit / units_risked * 100.0) if units_risked > 0 else 0.0
        win_rate = (wins / (wins + losses) * 100.0) if (wins + losses) > 0 else 0.0

        if roi <= -10 or win_rate <= 44:
            conf_multipliers[bucket_name] = 0.92
        elif roi >= 10 and win_rate >= 55:
            conf_multipliers[bucket_name] = 1.08 if bucket_name in ["High", "Elite"] else 1.03

    settings["unit_mult_low"] = conf_multipliers["Low"]
    settings["unit_mult_medium"] = conf_multipliers["Medium"]
    settings["unit_mult_high"] = conf_multipliers["High"]
    settings["unit_mult_elite"] = conf_multipliers["Elite"]

    state["notes"] = notes
    state["settings"] = settings
    return state
# =========================================================
# PORTFOLIO LAYER
# =========================================================
def build_ai_portfolio(best_single, chosen_parlay, parlay_candidates):
    portfolio = []
    used_keys = set()
    running_units = 0.0

    if best_single is not None:
        units = scale_single_units(best_single)
        key = f"single::{best_single.get('play_id', best_single.get('selection', ''))}"

        if running_units + units <= TEST_DAILY_UNIT_CAP:
            portfolio.append(
                {
                    "type": "Single",
                    "label": "Core Play",
                    "units": units,
                    "data": best_single,
                }
            )
            used_keys.add(key)
            running_units += units

    if chosen_parlay is not None:
        units = scale_parlay_units(chosen_parlay)
        key = "parlay::" + "|".join([leg.get("selection", "") for leg in chosen_parlay.get("legs", [])])

        if key not in used_keys and running_units + units <= TEST_DAILY_UNIT_CAP:
            portfolio.append(
                {
                    "type": "Parlay",
                    "label": chosen_parlay.get("approval_type", "Primary"),
                    "units": units,
                    "data": chosen_parlay,
                }
            )
            used_keys.add(key)
            running_units += units

    return portfolio
    
# =========================================================
# DATA PREP (CRITICAL FIX)
# =========================================================
df = generate_ai_plays()

# =========================================================
# APPLY SPORTSDATA ENRICHMENT
# =========================================================
try:
    if df is not None and len(df) > 0:
        df = enrich_plays_with_sportsdata(
            df,
            sport=selected_sportsdata_sport,
            game_date=sportsdata_game_date
        )
        df = recalculate_play_metrics(df)
except Exception as e:
    st.warning(f"SportsData enrichment skipped: {e}")

# ================================
# AUTO LOG TOP PLAYS
# ================================
auto_logged_count = auto_log_active_plays(df)

active_df = df[df["status"] == "Active"].copy().reset_index(drop=True)
watch_df = df[df["status"] == "Watch"].copy().reset_index(drop=True)

# ================================
# BEST SINGLE
# ================================
best_row = None
if not active_df.empty:
    best_row = active_df.sort_values(
        ["rank_score", "true_confidence"],
        ascending=False
    ).iloc[0]

# ================================
# PARLAY ENGINE
# ================================
best_parlay, sharp_candidates, fallback_candidates = choose_best_parlay(active_df)

# ================================
# SAFE LOGGING (RUN ONCE PER NEW PLAY)
# ================================
if best_row is not None:
    log_ai_slip_pick(best_row)

if best_parlay is not None:
    log_ai_parlay_pick(best_parlay)

# ================================
# PORTFOLIO BUILD
# ================================
all_portfolio_candidates = [*sharp_candidates, *fallback_candidates]
portfolio = build_ai_portfolio(best_row, best_parlay, all_portfolio_candidates)

# ================================
# SNAPSHOT METRICS
# ================================
avg_active_edge = active_df["edge"].mean() if not active_df.empty else 0.0
best_score = best_row["score"] if best_row is not None else "—"
avg_true_conf = active_df["true_confidence"].mean() if not active_df.empty else 0.0
avg_true_prob = active_df["true_prob"].mean() if (not active_df.empty and "true_prob" in active_df.columns) else 0.0
total_units = active_df["units"].sum() if not active_df.empty else 0.0

# =========================================================
# PAGE STYLES
# =========================================================
st.markdown(
    """
<style>
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
.stApp {
    background-color: #f6f7fb;
}
.block-container {
    max-width: 880px;
    padding-top: 0.85rem;
    padding-bottom: 1.8rem;
}
h1, h2, h3 {
    letter-spacing: -0.02em;
    color: #202533;
}
.metric-panel {
    background: #ffffff;
    border: 1px solid #e7ebf2;
    border-radius: 18px;
    padding: 10px 12px;
    margin-bottom: 10px;
}
.metric-panel-title {
    color: #1f2937;
    font-weight: 800;
    font-size: 0.94rem;
    margin-bottom: 6px;
}
.metric-mini-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px 12px;
}
.metric-mini-label {
    font-size: 0.75rem;
    color: #6b7280;
}
.metric-mini-value {
    font-size: 0.98rem;
    font-weight: 800;
    color: #111827;
}
.nav-wrap {
    background: #ffffff;
    border: 1px solid #e6eaf2;
    border-radius: 18px;
    padding: 10px 12px 7px 12px;
    margin-bottom: 12px;
}
.section-title {
    font-size: 0.98rem;
    font-weight: 800;
    margin-bottom: 0.25rem;
    color: #1e2430;
}
.slip-card {
    background: linear-gradient(180deg, #151b29 0%, #0e1422 100%);
    border: 1px solid #243047;
    border-radius: 22px;
    padding: 13px;
    margin-bottom: 10px;
    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.14);
}
.slip-kicker {
    color: #fbbf24;
    font-size: 0.82rem;
    font-weight: 800;
    margin-bottom: 5px;
}
.slip-title {
    color: #ffffff;
    font-size: 1.35rem;
    font-weight: 800;
    margin-bottom: 5px;
    letter-spacing: -0.03em;
}
.slip-meta {
    color: #d6deea;
    font-size: 0.86rem;
    margin-bottom: 3px;
}
.bet-form-wrap {
    background: #ffffff;
    border: 1px solid #e7ebf2;
    border-radius: 20px;
    padding: 14px;
    margin-bottom: 14px;
}
.notice-box {
    background: #ecfdf5;
    border: 1px solid #a7f3d0;
    color: #065f46;
    border-radius: 16px;
    padding: 10px 12px;
    margin-bottom: 10px;
    font-weight: 700;
}
</style>
""",
    unsafe_allow_html=True,
)

# =========================================================
# HEADER
# =========================================================
status_text, status_dot, status_bg, status_fg = api_status_label()

st.title("🔥 Sports Betting AI Dashboard V34")
st.caption("Manual Live Odds Refresh • SportsDataIO Context • Cached Fallback • True Probability + True Confidence Engine")

st.markdown(
    f"""
    <div style="
        display:inline-flex;
        align-items:center;
        gap:8px;
        background:{status_bg};
        color:{status_fg};
        border:1px solid #e5e7eb;
        border-radius:999px;
        padding:6px 12px;
        font-weight:800;
        margin-bottom:10px;">
        <span style="
            width:10px;
            height:10px;
            border-radius:999px;
            background:{status_dot};
            display:inline-block;"></span>
        API {status_text}
    </div>
    """,
    unsafe_allow_html=True,
)

if status_text in ["CACHED", "LIMIT HIT", "OFFLINE", "KEY ERROR", "NO KEY"]:
    st.info("Fallback mode is active. Cached odds will be used when available. If no cached odds exist yet, no live market plays can be generated.")

if auto_logged_count > 0:
    st.markdown(
        f'<div class="notice-box">Auto-logged {auto_logged_count} new active play(s).</div>',
        unsafe_allow_html=True,
    )

# =========================================================
# SNAPSHOT
# =========================================================
st.markdown('<div class="metric-panel">', unsafe_allow_html=True)
st.markdown('<div class="metric-panel-title">Market Snapshot</div>', unsafe_allow_html=True)
st.markdown(
    f"""
    <div class="metric-mini-grid">
        <div><div class="metric-mini-label">Active Plays</div><div class="metric-mini-value">{len(active_df)}</div></div>
        <div><div class="metric-mini-label">Watchlist</div><div class="metric-mini-value">{len(watch_df)}</div></div>
        <div><div class="metric-mini-label">Best Score</div><div class="metric-mini-value">{best_score}</div></div>
        <div><div class="metric-mini-label">Avg Value Edge</div><div class="metric-mini-value">{avg_active_edge:.2f}%</div></div>
        <div><div class="metric-mini-label">Avg True Prob</div><div class="metric-mini-value">{avg_true_prob:.1f}%</div></div>
        <div><div class="metric-mini-label">Avg True Conf</div><div class="metric-mini-value">{avg_true_conf:.1f}</div></div>
        <div><div class="metric-mini-label">Total Active Units</div><div class="metric-mini-value">{total_units:.2f}u</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# BET LOG HELPERS
# =========================================================
def normalize_result_value(result_value):
    value = str(result_value).strip().title()
    if value in ["Pending", "Win", "Loss", "Push"]:
        return value
    return "Pending"


def update_logged_bet_result(play_id, result_value):
    result_value = normalize_result_value(result_value)
    updated = False

    for i, bet in enumerate(st.session_state.get("bet_log", [])):
        if str(bet.get("play_id", "")).strip() != str(play_id).strip():
            continue

        units = bet.get("units", 0)
        odds = bet.get("odds", "")

        st.session_state["bet_log"][i]["result"] = result_value
        st.session_state["bet_log"][i]["profit"] = settle_result_pnl(odds, units, result_value)
        updated = True
        break

    if updated:
        save_bet_log()

    return updated


def sync_manual_results_into_bet_log():
    manual_results = st.session_state.get("manual_results", {})
    if not manual_results:
        return

    changed = False

    for i, bet in enumerate(st.session_state.get("bet_log", [])):
        pid = str(bet.get("play_id", "")).strip()
        if not pid or pid not in manual_results:
            continue

        result_value = normalize_result_value(manual_results.get(pid, "Pending"))
        current_result = normalize_result_value(bet.get("result", "Pending"))
        current_profit = float(bet.get("profit", 0.0) or 0.0)

        new_profit = settle_result_pnl(
            bet.get("odds", ""),
            bet.get("units", 0),
            result_value,
        )

        if current_result != result_value or round(current_profit, 2) != round(new_profit, 2):
            st.session_state["bet_log"][i]["result"] = result_value
            st.session_state["bet_log"][i]["profit"] = new_profit
            changed = True

    if changed:
        save_bet_log()
# =========================================================
# NAVIGATION
# =========================================================
st.markdown('<div class="nav-wrap">', unsafe_allow_html=True)
st.markdown('<div class="section-title">🚀 Navigation</div>', unsafe_allow_html=True)

nav = st.radio(
    "Navigation",
    ["Top Plays", "Watchlist", "AI Slip", "Bet Log"],
    horizontal=True,
    label_visibility="collapsed",
    key="nav_choice_native",
)

st.session_state["nav_choice"] = nav
st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# TOP PLAYS
# =========================================================
if nav == "Top Plays":
    st.header("🎯 Top Plays")
    st.caption("Up to 10 qualified plays only. No filler.")

    if len(get_effective_odds_games()) == 0:
        st.warning("Press 'Refresh Live Odds' in the sidebar to load live odds.")
    else:
        top_df = (
            active_df.sort_values(["rank_score", "true_confidence"], ascending=False)
            .head(TOP_PLAYS_LIMIT)
            .reset_index(drop=True)
        )

        if top_df.empty:
            st.info("No plays met the active criteria for the current live slate.")
        else:
            render_mobile_or_table(top_df, best_first=True)

# =========================================================
# WATCHLIST
# =========================================================
elif nav == "Watchlist":
    st.header("👀 Watchlist")
    st.caption("Near-qualified plays only.")

    if len(get_effective_odds_games()) == 0:
        st.warning("Press 'Refresh Live Odds' in the sidebar to load live odds.")
    else:
        wl_df = (
            watch_df.sort_values(["rank_score", "true_confidence"], ascending=False)
            .head(WATCHLIST_LIMIT)
            .reset_index(drop=True)
        )

        render_mobile_or_table(wl_df)

# =========================================================
# AI SLIP + PARLAY INTELLIGENCE
# =========================================================
elif nav == "AI Slip":
    st.header("🧠 AI Slip")

    if today_games:
        st.caption("Filtered Slate: " + " | ".join(today_games))
    else:
        st.caption("Using all live games returned by the API.")

    if len(get_effective_odds_games()) == 0:
        st.warning("Press 'Refresh Live Odds' in the sidebar to load live odds.")
    elif best_row is not None:
        risk_level = "Low" if float(best_row["units"]) <= 0.60 else "Moderate"

        st.markdown(
            f"""
            <div class="slip-card">
                <div class="slip-kicker">🔥 AI Recommended Single</div>
                <div class="slip-title">{best_row['selection']}</div>
                <div class="slip-meta">{best_row['game']} • {prop_market_label(best_row['market']) if is_prop_market(best_row['market']) else str(best_row['market']).title()}</div>
                <div class="slip-meta"><strong>Odds:</strong> {best_row['odds']}</div>
                <div class="slip-meta"><strong>Implied Probability:</strong> {float(best_row.get('implied_prob', 0)):.1f}%</div>
                <div class="slip-meta"><strong>True Probability:</strong> {float(best_row.get('true_prob', 0)):.1f}%</div>
                <div class="slip-meta"><strong>Value Edge:</strong> {float(best_row.get('edge', 0)):.2f}%</div>
                <div class="slip-meta"><strong>Confidence:</strong> {best_row['confidence']}</div>
                <div class="slip-meta"><strong>True Confidence:</strong> {best_row['true_confidence']:.1f}</div>
                <div class="slip-meta"><strong>Quality Label:</strong> {best_row['quality_label']}</div>
                <div class="slip-meta"><strong>Type:</strong> Single best bet</div>
                <div class="slip-meta"><strong>Risk Level:</strong> {risk_level}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        render_play_card(best_row, show_best_badge=True)
    else:
        st.info("No active AI single available.")

    st.subheader("🎯 AI Parlay Intelligence")

    if best_parlay is None:
        st.info("Not enough qualifying legs.")
    else:
        render_parlay_card(best_parlay)

    with st.expander("Show top parlay candidates", expanded=False):
        render_parlay_table(sharp_candidates, "Sharp Approved")
        render_parlay_table(fallback_candidates, "Fallback")

    st.subheader("🧠 AI Portfolio Allocation")

    if not portfolio:
        st.info("No portfolio available.")
    else:
        rows = []

        for item in portfolio:
            data = item["data"]

            if item["type"] == "Single":
                summary = f"{data['selection']} ({data['game']})"
                odds = data["odds"]
                conf = data["true_confidence"]
            else:
                summary = " | ".join([leg["selection"] for leg in data["legs"]])
                odds = data["combined_odds"]
                conf = data["avg_true_conf"]

            rows.append(
                {
                    "Label": item["label"],
                    "Type": item["type"],
                    "Units": item["units"],
                    "Odds": odds,
                    "Confidence": conf,
                    "Summary": summary,
                }
            )

        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# =========================================================
# BET LOG
# =========================================================
elif nav == "Bet Log":
    st.header("🧾 Bet Log")

    sync_manual_results_into_bet_log()

    st.subheader("📊 ROI Dashboard")

    log_df_full = pd.DataFrame(st.session_state.get("bet_log", []))
    roi_df = build_roi_dashboard(log_df_full)

    if roi_df.empty:
        st.info("No settled bets yet.")
    else:
        st.dataframe(roi_df, use_container_width=True, hide_index=True)

    if len(st.session_state.get("bet_log", [])) == 0:
        st.info("No bets logged yet.")
    else:
        log_df = pd.DataFrame(st.session_state["bet_log"]).copy()

        if "units" in log_df.columns:
            log_df["units"] = pd.to_numeric(log_df["units"], errors="coerce").fillna(0).round(2)
        if "profit" in log_df.columns:
            log_df["profit"] = pd.to_numeric(log_df["profit"], errors="coerce").fillna(0).round(2)
        if "implied_prob" in log_df.columns:
            log_df["implied_prob"] = pd.to_numeric(log_df["implied_prob"], errors="coerce").round(2)
        if "true_prob" in log_df.columns:
            log_df["true_prob"] = pd.to_numeric(log_df["true_prob"], errors="coerce").round(2)
        if "true_confidence" in log_df.columns:
            log_df["true_confidence"] = pd.to_numeric(log_df["true_confidence"], errors="coerce").round(1)
        if "edge" in log_df.columns:
            log_df["edge"] = pd.to_numeric(log_df["edge"], errors="coerce").round(2)

        st.dataframe(log_df, use_container_width=True, hide_index=True)

        st.subheader("Update Results")

        selectable_labels = []
        selectable_map = {}

        for _, r in log_df.iterrows():
            pid = str(r.get("play_id", "")).strip()
            selection = str(r.get("selection", ""))
            game = str(r.get("game", ""))

            if not pid:
                continue

            short_pid = pid[:8]
            label = f"{selection} • {game} • ID {short_pid}"

            suffix = 2
            base_label = label
            while label in selectable_map:
                label = f"{base_label} ({suffix})"
                suffix += 1

            selectable_labels.append(label)
            selectable_map[label] = pid

        if selectable_labels:
            selected_label = st.selectbox("Select Bet", selectable_labels)
            selected_id = selectable_map[selected_label]

            existing_result = "Pending"
            for bet in st.session_state.get("bet_log", []):
                if str(bet.get("play_id", "")).strip() == selected_id:
                    existing_result = normalize_result_value(bet.get("result", "Pending"))
                    break

            result_choice = st.selectbox(
                "Result",
                ["Pending", "Win", "Loss", "Push"],
                index=["Pending", "Win", "Loss", "Push"].index(existing_result),
            )

            if st.button("Save Result"):
                st.session_state["manual_results"][selected_id] = result_choice
                updated = update_logged_bet_result(selected_id, result_choice)

                if updated:
                    st.success("Updated.")
                    st.rerun()
                else:
                    st.warning("Could not update that bet.")
        else:
            st.info("No selectable bets found.")

    # ================================
    # MANUAL BET ENTRY
    # ================================
    st.markdown('<div class="bet-form-wrap">', unsafe_allow_html=True)

    with st.form("manual_bet", clear_on_submit=True):
        c1, c2 = st.columns(2)

        with c1:
            game = st.text_input("Game")
            market = st.selectbox("Market", ["moneyline", "spread", "total"])
            units = st.number_input("Units", min_value=0.0, max_value=10.0, value=0.5, step=0.25)

        with c2:
            selection = st.text_input("Selection")
            odds = st.text_input("Odds")
            confidence = st.selectbox("Confidence", ["Low", "Medium", "High", "Elite"])

        submit = st.form_submit_button("Add Bet")

        if submit:
            game_clean = str(game).strip()
            market_clean = str(market).strip().lower()
            selection_clean = str(selection).strip()
            odds_clean = str(odds).strip()

            if not game_clean or not selection_clean or not odds_clean:
                st.warning("Game, selection, and odds are required.")
            elif american_to_int(odds_clean) is None:
                st.warning("Odds must be valid American odds like -110 or +125.")
            else:
                new_play_id = build_play_id(
                    {
                        "game": game_clean,
                        "market": market_clean,
                        "selection": selection_clean,
                        "odds": odds_clean,
                    }
                )

                existing_ids = {
                    str(r.get("play_id", "")).strip()
                    for r in st.session_state.get("bet_log", [])
                }

                if new_play_id in existing_ids:
                    st.warning("That bet already exists in the log.")
                else:
                    new = {
                        "play_id": new_play_id,
                        "game": game_clean,
                        "market": market_clean,
                        "selection": selection_clean,
                        "odds": odds_clean,
                        "implied_prob": None,
                        "true_prob": None,
                        "units": round(float(units), 2),
                        "confidence": confidence,
                        "true_confidence": None,
                        "edge": None,
                        "books_seen": None,
                        "consensus": None,
                        "result": "Pending",
                        "profit": 0.0,
                        "mode": TEST_MODE,
                        "log_category": "Manual",
                        "timestamp": datetime.now().isoformat(),
                    }

                    st.session_state["bet_log"].append(new)
                    save_bet_log()
                    st.success("Bet added.")
                    st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# ADAPTIVE SETTINGS
# =========================================================
with st.expander("⚙️ Adaptive Settings", expanded=False):
    c1, c2 = st.columns(2)

    with c1:
        st.write(f"Min Active Edge: {MIN_ACTIVE_EDGE}")
        st.write(f"Min Watch Edge: {MIN_WATCH_EDGE}")
        st.write(f"Min Active True Conf: {MIN_ACTIVE_TRUE_CONF}")
        st.write(f"Min Active Books: {MIN_ACTIVE_BOOKS}")

    with c2:
        st.write(f"Max Top Plays: {TOP_PLAYS_LIMIT}")
        st.write(f"Max Active Plays: {MAX_ACTIVE_PLAYS}")
        st.write(f"Max Total Units: {MAX_TOTAL_UNITS}")
        st.write(f"Min Parlay Odds: +{MIN_PARLAY_ODDS}")
