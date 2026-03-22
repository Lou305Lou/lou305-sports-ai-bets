
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
APP_TITLE = "Sports AI Betting Dashboard — V17"
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

BET_LOG_PATH = DATA_DIR / "bet_log.csv"
SETTINGS_PATH = DATA_DIR / "settings.json"
MODEL_MEMORY_PATH = DATA_DIR / "model_memory.csv"
BOOK_PERF_PATH = DATA_DIR / "book_performance.csv"
CALIBRATION_PATH = DATA_DIR / "calibration_profile.csv"
PROFILE_PERF_PATH = DATA_DIR / "profile_performance.csv"


# =========================
# PAGE
# =========================
st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title(APP_TITLE)
st.caption("V17: true self-learning + CLV engine + confidence calibration + sharp mode + profile filtering")


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


def pct(x):
    try:
        return f"{100 * float(x):.1f}%"
    except Exception:
        return "—"


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


def plus_money_range_ok(odds, min_odds=-200, max_odds=150):
    try:
        odds = float(odds)
        return min_odds <= odds <= max_odds
    except Exception:
        return False


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
    upper = lower + 0.1
    if upper > 1.0:
        upper = 1.0
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
        "priority_score", "consensus", "tier", "recommended_units", "sharp_flag",
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


def load_book_performance():
    cols = ["sport", "book", "bets", "units", "profit_units", "roi", "win_rate", "avg_clv", "temperature"]
    return safe_read_csv(BOOK_PERF_PATH, cols)


def save_book_performance(df):
    safe_write_csv(df, BOOK_PERF_PATH)


def load_calibration_profile():
    cols = ["sport", "market_bucket", "prob_bucket", "bets", "pred_avg", "actual_win_rate", "delta", "multiplier"]
    return safe_read_csv(CALIBRATION_PATH, cols)


def save_calibration_profile(df):
    safe_write_csv(df, CALIBRATION_PATH)


def load_profile_performance():
    cols = ["profile_key", "sport", "market_bucket", "bets", "units", "profit_units", "roi", "win_rate", "avg_clv", "profile_signal"]
    return safe_read_csv(PROFILE_PERF_PATH, cols)


def save_profile_performance(df):
    safe_write_csv(df, PROFILE_PERF_PATH)


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

    required = [
        "sport", "event", "market", "bet_type", "selection", "book",
        "odds", "projection", "line", "edge", "model_prob", "score", "consensus"
    ]
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
            + df["odds"].apply(lambda x: 10 if plus_money_range_ok(x, -200, 150) else 0).fillna(0)
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


# =========================
# LEARNING TABLES
# =========================
def summarize_market_performance(memory_df, min_samples=15):
    if len(memory_df) == 0:
        return pd.DataFrame(columns=["sport", "market", "market_bucket", "bets", "units", "profit_units", "roi", "win_rate", "avg_clv", "market_signal"])

    m = ensure_columns(memory_df.copy(), ["sport", "market", "market_bucket", "units", "profit_units", "result", "clv"])
    settled = m[m["result"].astype(str).str.lower().isin(["win", "loss", "push", "void"])].copy()

    if len(settled) == 0:
        return pd.DataFrame(columns=["sport", "market", "market_bucket", "bets", "units", "profit_units", "roi", "win_rate", "avg_clv", "market_signal"])

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
    if len(memory_df) == 0:
        return pd.DataFrame(columns=["sport", "book", "bets", "units", "profit_units", "roi", "win_rate", "avg_clv", "temperature"])

    m = ensure_columns(memory_df.copy(), ["sport", "book", "units", "profit_units", "result", "clv"])
    settled = m[m["result"].astype(str).str.lower().isin(["win", "loss", "push", "void"])].copy()
    if len(settled) == 0:
        return pd.DataFrame(columns=["sport", "book", "bets", "units", "profit_units", "roi", "win_rate", "avg_clv", "temperature"])

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
        .agg(
            bets=("actual_result", "count"),
            pred_avg=("model_prob", "mean"),
            actual_win_rate=("actual_result", "mean"),
        )
        .reset_index()
    )
    grp["delta"] = grp["actual_win_rate"] - grp["pred_avg"]

    def calc_multiplier(row):
        if row["bets"] < min_samples:
            return 1.0
        pred = float(row["pred_avg"])
        actual = float(row["actual_win_rate"])
        if pred <= 0:
            return 1.0
        raw = actual / pred
        return float(np.clip(raw, 0.85, 1.15))

    grp["multiplier"] = grp.apply(calc_multiplier, axis=1)
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

    sharp = (
        pd.notna(avg_clv) and
        avg_clv >= float(settings["sharp_mode_clv_threshold"]) and
        roi >= float(settings["sharp_mode_roi_threshold"])
    )
    return {"sharp_mode": bool(sharp), "roi": roi, "avg_clv": avg_clv, "samples": len(settled)}


# =========================
# ADJUSTMENT FUNCTIONS
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

    units = max(0.10, min(max_unit, units))
    return round(units, 2)


def adjusted_priority_score(row, market_perf_df, book_perf_df, profile_perf_df, sharp_status, settings):
    base_score = float(row.get("score", 0) if pd.notna(row.get("score", np.nan)) else 0)
    m_w = market_weight(row, market_perf_df, settings)
    b_w = book_weight(row, book_perf_df, settings)
    p_w = profile_weight(row, profile_perf_df, settings)
    sharp_w = sharp_mode_weight(sharp_status, settings)
    ev_bonus = 12 * float(row.get("ev", 0) if pd.notna(row.get("ev", np.nan)) else 0)
    clv_bonus = 0.0
    return round(base_score * m_w * b_w * p_w * sharp_w + ev_bonus + clv_bonus, 2)


def qualify_plays(df, settings):
    if len(df) == 0:
        return df.copy()
    out = df.copy()
    out = out[
        (out["consensus"] >= settings["min_consensus"]) &
        (out["score"] >= 65) &
        (out["odds"] >= settings["default_odds_min"]) &
        (out["odds"] <= settings["default_odds_max"])
    ].copy()

    if settings.get("suppress_losing_profiles", True) and "profile_signal" in out.columns:
        out = out[out["profile_signal"].astype(str) != "Suppress"].copy()

    return out


def add_model_features(df, calibration_df, market_perf_df, book_perf_df, profile_perf_df, sharp_status, settings):
    out = df.copy()
    out = apply_calibration(out, calibration_df, settings)
    out["ev"] = out.apply(lambda r: compute_ev(r.get("calibrated_prob", np.nan), r.get("odds", np.nan)), axis=1)
    out["profile_signal"] = out["profile_key"].map(
        profile_perf_df.set_index("profile_key")["profile_signal"].to_dict()
    ) if len(profile_perf_df) else "Neutral"
    out["sharp_flag"] = "Sharp" if sharp_status.get("sharp_mode", False) else "Normal"
    out["recommended_units"] = out.apply(
        lambda r: recommend_units(r, settings, market_perf_df, book_perf_df, profile_perf_df, sharp_status), axis=1
    )
    out["priority_score"] = out.apply(
        lambda r: adjusted_priority_score(r, market_perf_df, book_perf_df, profile_perf_df, sharp_status, settings), axis=1
    )
    return out


# =========================
# PARLAYS
# =========================
def same_pick_conflict(a, b):
    sa = normalize_text(a.get("selection", "")).lower()
    sb = normalize_text(b.get("selection", "")).lower()
    ba = normalize_text(a.get("bet_type", "")).lower()
    bb = normalize_text(b.get("bet_type", "")).lower()
    return sa == sb and ba == bb


def parlay_correlation_penalty(legs):
    penalty = 0.0
    reasons = []

    if legs["event"].nunique() < len(legs):
        dup_count = len(legs) - legs["event"].nunique()
        penalty += 8.0 * dup_count
        reasons.append("same-event overlap")

    market_buckets = legs["market_bucket"].astype(str).tolist()
    if market_buckets.count("Totals") >= 2 and legs["event"].nunique() < len(legs):
        penalty += 6.0
        reasons.append("same-event totals linkage")

    selections = legs["selection"].astype(str).str.lower()
    if selections.nunique() < len(legs):
        penalty += 10.0
        reasons.append("duplicate selection")

    suppressed_profiles = (legs.get("profile_signal", pd.Series(["Neutral"] * len(legs))).astype(str) == "Suppress").sum()
    if suppressed_profiles > 0:
        penalty += 9.0 * suppressed_profiles
        reasons.append("suppressed profile")

    for i in range(len(legs)):
        for j in range(i + 1, len(legs)):
            if same_pick_conflict(legs.iloc[i], legs.iloc[j]):
                penalty += 12.0
                reasons.append("same pick repeated")

    return penalty, ", ".join(sorted(set(reasons))) if reasons else "low correlation"


def build_consensus_parlays(df, settings):
    if len(df) == 0:
        return pd.DataFrame()

    df = df.copy()
    df = df.sort_values(["priority_score", "score", "ev"], ascending=[False, False, False]).head(14)

    rows = []
    min_legs = int(settings["min_parlay_legs"])
    max_legs = int(settings["max_parlay_legs"])

    for leg_count in range(min_legs, max_legs + 1):
        for combo in itertools.combinations(df.index.tolist(), leg_count):
            legs = df.loc[list(combo)].copy()

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
            raw_score = (
                legs["priority_score"].mean() * 0.50
                + legs["consensus"].mean() * 5.0
                + max(0, (joint_prob - implied) * 100) * 0.9
                + min(10, len(legs))
            )
            final_score = raw_score - penalty if settings.get("correlation_penalty_on", True) else raw_score

            rows.append({
                "legs": len(legs),
                "parlay_odds": int(parlay_american),
                "joint_prob": joint_prob,
                "implied_prob": implied,
                "ev": ev,
                "raw_score": round(raw_score, 2),
                "correlation_penalty": round(penalty, 2),
                "score": round(final_score, 2),
                "correlation_note": penalty_reason,
                "summary": " + ".join(legs["selection"].astype(str) + " " + legs["bet_type"].astype(str)),
                "events": " | ".join(legs["event"].astype(str)),
            })

    out = pd.DataFrame(rows)
    if len(out) == 0:
        return out

    out = out.sort_values(["score", "ev", "joint_prob"], ascending=[False, False, False]).drop_duplicates(subset=["summary"])
    return out.head(12)


# =========================
# LOGGING / METRICS
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
        "priority_score", "consensus", "tier", "recommended_units", "sharp_flag",
        "profile_key", "result", "profit_units", "clv", "notes"
    ]
    to_add = ensure_columns(to_add, keep_cols)
    updated = pd.concat([base, to_add[keep_cols]], ignore_index=True)
    return updated, len(to_add)


def update_bet_outcomes(log_df):
    out = log_df.copy()
    out = ensure_columns(out, ["odds", "recommended_units", "result", "closing_odds"])
    out["profit_units"] = out.apply(
        lambda r: calculate_profit_units(r.get("result", np.nan), r.get("odds", np.nan), r.get("recommended_units", np.nan)),
        axis=1,
    )
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

    return {
        "total_bets": total_bets,
        "settled": len(settled),
        "pending": len(pending),
        "wins": int(wins),
        "losses": int(losses),
        "pushes": int(pushes),
        "profit_units": profit_units,
        "roi": roi,
        "avg_clv": avg_clv,
    }


def format_pick_card(row):
    grade = row.get("grade", "D")
    emoji = score_to_emoji(row.get("score", 0))
    return f"""#{int(row.name)+1} {normalize_text(row.get("selection", ""))} — {normalize_text(row.get("bet_type", ""))}
{normalize_text(row.get("event", ""))} • {normalize_text(row.get("market_bucket", ""))} • {normalize_text(row.get("book", ""))}
Projection: {row.get("projection", np.nan):.2f} | Edge: {row.get("edge", np.nan):.2f} | Odds: {int(row.get("odds", 0)) if pd.notna(row.get("odds")) else "—"}
Model Hit %: {pct(row.get("model_prob", np.nan))} | Calibrated Hit %: {pct(row.get("calibrated_prob", np.nan))} | EV: {pct(row.get("ev", np.nan))}
Score: {row.get("score", np.nan):.1f} ({emoji} {grade}) | Priority: {row.get("priority_score", np.nan):.1f}
Tier: {row.get("tier", "Tier 4")} | Units: {row.get("recommended_units", np.nan):.2f}u | Consensus: {int(row.get("consensus", 0))}/5 | Mode: {normalize_text(row.get("sharp_flag", "Normal"))}"""


def export_download(df, filename, label):
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(label, csv, file_name=filename, mime="text/csv")


# =========================
# LOAD STATE
# =========================
settings = load_settings()
bet_log = update_bet_outcomes(load_bet_log())
memory_df = load_model_memory()

market_perf_df = summarize_market_performance(memory_df, min_samples=int(settings["learning_min_samples"]))
book_perf_df = summarize_book_performance(memory_df, min_samples=int(settings["book_min_samples"]))
calibration_df = build_calibration_profile(memory_df, min_samples=int(settings["calibration_min_samples"]))
profile_perf_df = summarize_profile_performance(memory_df, min_samples=int(settings["profile_min_samples"]))
sharp_status = evaluate_sharp_mode(memory_df, settings)

save_book_performance(book_perf_df)
save_calibration_profile(calibration_df)
save_profile_performance(profile_perf_df)


# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.header("V17 Controls")

    settings["bankroll"] = st.number_input("Bankroll", min_value=100.0, value=float(settings["bankroll"]), step=50.0)
    settings["kelly_multiplier"] = st.slider("Kelly Multiplier", 0.05, 1.00, float(settings["kelly_multiplier"]), 0.05)
    settings["base_unit_pct"] = st.slider("Base Unit % of Bankroll", 0.0025, 0.05, float(settings["base_unit_pct"]), 0.0025)
    settings["max_unit"] = st.slider("Max Units Per Bet", 0.5, 5.0, float(settings["max_unit"]), 0.25)
    settings["min_consensus"] = st.selectbox("Minimum AI Consensus", [2, 3, 4, 5], index=[2, 3, 4, 5].index(int(settings["min_consensus"])))
    settings["default_odds_min"] = st.number_input("Minimum Odds", value=int(settings["default_odds_min"]), step=5)
    settings["default_odds_max"] = st.number_input("Maximum Odds", value=int(settings["default_odds_max"]), step=5)
    settings["min_parlay_legs"] = st.selectbox("Min Parlay Legs", [2, 3], index=0 if int(settings["min_parlay_legs"]) == 2 else 1)
    settings["max_parlay_legs"] = st.selectbox("Max Parlay Legs", [3, 4, 5], index=[3, 4, 5].index(int(settings["max_parlay_legs"])))
    settings["learning_min_samples"] = st.number_input("Min Samples For Market Learning", min_value=5, value=int(settings["learning_min_samples"]), step=1)
    settings["book_min_samples"] = st.number_input("Min Samples For Book Temperature", min_value=5, value=int(settings["book_min_samples"]), step=1)
    settings["profile_min_samples"] = st.number_input("Min Samples For Profile Filter", min_value=5, value=int(settings["profile_min_samples"]), step=1)
    settings["calibration_min_samples"] = st.number_input("Min Samples For Calibration", min_value=5, value=int(settings["calibration_min_samples"]), step=1)
    settings["correlation_penalty_on"] = st.checkbox("Use Correlation Penalty In Parlays", value=bool(settings["correlation_penalty_on"]))
    settings["auto_prioritize_profitable_markets"] = st.checkbox("Auto-Prioritize Profitable Markets", value=bool(settings["auto_prioritize_profitable_markets"]))
    settings["sharp_mode_auto"] = st.checkbox("Auto Sharp Mode", value=bool(settings["sharp_mode_auto"]))
    settings["suppress_losing_profiles"] = st.checkbox("Suppress Losing Profiles", value=bool(settings["suppress_losing_profiles"]))

    if st.button("Save Settings"):
        save_settings(settings)
        st.success("Settings saved.")

    st.divider()
    st.markdown("**Sharp Mode Status**")
    st.write("Mode:", "ON" if sharp_status.get("sharp_mode", False) else "OFF")
    st.write("Samples:", int(sharp_status.get("samples", 0) or 0))
    st.write("ROI:", pct(sharp_status.get("roi", np.nan)))
    st.write("Avg CLV:", pct(sharp_status.get("avg_clv", np.nan)))


# =========================
# TABS
# =========================
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Upload + AI Board",
    "Best Bets",
    "Consensus Parlays",
    "Bet Tracker + CLV",
    "Calibration Engine",
    "Profile Filter",
    "Book + Market Intelligence",
])

input_df = pd.DataFrame()

with tab1:
    st.subheader("Upload Market Data")
    st.write("Upload a CSV of candidate bets. V17 calibrates hit rates, measures profile quality, and applies CLV-based sharp mode.")

    uploaded = st.file_uploader("Upload CSV", type=["csv"])

    sample_cols = [
        "sport", "event", "market", "bet_type", "selection", "book",
        "odds", "projection", "line", "edge", "model_prob", "score", "consensus"
    ]
    sample_df = pd.DataFrame([
        ["NBA", "Warriors vs Lakers", "player props", "Over 27.5 points", "Stephen Curry", "DraftKings", -115, 31.8, 27.5, 4.3, 0.66, 82, 5],
        ["NBA", "Warriors vs Lakers", "totals", "Over 234.5", "Game Total", "FanDuel", -110, 239.2, 234.5, 4.7, 0.58, 74, 4],
        ["NBA", "Heat vs Celtics", "spreads", "Celtics -6.5", "Boston Celtics", "BetMGM", -108, -8.1, -6.5, 1.6, 0.57, 71, 4],
        ["NHL", "Rangers vs Leafs", "moneyline", "Moneyline", "Rangers", "Caesars", 118, np.nan, np.nan, np.nan, 0.49, 67, 3],
    ], columns=sample_cols)

    with st.expander("See sample input format"):
        st.dataframe(sample_df, use_container_width=True)
        export_download(sample_df, "v17_sample_input.csv", "Download sample CSV")

    if uploaded is not None:
        try:
            raw = pd.read_csv(uploaded)
            input_df = clean_input_df(raw)
            input_df = add_model_features(
                input_df, calibration_df, market_perf_df, book_perf_df, profile_perf_df, sharp_status, settings
            )
            st.success(f"Loaded {len(input_df)} rows.")
        except Exception as e:
            st.error(f"Could not read CSV: {e}")

    if len(input_df) > 0:
        c1, c2, c3 = st.columns(3)
        with c1:
            sports = ["All"] + sorted(input_df["sport"].dropna().astype(str).unique().tolist())
            sport_filter = st.selectbox("Sport", sports)
        with c2:
            mkts = ["All"] + sorted(input_df["market_bucket"].dropna().astype(str).unique().tolist())
            market_filter = st.selectbox("Market Bucket", mkts)
        with c3:
            books = ["All"] + sorted(input_df["book"].dropna().astype(str).unique().tolist())
            book_filter = st.selectbox("Book", books)

        filtered = input_df.copy()
        if sport_filter != "All":
            filtered = filtered[filtered["sport"].astype(str) == sport_filter]
        if market_filter != "All":
            filtered = filtered[filtered["market_bucket"].astype(str) == market_filter]
        if book_filter != "All":
            filtered = filtered[filtered["book"].astype(str) == book_filter]

        filtered = filtered.sort_values(["priority_score", "score", "ev"], ascending=[False, False, False])

        st.subheader("AI Board")
        st.dataframe(
            filtered[[
                "sport", "event", "market_bucket", "selection", "bet_type", "book",
                "odds", "projection", "line", "edge", "model_prob", "calibrated_prob",
                "ev", "score", "priority_score", "consensus", "profile_signal",
                "recommended_units", "sharp_flag"
            ]],
            use_container_width=True,
        )

        if st.button("Auto-Save Qualified Bets To Tracker"):
            qualified = qualify_plays(filtered, settings)
            updated_log, added = append_new_bets_to_log(qualified, bet_log)
            save_bet_log(updated_log)
            st.success(f"Auto-saved {added} new bets.")
            st.rerun()


with tab2:
    st.subheader("Best Bets")
    if len(input_df) == 0:
        st.info("Upload a CSV in the first tab to generate V17 best bets.")
    else:
        qualified = qualify_plays(input_df, settings).copy()
        qualified = qualified.sort_values(["priority_score", "score", "ev"], ascending=[False, False, False])

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Qualified Bets", len(qualified))
        c2.metric("Avg EV", pct(qualified["ev"].mean()) if len(qualified) else "—")
        c3.metric("Avg Calibrated Hit %", pct(qualified["calibrated_prob"].mean()) if len(qualified) else "—")
        c4.metric("Sharp Mode", "ON" if sharp_status.get("sharp_mode", False) else "OFF")

        if len(qualified) == 0:
            st.warning("No plays met the filters. Try loosening consensus or odds range.")
        else:
            st.dataframe(
                qualified[[
                    "sport", "event", "market_bucket", "selection", "bet_type", "book",
                    "odds", "edge", "model_prob", "calibrated_prob", "ev", "score",
                    "priority_score", "consensus", "tier", "profile_signal",
                    "recommended_units", "sharp_flag"
                ]],
                use_container_width=True,
            )

            st.subheader("Top Pick Cards")
            top_cards = qualified.head(10).reset_index(drop=True)
            for i, row in top_cards.iterrows():
                st.code(format_pick_card(row))


with tab3:
    st.subheader("Consensus Parlays")
    if len(input_df) == 0:
        st.info("Upload a CSV in the first tab to generate parlays.")
    else:
        qualified = qualify_plays(input_df, settings).copy()
        parlays = build_consensus_parlays(qualified, settings)
        if len(parlays) == 0:
            st.warning("No qualifying parlays found.")
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("Parlays Found", len(parlays))
            c2.metric("Best Score", f"{parlays['score'].max():.1f}")
            c3.metric("Best EV", pct(parlays["ev"].max()))

            st.dataframe(parlays, use_container_width=True)
            export_download(parlays, "v17_consensus_parlays.csv", "Download parlays CSV")


with tab4:
    st.subheader("Bet Tracker + CLV")
    bet_log = update_bet_outcomes(load_bet_log())
    metrics = summary_metrics(bet_log)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Bets", metrics["total_bets"])
    c2.metric("Record", f'{metrics["wins"]}-{metrics["losses"]}-{metrics["pushes"]}')
    c3.metric("Profit (u)", f'{metrics["profit_units"]:.2f}')
    c4.metric("ROI", f'{metrics["roi"]*100:.1f}%')

    c5, c6 = st.columns(2)
    c5.metric("Pending", metrics["pending"])
    c6.metric("Avg CLV", f'{metrics["avg_clv"]*100:.2f}%' if pd.notna(metrics["avg_clv"]) else "—")

    if len(bet_log) == 0:
        st.info("No tracked bets yet. Use Auto-Save in the first tab.")
    else:
        editable = ensure_columns(bet_log.copy(), ["closing_odds", "result", "notes"])
        edited = st.data_editor(
            editable,
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "result": st.column_config.SelectboxColumn("result", options=["", "win", "loss", "push", "void"]),
            },
            key="bet_log_editor_v17",
        )

        if st.button("Save Tracker Changes"):
            edited = update_bet_outcomes(edited)
            save_bet_log(edited)

            settled = edited[edited["result"].astype(str).str.lower().isin(["win", "loss", "push", "void"])].copy()
            if len(settled) > 0:
                mem = load_model_memory()
                mem_add = settled[[
                    "market", "market_bucket", "sport", "book", "bet_type", "selection", "event",
                    "odds", "model_prob", "calibrated_prob", "closing_odds", "result",
                    "recommended_units", "profit_units", "clv", "profile_key", "sharp_flag"
                ]].copy()
                mem_add = mem_add.rename(columns={"recommended_units": "units"})
                mem_add["date"] = datetime.now().strftime("%Y-%m-%d")
                mem = pd.concat([mem, mem_add], ignore_index=True)
                mem = mem.drop_duplicates(
                    subset=["date", "sport", "market", "selection", "book", "odds", "result"],
                    keep="last"
                )
                save_model_memory(mem)

                save_book_performance(summarize_book_performance(mem, min_samples=int(settings["book_min_samples"])))
                save_calibration_profile(build_calibration_profile(mem, min_samples=int(settings["calibration_min_samples"])))
                save_profile_performance(summarize_profile_performance(mem, min_samples=int(settings["profile_min_samples"])))

            st.success("Tracker, CLV, calibration, and learning profiles updated.")
            st.rerun()

        export_download(bet_log, "v17_bet_log.csv", "Download bet log CSV")


with tab5:
    st.subheader("Calibration Engine")
    calibration_df = build_calibration_profile(load_model_memory(), min_samples=int(settings["calibration_min_samples"]))

    if len(calibration_df) == 0:
        st.info("Not enough settled history yet for calibration.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Calibration Segments", len(calibration_df))
        c2.metric("Avg Multiplier", f"{calibration_df['multiplier'].mean():.3f}")
        c3.metric("Avg Delta", pct(calibration_df["delta"].mean()))

        st.dataframe(
            calibration_df.sort_values(["sport", "market_bucket", "prob_bucket"]),
            use_container_width=True,
        )

        st.markdown("**How calibration works**")
        st.write(
            "V17 compares predicted win probability to actual win rate by sport, market bucket, and probability band. "
            "If the model has been overconfident, calibrated probability is scaled down. If underconfident, it is scaled up."
        )
        export_download(calibration_df, "v17_calibration_profile.csv", "Download calibration CSV")


with tab6:
    st.subheader("Profile Filter")
    profile_perf_df = summarize_profile_performance(load_model_memory(), min_samples=int(settings["profile_min_samples"]))

    if len(profile_perf_df) == 0:
        st.info("Not enough settled history yet for profile filtering.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Tracked Profiles", len(profile_perf_df))
        c2.metric("Boosted Profiles", int((profile_perf_df["profile_signal"] == "Boost").sum()))
        c3.metric("Suppressed Profiles", int((profile_perf_df["profile_signal"] == "Suppress").sum()))

        st.dataframe(
            profile_perf_df.sort_values(["roi", "bets"], ascending=[False, False]),
            use_container_width=True,
        )

        st.markdown("**Profile logic**")
        st.write(
            "Profiles combine sport, market type, model probability band, edge band, and odds band. "
            "Winning profiles get boosted. Persistently losing profiles can be suppressed from best-bet consideration."
        )
        export_download(profile_perf_df, "v17_profile_performance.csv", "Download profile CSV")


with tab7:
    st.subheader("Book + Market Intelligence")
    current_memory = load_model_memory()
    market_perf_df = summarize_market_performance(current_memory, min_samples=int(settings["learning_min_samples"]))
    book_perf_df = summarize_book_performance(current_memory, min_samples=int(settings["book_min_samples"]))
    sharp_status = evaluate_sharp_mode(current_memory, settings)

    c1, c2, c3 = st.columns(3)
    c1.metric("Sharp Mode", "ON" if sharp_status.get("sharp_mode", False) else "OFF")
    c2.metric("System ROI", pct(sharp_status.get("roi", np.nan)))
    c3.metric("System Avg CLV", pct(sharp_status.get("avg_clv", np.nan)))

    st.markdown("**Market intelligence**")
    if len(market_perf_df) == 0:
        st.info("No market intelligence yet.")
    else:
        st.dataframe(market_perf_df.sort_values(["roi", "bets"], ascending=[False, False]), use_container_width=True)

    st.markdown("**Book intelligence**")
    if len(book_perf_df) == 0:
        st.info("No book intelligence yet.")
    else:
        st.dataframe(book_perf_df.sort_values(["roi", "bets"], ascending=[False, False]), use_container_width=True)

        export_download(book_perf_df, "v17_book_intelligence.csv", "Download book intelligence CSV")
        export_download(market_perf_df, "v17_market_intelligence.csv", "Download market intelligence CSV")
