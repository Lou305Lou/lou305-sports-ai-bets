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
        "snapshot_watchlist_df": st.session_state.get("snapshot_watchlist_df", pd.DataFrame()).to_dict("records"),
        "snapshot_ai_slip_df": st.session_state.get("snapshot_ai_slip_df", pd.DataFrame()).to_dict("records"),
        "snapshot_parlay_df": st.session_state.get("snapshot_parlay_df", pd.DataFrame()).to_dict("records"),
    }
    return _safe_save_json_file(TAB_SNAPSHOT_FILE, payload)

def restore_tab_snapshots_for_sport(sport_name=None):
    sport = str(sport_name or get_selected_sport()).strip().upper()
    payload = load_tab_snapshots_from_disk()
    sport_payload = payload.get(sport, {})

    if not isinstance(sport_payload, dict) or not sport_payload:
        return False

    for key in [
        "snapshot_plays_df",
        "snapshot_all_plays_df",
        "snapshot_active_df",
        "snapshot_top_plays_df",
        "snapshot_watchlist_df",
        "snapshot_ai_slip_df",
        "snapshot_parlay_df",
    ]:
        records = sport_payload.get(key, [])
        st.session_state[key] = pd.DataFrame(records if isinstance(records, list) else [])

    st.session_state["snapshot_best_row"] = sport_payload.get("snapshot_best_row", {})
    st.session_state["snapshot_generated_at"] = sport_payload.get("snapshot_generated_at", "")
    st.session_state["snapshot_last_updated"] = sport_payload.get("snapshot_last_updated", "")
    st.session_state["snapshot_refresh_id"] = safe_int(sport_payload.get("snapshot_refresh_id", 0), 0)

    return True

def persist_generated_play_snapshots(plays_df: pd.DataFrame):
    selected_sport = get_selected_sport()
    payload = _safe_load_json_file(PERSISTED_PLAYS_FILE, {})
    if not isinstance(payload, dict):
        payload = {}

    if plays_df is None or plays_df.empty:
        payload[selected_sport] = []
    else:
        safe_df = plays_df.copy()
        payload[selected_sport] = safe_df.to_dict("records")

    _safe_save_json_file(PERSISTED_PLAYS_FILE, payload)

def get_persisted_plays_df(sport_name=None):
    sport = str(sport_name or get_selected_sport()).strip().upper()
    payload = _safe_load_json_file(PERSISTED_PLAYS_FILE, {})
    if not isinstance(payload, dict):
        return pd.DataFrame()

    records = payload.get(sport, [])
    if not isinstance(records, list):
        return pd.DataFrame()

    return pd.DataFrame(records)

def clear_generated_play_snapshots():
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
        st.session_state[key] = pd.DataFrame()

    st.session_state["snapshot_best_row"] = {}
    st.session_state["snapshot_generated_at"] = ""
    st.session_state["snapshot_last_updated"] = ""

# =========================================================
# DATAFRAME NORMALIZATION + RANKING HELPERS
# =========================================================
def normalize_dataframe_for_selected_sport(df: pd.DataFrame, sport_name=None):
    if df is None or not isinstance(df, pd.DataFrame):
        return pd.DataFrame()

    working_df = df.copy()
    selected_sport = str(sport_name or get_selected_sport()).strip().upper()

    if "sport" not in working_df.columns:
        working_df["sport"] = selected_sport

    working_df["sport"] = working_df["sport"].fillna(selected_sport).astype(str).str.upper()

    for col, default_val in {
        "game": "",
        "market": "",
        "selection": "",
        "player": "",
        "team": "",
        "opponent": "",
        "line": None,
        "odds": None,
        "best_price": None,
        "best_book": "",
        "implied_prob": 0.0,
        "true_prob": 0.0,
        "implied_probability": 0.0,
        "true_probability": 0.0,
        "edge": 0.0,
        "price_edge": 0.0,
        "books": 0,
        "books_seen": 0,
        "consensus": "",
        "consensus_pct": 0.0,
        "sharp_score": 0.0,
        "market_signal": 0.0,
        "matchup_score": 0.0,
        "historical_score": 0.0,
        "true_confidence": 0.0,
        "status": "",
        "units": 0.0,
        "log_category": "",
        "sportsdata_note": "",
        "injury_flag": "",
        "lineup_flag": "",
        "model_score": 0.0,
        "score": 0.0,
        "rank_score": 0.0,
        "tier": "C",
        "quality_label": "Watch",
        "watch_tier": "",
        "ai_tags": "",
        "context_score": 0.0,
    }.items():
        if col not in working_df.columns:
            working_df[col] = default_val

    numeric_cols = [
        "line",
        "odds",
        "best_price",
        "implied_prob",
        "true_prob",
        "implied_probability",
        "true_probability",
        "edge",
        "price_edge",
        "books",
        "books_seen",
        "consensus_pct",
        "sharp_score",
        "market_signal",
        "matchup_score",
        "historical_score",
        "true_confidence",
        "units",
        "model_score",
        "score",
        "rank_score",
        "context_score",
    ]
    for col in numeric_cols:
        if col in working_df.columns:
            working_df[col] = pd.to_numeric(working_df[col], errors="coerce")

    return working_df.reset_index(drop=True)

def recalculate_play_metrics(df: pd.DataFrame):
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df

    working_df = df.copy()

    if "books_seen" not in working_df.columns and "books" in working_df.columns:
        working_df["books_seen"] = working_df["books"]

    if "price_edge" not in working_df.columns and "edge" in working_df.columns:
        working_df["price_edge"] = working_df["edge"]

    if "score" not in working_df.columns:
        working_df["score"] = pd.to_numeric(working_df.get("model_score", 0), errors="coerce").fillna(0.0)

    if "rank_score" not in working_df.columns:
        working_df["rank_score"] = 0.0

    working_df["true_confidence"] = pd.to_numeric(working_df.get("true_confidence", 0), errors="coerce").fillna(0.0)
    working_df["edge"] = pd.to_numeric(working_df.get("edge", 0), errors="coerce").fillna(0.0)
    working_df["books_seen"] = pd.to_numeric(working_df.get("books_seen", working_df.get("books", 0)), errors="coerce").fillna(0.0)
    working_df["model_score"] = pd.to_numeric(working_df.get("model_score", 0), errors="coerce").fillna(0.0)
    working_df["context_score"] = pd.to_numeric(working_df.get("context_score", 0), errors="coerce").fillna(0.0)

    working_df["rank_score"] = (
        (working_df["true_confidence"] * 0.55)
        + (working_df["edge"] * 4.0)
        + (working_df["books_seen"] * 2.0)
        + (working_df["model_score"] * 0.15)
        + (working_df["context_score"] * 1.5)
    ).round(2)

    working_df["score"] = working_df["rank_score"]

    def _tier_from_row(row):
        tc = safe_float(row.get("true_confidence", 0), 0)
        edge = safe_float(row.get("edge", 0), 0)

        if tc >= 74 and edge >= 4.5:
            return "A"
        if tc >= 66 and edge >= 3.0:
            return "B"
        return "C"

    working_df["tier"] = working_df.apply(_tier_from_row, axis=1)
    working_df["quality_label"] = working_df["tier"].apply(quality_label_from_tier)

    if "watch_tier" not in working_df.columns:
        working_df["watch_tier"] = ""

    if "ai_tags" not in working_df.columns:
        working_df["ai_tags"] = ""

    working_df["ai_tags"] = working_df.apply(
        lambda r: [
            tag for tag in [
                f"Conf {safe_float(r.get('true_confidence', 0), 0):.1f}",
                f"Edge {safe_float(r.get('edge', 0), 0):.2f}%",
                f"Books {safe_int(r.get('books_seen', r.get('books', 0)), 0)}",
            ] if str(tag).strip()
        ],
        axis=1,
    )

    return working_df.reset_index(drop=True)

# =========================================================
# TEAM NORMALIZATION
# =========================================================
def normalize_team_name(abbrev: str):
    raw = str(abbrev).strip()
    key = raw.upper()

    mapping = {
        # NBA
        "ATL": "Hawks", "ATLANTA HAWKS": "Hawks", "HAWKS": "Hawks",
        "BOS": "Celtics", "BOSTON CELTICS": "Celtics", "CELTICS": "Celtics",
        "BKN": "Nets", "BROOKLYN NETS": "Nets", "NETS": "Nets",
        "CHA": "Hornets", "CHARLOTTE HORNETS": "Hornets", "HORNETS": "Hornets",
        "CHI": "Bulls", "CHICAGO BULLS": "Bulls", "BULLS": "Bulls",
        "CLE": "Cavaliers", "CLEVELAND CAVALIERS": "Cavaliers", "CAVALIERS": "Cavaliers",
        "DAL": "Mavericks", "DALLAS MAVERICKS": "Mavericks", "MAVERICKS": "Mavericks",
        "DEN": "Nuggets", "DENVER NUGGETS": "Nuggets", "NUGGETS": "Nuggets",
        "DET": "Pistons", "DETROIT PISTONS": "Pistons", "PISTONS": "Pistons",
        "GSW": "Warriors", "GOLDEN STATE WARRIORS": "Warriors", "WARRIORS": "Warriors",
        "HOU": "Rockets", "HOUSTON ROCKETS": "Rockets", "ROCKETS": "Rockets",
        "IND": "Pacers", "INDIANA PACERS": "Pacers", "PACERS": "Pacers",
        "LAC": "Clippers", "LOS ANGELES CLIPPERS": "Clippers", "CLIPPERS": "Clippers",
        "LAL": "Lakers", "LOS ANGELES LAKERS": "Lakers", "LAKERS": "Lakers",
        "MEM": "Grizzlies", "MEMPHIS GRIZZLIES": "Grizzlies", "GRIZZLIES": "Grizzlies",
        "MIA": "Heat", "MIAMI HEAT": "Heat", "HEAT": "Heat",
        "MIL": "Bucks", "MILWAUKEE BUCKS": "Bucks", "BUCKS": "Bucks",
        "MIN": "Timberwolves", "MINNESOTA TIMBERWOLVES": "Timberwolves", "TIMBERWOLVES": "Timberwolves", "WOLVES": "Timberwolves",
        "NOP": "Pelicans", "NEW ORLEANS PELICANS": "Pelicans", "PELICANS": "Pelicans",
        "NYK": "Knicks", "NEW YORK KNICKS": "Knicks", "KNICKS": "Knicks",
        "OKC": "Thunder", "OKLAHOMA CITY THUNDER": "Thunder", "THUNDER": "Thunder",
        "ORL": "Magic", "ORLANDO MAGIC": "Magic", "MAGIC": "Magic",
        "PHI": "76ers", "PHILADELPHIA 76ERS": "76ers", "76ERS": "76ers", "SIXERS": "76ers",
        "PHX": "Suns", "PHOENIX SUNS": "Suns", "SUNS": "Suns",
        "POR": "Trail Blazers", "PORTLAND TRAIL BLAZERS": "Trail Blazers", "BLAZERS": "Trail Blazers", "TRAIL BLAZERS": "Trail Blazers",
        "SAC": "Kings", "SACRAMENTO KINGS": "Kings", "KINGS": "Kings",
        "SAS": "Spurs", "SAN ANTONIO SPURS": "Spurs", "SPURS": "Spurs",
        "TOR": "Raptors", "TORONTO RAPTORS": "Raptors", "RAPTORS": "Raptors",
        "UTA": "Jazz", "UTAH JAZZ": "Jazz", "JAZZ": "Jazz",
        "WAS": "Wizards", "WASHINGTON WIZARDS": "Wizards", "WIZARDS": "Wizards",

        # NHL
        "BOS BRUINS": "Bruins", "BRUINS": "Bruins",
        "RANGERS": "Rangers", "NY RANGERS": "Rangers", "NEW YORK RANGERS": "Rangers",
        "MAPLE LEAFS": "Maple Leafs", "TORONTO MAPLE LEAFS": "Maple Leafs",
        "LIGHTNING": "Lightning", "TAMPA BAY LIGHTNING": "Lightning",
        "PANTHERS": "Panthers", "FLORIDA PANTHERS": "Panthers",
        "HURRICANES": "Hurricanes", "CAROLINA HURRICANES": "Hurricanes",
        "OILERS": "Oilers", "EDMONTON OILERS": "Oilers",
        "AVALANCHE": "Avalanche", "COLORADO AVALANCHE": "Avalanche",
        "GOLDEN KNIGHTS": "Golden Knights", "VEGAS GOLDEN KNIGHTS": "Golden Knights",

        # MLB
        "YANKEES": "Yankees", "NEW YORK YANKEES": "Yankees",
        "METS": "Mets", "NEW YORK METS": "Mets",
        "DODGERS": "Dodgers", "LOS ANGELES DODGERS": "Dodgers",
        "PADRES": "Padres", "SAN DIEGO PADRES": "Padres",
        "BRAVES": "Braves", "ATLANTA BRAVES": "Braves",
        "PHILLIES": "Phillies", "PHILADELPHIA PHILLIES": "Phillies",
        "ASTROS": "Astros", "HOUSTON ASTROS": "Astros",
        "RANGERS MLB": "Rangers", "TEXAS RANGERS": "Rangers",
        "RED SOX": "Red Sox", "BOSTON RED SOX": "Red Sox",
        "CUBS": "Cubs", "CHICAGO CUBS": "Cubs",
    }

    return mapping.get(key, raw.title())

# =========================================================
# LIVE SLATE INPUT (CLEAN)
# =========================================================
def parse_today_games(games_text: str):
    games = []

    for line in str(games_text).splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue

        parts = re.split(r"\s+vs\s+|\s+v\s+|\s+@\s+", cleaned, flags=re.IGNORECASE)
        if len(parts) != 2:
            continue

        away = normalize_team_name(parts[0].strip())
        home = normalize_team_name(parts[1].strip())

        if away and home:
            games.append(f"{away} vs {home}")

    return games

# =========================================================
# SIDEBAR CONTROLS
# =========================================================
st.sidebar.markdown("### 🏟️ Sport")
selected_sidebar_sport = st.sidebar.selectbox(
    "Select Sport",
    options=["NBA", "NHL", "MLB"],
    index=["NBA", "NHL", "MLB"].index(get_selected_sport()) if get_selected_sport() in ["NBA", "NHL", "MLB"] else 0,
    key="selected_sport_sidebar",
)
set_selected_sport(selected_sidebar_sport)

st.sidebar.markdown("### 🗓️ Today's Slate")
today_games_text = st.sidebar.text_area(
    "Optional: Filter today's slate",
    key="today_games_text",
    height=180,
    placeholder="Examples:\nSAS vs CHA\nLAL vs BOS\nNYY vs BOS\nEDM vs COL\n\nLeave blank to use all live games",
)

st.sidebar.caption(
    "Supports abbreviations, full names, nicknames, and either VS or @."
)

today_games = parse_today_games(str(today_games_text))
selected_sport = get_selected_sport()

st.sidebar.markdown("### 📡 SportsDataIO Controls")
st.session_state["sportsdata_enabled"] = st.sidebar.toggle(
    "Enable SportsDataIO Context",
    value=st.session_state.get("sportsdata_enabled", True),
    key="sportsdata_enabled_toggle",
)

st.sidebar.caption(f"Current SportData mode: {get_current_sportsdata_slug().upper()}")

sportsdata_game_date = st.sidebar.text_input(
    "SportsData Game Date (YYYY-MM-DD)",
    value=today_str(),
    key="sportsdata_game_date_input",
)

if SPORTSDATA_API_KEY:
    st.sidebar.success("SportsDataIO key loaded")
else:
    st.sidebar.warning("Missing SportsDataIO API key in Streamlit secrets")

refresh_button_key = f"refresh_live_odds_btn_{get_selected_sport()}"
refresh_clicked = st.sidebar.button(
    "🔄 Refresh Live Odds",
    use_container_width=True,
    key=refresh_button_key,
)

# Show latest refresh note directly in sidebar
last_sidebar_note = str(st.session_state.get("api_status_note", "")).strip()
last_sidebar_error = str(st.session_state.get("last_refresh_error", "")).strip()

if last_sidebar_note:
    st.sidebar.caption(f"Status: {last_sidebar_note}")

if last_sidebar_error:
    st.sidebar.error(f"Last refresh error: {last_sidebar_error}")

# =========================================================
# ODDS CACHE HELPERS
# =========================================================
def get_odds_games_for_sport(sport_name):
    sport = str(sport_name).strip().upper()
    mapping = st.session_state.get("odds_api_games_by_sport", {})
    if not isinstance(mapping, dict):
        return []
    value = mapping.get(sport, [])
    return value if isinstance(value, list) else []

def set_odds_games_for_sport(games, sport_name):
    sport = str(sport_name).strip().upper()
    mapping = dict(st.session_state.get("odds_api_games_by_sport", {}))
    mapping[sport] = games if isinstance(games, list) else []
    st.session_state["odds_api_games_by_sport"] = mapping

def get_cached_games_for_sport(sport_name):
    sport = str(sport_name).strip().upper()
    mapping = st.session_state.get("last_successful_odds_games_by_sport", {})
    if not isinstance(mapping, dict):
        return []
    value = mapping.get(sport, [])
    return value if isinstance(value, list) else []

def set_cached_games_for_sport(games, sport_name):
    sport = str(sport_name).strip().upper()
    mapping = dict(st.session_state.get("last_successful_odds_games_by_sport", {}))
    mapping[sport] = games if isinstance(games, list) else []
    st.session_state["last_successful_odds_games_by_sport"] = mapping

# =========================================================
# LIVE ODDS FETCH + EFFECTIVE DATA HELPERS
# =========================================================
def fetch_odds_for_sport(sport_name: str):
    sport_name = str(sport_name).strip().upper()
    sport_cfg = get_sport_config(sport_name)
    api_key = get_odds_api_key()

    st.session_state["last_refresh_requested_sport"] = sport_name

    if not api_key:
        st.session_state["last_refresh_error"] = "No Odds API key found in secrets."
        st.session_state["last_odds_refresh_ok"] = False
        st.session_state["last_refresh_count"] = 0
        st.session_state["api_status_note"] = f"{sport_name}: Odds API key missing."
        set_api_status("no_key", "No Odds API key found in secrets.")
        return []

    if get_daily_api_calls_remaining() <= 0:
        reset_guess = (pd.Timestamp.now() + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        st.session_state["odds_api_reset_expected"] = reset_guess
        set_api_reset_expected_for_sport(reset_guess, sport_name)
        st.session_state["last_refresh_error"] = ""
        st.session_state["last_odds_refresh_ok"] = False
        st.session_state["api_status_note"] = f"{sport_name}: Daily Odds API call cap reached."
        set_api_status("waiting_reset", "Daily Odds API call cap reached.")
        fallback_games = get_cached_games_for_sport(sport_name)
        return fallback_games if isinstance(fallback_games, list) else []

    url = f"{ODDS_API_BASE}/{sport_cfg['sport_key']}/odds"
    params = {
        "apiKey": api_key,
        "regions": ODDS_REGIONS,
        "markets": ODDS_MARKETS,
        "oddsFormat": ODDS_ODDS_FORMAT,
        "dateFormat": "iso",
        "bookmakers": ODDS_BOOKMAKERS,
    }

    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()

        data = response.json()
        if not isinstance(data, list):
            data = []

        increment_daily_api_call_count()

        set_odds_games_for_sport(data, sport_name)
        set_cached_games_for_sport(data, sport_name)

        pull_time = time.time()
        st.session_state["last_odds_refresh_ok"] = True
        st.session_state["last_refresh_error"] = ""
        st.session_state["last_refresh_count"] = len(data)
        st.session_state["last_refresh_time"] = pd.Timestamp.now().strftime("%Y-%m-%d %I:%M:%S %p")
        st.session_state["last_api_pull_epoch"] = pull_time
        set_last_pull_epoch_for_sport(pull_time, sport_name)

        st.session_state["api_status_note"] = (
            f"{sport_name}: loaded {len(data)} game(s). "
            f"Calls used today: {get_daily_api_calls_used()} / {DAILY_API_CALL_LIMIT}"
        )

        if len(data) > 0:
            set_api_status(
                "live",
                f"{sport_name} live odds loaded. Calls used today: {get_daily_api_calls_used()} / {DAILY_API_CALL_LIMIT}",
            )
        else:
            set_api_status(
                "live",
                f"{sport_name} refresh completed but returned 0 games.",
            )

        return data

    except Exception as e:
        err = str(e)
        st.session_state["last_refresh_error"] = err
        st.session_state["last_odds_refresh_ok"] = False
        st.session_state["last_refresh_count"] = 0

        fallback = get_cached_games_for_sport(sport_name)
        if isinstance(fallback, list) and len(fallback) > 0:
            st.session_state["api_status_note"] = f"{sport_name}: live pull failed, using cached odds."
            set_api_status("cached", f"{sport_name} live pull failed. Using cached odds.")
            return fallback

        st.session_state["api_status_note"] = f"{sport_name}: live pull failed. {err}"
        set_api_status("error", f"{sport_name} live pull failed.")
        return []

def refresh_live_odds(selected_only=True):
    selected_sport = str(get_selected_sport()).strip().upper()

    if selected_only:
        requested_sports = [selected_sport]
    else:
        requested_sports = [str(s).strip().upper() for s in ACTIVE_REFRESH_SPORTS if str(s).strip().upper() in SUPPORTED_SPORTS]
        if not requested_sports:
            requested_sports = [selected_sport]

    if not api_cooldown_ready():
        st.session_state["last_odds_refresh_ok"] = False
        st.session_state["api_status_note"] = (
            f"Cooldown active. Wait about {API_COOLDOWN_SECONDS} seconds between pulls."
        )
        set_api_status("cooldown", f"Cooldown active. Wait about {API_COOLDOWN_SECONDS} seconds between pulls.")
        return False

    total_loaded = 0
    combined_note_parts = []

    for sport_name in requested_sports:
        games = fetch_odds_for_sport(sport_name)
        games_count = len(games) if isinstance(games, list) else 0
        total_loaded += games_count
        combined_note_parts.append(f"{sport_name}: {games_count}")

    st.session_state["last_refresh_count"] = total_loaded
    st.session_state["last_refresh_time"] = pd.Timestamp.now().strftime("%Y-%m-%d %I:%M:%S %p")
    st.session_state["api_status_note"] = " | ".join(combined_note_parts) if combined_note_parts else "No refresh results."

    selected_live = get_odds_games_for_sport(selected_sport)
    selected_cached = get_cached_games_for_sport(selected_sport)

    selected_live_count = len(selected_live) if isinstance(selected_live, list) else 0
    selected_cached_count = len(selected_cached) if isinstance(selected_cached, list) else 0

    if selected_live_count > 0:
        st.session_state["last_odds_refresh_ok"] = True
        set_api_status("live", f"{selected_sport} refresh complete. Loaded {selected_live_count} game(s).")
    elif selected_cached_count > 0:
        st.session_state["last_odds_refresh_ok"] = False
        set_api_status("cached", f"{selected_sport} using cached odds ({selected_cached_count} game(s)).")
    elif not get_odds_api_key():
        st.session_state["last_odds_refresh_ok"] = False
        set_api_status("no_key", "No Odds API key found in secrets.")
    else:
        st.session_state["last_odds_refresh_ok"] = False
        set_api_status("error", f"{selected_sport} refresh returned 0 games.")

    finalize_selected_sport_context()
    return True

def get_effective_odds_games_for_sport(sport_name: str):
    live_games = get_odds_games_for_sport(sport_name)
    cached_games = get_cached_games_for_sport(sport_name)

    if isinstance(live_games, list) and len(live_games) > 0:
        return live_games
    if isinstance(cached_games, list) and len(cached_games) > 0:
        return cached_games
    return []

def get_effective_odds_games():
    return get_effective_odds_games_for_sport(get_selected_sport())

def get_today_games_filter():
    raw = str(st.session_state.get("today_games_text", "")).strip()
    if not raw:
        return []

    cleaned = []
    for line in raw.splitlines():
        text = str(line).strip()
        if text:
            cleaned.append(text.lower())

    return cleaned

def game_matches_filter(home_team: str, away_team: str, filters: list):
    if not filters:
        return True

    combined_1 = f"{away_team} vs {home_team}".lower()
    combined_2 = f"{home_team} vs {away_team}".lower()
    combined_3 = f"{away_team} @ {home_team}".lower()
    combined_4 = f"{home_team} @ {away_team}".lower()

    for item in filters:
        check = item.strip().lower()
        if not check:
            continue
        if check in combined_1 or check in combined_2 or check in combined_3 or check in combined_4:
            return True

    return False

# =========================================================
# EXECUTE MANUAL REFRESH REQUEST
# =========================================================
if refresh_clicked:
    try:
        refresh_ok = refresh_live_odds(selected_only=True)

        if refresh_ok:
            selected_sport = get_selected_sport()
            live_count = len(get_odds_games_for_sport(selected_sport))
            cached_count = len(get_cached_games_for_sport(selected_sport))

            if live_count > 0:
                st.sidebar.success(f"{selected_sport} refresh loaded {live_count} game(s).")
            elif cached_count > 0:
                st.sidebar.warning(f"{selected_sport} live refresh failed. Using {cached_count} cached game(s).")
            else:
                last_err = str(st.session_state.get("last_refresh_error", "")).strip()
                if last_err:
                    st.sidebar.error(last_err)
                else:
                    st.sidebar.warning(f"{selected_sport} refresh completed but returned 0 games.")
    except Exception as e:
        st.session_state["last_refresh_error"] = str(e)
        set_api_status("error", f"Refresh failed: {e}")
        st.sidebar.error(f"Refresh failed: {e}")
# =========================================================
# CONSENSUS + SCORING HELPERS
# =========================================================
def calculate_consensus_pct(price_list):
    if not price_list:
        return 0.0

    favorites = 0
    for price in price_list:
        if safe_float(price, 0) < 0:
            favorites += 1

    return round((favorites / max(len(price_list), 1)) * 100.0, 1)

def estimate_true_probability(implied_prob, books, consensus_pct, market_name):
    implied_prob = safe_float(implied_prob, 0)
    books = safe_float(books, 0)
    consensus_pct = safe_float(consensus_pct, 0)

    market_bonus = 0.0
    if market_name in ["spread", "spreads"]:
        market_bonus = 0.010
    elif market_name in ["total", "totals"]:
        market_bonus = 0.008
    elif market_name in ["h2h", "moneyline"]:
        market_bonus = 0.006

    books_bonus = min(0.025, books * 0.0035)
    consensus_bonus = (consensus_pct / 100.0) * 0.020

    true_prob = implied_prob + books_bonus + consensus_bonus + market_bonus
    return clamp(true_prob, 0.02, 0.95)

def calculate_market_signal(books, edge):
    books = safe_float(books, 0)
    edge = safe_float(edge, 0)
    signal = (books * 4.5) + (edge * 2.0)
    return clamp(signal, 0.0, 100.0)

def calculate_matchup_score(market_name):
    m = str(market_name).strip().lower()
    if m in ["spread", "spreads"]:
        return 67.0
    if m in ["total", "totals"]:
        return 63.0
    if m in ["h2h", "moneyline"]:
        return 61.0
    return 55.0

def calculate_historical_score():
    return 58.0

def calculate_model_score(true_prob, edge, books):
    true_prob = safe_float(true_prob, 0)
    edge = safe_float(edge, 0)
    books = safe_float(books, 0)
    score = (true_prob * 100.0 * 0.55) + (edge * 4.0) + (books * 2.0)
    return clamp(score, 0.0, 100.0)

def calculate_true_confidence(true_prob, edge, books, market_signal, matchup_score, historical_score):
    true_prob_pct = safe_float(true_prob, 0) * 100.0
    edge_score = clamp(safe_float(edge, 0) * 8.0, 0.0, 100.0)
    books_score = clamp(safe_float(books, 0) * 12.0, 0.0, 100.0)

    weighted = (
        (true_prob_pct * TRUE_PROB_WEIGHT)
        + (edge_score * PRICE_EDGE_WEIGHT)
        + (safe_float(market_signal, 0) * MARKET_SIGNAL_WEIGHT)
        + (safe_float(matchup_score, 0) * MATCHUP_WEIGHT)
        + (safe_float(historical_score, 0) * HISTORICAL_WEIGHT)
    )

    if books < 2:
        weighted -= 8.0
    if edge < 2:
        weighted -= 6.0
    if true_prob_pct < 54:
        weighted -= 5.0

    return round(clamp(weighted, 0.0, 99.0), 1)

def calculate_units(true_confidence, status):
    tc = safe_float(true_confidence, 0)
    if str(status).strip() == "Active":
        base = SINGLE_UNIT_MIN + ((tc - MIN_ACTIVE_TRUE_CONF) / 25.0) * (SINGLE_UNIT_MAX - SINGLE_UNIT_MIN)
        return round(clamp(base, SINGLE_UNIT_MIN, SINGLE_UNIT_MAX), 2)

    base = WATCH_UNIT_MIN + ((tc - MIN_WATCH_TRUE_CONF) / 25.0) * (WATCH_UNIT_MAX - WATCH_UNIT_MIN)
    return round(clamp(base, WATCH_UNIT_MIN, WATCH_UNIT_MAX), 2)

# =========================================================
# SELF-LEARNING ENGINE HELPERS (V33.2 ON TOP OF V34)
# =========================================================
def american_odds_to_implied_prob(odds):
    try:
        odds = float(odds)
        if odds > 0:
            return 100.0 / (odds + 100.0)
        return abs(odds) / (abs(odds) + 100.0)
    except Exception:
        return 0.0


def normalize_category_label(category_text):
    raw = str(category_text or "").strip()
    if not raw:
        return "Uncategorized"

    parts = [p.strip() for p in raw.split("|") if str(p).strip()]
    if not parts:
        return "Uncategorized"

    priority = ["Top Plays", "AI Picks", "AI Parlays", "Watchlist", "Manual"]
    for label in priority:
        if label in parts:
            return label

    legacy_map = {
        "Top Play": "Top Plays",
        "AI Slip": "AI Picks",
        "AI Parlay": "AI Parlays",
    }
    for part in parts:
        if part in legacy_map:
            return legacy_map[part]

    return parts[0]


def classify_play_type(row):
    market = str(row.get("market", "")).strip().lower()
    selection = str(row.get("selection", row.get("pick", ""))).strip().lower()
    category = normalize_category_label(row.get("category", row.get("log_category", "")))

    if "parlay" in category.lower() or market == "parlay":
        return "parlay"

    if market in ["h2h", "moneyline", "ml"]:
        return "moneyline"

    if "spread" in market:
        return "spread"

    if "total" in market:
        if "over" in selection:
            return "total_over"
        if "under" in selection:
            return "total_under"
        return "total"

    if "prop" in market:
        if "points" in market:
            return "prop_points"
        if "rebounds" in market:
            return "prop_rebounds"
        if "assists" in market:
            return "prop_assists"
        if "pra" in market:
            return "prop_pra"
        return "prop"

    return "other"


def safe_clv_score(row):
    clv_result = str(row.get("clv_result", "")).strip().lower()
    clv_diff = safe_float(row.get("clv_diff", 0.0), 0.0)

    if clv_result == "beat":
        return clamp(clv_diff / 5.0, 0.0, 1.0)
    if clv_result == "lost":
        return clamp(-abs(clv_diff) / 5.0, -1.0, 0.0)
    return 0.0


def get_active_learning_state(sport=None):
    return get_learning_state_for_sport(sport or get_selected_sport())


def compute_true_probability(row, sport=None):
    implied_prob = american_odds_to_implied_prob(row.get("odds", 0))

    model_projection = safe_float(row.get("model_projection", 0.50), 0.50)
    price_edge = safe_float(row.get("model_price_ev", row.get("price_edge", 0.0)), 0.0)
    model_risk = safe_float(row.get("model_risk", 0.50), 0.50)
    model_market = safe_float(row.get("model_market", 0.50), 0.50)
    model_history = safe_float(row.get("model_history", 0.50), 0.50)
    multi_ai_score = safe_float(row.get("multi_ai_score", row.get("score", 50)), 50)
    clv_signal = safe_clv_score(row)

    learning_state = get_active_learning_state(sport)
    weights = learning_state.get(
        "weights",
        {
            "true_probability": 0.30,
            "price_edge": 0.25,
            "market_signal": 0.15,
            "matchup_quality": 0.15,
            "historical_performance": 0.15,
        },
    )

    projection_component = clamp(model_projection, 0.01, 0.99)
    market_component = clamp(model_market, 0.01, 0.99)
    history_component = clamp(model_history, 0.01, 0.99)

    risk_quality = 1.0 - clamp(model_risk, 0.0, 1.0)
    matchup_quality = clamp(((multi_ai_score / 100.0) * 0.75) + (risk_quality * 0.25), 0.01, 0.99)
    price_nudge = clamp(implied_prob + (price_edge * 0.25), 0.01, 0.99)

    weighted_prob = (
        projection_component * safe_float(weights.get("true_probability", 0.30), 0.30)
        + price_nudge * safe_float(weights.get("price_edge", 0.25), 0.25)
        + market_component * safe_float(weights.get("market_signal", 0.15), 0.15)
        + matchup_quality * safe_float(weights.get("matchup_quality", 0.15), 0.15)
        + history_component * safe_float(weights.get("historical_performance", 0.15), 0.15)
    )

    clv_nudge = clv_signal * 0.015
    true_probability = (weighted_prob * 0.55) + (implied_prob * 0.45)
    true_probability = true_probability + clv_nudge

    return clamp(true_probability, 0.01, 0.99)


def enrich_play_with_learning_fields(row, sport=None):
    row = dict(row)

    implied_probability = american_odds_to_implied_prob(row.get("odds", 0))
    true_probability = compute_true_probability(row, sport=sport)
    edge_decimal = true_probability - implied_probability

    row["implied_probability"] = round(implied_probability, 4)
    row["true_probability"] = round(true_probability, 4)
    row["edge_decimal"] = round(edge_decimal, 4)
    row["play_type"] = classify_play_type(row)
    row["primary_category"] = normalize_category_label(row.get("category", row.get("log_category", "")))

    return row


def should_allow_play(row, sport=None):
    learning_state = get_active_learning_state(sport)
    row = enrich_play_with_learning_fields(row, sport=sport)

    category = row.get("primary_category", "Uncategorized")
    play_type = row.get("play_type", "other")

    edge_value = safe_float(row.get("edge", row.get("price_edge", 0.0)), 0.0)
    if edge_value > 1.0:
        edge_for_threshold = edge_value / 100.0
    else:
        edge_for_threshold = edge_value

    category_threshold = safe_float(
        learning_state.get("category_thresholds", {}).get(category, 0.03),
        0.03,
    )

    bad_play_type_flags = learning_state.get("bad_play_type_flags", {})
    flag_info = bad_play_type_flags.get(play_type, {})

    if isinstance(flag_info, dict):
        if bool(flag_info.get("is_filtered", False)):
            return False, f"Filtered by learning engine: {play_type} underperforming"
    elif bool(flag_info):
        return False, f"Filtered by learning engine: {play_type} underperforming"

    if edge_for_threshold < category_threshold:
        return False, f"Edge below threshold ({round(edge_for_threshold, 4)} < {round(category_threshold, 4)})"

    return True, "Allowed"


def calculate_bet_profit(odds, stake, result):
    odds = safe_float(odds, 0.0)
    stake = safe_float(stake, 0.0)
    result = str(result or "").strip().lower()

    if result == "win":
        if odds > 0:
            return round(stake * (odds / 100.0), 2)
        if odds < 0:
            return round(stake * (100.0 / abs(odds)), 2)
        return round(stake, 2)

    if result == "loss":
        return round(-stake, 2)

    return 0.0


def update_learning_from_results(sport=None):
    selected_sport_name = str(sport or get_selected_sport()).strip().upper()
    bet_log = get_bet_log_for_sport(selected_sport_name)

    if not bet_log:
        return

    df = pd.DataFrame(bet_log)
    if df.empty:
        return

    required_cols = ["result", "odds"]
    for col in required_cols:
        if col not in df.columns:
            df[col] = ""

    df["result"] = df["result"].astype(str).str.strip().str.lower()
    graded = df[df["result"].isin(["win", "loss", "push"])].copy()

    if graded.empty:
        return

    enriched_rows = []
    for _, row in graded.iterrows():
        enriched_rows.append(
            enrich_play_with_learning_fields_compat(
                row.to_dict(),
                sport=selected_sport_name,
            )
        )
    graded = pd.DataFrame(enriched_rows)

    if graded.empty:
        return

    if "stake" not in graded.columns:
        graded["stake"] = graded.get("units", 1.0)

    graded["stake"] = pd.to_numeric(graded["stake"], errors="coerce").fillna(1.0)
    graded["odds"] = pd.to_numeric(graded["odds"], errors="coerce").fillna(0.0)

    graded["profit"] = graded.apply(
        lambda r: calculate_bet_profit(
            r.get("odds", 0),
            r.get("stake", 1.0),
            r.get("result", ""),
        ),
        axis=1,
    )

    if "clv_diff" not in graded.columns:
        graded["clv_diff"] = 0.0
    if "clv_result" not in graded.columns:
        graded["clv_result"] = ""

    graded["clv_diff"] = pd.to_numeric(graded["clv_diff"], errors="coerce").fillna(0.0)
    graded["clv_result"] = graded["clv_result"].astype(str).str.strip()
    graded["clv_score"] = graded.apply(safe_clv_score, axis=1)

    learning_state = get_active_learning_state(selected_sport_name)
    min_samples = safe_int(learning_state.get("category_min_samples", 8), 8)

    # -----------------------------------------------------
    # PLAY TYPE STATS
    # -----------------------------------------------------
    play_type_stats = {}

    for play_type, group in graded.groupby("play_type"):
        bets = len(group)
        wins = int((group["result"] == "win").sum())
        losses = int((group["result"] == "loss").sum())
        pushes = int((group["result"] == "push").sum())
        profit = round(pd.to_numeric(group["profit"], errors="coerce").fillna(0.0).sum(), 2)
        stake_sum = max(pd.to_numeric(group["stake"], errors="coerce").fillna(0.0).sum(), 1.0)
        roi = round(profit / stake_sum, 4)

        beat_clv = int((group["clv_result"].astype(str).str.lower() == "beat").sum())
        lost_clv = int((group["clv_result"].astype(str).str.lower() == "lost").sum())
        push_clv = int((group["clv_result"].astype(str).str.lower() == "push").sum())
        avg_clv = round(group["clv_diff"].mean(), 3) if len(group) > 0 else 0.0
        avg_clv_score = round(group["clv_score"].mean(), 4) if len(group) > 0 else 0.0

        play_type_stats[play_type] = {
            "bets": bets,
            "wins": wins,
            "losses": losses,
            "pushes": pushes,
            "profit": profit,
            "roi": roi,
            "beat_clv": beat_clv,
            "lost_clv": lost_clv,
            "push_clv": push_clv,
            "avg_clv": avg_clv,
            "avg_clv_score": avg_clv_score,
        }

    learning_state["play_type_stats"] = play_type_stats

    # -----------------------------------------------------
    # AUTO-FILTERING
    # -----------------------------------------------------
    bad_flags = {}
    for play_type, stats in play_type_stats.items():
        bets = safe_int(stats.get("bets", 0), 0)
        roi = safe_float(stats.get("roi", 0.0), 0.0)
        avg_clv_score = safe_float(stats.get("avg_clv_score", 0.0), 0.0)

        if bets >= min_samples and (roi <= -0.12 or (roi <= -0.06 and avg_clv_score < -0.15)):
            bad_flags[play_type] = {
                "is_filtered": True,
                "reason": f"Auto-filtered from results: ROI {round(roi * 100, 2)}%, CLV score {round(avg_clv_score, 4)}",
            }
        else:
            bad_flags[play_type] = {
                "is_filtered": False,
                "reason": "Not filtered",
            }

    learning_state["bad_play_type_flags"] = bad_flags

    # -----------------------------------------------------
    # CATEGORY THRESHOLDS
    # -----------------------------------------------------
    updated_thresholds = dict(learning_state.get("category_thresholds", {}))

    for category, group in graded.groupby("primary_category"):
        bets = len(group)
        total_stake = max(pd.to_numeric(group["stake"], errors="coerce").fillna(0.0).sum(), 1.0)
        roi = pd.to_numeric(group["profit"], errors="coerce").fillna(0.0).sum() / total_stake
        avg_clv_score = group["clv_score"].mean() if len(group) > 0 else 0.0

        current_threshold = safe_float(updated_thresholds.get(category, 0.03), 0.03)

        if bets >= min_samples:
            if roi < -0.08:
                current_threshold += 0.005
            elif roi > 0.08:
                current_threshold -= 0.003

            if avg_clv_score < -0.12:
                current_threshold += 0.003
            elif avg_clv_score > 0.12:
                current_threshold -= 0.002

        updated_thresholds[category] = round(clamp(current_threshold, 0.015, 0.08), 4)

    learning_state["category_thresholds"] = updated_thresholds

    # -----------------------------------------------------
    # WEIGHT ADJUSTMENT
    # -----------------------------------------------------
    wins_df = graded[graded["result"] == "win"].copy()
    losses_df = graded[graded["result"] == "loss"].copy()

    if not wins_df.empty and not losses_df.empty:
        win_edge = pd.to_numeric(wins_df.get("edge", 0.0), errors="coerce").fillna(0.0).mean()
        loss_edge = pd.to_numeric(losses_df.get("edge", 0.0), errors="coerce").fillna(0.0).mean()
        win_clv_score = pd.to_numeric(wins_df.get("clv_score", 0.0), errors="coerce").fillna(0.0).mean()
        loss_clv_score = pd.to_numeric(losses_df.get("clv_score", 0.0), errors="coerce").fillna(0.0).mean()

        weights = dict(
            learning_state.get(
                "weights",
                {
                    "true_probability": 0.30,
                    "price_edge": 0.25,
                    "market_signal": 0.15,
                    "matchup_quality": 0.15,
                    "historical_performance": 0.15,
                },
            )
        )

        if win_edge > loss_edge:
            weights["true_probability"] = clamp(
                safe_float(weights.get("true_probability", 0.30), 0.30) + 0.01,
                0.22,
                0.38,
            )
            weights["price_edge"] = clamp(
                safe_float(weights.get("price_edge", 0.25), 0.25) + 0.005,
                0.18,
                0.32,
            )
            weights["market_signal"] = clamp(
                safe_float(weights.get("market_signal", 0.15), 0.15) - 0.005,
                0.10,
                0.22,
            )

        if win_clv_score > loss_clv_score:
            weights["market_signal"] = clamp(
                safe_float(weights.get("market_signal", 0.15), 0.15) + 0.006,
                0.10,
                0.24,
            )
            weights["historical_performance"] = clamp(
                safe_float(weights.get("historical_performance", 0.15), 0.15) + 0.004,
                0.10,
                0.24,
            )
            weights["matchup_quality"] = clamp(
                safe_float(weights.get("matchup_quality", 0.15), 0.15) - 0.004,
                0.10,
                0.22,
            )

        total_weight = sum(weights.values())
        if total_weight > 0:
            for key in list(weights.keys()):
                weights[key] = round(weights[key] / total_weight, 4)

        learning_state["weights"] = weights

    learning_state["last_learning_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_learning_state_for_sport(learning_state, selected_sport_name)


def get_learning_summary_rows(sport=None):
    learning_state = get_active_learning_state(sport)
    stats = learning_state.get("play_type_stats", {})
    bad_flags = learning_state.get("bad_play_type_flags", {})

    rows = []
    for play_type, info in stats.items():
        flag_info = bad_flags.get(play_type, {})
        filtered_value = False

        if isinstance(flag_info, dict):
            filtered_value = bool(flag_info.get("is_filtered", False))
        else:
            filtered_value = bool(flag_info)

        rows.append(
            {
                "Play Type": play_type,
                "Bets": info.get("bets", 0),
                "Wins": info.get("wins", 0),
                "Losses": info.get("losses", 0),
                "Pushes": info.get("pushes", 0),
                "Profit": round(info.get("profit", 0.0), 2),
                "ROI %": round(info.get("roi", 0.0) * 100, 2),
                "Beat CLV": info.get("beat_clv", 0),
                "Lost CLV": info.get("lost_clv", 0),
                "Avg CLV": round(info.get("avg_clv", 0.0), 2),
                "Filtered": "Yes" if filtered_value else "No",
            }
        )

    return pd.DataFrame(rows)

# =========================================================
# LEARNING ENGINE COMPATIBILITY LAYER
# =========================================================
def get_row_category_for_learning(row):
    category = str(row.get("category", "")).strip()
    if category:
        return category

    log_category = str(row.get("log_category", "")).strip()
    if log_category:
        parts = [p.strip() for p in log_category.split("|") if str(p).strip()]
        if "Top Play" in parts or "Top Plays" in parts:
            return "Top Plays"
        if "AI Slip" in parts or "AI Picks" in parts:
            return "AI Picks"
        if "AI Parlay" in parts or "AI Parlays" in parts:
            return "AI Parlays"
        if "Watchlist" in parts:
            return "Watchlist"
        if parts:
            return parts[0]

    status = str(row.get("status", "")).strip()
    if status == "Active":
        return "Top Plays"
    if status in ["Watch", "Watchlist"]:
        return "Watchlist"

    return "Uncategorized"

def enrich_play_with_learning_fields_compat(row, sport=None):
    row = dict(row)

    if "category" not in row or not str(row.get("category", "")).strip():
        row["category"] = get_row_category_for_learning(row)

    if "model_projection" not in row:
        row["model_projection"] = clamp(safe_float(row.get("true_prob", 50.0), 50.0) / 100.0, 0.01, 0.99)

    if "model_price_ev" not in row:
        row["model_price_ev"] = safe_float(row.get("price_edge", row.get("edge", 0.0)), 0.0) / 100.0

    if "model_risk" not in row:
        tc = safe_float(row.get("true_confidence", 65.0), 65.0)
        row["model_risk"] = clamp(1.0 - (tc / 100.0), 0.01, 0.99)

    if "model_market" not in row:
        row["model_market"] = clamp(safe_float(row.get("implied_prob", 50.0), 50.0) / 100.0, 0.01, 0.99)

    if "model_history" not in row:
        row["model_history"] = clamp(safe_float(row.get("true_confidence", 65.0), 65.0) / 100.0, 0.01, 0.99)

    if "multi_ai_score" not in row:
        row["multi_ai_score"] = safe_float(row.get("score", row.get("model_score", 50.0)), 50.0)

    if "stake" not in row:
        row["stake"] = safe_float(row.get("units", 1.0), 1.0)

    enriched = enrich_play_with_learning_fields(row, sport=sport)

    enriched["implied_prob"] = round(safe_float(enriched.get("implied_probability", 0.0), 0.0) * 100.0, 2)
    enriched["true_prob"] = round(safe_float(enriched.get("true_probability", 0.0), 0.0) * 100.0, 2)
    enriched["edge"] = round(enriched["true_prob"] - enriched["implied_prob"], 2)

    return enriched

# =========================================================
# V33.1 LEARNING ACTIVATION ENGINE
# =========================================================
LEARNING_MIN_SAMPLE = 10
BAD_PLAYTYPE_THRESHOLD = -0.25
GOOD_PLAYTYPE_THRESHOLD = 0.10

def get_learning_activation_metrics(sport=None):
    selected_sport_name = str(sport or get_selected_sport()).strip().upper()
    df = pd.DataFrame(get_bet_log_for_sport(selected_sport_name))
    if df.empty:
        return {}

    if "result" not in df.columns:
        return {}

    graded = df[df["result"].isin(["Win", "Loss", "win", "loss"])].copy()
    if graded.empty:
        return {}

    summary = {}

    if "play_type" in graded.columns:
        for play_type, group in graded.groupby("play_type"):
            bets = len(group)
            profit = pd.to_numeric(group.get("profit", 0), errors="coerce").fillna(0.0).sum()

            if "stake" in group.columns:
                stake = pd.to_numeric(group.get("stake", 0), errors="coerce").fillna(0.0).sum()
            elif "units" in group.columns:
                stake = pd.to_numeric(group.get("units", 0), errors="coerce").fillna(0.0).sum()
            else:
                stake = float(bets)

            roi = (profit / stake) if stake > 0 else 0.0

            summary[str(play_type).strip().lower()] = {
                "bets": int(bets),
                "roi": float(roi),
            }

    return summary

def get_dynamic_edge_threshold(category, sport=None):
    learning_state = get_active_learning_state(sport)
    thresholds = learning_state.get("category_thresholds", {})

    base_threshold = float(thresholds.get(category, 0.02))
    activation = get_learning_activation_metrics(sport)

    for _, stats in activation.items():
        if int(stats.get("bets", 0)) < LEARNING_MIN_SAMPLE:
            continue

        roi = float(stats.get("roi", 0.0))
        if roi < BAD_PLAYTYPE_THRESHOLD:
            base_threshold += 0.02
        elif roi > GOOD_PLAYTYPE_THRESHOLD:
            base_threshold -= 0.01

    return max(0.01, min(base_threshold, 0.10))

def should_block_play_type(play_type, sport=None):
    activation = get_learning_activation_metrics(sport)
    stats = activation.get(str(play_type).strip().lower())

    if not stats:
        return False
    if int(stats.get("bets", 0)) < LEARNING_MIN_SAMPLE:
        return False

    return float(stats.get("roi", 0.0)) < BAD_PLAYTYPE_THRESHOLD

def apply_v33_learning_filters(play, sport=None):
    play_type = str(play.get("play_type", "")).lower()
    category = str(play.get("category", "Top Plays")).strip() or "Top Plays"

    if should_block_play_type(play_type, sport=sport):
        return False, "Play type underperforming (auto-blocked)"

    edge = safe_float(play.get("edge", 0), 0) / 100.0
    min_edge = get_dynamic_edge_threshold(category, sport=sport)

    if edge < min_edge:
        return False, f"Edge below dynamic threshold ({round(min_edge * 100, 2)}%)"

    return True, "Passed V33.1 filters"

def apply_learning_engine_to_df(df, category_name, sport=None):
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df

    selected_sport_name = str(sport or get_selected_sport()).strip().upper()
    rows = []

    for _, row in df.iterrows():
        item = row.to_dict()
        item["category"] = category_name
        item["sport"] = selected_sport_name

        item = enrich_play_with_learning_fields_compat(item, sport=selected_sport_name)

        allowed, reason = should_allow_play(item, sport=selected_sport_name)

        v33_allowed, v33_reason = apply_v33_learning_filters(item, sport=selected_sport_name)
        if not v33_allowed:
            allowed = False
            reason = v33_reason

        item["learning_status"] = "Allowed" if allowed else "Filtered"
        item["learning_reason"] = reason

        rows.append(item)

    out = pd.DataFrame(rows)
    if out.empty:
        return out

    out = out[out["learning_status"] == "Allowed"].copy()

    if out.empty:
        return out.reset_index(drop=True)

    if "rank_score" in out.columns:
        out = out.sort_values(["rank_score", "true_confidence"], ascending=False)
    elif "edge" in out.columns:
        out = out.sort_values(["edge", "true_prob"], ascending=False)

    return out.reset_index(drop=True)

# =========================================================
# PLAYER PROP HELPERS
# =========================================================
def prop_line_for_type(prop_type: str, sport_name=None):
    sport = str(sport_name or get_selected_sport()).strip().upper()

    default_lines = {
        "NBA": {
            "points": [17.5, 19.5, 21.5, 23.5, 25.5, 27.5],
            "rebounds": [5.5, 6.5, 7.5, 8.5, 9.5, 10.5],
            "assists": [4.5, 5.5, 6.5, 7.5, 8.5],
            "pra": [28.5, 31.5, 34.5, 37.5, 40.5],
        },
        "NHL": {
            "shots_on_goal": [2.5, 3.5, 4.5],
            "points": [0.5, 1.5, 2.5],
            "assists": [0.5, 1.5],
        },
        "MLB": {
            "hits": [0.5, 1.5, 2.5],
            "total_bases": [1.5, 2.5, 3.5],
            "runs": [0.5, 1.5],
            "rbis": [0.5, 1.5],
            "strikeouts": [4.5, 5.5, 6.5, 7.5],
        },
    }

    choices = default_lines.get(sport, {}).get(prop_type, [0.5, 1.5, 2.5])
    return random.choice(choices)

def build_prop_selection(player_name: str, prop_type: str, sport_name=None):
    line = prop_line_for_type(prop_type, sport_name=sport_name)

    label_map = {
        "points": "Points",
        "rebounds": "Rebounds",
        "assists": "Assists",
        "pra": "PRA",
        "shots_on_goal": "Shots on Goal",
        "hits": "Hits",
        "total_bases": "Total Bases",
        "runs": "Runs",
        "rbis": "RBIs",
        "strikeouts": "Strikeouts",
    }

    direction = random.choice(["Over", "Under"])
    return f"{player_name} {direction} {line} {label_map.get(prop_type, prop_type.title())}"

def is_prop_market(market: str):
    return str(market).lower().startswith("prop_")

def prop_market_label(market: str):
    m = str(market).lower()
    mapping = {
        "prop_points": "Player Props • Points",
        "prop_rebounds": "Player Props • Rebounds",
        "prop_assists": "Player Props • Assists",
        "prop_pra": "Player Props • PRA",
        "prop_shots_on_goal": "Player Props • Shots on Goal",
        "prop_hits": "Player Props • Hits",
        "prop_total_bases": "Player Props • Total Bases",
        "prop_runs": "Player Props • Runs",
        "prop_rbis": "Player Props • RBIs",
        "prop_strikeouts": "Player Props • Strikeouts",
    }
    return mapping.get(m, str(market).replace("_", " ").title())

def get_mock_players_for_game(game_label, sport_name=None):
    sport = str(sport_name or get_selected_sport()).strip().upper()

    if sport == "NBA":
        return [
            "Jalen Brunson", "Jayson Tatum", "LeBron James", "Nikola Jokic",
            "Luka Doncic", "Anthony Davis", "Paolo Banchero", "Donovan Mitchell",
        ]
    if sport == "NHL":
        return [
            "Connor McDavid", "Nathan MacKinnon", "Auston Matthews", "David Pastrnak",
            "Artemi Panarin", "Leon Draisaitl",
        ]
    if sport == "MLB":
        return [
            "Aaron Judge", "Juan Soto", "Mookie Betts", "Freddie Freeman",
            "Ronald Acuna Jr.", "Bryce Harper", "Gerrit Cole", "Zack Wheeler",
        ]
    return []

def generate_mock_prop_rows_for_game(game_label, selected_sport, home_team, away_team):
    if not ENABLE_PLAYER_PROPS:
        return []

    prop_types = PROP_TYPES_BY_SPORT.get(selected_sport, [])
    if not prop_types:
        return []

    players = get_mock_players_for_game(game_label, selected_sport)
    if not players:
        return []

    rows = []
    used_keys = set()

    candidate_players = players[: min(len(players), MAX_PROP_PLAYS_PER_GAME)]

    for player_name in candidate_players:
        for prop_type in prop_types[:2]:
            market_name = f"prop_{prop_type}"
            selection = build_prop_selection(player_name, prop_type, sport_name=selected_sport)
            odds = random.choice([-125, -120, -115, -110, -105, 100, 105, 110, 115, 120])

            if not in_allowed_odds_range(odds, PROP_ODDS_RANGE[0], PROP_ODDS_RANGE[1]):
                continue

            implied_prob = american_to_implied_prob(odds)
            books = random.choice([2, 3, 4, 5])
            consensus_pct = random.choice([52.0, 56.0, 60.0, 64.0, 68.0])
            true_prob = estimate_true_probability(implied_prob, books, consensus_pct, market_name)
            edge = round((true_prob - implied_prob) * 100.0, 2)
            market_signal = calculate_market_signal(books, edge)
            matchup_score = calculate_matchup_score(market_name)
            historical_score = calculate_historical_score()
            true_confidence = calculate_true_confidence(
                true_prob,
                edge,
                books,
                market_signal,
                matchup_score,
                historical_score,
            )

            if books >= MIN_ACTIVE_BOOKS and edge >= MIN_ACTIVE_EDGE and true_confidence >= MIN_ACTIVE_TRUE_CONF:
                status = "Active"
                log_category = "Top Plays"
            elif books >= MIN_WATCH_BOOKS and edge >= MIN_WATCH_EDGE and true_confidence >= MIN_WATCH_TRUE_CONF:
                status = "Watch"
                log_category = "Watchlist"
            else:
                continue

            sharp_score = round(clamp((books * 10.0) + (edge * 5.0), 0.0, 100.0), 1)
            units = calculate_units(true_confidence, status)
            model_score = round(calculate_model_score(true_prob, edge, books), 1)

            team_name = home_team if len(rows) % 2 == 0 else away_team
            opponent = away_team if team_name == home_team else home_team
            play_id = build_play_id(selected_sport, game_label, market_name, selection, prop_type)

            if play_id in used_keys:
                continue
            used_keys.add(play_id)

            rows.append(
                {
                    "sport": selected_sport,
                    "game": game_label,
                    "market": market_name,
                    "selection": selection,
                    "player": player_name,
                    "team": team_name,
                    "opponent": opponent,
                    "line": extract_line_from_selection(selection),
                    "odds": int(odds),
                    "best_price": int(odds),
                    "best_book": random.choice(["DraftKings", "FanDuel", "BetMGM"]),
                    "implied_prob": round(implied_prob * 100.0, 2),
                    "true_prob": round(true_prob * 100.0, 2),
                    "edge": edge,
                    "price_edge": edge,
                    "books": books,
                    "books_seen": books,
                    "consensus_pct": consensus_pct,
                    "consensus": f"{consensus_pct:.1f}%",
                    "sharp_score": sharp_score,
                    "market_signal": round(market_signal, 1),
                    "matchup_score": round(matchup_score, 1),
                    "historical_score": round(historical_score, 1),
                    "true_confidence": true_confidence,
                    "status": status,
                    "units": units,
                    "play_id": play_id,
                    "log_category": log_category,
                    "sportsdata_note": "",
                    "injury_flag": "",
                    "lineup_flag": "",
                    "model_score": model_score,
                    "context_score": 0.0,
                }
            )

            if len(rows) >= MAX_PROP_PLAYS_PER_GAME:
                break

        if len(rows) >= MAX_PROP_PLAYS_PER_GAME:
            break

    return rows

# =========================================================
# DATA BUILD (CLEAN SAFE VERSION)
# =========================================================
def generate_ai_plays():
    selected_sport = get_selected_sport()
    odds_games = get_effective_odds_games_for_sport(selected_sport)

    if not odds_games:
        return pd.DataFrame()

    rows = []

    for game in odds_games:
        home_team = str(game.get("home_team", "")).strip()
        away_team = str(game.get("away_team", "")).strip()

        if not home_team or not away_team:
            continue

        game_label = f"{away_team} @ {home_team}"

        for book in game.get("bookmakers", []):
            book_name = str(book.get("title", "")).strip()

            for market in book.get("markets", []):
                market_key = str(market.get("key", "")).strip().lower()

                if market_key not in ["h2h", "spreads", "totals"]:
                    continue

                normalized_market = normalize_market_name_by_sport(market_key, selected_sport)

                for outcome in market.get("outcomes", []):
                    price = outcome.get("price", None)
                    if price is None:
                        continue

                    odds_int = american_to_int(price)
                    if odds_int is None:
                        continue

                    implied_prob = american_to_implied_prob(odds_int)
                    true_prob = clamp(implied_prob + 0.03, 0.02, 0.95)
                    edge = round((true_prob - implied_prob) * 100.0, 2)
                    true_conf = round(true_prob * 100.0, 2)

                    if edge >= 2.0:
                        status = "Active"
                        log_category = "Top Plays"
                    else:
                        status = "Watchlist"
                        log_category = "Watchlist"

                    selection_name = str(outcome.get("name", "")).strip()
                    line_value = outcome.get("point", None)

                    rows.append(
                        {
                            "sport": selected_sport,
                            "game": game_label,
                            "market": normalized_market,
                            "selection": selection_name,
                            "player": "",
                            "team": selection_name,
                            "opponent": "",
                            "line": line_value,
                            "odds": odds_int,
                            "best_price": odds_int,
                            "best_book": book_name,
                            "implied_prob": round(implied_prob * 100.0, 2),
                            "true_prob": round(true_prob * 100.0, 2),
                            "edge": edge,
                            "price_edge": edge,
                            "books": 1,
                            "books_seen": 1,
                            "consensus_pct": 50.0,
                            "consensus": "50%",
                            "sharp_score": 50.0,
                            "market_signal": 50.0,
                            "matchup_score": 50.0,
                            "historical_score": 50.0,
                            "true_confidence": true_conf,
                            "status": status,
                            "units": calculate_units(true_conf, status),
                            "play_id": build_play_id(
                                selected_sport,
                                game_label,
                                normalized_market,
                                selection_name,
                                line_value,
                            ),
                            "log_category": log_category,
                            "sportsdata_note": "",
                            "injury_flag": "",
                            "lineup_flag": "",
                            "model_score": 50.0,
                            "context_score": 0.0,
                        }
                    )

    plays_df = pd.DataFrame(rows)

    if plays_df.empty:
        return pd.DataFrame()

    plays_df = normalize_dataframe_for_selected_sport(plays_df, selected_sport)
    plays_df = recalculate_play_metrics(plays_df)

    if "status" not in plays_df.columns:
        plays_df["status"] = ""

    if "log_category" not in plays_df.columns:
        plays_df["log_category"] = ""

    plays_df["status"] = plays_df["status"].fillna("").astype(str).str.strip()
    plays_df["log_category"] = plays_df["log_category"].fillna("").astype(str).str.strip()

    plays_df = plays_df.sort_values(
        by=["true_confidence", "edge"],
        ascending=[False, False],
    ).reset_index(drop=True)

    if "play_id" in plays_df.columns:
        plays_df["play_id"] = plays_df["play_id"].fillna("").astype(str).str.strip()
        plays_df = plays_df[plays_df["play_id"] != ""].copy()
        plays_df = plays_df.drop_duplicates(subset=["play_id"], keep="first").reset_index(drop=True)

    return plays_df


# =========================================================
# EXECUTE DATA BUILD + SNAPSHOT
# =========================================================
plays_df = generate_ai_plays()
selected_sport = get_selected_sport()

if plays_df is None or not isinstance(plays_df, pd.DataFrame):
    plays_df = pd.DataFrame()

if plays_df.empty:
    st.session_state["plays_df"] = pd.DataFrame()
    st.session_state["snapshot_plays_df"] = pd.DataFrame()
    st.session_state["snapshot_all_plays_df"] = pd.DataFrame()
    st.session_state["snapshot_active_df"] = pd.DataFrame()
    st.session_state["snapshot_top_plays_df"] = pd.DataFrame()
    st.session_state["snapshot_watchlist_df"] = pd.DataFrame()
    st.session_state["snapshot_ai_slip_df"] = pd.DataFrame()
    st.session_state["snapshot_parlay_df"] = pd.DataFrame()
    st.session_state["snapshot_best_row"] = {}
else:
    plays_df = normalize_dataframe_for_selected_sport(plays_df, selected_sport)
    plays_df = recalculate_play_metrics(plays_df)

    if "status" not in plays_df.columns:
        plays_df["status"] = ""

    if "log_category" not in plays_df.columns:
        plays_df["log_category"] = ""

    plays_df["status"] = plays_df["status"].fillna("").astype(str).str.strip()
    plays_df["log_category"] = plays_df["log_category"].fillna("").astype(str).str.strip()

    plays_df.loc[plays_df["status"].eq("Watch"), "status"] = "Watchlist"

    active_df = plays_df[plays_df["status"] == "Active"].copy()
    watchlist_df = plays_df[plays_df["status"].isin(["Watchlist", "Watch"])].copy()

    if active_df.empty:
        active_df = plays_df.sort_values(
            by=["true_confidence", "edge", "books_seen"],
            ascending=[False, False, False],
        ).head(TOP_PLAYS_LIMIT).copy()

        if not active_df.empty:
            active_df["status"] = "Active"
            active_df["log_category"] = "Top Plays"

    top_plays_df = active_df.sort_values(
        by=["true_confidence", "edge", "books_seen"],
        ascending=[False, False, False],
    ).head(TOP_PLAYS_LIMIT).copy()

    if watchlist_df.empty:
        remaining_df = plays_df.copy()

        if "play_id" in remaining_df.columns and "play_id" in top_plays_df.columns:
            remaining_df = remaining_df[
                ~remaining_df["play_id"].isin(top_plays_df["play_id"])
            ].copy()

        if remaining_df.empty:
            remaining_df = plays_df.copy()

        watchlist_df = remaining_df.sort_values(
            by=["true_confidence", "edge", "books_seen"],
            ascending=[False, False, False],
        ).head(WATCHLIST_LIMIT).copy()

        if not watchlist_df.empty:
            watchlist_df["status"] = "Watchlist"
            watchlist_df["log_category"] = "Watchlist"

    ai_slip_df = top_plays_df.head(5).copy()

    st.session_state["plays_df"] = plays_df.copy()
    st.session_state["snapshot_plays_df"] = plays_df.copy()
    st.session_state["snapshot_all_plays_df"] = plays_df.copy()
    st.session_state["snapshot_active_df"] = active_df.copy()
    st.session_state["snapshot_top_plays_df"] = top_plays_df.copy()
    st.session_state["snapshot_watchlist_df"] = watchlist_df.copy()
    st.session_state["snapshot_ai_slip_df"] = ai_slip_df.copy()
    st.session_state["snapshot_parlay_df"] = pd.DataFrame()
    st.session_state["snapshot_best_row"] = ai_slip_df.iloc[0].to_dict() if not ai_slip_df.empty else {}

    timestamp_now = pd.Timestamp.now().strftime("%Y-%m-%d %I:%M:%S %p")
    st.session_state["snapshot_generated_at"] = timestamp_now
    st.session_state["snapshot_last_updated"] = timestamp_now
    st.session_state["snapshot_refresh_id"] = safe_int(
        st.session_state.get("snapshot_refresh_id", 0), 0
    ) + 1

    try:
        persist_generated_play_snapshots(plays_df.copy())
    except Exception:
        pass

    try:
        save_tab_snapshots_to_disk()
    except Exception:
        pass

# =========================================================
# FORCE SESSION STATE PERSISTENCE (CRITICAL FIX)
# =========================================================
def build_top_plays_df(plays_df: pd.DataFrame):
    if plays_df is None or plays_df.empty:
        return pd.DataFrame()

    top_df = plays_df[
        (plays_df["status"].astype(str) == "Active")
        & (pd.to_numeric(plays_df["books"], errors="coerce").fillna(0) >= MIN_ACTIVE_BOOKS)
        & (pd.to_numeric(plays_df["edge"], errors="coerce").fillna(0) >= MIN_ACTIVE_EDGE)
        & (pd.to_numeric(plays_df["true_confidence"], errors="coerce").fillna(0) >= MIN_ACTIVE_TRUE_CONF)
    ].copy()

    if top_df.empty:
        return pd.DataFrame()

    sort_cols = [c for c in ["rank_score", "true_confidence", "edge", "books"] if c in top_df.columns]
    if sort_cols:
        top_df = top_df.sort_values(sort_cols, ascending=[False] * len(sort_cols))

    top_df["log_category"] = "Top Plays"
    top_df["category"] = "Top Plays"
    top_df["primary_category"] = "Top Plays"

    return top_df.head(TOP_PLAYS_LIMIT).reset_index(drop=True)

def build_watchlist_df(plays_df: pd.DataFrame, top_df: pd.DataFrame):
    if plays_df is None or plays_df.empty:
        return pd.DataFrame()

    top_ids = set()
    if top_df is not None and not top_df.empty and "play_id" in top_df.columns:
        top_ids = set(top_df["play_id"].astype(str).tolist())

    watch_df = plays_df[
        (pd.to_numeric(plays_df["books"], errors="coerce").fillna(0) >= MIN_WATCH_BOOKS)
        & (pd.to_numeric(plays_df["edge"], errors="coerce").fillna(0) >= MIN_WATCH_EDGE)
        & (pd.to_numeric(plays_df["true_confidence"], errors="coerce").fillna(0) >= MIN_WATCH_TRUE_CONF)
    ].copy()

    if watch_df.empty:
        return pd.DataFrame()

    if "play_id" in watch_df.columns:
        watch_df = watch_df[~watch_df["play_id"].astype(str).isin(top_ids)].copy()

    sort_cols = [c for c in ["rank_score", "true_confidence", "edge", "books"] if c in watch_df.columns]
    if sort_cols:
        watch_df = watch_df.sort_values(sort_cols, ascending=[False] * len(sort_cols))

    watch_df["status"] = "Watch"
    watch_df["log_category"] = "Watchlist"
    watch_df["category"] = "Watchlist"
    watch_df["primary_category"] = "Watchlist"

    return watch_df.head(WATCHLIST_LIMIT).reset_index(drop=True)

def calculate_parlay_odds(american_odds_list):
    decimal_total = 1.0

    for odds in american_odds_list:
        odds = safe_float(odds, 0)
        if odds == 0:
            return 0

        if odds > 0:
            decimal_price = 1.0 + (odds / 100.0)
        else:
            decimal_price = 1.0 + (100.0 / abs(odds))

        decimal_total *= decimal_price

    if decimal_total <= 1.0:
        return 0

    if decimal_total >= 2.0:
        return int(round((decimal_total - 1.0) * 100.0))

    return int(round(-100.0 / (decimal_total - 1.0)))

def build_ai_slip_df(top_df: pd.DataFrame, watch_df: pd.DataFrame):
    source_frames = []

    if isinstance(top_df, pd.DataFrame) and not top_df.empty:
        source_frames.append(top_df.copy())

    if isinstance(watch_df, pd.DataFrame) and not watch_df.empty:
        source_frames.append(watch_df.head(6).copy())

    if not source_frames:
        return pd.DataFrame()

    candidate_df = pd.concat(source_frames, ignore_index=True)
    if candidate_df.empty:
        return pd.DataFrame()

    sort_cols = [c for c in ["rank_score", "true_confidence", "edge", "books"] if c in candidate_df.columns]
    if sort_cols:
        candidate_df = candidate_df.sort_values(sort_cols, ascending=[False] * len(sort_cols)).reset_index(drop=True)

    rows = []

    best_row = candidate_df.iloc[0].to_dict()
    best_row["slip_type"] = "Best Single"
    best_row["parlay_legs"] = 1
    best_row["parlay_odds"] = best_row.get("odds", 0)
    best_row["recommended_units"] = best_row.get("units", 0.5)
    best_row["log_category"] = "AI Picks"
    best_row["category"] = "AI Picks"
    best_row["primary_category"] = "AI Picks"
    rows.append(best_row)

    parlay_candidates = candidate_df.head(6).copy()

    for leg_count in [2, 3]:
        if len(parlay_candidates) < leg_count:
            continue

        best_combo = None
        best_score = -9999

        for combo_idx in combinations(range(len(parlay_candidates)), leg_count):
            legs = parlay_candidates.iloc[list(combo_idx)].copy()

            if "game" in legs.columns and legs["game"].nunique() < leg_count:
                continue

            avg_conf = pd.to_numeric(legs["true_confidence"], errors="coerce").fillna(0).mean()
            avg_edge = pd.to_numeric(legs["edge"], errors="coerce").fillna(0).mean()
            avg_books = pd.to_numeric(legs["books"], errors="coerce").fillna(0).mean()
            parlay_odds = calculate_parlay_odds(legs["odds"].tolist())

            if parlay_odds < MIN_PARLAY_ODDS:
                continue

            combo_score = (avg_conf * 0.60) + (avg_edge * 4.0) + (avg_books * 2.5)

            if combo_score > best_score:
                best_score = combo_score
                best_combo = {
                    "sport": get_selected_sport(),
                    "game": " | ".join(legs["game"].astype(str).tolist()),
                    "market": "Parlay",
                    "selection": " + ".join(legs["selection"].astype(str).tolist()),
                    "player": "",
                    "team": "",
                    "opponent": "",
                    "line": 0,
                    "odds": parlay_odds,
                    "best_price": parlay_odds,
                    "best_book": "",
                    "implied_prob": round(american_to_implied_prob(parlay_odds) * 100.0, 2),
                    "true_prob": round(pd.to_numeric(legs["true_prob"], errors="coerce").fillna(0).mean(), 2),
                    "edge": round(avg_edge, 2),
                    "price_edge": round(avg_edge, 2),
                    "books": round(avg_books, 1),
                    "books_seen": round(avg_books, 1),
                    "consensus_pct": round(pd.to_numeric(legs.get("consensus_pct", 0), errors="coerce").fillna(0).mean(), 1),
                    "consensus": "AI Parlay",
                    "sharp_score": round(pd.to_numeric(legs.get("sharp_score", 0), errors="coerce").fillna(0).mean(), 1),
                    "market_signal": round(pd.to_numeric(legs.get("market_signal", 0), errors="coerce").fillna(0).mean(), 1),
                    "matchup_score": round(pd.to_numeric(legs.get("matchup_score", 0), errors="coerce").fillna(0).mean(), 1),
                    "historical_score": round(pd.to_numeric(legs.get("historical_score", 0), errors="coerce").fillna(0).mean(), 1),
                    "true_confidence": round(avg_conf, 1),
                    "status": "Active",
                    "units": PARLAY_UNIT_SHARP if leg_count == 2 else PARLAY_UNIT_FALLBACK_3,
                    "play_id": build_play_id(
                        {
                            "sport": get_selected_sport(),
                            "game": " | ".join(legs["game"].astype(str).tolist()),
                            "market": "Parlay",
                            "selection": " + ".join(legs["selection"].astype(str).tolist()),
                            "odds": parlay_odds,
                        }
                    ),
                    "log_category": "AI Parlays",
                    "category": "AI Parlays",
                    "primary_category": "AI Parlays",
                    "sportsdata_note": "",
                    "injury_flag": "",
                    "lineup_flag": "",
                    "model_score": round(pd.to_numeric(legs.get("model_score", 0), errors="coerce").fillna(0).mean(), 1),
                    "slip_type": f"{leg_count}-Leg Parlay",
                    "parlay_legs": leg_count,
                    "parlay_odds": parlay_odds,
                    "recommended_units": PARLAY_UNIT_FALLBACK_2 if leg_count == 2 else PARLAY_UNIT_FALLBACK_3,
                }

        if best_combo is not None:
            rows.append(best_combo)

    if not rows:
        return pd.DataFrame()

    out = pd.DataFrame(rows).reset_index(drop=True)
    out = normalize_dataframe_for_selected_sport(out, get_selected_sport())
    return out

def save_generated_play_snapshots(plays_df: pd.DataFrame):
    selected_sport = get_selected_sport()

    plays_df = normalize_dataframe_for_selected_sport(plays_df, selected_sport)
    plays_df = recalculate_play_metrics(plays_df)

    top_df = build_top_plays_df(plays_df)
    watch_df = build_watchlist_df(plays_df, top_df)
    ai_slip_df = build_ai_slip_df(top_df, watch_df)

    st.session_state["plays_df"] = plays_df.copy()
    st.session_state["snapshot_plays_df"] = plays_df.copy()
    st.session_state["snapshot_all_plays_df"] = plays_df.copy()

    st.session_state["snapshot_active_df"] = top_df.copy()
    st.session_state["snapshot_top_plays_df"] = top_df.copy()
    st.session_state["snapshot_watchlist_df"] = watch_df.copy()
    st.session_state["snapshot_ai_slip_df"] = ai_slip_df.copy()

    if not ai_slip_df.empty:
        st.session_state["ai_slip_df"] = ai_slip_df.copy()

    if not top_df.empty:
        first_row = top_df.iloc[0]
        st.session_state["snapshot_best_row"] = first_row.to_dict()

    st.session_state["snapshot_generated_at"] = pd.Timestamp.now().strftime("%Y-%m-%d %I:%M:%S %p")
    st.session_state["snapshot_last_updated"] = st.session_state["snapshot_generated_at"]
    st.session_state["snapshot_refresh_id"] = int(st.session_state.get("snapshot_refresh_id", 0)) + 1

    try:
        persist_generated_play_snapshots(plays_df)
    except Exception:
        pass

    try:
        save_tab_snapshots_to_disk()
    except Exception:
        pass

    return top_df, watch_df, ai_slip_df

def get_snapshot_df(key_name: str):
    value = st.session_state.get(key_name, pd.DataFrame())
    if isinstance(value, pd.DataFrame):
        return value.copy()
    return pd.DataFrame()

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
    avg_books = sum(float(leg.get("books_seen", leg.get("books", 0))) for leg in combo) / len(combo)

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
    if active_df is None or active_df.empty or len(active_df) < 2:
        return []

    rows = active_df.to_dict("records")
    candidates = []

    for leg_count in range(MIN_PARLAY_LEGS, min(MAX_PARLAY_LEGS, len(rows)) + 1):
        for combo in combinations(rows, leg_count):
            if any(float(safe_float(leg.get("edge", 0), 0)) < 4.0 for leg in combo):
                continue
            if any(float(safe_float(leg.get("true_confidence", 0), 0)) < 70.0 for leg in combo):
                continue
            if any(int(safe_int(leg.get("books_seen", leg.get("books", 0)), 0)) < 3 for leg in combo):
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
# AUTO-LOG ACTIVE PLAYS (CATEGORY-AWARE + CLV READY)
# =========================================================
def normalize_result_value(result_value):
    value = str(result_value).strip().title()
    if value in ["Pending", "Win", "Loss", "Push"]:
        return value
    return "Pending"

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
    row = dict(existing_row)
    categories = normalize_log_categories(row.get("log_category", ""))
    if new_category not in categories:
        categories.append(new_category)
    row["log_category"] = format_log_categories_for_storage(categories)
    return row

def ensure_logged_bet_clv_fields(row):
    row = dict(row)

    if "open_odds" not in row:
        row["open_odds"] = row.get("odds")

    if "open_line" not in row:
        row["open_line"] = extract_line_from_selection(row.get("selection", ""))

    if "closing_odds" not in row:
        row["closing_odds"] = None

    if "closing_line" not in row:
        row["closing_line"] = None

    if "clv_diff" not in row:
        row["clv_diff"] = None

    if "clv_result" not in row:
        row["clv_result"] = None

    return row

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

def get_base_play_id(play_id):
    pid = str(play_id).strip()
    if "__" in pid:
        return pid.split("__")[0].strip()
    return pid

def same_play_family(play_id_a, play_id_b):
    return get_base_play_id(play_id_a) == get_base_play_id(play_id_b)

def extract_line_from_selection(selection_text):
    text = str(selection_text).strip()
    if not text:
        return None

    match = re.search(r'([+-]?\d+(?:\.\d+)?)', text)
    if not match:
        return None

    try:
        return float(match.group(1))
    except Exception:
        return None

def build_logged_bet_row(row_dict, log_category_label):
    enriched = enrich_play_with_learning_fields_compat(row_dict)

    selection_line = extract_line_from_selection(enriched.get("selection", ""))
    open_odds = enriched.get("odds")
    open_line = selection_line if selection_line is not None else enriched.get("line", None)

    new_row = {
        "play_id": str(enriched.get("play_id", "")).strip(),
        "sport": get_selected_sport(),
        "game": enriched.get("game"),
        "market": enriched.get("market"),
        "selection": enriched.get("selection"),
        "player": enriched.get("player", ""),
        "team": enriched.get("team", ""),
        "opponent": enriched.get("opponent", ""),
        "line": enriched.get("line"),
        "odds": enriched.get("odds"),
        "best_price": enriched.get("best_price", enriched.get("odds")),
        "best_book": enriched.get("best_book", ""),
        "implied_prob": enriched.get("implied_prob"),
        "true_prob": enriched.get("true_prob"),
        "implied_probability": enriched.get("implied_probability"),
        "true_probability": enriched.get("true_probability"),
        "edge": enriched.get("edge"),
        "price_edge": enriched.get("price_edge", enriched.get("edge")),
        "play_type": enriched.get("play_type"),
        "primary_category": enriched.get("primary_category"),
        "category": enriched.get("category"),
        "units": safe_float(enriched.get("units", 1.0), 1.0),
        "stake": safe_float(enriched.get("units", 1.0), 1.0),
        "confidence": enriched.get("confidence"),
        "true_confidence": enriched.get("true_confidence"),
        "books_seen": enriched.get("books_seen", enriched.get("books")),
        "books": enriched.get("books", enriched.get("books_seen")),
        "consensus": enriched.get("consensus"),
        "consensus_pct": enriched.get("consensus_pct"),
        "result": "Pending",
        "profit": 0.0,
        "mode": TEST_MODE,
        "log_category": log_category_label,
        "timestamp": datetime.now().isoformat(),
        "sportsdata_note": enriched.get("sportsdata_note", ""),
        "injury_flag": enriched.get("injury_flag", ""),
        "lineup_flag": enriched.get("lineup_flag", ""),
        "context_score": enriched.get("context_score", 0.0),
        "model_score": enriched.get("model_score", 0.0),
        "score": enriched.get("score", enriched.get("model_score", 0.0)),
        "rank_score": enriched.get("rank_score", enriched.get("score", 0.0)),
        "tier": enriched.get("tier", "C"),
        "quality_label": enriched.get("quality_label", "Watch"),
        "watch_tier": enriched.get("watch_tier", ""),
        "ai_tags": enriched.get("ai_tags", []),
        "open_odds": open_odds,
        "open_line": open_line,
        "closing_odds": None,
        "closing_line": None,
        "clv_diff": None,
        "clv_result": None,
    }

    return ensure_logged_bet_clv_fields(new_row)

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
            existing_row = dict(st.session_state["bet_log"][exact_idx])
            before_category = str(existing_row.get("log_category", "")).strip()

            updated_row = add_category_to_logged_bet(existing_row, "Top Play")
            updated_row["category"] = "Top Plays"
            updated_row["primary_category"] = "Top Plays"
            updated_row = ensure_logged_bet_clv_fields(updated_row)

            st.session_state["bet_log"][exact_idx] = updated_row
            st.session_state["auto_logged_ids"].add(pid)

            if before_category != str(updated_row.get("log_category", "")).strip():
                changed = True

            continue

        suffix_idx = find_logged_bet_index_by_suffix_play_id(pid)

        new_bet = build_logged_bet_row(row.to_dict(), "Top Play")
        new_bet["category"] = "Top Plays"
        new_bet["primary_category"] = "Top Plays"

        if suffix_idx is not None:
            suffix_row = ensure_logged_bet_clv_fields(st.session_state["bet_log"][suffix_idx])

            suffix_categories = normalize_log_categories(suffix_row.get("log_category", ""))
            merged_categories = ["Top Play"]
            for cat in suffix_categories:
                if cat not in merged_categories:
                    merged_categories.append(cat)

            new_bet["log_category"] = format_log_categories_for_storage(merged_categories)

            suffix_result = normalize_result_value(suffix_row.get("result", "Pending"))
            new_bet["result"] = suffix_result
            new_bet["profit"] = settle_result_pnl(new_bet["odds"], new_bet["units"], suffix_result)

            new_bet["closing_odds"] = suffix_row.get("closing_odds", None)
            new_bet["closing_line"] = suffix_row.get("closing_line", None)
            new_bet["clv_diff"] = suffix_row.get("clv_diff", None)
            new_bet["clv_result"] = suffix_row.get("clv_result", None)

        new_bet = ensure_logged_bet_clv_fields(new_bet)

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

    pid = str(best_row.get("play_id", "")).strip() if hasattr(best_row, "get") else ""
    if not pid:
        return False

    exact_idx = find_logged_bet_index_by_exact_play_id(pid)
    if exact_idx is not None:
        existing_row = dict(st.session_state["bet_log"][exact_idx])
        updated_row = add_category_to_logged_bet(existing_row, "AI Slip")
        updated_row["category"] = "AI Picks"
        updated_row["primary_category"] = "AI Picks"
        updated_row = ensure_logged_bet_clv_fields(updated_row)

        st.session_state["bet_log"][exact_idx] = updated_row
        save_bet_log()
        return False

    suffix_idx = find_logged_bet_index_by_suffix_play_id(pid)
    if suffix_idx is not None:
        existing_row = dict(st.session_state["bet_log"][suffix_idx])
        updated_row = add_category_to_logged_bet(existing_row, "AI Slip")
        updated_row["category"] = "AI Picks"
        updated_row["primary_category"] = "AI Picks"
        updated_row = ensure_logged_bet_clv_fields(updated_row)

        st.session_state["bet_log"][suffix_idx] = updated_row
        save_bet_log()
        return False

    ai_slip_id = f"{pid}__ai_slip"

    row_dict = best_row.to_dict() if hasattr(best_row, "to_dict") else dict(best_row)
    row_dict["play_id"] = ai_slip_id

    new_row = build_logged_bet_row(row_dict, "AI Slip")
    new_row["category"] = "AI Picks"
    new_row["primary_category"] = "AI Picks"
    new_row = ensure_logged_bet_clv_fields(new_row)

    st.session_state["bet_log"].append(new_row)
    save_bet_log()
    return True

def scale_parlay_units(parlay):
    if not parlay:
        return 0.0

    leg_count = safe_int(parlay.get("leg_count", 2), 2)
    avg_true_conf = safe_float(parlay.get("avg_true_conf", 0), 0.0)
    penalty = safe_float(parlay.get("total_penalty", 1.0), 1.0)
    approval_type = str(parlay.get("approval_type", "")).strip()

    if approval_type == "Sharp Approved" and avg_true_conf >= 70 and penalty <= SHARP_PARLAY_MAX_PENALTY:
        return round(PARLAY_UNIT_SHARP, 2)

    if leg_count <= 2:
        return round(PARLAY_UNIT_FALLBACK_2, 2)

    return round(PARLAY_UNIT_FALLBACK_3, 2)

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
        existing_row = dict(st.session_state["bet_log"][existing_idx])
        updated_row = add_category_to_logged_bet(existing_row, "AI Parlay")
        updated_row["category"] = "AI Parlays"
        updated_row["primary_category"] = "AI Parlays"
        updated_row = ensure_logged_bet_clv_fields(updated_row)

        st.session_state["bet_log"][existing_idx] = updated_row
        save_bet_log()
        return False

    new_row = {
        "play_id": parlay_id,
        "sport": get_selected_sport(),
        "game": " | ".join(sorted(set([str(leg.get("game", "")) for leg in best_parlay.get("legs", [])]))),
        "market": "parlay",
        "selection": " | ".join([str(leg.get("selection", "")) for leg in best_parlay.get("legs", [])]),
        "player": "",
        "team": "",
        "opponent": "",
        "line": None,
        "odds": best_parlay.get("combined_odds"),
        "best_price": best_parlay.get("combined_odds"),
        "best_book": "",
        "implied_prob": None,
        "true_prob": None,
        "implied_probability": None,
        "true_probability": None,
        "edge": best_parlay.get("avg_edge"),
        "price_edge": best_parlay.get("avg_edge"),
        "play_type": "parlay",
        "primary_category": "AI Parlays",
        "category": "AI Parlays",
        "units": scale_parlay_units(best_parlay),
        "stake": scale_parlay_units(best_parlay),
        "confidence": "High" if float(best_parlay.get("avg_true_conf", 0)) >= 70 else "Medium",
        "true_confidence": best_parlay.get("avg_true_conf"),
        "books_seen": best_parlay.get("avg_books"),
        "books": best_parlay.get("avg_books"),
        "consensus": best_parlay.get("approval_type"),
        "consensus_pct": None,
        "result": "Pending",
        "profit": 0.0,
        "mode": TEST_MODE,
        "log_category": "AI Parlay",
        "timestamp": datetime.now().isoformat(),
        "sportsdata_note": "",
        "injury_flag": "",
        "lineup_flag": "",
        "context_score": 0.0,
        "model_score": best_parlay.get("score", 0.0),
        "score": best_parlay.get("score", 0.0),
        "rank_score": best_parlay.get("score", 0.0),
        "tier": "B",
        "quality_label": "Strong",
        "watch_tier": "",
        "ai_tags": [],
        "open_odds": best_parlay.get("combined_odds"),
        "open_line": None,
        "closing_odds": None,
        "closing_line": None,
        "clv_diff": None,
        "clv_result": None,
    }

    new_row = ensure_logged_bet_clv_fields(new_row)

    st.session_state["bet_log"].append(new_row)
    save_bet_log()
    return True

# =========================================================
# ROI CALCULATOR (CATEGORY-BASED)
# =========================================================
def build_roi_dashboard(log_df: pd.DataFrame):
    if log_df is None or log_df.empty:
        return pd.DataFrame()

    df = log_df.copy()

    if "log_category" not in df.columns:
        df["log_category"] = "Uncategorized"

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
# V33 SELF-LEARNING ENGINE (LEGACY BLOCK DISABLED)
# =========================================================
# This legacy block has been intentionally disabled.
# The active learning system now uses:
# - update_learning_from_results()
# - get_learning_summary_rows()
# - get_learning_activation_metrics()
# - apply_v33_learning_filters()
# - apply_learning_engine_to_df()

# =========================================================
# EFFECTIVE THRESHOLDS + UNIT SCALING HELPERS
# =========================================================
def get_effective_min_active_edge():
    return round(get_dynamic_edge_threshold("Top Plays") * 100.0, 2)

def get_effective_min_watch_edge():
    active_edge = get_effective_min_active_edge()
    return round(max(MIN_WATCH_EDGE, active_edge - 1.75), 2)

def get_effective_min_active_true_conf():
    return float(MIN_ACTIVE_TRUE_CONF)

def get_effective_min_watch_true_conf():
    return float(MIN_WATCH_TRUE_CONF)

def classify_watch_tier(row):
    edge = safe_float(row.get("edge", 0), 0.0)
    tc = safe_float(row.get("true_confidence", 0), 0.0)
    books = safe_int(row.get("books_seen", 0), 0)

    near_active_edge = max(get_effective_min_active_edge() - 0.75, get_effective_min_watch_edge())
    near_active_conf = max(get_effective_min_active_true_conf() - 4.0, get_effective_min_watch_true_conf())

    if edge >= near_active_edge and tc >= near_active_conf and books >= 2:
        return "Near Active"

    if edge >= get_effective_min_watch_edge() + 0.5 and tc >= get_effective_min_watch_true_conf() + 3.0:
        return "Monitor"

    return "Weak Watch"

def _confidence_unit_multiplier(true_conf):
    tc = safe_float(true_conf, 0.0)

    if tc >= 75:
        return 1.05
    if tc >= 70:
        return 1.00
    if tc >= 65:
        return 1.00
    return 0.92

def scale_single_units(row):
    edge = safe_float(row.get("edge", 0), 0.0)
    tc = safe_float(row.get("true_confidence", 0), 0.0)

    base_units = 0.40

    if tc >= 78 and edge >= 5.5:
        base_units = 1.25
    elif tc >= 74 and edge >= 5.0:
        base_units = 1.00
    elif tc >= 70 and edge >= 4.5:
        base_units = 0.75
    elif tc >= 65 and edge >= 4.0:
        base_units = 0.50

    base_units *= _confidence_unit_multiplier(tc)

    return round(clamp(base_units, SINGLE_UNIT_MIN, SINGLE_UNIT_MAX), 2)

def scale_watch_units(row):
    edge = safe_float(row.get("edge", 0), 0.0)
    tc = safe_float(row.get("true_confidence", 0), 0.0)

    base_units = WATCH_UNIT_MIN

    if tc >= 68 and edge >= 3.5:
        base_units = 0.50
    elif tc >= 62 and edge >= 2.75:
        base_units = 0.35
    else:
        base_units = WATCH_UNIT_MIN

    return round(clamp(base_units, WATCH_UNIT_MIN, WATCH_UNIT_MAX), 2)

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
loaded_bet_log = load_bet_log()

SAFE_BET_LOG_COLUMNS = [
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
    "units",
    "status",
    "log_category",
    "result",
    "profit",
    "timestamp",
    "confidence",
    "category",
    "primary_category",
    "play_type",
    "stake",
    "mode",
    "sportsdata_note",
    "injury_flag",
    "lineup_flag",
    "model_score",
    "score",
    "rank_score",
    "tier",
    "quality_label",
    "watch_tier",
    "ai_tags",
    "context_score",
    "open_odds",
    "open_line",
    "closing_odds",
    "closing_line",
    "clv_diff",
    "clv_result",
]

if "bet_log" not in st.session_state or not st.session_state["bet_log"]:
    st.session_state["bet_log"] = loaded_bet_log
else:
    existing_df = pd.DataFrame(st.session_state.get("bet_log", []))

    if existing_df is None or existing_df.empty:
        st.session_state["bet_log"] = loaded_bet_log
    else:
        for col in SAFE_BET_LOG_COLUMNS:
            if col not in existing_df.columns:
                existing_df[col] = None

        existing_df = _merge_duplicate_play_id_rows(existing_df)
        st.session_state["bet_log"] = existing_df.to_dict("records")

bet_log_df = pd.DataFrame(st.session_state.get("bet_log", []))
if bet_log_df is None or bet_log_df.empty:
    bet_log_df = pd.DataFrame(columns=SAFE_BET_LOG_COLUMNS)
else:
    for col in SAFE_BET_LOG_COLUMNS:
        if col not in bet_log_df.columns:
            bet_log_df[col] = None

    bet_log_df = _merge_duplicate_play_id_rows(bet_log_df)

st.session_state["bet_log"] = bet_log_df.to_dict("records")
save_bet_log(st.session_state["bet_log"])
st.session_state["auto_logged_ids"] = build_logged_id_set(
    st.session_state.get("bet_log", [])
)

# ---------------------------------------------------------
# SAFE FALLBACK: prevent NameError if learning function is
# missing or defined later in the current file
# ---------------------------------------------------------
if "update_learning_from_results" not in globals() or not callable(globals().get("update_learning_from_results")):
    def update_learning_from_results(sport=None):
        return None


# =========================================================
# BUILD + PERSIST GENERATED PLAYS
# =========================================================
plays_df = generate_ai_plays()

if not isinstance(plays_df, pd.DataFrame):
    plays_df = pd.DataFrame()

selected_sport = get_selected_sport()
plays_df = normalize_dataframe_for_selected_sport(plays_df, selected_sport)

if not plays_df.empty:
    plays_df = recalculate_play_metrics(plays_df)

    # -----------------------------------------------------
    # ENSURE REQUIRED COLUMNS EXIST
    # -----------------------------------------------------
    for col, default_val in {
        "sport": selected_sport,
        "status": "",
        "edge": 0.0,
        "true_confidence": 0.0,
        "books_seen": 0,
        "books": 0,
        "units": 0.0,
        "best_price": None,
        "best_book": "",
        "selection": "",
        "market": "",
        "game": "",
        "log_category": "",
    }.items():
        if col not in plays_df.columns:
            plays_df[col] = default_val

    plays_df["sport"] = plays_df["sport"].fillna(selected_sport).astype(str).str.upper()
    plays_df["edge"] = pd.to_numeric(plays_df["edge"], errors="coerce").fillna(0.0)
    plays_df["true_confidence"] = pd.to_numeric(plays_df["true_confidence"], errors="coerce").fillna(0.0)

    if "books_seen" in plays_df.columns:
        plays_df["books_seen"] = pd.to_numeric(plays_df["books_seen"], errors="coerce").fillna(0)
    else:
        plays_df["books_seen"] = pd.to_numeric(plays_df.get("books", 0), errors="coerce").fillna(0)

    plays_df["units"] = pd.to_numeric(plays_df["units"], errors="coerce").fillna(0.0)

    # -----------------------------------------------------
    # IF STATUS IS MISSING, BUILD IT HERE
    # -----------------------------------------------------
    def _derive_status(row):
        existing = str(row.get("status", "")).strip()
        if existing in ["Active", "Watchlist", "Fallback"]:
            return existing

        edge_val = float(row.get("edge", 0.0))
        conf_val = float(row.get("true_confidence", 0.0))
        books_val = float(row.get("books_seen", row.get("books", 0)))

        if (
            edge_val >= MIN_ACTIVE_EDGE
            and conf_val >= MIN_ACTIVE_TRUE_CONF
            and books_val >= MIN_ACTIVE_BOOKS
        ):
            return "Active"

        if (
            edge_val >= MIN_WATCH_EDGE
            and conf_val >= MIN_WATCH_TRUE_CONF
            and books_val >= MIN_WATCH_BOOKS
        ):
            return "Watchlist"

        return ""

    plays_df["status"] = plays_df.apply(_derive_status, axis=1)

    # -----------------------------------------------------
    # FAILSAFE: if nothing qualified, keep best rows visible
    # -----------------------------------------------------
    if plays_df["status"].astype(str).str.strip().eq("").all():
        fallback_df = plays_df.copy()

        fallback_df = fallback_df.sort_values(
            by=["true_confidence", "edge", "books_seen"],
            ascending=[False, False, False],
        ).head(TOP_PLAYS_LIMIT)

        fallback_df["status"] = "Fallback"
        fallback_df["log_category"] = fallback_df["log_category"].replace("", "Top Plays")
        plays_df = fallback_df.copy()

    # -----------------------------------------------------
    # UNITS + CATEGORY
    # -----------------------------------------------------
    def _derive_units(row):
        current_units = float(row.get("units", 0.0))
        if current_units > 0:
            return round(current_units, 2)
        return calculate_units(row.get("true_confidence", 0.0), row.get("status", ""))

    plays_df["units"] = plays_df.apply(_derive_units, axis=1)

    def _derive_log_category(row):
        existing = str(row.get("log_category", "")).strip()
        if existing:
            return existing
        status_val = str(row.get("status", "")).strip()
        if status_val in ["Active", "Fallback"]:
            return "Top Plays"
        if status_val == "Watchlist":
            return "Watchlist"
        return ""

    plays_df["log_category"] = plays_df.apply(_derive_log_category, axis=1)

    # -----------------------------------------------------
    # BUILD TAB DATAFRAMES
    # -----------------------------------------------------
    active_df = plays_df[
        plays_df["status"].astype(str).isin(["Active", "Fallback"])
    ].copy()

    watchlist_df = plays_df[
        plays_df["status"].astype(str) == "Watchlist"
    ].copy()

    top_plays_df = active_df.sort_values(
        by=["true_confidence", "edge", "books_seen"],
        ascending=[False, False, False],
    ).head(TOP_PLAYS_LIMIT).copy()

    ai_slip_df = top_plays_df.head(5).copy()

    best_row = {}
    if not top_plays_df.empty:
        best_row = top_plays_df.iloc[0].to_dict()

    # -----------------------------------------------------
    # SAVE INTO SESSION STATE
    # -----------------------------------------------------
    st.session_state["plays_df"] = plays_df.copy()
    st.session_state["snapshot_plays_df"] = plays_df.copy()
    st.session_state["snapshot_all_plays_df"] = plays_df.copy()
    st.session_state["snapshot_active_df"] = active_df.copy()
    st.session_state["snapshot_top_plays_df"] = top_plays_df.copy()
    st.session_state["snapshot_watchlist_df"] = watchlist_df.copy()
    st.session_state["snapshot_ai_slip_df"] = ai_slip_df.copy()
    st.session_state["ai_slip_df"] = ai_slip_df.copy()
    st.session_state["snapshot_best_row"] = best_row
    st.session_state["snapshot_generated_at"] = pd.Timestamp.now().strftime("%Y-%m-%d %I:%M:%S %p")
    st.session_state["snapshot_last_updated"] = pd.Timestamp.now().strftime("%Y-%m-%d %I:%M:%S %p")
    st.session_state["snapshot_refresh_id"] = int(st.session_state.get("snapshot_refresh_id", 0)) + 1

    # -----------------------------------------------------
    # SAVE TO DISK
    # -----------------------------------------------------
    persist_generated_play_snapshots(plays_df)
    save_tab_snapshots_to_disk()

else:
    # -----------------------------------------------------
    # CLEAR EMPTY SNAPSHOTS CLEANLY
    # -----------------------------------------------------
    st.session_state["plays_df"] = pd.DataFrame()
    st.session_state["snapshot_plays_df"] = pd.DataFrame()
    st.session_state["snapshot_all_plays_df"] = pd.DataFrame()
    st.session_state["snapshot_active_df"] = pd.DataFrame()
    st.session_state["snapshot_top_plays_df"] = pd.DataFrame()
    st.session_state["snapshot_watchlist_df"] = pd.DataFrame()
    st.session_state["snapshot_ai_slip_df"] = pd.DataFrame()
    st.session_state["ai_slip_df"] = pd.DataFrame()
    st.session_state["snapshot_best_row"] = {}
    st.session_state["snapshot_generated_at"] = pd.Timestamp.now().strftime("%Y-%m-%d %I:%M:%S %p")
    st.session_state["snapshot_last_updated"] = pd.Timestamp.now().strftime("%Y-%m-%d %I:%M:%S %p")

    persist_generated_play_snapshots(pd.DataFrame())
    save_tab_snapshots_to_disk()
# =========================================================
# APPLY SPORTSDATA ENRICHMENT
# =========================================================
try:
    if plays_df is not None and not plays_df.empty:
        plays_df = enrich_plays_with_sportsdata(
            plays_df,
            sport=get_current_sportsdata_slug(),
            game_date=sportsdata_game_date,
        )
        if "recalculate_play_metrics" in globals() and callable(globals().get("recalculate_play_metrics")):
            plays_df = recalculate_play_metrics(plays_df)
except Exception as e:
    st.warning(f"SportsData enrichment skipped: {e}")

# =========================================================
# APPLY LEARNING FILTERS
# =========================================================
if plays_df is not None and not plays_df.empty:
    active_source_df = plays_df[
        plays_df["status"].astype(str).str.strip() == "Active"
    ].copy().reset_index(drop=True)

    watch_source_df = plays_df[
        plays_df["status"].astype(str).str.strip().isin(["Watch", "Watchlist"])
    ].copy().reset_index(drop=True)

    if "apply_learning_engine_to_df" in globals() and callable(globals().get("apply_learning_engine_to_df")):
        active_df = apply_learning_engine_to_df(active_source_df, "Top Plays")
        watch_df = apply_learning_engine_to_df(watch_source_df, "Watchlist")
    else:
        active_df = active_source_df.copy()
        watch_df = watch_source_df.copy()
else:
    active_df = pd.DataFrame()
    watch_df = pd.DataFrame()

# Keep compatibility names that older UI may still reference
top_plays_df = active_df.copy()
watchlist_df = watch_df.copy()

# =========================================================
# RECALCULATE TOP/WATCH SNAPSHOTS AFTER LEARNING FILTERS
# =========================================================
try:
    selected_sport = get_selected_sport()

    snapshot_source_frames = []
    if isinstance(active_df, pd.DataFrame) and not active_df.empty:
        snapshot_source_frames.append(active_df.copy())
    if isinstance(watch_df, pd.DataFrame) and not watch_df.empty:
        snapshot_source_frames.append(watch_df.copy())

    if snapshot_source_frames:
        filtered_snapshot_df = pd.concat(snapshot_source_frames, ignore_index=True)
        filtered_snapshot_df = normalize_dataframe_for_selected_sport(filtered_snapshot_df, selected_sport)
        filtered_snapshot_df = recalculate_play_metrics(filtered_snapshot_df)

        rebuilt_top_df = build_top_plays_df(filtered_snapshot_df)
        rebuilt_watch_df = build_watchlist_df(filtered_snapshot_df, rebuilt_top_df)

        if not rebuilt_top_df.empty:
            active_df = rebuilt_top_df.copy()
            top_plays_df = rebuilt_top_df.copy()

        if not rebuilt_watch_df.empty:
            watch_df = rebuilt_watch_df.copy()
            watchlist_df = rebuilt_watch_df.copy()
except Exception:
    pass

# ================================
# AUTO LOG TOP PLAYS
# ================================
auto_logged_count = 0
try:
    auto_logged_count = auto_log_active_plays(active_df)
except Exception:
    auto_logged_count = 0

# ================================
# BEST SINGLE
# ================================
best_row = None
if isinstance(active_df, pd.DataFrame) and not active_df.empty:
    if "rank_score" in active_df.columns:
        best_row = active_df.sort_values(
            ["rank_score", "true_confidence"],
            ascending=False,
        ).iloc[0]
    else:
        sort_cols = [c for c in ["true_confidence", "edge"] if c in active_df.columns]
        if sort_cols:
            best_row = active_df.sort_values(
                sort_cols,
                ascending=[False] * len(sort_cols),
            ).iloc[0]
        else:
            best_row = active_df.iloc[0]

# ================================
# PARLAY ENGINE
# ================================
best_parlay, sharp_candidates, fallback_candidates = choose_best_parlay(active_df)

parlay_df = pd.DataFrame()
try:
    parlay_rows = []

    if best_parlay is not None:
        parlay_rows.append(
            {
                "sport": get_selected_sport(),
                "approval_type": best_parlay.get("approval_type", ""),
                "leg_count": best_parlay.get("leg_count", 0),
                "combined_odds": best_parlay.get("combined_odds", ""),
                "combined_odds_int": best_parlay.get("combined_odds_int", 0),
                "avg_true_conf": best_parlay.get("avg_true_conf", 0.0),
                "avg_edge": best_parlay.get("avg_edge", 0.0),
                "avg_books": best_parlay.get("avg_books", 0.0),
                "total_penalty": best_parlay.get("total_penalty", 0.0),
                "cross_game": best_parlay.get("cross_game", False),
                "correlation_score": best_parlay.get("correlation_score", 0.0),
                "score": best_parlay.get("score", 0.0),
                "display_score": best_parlay.get("display_score", 0.0),
                "risk_label": best_parlay.get("risk_label", ""),
                "reasons": " | ".join(best_parlay.get("reasons", [])),
                "legs_text": " | ".join(
                    [str(leg.get("selection", "")).strip() for leg in best_parlay.get("legs", [])]
                ),
                "games_text": " | ".join(
                    [str(leg.get("game", "")).strip() for leg in best_parlay.get("legs", [])]
                ),
            }
        )

    if parlay_rows:
        parlay_df = pd.DataFrame(parlay_rows)
except Exception:
    parlay_df = pd.DataFrame()

# ================================
# SAFE LOGGING
# ================================
if best_row is not None:
    log_ai_slip_pick(best_row)

if best_parlay is not None:
    log_ai_parlay_pick(best_parlay)

update_learning_from_results()

# ================================
# PORTFOLIO BUILD
# ================================
all_portfolio_candidates = [*sharp_candidates, *fallback_candidates]
portfolio = build_ai_portfolio(best_row, best_parlay, all_portfolio_candidates)

# ================================
# SNAPSHOT BUILD + SAVE
# ================================
ai_slip_df = pd.DataFrame()

try:
    active_exists = isinstance(active_df, pd.DataFrame) and not active_df.empty
    watch_exists = isinstance(watch_df, pd.DataFrame) and not watch_df.empty

    if active_exists and watch_exists:
        snapshot_source_df = pd.concat(
            [active_df.copy(), watch_df.copy()],
            ignore_index=True,
        )
    elif active_exists:
        snapshot_source_df = active_df.copy()
    elif watch_exists:
        snapshot_source_df = watch_df.copy()
    else:
        snapshot_source_df = pd.DataFrame()

    snapshot_source_df = normalize_dataframe_for_selected_sport(
        snapshot_source_df,
        get_selected_sport(),
    )

    if isinstance(snapshot_source_df, pd.DataFrame) and not snapshot_source_df.empty:
        snapshot_source_df = recalculate_play_metrics(snapshot_source_df)

        snapshot_top_df, snapshot_watch_df, ai_slip_df = save_generated_play_snapshots(snapshot_source_df)

        top_plays_df = (
            snapshot_top_df.copy()
            if isinstance(snapshot_top_df, pd.DataFrame)
            else pd.DataFrame()
        )
        watchlist_df = (
            snapshot_watch_df.copy()
            if isinstance(snapshot_watch_df, pd.DataFrame)
            else pd.DataFrame()
        )

        active_df = top_plays_df.copy()
        watch_df = watchlist_df.copy()

        if (best_row is None) and not top_plays_df.empty:
            best_row = top_plays_df.iloc[0]

        if isinstance(parlay_df, pd.DataFrame):
            st.session_state["snapshot_parlay_df"] = parlay_df.copy()
        else:
            st.session_state["snapshot_parlay_df"] = pd.DataFrame()

        if best_row is not None:
            if hasattr(best_row, "to_dict"):
                st.session_state["snapshot_best_row"] = best_row.to_dict()
            elif isinstance(best_row, dict):
                st.session_state["snapshot_best_row"] = dict(best_row)

        try:
            save_tab_snapshots_to_disk()
        except Exception:
            pass

    else:
        existing_snapshot_df = st.session_state.get("snapshot_plays_df", pd.DataFrame())
        if not isinstance(existing_snapshot_df, pd.DataFrame) or existing_snapshot_df.empty:
            clear_generated_play_snapshots()
            st.session_state["snapshot_parlay_df"] = pd.DataFrame()

except Exception as e:
    st.warning(f"Snapshot build/save skipped: {e}")
    ai_slip_df = pd.DataFrame()

# ================================
# SNAPSHOT METRICS
# ================================
avg_active_edge = (
    pd.to_numeric(active_df["edge"], errors="coerce").fillna(0).mean()
    if isinstance(active_df, pd.DataFrame) and not active_df.empty and "edge" in active_df.columns
    else 0.0
)

if best_row is not None:
    if hasattr(best_row, "get"):
        if "score" in best_row:
            best_score = best_row.get("score", "—")
        elif "rank_score" in best_row:
            best_score = best_row.get("rank_score", "—")
        elif "model_score" in best_row:
            best_score = best_row.get("model_score", "—")
        else:
            best_score = "—"
    else:
        best_score = "—"
else:
    best_score = "—"

avg_true_conf = (
    pd.to_numeric(active_df["true_confidence"], errors="coerce").fillna(0).mean()
    if isinstance(active_df, pd.DataFrame) and not active_df.empty and "true_confidence" in active_df.columns
    else 0.0
)

avg_true_prob = (
    pd.to_numeric(active_df["true_prob"], errors="coerce").fillna(0).mean()
    if isinstance(active_df, pd.DataFrame) and not active_df.empty and "true_prob" in active_df.columns
    else 0.0
)

total_units = (
    pd.to_numeric(active_df["units"], errors="coerce").fillna(0).sum()
    if isinstance(active_df, pd.DataFrame) and not active_df.empty and "units" in active_df.columns
    else 0.0
)

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
current_api_mode = str(st.session_state.get("api_mode", "idle")).strip().lower()
current_api_error = str(st.session_state.get("last_refresh_error", "")).strip().lower()

if current_api_mode == "live":
    status_text, status_dot, status_bg, status_fg = "LIVE", "#10b981", "#ecfdf5", "#065f46"
elif current_api_mode == "cached":
    status_text, status_dot, status_bg, status_fg = "CACHED", "#0ea5e9", "#eff6ff", "#075985"
elif current_api_mode in ["daily_limit", "limit_hit"]:
    status_text, status_dot, status_bg, status_fg = "DAILY LIMIT", "#7c3aed", "#f5f3ff", "#5b21b6"
elif current_api_mode == "waiting_reset":
    status_text, status_dot, status_bg, status_fg = "WAITING RESET", "#f97316", "#fff7ed", "#9a3412"
elif current_api_mode == "no_key":
    status_text, status_dot, status_bg, status_fg = "NO KEY", "#f59e0b", "#fffbeb", "#92400e"
elif "401" in current_api_error or "unauthorized" in current_api_error:
    status_text, status_dot, status_bg, status_fg = "KEY ERROR", "#ef4444", "#fef2f2", "#991b1b"
elif current_api_mode in ["error", "fallback"]:
    status_text, status_dot, status_bg, status_fg = "OFFLINE", "#64748b", "#f8fafc", "#334155"
else:
    status_text, status_dot, status_bg, status_fg = "IDLE", "#64748b", "#f8fafc", "#334155"

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

reset_expected = str(st.session_state.get("odds_api_reset_expected", "")).strip()

if status_text == "WAITING RESET":
    st.warning(
        f"The Odds API appears to be waiting for quota reset."
        + (f" Expected reset around {reset_expected}." if reset_expected else "")
    )
    st.info(
        "Cached odds will be used when available. "
        "If no cached odds exist yet, no live market plays can be generated."
    )

elif status_text in ["CACHED", "DAILY LIMIT", "OFFLINE", "KEY ERROR", "NO KEY"]:
    st.info(
        "Fallback mode is active. Cached odds will be used when available. "
        "If no cached odds exist yet, no live market plays can be generated."
    )

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
def update_logged_bet_result(play_id, result_value):
    result_value = normalize_result_value(result_value)
    updated = False
    target_base_id = get_base_play_id(play_id)

    for i, bet in enumerate(st.session_state.get("bet_log", [])):
        current_play_id = str(bet.get("play_id", "")).strip()
        current_base_id = get_base_play_id(current_play_id)

        if current_play_id != str(play_id).strip() and current_base_id != target_base_id:
            continue

        units = safe_float(bet.get("units", bet.get("stake", 0)), 0.0)
        odds = bet.get("odds", "")

        st.session_state["bet_log"][i]["result"] = result_value
        st.session_state["bet_log"][i]["profit"] = settle_result_pnl(odds, units, result_value)
        st.session_state["bet_log"][i]["stake"] = units

        if "open_odds" not in st.session_state["bet_log"][i]:
            st.session_state["bet_log"][i]["open_odds"] = bet.get("odds")
        if "open_line" not in st.session_state["bet_log"][i]:
            st.session_state["bet_log"][i]["open_line"] = extract_line_from_selection(bet.get("selection", ""))
        if "closing_odds" not in st.session_state["bet_log"][i]:
            st.session_state["bet_log"][i]["closing_odds"] = None
        if "closing_line" not in st.session_state["bet_log"][i]:
            st.session_state["bet_log"][i]["closing_line"] = None
        if "clv_diff" not in st.session_state["bet_log"][i]:
            st.session_state["bet_log"][i]["clv_diff"] = None
        if "clv_result" not in st.session_state["bet_log"][i]:
            st.session_state["bet_log"][i]["clv_result"] = None

        open_line = st.session_state["bet_log"][i].get("open_line")
        closing_line = st.session_state["bet_log"][i].get("closing_line")

        clv_diff = None
        clv_result = None

        if open_line not in [None, ""] and closing_line not in [None, ""]:
            clv_diff, clv_result = calculate_clv_diff(
                open_line=open_line,
                closing_line=closing_line,
                market=st.session_state["bet_log"][i].get("market", ""),
                selection=st.session_state["bet_log"][i].get("selection", ""),
            )

        st.session_state["bet_log"][i]["clv_diff"] = clv_diff
        st.session_state["bet_log"][i]["clv_result"] = clv_result

        updated = True

    if updated:
        save_bet_log()
        update_learning_from_results()

    return updated

def sync_manual_results_into_bet_log():
    manual_results = st.session_state.get("manual_results", {})
    if not manual_results:
        return

    changed = False

    for selected_pid, selected_result in manual_results.items():
        target_base_id = get_base_play_id(selected_pid)
        normalized_result = normalize_result_value(selected_result)

        for i, bet in enumerate(st.session_state.get("bet_log", [])):
            pid = str(bet.get("play_id", "")).strip()
            if not pid:
                continue

            if get_base_play_id(pid) != target_base_id and pid != str(selected_pid).strip():
                continue

            current_result = normalize_result_value(bet.get("result", "Pending"))
            current_profit = safe_float(bet.get("profit", 0.0), 0.0)
            units = safe_float(bet.get("units", bet.get("stake", 0)), 0.0)

            new_profit = settle_result_pnl(
                bet.get("odds", ""),
                units,
                normalized_result,
            )

            if "open_odds" not in st.session_state["bet_log"][i]:
                st.session_state["bet_log"][i]["open_odds"] = bet.get("odds")
            if "open_line" not in st.session_state["bet_log"][i]:
                st.session_state["bet_log"][i]["open_line"] = extract_line_from_selection(bet.get("selection", ""))
            if "closing_odds" not in st.session_state["bet_log"][i]:
                st.session_state["bet_log"][i]["closing_odds"] = None
            if "closing_line" not in st.session_state["bet_log"][i]:
                st.session_state["bet_log"][i]["closing_line"] = None
            if "clv_diff" not in st.session_state["bet_log"][i]:
                st.session_state["bet_log"][i]["clv_diff"] = None
            if "clv_result" not in st.session_state["bet_log"][i]:
                st.session_state["bet_log"][i]["clv_result"] = None

            open_line = st.session_state["bet_log"][i].get("open_line")
            closing_line = st.session_state["bet_log"][i].get("closing_line")

            clv_diff = None
            clv_result = None

            if open_line not in [None, ""] and closing_line not in [None, ""]:
                clv_diff, clv_result = calculate_clv_diff(
                    open_line=open_line,
                    closing_line=closing_line,
                    market=bet.get("market", ""),
                    selection=bet.get("selection", ""),
                )

            if (
                current_result != normalized_result
                or round(current_profit, 2) != round(new_profit, 2)
                or st.session_state["bet_log"][i].get("clv_diff") != clv_diff
                or st.session_state["bet_log"][i].get("clv_result") != clv_result
            ):
                st.session_state["bet_log"][i]["result"] = normalized_result
                st.session_state["bet_log"][i]["profit"] = new_profit
                st.session_state["bet_log"][i]["stake"] = units
                st.session_state["bet_log"][i]["clv_diff"] = clv_diff
                st.session_state["bet_log"][i]["clv_result"] = clv_result
                changed = True

    if changed:
        save_bet_log()
        update_learning_from_results()

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
# AUTO-LOG TOP PLAYS
# =========================================================
# Duplicate auto-log block intentionally disabled.
# Active plays are already auto-logged earlier with:
# auto_logged_count = auto_log_active_plays(active_df)

# =========================================================
# SNAPSHOT SAVE (LOCK TAB DATA UNTIL NEXT REFRESH)
# =========================================================
try:
    snapshot_saved = False

    snapshot_top_df = pd.DataFrame()
    snapshot_active_df = pd.DataFrame()
    snapshot_watch_df = pd.DataFrame()
    snapshot_ai_df = pd.DataFrame()
    snapshot_parlay_df = pd.DataFrame()
    snapshot_best_row = None

    if "top_plays_df" in locals() and isinstance(top_plays_df, pd.DataFrame) and not top_plays_df.empty:
        snapshot_top_df = top_plays_df.copy()
    elif "active_df" in locals() and isinstance(active_df, pd.DataFrame) and not active_df.empty:
        snapshot_top_df = active_df.copy()
        sort_cols = [c for c in ["rank_score", "true_confidence"] if c in snapshot_top_df.columns]
        if sort_cols:
            snapshot_top_df = (
                snapshot_top_df
                .sort_values(by=sort_cols, ascending=[False] * len(sort_cols))
                .head(TOP_PLAYS_LIMIT)
                .reset_index(drop=True)
                .copy()
            )
        else:
            snapshot_top_df = snapshot_top_df.head(TOP_PLAYS_LIMIT).reset_index(drop=True).copy()

    if "active_df" in locals() and isinstance(active_df, pd.DataFrame) and not active_df.empty:
        snapshot_active_df = active_df.copy()

    if "watch_df" in locals() and isinstance(watch_df, pd.DataFrame) and not watch_df.empty:
        snapshot_watch_df = watch_df.copy()
    elif "watchlist_df" in locals() and isinstance(watchlist_df, pd.DataFrame) and not watchlist_df.empty:
        snapshot_watch_df = watchlist_df.copy()

    if "ai_slip_df" in locals() and isinstance(ai_slip_df, pd.DataFrame) and not ai_slip_df.empty:
        snapshot_ai_df = ai_slip_df.copy()
    elif "active_df" in locals() and isinstance(active_df, pd.DataFrame) and not active_df.empty:
        snapshot_ai_df = active_df.head(5).copy()

    if "parlay_df" in locals() and isinstance(parlay_df, pd.DataFrame) and not parlay_df.empty:
        snapshot_parlay_df = parlay_df.copy()

    if "best_row" in locals():
        if isinstance(best_row, pd.Series):
            snapshot_best_row = best_row.to_dict()
        elif isinstance(best_row, dict):
            snapshot_best_row = best_row.copy()

    has_any_snapshot_data = any(
        [
            isinstance(snapshot_top_df, pd.DataFrame) and not snapshot_top_df.empty,
            isinstance(snapshot_active_df, pd.DataFrame) and not snapshot_active_df.empty,
            isinstance(snapshot_watch_df, pd.DataFrame) and not snapshot_watch_df.empty,
            isinstance(snapshot_ai_df, pd.DataFrame) and not snapshot_ai_df.empty,
            isinstance(snapshot_parlay_df, pd.DataFrame) and not snapshot_parlay_df.empty,
            isinstance(snapshot_best_row, dict) and len(snapshot_best_row) > 0,
        ]
    )

    if has_any_snapshot_data:
        if isinstance(snapshot_top_df, pd.DataFrame) and not snapshot_top_df.empty:
            st.session_state["snapshot_top_plays_df"] = snapshot_top_df.copy()

        if isinstance(snapshot_active_df, pd.DataFrame) and not snapshot_active_df.empty:
            st.session_state["snapshot_active_df"] = snapshot_active_df.copy()
            st.session_state["snapshot_plays_df"] = snapshot_active_df.copy()

        if isinstance(snapshot_watch_df, pd.DataFrame) and not snapshot_watch_df.empty:
            st.session_state["snapshot_watchlist_df"] = snapshot_watch_df.copy()

        if isinstance(snapshot_ai_df, pd.DataFrame) and not snapshot_ai_df.empty:
            st.session_state["snapshot_ai_slip_df"] = snapshot_ai_df.copy()

        if isinstance(snapshot_parlay_df, pd.DataFrame) and not snapshot_parlay_df.empty:
            st.session_state["snapshot_parlay_df"] = snapshot_parlay_df.copy()

        if isinstance(snapshot_best_row, dict) and snapshot_best_row:
            st.session_state["snapshot_best_row"] = snapshot_best_row.copy()

        st.session_state["snapshot_generated_at"] = pd.Timestamp.now().strftime(
            "%Y-%m-%d %I:%M:%S %p"
        )
        st.session_state["snapshot_refresh_id"] = int(st.session_state.get("snapshot_refresh_id", 0)) + 1

        save_tab_snapshots_to_disk()
        snapshot_saved = True

except Exception as e:
    st.warning(f"Snapshot save error: {e}")

# =========================================================
# SAVE GENERATED PLAY SNAPSHOTS
# =========================================================
try:
    if isinstance(plays_df, pd.DataFrame):
        if not plays_df.empty:
            persist_generated_play_snapshots(plays_df)
        else:
            existing_snapshot_df = st.session_state.get("snapshot_plays_df", pd.DataFrame())
            if not isinstance(existing_snapshot_df, pd.DataFrame) or existing_snapshot_df.empty:
                clear_generated_play_snapshots()
    else:
        existing_snapshot_df = st.session_state.get("snapshot_plays_df", pd.DataFrame())
        if not isinstance(existing_snapshot_df, pd.DataFrame):
            clear_generated_play_snapshots()
except Exception as e:
    st.session_state["snapshot_save_error"] = str(e)

# =========================================================
# RENDER HELPERS (FIXED - REQUIRED FOR UI)
# =========================================================

def render_mobile_or_table(df, best_first=True):
    """
    Safe renderer for mobile card UI OR fallback table
    """
    if df is None or df.empty:
        st.info("No plays available.")
        return

    df = df.copy()

    # Sort if needed
    if best_first and "true_confidence" in df.columns:
        df = df.sort_values(by="true_confidence", ascending=False)

    for _, row in df.iterrows():
        game = row.get("game", "N/A")
        pick = row.get("selection", "N/A")
        market = row.get("market", "N/A")
        book = row.get("book", "N/A")
        odds = row.get("odds", "N/A")
        edge = row.get("edge", 0)
        true_conf = row.get("true_confidence", 0)
        units = row.get("units", 0)

        st.markdown(f"""
        <div style="
            background-color:#1e1e1e;
            padding:12px;
            border-radius:10px;
            margin-bottom:10px;
            border:1px solid #333;
        ">
            <b>{game}</b><br>
            Pick: {pick}<br>
            Market: {market}<br>
            Book: {book} | Odds: {odds}<br>
            Edge: {edge:.2f}% | True Confidence: {true_conf:.1f}% | Units: {units}
        </div>
        """, unsafe_allow_html=True)


def render_parlay_card(parlay_obj):
    """
    Safe parlay card renderer
    """
    if not parlay_obj:
        st.info("No parlay available.")
        return

    legs = parlay_obj.get("legs", [])
    total_odds = parlay_obj.get("odds", "N/A")
    total_units = parlay_obj.get("units", 0)

    st.markdown(f"""
    <div style="
        background-color:#111827;
        padding:15px;
        border-radius:12px;
        border:1px solid #333;
        margin-bottom:15px;
    ">
        <h4>🔥 AI Parlay</h4>
        <b>Odds:</b> {total_odds}<br>
        <b>Units:</b> {total_units}<br><br>
    """, unsafe_allow_html=True)

    for leg in legs:
        st.markdown(f"""
        • {leg.get("game","")} → {leg.get("selection","")}
        """)

    st.markdown("</div>", unsafe_allow_html=True)
# =========================================================
# UI RENDER HELPERS (TOP PLAYS / WATCHLIST / AI SLIP SAFE)
# =========================================================
def _safe_display_odds(value):
    try:
        if value is None or str(value).strip() == "":
            return "N/A"
        val = int(float(value))
        return f"+{val}" if val > 0 else str(val)
    except Exception:
        return str(value) if value is not None else "N/A"


def _safe_display_pct(value, decimals=1):
    try:
        return f"{float(value):.{decimals}f}%"
    except Exception:
        return "0.0%"


def _safe_display_num(value, decimals=2):
    try:
        return f"{float(value):.{decimals}f}"
    except Exception:
        return f"{0:.{decimals}f}"


def render_pick_card(row_dict):
    matchup = str(row_dict.get("game", "Unknown Matchup"))
    pick = str(row_dict.get("selection", "N/A"))
    market = str(row_dict.get("market", "N/A"))
    book = str(row_dict.get("best_book", "N/A"))
    odds = _safe_display_odds(row_dict.get("best_price", row_dict.get("odds", "N/A")))
    edge = _safe_display_pct(row_dict.get("edge", 0), 2)
    true_conf = _safe_display_pct(row_dict.get("true_confidence", 0), 1)
    units = _safe_display_num(row_dict.get("units", 0), 2)
    note = str(row_dict.get("sportsdata_note", "")).strip() or "No additional note available."

    st.markdown(
        f"""
        <div style="
            background: white;
            border: 1px solid rgba(0,0,0,0.08);
            border-radius: 18px;
            padding: 18px 18px 14px 18px;
            margin-bottom: 14px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        ">
            <div style="font-size: 1.05rem; font-weight: 700; margin-bottom: 10

# =========================================================
# TOP PLAYS (CLEAN + SAFE HTML + SNAPSHOT)
# =========================================================
if nav == "Top Plays":
    st.header("🎯 Top Plays")
    st.caption("Up to 10 qualified plays only. No filler.")

    current_api_mode = st.session_state.get("api_mode", "idle")

    if len(get_effective_odds_games()) == 0:
        if current_api_mode == "waiting_reset":
            reset_expected = str(st.session_state.get("odds_api_reset_expected", "")).strip()
            if reset_expected:
                st.warning(f"The Odds API is waiting for reset. Expected reset around {reset_expected}.")
            else:
                st.warning("The Odds API is waiting for reset.")
        else:
            st.warning("Press 'Refresh Live Odds' in the sidebar to load live odds.")
    else:
        snapshot_top_df = st.session_state.get("snapshot_top_plays_df", pd.DataFrame())

        if snapshot_top_df is not None and not snapshot_top_df.empty:

            top_df = snapshot_top_df.copy()

            # =========================
            # SUMMARY METRICS
            # =========================
            try:
                avg_edge = round(top_df["edge"].astype(float).mean(), 2)
            except:
                avg_edge = 0

            try:
                avg_conf = round(top_df["true_confidence"].astype(float).mean(), 1)
            except:
                avg_conf = 0

            st.markdown(f"""
            **Top Plays Shown:** {len(top_df)}  
            **Avg Edge:** {avg_edge}  
            **Avg True Confidence:** {avg_conf}
            """)

            st.markdown("---")

            # =========================
            # CARD RENDER
            # =========================
            for _, row in top_df.iterrows():

                game = row.get("game", "N/A")
                pick = row.get("selection", "N/A")
                market = row.get("market", "N/A")
                book = row.get("book", "N/A")
                odds = row.get("odds", "N/A")

                try:
                    edge = f'{float(row.get("edge", 0)):.2f}%'
                except:
                    edge = "0.00%"

                try:
                    conf = f'{float(row.get("true_confidence", 0)):.1f}%'
                except:
                    conf = "0.0%"

                try:
                    units = f'{float(row.get("units", 0)):.2f}'
                except:
                    units = "0.00"

                st.markdown(f'''
                <div style="
                    background: #111;
                    padding: 14px;
                    border-radius: 14px;
                    margin-bottom: 12px;
                    border: 1px solid #333;
                    color: white;
                    font-size: 14px;
                    line-height: 1.4;
                ">
                    <div style="font-weight:600; font-size:15px; margin-bottom:6px;">
                        {game}
                    </div>

                    <div><b>Pick:</b> {pick}</div>
                    <div><b>Market:</b> {market}</div>
                    <div><b>Book:</b> {book} | <b>Odds:</b> {odds}</div>

                    <div style="margin-top:6px; font-size:13px; color:#ccc;">
                        Edge: {edge} | True Conf: {conf} | Units: {units}
                    </div>
                </div>
                ''', unsafe_allow_html=True)

        else:
            st.info("No qualified plays yet. Try refreshing odds.")

# =========================================================
# WATCHLIST (CLEAN + SAFE RENDER)
# =========================================================
elif nav == "Watchlist":
    st.header("👀 Watchlist")
    st.caption("Near-qualified plays worth monitoring.")

    current_api_mode = st.session_state.get("api_mode", "idle")
    snapshot_watchlist_df = st.session_state.get("snapshot_watchlist_df", pd.DataFrame())
    snapshot_last_updated = str(st.session_state.get("snapshot_last_updated", "")).strip()

    if len(get_effective_odds_games()) == 0 and snapshot_watchlist_df.empty:
        if current_api_mode == "waiting_reset":
            reset_expected = str(st.session_state.get("odds_api_reset_expected", "")).strip()
            if reset_expected:
                st.warning(f"The Odds API is waiting for reset. Expected reset around {reset_expected}.")
            else:
                st.warning("The Odds API is waiting for reset.")
        else:
            st.warning("Press 'Refresh Live Odds' in the sidebar to load live odds.")

    elif snapshot_watchlist_df.empty:
        st.info("No Watchlist plays currently qualified.")
        if snapshot_last_updated:
            st.caption(f"Last saved play snapshot: {snapshot_last_updated}")

    else:
        watch_df = snapshot_watchlist_df.copy().reset_index(drop=True)

        # =========================
        # SAFE DEFAULTS
        # =========================
        for col in ["game","selection","market","best_book","odds"]:
            if col not in watch_df.columns:
                watch_df[col] = ""

        for col in ["edge","true_confidence","units"]:
            if col not in watch_df.columns:
                watch_df[col] = 0.0

        watch_df["edge"] = pd.to_numeric(watch_df["edge"], errors="coerce").fillna(0.0)
        watch_df["true_confidence"] = pd.to_numeric(watch_df["true_confidence"], errors="coerce").fillna(0.0)
        watch_df["units"] = pd.to_numeric(watch_df["units"], errors="coerce").fillna(0.0)

        # =========================
        # HEADER INFO
        # =========================
        if snapshot_last_updated:
            st.caption(f"Last saved play snapshot: {snapshot_last_updated}")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Watchlist Plays", len(watch_df))

        with col2:
            avg_edge = round(float(watch_df["edge"].mean()), 2) if not watch_df.empty else 0
            st.metric("Avg Edge", avg_edge)

        with col3:
            avg_conf = round(float(watch_df["true_confidence"].mean()), 1) if not watch_df.empty else 0
            st.metric("Avg True Confidence", avg_conf)

        st.markdown("---")

        # =========================
        # SAFE CARD RENDER
        # =========================
        for _, row in watch_df.iterrows():

            game = str(row.get("game", "")).strip() or "Unknown Matchup"
            pick = str(row.get("selection", "")).strip() or "N/A"
            market = str(row.get("market", "")).strip() or "N/A"
            book = str(row.get("best_book", "")).strip() or "N/A"
            odds = str(row.get("odds", "N/A"))

            try:
                edge = "{:.2f}".format(float(row.get("edge", 0.0)))
            except:
                edge = "0.00"

            try:
                conf = "{:.1f}".format(float(row.get("true_confidence", 0.0)))
            except:
                conf = "0.0"

            try:
                units = "{:.2f}".format(float(row.get("units", 0.0)))
            except:
                units = "0.00"

            st.markdown(
                f'''
<div style="
    background:#111827;
    border:1px solid #374151;
    border-radius:16px;
    padding:16px;
    margin-bottom:14px;
    color:#f9fafb;
">
    <div style="font-weight:600;font-size:15px;margin-bottom:6px;">
        {game}
    </div>

    <div><b>Pick:</b> {pick}</div>
    <div><b>Market:</b> {market}</div>
    <div><b>Book:</b> {book} | <b>Odds:</b> {odds}</div>

    <div style="margin-top:6px;color:#d1d5db;">
        Edge: {edge}% | True Conf: {conf}% | Units: {units}
    </div>
</div>
                ''',
                unsafe_allow_html=True
            )

# =========================================================
# WATCHLIST
# =========================================================
elif nav == "Watchlist":
    st.header("👀 Watchlist")
    st.caption("Near-qualified plays worth monitoring.")

    current_api_mode = st.session_state.get("api_mode", "idle")
    persisted_plays_df = get_persisted_plays_df()
    snapshot_watchlist_df = st.session_state.get("snapshot_watchlist_df", pd.DataFrame())
    snapshot_last_updated = str(st.session_state.get("snapshot_last_updated", "")).strip()

    if snapshot_watchlist_df.empty and not persisted_plays_df.empty:
        try:
            restored_df = persisted_plays_df.copy()
            restored_df = normalize_dataframe_for_selected_sport(restored_df, get_selected_sport())
            restored_df = recalculate_play_metrics(restored_df)

            if "status" not in restored_df.columns:
                restored_df["status"] = ""
            if "log_category" not in restored_df.columns:
                restored_df["log_category"] = ""

            restored_df["status"] = restored_df["status"].fillna("").astype(str).str.strip()
            restored_df["log_category"] = restored_df["log_category"].fillna("").astype(str).str.strip()

            snapshot_watchlist_df = restored_df[
                restored_df["status"].isin(["Watchlist", "Watch"])
            ].copy()

            if snapshot_watchlist_df.empty:
                remaining_df = restored_df.copy()
                snapshot_watchlist_df = remaining_df.sort_values(
                    by=["true_confidence", "edge", "books_seen"],
                    ascending=[False, False, False],
                ).head(WATCHLIST_LIMIT).copy()

                if not snapshot_watchlist_df.empty:
                    snapshot_watchlist_df["status"] = "Watchlist"
                    snapshot_watchlist_df["log_category"] = "Watchlist"

            st.session_state["snapshot_watchlist_df"] = snapshot_watchlist_df.copy()
            snapshot_last_updated = str(st.session_state.get("snapshot_last_updated", "")).strip()
        except Exception:
            pass

    if len(get_effective_odds_games()) == 0 and persisted_plays_df.empty and snapshot_watchlist_df.empty:
        if current_api_mode == "waiting_reset":
            reset_expected = str(st.session_state.get("odds_api_reset_expected", "")).strip()
            if reset_expected:
                st.warning(f"The Odds API is waiting for reset. Expected reset around {reset_expected}.")
            else:
                st.warning("The Odds API is waiting for reset.")
        else:
            st.warning("Press 'Refresh Live Odds' in the sidebar to load live odds.")

    elif snapshot_watchlist_df.empty:
        st.info("No Watchlist plays currently qualified.")
        if snapshot_last_updated:
            st.caption(f"Last saved play snapshot: {snapshot_last_updated}")

    else:
        watch_df = snapshot_watchlist_df.copy().reset_index(drop=True)

        defaults_map = {
            "game": "",
            "selection": "",
            "market": "",
            "best_book": "",
            "odds": "",
            "edge": 0.0,
            "true_confidence": 0.0,
            "units": 0.0,
            "status": "Watchlist",
            "books_seen": 0,
            "context_score": 0.0,
            "score": 0.0,
            "rank_score": 0.0,
            "implied_prob": 0.0,
            "true_prob": 0.0,
            "sportsdata_note": "",
            "injury_flag": "",
            "lineup_flag": "",
            "log_category": "Watchlist",
        }

        for col, default_val in defaults_map.items():
            if col not in watch_df.columns:
                watch_df[col] = default_val

        numeric_cols = [
            "true_confidence",
            "edge",
            "units",
            "books_seen",
            "context_score",
            "score",
            "rank_score",
            "implied_prob",
            "true_prob",
        ]
        for col in numeric_cols:
            watch_df[col] = pd.to_numeric(watch_df[col], errors="coerce").fillna(0.0)

        watch_df["status"] = watch_df["status"].fillna("Watchlist").astype(str).str.strip()
        watch_df["log_category"] = watch_df["log_category"].fillna("Watchlist").astype(str).str.strip()

        watch_df = watch_df.sort_values(
            by=["true_confidence", "edge", "books_seen"],
            ascending=[False, False, False],
        ).reset_index(drop=True)

        if snapshot_last_updated:
            st.caption(f"Last saved play snapshot: {snapshot_last_updated}")

        metric_col_1, metric_col_2, metric_col_3 = st.columns(3)
        with metric_col_1:
            st.metric("Watchlist Plays", len(watch_df))
        with metric_col_2:
            avg_edge = round(float(watch_df["edge"].mean()), 2) if not watch_df.empty else 0.0
            st.metric("Avg Edge", avg_edge)
        with metric_col_3:
            avg_conf = round(float(watch_df["true_confidence"].mean()), 1) if not watch_df.empty else 0.0
            st.metric("Avg True Confidence", avg_conf)

        st.markdown("---")

        for _, row in watch_df.iterrows():
            game = str(row.get("game", "")).strip() or "Unknown Matchup"
            selection = str(row.get("selection", "")).strip() or "N/A"
            market = str(row.get("market", "")).strip() or "N/A"
            best_book = str(row.get("best_book", "")).strip() or "N/A"
            odds = row.get("odds", "")
            edge = float(safe_float(row.get("edge", 0.0), 0.0))
            true_conf = float(safe_float(row.get("true_confidence", 0.0), 0.0))
            units = float(safe_float(row.get("units", 0.0), 0.0))

            st.markdown(
                f"""
<div style="background:#111827;border:1px solid #374151;border-radius:16px;padding:16px 18px;margin-bottom:14px;">
    <div style="font-size:1.15rem;font-weight:700;color:#f9fafb;margin-bottom:10px;">{game}</div>
    <div style="font-size:1rem;color:#e5e7eb;margin-bottom:8px;"><strong>Pick:</strong> {selection}</div>
    <div style="font-size:1rem;color:#e5e7eb;margin-bottom:8px;"><strong>Market:</strong> {market}</div>
    <div style="font-size:1rem;color:#e5e7eb;margin-bottom:8px;"><strong>Book:</strong> {best_book} | <strong>Odds:</strong> {odds}</div>
    <div style="font-size:1rem;color:#e5e7eb;">
        <strong>Edge:</strong> {edge:.2f}% |
        <strong>True Confidence:</strong> {true_conf:.1f}% |
        <strong>Units:</strong> {units:.2f}
    </div>
</div>
                """,
                unsafe_allow_html=True,
            )

# =========================================================
# BET LOG
# =========================================================
if nav == "Bet Log":
    st.header("🧾 Bet Log")

    sync_manual_results_into_bet_log()

    def _safe_num(series_or_value, default=0.0):
        try:
            if isinstance(series_or_value, pd.Series):
                return pd.to_numeric(series_or_value, errors="coerce").fillna(default)
            return float(series_or_value)
        except Exception:
            return default

    def _normalize_result_text(value):
        raw = str(value).strip().title()
        if raw in ["Win", "Loss", "Push", "Pending"]:
            return raw
        if raw == "Won":
            return "Win"
        if raw == "Lost":
            return "Loss"
        return "Pending"

    def _normalize_bet_type(value):
        raw = str(value).strip().lower()

        if raw in ["moneyline", "ml", "h2h"]:
            return "Moneyline"
        if raw in ["spread", "spreads"]:
            return "Spread"
        if raw in ["total", "totals"]:
            return "Total"
        if raw.startswith("prop"):
            return "Prop"
        if raw == "parlay":
            return "Parlay"

        return str(value).strip().title() if str(value).strip() else "Other"

    def _normalize_category(value):
        raw = str(value).strip()
        if not raw:
            return "Uncategorized"

        parts = [p.strip() for p in raw.split("|") if str(p).strip()]
        if not parts:
            return "Uncategorized"

        for label in ["Top Plays", "AI Picks", "AI Parlays", "Watchlist", "Manual"]:
            if label in parts:
                return label

        for label in ["Top Play", "AI Slip", "AI Parlay", "Watchlist", "Manual"]:
            if label in parts:
                mapping = {
                    "Top Play": "Top Plays",
                    "AI Slip": "AI Picks",
                    "AI Parlay": "AI Parlays",
                    "Watchlist": "Watchlist",
                    "Manual": "Manual",
                }
                return mapping[label]

        return parts[0]

    def _extract_date_only(value):
        raw = str(value).strip()
        if not raw:
            return ""
        if "T" in raw:
            return raw.split("T")[0]
        if " " in raw:
            return raw.split(" ")[0]
        return raw[:10]

    def _american_profit_from_stake(odds, stake):
        odds_val = american_to_int(odds)
        stake = safe_float(stake, 0.0)

        if odds_val is None or stake <= 0:
            return 0.0

        if odds_val > 0:
            return round(stake * (odds_val / 100.0), 2)

        return round(stake * (100.0 / abs(odds_val)), 2)

    def _sim_profit(row, mode_label, stake_amount):
        result = _normalize_result_text(row.get("result", "Pending"))
        odds = row.get("odds", "")
        units_val = safe_float(row.get("units", 1.0), 1.0)

        if mode_label == "Per Unit":
            stake = units_val * safe_float(stake_amount, 0.0)
        else:
            stake = safe_float(stake_amount, 0.0)

        if result == "Win":
            return _american_profit_from_stake(odds, stake)
        if result == "Loss":
            return round(-stake, 2)
        return 0.0

    def _sim_stake(row, mode_label, stake_amount):
        units_val = safe_float(row.get("units", 1.0), 1.0)
        if mode_label == "Per Unit":
            return round(units_val * safe_float(stake_amount, 0.0), 2)
        return round(safe_float(stake_amount, 0.0), 2)

    def _build_group_summary(df, group_col):
        if df.empty or group_col not in df.columns:
            return pd.DataFrame()

        grouped_rows = []
        for group_name, grp in df.groupby(group_col):
            picks = len(grp)
            wins = int((grp["result_clean"] == "Win").sum())
            losses = int((grp["result_clean"] == "Loss").sum())
            pushes = int((grp["result_clean"] == "Push").sum())

            total_units_profit = round(_safe_num(grp["profit"], 0.0).sum(), 2)
            total_sim_profit = round(_safe_num(grp["sim_profit"], 0.0).sum(), 2)
            total_sim_staked = round(_safe_num(grp["sim_stake"], 0.0).sum(), 2)

            decision_count = wins + losses
            win_rate = round((wins / decision_count * 100.0), 1) if decision_count > 0 else 0.0
            roi = round((total_sim_profit / total_sim_staked * 100.0), 2) if total_sim_staked > 0 else 0.0

            grouped_rows.append(
                {
                    group_col: group_name,
                    "Picks": picks,
                    "Wins": wins,
                    "Losses": losses,
                    "Pushes": pushes,
                    "Win Rate %": win_rate,
                    "Units P&L": total_units_profit,
                    "Sim $ P&L": total_sim_profit,
                    "Sim ROI %": roi,
                }
            )

        out = pd.DataFrame(grouped_rows)
        if not out.empty and "Sim $ P&L" in out.columns:
            out = out.sort_values(by=["Sim $ P&L", "Win Rate %"], ascending=[False, False])

        return out.reset_index(drop=True)

    selected_sport = get_selected_sport()

    latest_bet_log = st.session_state.get("bet_log", [])
    if not isinstance(latest_bet_log, list):
        latest_bet_log = []

    full_log_df = pd.DataFrame(latest_bet_log)

    if full_log_df.empty:
        st.info("No bets logged yet.")
    else:
        log_df = full_log_df.copy()

        for col in REQUIRED_BET_LOG_COLUMNS:
            if col not in log_df.columns:
                log_df[col] = None

        if "sport" not in log_df.columns:
            log_df["sport"] = ""

        log_df["sport"] = log_df["sport"].fillna("").astype(str).str.strip().str.upper()
        log_df["sport"] = log_df["sport"].replace("", selected_sport)
        log_df = log_df[log_df["sport"] == selected_sport].copy()

        if log_df.empty:
            st.info(f"No bets logged yet for {selected_sport}.")
        else:
            numeric_cols = [
                "units",
                "profit",
                "implied_prob",
                "true_prob",
                "implied_probability",
                "true_probability",
                "true_confidence",
                "edge",
                "clv_diff",
                "stake",
                "sim_stake",
                "sim_profit",
            ]
            for col in numeric_cols:
                if col in log_df.columns:
                    log_df[col] = pd.to_numeric(log_df[col], errors="coerce")

            text_cols = [
                "market",
                "log_category",
                "timestamp",
                "result",
                "odds",
                "selection",
                "game",
                "play_id",
                "consensus",
                "clv_result",
            ]
            for col in text_cols:
                if col in log_df.columns:
                    log_df[col] = (
                        log_df[col]
                        .fillna("")
                        .astype(str)
                        .replace({"nan": "", "None": "", "none": ""})
                        .str.strip()
                    )

            if "units" not in log_df.columns:
                log_df["units"] = 1.0
            if "stake" not in log_df.columns:
                log_df["stake"] = log_df["units"] if "units" in log_df.columns else 1.0
            if "profit" not in log_df.columns:
                log_df["profit"] = 0.0
            if "market" not in log_df.columns:
                log_df["market"] = ""
            if "log_category" not in log_df.columns:
                log_df["log_category"] = ""
            if "timestamp" not in log_df.columns:
                log_df["timestamp"] = ""

            log_df["units"] = pd.to_numeric(log_df["units"], errors="coerce").fillna(0.0).round(2)
            log_df["stake"] = pd.to_numeric(log_df["stake"], errors="coerce").fillna(log_df["units"]).round(2)
            log_df["profit"] = pd.to_numeric(log_df["profit"], errors="coerce").fillna(0.0).round(2)

            for pct_col, rounding in [
                ("implied_prob", 2),
                ("true_prob", 2),
                ("implied_probability", 2),
                ("true_probability", 2),
                ("true_confidence", 1),
                ("edge", 2),
                ("clv_diff", 2),
            ]:
                if pct_col in log_df.columns:
                    log_df[pct_col] = pd.to_numeric(log_df[pct_col], errors="coerce").round(rounding)

            log_df["result_clean"] = log_df["result"].apply(_normalize_result_text)
            log_df["bet_type"] = log_df["market"].apply(_normalize_bet_type)
            log_df["category_clean"] = log_df["log_category"].apply(_normalize_category)
            log_df["date_only"] = log_df["timestamp"].apply(_extract_date_only)

            st.subheader(f"📊 ROI Dashboard ({selected_sport})")
            roi_df = build_roi_dashboard(log_df)

            if roi_df.empty:
                st.info("No settled bets yet.")
            else:
                st.dataframe(roi_df, use_container_width=True, hide_index=True)

            st.subheader("💵 Stake Simulator")

            sim_col1, sim_col2 = st.columns([1.2, 1.4])

            with sim_col1:
                stake_mode = st.radio(
                    "Simulation Mode",
                    ["Flat Bet", "Per Unit"],
                    horizontal=True,
                    key=f"stake_mode_toggle_{selected_sport}",
                )

            with sim_col2:
                preset_choice = st.radio(
                    "Stake Size",
                    ["$5", "$10", "$25", "$50", "Custom"],
                    horizontal=True,
                    key=f"stake_size_toggle_{selected_sport}",
                )

            if preset_choice == "Custom":
                custom_stake = st.number_input(
                    "Custom Stake Amount",
                    min_value=1.0,
                    max_value=10000.0,
                    value=10.0,
                    step=1.0,
                    key=f"custom_stake_amount_{selected_sport}",
                )
                selected_stake_amount = float(custom_stake)
            else:
                selected_stake_amount = float(str(preset_choice).replace("$", ""))

            st.caption(
                f"Viewing simulated dollar results for **{selected_sport}** using **{stake_mode}** mode at **${selected_stake_amount:.2f}**."
            )

            log_df["sim_stake"] = log_df.apply(
                lambda r: _sim_stake(r, stake_mode, selected_stake_amount),
                axis=1,
            )
            log_df["sim_profit"] = log_df.apply(
                lambda r: _sim_profit(r, stake_mode, selected_stake_amount),
                axis=1,
            )

            settled_df = log_df[log_df["result_clean"].isin(["Win", "Loss", "Push"])].copy()

            total_picks = int(len(log_df))
            settled_count = int(len(settled_df))
            wins = int((settled_df["result_clean"] == "Win").sum())
            losses = int((settled_df["result_clean"] == "Loss").sum())
            pushes = int((settled_df["result_clean"] == "Push").sum())
            total_units_profit = round(_safe_num(settled_df["profit"], 0.0).sum(), 2)
            total_sim_profit = round(_safe_num(settled_df["sim_profit"], 0.0).sum(), 2)
            total_sim_staked = round(_safe_num(settled_df["sim_stake"], 0.0).sum(), 2)

            decision_count = wins + losses
            overall_win_rate = round((wins / decision_count * 100.0), 1) if decision_count > 0 else 0.0
            overall_roi = round((total_sim_profit / total_sim_staked * 100.0), 2) if total_sim_staked > 0 else 0.0

            sum_col1, sum_col2, sum_col3, sum_col4 = st.columns(4)
            sum_col1.metric("Logged Bets", total_picks)
            sum_col2.metric("Settled", settled_count)
            sum_col3.metric("Win Rate", f"{overall_win_rate:.1f}%")
            sum_col4.metric("Units P&L", f"{total_units_profit:+.2f}u")

            sum_col5, sum_col6 = st.columns(2)
            sum_col5.metric("Simulated $ P&L", f"${total_sim_profit:+,.2f}")
            sum_col6.metric("Simulated ROI", f"{overall_roi:.2f}%")

            st.subheader("📈 Performance Breakdowns")

            filter_col1, filter_col2, filter_col3 = st.columns(3)

            all_bet_types = ["All"] + sorted(
                [str(x).strip() for x in log_df["bet_type"].dropna().unique() if str(x).strip()]
            )
            all_categories = ["All"] + sorted(
                [str(x).strip() for x in log_df["category_clean"].dropna().unique() if str(x).strip()]
            )
            all_dates = sorted(
                [str(x).strip() for x in log_df["date_only"].dropna().unique() if str(x).strip()],
                reverse=True,
            )

            with filter_col1:
                dashboard_type_filter = st.selectbox(
                    "Bet Type Filter",
                    all_bet_types,
                    index=0,
                    key=f"dashboard_type_filter_{selected_sport}",
                )

            with filter_col2:
                dashboard_category_filter = st.selectbox(
                    "Category Filter",
                    all_categories,
                    index=0,
                    key=f"dashboard_category_filter_{selected_sport}",
                )

            with filter_col3:
                dashboard_date_mode = st.selectbox(
                    "Date Range",
                    ["All", "Last 7", "Last 14", "Last 30", "Single Date"],
                    index=0,
                    key=f"dashboard_date_mode_{selected_sport}",
                )

            filtered_dashboard_df = settled_df.copy()

            if dashboard_type_filter != "All":
                filtered_dashboard_df = filtered_dashboard_df[
                    filtered_dashboard_df["bet_type"].astype(str) == dashboard_type_filter
                ].copy()

            if dashboard_category_filter != "All":
                filtered_dashboard_df = filtered_dashboard_df[
                    filtered_dashboard_df["category_clean"].astype(str) == dashboard_category_filter
                ].copy()

            if dashboard_date_mode == "Single Date":
                single_date_choice = st.selectbox(
                    "Choose Date",
                    ["All"] + all_dates,
                    index=0,
                    key=f"dashboard_single_date_choice_{selected_sport}",
                )
                if single_date_choice != "All":
                    filtered_dashboard_df = filtered_dashboard_df[
                        filtered_dashboard_df["date_only"].astype(str) == single_date_choice
                    ].copy()
            elif dashboard_date_mode in ["Last 7", "Last 14", "Last 30"]:
                days_map = {"Last 7": 7, "Last 14": 14, "Last 30": 30}
                day_cutoff = pd.Timestamp.now().normalize() - pd.Timedelta(days=days_map[dashboard_date_mode] - 1)

                filtered_dashboard_df["timestamp_dt_tmp"] = pd.to_datetime(
                    filtered_dashboard_df["timestamp"],
                    errors="coerce",
                )
                filtered_dashboard_df = filtered_dashboard_df[
                    filtered_dashboard_df["timestamp_dt_tmp"] >= day_cutoff
                ].copy()
                filtered_dashboard_df = filtered_dashboard_df.drop(columns=["timestamp_dt_tmp"], errors="ignore")

            f_total_picks = int(len(filtered_dashboard_df))
            f_wins = int((filtered_dashboard_df["result_clean"] == "Win").sum()) if not filtered_dashboard_df.empty else 0
            f_losses = int((filtered_dashboard_df["result_clean"] == "Loss").sum()) if not filtered_dashboard_df.empty else 0
            f_pushes = int((filtered_dashboard_df["result_clean"] == "Push").sum()) if not filtered_dashboard_df.empty else 0
            f_units_profit = round(_safe_num(filtered_dashboard_df["profit"], 0.0).sum(), 2) if not filtered_dashboard_df.empty else 0.0
            f_sim_profit = round(_safe_num(filtered_dashboard_df["sim_profit"], 0.0).sum(), 2) if not filtered_dashboard_df.empty else 0.0
            f_sim_staked = round(_safe_num(filtered_dashboard_df["sim_stake"], 0.0).sum(), 2) if not filtered_dashboard_df.empty else 0.0

            f_decision_count = f_wins + f_losses
            f_win_rate = round((f_wins / f_decision_count * 100.0), 1) if f_decision_count > 0 else 0.0
            f_roi = round((f_sim_profit / f_sim_staked * 100.0), 2) if f_sim_staked > 0 else 0.0

            card_col1, card_col2, card_col3, card_col4 = st.columns(4)
            card_col1.metric("Filtered Picks", f_total_picks)
            card_col2.metric("Filtered Win Rate", f"{f_win_rate:.1f}%")
            card_col3.metric("Filtered Units P&L", f"{f_units_profit:+.2f}u")
            card_col4.metric("Filtered Sim $ P&L", f"${f_sim_profit:+,.2f}")

            card_col5, card_col6, card_col7 = st.columns(3)
            card_col5.metric("Filtered ROI", f"{f_roi:.2f}%")
            card_col6.metric("Wins / Losses", f"{f_wins}-{f_losses}")
            card_col7.metric("Pushes", f_pushes)

            filtered_by_type_df = _build_group_summary(filtered_dashboard_df, "bet_type")
            filtered_by_category_df = _build_group_summary(filtered_dashboard_df, "category_clean")
            filtered_by_date_df = _build_group_summary(filtered_dashboard_df, "date_only")

            type_card_rows = []
            if not filtered_by_type_df.empty:
                for _, row in filtered_by_type_df.iterrows():
                    type_card_rows.append(
                        f"""
                        <div style="
                            border:1px solid #e5e7eb;
                            border-radius:16px;
                            padding:14px 16px;
                            margin-bottom:10px;">
                            <div style="font-size:18px;font-weight:700;margin-bottom:8px;">{row['bet_type']}</div>
                            <div style="font-size:30px;font-weight:800;">{row['Win Rate %']:.0f}%</div>
                            <div style="font-size:16px;opacity:0.8;">{int(row['Wins'])}W - {int(row['Losses'])}L - {int(row['Pushes'])}P ({int(row['Picks'])} picks)</div>
                            <div style="margin-top:8px;font-size:22px;font-weight:700;">${row['Sim $ P&L']:+,.2f}</div>
                            <div style="font-size:16px;font-weight:600;">{row['Sim ROI %']:.2f}% ROI</div>
                        </div>
                        """
                    )

            visual_tab1, visual_tab2 = st.tabs(["By Bet Type Cards", "Filtered Tables"])

            with visual_tab1:
                if type_card_rows:
                    for html in type_card_rows:
                        st.markdown(html, unsafe_allow_html=True)
                else:
                    st.info("No filtered bet-type data yet.")

            with visual_tab2:
                ft_col1, ft_col2 = st.columns(2)

                with ft_col1:
                    if filtered_by_category_df.empty:
                        st.info("No category summary yet.")
                    else:
                        st.markdown("**By Category**")
                        st.dataframe(filtered_by_category_df, use_container_width=True, hide_index=True)

                with ft_col2:
                    if filtered_by_type_df.empty:
                        st.info("No bet-type summary yet.")
                    else:
                        st.markdown("**By Bet Type**")
                        st.dataframe(filtered_by_type_df, use_container_width=True, hide_index=True)

                    if filtered_by_date_df.empty:
                        st.info("No date summary yet.")
                    else:
                        filtered_by_date_df = filtered_by_date_df.sort_values(by="date_only", ascending=False)
                        st.markdown("**By Date**")
                        st.dataframe(filtered_by_date_df, use_container_width=True, hide_index=True)

            st.subheader("💰 Bankroll Simulator")

            if filtered_dashboard_df.empty:
                st.info("No settled bets available for simulation.")
            else:
                sim_col1, sim_col2 = st.columns([2, 1])

                with sim_col1:
                    bankroll_stake_mode = st.selectbox(
                        "Stake Mode",
                        ["Flat Bet ($5)", "Flat Bet ($10)", "Flat Bet ($25)", "Flat Bet ($50)", "Custom"],
                        index=1,
                        key=f"bankroll_stake_mode_{selected_sport}",
                    )

                with sim_col2:
                    if bankroll_stake_mode == "Custom":
                        custom_bankroll_stake = st.number_input(
                            "Custom Stake ($)",
                            min_value=1.0,
                            max_value=1000.0,
                            value=10.0,
                            step=1.0,
                            key=f"bankroll_custom_stake_{selected_sport}",
                        )
                    else:
                        custom_bankroll_stake = None

                if bankroll_stake_mode == "Flat Bet ($5)":
                    stake_size = 5.0
                elif bankroll_stake_mode == "Flat Bet ($10)":
                    stake_size = 10.0
                elif bankroll_stake_mode == "Flat Bet ($25)":
                    stake_size = 25.0
                elif bankroll_stake_mode == "Flat Bet ($50)":
                    stake_size = 50.0
                else:
                    stake_size = float(custom_bankroll_stake or 10.0)

                sim_df = filtered_dashboard_df.copy()
                sim_df["odds_num"] = sim_df["odds"].apply(american_to_int)

                sim_profit_list = []
                cumulative_profit = []
                running_total = 0.0

                for _, row in sim_df.iterrows():
                    odds = row.get("odds_num")
                    result = str(row.get("result_clean", "")).lower()
                    profit = 0.0

                    if odds is not None:
                        if result == "win":
                            if odds > 0:
                                profit = stake_size * (odds / 100.0)
                            else:
                                profit = stake_size / (abs(odds) / 100.0)
                        elif result == "loss":
                            profit = -stake_size
                        elif result == "push":
                            profit = 0.0

                    running_total += profit
                    sim_profit_list.append(profit)
                    cumulative_profit.append(running_total)

                sim_df["sim_profit_recalc"] = sim_profit_list
                sim_df["bankroll_curve"] = cumulative_profit

                total_profit_sim = round(sum(sim_profit_list), 2)
                total_bets_sim = len(sim_profit_list)
                total_staked_sim = round(stake_size * total_bets_sim, 2)
                roi_sim = round((total_profit_sim / total_staked_sim * 100.0), 2) if total_staked_sim > 0 else 0.0

                sim_stat1, sim_stat2, sim_stat3 = st.columns(3)
                sim_stat1.metric("Stake Size", f"${stake_size:.2f}")
                sim_stat2.metric("Total Profit", f"${total_profit_sim:+,.2f}")
                sim_stat3.metric("ROI", f"{roi_sim:.2f}%")

                chart_df = sim_df.copy().reset_index(drop=True)

                if "bankroll_curve" in chart_df.columns:
                    chart_df["Bet #"] = chart_df.index + 1

                    import matplotlib.pyplot as plt

                    plt.figure()
                    plt.plot(chart_df["Bet #"], chart_df["bankroll_curve"])
                    plt.xlabel("Bet Number")
                    plt.ylabel("Profit ($)")
                    plt.title(f"{selected_sport} Bankroll Growth")

                    st.pyplot(plt)

                with st.expander("View Simulation Data"):
                    show_cols = [
                        c for c in [
                            "selection",
                            "game",
                            "odds",
                            "result_clean",
                            "sim_profit_recalc",
                            "bankroll_curve",
                        ] if c in sim_df.columns
                    ]
                    st.dataframe(
                        sim_df[show_cols],
                        use_container_width=True,
                        hide_index=True,
                    )

            st.subheader(f"📋 Full Bet Log ({selected_sport})")

            display_cols = [
                c for c in [
                    "sport",
                    "timestamp",
                    "game",
                    "market",
                    "selection",
                    "odds",
                    "units",
                    "stake",
                    "profit",
                    "sim_stake",
                    "sim_profit",
                    "implied_prob",
                    "true_prob",
                    "true_confidence",
                    "edge",
                    "books_seen",
                    "consensus",
                    "result",
                    "category_clean",
                    "clv_diff",
                    "clv_result",
                    "play_id",
                ] if c in log_df.columns
            ]

            display_df = log_df[display_cols].copy()
            st.dataframe(display_df, use_container_width=True, hide_index=True)

            st.subheader("✍️ Update Results")

            selectable_labels = []
            selectable_map = {}

            latest_bet_log = st.session_state.get("bet_log", [])
            if not isinstance(latest_bet_log, list):
                latest_bet_log = []

            for _, r in log_df.iterrows():
                pid = str(r.get("play_id", "")).strip()
                selection = str(r.get("selection", "")).strip()
                game = str(r.get("game", "")).strip()
                market = str(r.get("market", "")).strip().lower()

                if not pid:
                    continue

                short_pid = pid[:8]
                market_label = f" [{market}]" if market else ""
                label = f"{selection}{market_label} • {game} • ID {short_pid}"

                suffix = 2
                base_label = label
                while label in selectable_map:
                    label = f"{base_label} ({suffix})"
                    suffix += 1

                selectable_labels.append(label)
                selectable_map[label] = pid

            if selectable_labels:
                selected_label = st.selectbox(
                    "Select Bet",
                    selectable_labels,
                    key=f"update_result_select_{selected_sport}",
                )
                selected_id = selectable_map[selected_label]
                selected_base_id = get_base_play_id(selected_id)

                existing_result = "Pending"

                for bet in latest_bet_log:
                    pid = str(bet.get("play_id", "")).strip()
                    if not pid:
                        continue

                    bet_sport = str(bet.get("sport", "")).strip().upper()
                    if bet_sport and bet_sport != selected_sport:
                        continue

                    if pid == selected_id or get_base_play_id(pid) == selected_base_id:
                        existing_result = normalize_result_value(bet.get("result", "Pending"))
                        break

                result_options = ["Pending", "Win", "Loss", "Push"]
                if existing_result not in result_options:
                    existing_result = "Pending"

                result_choice = st.selectbox(
                    "Result",
                    result_options,
                    index=result_options.index(existing_result),
                    key=f"bet_result_choice_{selected_sport}",
                )

                if st.button("Save Result", key=f"save_result_button_{selected_sport}"):
                    normalized_choice = normalize_result_value(result_choice)
                    updated_any = False

                    refreshed_bet_log = st.session_state.get("bet_log", [])
                    if not isinstance(refreshed_bet_log, list):
                        refreshed_bet_log = []

                    for idx, bet in enumerate(refreshed_bet_log):
                        pid = str(bet.get("play_id", "")).strip()
                        if not pid:
                            continue

                        bet_sport = str(bet.get("sport", "")).strip().upper()
                        if bet_sport and bet_sport != selected_sport:
                            continue

                        if pid == selected_id or get_base_play_id(pid) == selected_base_id:
                            refreshed_bet_log[idx]["result"] = normalized_choice
                            updated_any = True

                            if normalized_choice == "Pending":
                                refreshed_bet_log[idx]["profit"] = 0.0
                            else:
                                try:
                                    odds_val = american_to_int(str(refreshed_bet_log[idx].get("odds", "")).strip())
                                except Exception:
                                    odds_val = None

                                try:
                                    stake_units = float(
                                        refreshed_bet_log[idx].get(
                                            "stake",
                                            refreshed_bet_log[idx].get("units", 1.0),
                                        )
                                    )
                                except Exception:
                                    stake_units = 1.0

                                if stake_units <= 0:
                                    stake_units = 1.0

                                profit_val = 0.0
                                if normalized_choice == "Win":
                                    if odds_val is not None:
                                        if odds_val > 0:
                                            profit_val = round(stake_units * (odds_val / 100.0), 4)
                                        elif odds_val < 0:
                                            profit_val = round(stake_units * (100.0 / abs(odds_val)), 4)
                                        else:
                                            profit_val = round(stake_units, 4)
                                    else:
                                        profit_val = round(stake_units, 4)
                                elif normalized_choice == "Loss":
                                    profit_val = round(-stake_units, 4)
                                elif normalized_choice == "Push":
                                    profit_val = 0.0

                                refreshed_bet_log[idx]["profit"] = profit_val

                    st.session_state["bet_log"] = refreshed_bet_log
                    st.session_state.setdefault("manual_results", {})
                    st.session_state["manual_results"][selected_id] = normalized_choice

                    save_bet_log()

                    try:
                        reloaded = load_bet_log()
                        if isinstance(reloaded, list):
                            st.session_state["bet_log"] = reloaded
                    except Exception:
                        pass

                    if updated_any:
                        st.success("Bet result saved successfully.")
                        st.rerun()
                    else:
                        st.warning("Could not find that bet to update.")
            else:
                st.info("No selectable bets found.")

    st.subheader("➕ Add Manual Bet")

    with st.expander("Add Manual Bet Entry", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            game_input = st.text_input("Game (e.g. LAL @ BOS)", key="manual_game_input")
            market_input = st.selectbox(
                "Market",
                ["moneyline", "spread", "total", "prop"],
                index=0,
                key="manual_market_input",
            )
            selection_input = st.text_input(
                "Selection (e.g. Lakers -3.5 or Over 221.5)",
                key="manual_selection_input",
            )

        with col2:
            odds_input = st.text_input(
                "Odds (American, e.g. -110 or +150)",
                key="manual_odds_input",
            )
            units_input = st.number_input(
                "Units",
                min_value=0.1,
                max_value=10.0,
                value=1.0,
                step=0.1,
                key="manual_units_input",
            )
            confidence_input = st.selectbox(
                "Confidence",
                ["Low", "Medium", "High"],
                index=1,
                key="manual_confidence_input",
            )

        if st.button("Add Bet", key="manual_add_bet_button"):
            game_clean = str(game_input).strip()
            market_clean = str(market_input).strip().lower()
            selection_clean = str(selection_input).strip()
            odds_clean = str(odds_input).strip()
            units = float(units_input)
            confidence = str(confidence_input).strip()

            odds_int = american_to_int(odds_clean)

            if not game_clean or not selection_clean or not odds_clean:
                st.warning("Please fill in Game, Selection, and Odds.")
            elif odds_int is None:
                st.warning("Odds must be valid American odds like -110 or +150.")
            else:
                new_play_id = hashlib.md5(
                    f"{selected_sport}|{game_clean}|{market_clean}|{selection_clean}|{odds_clean}|{time.time()}".encode()
                ).hexdigest()

                open_line_val = extract_line_from_selection(selection_clean)

                implied_prob_val = None
                try:
                    if odds_int > 0:
                        implied_prob_val = round(100.0 / (odds_int + 100.0) * 100.0, 2)
                    elif odds_int < 0:
                        implied_prob_val = round(abs(odds_int) / (abs(odds_int) + 100.0) * 100.0, 2)
                except Exception:
                    implied_prob_val = None

                new = {
                    "play_id": new_play_id,
                    "sport": selected_sport,
                    "game": game_clean,
                    "market": market_clean,
                    "selection": selection_clean,
                    "odds": odds_int,
                    "implied_prob": implied_prob_val,
                    "true_prob": None,
                    "implied_probability": implied_prob_val,
                    "true_probability": None,
                    "edge": None,
                    "play_type": classify_play_type(
                        {
                            "market": market_clean,
                            "selection": selection_clean,
                            "category": "Manual",
                        }
                    ),
                    "primary_category": "Manual",
                    "category": "Manual",
                    "units": round(float(units), 2),
                    "stake": round(float(units), 2),
                    "confidence": confidence,
                    "true_confidence": None,
                    "books_seen": None,
                    "consensus": None,
                    "result": "Pending",
                    "profit": 0.0,
                    "mode": TEST_MODE,
                    "log_category": "Manual",
                    "timestamp": datetime.now().isoformat(),
                    "open_odds": odds_int,
                    "open_line": open_line_val,
                    "closing_odds": None,
                    "closing_line": None,
                    "clv_diff": None,
                    "clv_result": None,
                }

                st.session_state.setdefault("bet_log", [])
                st.session_state["bet_log"].append(new)
                save_bet_log()

                try:
                    reloaded = load_bet_log()
                    if isinstance(reloaded, list):
                        st.session_state["bet_log"] = reloaded
                except Exception:
                    pass

                st.success(f"Manual {selected_sport} bet added successfully.")
                st.rerun()



    # =========================================================
    # DEFAULT LEARNING STATE
    # =========================================================
    learning_state = get_learning_state_for_sport(selected_sport)

    default_learning_state = {
        "weights": {
            "true_probability": 0.30,
            "price_edge": 0.25,
            "market_signal": 0.15,
            "matchup_quality": 0.15,
            "historical_performance": 0.15,
        },
        "category_thresholds": {
            "Top Plays": 0.030,
            "AI Picks": 0.035,
            "AI Parlays": 0.050,
            "Watchlist": 0.020,
        },
        "category_min_samples": 8,
        "play_type_stats": {},
        "category_stats": {},
        "bad_play_type_flags": {},
        "last_learning_refresh": "",
        "learning_notes": [],
        "accelerated_learning_mode": False,
    }

    for key, value in default_learning_state.items():
        if key not in learning_state:
            learning_state[key] = value

    if not isinstance(learning_state.get("weights"), dict):
        learning_state["weights"] = default_learning_state["weights"].copy()

    if not isinstance(learning_state.get("category_thresholds"), dict):
        learning_state["category_thresholds"] = default_learning_state["category_thresholds"].copy()

    if not isinstance(learning_state.get("play_type_stats"), dict):
        learning_state["play_type_stats"] = {}

    if not isinstance(learning_state.get("category_stats"), dict):
        learning_state["category_stats"] = {}

    if not isinstance(learning_state.get("bad_play_type_flags"), dict):
        learning_state["bad_play_type_flags"] = {}

    if not isinstance(learning_state.get("learning_notes"), list):
        learning_state["learning_notes"] = []

    # =========================================================
    # HELPER FUNCTIONS
    # =========================================================
    def _clamp(v, low, high):
        return max(low, min(high, v))

    def _safe_pct_threshold(raw_value, fallback_decimal):
        try:
            raw = float(raw_value)
        except Exception:
            raw = float(fallback_decimal)

        if raw > 1:
            raw = raw / 100.0

        return raw

    def _status_from_threshold(current_decimal, base_decimal):
        if current_decimal > base_decimal + 0.0001:
            return "Tightened"
        if current_decimal < base_decimal - 0.0001:
            return "Loosened"
        return "Base"

    def _learning_stage(sample_size):
        if sample_size >= 8:
            return "Trusted"
        if sample_size >= 5:
            return "Active"
        if sample_size >= 3:
            return "Probation"
        return "Collecting"

    # =========================================================
    # LEARNING CONTROLS
    # =========================================================
    learning_col1, learning_col2, learning_col3 = st.columns(3)

    with learning_col1:
        learning_enabled = st.toggle(
            "Enable Controlled Learning",
            value=True,
            key=f"learning_enabled_{selected_sport}",
        )

    with learning_col2:
        auto_filter_bad_types = st.toggle(
            "Auto-Filter Bad Play Types",
            value=True,
            key=f"auto_filter_bad_types_{selected_sport}",
        )

    with learning_col3:
        min_sample_size = st.number_input(
            "Minimum Samples Before Learning Applies",
            min_value=3,
            max_value=50,
            value=int(learning_state.get("category_min_samples", 8)),
            step=1,
            key=f"learning_min_samples_{selected_sport}",
        )

    learning_state["category_min_samples"] = int(min_sample_size)
    min_samples = int(learning_state.get("category_min_samples", 8) or 8)

    st.caption(
        "Controlled learning adjusts filtering logic and play-type confidence only. "
        "It does not auto-increase bet sizing."
    )

# =========================================================
# SETTLED PERFORMANCE SUMMARY + LEARNING UPDATE (SAFE FIX)
# =========================================================

# Ensure settled_df ALWAYS exists
settled_df = pd.DataFrame()

selected_sport = get_selected_sport()

try:
    sport_bet_log = get_bet_log_for_sport(selected_sport)

    if sport_bet_log:
        settled_df = pd.DataFrame(sport_bet_log).copy()

        # Ensure required columns exist
        required_cols = [
            "result",
            "profit",
            "market",
            "log_category",
            "true_confidence",
            "edge",
            "play_type",
        ]
        for col in required_cols:
            if col not in settled_df.columns:
                settled_df[col] = ""

        settled_df["result_clean"] = (
            settled_df["result"]
            .astype(str)
            .str.strip()
            .str.lower()
            .replace(
                {
                    "won": "win",
                    "lost": "loss",
                    "pushes": "push",
                }
            )
        )

        settled_df["profit_num"] = pd.to_numeric(
            settled_df["profit"], errors="coerce"
        ).fillna(0.0)

        settled_df["true_conf_num"] = pd.to_numeric(
            settled_df["true_confidence"], errors="coerce"
        ).fillna(0.0)

        settled_df["edge_num"] = pd.to_numeric(
            settled_df["edge"], errors="coerce"
        ).fillna(0.0)

        settled_df["market_clean"] = (
            settled_df["market"].astype(str).str.strip().str.lower()
        )

        settled_df["category_clean"] = (
            settled_df["log_category"].astype(str).str.strip()
        )

        settled_df["play_type_clean"] = (
            settled_df["play_type"].astype(str).str.strip().str.lower()
        )

        settled_df = settled_df[
            settled_df["result_clean"].isin(["win", "loss", "push"])
        ].copy()

except Exception as e:
    st.warning(f"Performance summary error: {e}")
    settled_df = pd.DataFrame()

# ---------------------------------------------------------
# SAFE TOTALS
# ---------------------------------------------------------
if not settled_df.empty:
    total_settled_bets = int(len(settled_df))
    total_wins = int((settled_df["result_clean"] == "win").sum())
    total_losses = int((settled_df["result_clean"] == "loss").sum())
    total_pushes = int((settled_df["result_clean"] == "push").sum())
    total_profit = float(settled_df["profit_num"].sum())

    decision_count = total_wins + total_losses
    overall_win_rate = (
        (total_wins / decision_count) * 100.0 if decision_count > 0 else 0.0
    )
else:
    total_settled_bets = 0
    total_wins = 0
    total_losses = 0
    total_pushes = 0
    total_profit = 0.0
    overall_win_rate = 0.0

# ---------------------------------------------------------
# DISPLAY
# ---------------------------------------------------------
st.markdown("### 📊 Performance Summary")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Bets", total_settled_bets)
col2.metric("Wins", total_wins)
col3.metric("Losses", total_losses)
col4.metric("Profit", f"{total_profit:.2f}")

# ---------------------------------------------------------
# SAFE DEFAULTS
# ---------------------------------------------------------
learning_state = get_active_learning_state(selected_sport)

default_thresholds = {
    "Top Plays": 0.03,
    "AI Picks": 0.035,
    "AI Parlays": 0.05,
    "Watchlist": 0.02,
    "Manual": 0.03,
}

if "default_learning_state" in globals() and isinstance(default_learning_state, dict):
    default_thresholds = dict(
        default_learning_state.get("category_thresholds", default_thresholds)
    )

learning_enabled = bool(st.session_state.get("learning_enabled", True))
auto_filter_bad_types = bool(st.session_state.get("auto_filter_bad_types", True))
min_samples = int(st.session_state.get("min_samples", 8))
min_sample_size = int(st.session_state.get("min_sample_size", min_samples))

def _safe_pct_threshold(value, fallback):
    try:
        return float(clamp(float(value), 0.015, 0.075))
    except Exception:
        return float(fallback)

def _clamp(value, low, high):
    try:
        return max(low, min(high, float(value)))
    except Exception:
        return low

def _learning_stage(sample_size):
    sample_size = int(sample_size)
    if sample_size >= 8:
        return "Trusted"
    if sample_size >= 5:
        return "Active"
    if sample_size >= min_samples:
        return "Probation"
    return "Collecting"

# ---------------------------------------------------------
# BUILD PLAY TYPE STATS
# ---------------------------------------------------------
play_type_stats = {}
category_stats = {}
learning_notes = []
bad_play_type_flags = {}

if not settled_df.empty:
    play_type_grouped = (
        settled_df.groupby("play_type_clean", dropna=False)
        .agg(
            bets=("result_clean", "count"),
            wins=("result_clean", lambda s: (s == "win").sum()),
            losses=("result_clean", lambda s: (s == "loss").sum()),
            pushes=("result_clean", lambda s: (s == "push").sum()),
            profit=("profit_num", "sum"),
            avg_true_conf=("true_conf_num", "mean"),
            avg_edge=("edge_num", "mean"),
        )
        .reset_index()
    )

    for _, row in play_type_grouped.iterrows():
        play_type_name = str(row["play_type_clean"]).strip()
        if not play_type_name:
            play_type_name = "unknown"

        bets = int(row["bets"])
        wins = int(row["wins"])
        losses = int(row["losses"])
        pushes = int(row["pushes"])
        profit = float(row["profit"])
        avg_true_conf = (
            float(row["avg_true_conf"]) if pd.notna(row["avg_true_conf"]) else 0.0
        )
        avg_edge = float(row["avg_edge"]) if pd.notna(row["avg_edge"]) else 0.0

        decision_count = wins + losses
        win_rate = (wins / decision_count * 100.0) if decision_count > 0 else 0.0
        roi_per_bet = (profit / bets) if bets > 0 else 0.0
        stage = _learning_stage(bets)

        play_type_stats[play_type_name] = {
            "sample_size": bets,
            "wins": wins,
            "losses": losses,
            "pushes": pushes,
            "profit": round(profit, 4),
            "win_rate": round(win_rate, 2),
            "roi_per_bet": round(roi_per_bet, 4),
            "avg_true_conf": round(avg_true_conf, 2),
            "avg_edge": round(avg_edge, 2),
            "stage": stage,
        }

        if auto_filter_bad_types:
            if bets >= 8:
                if profit <= -2 and win_rate < 45:
                    bad_play_type_flags[play_type_name] = {
                        "is_filtered": True,
                        "reason": f"Trusted filter: poor results ({wins}-{losses}-{pushes}, profit {round(profit, 2)})",
                    }
                elif profit >= 2 and win_rate >= 55:
                    bad_play_type_flags[play_type_name] = {
                        "is_filtered": False,
                        "reason": f"Trusted positive results ({wins}-{losses}-{pushes}, profit {round(profit, 2)})",
                    }
                else:
                    bad_play_type_flags[play_type_name] = {
                        "is_filtered": False,
                        "reason": "Trusted but neutral",
                    }

            elif bets >= 5:
                if profit <= -1.5 and win_rate < 45:
                    bad_play_type_flags[play_type_name] = {
                        "is_filtered": True,
                        "reason": f"Active filter: weak results ({wins}-{losses}-{pushes}, profit {round(profit, 2)})",
                    }
                elif profit >= 1.5 and win_rate >= 55:
                    bad_play_type_flags[play_type_name] = {
                        "is_filtered": False,
                        "reason": f"Active positive results ({wins}-{losses}-{pushes}, profit {round(profit, 2)})",
                    }
                else:
                    bad_play_type_flags[play_type_name] = {
                        "is_filtered": False,
                        "reason": "Active review",
                    }

            elif bets >= min_samples:
                if profit <= -1 and win_rate < 40:
                    bad_play_type_flags[play_type_name] = {
                        "is_filtered": True,
                        "reason": f"Probation filter: very weak start ({wins}-{losses}-{pushes}, profit {round(profit, 2)})",
                    }
                elif profit >= 1 and win_rate >= 60:
                    bad_play_type_flags[play_type_name] = {
                        "is_filtered": False,
                        "reason": f"Probation positive start ({wins}-{losses}-{pushes}, profit {round(profit, 2)})",
                    }
                else:
                    bad_play_type_flags[play_type_name] = {
                        "is_filtered": False,
                        "reason": "Probation / still evaluating",
                    }
            else:
                bad_play_type_flags[play_type_name] = {
                    "is_filtered": False,
                    "reason": f"Collecting data ({bets}/{min_samples})",
                }

    category_grouped = (
        settled_df.groupby("category_clean", dropna=False)
        .agg(
            bets=("result_clean", "count"),
            wins=("result_clean", lambda s: (s == "win").sum()),
            losses=("result_clean", lambda s: (s == "loss").sum()),
            pushes=("result_clean", lambda s: (s == "push").sum()),
            profit=("profit_num", "sum"),
            avg_true_conf=("true_conf_num", "mean"),
            avg_edge=("edge_num", "mean"),
        )
        .reset_index()
    )

    for _, row in category_grouped.iterrows():
        category_name = str(row["category_clean"]).strip()
        if not category_name:
            continue

        bets = int(row["bets"])
        wins = int(row["wins"])
        losses = int(row["losses"])
        pushes = int(row["pushes"])
        profit = float(row["profit"])
        avg_true_conf = (
            float(row["avg_true_conf"]) if pd.notna(row["avg_true_conf"]) else 0.0
        )
        avg_edge = float(row["avg_edge"]) if pd.notna(row["avg_edge"]) else 0.0

        decision_count = wins + losses
        win_rate = (wins / decision_count * 100.0) if decision_count > 0 else 0.0
        roi_per_bet = (profit / bets) if bets > 0 else 0.0
        stage = _learning_stage(bets)

        category_stats[category_name] = {
            "sample_size": bets,
            "wins": wins,
            "losses": losses,
            "pushes": pushes,
            "profit": round(profit, 4),
            "win_rate": round(win_rate, 2),
            "roi_per_bet": round(roi_per_bet, 4),
            "avg_true_conf": round(avg_true_conf, 2),
            "avg_edge": round(avg_edge, 2),
            "stage": stage,
        }

# ---------------------------------------------------------
# CONTROLLED LEARNING ADJUSTMENTS
# ---------------------------------------------------------
adjusted_category_thresholds = dict(learning_state.get("category_thresholds", {}))

for cat_name, fallback_val in default_thresholds.items():
    adjusted_category_thresholds[cat_name] = _safe_pct_threshold(
        adjusted_category_thresholds.get(cat_name, fallback_val),
        fallback_val,
    )

if learning_enabled:
    for category_name, stats in category_stats.items():
        if category_name not in adjusted_category_thresholds:
            continue

        current_threshold = float(adjusted_category_thresholds.get(category_name, 0.03))
        bets = int(stats.get("sample_size", 0))
        profit = float(stats.get("profit", 0.0))
        win_rate = float(stats.get("win_rate", 0.0))
        avg_true_conf = float(stats.get("avg_true_conf", 0.0))

        if bets >= min_samples:
            if bets >= 8:
                if profit <= -2 and win_rate < 45:
                    current_threshold += 0.0030
                elif profit >= 2 and win_rate >= 55 and avg_true_conf >= 65:
                    current_threshold -= 0.0030

            elif bets >= 5:
                if profit <= -1.5 and win_rate < 45:
                    current_threshold += 0.0025
                elif profit >= 1.5 and win_rate >= 55 and avg_true_conf >= 65:
                    current_threshold -= 0.0025

            elif bets >= 3:
                if profit <= -1 and win_rate < 40:
                    current_threshold += 0.0015
                elif profit >= 1 and win_rate >= 60 and avg_true_conf >= 68:
                    current_threshold -= 0.0015

            adjusted_category_thresholds[category_name] = _clamp(
                current_threshold,
                0.015,
                0.075,
            )

    if total_settled_bets >= int(min_samples):
        if overall_win_rate >= 55.0 and total_profit > 0:
            learning_notes.append(
                "Recent settled performance is positive. Slightly loosening qualified category thresholds."
            )
        elif overall_win_rate < 45.0 or total_profit < 0:
            learning_notes.append(
                "Recent settled performance is weak. Tightening category thresholds for better selectivity."
            )

learning_state["play_type_stats"] = play_type_stats
learning_state["category_stats"] = category_stats
learning_state["bad_play_type_flags"] = (
    bad_play_type_flags if auto_filter_bad_types else {}
)
learning_state["category_thresholds"] = adjusted_category_thresholds
learning_state["learning_notes"] = learning_notes
learning_state["last_learning_refresh"] = pd.Timestamp.now().strftime(
    "%Y-%m-%d %I:%M:%S %p"
)
learning_state["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
learning_state["category_min_samples"] = min_samples
learning_state["accelerated_learning_mode"] = min_samples <= 3

save_learning_state_for_sport(learning_state, selected_sport)

# =========================================================
# TRUE PROBABILITY EMPHASIS
# =========================================================
st.markdown("#### 🎯 True Probability Emphasis")
st.caption(
    "True probability remains the largest learning weight so the engine does not overreact "
    "to short-term variance from weaker play types or categories."
)

safe_weights = learning_state.get("weights", {})
if not isinstance(safe_weights, dict):
    safe_weights = {}

weight_df = pd.DataFrame(
    [
        {
            "Factor": "True Probability",
            "Weight": float(safe_weights.get("true_probability", 0.30)),
        },
        {
            "Factor": "Price Edge",
            "Weight": float(safe_weights.get("price_edge", 0.25)),
        },
        {
            "Factor": "Market Signal",
            "Weight": float(safe_weights.get("market_signal", 0.15)),
        },
        {
            "Factor": "Matchup Quality",
            "Weight": float(safe_weights.get("matchup_quality", 0.15)),
        },
        {
            "Factor": "Historical Performance",
            "Weight": float(safe_weights.get("historical_performance", 0.15)),
        },
    ]
)

st.dataframe(weight_df, use_container_width=True, hide_index=True)

# =========================================================
# CATEGORY THRESHOLDS TABLE
# =========================================================
st.markdown("#### 📊 Adaptive Category Thresholds")

threshold_rows = []
default_threshold_map = {
    "Top Plays": 0.03,
    "AI Picks": 0.035,
    "AI Parlays": 0.05,
    "Watchlist": 0.02,
}

for category_name in ["Top Plays", "AI Picks", "AI Parlays", "Watchlist"]:
    current_threshold = float(adjusted_category_thresholds.get(category_name, default_threshold_map.get(category_name, 0.03)))
    base_threshold = float(default_threshold_map.get(category_name, 0.03))

    if current_threshold < base_threshold:
        status_label = "Looser"
    elif current_threshold > base_threshold:
        status_label = "Tighter"
    else:
        status_label = "Base"

    threshold_rows.append(
        {
            "Category": category_name,
            "Threshold": round(current_threshold, 4),
            "Status": status_label,
        }
    )

threshold_df = pd.DataFrame(threshold_rows)
st.dataframe(threshold_df, use_container_width=True, hide_index=True)



# =========================================================
# PLAY TYPE PERFORMANCE / AUTO-FILTER STATUS
# =========================================================
st.markdown("### Play Type Performance / Auto-Filter Status")

if play_type_stats:
    pt_rows = []
    for play_type_name, stats in play_type_stats.items():
        flag_info = learning_state.get("bad_play_type_flags", {}).get(play_type_name, {})
        pt_rows.append(
            {
                "Play Type": play_type_name if play_type_name else "Unknown",
                "Stage": stats.get("stage", "Collecting"),
                "Bets": stats.get("sample_size", 0),
                "Wins": stats.get("wins", 0),
                "Losses": stats.get("losses", 0),
                "Pushes": stats.get("pushes", 0),
                "Profit": stats.get("profit", 0.0),
                "Win Rate %": stats.get("win_rate", 0.0),
                "Avg True Conf": stats.get("avg_true_conf", 0.0),
                "Avg Edge %": stats.get("avg_edge", 0.0),
                "Filtered": "Yes" if flag_info.get("is_filtered", False) else "No",
                "Reason": flag_info.get("reason", ""),
            }
        )

    pt_df = pd.DataFrame(pt_rows).sort_values(
        by=["Filtered", "Profit", "Win Rate %"],
        ascending=[False, False, False],
    )
    st.dataframe(pt_df, use_container_width=True, hide_index=True)
else:
    st.info(
        f"No graded {selected_sport} bet history yet. The self-learning engine will activate after enough settled bets."
    )

# =========================================================
# CATEGORY PERFORMANCE SNAPSHOT
# =========================================================
st.markdown("### Category Performance Snapshot")

if category_stats:
    cat_rows = []
    for category_name, stats in category_stats.items():
        cat_rows.append(
            {
                "Category": category_name if category_name else "Unknown",
                "Stage": stats.get("stage", "Collecting"),
                "Bets": stats.get("sample_size", 0),
                "Wins": stats.get("wins", 0),
                "Losses": stats.get("losses", 0),
                "Pushes": stats.get("pushes", 0),
                "Profit": stats.get("profit", 0.0),
                "Win Rate %": stats.get("win_rate", 0.0),
                "Avg True Conf": stats.get("avg_true_conf", 0.0),
                "Avg Edge %": stats.get("avg_edge", 0.0),
            }
        )

    cat_df = pd.DataFrame(cat_rows).sort_values(
        by=["Profit", "Win Rate %"],
        ascending=[False, False],
    )
    st.dataframe(cat_df, use_container_width=True, hide_index=True)
else:
    st.info(f"No settled {selected_sport} category data yet.")

# =========================================================
# CLV LEARNING NOTES
# =========================================================
st.markdown("### CLV Learning Notes")
st.caption(
    f"Accelerated Learning Mode for {selected_sport} starts with probation-stage learning after 3 settled bets, "
    "becomes active around 5, and trusted around 8. Early adjustments stay small to reduce overreaction."
)

# =========================================================
# ENGINE READINESS
# =========================================================
st.markdown("### Engine Readiness")

if len(settled_df) < min_samples:
    st.warning(f"{selected_sport} learning engine is collecting data (need {min_samples}+ settled bets).")
elif len(settled_df) < 5:
    st.info(f"{selected_sport} Accelerated Learning Mode is in probation stage.")
elif len(settled_df) < 8:
    st.info(f"{selected_sport} Accelerated Learning Mode is active.")
else:
    st.success(f"{selected_sport} Accelerated Learning Mode is fully active.")
