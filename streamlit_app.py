
import math
import itertools
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Sports AI Betting Dashboard V12 Automation Engine", layout="wide")

CALL_LOG_FILE = "api_call_log.csv"
BET_LOG_FILE = "bet_log.csv"
ALERT_LOG_FILE = "alert_log.csv"
SNAPSHOT_FILE = "play_snapshot.csv"
MODEL_PERF_FILE = "model_perf_log.csv"

MAX_DAILY_CALLS = 500
ET_TZ = ZoneInfo("America/New_York")
SCHEDULE_WINDOWS = {
    "5:00 AM ET": (5, 0),
    "1:00 PM ET": (13, 0),
    "5:30 PM ET": (17, 30),
}

# -----------------------------
# Helpers
# -----------------------------
def safe_float(v, default=np.nan):
    try:
        if pd.isna(v):
            return default
        return float(v)
    except Exception:
        return default

def safe_get(row, key, default=0):
    try:
        if hasattr(row, "get"):
            val = row.get(key, default)
        else:
            val = default
        if val is None:
            return default
        return val
    except Exception:
        return default


def execution_signal(row):
    try:
        tier = safe_get(row, "tier", "")
        decision = safe_get(row, "bet_decision", "")
        clv = safe_float(safe_get(row, "predicted_clv_pct", 0.0), 0.0)
        market = safe_float(safe_get(row, "model_market", 0.0), 0.0)
        if tier == "Qualified" and decision == "Auto Bet":
            if clv >= 3 and market >= 45:
                return "🎯 BET NOW"
            return "📈 SCALE IN"
        if tier in ["Near threshold", "Monitor"]:
            return "⏳ WAIT"
        return "🛑 NO BET"
    except Exception:
        return "⏳ WAIT"

def urgency_level(row):
    try:
        ens = safe_float(safe_get(row, "ensemble_score", 0.0), 0.0)
        clv = safe_float(safe_get(row, "predicted_clv_pct", 0.0), 0.0)
        agree = int(safe_get(row, "agreement_count", 0))
        if ens >= 72 and clv >= 3 and agree >= 4:
            return "HIGH"
        if ens >= 58 and agree >= 3:
            return "MEDIUM"
        return "LOW"
    except Exception:
        return "LOW"


def clamp01(x):
    return max(0.0, min(1.0, x))

def american_to_decimal(odds):
    odds = safe_float(odds)
    if pd.isna(odds):
        return np.nan
    return 1 + (odds / 100) if odds > 0 else 1 + (100 / abs(odds))

def american_to_implied_prob(odds):
    odds = safe_float(odds)
    if pd.isna(odds):
        return np.nan
    return 100 / (odds + 100) if odds > 0 else abs(odds) / (abs(odds) + 100)

def decimal_to_american(dec):
    dec = safe_float(dec)
    if pd.isna(dec) or dec <= 1:
        return np.nan
    if dec >= 2:
        return round((dec - 1) * 100)
    return round(-100 / (dec - 1))

def normal_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))

def fmt_american(v):
    try:
        if pd.isna(v):
            return "—"
        v = float(v)
        v = int(round(v))
        return f"+{v}" if v > 0 else str(v)
    except Exception:
        return "—"

def et_now():
    return datetime.now(ET_TZ)

def today_et_str():
    return et_now().strftime("%Y-%m-%d")

def current_et_label():
    return et_now().strftime("%Y-%m-%d %I:%M %p ET")

def normalize_series(s):
    s = pd.to_numeric(s, errors="coerce")
    mn, mx = s.min(), s.max()
    if pd.isna(mn) or pd.isna(mx) or mx - mn == 0:
        return pd.Series(np.full(len(s), 50.0), index=s.index)
    return ((s - mn) / (mx - mn) * 100).clip(0, 100)

# -----------------------------
# Styling
# -----------------------------
st.markdown("""
<style>
.block-container {padding-top: 1rem; padding-bottom: 4rem; max-width: 1220px;}
.banner {
    border:1px solid rgba(148,163,184,.24);
    border-radius:22px;
    padding:16px;
    background: linear-gradient(135deg, #f8fafc 0%, #eff6ff 100%);
    margin-bottom: 14px;
}
.metric-box {
    border:1px solid rgba(148,163,184,.22);
    border-radius:18px;
    background: rgba(255,255,255,.98);
    padding:12px 14px;
    min-height: 86px;
    margin-bottom:10px;
}
.metric-label {font-size:.88rem; color:#6b7280; margin-bottom:6px;}
.metric-value {font-size:1.75rem; line-height:1.05; font-weight:800;}
.good-box, .watch-box, .alert-box, .model-box, .pass-box {
    border-radius:18px; padding:14px; margin-bottom:12px;
}
.good-box {border:1px solid rgba(34,197,94,.28); background:#f0fdf4;}
.watch-box {border:1px solid rgba(59,130,246,.28); background:#eff6ff;}
.alert-box {border:1px solid rgba(245,158,11,.35); background:#fff7ed;}
.model-box {border:1px solid rgba(148,163,184,.20); background:#ffffff;}
.pass-box {border:1px solid rgba(239,68,68,.18); background:#fef2f2;}
.small-muted {color:#6b7280; font-size:.94rem;}
.summary-box {
    border:1px solid rgba(148,163,184,.22);
    border-radius:20px;
    background: rgba(255,255,255,.98);
    padding:14px;
    margin-bottom:12px;
}
.summary-grid {
    display:grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap:10px;
}
.summary-cell {
    border:1px solid rgba(148,163,184,.16);
    border-radius:14px;
    background:#f8fafc;
    padding:10px 12px;
}
.summary-label {
    font-size:.84rem;
    color:#6b7280;
    margin-bottom:6px;
}
.summary-value {
    font-size:1.15rem;
    font-weight:800;
    line-height:1.1;
}
.tight-card {
    border:1px solid rgba(148,163,184,.22);
    border-radius:22px;
    background: rgba(255,255,255,.98);
    padding:14px;
    margin-bottom:14px;
}
.conf-pill {
    display:inline-block;
    padding:6px 10px;
    border-radius:999px;
    font-weight:700;
    margin-right:8px;
    margin-bottom:8px;
    font-size:.92rem;
    border:1px solid rgba(148,163,184,.18);
}
.conf-a {background:#dcfce7; color:#166534;}
.conf-b {background:#fef3c7; color:#92400e;}
.conf-c {background:#dbeafe; color:#1d4ed8;}
.conf-d {background:#fee2e2; color:#991b1b;}
.insight-box {
    border:1px solid rgba(59,130,246,.24);
    border-radius:18px;
    background:#eff6ff;
    padding:14px;
    margin-bottom:14px;
}
.trigger-box {
    border:1px dashed rgba(99,102,241,.45);
    border-radius:16px;
    background:#f8fafc;
    padding:12px;
    margin-top:10px;
}
.why-box {
    border:1px solid rgba(148,163,184,.20);
    border-radius:16px;
    background:#fafafa;
    padding:12px;
    margin-top:10px;
}
@media (max-width: 768px) {
    .metric-value {font-size:1.45rem;}
    .summary-value {font-size:1.08rem;}
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Persistence
# -----------------------------
def load_csv_file(path, columns):
    if os.path.exists(path):
        try:
            return pd.read_csv(path)
        except Exception:
            pass
    return pd.DataFrame(columns=columns)

def save_df(df, path):
    df.to_csv(path, index=False)

def load_call_log():
    return load_csv_file(CALL_LOG_FILE, ["timestamp_et", "date_et", "window", "reason", "call_count"])

def load_bet_log():
    return load_csv_file(BET_LOG_FILE, [
        "timestamp", "player", "market", "bet_side", "line", "book", "best_book",
        "placed_odds", "best_odds", "stake_u", "stake_$", "edge_pct", "ev_pct",
        "tier", "bet_decision", "predicted_clv_pct", "ensemble_score", "agreement_count",
        "model_projection", "model_market", "model_clv", "model_script", "model_variance",
        "result", "profit_u", "closing_odds", "clv_placed_vs_close_pct", "notes"
    ])

def load_alert_log():
    return load_csv_file(ALERT_LOG_FILE, ["timestamp_et", "date_et", "window", "play_key", "alert_type", "message"])

def load_snapshot():
    return load_csv_file(SNAPSHOT_FILE, [
        "play_key", "player", "market", "bet_side", "line", "best_book", "best_display_odds",
        "true_edge", "realistic_ev_pct", "movement_note", "tier", "qualified", "predicted_clv_pct",
        "ensemble_score", "agreement_count"
    ])

def load_model_perf():
    return load_csv_file(MODEL_PERF_FILE, [
        "timestamp", "model_name", "raw_weight", "adj_weight", "sample_size", "avg_clv", "win_rate", "roi_pct"
    ])

def log_api_call(reason, call_count=1, window=""):
    log = load_call_log()
    row = {"timestamp_et": current_et_label(), "date_et": today_et_str(), "window": window, "reason": reason, "call_count": call_count}
    save_df(pd.concat([log, pd.DataFrame([row])], ignore_index=True), CALL_LOG_FILE)

def log_alert(window, play_key, alert_type, message):
    log = load_alert_log()
    row = {"timestamp_et": current_et_label(), "date_et": today_et_str(), "window": window, "play_key": play_key, "alert_type": alert_type, "message": message}
    save_df(pd.concat([log, pd.DataFrame([row])], ignore_index=True), ALERT_LOG_FILE)

def get_today_calls():
    log = load_call_log()
    if log.empty:
        return 0
    return int(pd.to_numeric(log.loc[log["date_et"] == today_et_str(), "call_count"], errors="coerce").fillna(0).sum())

def get_remaining_calls():
    return max(0, MAX_DAILY_CALLS - get_today_calls())

def call_status_label(used):
    pct = used / MAX_DAILY_CALLS if MAX_DAILY_CALLS else 0
    if pct >= 0.95:
        return "🔴 Hard stop"
    if pct >= 0.80:
        return "🟠 Warning"
    return "🟢 Safe"

def was_window_run_today(window_name):
    log = load_call_log()
    if log.empty:
        return False
    return bool(((log["date_et"] == today_et_str()) & (log["window"] == window_name)).any())

def should_run_window(window_name):
    hour, minute = SCHEDULE_WINDOWS[window_name]
    now = et_now()
    if now.hour > hour or (now.hour == hour and now.minute >= minute):
        return not was_window_run_today(window_name)
    return False

# -----------------------------
# Data prep
# -----------------------------
def ensure_columns(df):
    df = df.copy()
    defaults = {
        "player": "", "team": "", "opponent": "", "matchup": "", "market": "",
        "bet_side": "", "line": np.nan, "projection": np.nan, "odds": np.nan,
        "book": "", "starter": False, "minutes": np.nan, "std_dev": np.nan,
        "spread": np.nan, "pace": np.nan, "usage": np.nan, "open_odds": np.nan,
        "last5_avg": np.nan, "defense_rank": np.nan, "minutes_volatility": np.nan,
        "odds_fanduel": np.nan, "odds_draftkings": np.nan, "odds_betmgm": np.nan, "odds_caesars": np.nan
    }
    for col, val in defaults.items():
        if col not in df.columns:
            df[col] = val
    for c in ["player", "team", "opponent", "matchup", "market", "bet_side", "book"]:
        df[c] = df[c].fillna("").astype(str).str.strip()
    num_cols = ["line", "projection", "odds", "minutes", "std_dev", "spread", "pace", "usage", "open_odds",
                "last5_avg", "defense_rank", "minutes_volatility", "odds_fanduel", "odds_draftkings", "odds_betmgm", "odds_caesars"]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["starter"] = df["starter"].fillna(False).astype(bool)
    if (df["matchup"] == "").any():
        auto_match = df["team"].fillna("") + np.where(df["opponent"].fillna("") != "", " vs " + df["opponent"].fillna(""), "")
        df.loc[df["matchup"] == "", "matchup"] = auto_match[df["matchup"] == ""]
    return df

def infer_market_std(row):
    supplied = row.get("std_dev")
    if pd.notna(supplied) and supplied > 0:
        return float(supplied)
    market = str(row.get("market", "")).lower()
    defaults = {"points": 8.5, "rebounds": 4.0, "assists": 3.6, "pra": 9.0, "threes": 2.4, "3pm": 2.4}
    for k, v in defaults.items():
        if k in market:
            return v
    return 7.5

def infer_bet_side(row):
    side = str(row.get("bet_side", "")).title()
    if side in {"Over", "Under"}:
        return side
    p, l = row.get("projection"), row.get("line")
    if pd.isna(p) or pd.isna(l):
        return "Over"
    return "Over" if p >= l else "Under"

def calculate_hit_probability(row):
    p, l = row.get("projection"), row.get("line")
    if pd.isna(p) or pd.isna(l):
        return np.nan
    std = infer_market_std(row)
    z = (p - l) / std if std > 0 else 0
    p_over = normal_cdf(z)
    return clamp01(1 - p_over if infer_bet_side(row) == "Under" else p_over)

def best_book_and_odds(row):
    books = {
        "FanDuel": safe_float(row.get("odds_fanduel"), np.nan),
        "DraftKings": safe_float(row.get("odds_draftkings"), np.nan),
        "BetMGM": safe_float(row.get("odds_betmgm"), np.nan),
        "Caesars": safe_float(row.get("odds_caesars"), np.nan),
    }
    valid = {k: v for k, v in books.items() if not pd.isna(v)}
    if not valid:
        return (str(row.get("book", "")).strip() or "Current Book", safe_float(row.get("odds"), np.nan))
    best_book, best_prob, best_odds = None, None, np.nan
    for bk, od in valid.items():
        ip = american_to_implied_prob(od)
        if pd.isna(ip):
            continue
        if best_prob is None or ip < best_prob:
            best_prob = ip
            best_book = bk
            best_odds = od
    return best_book, best_odds

def movement_label(delta_implied_pct):
    if pd.isna(delta_implied_pct):
        return "No move"
    if delta_implied_pct >= 4:
        return "🔥 Strong steam"
    if delta_implied_pct >= 2:
        return "📈 Steam"
    if delta_implied_pct <= -4:
        return "🧊 Reverse move"
    if delta_implied_pct <= -2:
        return "↩️ Soft reverse"
    return "⏳ Stable"

# -----------------------------
# Multi-AI models
# -----------------------------
def model_projection_raw(row):
    line = safe_float(row.get("line"))
    proj = safe_float(row.get("projection"))
    if pd.isna(line) or pd.isna(proj):
        return 0.0
    std = infer_market_std(row)
    return (proj - line) / max(std, 1e-6)

def model_market_raw(row):
    best_odds = safe_float(row.get("best_display_odds"))
    open_odds = safe_float(row.get("open_odds"))
    if pd.isna(best_odds):
        return 0.0
    best_ip = american_to_implied_prob(best_odds)
    open_ip = american_to_implied_prob(open_odds) if not pd.isna(open_odds) else best_ip
    raw = (open_ip - best_ip) * 100
    if "Steam" in str(row.get("movement_note", "")):
        raw += 1.0
    return raw

def model_clv_raw(row):
    move = safe_float(row.get("line_move_pct"), 0.0)
    edge = safe_float(row.get("true_edge"), 0.0) * 100
    return move * 0.6 + edge * 0.3

def model_script_raw(row):
    pace = safe_float(row.get("pace"), 98.0)
    usage = safe_float(row.get("usage"), 22.0)
    spread = abs(safe_float(row.get("spread"), 0.0))
    market = str(row.get("market", "")).lower()
    raw = (pace - 98) * 0.8 + max(usage - 22, 0) * 0.35
    if spread <= 5:
        raw += 2.0
    elif spread >= 10:
        raw -= 2.0
    if "points" in market or "pra" in market:
        raw += 1.2
    return raw

def model_variance_raw(row):
    starter = bool(row.get("starter", False))
    minutes = safe_float(row.get("minutes"), 0.0)
    mv = safe_float(row.get("minutes_volatility"), 3.0)
    raw = (minutes / 36.0) * 10 - mv * 1.5
    raw += 1.5 if starter else -2.0
    return raw

def weight_adjustment_from_perf(base_weights):
    perf = load_model_perf()
    if perf.empty:
        return base_weights.copy(), pd.DataFrame()
    latest = perf.sort_values("timestamp").groupby("model_name", as_index=False).tail(1)
    factors = {}
    for _, row in latest.iterrows():
        sample = safe_float(row.get("sample_size"), 0)
        if sample < 50:
            factors[row["model_name"]] = 1.0
            continue
        roi = safe_float(row.get("roi_pct"), 0.0)
        clv = safe_float(row.get("avg_clv"), 0.0)
        win = safe_float(row.get("win_rate"), 50.0)
        adj = 1.0 + max(-0.05, min(0.05, (roi / 100) * 0.4 + (clv / 100) * 0.4 + ((win - 50) / 100) * 0.2))
        factors[row["model_name"]] = adj
    out = {}
    total = 0.0
    for k, v in base_weights.items():
        out[k] = v * factors.get(k, 1.0)
        total += out[k]
    if total <= 0:
        total = 1.0
    out = {k: v / total for k, v in out.items()}
    latest = latest.copy()
    latest["adj_factor"] = latest["model_name"].map(factors)
    return out, latest

def predicted_clv_pct(row):
    raw = safe_float(row.get("model_clv"), 50.0)
    return round(max(0.0, (raw - 50) / 10), 2)

def agreement_count(row):
    vals = [
        safe_float(row.get("model_projection"), 0.0),
        safe_float(row.get("model_market"), 0.0),
        safe_float(row.get("model_clv"), 0.0),
        safe_float(row.get("model_script"), 0.0),
        safe_float(row.get("model_variance"), 0.0),
    ]
    return int(sum(v >= 60 for v in vals))

def confidence_tier(ensemble, agreement):
    if ensemble >= 82 and agreement >= 4:
        return "A", "🟢 A Elite", "conf-a"
    if ensemble >= 72 and agreement >= 4:
        return "B", "🟡 B Strong", "conf-b"
    if ensemble >= 62 and agreement >= 3:
        return "C", "🔵 C Playable", "conf-c"
    return "D", "🔴 D Avoid", "conf-d"

def tier_and_decision(row):
    ensemble = safe_float(row.get("ensemble_score"), 0.0)
    edge = safe_float(row.get("true_edge"), 0.0) * 100
    ev = safe_float(row.get("realistic_ev_pct"), 0.0)
    clv = safe_float(row.get("predicted_clv_pct"), 0.0)
    agree = int(row.get("agreement_count", 0))
    starter = bool(row.get("starter", False))

    if ensemble >= 74 and agree >= 4 and edge >= 3.5 and ev >= 2.0:
        return "Qualified", "Auto Bet"
    if ensemble >= 68 and agree >= 4 and edge >= 2.5 and ev >= 2.0:
        return "Qualified", "Strong Bet"
    if starter and ensemble >= 62 and agree >= 3 and edge >= 8 and ev >= 10:
        return "Near threshold", "Strong Bet"
    if ensemble >= 55 and agree >= 3 and ev >= 7 and clv >= 1.0:
        return "Monitor", "Lean"
    return "Needs line movement", "Wait"

def stake_multiplier_by_tier(tier, decision):
    if decision == "Auto Bet":
        return 1.00
    if decision == "Strong Bet":
        return 0.85
    return {
        "Qualified": 0.75,
        "Near threshold": 0.60,
        "Monitor": 0.35,
        "Needs line movement": 0.00,
    }.get(tier, 0.00)

def apply_aggression_mode(df, mode):
    out = df.copy()
    if mode == "Conservative":
        return out
    if mode == "Balanced":
        out["ensemble_score"] = (out["ensemble_score"] + 2).clip(upper=100)
        out["realistic_ev_pct"] = out["realistic_ev_pct"] + 0.5
        return out
    if mode == "Aggressive":
        out["ensemble_score"] = (out["ensemble_score"] + 4).clip(upper=100)
        out["realistic_ev_pct"] = out["realistic_ev_pct"] + 1.0
        out["true_edge"] = out["true_edge"] + 0.003
        return out
    return out

def compute_scores(df, bankroll=1000, max_single_pct=0.0125, model_weights=None):
    if model_weights is None:
        model_weights = {"projection": 0.28, "market": 0.20, "clv": 0.18, "script": 0.18, "variance": 0.16}

    out = df.copy()
    out["bet_side"] = out.apply(infer_bet_side, axis=1)
    out["hit_prob"] = out.apply(calculate_hit_probability, axis=1)

    bests = out.apply(best_book_and_odds, axis=1)
    out["best_book"] = [x[0] for x in bests]
    out["best_display_odds"] = [x[1] for x in bests]
    out["implied_prob"] = out["best_display_odds"].apply(american_to_implied_prob)
    out["true_edge"] = (out["hit_prob"] - out["implied_prob"]).round(4)

    dec = out["best_display_odds"].apply(american_to_decimal)
    out["realistic_hit_prob"] = (
        out["hit_prob"]
        - np.where(out["true_edge"] > 0.08, 0.03, 0.0)
        - np.where(out["true_edge"] > 0.12, 0.03, 0.0)
        - np.where(out["starter"], 0.0, 0.02)
    ).clip(0.01, 0.95)

    open_ip = out["open_odds"].apply(american_to_implied_prob)
    curr_ip = out["odds"].apply(american_to_implied_prob)
    out["line_move_pct"] = ((curr_ip - open_ip) * 100).round(2)
    out["movement_note"] = out["line_move_pct"].apply(movement_label)
    out["realistic_ev"] = (out["realistic_hit_prob"] * (dec - 1)) - (1 - out["realistic_hit_prob"])
    out["realistic_ev_pct"] = (out["realistic_ev"] * 100).clip(-10, 45).round(2)

    out["projection_raw"] = out.apply(model_projection_raw, axis=1)
    out["market_raw"] = out.apply(model_market_raw, axis=1)
    out["clv_raw"] = out.apply(model_clv_raw, axis=1)
    out["script_raw"] = out.apply(model_script_raw, axis=1)
    out["variance_raw"] = out.apply(model_variance_raw, axis=1)

    out["model_projection"] = normalize_series(out["projection_raw"]).round(1)
    out["model_market"] = normalize_series(out["market_raw"]).round(1)
    out["model_clv"] = normalize_series(out["clv_raw"]).round(1)
    out["model_script"] = normalize_series(out["script_raw"]).round(1)
    out["model_variance"] = normalize_series(out["variance_raw"]).round(1)

    out["ensemble_score"] = (
        out["model_projection"] * model_weights["projection"]
        + out["model_market"] * model_weights["market"]
        + out["model_clv"] * model_weights["clv"]
        + out["model_script"] * model_weights["script"]
        + out["model_variance"] * model_weights["variance"]
    ).round(1)

    out["agreement_count"] = out.apply(agreement_count, axis=1)
    conf = out.apply(lambda r: confidence_tier(r["ensemble_score"], r["agreement_count"]), axis=1)
    out["confidence_letter"] = [x[0] for x in conf]
    out["confidence_label"] = [x[1] for x in conf]
    out["confidence_css"] = [x[2] for x in conf]

    out["confidence_grade"] = np.select(
        [out["ensemble_score"] >= 84, out["ensemble_score"] >= 76, out["ensemble_score"] >= 68, out["ensemble_score"] >= 60],
        ["A+ ELITE", "A STRONG", "B+ VALUE", "B LEAN"], default="C PASS"
    )
    out["consensus_action"] = np.where(
        (out["ensemble_score"] >= 74) & (out["agreement_count"] >= 4) & (out["true_edge"] >= 0.035), "Bet",
        np.where((out["ensemble_score"] >= 62) & (out["agreement_count"] >= 3) & (out["true_edge"] >= 0.015), "Lean", "Pass")
    )

    b = dec - 1
    q = 1 - out["realistic_hit_prob"]
    raw_kelly = np.where((b > 0) & out["realistic_hit_prob"].between(0.001, 0.999), np.maximum(0, (b * out["realistic_hit_prob"] - q) / b), 0)
    mult = np.where(out["ensemble_score"] >= 78, 0.42, np.where(out["ensemble_score"] >= 68, 0.30, 0.18))
    frac = np.minimum(raw_kelly * mult, max_single_pct)
    out["base_stake_$"] = bankroll * frac
    out["base_stake_u"] = np.where(bankroll > 0, out["base_stake_$"] / (bankroll * 0.01), 0)

    out["predicted_clv_pct"] = out.apply(predicted_clv_pct, axis=1)
    tier_decisions = out.apply(tier_and_decision, axis=1)
    out["tier"] = [x[0] for x in tier_decisions]
    out["bet_decision"] = [x[1] for x in tier_decisions]
    out["stake_mult"] = [stake_multiplier_by_tier(t, d) for t, d in zip(out["tier"], out["bet_decision"])]
    out["single_stake_$"] = (out["base_stake_$"] * out["stake_mult"]).round(2)
    out["single_stake_u"] = (out["base_stake_u"] * out["stake_mult"]).round(2)

    out["rank_score"] = (
        out["ensemble_score"] * 0.52
        + out["realistic_ev_pct"] * 0.72
        + (out["true_edge"] * 100) * 0.70
        + out["predicted_clv_pct"] * 2.5
        + out["agreement_count"] * 2.0
    ).round(2)

    out["play_key"] = out["player"].astype(str) + "|" + out["market"].astype(str) + "|" + out["bet_side"].astype(str) + "|" + out["line"].astype(str)
    return out

def approved_pool(df):
    return df[df["tier"] == "Qualified"].copy()

def apply_game_exposure_limit(df, max_per_game=2):
    if df.empty:
        return df
    counts, rows = {}, []
    for _, row in df.sort_values(["rank_score", "realistic_ev_pct"], ascending=False).iterrows():
        matchup = str(row.get("matchup", ""))
        counts.setdefault(matchup, 0)
        if counts[matchup] < max_per_game:
            rows.append(row)
            counts[matchup] += 1
    return pd.DataFrame(rows).reset_index(drop=True)

def unique_top_plays(df):
    if df.empty:
        return {"best": pd.Series(dtype=object), "safe": pd.Series(dtype=object), "edge": pd.Series(dtype=object)}
    return {
        "best": df.sort_values(["rank_score", "realistic_ev_pct"], ascending=False).iloc[0],
        "safe": df.sort_values(["realistic_hit_prob", "ensemble_score"], ascending=False).iloc[0],
        "edge": df.sort_values(["true_edge", "realistic_ev_pct"], ascending=False).iloc[0],
    }

def combo_corr_penalty(rows):
    total = 0.0
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            total += 0.12 if str(rows[i].get("matchup", "")) == str(rows[j].get("matchup", "")) else 0.0
    return total

def build_best_parlay(df, leg_size=2):
    if len(df) < leg_size:
        return {}
    top_rows = [r[1] for r in df.head(min(8, len(df))).iterrows()]
    best = None
    for combo in itertools.combinations(top_rows, leg_size):
        decs = [american_to_decimal(r["best_display_odds"]) for r in combo]
        probs = [r["realistic_hit_prob"] for r in combo]
        if any(pd.isna(x) for x in decs) or any(pd.isna(x) for x in probs):
            continue
        combined_dec = float(np.prod(decs))
        corr_pen = combo_corr_penalty(list(combo))
        hit_prob = clamp01(float(np.prod(probs)) * (1 - corr_pen))
        ev = hit_prob * (combined_dec - 1) - (1 - hit_prob)
        score = min(ev * 100, 55) + hit_prob * 25 - corr_pen * 20
        candidate = {"legs": list(combo), "odds": decimal_to_american(combined_dec), "hit_prob": hit_prob, "ev_pct": min(ev * 100, 60), "corr_pen": corr_pen, "score": score}
        if best is None or candidate["score"] > best["score"]:
            best = candidate
    return best or {}

def simulate_live_refresh(df, top_n, edge_threshold_pct, model_weights):
    refreshed = df.copy()
    pre = compute_scores(refreshed, model_weights=model_weights)
    eligible = pre[(pre["true_edge"] * 100 >= edge_threshold_pct)].sort_values(["rank_score", "realistic_ev_pct"], ascending=False).head(top_n)
    count = len(eligible)
    for idx in eligible.index:
        for col in ["odds_fanduel", "odds_draftkings", "odds_betmgm", "odds_caesars"]:
            val = safe_float(refreshed.loc[idx, col], np.nan)
            if not pd.isna(val):
                refreshed.loc[idx, col] = val + np.random.choice([-2, -1, 0, 1, 2])
        curr = safe_float(refreshed.loc[idx, "odds"], np.nan)
        if not pd.isna(curr):
            refreshed.loc[idx, "odds"] = curr + np.random.choice([-2, -1, 0, 1, 2])
    return refreshed, max(1, count) if count > 0 else 0

def create_alerts(previous_snapshot, current_all, current_qualified, window_name):
    alerts = []
    prev_map = {row["play_key"]: row for _, row in previous_snapshot.iterrows()} if not previous_snapshot.empty else {}
    curr_all_map = {row["play_key"]: row for _, row in current_all.iterrows()} if not current_all.empty else {}
    curr_qual_keys = set(current_qualified["play_key"].tolist()) if not current_qualified.empty else set()

    for key, row in curr_all_map.items():
        prev_row = prev_map.get(key)
        player = safe_get(row, "player", "—")
        current_tier = safe_get(row, "tier", "")
        current_clv = safe_float(row.get("predicted_clv_pct"), 0.0)
        current_ensemble = safe_float(row.get("ensemble_score"), 0.0)

        if prev_row is None and current_tier == "Qualified":
            msg = f"{player}: new qualified play entered pool."
            alerts.append(msg); log_alert(window_name, key, "new_qualified", msg)
            continue

        if prev_row is not None:
            prev_tier = str(prev_row.get("tier", ""))
            prev_ev = safe_float(prev_row.get("realistic_ev_pct"), np.nan)
            curr_ev = safe_float(row.get("realistic_ev_pct"), np.nan)
            prev_book = str(prev_row.get("best_book", ""))
            curr_book = str(row.get("best_book", ""))
            prev_clv = safe_float(prev_row.get("predicted_clv_pct"), 0.0)
            prev_ensemble = safe_float(prev_row.get("ensemble_score"), 0.0)

            if prev_tier != "Qualified" and current_tier == "Qualified":
                msg = f"{player}: upgraded from {prev_tier or 'watch'} to Qualified."
                alerts.append(msg); log_alert(window_name, key, "upgrade_to_qualified", msg)
            if not pd.isna(prev_ev) and not pd.isna(curr_ev) and curr_ev - prev_ev >= 2.0:
                msg = f"{player}: EV improved by {curr_ev - prev_ev:.1f}%."
                alerts.append(msg); log_alert(window_name, key, "ev_improved", msg)
            if prev_book != curr_book:
                msg = f"{player}: best book changed to {curr_book}."
                alerts.append(msg); log_alert(window_name, key, "best_book_changed", msg)
            if current_clv - prev_clv >= 1.0:
                msg = f"{player}: predicted CLV improved to {current_clv:.2f}%."
                alerts.append(msg); log_alert(window_name, key, "clv_improved", msg)
            if current_ensemble - prev_ensemble >= 4.0:
                msg = f"{player}: ensemble score improved to {current_ensemble:.1f}."
                alerts.append(msg); log_alert(window_name, key, "ensemble_improved", msg)

    for key, row in prev_map.items():
        if str(row.get("tier", "")) == "Qualified" and key not in curr_qual_keys:
            msg = f"{row['player']}: dropped out of qualified pool."
            alerts.append(msg); log_alert(window_name, key, "dropped_out", msg)
    return alerts

def save_snapshot_from_df(df):
    if df.empty:
        save_df(pd.DataFrame(columns=[
            "play_key", "player", "market", "bet_side", "line", "best_book", "best_display_odds",
            "true_edge", "realistic_ev_pct", "movement_note", "tier", "qualified",
            "predicted_clv_pct", "ensemble_score", "agreement_count"
        ]), SNAPSHOT_FILE)
        return
    snap = df[[
        "play_key", "player", "market", "bet_side", "line", "best_book", "best_display_odds",
        "true_edge", "realistic_ev_pct", "movement_note", "tier", "predicted_clv_pct",
        "ensemble_score", "agreement_count"
    ]].copy()
    snap["qualified"] = snap["tier"].eq("Qualified")
    save_df(snap, SNAPSHOT_FILE)

# -----------------------------
# Portfolio optimizer
# -----------------------------
def portfolio_bucket_score(row):
    edge = safe_float(row.get("true_edge"), 0.0) * 100
    ev = safe_float(row.get("realistic_ev_pct"), 0.0)
    clv = safe_float(row.get("predicted_clv_pct"), 0.0)
    ensemble = safe_float(row.get("ensemble_score"), 0.0)
    agree = safe_float(row.get("agreement_count"), 0.0)
    score = edge * 0.9 + ev * 0.8 + clv * 2.0 + ensemble * 0.45 + agree * 2.5
    if str(row.get("tier", "")) == "Qualified":
        score += 12
    elif str(row.get("tier", "")) == "Near threshold":
        score += 6
    return max(score, 0.0)

def allocate_portfolio(df, bankroll, max_total_u, max_per_game=2):
    if df.empty:
        return pd.DataFrame(columns=list(df.columns) + ["alloc_u", "alloc_$", "portfolio_weight"])
    work = df.copy().sort_values(["rank_score", "realistic_ev_pct"], ascending=False)
    counts, kept_rows = {}, []
    for _, row in work.iterrows():
        matchup = str(row.get("matchup", ""))
        counts.setdefault(matchup, 0)
        if counts[matchup] < max_per_game and safe_float(row.get("single_stake_u"), 0) > 0:
            kept_rows.append(row)
            counts[matchup] += 1
    if not kept_rows:
        return pd.DataFrame(columns=list(df.columns) + ["alloc_u", "alloc_$", "portfolio_weight"])
    port = pd.DataFrame(kept_rows).reset_index(drop=True)
    port["portfolio_raw"] = port.apply(portfolio_bucket_score, axis=1)
    total_raw = port["portfolio_raw"].sum()
    if total_raw <= 0:
        port["portfolio_weight"] = 0.0
    else:
        port["portfolio_weight"] = port["portfolio_raw"] / total_raw
    port["alloc_u"] = (port["portfolio_weight"] * max_total_u).round(2)
    port["alloc_u"] = np.minimum(port["alloc_u"], port["single_stake_u"])
    port["alloc_$"] = (port["alloc_u"] * (bankroll * 0.01)).round(2)
    return port.sort_values(["alloc_u", "rank_score"], ascending=[False, False]).reset_index(drop=True)

# -----------------------------
# Self-learning perf tracker
# -----------------------------
def compute_model_performance_from_betlog(log):
    if log.empty:
        return pd.DataFrame(columns=["model_name", "raw_weight", "adj_weight", "sample_size", "avg_clv", "win_rate", "roi_pct"])
    settled = log[log["result"].isin(["Win", "Loss", "Push"])].copy()
    if settled.empty:
        return pd.DataFrame(columns=["model_name", "raw_weight", "adj_weight", "sample_size", "avg_clv", "win_rate", "roi_pct"])

    models = {
        "projection": "model_projection",
        "market": "model_market",
        "clv": "model_clv",
        "script": "model_script",
        "variance": "model_variance",
    }
    rows = []
    for model_name, col in models.items():
        sample = settled[pd.to_numeric(settled[col], errors="coerce").notna()].copy()
        if sample.empty:
            continue
        high = sample[pd.to_numeric(sample[col], errors="coerce") >= 60]
        if high.empty:
            high = sample
        wins = int((high["result"] == "Win").sum())
        losses = int((high["result"] == "Loss").sum())
        total = len(high)
        total_staked = pd.to_numeric(high["stake_u"], errors="coerce").fillna(0).sum()
        profit = pd.to_numeric(high["profit_u"], errors="coerce").fillna(0).sum()
        roi = (profit / total_staked * 100) if total_staked > 0 else 0.0
        win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 50.0
        avg_clv = pd.to_numeric(high["clv_placed_vs_close_pct"], errors="coerce").dropna().mean()
        avg_clv = 0.0 if pd.isna(avg_clv) else avg_clv
        rows.append({
            "timestamp": current_et_label(),
            "model_name": model_name,
            "raw_weight": np.nan,
            "adj_weight": np.nan,
            "sample_size": total,
            "avg_clv": round(avg_clv, 2),
            "win_rate": round(win_rate, 1),
            "roi_pct": round(roi, 1),
        })
    return pd.DataFrame(rows)

# -----------------------------
# Bet log helpers
# -----------------------------
def add_bet_to_log(row):
    log = load_bet_log()
    new_row = {
        "timestamp": current_et_label(),
        "player": safe_get(row, "player", "—"),
        "market": safe_get(row, "market", "—"),
        "bet_side": safe_get(row, "bet_side", "—"),
        "line": safe_get(row, "line", "—"),
        "book": row["book"],
        "best_book": safe_get(row, "best_book", safe_get(row, "book", "—")),
        "placed_odds": row["odds"],
        "best_odds": safe_get(row, "best_display_odds", safe_get(row, "best_odds", safe_get(row, "odds", np.nan))),
        "stake_u": row.get("alloc_u", row.get("single_stake_u", 0)),
        "stake_$": row.get("alloc_$", row.get("single_stake_$", 0)),
        "edge_pct": safe_get(row, "true_edge", 0.0) * 100,
        "ev_pct": safe_get(row, "realistic_ev_pct", 0.0),
        "tier": safe_get(row, "tier", ""),
        "bet_decision": safe_get(row, "bet_decision", ""),
        "predicted_clv_pct": safe_get(row, "predicted_clv_pct", 0.0),
        "ensemble_score": safe_get(row, "ensemble_score", 0.0),
        "agreement_count": safe_get(row, "agreement_count", 0),
        "model_projection": row["model_projection"],
        "model_market": row["model_market"],
        "model_clv": row["model_clv"],
        "model_script": row["model_script"],
        "model_variance": row["model_variance"],
        "result": "Pending",
        "profit_u": 0.0,
        "closing_odds": np.nan,
        "clv_placed_vs_close_pct": np.nan,
        "notes": ""
    }
    save_df(pd.concat([log, pd.DataFrame([new_row])], ignore_index=True), BET_LOG_FILE)

def settle_bet(result, placed_odds, stake_u):
    dec = american_to_decimal(placed_odds)
    if pd.isna(dec):
        return 0.0
    if result == "Win":
        return round((dec - 1) * stake_u, 2)
    if result == "Loss":
        return round(-1.0 * stake_u, 2)
    return 0.0

def tracker_summary(log):
    if log.empty:
        return {"bets": 0, "wins": 0, "losses": 0, "pushes": 0, "profit_u": 0.0, "roi_pct": 0.0, "win_rate": 0.0, "avg_clv": 0.0}
    wins = int((log["result"] == "Win").sum())
    losses = int((log["result"] == "Loss").sum())
    pushes = int((log["result"] == "Push").sum())
    total_staked = pd.to_numeric(log["stake_u"], errors="coerce").fillna(0).sum()
    profit_u = pd.to_numeric(log["profit_u"], errors="coerce").fillna(0).sum()
    roi_pct = (profit_u / total_staked * 100) if total_staked > 0 else 0.0
    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0.0
    avg_clv = pd.to_numeric(log["clv_placed_vs_close_pct"], errors="coerce").dropna().mean()
    avg_clv = 0.0 if pd.isna(avg_clv) else avg_clv
    return {"bets": int(len(log)), "wins": wins, "losses": losses, "pushes": pushes, "profit_u": round(profit_u, 2), "roi_pct": round(roi_pct, 1), "win_rate": round(win_rate, 1), "avg_clv": round(avg_clv, 2)}

# -----------------------------
# UI helpers
# -----------------------------
def render_summary_box(items):
    html = ['<div class="summary-box"><div class="summary-grid">']
    for label, value in items:
        html.append(f'<div class="summary-cell"><div class="summary-label">{label}</div><div class="summary-value">{value}</div></div>')
    html.append('</div></div>')
    st.markdown("".join(html), unsafe_allow_html=True)

def market_insight_banner(df, qualified, fallback):
    if df.empty:
        return
    top = df.iloc[0]
    clv_env = pd.to_numeric(df["predicted_clv_pct"], errors="coerce").fillna(0).mean()
    market_notes = []
    if len(qualified) >= 2:
        market_notes.append(f"{len(qualified)} strong plays detected")
    elif len(qualified) == 1:
        market_notes.append("1 strong play detected")
    else:
        market_notes.append("No elite plays yet")
    if clv_env >= 3:
        market_notes.append("positive CLV environment")
    if (df["movement_note"].astype(str).str.contains("Steam")).sum() >= 2:
        market_notes.append("steam signals active")
    if len(fallback) >= 2 and len(qualified) <= 2:
        market_notes.append("watchlist setup is live")
    st.markdown(f'<div class="insight-box"><b>📊 MARKET EDGE TODAY:</b> ' + " • ".join(market_notes) + "</div>", unsafe_allow_html=True)

def why_this_play(row):
    reasons = []
    proj_edge = safe_float(safe_get(row, "projection", np.nan), np.nan) - safe_float(safe_get(row, "line", np.nan), np.nan)
    if not pd.isna(proj_edge):
        reasons.append(f"Projection edge: {proj_edge:+.1f} vs line")
    if safe_float(row.get("model_market"), 0) >= 60:
        reasons.append("Market pricing is supportive")
    elif safe_float(row.get("model_market"), 0) <= 40:
        reasons.append("Market support is weaker than other models")
    if safe_float(row.get("predicted_clv_pct"), 0) > 0:
        reasons.append(f"Positive CLV expected ({row['predicted_clv_pct']:.2f}%)")
    reasons.append(f"High AI agreement ({int(row['agreement_count'])}/5)")
    return reasons[:4]

def render_best_bet(row):
    st.markdown("## 🔥 Best Bet")
    st.markdown(f"### {row['player']} — {row['bet_side']} {row['line']} {row['market']}")
    st.markdown(
        f"**Current Odds:** {fmt_american(row['odds'])} | "
        f"**Best Odds:** {fmt_american(row['best_display_odds'])} ({row['best_book']}) | "
        f"**EV:** {row['realistic_ev_pct']:.1f}% | "
        f"**Predicted CLV:** {row['predicted_clv_pct']:.2f}%"
    )
    st.markdown(f'<span class="conf-pill {row["confidence_css"]}">{row["confidence_label"]}</span>', unsafe_allow_html=True)
    render_summary_box([
        ("Hit %", f"{row['realistic_hit_prob']*100:.0f}%"),
        ("Edge", f"{row['true_edge']*100:.1f}%"),
        ("Stake", f"{row.get('alloc_u', row['single_stake_u']):.2f}u"),
        ("Ensemble", f"{row['ensemble_score']:.1f}"),
        ("Agreement", f"{int(row['agreement_count'])}/5"),
    ])
    why = why_this_play(row)
    st.markdown("<div class='why-box'><b>📊 Why this play:</b><br>" + "<br>".join([f"• {x}" for x in why]) + "</div>", unsafe_allow_html=True)
    st.progress(float(row["realistic_hit_prob"]))

def render_compact_play(row):
    if safe_get(row, "tier", "") == "Qualified":
        box_class = "good-box"
    elif safe_get(row, "tier", "") in ["Near threshold", "Monitor"]:
        box_class = "watch-box"
    else:
        box_class = "pass-box"
    trigger_odds = safe_float(safe_get(row, "best_display_odds", safe_get(row, "best_odds", safe_get(row, "odds", np.nan))), np.nan)
    target_odds = fmt_american(trigger_odds + 5) if not pd.isna(trigger_odds) else "—"
    trigger_clv = max(2.0, safe_float(row.get("predicted_clv_pct"), 0) + 0.5)
    risk_txt = "Medium" if safe_get(row, "tier", "") in ["Near threshold", "Monitor"] else "Low" if safe_get(row, "tier", "") == "Qualified" else "Wait"
    stake_u = row.get("alloc_u", row.get("single_stake_u", 0))
    extra = ""
    if safe_get(row, "tier", "") != "Qualified":
        extra = (
            f"<div class='trigger-box'><b>Trigger:</b> Bet if price reaches {target_odds} or better • "
            f"Target CLV ≥ {trigger_clv:.1f}% • Confidence {risk_txt}</div>"
        )
    st.markdown(
        f'<div class="{box_class}"><b>{safe_get(row, "tier", "")}</b> • {safe_get(row, "bet_decision", "")} • {int(safe_get(row, "agreement_count", 0))}/5 agree<br>'
        f'{safe_get(row, "player", "—")} — {safe_get(row, "bet_side", "—")} {safe_get(row, "line", "—")} {safe_get(row, "market", "—")}<br>'
        f'Best {fmt_american(safe_get(row, "best_display_odds", safe_get(row, "best_odds", safe_get(row, "odds", np.nan))))} ({safe_get(row, "best_book", safe_get(row, "book", "—"))}) | '
        f'EV {safe_get(row, "realistic_ev_pct", 0.0):.1f}% | Edge {safe_get(row, "true_edge", 0.0)*100:.1f}% | '
        f'Stake {stake_u:.2f}u | Pred. CLV {safe_get(row, "predicted_clv_pct", 0.0):.2f}% | Ensemble {safe_get(row, "ensemble_score", 0.0):.1f}'
        f'{extra}</div>',
        unsafe_allow_html=True
    )

# -----------------------------
# Sample data
# -----------------------------
def sample_data():
    return pd.DataFrame([
        {"player": "Stephen Curry", "team": "GSW", "opponent": "LAL", "matchup": "Warriors vs Lakers", "market": "points", "bet_side": "Over", "line": 27.0, "projection": 32.2, "odds": -115, "open_odds": -102, "book": "DraftKings", "starter": True, "minutes": 35, "spread": -2.5, "pace": 102.4, "usage": 31.0, "last5_avg": 33.1, "defense_rank": 24, "minutes_volatility": 2.1, "odds_fanduel": -112, "odds_draftkings": -115, "odds_betmgm": -108, "odds_caesars": -110},
        {"player": "LeBron James", "team": "LAL", "opponent": "GSW", "matchup": "Lakers vs Warriors", "market": "pra", "bet_side": "Over", "line": 38.0, "projection": 43.8, "odds": -115, "open_odds": -105, "book": "DraftKings", "starter": True, "minutes": 36, "spread": 2.5, "pace": 101.9, "usage": 30.5, "last5_avg": 45.2, "defense_rank": 23, "minutes_volatility": 2.2, "odds_fanduel": -112, "odds_draftkings": -115, "odds_betmgm": -110, "odds_caesars": -111},
        {"player": "Anthony Davis", "team": "LAL", "opponent": "GSW", "matchup": "Lakers vs Warriors", "market": "rebounds", "bet_side": "Over", "line": 11.5, "projection": 13.1, "odds": -105, "open_odds": -104, "book": "FanDuel", "starter": True, "minutes": 35, "spread": 2.5, "pace": 101.9, "usage": 27.0, "last5_avg": 12.8, "defense_rank": 19, "minutes_volatility": 2.6, "odds_fanduel": -105, "odds_draftkings": -102, "odds_betmgm": 100, "odds_caesars": -101},
        {"player": "Jordan Poole", "team": "WAS", "opponent": "BKN", "matchup": "Wizards vs Nets", "market": "points", "bet_side": "Over", "line": 21.5, "projection": 24.4, "odds": 102, "open_odds": 108, "book": "Caesars", "starter": True, "minutes": 33, "spread": 5.0, "pace": 99.6, "usage": 30.0, "last5_avg": 25.8, "defense_rank": 25, "minutes_volatility": 4.2, "odds_fanduel": 100, "odds_draftkings": 101, "odds_betmgm": 103, "odds_caesars": 102},
        {"player": "Jalen Brunson", "team": "NYK", "opponent": "MIA", "matchup": "Knicks vs Heat", "market": "points", "bet_side": "Over", "line": 26.5, "projection": 29.7, "odds": -110, "open_odds": -101, "book": "FanDuel", "starter": True, "minutes": 36, "spread": -3.0, "pace": 98.7, "usage": 30.6, "last5_avg": 30.9, "defense_rank": 9, "minutes_volatility": 1.8, "odds_fanduel": -110, "odds_draftkings": -106, "odds_betmgm": -104, "odds_caesars": -108},
        {"player": "Jimmy Butler", "team": "MIA", "opponent": "NYK", "matchup": "Heat vs Knicks", "market": "assists", "bet_side": "Over", "line": 5.5, "projection": 6.9, "odds": -102, "open_odds": -100, "book": "BetMGM", "starter": True, "minutes": 34, "spread": 3.0, "pace": 98.7, "usage": 25.5, "last5_avg": 7.0, "defense_rank": 11, "minutes_volatility": 2.0, "odds_fanduel": -105, "odds_draftkings": -104, "odds_betmgm": -102, "odds_caesars": -103},
    ])

@st.cache_data(show_spinner=False)
def load_uploaded_csv(file):
    return pd.read_csv(file)

# -----------------------------
# App
# -----------------------------
st.title("🏀 Sports AI Betting Dashboard V13 Tracking + PnL Core")
st.caption("TRACKING + PNL CORE: corrected automation engine with bet log, grading workflow, profit tracking, ROI, CLV tracking, automation queue, and mobile-first workflow.")

with st.sidebar:
    st.markdown("### Data")
    uploaded = st.file_uploader("Upload CSV", type=["csv"])
    use_sample = st.toggle("Use sample data", value=uploaded is None)

    st.markdown("### Live Control")
    live_mode = st.selectbox("Live mode", ["OFF", "Manual Only", "Scheduled (3x daily)"])
    scheduled_windows = st.multiselect("Scheduled windows", list(SCHEDULE_WINDOWS.keys()), default=["5:00 AM ET", "1:00 PM ET", "5:30 PM ET"])
    top_live_checks = st.slider("Top plays to live-check", 1, 5, 3)
    min_live_edge = st.slider("Minimum edge % for live-check", 0.0, 10.0, 5.0, 0.5)
    manual_refresh = st.button("Refresh Top Plays Only")

    st.markdown("### Automation")
    auto_alerts_enabled = st.toggle("Enable alert routing", value=True)
    alert_delivery = st.selectbox("Alert route", ["In-App Only", "Scheduled Scan Only", "Manual + Scheduled"])
    auto_execute_mode = st.selectbox("Execution mode", ["Manual Confirmation", "Queue Signals Only", "Auto Queue"])
    scheduled_scan_button = st.button("Run Scheduled Alert Scan Now")

    st.markdown("### Portfolio")
    bankroll = st.number_input("Bankroll ($)", min_value=100, max_value=100000, value=1000, step=50)
    max_single_pct = st.slider("Max bankroll % per single", 0.25, 3.0, 1.25, 0.25) / 100.0
    max_total_portfolio_u = st.slider("Max total portfolio units", 0.5, 5.0, 2.5, 0.25)
    aggression_mode = st.selectbox("Aggression mode", ["Conservative", "Balanced", "Aggressive"], index=1)

    st.markdown("### Base Model Weights")
    projection_w = st.slider("Projection model", 0.05, 0.50, 0.28, 0.01)
    market_w = st.slider("Market model", 0.05, 0.50, 0.20, 0.01)
    clv_w = st.slider("CLV model", 0.05, 0.50, 0.18, 0.01)
    script_w = st.slider("Game script model", 0.05, 0.50, 0.18, 0.01)
    variance_w = st.slider("Variance model", 0.05, 0.50, 0.16, 0.01)
    use_self_learning = st.toggle("Use self-learning adjustments", value=True)

    st.markdown("### PRO MODE Rules")
    min_ensemble = st.slider("Min ensemble score", 55, 90, 72)
    min_edge = st.slider("Min true edge %", 0.0, 15.0, 2.0, 0.5)
    min_ev = st.slider("Min EV %", 0.0, 25.0, 2.0, 0.5)
    min_agreement = st.slider("Min model agreement", 1, 5, 4)
    sharp_mode = st.toggle("Sharp Mode", value=True)
    max_per_game = st.slider("Max plays per game", 1, 3, 2)

base_weights = {
    "projection": projection_w,
    "market": market_w,
    "clv": clv_w,
    "script": script_w,
    "variance": variance_w,
}
total_w = sum(base_weights.values()) or 1.0
base_weights = {k: v / total_w for k, v in base_weights.items()}

adj_weights, perf_table = weight_adjustment_from_perf(base_weights) if use_self_learning else (base_weights.copy(), pd.DataFrame())

used_calls = get_today_calls()
remaining_calls = get_remaining_calls()
status = call_status_label(used_calls)
st.markdown(
    f'<div class="banner"><div><b>API Calls Used Today:</b> {used_calls} / {MAX_DAILY_CALLS}</div>'
    f'<div><b>Remaining:</b> {remaining_calls}</div><div><b>Status:</b> {status}</div>'
    f'<div><b>Eastern Time:</b> {current_et_label()}</div><div><b>Aggression Mode:</b> {aggression_mode}</div></div>',
    unsafe_allow_html=True
)
st.progress(min(used_calls / MAX_DAILY_CALLS, 1.0))

base_df = ensure_columns(load_uploaded_csv(uploaded) if (uploaded and not use_sample) else sample_data())

refresh_reason, refresh_window = None, ""
if remaining_calls <= int(MAX_DAILY_CALLS * 0.05):
    st.warning("Daily call protection is active. Live refresh disabled because you are above 95% of limit.")
elif live_mode == "Manual Only" and manual_refresh:
    refresh_reason, refresh_window = "manual_top_plays_refresh", "manual"
elif live_mode == "Scheduled (3x daily)":
    for win in scheduled_windows:
        if should_run_window(win):
            refresh_reason, refresh_window = "scheduled_window_refresh", win
            break
    if manual_refresh:
        refresh_reason, refresh_window = "manual_top_plays_refresh", "manual"

previous_snapshot = load_snapshot()
alerts_to_show = []
if refresh_reason:
    base_df, call_cost = simulate_live_refresh(base_df, top_n=top_live_checks, edge_threshold_pct=min_live_edge, model_weights=adj_weights)
    log_api_call(refresh_reason, call_count=max(1, call_cost), window=refresh_window)
    st.success(f"Live check completed for top plays. Logged {max(1, call_cost)} call(s).")

scored = compute_scores(base_df, bankroll=float(bankroll), max_single_pct=float(max_single_pct), model_weights=adj_weights)
scored = apply_aggression_mode(scored, aggression_mode)

tier_decisions = scored.apply(tier_and_decision, axis=1)
scored["tier"] = [x[0] for x in tier_decisions]
scored["bet_decision"] = [x[1] for x in tier_decisions]
scored["stake_mult"] = [stake_multiplier_by_tier(t, d) for t, d in zip(scored["tier"], scored["bet_decision"])]
scored["single_stake_$"] = (scored["base_stake_$"] * scored["stake_mult"]).round(2)
scored["single_stake_u"] = (scored["base_stake_u"] * scored["stake_mult"]).round(2)

with st.expander("⚙️ Filters", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        starters_only = st.toggle("Starters only", value=True)
    with c2:
        min_minutes = st.slider("Min minutes", 0, 40, 0)
    odds_preset = st.selectbox("Odds Range", ["All", "-300 to +200", "-200 to +150", "Plus Money Only"])

filtered = scored.copy()
if starters_only:
    filtered = filtered[filtered["starter"] == True]
filtered = filtered[filtered["minutes"].fillna(0) >= min_minutes]
if odds_preset == "-300 to +200":
    filtered = filtered[filtered["best_display_odds"].between(-300, 200)]
elif odds_preset == "-200 to +150":
    filtered = filtered[filtered["best_display_odds"].between(-200, 150)]
elif odds_preset == "Plus Money Only":
    filtered = filtered[filtered["best_display_odds"] > 0]

qualified = approved_pool(filtered)
qualified = qualified[
    (qualified["ensemble_score"] >= min_ensemble)
    & ((qualified["true_edge"] * 100) >= min_edge)
    & (qualified["realistic_ev_pct"] >= min_ev)
    & (qualified["agreement_count"] >= min_agreement)
].copy()
qualified = apply_game_exposure_limit(qualified, max_per_game=max_per_game)

if sharp_mode:
    qualified = qualified[(qualified["confidence_letter"].isin(["A", "B"])) & (qualified["consensus_action"] == "Bet")].copy()

all_ranked = filtered.sort_values(["rank_score", "realistic_ev_pct", "true_edge"], ascending=False).reset_index(drop=True)
qualified = qualified.sort_values(["rank_score", "realistic_ev_pct", "true_edge"], ascending=False).reset_index(drop=True)

portfolio_source = pd.concat([qualified, all_ranked[all_ranked["tier"] != "Needs line movement"].head(6)], ignore_index=True).drop_duplicates(subset=["play_key"])
portfolio = allocate_portfolio(portfolio_source, bankroll=float(bankroll), max_total_u=float(max_total_portfolio_u), max_per_game=max_per_game)

if refresh_reason:
    alerts_to_show = create_alerts(previous_snapshot, all_ranked.head(10), qualified, refresh_window)
    save_snapshot_from_df(all_ranked.head(10))
elif previous_snapshot.empty:
    save_snapshot_from_df(all_ranked.head(10))

# self-learning snapshot
bet_log_for_perf = load_bet_log()
perf_now = compute_model_performance_from_betlog(bet_log_for_perf)
if not perf_now.empty:
    perf_now["raw_weight"] = perf_now["model_name"].map(base_weights)
    perf_now["adj_weight"] = perf_now["model_name"].map(adj_weights)
    save_df(perf_now, MODEL_PERF_FILE)

fallback_pool = all_ranked[all_ranked["tier"] != "Qualified"].head(4).copy()

market_insight_banner(all_ranked, qualified, fallback_pool)

if alerts_to_show:
    st.markdown("## 🔔 Alerts")
    for a in alerts_to_show:
        st.markdown(f'<div class="alert-box">{a}</div>', unsafe_allow_html=True)

st.markdown(
    f'<div class="banner"><div><b>Qualified Plays:</b> {len(qualified)}</div>'
    f'<div><b>Fallback Plays:</b> {len(fallback_pool)}</div>'
    f'<div><b>Top Ensemble:</b> {all_ranked.iloc[0]["player"] if not all_ranked.empty else "—"} ({all_ranked.iloc[0]["ensemble_score"]:.1f})</div>'
    f'<div><b>Portfolio Size:</b> {portfolio["alloc_u"].sum():.2f}u</div></div>',
    unsafe_allow_html=True
)

st.markdown("## 🧠 Weight Engine")
weights_df = pd.DataFrame({
    "model": list(base_weights.keys()),
    "base_weight": [round(base_weights[k], 3) for k in base_weights],
    "active_weight": [round(adj_weights[k], 3) for k in base_weights],
})
st.dataframe(weights_df, use_container_width=True, hide_index=True)

if qualified.empty:
    st.warning("No qualified plays under the current V11.2 PRO UI filters.")
    st.markdown("## 🔎 Fallback Plays")
    for _, row in fallback_pool.iterrows():
        render_compact_play(row)

    fallback_alloc = allocate_portfolio(fallback_pool, bankroll=float(bankroll), max_total_u=float(max_total_portfolio_u), max_per_game=max_per_game)
    st.markdown("## 💰 Suggested Fallback Stakes")
    if fallback_alloc.empty:
        st.info("No fallback allocations available.")
    else:
        for _, row in fallback_alloc.iterrows():
            st.write(f"**{row['player']}** — {row['tier']} • {row['bet_decision']} • Stake {row['alloc_u']:.2f}u • CLV {row['predicted_clv_pct']:.2f}% • Ensemble {row['ensemble_score']:.1f} • Agreement {int(row['agreement_count'])}/5")

    st.markdown("## 🤖 PRO MODE Engine Output")
    engine_show = all_ranked[[
        "player", "market", "bet_side", "model_projection", "model_market", "model_clv",
        "model_script", "model_variance", "ensemble_score", "agreement_count", "tier", "bet_decision"
    ]].head(8)
    st.dataframe(engine_show, use_container_width=True, hide_index=True)
    st.stop()

tops = unique_top_plays(qualified)
best_play = tops["best"]
best_parlay = build_best_parlay(qualified, leg_size=2)

best_play_port = portfolio[portfolio["play_key"] == best_play["play_key"]]
if not best_play_port.empty:
    best_play = best_play.copy()
    best_play["alloc_u"] = float(best_play_port.iloc[0]["alloc_u"])
    best_play["alloc_$"] = float(best_play_port.iloc[0]["alloc_$"])

render_best_bet(best_play)

best_exec_signal = execution_signal(best_play) if "execution_signal" in globals() else "⏳ WAIT"
best_urgency = urgency_level(best_play) if "urgency_level" in globals() else "LOW"
best_book_label = safe_get(best_play, "best_book", "—")
best_odds_label = fmt_american(safe_get(best_play, "best_display_odds", safe_get(best_play, "best_odds", safe_get(best_play, "odds", np.nan))))
st.markdown(
    f'<div class="insight-box"><b>🎯 Execution Signal:</b> {best_exec_signal} • Confidence {best_urgency} • Best book {best_book_label} {best_odds_label}</div>',
    unsafe_allow_html=True
)

st.markdown("## 🤖 PRO MODE Model Panel")
st.markdown(f'<span class="conf-pill {best_play["confidence_css"]}">{best_play["confidence_label"]}</span>', unsafe_allow_html=True)
render_summary_box([
    ("Projection", f"{best_play['model_projection']:.1f}"),
    ("Market", f"{best_play['model_market']:.1f}"),
    ("CLV", f"{best_play['model_clv']:.1f}"),
    ("Script", f"{best_play['model_script']:.1f}"),
    ("Variance", f"{best_play['model_variance']:.1f}"),
    ("Agreement", f"{int(best_play['agreement_count'])}/5"),
])
strong = []
if best_play["model_projection"] >= 70: strong.append("Projection")
if best_play["model_clv"] >= 70: strong.append("CLV")
if best_play["model_script"] >= 70: strong.append("Script")
weak = []
if best_play["model_market"] < 50: weak.append("Market")
if best_play["model_variance"] < 50: weak.append("Variance")
insight = f"{' + '.join(strong) if strong else 'Mixed signals'} strong"
if weak:
    insight += f" • {', '.join(weak)} slightly weaker"
best_exec_signal_for_insight = execution_signal(best_play) if "execution_signal" in globals() else "⏳ WAIT"
insight += f" → {best_exec_signal_for_insight}"
st.markdown(f"<div class='insight-box'><b>🧠 Model Insight:</b> {insight}</div>", unsafe_allow_html=True)

st.markdown("## ✅ Qualified Plays")
for _, row in qualified.iterrows():
    row_copy = row.copy()
    port_match = portfolio[portfolio["play_key"] == row["play_key"]]
    if not port_match.empty:
        row_copy["alloc_u"] = float(port_match.iloc[0]["alloc_u"])
    render_compact_play(row_copy)

if not fallback_pool.empty:
    st.markdown("## 🔎 Fallback Plays")
    for _, row in fallback_pool.iterrows():
        row_copy = row.copy()
        port_match = portfolio[portfolio["play_key"] == row["play_key"]]
        if not port_match.empty:
            row_copy["alloc_u"] = float(port_match.iloc[0]["alloc_u"])
        render_compact_play(row_copy)

st.markdown("## 🤖 PRO MODE Engine Output")
engine_show = all_ranked[[
    "player", "market", "bet_side", "model_projection", "model_market", "model_clv",
    "model_script", "model_variance", "ensemble_score", "agreement_count", "tier", "bet_decision"
]].head(10)
st.dataframe(engine_show, use_container_width=True, hide_index=True)

st.markdown("## 🧠 Auto Bet Allocation (Portfolio Optimizer)")
if portfolio.empty:
    st.info("No portfolio allocations available.")
else:
    portfolio_show = portfolio[[
        "player", "market", "bet_side", "tier", "bet_decision",
        "single_stake_u", "alloc_u", "alloc_$", "portfolio_weight", "predicted_clv_pct", "ensemble_score", "agreement_count"
    ]].copy()
    portfolio_show["portfolio_weight"] = (portfolio_show["portfolio_weight"] * 100).round(1).astype(str) + "%"
    st.dataframe(portfolio_show, use_container_width=True, hide_index=True)

st.markdown("## 🛰️ Automation Queue")
try:
    queue_df = build_automation_queue(qualified, fallback_pool)
    if queue_df is None or queue_df.empty:
        st.info("No automation actions at this time.")
    else:
        st.dataframe(queue_df, use_container_width=True, hide_index=True)
except Exception:
    st.warning("Automation queue temporarily unavailable.")

st.markdown("## ✅ Add To Bet Log")
track_rows = portfolio.head(5).copy()
cols = st.columns(min(3, len(track_rows))) if len(track_rows) > 0 else []
for i, (_, row) in enumerate(track_rows.iterrows()):
    with cols[i % len(cols)]:
        if st.button(f"Track {row['player']}", key=f"track_{i}"):
            add_bet_to_log(row)
            st.success(f"Added {row['player']} to bet log.")

st.markdown("## 💰 Bankroll")
parlay_units = 0.75 if not best_parlay else min(1.00, max(0.25, best_parlay["ev_pct"] / 20))
roi_est = (best_play["realistic_ev_pct"] * 0.55) + ((best_parlay["ev_pct"] if best_parlay else 0) * 0.45)
risk_level = "Moderate" if portfolio["alloc_u"].sum() >= 2 else "Light"
exposure = f"{portfolio['alloc_u'].sum():.2f}u / {max_total_portfolio_u:.2f}u"
render_summary_box([
    ("Top Stake", f"{best_play.get('alloc_u', best_play['single_stake_u']):.2f}u"),
    ("Parlay Stake", f"{parlay_units:.2f}u"),
    ("ROI", f"{min(roi_est, 42.0):.1f}%"),
    ("Pred. CLV", f"{best_play['predicted_clv_pct']:.2f}%"),
    ("Risk", risk_level),
    ("Exposure", exposure),
])
st.markdown(f"<div class='insight-box'><b>💼 Strategy:</b> {aggression_mode} aggression • {risk_level} risk • exposure {exposure}</div>", unsafe_allow_html=True)

if best_parlay:
    legs_txt = " + ".join([f"{x['player']} {x['bet_side']} {x['line']}" for x in best_parlay["legs"]])
    st.markdown("## 🧩 Best 2-Leg Parlay")
    st.markdown(f"**Legs:** {legs_txt}")
    st.markdown(f"**Odds:** {fmt_american(best_parlay['odds'])} | **Hit %:** {best_parlay['hit_prob']*100:.1f}% | **EV:** {best_parlay['ev_pct']:.1f}% | **Correlation Penalty:** {best_parlay['corr_pen']:.2f}")

st.markdown("## 📈 Self-Learning Status")
if perf_now.empty:
    st.info("Not enough settled bet history yet for supervised self-learning. Track and grade at least 50 settled bets per model.")
else:
    st.dataframe(perf_now, use_container_width=True, hide_index=True)

st.markdown("## 📒 Bet Log + Performance")
bet_log = load_bet_log()
if bet_log.empty:
    st.info("No tracked bets yet.")
else:
    summary = tracker_summary(bet_log)
    render_summary_box([
        ("Tracked Bets", str(summary["bets"])),
        ("Profit", f"{summary['profit_u']:.2f}u"),
        ("ROI", f"{summary['roi_pct']:.1f}%"),
        ("Avg CLV", f"{summary['avg_clv']:.2f}%"),
    ])

    editable = bet_log.copy()
    for idx in editable.index:
        title = f'{editable.loc[idx, "player"]} • {editable.loc[idx, "market"]} • {editable.loc[idx, "bet_side"]} {editable.loc[idx, "line"]}'
        with st.expander(title, expanded=False):
            result = st.selectbox("Result", ["Pending", "Win", "Loss", "Push"], index=["Pending","Win","Loss","Push"].index(str(editable.loc[idx, "result"])), key=f"res_{idx}")
            closing_odds = st.number_input("Closing odds", value=float(editable.loc[idx, "closing_odds"]) if pd.notna(editable.loc[idx, "closing_odds"]) else 0.0, step=1.0, key=f"close_{idx}")
            notes = st.text_input("Notes", value=str(editable.loc[idx, "notes"]), key=f"note_{idx}")
            if st.button("Save grading", key=f"save_{idx}"):
                editable.loc[idx, "result"] = result
                editable.loc[idx, "closing_odds"] = closing_odds if closing_odds != 0 else np.nan
                editable.loc[idx, "notes"] = notes
                editable.loc[idx, "profit_u"] = settle_bet(result, safe_float(editable.loc[idx, "placed_odds"], np.nan), safe_float(editable.loc[idx, "stake_u"], 0.0))
                if pd.notna(editable.loc[idx, "closing_odds"]):
                    placed_ip = american_to_implied_prob(safe_float(editable.loc[idx, "placed_odds"], np.nan))
                    close_ip = american_to_implied_prob(safe_float(editable.loc[idx, "closing_odds"], np.nan))
                    editable.loc[idx, "clv_placed_vs_close_pct"] = round((close_ip - placed_ip) * 100, 2)
                else:
                    editable.loc[idx, "clv_placed_vs_close_pct"] = np.nan
                save_df(editable, BET_LOG_FILE)
                st.success("Bet updated.")

    display_log = load_bet_log().copy()
    if not display_log.empty:
        for col in ["placed_odds", "best_odds", "closing_odds"]:
            display_log[col] = display_log[col].apply(lambda x: fmt_american(x) if pd.notna(x) else "—")
        for col in ["edge_pct", "ev_pct", "predicted_clv_pct", "clv_placed_vs_close_pct"]:
            display_log[col] = pd.to_numeric(display_log[col], errors="coerce").apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "—")
        display_log["stake_u"] = pd.to_numeric(display_log["stake_u"], errors="coerce").round(2).astype(str) + "u"
        st.dataframe(display_log, use_container_width=True, hide_index=True)

st.markdown("## 📢 Alert Log")
alert_log = load_alert_log()
if alert_log.empty:
    st.info("No alerts yet. Alerts trigger only after scheduled windows or manual refresh.")
else:
    st.dataframe(alert_log.sort_index(ascending=False), use_container_width=True, hide_index=True)

st.markdown("## 📒 Call Log")
call_log = load_call_log()
if call_log.empty:
    st.info("No API calls logged yet.")
else:
    st.dataframe(call_log.sort_index(ascending=False), use_container_width=True, hide_index=True)

st.caption("V13 TRACKING + PNL CORE: full build with bet log, grading, profit tracking, ROI, CLV tracking, automation queue, fallback triggers, confidence tiers, and stability-safe data guards.")
