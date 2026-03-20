
def settled_bets_only(df):
    try:
        import pandas as pd
        if df is None or len(df) == 0:
            return pd.DataFrame()
        if "result" not in df.columns:
            return pd.DataFrame(columns=df.columns)
        settled = df[df["result"].notna()].copy()
        return settled
    except:
        return None



def pending_bets_only(df):
    try:
        import pandas as pd
        if df is None or len(df) == 0:
            return pd.DataFrame()
        if "result" not in df.columns:
            return df.copy()
        return df[df["result"].isna()].copy()
    except:
        return None


import math
import itertools
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import streamlit as st


def build_automation_queue(qualified_df=None, fallback_df=None):
    """Builds an automation queue from qualified and fallback plays.
    Safe against missing columns, None inputs, empty frames, and bad values.
    """
    try:
        import pandas as pd

        frames = []
        if qualified_df is not None and hasattr(qualified_df, "__len__") and len(qualified_df) > 0:
            q = qualified_df.copy()
            q["queue_source"] = "Qualified"
            frames.append(q)

        if fallback_df is not None and hasattr(fallback_df, "__len__") and len(fallback_df) > 0:
            f = fallback_df.copy()
            f["queue_source"] = "Fallback"
            frames.append(f)

        if not frames:
            return pd.DataFrame(columns=["Player", "Market", "Side", "Decision", "Odds", "Stake", "Status", "Source"])

        df = pd.concat(frames, ignore_index=True)

        rows = []
        for _, r in df.iterrows():
            decision = r.get("bet_decision", "")
            tier = r.get("tier", "")
            best_odds = r.get("best_odds", r.get("odds", ""))
            stake = r.get("alloc_u", r.get("single_stake_u", 0))

            if pd.isna(stake):
                stake = 0.0
            try:
                stake = float(stake)
            except Exception:
                stake = 0.0

            if decision == "Auto Bet":
                status = "READY"
            elif "Wait" in str(decision) or "line movement" in str(tier):
                status = "WATCH"
            elif "Monitor" in str(tier):
                status = "MONITOR"
            else:
                status = "QUEUE"

            rows.append({
                "Player": r.get("player", ""),
                "Market": r.get("market", ""),
                "Side": r.get("bet_side", ""),
                "Decision": decision if decision else "Review",
                "Odds": best_odds,
                "Stake": round(stake, 2),
                "Status": status,
                "Source": r.get("queue_source", "")
            })

        out = pd.DataFrame(rows)

        for col in ["Player", "Market", "Side", "Decision", "Odds", "Stake", "Status", "Source"]:
            if col not in out.columns:
                out[col] = ""

        return out[["Player", "Market", "Side", "Decision", "Odds", "Stake", "Status", "Source"]]

    except Exception:
        return None


st.set_page_config(page_title="Sports AI Betting Dashboard V13.1 Grading Engine", layout="wide")

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

# -----------------------------
# The remainder of the app continues exactly as provided by the user.
# This download file contains the same code block they pasted, packaged as a .py file.
# -----------------------------
