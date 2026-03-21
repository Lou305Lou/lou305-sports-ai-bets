
import io
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Sports AI Dashboard V12.4.1 Pro", layout="wide")

# ---------- SESSION ----------
if "active_df" not in st.session_state:
    st.session_state.active_df = None
if "active_source" not in st.session_state:
    st.session_state.active_source = "None"
if "bet_log" not in st.session_state:
    st.session_state.bet_log = pd.DataFrame(columns=[
        "bet_id","added_at","sport","player","market","book","odds","line","stake","score","adjusted_score",
        "tier","units","game","bet_side","result","profit","notes","risk_mode","bankroll_snapshot",
        "model_projection","model_price_ev","model_risk","model_market","model_history",
        "multi_ai_score","clv_closing_line","clv_direction","clv_diff","clv_win"
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
    log = st.session_state.bet_log.copy()
    if log.empty:
        return log
    log = to_numeric_safe(log, ["stake", "profit", "score", "adjusted_score", "multi_ai_score", "clv_diff"])
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

def compute_learning_adjustments():
    settled = get_settled_log()
    defaults = {"market_adj": {}, "tier_adj": {}, "score_adj": {}, "global_adj": 0.0, "hot_cold": "Neutral"}
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
    return defaults

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

    weights = st.session_state.learning_state["weights"]
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

    df["tier"] = np.select(
        [df["score"] >= 84, df["score"] >= 72, df["score"] >= 60],
        ["Tier 1", "Tier 2", "Tier 3"],
        default="Pass"
    )

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

def engine_all_sports(df):
    out = build_engine(df)
    out = apply_learning_layer(out)
    return out

def filtered_launch_ready(df):
    out = engine_all_sports(df)
    out = out[out["adjusted_score"] >= out["sport_min_score"]].copy()
    return out

def best_bets(df):
    out = df.copy()
    out = out[out["units"].fillna(0) > 0].copy()
    return out.sort_values(["adjusted_score", "multi_ai_score", "score", "ev_edge"], ascending=False)

# ---------- TRACKER / SLIP ----------
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

def add_bet_to_log(row, stake, risk_mode, bankroll_snapshot):
    log = st.session_state.bet_log.copy()
    bet_id = f"BET-{len(log)+1:04d}"
    new_row = {
        "bet_id": bet_id,
        "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
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
    st.session_state.bet_log = pd.concat([log, pd.DataFrame([new_row])], ignore_index=True)

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

def confirm_slip_to_tracker():
    for item in st.session_state.bet_slip:
        add_bet_to_log(item, item["stake"], item["risk_mode"], item["bankroll_snapshot"])
    count = len(st.session_state.bet_slip)
    clear_slip()
    return count

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

def refresh_bet_log_metrics():
    log = st.session_state.bet_log.copy()
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

def render_mobile_bet_picker(df, bankroll, risk_mode, drawdown_pct, roi_pct, key_prefix):
    if df.empty:
        st.info("No qualified plays available.")
        return
    work = df.copy().reset_index(drop=True)
    work["suggested_stake"] = work["units"].apply(lambda u: suggested_stake_from_units(u, bankroll, risk_mode, drawdown_pct, roi_pct))
    st.subheader("Smart Bet Slip Selector")
    st.caption("Sport-aware selection with launch filters applied.")
    for i, row in work.head(12).iterrows():
        st.markdown("**" + str(row.get("sport","")) + " | " + str(row.get("player","")) + " - " + str(row.get("market","")) + "**")
        st.write(str(row.get("book","")) + " | Odds: " + str(row.get("odds","")) + " | Line: " + str(row.get("line","")))
        st.write("Score: " + f"{row.get('score',0):.1f}" + " | Adjusted: " + f"{row.get('adjusted_score',0):.1f}" + " | Multi-AI: " + f"{row.get('multi_ai_score',0):.1f}")
        st.write(str(row.get("tier","")) + " | Units: " + f"{row.get('units',0):.2f}" + "u | Suggested Stake: $" + f"{row.get('suggested_stake',0):.2f}")
        st.write("Game: " + str(row.get("game","")) + " | Sport Mult: " + f"{row.get('sport_unit_mult',1.0):.2f}" + "x")
        c1, c2 = st.columns([1,1])
        with c1:
            custom_stake = st.number_input("Stake", min_value=1.0, value=float(max(1.0, row.get("suggested_stake", 1.0))), step=1.0, key=f"{key_prefix}_stake_{i}")
        with c2:
            st.write("")
            if st.button(f"Add To Slip {i+1}", key=f"{key_prefix}_add_{i}", use_container_width=True):
                add_to_slip(row.to_dict(), custom_stake, bankroll, risk_mode)
                st.success("Added to bet slip.")
        st.divider()

def render_bet_slip(namespace):
    st.subheader("Live Smart Bet Slip")
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

    st.markdown("### Remove Individual Bets")
    for i, item in slip.reset_index(drop=True).iterrows():
        label = f"{item['sport']} | {item['player']} - {item['market']} | ${float(item['stake']):.2f}"
        if st.button(
            "Remove: " + label,
            key=f"{namespace}_remove_slip_{i}_{item['slip_key']}",
            use_container_width=True
        ):
            remove_from_slip(item["slip_key"])
            st.success("Removed from slip.")
            st.rerun()

    x1, x2 = st.columns(2)
    with x1:
        if st.button("Clear Bet Slip", key=f"{namespace}_clear_slip", use_container_width=True):
            clear_slip()
            st.success("Bet slip cleared.")
            st.rerun()
    with x2:
        if st.button("Confirm Slip To Tracker", key=f"{namespace}_confirm_slip", use_container_width=True):
            count = confirm_slip_to_tracker()
            st.success(f"Added {count} bet(s) to tracker.")
            st.rerun()

# ---------- APP ----------
st.title("Sports AI Dashboard V12.4.1 Pro")
st.caption("V12.4.1 Pro fixes the smart slip key collision and keeps the multi-sport launch engine.")

tabs = st.tabs([
    "Dashboard","Data Input","Launch Board","Auto Unit AI","Smart Bet Slip",
    "CLV Tracker","Bet Tracker","Performance","Sport Stats","Multi-AI Lab","Learning Dashboard"
])

with tabs[0]:
    st.write("Active Source:", st.session_state.active_source)
    metrics = refresh_bet_log_metrics()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tracked Bets", metrics["total_bets"])
    c2.metric("Profit", f"${metrics['profit']:.2f}")
    c3.metric("ROI", f"{metrics['roi']:.2f}%")
    c4.metric("Win Rate", f"{metrics['win_rate']:.1f}%")
    if st.session_state.active_df is None:
        st.info("Load data in Data Input to begin.")
    else:
        df = best_bets(filtered_launch_ready(st.session_state.active_df)).head(10)
        show_cols = [c for c in ["sport","player","market","book","odds","score","adjusted_score","tier","units"] if c in df.columns]
        st.dataframe(df[show_cols], use_container_width=True)

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
    uploaded_file = st.file_uploader("Choose CSV or Excel", type=["csv","xlsx","xls"])
    if uploaded_file is not None:
        df_upload, err = read_uploaded_file(uploaded_file)
        if err:
            st.error(err)
        else:
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
    if st.session_state.active_df is not None:
        preview = filtered_launch_ready(st.session_state.active_df)
        st.dataframe(preview.head(20), use_container_width=True)

with tabs[2]:
    if st.session_state.active_df is None:
        st.info("Load data first.")
    else:
        df = filtered_launch_ready(st.session_state.active_df)
        sport_options = sorted(df["sport"].dropna().astype(str).unique().tolist()) if "sport" in df.columns else []
        selected_sports = st.multiselect("Sports", sport_options, default=sport_options)
        min_adjusted = st.slider("Min adjusted score", 0, 100, 60)
        filtered = df.copy()
        if selected_sports:
            filtered = filtered[filtered["sport"].astype(str).isin(selected_sports)]
        filtered = filtered[filtered["adjusted_score"].fillna(0) >= min_adjusted]
        filtered = best_bets(filtered)

        bankroll_quick = st.number_input("Bankroll for selector ($)", min_value=25.0, value=250.0, step=25.0, key="launch_bankroll")
        risk_mode_quick = st.selectbox("Risk mode", ["Conservative","Balanced","Aggressive"], index=1, key="launch_risk")
        drawdown_quick = st.number_input("Drawdown %", min_value=0.0, max_value=100.0, value=0.0, step=1.0, key="launch_drawdown")
        roi_quick = st.number_input("ROI %", value=float(refresh_bet_log_metrics()["roi"]), step=0.5, key="launch_roi")

        render_mobile_bet_picker(filtered, bankroll_quick, risk_mode_quick, drawdown_quick, roi_quick, "launch_picker")
        render_bet_slip("launch_board")

with tabs[3]:
    st.subheader("Auto Unit AI by Sport")
    metrics = refresh_bet_log_metrics()
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        bankroll = st.number_input("Current bankroll ($)", min_value=25.0, value=250.0, step=25.0)
    with c2:
        risk_mode = st.selectbox("Risk mode", ["Conservative","Balanced","Aggressive"], index=1)
    with c3:
        drawdown_pct = st.number_input("Current drawdown %", min_value=0.0, max_value=100.0, value=0.0, step=1.0)
    with c4:
        roi_input = st.number_input("Current ROI %", value=float(metrics["roi"]), step=0.5)
    st.success(f"Recommended unit multiplier: {recommended_unit_multiplier(risk_mode, bankroll, drawdown_pct, roi_input)}x")
    if st.session_state.active_df is None:
        st.info("Load data first.")
    else:
        ai_df = best_bets(filtered_launch_ready(st.session_state.active_df)).reset_index(drop=True)
        render_mobile_bet_picker(ai_df, bankroll, risk_mode, drawdown_pct, roi_input, "auto_unit")
        render_bet_slip("auto_unit")

with tabs[4]:
    render_bet_slip("smart_bet_slip")

with tabs[5]:
    st.subheader("CLV Tracker")
    log = st.session_state.bet_log.copy()
    if log.empty:
        st.info("No tracked bets yet.")
    else:
        editable_idx = st.selectbox("Select tracked bet", options=list(log.index), format_func=lambda i: f"{log.loc[i, 'bet_id']} | {log.loc[i, 'sport']} | {log.loc[i, 'player']} {log.loc[i, 'market']}")
        current = log.loc[editable_idx]
        closing_line = st.number_input("Closing line", value=float(current["clv_closing_line"]) if pd.notna(current["clv_closing_line"]) else float(current["line"]) if pd.notna(current["line"]) else 0.0, step=0.5)
        if st.button("Save CLV", use_container_width=True):
            st.session_state.bet_log.loc[editable_idx, "clv_closing_line"] = closing_line
            diff, result = clv_result(st.session_state.bet_log.loc[editable_idx])
            st.session_state.bet_log.loc[editable_idx, "clv_diff"] = diff
            st.session_state.bet_log.loc[editable_idx, "clv_win"] = result
            st.success("CLV updated.")
        st.dataframe(st.session_state.bet_log[[c for c in ["bet_id","sport","player","market","bet_side","line","clv_closing_line","clv_diff","clv_win","result"] if c in st.session_state.bet_log.columns]], use_container_width=True)

with tabs[6]:
    st.subheader("Bet Tracker")
    log = st.session_state.bet_log.copy()
    if log.empty:
        st.info("No bets tracked yet.")
    else:
        for i in range(len(log)):
            with st.expander(f"{log.loc[i, 'bet_id']} | {log.loc[i, 'sport']} | {log.loc[i, 'player']} {log.loc[i, 'market']}", expanded=False):
                st.write(f"Book: {log.loc[i, 'book']} | Odds: {log.loc[i, 'odds']} | Stake: ${float(log.loc[i, 'stake']):.2f}")
                result = st.selectbox(f"Result for {log.loc[i, 'bet_id']}", ["Pending","Win","Loss","Push"], index=["Pending","Win","Loss","Push"].index(log.loc[i, "result"]) if log.loc[i, "result"] in ["Pending","Win","Loss","Push"] else 0, key=f"result_{i}")
                notes = st.text_input("Notes", value=str(log.loc[i, "notes"]), key=f"notes_{i}")
                if st.button(f"Save {log.loc[i, 'bet_id']}", key=f"save_{i}"):
                    log.loc[i, "result"] = result
                    log.loc[i, "notes"] = notes
                    log.loc[i, "profit"] = settle_profit(log.loc[i, "odds"], log.loc[i, "stake"], result)
                    st.session_state.bet_log = log.copy()
                    st.success("Bet updated.")
        st.dataframe(st.session_state.bet_log, use_container_width=True)

with tabs[7]:
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
        perf = settled.groupby("sport", dropna=False).agg(
            bets=("bet_id","count"),
            profit=("profit","sum"),
            avg_score=("score","mean"),
            avg_adjusted=("adjusted_score","mean"),
            win_rate=("result", lambda s: round((s.eq("Win").sum() / max(1, s.isin(["Win","Loss"]).sum())) * 100, 2))
        ).reset_index()
        st.dataframe(perf, use_container_width=True)

with tabs[8]:
    st.subheader("Sport Stats")
    settled = get_settled_log()
    if settled.empty:
        st.info("No settled bets yet.")
    else:
        by_sport = settled.groupby("sport", dropna=False).agg(
            bets=("bet_id","count"),
            wins=("result", lambda s: int((s=="Win").sum())),
            losses=("result", lambda s: int((s=="Loss").sum())),
            profit=("profit","sum"),
            avg_clv=("clv_diff","mean"),
        ).reset_index()
        st.dataframe(by_sport, use_container_width=True)
        clv_sport = settled[settled["clv_win"].astype(str) != ""].groupby(["sport","clv_win"], dropna=False).agg(
            bets=("bet_id","count"),
            profit=("profit","sum")
        ).reset_index()
        if len(clv_sport):
            st.dataframe(clv_sport, use_container_width=True)

with tabs[9]:
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

with tabs[10]:
    st.subheader("Learning Dashboard")
    settled = get_settled_log()
    weight_df = pd.DataFrame({"model": list(st.session_state.learning_state["weights"].keys()), "weight": [round(v, 4) for v in st.session_state.learning_state["weights"].values()]})
    st.dataframe(weight_df, use_container_width=True)
    if settled.empty or len(settled) < 5:
        st.info("Learning engine is in stable warm-up mode. Settle at least 5 bets to activate adaptive learning.")
    else:
        learn = compute_learning_adjustments()
        st.metric("System State", learn["hot_cold"])
        st.metric("Global Learning Adj", f"{learn['global_adj']:.2f}")

st.success("V12.4.1 Pro Multi-Sport Engine ready.")
