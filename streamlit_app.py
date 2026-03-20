
import math
import itertools
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Sports AI Betting Dashboard V9.6", layout="wide")

APP_VERSION = "V9.6 Fallback + CLV + Scheduled Alerts"
CALL_LOG_FILE = "api_call_log.csv"
BET_LOG_FILE = "bet_log.csv"
ALERT_LOG_FILE = "alert_log.csv"
SNAPSHOT_FILE = "play_snapshot.csv"
MAX_DAILY_CALLS = 500
ET_TZ = ZoneInfo("America/New_York")
SCHEDULE_WINDOWS = {
    "5:00 AM ET": (5, 0),
    "1:00 PM ET": (13, 0),
    "5:30 PM ET": (17, 30),
}

def safe_float(v, default=np.nan):
    try:
        if pd.isna(v):
            return default
        return float(v)
    except Exception:
        return default

def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))

def american_to_decimal(odds: float) -> float:
    odds = safe_float(odds)
    if pd.isna(odds):
        return np.nan
    return 1 + (odds / 100) if odds > 0 else 1 + (100 / abs(odds))

def american_to_implied_prob(odds: float) -> float:
    odds = safe_float(odds)
    if pd.isna(odds):
        return np.nan
    return 100 / (odds + 100) if odds > 0 else abs(odds) / (abs(odds) + 100)

def decimal_to_american(dec: float) -> float:
    dec = safe_float(dec)
    if pd.isna(dec) or dec <= 1:
        return np.nan
    if dec >= 2:
        return round((dec - 1) * 100)
    return round(-100 / (dec - 1))

def normal_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))

def fmt_american(v: float) -> str:
    if pd.isna(v):
        return "—"
    v = int(round(v))
    return f"+{v}" if v > 0 else str(v)

def et_now() -> datetime:
    return datetime.now(ET_TZ)

def today_et_str() -> str:
    return et_now().strftime("%Y-%m-%d")

def current_et_label() -> str:
    return et_now().strftime("%Y-%m-%d %I:%M %p ET")

st.markdown("""
<style>
.block-container {padding-top: 1rem; padding-bottom: 4rem; max-width: 1120px;}
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
.small-muted {color:#6b7280; font-size:.95rem;}
.alert-box {
    border:1px solid rgba(245,158,11,.35);
    border-radius:18px;
    padding:14px;
    background: #fff7ed;
    margin-bottom: 12px;
}
.watch-box {
    border:1px solid rgba(59,130,246,.28);
    border-radius:18px;
    padding:14px;
    background: #eff6ff;
    margin-bottom: 12px;
}
</style>
""", unsafe_allow_html=True)

def load_csv_file(path: str, columns: list[str]) -> pd.DataFrame:
    if os.path.exists(path):
        try:
            return pd.read_csv(path)
        except Exception:
            pass
    return pd.DataFrame(columns=columns)

def save_df(df: pd.DataFrame, path: str):
    df.to_csv(path, index=False)

def load_call_log() -> pd.DataFrame:
    return load_csv_file(CALL_LOG_FILE, ["timestamp_et", "date_et", "window", "reason", "call_count"])

def load_bet_log() -> pd.DataFrame:
    return load_csv_file(BET_LOG_FILE, [
        "timestamp", "player", "market", "bet_side", "line", "book", "best_book",
        "placed_odds", "best_odds", "stake_u", "stake_$", "edge_pct", "ev_pct",
        "result", "profit_u", "closing_odds", "clv_placed_vs_close_pct", "notes"
    ])

def load_alert_log() -> pd.DataFrame:
    return load_csv_file(ALERT_LOG_FILE, ["timestamp_et", "date_et", "window", "play_key", "alert_type", "message"])

def load_snapshot() -> pd.DataFrame:
    return load_csv_file(SNAPSHOT_FILE, ["play_key", "player", "market", "bet_side", "line", "best_book", "best_display_odds", "true_edge", "realistic_ev_pct", "movement_note", "qualified"])

def log_api_call(reason: str, call_count: int = 1, window: str = ""):
    log = load_call_log()
    row = {
        "timestamp_et": current_et_label(),
        "date_et": today_et_str(),
        "window": window,
        "reason": reason,
        "call_count": call_count,
    }
    log = pd.concat([log, pd.DataFrame([row])], ignore_index=True)
    save_df(log, CALL_LOG_FILE)

def log_alert(window: str, play_key: str, alert_type: str, message: str):
    log = load_alert_log()
    row = {
        "timestamp_et": current_et_label(),
        "date_et": today_et_str(),
        "window": window,
        "play_key": play_key,
        "alert_type": alert_type,
        "message": message,
    }
    log = pd.concat([log, pd.DataFrame([row])], ignore_index=True)
    save_df(log, ALERT_LOG_FILE)

def get_today_calls() -> int:
    log = load_call_log()
    if log.empty:
        return 0
    return int(pd.to_numeric(log.loc[log["date_et"] == today_et_str(), "call_count"], errors="coerce").fillna(0).sum())

def get_remaining_calls() -> int:
    return max(0, MAX_DAILY_CALLS - get_today_calls())

def call_status_label(used: int) -> str:
    pct = used / MAX_DAILY_CALLS if MAX_DAILY_CALLS else 0
    if pct >= 0.95:
        return "🔴 Hard stop"
    if pct >= 0.80:
        return "🟠 Warning"
    return "🟢 Safe"

def was_window_run_today(window_name: str) -> bool:
    log = load_call_log()
    if log.empty:
        return False
    today = today_et_str()
    return bool(((log["date_et"] == today) & (log["window"] == window_name)).any())

def should_run_window(window_name: str) -> bool:
    hour, minute = SCHEDULE_WINDOWS[window_name]
    now = et_now()
    if now.hour > hour or (now.hour == hour and now.minute >= minute):
        return not was_window_run_today(window_name)
    return False

def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
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
    for c in ["line", "projection", "odds", "minutes", "std_dev", "spread", "pace", "usage",
              "open_odds", "last5_avg", "defense_rank", "minutes_volatility",
              "odds_fanduel", "odds_draftkings", "odds_betmgm", "odds_caesars"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["starter"] = df["starter"].fillna(False).astype(bool)
    if (df["matchup"] == "").any():
        auto_match = df["team"].fillna("") + np.where(df["opponent"].fillna("") != "", " vs " + df["opponent"].fillna(""), "")
        df.loc[df["matchup"] == "", "matchup"] = auto_match[df["matchup"] == ""]
    return df

def infer_market_std(row: pd.Series) -> float:
    supplied = row.get("std_dev")
    if pd.notna(supplied) and supplied > 0:
        return float(supplied)
    market = str(row.get("market", "")).lower()
    defaults = {"points": 8.5, "rebounds": 4.0, "assists": 3.6, "pra": 9.0, "threes": 2.4, "3pm": 2.4}
    for k, v in defaults.items():
        if k in market:
            return v
    return 7.5

def infer_bet_side(row: pd.Series) -> str:
    side = str(row.get("bet_side", "")).title()
    if side in {"Over", "Under"}:
        return side
    p, l = row.get("projection"), row.get("line")
    if pd.isna(p) or pd.isna(l):
        return "Over"
    return "Over" if p >= l else "Under"

def calculate_hit_probability(row: pd.Series) -> float:
    p, l = row.get("projection"), row.get("line")
    if pd.isna(p) or pd.isna(l):
        return np.nan
    std = infer_market_std(row)
    z = (p - l) / std if std > 0 else 0
    p_over = normal_cdf(z)
    return clamp01(1 - p_over if infer_bet_side(row) == "Under" else p_over)

def best_book_and_odds(row: pd.Series) -> Tuple[str, float]:
    books = {
        "FanDuel": safe_float(row.get("odds_fanduel"), np.nan),
        "DraftKings": safe_float(row.get("odds_draftkings"), np.nan),
        "BetMGM": safe_float(row.get("odds_betmgm"), np.nan),
        "Caesars": safe_float(row.get("odds_caesars"), np.nan),
    }
    valid = {k: v for k, v in books.items() if not pd.isna(v)}
    if not valid:
        current_book = str(row.get("book", "")).strip() or "Current Book"
        return current_book, safe_float(row.get("odds"), np.nan)
    best_book = None
    best_prob = None
    best_odds = np.nan
    for bk, od in valid.items():
        ip = american_to_implied_prob(od)
        if pd.isna(ip):
            continue
        if best_prob is None or ip < best_prob:
            best_prob = ip
            best_book = bk
            best_odds = od
    return best_book, best_odds

def movement_label(delta_implied_pct: float) -> str:
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

def compute_scores(df: pd.DataFrame, bankroll: float = 1000, max_single_pct: float = 0.0125) -> pd.DataFrame:
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
    out["consensus_score"] = (
        (out["realistic_hit_prob"] * 100) * 0.30
        + (out["true_edge"] * 100).clip(-5, 18) * 1.15
        + out["realistic_ev_pct"].clip(-10, 25) * 0.85
        + np.where(out["starter"], 4, -6)
        + np.where(out["minutes"].fillna(0) >= 33, 5, np.where(out["minutes"].fillna(0) >= 28, 2, -4))
        + np.where(out["line_move_pct"] >= 2, 2, 0)
    ).clip(0, 100).round(1)
    out["model_agreement_pct"] = np.select(
        [out["consensus_score"] >= 80, out["consensus_score"] >= 72, out["consensus_score"] >= 64],
        [80, 60, 40],
        default=20
    )
    out["consensus_action"] = np.where(
        (out["consensus_score"] >= 78) & (out["true_edge"] >= 0.035), "Bet",
        np.where((out["consensus_score"] >= 64) & (out["true_edge"] >= 0.015), "Lean", "Pass")
    )
    out["confidence_grade"] = np.select(
        [out["consensus_score"] >= 80, out["consensus_score"] >= 72, out["consensus_score"] >= 65, out["consensus_score"] >= 60],
        ["A+ ELITE", "A STRONG", "B+ VALUE", "B LEAN"],
        default="C PASS"
    )
    b = dec - 1
    q = 1 - out["realistic_hit_prob"]
    raw_kelly = np.where((b > 0) & out["realistic_hit_prob"].between(0.001, 0.999), np.maximum(0, (b * out["realistic_hit_prob"] - q) / b), 0)
    mult = np.where(out["consensus_score"] >= 78, 0.42, np.where(out["consensus_score"] >= 68, 0.30, 0.18))
    frac = np.minimum(raw_kelly * mult, max_single_pct)
    out["single_stake_$"] = bankroll * frac
    out["single_stake_u"] = np.where(bankroll > 0, out["single_stake_$"] / (bankroll * 0.01), 0).round(2)
    out["rank_score"] = (
        out["consensus_score"] * 0.46
        + out["realistic_ev_pct"] * 0.95
        + (out["true_edge"] * 100) * 1.05
    ).round(2)
    out["play_key"] = out["player"].astype(str) + "|" + out["market"].astype(str) + "|" + out["bet_side"].astype(str) + "|" + out["line"].astype(str)
    return out

def approved_pool(df: pd.DataFrame) -> pd.DataFrame:
    return df[
        (
            (df["consensus_action"] == "Bet") |
            ((df["consensus_action"] == "Lean") & (df["model_agreement_pct"] >= 60))
        )
        & (df["true_edge"] >= 0.02)
        & (df["realistic_ev_pct"] >= 2.0)
    ].copy()

def apply_game_exposure_limit(df: pd.DataFrame, max_per_game: int = 2) -> pd.DataFrame:
    if df.empty:
        return df
    counts = {}
    rows = []
    for _, row in df.sort_values(["rank_score", "realistic_ev_pct"], ascending=False).iterrows():
        matchup = str(row.get("matchup", ""))
        counts.setdefault(matchup, 0)
        if counts[matchup] < max_per_game:
            rows.append(row)
            counts[matchup] += 1
    return pd.DataFrame(rows).reset_index(drop=True)

def unique_top_plays(df: pd.DataFrame) -> Dict[str, pd.Series]:
    if df.empty:
        return {"best": pd.Series(dtype=object), "safe": pd.Series(dtype=object), "edge": pd.Series(dtype=object)}
    best = df.sort_values(["rank_score", "realistic_ev_pct"], ascending=False).iloc[0]
    safe = df.sort_values(["realistic_hit_prob", "consensus_score"], ascending=False).iloc[0]
    edge = df.sort_values(["true_edge", "realistic_ev_pct"], ascending=False).iloc[0]
    return {"best": best, "safe": safe, "edge": edge}

def combo_corr_penalty(rows: List[pd.Series]) -> float:
    total = 0.0
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            total += 0.12 if str(rows[i].get("matchup","")) == str(rows[j].get("matchup","")) else 0.0
    return total

def build_best_parlay(df: pd.DataFrame, leg_size: int = 2) -> Dict:
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
        candidate = {
            "legs": list(combo),
            "odds": decimal_to_american(combined_dec),
            "hit_prob": hit_prob,
            "ev_pct": min(ev * 100, 60),
            "corr_pen": corr_pen,
            "score": score
        }
        if best is None or candidate["score"] > best["score"]:
            best = candidate
    return best or {}

def simulate_live_refresh(df: pd.DataFrame, top_n: int, edge_threshold_pct: float) -> Tuple[pd.DataFrame, int]:
    refreshed = df.copy()
    eligible = refreshed[(refreshed["true_edge"] * 100 >= edge_threshold_pct)].sort_values(["rank_score", "realistic_ev_pct"], ascending=False).head(top_n)
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

def create_alerts(previous_snapshot: pd.DataFrame, current_pool: pd.DataFrame, window_name: str) -> list[str]:
    alerts = []
    prev_map = {row["play_key"]: row for _, row in previous_snapshot.iterrows()} if not previous_snapshot.empty else {}
    curr_map = {row["play_key"]: row for _, row in current_pool.iterrows()} if not current_pool.empty else {}

    for key, row in curr_map.items():
        prev_row = prev_map.get(key)
        player = row["player"]
        if prev_row is None:
            msg = f"{player}: new qualified play entered pool."
            alerts.append(msg); log_alert(window_name, key, "new_play", msg); continue

        prev_ev = safe_float(prev_row.get("realistic_ev_pct"), np.nan)
        curr_ev = safe_float(row.get("realistic_ev_pct"), np.nan)
        if not pd.isna(prev_ev) and not pd.isna(curr_ev) and curr_ev - prev_ev >= 2.0:
            msg = f"{player}: EV improved by {curr_ev - prev_ev:.1f}%."
            alerts.append(msg); log_alert(window_name, key, "ev_improved", msg)

        if str(prev_row.get("best_book","")) != str(row.get("best_book","")):
            msg = f"{player}: best book changed to {row['best_book']}."
            alerts.append(msg); log_alert(window_name, key, "best_book_changed", msg)

        if "Steam" not in str(prev_row.get("movement_note","")) and "Steam" in str(row.get("movement_note","")):
            msg = f"{player}: steam detected after refresh."
            alerts.append(msg); log_alert(window_name, key, "steam_detected", msg)

    for key, row in prev_map.items():
        if key not in curr_map:
            msg = f"{row['player']}: play dropped out of qualification."
            alerts.append(msg); log_alert(window_name, key, "dropped_out", msg)

    return alerts

def save_snapshot_from_pool(pool: pd.DataFrame):
    if pool.empty:
        save_df(pd.DataFrame(columns=["play_key", "player", "market", "bet_side", "line", "best_book", "best_display_odds", "true_edge", "realistic_ev_pct", "movement_note", "qualified"]), SNAPSHOT_FILE)
        return
    snap = pool[["play_key", "player", "market", "bet_side", "line", "best_book", "best_display_odds", "true_edge", "realistic_ev_pct", "movement_note"]].copy()
    snap["qualified"] = True
    save_df(snap, SNAPSHOT_FILE)

def add_bet_to_log(row: pd.Series):
    log = load_bet_log()
    new_row = {
        "timestamp": current_et_label(),
        "player": row["player"],
        "market": row["market"],
        "bet_side": row["bet_side"],
        "line": row["line"],
        "book": row["book"],
        "best_book": row["best_book"],
        "placed_odds": row["odds"],
        "best_odds": row["best_display_odds"],
        "stake_u": row["single_stake_u"],
        "stake_$": row["single_stake_$"],
        "edge_pct": row["true_edge"] * 100,
        "ev_pct": row["realistic_ev_pct"],
        "result": "Pending",
        "profit_u": 0.0,
        "closing_odds": np.nan,
        "clv_placed_vs_close_pct": np.nan,
        "notes": ""
    }
    log = pd.concat([log, pd.DataFrame([new_row])], ignore_index=True)
    save_df(log, BET_LOG_FILE)

def settle_bet(result: str, placed_odds: float, stake_u: float) -> float:
    dec = american_to_decimal(placed_odds)
    if pd.isna(dec):
        return 0.0
    if result == "Win":
        return round((dec - 1) * stake_u, 2)
    if result == "Loss":
        return round(-1.0 * stake_u, 2)
    return 0.0

def tracker_summary(log: pd.DataFrame) -> Dict[str, float]:
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

def render_metric_box(label: str, value: str):
    st.markdown(f"""<div class="metric-box"><div class="metric-label">{label}</div><div class="metric-value">{value}</div></div>""", unsafe_allow_html=True)

def render_best_bet(row: pd.Series):
    st.markdown("## 🔥 Best Bet")
    st.markdown(f"### {row['player']} — {row['bet_side']} {row['line']} {row['market']}")
    st.markdown(f"**Current Odds:** {fmt_american(row['odds'])} | **Best Odds:** {fmt_american(row['best_display_odds'])} ({row['best_book']}) | **EV:** {row['realistic_ev_pct']:.1f}%")
    c1, c2, c3 = st.columns(3)
    with c1: render_metric_box("Hit %", f"{row['realistic_hit_prob']*100:.0f}%")
    with c2: render_metric_box("Edge", f"{row['true_edge']*100:.1f}%")
    with c3: render_metric_box("Stake", f"{row['single_stake_u']:.2f}u")
    st.progress(float(row["realistic_hit_prob"]))

def render_compact_play(row: pd.Series):
    st.markdown(f"**{row['player']} — {row['bet_side']} {row['line']} {row['market']}**")
    st.caption(f"Best {fmt_american(row['best_display_odds'])} ({row['best_book']}) | EV {row['realistic_ev_pct']:.1f}% | Edge {row['true_edge']*100:.1f}% | Stake {row['single_stake_u']:.2f}u | {row['movement_note']}")
    st.divider()

def sample_data() -> pd.DataFrame:
    return pd.DataFrame([
        {"player": "Stephen Curry", "team": "GSW", "opponent": "LAL", "matchup": "Warriors vs Lakers", "market": "points", "bet_side": "Over", "line": 27.0, "projection": 32.2, "odds": -115, "open_odds": -102, "book": "DraftKings", "starter": True, "minutes": 35, "spread": -2.5, "pace": 102.4, "usage": 31.0, "last5_avg": 33.1, "defense_rank": 24, "minutes_volatility": 2.1, "odds_fanduel": -112, "odds_draftkings": -115, "odds_betmgm": -108, "odds_caesars": -110},
        {"player": "LeBron James", "team": "LAL", "opponent": "GSW", "matchup": "Lakers vs Warriors", "market": "pra", "bet_side": "Over", "line": 38.0, "projection": 43.8, "odds": -115, "open_odds": -105, "book": "DraftKings", "starter": True, "minutes": 36, "spread": 2.5, "pace": 101.9, "usage": 30.5, "last5_avg": 45.2, "defense_rank": 23, "minutes_volatility": 2.2, "odds_fanduel": -112, "odds_draftkings": -115, "odds_betmgm": -110, "odds_caesars": -111},
        {"player": "Anthony Davis", "team": "LAL", "opponent": "GSW", "matchup": "Lakers vs Warriors", "market": "rebounds", "bet_side": "Over", "line": 11.5, "projection": 13.1, "odds": -105, "open_odds": -104, "book": "FanDuel", "starter": True, "minutes": 35, "spread": 2.5, "pace": 101.9, "usage": 27.0, "last5_avg": 12.8, "defense_rank": 19, "minutes_volatility": 2.6, "odds_fanduel": -105, "odds_draftkings": -102, "odds_betmgm": 100, "odds_caesars": -101},
        {"player": "Jordan Poole", "team": "WAS", "opponent": "BKN", "matchup": "Wizards vs Nets", "market": "points", "bet_side": "Over", "line": 21.5, "projection": 24.4, "odds": 102, "open_odds": 108, "book": "Caesars", "starter": True, "minutes": 33, "spread": 5.0, "pace": 99.6, "usage": 30.0, "last5_avg": 25.8, "defense_rank": 25, "minutes_volatility": 4.2, "odds_fanduel": 100, "odds_draftkings": 101, "odds_betmgm": 103, "odds_caesars": 102},
        {"player": "Jalen Brunson", "team": "NYK", "opponent": "MIA", "matchup": "Knicks vs Heat", "market": "points", "bet_side": "Over", "line": 26.5, "projection": 29.7, "odds": -110, "open_odds": -101, "book": "FanDuel", "starter": True, "minutes": 36, "spread": -3.0, "pace": 98.7, "usage": 30.6, "last5_avg": 30.9, "defense_rank": 9, "minutes_volatility": 1.8, "odds_fanduel": -110, "odds_draftkings": -106, "odds_betmgm": -104, "odds_caesars": -108},
    ])

@st.cache_data(show_spinner=False)
def load_uploaded_csv(file) -> pd.DataFrame:
    return pd.read_csv(file)

st.title("🏀 Sports AI Betting Dashboard V9.6")
st.caption("Fallback plays, CLV tracking, and alerts only after scheduled windows or manual refresh.")

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
    st.markdown("### Bankroll")
    bankroll = st.number_input("Bankroll ($)", min_value=100, max_value=100000, value=1000, step=50)
    max_single_pct = st.slider("Max bankroll % per single", 0.25, 3.0, 1.25, 0.25) / 100.0
    st.markdown("### Engine")
    min_score = st.slider("Min approval score", 55, 90, 64)
    min_edge = st.slider("Min true edge %", 0.0, 15.0, 2.0, 0.5)
    min_ev = st.slider("Min EV %", 0.0, 25.0, 2.0, 0.5)
    sharp_mode = st.toggle("Sharp Mode", value=True)
    max_per_game = st.slider("Max plays per game", 1, 3, 2)

used_calls = get_today_calls()
remaining_calls = get_remaining_calls()
status = call_status_label(used_calls)
st.markdown(f"""<div class="banner"><div><b>API Calls Used Today:</b> {used_calls} / {MAX_DAILY_CALLS}</div><div><b>Remaining:</b> {remaining_calls}</div><div><b>Status:</b> {status}</div><div><b>Eastern Time:</b> {current_et_label()}</div></div>""", unsafe_allow_html=True)
st.progress(min(used_calls / MAX_DAILY_CALLS, 1.0))

if uploaded and not use_sample:
    base_df = ensure_columns(load_uploaded_csv(uploaded))
else:
    base_df = ensure_columns(sample_data())

pre_scored = compute_scores(base_df, bankroll=float(bankroll), max_single_pct=float(max_single_pct))
refresh_reason = None
refresh_window = ""
if remaining_calls <= int(MAX_DAILY_CALLS * 0.05):
    st.warning("Daily call protection is active. Live refresh disabled because you are above 95% of limit.")
elif live_mode == "Manual Only" and manual_refresh:
    refresh_reason = "manual_top_plays_refresh"; refresh_window = "manual"
elif live_mode == "Scheduled (3x daily)":
    for win in scheduled_windows:
        if should_run_window(win):
            refresh_reason = "scheduled_window_refresh"; refresh_window = win; break
    if manual_refresh:
        refresh_reason = "manual_top_plays_refresh"; refresh_window = "manual"

previous_snapshot = load_snapshot()
alerts_to_show = []
if refresh_reason:
    base_df, call_cost = simulate_live_refresh(base_df, top_n=top_live_checks, edge_threshold_pct=min_live_edge)
    log_api_call(refresh_reason, call_count=max(1, call_cost), window=refresh_window)

scored = compute_scores(base_df, bankroll=float(bankroll), max_single_pct=float(max_single_pct))

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

pool = approved_pool(filtered)
pool = pool[(pool["consensus_score"] >= min_score) & ((pool["true_edge"] * 100) >= min_edge) & (pool["realistic_ev_pct"] >= min_ev)].copy()
pool = apply_game_exposure_limit(pool, max_per_game=max_per_game)

if sharp_mode:
    pool = pool[(pool["confidence_grade"].isin(["A+ ELITE", "A STRONG"])) & (pool["consensus_action"] == "Bet")].copy()
    pool = pool.sort_values(["rank_score", "realistic_ev_pct"], ascending=False).head(3)

if refresh_reason:
    alerts_to_show = create_alerts(previous_snapshot, pool, refresh_window)
    save_snapshot_from_pool(pool)
elif previous_snapshot.empty:
    save_snapshot_from_pool(pool)

if alerts_to_show:
    st.markdown("## 🔔 Alerts")
    for a in alerts_to_show:
        st.markdown(f'<div class="alert-box">{a}</div>', unsafe_allow_html=True)

fallback_pool = filtered.sort_values(["rank_score", "realistic_ev_pct", "true_edge"], ascending=False).head(3).copy()
fallback_pool["fallback_label"] = np.where(
    fallback_pool["consensus_score"] >= max(min_score - 3, 55),
    "⚠️ Near threshold",
    np.where(fallback_pool["realistic_ev_pct"] >= max(min_ev - 1, 0), "🟡 Monitor", "🔍 Needs line movement")
)

if pool.empty:
    st.warning("No plays qualify under the current V9.6 filters.")
    st.markdown("## 🔎 Fallback Plays")
    for _, row in fallback_pool.iterrows():
        st.markdown(f'<div class="watch-box"><b>{row["fallback_label"]}</b><br>{row["player"]} — {row["bet_side"]} {row["line"]} {row["market"]}<br>Best {fmt_american(row["best_display_odds"])} ({row["best_book"]}) | EV {row["realistic_ev_pct"]:.1f}% | Edge {row["true_edge"]*100:.1f}%</div>', unsafe_allow_html=True)
    st.stop()

pool = pool.sort_values(["rank_score", "realistic_ev_pct", "true_edge"], ascending=False).reset_index(drop=True)
tops = unique_top_plays(pool)
best_play = tops["best"]; safe_play = tops["safe"]; edge_play = tops["edge"]
best_parlay = build_best_parlay(pool, leg_size=2)

st.markdown(f"""<div class="banner"><div><b>Approved Plays:</b> {len(pool)}</div><div><b>Best Play:</b> {best_play['player']} {best_play['bet_side']} {best_play['line']} {best_play['market']}</div><div><b>Safest Play:</b> {safe_play['player']} ({safe_play['realistic_hit_prob']*100:.1f}%)</div><div><b>Highest Edge:</b> {edge_play['player']} ({edge_play['true_edge']*100:.1f}%)</div><div><b>Line Shop:</b> {best_play['best_book']} {fmt_american(best_play['best_display_odds'])}</div></div>""", unsafe_allow_html=True)

render_best_bet(best_play)

st.markdown("## 📋 Other Plays")
for _, row in pool.iloc[1:4].iterrows():
    render_compact_play(row)

st.markdown("## ✅ Add To Bet Log")
cols = st.columns(min(3, len(pool)))
for i, (_, row) in enumerate(pool.head(3).iterrows()):
    with cols[i]:
        if st.button(f"Track {row['player']}", key=f"track_{i}"):
            add_bet_to_log(row)
            st.success(f"Added {row['player']} to bet log.")

st.markdown("## 💰 Bankroll")
c1, c2, c3 = st.columns(3)
with c1: render_metric_box("Top Stake", f"{best_play['single_stake_u']:.2f}u")
with c2:
    parlay_units = 0.75 if not best_parlay else min(1.00, max(0.25, best_parlay["ev_pct"] / 20))
    render_metric_box("Parlay Stake", f"{parlay_units:.2f}u")
with c3:
    roi_est = (best_play["realistic_ev_pct"] * 0.55) + ((best_parlay["ev_pct"] if best_parlay else 0) * 0.45)
    render_metric_box("ROI", f"{min(roi_est, 42.0):.1f}%")

if best_parlay:
    legs_txt = " + ".join([f"{x['player']} {x['bet_side']} {x['line']}" for x in best_parlay["legs"]])
    st.markdown("## 🧩 Best 2-Leg Parlay")
    st.markdown(f"**Legs:** {legs_txt}")
    st.markdown(f"**Odds:** {fmt_american(best_parlay['odds'])} | **Hit %:** {best_parlay['hit_prob']*100:.1f}% | **EV:** {best_parlay['ev_pct']:.1f}% | **Correlation Penalty:** {best_parlay['corr_pen']:.2f}")

st.markdown("## 📒 Auto Tracker + CLV")
bet_log = load_bet_log()
if bet_log.empty:
    st.info("No tracked bets yet.")
else:
    summary = tracker_summary(bet_log)
    s1, s2, s3, s4 = st.columns(4)
    with s1: render_metric_box("Tracked Bets", str(summary["bets"]))
    with s2: render_metric_box("Profit", f"{summary['profit_u']:.2f}u")
    with s3: render_metric_box("ROI", f"{summary['roi_pct']:.1f}%")
    with s4: render_metric_box("Avg CLV", f"{summary['avg_clv']:.2f}%")
    editable = bet_log.copy()
    for idx in editable.index:
        with st.expander(f'{editable.loc[idx, "player"]} • {editable.loc[idx, "market"]} • {editable.loc[idx, "bet_side"]} {editable.loc[idx, "line"]}', expanded=False):
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
        display_log["placed_odds"] = display_log["placed_odds"].apply(lambda x: fmt_american(x) if pd.notna(x) else "—")
        display_log["best_odds"] = display_log["best_odds"].apply(lambda x: fmt_american(x) if pd.notna(x) else "—")
        display_log["closing_odds"] = display_log["closing_odds"].apply(lambda x: fmt_american(x) if pd.notna(x) else "—")
        display_log["edge_pct"] = pd.to_numeric(display_log["edge_pct"], errors="coerce").round(1).astype(str) + "%"
        display_log["ev_pct"] = pd.to_numeric(display_log["ev_pct"], errors="coerce").round(1).astype(str) + "%"
        display_log["stake_u"] = pd.to_numeric(display_log["stake_u"], errors="coerce").round(2).astype(str) + "u"
        display_log["clv_placed_vs_close_pct"] = display_log["clv_placed_vs_close_pct"].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "—")
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

st.caption("V9.6: fallback plays, CLV tracking, and alerts only after scheduled windows or manual refresh.")
