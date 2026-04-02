# =========================================================
# IMPORTS + API CONFIG (CLEAN MASTER BLOCK)
# =========================================================
import os
import json
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
# MULTI-SPORT STATE + HELPERS
# =========================================================
SUPPORTED_SPORTS = {
    "NBA": {
        "sport_key": "basketball_nba",
        "sportsdata_slug": "nba",
    },
    "NHL": {
        "sport_key": "icehockey_nhl",
        "sportsdata_slug": "nhl",
    },
    "MLB": {
        "sport_key": "baseball_mlb",
        "sportsdata_slug": "mlb",
    },
    "WNBA": {
        "sport_key": "basketball_wnba",
        "sportsdata_slug": "wnba",
    },
}

DEFAULT_SPORT = "NBA"

if "selected_sport" not in st.session_state:
    st.session_state["selected_sport"] = DEFAULT_SPORT

if "learning_state_by_sport" not in st.session_state:
    st.session_state["learning_state_by_sport"] = {}

if "odds_api_games_by_sport" not in st.session_state:
    st.session_state["odds_api_games_by_sport"] = {}

if "last_successful_odds_games_by_sport" not in st.session_state:
    st.session_state["last_successful_odds_games_by_sport"] = {}

if "api_mode_by_sport" not in st.session_state:
    st.session_state["api_mode_by_sport"] = {}

if "last_api_pull_epoch_by_sport" not in st.session_state:
    st.session_state["last_api_pull_epoch_by_sport"] = {}

if "odds_api_reset_expected_by_sport" not in st.session_state:
    st.session_state["odds_api_reset_expected_by_sport"] = {}

def get_selected_sport():
    raw = str(st.session_state.get("selected_sport", DEFAULT_SPORT)).strip().upper()
    if raw in SUPPORTED_SPORTS:
        return raw
    return DEFAULT_SPORT

# =========================================================
# GENERATED PLAY SNAPSHOT PERSISTENCE
# =========================================================
def _safe_df_snapshot(df):
    if isinstance(df, pd.DataFrame) and not df.empty:
        return df.copy()
    return pd.DataFrame()


def persist_generated_play_snapshots(plays_df: pd.DataFrame):
    """
    Persist generated plays + derived snapshots safely across reruns.
    This version is STABLE and will NOT wipe snapshots unintentionally.
    """

    if not isinstance(plays_df, pd.DataFrame):
        return

    if plays_df.empty:
        existing_snapshot_df = st.session_state.get("snapshot_plays_df", pd.DataFrame())
        if not isinstance(existing_snapshot_df, pd.DataFrame) or existing_snapshot_df.empty:
            clear_generated_play_snapshots()
        return

    working_df = plays_df.copy()

    selected_sport = get_selected_sport()

    try:
        working_df = attach_selected_sport_to_dataframe(working_df, selected_sport)
    except Exception:
        pass

    try:
        working_df = normalize_dataframe_for_selected_sport(working_df, selected_sport)
    except Exception:
        pass

    # -----------------------------------------------------
    # COLUMN SAFETY
    # -----------------------------------------------------
    if "status" not in working_df.columns:
        working_df["status"] = ""

    if "edge" not in working_df.columns:
        working_df["edge"] = 0.0

    if "true_confidence" not in working_df.columns:
        working_df["true_confidence"] = 0.0

    working_df["status"] = working_df["status"].astype(str).str.strip()
    working_df["edge"] = pd.to_numeric(working_df["edge"], errors="coerce").fillna(0.0)
    working_df["true_confidence"] = pd.to_numeric(
        working_df["true_confidence"], errors="coerce"
    ).fillna(0.0)

    # -----------------------------------------------------
    # SNAPSHOT CREATION (FIXED)
    # -----------------------------------------------------
    active_df = working_df[
        working_df["status"].astype(str).str.strip().str.lower() == "active"
    ].copy()

    watchlist_df = working_df[
        working_df["status"].astype(str).str.strip().str.lower() == "watchlist"
    ].copy()

    if not active_df.empty:
        active_df = active_df.sort_values(
            by=["true_confidence", "edge"],
            ascending=[False, False],
        ).reset_index(drop=True)

    if not watchlist_df.empty:
        watchlist_df = watchlist_df.sort_values(
            by=["true_confidence", "edge"],
            ascending=[False, False],
        ).reset_index(drop=True)

    top_limit = int(globals().get("TOP_PLAYS_LIMIT", 10))
    top_plays_df = active_df.head(top_limit).copy() if not active_df.empty else pd.DataFrame()

    # -----------------------------------------------------
    # SAVE TO SESSION STATE (CORE FIX)
    # -----------------------------------------------------
    st.session_state["plays_df"] = working_df.copy()
    st.session_state["snapshot_plays_df"] = working_df.copy()
    st.session_state["snapshot_active_df"] = active_df.copy()
    st.session_state["snapshot_watchlist_df"] = watchlist_df.copy()
    st.session_state["snapshot_top_plays_df"] = top_plays_df.copy()

    st.session_state["snapshot_last_updated"] = pd.Timestamp.now().strftime(
        "%Y-%m-%d %I:%M:%S %p"
    )


def get_persisted_plays_df():
    df = st.session_state.get("plays_df", pd.DataFrame())
    if isinstance(df, pd.DataFrame):
        return df.copy()
    return pd.DataFrame()


def clear_generated_play_snapshots():
    """
    Only clears snapshots when truly necessary.
    """
    st.session_state["plays_df"] = pd.DataFrame()
    st.session_state["snapshot_plays_df"] = pd.DataFrame()
    st.session_state["snapshot_active_df"] = pd.DataFrame()
    st.session_state["snapshot_watchlist_df"] = pd.DataFrame()
    st.session_state["snapshot_top_plays_df"] = pd.DataFrame()
    st.session_state["snapshot_last_updated"] = pd.Timestamp.now().strftime(
        "%Y-%m-%d %I:%M:%S %p"
    )

# =========================================================
# SPORT SELECTOR (V35 BLOCK 3)
# =========================================================

st.sidebar.markdown("### 🏆 Select Sport")

# Build dropdown options
sport_options = list(SUPPORTED_SPORTS.keys())

# Ensure current selection is valid
current_selected = st.session_state.get("selected_sport", DEFAULT_SPORT)
if current_selected not in sport_options:
    current_selected = DEFAULT_SPORT

# UI selector
selected_sport_ui = st.sidebar.selectbox(
    "Choose Sport",
    sport_options,
    index=sport_options.index(current_selected)
)

# Sync UI → session state
st.session_state["selected_sport"] = selected_sport_ui

# Always use helper (single source of truth)
CURRENT_SPORT = get_selected_sport()

# Convenience accessors (CRITICAL FOR NEXT BLOCKS)
CURRENT_SPORT_CONFIG = SUPPORTED_SPORTS.get(CURRENT_SPORT, {})

CURRENT_ODDS_KEY = CURRENT_SPORT_CONFIG.get("sport_key", "")
CURRENT_SPORTSDATA_SLUG = CURRENT_SPORT_CONFIG.get("sportsdata_slug", "")

# Debug (safe to remove later)
st.sidebar.caption(f"Active Sport: {CURRENT_SPORT}")

def get_sport_config(sport=None):
    sport_name = str(sport or get_selected_sport()).strip().upper()
    return SUPPORTED_SPORTS.get(sport_name, SUPPORTED_SPORTS[DEFAULT_SPORT])

def get_current_sport_key():
    return get_sport_config()["sport_key"]

def get_current_sportsdata_slug():
    return get_sport_config()["sportsdata_slug"]

def get_learning_state_for_sport(sport=None):
    sport_name = str(sport or get_selected_sport()).strip().upper()
    all_states = st.session_state.get("learning_state_by_sport", {})

    if sport_name not in all_states or not isinstance(all_states.get(sport_name), dict):
        all_states[sport_name] = {
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
            "last_update": None,
            "play_type_stats": {},
            "category_stats": {},
            "bad_play_type_flags": {},
            "category_min_samples": 3,
            "accelerated_learning_mode": True,
        }

    st.session_state["learning_state_by_sport"] = all_states
    return all_states[sport_name]

def save_learning_state_for_sport(state, sport=None):
    sport_name = str(sport or get_selected_sport()).strip().upper()
    all_states = st.session_state.get("learning_state_by_sport", {})
    all_states[sport_name] = state
    st.session_state["learning_state_by_sport"] = all_states

def get_odds_games_for_sport(sport=None):
    sport_name = str(sport or get_selected_sport()).strip().upper()
    return st.session_state.get("odds_api_games_by_sport", {}).get(sport_name, [])

def set_odds_games_for_sport(games, sport=None):
    sport_name = str(sport or get_selected_sport()).strip().upper()
    mapping = st.session_state.get("odds_api_games_by_sport", {})
    mapping[sport_name] = games
    st.session_state["odds_api_games_by_sport"] = mapping

def get_cached_games_for_sport(sport=None):
    sport_name = str(sport or get_selected_sport()).strip().upper()
    return st.session_state.get("last_successful_odds_games_by_sport", {}).get(sport_name, [])

def set_cached_games_for_sport(games, sport=None):
    sport_name = str(sport or get_selected_sport()).strip().upper()
    mapping = st.session_state.get("last_successful_odds_games_by_sport", {})
    mapping[sport_name] = games
    st.session_state["last_successful_odds_games_by_sport"] = mapping

def get_api_mode_for_sport(sport=None):
    sport_name = str(sport or get_selected_sport()).strip().upper()
    return st.session_state.get("api_mode_by_sport", {}).get(sport_name, "idle")

def set_api_mode_for_sport(mode, sport=None):
    sport_name = str(sport or get_selected_sport()).strip().upper()
    mapping = st.session_state.get("api_mode_by_sport", {})
    mapping[sport_name] = str(mode).strip().lower()
    st.session_state["api_mode_by_sport"] = mapping

def get_last_pull_epoch_for_sport(sport=None):
    sport_name = str(sport or get_selected_sport()).strip().upper()
    return float(st.session_state.get("last_api_pull_epoch_by_sport", {}).get(sport_name, 0) or 0)

def set_last_pull_epoch_for_sport(epoch_value, sport=None):
    sport_name = str(sport or get_selected_sport()).strip().upper()
    mapping = st.session_state.get("last_api_pull_epoch_by_sport", {})
    mapping[sport_name] = float(epoch_value or 0)
    st.session_state["last_api_pull_epoch_by_sport"] = mapping

def get_api_reset_expected_for_sport(sport=None):
    sport_name = str(sport or get_selected_sport()).strip().upper()
    return str(st.session_state.get("odds_api_reset_expected_by_sport", {}).get(sport_name, "")).strip()

def set_api_reset_expected_for_sport(value, sport=None):
    sport_name = str(sport or get_selected_sport()).strip().upper()
    mapping = st.session_state.get("odds_api_reset_expected_by_sport", {})
    mapping[sport_name] = str(value).strip()
    st.session_state["odds_api_reset_expected_by_sport"] = mapping

def get_effective_odds_games_for_sport(sport=None):
    live_games = get_odds_games_for_sport(sport)
    if live_games:
        return live_games
    return get_cached_games_for_sport(sport)

def get_bet_log_for_sport(sport=None):
    sport_name = str(sport or get_selected_sport()).strip().upper()
    rows = st.session_state.get("bet_log", [])
    return [
        row for row in rows
        if str(row.get("sport", "")).strip().upper() == sport_name
    ]
# =========================================================
# API CONFIG (REQUIRED)
# =========================================================

# -----------------------------
# SPORTS DATA IO CONFIG
# -----------------------------
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


# -----------------------------
# ODDS API CONFIG
# -----------------------------
def get_odds_api_key():
    possible_keys = [
        "ODDS_API_KEY",
        "THE_ODDS_API_KEY",
    ]
    for key_name in possible_keys:
        try:
            value = st.secrets.get(key_name, "")
            if value:
                return str(value).strip()
        except:
            pass
    return ""

ODDS_API_KEY = get_odds_api_key()

# =========================================================
# ODDS API ENDPOINT (MULTI-SPORT - V35 BLOCK 4)
# =========================================================

CURRENT_SPORT_KEY = get_current_sport_key()

ODDS_API_URL = f"https://api.the-odds-api.com/v4/sports/{CURRENT_SPORT_KEY}/odds"
# Free-plan friendly bookmaker set
ODDS_BOOKMAKERS = "draftkings,fanduel,betmgm"
# =========================================================
# PERSISTENCE (BET LOG CSV)
# =========================================================
BET_LOG_FILE = "bet_log.csv"

REQUIRED_BET_LOG_COLUMNS = [
    "play_id",
    "game",
    "market",
    "selection",
    "odds",
    "units",
    "stake",
    "confidence",
    "true_confidence",
    "edge",
    "books_seen",
    "consensus",
    "result",
    "profit",
    "mode",
    "log_category",
    "timestamp",

    # learning / compatibility
    "implied_prob",
    "true_prob",
    "implied_probability",
    "true_probability",
    "play_type",
    "primary_category",
    "category",

    # -----------------------------
    # CLV / MARKET TRACKING FIELDS
    # -----------------------------
    "open_odds",
    "open_line",
    "closing_odds",
    "closing_line",
    "clv_diff",
    "clv_result",
]


def load_bet_log():
    try:
        df = pd.read_csv(BET_LOG_FILE)

        if df is None or df.empty:
            return []

        # Ensure all required columns exist
        for col in REQUIRED_BET_LOG_COLUMNS:
            if col not in df.columns:
                df[col] = None

        # Normalize core text fields
        for col in ["play_id", "game", "market", "selection", "odds", "log_category", "result"]:
            if col in df.columns:
                df[col] = df[col].fillna("").astype(str).replace({"nan": "", "None": "", "none": ""}).str.strip()

        # Clean result labels
        if "result" in df.columns:
            df["result"] = df["result"].replace(
                {
                    "win": "Win",
                    "loss": "Loss",
                    "push": "Push",
                    "pending": "Pending",
                    "": "Pending",
                    "nan": "Pending",
                    "None": "Pending",
                    "none": "Pending",
                }
            )
            df["result"] = df["result"].apply(
                lambda x: x if x in ["Pending", "Win", "Loss", "Push"] else "Pending"
            )

        # Numeric cleanup
        numeric_cols = [
            "units",
            "stake",
            "true_confidence",
            "edge",
            "books_seen",
            "profit",
            "implied_prob",
            "true_prob",
            "implied_probability",
            "true_probability",
            "open_line",
            "closing_line",
            "clv_diff",
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Fill text blanks only after numeric conversion
        text_cols = [c for c in df.columns if c not in numeric_cols]
        for col in text_cols:
            df[col] = df[col].fillna("").astype(str).replace({"nan": "", "None": "", "none": ""}).str.strip()

        # Backfill stake from units if needed
        if "stake" in df.columns and "units" in df.columns:
            df["stake"] = df["stake"].fillna(df["units"])

        # Deduplicate by play_id for non-blank IDs
        if "play_id" in df.columns:
            df["play_id"] = df["play_id"].fillna("").astype(str).str.strip()
            non_blank_ids = df["play_id"] != ""

            df_with_ids = df[non_blank_ids].drop_duplicates(
                subset=["play_id"],
                keep="first",
            )
            df_without_ids = df[~non_blank_ids]
            df = pd.concat([df_with_ids, df_without_ids], ignore_index=True)

        # Final column order
        ordered_cols = REQUIRED_BET_LOG_COLUMNS + [c for c in df.columns if c not in REQUIRED_BET_LOG_COLUMNS]
        df = df[ordered_cols]

        return df.to_dict("records")

    except Exception:
        return []


def save_bet_log(records=None):
    try:
        if records is None:
            records = st.session_state.get("bet_log", [])

        df = pd.DataFrame(records)

        if df is None or df.empty:
            df = pd.DataFrame(columns=REQUIRED_BET_LOG_COLUMNS)

        # Ensure all required columns exist
        for col in REQUIRED_BET_LOG_COLUMNS:
            if col not in df.columns:
                df[col] = None

        # Normalize text fields
        for col in ["play_id", "game", "market", "selection", "odds", "log_category", "result"]:
            if col in df.columns:
                df[col] = df[col].fillna("").astype(str).replace({"nan": "", "None": "", "none": ""}).str.strip()

        # Normalize result values
        if "result" in df.columns:
            df["result"] = df["result"].replace(
                {
                    "win": "Win",
                    "loss": "Loss",
                    "push": "Push",
                    "pending": "Pending",
                    "": "Pending",
                    "nan": "Pending",
                    "None": "Pending",
                    "none": "Pending",
                }
            )
            df["result"] = df["result"].apply(
                lambda x: x if x in ["Pending", "Win", "Loss", "Push"] else "Pending"
            )

        # Numeric cleanup
        numeric_cols = [
            "units",
            "stake",
            "true_confidence",
            "edge",
            "books_seen",
            "profit",
            "implied_prob",
            "true_prob",
            "implied_probability",
            "true_probability",
            "open_line",
            "closing_line",
            "clv_diff",
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Backfill stake from units if missing
        if "stake" in df.columns and "units" in df.columns:
            df["stake"] = df["stake"].fillna(df["units"])

        # De-duplicate saved rows by play_id
        if "play_id" in df.columns:
            df["play_id"] = df["play_id"].fillna("").astype(str).str.strip()
            non_blank_ids = df["play_id"] != ""

            df_with_ids = df[non_blank_ids].drop_duplicates(
                subset=["play_id"],
                keep="first",
            )
            df_without_ids = df[~non_blank_ids]
            df = pd.concat([df_with_ids, df_without_ids], ignore_index=True)

        # Final column order
        ordered_cols = REQUIRED_BET_LOG_COLUMNS + [c for c in df.columns if c not in REQUIRED_BET_LOG_COLUMNS]
        df = df[ordered_cols]

        df.to_csv(BET_LOG_FILE, index=False)

        # Sync back into session
        st.session_state["bet_log"] = df.to_dict("records")

    except Exception:
        pass


def calculate_clv_diff(open_line, closing_line, market, selection):
    try:
        if open_line in [None, ""] or closing_line in [None, ""]:
            return None, None

        open_line = float(open_line)
        closing_line = float(closing_line)

        market = str(market).strip().lower()
        selection = str(selection).strip().lower()

        if "total" in market:
            if "over" in selection:
                diff = closing_line - open_line
            elif "under" in selection:
                diff = open_line - closing_line
            else:
                diff = closing_line - open_line
        elif "spread" in market:
            diff = closing_line - open_line
        elif "moneyline" in market or market == "ml":
            diff = open_line - closing_line
        else:
            diff = closing_line - open_line

        diff = round(diff, 2)

        if diff > 0:
            result = "Beat"
        elif diff < 0:
            result = "Lost"
        else:
            result = "Push"

        return diff, result

    except Exception:
        return None, None
# =========================================================
# LEGACY COMPATIBILITY HELPERS (DO NOT REMOVE)
# =========================================================
def build_logged_id_set(bet_log):
    ids = set()
    for row in bet_log:
        pid = str(row.get("play_id", "")).strip()
        if pid:
            ids.add(pid)
    return ids


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
        return df

    df = df.copy()
    df["play_id"] = df["play_id"].astype(str).str.strip()

    non_blank_ids = df["play_id"] != ""

    df_with_ids = df[non_blank_ids].drop_duplicates(
        subset=["play_id"],
        keep="first",
    )

    df_without_ids = df[~non_blank_ids]

    return pd.concat([df_with_ids, df_without_ids], ignore_index=True)

# =========================================================
# SESSION STATE / LEARNING ENGINE STATE / SNAPSHOT STATE
# =========================================================
if "is_mobile" not in st.session_state:
    st.session_state["is_mobile"] = True

if "bet_log" not in st.session_state:
    st.session_state["bet_log"] = []

if "auto_logged_ids" not in st.session_state:
    st.session_state["auto_logged_ids"] = set()

if "nav_choice" not in st.session_state:
    st.session_state["nav_choice"] = "Top Plays"

if "manual_results" not in st.session_state:
    st.session_state["manual_results"] = {}

if "odds_api_games" not in st.session_state:
    st.session_state["odds_api_games"] = []

if "last_successful_odds_games" not in st.session_state:
    st.session_state["last_successful_odds_games"] = []

if "odds_api_last_refresh" not in st.session_state:
    st.session_state["odds_api_last_refresh"] = None

if "last_odds_refresh_ok" not in st.session_state:
    st.session_state["last_odds_refresh_ok"] = False

if "last_refresh_error" not in st.session_state:
    st.session_state["last_refresh_error"] = ""

if "last_refresh_count" not in st.session_state:
    st.session_state["last_refresh_count"] = 0

if "last_refresh_time" not in st.session_state:
    st.session_state["last_refresh_time"] = None

if "last_api_pull_epoch" not in st.session_state:
    st.session_state["last_api_pull_epoch"] = None

if "api_mode" not in st.session_state:
    st.session_state["api_mode"] = "idle"

if "api_status_note" not in st.session_state:
    st.session_state["api_status_note"] = ""

if "daily_api_call_limit" not in st.session_state:
    st.session_state["daily_api_call_limit"] = 10

if "daily_api_call_count" not in st.session_state:
    st.session_state["daily_api_call_count"] = 0

if "daily_api_call_date" not in st.session_state:
    st.session_state["daily_api_call_date"] = datetime.now().strftime("%Y-%m-%d")

# Optional testing note for current quota situation
if "odds_api_reset_expected" not in st.session_state:
    st.session_state["odds_api_reset_expected"] = "2026-04-01"

if "sportsdata_cache" not in st.session_state:
    st.session_state["sportsdata_cache"] = {}

if "sportsdata_last_refresh" not in st.session_state:
    st.session_state["sportsdata_last_refresh"] = {}

if "api_calls_today" not in st.session_state:
    st.session_state["api_calls_today"] = 0

if "api_call_date" not in st.session_state:
    st.session_state["api_call_date"] = datetime.now().strftime("%Y-%m-%d")

if "learning_state_by_sport" not in st.session_state:
    st.session_state["learning_state_by_sport"] = {}

# -------------------------
# SNAPSHOT STATE (LOCK TAB DATA UNTIL NEXT REFRESH)
# -------------------------
if "snapshot_plays_df" not in st.session_state:
    st.session_state["snapshot_plays_df"] = pd.DataFrame()

if "snapshot_active_df" not in st.session_state:
    st.session_state["snapshot_active_df"] = pd.DataFrame()

if "snapshot_watchlist_df" not in st.session_state:
    st.session_state["snapshot_watchlist_df"] = pd.DataFrame()

if "snapshot_top_plays_df" not in st.session_state:
    st.session_state["snapshot_top_plays_df"] = pd.DataFrame()

if "snapshot_ai_slip_df" not in st.session_state:
    st.session_state["snapshot_ai_slip_df"] = pd.DataFrame()

if "snapshot_parlay_df" not in st.session_state:
    st.session_state["snapshot_parlay_df"] = pd.DataFrame()

if "snapshot_best_row" not in st.session_state:
    st.session_state["snapshot_best_row"] = None

if "snapshot_generated_at" not in st.session_state:
    st.session_state["snapshot_generated_at"] = ""

if "snapshot_refresh_id" not in st.session_state:
    st.session_state["snapshot_refresh_id"] = 0
# =========================================================
# SNAPSHOT PERSISTENCE HELPERS
# =========================================================
SNAPSHOT_STORE_FILE = "tab_snapshot_store.json"

def load_saved_tab_snapshots():
    try:
        if not os.path.exists(SNAPSHOT_STORE_FILE):
            return

        with open(SNAPSHOT_STORE_FILE, "r") as f:
            payload = json.load(f)

        mapping = {
            "snapshot_top_plays_df": "snapshot_top_plays_df",
            "snapshot_active_df": "snapshot_active_df",
            "snapshot_watchlist_df": "snapshot_watchlist_df",
            "snapshot_ai_slip_df": "snapshot_ai_slip_df",
            "snapshot_parlay_df": "snapshot_parlay_df",
        }

        for payload_key, session_key in mapping.items():
            rows = payload.get(payload_key, [])
            current_val = st.session_state.get(session_key, pd.DataFrame())

            if rows:
                if not isinstance(current_val, pd.DataFrame) or current_val.empty:
                    st.session_state[session_key] = pd.DataFrame(rows)

        best_row = payload.get("snapshot_best_row", {})
        current_best = st.session_state.get("snapshot_best_row", None)
        if isinstance(best_row, dict) and best_row:
            if current_best in [None, {}, ""]:
                st.session_state["snapshot_best_row"] = best_row

        saved_generated_at = str(payload.get("snapshot_generated_at", "")).strip()
        current_generated_at = str(st.session_state.get("snapshot_generated_at", "")).strip()
        if saved_generated_at and not current_generated_at:
            st.session_state["snapshot_generated_at"] = saved_generated_at

        saved_refresh_id = int(payload.get("snapshot_refresh_id", 0) or 0)
        current_refresh_id = int(st.session_state.get("snapshot_refresh_id", 0) or 0)
        if saved_refresh_id > current_refresh_id:
            st.session_state["snapshot_refresh_id"] = saved_refresh_id

    except Exception:
        pass


if "tab_snapshots_loaded" not in st.session_state:
    load_saved_tab_snapshots()
    st.session_state["tab_snapshots_loaded"] = True


def save_tab_snapshots_to_disk():
    try:
        def _df_to_records(key_name):
            value = st.session_state.get(key_name, pd.DataFrame())
            if isinstance(value, pd.DataFrame) and not value.empty:
                return value.to_dict("records")
            return []

        payload = {
            "snapshot_top_plays_df": _df_to_records("snapshot_top_plays_df"),
            "snapshot_active_df": _df_to_records("snapshot_active_df"),
            "snapshot_watchlist_df": _df_to_records("snapshot_watchlist_df"),
            "snapshot_ai_slip_df": _df_to_records("snapshot_ai_slip_df"),
            "snapshot_parlay_df": _df_to_records("snapshot_parlay_df"),
            "snapshot_best_row": st.session_state.get("snapshot_best_row", {}),
            "snapshot_generated_at": st.session_state.get("snapshot_generated_at", ""),
            "snapshot_refresh_id": int(st.session_state.get("snapshot_refresh_id", 0)),
        }

        with open(SNAPSHOT_STORE_FILE, "w") as f:
            json.dump(payload, f)

    except Exception:
        pass
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
# MULTI-SPORT API HELPERS
# =========================================================
def get_sportsdata_base(sport_slug=None):
    slug = str(sport_slug or get_current_sportsdata_slug()).strip().lower()
    return SPORTSDATA_BASES.get(slug, SPORTSDATA_BASES["nba"])

def get_odds_api_sport_key(sport_name=None):
    return get_sport_config(sport_name)["sport_key"]

def get_sportsdata_sport_slug(sport_name=None):
    return get_sport_config(sport_name)["sportsdata_slug"]

# =========================================================
# MULTI-SPORT ODDS STATE COMPATIBILITY HELPERS
# =========================================================
def sync_selected_sport_state_to_legacy_keys():
    """
    Keeps old single-sport parts of the app working while V35 is being upgraded.
    This mirrors the selected sport's state into the original session keys.
    """
    selected_sport = get_selected_sport()

    st.session_state["api_mode"] = get_api_mode_for_sport(selected_sport)
    st.session_state["odds_api_games"] = get_odds_games_for_sport(selected_sport)
    st.session_state["last_successful_odds_games"] = get_cached_games_for_sport(selected_sport)
    st.session_state["last_api_pull_epoch"] = get_last_pull_epoch_for_sport(selected_sport)
    st.session_state["odds_api_reset_expected"] = get_api_reset_expected_for_sport(selected_sport)

def sync_legacy_keys_to_selected_sport_state():
    """
    Pushes results from older existing code back into the selected sport bucket.
    Use this after old refresh/fetch logic runs, so V35 keeps sport-isolated storage.
    """
    selected_sport = get_selected_sport()

    set_api_mode_for_sport(st.session_state.get("api_mode", "idle"), selected_sport)
    set_odds_games_for_sport(st.session_state.get("odds_api_games", []), selected_sport)
    set_cached_games_for_sport(st.session_state.get("last_successful_odds_games", []), selected_sport)
    set_last_pull_epoch_for_sport(st.session_state.get("last_api_pull_epoch", 0), selected_sport)
    set_api_reset_expected_for_sport(st.session_state.get("odds_api_reset_expected", ""), selected_sport)

def get_active_odds_api_sport_key():
    return get_sport_config(get_selected_sport())["sport_key"]

def get_active_sportsdata_slug():
    return get_sport_config(get_selected_sport())["sportsdata_slug"]

# Make sure old code below can still operate on the currently selected sport
sync_selected_sport_state_to_legacy_keys()

# =========================================================
# MULTI-SPORT ODDS REQUEST HELPERS
# =========================================================
def get_odds_api_url_for_sport(sport_name=None):
    sport_key = get_odds_api_sport_key(sport_name)
    return f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"

def get_default_odds_params_for_sport(sport_name=None):
    return {
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american",
        "dateFormat": "iso",
        "bookmakers": "draftkings,fanduel,betmgm,caesars,espnbet,betrivers",
    }

def get_supported_market_types_for_sport(sport_name=None):
    sport_name = str(sport_name or get_selected_sport()).strip().upper()

    if sport_name == "MLB":
        return ["h2h", "spreads", "totals"]
    if sport_name == "NHL":
        return ["h2h", "spreads", "totals"]
    if sport_name == "WNBA":
        return ["h2h", "spreads", "totals"]
    return ["h2h", "spreads", "totals"]

def normalize_market_name_by_sport(market_name, sport_name=None):
    sport_name = str(sport_name or get_selected_sport()).strip().upper()
    raw = str(market_name).strip().lower()

    if raw in ["h2h", "moneyline", "ml"]:
        return "moneyline"
    if raw in ["spreads", "spread"]:
        return "spread"
    if raw in ["totals", "total", "ou", "over_under"]:
        return "total"

    # keep raw label for anything custom that may come later
    return raw

def enrich_play_row_with_sport(play_row, sport_name=None):
    sport_name = str(sport_name or get_selected_sport()).strip().upper()
    row = dict(play_row) if isinstance(play_row, dict) else {}

    row["sport"] = sport_name

    if "market" in row:
        row["market"] = normalize_market_name_by_sport(row.get("market", ""), sport_name)

    return row

def normalize_dataframe_for_selected_sport(df, sport_name=None):
    sport_name = str(sport_name or get_selected_sport()).strip().upper()

    if df is None or not isinstance(df, pd.DataFrame):
        return pd.DataFrame()

    out = df.copy()

    if "sport" not in out.columns:
        out["sport"] = sport_name
    else:
        out["sport"] = out["sport"].astype(str).str.upper().replace("", sport_name)

    if "market" in out.columns:
        out["market"] = out["market"].apply(lambda x: normalize_market_name_by_sport(x, sport_name))

    return out

# =========================================================
# MULTI-SPORT FETCH / STATE WRAPPER HELPERS
# =========================================================
def prepare_selected_sport_context():
    """
    Before older odds-fetch code runs, mirror the selected sport's state
    into the original single-sport session keys so legacy logic keeps working.
    """
    sync_selected_sport_state_to_legacy_keys()


def finalize_selected_sport_context():
    """
    After older odds-fetch code runs, push any updated legacy keys back into
    the selected sport's dedicated storage bucket.
    """
    sync_legacy_keys_to_selected_sport_state()

# =========================================================
# MULTI-SPORT DISPLAY / LOG HELPERS
# =========================================================
def get_selected_sport_label():
    return str(get_selected_sport()).strip().upper()

def format_scope_caption(base_text):
    return f"{base_text} ({get_selected_sport_label()})"

def get_selected_sport_bet_count():
    return len(get_bet_log_for_sport(get_selected_sport()))

def build_composite_play_id(play_id, sport_name=None):
    sport_name = str(sport_name or get_selected_sport()).strip().upper()
    raw_play_id = str(play_id).strip()
    return f"{sport_name}__{raw_play_id}"

def get_existing_composite_play_ids():
    existing_rows = st.session_state.get("bet_log", [])
    output = set()

    for row in existing_rows:
        sport_name = str(row.get("sport", "")).strip().upper()
        play_id = str(row.get("play_id", "")).strip()
        if sport_name and play_id:
            output.add(f"{sport_name}__{play_id}")

    return output

def ensure_row_has_selected_sport(row, sport_name=None):
    sport_name = str(sport_name or get_selected_sport()).strip().upper()
    out = dict(row) if isinstance(row, dict) else {}
    out["sport"] = sport_name
    return out

def filter_dataframe_to_selected_sport(df, sport_name=None):
    sport_name = str(sport_name or get_selected_sport()).strip().upper()

    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame() if not isinstance(df, pd.DataFrame) else df.copy()

    out = df.copy()

    if "sport" not in out.columns:
        out["sport"] = sport_name
        return out

    out["sport"] = out["sport"].astype(str).str.upper().str.strip()
    filtered = out[out["sport"].isin(["", sport_name])].copy()

    if filtered.empty:
        return out.copy()

    filtered.loc[:, "sport"] = filtered["sport"].replace("", sport_name)
    return filtered

def get_selected_sport_learning_summary():
    learning_state = get_learning_state_for_sport(get_selected_sport())

    if not isinstance(learning_state, dict):
        return {
            "min_samples": 3,
            "last_update": None,
            "accelerated_mode": True,
        }

    return {
        "min_samples": int(learning_state.get("category_min_samples", 3) or 3),
        "last_update": learning_state.get("last_update"),
        "accelerated_mode": bool(learning_state.get("accelerated_learning_mode", True)),
    }

# =========================================================
# MULTI-SPORT PLAY TEMPLATE HELPERS
# =========================================================
def get_default_team_market_templates_for_sport(sport_name=None):
    sport_name = str(sport_name or get_selected_sport()).strip().upper()

    if sport_name == "NBA":
        return [
            ("moneyline", lambda g: g.split(" vs ")[1]),
            ("moneyline", lambda g: g.split(" vs ")[0]),
            ("total", lambda g: "Over 221.5"),
            ("total", lambda g: "Under 221.5"),
        ]

    if sport_name == "NHL":
        return [
            ("moneyline", lambda g: g.split(" vs ")[1]),
            ("moneyline", lambda g: g.split(" vs ")[0]),
            ("total", lambda g: "Over 6.5"),
            ("total", lambda g: "Under 6.5"),
        ]

    if sport_name == "MLB":
        return [
            ("moneyline", lambda g: g.split(" vs ")[1]),
            ("moneyline", lambda g: g.split(" vs ")[0]),
            ("total", lambda g: "Over 8.5"),
            ("total", lambda g: "Under 8.5"),
        ]

    if sport_name == "WNBA":
        return [
            ("moneyline", lambda g: g.split(" vs ")[1]),
            ("moneyline", lambda g: g.split(" vs ")[0]),
            ("total", lambda g: "Over 164.5"),
            ("total", lambda g: "Under 164.5"),
        ]

    return [
        ("moneyline", lambda g: g.split(" vs ")[1]),
        ("moneyline", lambda g: g.split(" vs ")[0]),
        ("total", lambda g: "Over 221.5"),
        ("total", lambda g: "Under 221.5"),
    ]

def get_default_prop_types_for_sport(sport_name=None):
    sport_name = str(sport_name or get_selected_sport()).strip().upper()

    if sport_name in ["NBA", "WNBA"]:
        return ["points", "rebounds", "assists", "pra"]

    if sport_name == "NHL":
        return ["goals", "assists", "points", "sog"]

    if sport_name == "MLB":
        return ["hits", "runs", "rbis", "strikeouts"]

    return ["points", "rebounds", "assists", "pra"]

def get_default_total_band_for_sport(sport_name=None):
    sport_name = str(sport_name or get_selected_sport()).strip().upper()

    if sport_name == "NBA":
        return (210.5, 238.5)
    if sport_name == "NHL":
        return (5.5, 7.5)
    if sport_name == "MLB":
        return (7.0, 10.5)
    if sport_name == "WNBA":
        return (156.5, 178.5)

    return (210.5, 238.5)

def get_sport_display_note(sport_name=None):
    sport_name = str(sport_name or get_selected_sport()).strip().upper()

    notes = {
        "NBA": "Basketball scoring environment with standard moneyline / total logic.",
        "NHL": "Lower-scoring environment; totals and moneylines tend to be tighter.",
        "MLB": "Baseball scoring environment with lower totals and different volatility.",
        "WNBA": "Basketball logic with lower default totals than NBA.",
    }

    return notes.get(sport_name, "Multi-sport framework active.")

def safe_parse_matchup(game_text):
    raw = str(game_text).strip()

    if " vs " in raw:
        parts = raw.split(" vs ")
        if len(parts) == 2:
            return parts[0].strip(), parts[1].strip()

    if " v " in raw:
        parts = raw.split(" v ")
        if len(parts) == 2:
            return parts[0].strip(), parts[1].strip()

    return "", ""

def build_team_market_templates_for_selected_sport():
    return get_default_team_market_templates_for_sport(get_selected_sport())

def build_prop_types_for_selected_sport():
    return get_default_prop_types_for_sport(get_selected_sport())

def get_total_band_for_selected_sport():
    return get_default_total_band_for_sport(get_selected_sport())
# =========================================================
# MULTI-SPORT PLAY GENERATION HELPERS
# =========================================================
def build_default_game_label(away_team, home_team):
    away = str(away_team).strip().upper()
    home = str(home_team).strip().upper()

    if away and home:
        return f"{away} vs {home}"
    return ""

def get_default_total_value_for_sport(sport_name=None):
    sport_name = str(sport_name or get_selected_sport()).strip().upper()

    defaults = {
        "NBA": 221.5,
        "NHL": 6.5,
        "MLB": 8.5,
        "WNBA": 164.5,
    }

    return float(defaults.get(sport_name, 221.5))

def format_default_total_selection(direction, sport_name=None):
    total_value = get_default_total_value_for_sport(sport_name)
    direction = str(direction).strip().title()

    if direction not in ["Over", "Under"]:
        direction = "Over"

    return f"{direction} {total_value}"

def build_team_market_templates_for_game(game_text, sport_name=None):
    sport_name = str(sport_name or get_selected_sport()).strip().upper()
    away_team, home_team = safe_parse_matchup(game_text)

    if not away_team or not home_team:
        return []

    return [
        {
            "market": "moneyline",
            "selection": home_team,
            "sport": sport_name,
            "game": game_text,
        },
        {
            "market": "moneyline",
            "selection": away_team,
            "sport": sport_name,
            "game": game_text,
        },
        {
            "market": "total",
            "selection": format_default_total_selection("Over", sport_name),
            "sport": sport_name,
            "game": game_text,
        },
        {
            "market": "total",
            "selection": format_default_total_selection("Under", sport_name),
            "sport": sport_name,
            "game": game_text,
        },
    ]

def build_default_market_rows_from_games(games_list, sport_name=None):
    sport_name = str(sport_name or get_selected_sport()).strip().upper()
    rows = []

    for game_text in games_list or []:
        rows.extend(build_team_market_templates_for_game(game_text, sport_name))

    if not rows:
        return pd.DataFrame(columns=["sport", "game", "market", "selection"])

    return pd.DataFrame(rows)

def attach_selected_sport_to_dataframe(df, sport_name=None):
    sport_name = str(sport_name or get_selected_sport()).strip().upper()

    if df is None or not isinstance(df, pd.DataFrame):
        return pd.DataFrame()

    out = df.copy()

    if "sport" not in out.columns:
        out["sport"] = sport_name
    else:
        out["sport"] = out["sport"].astype(str).str.upper().replace("", sport_name)

    return out

def get_selected_sport_template_summary():
    sport_name = get_selected_sport()

    return {
        "sport": sport_name,
        "default_total": get_default_total_value_for_sport(sport_name),
        "prop_types": get_default_prop_types_for_sport(sport_name),
        "display_note": get_sport_display_note(sport_name),
    }

# =========================================================
# MULTI-SPORT FRAMEWORK STATUS HELPERS
# =========================================================
def get_multi_sport_framework_status():
    selected_sport = get_selected_sport()
    cfg = get_sport_config(selected_sport)
    learning_state = get_learning_state_for_sport(selected_sport)

    if not isinstance(learning_state, dict):
        learning_state = {}

    return {
        "selected_sport": selected_sport,
        "sport_key": cfg.get("sport_key", ""),
        "sportsdata_slug": cfg.get("sportsdata_slug", ""),
        "api_mode": get_api_mode_for_sport(selected_sport),
        "live_games_count": len(get_odds_games_for_sport(selected_sport)),
        "cached_games_count": len(get_cached_games_for_sport(selected_sport)),
        "bet_log_count": len(get_bet_log_for_sport(selected_sport)),
        "min_samples": int(learning_state.get("category_min_samples", 3) or 3),
        "accelerated_learning_mode": bool(learning_state.get("accelerated_learning_mode", True)),
    }

def render_multi_sport_framework_status():
    status = get_multi_sport_framework_status()

    st.sidebar.markdown("### 🧭 V35 Framework")
    st.sidebar.caption(
        f"Sport: {status['selected_sport']} • Odds key: {status['sport_key']} • SportsData: {status['sportsdata_slug']}"
    )
    st.sidebar.caption(
        f"Live games: {status['live_games_count']} • Cached games: {status['cached_games_count']} • Logged bets: {status['bet_log_count']}"
    )
    st.sidebar.caption(
        f"Learning min samples: {status['min_samples']} • Accelerated mode: {'On' if status['accelerated_learning_mode'] else 'Off'}"
    )

def get_selected_sport_empty_state_message():
    selected_sport = get_selected_sport()
    api_mode = str(get_api_mode_for_sport(selected_sport)).strip().lower()

    if api_mode == "waiting_reset":
        return f"{selected_sport} odds are waiting for API reset."
    if api_mode == "limit_hit":
        return f"{selected_sport} odds API limit has been reached."
    if api_mode in ["key_error", "invalid_key", "auth_error", "no_key"]:
        return f"{selected_sport} odds are unavailable because of an API key issue."
    return f"No live {selected_sport} data loaded yet."

def get_selected_sport_runtime_note():
    selected_sport = get_selected_sport()
    notes = {
        "NBA": "NBA framework ready. Best current sport for immediate testing while season is active.",
        "NHL": "NHL framework ready. Good parallel test sport during current active season.",
        "MLB": "MLB framework ready. Strong long-run testing sport because of large game volume.",
        "WNBA": "WNBA framework ready. Sport lane prepared for season start and later live learning.",
    }
    return notes.get(selected_sport, "Multi-sport framework active.")

render_multi_sport_framework_status()



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
# SELF-LEARNING ENGINE HELPERS (V33.2 ON TOP OF V34)
# =========================================================
def american_odds_to_implied_prob(odds):
    try:
        odds = float(odds)
        if odds > 0:
            return 100.0 / (odds + 100.0)
        return abs(odds) / (abs(odds) + 100.0)
    except:
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

    return parts[0]


def classify_play_type(row):
    market = str(row.get("market", "")).strip().lower()
    selection = str(row.get("selection", row.get("pick", ""))).strip().lower()
    category = normalize_category_label(row.get("category", ""))

    if "parlay" in category.lower():
        return "parlay"

    if "moneyline" in market or market == "ml":
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
        return "prop"

    return "other"


def safe_clv_score(row):
    """
    Convert CLV result + diff into a controlled score for learning.
    Positive = model likely beat market
    Negative = model likely lost to market
    """
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
    """
    Controlled true probability estimate.
    V33.2 adds a SMALL CLV-aware adjustment.
    This remains conservative for live testing.
    """
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
    matchup_quality = clamp(multi_ai_score / 100.0, 0.01, 0.99)

    price_nudge = clamp(implied_prob + (price_edge * 0.25), 0.01, 0.99)

    weighted_prob = (
        projection_component * safe_float(weights.get("true_probability", 0.30), 0.30) +
        price_nudge * safe_float(weights.get("price_edge", 0.25), 0.25) +
        market_component * safe_float(weights.get("market_signal", 0.15), 0.15) +
        matchup_quality * safe_float(weights.get("matchup_quality", 0.15), 0.15) +
        history_component * safe_float(weights.get("historical_performance", 0.15), 0.15)
    )

    # very small CLV nudge only after base probability is formed
    clv_nudge = clv_signal * 0.015

    true_probability = (weighted_prob * 0.55) + (implied_prob * 0.45)
    true_probability = true_probability + clv_nudge

    return clamp(true_probability, 0.01, 0.99)


def enrich_play_with_learning_fields(row, sport=None):
    row = dict(row)

    implied_probability = american_odds_to_implied_prob(row.get("odds", 0))
    true_probability = compute_true_probability(row, sport=sport)
    edge = true_probability - implied_probability

    row["implied_probability"] = round(implied_probability, 4)
    row["true_probability"] = round(true_probability, 4)
    row["edge"] = round(edge, 4)
    row["play_type"] = classify_play_type(row)
    row["primary_category"] = normalize_category_label(row.get("category", ""))

    return row


def should_allow_play(row, sport=None):
    learning_state = get_active_learning_state(sport)
    row = enrich_play_with_learning_fields(row, sport=sport)

    category = row.get("primary_category", "Uncategorized")
    play_type = row.get("play_type", "other")
    edge = safe_float(row.get("edge", 0.0), 0.0)

    category_threshold = safe_float(
        learning_state.get("category_thresholds", {}).get(category, 0.03),
        0.03
    )

    bad_play_type_flags = learning_state.get("bad_play_type_flags", {})
    if isinstance(bad_play_type_flags.get(play_type), dict):
        if bool(bad_play_type_flags.get(play_type, {}).get("is_filtered", False)):
            return False, f"Filtered by learning engine: {play_type} underperforming"
    elif bool(bad_play_type_flags.get(play_type, False)):
        return False, f"Filtered by learning engine: {play_type} underperforming"

    if edge < category_threshold:
        return False, f"Edge below threshold ({round(edge, 4)} < {round(category_threshold, 4)})"

    return True, "Allowed"


def calculate_bet_profit(odds, stake, result):
    odds = safe_float(odds, 0.0)
    stake = safe_float(stake, 0.0)
    result = str(result or "").strip().lower()

    if result == "win":
        if odds > 0:
            return round(stake * (odds / 100.0), 2)
        return round(stake * (100.0 / abs(odds)), 2)

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
            return

    df["result"] = df["result"].astype(str).str.strip().str.lower()
    graded = df[df["result"].isin(["win", "loss", "push"])].copy()

    if graded.empty:
        return

    enriched_rows = []
    for _, row in graded.iterrows():
        enriched_rows.append(enrich_play_with_learning_fields(row.to_dict(), sport=selected_sport_name))
    graded = pd.DataFrame(enriched_rows)

    if "stake" not in graded.columns:
        graded["stake"] = 1.0
    graded["stake"] = graded["stake"].apply(lambda x: safe_float(x, 1.0))

    graded["profit"] = graded.apply(
        lambda r: calculate_bet_profit(r.get("odds", 0), r.get("stake", 1.0), r.get("result", "")),
        axis=1
    )

    if "clv_diff" not in graded.columns:
        graded["clv_diff"] = 0.0
    if "clv_result" not in graded.columns:
        graded["clv_result"] = ""

    graded["clv_diff"] = graded["clv_diff"].apply(lambda x: safe_float(x, 0.0))
    graded["clv_result"] = graded["clv_result"].astype(str).str.strip()
    graded["clv_score"] = graded.apply(safe_clv_score, axis=1)

    learning_state = get_active_learning_state(selected_sport_name)
    min_samples = safe_float(learning_state.get("category_min_samples", 8), 8)

    # -----------------------------------------------------
    # PLAY TYPE STATS
    # -----------------------------------------------------
    play_type_stats = {}

    for play_type, group in graded.groupby("play_type"):
        bets = len(group)
        wins = int((group["result"] == "win").sum())
        losses = int((group["result"] == "loss").sum())
        pushes = int((group["result"] == "push").sum())
        profit = round(group["profit"].sum(), 2)
        stake_sum = max(group["stake"].sum(), 1.0)
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
        bets = stats["bets"]
        roi = stats["roi"]
        avg_clv_score = stats.get("avg_clv_score", 0.0)

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
        total_stake = max(group["stake"].sum(), 1.0)
        roi = group["profit"].sum() / total_stake
        avg_clv_score = group["clv_score"].mean() if len(group) > 0 else 0.0

        current_threshold = updated_thresholds.get(category, 0.03)

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
    wins = graded[graded["result"] == "win"]
    losses = graded[graded["result"] == "loss"]

    if not wins.empty and not losses.empty:
        win_edge = wins["edge"].mean()
        loss_edge = losses["edge"].mean()
        win_clv_score = wins["clv_score"].mean() if "clv_score" in wins.columns else 0.0
        loss_clv_score = losses["clv_score"].mean() if "clv_score" in losses.columns else 0.0

        weights = dict(learning_state.get("weights", {}))

        if win_edge > loss_edge:
            weights["true_probability"] = clamp(safe_float(weights.get("true_probability", 0.30), 0.30) + 0.01, 0.22, 0.38)
            weights["price_edge"] = clamp(safe_float(weights.get("price_edge", 0.25), 0.25) + 0.005, 0.18, 0.32)
            weights["market_signal"] = clamp(safe_float(weights.get("market_signal", 0.15), 0.15) - 0.005, 0.10, 0.22)

        if win_clv_score > loss_clv_score:
            weights["market_signal"] = clamp(safe_float(weights.get("market_signal", 0.15), 0.15) + 0.006, 0.10, 0.24)
            weights["historical_performance"] = clamp(safe_float(weights.get("historical_performance", 0.15), 0.15) + 0.004, 0.10, 0.24)
            weights["matchup_quality"] = clamp(safe_float(weights.get("matchup_quality", 0.15), 0.15) - 0.004, 0.10, 0.22)

        total = sum(weights.values())
        if total > 0:
            for key in weights:
                weights[key] = round(weights[key] / total, 4)

        learning_state["weights"] = weights

    learning_state["last_learning_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_learning_state_for_sport(learning_state, selected_sport_name)


def get_learning_summary_rows(sport=None):
    learning_state = get_active_learning_state(sport)
    stats = learning_state.get("play_type_stats", {})

    rows = []
    for play_type, info in stats.items():
        rows.append({
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
            "Filtered": "Yes" if learning_state.get("bad_category_flags", {}).get(play_type, False) else "No",
        })
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
        if "Top Play" in parts:
            return "Top Plays"
        if "AI Slip" in parts:
            return "AI Picks"
        if "AI Parlay" in parts:
            return "AI Parlays"
        if "Watchlist" in parts:
            return "Watchlist"
        if parts:
            return parts[0]

    status = str(row.get("status", "")).strip()
    if status == "Active":
        return "Top Plays"
    if status == "Watch":
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
        row["multi_ai_score"] = safe_float(row.get("score", 50.0), 50.0)

    if "stake" not in row:
        row["stake"] = safe_float(row.get("units", 1.0), 1.0)

    enriched = enrich_play_with_learning_fields(row, sport=sport)

    enriched["implied_prob"] = round(safe_float(enriched.get("implied_probability", 0.0), 0.0) * 100.0, 2)
    enriched["true_prob"] = round(safe_float(enriched.get("true_probability", 0.0), 0.0) * 100.0, 2)
    enriched["edge"] = round(
        enriched["true_prob"] - enriched["implied_prob"],
        2
    )

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

    graded = df[df["result"].isin(["Win", "Loss"])].copy()
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
        return df

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

today_games_text = st.sidebar.text_area(
    "Optional: Filter today's slate",
    key="today_games_text",
    height=180,
    placeholder="Examples:\nSAS vs CHA\nLAL vs BOS\nHeat vs Knicks\n\nLeave blank to use all live games",
)

st.sidebar.caption(
    "Supports abbreviations, full team names, or nicknames (e.g., LAL, Lakers, Los Angeles Lakers)"
)

today_games = parse_today_games(str(today_games_text).upper())
selected_sport = get_selected_sport()

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
# LIVE ODDS FETCH + EFFECTIVE DATA HELPERS
# =========================================================
def fetch_odds_for_sport(sport_name: str):
    sport_cfg = get_sport_config(sport_name)
    api_key = get_odds_api_key()

    if not api_key:
        set_api_status("no_key", "No Odds API key found in secrets.")
        return []

    if get_daily_api_calls_remaining() <= 0:
        st.session_state["odds_api_reset_expected"] = (
            (pd.Timestamp.now() + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        )
        set_api_status("waiting_reset", "Daily Odds API call cap reached.")
        return st.session_state.get("last_successful_odds_games_by_sport", {}).get(sport_name, [])

    url = f"{ODDS_API_BASE}/{sport_cfg['sport_key']}/odds"

    params = {
        "apiKey": api_key,
        "regions": ODDS_REGIONS,
        "markets": ODDS_MARKETS,
        "oddsFormat": ODDS_ODDS_FORMAT,
        "bookmakers": ODDS_BOOKMAKERS,
    }

    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()

        data = response.json()
        if not isinstance(data, list):
            data = []

        increment_daily_api_call_count()

        games_by_sport = dict(st.session_state.get("odds_api_games_by_sport", {}))
        last_success = dict(st.session_state.get("last_successful_odds_games_by_sport", {}))

        games_by_sport[sport_name] = data
        last_success[sport_name] = data

        st.session_state["odds_api_games_by_sport"] = games_by_sport
        st.session_state["last_successful_odds_games_by_sport"] = last_success
        st.session_state["last_odds_refresh_ok"] = True
        st.session_state["last_refresh_error"] = ""
        st.session_state["last_refresh_count"] = len(data)
        st.session_state["last_refresh_time"] = pd.Timestamp.now().strftime("%Y-%m-%d %I:%M:%S %p")
        st.session_state["last_api_pull_epoch"] = time.time()

        set_api_status(
            "live",
            f"{sport_name} live odds loaded. Calls used today: {get_daily_api_calls_used()} / {DAILY_API_CALL_LIMIT}",
        )

        return data

    except Exception as e:
        err = str(e)
        st.session_state["last_refresh_error"] = err
        st.session_state["last_odds_refresh_ok"] = False

        fallback = st.session_state.get("last_successful_odds_games_by_sport", {}).get(sport_name, [])
        if fallback:
            set_api_status("cached", f"{sport_name} live pull failed. Using cached odds.")
            return fallback

        set_api_status("error", f"{sport_name} live pull failed.")
        return []


def refresh_live_odds():
    if not api_cooldown_ready():
        set_api_status("cooldown", f"Cooldown active. Wait about {API_COOLDOWN_SECONDS} seconds between pulls.")
        return

    total_loaded = 0
    combined_note_parts = []

    for sport_name in ACTIVE_REFRESH_SPORTS:
        games = fetch_odds_for_sport(sport_name)
        total_loaded += len(games)
        combined_note_parts.append(f"{sport_name}: {len(games)}")

    st.session_state["last_refresh_count"] = total_loaded
    st.session_state["last_refresh_time"] = pd.Timestamp.now().strftime("%Y-%m-%d %I:%M:%S %p")
    st.session_state["api_status_note"] = " | ".join(combined_note_parts)


def get_effective_odds_games_for_sport(sport_name: str):
    live_map = st.session_state.get("odds_api_games_by_sport", {})
    cached_map = st.session_state.get("last_successful_odds_games_by_sport", {})

    live_games = live_map.get(sport_name, [])
    cached_games = cached_map.get(sport_name, [])

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
    if market_name == "spreads":
        market_bonus = 0.010
    elif market_name == "totals":
        market_bonus = 0.008
    elif market_name == "h2h":
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
    if market_name == "spreads":
        return 67.0
    if market_name == "totals":
        return 63.0
    if market_name == "h2h":
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
        (true_prob_pct * TRUE_PROB_WEIGHT) +
        (edge_score * PRICE_EDGE_WEIGHT) +
        (safe_float(market_signal, 0) * MARKET_SIGNAL_WEIGHT) +
        (safe_float(matchup_score, 0) * MATCHUP_WEIGHT) +
        (safe_float(historical_score, 0) * HISTORICAL_WEIGHT)
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
    if status == "Active":
        base = SINGLE_UNIT_MIN + ((tc - MIN_ACTIVE_TRUE_CONF) / 25.0) * (SINGLE_UNIT_MAX - SINGLE_UNIT_MIN)
        return round(clamp(base, SINGLE_UNIT_MIN, SINGLE_UNIT_MAX), 2)

    base = WATCH_UNIT_MIN + ((tc - MIN_WATCH_TRUE_CONF) / 25.0) * (WATCH_UNIT_MAX - WATCH_UNIT_MIN)
    return round(clamp(base, WATCH_UNIT_MIN, WATCH_UNIT_MAX), 2)


# =========================================================
# DATA BUILD
# =========================================================
def generate_ai_plays():
    selected_sport = get_selected_sport()
    odds_games = get_effective_odds_games_for_sport(selected_sport)
    slate_filters = get_today_games_filter()

    empty_cols = [
        "sport",
        "game",
        "market",
        "selection",
        "player",
        "team",
        "opponent",
        "line",
        "odds",
        "implied_prob",
        "true_prob",
        "edge",
        "books",
        "consensus_pct",
        "sharp_score",
        "market_signal",
        "matchup_score",
        "historical_score",
        "true_confidence",
        "status",
        "units",
        "play_id",
        "log_category",
        "sportsdata_note",
        "injury_flag",
        "lineup_flag",
        "model_score",
    ]

    if not odds_games:
        return pd.DataFrame(columns=empty_cols)

    rows = []

    for game in odds_games:
        home_team = str(game.get("home_team", "")).strip()
        away_team = str(game.get("away_team", "")).strip()

        if not home_team or not away_team:
            continue

        if not game_matches_filter(home_team, away_team, slate_filters):
            continue

        game_label = f"{away_team} @ {home_team}"
        bookmakers = game.get("bookmakers", [])

        market_price_map = {}

        for book in bookmakers:
            book_title = str(book.get("title", "")).strip()
            markets = book.get("markets", [])

            for market in markets:
                market_key = str(market.get("key", "")).strip()
                outcomes = market.get("outcomes", [])

                if market_key not in ["h2h", "spreads", "totals"]:
                    continue

                for outcome in outcomes:
                    name = str(outcome.get("name", "")).strip()
                    price = safe_float(outcome.get("price", 0), 0)
                    point = safe_float(outcome.get("point", 0), 0)

                    if market_key == "totals":
                        selection = f"{name} {point}".strip()
                        team_name = ""
                        opponent = ""
                        line_value = point
                    else:
                        selection = name
                        team_name = name
                        opponent = away_team if name == home_team else home_team
                        line_value = point

                    key = (market_key, selection, line_value)

                    if key not in market_price_map:
                        market_price_map[key] = {
                            "sport": selected_sport,
                            "game": game_label,
                            "market": market_key,
                            "selection": selection,
                            "player": "",
                            "team": team_name,
                            "opponent": opponent,
                            "line": line_value,
                            "prices": [],
                            "book_names": [],
                        }

                    market_price_map[key]["prices"].append(price)
                    market_price_map[key]["book_names"].append(book_title)

        for (_, _, _), data in market_price_map.items():
            prices = data.get("prices", [])
            books = len(prices)

            if books == 0:
                continue

            best_odds = max(prices)
            implied_prob = american_to_implied_prob(best_odds)
            consensus_pct = calculate_consensus_pct(prices)
            true_prob = estimate_true_probability(implied_prob, books, consensus_pct, data["market"])
            edge = round((true_prob - implied_prob) * 100.0, 2)

            market_signal = calculate_market_signal(books, edge)
            matchup_score = calculate_matchup_score(data["market"])
            historical_score = calculate_historical_score()
            true_confidence = calculate_true_confidence(
                true_prob,
                edge,
                books,
                market_signal,
                matchup_score,
                historical_score,
            )

            status = "Watch"
            log_category = "Watchlist"

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
            model_score = calculate_model_score(true_prob, edge, books)
            play_id = build_play_id(selected_sport, data["game"], data["market"], data["selection"], data["line"])

            rows.append({
                "sport": selected_sport,
                "game": data["game"],
                "market": data["market"],
                "selection": data["selection"],
                "player": "",
                "team": data["team"],
                "opponent": data["opponent"],
                "line": data["line"],
                "odds": best_odds,
                "implied_prob": round(implied_prob, 4),
                "true_prob": round(true_prob, 4),
                "edge": edge,
                "books": books,
                "consensus_pct": consensus_pct,
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
                "model_score": round(model_score, 1),
            })

    plays_df = pd.DataFrame(rows)
    plays_df = normalize_dataframe_for_selected_sport(plays_df, selected_sport)

    if plays_df.empty:
        return pd.DataFrame(columns=empty_cols)

    plays_df = plays_df.sort_values(
        by=["status", "true_confidence", "edge", "books"],
        ascending=[True, False, False, False],
    ).reset_index(drop=True)

    return plays_df

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

    sort_cols = [c for c in ["true_confidence", "edge", "books"] if c in top_df.columns]
    if sort_cols:
        top_df = top_df.sort_values(sort_cols, ascending=[False] * len(sort_cols))

    top_df["log_category"] = "Top Plays"
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

    sort_cols = [c for c in ["true_confidence", "edge", "books"] if c in watch_df.columns]
    if sort_cols:
        watch_df = watch_df.sort_values(sort_cols, ascending=[False] * len(sort_cols))

    watch_df["status"] = "Watch"
    watch_df["log_category"] = "Watchlist"
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

    sort_cols = [c for c in ["true_confidence", "edge", "books"] if c in candidate_df.columns]
    if sort_cols:
        candidate_df = candidate_df.sort_values(sort_cols, ascending=[False] * len(sort_cols)).reset_index(drop=True)

    rows = []

    # Best single
    best_row = candidate_df.iloc[0].to_dict()
    best_row["slip_type"] = "Best Single"
    best_row["parlay_legs"] = 1
    best_row["parlay_odds"] = best_row.get("odds", 0)
    best_row["recommended_units"] = best_row.get("units", 0.5)
    best_row["log_category"] = "AI Picks"
    rows.append(best_row)

    # Best 2-leg and 3-leg
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
                    "implied_prob": american_to_implied_prob(parlay_odds),
                    "true_prob": round(pd.to_numeric(legs["true_prob"], errors="coerce").fillna(0).mean(), 4),
                    "edge": round(avg_edge, 2),
                    "books": round(avg_books, 1),
                    "consensus_pct": round(pd.to_numeric(legs.get("consensus_pct", 0), errors="coerce").fillna(0).mean(), 1),
                    "sharp_score": round(pd.to_numeric(legs.get("sharp_score", 0), errors="coerce").fillna(0).mean(), 1),
                    "market_signal": round(pd.to_numeric(legs.get("market_signal", 0), errors="coerce").fillna(0).mean(), 1),
                    "matchup_score": round(pd.to_numeric(legs.get("matchup_score", 0), errors="coerce").fillna(0).mean(), 1),
                    "historical_score": round(pd.to_numeric(legs.get("historical_score", 0), errors="coerce").fillna(0).mean(), 1),
                    "true_confidence": round(avg_conf, 1),
                    "status": "Active",
                    "units": PARLAY_UNIT_SHARP if leg_count == 2 else PARLAY_UNIT_FALLBACK_3,
                    "play_id": build_play_id(
                        {
                            "game": " | ".join(legs["game"].astype(str).tolist()),
                            "market": "Parlay",
                            "selection": " + ".join(legs["selection"].astype(str).tolist()),
                            "odds": parlay_odds,
                        }
                    ),
                    "log_category": "AI Parlays",
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

    return pd.DataFrame(rows).reset_index(drop=True)


def save_generated_play_snapshots(plays_df: pd.DataFrame):
    selected_sport = get_selected_sport()

    plays_df = normalize_dataframe_for_selected_sport(plays_df, selected_sport)
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
        "game": enriched.get("game"),
        "market": enriched.get("market"),
        "selection": enriched.get("selection"),
        "odds": enriched.get("odds"),
        "implied_prob": enriched.get("implied_prob"),
        "true_prob": enriched.get("true_prob"),
        "implied_probability": enriched.get("implied_probability"),
        "true_probability": enriched.get("true_probability"),
        "edge": enriched.get("edge"),
        "play_type": enriched.get("play_type"),
        "primary_category": enriched.get("primary_category"),
        "category": enriched.get("category"),
        "units": safe_float(enriched.get("units", 1.0), 1.0),
        "stake": safe_float(enriched.get("units", 1.0), 1.0),
        "confidence": enriched.get("confidence"),
        "true_confidence": enriched.get("true_confidence"),
        "books_seen": enriched.get("books_seen"),
        "consensus": enriched.get("consensus"),
        "result": "Pending",
        "profit": 0.0,
        "mode": TEST_MODE,
        "log_category": log_category_label,
        "timestamp": datetime.now().isoformat(),

        # CLV / MARKET TRACKING
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

    pid = str(best_row.get("play_id", "")).strip()
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
        "game": " | ".join(sorted(set([str(leg.get("game", "")) for leg in best_parlay.get("legs", [])]))),
        "market": "parlay",
        "selection": " | ".join([str(leg.get("selection", "")) for leg in best_parlay.get("legs", [])]),
        "odds": best_parlay.get("combined_odds"),
        "implied_prob": None,
        "true_prob": None,
        "implied_probability": None,
        "true_probability": None,
        "edge": best_parlay.get("avg_edge"),
        "play_type": "parlay",
        "primary_category": "AI Parlays",
        "category": "AI Parlays",
        "units": scale_parlay_units(best_parlay),
        "stake": scale_parlay_units(best_parlay),
        "confidence": "High" if float(best_parlay.get("avg_true_conf", 0)) >= 70 else "Medium",
        "true_confidence": best_parlay.get("avg_true_conf"),
        "books_seen": best_parlay.get("avg_books"),
        "consensus": best_parlay.get("approval_type"),
        "result": "Pending",
        "profit": 0.0,
        "mode": TEST_MODE,
        "log_category": "AI Parlay",
        "timestamp": datetime.now().isoformat(),

        # CLV / MARKET TRACKING
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

if "bet_log" not in st.session_state or not st.session_state["bet_log"]:
    st.session_state["bet_log"] = loaded_bet_log
else:
    existing_df = pd.DataFrame(st.session_state.get("bet_log", []))

    if existing_df is None or existing_df.empty:
        st.session_state["bet_log"] = loaded_bet_log
    else:
        for col in REQUIRED_BET_LOG_COLUMNS:
            if col not in existing_df.columns:
                existing_df[col] = None

        existing_df = _merge_duplicate_play_id_rows(existing_df)
        st.session_state["bet_log"] = existing_df.to_dict("records")

bet_log_df = pd.DataFrame(st.session_state.get("bet_log", []))
if bet_log_df is None or bet_log_df.empty:
    bet_log_df = pd.DataFrame(columns=REQUIRED_BET_LOG_COLUMNS)
else:
    for col in REQUIRED_BET_LOG_COLUMNS:
        if col not in bet_log_df.columns:
            bet_log_df[col] = None
    bet_log_df = _merge_duplicate_play_id_rows(bet_log_df)

st.session_state["bet_log"] = bet_log_df.to_dict("records")
save_bet_log(st.session_state["bet_log"])
st.session_state["auto_logged_ids"] = build_logged_id_set(st.session_state.get("bet_log", []))

update_learning_from_results()

plays_df = generate_ai_plays()

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
        plays_df = recalculate_play_metrics(plays_df)
except Exception as e:
    st.warning(f"SportsData enrichment skipped: {e}")

# =========================================================
# APPLY LEARNING FILTERS
# =========================================================
if plays_df is not None and not plays_df.empty:
    active_source_df = plays_df[plays_df["status"] == "Active"].copy().reset_index(drop=True)
    watch_source_df = plays_df[plays_df["status"] == "Watch"].copy().reset_index(drop=True)

    active_df = apply_learning_engine_to_df(active_source_df, "Top Plays")
    watch_df = apply_learning_engine_to_df(watch_source_df, "Watchlist")
else:
    active_df = pd.DataFrame()
    watch_df = pd.DataFrame()

# Keep compatibility names that older UI may still reference
top_plays_df = active_df.copy()
watchlist_df = watch_df.copy()

# ================================
# AUTO LOG TOP PLAYS
# ================================
auto_logged_count = auto_log_active_plays(active_df)

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
snapshot_source_df = pd.concat(
    [active_df.copy(), watch_df.copy()],
    ignore_index=True
) if (
    (isinstance(active_df, pd.DataFrame) and not active_df.empty)
    or (isinstance(watch_df, pd.DataFrame) and not watch_df.empty)
) else pd.DataFrame()

if snapshot_source_df is not None and not snapshot_source_df.empty:
    snapshot_source_df = normalize_dataframe_for_selected_sport(snapshot_source_df, get_selected_sport())

    snapshot_top_df, snapshot_watch_df, ai_slip_df = save_generated_play_snapshots(snapshot_source_df)

    # keep old variable names alive for later UI blocks
    top_plays_df = snapshot_top_df.copy()
    watchlist_df = snapshot_watch_df.copy()

    if not snapshot_top_df.empty:
        active_df = snapshot_top_df.copy()

    if not snapshot_watch_df.empty:
        watch_df = snapshot_watch_df.copy()

    if best_row is None and not snapshot_top_df.empty:
        best_row = snapshot_top_df.iloc[0]

else:
    ai_slip_df = pd.DataFrame()

    # only clear if truly nothing exists anywhere
    existing_snapshot_df = st.session_state.get("snapshot_plays_df", pd.DataFrame())
    if not isinstance(existing_snapshot_df, pd.DataFrame) or existing_snapshot_df.empty:
        clear_generated_play_snapshots()

# ================================
# SNAPSHOT METRICS
# ================================
avg_active_edge = pd.to_numeric(active_df["edge"], errors="coerce").fillna(0).mean() if not active_df.empty else 0.0
best_score = best_row["score"] if best_row is not None and "score" in best_row else "—"
avg_true_conf = pd.to_numeric(active_df["true_confidence"], errors="coerce").fillna(0).mean() if not active_df.empty else 0.0
avg_true_prob = pd.to_numeric(active_df["true_prob"], errors="coerce").fillna(0).mean() if (not active_df.empty and "true_prob" in active_df.columns) else 0.0
total_units = pd.to_numeric(active_df["units"], errors="coerce").fillna(0).sum() if not active_df.empty else 0.0

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

    # -----------------------------------------------------
    # BUILD BEST AVAILABLE SNAPSHOT SOURCES
    # -----------------------------------------------------
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

    # -----------------------------------------------------
    # SAVE ONLY IF WE HAVE REAL DATA
    # -----------------------------------------------------
    has_any_snapshot_data = any([
        isinstance(snapshot_top_df, pd.DataFrame) and not snapshot_top_df.empty,
        isinstance(snapshot_active_df, pd.DataFrame) and not snapshot_active_df.empty,
        isinstance(snapshot_watch_df, pd.DataFrame) and not snapshot_watch_df.empty,
        isinstance(snapshot_ai_df, pd.DataFrame) and not snapshot_ai_df.empty,
        isinstance(snapshot_parlay_df, pd.DataFrame) and not snapshot_parlay_df.empty,
        isinstance(snapshot_best_row, dict) and len(snapshot_best_row) > 0,
    ])

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
    if "plays_df" in locals() and isinstance(plays_df, pd.DataFrame):
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
# TOP PLAYS
# =========================================================
if nav == "Top Plays":
    st.header("🎯 Top Plays")
    st.caption("Up to 10 qualified plays only. No filler.")

    current_api_mode = st.session_state.get("api_mode", "idle")
    persisted_plays_df = get_persisted_plays_df()
    snapshot_active_df = st.session_state.get("snapshot_active_df", pd.DataFrame())
    snapshot_top_df = st.session_state.get("snapshot_top_plays_df", pd.DataFrame())
    snapshot_last_updated = str(st.session_state.get("snapshot_last_updated", "")).strip()

    if snapshot_top_df.empty and not persisted_plays_df.empty:
        try:
            persist_generated_play_snapshots(persisted_plays_df)
            snapshot_active_df = st.session_state.get("snapshot_active_df", pd.DataFrame())
            snapshot_top_df = st.session_state.get("snapshot_top_plays_df", pd.DataFrame())
            snapshot_last_updated = str(st.session_state.get("snapshot_last_updated", "")).strip()
        except Exception:
            pass

    if snapshot_top_df.empty and not snapshot_active_df.empty:
        working_active_df = snapshot_active_df.copy()

        if "true_confidence" not in working_active_df.columns:
            working_active_df["true_confidence"] = 0.0
        if "edge" not in working_active_df.columns:
            working_active_df["edge"] = 0.0

        working_active_df["true_confidence"] = pd.to_numeric(
            working_active_df["true_confidence"], errors="coerce"
        ).fillna(0.0)
        working_active_df["edge"] = pd.to_numeric(
            working_active_df["edge"], errors="coerce"
        ).fillna(0.0)

        snapshot_top_df = working_active_df.sort_values(
            by=["true_confidence", "edge"],
            ascending=[False, False],
        ).head(int(globals().get("TOP_PLAYS_LIMIT", 10))).copy()

    if len(get_effective_odds_games()) == 0 and persisted_plays_df.empty and snapshot_top_df.empty:
        if current_api_mode == "waiting_reset":
            reset_expected = str(st.session_state.get("odds_api_reset_expected", "")).strip()
            if reset_expected:
                st.warning(f"The Odds API is waiting for reset. Expected reset around {reset_expected}.")
            else:
                st.warning("The Odds API is waiting for reset.")
        else:
            st.warning("Press 'Refresh Live Odds' in the sidebar to load live odds.")

    elif snapshot_top_df.empty:
        st.info("No Top Plays currently qualified.")
        if snapshot_last_updated:
            st.caption(f"Last saved play snapshot: {snapshot_last_updated}")

    else:
        top_df = snapshot_top_df.copy().reset_index(drop=True)

        if "true_confidence" not in top_df.columns:
            top_df["true_confidence"] = 0.0
        if "edge" not in top_df.columns:
            top_df["edge"] = 0.0
        if "units" not in top_df.columns:
            top_df["units"] = 0.0
        if "status" not in top_df.columns:
            top_df["status"] = "Active"

        top_df["true_confidence"] = pd.to_numeric(
            top_df["true_confidence"], errors="coerce"
        ).fillna(0.0)
        top_df["edge"] = pd.to_numeric(
            top_df["edge"], errors="coerce"
        ).fillna(0.0)
        top_df["units"] = pd.to_numeric(
            top_df["units"], errors="coerce"
        ).fillna(0.0)

        if snapshot_last_updated:
            st.caption(f"Last saved play snapshot: {snapshot_last_updated}")

        metric_col_1, metric_col_2, metric_col_3 = st.columns(3)
        with metric_col_1:
            st.metric("Top Plays Shown", len(top_df))
        with metric_col_2:
            avg_edge = round(float(top_df["edge"].mean()), 2) if not top_df.empty else 0.0
            st.metric("Avg Edge", avg_edge)
        with metric_col_3:
            avg_conf = round(float(top_df["true_confidence"].mean()), 1) if not top_df.empty else 0.0
            st.metric("Avg True Confidence", avg_conf)

        st.markdown("---")

        for _, row in top_df.iterrows():
            matchup = ""
            for col in ["matchup", "game", "event_name", "display_name", "teams"]:
                if col in top_df.columns:
                    value = str(row.get(col, "")).strip()
                    if value:
                        matchup = value
                        break

            if not matchup:
                home_team = str(row.get("home_team", "")).strip() if "home_team" in top_df.columns else ""
                away_team = str(row.get("away_team", "")).strip() if "away_team" in top_df.columns else ""
                if away_team and home_team:
                    matchup = f"{away_team} @ {home_team}"

            pick_text = ""
            for col in ["selection", "pick", "bet_name", "play_name", "side"]:
                if col in top_df.columns:
                    value = str(row.get(col, "")).strip()
                    if value:
                        pick_text = value
                        break

            market_text = ""
            for col in ["market", "market_type", "bet_type"]:
                if col in top_df.columns:
                    value = str(row.get(col, "")).strip()
                    if value:
                        market_text = value
                        break

            sportsbook_text = ""
            for col in ["sportsbook", "book", "bookmaker", "best_book"]:
                if col in top_df.columns:
                    value = str(row.get(col, "")).strip()
                    if value:
                        sportsbook_text = value
                        break

            odds_text = ""
            for col in ["odds", "best_price", "price", "american_odds"]:
                if col in top_df.columns:
                    value = row.get(col, "")
                    if pd.notna(value) and str(value).strip() != "":
                        odds_text = str(value).strip()
                        break

            note_text = ""
            for col in ["reason", "sportsdata_note", "context_note", "ai_note", "note"]:
                if col in top_df.columns:
                    value = str(row.get(col, "")).strip()
                    if value:
                        note_text = value
                        break

            true_conf = float(row.get("true_confidence", 0.0))
            edge_val = float(row.get("edge", 0.0))
            units_val = float(row.get("units", 0.0))
            status_text = str(row.get("status", "Active")).strip()

            with st.container():
                st.markdown(
                    f"""
                    <div style="
                        border:1px solid rgba(255,255,255,0.12);
                        border-radius:14px;
                        padding:14px;
                        margin-bottom:12px;
                    ">
                        <div style="font-size:1.02rem; font-weight:700; margin-bottom:6px;">
                            {matchup if matchup else "Matchup not available"}
                        </div>
                        <div style="font-size:0.95rem; margin-bottom:4px;">
                            <b>Pick:</b> {pick_text if pick_text else "N/A"}
                        </div>
                        <div style="font-size:0.92rem; margin-bottom:4px;">
                            <b>Market:</b> {market_text if market_text else "N/A"}
                        </div>
                        <div style="font-size:0.92rem; margin-bottom:4px;">
                            <b>Book:</b> {sportsbook_text if sportsbook_text else "N/A"} &nbsp;&nbsp; <b>Odds:</b> {odds_text if odds_text else "N/A"}
                        </div>
                        <div style="font-size:0.92rem; margin-bottom:4px;">
                            <b>Edge:</b> {edge_val:.2f}% &nbsp;&nbsp; <b>True Confidence:</b> {true_conf:.1f}% &nbsp;&nbsp; <b>Units:</b> {units_val:.2f}
                        </div>
                        <div style="font-size:0.92rem; margin-bottom:4px;">
                            <b>Status:</b> {status_text}
                        </div>
                        <div style="font-size:0.88rem; opacity:0.9;">
                            <b>Note:</b> {note_text if note_text else "No additional note available."}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
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
            persist_generated_play_snapshots(persisted_plays_df)
            snapshot_watchlist_df = st.session_state.get("snapshot_watchlist_df", pd.DataFrame())
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

        if "true_confidence" not in watch_df.columns:
            watch_df["true_confidence"] = 0.0
        if "edge" not in watch_df.columns:
            watch_df["edge"] = 0.0
        if "units" not in watch_df.columns:
            watch_df["units"] = 0.0
        if "status" not in watch_df.columns:
            watch_df["status"] = "Watchlist"

        watch_df["true_confidence"] = pd.to_numeric(
            watch_df["true_confidence"], errors="coerce"
        ).fillna(0.0)
        watch_df["edge"] = pd.to_numeric(
            watch_df["edge"], errors="coerce"
        ).fillna(0.0)
        watch_df["units"] = pd.to_numeric(
            watch_df["units"], errors="coerce"
        ).fillna(0.0)

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
            matchup = ""
            for col in ["matchup", "game", "event_name", "display_name", "teams"]:
                if col in watch_df.columns:
                    value = str(row.get(col, "")).strip()
                    if value:
                        matchup = value
                        break

            if not matchup:
                home_team = str(row.get("home_team", "")).strip() if "home_team" in watch_df.columns else ""
                away_team = str(row.get("away_team", "")).strip() if "away_team" in watch_df.columns else ""
                if away_team and home_team:
                    matchup = f"{away_team} @ {home_team}"

            pick_text = ""
            for col in ["selection", "pick", "bet_name", "play_name", "side"]:
                if col in watch_df.columns:
                    value = str(row.get(col, "")).strip()
                    if value:
                        pick_text = value
                        break

            market_text = ""
            for col in ["market", "market_type", "bet_type"]:
                if col in watch_df.columns:
                    value = str(row.get(col, "")).strip()
                    if value:
                        market_text = value
                        break

            sportsbook_text = ""
            for col in ["sportsbook", "book", "bookmaker", "best_book"]:
                if col in watch_df.columns:
                    value = str(row.get(col, "")).strip()
                    if value:
                        sportsbook_text = value
                        break

            odds_text = ""
            for col in ["odds", "best_price", "price", "american_odds"]:
                if col in watch_df.columns:
                    value = row.get(col, "")
                    if pd.notna(value) and str(value).strip() != "":
                        odds_text = str(value).strip()
                        break

            note_text = ""
            for col in ["reason", "sportsdata_note", "context_note", "ai_note", "note"]:
                if col in watch_df.columns:
                    value = str(row.get(col, "")).strip()
                    if value:
                        note_text = value
                        break

            true_conf = float(row.get("true_confidence", 0.0))
            edge_val = float(row.get("edge", 0.0))
            units_val = float(row.get("units", 0.0))
            status_text = str(row.get("status", "Watchlist")).strip()

            with st.container():
                st.markdown(
                    f"""
                    <div style="
                        border:1px solid rgba(255,255,255,0.12);
                        border-radius:14px;
                        padding:14px;
                        margin-bottom:12px;
                    ">
                        <div style="font-size:1.02rem; font-weight:700; margin-bottom:6px;">
                            {matchup if matchup else "Matchup not available"}
                        </div>
                        <div style="font-size:0.95rem; margin-bottom:4px;">
                            <b>Pick:</b> {pick_text if pick_text else "N/A"}
                        </div>
                        <div style="font-size:0.92rem; margin-bottom:4px;">
                            <b>Market:</b> {market_text if market_text else "N/A"}
                        </div>
                        <div style="font-size:0.92rem; margin-bottom:4px;">
                            <b>Book:</b> {sportsbook_text if sportsbook_text else "N/A"} &nbsp;&nbsp; <b>Odds:</b> {odds_text if odds_text else "N/A"}
                        </div>
                        <div style="font-size:0.92rem; margin-bottom:4px;">
                            <b>Edge:</b> {edge_val:.2f}% &nbsp;&nbsp; <b>True Confidence:</b> {true_conf:.1f}% &nbsp;&nbsp; <b>Units:</b> {units_val:.2f}
                        </div>
                        <div style="font-size:0.92rem; margin-bottom:4px;">
                            <b>Status:</b> {status_text}
                        </div>
                        <div style="font-size:0.88rem; opacity:0.9;">
                            <b>Note:</b> {note_text if note_text else "No additional note available."}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


# =========================================================
# AI SLIP
# =========================================================
elif nav == "AI Slip":
    st.header("🧠 AI Slip")

    if today_games:
        st.caption("Filtered Slate: " + " | ".join(today_games))
    else:
        st.caption("Using all live games returned by the API.")

    current_api_mode = st.session_state.get("api_mode", "idle")
    persisted_plays_df = get_persisted_plays_df()
    snapshot_active_df = st.session_state.get("snapshot_active_df", pd.DataFrame())
    snapshot_top_df = st.session_state.get("snapshot_top_plays_df", pd.DataFrame())
    snapshot_last_updated = str(st.session_state.get("snapshot_last_updated", "")).strip()

    if snapshot_top_df.empty and not persisted_plays_df.empty:
        try:
            persist_generated_play_snapshots(persisted_plays_df)
            snapshot_active_df = st.session_state.get("snapshot_active_df", pd.DataFrame())
            snapshot_top_df = st.session_state.get("snapshot_top_plays_df", pd.DataFrame())
            snapshot_last_updated = str(st.session_state.get("snapshot_last_updated", "")).strip()
        except Exception:
            pass

    if snapshot_top_df.empty and not snapshot_active_df.empty:
        working_active_df = snapshot_active_df.copy()

        if "true_confidence" not in working_active_df.columns:
            working_active_df["true_confidence"] = 0.0
        if "edge" not in working_active_df.columns:
            working_active_df["edge"] = 0.0

        working_active_df["true_confidence"] = pd.to_numeric(
            working_active_df["true_confidence"], errors="coerce"
        ).fillna(0.0)
        working_active_df["edge"] = pd.to_numeric(
            working_active_df["edge"], errors="coerce"
        ).fillna(0.0)

        snapshot_top_df = working_active_df.sort_values(
            by=["true_confidence", "edge"],
            ascending=[False, False],
        ).head(int(globals().get("TOP_PLAYS_LIMIT", 10))).copy()

    if len(get_effective_odds_games()) == 0 and persisted_plays_df.empty and snapshot_top_df.empty:
        if current_api_mode == "waiting_reset":
            reset_expected = str(st.session_state.get("odds_api_reset_expected", "")).strip()
            if reset_expected:
                st.warning(f"The Odds API is waiting for reset. Expected reset around {reset_expected}.")
            else:
                st.warning("The Odds API is waiting for reset.")
        else:
            st.warning("Press 'Refresh Live Odds' in the sidebar to load live odds.")

    elif snapshot_top_df.empty:
        st.info("No AI Slip available yet because no Top Plays are currently qualified.")
        if snapshot_last_updated:
            st.caption(f"Last saved play snapshot: {snapshot_last_updated}")

    else:
        top_df = snapshot_top_df.copy().reset_index(drop=True)

        for col, default_val in {
            "true_confidence": 0.0,
            "edge": 0.0,
            "units": 0.0,
            "status": "Active",
            "best_book": "",
            "best_price": "",
        }.items():
            if col not in top_df.columns:
                top_df[col] = default_val

        top_df["true_confidence"] = pd.to_numeric(top_df["true_confidence"], errors="coerce").fillna(0.0)
        top_df["edge"] = pd.to_numeric(top_df["edge"], errors="coerce").fillna(0.0)
        top_df["units"] = pd.to_numeric(top_df["units"], errors="coerce").fillna(0.0)

        def _first_nonblank(row, cols):
            for col in cols:
                if col in top_df.columns:
                    value = row.get(col, "")
                    if pd.notna(value):
                        text = str(value).strip()
                        if text and text.lower() not in ["nan", "none", "n/a"]:
                            return text
            return ""

        def _matchup_from_row(row):
            matchup_val = _first_nonblank(
                row,
                ["matchup", "game", "event_name", "display_name", "teams"],
            )
            if matchup_val:
                return matchup_val

            home_team = str(row.get("home_team", "")).strip() if "home_team" in top_df.columns else ""
            away_team = str(row.get("away_team", "")).strip() if "away_team" in top_df.columns else ""
            if away_team and home_team:
                return f"{away_team} @ {home_team}"

            return "Matchup not available"

        def _pick_from_row(row):
            return _first_nonblank(row, ["selection", "pick", "bet_name", "play_name", "side"]) or "N/A"

        def _market_from_row(row):
            return _first_nonblank(row, ["market", "market_type", "bet_type"]) or "N/A"

        def _sportsbook_from_row(row):
            for col in ["best_book", "sportsbook", "book", "bookmaker"]:
                if col in top_df.columns:
                    value = row.get(col, "")
                    if pd.notna(value):
                        text = str(value).strip()
                        if text and text.lower() not in ["nan", "none", "n/a", "sim"]:
                            return text
            return "Best available"

        def _odds_from_row(row):
            for col in ["best_price", "odds", "price", "american_odds"]:
                if col in top_df.columns:
                    value = row.get(col, "")
                    if pd.notna(value):
                        text = str(value).strip()
                        if text and text.lower() not in ["nan", "none"]:
                            return text
            return "N/A"

        def _note_from_row(row):
            return _first_nonblank(row, ["reason", "sportsdata_note", "context_note", "ai_note", "note"]) or "No additional note available."

        best_row = top_df.iloc[0].copy()

        matchup = _matchup_from_row(best_row)
        pick_text = _pick_from_row(best_row)
        market_text = _market_from_row(best_row)
        sportsbook_text = _sportsbook_from_row(best_row)
        odds_text = _odds_from_row(best_row)
        note_text = _note_from_row(best_row)

        true_conf = float(best_row.get("true_confidence", 0.0))
        edge_val = float(best_row.get("edge", 0.0))
        units_val = float(best_row.get("units", 0.0))
        risk_level = "Low" if units_val <= 0.60 else "Moderate"

        if snapshot_last_updated:
            st.caption(f"Last saved play snapshot: {snapshot_last_updated}")

        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, #111827 0%, #0f172a 100%);
                border: 1px solid rgba(255,255,255,0.16);
                border-radius: 16px;
                padding: 16px;
                margin-bottom: 14px;
                box-shadow: 0 6px 18px rgba(0,0,0,0.22);
                color: #f9fafb;
            ">
                <div style="font-size:1.10rem; font-weight:800; margin-bottom:10px; color:#ffffff;">
                    Best Current AI Play
                </div>
                <div style="font-size:1rem; margin-bottom:7px; color:#f3f4f6;">
                    <span style="color:#93c5fd; font-weight:700;">Matchup:</span> {matchup}
                </div>
                <div style="font-size:1rem; margin-bottom:7px; color:#f3f4f6;">
                    <span style="color:#93c5fd; font-weight:700;">Pick:</span> {pick_text}
                </div>
                <div style="font-size:0.96rem; margin-bottom:7px; color:#e5e7eb;">
                    <span style="color:#93c5fd; font-weight:700;">Market:</span> {market_text}
                </div>
                <div style="font-size:0.96rem; margin-bottom:7px; color:#e5e7eb;">
                    <span style="color:#93c5fd; font-weight:700;">Book:</span> {sportsbook_text}
                    &nbsp;&nbsp;
                    <span style="color:#93c5fd; font-weight:700;">Odds:</span> {odds_text}
                </div>
                <div style="font-size:0.96rem; margin-bottom:7px; color:#e5e7eb;">
                    <span style="color:#93c5fd; font-weight:700;">Edge:</span> {edge_val:.2f}%
                    &nbsp;&nbsp;
                    <span style="color:#93c5fd; font-weight:700;">True Confidence:</span> {true_conf:.1f}%
                    &nbsp;&nbsp;
                    <span style="color:#93c5fd; font-weight:700;">Units:</span> {units_val:.2f}
                </div>
                <div style="font-size:0.96rem; margin-bottom:7px; color:#e5e7eb;">
                    <span style="color:#93c5fd; font-weight:700;">Risk Level:</span> {risk_level}
                </div>
                <div style="font-size:0.93rem; line-height:1.5; color:#f3f4f6;">
                    <span style="color:#93c5fd; font-weight:700;">Note:</span> {note_text}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")
        st.subheader("Top AI Options")

        for _, row in top_df.head(5).iterrows():
            option_matchup = _matchup_from_row(row)
            option_pick = _pick_from_row(row)
            option_market = _market_from_row(row)
            option_book = _sportsbook_from_row(row)
            option_odds = _odds_from_row(row)
            option_true_conf = float(row.get("true_confidence", 0.0))
            option_edge = float(row.get("edge", 0.0))
            option_units = float(row.get("units", 0.0))

            st.markdown(
                f"""
                <div style="
                    border:1px solid rgba(17,24,39,0.10);
                    border-radius:12px;
                    padding:12px;
                    margin-bottom:10px;
                    background:#ffffff;
                    color:#111827;
                    box-shadow:0 2px 8px rgba(15,23,42,0.06);
                ">
                    <div style="font-weight:800; margin-bottom:6px; color:#111827;">
                        {option_matchup}
                    </div>
                    <div style="margin-bottom:4px; color:#111827;">
                        <b>Pick:</b> {option_pick}
                    </div>
                    <div style="margin-bottom:4px; color:#111827;">
                        <b>Market:</b> {option_market}
                    </div>
                    <div style="margin-bottom:4px; color:#111827;">
                        <b>Book:</b> {option_book} &nbsp;&nbsp; <b>Odds:</b> {option_odds}
                    </div>
                    <div style="color:#111827;">
                        <b>Edge:</b> {option_edge:.2f}% &nbsp;&nbsp;
                        <b>True Confidence:</b> {option_true_conf:.1f}% &nbsp;&nbsp;
                        <b>Units:</b> {option_units:.2f}
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

    # =========================================================
    # LOCAL HELPERS
    # =========================================================
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
        if raw in ["Won"]:
            return "Win"
        if raw in ["Lost"]:
            return "Loss"
        return "Pending"

    def _normalize_bet_type(value):
        raw = str(value).strip().lower()

        if raw in ["moneyline", "ml"]:
            return "Moneyline"
        if raw == "spread":
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

    # =========================================================
    # LOAD + CLEAN LOG DATA
    # =========================================================
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

            # =========================================================
            # ROI DASHBOARD
            # =========================================================
            st.subheader(f"📊 ROI Dashboard ({selected_sport})")
            roi_df = build_roi_dashboard(log_df)

            if roi_df.empty:
                st.info("No settled bets yet.")
            else:
                st.dataframe(roi_df, use_container_width=True, hide_index=True)

            # =========================================================
            # STAKE SIMULATOR
            # =========================================================
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

            # =========================================================
            # PERFORMANCE BREAKDOWNS
            # =========================================================
            st.subheader("📈 Performance Breakdowns")

            # =========================================================
            # DASHBOARD FILTERS
            # =========================================================
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

            # =========================================================
            # FILTERED SUMMARY CARDS
            # =========================================================
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

            # =========================================================
            # FILTERED BREAKDOWNS
            # =========================================================
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

            # =========================================================
            # BANKROLL SIMULATOR (MULTI-STAKE VIEW)
            # =========================================================
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
                    st.dataframe(
                        sim_df[
                            [
                                "selection",
                                "game",
                                "odds",
                                "result_clean",
                                "sim_profit_recalc",
                                "bankroll_curve",
                            ]
                        ],
                        use_container_width=True,
                        hide_index=True,
                    )

            # =========================================================
            # FULL LOG TABLE
            # =========================================================
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
            
            # =========================================================
            # UPDATE RESULTS
            # =========================================================
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
                                    stake_units = float(refreshed_bet_log[idx].get("stake", refreshed_bet_log[idx].get("units", 1.0)))
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

    # =========================================================
    # MANUAL BET ENTRY (CLV READY)
    # =========================================================
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

                    # -----------------------------
                    # CLV / MARKET TRACKING FIELDS
                    # -----------------------------
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
# ADAPTIVE SETTINGS + V33 SELF-LEARNING ENGINE
# =========================================================
with st.expander("⚙️ Adaptive Settings + V33 Self-Learning Engine", expanded=False):

    # =========================================================
    # SAFE SETTLED DATA INIT
    # =========================================================
    selected_sport = get_selected_sport()
    settled_df = pd.DataFrame()

    try:
        sport_bet_log = get_bet_log_for_sport(selected_sport)

        if sport_bet_log:
            _df = pd.DataFrame(sport_bet_log).copy()

            for required_col in [
                "result",
                "profit",
                "market",
                "log_category",
                "true_confidence",
                "edge",
                "play_type",
            ]:
                if required_col not in _df.columns:
                    _df[required_col] = ""

            _df["result_clean"] = (
                _df["result"]
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
            _df["profit_num"] = pd.to_numeric(_df["profit"], errors="coerce").fillna(0.0)
            _df["true_conf_num"] = pd.to_numeric(_df["true_confidence"], errors="coerce").fillna(0.0)
            _df["edge_num"] = pd.to_numeric(_df["edge"], errors="coerce").fillna(0.0)
            _df["market_clean"] = _df["market"].astype(str).str.strip().str.lower()
            _df["category_clean"] = _df["log_category"].astype(str).str.strip()
            _df["play_type_clean"] = _df["play_type"].astype(str).str.strip().str.lower()

            settled_df = _df[_df["result_clean"].isin(["win", "loss", "push"])].copy()
    except Exception:
        settled_df = pd.DataFrame()

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
    # SETTLED PERFORMANCE SUMMARY
    # =========================================================
    total_settled_bets = int(len(settled_df))
    total_wins = int((settled_df["result_clean"] == "win").sum()) if not settled_df.empty else 0
    total_losses = int((settled_df["result_clean"] == "loss").sum()) if not settled_df.empty else 0
    total_pushes = int((settled_df["result_clean"] == "push").sum()) if not settled_df.empty else 0
    total_profit = float(settled_df["profit_num"].sum()) if not settled_df.empty else 0.0
    decision_bets = total_wins + total_losses
    overall_win_rate = (total_wins / decision_bets * 100.0) if decision_bets > 0 else 0.0

    summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
    summary_col1.metric("Settled Bets", total_settled_bets)
    summary_col2.metric("Wins / Losses / Pushes", f"{total_wins} / {total_losses} / {total_pushes}")
    summary_col3.metric("Win Rate", f"{overall_win_rate:.1f}%")
    summary_col4.metric("Profit", f"{total_profit:.2f}u")

    # =========================================================
    # BUILD PLAY TYPE STATS
    # =========================================================
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
            avg_true_conf = float(row["avg_true_conf"]) if pd.notna(row["avg_true_conf"]) else 0.0
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
                            "reason": f"Trusted filter: poor results ({wins}-{losses}-{pushes}, profit {round(profit, 2)})"
                        }
                    elif profit >= 2 and win_rate >= 55:
                        bad_play_type_flags[play_type_name] = {
                            "is_filtered": False,
                            "reason": f"Trusted positive results ({wins}-{losses}-{pushes}, profit {round(profit, 2)})"
                        }
                    else:
                        bad_play_type_flags[play_type_name] = {
                            "is_filtered": False,
                            "reason": "Trusted but neutral"
                        }

                elif bets >= 5:
                    if profit <= -1.5 and win_rate < 45:
                        bad_play_type_flags[play_type_name] = {
                            "is_filtered": True,
                            "reason": f"Active filter: weak results ({wins}-{losses}-{pushes}, profit {round(profit, 2)})"
                        }
                    elif profit >= 1.5 and win_rate >= 55:
                        bad_play_type_flags[play_type_name] = {
                            "is_filtered": False,
                            "reason": f"Active positive results ({wins}-{losses}-{pushes}, profit {round(profit, 2)})"
                        }
                    else:
                        bad_play_type_flags[play_type_name] = {
                            "is_filtered": False,
                            "reason": "Active review"
                        }

                elif bets >= min_samples:
                    if profit <= -1 and win_rate < 40:
                        bad_play_type_flags[play_type_name] = {
                            "is_filtered": True,
                            "reason": f"Probation filter: very weak start ({wins}-{losses}-{pushes}, profit {round(profit, 2)})"
                        }
                    elif profit >= 1 and win_rate >= 60:
                        bad_play_type_flags[play_type_name] = {
                            "is_filtered": False,
                            "reason": f"Probation positive start ({wins}-{losses}-{pushes}, profit {round(profit, 2)})"
                        }
                    else:
                        bad_play_type_flags[play_type_name] = {
                            "is_filtered": False,
                            "reason": "Probation / still evaluating"
                        }
                else:
                    bad_play_type_flags[play_type_name] = {
                        "is_filtered": False,
                        "reason": f"Collecting data ({bets}/{min_samples})"
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
            avg_true_conf = float(row["avg_true_conf"]) if pd.notna(row["avg_true_conf"]) else 0.0
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

    # =========================================================
    # CONTROLLED LEARNING ADJUSTMENTS
    # =========================================================
    adjusted_category_thresholds = learning_state.get("category_thresholds", {}).copy()
    base_thresholds = default_learning_state["category_thresholds"].copy()

    for cat_name, fallback_val in base_thresholds.items():
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

                adjusted_category_thresholds[category_name] = _clamp(current_threshold, 0.015, 0.075)

        if total_settled_bets >= int(min_sample_size):
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
    learning_state["bad_play_type_flags"] = bad_play_type_flags if auto_filter_bad_types else {}
    learning_state["category_thresholds"] = adjusted_category_thresholds
    learning_state["learning_notes"] = learning_notes
    learning_state["last_learning_refresh"] = pd.Timestamp.now().strftime("%Y-%m-%d %I:%M:%S %p")
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

    weight_df = pd.DataFrame(
        [
            {"Factor": "True Probability", "Weight": float(learning_state["weights"].get("true_probability", 0.30))},
            {"Factor": "Price Edge", "Weight": float(learning_state["weights"].get("price_edge", 0.25))},
            {"Factor": "Market Signal", "Weight": float(learning_state["weights"].get("market_signal", 0.15))},
            {"Factor": "Matchup Quality", "Weight": float(learning_state["weights"].get("matchup_quality", 0.15))},
            {"Factor": "Historical Performance", "Weight": float(learning_state["weights"].get("historical_performance", 0.15))},
        ]
    )

    st.dataframe(weight_df, use_container_width=True, hide_index=True)

    # =========================================================
    # CATEGORY THRESHOLDS TABLE
    # =========================================================
    st.markdown("#### 📊 Adaptive Category Thresholds")

    threshold_rows = []
    for category_name in ["Top Plays", "AI Picks", "AI Parlays", "Watchlist"]:
        threshold_rows.append(
            {
                "Category": category_name,
                "Threshold": round(float(adjusted_category_thresholds.get(category_name, 0.03)), 4),
                "Status": _status_from_threshold(
                    adjusted_category_thresholds.get(category_name, 0.03),
                    base_thresholds.get(category_name, 0.03),
                ),
            }
        )

    threshold_df = pd.DataFrame(threshold_rows)
    st.dataframe(threshold_df, use_container_width=True, hide_index=True)

    # =========================================================
    # PLAY TYPE PERFORMANCE TABLE
    # =========================================================
    st.markdown("#### 🧠 Play Type Performance")

    if play_type_stats:
        play_type_stats_df = pd.DataFrame(
            [
                {
                    "Play Type": play_type_name,
                    "Bets": stats["sample_size"],
                    "Wins": stats["wins"],
                    "Losses": stats["losses"],
                    "Pushes": stats.get("pushes", 0),
                    "Win Rate %": stats["win_rate"],
                    "Profit": stats["profit"],
                    "ROI/Bet": stats["roi_per_bet"],
                    "Avg True Conf": stats["avg_true_conf"],
                    "Avg Edge": stats["avg_edge"],
                    "Filtered": "Yes" if learning_state.get("bad_play_type_flags", {}).get(play_type_name, {}).get("is_filtered", False) else "No",
                }
                for play_type_name, stats in play_type_stats.items()
            ]
        ).sort_values(by=["Profit", "Win Rate %"], ascending=[False, False])

        st.dataframe(play_type_stats_df, use_container_width=True, hide_index=True)
    else:
        st.info("No settled play-type data yet for this sport.")

    # =========================================================
    # CATEGORY PERFORMANCE TABLE
    # =========================================================
    st.markdown("#### 📚 Category Performance")

    if category_stats:
        category_stats_df = pd.DataFrame(
            [
                {
                    "Category": category_name,
                    "Bets": stats["sample_size"],
                    "Wins": stats["wins"],
                    "Losses": stats["losses"],
                    "Pushes": stats.get("pushes", 0),
                    "Win Rate %": stats["win_rate"],
                    "Profit": stats["profit"],
                    "ROI/Bet": stats["roi_per_bet"],
                    "Avg True Conf": stats["avg_true_conf"],
                    "Avg Edge": stats["avg_edge"],
                    "Stage": stats["stage"],
                }
                for category_name, stats in category_stats.items()
            ]
        ).sort_values(by=["Profit", "Win Rate %"], ascending=[False, False])

        st.dataframe(category_stats_df, use_container_width=True, hide_index=True)
    else:
        st.info("No settled category data yet for this sport.")

    # =========================================================
    # LEARNING NOTES
    # =========================================================
    st.markdown("#### 📝 Learning Notes")

    if learning_state.get("learning_notes"):
        for note in learning_state["learning_notes"]:
            st.caption(f"• {note}")
    else:
        st.caption("• Learning engine is active, but more settled samples are needed before stronger adjustments are made.")

    st.caption(
        f"Last learning refresh: {learning_state.get('last_learning_refresh', 'Not available')}"
    )

    # =========================================================
    # LEARNING WEIGHTS DISPLAY
    # =========================================================
    st.markdown("### Learning Weights")

    weights = learning_state.get("weights", {})

    c1, c2 = st.columns(2)
    with c1:
        st.metric("True Prob", f"{weights.get('true_probability', 0) * 100:.1f}%")
        st.metric("Price Edge", f"{weights.get('price_edge', 0) * 100:.1f}%")
        st.metric("Market Signal", f"{weights.get('market_signal', 0) * 100:.1f}%")
    with c2:
        st.metric("Matchup Quality", f"{weights.get('matchup_quality', 0) * 100:.1f}%")
        st.metric("History", f"{weights.get('historical_performance', 0) * 100:.1f}%")
        st.metric("Min Samples", str(min_samples))

    last_update = learning_state.get("last_update")
    st.caption(f"Last learning update: {last_update if last_update else 'None'}")
    st.caption(f"Learning scope: {selected_sport}")

    # =========================================================
    # PLAY TYPE PERFORMANCE / AUTO-FILTER STATUS
    # =========================================================
    st.markdown("### Play Type Performance / Auto-Filter Status")

    if play_type_stats:
        pt_rows = []
        for play_type_name, stats in play_type_stats.items():
            flag_info = learning_state.get("bad_play_type_flags", {}).get(play_type_name, {})
            pt_rows.append({
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
                "Reason": flag_info.get("reason", "")
            })

        pt_df = pd.DataFrame(pt_rows).sort_values(
            by=["Filtered", "Profit", "Win Rate %"],
            ascending=[False, False, False]
        )
        st.dataframe(pt_df, use_container_width=True, hide_index=True)
    else:
        st.info(f"No graded {selected_sport} bet history yet. The self-learning engine will activate after enough settled bets.")

    # =========================================================
    # CATEGORY PERFORMANCE SNAPSHOT
    # =========================================================
    st.markdown("### Category Performance Snapshot")

    if category_stats:
        cat_rows = []
        for category_name, stats in category_stats.items():
            cat_rows.append({
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
            })

        cat_df = pd.DataFrame(cat_rows).sort_values(
            by=["Profit", "Win Rate %"],
            ascending=[False, False]
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
