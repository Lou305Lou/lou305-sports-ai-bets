
import io
import json
from datetime import datetime, date

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Sports AI Dashboard V12.6 Stability Build", layout="wide")

# ---------- SESSION ----------
BET_LOG_COLUMNS = [
    "bet_id","added_at","bet_date","mode","sport","player","market","book","odds","line","stake","score","adjusted_score",
    "tier","units","game","bet_side","result","profit","notes","risk_mode","bankroll_snapshot",
    "model_projection","model_price_ev","model_risk","model_market","model_history",
    "multi_ai_score","clv_closing_line","clv_direction","clv_diff","clv_win"
]

DEFAULT_WEIGHTS = {
    "model_projection": 0.30,
    "model_price_ev": 0.25,
    "model_risk": 0.15,
    "model_market": 0.15,
    "model_history": 0.15,
}

if "active_df" not in st.session_state:
    st.session_state.active_df = None
if "active_source" not in st.session_state:
    st.session_state.active_source = "None"
if "bet_log" not in st.session_state:
    st.session_state.bet_log = pd.DataFrame(columns=BET_LOG_COLUMNS)
if "learning_state" not in st.session_state:
    st.session_state.learning_state = {
        "weights": DEFAULT_WEIGHTS.copy(),
        "last_recalculated_at": None,
        "warmup_needed": 12,
    }
if "bet_slip" not in st.session_state:
    st.session_state.bet_slip = []
if "launch_settings" not in st.session_state:
    st.session_state.launch_settings = {
        "starting_bankroll": 250.0,
        "risk_mode": "Balanced",
        "max_bets_per_day": 6,
        "max_daily_exposure": 75.0,
        "default_mode": "Paper",
        "lock_after_add": True,
        "min_adjusted_score": 60,
    }

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
    return ""

def market_family(market):
    text = str(market).strip().lower()
    for token in [" over", " under", " yes", " no"]:
        text = text.replace(token, "")
    return text.replace("_", " ").title()

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
        if name.endswith(".json"):
            payload = json.loads(file_bytes.decode("utf-8"))
            return payload, None
        return None, "Unsupported file type. Use CSV, Excel, or JSON."
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
    return np.nan, ""

def safe_float(x, default=0.0):
    try:
        if pd.isna(x):
            return default
        return float(x)
    except Exception:
        return default

def ensure_bet_log_shape(df):
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=BET_LOG_COLUMNS)
    out = df.copy()
    for c in BET_LOG_COLUMNS:
        if c not in out.columns:
            out[c] = np.nan
    out = out[BET_LOG_COLUMNS].copy()
    fill_text_cols = ["bet_id","added_at","bet_date","mode","sport","player","market","book","tier","game","bet_side","result","notes","risk_mode","clv_direction","clv_win"]
    for c in fill_text_cols:
        out[c] = out[c].fillna("").astype(str)
    return out

def export_state_payload():
    return {
        "active_source": st.session_state.active_source,
        "launch_settings": st.session_state.launch_settings,
        "learning_state": st.session_state.learning_state,
        "bet_log": ensure_bet_log_shape(st.session_state.bet_log).replace({np.nan: None}).to_dict(orient="records"),
    }

def import_state_payload(payload):
    if not isinstance(payload, dict):
        return False, "Invalid import file."
    if "bet_log" in payload:
        st.session_state.bet_log = ensure_bet_log_shape(pd.DataFrame(payload.get("bet_log", [])))
    if "launch_settings" in payload and isinstance(payload["launch_settings"], dict):
        merged_settings = st.session_state.launch_settings.copy()
        merged_settings.update(payload["launch_settings"])
        st.session_state.launch_settings = merged_settings
    if "learning_state" in payload and isinstance(payload["learning_state"], dict):
        merged_learning = st.session_state.learning_state.copy()
        merged_learning.update(payload["learning_state"])
        merged_learning["weights"] = normalize_weights(merged_learning.get("weights", DEFAULT_WEIGHTS.copy()))
        st.session_state.learning_state = merged_learning
    if "active_source" in payload:
        st.session_state.active_source = str(payload.get("active_source", "Imported"))
    return True, "Tracker state imported."

# ---------- SAMPLE DATA ----------
def sample_data():
    rows = [
        ["NBA","Stephen Curry","Points Over",-115,27.5,"DraftKings",32.2,4.7,66.7,None,True,"GSW","LAL","GSW @ LAL"],
        ["NBA","Stephen Curry","Points Over",-108,27.0,"Caesars",32.2,5.2,66.7,None,True,"GSW","LAL","GSW @ LAL"],
        ["NBA","LeBron James","PRA Over",-110,38.5,"FanDuel",43.8,5.3,64.8,None,True,"LAL","GSW","GSW @ LAL"],
        ["NHL","Connor McDavid","Shots Over",-120,3.5,"DraftKings",4.3,0.8,58.0,None,True,"EDM","CGY","EDM @ CGY"],
        ["NHL","Auston Matthews","Goals Over",145,0.5,"FanDuel",0.72,0.22,43.0,None,True,"TOR","MTL","TOR @ MTL"],
        ["MLB","Aaron Judge","Hits Over",-135,1.5,"Caesars",1.9,0.4,57.5,None,True,"NYY","BOS","NYY @ BOS"],
        ["MLB","Mookie Betts","Total Bases Over",110,1.5,"BetMGM",1.95,0.45,55.0,None,True,"LAD","SF","LAD @ SF"],
    ]
    return pd.DataFrame(
        rows,
        columns=["sport","player","market","odds","point","book","projection","edge","hit_pct","score","is_starter","team","opponent","game"]
    )

# ---------- LEARNING ----------
def get_settled_log():
    log = ensure_bet_log_shape(st.session_state.bet_log.copy())
    if log.empty:
        return log
    log = to_numeric_safe(log, ["stake", "profit", "score", "adjusted_score", "multi_ai_score", "clv_diff",
                                "model_projection","model_price_ev","model_risk","model_market","model_history"])
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

def normalize_weights(weights):
    base = DEFAULT_WEIGHTS.copy()
    if isinstance(weights, dict):
        for key in base:
            try:
                if key in weights:
                    base[key] = max(0.01, float(weights[key]))
            except Exception:
                pass
    total = sum(base.values())
    if total <= 0:
        return DEFAULT_WEIGHTS.copy()
    return {k: v / total for k, v in base.items()}

def compute_learning_adjustments():
    settled = get_settled_log()
    defaults = {
        "market_adj": {}, "tier_adj": {}, "score_adj": {}, "global_adj": 0.0, "hot_cold": "Neutral",
        "roi": 0.0, "settled_count": int(len(settled))
    }
    if settled.empty or len(settled) < 5:
        return defaults
    settled["win_flag"] = (settled["result"] == "Win").astype(int)
    settled["score_bucket"] = settled["score"].apply(stable_score_bucket)
    profit_sum = settled["profit"].fillna(0).sum()
    staked_sum = settled["stake"].fillna(0).sum()
    roi = (profit_sum / staked_sum * 100) if staked_sum > 0 else 0.0
    defaults["roi"] = round(roi, 2)
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
    return defaults

def compute_adaptive_weights():
    settled = get_settled_log()
    warmup_needed = int(st.session_state.learning_state.get("warmup_needed", 12))
    if settled.empty or len(settled) < warmup_needed:
        return DEFAULT_WEIGHTS.copy(), False

    work = settled.copy()
    work["profit"] = pd.to_numeric(work["profit"], errors="coerce").fillna(0.0)
    score_cols = ["model_projection","model_price_ev","model_risk","model_market","model_history"]
    scores = {}
    for col in score_cols:
        series = pd.to_numeric(work[col], errors="coerce")
        valid = series.notna()
        if valid.sum() < max(5, warmup_needed // 2):
            scores[col] = 0.0
            continue
        corr = series[valid].corr(work.loc[valid, "profit"])
        if pd.isna(corr):
            corr = 0.0
        top_half = work.loc[valid & (series >= series.median()), "profit"].mean()
        bottom_half = work.loc[valid & (series < series.median()), "profit"].mean()
        edge = 0.0 if pd.isna(top_half) or pd.isna(bottom_half) else (top_half - bottom_half)
        score = max(0.0, (corr + 1.0) / 2.0) + max(0.0, edge / 10.0)
        scores[col] = score

    base = DEFAULT_WEIGHTS.copy()
    adjusted = {}
    for col in score_cols:
        adjusted[col] = base[col] * (1.0 + scores[col])

    adjusted = normalize_weights(adjusted)
    return adjusted, True

def refresh_learning_state():
    new_weights, active = compute_adaptive_weights()
    st.session_state.learning_state["weights"] = normalize_weights(new_weights)
    st.session_state.learning_state["adaptive_active"] = active
    st.session_state.learning_state["last_recalculated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def apply_learning_layer(df):
    out = df.copy()
    learn = compute_learning_adjustments()
    out["score_bucket"] = out["score"].apply(stable_score_bucket)
    out["market_learning_adj"] = out["market"].map(learn["market_adj"]).fillna(0.0)
    out["tier_learning_adj"] = out["tier"].map(learn["tier_adj"]).fillna(0.0)
    out["score_learning_adj"] = out["score_bucket"].map(learn["score_adj"]).fillna(0.0)
    out["global_learning_adj"] = learn["global_adj"]
    out["learning_boost"] = out["market_learning_adj"] + out["tier_learning_adj"] + out["score_learning_adj"] + out["global_learning_adj"]
    out["adjusted_score"] = np.clip(out["score"].fillna(0) + out["learning_boost"], 1, 99)
    out["learning_state"] = learn["hot_cold"]
    return out

# ---------- SPORT ENGINE ----------
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
        return 65
    if sport == "MLB":
        return 70
    return 60

def build_engine(df):
    df = normalize_columns(df)
    df = to_numeric_safe(df, ["odds","point","projection","edge","hit_pct","score","ev_edge","units"])

    if "sport" not in df.columns:
        if "league" in df.columns:
            df["sport"] = df["league"].astype(str).str.upper()
        else:
            df["sport"] = "NBA"

    if "line" not in df.columns and "point" in df.columns:
        df["line"] = df["point"]
    if "bet_side" not in df.columns:
        df["bet_side"] = df["market"].apply(detect_side) if "market" in df.columns else ""
    if "market_family" not in df.columns:
        df["market_family"] = df["market"].apply(market_family) if "market" in df.columns else ""
    if "implied_prob" not in df.columns and "odds" in df.columns:
        df["implied_prob"] = df["odds"].apply(implied_prob) * 100
    if "break_even_pct" not in df.columns and "odds" in df.columns:
        df["break_even_pct"] = df["odds"].apply(implied_prob) * 100
    if "edge" not in df.columns:
        df["edge"] = df["projection"] - df["line"] if "projection" in df.columns and "line" in df.columns else 0.0
    if "hit_pct" not in df.columns:
        df["hit_pct"] = np.clip(50 + df["edge"].fillna(0) * 3.5, 35, 75)
    else:
        missing = df["hit_pct"].isna()
        df.loc[missing, "hit_pct"] = np.clip(50 + df.loc[missing, "edge"].fillna(0) * 3.5, 35, 75)

    if "ev_edge" not in df.columns:
        df["ev_edge"] = np.nan
    missing_ev = df["ev_edge"].isna()
    df.loc[missing_ev, "ev_edge"] = df.loc[missing_ev].apply(
        lambda r: calc_ev(r["hit_pct"], r["odds"]) if pd.notna(r.get("hit_pct")) and pd.notna(r.get("odds")) else np.nan,
        axis=1,
    )

    if "model_projection" not in df.columns:
        df["model_projection"] = np.clip(50 + df["edge"].fillna(0) * 8, 0, 100)
    if "model_price_ev" not in df.columns:
        df["model_price_ev"] = np.clip(50 + df["ev_edge"].fillna(0) * 1.8, 0, 100)
    if "model_risk" not in df.columns:
        base_risk = np.where(df["odds"].fillna(0) >= 120, 48, np.where(df["odds"].fillna(0) <= -170, 68, 58))
        starter_bonus = np.where(df.get("is_starter", pd.Series(False, index=df.index)).astype(str).str.lower().isin(["true","1","yes"]), 6, 0)
        df["model_risk"] = np.clip(base_risk + starter_bonus, 0, 100)
    if "model_market" not in df.columns:
        df["model_market"] = np.clip(50 + (df["hit_pct"].fillna(50) - df["break_even_pct"].fillna(50)) * 2.0, 0, 100)
    if "model_history" not in df.columns:
        df["model_history"] = np.select([df["score"].fillna(0) >= 84, df["score"].fillna(0) >= 72, df["score"].fillna(0) >= 60], [72, 62, 54], default=45)

    weights = normalize_weights(st.session_state.learning_state.get("weights", DEFAULT_WEIGHTS.copy()))
    df["multi_ai_score"] = (
        df["model_projection"].fillna(50) * weights["model_projection"] +
        df["model_price_ev"].fillna(50) * weights["model_price_ev"] +
        df["model_risk"].fillna(50) * weights["model_risk"] +
        df["model_market"].fillna(50) * weights["model_market"] +
        df["model_history"].fillna(50) * weights["model_history"]
    )

    if "score" not in df.columns:
        df["score"] = np.nan
    need_score = df["score"].isna()
    edge_component = np.clip(df["edge"].fillna(0) * 6, -10, 35)
    hit_component = np.clip((df["hit_pct"].fillna(50) - 50) * 1.5, -10, 35)
    ev_component = np.clip(df["ev_edge"].fillna(0) * 0.8, -10, 30)
    starter_bonus = np.where(df.get("is_starter", pd.Series(False, index=df.index)).astype(str).str.lower().isin(["true","1","yes"]), 4, 0)
    df.loc[need_score, "score"] = np.clip(
        0.55 * df.loc[need_score, "multi_ai_score"].fillna(50)
        + 20 + edge_component[need_score] + hit_component[need_score] + ev_component[need_score] + starter_bonus[need_score],
        1, 99
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
    df["units"] = (df["units"].fillna(0) * df["sport_unit_mult"]).round(2)
    return df

def filtered_launch_ready(df):
    refresh_learning_state()
    out = build_engine(df)
    out = apply_learning_layer(out)
    out = out[out["adjusted_score"] >= out["sport_min_score"]].copy()
    return out

def best_bets(df):
    out = df.copy()
    out = out[out["units"].fillna(0) > 0].copy()
    return out.sort_values(["adjusted_score", "multi_ai_score", "score", "ev_edge"], ascending=False)

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
    return f"{row.get('sport','')}|{row.get('player','')}|{row.get('market','')}|{row.get('book','')}|{row.get('line','')}"

def add_to_slip(row, stake, bankroll, risk_mode):
    key = slip_key(row)
    current = [x for x in st.session_state.bet_slip if x["slip_key"] != key]
    item = {
        "slip_key": key,
        "sport": row.get("sport",""),
        "player": row.get("player",""),
        "market": row.get("market",""),
        "book": row.get("book",""),
        "odds": row.get("odds",np.nan),
        "line": row.get("line",np.nan),
        "stake": round(float(stake), 2),
        "score": row.get("score",np.nan),
        "adjusted_score": row.get("adjusted_score",np.nan),
        "tier": row.get("tier",""),
        "units": row.get("units",np.nan),
        "game": row.get("game",""),
        "bet_side": row.get("bet_side",""),
        "risk_mode": risk_mode,
        "bankroll_snapshot": bankroll,
        "model_projection": row.get("model_projection",np.nan),
        "model_price_ev": row.get("model_price_ev",np.nan),
        "model_risk": row.get("model_risk",np.nan),
        "model_market": row.get("model_market",np.nan),
        "model_history": row.get("model_history",np.nan),
        "multi_ai_score": row.get("multi_ai_score",np.nan),
    }
    current.append(item)
    st.session_state.bet_slip = current

def remove_from_slip(slip_key_value):
    st.session_state.bet_slip = [x for x in st.session_state.bet_slip if x["slip_key"] != slip_key_value]

def clear_slip():
    st.session_state.bet_slip = []

def slip_summary():
    slip = pd.DataFrame(st.session_state.bet_slip)
    if slip.empty:
        return {"bets":0,"stake":0.0,"games":0,"players":0,"sports":0,"same_game_extra":0,"same_player_extra":0}
    game_counts = slip["game"].value_counts()
    player_counts = slip["player"].value_counts()
    return {
        "bets": len(slip),
        "stake": round(float(pd.to_numeric(slip["stake"], errors="coerce").fillna(0).sum()), 2),
        "games": int(slip["game"].nunique()),
        "players": int(slip["player"].nunique()),
        "sports": int(slip["sport"].nunique()),
        "same_game_extra": int(sum(max(0, x - 1) for x in game_counts)),
        "same_player_extra": int(sum(max(0, x - 1) for x in player_counts)),
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
    log = ensure_bet_log_shape(st.session_state.bet_log.copy())
    if log.empty:
        return log
    if "bet_date" in log.columns and log["bet_date"].astype(str).str.len().gt(0).any():
        return log
    log["bet_date"] = pd.to_datetime(log["added_at"], errors="coerce").dt.date.astype(str)
    return log

def today_counts_and_exposure():
    log = daily_log_df()
    if log.empty:
        return 0, 0.0
    today_str = str(date.today())
    today_log = log[log["bet_date"].astype(str) == today_str].copy()
    total_bets = len(today_log)
    total_stake = float(pd.to_numeric(today_log["stake"], errors="coerce").fillna(0).sum())
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

def confirm_slip_to_tracker(mode):
    count = 0
    for item in st.session_state.bet_slip:
        add_bet_to_log(item, item["stake"], item["risk_mode"], item["bankroll_snapshot"], mode)
        count += 1
    clear_slip()
    refresh_learning_state()
    return count

# ---------- TRACKER ----------
def add_bet_to_log(row, stake, risk_mode, bankroll_snapshot, mode):
    log = ensure_bet_log_shape(st.session_state.bet_log.copy())
    bet_id = f"BET-{len(log)+1:04d}"
    bet_date = str(date.today())
    new_row = {
        "bet_id": bet_id,
        "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "bet_date": bet_date,
        "mode": mode,
        "sport": row.get("sport",""),
        "player": row.get("player",""),
        "market": row.get("market",""),
        "book": row.get("book",""),
        "odds": row.get("odds",np.nan),
        "line": row.get("line", row.get("point",np.nan)),
        "stake": round(float(stake),2),
        "score": row.get("score",np.nan),
        "adjusted_score": row.get("adjusted_score",np.nan),
        "tier": row.get("tier",""),
        "units": row.get("units",np.nan),
        "game": row.get("game",""),
        "bet_side": row.get("bet_side",""),
        "result": "Pending",
        "profit": np.nan,
        "notes": "",
        "risk_mode": risk_mode,
        "bankroll_snapshot": round(float(bankroll_snapshot),2),
        "model_projection": row.get("model_projection",np.nan),
        "model_price_ev": row.get("model_price_ev",np.nan),
        "model_risk": row.get("model_risk",np.nan),
        "model_market": row.get("model_market",np.nan),
        "model_history": row.get("model_history",np.nan),
        "multi_ai_score": row.get("multi_ai_score",np.nan),
        "clv_closing_line": np.nan,
        "clv_direction": row.get("bet_side",""),
        "clv_diff": np.nan,
        "clv_win": "",
    }
    st.session_state.bet_log = ensure_bet_log_shape(pd.concat([log, pd.DataFrame([new_row])], ignore_index=True))

def refresh_bet_log_metrics():
    log = ensure_bet_log_shape(st.session_state.bet_log.copy())
    if log.empty:
        return {"total_bets":0,"settled_bets":0,"wins":0,"losses":0,"pushes":0,"pending":0,"total_staked":0.0,"profit":0.0,"roi":0.0,"win_rate":0.0}
    settled = log[log["result"].isin(["Win","Loss","Push"])].copy()
    total_staked = pd.to_numeric(log["stake"], errors="coerce").fillna(0).sum()
    settled_profit = pd.to_numeric(settled["profit"], errors="coerce").fillna(0).sum()
    wins = int((log["result"] == "Win").sum())
    losses = int((log["result"] == "Loss").sum())
    pushes = int((log["result"] == "Push").sum())
    pending = int((log["result"] == "Pending").sum())
    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0.0
    roi = (settled_profit / total_staked * 100) if total_staked > 0 else 0.0
    return {"total_bets":len(log),"settled_bets":len(settled),"wins":wins,"losses":losses,"pushes":pushes,"pending":pending,"total_staked":round(total_staked,2),"profit":round(settled_profit,2),"roi":round(roi,2),"win_rate":round(win_rate,2)}

def clv_summary_table():
    settled = get_settled_log()
    if settled.empty:
        return pd.DataFrame()
    work = settled.copy()
    work["clv_diff"] = pd.to_numeric(work["clv_diff"], errors="coerce")
    work["beat_close_flag"] = work["clv_win"].eq("Beat Close").astype(int)
    summary = work.groupby(["sport","market","book"], dropna=False).agg(
        bets=("bet_id","count"),
        avg_clv=("clv_diff","mean"),
        beat_close_rate=("beat_close_flag","mean"),
        profit=("profit","sum")
    ).reset_index()
    summary["beat_close_rate"] = (summary["beat_close_rate"] * 100).round(2)
    summary["avg_clv"] = summary["avg_clv"].round(2)
    summary["profit"] = summary["profit"].round(2)
    return summary.sort_values(["profit","avg_clv"], ascending=False)

# ---------- RENDER ----------
def render_mobile_bet_picker(df, bankroll, risk_mode, drawdown_pct, roi_pct, key_prefix):
    if df.empty:
        st.info("No qualified plays available.")
        return
    work = df.copy().reset_index(drop=True)
    work["suggested_stake"] = work["units"].apply(lambda u: suggested_stake_from_units(u, bankroll, risk_mode, drawdown_pct, roi_pct))
    st.subheader("Launch Selector")
    st.caption("Add plays to slip, then confirm them to tracker in Paper or Live mode.")
    for i, row in work.head(20).iterrows():
        st.markdown("**" + str(row.get("sport","")) + " | " + str(row.get("player","")) + " - " + str(row.get("market","")) + "**")
        st.write(str(row.get("book","")) + " | Odds: " + str(row.get("odds","")) + " | Line: " + str(row.get("line","")))
        st.write("Score: " + f"{safe_float(row.get('score')):.1f}" + " | Adjusted: " + f"{safe_float(row.get('adjusted_score')):.1f}" + " | Multi-AI: " + f"{safe_float(row.get('multi_ai_score')):.1f}")
        st.write(str(row.get("tier","")) + " | Units: " + f"{safe_float(row.get('units')):.2f}" + "u | Suggested Stake: $" + f"{safe_float(row.get('suggested_stake')):.2f}")
        st.write("Game: " + str(row.get("game","")) + " | Sport Mult: " + f"{safe_float(row.get('sport_unit_mult'), 1.0):.2f}" + "x")
        c1, c2 = st.columns([1,1])
        with c1:
            custom_stake = st.number_input("Stake", min_value=1.0, value=float(max(1.0, safe_float(row.get("suggested_stake"), 1.0))), step=1.0, key=f"{key_prefix}_stake_{i}")
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
    slip_show = slip[[c for c in ["sport","player","market","book","odds","line","stake","adjusted_score","tier","game"] if c in slip.columns]]
    st.dataframe(slip_show, use_container_width=True)

    for i, item in slip.reset_index(drop=True).iterrows():
        label = f"{item['sport']} | {item['player']} - {item['market']} | ${float(item['stake']):.2f}"
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

# ---------- APP ----------
st.title("Sports AI Dashboard V12.6 Stability Build")
st.caption("Adaptive weights, launch guardrails, export/import support, safer analytics, and upgraded CLV review.")

tabs = st.tabs([
    "Dashboard","Data Input","Launch Settings","Launch Board","Auto Unit AI","Bet Slip",
    "CLV Tracker","Bet Tracker","Performance","Sport Stats","30-Day Test","Multi-AI Lab","Learning Dashboard"
])

with tabs[0]:
    st.write("Active Source:", st.session_state.active_source)
    metrics = refresh_bet_log_metrics()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tracked Bets", metrics["total_bets"])
    c2.metric("Profit", f"${metrics['profit']:.2f}")
    c3.metric("ROI", f"{metrics['roi']:.2f}%")
    c4.metric("Win Rate", f"{metrics['win_rate']:.1f}%")
    d1, d2, d3 = st.columns(3)
    today_bets, today_stake = today_counts_and_exposure()
    d1.metric("Today's Bets", today_bets)
    d2.metric("Today's Exposure", f"${today_stake:.2f}")
    d3.metric("Adaptive Weights", "On" if st.session_state.learning_state.get("adaptive_active") else "Warm-Up")
    st.caption("Last weight refresh: " + str(st.session_state.learning_state.get("last_recalculated_at", "Not yet")))

with tabs[1]:
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Load Sample Multi-Sport Data", use_container_width=True):
            st.session_state.active_df = sample_data()
            st.session_state.active_source = "Sample"
            st.success("Sample data loaded.")
    with c2:
        if st.button("Clear Active Data", use_container_width=True):
            st.session_state.active_df = None
            st.session_state.active_source = "None"
            st.warning("Active data cleared.")

    uploaded_file = st.file_uploader("Choose CSV or Excel for active board", type=["csv","xlsx","xls"])
    if uploaded_file is not None:
        df_upload, err = read_uploaded_file(uploaded_file)
        if err:
            st.error(err)
        elif isinstance(df_upload, pd.DataFrame):
            st.session_state.active_df = df_upload
            st.session_state.active_source = f"Uploaded: {uploaded_file.name}"
            st.success("File loaded.")

    sample_text = "sport,player,market,odds,point,book,projection,edge,hit_pct,is_starter,team,opponent,game\nNBA,Stephen Curry,Points Over,-115,27.5,DraftKings,32.2,4.7,66.7,True,GSW,LAL,GSW @ LAL\nNHL,Connor McDavid,Shots Over,-120,3.5,DraftKings,4.3,0.8,58.0,True,EDM,CGY,EDM @ CGY"
    txt = st.text_area("Paste CSV here", value="", height=180, placeholder=sample_text)
    if st.button("Load Pasted Data", use_container_width=True):
        df_paste, err = parse_csv_text(txt)
        if err:
            st.error(err)
        else:
            st.session_state.active_df = df_paste
            st.session_state.active_source = "Pasted CSV"
            st.success("Pasted data loaded.")

    st.divider()
    st.subheader("Export / Import Tracker State")
    export_bytes = json.dumps(export_state_payload(), indent=2).encode("utf-8")
    st.download_button("Download tracker_state_v12_6.json", data=export_bytes, file_name="tracker_state_v12_6.json", mime="application/json", use_container_width=True)
    import_file = st.file_uploader("Import tracker state JSON", type=["json"], key="state_import_json")
    if import_file is not None:
        imported_payload, err = read_uploaded_file(import_file)
        if err:
            st.error(err)
        else:
            ok, msg = import_state_payload(imported_payload)
            if ok:
                st.success(msg)
                refresh_learning_state()
            else:
                st.error(msg)

    if st.session_state.active_df is not None:
        preview = filtered_launch_ready(st.session_state.active_df)
        st.dataframe(preview.head(20), use_container_width=True)

with tabs[2]:
    st.subheader("Launch Settings")
    settings = st.session_state.launch_settings
    settings["starting_bankroll"] = st.number_input("Starting bankroll ($)", min_value=25.0, value=float(settings["starting_bankroll"]), step=25.0)
    settings["risk_mode"] = st.selectbox("Default risk mode", ["Conservative", "Balanced", "Aggressive"], index=["Conservative", "Balanced", "Aggressive"].index(settings["risk_mode"]))
    settings["max_bets_per_day"] = st.number_input("Max bets per day", min_value=1, max_value=20, value=int(settings["max_bets_per_day"]), step=1)
    settings["max_daily_exposure"] = st.number_input("Max daily exposure ($)", min_value=10.0, value=float(settings["max_daily_exposure"]), step=5.0)
    settings["default_mode"] = st.selectbox("Default tracking mode", ["Paper", "Live"], index=0 if settings["default_mode"] == "Paper" else 1)
    settings["lock_after_add"] = st.toggle("Lock bet details after adding to tracker", value=bool(settings["lock_after_add"]))
    settings["min_adjusted_score"] = st.slider("Launch minimum adjusted score", 0, 100, int(settings["min_adjusted_score"]))
    warmup = int(st.session_state.learning_state.get("warmup_needed", 12))
    st.session_state.learning_state["warmup_needed"] = st.slider("Adaptive weights warm-up settled bets", 5, 50, warmup)
    st.success("Launch settings saved in session.")

with tabs[3]:
    if st.session_state.active_df is None:
        st.info("Load data first.")
    else:
        df = filtered_launch_ready(st.session_state.active_df)
        sport_options = sorted(df["sport"].dropna().astype(str).unique().tolist()) if "sport" in df.columns else []
        book_options = sorted(df["book"].dropna().astype(str).unique().tolist()) if "book" in df.columns else []
        tier_options = sorted(df["tier"].dropna().astype(str).unique().tolist()) if "tier" in df.columns else []
        f1, f2, f3 = st.columns(3)
        with f1:
            selected_sports = st.multiselect("Sports", sport_options, default=sport_options)
        with f2:
            selected_books = st.multiselect("Books", book_options, default=book_options)
        with f3:
            selected_tiers = st.multiselect("Tiers", tier_options, default=tier_options)
        min_adjusted = st.slider("Min adjusted score", 0, 100, int(st.session_state.launch_settings["min_adjusted_score"]), key="launchboard_min")
        odds_min, odds_max = st.slider("Odds range", -500, 500, (-150, 200), key="launchboard_odds")
        filtered = df.copy()
        if selected_sports:
            filtered = filtered[filtered["sport"].astype(str).isin(selected_sports)]
        if selected_books:
            filtered = filtered[filtered["book"].astype(str).isin(selected_books)]
        if selected_tiers:
            filtered = filtered[filtered["tier"].astype(str).isin(selected_tiers)]
        filtered = filtered[
            (filtered["adjusted_score"].fillna(0) >= min_adjusted) &
            (filtered["odds"].fillna(0) >= odds_min) &
            (filtered["odds"].fillna(0) <= odds_max)
        ]
        filtered = best_bets(filtered)

        bankroll_quick = st.number_input("Bankroll for selector ($)", min_value=25.0, value=float(st.session_state.launch_settings["starting_bankroll"]), step=25.0, key="launch_bankroll")
        risk_mode_quick = st.selectbox("Risk mode", ["Conservative","Balanced","Aggressive"], index=["Conservative","Balanced","Aggressive"].index(st.session_state.launch_settings["risk_mode"]), key="launch_risk")
        drawdown_quick = st.number_input("Drawdown %", min_value=0.0, max_value=100.0, value=0.0, step=1.0, key="launch_drawdown")
        roi_quick = st.number_input("ROI %", value=float(refresh_bet_log_metrics()["roi"]), step=0.5, key="launch_roi")

        st.dataframe(filtered[[c for c in ["sport","player","market","book","odds","line","score","adjusted_score","tier","units","game"] if c in filtered.columns]], use_container_width=True)
        render_mobile_bet_picker(filtered, bankroll_quick, risk_mode_quick, drawdown_quick, roi_quick, "launch_picker")
        render_bet_slip("launch_board")

with tabs[4]:
    st.subheader("Auto Unit AI")
    metrics = refresh_bet_log_metrics()
    bankroll = st.number_input("Current bankroll ($)", min_value=25.0, value=float(st.session_state.launch_settings["starting_bankroll"]), step=25.0)
    risk_mode = st.selectbox("Risk mode", ["Conservative","Balanced","Aggressive"], index=["Conservative","Balanced","Aggressive"].index(st.session_state.launch_settings["risk_mode"]))
    drawdown_pct = st.number_input("Current drawdown %", min_value=0.0, max_value=100.0, value=0.0, step=1.0)
    roi_input = st.number_input("Current ROI %", value=float(metrics["roi"]), step=0.5)
    st.success(f"Recommended unit multiplier: {recommended_unit_multiplier(risk_mode, bankroll, drawdown_pct, roi_input)}x")
    if st.session_state.active_df is None:
        st.info("Load data first.")
    else:
        ai_df = best_bets(filtered_launch_ready(st.session_state.active_df)).reset_index(drop=True)
        render_mobile_bet_picker(ai_df, bankroll, risk_mode, drawdown_pct, roi_input, "auto_unit")
        render_bet_slip("auto_unit")

with tabs[5]:
    render_bet_slip("bet_slip")

with tabs[6]:
    st.subheader("CLV Tracker")
    log = ensure_bet_log_shape(st.session_state.bet_log.copy())
    if log.empty:
        st.info("No tracked bets yet.")
    else:
        editable_idx = st.selectbox("Select tracked bet", options=list(log.index), format_func=lambda i: f"{log.loc[i, 'bet_id']} | {log.loc[i, 'mode']} | {log.loc[i, 'sport']} | {log.loc[i, 'player']} {log.loc[i, 'market']}")
        current = log.loc[editable_idx]
        default_line = safe_float(current["clv_closing_line"], safe_float(current["line"], 0.0))
        closing_line = st.number_input("Closing line", value=float(default_line), step=0.5)
        if st.button("Save CLV", use_container_width=True):
            st.session_state.bet_log.loc[editable_idx, "clv_closing_line"] = closing_line
            diff, result = clv_result(st.session_state.bet_log.loc[editable_idx])
            st.session_state.bet_log.loc[editable_idx, "clv_diff"] = diff
            st.session_state.bet_log.loc[editable_idx, "clv_win"] = result
            st.success("CLV updated.")
            st.rerun()
        st.dataframe(st.session_state.bet_log[[c for c in ["bet_id","mode","sport","player","market","bet_side","line","clv_closing_line","clv_diff","clv_win","result"] if c in st.session_state.bet_log.columns]], use_container_width=True)
        st.divider()
        clv_summary = clv_summary_table()
        if clv_summary.empty:
            st.info("Settle bets and save CLV to unlock CLV summary.")
        else:
            st.dataframe(clv_summary, use_container_width=True)

with tabs[7]:
    st.subheader("Bet Tracker")
    log = ensure_bet_log_shape(st.session_state.bet_log.copy())
    if log.empty:
        st.info("No bets tracked yet.")
    else:
        lock_after_add = bool(st.session_state.launch_settings["lock_after_add"])
        for i in range(len(log)):
            with st.expander(f"{log.loc[i, 'bet_id']} | {log.loc[i, 'mode']} | {log.loc[i, 'sport']} | {log.loc[i, 'player']} {log.loc[i, 'market']}", expanded=False):
                st.write(f"Book: {log.loc[i, 'book']} | Odds: {log.loc[i, 'odds']} | Stake: ${safe_float(log.loc[i, 'stake']):.2f}")
                result = st.selectbox(
                    f"Result for {log.loc[i, 'bet_id']}",
                    ["Pending","Win","Loss","Push"],
                    index=["Pending","Win","Loss","Push"].index(log.loc[i, "result"]) if log.loc[i, "result"] in ["Pending","Win","Loss","Push"] else 0,
                    key=f"result_{i}",
                )
                notes = st.text_input("Notes", value=str(log.loc[i, "notes"]), key=f"notes_{i}")
                if lock_after_add:
                    st.caption("Bet details are locked after add. You can still update result, notes, and CLV.")
                else:
                    stake_edit = st.number_input("Stake override", min_value=1.0, value=float(max(1.0, safe_float(log.loc[i, "stake"], 1.0))), step=1.0, key=f"stake_edit_{i}")
                    odds_edit = st.number_input("Odds override", value=float(safe_float(log.loc[i, "odds"], 0.0)), step=1.0, key=f"odds_edit_{i}")
                if st.button(f"Save {log.loc[i, 'bet_id']}", key=f"save_{i}"):
                    log.loc[i, "result"] = result
                    log.loc[i, "notes"] = notes
                    if not lock_after_add:
                        log.loc[i, "stake"] = stake_edit
                        log.loc[i, "odds"] = odds_edit
                    log.loc[i, "profit"] = settle_profit(log.loc[i, "odds"], log.loc[i, "stake"], result)
                    st.session_state.bet_log = ensure_bet_log_shape(log.copy())
                    refresh_learning_state()
                    st.success("Bet updated.")
                    st.rerun()
        st.dataframe(st.session_state.bet_log, use_container_width=True)

with tabs[8]:
    st.subheader("Performance")
    metrics = refresh_bet_log_metrics()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Settled Bets", metrics["settled_bets"])
    c2.metric("Profit", f"${metrics['profit']:.2f}")
    c3.metric("ROI", f"{metrics['roi']:.2f}%")
    c4.metric("Win Rate", f"{metrics['win_rate']:.2f}%")
    settled = get_settled_log()
    if settled.empty:
        st.info("No settled bets yet.")
    else:
        perf = settled.groupby(["mode","sport"], dropna=False).agg(
            bets=("bet_id","count"),
            profit=("profit","sum"),
            avg_score=("score","mean"),
            avg_adjusted=("adjusted_score","mean"),
            win_rate=("result", lambda s: round((s.eq("Win").sum() / max(1, s.isin(["Win","Loss"]).sum())) * 100, 2))
        ).reset_index()
        perf["profit"] = perf["profit"].round(2)
        perf["avg_score"] = perf["avg_score"].round(2)
        perf["avg_adjusted"] = perf["avg_adjusted"].round(2)
        st.dataframe(perf, use_container_width=True)

with tabs[9]:
    st.subheader("Sport Stats")
    settled = get_settled_log()
    if settled.empty:
        st.info("No settled bets yet.")
    else:
        by_sport = settled.groupby(["mode","sport"], dropna=False).agg(
            bets=("bet_id","count"),
            wins=("result", lambda s: int((s=="Win").sum())),
            losses=("result", lambda s: int((s=="Loss").sum())),
            profit=("profit","sum"),
            avg_clv=("clv_diff","mean"),
        ).reset_index()
        by_sport["profit"] = by_sport["profit"].round(2)
        by_sport["avg_clv"] = by_sport["avg_clv"].round(2)
        st.dataframe(by_sport, use_container_width=True)

with tabs[10]:
    st.subheader("30-Day Test Dashboard")
    log = daily_log_df()
    if log.empty:
        st.info("No tracked bets yet.")
    else:
        work = log.copy()
        work["profit"] = pd.to_numeric(work["profit"], errors="coerce").fillna(0.0)
        work["stake"] = pd.to_numeric(work["stake"], errors="coerce").fillna(0.0)
        daily = work.groupby(["bet_date","mode"], dropna=False).agg(
            bets=("bet_id","count"),
            risk=("stake","sum"),
            profit=("profit","sum"),
        ).reset_index()
        daily["cum_profit"] = daily.groupby("mode")["profit"].cumsum()
        daily["starting_bankroll"] = float(st.session_state.launch_settings["starting_bankroll"])
        daily["roll"] = daily["starting_bankroll"] + daily["cum_profit"]
        daily["risk"] = daily["risk"].round(2)
        daily["profit"] = daily["profit"].round(2)
        daily["roll"] = daily["roll"].round(2)
        st.dataframe(daily, use_container_width=True)

with tabs[11]:
    st.subheader("Multi-AI Lab")
    if st.session_state.active_df is None:
        st.info("Load data first.")
    else:
        df = best_bets(filtered_launch_ready(st.session_state.active_df)).reset_index(drop=True)
        st.dataframe(df[[c for c in [
            "sport","player","market","book","model_projection","model_price_ev","model_risk",
            "model_market","model_history","multi_ai_score","score","learning_boost","adjusted_score",
            "sport_unit_mult","sport_min_score","tier","units"
        ] if c in df.columns]], use_container_width=True)

with tabs[12]:
    st.subheader("Learning Dashboard")
    settled = get_settled_log()
    refresh_learning_state()
    learn = compute_learning_adjustments()
    weights = normalize_weights(st.session_state.learning_state.get("weights", DEFAULT_WEIGHTS.copy()))
    weight_df = pd.DataFrame({
        "model": list(weights.keys()),
        "weight": [round(v, 4) for v in weights.values()],
        "default_weight": [round(DEFAULT_WEIGHTS[k], 4) for k in weights.keys()],
        "delta": [round(weights[k] - DEFAULT_WEIGHTS[k], 4) for k in weights.keys()],
    })
    st.dataframe(weight_df, use_container_width=True)
    x1, x2, x3 = st.columns(3)
    x1.metric("System State", learn["hot_cold"])
    x2.metric("Global Learning Adj", f"{learn['global_adj']:.2f}")
    x3.metric("Settled Bets", int(learn["settled_count"]))
    if settled.empty or len(settled) < 5:
        st.info("Learning engine is in stable warm-up mode. Settle at least 5 bets to activate score adjustments.")
    else:
        st.success(f"Learning adjustments active. Current learning ROI: {learn['roi']:.2f}%")
        st.write("Market adjustments")
        st.dataframe(pd.DataFrame(sorted(learn["market_adj"].items()), columns=["market", "adj"]).sort_values("adj", ascending=False), use_container_width=True)
        st.write("Tier adjustments")
        st.dataframe(pd.DataFrame(sorted(learn["tier_adj"].items()), columns=["tier", "adj"]).sort_values("adj", ascending=False), use_container_width=True)
        st.write("Score bucket adjustments")
        st.dataframe(pd.DataFrame(sorted(learn["score_adj"].items()), columns=["score_bucket", "adj"]).sort_values("adj", ascending=False), use_container_width=True)
    if not st.session_state.learning_state.get("adaptive_active"):
        st.caption(f"Adaptive weights stay in warm-up until {st.session_state.learning_state.get('warmup_needed', 12)} settled bets.")
    else:
        st.caption("Adaptive weights are live and updating from settled performance.")

st.success("V12.6 Stability Build ready.")
