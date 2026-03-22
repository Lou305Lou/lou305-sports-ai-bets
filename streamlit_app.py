
import io
import os
import math
import json
import itertools
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st


# =========================
# CONFIG
# =========================
APP_TITLE = "Sports AI Betting Dashboard — V21"
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

BET_LOG_PATH = DATA_DIR / "bet_log.csv"
SETTINGS_PATH = DATA_DIR / "settings.json"
MODEL_MEMORY_PATH = DATA_DIR / "model_memory.csv"
PORTFOLIO_HISTORY_PATH = DATA_DIR / "portfolio_history.csv"
MODEL_VOTES_PATH = DATA_DIR / "model_votes_history.csv"
MODEL_PERFORMANCE_PATH = DATA_DIR / "model_performance.csv"
MODEL_SEGMENT_PERFORMANCE_PATH = DATA_DIR / "model_segment_performance.csv"
EXECUTION_BOARD_PATH = DATA_DIR / "execution_board.csv"
PLACED_BETS_PATH = DATA_DIR / "placed_bets.csv"
EXECUTION_SETTLEMENT_PATH = DATA_DIR / "execution_settlement.csv"
LIVE_ODDS_PATH = DATA_DIR / "live_odds_snapshot.csv"
LINE_MOVEMENT_PATH = DATA_DIR / "line_movement_monitor.csv"
EXECUTION_REFRESH_PATH = DATA_DIR / "execution_refresh_board.csv"
BOOK_SCORE_PATH = DATA_DIR / "book_shopping_scores.csv"
CLOSING_LINE_INTEL_PATH = DATA_DIR / "closing_line_intelligence.csv"


# =========================
# PAGE
# =========================
st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title(APP_TITLE)
st.caption("V21: Closing line intelligence + book shopping score with book quality ranking, CLV capture analysis, and smarter shop-now vs wait guidance")


# =========================
# HELPERS
# =========================
def safe_read_csv(path: Path, columns=None):
    try:
        if path.exists():
            return pd.read_csv(path)
    except Exception:
        pass
    return pd.DataFrame(columns=columns if columns is not None else [])


def safe_write_csv(df: pd.DataFrame, path: Path):
    try:
        df.to_csv(path, index=False)
    except Exception:
        pass


def safe_to_numeric(series, default=np.nan):
    try:
        return pd.to_numeric(series, errors="coerce")
    except Exception:
        return pd.Series([default] * len(series))


def normalize_text(x):
    try:
        return str(x).strip()
    except Exception:
        return ""


def ensure_columns(df: pd.DataFrame, required_cols):
    out = df.copy()
    for c in required_cols:
        if c not in out.columns:
            out[c] = np.nan
    return out


def pct(x):
    try:
        return f"{100 * float(x):.1f}%"
    except Exception:
        return "—"


def american_to_decimal(odds):
    try:
        odds = float(odds)
        if odds > 0:
            return 1 + odds / 100.0
        return 1 + 100.0 / abs(odds)
    except Exception:
        return np.nan


def american_implied_prob(odds):
    try:
        odds = float(odds)
        if odds > 0:
            return 100.0 / (odds + 100.0)
        return abs(odds) / (abs(odds) + 100.0)
    except Exception:
        return np.nan


def decimal_to_american(decimal_odds):
    try:
        d = float(decimal_odds)
        if d <= 1:
            return np.nan
        if d >= 2:
            return int(round((d - 1) * 100))
        return int(round(-100 / (d - 1)))
    except Exception:
        return np.nan


def compute_ev(prob, odds):
    try:
        dec = american_to_decimal(odds)
        if np.isnan(dec):
            return np.nan
        return prob * (dec - 1) - (1 - prob)
    except Exception:
        return np.nan


def kelly_fraction(p, odds_american):
    try:
        p = float(p)
        dec = american_to_decimal(odds_american)
        if np.isnan(dec) or dec <= 1:
            return 0.0
        b = dec - 1
        q = 1 - p
        k = (b * p - q) / b
        return max(0.0, k)
    except Exception:
        return 0.0


def score_to_emoji(score):
    try:
        s = float(score)
    except Exception:
        return "⚪"
    if s >= 85:
        return "🟢"
    if s >= 75:
        return "🟡"
    if s >= 65:
        return "🟠"
    return "⚪"


def letter_grade(score):
    try:
        s = float(score)
    except Exception:
        return "D"
    if s >= 85:
        return "A"
    if s >= 75:
        return "B"
    if s >= 65:
        return "C"
    return "D"


def tier_label(score):
    try:
        s = float(score)
    except Exception:
        return "Tier 4"
    if s >= 85:
        return "Tier 1"
    if s >= 75:
        return "Tier 2"
    if s >= 65:
        return "Tier 3"
    return "Tier 4"


def market_bucket(market_text):
    m = normalize_text(market_text).lower()
    if "player" in m or "prop" in m:
        return "Player Props"
    if "spread" in m:
        return "Spreads"
    if "total" in m:
        return "Totals"
    if "moneyline" in m or m == "ml" or "mainline" in m:
        return "Moneylines"
    return "Other"


def clv_value(odds, closing_odds):
    try:
        open_ip = american_implied_prob(odds)
        close_ip = american_implied_prob(closing_odds)
        return close_ip - open_ip
    except Exception:
        return np.nan


def result_to_binary(result):
    r = normalize_text(result).lower()
    if r == "win":
        return 1.0
    if r == "loss":
        return 0.0
    return np.nan


def calculate_profit_units(result, odds, units):
    try:
        odds = float(odds)
        units = float(units)
        result = normalize_text(result).lower()
        if result == "win":
            if odds > 0:
                return units * odds / 100.0
            return units * 100.0 / abs(odds)
        if result == "loss":
            return -units
        if result in {"push", "void"}:
            return 0.0
    except Exception:
        pass
    return np.nan


def probability_bucket(prob):
    try:
        p = float(prob)
    except Exception:
        return "unknown"
    if np.isnan(p):
        return "unknown"
    p = max(0.0, min(0.999, p))
    lower = math.floor(p * 10) / 10.0
    upper = min(1.0, lower + 0.1)
    return f"{lower:.1f}-{upper:.1f}"


def edge_bucket(edge):
    try:
        e = float(edge)
    except Exception:
        return "unknown"
    if np.isnan(e):
        return "unknown"
    if e < 1:
        return "<1"
    if e < 2:
        return "1-2"
    if e < 4:
        return "2-4"
    if e < 6:
        return "4-6"
    return "6+"


def odds_bucket(odds):
    try:
        o = float(odds)
    except Exception:
        return "unknown"
    if np.isnan(o):
        return "unknown"
    if o <= -200:
        return "-200 or worse"
    if o < -120:
        return "-199 to -121"
    if o < -105:
        return "-120 to -106"
    if o <= 100:
        return "-105 to +100"
    if o <= 150:
        return "+101 to +150"
    return "+151+"


def build_profile_key(row):
    sport = normalize_text(row.get("sport", ""))
    market = normalize_text(row.get("market_bucket", row.get("market", "")))
    bucket = probability_bucket(row.get("model_prob", np.nan))
    edge_b = edge_bucket(row.get("edge", np.nan))
    odds_b = odds_bucket(row.get("odds", np.nan))
    return f"{sport}|{market}|p:{bucket}|e:{edge_b}|o:{odds_b}"


def build_bet_id(row):
    parts = [
        normalize_text(row.get("sport", "")),
        normalize_text(row.get("event", "")),
        normalize_text(row.get("market", "")),
        normalize_text(row.get("bet_type", "")),
        normalize_text(row.get("selection", "")),
        normalize_text(row.get("book", "")),
        normalize_text(row.get("line", "")),
        normalize_text(row.get("odds", "")),
    ]
    return "|".join(parts)


def score_to_risk_band(score):
    try:
        s = float(score)
    except Exception:
        return "High"
    if s >= 85:
        return "Low"
    if s >= 75:
        return "Medium"
    return "High"


MODEL_NAMES = ["Model_A", "Model_B", "Model_C", "Model_D", "Model_E"]


def default_model_thresholds():
    return {m: 0.015 for m in MODEL_NAMES}


# =========================
# CLEANING
# =========================
def clean_input_df(df: pd.DataFrame):
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    rename_map = {
        "game": "event",
        "matchup": "event",
        "player": "selection",
        "name": "selection",
        "sportsbook": "book",
        "price": "odds",
        "probability": "model_prob",
        "hit_rate": "model_prob",
        "confidence": "score",
        "market_type": "market",
        "pick_type": "bet_type",
        "proj": "projection",
        "team": "selection",
        "side": "selection",
        "points": "line",
        "prop_line": "line",
    }
    df = df.rename(columns={c: rename_map[c] for c in df.columns if c in rename_map})
    required = ["sport", "event", "market", "bet_type", "selection", "book", "odds", "projection", "line", "edge", "model_prob", "score", "consensus"]
    df = ensure_columns(df, required)
    numeric_cols = ["odds", "projection", "line", "edge", "model_prob", "score", "consensus"]
    for c in numeric_cols:
        df[c] = safe_to_numeric(df[c])

    if df["model_prob"].dropna().max() > 1.5:
        df["model_prob"] = df["model_prob"] / 100.0

    df["implied_prob"] = df["odds"].apply(american_implied_prob)
    if df["edge"].isna().all():
        df["edge"] = df["projection"] - df["line"]
    if df["score"].isna().all():
        df["score"] = (
            df["model_prob"].fillna(0) * 55
            + df["edge"].fillna(0).clip(lower=0) * 4
            + df["consensus"].fillna(0) * 6
            + df["odds"].apply(lambda x: 10 if -200 <= x <= 150 else 0).fillna(0)
        ).clip(0, 99)
    if df["consensus"].isna().all():
        df["consensus"] = np.where(df["score"] >= 85, 5, np.where(df["score"] >= 75, 4, np.where(df["score"] >= 65, 3, 2)))

    df["tier"] = df["score"].apply(tier_label)
    df["grade"] = df["score"].apply(letter_grade)
    df["market_bucket"] = df["market"].apply(market_bucket)
    df["profile_key"] = df.apply(build_profile_key, axis=1)
    df["bet_id"] = df.apply(build_bet_id, axis=1)
    df["date_added"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return df


def clean_live_odds_df(df: pd.DataFrame):
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    rename_map = {
        "game": "event",
        "matchup": "event",
        "sportsbook": "book",
        "player": "selection",
        "name": "selection",
        "price": "current_odds",
        "odds": "current_odds",
        "line": "current_line",
        "prop_line": "current_line",
        "market_type": "market",
        "pick_type": "bet_type",
    }
    df = df.rename(columns={c: rename_map[c] for c in df.columns if c in rename_map})
    required = ["sport", "event", "market", "bet_type", "selection", "book", "current_odds", "current_line"]
    df = ensure_columns(df, required)
    for c in ["current_odds", "current_line"]:
        df[c] = safe_to_numeric(df[c])
    return df


# =========================
# STORAGE
# =========================
def load_settings():
    defaults = {
        "bankroll": 1000.0,
        "kelly_multiplier": 0.35,
        "max_unit": 2.0,
        "base_unit_pct": 0.01,
        "min_consensus": 3,
        "min_parlay_legs": 2,
        "max_parlay_legs": 4,
        "default_odds_min": -200,
        "default_odds_max": 150,
        "learning_min_samples": 15,
        "book_min_samples": 10,
        "profile_min_samples": 12,
        "calibration_min_samples": 20,
        "clv_min_samples": 12,
        "correlation_penalty_on": True,
        "auto_prioritize_profitable_markets": True,
        "sharp_mode_auto": True,
        "sharp_mode_clv_threshold": 0.01,
        "sharp_mode_roi_threshold": 0.05,
        "suppress_losing_profiles": True,
        "max_profile_penalty": 0.18,
        "portfolio_max_total_units": 8.0,
        "portfolio_max_per_bet_units": 2.0,
        "portfolio_max_per_event_units": 2.5,
        "portfolio_max_per_market_pct": 0.40,
        "portfolio_max_per_book_pct": 0.45,
        "portfolio_max_bets": 8,
        "portfolio_target_risk": "Balanced",
        "model_consensus_min": 3,
        "use_model_weights": True,
        "debate_penalty_on": True,
        "adaptive_thresholds_on": True,
        "adaptive_segments_on": True,
        "adaptive_min_samples": 10,
        "execution_max_singles": 8,
        "execution_max_parlays": 4,
        "execution_min_priority": 75.0,
        "execution_auto_lock_elite": False,
        "movement_wait_threshold": 0.015,
        "movement_pass_threshold": -0.02,
        "line_move_points_alert": 1.0,
        "refresh_auto_raise_units": True,
        "refresh_auto_reduce_when_worse": True,
        "refresh_min_current_ev": 0.00,
        "refresh_priority_floor": 70.0,
        "refresh_improve_unit_boost": 1.10,
        "refresh_worse_unit_cut": 0.80,
        "book_score_min_samples": 8,
        "book_score_weight_price": 0.40,
        "book_score_weight_clv": 0.35,
        "book_score_weight_roi": 0.25,
    }
    try:
        if SETTINGS_PATH.exists():
            with open(SETTINGS_PATH, "r") as f:
                saved = json.load(f)
            defaults.update(saved)
    except Exception:
        pass
    return defaults


def save_settings(settings):
    try:
        with open(SETTINGS_PATH, "w") as f:
            json.dump(settings, f, indent=2)
    except Exception:
        pass


def load_bet_log():
    cols = [
        "bet_id", "date_added", "sport", "event", "market", "market_bucket",
        "bet_type", "selection", "book", "odds", "closing_odds", "projection", "line",
        "edge", "model_prob", "calibrated_prob", "implied_prob", "ev", "score",
        "priority_score", "consensus", "model_yes_votes", "weighted_yes_votes",
        "debate_label", "tier", "recommended_units", "sharp_flag",
        "profile_key", "result", "profit_units", "clv", "notes"
    ]
    return safe_read_csv(BET_LOG_PATH, cols)


def save_bet_log(df):
    safe_write_csv(df, BET_LOG_PATH)


def load_model_memory():
    cols = [
        "date", "market", "market_bucket", "sport", "book", "bet_type", "selection", "event",
        "odds", "model_prob", "calibrated_prob", "closing_odds", "result", "units",
        "profit_units", "clv", "profile_key", "sharp_flag"
    ]
    return safe_read_csv(MODEL_MEMORY_PATH, cols)


def save_model_memory(df):
    safe_write_csv(df, MODEL_MEMORY_PATH)


def load_model_votes_history():
    cols = [
        "saved_at", "bet_id", "sport", "event", "market_bucket", "selection", "bet_type",
        "book", "odds", "result",
        "Model_A_prob", "Model_A_vote", "Model_B_prob", "Model_B_vote",
        "Model_C_prob", "Model_C_vote", "Model_D_prob", "Model_D_vote",
        "Model_E_prob", "Model_E_vote"
    ]
    return safe_read_csv(MODEL_VOTES_PATH, cols)


def save_model_votes_history(df):
    safe_write_csv(df, MODEL_VOTES_PATH)


def load_model_performance():
    cols = ["model_name", "bets", "wins", "losses", "win_rate", "avg_prob", "brier_proxy", "weight", "status", "adaptive_threshold"]
    return safe_read_csv(MODEL_PERFORMANCE_PATH, cols)


def save_model_performance(df):
    safe_write_csv(df, MODEL_PERFORMANCE_PATH)


def load_model_segment_performance():
    cols = ["model_name", "sport", "market_bucket", "bets", "wins", "losses", "win_rate", "avg_prob", "brier_proxy", "segment_weight", "segment_threshold", "segment_status"]
    return safe_read_csv(MODEL_SEGMENT_PERFORMANCE_PATH, cols)


def save_model_segment_performance(df):
    safe_write_csv(df, MODEL_SEGMENT_PERFORMANCE_PATH)


def load_execution_board():
    cols = [
        "execution_id", "created_at", "bet_id", "ticket_type", "slip_group", "sport", "event",
        "market_bucket", "selection", "bet_type", "book", "odds", "line", "calibrated_prob", "ev",
        "score", "priority_score", "model_yes_votes", "weighted_consensus_ratio",
        "recommended_units", "approved_units", "execution_priority", "status",
        "locked_flag", "review_flag", "placed_flag", "ai_recommended", "user_placed",
        "difference_flag", "notes"
    ]
    return safe_read_csv(EXECUTION_BOARD_PATH, cols)


def save_execution_board(df):
    safe_write_csv(df, EXECUTION_BOARD_PATH)


def load_execution_settlement():
    cols = [
        "execution_id", "bet_id", "ticket_type", "status_at_execution", "sport", "event", "selection",
        "bet_type", "book", "odds", "result", "ai_recommended_units", "placed_units",
        "ai_profit_units", "placed_profit_units", "unit_delta", "profit_delta",
        "placement_alignment", "difference_flag", "linked_tracker_row"
    ]
    return safe_read_csv(EXECUTION_SETTLEMENT_PATH, cols)


def save_execution_settlement(df):
    safe_write_csv(df, EXECUTION_SETTLEMENT_PATH)


def load_live_odds():
    cols = ["captured_at", "sport", "event", "market", "bet_type", "selection", "book", "current_odds", "current_line"]
    return safe_read_csv(LIVE_ODDS_PATH, cols)


def save_live_odds(df):
    safe_write_csv(df, LIVE_ODDS_PATH)


def load_line_movement_monitor():
    cols = [
        "captured_at", "bet_id", "sport", "event", "market_bucket", "selection", "bet_type", "rec_book",
        "rec_odds", "best_current_book", "best_current_odds", "best_current_line",
        "odds_change", "implied_prob_change", "line_change", "timing_signal",
        "best_execution_signal", "movement_note"
    ]
    return safe_read_csv(LINE_MOVEMENT_PATH, cols)


def save_line_movement_monitor(df):
    safe_write_csv(df, LINE_MOVEMENT_PATH)


def load_execution_refresh():
    cols = [
        "refreshed_at", "execution_id", "bet_id", "ticket_type", "sport", "event", "selection", "bet_type",
        "original_book", "original_odds", "current_best_book", "current_best_odds", "current_best_line",
        "original_ev", "current_ev", "ev_delta", "original_execution_priority", "current_execution_priority",
        "priority_delta", "original_units", "refreshed_units", "unit_delta", "timing_signal",
        "refresh_signal", "still_qualifies", "refresh_note"
    ]
    return safe_read_csv(EXECUTION_REFRESH_PATH, cols)


def save_execution_refresh(df):
    safe_write_csv(df, EXECUTION_REFRESH_PATH)


def load_book_scores():
    cols = ["book", "sport", "bets", "avg_clv", "roi", "avg_market_price_score", "book_shopping_score", "book_quality_label"]
    return safe_read_csv(BOOK_SCORE_PATH, cols)


def save_book_scores(df):
    safe_write_csv(df, BOOK_SCORE_PATH)


def load_closing_line_intel():
    cols = [
        "captured_at", "execution_id", "bet_id", "sport", "event", "selection", "bet_type",
        "recommended_book", "recommended_odds", "best_live_book", "best_live_odds",
        "closing_book", "closing_odds", "rec_vs_close_clv", "live_vs_close_clv",
        "best_source", "shopping_signal", "book_shopping_score", "intel_note"
    ]
    return safe_read_csv(CLOSING_LINE_INTEL_PATH, cols)


def save_closing_line_intel(df):
    safe_write_csv(df, CLOSING_LINE_INTEL_PATH)


# =========================
# LEARNING / BOOK SCORING
# =========================
def summarize_market_performance(memory_df, min_samples=15):
    cols = ["sport", "market", "market_bucket", "bets", "units", "profit_units", "roi", "win_rate", "avg_clv", "market_signal"]
    if len(memory_df) == 0:
        return pd.DataFrame(columns=cols)
    m = ensure_columns(memory_df.copy(), ["sport", "market", "market_bucket", "units", "profit_units", "result", "clv"])
    settled = m[m["result"].astype(str).str.lower().isin(["win", "loss", "push", "void"])].copy()
    if len(settled) == 0:
        return pd.DataFrame(columns=cols)
    grp = (
        settled.groupby(["sport", "market", "market_bucket"], dropna=False)
        .agg(
            bets=("result", "count"),
            units=("units", "sum"),
            profit_units=("profit_units", "sum"),
            wins=("result", lambda s: (s.astype(str).str.lower() == "win").sum()),
            avg_clv=("clv", "mean"),
        )
        .reset_index()
    )
    grp["win_rate"] = grp["wins"] / grp["bets"].replace(0, np.nan)
    grp["roi"] = grp["profit_units"] / grp["units"].replace(0, np.nan)
    grp["market_signal"] = np.where(
        (grp["bets"] >= min_samples) & (grp["roi"] > 0.08), "Prioritize",
        np.where((grp["bets"] >= min_samples) & (grp["roi"] < -0.08), "De-prioritize", "Neutral")
    )
    return grp.drop(columns=["wins"])


def summarize_book_performance(memory_df, min_samples=10):
    cols = ["sport", "book", "bets", "units", "profit_units", "roi", "win_rate", "avg_clv", "temperature"]
    if len(memory_df) == 0:
        return pd.DataFrame(columns=cols)
    m = ensure_columns(memory_df.copy(), ["sport", "book", "units", "profit_units", "result", "clv"])
    settled = m[m["result"].astype(str).str.lower().isin(["win", "loss", "push", "void"])].copy()
    if len(settled) == 0:
        return pd.DataFrame(columns=cols)
    grp = (
        settled.groupby(["sport", "book"], dropna=False)
        .agg(
            bets=("result", "count"),
            units=("units", "sum"),
            profit_units=("profit_units", "sum"),
            wins=("result", lambda s: (s.astype(str).str.lower() == "win").sum()),
            avg_clv=("clv", "mean"),
        )
        .reset_index()
    )
    grp["win_rate"] = grp["wins"] / grp["bets"].replace(0, np.nan)
    grp["roi"] = grp["profit_units"] / grp["units"].replace(0, np.nan)
    grp["temperature"] = np.where(
        (grp["bets"] >= min_samples) & (grp["roi"] > 0.08), "Hot",
        np.where((grp["bets"] >= min_samples) & (grp["roi"] < -0.08), "Cold", "Neutral")
    )
    return grp.drop(columns=["wins"])


def build_calibration_profile(memory_df, min_samples=20):
    cols = ["sport", "market_bucket", "prob_bucket", "bets", "pred_avg", "actual_win_rate", "delta", "multiplier"]
    if len(memory_df) == 0:
        return pd.DataFrame(columns=cols)
    m = ensure_columns(memory_df.copy(), ["sport", "market_bucket", "model_prob", "result"])
    m["actual_result"] = m["result"].apply(result_to_binary)
    m = m[m["actual_result"].notna() & m["model_prob"].notna()].copy()
    if len(m) == 0:
        return pd.DataFrame(columns=cols)
    m["prob_bucket"] = m["model_prob"].apply(probability_bucket)
    grp = (
        m.groupby(["sport", "market_bucket", "prob_bucket"], dropna=False)
        .agg(bets=("actual_result", "count"), pred_avg=("model_prob", "mean"), actual_win_rate=("actual_result", "mean"))
        .reset_index()
    )
    grp["delta"] = grp["actual_win_rate"] - grp["pred_avg"]
    grp["multiplier"] = grp.apply(lambda row: 1.0 if row["bets"] < min_samples or float(row["pred_avg"]) <= 0 else float(np.clip(float(row["actual_win_rate"]) / float(row["pred_avg"]), 0.85, 1.15)), axis=1)
    return grp[cols]


def summarize_profile_performance(memory_df, min_samples=12):
    cols = ["profile_key", "sport", "market_bucket", "bets", "units", "profit_units", "roi", "win_rate", "avg_clv", "profile_signal"]
    if len(memory_df) == 0:
        return pd.DataFrame(columns=cols)
    m = ensure_columns(memory_df.copy(), ["profile_key", "sport", "market_bucket", "units", "profit_units", "result", "clv"])
    settled = m[m["result"].astype(str).str.lower().isin(["win", "loss", "push", "void"])].copy()
    if len(settled) == 0:
        return pd.DataFrame(columns=cols)
    grp = (
        settled.groupby(["profile_key", "sport", "market_bucket"], dropna=False)
        .agg(
            bets=("result", "count"),
            units=("units", "sum"),
            profit_units=("profit_units", "sum"),
            wins=("result", lambda s: (s.astype(str).str.lower() == "win").sum()),
            avg_clv=("clv", "mean"),
        )
        .reset_index()
    )
    grp["win_rate"] = grp["wins"] / grp["bets"].replace(0, np.nan)
    grp["roi"] = grp["profit_units"] / grp["units"].replace(0, np.nan)
    grp["profile_signal"] = np.where(
        (grp["bets"] >= min_samples) & (grp["roi"] > 0.08), "Boost",
        np.where((grp["bets"] >= min_samples) & (grp["roi"] < -0.10), "Suppress", "Neutral")
    )
    return grp.drop(columns=["wins"])


def evaluate_sharp_mode(memory_df, settings):
    if len(memory_df) == 0:
        return {"sharp_mode": False, "roi": np.nan, "avg_clv": np.nan, "samples": 0}
    settled = memory_df[memory_df["result"].astype(str).str.lower().isin(["win", "loss", "push", "void"])].copy()
    if len(settled) < max(int(settings["clv_min_samples"]), 8):
        return {"sharp_mode": False, "roi": np.nan, "avg_clv": np.nan, "samples": len(settled)}
    units = settled["units"].fillna(0).sum()
    roi = settled["profit_units"].fillna(0).sum() / max(units, 1e-9)
    avg_clv = settled["clv"].dropna().mean() if "clv" in settled.columns else np.nan
    sharp = pd.notna(avg_clv) and avg_clv >= float(settings["sharp_mode_clv_threshold"]) and roi >= float(settings["sharp_mode_roi_threshold"])
    return {"sharp_mode": bool(sharp), "roi": roi, "avg_clv": avg_clv, "samples": len(settled)}


def build_book_shopping_scores(memory_df, live_df, settings):
    cols = ["book", "sport", "bets", "avg_clv", "roi", "avg_market_price_score", "book_shopping_score", "book_quality_label"]
    if len(memory_df) == 0 and len(live_df) == 0:
        return pd.DataFrame(columns=cols)

    mem = ensure_columns(memory_df.copy(), ["sport", "book", "units", "profit_units", "clv", "result"])
    settled = mem[mem["result"].astype(str).str.lower().isin(["win", "loss", "push", "void"])].copy()

    perf = pd.DataFrame(columns=["sport", "book", "bets", "avg_clv", "roi"])
    if len(settled):
        perf = (
            settled.groupby(["sport", "book"], dropna=False)
            .agg(
                bets=("result", "count"),
                units=("units", "sum"),
                profit_units=("profit_units", "sum"),
                avg_clv=("clv", "mean"),
            )
            .reset_index()
        )
        perf["roi"] = perf["profit_units"] / perf["units"].replace(0, np.nan)
        perf = perf[["sport", "book", "bets", "avg_clv", "roi"]]

    price_score = pd.DataFrame(columns=["sport", "book", "avg_market_price_score"])
    if len(live_df):
        live = live_df.copy()
        live["current_odds"] = safe_to_numeric(live["current_odds"])
        live["key"] = (
            live["sport"].astype(str) + "|" +
            live["event"].astype(str) + "|" +
            live["bet_type"].astype(str) + "|" +
            live["selection"].astype(str)
        )
        live["best_in_market"] = live.groupby("key")["current_odds"].transform("max")
        live["price_gap"] = live["best_in_market"] - live["current_odds"]
        live["market_price_score"] = (100 - live["price_gap"].fillna(0).clip(lower=0) * 2).clip(lower=40, upper=100)
        price_score = (
            live.groupby(["sport", "book"], dropna=False)
            .agg(avg_market_price_score=("market_price_score", "mean"))
            .reset_index()
        )

    merged = pd.merge(perf, price_score, on=["sport", "book"], how="outer")
    merged = ensure_columns(merged, ["bets", "avg_clv", "roi", "avg_market_price_score"])
    merged["bets"] = merged["bets"].fillna(0)
    merged["avg_clv"] = merged["avg_clv"].fillna(0.0)
    merged["roi"] = merged["roi"].fillna(0.0)
    merged["avg_market_price_score"] = merged["avg_market_price_score"].fillna(70.0)

    min_samples = float(settings["book_score_min_samples"])
    w_price = float(settings["book_score_weight_price"])
    w_clv = float(settings["book_score_weight_clv"])
    w_roi = float(settings["book_score_weight_roi"])

    merged["clv_component"] = (50 + merged["avg_clv"] * 800).clip(lower=0, upper=100)
    merged["roi_component"] = (50 + merged["roi"] * 250).clip(lower=0, upper=100)
    merged["sample_discount"] = np.where(merged["bets"] >= min_samples, 1.0, merged["bets"] / np.maximum(min_samples, 1))
    merged["book_shopping_score"] = (
        (merged["avg_market_price_score"] * w_price) +
        (merged["clv_component"] * w_clv) +
        (merged["roi_component"] * w_roi)
    ) * merged["sample_discount"] + (1 - merged["sample_discount"]) * 55

    merged["book_quality_label"] = np.where(
        merged["book_shopping_score"] >= 80, "Elite",
        np.where(merged["book_shopping_score"] >= 70, "Strong",
                 np.where(merged["book_shopping_score"] >= 60, "Playable", "Weak"))
    )
    return merged[cols].sort_values(["book_shopping_score", "avg_clv"], ascending=[False, False])


# =========================
# MODEL PERFORMANCE / VOTING
# =========================
def default_model_performance():
    return pd.DataFrame([{
        "model_name": m,
        "bets": 0, "wins": 0, "losses": 0, "win_rate": np.nan, "avg_prob": np.nan,
        "brier_proxy": np.nan, "weight": 1.0, "status": "Neutral",
        "adaptive_threshold": default_model_thresholds()[m]
    } for m in MODEL_NAMES])


def initialize_model_performance():
    perf = load_model_performance()
    if len(perf) == 0:
        perf = default_model_performance()
        save_model_performance(perf)
    else:
        existing = set(perf["model_name"].astype(str).tolist())
        add_rows = []
        for m in MODEL_NAMES:
            if m not in existing:
                add_rows.append(default_model_performance().query("model_name == @m"))
        if add_rows:
            perf = pd.concat([perf] + add_rows, ignore_index=True)
            save_model_performance(perf)
    return perf


def default_model_segment_performance():
    return pd.DataFrame(columns=[
        "model_name", "sport", "market_bucket", "bets", "wins", "losses",
        "win_rate", "avg_prob", "brier_proxy", "segment_weight", "segment_threshold", "segment_status"
    ])


def overall_model_weight_lookup(perf_df):
    out = {m: 1.0 for m in MODEL_NAMES}
    thr = default_model_thresholds()
    if len(perf_df) == 0:
        return out, thr
    for m in MODEL_NAMES:
        seg = perf_df[perf_df["model_name"].astype(str) == m]
        if len(seg):
            row = seg.iloc[0]
            out[m] = float(row.get("weight", 1.0) if pd.notna(row.get("weight", np.nan)) else 1.0)
            thr[m] = float(row.get("adaptive_threshold", thr[m]) if pd.notna(row.get("adaptive_threshold", np.nan)) else thr[m])
    return out, thr


def segment_weight_lookup(segment_df, sport, market_bucket):
    base = {m: 1.0 for m in MODEL_NAMES}
    base_thr = default_model_thresholds()
    if len(segment_df) == 0:
        return base, base_thr
    seg = segment_df[
        segment_df["sport"].astype(str).eq(normalize_text(sport)) &
        segment_df["market_bucket"].astype(str).eq(normalize_text(market_bucket))
    ]
    if len(seg) == 0:
        return base, base_thr
    for m in MODEL_NAMES:
        row = seg[seg["model_name"].astype(str) == m]
        if len(row):
            r = row.iloc[0]
            base[m] = float(r.get("segment_weight", 1.0) if pd.notna(r.get("segment_weight", np.nan)) else 1.0)
            base_thr[m] = float(r.get("segment_threshold", base_thr[m]) if pd.notna(r.get("segment_threshold", np.nan)) else base_thr[m])
    return base, base_thr


def build_multi_model_votes(df, perf_df, segment_df, settings):
    out = df.copy()
    overall_weights, overall_thresholds = overall_model_weight_lookup(perf_df)

    out["Model_A_prob"] = (out["calibrated_prob"].fillna(out["model_prob"].fillna(0.50)) * 0.60 + out["model_prob"].fillna(0.50) * 0.40).clip(0.01, 0.99)
    edge_scaled = out["edge"].fillna(0).clip(lower=-3, upper=8) * 0.015
    out["Model_B_prob"] = (out["implied_prob"].fillna(0.50) + 0.04 + edge_scaled).clip(0.01, 0.99)
    score_adj = ((out["score"].fillna(65) - 65) / 100.0) * 0.18
    consensus_adj = (out["consensus"].fillna(3) - 3) * 0.02
    out["Model_C_prob"] = (0.50 + score_adj + consensus_adj).clip(0.01, 0.99)
    ev_adj = out["ev"].fillna(0).clip(lower=-0.10, upper=0.25) * 0.8
    sharp_adj = np.where(out.get("sharp_flag", "Normal").astype(str) == "Sharp", 0.03, 0.0)
    out["Model_D_prob"] = (out["implied_prob"].fillna(0.50) + 0.03 + ev_adj + sharp_adj).clip(0.01, 0.99)
    risk_penalty = np.where(out.get("risk_band", "High").astype(str) == "High", -0.04, np.where(out.get("risk_band", "High").astype(str) == "Medium", -0.01, 0.02))
    out["Model_E_prob"] = (out["calibrated_prob"].fillna(0.50) + risk_penalty + out["ev"].fillna(0).clip(lower=-0.08, upper=0.12) * 0.35).clip(0.01, 0.99)

    vote_counts = []
    weighted_votes = []
    weighted_ratios = []

    for _, row in out.iterrows():
        sport = row.get("sport", "")
        mkt = row.get("market_bucket", "")
        seg_weights, seg_thresholds = segment_weight_lookup(segment_df, sport, mkt)
        yes_count = 0
        w_yes = 0.0
        total_weight = 0.0

        for m in MODEL_NAMES:
            overall_w = overall_weights.get(m, 1.0)
            overall_thr = overall_thresholds.get(m, 0.015)
            seg_w = seg_weights.get(m, 1.0) if settings.get("adaptive_segments_on", True) else 1.0
            seg_thr = seg_thresholds.get(m, overall_thr) if settings.get("adaptive_segments_on", True) else overall_thr
            final_weight = overall_w * seg_w if settings.get("use_model_weights", True) else 1.0
            final_threshold = seg_thr if settings.get("adaptive_thresholds_on", True) else 0.015
            baseline = float(row.get("implied_prob", 0.50) if pd.notna(row.get("implied_prob", np.nan)) else 0.50)
            prob = float(row.get(f"{m}_prob", np.nan) if pd.notna(row.get(f"{m}_prob", np.nan)) else np.nan)
            vote = "YES" if pd.notna(prob) and prob > (baseline + final_threshold) else "NO"
            out.loc[row.name, f"{m}_vote"] = vote
            total_weight += final_weight
            if vote == "YES":
                yes_count += 1
                w_yes += final_weight

        vote_counts.append(yes_count)
        weighted_votes.append(w_yes)
        weighted_ratios.append(w_yes / max(total_weight, 1e-9))

    out["model_yes_votes"] = vote_counts
    out["weighted_yes_votes"] = weighted_votes
    out["weighted_consensus_ratio"] = weighted_ratios
    out["debate_label"] = np.where(
        out["model_yes_votes"] == 5, "5/5 Elite",
        np.where(out["model_yes_votes"] == 4, "4/5 Strong",
                 np.where(out["model_yes_votes"] == 3, "3/5 Playable",
                          np.where(out["model_yes_votes"] == 2, "2/5 Weak", "1/5 Pass")))
    )
    return out


def summarize_model_performance(votes_history_df):
    if len(votes_history_df) == 0:
        return default_model_performance()
    settled = votes_history_df[votes_history_df["result"].astype(str).str.lower().isin(["win", "loss"])].copy()
    if len(settled) == 0:
        return default_model_performance()
    settled["actual"] = settled["result"].astype(str).str.lower().map({"win": 1.0, "loss": 0.0})
    rows = []
    for m in MODEL_NAMES:
        prob_col = f"{m}_prob"
        vote_col = f"{m}_vote"
        seg = settled[[prob_col, vote_col, "actual"]].copy()
        seg = seg[seg[prob_col].notna()]
        if len(seg) == 0:
            rows.append(default_model_performance().query("model_name == @m").iloc[0].to_dict())
            continue
        yes_seg = seg[seg[vote_col].astype(str) == "YES"].copy()
        win_rate = yes_seg["actual"].mean() if len(yes_seg) else np.nan
        brier = ((seg[prob_col] - seg["actual"]) ** 2).mean()
        weight = 1.0
        status = "Neutral"
        threshold = default_model_thresholds()[m]
        if len(yes_seg) >= 10 and pd.notna(win_rate):
            if win_rate >= 0.58 and brier <= 0.24:
                weight = 1.16
                status = "Hot"
                threshold = 0.012
            elif win_rate <= 0.46:
                weight = 0.88
                status = "Cold"
                threshold = 0.022
        rows.append({
            "model_name": m,
            "bets": int(len(yes_seg)),
            "wins": int((yes_seg["actual"] == 1).sum()),
            "losses": int((yes_seg["actual"] == 0).sum()),
            "win_rate": win_rate,
            "avg_prob": seg[prob_col].mean(),
            "brier_proxy": brier,
            "weight": round(weight, 3),
            "status": status,
            "adaptive_threshold": round(threshold, 4),
        })
    return pd.DataFrame(rows)


def summarize_model_segment_performance(votes_history_df, min_samples=10):
    if len(votes_history_df) == 0:
        return default_model_segment_performance()
    settled = votes_history_df[votes_history_df["result"].astype(str).str.lower().isin(["win", "loss"])].copy()
    if len(settled) == 0:
        return default_model_segment_performance()
    settled["actual"] = settled["result"].astype(str).str.lower().map({"win": 1.0, "loss": 0.0})
    rows = []
    for m in MODEL_NAMES:
        prob_col = f"{m}_prob"
        vote_col = f"{m}_vote"
        for (sport, market_bucket), grp in settled.groupby(["sport", "market_bucket"], dropna=False):
            g = grp[[prob_col, vote_col, "actual"]].copy()
            g = g[g[prob_col].notna()]
            yes = g[g[vote_col].astype(str) == "YES"].copy()
            bets = len(yes)
            win_rate = yes["actual"].mean() if bets else np.nan
            brier = ((g[prob_col] - g["actual"]) ** 2).mean() if len(g) else np.nan
            seg_weight = 1.0
            seg_threshold = default_model_thresholds()[m]
            seg_status = "Neutral"
            if bets >= min_samples and pd.notna(win_rate):
                if win_rate >= 0.60 and (pd.isna(brier) or brier <= 0.24):
                    seg_weight = 1.12
                    seg_threshold = 0.011
                    seg_status = "Favored"
                elif win_rate <= 0.45:
                    seg_weight = 0.88
                    seg_threshold = 0.024
                    seg_status = "Reduced"
            rows.append({
                "model_name": m,
                "sport": sport,
                "market_bucket": market_bucket,
                "bets": bets,
                "wins": int((yes["actual"] == 1).sum()) if bets else 0,
                "losses": int((yes["actual"] == 0).sum()) if bets else 0,
                "win_rate": win_rate,
                "avg_prob": g[prob_col].mean() if len(g) else np.nan,
                "brier_proxy": brier,
                "segment_weight": round(seg_weight, 3),
                "segment_threshold": round(seg_threshold, 4),
                "segment_status": seg_status,
            })
    return pd.DataFrame(rows)


# =========================
# MODEL ADJUSTMENTS
# =========================
def calibration_multiplier(row, calibration_df, settings):
    if len(calibration_df) == 0:
        return 1.0
    sport = normalize_text(row.get("sport", ""))
    mkt = normalize_text(row.get("market_bucket", ""))
    prob_b = probability_bucket(row.get("model_prob", np.nan))
    seg = calibration_df[
        calibration_df["sport"].astype(str).eq(sport) &
        calibration_df["market_bucket"].astype(str).eq(mkt) &
        calibration_df["prob_bucket"].astype(str).eq(prob_b)
    ]
    if len(seg) == 0:
        return 1.0
    rec = seg.iloc[0]
    if float(rec.get("bets", 0) or 0) < float(settings["calibration_min_samples"]):
        return 1.0
    return float(rec.get("multiplier", 1.0))


def apply_calibration(df, calibration_df, settings):
    out = df.copy()
    out["calibration_multiplier"] = out.apply(lambda r: calibration_multiplier(r, calibration_df, settings), axis=1)
    out["calibrated_prob"] = (out["model_prob"] * out["calibration_multiplier"]).clip(lower=0.01, upper=0.99)
    return out


def market_weight(row, market_perf_df, settings):
    if not settings.get("auto_prioritize_profitable_markets", True) or len(market_perf_df) == 0:
        return 1.0
    sport = normalize_text(row.get("sport", "")).lower()
    market = normalize_text(row.get("market", "")).lower()
    seg = market_perf_df[
        market_perf_df["sport"].astype(str).str.lower().eq(sport) &
        market_perf_df["market"].astype(str).str.lower().eq(market)
    ]
    if len(seg) == 0:
        return 1.0
    s = seg.iloc[0]
    if float(s.get("bets", 0) or 0) < float(settings["learning_min_samples"]):
        return 1.0
    roi = float(s.get("roi", 0) if pd.notna(s.get("roi", np.nan)) else 0)
    avg_clv = float(s.get("avg_clv", 0) if pd.notna(s.get("avg_clv", np.nan)) else 0)
    if roi > 0.08 and avg_clv > 0:
        return 1.14
    if roi > 0.03:
        return 1.06
    if roi < -0.08:
        return 0.85
    if roi < -0.03:
        return 0.93
    return 1.0


def book_weight(row, book_perf_df, settings):
    if len(book_perf_df) == 0:
        return 1.0
    sport = normalize_text(row.get("sport", "")).lower()
    book = normalize_text(row.get("book", "")).lower()
    seg = book_perf_df[
        book_perf_df["sport"].astype(str).str.lower().eq(sport) &
        book_perf_df["book"].astype(str).str.lower().eq(book)
    ]
    if len(seg) == 0:
        return 1.0
    s = seg.iloc[0]
    if float(s.get("bets", 0) or 0) < float(settings["book_min_samples"]):
        return 1.0
    temp = normalize_text(s.get("temperature", "Neutral"))
    avg_clv = float(s.get("avg_clv", 0) if pd.notna(s.get("avg_clv", np.nan)) else 0)
    if temp == "Hot" and avg_clv >= 0:
        return 1.08
    if temp == "Cold":
        return 0.90
    return 1.0


def profile_weight(row, profile_perf_df, settings):
    if len(profile_perf_df) == 0:
        return 1.0
    key = normalize_text(row.get("profile_key", ""))
    seg = profile_perf_df[profile_perf_df["profile_key"].astype(str).eq(key)]
    if len(seg) == 0:
        return 1.0
    s = seg.iloc[0]
    if float(s.get("bets", 0) or 0) < float(settings["profile_min_samples"]):
        return 1.0
    signal = normalize_text(s.get("profile_signal", "Neutral"))
    if signal == "Boost":
        return 1.08
    if signal == "Suppress":
        return max(0.82, 1.0 - float(settings["max_profile_penalty"]))
    return 1.0


def sharp_mode_weight(sharp_status, settings):
    if not bool(settings.get("sharp_mode_auto", True)):
        return 1.0
    return 1.12 if sharp_status.get("sharp_mode", False) else 1.0


def debate_weight(row, settings):
    yes_votes = float(row.get("model_yes_votes", 0) if pd.notna(row.get("model_yes_votes", np.nan)) else 0)
    weighted_ratio = float(row.get("weighted_consensus_ratio", 0) if pd.notna(row.get("weighted_consensus_ratio", np.nan)) else 0)
    if yes_votes >= 5:
        return 1.18
    if yes_votes >= 4:
        return 1.10 if weighted_ratio >= 0.75 else 1.06
    if yes_votes >= 3:
        return 1.03 if weighted_ratio >= 0.62 else 1.00
    if settings.get("debate_penalty_on", True):
        return 0.82
    return 1.0


def recommend_units(row, settings, market_perf_df=None, book_perf_df=None, profile_perf_df=None, sharp_status=None):
    bankroll = float(settings["bankroll"])
    kelly_multiplier = float(settings["kelly_multiplier"])
    base_unit_pct = float(settings["base_unit_pct"])
    max_unit = float(settings["max_unit"])
    p = row.get("calibrated_prob", row.get("model_prob", np.nan))
    odds = row.get("odds", np.nan)
    score = row.get("score", 0)
    consensus = row.get("consensus", 0)
    k = kelly_fraction(p, odds)
    units = k * kelly_multiplier * (bankroll * base_unit_pct)
    if score >= 85:
        units *= 1.25
    elif score >= 75:
        units *= 1.10
    elif score < 65:
        units *= 0.70
    if consensus >= 5:
        units *= 1.15
    elif consensus <= 2:
        units *= 0.80
    units *= market_weight(row, market_perf_df if market_perf_df is not None else pd.DataFrame(), settings)
    units *= book_weight(row, book_perf_df if book_perf_df is not None else pd.DataFrame(), settings)
    units *= profile_weight(row, profile_perf_df if profile_perf_df is not None else pd.DataFrame(), settings)
    units *= sharp_mode_weight(sharp_status if sharp_status is not None else {"sharp_mode": False}, settings)
    units *= debate_weight(row, settings)
    units = max(0.10, min(max_unit, units))
    return round(units, 2)


def adjusted_priority_score(row, market_perf_df, book_perf_df, profile_perf_df, sharp_status, settings):
    base_score = float(row.get("score", 0) if pd.notna(row.get("score", np.nan)) else 0)
    m_w = market_weight(row, market_perf_df, settings)
    b_w = book_weight(row, book_perf_df, settings)
    p_w = profile_weight(row, profile_perf_df, settings)
    sharp_w = sharp_mode_weight(sharp_status, settings)
    debate_w = debate_weight(row, settings)
    ev_bonus = 12 * float(row.get("ev", 0) if pd.notna(row.get("ev", np.nan)) else 0)
    model_bonus = float(row.get("weighted_yes_votes", 0) if pd.notna(row.get("weighted_yes_votes", np.nan)) else 0) * 2.0
    return round(base_score * m_w * b_w * p_w * sharp_w * debate_w + ev_bonus + model_bonus, 2)


def qualify_plays(df, settings):
    if len(df) == 0:
        return df.copy()
    out = df.copy()
    out = out[
        (out["consensus"] >= settings["min_consensus"]) &
        (out["score"] >= 65) &
        (out["odds"] >= settings["default_odds_min"]) &
        (out["odds"] <= settings["default_odds_max"]) &
        (out["model_yes_votes"] >= settings["model_consensus_min"])
    ].copy()
    if settings.get("suppress_losing_profiles", True) and "profile_signal" in out.columns:
        out = out[out["profile_signal"].astype(str) != "Suppress"].copy()
    return out


def add_model_features(df, calibration_df, market_perf_df, book_perf_df, profile_perf_df, sharp_status, perf_df, segment_df, settings):
    out = df.copy()
    out = apply_calibration(out, calibration_df, settings)
    out["ev"] = out.apply(lambda r: compute_ev(r.get("calibrated_prob", np.nan), r.get("odds", np.nan)), axis=1)
    out["profile_signal"] = out["profile_key"].map(profile_perf_df.set_index("profile_key")["profile_signal"].to_dict()) if len(profile_perf_df) else "Neutral"
    out["sharp_flag"] = "Sharp" if sharp_status.get("sharp_mode", False) else "Normal"
    out["risk_band"] = out["score"].apply(score_to_risk_band)
    out = build_multi_model_votes(out, perf_df, segment_df, settings)
    out["recommended_units"] = out.apply(lambda r: recommend_units(r, settings, market_perf_df, book_perf_df, profile_perf_df, sharp_status), axis=1)
    out["priority_score"] = out.apply(lambda r: adjusted_priority_score(r, market_perf_df, book_perf_df, profile_perf_df, sharp_status, settings), axis=1)
    return out


# =========================
# LIVE ODDS / LINE MOVEMENT / REFRESH / CLOSING INTEL
# =========================
def best_live_match_for_recommendation(rec_row, live_df):
    matches = live_df[
        live_df["sport"].astype(str).eq(normalize_text(rec_row.get("sport", ""))) &
        live_df["event"].astype(str).eq(normalize_text(rec_row.get("event", ""))) &
        live_df["bet_type"].astype(str).eq(normalize_text(rec_row.get("bet_type", ""))) &
        live_df["selection"].astype(str).eq(normalize_text(rec_row.get("selection", "")))
    ].copy()
    if len(matches) == 0:
        return None
    matches["current_odds_num"] = safe_to_numeric(matches["current_odds"])
    best_idx = matches["current_odds_num"].idxmax()
    return matches.loc[best_idx]


def build_live_odds_monitor(execution_board_df, live_odds_df, settings):
    board = execution_board_df.copy()
    live = live_odds_df.copy()
    if len(board) == 0 or len(live) == 0:
        return pd.DataFrame(columns=[
            "captured_at", "bet_id", "sport", "event", "market_bucket", "selection", "bet_type", "rec_book",
            "rec_odds", "best_current_book", "best_current_odds", "best_current_line",
            "odds_change", "implied_prob_change", "line_change", "timing_signal",
            "best_execution_signal", "movement_note"
        ])
    singles = board[board["ticket_type"].astype(str) == "single"].copy()
    rows = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for _, rec in singles.iterrows():
        best = best_live_match_for_recommendation(rec, live)
        if best is None:
            continue
        rec_odds = float(rec.get("odds", np.nan))
        best_odds = float(best.get("current_odds", np.nan))
        rec_ip = american_implied_prob(rec_odds)
        cur_ip = american_implied_prob(best_odds)
        odds_change = best_odds - rec_odds if pd.notna(best_odds) and pd.notna(rec_odds) else np.nan
        ip_change = rec_ip - cur_ip if pd.notna(rec_ip) and pd.notna(cur_ip) else np.nan
        rec_line = rec.get("line", np.nan) if "line" in rec.index else np.nan
        cur_line = best.get("current_line", np.nan)
        line_change = cur_line - rec_line if pd.notna(cur_line) and pd.notna(rec_line) else np.nan
        if pd.notna(ip_change):
            if ip_change >= float(settings["movement_wait_threshold"]):
                timing_signal = "Bet Now"
            elif ip_change <= float(settings["movement_pass_threshold"]):
                timing_signal = "Pass / Worse"
            else:
                timing_signal = "Wait / Monitor"
        else:
            timing_signal = "Monitor"
        best_execution_signal = "Use Current Best Book" if normalize_text(best.get("book", "")) != normalize_text(rec.get("book", "")) else "Original Book Still Best"
        rows.append({
            "captured_at": now,
            "bet_id": rec.get("bet_id", ""),
            "sport": rec.get("sport", ""),
            "event": rec.get("event", ""),
            "market_bucket": rec.get("market_bucket", ""),
            "selection": rec.get("selection", ""),
            "bet_type": rec.get("bet_type", ""),
            "rec_book": rec.get("book", ""),
            "rec_odds": rec_odds,
            "best_current_book": best.get("book", ""),
            "best_current_odds": best_odds,
            "best_current_line": cur_line,
            "odds_change": odds_change,
            "implied_prob_change": ip_change,
            "line_change": line_change,
            "timing_signal": timing_signal,
            "best_execution_signal": best_execution_signal,
            "movement_note": f"odds Δ {odds_change:+.0f} | CLV edge {ip_change:+.3f}" if pd.notna(odds_change) and pd.notna(ip_change) else "",
        })
    return pd.DataFrame(rows)


def merge_live_monitor(existing_df, new_df):
    if len(new_df) == 0:
        return existing_df.copy()
    if len(existing_df) == 0:
        return new_df.copy()
    combined = pd.concat([existing_df.copy(), new_df.copy()], ignore_index=True)
    return combined.sort_values(["captured_at"]).drop_duplicates(subset=["bet_id"], keep="last")


def live_monitor_summary(df):
    if len(df) == 0:
        return {"rows": 0, "bet_now": 0, "wait": 0, "pass": 0}
    return {
        "rows": len(df),
        "bet_now": int((df["timing_signal"].astype(str) == "Bet Now").sum()),
        "wait": int((df["timing_signal"].astype(str) == "Wait / Monitor").sum()),
        "pass": int((df["timing_signal"].astype(str) == "Pass / Worse").sum()),
    }


def refresh_execution_board_with_live(board_df, live_df, settings):
    if len(board_df) == 0 or len(live_df) == 0:
        return pd.DataFrame(columns=[
            "refreshed_at", "execution_id", "bet_id", "ticket_type", "sport", "event", "selection", "bet_type",
            "original_book", "original_odds", "current_best_book", "current_best_odds", "current_best_line",
            "original_ev", "current_ev", "ev_delta", "original_execution_priority", "current_execution_priority",
            "priority_delta", "original_units", "refreshed_units", "unit_delta", "timing_signal",
            "refresh_signal", "still_qualifies", "refresh_note"
        ])
    singles = board_df[board_df["ticket_type"].astype(str) == "single"].copy()
    rows = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for _, rec in singles.iterrows():
        best = best_live_match_for_recommendation(rec, live_df)
        if best is None:
            continue
        original_odds = float(rec.get("odds", np.nan))
        current_odds = float(best.get("current_odds", np.nan))
        model_prob = float(rec.get("calibrated_prob", np.nan))
        original_ev = compute_ev(model_prob, original_odds)
        current_ev = compute_ev(model_prob, current_odds)
        ev_delta = current_ev - original_ev if pd.notna(current_ev) and pd.notna(original_ev) else np.nan
        rec_ip = american_implied_prob(original_odds)
        cur_ip = american_implied_prob(current_odds)
        ip_change = rec_ip - cur_ip if pd.notna(rec_ip) and pd.notna(cur_ip) else np.nan

        if pd.notna(ip_change):
            if ip_change >= float(settings["movement_wait_threshold"]):
                timing_signal = "Bet Now"
            elif ip_change <= float(settings["movement_pass_threshold"]):
                timing_signal = "Pass / Worse"
            else:
                timing_signal = "Wait / Monitor"
        else:
            timing_signal = "Monitor"

        temp_row = rec.copy()
        temp_row["odds"] = current_odds
        temp_row["ev"] = current_ev
        current_priority = (
            float(rec.get("priority_score", 0)) * 0.65
            + float(rec.get("model_yes_votes", 0)) * 5
            + float(rec.get("weighted_consensus_ratio", 0)) * 12
            + float(current_ev if pd.notna(current_ev) else 0) * 100 * 0.15
        )
        original_priority = float(rec.get("execution_priority", np.nan))
        priority_delta = current_priority - original_priority if pd.notna(original_priority) else np.nan
        original_units = float(rec.get("approved_units", np.nan))
        refreshed_units = original_units
        refresh_signal = "Keep"
        notes = []

        if pd.notna(ev_delta) and ev_delta > 0 and settings.get("refresh_auto_raise_units", True):
            refreshed_units = min(float(settings["max_unit"]), original_units * float(settings["refresh_improve_unit_boost"]))
            refresh_signal = "Upgrade"
            notes.append("price improved")
        elif pd.notna(ev_delta) and ev_delta < 0 and settings.get("refresh_auto_reduce_when_worse", True):
            refreshed_units = max(0.10, original_units * float(settings["refresh_worse_unit_cut"]))
            refresh_signal = "Reduce"
            notes.append("price worsened")

        still_qualifies = "Yes"
        if pd.notna(current_ev) and float(current_ev) < float(settings["refresh_min_current_ev"]):
            still_qualifies = "No"
            refresh_signal = "Suppress"
            notes.append("current EV below floor")
        if pd.notna(current_priority) and float(current_priority) < float(settings["refresh_priority_floor"]):
            still_qualifies = "No"
            refresh_signal = "Suppress"
            notes.append("current priority below floor")
        if timing_signal == "Pass / Worse":
            still_qualifies = "No"
            refresh_signal = "Suppress"
            notes.append("timing says pass")

        rows.append({
            "refreshed_at": now,
            "execution_id": rec.get("execution_id", ""),
            "bet_id": rec.get("bet_id", ""),
            "ticket_type": rec.get("ticket_type", ""),
            "sport": rec.get("sport", ""),
            "event": rec.get("event", ""),
            "selection": rec.get("selection", ""),
            "bet_type": rec.get("bet_type", ""),
            "original_book": rec.get("book", ""),
            "original_odds": original_odds,
            "current_best_book": best.get("book", ""),
            "current_best_odds": current_odds,
            "current_best_line": best.get("current_line", np.nan),
            "original_ev": original_ev,
            "current_ev": current_ev,
            "ev_delta": ev_delta,
            "original_execution_priority": original_priority,
            "current_execution_priority": current_priority,
            "priority_delta": priority_delta,
            "original_units": original_units,
            "refreshed_units": round(refreshed_units, 2) if pd.notna(refreshed_units) else np.nan,
            "unit_delta": round(refreshed_units - original_units, 2) if pd.notna(refreshed_units) and pd.notna(original_units) else np.nan,
            "timing_signal": timing_signal,
            "refresh_signal": refresh_signal,
            "still_qualifies": still_qualifies,
            "refresh_note": " | ".join(notes),
        })
    return pd.DataFrame(rows)


def apply_refresh_to_execution_board(board_df, refresh_df):
    if len(board_df) == 0 or len(refresh_df) == 0:
        return board_df.copy()
    board = board_df.copy()
    ref = refresh_df.copy().set_index("execution_id")
    for idx, row in board.iterrows():
        ex_id = row.get("execution_id", "")
        if ex_id not in ref.index:
            continue
        r = ref.loc[ex_id]
        board.loc[idx, "book"] = r.get("current_best_book", row.get("book", ""))
        board.loc[idx, "odds"] = r.get("current_best_odds", row.get("odds", np.nan))
        if pd.notna(r.get("current_execution_priority", np.nan)):
            board.loc[idx, "execution_priority"] = r.get("current_execution_priority", row.get("execution_priority", np.nan))
        if pd.notna(r.get("current_ev", np.nan)):
            board.loc[idx, "ev"] = r.get("current_ev", row.get("ev", np.nan))
        if pd.notna(r.get("refreshed_units", np.nan)):
            board.loc[idx, "approved_units"] = r.get("refreshed_units", row.get("approved_units", np.nan))
        note = normalize_text(board.loc[idx, "notes"])
        addon = f"refresh:{r.get('refresh_signal', '')}; timing:{r.get('timing_signal', '')}"
        board.loc[idx, "notes"] = addon if note == "" else f"{note} | {addon}"
        if normalize_text(r.get("still_qualifies", "Yes")) == "No" and normalize_text(str(board.loc[idx, "status"])) != "placed":
            board.loc[idx, "status"] = "passed"
            board.loc[idx, "review_flag"] = 0
            board.loc[idx, "locked_flag"] = 0
            board.loc[idx, "placed_flag"] = 0
    return board


def refresh_summary(refresh_df):
    if len(refresh_df) == 0:
        return {"rows": 0, "upgrade": 0, "reduce": 0, "suppress": 0, "qualify_yes": 0}
    return {
        "rows": len(refresh_df),
        "upgrade": int((refresh_df["refresh_signal"].astype(str) == "Upgrade").sum()),
        "reduce": int((refresh_df["refresh_signal"].astype(str) == "Reduce").sum()),
        "suppress": int((refresh_df["refresh_signal"].astype(str) == "Suppress").sum()),
        "qualify_yes": int((refresh_df["still_qualifies"].astype(str) == "Yes").sum()),
    }


def build_closing_line_intelligence(execution_df, live_df, bet_log_df, book_scores_df):
    cols = [
        "captured_at", "execution_id", "bet_id", "sport", "event", "selection", "bet_type",
        "recommended_book", "recommended_odds", "best_live_book", "best_live_odds",
        "closing_book", "closing_odds", "rec_vs_close_clv", "live_vs_close_clv",
        "best_source", "shopping_signal", "book_shopping_score", "intel_note"
    ]
    if len(execution_df) == 0:
        return pd.DataFrame(columns=cols)

    log_map_close = {}
    if len(bet_log_df):
        temp = ensure_columns(bet_log_df.copy(), ["bet_id", "closing_odds", "book"])
        log_map_close = temp.set_index("bet_id")[["closing_odds", "book"]].to_dict("index")

    score_map = {}
    if len(book_scores_df):
        for _, row in book_scores_df.iterrows():
            key = f"{normalize_text(row.get('sport',''))}|{normalize_text(row.get('book',''))}"
            score_map[key] = float(row.get("book_shopping_score", np.nan) if pd.notna(row.get("book_shopping_score", np.nan)) else np.nan)

    rows = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    singles = execution_df[execution_df["ticket_type"].astype(str) == "single"].copy()
    for _, rec in singles.iterrows():
        best = best_live_match_for_recommendation(rec, live_df) if len(live_df) else None
        closing_row = log_map_close.get(rec.get("bet_id", ""), {})
        rec_odds = rec.get("odds", np.nan)
        live_odds = best.get("current_odds", np.nan) if best is not None else np.nan
        closing_odds = closing_row.get("closing_odds", np.nan)
        rec_clv = clv_value(rec_odds, closing_odds)
        live_clv = clv_value(live_odds, closing_odds)

        best_source = "Recommended Book"
        if pd.notna(live_clv) and pd.notna(rec_clv):
            best_source = "Best Live Book" if live_clv > rec_clv else "Recommended Book"
        elif pd.notna(live_odds) and pd.isna(rec_odds):
            best_source = "Best Live Book"

        live_score = np.nan
        if best is not None:
            key = f"{normalize_text(rec.get('sport',''))}|{normalize_text(best.get('book',''))}"
            live_score = score_map.get(key, np.nan)

        shopping_signal = "Need More Shop"
        if pd.notna(live_clv) and pd.notna(rec_clv):
            if live_clv > rec_clv + 0.005:
                shopping_signal = "Take Best Live Book"
            elif rec_clv >= live_clv - 0.002:
                shopping_signal = "Original Book Fine"
        elif best is not None:
            shopping_signal = "Use Best Live Price"

        intel_note_parts = []
        if pd.notna(rec_clv):
            intel_note_parts.append(f"rec->close {rec_clv:+.3f}")
        if pd.notna(live_clv):
            intel_note_parts.append(f"live->close {live_clv:+.3f}")
        if pd.notna(live_score):
            intel_note_parts.append(f"shop score {live_score:.1f}")

        rows.append({
            "captured_at": now,
            "execution_id": rec.get("execution_id", ""),
            "bet_id": rec.get("bet_id", ""),
            "sport": rec.get("sport", ""),
            "event": rec.get("event", ""),
            "selection": rec.get("selection", ""),
            "bet_type": rec.get("bet_type", ""),
            "recommended_book": rec.get("book", ""),
            "recommended_odds": rec_odds,
            "best_live_book": best.get("book", "") if best is not None else "",
            "best_live_odds": live_odds,
            "closing_book": closing_row.get("book", ""),
            "closing_odds": closing_odds,
            "rec_vs_close_clv": rec_clv,
            "live_vs_close_clv": live_clv,
            "best_source": best_source,
            "shopping_signal": shopping_signal,
            "book_shopping_score": live_score,
            "intel_note": " | ".join(intel_note_parts),
        })
    return pd.DataFrame(rows, columns=cols)


def closing_intel_summary(df):
    if len(df) == 0:
        return {"rows": 0, "take_live": 0, "orig_ok": 0, "need_shop": 0}
    return {
        "rows": len(df),
        "take_live": int((df["shopping_signal"].astype(str) == "Take Best Live Book").sum()),
        "orig_ok": int((df["shopping_signal"].astype(str) == "Original Book Fine").sum()),
        "need_shop": int((df["shopping_signal"].astype(str) == "Need More Shop").sum()),
    }


def save_current_vote_snapshot(df_with_votes):
    if len(df_with_votes) == 0:
        return 0
    hist = load_model_votes_history()
    save_cols = [
        "bet_id", "sport", "event", "market_bucket", "selection", "bet_type", "book", "odds",
        "Model_A_prob", "Model_A_vote", "Model_B_prob", "Model_B_vote",
        "Model_C_prob", "Model_C_vote", "Model_D_prob", "Model_D_vote",
        "Model_E_prob", "Model_E_vote"
    ]
    snap = ensure_columns(df_with_votes.copy(), save_cols + ["result"])
    snap = snap[save_cols + ["result"]].copy()
    snap["saved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hist = pd.concat([hist, snap], ignore_index=True)
    hist = hist.drop_duplicates(subset=["bet_id"], keep="last")
    save_model_votes_history(hist)
    return len(snap)


# =========================
# MODEL ADJUSTMENTS
# =========================

def build_consensus_parlays(df, settings):
    if len(df) == 0:
        return pd.DataFrame()
    df = df.copy().sort_values(["weighted_consensus_ratio", "model_yes_votes", "priority_score", "score", "ev"], ascending=[False, False, False, False, False]).head(16)
    rows = []
    for leg_count in range(int(settings["min_parlay_legs"]), int(settings["max_parlay_legs"]) + 1):
        for combo in itertools.combinations(df.index.tolist(), leg_count):
            legs = df.loc[list(combo)].copy()
            if (legs["model_yes_votes"] < 3).any():
                continue
            dec_odds = legs["odds"].apply(american_to_decimal)
            if dec_odds.isna().any():
                continue
            parlay_dec = float(dec_odds.prod())
            parlay_american = decimal_to_american(parlay_dec)
            if pd.isna(parlay_american) or parlay_american < 200:
                continue
            joint_prob = float(legs["calibrated_prob"].clip(lower=0.01, upper=0.99).prod())
            implied = american_implied_prob(parlay_american)
            ev = compute_ev(joint_prob, parlay_american)
            penalty, penalty_reason = parlay_correlation_penalty(legs)
            raw_score = legs["priority_score"].mean() * 0.38 + legs["weighted_consensus_ratio"].mean() * 25.0 + legs["model_yes_votes"].mean() * 4.0 + max(0, (joint_prob - implied) * 100) * 0.9 + min(10, len(legs))
            final_score = raw_score - penalty if settings.get("correlation_penalty_on", True) else raw_score
            rows.append({
                "legs": len(legs),
                "avg_debate_votes": round(legs["model_yes_votes"].mean(), 2),
                "avg_weighted_ratio": round(legs["weighted_consensus_ratio"].mean(), 3),
                "parlay_odds": int(parlay_american),
                "joint_prob": joint_prob,
                "implied_prob": implied,
                "ev": ev,
                "score": round(final_score, 2),
                "correlation_note": penalty_reason,
                "summary": " + ".join(legs["selection"].astype(str) + " " + legs["bet_type"].astype(str)),
                "events": " | ".join(legs["event"].astype(str)),
            })
    out = pd.DataFrame(rows)
    if len(out) == 0:
        return out
    return out.sort_values(["avg_weighted_ratio", "avg_debate_votes", "score", "ev"], ascending=[False, False, False, False]).drop_duplicates(subset=["summary"]).head(12)


# =========================
# EXECUTION / SETTLEMENT
# =========================

def build_execution_board(singles_df, parlays_df, settings):
    rows = []
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    auto_lock = bool(settings.get("execution_auto_lock_elite", False))
    if len(singles_df) > 0:
        singles = singles_df.copy().sort_values(["weighted_consensus_ratio", "model_yes_votes", "priority_score"], ascending=[False, False, False]).head(int(settings["execution_max_singles"]))
        for i, (_, row) in enumerate(singles.iterrows(), start=1):
            exec_priority = build_execution_priority(row)
            status = "locked" if auto_lock and int(row.get("model_yes_votes", 0)) == 5 else "review"
            rows.append({
                "execution_id": f"S-{datetime.now().strftime('%Y%m%d%H%M%S')}-{i}",
                "created_at": created_at,
                "bet_id": row.get("bet_id", ""),
                "ticket_type": "single",
                "slip_group": f"SINGLES-{created_at[:10]}",
                "sport": row.get("sport", ""),
                "event": row.get("event", ""),
                "market_bucket": row.get("market_bucket", ""),
                "selection": row.get("selection", ""),
                "bet_type": row.get("bet_type", ""),
                "book": row.get("book", ""),
                "odds": row.get("odds", np.nan),
                "line": row.get("line", np.nan) if "line" in row else np.nan,
                "calibrated_prob": row.get("calibrated_prob", np.nan),
                "ev": row.get("ev", np.nan),
                "score": row.get("score", np.nan),
                "priority_score": row.get("priority_score", np.nan),
                "model_yes_votes": row.get("model_yes_votes", np.nan),
                "weighted_consensus_ratio": row.get("weighted_consensus_ratio", np.nan),
                "recommended_units": row.get("recommended_units", np.nan),
                "approved_units": row.get("recommended_units", np.nan),
                "execution_priority": exec_priority,
                "status": status,
                "locked_flag": 1 if status == "locked" else 0,
                "review_flag": 1 if status == "review" else 0,
                "placed_flag": 0,
                "ai_recommended": 1,
                "user_placed": 0,
                "difference_flag": 0,
                "notes": "",
            })
    if len(parlays_df) > 0:
        parlays = parlays_df.copy().sort_values(["avg_weighted_ratio", "avg_debate_votes", "score", "ev"], ascending=[False, False, False, False]).head(int(settings["execution_max_parlays"]))
        for i, (_, row) in enumerate(parlays.iterrows(), start=1):
            exec_priority = round(float(row.get("score", 0)) * 0.75 + float(row.get("avg_weighted_ratio", 0)) * 20 + float(row.get("ev", 0)) * 100 * 0.2, 2)
            rows.append({
                "execution_id": f"P-{datetime.now().strftime('%Y%m%d%H%M%S')}-{i}",
                "created_at": created_at,
                "bet_id": f"PARLAY|{i}|{normalize_text(row.get('summary', ''))}",
                "ticket_type": "parlay",
                "slip_group": f"PARLAYS-{created_at[:10]}",
                "sport": "MULTI",
                "event": row.get("events", ""),
                "market_bucket": "Parlay",
                "selection": row.get("summary", ""),
                "bet_type": f"{int(row.get('legs', 0))}-Leg Parlay",
                "book": "Best Available",
                "odds": row.get("parlay_odds", np.nan),
                "line": np.nan,
                "calibrated_prob": row.get("joint_prob", np.nan),
                "ev": row.get("ev", np.nan),
                "score": row.get("score", np.nan),
                "priority_score": row.get("score", np.nan),
                "model_yes_votes": row.get("avg_debate_votes", np.nan),
                "weighted_consensus_ratio": row.get("avg_weighted_ratio", np.nan),
                "recommended_units": 0.5,
                "approved_units": 0.5,
                "execution_priority": exec_priority,
                "status": "review",
                "locked_flag": 0,
                "review_flag": 1,
                "placed_flag": 0,
                "ai_recommended": 1,
                "user_placed": 0,
                "difference_flag": 0,
                "notes": row.get("correlation_note", ""),
            })
    board = pd.DataFrame(rows)
    if len(board) == 0:
        return board
    board = board[board["execution_priority"] >= float(settings.get("execution_min_priority", 75.0))].copy()
    return board.sort_values(["execution_priority", "ticket_type"], ascending=[False, True]).reset_index(drop=True)

def merge_execution_board(new_board, existing_board):
    if len(new_board) == 0:
        return existing_board.copy()
    existing = existing_board.copy()
    if len(existing) == 0:
        return new_board.copy()
    key_cols = ["bet_id", "ticket_type"]
    existing_keys = set(existing[key_cols].astype(str).agg("|".join, axis=1).tolist())
    keep = new_board[~new_board[key_cols].astype(str).agg("|".join, axis=1).isin(existing_keys)].copy()
    return pd.concat([existing, keep], ignore_index=True)

def execution_summary(board_df):
    if len(board_df) == 0:
        return {"total": 0, "locked": 0, "review": 0, "placed": 0, "singles": 0, "parlays": 0}
    return {
        "total": len(board_df),
        "locked": int((board_df["status"].astype(str) == "locked").sum()),
        "review": int((board_df["status"].astype(str) == "review").sum()),
        "placed": int((board_df["status"].astype(str) == "placed").sum()),
        "singles": int((board_df["ticket_type"].astype(str) == "single").sum()),
        "parlays": int((board_df["ticket_type"].astype(str) == "parlay").sum()),
    }

def settlement_detail_table(settlement_df):
    if len(settlement_df) == 0:
        return settlement_df
    return settlement_df.sort_values(["status_at_execution", "placement_alignment", "event"], ascending=[True, True, True])


# =========================
# LIVE ODDS / REFRESH
# =========================

# =========================
# METRICS / FORMATTING
# =========================
def append_new_bets_to_log(candidates_df, bet_log_df):
    if len(candidates_df) == 0:
        return bet_log_df.copy(), 0
    base = ensure_columns(bet_log_df.copy(), ["bet_id"])
    new_rows = candidates_df.copy()
    new_rows["bet_id"] = new_rows.apply(build_bet_id, axis=1)
    existing = set(base["bet_id"].astype(str).tolist())
    to_add = new_rows[~new_rows["bet_id"].astype(str).isin(existing)].copy()
    if len(to_add) == 0:
        return base, 0
    keep_cols = [
        "bet_id", "date_added", "sport", "event", "market", "market_bucket",
        "bet_type", "selection", "book", "odds", "closing_odds", "projection", "line",
        "edge", "model_prob", "calibrated_prob", "implied_prob", "ev", "score",
        "priority_score", "consensus", "model_yes_votes", "weighted_yes_votes",
        "debate_label", "tier", "recommended_units", "sharp_flag",
        "profile_key", "result", "profit_units", "clv", "notes"
    ]
    to_add = ensure_columns(to_add, keep_cols)
    return pd.concat([base, to_add[keep_cols]], ignore_index=True), len(to_add)


def update_bet_outcomes(log_df):
    out = log_df.copy()
    out = ensure_columns(out, ["odds", "recommended_units", "result", "closing_odds"])
    out["profit_units"] = out.apply(lambda r: calculate_profit_units(r.get("result", np.nan), r.get("odds", np.nan), r.get("recommended_units", np.nan)), axis=1)
    out["clv"] = out.apply(lambda r: clv_value(r.get("odds", np.nan), r.get("closing_odds", np.nan)), axis=1)
    return out


def summary_metrics(log_df):
    settled = log_df[log_df["result"].astype(str).str.lower().isin(["win", "loss", "push", "void"])].copy()
    pending = log_df[~log_df.index.isin(settled.index)].copy()
    total_bets = len(log_df)
    wins = (settled["result"].astype(str).str.lower() == "win").sum()
    losses = (settled["result"].astype(str).str.lower() == "loss").sum()
    pushes = (settled["result"].astype(str).str.lower().isin(["push", "void"])).sum()
    profit_units = settled["profit_units"].fillna(0).sum()
    staked_units = settled["recommended_units"].fillna(0).sum()
    roi = profit_units / staked_units if staked_units else 0.0
    avg_clv = settled["clv"].dropna().mean() if "clv" in settled.columns else np.nan
    return {"total_bets": total_bets, "settled": len(settled), "pending": len(pending), "wins": int(wins), "losses": int(losses), "pushes": int(pushes), "profit_units": profit_units, "roi": roi, "avg_clv": avg_clv}


def format_pick_card(row):
    grade = row.get("grade", "D")
    emoji = score_to_emoji(row.get("score", 0))
    return f"""#{int(row.name)+1} {normalize_text(row.get("selection", ""))} — {normalize_text(row.get("bet_type", ""))}
{normalize_text(row.get("event", ""))} • {normalize_text(row.get("market_bucket", ""))} • {normalize_text(row.get("book", ""))}
Projection: {row.get("projection", np.nan):.2f} | Edge: {row.get("edge", np.nan):.2f} | Odds: {int(row.get("odds", 0)) if pd.notna(row.get("odds")) else "—"}
Model Hit %: {pct(row.get("model_prob", np.nan))} | Calibrated Hit %: {pct(row.get("calibrated_prob", np.nan))} | EV: {pct(row.get("ev", np.nan))}
Score: {row.get("score", np.nan):.1f} ({emoji} {grade}) | Priority: {row.get("priority_score", np.nan):.1f}
Debate: {int(row.get("model_yes_votes", 0))}/5 | Weighted: {float(row.get("weighted_consensus_ratio", 0)):.2f} | Label: {normalize_text(row.get("debate_label", ""))}
Tier: {row.get("tier", "Tier 4")} | Units: {row.get("recommended_units", np.nan):.2f}u | Mode: {normalize_text(row.get("sharp_flag", "Normal"))}"""


def export_download(df, filename, label):
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(label, csv, file_name=filename, mime="text/csv")


# =========================
# LOAD STATE
# =========================
settings = load_settings()
bet_log = update_bet_outcomes(load_bet_log())
memory_df = load_model_memory()
execution_board_df = load_execution_board()
execution_settlement_df = load_execution_settlement()
live_odds_df = load_live_odds()
line_monitor_df = load_line_movement_monitor()
execution_refresh_df = load_execution_refresh()
book_scores_df = load_book_scores()
closing_intel_df = load_closing_line_intel()

market_perf_df = summarize_market_performance(memory_df, min_samples=int(settings["learning_min_samples"]))
book_perf_df = summarize_book_performance(memory_df, min_samples=int(settings["book_min_samples"]))
calibration_df = build_calibration_profile(memory_df, min_samples=int(settings["calibration_min_samples"]))
profile_perf_df = summarize_profile_performance(memory_df, min_samples=int(settings["profile_min_samples"]))
sharp_status = evaluate_sharp_mode(memory_df, settings)
model_perf_df = initialize_model_performance()
votes_history_df = load_model_votes_history()
model_segment_perf_df = load_model_segment_performance()
if len(votes_history_df) > 0:
    model_perf_df = summarize_model_performance(votes_history_df)
    save_model_performance(model_perf_df)
    model_segment_perf_df = summarize_model_segment_performance(votes_history_df, min_samples=int(settings["adaptive_min_samples"]))
    save_model_segment_performance(model_segment_perf_df)


# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.header("V21 Controls")
    settings["bankroll"] = st.number_input("Bankroll", min_value=100.0, value=float(settings["bankroll"]), step=50.0)
    settings["kelly_multiplier"] = st.slider("Kelly Multiplier", 0.05, 1.00, float(settings["kelly_multiplier"]), 0.05)
    settings["max_unit"] = st.slider("Max Units Per Bet", 0.5, 5.0, float(settings["max_unit"]), 0.25)
    settings["execution_min_priority"] = st.slider("Minimum Execution Priority", 40.0, 140.0, float(settings["execution_min_priority"]), 1.0)
    settings["refresh_min_current_ev"] = st.slider("Min Current EV To Keep", -0.05, 0.10, float(settings["refresh_min_current_ev"]), 0.005)
    settings["refresh_priority_floor"] = st.slider("Min Current Priority To Keep", 40.0, 120.0, float(settings["refresh_priority_floor"]), 1.0)
    settings["book_score_min_samples"] = st.slider("Min Book Samples", 3, 30, int(settings["book_score_min_samples"]), 1)

    if st.button("Save Settings"):
        save_settings(settings)
        st.success("Settings saved.")

    st.divider()
    st.markdown("**Book Shopping**")
    st.write("Books scored:", len(book_scores_df))
    if len(book_scores_df):
        st.write("Top book:", normalize_text(book_scores_df.sort_values("book_shopping_score", ascending=False).iloc[0]["book"]))

    cs = closing_intel_summary(closing_intel_df)
    st.divider()
    st.markdown("**Closing Intel**")
    st.write("Take live:", cs["take_live"])
    st.write("Original OK:", cs["orig_ok"])
    st.write("Need shop:", cs["need_shop"])


# =========================
# TABS
# =========================
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "Upload + Multi-AI Board",
    "Best Bets",
    "Execution Board",
    "Live Odds Upload",
    "Line Movement + Refresh",
    "Book Shopping Score",
    "Closing Line Intelligence",
    "Bet Tracker + Learning",
    "Settlement + Accuracy",
])

input_df = pd.DataFrame()

with tab1:
    st.subheader("Upload Recommendation Data")
    uploaded = st.file_uploader("Upload recommendation CSV", type=["csv"])
    sample_df = pd.DataFrame([
        ["NBA", "Warriors vs Lakers", "player props", "Over 27.5 points", "Stephen Curry", "DraftKings", -115, 31.8, 27.5, 4.3, 0.66, 82, 5],
        ["NBA", "Heat vs Celtics", "spreads", "Celtics -6.5", "Boston Celtics", "BetMGM", -108, -8.1, -6.5, 1.6, 0.57, 71, 4],
    ], columns=["sport", "event", "market", "bet_type", "selection", "book", "odds", "projection", "line", "edge", "model_prob", "score", "consensus"])
    with st.expander("See sample recommendation format"):
        st.dataframe(sample_df, use_container_width=True)
        export_download(sample_df, "v21_sample_recommendations.csv", "Download sample recommendation CSV")
    if uploaded is not None:
        try:
            raw = pd.read_csv(uploaded)
            input_df = clean_input_df(raw)
            input_df = add_model_features(input_df, calibration_df, market_perf_df, book_perf_df, profile_perf_df, sharp_status, model_perf_df, model_segment_perf_df, settings)
            st.success(f"Loaded {len(input_df)} recommendation rows.")
        except Exception as e:
            st.error(f"Could not read CSV: {e}")
    if len(input_df):
        filtered = input_df.sort_values(["weighted_consensus_ratio", "model_yes_votes", "priority_score", "score", "ev"], ascending=[False, False, False, False, False])
        st.dataframe(filtered[["sport", "event", "market_bucket", "selection", "bet_type", "book", "odds", "calibrated_prob", "ev", "priority_score", "model_yes_votes", "weighted_consensus_ratio", "recommended_units"]], use_container_width=True)
        if st.button("Auto-Save Qualified Bets To Tracker"):
            qualified = qualify_plays(filtered, settings)
            updated_log, added = append_new_bets_to_log(qualified, bet_log)
            save_bet_log(updated_log)
            save_current_vote_snapshot(qualified)
            st.success(f"Auto-saved {added} bets.")
            st.rerun()


with tab2:
    st.subheader("Best Bets")
    if len(input_df) == 0:
        st.info("Upload a recommendation CSV first.")
    else:
        qualified = qualify_plays(input_df, settings).copy().sort_values(["weighted_consensus_ratio", "model_yes_votes", "priority_score", "score", "ev"], ascending=[False, False, False, False, False])
        st.dataframe(qualified[["sport", "event", "market_bucket", "selection", "bet_type", "book", "odds", "calibrated_prob", "ev", "priority_score", "model_yes_votes", "weighted_consensus_ratio", "recommended_units"]], use_container_width=True)
        for i, row in qualified.head(8).reset_index(drop=True).iterrows():
            st.code(format_pick_card(row))
        singles_for_exec = qualified.copy()
        parlays_for_exec = build_consensus_parlays(qualified, settings)
        if st.button("Build Ready-To-Place Execution Board"):
            new_board = build_execution_board(singles_for_exec, parlays_for_exec, settings)
            merged = merge_execution_board(new_board, execution_board_df)
            save_execution_board(merged)
            st.success(f"Execution board built with {len(new_board)} new items.")
            st.rerun()


with tab3:
    st.subheader("Execution Board")
    board = load_execution_board()
    summary = execution_summary(board)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Items", summary["total"])
    c2.metric("Locked", summary["locked"])
    c3.metric("Review", summary["review"])
    c4.metric("Placed", summary["placed"])
    if len(board) == 0:
        st.info("No execution items yet.")
    else:
        editable = ensure_columns(board.copy(), ["approved_units", "status", "locked_flag", "review_flag", "placed_flag", "user_placed", "difference_flag", "notes"])
        edited = st.data_editor(
            editable.sort_values(["execution_priority"], ascending=[False]),
            use_container_width=True,
            num_rows="dynamic",
            column_config={"status": st.column_config.SelectboxColumn("status", options=["review", "locked", "placed", "passed"])},
            key="execution_board_editor_v21",
        )
        if st.button("Save Execution Board Changes"):
            edited["locked_flag"] = np.where(edited["status"].astype(str) == "locked", 1, 0)
            edited["review_flag"] = np.where(edited["status"].astype(str) == "review", 1, 0)
            edited["placed_flag"] = np.where(edited["status"].astype(str) == "placed", 1, 0)
            edited["user_placed"] = np.where(edited["status"].astype(str) == "placed", 1, edited["user_placed"].fillna(0))
            edited["difference_flag"] = np.where(safe_to_numeric(edited["approved_units"]).round(2) != safe_to_numeric(edited["recommended_units"]).round(2), 1, 0)
            save_execution_board(edited)
            st.success("Execution board updated.")
            st.rerun()
        export_download(board, "v21_execution_board.csv", "Download execution board CSV")


with tab4:
    st.subheader("Live Odds Upload")
    live_upload = st.file_uploader("Upload live odds CSV", type=["csv"], key="live_odds_upload_v21")
    live_sample = pd.DataFrame([
        ["NBA", "Warriors vs Lakers", "player props", "Over 27.5 points", "Stephen Curry", "FanDuel", -110, 27.5],
        ["NBA", "Heat vs Celtics", "spreads", "Celtics -6.5", "Boston Celtics", "Caesars", -102, -6.5],
    ], columns=["sport", "event", "market", "bet_type", "selection", "book", "current_odds", "current_line"])
    with st.expander("See sample live odds format"):
        st.dataframe(live_sample, use_container_width=True)
        export_download(live_sample, "v21_sample_live_odds.csv", "Download sample live odds CSV")
    if live_upload is not None:
        try:
            raw_live = pd.read_csv(live_upload)
            cleaned_live = clean_live_odds_df(raw_live)
            cleaned_live["captured_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_live_odds(cleaned_live)
            st.success(f"Saved {len(cleaned_live)} live odds rows.")
        except Exception as e:
            st.error(f"Could not read live odds CSV: {e}")
    current_live = load_live_odds()
    if len(current_live) > 0:
        st.dataframe(current_live, use_container_width=True)


with tab5:
    st.subheader("Line Movement + Refresh")
    board = load_execution_board()
    live = load_live_odds()
    if len(board) == 0:
        st.info("Build an execution board first.")
    elif len(live) == 0:
        st.info("Upload a live odds snapshot first.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Run Live Odds Comparison"):
                new_monitor = build_live_odds_monitor(board, live, settings)
                merged_monitor = merge_live_monitor(load_line_movement_monitor(), new_monitor)
                save_line_movement_monitor(merged_monitor)
                st.success(f"Compared {len(new_monitor)} execution items.")
                st.rerun()
        with c2:
            if st.button("Refresh Execution Board From Live Odds"):
                refreshed = refresh_execution_board_with_live(board, live, settings)
                save_execution_refresh(refreshed)
                st.success(f"Refreshed {len(refreshed)} single-bet execution items.")
                st.rerun()

        monitor = load_line_movement_monitor()
        refreshed = load_execution_refresh()
        msum = live_monitor_summary(monitor)
        rsum = refresh_summary(refreshed)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Bet Now", msum["bet_now"])
        c2.metric("Wait", msum["wait"])
        c3.metric("Pass", msum["pass"])
        c4.metric("Still Qualify", rsum["qualify_yes"])

        if len(monitor) > 0:
            st.markdown("**Line movement**")
            st.dataframe(monitor[["sport", "event", "selection", "bet_type", "rec_book", "rec_odds", "best_current_book", "best_current_odds", "implied_prob_change", "timing_signal"]], use_container_width=True)
        if len(refreshed) > 0:
            st.markdown("**Refresh board**")
            st.dataframe(refreshed[["sport", "event", "selection", "bet_type", "original_book", "current_best_book", "original_ev", "current_ev", "ev_delta", "original_execution_priority", "current_execution_priority", "priority_delta", "original_units", "refreshed_units", "refresh_signal", "still_qualifies"]], use_container_width=True)
            if st.button("Apply Refresh To Execution Board"):
                updated_board = apply_refresh_to_execution_board(load_execution_board(), refreshed)
                save_execution_board(updated_board)
                st.success("Execution board updated with refreshed live executable values.")
                st.rerun()


with tab6:
    st.subheader("Book Shopping Score")
    if st.button("Rebuild Book Shopping Scores"):
        scores = build_book_shopping_scores(load_model_memory(), load_live_odds(), settings)
        save_book_scores(scores)
        st.success(f"Scored {len(scores)} book/sport pairs.")
        st.rerun()

    scores = load_book_scores()
    if len(scores) == 0:
        st.info("No book scores yet. Upload live odds and/or settle bets, then rebuild scores.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Books Scored", len(scores))
        c2.metric("Elite Books", int((scores["book_quality_label"] == "Elite").sum()))
        c3.metric("Strong Books", int((scores["book_quality_label"] == "Strong").sum()))
        st.dataframe(scores.sort_values(["book_shopping_score", "avg_clv"], ascending=[False, False]), use_container_width=True)
        export_download(scores, "v21_book_shopping_scores.csv", "Download book shopping scores CSV")


with tab7:
    st.subheader("Closing Line Intelligence")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Build Closing Line Intelligence"):
            intel = build_closing_line_intelligence(load_execution_board(), load_live_odds(), load_bet_log(), load_book_scores())
            save_closing_line_intel(intel)
            st.success(f"Built {len(intel)} closing-line intelligence rows.")
            st.rerun()
    with c2:
        if st.button("Refresh Closing Intel"):
            intel = build_closing_line_intelligence(load_execution_board(), load_live_odds(), load_bet_log(), load_book_scores())
            save_closing_line_intel(intel)
            st.success("Closing intel refreshed.")
            st.rerun()

    intel = load_closing_line_intel()
    summary = closing_intel_summary(intel)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows", summary["rows"])
    c2.metric("Take Live", summary["take_live"])
    c3.metric("Original OK", summary["orig_ok"])
    c4.metric("Need Shop", summary["need_shop"])

    if len(intel) == 0:
        st.info("No closing-line intelligence yet.")
    else:
        st.dataframe(
            intel[[
                "sport", "event", "selection", "bet_type",
                "recommended_book", "recommended_odds",
                "best_live_book", "best_live_odds",
                "closing_book", "closing_odds",
                "rec_vs_close_clv", "live_vs_close_clv",
                "best_source", "shopping_signal", "book_shopping_score", "intel_note"
            ]].sort_values(["shopping_signal", "book_shopping_score"], ascending=[True, False]),
            use_container_width=True,
        )
        export_download(intel, "v21_closing_line_intelligence.csv", "Download closing line intelligence CSV")


with tab8:
    st.subheader("Bet Tracker + Learning")
    bet_log = update_bet_outcomes(load_bet_log())
    metrics = summary_metrics(bet_log)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Bets", metrics["total_bets"])
    c2.metric("Record", f'{metrics["wins"]}-{metrics["losses"]}-{metrics["pushes"]}')
    c3.metric("Profit (u)", f'{metrics["profit_units"]:.2f}')
    c4.metric("ROI", f'{metrics["roi"]*100:.1f}%')

    if len(bet_log) == 0:
        st.info("No tracked bets yet.")
    else:
        editable = ensure_columns(bet_log.copy(), ["closing_odds", "result", "notes"])
        edited = st.data_editor(
            editable,
            use_container_width=True,
            num_rows="dynamic",
            column_config={"result": st.column_config.SelectboxColumn("result", options=["", "win", "loss", "push", "void"])},
            key="bet_log_editor_v21",
        )
        if st.button("Save Tracker Changes"):
            edited = update_bet_outcomes(edited)
            save_bet_log(edited)

            settled = edited[edited["result"].astype(str).str.lower().isin(["win", "loss", "push", "void"])].copy()
            if len(settled) > 0:
                mem = load_model_memory()
                mem_add = settled[["market", "market_bucket", "sport", "book", "bet_type", "selection", "event", "odds", "model_prob", "calibrated_prob", "closing_odds", "result", "recommended_units", "profit_units", "clv", "profile_key", "sharp_flag"]].copy()
                mem_add = mem_add.rename(columns={"recommended_units": "units"})
                mem_add["date"] = datetime.now().strftime("%Y-%m-%d")
                mem = pd.concat([mem, mem_add], ignore_index=True)
                mem = mem.drop_duplicates(subset=["date", "sport", "market", "selection", "book", "odds", "result"], keep="last")
                save_model_memory(mem)

                scores = build_book_shopping_scores(mem, load_live_odds(), settings)
                save_book_scores(scores)

                votes_hist = load_model_votes_history()
                if len(votes_hist) > 0 and "bet_id" in votes_hist.columns:
                    result_map = settled.set_index("bet_id")["result"].to_dict()
                    votes_hist["result"] = votes_hist["bet_id"].map(result_map).fillna(votes_hist.get("result"))
                    save_model_votes_history(votes_hist)
                    save_model_performance(summarize_model_performance(votes_hist))
                    save_model_segment_performance(summarize_model_segment_performance(votes_hist, min_samples=int(settings["adaptive_min_samples"])))

            st.success("Tracker, learning memory, and book-shopping scores updated.")
            st.rerun()
        export_download(bet_log, "v21_bet_log.csv", "Download bet log CSV")


with tab9:
    st.subheader("Settlement + Accuracy")
    settlement = load_execution_settlement()
    if len(settlement) == 0:
        st.info("No settlement data yet.")
    else:
        acc_placed = settlement[settlement["status_at_execution"].astype(str) == "placed"].copy()
        c1, c2, c3 = st.columns(3)
        c1.metric("Placed Rows", len(acc_placed))
        c2.metric("AI P/L", f"{settlement['ai_profit_units'].dropna().sum():.2f}u")
        c3.metric("Placed P/L", f"{acc_placed['placed_profit_units'].dropna().sum():.2f}u")
        st.dataframe(settlement_detail_table(settlement), use_container_width=True)
        export_download(settlement, "v21_execution_settlement.csv", "Download execution settlement CSV")
