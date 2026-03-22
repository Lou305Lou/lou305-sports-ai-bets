
import io
import json
import itertools
from datetime import datetime, date
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Sports AI Dashboard V14 Results + CLV Intelligence", layout="wide")

BET_LOG_FILE = Path("bet_log_auto.csv")
PARLAY_LOG_FILE = Path("parlay_log_auto.csv")
APP_STATE_FILE = Path("sports_ai_auto_state.json")


# ---------- SESSION ----------
if "active_df" not in st.session_state:
    st.session_state.active_df = None
if "active_source" not in st.session_state:
    st.session_state.active_source = "None"
if "bet_log" not in st.session_state:
    st.session_state.bet_log = pd.DataFrame(columns=[
        "bet_id", "added_at", "bet_date", "mode", "entry_type", "sport", "player", "market", "book", "odds", "line", "stake",
        "score", "adjusted_score", "tier", "units", "game", "bet_side", "market_type", "result", "profit", "notes", "risk_mode",
        "bankroll_snapshot", "model_projection", "model_price_ev", "model_risk", "model_market", "model_history", "multi_ai_score",
        "ai_votes_for", "ai_consensus", "clv_closing_line", "clv_direction", "clv_diff", "clv_win"
    ])
if "parlay_log" not in st.session_state:
    st.session_state.parlay_log = pd.DataFrame(columns=[
        "parlay_id", "added_at", "bet_date", "mode", "builder", "sport_mix", "legs", "combined_odds", "stake", "target_min_odds",
        "avg_leg_score", "min_leg_score", "avg_leg_adjusted", "avg_leg_consensus", "consensus_label", "same_game_overlap",
        "same_team_overlap", "result", "profit", "notes", "leg_keys_json", "legs_preview", "parlay_rank", "parlay_grade",
        "parlay_expected_roi", "duplication_penalty", "correlation_penalty", "slip_profile", "portfolio_share",
        "portfolio_target_stake", "estimated_hit_rate", "diversity_score", "adaptive_edge", "adaptive_notes"
    ])
if "learning_state" not in st.session_state:
    st.session_state.learning_state = {
        "weights": {
            "model_projection": 0.30,
            "model_price_ev": 0.25,
            "model_risk": 0.15,
            "model_market": 0.15,
            "model_history": 0.15,
        }
    }
if "bet_slip" not in st.session_state:
    st.session_state.bet_slip = []
if "ai_parlay_slips" not in st.session_state:
    st.session_state.ai_parlay_slips = []
if "launch_settings" not in st.session_state:
    st.session_state.launch_settings = {
        "starting_bankroll": 250.0,
        "risk_mode": "Balanced",
        "max_bets_per_day": 6,
        "max_daily_exposure": 75.0,
        "default_mode": "Paper",
        "lock_after_add": True,
        "min_adjusted_score": 60,
        "singles_min_consensus": 3,
        "singles_min_confidence": 70,
        "singles_min_odds": -200,
        "singles_max_odds": 150,
        "parlay_min_combined_odds": 200,
        "parlay_min_leg_adjusted": 72,
        "parlay_min_leg_consensus": 4,
        "parlay_max_legs": 3,
        "allow_same_game_parlays": False,
        "parlay_build_style": "Hybrid",
        "parlay_support_slips": 3,
        "parlay_pool_size": 16,
        "parlay_max_leg_reuse": 2,
        "parlay_allow_same_market_family_same_game": False,
        "portfolio_best_share": 0.55,
        "portfolio_support_share": 0.45,
        "portfolio_max_total_pct": 0.025,
        "portfolio_min_slip_prob": 0.05,
        "adaptive_auto_mode": True,
        "adaptive_weight": 0.18,
        "adaptive_min_samples": 5,
        "results_clv_auto_mode": True,
        "results_clv_min_samples": 5,
        "results_clv_weight": 0.16,
        "auto_track_enabled": False,
        "auto_track_singles": True,
        "auto_track_parlays": True,
        "auto_track_support_slips": 2,
        "auto_track_mode": "Paper",
    }
if "auto_storage_loaded" not in st.session_state:
    st.session_state.auto_storage_loaded = False
if "auto_last_summary" not in st.session_state:
    st.session_state.auto_last_summary = "Auto-track idle."

# ---------- HELPERS ----------
def normalize_columns(df):
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    return df


def to_numeric_safe(df, cols):
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    return out


def clean_bool(x):
    return str(x).strip().lower() in ["true", "1", "yes", "y"]


def american_to_decimal(odds):
    try:
        odds = float(odds)
    except Exception:
        return np.nan
    if odds == 0:
        return np.nan
    return 1 + (odds / 100 if odds > 0 else 100 / abs(odds))


def decimal_to_american(decimal_odds):
    try:
        d = float(decimal_odds)
    except Exception:
        return np.nan
    if d <= 1:
        return np.nan
    if d >= 2:
        return int(round((d - 1) * 100))
    return int(round(-100 / (d - 1)))


def combined_parlay_odds(odds_list):
    decimals = [american_to_decimal(x) for x in odds_list]
    if any(pd.isna(x) for x in decimals) or not decimals:
        return np.nan
    combined_decimal = float(np.prod(decimals))
    return decimal_to_american(combined_decimal)


def implied_prob(odds):
    try:
        odds = float(odds)
    except Exception:
        return np.nan
    if odds == 0:
        return np.nan
    return 100 / (odds + 100) if odds > 0 else abs(odds) / (abs(odds) + 100)


def calc_ev(hit_pct, odds):
    try:
        p = float(hit_pct) / 100.0
    except Exception:
        return np.nan
    dec = american_to_decimal(odds)
    if pd.isna(dec):
        return np.nan
    return ((p * dec) - 1) * 100


def detect_side(market):
    text = str(market).lower()
    if "over" in text:
        return "Over"
    if "under" in text:
        return "Under"
    if "yes" in text:
        return "Yes"
    if "no" in text:
        return "No"
    if any(x in text for x in ["moneyline", "mainline", "ml"]):
        return "Side"
    if "spread" in text:
        return "Side"
    return ""


def market_family(market):
    text = str(market).strip().lower()
    for token in [" over", " under", " yes", " no"]:
        text = text.replace(token, "")
    return text.replace("_", " ").title()


def classify_market_type(market, player="", game=""):
    text = str(market).strip().lower()
    player_text = str(player).strip()
    game_text = str(game).strip().lower()
    if any(x in text for x in ["moneyline", "mainline", "ml"]):
        return "Mainline"
    if "spread" in text:
        return "Spread"
    if "total" in text:
        return "Total"
    if "team total" in text:
        return "Total"
    if player_text and player_text.lower() not in ["", "nan", "none"]:
        return "Player Prop"
    if any(x in text for x in ["points", "rebounds", "assists", "pra", "shots", "goals", "hits", "bases", "strikeouts"]):
        return "Player Prop"
    if "@" in game_text and not player_text:
        return "Game Bet"
    return "Other"


def parse_csv_text(text):
    if not text or not text.strip():
        return None, "Paste box is empty."
    attempts = [{"sep": ","}, {"sep": ";"}, {"sep": None, "engine": "python"}]
    last_error = None
    for attempt in attempts:
        try:
            return pd.read_csv(io.StringIO(text.strip()), **attempt), None
        except Exception as e:
            last_error = e
    return None, f"Could not parse pasted data: {last_error}"


def read_uploaded_file(uploaded_file):
    if uploaded_file is None:
        return None, "No file uploaded."
    name = (uploaded_file.name or "").lower()
    try:
        file_bytes = uploaded_file.getvalue()
        if not file_bytes:
            return None, "Uploaded file is empty."
        if name.endswith(".csv"):
            attempts = [
                {"encoding": "utf-8", "sep": ","},
                {"encoding": "utf-8-sig", "sep": ","},
                {"encoding": "latin1", "sep": ","},
                {"encoding": "utf-8", "sep": ";"},
                {"encoding": "latin1", "sep": ";"},
            ]
            last_error = None
            for attempt in attempts:
                try:
                    return pd.read_csv(io.BytesIO(file_bytes), **attempt), None
                except Exception as e:
                    last_error = e
            return None, f"CSV read failed: {last_error}"
        if name.endswith(".xlsx") or name.endswith(".xls"):
            return pd.read_excel(io.BytesIO(file_bytes)), None
        return None, "Unsupported file type. Use CSV or Excel."
    except Exception as e:
        return None, f"Unexpected upload error: {e}"


def settle_profit(odds, stake, result):
    try:
        odds = float(odds)
        stake = float(stake)
    except Exception:
        return np.nan
    result = str(result).strip().lower()
    if result == "win":
        if odds > 0:
            return round(stake * (odds / 100), 2)
        return round(stake * (100 / abs(odds)), 2)
    if result == "loss":
        return round(-stake, 2)
    if result == "push":
        return 0.0
    return np.nan


def settle_parlay_profit(combined_odds, stake, result):
    return settle_profit(combined_odds, stake, result)


def clv_result(row):
    try:
        open_line = float(row.get("line"))
        close_line = float(row.get("clv_closing_line"))
    except Exception:
        return np.nan, ""
    side = str(row.get("bet_side", "")).lower()
    if side == "over":
        diff = round(close_line - open_line, 2)
        return diff, "Beat Close" if diff > 0 else ("Lost Close" if diff < 0 else "Push Close")
    if side == "under":
        diff = round(open_line - close_line, 2)
        return diff, "Beat Close" if diff > 0 else ("Lost Close" if diff < 0 else "Push Close")
    if side == "side":
        diff = round(abs(close_line) - abs(open_line), 2)
        return diff, "Beat Close" if diff > 0 else ("Lost Close" if diff < 0 else "Push Close")
    return np.nan, ""


def safe_float(x, default=0.0):
    try:
        v = float(x)
        if pd.isna(v):
            return default
        return v
    except Exception:
        return default

def ensure_columns(df, columns):
    if df is None or df.empty:
        return pd.DataFrame(columns=columns)
    out = df.copy()
    for col in columns:
        if col not in out.columns:
            out[col] = np.nan
    return out[columns]


def save_logs_to_disk():
    try:
        ensure_columns(st.session_state.bet_log, list(st.session_state.bet_log.columns)).to_csv(BET_LOG_FILE, index=False)
        ensure_columns(st.session_state.parlay_log, list(st.session_state.parlay_log.columns)).to_csv(PARLAY_LOG_FILE, index=False)
    except Exception:
        pass


def load_logs_from_disk():
    bet_cols = list(st.session_state.bet_log.columns)
    parlay_cols = list(st.session_state.parlay_log.columns)
    try:
        if BET_LOG_FILE.exists():
            st.session_state.bet_log = ensure_columns(pd.read_csv(BET_LOG_FILE), bet_cols)
    except Exception:
        st.session_state.bet_log = ensure_columns(st.session_state.bet_log, bet_cols)
    try:
        if PARLAY_LOG_FILE.exists():
            st.session_state.parlay_log = ensure_columns(pd.read_csv(PARLAY_LOG_FILE), parlay_cols)
    except Exception:
        st.session_state.parlay_log = ensure_columns(st.session_state.parlay_log, parlay_cols)
    st.session_state.auto_storage_loaded = True


def maybe_load_auto_storage():
    if not bool(st.session_state.get("auto_storage_loaded", False)):
        load_logs_from_disk()


def save_full_auto_state():
    payload = {
        "bet_log": st.session_state.bet_log.to_dict("records"),
        "parlay_log": st.session_state.parlay_log.to_dict("records"),
        "learning_state": st.session_state.learning_state,
        "launch_settings": st.session_state.launch_settings,
    }
    try:
        APP_STATE_FILE.write_text(json.dumps(payload, indent=2, default=str))
    except Exception:
        pass
    save_logs_to_disk()


def maybe_restore_full_auto_state():
    if not APP_STATE_FILE.exists():
        return
    try:
        payload = json.loads(APP_STATE_FILE.read_text())
    except Exception:
        return
    if st.session_state.bet_log.empty and payload.get("bet_log"):
        st.session_state.bet_log = ensure_columns(pd.DataFrame(payload["bet_log"]), list(st.session_state.bet_log.columns))
    if st.session_state.parlay_log.empty and payload.get("parlay_log"):
        st.session_state.parlay_log = ensure_columns(pd.DataFrame(payload["parlay_log"]), list(st.session_state.parlay_log.columns))
    if isinstance(payload.get("learning_state"), dict):
        st.session_state.learning_state = payload["learning_state"]
    if isinstance(payload.get("launch_settings"), dict):
        merged = st.session_state.launch_settings.copy()
        merged.update(payload["launch_settings"])
        st.session_state.launch_settings = merged
    save_full_auto_state()


maybe_load_auto_storage()
maybe_restore_full_auto_state()


# ---------- SAMPLE DATA ----------
def sample_data():
    rows = [
        ["NBA", "Stephen Curry", "Points Over", -115, 27.5, "DraftKings", 32.2, 4.7, 66.7, None, True, "GSW", "LAL", "GSW @ LAL"],
        ["NBA", "LeBron James", "PRA Over", -110, 38.5, "FanDuel", 43.8, 5.3, 64.8, None, True, "LAL", "GSW", "GSW @ LAL"],
        ["NBA", "", "Moneyline", -145, 0.0, "DraftKings", 0.0, 2.3, 61.5, None, True, "BOS", "MIA", "BOS @ MIA"],
        ["NBA", "", "Spread", -110, -4.5, "FanDuel", -7.2, 2.7, 58.5, None, True, "DEN", "UTA", "DEN @ UTA"],
        ["NBA", "", "Total Over", -108, 229.5, "Caesars", 235.8, 6.3, 59.7, None, True, "PHX", "DAL", "PHX @ DAL"],
        ["NHL", "Connor McDavid", "Shots Over", -120, 3.5, "DraftKings", 4.3, 0.8, 58.0, None, True, "EDM", "CGY", "EDM @ CGY"],
        ["NHL", "", "Moneyline", 120, 0.0, "BetMGM", 0.0, 3.0, 48.5, None, True, "NYR", "NJD", "NYR @ NJD"],
        ["MLB", "", "Total Under", -105, 8.5, "Caesars", 7.7, 0.8, 56.8, None, True, "NYY", "BOS", "NYY @ BOS"],
        ["MLB", "Aaron Judge", "Hits Over", -135, 1.5, "Caesars", 1.9, 0.4, 57.5, None, True, "NYY", "BOS", "NYY @ BOS"],
    ]
    return pd.DataFrame(
        rows,
        columns=["sport", "player", "market", "odds", "point", "book", "projection", "edge", "hit_pct", "score", "is_starter", "team", "opponent", "game"],
    )

# ---------- LEARNING ----------
def get_settled_log():
    log = st.session_state.bet_log.copy()
    if log.empty:
        return log
    log = to_numeric_safe(log, ["stake", "profit", "score", "adjusted_score", "multi_ai_score", "clv_diff", "ai_votes_for", "ai_consensus"])
    return log[log["result"].isin(["Win", "Loss", "Push"])].copy()


def get_settled_parlay_log():
    log = st.session_state.parlay_log.copy()
    if log.empty:
        return log
    log = to_numeric_safe(log, ["stake", "profit", "combined_odds", "avg_leg_score", "avg_leg_adjusted", "avg_leg_consensus", "legs"])
    return log[log["result"].isin(["Win", "Loss", "Push"])].copy()


def stable_score_bucket(score):
    try:
        s = float(score)
    except Exception:
        return "Unknown"
    if s < 60:
        return "<60"
    if s < 70:
        return "60-69"
    if s < 80:
        return "70-79"
    if s < 90:
        return "80-89"
    return "90+"


def update_learning_weights_from_history():
    settled = get_settled_log()
    if settled.empty or len(settled) < 8:
        return

    metrics = ["model_projection", "model_price_ev", "model_risk", "model_market", "model_history"]
    perf = {}
    for metric in metrics:
        if metric not in settled.columns:
            perf[metric] = 0.5
            continue
        vals = pd.to_numeric(settled[metric], errors="coerce").fillna(50)
        wins = (settled["result"] == "Win").astype(int)
        top_cut = vals.quantile(0.60)
        bottom_cut = vals.quantile(0.40)
        top_win = wins[vals >= top_cut].mean() if (vals >= top_cut).sum() > 0 else 0.5
        bottom_win = wins[vals <= bottom_cut].mean() if (vals <= bottom_cut).sum() > 0 else 0.5
        edge = max(0.01, (top_win - bottom_win) + 0.5)
        perf[metric] = edge

    total = sum(perf.values())
    if total <= 0:
        return
    new_weights = {k: round(v / total, 4) for k, v in perf.items()}
    old_weights = st.session_state.learning_state.get("weights", {}).copy()
    blended = {}
    for k in new_weights:
        old_val = float(old_weights.get(k, new_weights[k]))
        blended[k] = round((old_val * 0.65) + (new_weights[k] * 0.35), 4)
    norm = sum(blended.values())
    st.session_state.learning_state["weights"] = {k: round(v / norm, 4) for k, v in blended.items()}


def compute_learning_adjustments():
    settled = get_settled_log()
    defaults = {
        "market_adj": {}, "tier_adj": {}, "score_adj": {}, "global_adj": 0.0, "hot_cold": "Neutral",
        "market_type_adj": {}, "consensus_adj": {}
    }
    if settled.empty or len(settled) < 5:
        return defaults
    settled["win_flag"] = (settled["result"] == "Win").astype(int)
    settled["score_bucket"] = settled["score"].apply(stable_score_bucket)
    profit_sum = settled["profit"].fillna(0).sum()
    staked_sum = settled["stake"].fillna(0).sum()
    roi = (profit_sum / staked_sum * 100) if staked_sum > 0 else 0.0
    if roi >= 8:
        defaults["global_adj"] = 3.0
        defaults["hot_cold"] = "HOT"
    elif roi <= -8:
        defaults["global_adj"] = -3.0
        defaults["hot_cold"] = "COLD"
    for market, g in settled.groupby("market", dropna=False):
        if len(g) >= 3:
            defaults["market_adj"][market] = float(np.clip((g["win_flag"].mean() - 0.5) * 20, -4, 4))
    for tier, g in settled.groupby("tier", dropna=False):
        if len(g) >= 3:
            defaults["tier_adj"][tier] = float(np.clip((g["win_flag"].mean() - 0.5) * 16, -3, 3))
    for bucket, g in settled.groupby("score_bucket", dropna=False):
        if len(g) >= 3:
            defaults["score_adj"][bucket] = float(np.clip((g["win_flag"].mean() - 0.5) * 14, -2.5, 2.5))
    if "market_type" in settled.columns:
        for mt, g in settled.groupby("market_type", dropna=False):
            if len(g) >= 3:
                defaults["market_type_adj"][mt] = float(np.clip((g["win_flag"].mean() - 0.5) * 18, -3, 3))
    if "ai_consensus" in settled.columns:
        for c, g in settled.groupby("ai_consensus", dropna=False):
            if len(g) >= 3:
                defaults["consensus_adj"][float(c)] = float(np.clip((g["win_flag"].mean() - 0.5) * 10, -2, 2))
    return defaults


def apply_learning_layer(df):
    out = df.copy()
    learn = compute_learning_adjustments()
    out["score_bucket"] = out["score"].apply(stable_score_bucket)
    out["market_learning_adj"] = out["market"].map(learn["market_adj"]).fillna(0.0)
    out["tier_learning_adj"] = out["tier"].map(learn["tier_adj"]).fillna(0.0)
    out["score_learning_adj"] = out["score_bucket"].map(learn["score_adj"]).fillna(0.0)
    out["market_type_learning_adj"] = out["market_type"].map(learn["market_type_adj"]).fillna(0.0)
    out["consensus_learning_adj"] = out["ai_consensus"].map(learn["consensus_adj"]).fillna(0.0)
    out["global_learning_adj"] = learn["global_adj"]
    out["learning_boost"] = (
        out["market_learning_adj"] + out["tier_learning_adj"] + out["score_learning_adj"] +
        out["market_type_learning_adj"] + out["consensus_learning_adj"] + out["global_learning_adj"]
    )
    out["adjusted_score"] = np.clip(out["score"].fillna(0) + out["learning_boost"], 1, 99)
    out["learning_state"] = learn["hot_cold"]
    return out

# ---------- SPORT / MARKET ENGINE ----------
def sport_unit_multiplier(sport):
    sport = str(sport).upper()
    if sport == "NBA":
        return 1.00
    if sport == "NHL":
        return 0.85
    if sport == "MLB":
        return 0.75
    return 1.00


def sport_min_score(sport):
    sport = str(sport).upper()
    if sport == "NBA":
        return 60
    if sport == "NHL":
        return 62
    if sport == "MLB":
        return 64
    return 60


def market_min_score(market_type, sport):
    if market_type == "Player Prop":
        return sport_min_score(sport)
    if market_type == "Mainline":
        return 58 if str(sport).upper() == "NBA" else 60
    if market_type == "Spread":
        return 57 if str(sport).upper() == "NBA" else 59
    if market_type == "Total":
        return 56 if str(sport).upper() == "NBA" else 58
    return sport_min_score(sport)


def is_all_market_type(market_type):
    return market_type in ["Mainline", "Spread", "Total"]


def consensus_label(votes_for):
    votes_for = int(votes_for)
    if votes_for >= 5:
        return "5/5 Elite"
    if votes_for == 4:
        return "4/5 Strong"
    if votes_for == 3:
        return "3/5 Playable"
    return f"{votes_for}/5 Pass"


def build_engine(df):
    update_learning_weights_from_history()

    df = normalize_columns(df)
    df = to_numeric_safe(df, ["odds", "point", "projection", "edge", "hit_pct", "score", "ev_edge", "units"])

    if "sport" not in df.columns:
        if "league" in df.columns:
            df["sport"] = df["league"].astype(str).str.upper()
        else:
            df["sport"] = "NBA"

    if "line" not in df.columns and "point" in df.columns:
        df["line"] = df["point"]
    if "player" not in df.columns:
        df["player"] = ""
    if "game" not in df.columns:
        team = df.get("team", pd.Series("", index=df.index)).astype(str)
        opp = df.get("opponent", pd.Series("", index=df.index)).astype(str)
        df["game"] = np.where((team != "") & (opp != ""), team + " @ " + opp, "")
    if "bet_side" not in df.columns:
        df["bet_side"] = df["market"].apply(detect_side) if "market" in df.columns else ""
    if "market_family" not in df.columns:
        df["market_family"] = df["market"].apply(market_family) if "market" in df.columns else ""

    df["market_type"] = df.apply(lambda r: classify_market_type(r.get("market", ""), r.get("player", ""), r.get("game", "")), axis=1)
    df["is_all_market"] = df["market_type"].apply(is_all_market_type)

    if "implied_prob" not in df.columns and "odds" in df.columns:
        df["implied_prob"] = df["odds"].apply(implied_prob) * 100
    if "break_even_pct" not in df.columns and "odds" in df.columns:
        df["break_even_pct"] = df["odds"].apply(implied_prob) * 100
    if "edge" not in df.columns:
        df["edge"] = df["projection"] - df["line"] if "projection" in df.columns and "line" in df.columns else 0.0

    if "hit_pct" not in df.columns:
        df["hit_pct"] = np.nan

    prop_mask = df["market_type"] == "Player Prop"
    mainline_mask = df["market_type"] == "Mainline"
    spread_mask = df["market_type"] == "Spread"
    total_mask = df["market_type"] == "Total"

    missing = df["hit_pct"].isna()
    df.loc[missing & prop_mask, "hit_pct"] = np.clip(50 + df.loc[missing & prop_mask, "edge"].fillna(0) * 3.5, 35, 75)
    df.loc[missing & mainline_mask, "hit_pct"] = np.clip(df.loc[missing & mainline_mask, "break_even_pct"].fillna(50) + df.loc[missing & mainline_mask, "edge"].fillna(0) * 2.2, 38, 72)
    df.loc[missing & spread_mask, "hit_pct"] = np.clip(50 + df.loc[missing & spread_mask, "edge"].fillna(0) * 2.8, 40, 69)
    df.loc[missing & total_mask, "hit_pct"] = np.clip(50 + df.loc[missing & total_mask, "edge"].fillna(0) * 2.4, 40, 68)
    df["hit_pct"] = df["hit_pct"].fillna(np.clip(50 + df["edge"].fillna(0) * 2.5, 38, 70))

    if "ev_edge" not in df.columns:
        df["ev_edge"] = np.nan
    missing_ev = df["ev_edge"].isna()
    df.loc[missing_ev, "ev_edge"] = df.loc[missing_ev].apply(
        lambda r: calc_ev(r.get("hit_pct"), r.get("odds")) if pd.notna(r.get("hit_pct")) and pd.notna(r.get("odds")) else np.nan,
        axis=1,
    )

    if "model_projection" not in df.columns:
        df["model_projection"] = 50.0
        df.loc[prop_mask, "model_projection"] = np.clip(50 + df.loc[prop_mask, "edge"].fillna(0) * 8, 0, 100)
        df.loc[mainline_mask, "model_projection"] = np.clip(50 + df.loc[mainline_mask, "edge"].fillna(0) * 5.5, 0, 100)
        df.loc[spread_mask, "model_projection"] = np.clip(50 + df.loc[spread_mask, "edge"].fillna(0) * 6.5, 0, 100)
        df.loc[total_mask, "model_projection"] = np.clip(50 + df.loc[total_mask, "edge"].fillna(0) * 5.8, 0, 100)

    if "model_price_ev" not in df.columns:
        df["model_price_ev"] = np.clip(50 + df["ev_edge"].fillna(0) * 1.8, 0, 100)

    if "model_risk" not in df.columns:
        base_risk = np.where(df["odds"].fillna(0) >= 120, 48, np.where(df["odds"].fillna(0) <= -170, 68, 58))
        starter_bonus = np.where(df.get("is_starter", pd.Series(False, index=df.index)).astype(str).str.lower().isin(["true", "1", "yes"]), 6, 0)
        market_bonus = np.where(mainline_mask, 5, np.where(spread_mask, 4, np.where(total_mask, 3, 0)))
        df["model_risk"] = np.clip(base_risk + starter_bonus + market_bonus, 0, 100)

    if "model_market" not in df.columns:
        df["model_market"] = np.clip(50 + (df["hit_pct"].fillna(50) - df["break_even_pct"].fillna(50)) * 2.0, 0, 100)

    if "model_history" not in df.columns:
        base_history = np.select([df["score"].fillna(0) >= 84, df["score"].fillna(0) >= 72, df["score"].fillna(0) >= 60], [72, 62, 54], default=45)
        type_bonus = np.where(mainline_mask, 4, np.where(spread_mask, 3, np.where(total_mask, 2, 0)))
        df["model_history"] = np.clip(base_history + type_bonus, 0, 100)

    weights = st.session_state.learning_state["weights"]
    df["multi_ai_score"] = (
        df["model_projection"].fillna(50) * weights["model_projection"] +
        df["model_price_ev"].fillna(50) * weights["model_price_ev"] +
        df["model_risk"].fillna(50) * weights["model_risk"] +
        df["model_market"].fillna(50) * weights["model_market"] +
        df["model_history"].fillna(50) * weights["model_history"]
    )

    vote_thresholds = {
        "model_projection": 56,
        "model_price_ev": 54,
        "model_risk": 55,
        "model_market": 55,
        "model_history": 54,
    }
    vote_cols = []
    for metric, thresh in vote_thresholds.items():
        col = f"vote_{metric}"
        vote_cols.append(col)
        df[col] = (pd.to_numeric(df[metric], errors="coerce").fillna(50) >= thresh).astype(int)
    df["ai_votes_for"] = df[vote_cols].sum(axis=1)
    df["ai_consensus"] = df["ai_votes_for"].astype(int)
    df["ai_consensus_label"] = df["ai_votes_for"].apply(consensus_label)

    if "score" not in df.columns:
        df["score"] = np.nan
    need_score = df["score"].isna()
    edge_component = np.clip(df["edge"].fillna(0) * 6, -10, 35)
    hit_component = np.clip((df["hit_pct"].fillna(50) - 50) * 1.5, -10, 35)
    ev_component = np.clip(df["ev_edge"].fillna(0) * 0.8, -10, 30)
    starter_bonus = np.where(df.get("is_starter", pd.Series(False, index=df.index)).astype(str).str.lower().isin(["true", "1", "yes"]), 4, 0)
    consensus_bonus = np.clip((df["ai_votes_for"].fillna(0) - 2) * 4, -6, 12)
    market_bonus = np.where(mainline_mask, 4, np.where(spread_mask, 3, np.where(total_mask, 3, 0)))
    df.loc[need_score, "score"] = np.clip(
        0.55 * df.loc[need_score, "multi_ai_score"].fillna(50)
        + 20 + edge_component[need_score] + hit_component[need_score] + ev_component[need_score] +
        starter_bonus[need_score] + consensus_bonus[need_score] + market_bonus[need_score],
        1, 99,
    )

    df["tier"] = np.select([df["score"] >= 84, df["score"] >= 72, df["score"] >= 60], ["Tier 1", "Tier 2", "Tier 3"], default="Pass")

    if "units" not in df.columns:
        df["units"] = np.nan
    need_units = df["units"].isna()
    df.loc[need_units & (df["score"] >= 84), "units"] = 1.0
    df.loc[need_units & (df["score"] >= 72) & (df["score"] < 84), "units"] = 0.5
    df.loc[need_units & (df["score"] >= 60) & (df["score"] < 72), "units"] = 0.25
    df.loc[need_units & (df["score"] < 60), "units"] = 0.0

    df["sport_unit_mult"] = df["sport"].apply(sport_unit_multiplier)
    df["sport_min_score"] = df["sport"].apply(sport_min_score)
    df["market_min_score"] = df.apply(lambda r: market_min_score(r.get("market_type"), r.get("sport")), axis=1)
    df["units"] = (df["units"].fillna(0) * df["sport_unit_mult"]).round(2)
    return df


def filtered_launch_ready(df):
    out = build_engine(df)
    out = apply_learning_layer(out)
    out = apply_results_clv_intelligence(out)
    out = out[out["adjusted_score"] >= out["market_min_score"]].copy()
    return out


def best_bets(df):
    out = df.copy()
    out = out[out["units"].fillna(0) > 0].copy()
    sort_cols = [c for c in ["selection_score", "adjusted_score", "ai_consensus", "multi_ai_score", "score", "ev_edge"] if c in out.columns]
    return out.sort_values(sort_cols, ascending=False)


def high_probability_singles(df):
    settings = st.session_state.launch_settings
    adaptive = adaptive_single_thresholds()
    out = best_bets(df)
    out = out[out["market_type"].isin(["Mainline", "Spread", "Total"])].copy()
    out = out[out["ai_consensus"] >= int(adaptive["min_consensus"])]
    score_col = "selection_score" if "selection_score" in out.columns else "adjusted_score"
    out = out[out[score_col] >= float(adaptive["min_confidence"])]
    out = out[out["odds"].fillna(0).between(float(settings["singles_min_odds"]), float(settings["singles_max_odds"]))]
    return out

# ---------- SLIP / RULES ----------
def recommended_unit_multiplier(risk_mode, bankroll, drawdown_pct, roi_pct):
    base = {"Conservative": 0.75, "Balanced": 1.00, "Aggressive": 1.25}.get(risk_mode, 1.0)
    bankroll_factor = 0.75 if bankroll < 100 else (1.10 if bankroll >= 500 else 1.0)
    drawdown_factor = 0.70 if drawdown_pct >= 15 else (0.85 if drawdown_pct >= 8 else 1.0)
    performance_factor = 1.10 if roi_pct >= 8 else (0.85 if roi_pct <= -8 else 1.0)
    return round(base * bankroll_factor * drawdown_factor * performance_factor, 2)


def suggested_stake_from_units(base_units, bankroll, risk_mode, drawdown_pct, roi_pct):
    try:
        base_units = float(base_units)
    except Exception:
        base_units = 0.0
    unit_pct = {"Conservative": 0.01, "Balanced": 0.015, "Aggressive": 0.02}.get(risk_mode, 0.015)
    mult = recommended_unit_multiplier(risk_mode, bankroll, drawdown_pct, roi_pct)
    return round(max(1.0, bankroll * unit_pct * base_units * mult), 2)


def slip_key(row):
    return f"{row.get('sport', '')}|{row.get('player', '')}|{row.get('market', '')}|{row.get('book', '')}|{row.get('line', '')}"


def add_to_slip(row, stake, bankroll, risk_mode):
    key = slip_key(row)
    current = [x for x in st.session_state.bet_slip if x["slip_key"] != key]
    item = {
        "slip_key": key,
        "sport": row.get("sport", ""),
        "player": row.get("player", ""),
        "market": row.get("market", ""),
        "book": row.get("book", ""),
        "odds": row.get("odds", np.nan),
        "line": row.get("line", np.nan),
        "stake": round(float(stake), 2),
        "score": row.get("score", np.nan),
        "adjusted_score": row.get("adjusted_score", np.nan),
        "tier": row.get("tier", ""),
        "units": row.get("units", np.nan),
        "game": row.get("game", ""),
        "bet_side": row.get("bet_side", ""),
        "market_type": row.get("market_type", ""),
        "risk_mode": risk_mode,
        "bankroll_snapshot": bankroll,
        "model_projection": row.get("model_projection", np.nan),
        "model_price_ev": row.get("model_price_ev", np.nan),
        "model_risk": row.get("model_risk", np.nan),
        "model_market": row.get("model_market", np.nan),
        "model_history": row.get("model_history", np.nan),
        "multi_ai_score": row.get("multi_ai_score", np.nan),
        "ai_votes_for": row.get("ai_votes_for", np.nan),
        "ai_consensus": row.get("ai_consensus", np.nan),
    }
    current.append(item)
    st.session_state.bet_slip = current


def remove_from_slip(slip_key_value):
    st.session_state.bet_slip = [x for x in st.session_state.bet_slip if x["slip_key"] != slip_key_value]


def clear_slip():
    st.session_state.bet_slip = []


def clear_ai_parlays():
    st.session_state.ai_parlay_slips = []


def slip_summary():
    slip = pd.DataFrame(st.session_state.bet_slip)
    if slip.empty:
        return {"bets": 0, "stake": 0.0, "games": 0, "players": 0, "sports": 0, "same_game_extra": 0, "same_player_extra": 0}
    game_counts = slip["game"].value_counts()
    player_counts = slip["player"].replace("", np.nan).dropna().value_counts()
    return {
        "bets": len(slip),
        "stake": round(float(pd.to_numeric(slip["stake"], errors="coerce").fillna(0).sum()), 2),
        "games": int(slip["game"].nunique()),
        "players": int(slip["player"].replace("", np.nan).dropna().nunique()),
        "sports": int(slip["sport"].nunique()),
        "same_game_extra": int(sum(max(0, x - 1) for x in game_counts)),
        "same_player_extra": int(sum(max(0, x - 1) for x in player_counts)) if len(player_counts) else 0,
    }


def slip_risk_message(summary):
    msgs = []
    if summary["same_game_extra"] >= 2:
        msgs.append("High same-game exposure")
    elif summary["same_game_extra"] == 1:
        msgs.append("Moderate same-game overlap")
    if summary["same_player_extra"] >= 1:
        msgs.append("Player overlap detected")
    if summary["bets"] >= 6:
        msgs.append("Large slip size")
    return " | ".join(msgs) if msgs else "Balanced exposure"


def daily_log_df():
    log = st.session_state.bet_log.copy()
    if log.empty:
        return log
    if "bet_date" in log.columns:
        return log
    log["bet_date"] = pd.to_datetime(log["added_at"], errors="coerce").dt.date.astype(str)
    return log


def today_counts_and_exposure():
    log = daily_log_df()
    parlay_log = st.session_state.parlay_log.copy()
    total_bets = 0
    total_stake = 0.0
    today_str = str(date.today())
    if not log.empty:
        today_log = log[log["bet_date"].astype(str) == today_str].copy()
        total_bets += len(today_log)
        total_stake += float(pd.to_numeric(today_log["stake"], errors="coerce").fillna(0).sum())
    if not parlay_log.empty:
        today_parlay = parlay_log[parlay_log["bet_date"].astype(str) == today_str].copy()
        total_bets += len(today_parlay)
        total_stake += float(pd.to_numeric(today_parlay["stake"], errors="coerce").fillna(0).sum())
    return total_bets, round(total_stake, 2)


def can_add_slip_item(row, stake):
    settings = st.session_state.launch_settings
    current = pd.DataFrame(st.session_state.bet_slip)
    today_bets, today_stake = today_counts_and_exposure()
    slip_bets = len(current)
    slip_stake = float(pd.to_numeric(current["stake"], errors="coerce").fillna(0).sum()) if len(current) else 0.0

    projected_bets = today_bets + slip_bets + 1
    projected_stake = today_stake + slip_stake + float(stake)

    if projected_bets > int(settings["max_bets_per_day"]):
        return False, f"Blocked: max bets per day is {settings['max_bets_per_day']}."
    if projected_stake > float(settings["max_daily_exposure"]):
        return False, f"Blocked: max daily exposure is ${float(settings['max_daily_exposure']):.2f}."
    if float(row.get("adjusted_score", 0)) < float(settings["min_adjusted_score"]):
        return False, f"Blocked: adjusted score below launch minimum of {settings['min_adjusted_score']}."
    return True, "OK"


def existing_single_fingerprints():
    log = st.session_state.bet_log.copy()
    if log.empty:
        return set()
    fingerprints = set()
    for _, row in log.iterrows():
        fingerprints.add(f"{row.get('sport', '')}|{row.get('player', '')}|{row.get('market', '')}|{row.get('book', '')}|{row.get('line', '')}")
    return fingerprints


def is_duplicate_single_in_tracker(row):
    return slip_key(row) in existing_single_fingerprints()


def confirm_slip_to_tracker(mode):
    count = 0
    for item in st.session_state.bet_slip:
        add_bet_to_log(item, item["stake"], item["risk_mode"], item["bankroll_snapshot"], mode)
        count += 1
    clear_slip()
    return count

# ---------- AI PARLAY OPTIMIZATION ENGINE ----------
def parlay_leg_key(row):
    return slip_key(row)


def normalized_team_token(row):
    game = str(row.get("game", "")).strip().upper()
    team = str(row.get("team", "")).strip().upper()
    if team:
        return team
    if "@" in game:
        return game.replace(" ", "")
    return game


def candidate_parlay_pool(df):
    settings = st.session_state.launch_settings
    out = best_bets(df)
    out = out[out["market_type"].isin(["Mainline", "Spread", "Total"])].copy()
    threshold_col = "selection_score" if "selection_score" in out.columns else "adjusted_score"
    out = out[out[threshold_col] >= float(settings["parlay_min_leg_adjusted"])]
    out = out[out["ai_consensus"] >= int(settings["parlay_min_leg_consensus"])]
    out = out[out["odds"].notna()].copy()
    out["leg_key"] = out.apply(lambda r: parlay_leg_key(r), axis=1)
    out["team_token"] = out.apply(lambda r: normalized_team_token(r), axis=1)
    out["market_family_norm"] = out["market_family"].astype(str).str.lower()
    out = out.sort_values(
        ["selection_score", "adjusted_score", "ai_consensus", "multi_ai_score", "ev_edge", "hit_pct"],
        ascending=False
    ).head(int(settings.get("parlay_pool_size", 16)))
    return out.reset_index(drop=True)


def parlay_overlap_penalty(combo_df):
    same_game_overlap = int(combo_df["game"].duplicated().sum()) if "game" in combo_df.columns else 0
    same_team_overlap = int(combo_df["team_token"].astype(str).duplicated().sum()) if "team_token" in combo_df.columns else 0
    return same_game_overlap, same_team_overlap


def combo_has_direct_conflict(combo_df):
    combo = combo_df.copy()
    if combo.empty:
        return False

    # opposing totals in same game
    for game, g in combo.groupby("game", dropna=False):
        if len(g) <= 1:
            continue
        total_sides = set(g[g["market_type"] == "Total"]["bet_side"].astype(str).str.lower().tolist())
        if "over" in total_sides and "under" in total_sides:
            return True

    # multiple same market family in same game increases bad overlap
    fam_counts = combo.groupby(["game", "market_family_norm"], dropna=False).size()
    if (fam_counts > 1).any():
        return True

    return False


def correlation_penalty(combo_df):
    penalty = 0.0
    notes = []

    same_game_overlap, same_team_overlap = parlay_overlap_penalty(combo_df)
    if same_game_overlap > 0:
        penalty += same_game_overlap * 10
        notes.append("same-game overlap")

    if same_team_overlap > 0:
        penalty += same_team_overlap * 4
        notes.append("same-team reuse")

    combo = combo_df.copy()
    if combo_has_direct_conflict(combo):
        penalty += 18
        notes.append("direct conflict")

    for game, g in combo.groupby("game", dropna=False):
        if len(g) <= 1:
            continue
        market_types = set(g["market_type"].astype(str).tolist())
        if "Spread" in market_types and "Total" in market_types:
            penalty += 7
            notes.append("spread-total correlation")
        if "Mainline" in market_types and "Spread" in market_types:
            penalty += 9
            notes.append("mainline-spread correlation")
        if "Mainline" in market_types and "Total" in market_types:
            penalty += 5
            notes.append("mainline-total correlation")

    return round(penalty, 2), ", ".join(sorted(set(notes))) if notes else "Clean"


def parlay_grade(score):
    if score >= 94:
        return "A+"
    if score >= 90:
        return "A"
    if score >= 86:
        return "A-"
    if score >= 82:
        return "B+"
    if score >= 78:
        return "B"
    if score >= 74:
        return "B-"
    return "C"


def parlay_profile(legs, combined_odds):
    if legs == 2 and combined_odds <= 350:
        return "Core"
    if legs == 3 and combined_odds <= 650:
        return "Balanced"
    return "Upside"


def estimate_parlay_leg_hit_prob(row):
    hp = safe_float(row.get("hit_pct"), 50.0) / 100.0
    adj = safe_float(row.get("adjusted_score"), 70.0)
    consensus = safe_float(row.get("ai_consensus"), 3.0)
    blend = (hp * 0.70) + ((adj / 100.0) * 0.20) + ((consensus / 5.0) * 0.10)
    return float(np.clip(blend, 0.35, 0.80))


def estimate_parlay_success(combo_df):
    probs = [estimate_parlay_leg_hit_prob(r) for _, r in combo_df.iterrows()]
    if not probs:
        return 0.0
    combined = float(np.prod(probs))
    penalty, _ = correlation_penalty(combo_df)
    combined *= max(0.55, 1 - (penalty / 100.0))
    return float(np.clip(combined, 0.01, 0.60))


def estimate_parlay_roi_pct(combo_df, combined_odds):
    p = estimate_parlay_success(combo_df)
    dec = american_to_decimal(combined_odds)
    if pd.isna(dec):
        return 0.0
    roi = ((p * dec) - 1) * 100
    return round(float(roi), 2)


def smart_parlay_stake(combo_df, bankroll, risk_mode, drawdown_pct, roi_pct_input, expected_roi_pct, parlay_rank, is_best_slip=False):
    avg_units = float(pd.to_numeric(combo_df["units"], errors="coerce").fillna(0).mean()) if len(combo_df) else 0.25
    avg_adj = float(pd.to_numeric(combo_df["adjusted_score"], errors="coerce").fillna(0).mean()) if len(combo_df) else 75
    avg_consensus = float(pd.to_numeric(combo_df["ai_consensus"], errors="coerce").fillna(0).mean()) if len(combo_df) else 4

    base_units = 0.22 if len(combo_df) == 3 else 0.30
    quality_boost = 0.0
    if avg_adj >= 92:
        quality_boost += 0.10
    elif avg_adj >= 86:
        quality_boost += 0.06
    if avg_consensus >= 4.6:
        quality_boost += 0.08
    elif avg_consensus >= 4.0:
        quality_boost += 0.04
    if expected_roi_pct >= 18:
        quality_boost += 0.08
    elif expected_roi_pct >= 10:
        quality_boost += 0.04

    rank_boost = 0.08 if is_best_slip else (0.04 if parlay_rank <= 3 else 0.0)
    risk_penalty = 0.05 if len(combo_df) >= 3 else 0.0

    final_units = max(0.15, base_units + (avg_units * 0.08) + quality_boost + rank_boost - risk_penalty)
    return suggested_stake_from_units(final_units, bankroll, risk_mode, drawdown_pct, roi_pct_input)


def build_portfolio_plan(final_slips, bankroll, risk_mode, drawdown_pct, roi_pct_input):
    settings = st.session_state.launch_settings
    if not final_slips:
        return final_slips

    max_total_pct = safe_float(settings.get("portfolio_max_total_pct", 0.025), 0.025)
    best_share = safe_float(settings.get("portfolio_best_share", 0.55), 0.55)
    support_share = safe_float(settings.get("portfolio_support_share", 0.45), 0.45)
    total_budget = max(3.0, round(float(bankroll) * max_total_pct, 2))

    best_slips = [s for s in final_slips if s.get("is_best")]
    support_slips = [s for s in final_slips if not s.get("is_best")]

    if best_slips:
        best = best_slips[0]
        best_target = round(total_budget * best_share, 2)
        best["portfolio_share"] = round(best_share * 100, 1)
        best["portfolio_target_stake"] = best_target

    if support_slips:
        support_budget = round(total_budget * support_share, 2)
        raw_weights = []
        for slip in support_slips:
            weight = max(0.1, safe_float(slip.get("rank_score"), 75.0) / 100.0)
            weight *= max(0.2, 1 - (safe_float(slip.get("duplication_penalty"), 0.0) / 15.0))
            weight *= max(0.2, 1 - (safe_float(slip.get("correlation_penalty"), 0.0) / 20.0))
            raw_weights.append(weight)
        total_weight = sum(raw_weights) or 1.0
        for slip, weight in zip(support_slips, raw_weights):
            share = support_share * (weight / total_weight)
            slip["portfolio_share"] = round(share * 100, 1)
            slip["portfolio_target_stake"] = round(support_budget * (weight / total_weight), 2)

    for slip in final_slips:
        combo_df = pd.DataFrame(slip["legs_rows"])
        base_stake = smart_parlay_stake(
            combo_df,
            bankroll,
            risk_mode,
            drawdown_pct,
            roi_pct_input,
            slip["expected_roi_pct"],
            slip["parlay_rank"],
            is_best_slip=slip.get("is_best", False),
        )
        target_stake = safe_float(slip.get("portfolio_target_stake"), base_stake)
        slip["stake"] = round(max(1.0, min(base_stake, target_stake) if target_stake > 0 else base_stake), 2)
    return final_slips


def parlay_odds_bucket(combined_odds):
    odds = safe_float(combined_odds, 0.0)
    if odds < 300:
        return "+200 to +299"
    if odds < 500:
        return "+300 to +499"
    if odds < 800:
        return "+500 to +799"
    return "+800+"


def adaptive_parlay_history_summary():
    settings = st.session_state.launch_settings
    settled = get_settled_parlay_log().copy()
    default = {
        "samples": 0,
        "legs_roi": {},
        "profile_roi": {},
        "odds_bucket_roi": {},
        "consensus_roi": {},
        "best_legs": None,
        "best_profile": None,
        "best_odds_bucket": None,
        "mode": "Warm-up",
        "confidence": "Low",
        "notes": ["Settle more parlays to activate adaptive bias."],
    }
    if settled.empty:
        return default

    settled["stake"] = pd.to_numeric(settled["stake"], errors="coerce").fillna(0)
    settled["profit"] = pd.to_numeric(settled["profit"], errors="coerce").fillna(0)
    settled["legs"] = pd.to_numeric(settled["legs"], errors="coerce").fillna(0).astype(int)
    settled["odds_bucket"] = settled["combined_odds"].apply(parlay_odds_bucket)
    settled["slip_profile"] = settled.get("slip_profile", pd.Series("Unknown", index=settled.index)).fillna("Unknown")
    settled["consensus_label"] = settled.get("consensus_label", pd.Series("Unknown", index=settled.index)).fillna("Unknown")

    def build_roi_map(df, col):
        out = {}
        for key, g in df.groupby(col, dropna=False):
            stake = g["stake"].sum()
            roi = (g["profit"].sum() / stake * 100) if stake > 0 else 0.0
            out[str(key)] = {
                "samples": int(len(g)),
                "roi": round(float(roi), 2),
                "win_rate": round(float((g["result"] == "Win").mean() * 100), 2),
            }
        return out

    legs_roi = build_roi_map(settled, "legs")
    profile_roi = build_roi_map(settled, "slip_profile")
    odds_bucket_roi = build_roi_map(settled, "odds_bucket")
    consensus_roi = build_roi_map(settled, "consensus_label")

    min_samples = int(settings.get("adaptive_min_samples", 5))

    def best_key(d):
        eligible = {k: v for k, v in d.items() if int(v.get("samples", 0)) >= min_samples}
        if not eligible:
            return None
        return max(eligible.items(), key=lambda kv: (kv[1].get("roi", 0.0), kv[1].get("win_rate", 0.0)))[0]

    best_legs = best_key(legs_roi)
    best_profile = best_key(profile_roi)
    best_odds_bucket = best_key(odds_bucket_roi)

    total_stake = settled["stake"].sum()
    total_roi = (settled["profit"].sum() / total_stake * 100) if total_stake > 0 else 0.0
    if len(settled) >= 20:
        confidence = "High"
    elif len(settled) >= 10:
        confidence = "Medium"
    else:
        confidence = "Low"

    notes = []
    if best_legs is not None:
        notes.append(f"Best leg count so far: {best_legs}-leg")
    if best_profile is not None:
        notes.append(f"Best profile so far: {best_profile}")
    if best_odds_bucket is not None:
        notes.append(f"Best odds range so far: {best_odds_bucket}")
    if not notes:
        notes.append("Adaptive engine is collecting evidence.")

    mode = "Neutral"
    if total_roi >= 10:
        mode = "Press edge"
    elif total_roi <= -10:
        mode = "Tighten risk"

    return {
        "samples": int(len(settled)),
        "legs_roi": legs_roi,
        "profile_roi": profile_roi,
        "odds_bucket_roi": odds_bucket_roi,
        "consensus_roi": consensus_roi,
        "best_legs": best_legs,
        "best_profile": best_profile,
        "best_odds_bucket": best_odds_bucket,
        "mode": mode,
        "confidence": confidence,
        "notes": notes,
        "total_roi": round(float(total_roi), 2),
    }


def adaptive_rank_modifier(combo_df, slip_profile, combined_odds, consensus_text):
    settings = st.session_state.launch_settings
    if not bool(settings.get("adaptive_auto_mode", True)):
        return 0.0, []

    summary = adaptive_parlay_history_summary()
    if int(summary.get("samples", 0)) < int(settings.get("adaptive_min_samples", 5)):
        return 0.0, ["adaptive warm-up"]

    weight = safe_float(settings.get("adaptive_weight", 0.18), 0.18)
    notes = []
    modifier = 0.0
    legs_key = str(len(combo_df))
    profile_key = str(slip_profile)
    odds_key = parlay_odds_bucket(combined_odds)
    consensus_key = str(consensus_text)

    legs_map = summary.get("legs_roi", {})
    profile_map = summary.get("profile_roi", {})
    odds_map = summary.get("odds_bucket_roi", {})
    consensus_map = summary.get("consensus_roi", {})

    def apply_from_map(mapping, key, scale, label):
        nonlocal modifier
        item = mapping.get(str(key))
        if not item:
            return
        if int(item.get("samples", 0)) < int(settings.get("adaptive_min_samples", 5)):
            return
        roi = safe_float(item.get("roi", 0.0), 0.0)
        adj = float(np.clip(roi * scale * weight, -8, 8))
        modifier += adj
        if adj > 0.2:
            notes.append(f"{label} tailwind")
        elif adj < -0.2:
            notes.append(f"{label} headwind")

    apply_from_map(legs_map, legs_key, 0.20, f"{legs_key}-leg")
    apply_from_map(profile_map, profile_key, 0.18, profile_key)
    apply_from_map(odds_map, odds_key, 0.16, odds_key)
    apply_from_map(consensus_map, consensus_key, 0.12, consensus_key)

    if str(summary.get("best_legs")) == legs_key:
        modifier += 1.25 * weight * 5
        notes.append("best leg-count match")
    if str(summary.get("best_profile")) == profile_key:
        modifier += 1.10 * weight * 5
        notes.append("best profile match")
    if str(summary.get("best_odds_bucket")) == odds_key:
        modifier += 0.95 * weight * 5
        notes.append("best odds-band match")

    return round(float(np.clip(modifier, -12, 12)), 2), notes


def singles_odds_bucket(odds):
    odds = safe_float(odds, 0.0)
    if odds <= -170:
        return "-170 or shorter"
    if odds <= -110:
        return "-169 to -110"
    if odds <= -101:
        return "-109 to -101"
    if odds < 100:
        return "Even-ish"
    if odds <= 150:
        return "+100 to +150"
    return "+151+"


def settled_singles_intelligence_summary():
    settings = st.session_state.launch_settings
    settled = get_settled_log().copy()
    default = {
        "samples": 0,
        "overall_roi": 0.0,
        "overall_clv": 0.0,
        "sport_market_roi": {},
        "consensus_roi": {},
        "odds_roi": {},
        "best_sport_market": None,
        "best_consensus": None,
        "best_odds_bucket": None,
        "mode": "Warm-up",
        "notes": ["Settle more singles to activate results and CLV intelligence."],
    }
    if settled.empty:
        return default

    settled["stake"] = pd.to_numeric(settled["stake"], errors="coerce").fillna(0)
    settled["profit"] = pd.to_numeric(settled["profit"], errors="coerce").fillna(0)
    settled["ai_consensus"] = pd.to_numeric(settled.get("ai_consensus"), errors="coerce").fillna(0).astype(int)
    settled["clv_diff"] = pd.to_numeric(settled.get("clv_diff"), errors="coerce")
    settled["sport_market"] = settled["sport"].astype(str) + " | " + settled["market_type"].astype(str)
    settled["odds_bucket"] = settled["odds"].apply(singles_odds_bucket)
    settled["consensus_bucket"] = settled["ai_consensus"].astype(str) + "/5"

    def build_map(col):
        out = {}
        for key, g in settled.groupby(col, dropna=False):
            stake = g["stake"].sum()
            roi = (g["profit"].sum() / stake * 100) if stake > 0 else 0.0
            out[str(key)] = {
                "samples": int(len(g)),
                "roi": round(float(roi), 2),
                "win_rate": round(float((g["result"] == "Win").mean() * 100), 2),
                "avg_clv": round(float(pd.to_numeric(g.get("clv_diff"), errors="coerce").mean()), 2) if "clv_diff" in g.columns else 0.0,
                "beat_close_rate": round(float((g.get("clv_win", pd.Series(index=g.index)).astype(str) == "Beat Close").mean() * 100), 2) if "clv_win" in g.columns else 0.0,
            }
        return out

    sport_market_roi = build_map("sport_market")
    consensus_roi = build_map("consensus_bucket")
    odds_roi = build_map("odds_bucket")
    min_samples = int(settings.get("results_clv_min_samples", 5))

    def best_key(d):
        eligible = {k: v for k, v in d.items() if int(v.get("samples", 0)) >= min_samples}
        if not eligible:
            return None
        return max(eligible.items(), key=lambda kv: (kv[1].get("roi", 0.0), kv[1].get("beat_close_rate", 0.0), kv[1].get("avg_clv", 0.0)))[0]

    total_stake = settled["stake"].sum()
    overall_roi = (settled["profit"].sum() / total_stake * 100) if total_stake > 0 else 0.0
    overall_clv = float(pd.to_numeric(settled.get("clv_diff"), errors="coerce").fillna(0).mean()) if "clv_diff" in settled.columns else 0.0
    notes = []
    if best_key(sport_market_roi):
        notes.append(f"Best single profile so far: {best_key(sport_market_roi)}")
    if best_key(consensus_roi):
        notes.append(f"Best consensus so far: {best_key(consensus_roi)}")
    if best_key(odds_roi):
        notes.append(f"Best odds band so far: {best_key(odds_roi)}")
    if overall_clv > 0:
        notes.append("Singles are beating the close overall.")
    elif overall_clv < 0:
        notes.append("Singles are losing the close overall.")
    if not notes:
        notes.append("Results + CLV engine is collecting evidence.")

    mode = "Neutral"
    if overall_roi >= 8 and overall_clv >= 0:
        mode = "Press proven singles"
    elif overall_roi <= -8 or overall_clv <= -0.5:
        mode = "Tighten singles"

    return {
        "samples": int(len(settled)),
        "overall_roi": round(float(overall_roi), 2),
        "overall_clv": round(float(overall_clv), 2),
        "sport_market_roi": sport_market_roi,
        "consensus_roi": consensus_roi,
        "odds_roi": odds_roi,
        "best_sport_market": best_key(sport_market_roi),
        "best_consensus": best_key(consensus_roi),
        "best_odds_bucket": best_key(odds_roi),
        "mode": mode,
        "notes": notes,
    }


def results_clv_rank_modifier(row):
    settings = st.session_state.launch_settings
    if not bool(settings.get("results_clv_auto_mode", True)):
        return 0.0, []
    summary = settled_singles_intelligence_summary()
    min_samples = int(settings.get("results_clv_min_samples", 5))
    if int(summary.get("samples", 0)) < min_samples:
        return 0.0, ["results warm-up"]

    weight = safe_float(settings.get("results_clv_weight", 0.16), 0.16)
    modifier = 0.0
    notes = []
    sport_market = f"{row.get('sport', '')} | {row.get('market_type', '')}"
    consensus_bucket = f"{int(safe_float(row.get('ai_consensus'), 0))}/5"
    odds_bucket = singles_odds_bucket(row.get("odds"))

    maps = [
        (summary.get("sport_market_roi", {}), sport_market, 0.18, sport_market),
        (summary.get("consensus_roi", {}), consensus_bucket, 0.16, consensus_bucket),
        (summary.get("odds_roi", {}), odds_bucket, 0.14, odds_bucket),
    ]
    for mapping, key, scale, label in maps:
        item = mapping.get(str(key))
        if not item or int(item.get("samples", 0)) < min_samples:
            continue
        roi = safe_float(item.get("roi", 0.0), 0.0)
        clv = safe_float(item.get("avg_clv", 0.0), 0.0)
        beat = safe_float(item.get("beat_close_rate", 0.0), 50.0)
        adj = np.clip((roi * scale + clv * 1.5 + (beat - 50) * 0.05) * weight, -6, 6)
        modifier += float(adj)
        if adj > 0.2:
            notes.append(f"{label} tailwind")
        elif adj < -0.2:
            notes.append(f"{label} headwind")

    if sport_market == str(summary.get("best_sport_market")):
        modifier += 0.9
        notes.append("best single profile")
    if consensus_bucket == str(summary.get("best_consensus")):
        modifier += 0.7
        notes.append("best consensus")
    if odds_bucket == str(summary.get("best_odds_bucket")):
        modifier += 0.55
        notes.append("best odds band")

    if safe_float(summary.get("overall_clv"), 0.0) <= -0.5:
        modifier -= 0.6
        notes.append("poor recent CLV")
    elif safe_float(summary.get("overall_clv"), 0.0) >= 0.5:
        modifier += 0.6
        notes.append("strong recent CLV")

    return round(float(np.clip(modifier, -8, 8)), 2), notes


def adaptive_single_thresholds():
    settings = st.session_state.launch_settings
    base_conf = float(settings.get("singles_min_confidence", 70))
    base_cons = int(settings.get("singles_min_consensus", 3))
    summary = settled_singles_intelligence_summary()
    min_samples = int(settings.get("results_clv_min_samples", 5))
    out = {
        "min_confidence": base_conf,
        "min_consensus": base_cons,
        "notes": ["Base singles filters in use."],
    }
    if not bool(settings.get("results_clv_auto_mode", True)) or int(summary.get("samples", 0)) < min_samples:
        return out

    roi = safe_float(summary.get("overall_roi"), 0.0)
    clv = safe_float(summary.get("overall_clv"), 0.0)
    notes = []
    conf_adj = 0
    cons_adj = 0
    if roi <= -8 or clv <= -0.5:
        conf_adj += 3
        if base_cons < 5:
            cons_adj += 1
        notes.append("Tightened singles due to weak results/CLV.")
    elif roi >= 8 and clv >= 0.3:
        conf_adj -= 2
        notes.append("Slightly loosened singles due to proven results + CLV.")

    out["min_confidence"] = float(np.clip(base_conf + conf_adj, 55, 95))
    out["min_consensus"] = int(np.clip(base_cons + cons_adj, 3, 5))
    out["notes"] = notes or ["Singles filters aligned with recent results."]
    return out


def apply_results_clv_intelligence(df):
    out = df.copy()
    mods = out.apply(lambda r: results_clv_rank_modifier(r), axis=1)
    out["results_clv_edge"] = [m[0] for m in mods]
    out["results_clv_notes"] = [", ".join(m[1]) if m[1] else "Neutral" for m in mods]
    out["selection_score"] = np.clip(out["adjusted_score"].fillna(0) + out["results_clv_edge"].fillna(0), 1, 99)
    return out


def existing_parlay_fingerprints():
    log = st.session_state.parlay_log.copy()
    if log.empty or "leg_keys_json" not in log.columns:
        return set()
    fingerprints = set()
    for _, row in log.iterrows():
        raw = row.get("leg_keys_json", "[]")
        try:
            keys = tuple(sorted(json.loads(raw)))
            if keys:
                fingerprints.add(keys)
        except Exception:
            continue
    return fingerprints


def is_duplicate_parlay_in_tracker(slip):
    try:
        keys = tuple(sorted(json.loads(slip.get("leg_keys_json", "[]"))))
    except Exception:
        return False
    if not keys:
        return False
    return keys in existing_parlay_fingerprints()


def optimize_ai_parlay_slips(df, bankroll, risk_mode, drawdown_pct, roi_pct):
    settings = st.session_state.launch_settings
    pool = candidate_parlay_pool(df)
    slips = []
    if len(pool) < 2:
        return slips

    max_legs = int(settings["parlay_max_legs"])
    allow_same_game = bool(settings["allow_same_game_parlays"])
    min_combined_odds = float(settings["parlay_min_combined_odds"])
    allow_same_market_family_same_game = bool(settings.get("parlay_allow_same_market_family_same_game", False))

    for leg_count in [2, 3]:
        if leg_count > max_legs:
            continue

        for idxs in itertools.combinations(pool.index.tolist(), leg_count):
            combo = pool.loc[list(idxs)].copy().reset_index(drop=True)
            same_game_overlap, same_team_overlap = parlay_overlap_penalty(combo)

            if not allow_same_game and same_game_overlap > 0:
                continue

            if (not allow_same_market_family_same_game) and combo.groupby(["game", "market_family_norm"], dropna=False).size().gt(1).any():
                continue

            corr_penalty, corr_note = correlation_penalty(combo)
            if corr_penalty >= 18:
                continue

            combined_odds = combined_parlay_odds(combo["odds"].tolist())
            if pd.isna(combined_odds) or combined_odds < min_combined_odds:
                continue

            avg_score = float(pd.to_numeric(combo["score"], errors="coerce").fillna(0).mean())
            avg_adj = float(pd.to_numeric(combo["adjusted_score"], errors="coerce").fillna(0).mean())
            min_adj = float(pd.to_numeric(combo["adjusted_score"], errors="coerce").fillna(0).min())
            avg_consensus = float(pd.to_numeric(combo["ai_consensus"], errors="coerce").fillna(0).mean())
            min_consensus = int(pd.to_numeric(combo["ai_consensus"], errors="coerce").fillna(0).min())
            avg_ev = float(pd.to_numeric(combo["ev_edge"], errors="coerce").fillna(0).mean())
            avg_hit = float(pd.to_numeric(combo["hit_pct"], errors="coerce").fillna(0).mean())

            committee_votes = 0
            if avg_adj >= 80:
                committee_votes += 1
            if min_adj >= float(settings["parlay_min_leg_adjusted"]):
                committee_votes += 1
            if avg_consensus >= 4.0:
                committee_votes += 1
            if corr_penalty <= 6:
                committee_votes += 1
            if combined_odds >= min_combined_odds:
                committee_votes += 1

            if committee_votes < int(settings["parlay_min_leg_consensus"]):
                continue
            if min_consensus < int(settings["parlay_min_leg_consensus"]):
                continue

            expected_hit_rate = estimate_parlay_success(combo)
            min_hit_rate = float(settings.get("portfolio_min_slip_prob", 0.05))
            if expected_hit_rate < min_hit_rate:
                continue
            expected_roi_pct = estimate_parlay_roi_pct(combo, combined_odds)
            if expected_roi_pct < -2:
                continue

            slip_profile_name = parlay_profile(leg_count, int(combined_odds))
            adaptive_edge, adaptive_notes = adaptive_rank_modifier(
                combo,
                slip_profile_name,
                int(combined_odds),
                consensus_label(committee_votes),
            )

            raw_rank = (
                avg_adj * 0.42
                + avg_consensus * 8.5
                + min(avg_ev, 18) * 0.90
                + min(max(expected_roi_pct, -5), 25) * 0.85
                + min(max(combined_odds - min_combined_odds, 0), 500) / 75.0
                + min(avg_hit, 70) * 0.10
                - corr_penalty
                - (same_game_overlap * 5)
                - (same_team_overlap * 2)
                - (2 if leg_count == 3 else 0)
                + adaptive_edge
            )

            slip = {
                "slip_id": f"AI-PARLAY-{leg_count}-{'-'.join(map(str, idxs))}",
                "builder": "AI Optimizer",
                "legs": leg_count,
                "combined_odds": int(combined_odds),
                "stake": 1.0,
                "avg_leg_score": round(avg_score, 2),
                "min_leg_score": round(float(pd.to_numeric(combo["score"], errors="coerce").fillna(0).min()), 2),
                "avg_leg_adjusted": round(avg_adj, 2),
                "min_leg_adjusted": round(min_adj, 2),
                "avg_leg_consensus": round(avg_consensus, 2),
                "consensus_votes": committee_votes,
                "consensus_label": consensus_label(committee_votes),
                "same_game_overlap": same_game_overlap,
                "same_team_overlap": same_team_overlap,
                "sport_mix": ", ".join(sorted(combo["sport"].astype(str).unique().tolist())),
                "target_min_odds": min_combined_odds,
                "legs_preview": " | ".join([
                    f"{r.get('sport', '')} {r.get('game', '')} {r.get('market', '')} {r.get('line', '')} ({r.get('odds', '')})"
                    for _, r in combo.iterrows()
                ]),
                "legs_rows": combo.to_dict("records"),
                "leg_keys_json": json.dumps([parlay_leg_key(r) for r in combo.to_dict("records")]),
                "rank_score": round(raw_rank, 2),
                "expected_roi_pct": expected_roi_pct,
                "correlation_penalty": corr_penalty,
                "correlation_note": corr_note,
                "duplication_penalty": 0.0,
                "slip_profile": slip_profile_name,
                "adaptive_edge": adaptive_edge,
                "adaptive_notes": ", ".join(adaptive_notes) if adaptive_notes else "Neutral",
            }
            slips.append(slip)

    if not slips:
        return []

    slips = sorted(
        slips,
        key=lambda x: (
            x["rank_score"],
            x["expected_roi_pct"],
            x["avg_leg_adjusted"],
            x["combined_odds"]
        ),
        reverse=True,
    )

    style = str(settings.get("parlay_build_style", "Hybrid"))
    if style == "Conservative":
        max_support = 1
    elif style == "Aggressive":
        max_support = 4
    else:
        max_support = int(settings.get("parlay_support_slips", 3))

    total_target = 1 + max_support
    final_slips = []
    leg_use_count = {}
    max_reuse = int(settings.get("parlay_max_leg_reuse", 2))

    best_slip = slips[0]
    final_slips.append(best_slip)
    for lk in json.loads(best_slip["leg_keys_json"]):
        leg_use_count[lk] = leg_use_count.get(lk, 0) + 1

    for slip in slips[1:]:
        if len(final_slips) >= total_target:
            break
        leg_keys = json.loads(slip["leg_keys_json"])
        overlap_with_best = len(set(leg_keys) & set(json.loads(best_slip["leg_keys_json"])))
        if overlap_with_best >= max(1, slip["legs"]):
            continue

        projected_dup_penalty = 0.0
        allowed = True
        for lk in leg_keys:
            current_count = leg_use_count.get(lk, 0)
            if current_count >= max_reuse:
                allowed = False
                break
            if current_count >= 1:
                projected_dup_penalty += 5.0

        if not allowed:
            continue

        slip["duplication_penalty"] = round(projected_dup_penalty, 2)
        adjusted_rank = slip["rank_score"] - slip["duplication_penalty"]
        if adjusted_rank < 70:
            continue
        slip["rank_score"] = round(adjusted_rank, 2)

        final_slips.append(slip)
        for lk in leg_keys:
            leg_use_count[lk] = leg_use_count.get(lk, 0) + 1

    seen_sports = []
    for i, slip in enumerate(final_slips, start=1):
        combo_df = pd.DataFrame(slip["legs_rows"])
        slip["parlay_rank"] = i
        slip["is_best"] = i == 1
        slip["parlay_grade"] = parlay_grade(slip["rank_score"])
        adaptive_tag = "Adaptive " if bool(settings.get("adaptive_auto_mode", True)) else ""
        slip["builder"] = f"AI {adaptive_tag}Portfolio Optimizer" if style == "Hybrid" else f"AI {adaptive_tag}{style} Portfolio Optimizer"
        slip["estimated_hit_rate"] = round(estimate_parlay_success(combo_df) * 100, 1)
        unique_sports = combo_df["sport"].astype(str).nunique() if not combo_df.empty and "sport" in combo_df.columns else 1
        repeated_sports = sum(1 for s in combo_df.get("sport", pd.Series(dtype=str)).astype(str).tolist() if s in seen_sports)
        slip["diversity_score"] = round(max(0.0, (unique_sports * 20) + (10 if repeated_sports == 0 else 0) - (safe_float(slip.get("duplication_penalty"), 0.0) * 1.2) - (safe_float(slip.get("correlation_penalty"), 0.0) * 0.4)), 1)
        seen_sports.extend(combo_df.get("sport", pd.Series(dtype=str)).astype(str).tolist())

    final_slips = build_portfolio_plan(final_slips, bankroll, risk_mode, drawdown_pct, roi_pct)
    return final_slips


def add_ai_parlay_to_log(slip, mode):
    if is_duplicate_parlay_in_tracker(slip):
        return False, "This parlay is already in your tracker."
    log = st.session_state.parlay_log.copy()
    parlay_id = f"PARLAY-{len(log)+1:04d}"
    new_row = {
        "parlay_id": parlay_id,
        "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "bet_date": str(date.today()),
        "mode": mode,
        "builder": slip.get("builder", "AI Optimizer"),
        "sport_mix": slip.get("sport_mix", ""),
        "legs": int(slip.get("legs", 0)),
        "combined_odds": slip.get("combined_odds", np.nan),
        "stake": round(float(slip.get("stake", 0)), 2),
        "target_min_odds": slip.get("target_min_odds", np.nan),
        "avg_leg_score": slip.get("avg_leg_score", np.nan),
        "min_leg_score": slip.get("min_leg_score", np.nan),
        "avg_leg_adjusted": slip.get("avg_leg_adjusted", np.nan),
        "avg_leg_consensus": slip.get("avg_leg_consensus", np.nan),
        "consensus_label": slip.get("consensus_label", ""),
        "same_game_overlap": slip.get("same_game_overlap", 0),
        "same_team_overlap": slip.get("same_team_overlap", 0),
        "result": "Pending",
        "profit": np.nan,
        "notes": "",
        "leg_keys_json": slip.get("leg_keys_json", "[]"),
        "legs_preview": slip.get("legs_preview", ""),
        "parlay_rank": slip.get("parlay_rank", np.nan),
        "parlay_grade": slip.get("parlay_grade", ""),
        "parlay_expected_roi": slip.get("expected_roi_pct", np.nan),
        "duplication_penalty": slip.get("duplication_penalty", np.nan),
        "correlation_penalty": slip.get("correlation_penalty", np.nan),
        "slip_profile": slip.get("slip_profile", ""),
        "portfolio_share": slip.get("portfolio_share", np.nan),
        "portfolio_target_stake": slip.get("portfolio_target_stake", np.nan),
        "estimated_hit_rate": slip.get("estimated_hit_rate", np.nan),
        "diversity_score": slip.get("diversity_score", np.nan),
        "adaptive_edge": slip.get("adaptive_edge", np.nan),
        "adaptive_notes": slip.get("adaptive_notes", ""),
    }
    st.session_state.parlay_log = pd.concat([log, pd.DataFrame([new_row])], ignore_index=True)
    save_full_auto_state()
    return True, parlay_id

# ---------- TRACKER ----------
def add_bet_to_log(row, stake, risk_mode, bankroll_snapshot, mode):
    log = st.session_state.bet_log.copy()
    bet_id = f"BET-{len(log)+1:04d}"
    new_row = {
        "bet_id": bet_id,
        "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "bet_date": str(date.today()),
        "mode": mode,
        "entry_type": "Single",
        "sport": row.get("sport", ""),
        "player": row.get("player", ""),
        "market": row.get("market", ""),
        "book": row.get("book", ""),
        "odds": row.get("odds", np.nan),
        "line": row.get("line", row.get("point", np.nan)),
        "stake": round(float(stake), 2),
        "score": row.get("score", np.nan),
        "adjusted_score": row.get("adjusted_score", np.nan),
        "tier": row.get("tier", ""),
        "units": row.get("units", np.nan),
        "game": row.get("game", ""),
        "bet_side": row.get("bet_side", ""),
        "market_type": row.get("market_type", ""),
        "result": "Pending",
        "profit": np.nan,
        "notes": "",
        "risk_mode": risk_mode,
        "bankroll_snapshot": round(float(bankroll_snapshot), 2),
        "model_projection": row.get("model_projection", np.nan),
        "model_price_ev": row.get("model_price_ev", np.nan),
        "model_risk": row.get("model_risk", np.nan),
        "model_market": row.get("model_market", np.nan),
        "model_history": row.get("model_history", np.nan),
        "multi_ai_score": row.get("multi_ai_score", np.nan),
        "ai_votes_for": row.get("ai_votes_for", np.nan),
        "ai_consensus": row.get("ai_consensus", np.nan),
        "clv_closing_line": np.nan,
        "clv_direction": row.get("bet_side", ""),
        "clv_diff": np.nan,
        "clv_win": "",
    }
    st.session_state.bet_log = pd.concat([log, pd.DataFrame([new_row])], ignore_index=True)
    save_full_auto_state()


def refresh_bet_log_metrics():
    log = st.session_state.bet_log.copy()
    parlay_log = st.session_state.parlay_log.copy()
    total_staked = 0.0
    total_profit = 0.0
    wins = losses = pushes = pending = 0
    parlay_count = 0

    if not log.empty:
        settled = log[log["result"].isin(["Win", "Loss", "Push"])].copy()
        total_staked += pd.to_numeric(log["stake"], errors="coerce").fillna(0).sum()
        total_profit += pd.to_numeric(settled["profit"], errors="coerce").fillna(0).sum()
        wins += int((log["result"] == "Win").sum())
        losses += int((log["result"] == "Loss").sum())
        pushes += int((log["result"] == "Push").sum())
        pending += int((log["result"] == "Pending").sum())

    if not parlay_log.empty:
        settled_p = parlay_log[parlay_log["result"].isin(["Win", "Loss", "Push"])].copy()
        total_staked += pd.to_numeric(parlay_log["stake"], errors="coerce").fillna(0).sum()
        total_profit += pd.to_numeric(settled_p["profit"], errors="coerce").fillna(0).sum()
        wins += int((parlay_log["result"] == "Win").sum())
        losses += int((parlay_log["result"] == "Loss").sum())
        pushes += int((parlay_log["result"] == "Push").sum())
        pending += int((parlay_log["result"] == "Pending").sum())
        parlay_count = len(parlay_log)

    total_count = len(log) + len(parlay_log)
    settled_count = wins + losses + pushes
    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0.0
    roi = (total_profit / total_staked * 100) if total_staked > 0 else 0.0
    return {
        "total_bets": total_count,
        "singles": len(log),
        "parlays": parlay_count,
        "settled_bets": settled_count,
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "pending": pending,
        "total_staked": round(float(total_staked), 2),
        "profit": round(float(total_profit), 2),
        "roi": round(float(roi), 2),
        "win_rate": round(float(win_rate), 2),
    }

# ---------- EXPORT / IMPORT ----------
def export_state_json():
    payload = {
        "bet_log": st.session_state.bet_log.to_dict("records"),
        "parlay_log": st.session_state.parlay_log.to_dict("records"),
        "learning_state": st.session_state.learning_state,
        "launch_settings": st.session_state.launch_settings,
    }
    return json.dumps(payload, indent=2, default=str)


def import_state_json(text):
    payload = json.loads(text)
    if "bet_log" in payload:
        st.session_state.bet_log = pd.DataFrame(payload["bet_log"])
    if "parlay_log" in payload:
        st.session_state.parlay_log = pd.DataFrame(payload["parlay_log"])
    if "learning_state" in payload and isinstance(payload["learning_state"], dict):
        st.session_state.learning_state = payload["learning_state"]
    if "launch_settings" in payload and isinstance(payload["launch_settings"], dict):
        merged = st.session_state.launch_settings.copy()
        merged.update(payload["launch_settings"])
        st.session_state.launch_settings = merged

def auto_track_engine(df):
    settings = st.session_state.launch_settings
    if not bool(settings.get("auto_track_enabled", False)):
        st.session_state.auto_last_summary = "Auto-track disabled."
        return {"singles_added": 0, "parlays_added": 0}

    auto_mode = settings.get("auto_track_mode", settings.get("default_mode", "Paper"))
    bankroll = float(settings.get("starting_bankroll", 250.0))
    risk_mode = settings.get("risk_mode", "Balanced")
    drawdown_pct = 0.0
    roi_pct = float(refresh_bet_log_metrics().get("roi", 0.0))

    singles_added = 0
    parlays_added = 0

    if bool(settings.get("auto_track_singles", True)):
        singles_df = high_probability_singles(df).copy()
        for _, row in singles_df.iterrows():
            rowd = row.to_dict()
            if is_duplicate_single_in_tracker(rowd):
                continue
            stake = suggested_stake_from_units(rowd.get("units", 0), bankroll, risk_mode, drawdown_pct, roi_pct)
            ok, _ = can_add_slip_item(rowd, stake)
            if not ok:
                continue
            add_bet_to_log(rowd, stake, risk_mode, bankroll, auto_mode)
            singles_added += 1

    if bool(settings.get("auto_track_parlays", True)):
        slips = optimize_ai_parlay_slips(df, bankroll, risk_mode, drawdown_pct, roi_pct)
        limit = 1 + int(settings.get("auto_track_support_slips", 2))
        for slip in slips[:limit]:
            added, _ = add_ai_parlay_to_log(slip, auto_mode)
            if added:
                parlays_added += 1

    st.session_state.auto_last_summary = f"Auto-track added {singles_added} single(s) and {parlays_added} parlay(s) in {auto_mode} mode."
    if singles_added > 0 or parlays_added > 0:
        save_full_auto_state()
    return {"singles_added": singles_added, "parlays_added": parlays_added}


def maybe_run_auto_track():
    if st.session_state.active_df is None:
        return
    try:
        df = filtered_launch_ready(st.session_state.active_df)
    except Exception:
        return
    auto_track_engine(df)


# ---------- RENDER ----------
def render_mobile_bet_picker(df, bankroll, risk_mode, drawdown_pct, roi_pct, key_prefix):
    if df.empty:
        st.info("No qualified plays available.")
        return
    work = df.copy().reset_index(drop=True)
    work["suggested_stake"] = work["units"].apply(lambda u: suggested_stake_from_units(u, bankroll, risk_mode, drawdown_pct, roi_pct))
    st.subheader("Launch Selector")
    st.caption("Add plays to slip, then confirm them to tracker in Paper or Live mode.")
    for i, row in work.head(12).iterrows():
        player_part = f" | {row.get('player', '')}" if str(row.get("player", "")).strip() not in ["", "nan"] else ""
        st.markdown(f"**{row.get('sport', '')}{player_part} - {row.get('market', '')}**")
        st.write(f"{row.get('market_type', '')} | {row.get('book', '')} | Odds: {row.get('odds', '')} | Line: {row.get('line', '')}")
        st.write(f"Score: {row.get('score', 0):.1f} | Adjusted: {row.get('adjusted_score', 0):.1f} | Multi-AI: {row.get('multi_ai_score', 0):.1f}")
        st.write(f"{row.get('tier', '')} | Units: {row.get('units', 0):.2f}u | Debate: {int(row.get('ai_votes_for', 0))}/5 | Suggested Stake: ${row.get('suggested_stake', 0):.2f}")
        st.write(f"Game: {row.get('game', '')} | Sport Mult: {row.get('sport_unit_mult', 1.0):.2f}x")
        c1, c2 = st.columns([1, 1])
        with c1:
            custom_stake = st.number_input("Stake", min_value=1.0, value=float(max(1.0, row.get("suggested_stake", 1.0))), step=1.0, key=f"{key_prefix}_stake_{i}")
        with c2:
            st.write("")
            ok, msg = can_add_slip_item(row.to_dict(), custom_stake)
            if st.button(f"Add To Slip {i+1}", key=f"{key_prefix}_add_{i}", use_container_width=True):
                if ok:
                    add_to_slip(row.to_dict(), custom_stake, bankroll, risk_mode)
                    st.success("Added to bet slip.")
                else:
                    st.error(msg)
        st.divider()


def render_bet_slip(namespace):
    st.subheader("Live Bet Slip")
    slip = pd.DataFrame(st.session_state.bet_slip)
    if slip.empty:
        st.info("Your bet slip is empty.")
        return
    summary = slip_summary()
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Bets", summary["bets"])
    c2.metric("Total Stake", f"${summary['stake']:.2f}")
    c3.metric("Games", summary["games"])
    c4.metric("Players", summary["players"])
    c5.metric("Sports", summary["sports"])
    st.info("Risk check: " + slip_risk_message(summary))
    if summary["same_game_extra"] > 0:
        st.warning("Tip: You have multiple bets from the same game.")
    if summary["same_player_extra"] > 0:
        st.warning("Tip: You have multiple bets tied to the same player.")
    slip_show = slip[[c for c in ["sport", "player", "market_type", "market", "book", "odds", "line", "stake", "adjusted_score", "ai_consensus", "tier", "game"] if c in slip.columns]]
    st.dataframe(slip_show, use_container_width=True)

    for i, item in slip.reset_index(drop=True).iterrows():
        label = f"{item['sport']} | {item.get('player', '')} {item['market']} | ${float(item['stake']):.2f}"
        if st.button("Remove: " + label, key=f"{namespace}_remove_slip_{i}_{item['slip_key']}", use_container_width=True):
            remove_from_slip(item["slip_key"])
            st.success("Removed from slip.")
            st.rerun()

    mode = st.selectbox("Confirm mode", ["Paper", "Live"], index=0 if st.session_state.launch_settings["default_mode"] == "Paper" else 1, key=f"{namespace}_mode")
    x1, x2 = st.columns(2)
    with x1:
        if st.button("Clear Bet Slip", key=f"{namespace}_clear_slip", use_container_width=True):
            clear_slip()
            st.success("Bet slip cleared.")
            st.rerun()
    with x2:
        if st.button("Confirm Slip To Tracker", key=f"{namespace}_confirm_slip", use_container_width=True):
            count = confirm_slip_to_tracker(mode)
            st.success(f"Added {count} {mode} bet(s) to tracker.")
            st.rerun()


def render_ai_parlay_builder(df, bankroll, risk_mode, drawdown_pct, roi_pct):
    st.subheader("AI-Built Consensus Parlays")
    slips = optimize_ai_parlay_slips(df, bankroll, risk_mode, drawdown_pct, roi_pct)
    st.session_state.ai_parlay_slips = slips
    if not slips:
        st.warning("No optimized parlay today. The AI optimizer did not find enough strong, low-correlation combinations above your thresholds.")
        return

    adaptive_state = adaptive_parlay_history_summary()
    st.success("Adaptive portfolio mode active: 1 best parlay plus supporting slips with bankroll allocation.")
    st.caption(f"Adaptive state: {adaptive_state.get('mode', 'Neutral')} | Confidence: {adaptive_state.get('confidence', 'Low')} | Settled parlays: {adaptive_state.get('samples', 0)}")
    for i, slip in enumerate(slips):
        header_prefix = "🔥 Best AI Parlay" if slip.get("is_best") else f"Support Slip {slip.get('parlay_rank', i+1)}"
        st.markdown(
            f"**{header_prefix} | Grade {slip['parlay_grade']} | {slip['consensus_label']} | "
            f"{slip['legs']}-Leg AI Slip | Combined Odds: {slip['combined_odds']:+}**"
        )
        st.write(
            f"Stake: ${slip['stake']:.2f} | Portfolio Share: {safe_float(slip.get('portfolio_share'), 0.0):.1f}% | "
            f"Rank Score: {slip['rank_score']:.1f} | Expected ROI: {slip['expected_roi_pct']:.1f}% | "
            f"Hit Rate: {safe_float(slip.get('estimated_hit_rate'), 0.0):.1f}%"
        )
        st.write(
            f"Avg Adjusted: {slip['avg_leg_adjusted']:.1f} | Avg Consensus: {slip['avg_leg_consensus']:.2f} | "
            f"Diversity Score: {safe_float(slip.get('diversity_score'), 0.0):.1f}"
        )
        st.write(
            f"Profile: {slip['slip_profile']} | Sports: {slip['sport_mix']} | "
            f"Correlation Penalty: {slip['correlation_penalty']:.1f} | Duplication Penalty: {slip['duplication_penalty']:.1f} | Adaptive Edge: {safe_float(slip.get('adaptive_edge'), 0.0):.1f}"
        )
        st.write(f"Legs: {slip['legs_preview']}")
        if slip["same_game_overlap"] > 0:
            st.warning("Same-game overlap present.")
        notes_line = []
        if str(slip.get("correlation_note", "Clean")) != "Clean":
            notes_line.append("Correlation notes: " + str(slip.get("correlation_note", "")))
        if str(slip.get("adaptive_notes", "Neutral")) not in ["", "Neutral"]:
            notes_line.append("Adaptive notes: " + str(slip.get("adaptive_notes", "")))
        if notes_line:
            st.caption(" | ".join(notes_line))

        b1, b2 = st.columns([1, 1])
        with b1:
            custom_stake = st.number_input("AI Parlay Stake", min_value=1.0, value=float(max(1.0, slip["stake"])), step=1.0, key=f"ai_parlay_stake_{i}")
        with b2:
            mode = st.selectbox("Mode", ["Paper", "Live"], index=0 if st.session_state.launch_settings["default_mode"] == "Paper" else 1, key=f"ai_parlay_mode_{i}")
            if st.button(f"Add AI Slip {i+1} To Tracker", key=f"ai_parlay_add_{i}", use_container_width=True):
                slip_copy = slip.copy()
                slip_copy["stake"] = float(custom_stake)
                ok, msg = add_ai_parlay_to_log(slip_copy, mode)
                if ok:
                    st.success(f"AI-built parlay added to tracker: {msg}")
                    st.rerun()
                else:
                    st.warning(msg)
        st.divider()

# ---------- APP ----------
st.title("Sports AI Dashboard V14 Results + CLV Intelligence")
st.caption("Adaptive portfolio intelligence for Mainline, Spread, and Total singles plus self-adjusting AI-built consensus parlays.")

tabs = st.tabs([
    "Dashboard", "Data Input", "Launch Settings", "All-Market Board", "High-Probability Singles", "AI Parlay Builder",
    "Bet Slip", "CLV Tracker", "Singles Tracker", "Parlay Tracker", "Performance", "All-Market Stats", "30-Day Test",
    "Multi-AI Lab", "Learning Dashboard", "Adaptive Edge AI", "Results + CLV AI", "Import / Export"
])

maybe_run_auto_track()

with tabs[0]:
    st.write("Active Source:", st.session_state.active_source)
    metrics = refresh_bet_log_metrics()
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Tracked Entries", metrics["total_bets"])
    c2.metric("Singles", metrics["singles"])
    c3.metric("Parlays", metrics["parlays"])
    c4.metric("Profit", f"${metrics['profit']:.2f}")
    c5.metric("ROI", f"{metrics['roi']:.2f}%")
    d1, d2, d3 = st.columns(3)
    d1.metric("Win Rate", f"{metrics['win_rate']:.1f}%")
    today_bets, today_stake = today_counts_and_exposure()
    d2.metric("Today's Entries", today_bets)
    d3.metric("Today's Exposure", f"${today_stake:.2f}")
    st.caption(st.session_state.get("auto_last_summary", "Auto-track idle."))

with tabs[1]:
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Load Sample Mixed Market Data", use_container_width=True):
            st.session_state.active_df = sample_data()
            st.session_state.active_source = "Sample"
            st.success("Sample data loaded.")
    with c2:
        if st.button("Clear Active Data", use_container_width=True):
            st.session_state.active_df = None
            st.session_state.active_source = "None"
            st.warning("Active data cleared.")
    uploaded_file = st.file_uploader("Choose CSV or Excel", type=["csv", "xlsx", "xls"])
    if uploaded_file is not None:
        df_upload, err = read_uploaded_file(uploaded_file)
        if err:
            st.error(err)
        else:
            st.session_state.active_df = df_upload
            st.session_state.active_source = f"Uploaded: {uploaded_file.name}"
            st.success("File loaded.")
    sample_text = "sport,player,market,odds,point,book,projection,edge,hit_pct,is_starter,team,opponent,game\nNBA,,Moneyline,-145,0,DraftKings,0,2.3,61.5,True,BOS,MIA,BOS @ MIA\nNBA,,Spread,-110,-4.5,FanDuel,-7.2,2.7,58.5,True,DEN,UTA,DEN @ UTA\nNBA,,Total Over,-108,229.5,Caesars,235.8,6.3,59.7,True,PHX,DAL,PHX @ DAL"
    txt = st.text_area("Paste CSV here", value="", height=180, placeholder=sample_text)
    if st.button("Load Pasted Data", use_container_width=True):
        df_paste, err = parse_csv_text(txt)
        if err:
            st.error(err)
        else:
            st.session_state.active_df = df_paste
            st.session_state.active_source = "Pasted CSV"
            st.success("Pasted data loaded.")
    if st.session_state.active_df is not None:
        preview = filtered_launch_ready(st.session_state.active_df)
        st.dataframe(preview.head(30), use_container_width=True)

with tabs[2]:
    st.subheader("Launch Settings")
    settings = st.session_state.launch_settings
    settings["starting_bankroll"] = st.number_input("Starting bankroll ($)", min_value=25.0, value=float(settings["starting_bankroll"]), step=25.0)
    settings["risk_mode"] = st.selectbox("Default risk mode", ["Conservative", "Balanced", "Aggressive"], index=["Conservative", "Balanced", "Aggressive"].index(settings["risk_mode"]))
    settings["max_bets_per_day"] = st.number_input("Max entries per day", min_value=1, max_value=30, value=int(settings["max_bets_per_day"]), step=1)
    settings["max_daily_exposure"] = st.number_input("Max daily exposure ($)", min_value=10.0, value=float(settings["max_daily_exposure"]), step=5.0)
    settings["default_mode"] = st.selectbox("Default tracking mode", ["Paper", "Live"], index=0 if settings["default_mode"] == "Paper" else 1)
    settings["lock_after_add"] = st.toggle("Lock bet details after adding to tracker", value=bool(settings["lock_after_add"]))
    settings["min_adjusted_score"] = st.slider("Launch minimum adjusted score", 0, 100, int(settings["min_adjusted_score"]))

    st.markdown("**Singles Filters**")
    s1, s2, s3, s4 = st.columns(4)
    settings["singles_min_consensus"] = s1.selectbox("Min AI consensus", [3, 4, 5], index=[3, 4, 5].index(int(settings["singles_min_consensus"])))
    settings["singles_min_confidence"] = s2.slider("Min confidence", 50, 95, int(settings["singles_min_confidence"]))
    settings["singles_min_odds"] = s3.number_input("Min single odds", value=int(settings["singles_min_odds"]), step=5)
    settings["singles_max_odds"] = s4.number_input("Max single odds", value=int(settings["singles_max_odds"]), step=5)

    st.markdown("**AI Parlay Filters**")
    p1, p2, p3, p4 = st.columns(4)
    settings["parlay_min_combined_odds"] = p1.number_input("Min parlay odds", value=int(settings["parlay_min_combined_odds"]), step=10)
    settings["parlay_min_leg_adjusted"] = p2.slider("Min leg adjusted score", 60, 95, int(settings["parlay_min_leg_adjusted"]))
    settings["parlay_min_leg_consensus"] = p3.selectbox("Min leg debate threshold", [3, 4, 5], index=[3, 4, 5].index(int(settings["parlay_min_leg_consensus"])))
    settings["parlay_max_legs"] = p4.selectbox("Max legs AI can build", [2, 3], index=[2, 3].index(int(settings["parlay_max_legs"])))

    q1, q2, q3, q4 = st.columns(4)
    settings["parlay_build_style"] = q1.selectbox("Build style", ["Conservative", "Hybrid", "Aggressive"], index=["Conservative", "Hybrid", "Aggressive"].index(settings.get("parlay_build_style", "Hybrid")))
    settings["parlay_support_slips"] = q2.selectbox("Support slips", [1, 2, 3, 4], index=[1, 2, 3, 4].index(int(settings.get("parlay_support_slips", 3))))
    settings["parlay_pool_size"] = q3.selectbox("Optimizer pool size", [10, 12, 14, 16, 18], index=[10, 12, 14, 16, 18].index(int(settings.get("parlay_pool_size", 16))))
    settings["parlay_max_leg_reuse"] = q4.selectbox("Max leg reuse", [1, 2, 3], index=[1, 2, 3].index(int(settings.get("parlay_max_leg_reuse", 2))))

    r1, r2, r3, r4 = st.columns(4)
    settings["portfolio_best_share"] = r1.slider("Best slip share", 0.35, 0.75, float(settings.get("portfolio_best_share", 0.55)), 0.05)
    settings["portfolio_support_share"] = round(1.0 - float(settings["portfolio_best_share"]), 2)
    settings["portfolio_max_total_pct"] = r2.slider("Max parlay portfolio % bankroll", 0.01, 0.05, float(settings.get("portfolio_max_total_pct", 0.025)), 0.005)
    settings["portfolio_min_slip_prob"] = r3.slider("Min slip hit rate %", 1.0, 15.0, float(settings.get("portfolio_min_slip_prob", 5.0)), 0.5) / 100.0
    r4.metric("Support share", f"{float(settings['portfolio_support_share'])*100:.0f}%")

    a1, a2, a3 = st.columns(3)
    settings["adaptive_auto_mode"] = a1.toggle("Adaptive auto mode", value=bool(settings.get("adaptive_auto_mode", True)))
    settings["adaptive_weight"] = a2.slider("Adaptive weight", 0.05, 0.40, float(settings.get("adaptive_weight", 0.18)), 0.01)
    settings["adaptive_min_samples"] = a3.selectbox("Adaptive min samples", [3, 5, 8, 10], index=[3, 5, 8, 10].index(int(settings.get("adaptive_min_samples", 5))))

    st.markdown("**Auto-Track + Auto-Save**")
    t1, t2, t3, t4 = st.columns(4)
    settings["auto_track_enabled"] = t1.toggle("Enable auto-track", value=bool(settings.get("auto_track_enabled", False)))
    settings["auto_track_singles"] = t2.toggle("Auto singles", value=bool(settings.get("auto_track_singles", True)))
    settings["auto_track_parlays"] = t3.toggle("Auto parlays", value=bool(settings.get("auto_track_parlays", True)))
    settings["auto_track_mode"] = t4.selectbox("Auto-track mode", ["Paper", "Live"], index=0 if settings.get("auto_track_mode", settings["default_mode"]) == "Paper" else 1)
    settings["auto_track_support_slips"] = st.selectbox("Auto support parlays", [0, 1, 2, 3], index=[0, 1, 2, 3].index(int(settings.get("auto_track_support_slips", 2))))

    settings["allow_same_game_parlays"] = st.toggle("Allow same-game parlays", value=bool(settings["allow_same_game_parlays"]))
    settings["parlay_allow_same_market_family_same_game"] = st.toggle(
        "Allow same market family in same game",
        value=bool(settings.get("parlay_allow_same_market_family_same_game", False))
    )
    save_full_auto_state()
    st.success("Settings saved in session.")

with tabs[3]:
    if st.session_state.active_df is None:
        st.info("Load data first.")
    else:
        df = filtered_launch_ready(st.session_state.active_df)
        df = df[df["market_type"].isin(["Mainline", "Spread", "Total"])].copy()
        sport_options = sorted(df["sport"].dropna().astype(str).unique().tolist()) if "sport" in df.columns else []
        book_options = sorted(df["book"].dropna().astype(str).unique().tolist()) if "book" in df.columns else []
        tier_options = sorted(df["tier"].dropna().astype(str).unique().tolist()) if "tier" in df.columns else []
        c1, c2, c3, c4 = st.columns(4)
        selected_sports = c1.multiselect("Sports", sport_options, default=sport_options)
        selected_books = c2.multiselect("Books", book_options, default=book_options)
        selected_tiers = c3.multiselect("Tiers", tier_options, default=tier_options)
        min_consensus = c4.selectbox("Min debate", [3, 4, 5], index=0)
        odds_min, odds_max = st.slider("Odds range", -300, 300, (-200, 150), step=5)
        filtered = df.copy()
        if selected_sports:
            filtered = filtered[filtered["sport"].astype(str).isin(selected_sports)]
        if selected_books:
            filtered = filtered[filtered["book"].astype(str).isin(selected_books)]
        if selected_tiers:
            filtered = filtered[filtered["tier"].astype(str).isin(selected_tiers)]
        filtered = filtered[filtered["ai_consensus"] >= min_consensus]
        filtered = filtered[filtered["odds"].fillna(0).between(odds_min, odds_max)]
        filtered = best_bets(filtered)
        st.dataframe(filtered[[c for c in [
            "sport", "market_type", "game", "market", "book", "odds", "line", "hit_pct", "ev_edge", "score", "adjusted_score", "selection_score", "results_clv_edge", "ai_consensus", "ai_consensus_label", "tier", "units"
        ] if c in filtered.columns]], use_container_width=True)

with tabs[4]:
    if st.session_state.active_df is None:
        st.info("Load data first.")
    else:
        df = filtered_launch_ready(st.session_state.active_df)
        singles = high_probability_singles(df)
        bankroll_quick = st.number_input("Bankroll for singles ($)", min_value=25.0, value=float(st.session_state.launch_settings["starting_bankroll"]), step=25.0, key="singles_bankroll")
        risk_mode_quick = st.selectbox("Risk mode", ["Conservative", "Balanced", "Aggressive"], index=["Conservative", "Balanced", "Aggressive"].index(st.session_state.launch_settings["risk_mode"]), key="singles_risk")
        drawdown_quick = st.number_input("Drawdown %", min_value=0.0, max_value=100.0, value=0.0, step=1.0, key="singles_drawdown")
        roi_quick = st.number_input("ROI %", value=float(refresh_bet_log_metrics()["roi"]), step=0.5, key="singles_roi")
        st.caption("Only Mainline, Spread, and Total bets that pass your base filters plus the V14 results + CLV intelligence layer are shown here.")
        render_mobile_bet_picker(singles, bankroll_quick, risk_mode_quick, drawdown_quick, roi_quick, "high_prob_singles")

with tabs[5]:
    if st.session_state.active_df is None:
        st.info("Load data first.")
    else:
        df = filtered_launch_ready(st.session_state.active_df)
        metrics = refresh_bet_log_metrics()
        bankroll = st.number_input("Parlay bankroll ($)", min_value=25.0, value=float(st.session_state.launch_settings["starting_bankroll"]), step=25.0, key="parlay_bankroll")
        risk_mode = st.selectbox("Parlay risk mode", ["Conservative", "Balanced", "Aggressive"], index=["Conservative", "Balanced", "Aggressive"].index(st.session_state.launch_settings["risk_mode"]), key="parlay_risk")
        drawdown_pct = st.number_input("Parlay drawdown %", min_value=0.0, max_value=100.0, value=0.0, step=1.0, key="parlay_drawdown")
        roi_input = st.number_input("Parlay ROI %", value=float(metrics["roi"]), step=0.5, key="parlay_roi")
        render_ai_parlay_builder(df, bankroll, risk_mode, drawdown_pct, roi_input)

with tabs[6]:
    render_bet_slip("bet_slip")

with tabs[7]:
    st.subheader("CLV Tracker")
    log = st.session_state.bet_log.copy()
    if log.empty:
        st.info("No tracked singles yet.")
    else:
        editable_idx = st.selectbox("Select tracked single", options=list(log.index), format_func=lambda i: f"{log.loc[i, 'bet_id']} | {log.loc[i, 'mode']} | {log.loc[i, 'sport']} | {log.loc[i, 'market']}")
        current = log.loc[editable_idx]
        closing_line = st.number_input("Closing line", value=float(current["clv_closing_line"]) if pd.notna(current["clv_closing_line"]) else float(current["line"]) if pd.notna(current["line"]) else 0.0, step=0.5)
        if st.button("Save CLV", use_container_width=True):
            st.session_state.bet_log.loc[editable_idx, "clv_closing_line"] = closing_line
            diff, result = clv_result(st.session_state.bet_log.loc[editable_idx])
            st.session_state.bet_log.loc[editable_idx, "clv_diff"] = diff
            st.session_state.bet_log.loc[editable_idx, "clv_win"] = result
            st.success("CLV updated.")
        clv_df = st.session_state.bet_log.copy()
        st.dataframe(clv_df[[c for c in ["bet_id", "mode", "sport", "market_type", "game", "market", "bet_side", "line", "clv_closing_line", "clv_diff", "clv_win", "result"] if c in clv_df.columns]], use_container_width=True)

with tabs[8]:
    st.subheader("Singles Tracker")
    log = st.session_state.bet_log.copy()
    if log.empty:
        st.info("No singles tracked yet.")
    else:
        lock_enabled = bool(st.session_state.launch_settings["lock_after_add"])
        for i in range(len(log)):
            with st.expander(f"{log.loc[i, 'bet_id']} | {log.loc[i, 'mode']} | {log.loc[i, 'sport']} | {log.loc[i, 'market_type']} | {log.loc[i, 'market']}", expanded=False):
                st.write(f"Game: {log.loc[i, 'game']} | Book: {log.loc[i, 'book']} | Odds: {log.loc[i, 'odds']} | Stake: ${float(log.loc[i, 'stake']):.2f}")
                st.write(f"Adjusted: {float(pd.to_numeric(pd.Series([log.loc[i, 'adjusted_score']]), errors='coerce').fillna(0).iloc[0]):.1f} | Debate: {int(pd.to_numeric(pd.Series([log.loc[i, 'ai_consensus']]), errors='coerce').fillna(0).iloc[0])}/5")
                if lock_enabled:
                    st.caption("Lock-after-add is enabled. Core bet details are read-only once tracked.")
                result = st.selectbox(
                    f"Result for {log.loc[i, 'bet_id']}",
                    ["Pending", "Win", "Loss", "Push"],
                    index=["Pending", "Win", "Loss", "Push"].index(log.loc[i, "result"]) if log.loc[i, "result"] in ["Pending", "Win", "Loss", "Push"] else 0,
                    key=f"result_{i}",
                )
                notes = st.text_input("Notes", value=str(log.loc[i, "notes"]), key=f"notes_{i}")
                if st.button(f"Save {log.loc[i, 'bet_id']}", key=f"save_single_{i}"):
                    log.loc[i, "result"] = result
                    log.loc[i, "notes"] = notes
                    log.loc[i, "profit"] = settle_profit(log.loc[i, "odds"], log.loc[i, "stake"], result)
                    st.session_state.bet_log = log.copy()
                    st.success("Single bet updated.")
        st.dataframe(st.session_state.bet_log, use_container_width=True)

with tabs[9]:
    st.subheader("Parlay Tracker")
    plog = st.session_state.parlay_log.copy()
    if plog.empty:
        st.info("No AI parlays tracked yet.")
    else:
        for i in range(len(plog)):
            with st.expander(f"{plog.loc[i, 'parlay_id']} | {plog.loc[i, 'mode']} | Rank {plog.loc[i, 'parlay_rank']} | {int(plog.loc[i, 'legs'])}-Leg | {plog.loc[i, 'combined_odds']:+}", expanded=False):
                st.write(f"Builder: {plog.loc[i, 'builder']} | Stake: ${float(plog.loc[i, 'stake']):.2f} | Sports: {plog.loc[i, 'sport_mix']}")
                st.write(f"Grade: {plog.loc[i, 'parlay_grade']} | Profile: {plog.loc[i, 'slip_profile']} | Consensus: {plog.loc[i, 'consensus_label']}")
                st.write(f"Expected ROI: {safe_float(plog.loc[i, 'parlay_expected_roi']):.1f}% | Correlation Penalty: {safe_float(plog.loc[i, 'correlation_penalty']):.1f}")
                st.write(f"Legs: {plog.loc[i, 'legs_preview']}")
                result = st.selectbox(
                    f"Parlay Result for {plog.loc[i, 'parlay_id']}",
                    ["Pending", "Win", "Loss", "Push"],
                    index=["Pending", "Win", "Loss", "Push"].index(plog.loc[i, "result"]) if plog.loc[i, "result"] in ["Pending", "Win", "Loss", "Push"] else 0,
                    key=f"parlay_result_{i}",
                )
                notes = st.text_input("Parlay Notes", value=str(plog.loc[i, "notes"]), key=f"parlay_notes_{i}")
                if st.button(f"Save {plog.loc[i, 'parlay_id']}", key=f"save_parlay_{i}"):
                    plog.loc[i, "result"] = result
                    plog.loc[i, "notes"] = notes
                    plog.loc[i, "profit"] = settle_parlay_profit(plog.loc[i, "combined_odds"], plog.loc[i, "stake"], result)
                    st.session_state.parlay_log = plog.copy()
                    st.success("Parlay updated.")
        st.dataframe(st.session_state.parlay_log, use_container_width=True)

with tabs[10]:
    st.subheader("Performance")
    metrics = refresh_bet_log_metrics()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Settled Entries", metrics["settled_bets"])
    c2.metric("Profit", f"${metrics['profit']:.2f}")
    c3.metric("ROI", f"{metrics['roi']:.2f}%")
    c4.metric("Win Rate", f"{metrics['win_rate']:.2f}%")
    settled = get_settled_log()
    settled_parlays = get_settled_parlay_log()
    if settled.empty and settled_parlays.empty:
        st.info("No settled entries yet.")
    else:
        if not settled.empty:
            perf = settled.groupby(["mode", "sport", "market_type"], dropna=False).agg(
                bets=("bet_id", "count"),
                profit=("profit", "sum"),
                avg_score=("score", "mean"),
                avg_adjusted=("adjusted_score", "mean"),
                avg_consensus=("ai_consensus", "mean"),
                win_rate=("result", lambda s: round((s.eq("Win").sum() / max(1, s.isin(["Win", "Loss"]).sum())) * 100, 2)),
            ).reset_index()
            st.markdown("**Singles Performance**")
            st.dataframe(perf, use_container_width=True)
        if not settled_parlays.empty:
            pperf = settled_parlays.groupby(["mode", "legs", "parlay_grade"], dropna=False).agg(
                parlays=("parlay_id", "count"),
                profit=("profit", "sum"),
                avg_odds=("combined_odds", "mean"),
                avg_leg_adjusted=("avg_leg_adjusted", "mean"),
                avg_expected_roi=("parlay_expected_roi", "mean"),
                win_rate=("result", lambda s: round((s.eq("Win").sum() / max(1, s.isin(["Win", "Loss"]).sum())) * 100, 2)),
            ).reset_index()
            st.markdown("**AI Parlay Performance**")
            st.dataframe(pperf, use_container_width=True)

with tabs[11]:
    st.subheader("All-Market Stats")
    settled = get_settled_log()
    if settled.empty:
        st.info("No settled singles yet.")
    else:
        by_market = settled.groupby(["mode", "sport", "market_type", "ai_consensus"], dropna=False).agg(
            bets=("bet_id", "count"),
            wins=("result", lambda s: int((s == "Win").sum())),
            losses=("result", lambda s: int((s == "Loss").sum())),
            profit=("profit", "sum"),
            avg_clv=("clv_diff", "mean"),
            avg_score=("adjusted_score", "mean"),
        ).reset_index()
        st.dataframe(by_market, use_container_width=True)
        clv_book = settled.groupby(["book", "market_type"], dropna=False).agg(
            bets=("bet_id", "count"),
            avg_clv=("clv_diff", "mean"),
            beat_close_rate=("clv_win", lambda s: round((s.eq("Beat Close").sum() / max(1, s.notna().sum())) * 100, 2)),
        ).reset_index()
        st.markdown("**CLV by Book / Market Type**")
        st.dataframe(clv_book, use_container_width=True)

with tabs[12]:
    st.subheader("30-Day Test Dashboard")
    single_log = daily_log_df()
    parlay_log = st.session_state.parlay_log.copy()
    frames = []
    if not single_log.empty:
        s = single_log[["bet_date", "mode", "stake", "profit"]].copy()
        s["entry_type"] = "Single"
        frames.append(s)
    if not parlay_log.empty:
        p = parlay_log[["bet_date", "mode", "stake", "profit"]].copy()
        p["entry_type"] = "Parlay"
        frames.append(p)
    if not frames:
        st.info("No tracked entries yet.")
    else:
        log = pd.concat(frames, ignore_index=True)
        log["profit"] = pd.to_numeric(log["profit"], errors="coerce").fillna(0)
        daily = log.groupby(["bet_date", "mode", "entry_type"], dropna=False).agg(
            bets=("stake", "count"),
            risk=("stake", "sum"),
            profit=("profit", "sum"),
        ).reset_index()
        daily = daily.sort_values(["mode", "entry_type", "bet_date"])
        daily["cum_profit"] = daily.groupby(["mode", "entry_type"])["profit"].cumsum()
        daily["starting_bankroll"] = float(st.session_state.launch_settings["starting_bankroll"])
        daily["roll"] = daily["starting_bankroll"] + daily["cum_profit"]
        st.dataframe(daily, use_container_width=True)

with tabs[13]:
    st.subheader("Multi-AI Lab")
    if st.session_state.active_df is None:
        st.info("Load data first.")
    else:
        df = best_bets(filtered_launch_ready(st.session_state.active_df)).reset_index(drop=True)
        st.dataframe(df[[c for c in [
            "sport", "market_type", "player", "game", "market", "book", "odds", "line", "model_projection", "model_price_ev", "model_risk",
            "model_market", "model_history", "ai_votes_for", "ai_consensus_label", "multi_ai_score", "score", "learning_boost", "adjusted_score", "results_clv_edge", "selection_score",
            "sport_unit_mult", "market_min_score", "tier", "units"
        ] if c in df.columns]], use_container_width=True)

with tabs[14]:
    st.subheader("Learning Dashboard")
    settled = get_settled_log()
    weight_df = pd.DataFrame({"model": list(st.session_state.learning_state["weights"].keys()), "weight": [round(v, 4) for v in st.session_state.learning_state["weights"].values()]})
    st.dataframe(weight_df, use_container_width=True)
    if settled.empty or len(settled) < 5:
        st.info("Learning engine is in warm-up mode. Settle at least 5 singles to activate broader adaptation.")
    else:
        learn = compute_learning_adjustments()
        c1, c2 = st.columns(2)
        c1.metric("System State", learn["hot_cold"])
        c2.metric("Global Learning Adj", f"{learn['global_adj']:.2f}")
        st.markdown("**Market-Type Learning Adjustments**")
        mt = pd.DataFrame(list(learn["market_type_adj"].items()), columns=["market_type", "adjustment"])
        st.dataframe(mt, use_container_width=True)

with tabs[15]:
    st.subheader("Adaptive Edge AI")
    adaptive = adaptive_parlay_history_summary()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Adaptive Mode", adaptive.get("mode", "Neutral"))
    c2.metric("Confidence", adaptive.get("confidence", "Low"))
    c3.metric("Settled Parlays", adaptive.get("samples", 0))
    c4.metric("Parlay ROI", f"{safe_float(adaptive.get('total_roi'), 0.0):.2f}%")

    for note in adaptive.get("notes", []):
        st.caption("• " + str(note))

    def map_to_df(title, mapping, key_name):
        rows = []
        for k, v in mapping.items():
            rows.append({key_name: k, "samples": v.get("samples", 0), "roi": v.get("roi", 0.0), "win_rate": v.get("win_rate", 0.0)})
        st.markdown(f"**{title}**")
        if rows:
            st.dataframe(pd.DataFrame(rows).sort_values(["roi", "win_rate"], ascending=False), use_container_width=True)
        else:
            st.info("Not enough settled parlays yet.")

    map_to_df("Adaptive by Legs", adaptive.get("legs_roi", {}), "legs")
    map_to_df("Adaptive by Profile", adaptive.get("profile_roi", {}), "profile")
    map_to_df("Adaptive by Odds Bucket", adaptive.get("odds_bucket_roi", {}), "odds_bucket")
    map_to_df("Adaptive by Consensus", adaptive.get("consensus_roi", {}), "consensus")

with tabs[16]:
    st.subheader("Results + CLV AI")
    summary = settled_singles_intelligence_summary()
    adaptive_single = adaptive_single_thresholds()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Singles Mode", summary.get("mode", "Warm-up"))
    c2.metric("Settled Singles", summary.get("samples", 0))
    c3.metric("Singles ROI", f"{safe_float(summary.get('overall_roi'), 0.0):.2f}%")
    c4.metric("Avg CLV", f"{safe_float(summary.get('overall_clv'), 0.0):.2f}")
    for note in summary.get("notes", []):
        st.caption("• " + str(note))
    st.markdown("**Current Adaptive Singles Filters**")
    f1, f2 = st.columns(2)
    f1.metric("Min Confidence", f"{safe_float(adaptive_single.get('min_confidence'), 0.0):.1f}")
    f2.metric("Min Consensus", f"{int(adaptive_single.get('min_consensus', 3))}/5")
    for note in adaptive_single.get("notes", []):
        st.caption("• " + str(note))

    def map_to_df_v14(title, mapping, key_name):
        rows = []
        for k, v in mapping.items():
            rows.append({key_name: k, "samples": v.get("samples", 0), "roi": v.get("roi", 0.0), "win_rate": v.get("win_rate", 0.0), "avg_clv": v.get("avg_clv", 0.0), "beat_close_rate": v.get("beat_close_rate", 0.0)})
        st.markdown(f"**{title}**")
        if rows:
            st.dataframe(pd.DataFrame(rows).sort_values(["roi", "beat_close_rate", "avg_clv"], ascending=False), use_container_width=True)
        else:
            st.info("Not enough settled singles yet.")

    map_to_df_v14("By Sport + Market Type", summary.get("sport_market_roi", {}), "sport_market")
    map_to_df_v14("By Consensus", summary.get("consensus_roi", {}), "consensus")
    map_to_df_v14("By Odds Bucket", summary.get("odds_roi", {}), "odds_bucket")

with tabs[17]:
    st.subheader("Import / Export")
    export_text = export_state_json()
    st.download_button(
        "Download Session State JSON",
        data=export_text,
        file_name="sports_ai_v14_state.json",
        mime="application/json",
        use_container_width=True,
    )
    import_text = st.text_area("Paste exported JSON here to restore session", value="", height=180)
    if st.button("Import Session State", use_container_width=True):
        try:
            import_state_json(import_text)
            st.success("Session state imported.")
        except Exception as e:
            st.error(f"Import failed: {e}")
    x1, x2 = st.columns(2)
    with x1:
        if st.button("Force Auto-Save Now", use_container_width=True):
            save_full_auto_state()
            st.success("Auto-save completed.")
    with x2:
        if st.button("Reload Saved Logs", use_container_width=True):
            load_logs_from_disk()
            maybe_restore_full_auto_state()
            st.success("Saved logs reloaded.")

st.success("V14 Results + CLV Intelligence ready.")
