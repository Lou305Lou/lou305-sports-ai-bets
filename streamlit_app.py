# =========================================================
# IMPORTS + API CONFIG (CLEAN MASTER BLOCK)
# =========================================================
import os
import re
import json
import time
import random
import hashlib
from itertools import combinations
from datetime import datetime, timedelta

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Sports Betting AI Dashboard V34", layout="wide")

# =========================================================
# MULTI-SPORT STATE + HELPERS
# =========================================================
SUPPORTED_SPORTS = {
    "NBA": {
        "sport_key": "basketball_nba",
        "sportsdata_slug": "nba",
        "label": "NBA",
    },
    "NHL": {
        "sport_key": "icehockey_nhl",
        "sportsdata_slug": "nhl",
        "label": "NHL",
    },
    "MLB": {
        "sport_key": "baseball_mlb",
        "sportsdata_slug": "mlb",
        "label": "MLB",
    },
    "WNBA": {
        "sport_key": "basketball_wnba",
        "sportsdata_slug": "wnba",
        "label": "WNBA",
    },
}

DEFAULT_SPORT = "NBA"

# WNBA intentionally excluded for now to reduce calls until season is closer
ACTIVE_REFRESH_SPORTS = ["NBA", "NHL", "MLB"]

# =========================================================
# GLOBAL CONSTANTS
# =========================================================
BET_LOG_FILE = "bet_log.csv"
LEARNING_STATE_FILE = "learning_state_by_sport.json"
TAB_SNAPSHOT_FILE = "tab_snapshots_by_sport.json"
PERSISTED_PLAYS_FILE = "persisted_plays_by_sport.json"

ODDS_API_BASE = "https://api.the-odds-api.com/v4/sports"
ODDS_REGIONS = "us"
ODDS_MARKETS = "h2h,spreads,totals"
ODDS_ODDS_FORMAT = "american"
ODDS_BOOKMAKERS = "draftkings,fanduel,betmgm,caesars,espnbet,betrivers"

DAILY_API_CALL_LIMIT = 10
API_COOLDOWN_SECONDS = 90

TEST_MODE = "Paper Test"

TOP_PLAYS_LIMIT = 10
WATCHLIST_LIMIT = 18

MIN_ACTIVE_EDGE = 4.00
MIN_WATCH_EDGE = 2.25
ACTIVE_EDGE_PROMOTION = 4.50

MIN_ACTIVE_TRUE_CONF = 70.0
MIN_WATCH_TRUE_CONF = 55.0

MIN_ACTIVE_BOOKS = 3
MIN_WATCH_BOOKS = 2

DEFAULT_ODDS_RANGE = (-200, 150)

SINGLE_UNIT_MIN = 0.40
SINGLE_UNIT_MAX = 1.25
WATCH_UNIT_MIN = 0.25
WATCH_UNIT_MAX = 0.75

PARLAY_UNIT_SHARP = 0.60
PARLAY_UNIT_FALLBACK_2 = 0.35
PARLAY_UNIT_FALLBACK_3 = 0.20

MIN_PARLAY_LEGS = 2
MAX_PARLAY_LEGS = 3
MIN_PARLAY_ODDS = 200
SHARP_PARLAY_MIN_TRUE_CONF = 70.0
SHARP_PARLAY_MAX_PENALTY = 0.16
FALLBACK_PARLAY_MAX_PENALTY = 0.28

MAX_TOTAL_UNITS = 4.25
TEST_DAILY_UNIT_CAP = 4.50

TRUE_PROB_WEIGHT = 0.30
PRICE_EDGE_WEIGHT = 0.25
MARKET_SIGNAL_WEIGHT = 0.15
MATCHUP_WEIGHT = 0.15
HISTORICAL_WEIGHT = 0.15

ENABLE_PLAYER_PROPS = True
PROPS_ONLY_STARTERS = True
PROP_TYPES_BY_SPORT = {
    "NBA": ["points", "rebounds", "assists", "pra"],
    "NHL": ["shots_on_goal", "points", "assists"],
    "MLB": ["hits", "total_bases", "runs", "rbis", "strikeouts"],
}
PROP_ODDS_RANGE = (-200, 150)
MAX_PROP_PLAYS_PER_GAME = 8

REQUIRED_BET_LOG_COLUMNS = [
    "play_id",
    "sport",
    "game",
    "market",
    "selection",
    "player",
    "team",
    "opponent",
    "line",
    "odds",
    "best_price",
    "best_book",
    "implied_prob",
    "true_prob",
    "implied_probability",
    "true_probability",
    "edge",
    "price_edge",
    "books",
    "books_seen",
    "consensus",
    "consensus_pct",
    "sharp_score",
    "market_signal",
    "matchup_score",
    "historical_score",
    "true_confidence",
    "status",
    "units",
    "stake",
    "confidence",
    "result",
    "profit",
    "mode",
    "log_category",
    "category",
    "primary_category",
    "play_type",
    "timestamp",
    "sportsdata_note",
    "injury_flag",
    "lineup_flag",
    "context_score",
    "model_score",
    "score",
    "rank_score",
    "tier",
    "quality_label",
    "watch_tier",
    "ai_tags",
    "open_odds",
    "open_line",
    "closing_odds",
    "closing_line",
    "clv_diff",
    "clv_result",
]

# =========================================================
# SECRETS / API KEYS
# =========================================================
def _read_secret(*keys, default=""):
    for key in keys:
        try:
            if key in st.secrets:
                value = st.secrets.get(key)
                if value is not None and str(value).strip() != "":
                    return str(value).strip()
        except Exception:
            pass

        env_val = os.getenv(key)
        if env_val is not None and str(env_val).strip() != "":
            return str(env_val).strip()

    return default

ODDS_API_KEY = _read_secret("THE_ODDS_API_KEY", "ODDS_API_KEY", default="")
SPORTSDATA_API_KEY = _read_secret("SPORTSDATA_API_KEY", "SPORTS_DATA_IO_API_KEY", default="")

# =========================================================
# SESSION STATE INIT
# =========================================================
def _ensure_session_defaults():
    defaults = {
        "selected_sport": DEFAULT_SPORT,
        "nav_choice": "Top Plays",
        "nav_choice_native": "Top Plays",
        "is_mobile": True,
        "sportsdata_enabled": True,
        "today_games_text": "",
        "bet_log": [],
        "manual_results": {},
        "auto_logged_ids": set(),
        "api_mode": "idle",
        "api_status_note": "",
        "last_refresh_error": "",
        "last_refresh_count": 0,
        "last_refresh_time": "",
        "last_odds_refresh_ok": False,
        "last_api_pull_epoch": 0.0,
        "daily_api_calls_used": 0,
        "odds_api_reset_expected": "",
        "odds_api_games_by_sport": {},
        "last_successful_odds_games_by_sport": {},
        "last_api_pull_epoch_by_sport": {},
        "odds_api_reset_expected_by_sport": {},
        "snapshot_refresh_id": 0,
        "snapshot_generated_at": "",
        "snapshot_last_updated": "",
        "snapshot_save_error": "",
        "snapshot_plays_df": pd.DataFrame(),
        "snapshot_all_plays_df": pd.DataFrame(),
        "snapshot_active_df": pd.DataFrame(),
        "snapshot_top_plays_df": pd.DataFrame(),
        "snapshot_watchlist_df": pd.DataFrame(),
        "snapshot_ai_slip_df": pd.DataFrame(),
        "snapshot_parlay_df": pd.DataFrame(),
        "snapshot_best_row": {},
        "plays_df": pd.DataFrame(),
        "ai_slip_df": pd.DataFrame(),
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            if isinstance(value, pd.DataFrame):
                st.session_state[key] = value.copy()
            elif isinstance(value, dict):
                st.session_state[key] = value.copy()
            elif isinstance(value, list):
                st.session_state[key] = value.copy()
            elif isinstance(value, set):
                st.session_state[key] = set(value)
            else:
                st.session_state[key] = value

_ensure_session_defaults()

# =========================================================
# BASIC HELPERS
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

def today_str():
    return pd.Timestamp.now().strftime("%Y-%m-%d")

def american_to_int(odds_str):
    try:
        return int(str(odds_str).replace("+", "").strip())
    except Exception:
        return None

def american_to_implied_prob(odds):
    odds_val = american_to_int(odds)
    if odds_val is None:
        return 0.0
    if odds_val > 0:
        return 100.0 / (odds_val + 100.0)
    return abs(odds_val) / (abs(odds_val) + 100.0)

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
    odds_int = american_to_int(odds_val)
    if odds_int is None:
        return "N/A"
    if odds_int > 0:
        return f"+{int(odds_int)}"
    return str(int(odds_int))

def build_play_id(*args):
    """
    Supports:
    - build_play_id({"game":..., "market":..., "selection":..., "odds":...})
    - build_play_id(sport, game, market, selection, line)
    """
    if len(args) == 1 and isinstance(args[0], dict):
        row_dict = args[0]
        raw = "|".join(
            [
                str(row_dict.get("sport", "")),
                str(row_dict.get("game", "")),
                str(row_dict.get("market", "")),
                str(row_dict.get("selection", "")),
                str(row_dict.get("line", row_dict.get("odds", ""))),
            ]
        )
        return hashlib.md5(raw.encode()).hexdigest()

    sport = str(args[0]).strip() if len(args) > 0 else ""
    game = str(args[1]).strip() if len(args) > 1 else ""
    market = str(args[2]).strip() if len(args) > 2 else ""
    selection = str(args[3]).strip() if len(args) > 3 else ""
    line = str(args[4]).strip() if len(args) > 4 else ""

    raw = "|".join([sport, game, market, selection, line])
    return hashlib.md5(raw.encode()).hexdigest()

def confidence_bucket_from_true_conf(true_conf):
    tc = float(safe_float(true_conf, 0))
    if tc >= 75:
        return "Elite"
    if tc >= 70:
        return "High"
    if tc >= 65:
        return "Medium"
    return "Low"

def confidence_fill_and_color(true_conf):
    tc = float(safe_float(true_conf, 0))
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
    stake = float(safe_float(stake, 0.0))
    if odds_int > 0:
        return round(stake * (odds_int / 100.0), 2)
    return round(stake * (100.0 / abs(odds_int)), 2)

def settle_result_pnl(odds, units, result):
    result = str(result).strip().lower()
    units = float(safe_float(units, 0.0))
    if result == "win":
        return american_profit(odds, units)
    if result == "loss":
        return round(-units, 2)
    return 0.0

def market_family(market):
    m = str(market).strip().lower()
    if "moneyline" in m or m in ["h2h", "ml"]:
        return "moneyline"
    if "spread" in m:
        return "spread"
    if "total" in m:
        return "total"
    if "prop" in m:
        return "prop"
    if "parlay" in m:
        return "parlay"
    return "other"

# =========================================================
# SPORT HELPERS
# =========================================================
def get_sport_config(sport_name=None):
    sport_key = str(sport_name or st.session_state.get("selected_sport", DEFAULT_SPORT)).strip().upper()
    return SUPPORTED_SPORTS.get(sport_key, SUPPORTED_SPORTS[DEFAULT_SPORT])

def get_selected_sport():
    sport = str(st.session_state.get("selected_sport", DEFAULT_SPORT)).strip().upper()
    if sport not in SUPPORTED_SPORTS:
        sport = DEFAULT_SPORT
        st.session_state["selected_sport"] = sport
    return sport

def set_selected_sport(sport_name):
    sport = str(sport_name).strip().upper()
    if sport in SUPPORTED_SPORTS:
        st.session_state["selected_sport"] = sport

def get_current_sportsdata_slug():
    return get_sport_config(get_selected_sport()).get("sportsdata_slug", "nba")

def normalize_market_name_by_sport(market_name, sport_name=None):
    market = str(market_name).strip().lower()
    if market == "h2h":
        return "moneyline"
    if market == "spreads":
        return "spread"
    if market == "totals":
        return "total"
    return market

def finalize_selected_sport_context():
    selected_sport = get_selected_sport()

    for key in [
        "plays_df",
        "snapshot_plays_df",
        "snapshot_all_plays_df",
        "snapshot_active_df",
        "snapshot_top_plays_df",
        "snapshot_watchlist_df",
        "snapshot_ai_slip_df",
        "snapshot_parlay_df",
    ]:
        value = st.session_state.get(key, pd.DataFrame())
        if not isinstance(value, pd.DataFrame):
            st.session_state[key] = pd.DataFrame()
            continue

        if value.empty:
            continue

        if "sport" in value.columns:
            filtered = value[value["sport"].astype(str).str.upper() == selected_sport].copy()
            st.session_state[key] = filtered.reset_index(drop=True)

    best_row = st.session_state.get("snapshot_best_row", {})
    if isinstance(best_row, dict) and best_row:
        row_sport = str(best_row.get("sport", selected_sport)).strip().upper()
        if row_sport != selected_sport:
            st.session_state["snapshot_best_row"] = {}

# =========================================================
# API / COOL DOWN / DAILY LIMIT HELPERS
# =========================================================
def get_odds_api_key():
    return ODDS_API_KEY

def get_daily_api_calls_used():
    return safe_int(st.session_state.get("daily_api_calls_used", 0), 0)

def set_daily_api_calls_used(value):
    st.session_state["daily_api_calls_used"] = max(0, safe_int(value, 0))

def increment_daily_api_call_count():
    set_daily_api_calls_used(get_daily_api_calls_used() + 1)

def get_daily_api_calls_remaining():
    return max(0, DAILY_API_CALL_LIMIT - get_daily_api_calls_used())

def api_cooldown_ready():
    last_epoch = safe_float(st.session_state.get("last_api_pull_epoch", 0), 0.0)
    if last_epoch <= 0:
        return True
    return (time.time() - last_epoch) >= API_COOLDOWN_SECONDS

def set_api_status(mode, note=""):
    st.session_state["api_mode"] = str(mode).strip()
    st.session_state["api_status_note"] = str(note).strip()

def set_last_pull_epoch_for_sport(epoch_value, sport_name):
    mapping = dict(st.session_state.get("last_api_pull_epoch_by_sport", {}))
    mapping[str(sport_name).strip().upper()] = float(epoch_value)
    st.session_state["last_api_pull_epoch_by_sport"] = mapping
    st.session_state["last_api_pull_epoch"] = float(epoch_value)

def set_api_reset_expected_for_sport(reset_value, sport_name):
    mapping = dict(st.session_state.get("odds_api_reset_expected_by_sport", {}))
    mapping[str(sport_name).strip().upper()] = str(reset_value).strip()
    st.session_state["odds_api_reset_expected_by_sport"] = mapping

# =========================================================
# PERSISTENCE HELPERS
# =========================================================
def _safe_load_json_file(filepath, default_value):
    try:
        if not os.path.exists(filepath):
            return default_value
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default_value

def _safe_save_json_file(filepath, payload):
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return True
    except Exception:
        return False

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
    if df is None or df.empty or "play_id" not in df.columns:
        return pd.DataFrame() if df is None else df

    working_df = df.copy()
    working_df["play_id"] = working_df["play_id"].fillna("").astype(str).str.strip()
    working_df = working_df[working_df["play_id"] != ""].copy()

    if working_df.empty:
        return working_df

    rows = []
    seen_base_ids = set()

    for _, row in working_df.iterrows():
        row_dict = row.to_dict()
        play_id = str(row_dict.get("play_id", "")).strip()
        base_id = play_id.split("__")[0].strip() if "__" in play_id else play_id

        if base_id not in seen_base_ids:
            row_dict["play_id"] = play_id
            row_dict["log_category"] = _normalize_category_text(row_dict.get("log_category", ""))
            rows.append(row_dict)
            seen_base_ids.add(base_id)
            continue

        for i, existing in enumerate(rows):
            existing_id = str(existing.get("play_id", "")).strip()
            existing_base = existing_id.split("__")[0].strip() if "__" in existing_id else existing_id

            if existing_base != base_id:
                continue

            merged_categories = _normalize_category_text(
                f"{existing.get('log_category', '')} | {row_dict.get('log_category', '')}"
            )
            rows[i]["log_category"] = merged_categories

            for field in ["result", "profit", "clv_diff", "clv_result", "closing_odds", "closing_line", "timestamp"]:
                existing_val = rows[i].get(field)
                new_val = row_dict.get(field)
                if (existing_val in [None, "", 0, 0.0]) and (new_val not in [None, ""]):
                    rows[i][field] = new_val
            break

    out = pd.DataFrame(rows)
    return out.reset_index(drop=True)

def load_bet_log():
    try:
        if not os.path.exists(BET_LOG_FILE):
            return []

        df = pd.read_csv(BET_LOG_FILE)
        if df is None or df.empty:
            return []

        for col in REQUIRED_BET_LOG_COLUMNS:
            if col not in df.columns:
                df[col] = None

        df["play_id"] = df["play_id"].fillna("").astype(str).str.strip()
        df = df[df["play_id"] != ""].copy()
        df = _merge_duplicate_play_id_rows(df)

        return df.to_dict("records")
    except Exception:
        return []

def save_bet_log(rows=None):
    try:
        if rows is None:
            rows = st.session_state.get("bet_log", [])

        df = pd.DataFrame(rows if isinstance(rows, list) else [])
        for col in REQUIRED_BET_LOG_COLUMNS:
            if col not in df.columns:
                df[col] = None

        if not df.empty:
            df = _merge_duplicate_play_id_rows(df)

        df.to_csv(BET_LOG_FILE, index=False)
        return True
    except Exception:
        return False

def build_logged_id_set(rows):
    logged_ids = set()
    for row in rows if isinstance(rows, list) else []:
        play_id = str(row.get("play_id", "")).strip()
        if play_id:
            logged_ids.add(play_id)
            base_id = play_id.split("__")[0].strip() if "__" in play_id else play_id
            if base_id:
                logged_ids.add(base_id)
    return logged_ids

def get_bet_log_for_sport(sport_name):
    selected = str(sport_name).strip().upper()
    rows = st.session_state.get("bet_log", [])
    if not isinstance(rows, list):
        return []

    filtered = []
    for row in rows:
        row_sport = str(row.get("sport", selected)).strip().upper()
        if row_sport == selected:
            filtered.append(row)
    return filtered

def load_learning_state_by_sport():
    data = _safe_load_json_file(LEARNING_STATE_FILE, {})
    return data if isinstance(data, dict) else {}

def save_learning_state_by_sport(payload):
    return _safe_save_json_file(LEARNING_STATE_FILE, payload if isinstance(payload, dict) else {})

def get_learning_state_for_sport(sport_name=None):
    sport = str(sport_name or get_selected_sport()).strip().upper()
    all_states = load_learning_state_by_sport()
    state = all_states.get(sport, {})
    return state if isinstance(state, dict) else {}

def save_learning_state_for_sport(state, sport_name=None):
    sport = str(sport_name or get_selected_sport()).strip().upper()
    all_states = load_learning_state_by_sport()
    all_states[sport] = state if isinstance(state, dict) else {}
    return save_learning_state_by_sport(all_states)

def load_tab_snapshots_from_disk():
    data = _safe_load_json_file(TAB_SNAPSHOT_FILE, {})
    return data if isinstance(data, dict) else {}

def save_tab_snapshots_to_disk():
    selected_sport = get_selected_sport()

    payload = load_tab_snapshots_from_disk()
    payload[selected_sport] = {
        "snapshot_generated_at": st.session_state.get("snapshot_generated_at", ""),
        "snapshot_last_updated": st.session_state.get("snapshot_last_updated", ""),
        "snapshot_refresh_id": safe_int(st.session_state.get("snapshot_refresh_id", 0), 0),
        "snapshot_best_row": st.session_state.get("snapshot_best_row", {}),
        "snapshot_plays_df": st.session_state.get("snapshot_plays_df", pd.DataFrame()).to_dict("records"),
        "snapshot_all_plays_df": st.session_state.get("snapshot_all_plays_df", pd.DataFrame()).to_dict("records"),
        "snapshot_active_df": st.session_state.get("snapshot_active_df", pd.DataFrame()).to_dict("records"),
        "snapshot_top_plays_df": st.session_state.get("snapshot_top_plays_df", pd.DataFrame()).to_dict("records"),
        "snapshot_watchlist_df
