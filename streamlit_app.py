
import io
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Sports AI Dashboard V11", layout="wide")

# ---------- SESSION ----------
if "active_df" not in st.session_state:
    st.session_state.active_df = None
if "active_source" not in st.session_state:
    st.session_state.active_source = "None"
if "bet_log" not in st.session_state:
    st.session_state.bet_log = pd.DataFrame(columns=[
        "bet_id", "added_at", "player", "market", "book", "odds", "line",
        "stake", "score", "tier", "units", "game", "bet_side", "result",
        "profit", "notes", "risk_mode", "bankroll_snapshot",
        "model_projection", "model_price_ev", "model_risk", "model_market", "model_history",
        "multi_ai_score", "clv_closing_line", "clv_direction", "clv_diff", "clv_win"
    ])

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
    attempts = [
        {"sep": ","},
        {"sep": ";"},
        {"sep": None, "engine": "python"},
    ]
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

def sample_data():
    rows = [
        ["Stephen Curry","Points Over",-115,27.5,"NBA","NBA","DraftKings",32.2,4.7,66.7,None,True,"GSW","LAL","GSW @ LAL"],
        ["Stephen Curry","Points Over",-108,27.0,"NBA","NBA","Caesars",32.2,5.2,66.7,None,True,"GSW","LAL","GSW @ LAL"],
        ["Stephen Curry","Points Under",-105,30.5,"NBA","NBA","BetMGM",26.9,3.6,58.5,None,True,"GSW","LAL","GSW @ LAL"],
        ["LeBron James","PRA Over",-110,38.5,"NBA","NBA","FanDuel",43.8,5.3,64.8,None,True,"LAL","GSW","GSW @ LAL"],
        ["LeBron James","PRA Under",102,41.5,"NBA","NBA","DraftKings",39.6,1.9,55.0,None,True,"LAL","GSW","GSW @ LAL"],
        ["Anthony Davis","Rebounds Over",-125,11.5,"NBA","NBA","Caesars",13.2,1.7,59.4,None,True,"LAL","GSW","GSW @ LAL"],
        ["Anthony Davis","Rebounds Under",110,13.5,"NBA","NBA","FanDuel",11.8,1.7,57.0,None,True,"LAL","GSW","GSW @ LAL"],
        ["Tyrese Haliburton","Assists Over",105,8.5,"NBA","NBA","BetMGM",10.1,1.6,58.3,None,True,"IND","MIL","MIL @ IND"],
        ["Tyrese Haliburton","Assists Under",-102,10.5,"NBA","NBA","DraftKings",8.9,1.6,56.0,None,True,"IND","MIL","MIL @ IND"],
        ["Jayson Tatum","Points Over",120,29.5,"NBA","NBA","FanDuel",31.4,1.9,57.5,None,True,"BOS","MIA","BOS @ MIA"],
        ["Jayson Tatum","Points Under",-105,31.5,"NBA","NBA","Caesars",29.8,1.7,55.8,None,True,"BOS","MIA","BOS @ MIA"],
    ]
    return pd.DataFrame(
        rows,
        columns=["player","market","odds","point","sport","league","book","projection","edge","hit_pct","score","is_starter","team","opponent","game"]
    )

def build_engine(df):
    df = normalize_columns(df)
    df = to_numeric_safe(df, ["odds", "point", "projection", "edge", "hit_pct", "score", "ev_edge", "units"])

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
        if "projection" in df.columns and "line" in df.columns:
            df["edge"] = df["projection"] - df["line"]
        else:
            df["edge"] = 0.0

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

    # Multi-AI foundation
    if "model_projection" not in df.columns:
        df["model_projection"] = np.clip(50 + df["edge"].fillna(0) * 8, 0, 100)
    if "model_price_ev" not in df.columns:
        df["model_price_ev"] = np.clip(50 + df["ev_edge"].fillna(0) * 1.8, 0, 100)
    if "model_risk" not in df.columns:
        base_risk = 60.0
        if "odds" in df.columns:
            base_risk = np.where(df["odds"].fillna(0) >= 120, 48, np.where(df["odds"].fillna(0) <= -170, 68, 58))
        df["model_risk"] = np.clip(base_risk + np.where(df.get("is_starter", False).astype(str).str.lower().isin(["true","1","yes"]), 6, 0), 0, 100)
    if "model_market" not in df.columns:
        df["model_market"] = np.clip(
            50
            + (df["break_even_pct"].fillna(50) - df["implied_prob"].fillna(50)) * 0.0
            + (df["hit_pct"].fillna(50) - df["break_even_pct"].fillna(50)) * 2.0,
            0, 100
        )
    if "model_history" not in df.columns:
        df["model_history"] = np.select(
            [df["score"].fillna(0) >= 82, df["score"].fillna(0) >= 70, df["score"].fillna(0) >= 58],
            [72, 62, 54],
            default=45
        )

    weights = {
        "model_projection": 0.30,
        "model_price_ev": 0.25,
        "model_risk": 0.15,
        "model_market": 0.15,
        "model_history": 0.15,
    }
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
    starter_bonus = 0
    if "is_starter" in df.columns:
        starter_bonus = df["is_starter"].apply(clean_bool).astype(int) * 4

    df.loc[need_score, "score"] = np.clip(
        0.55 * df.loc[need_score, "multi_ai_score"].fillna(50)
        + 20
        + edge_component[need_score]
        + hit_component[need_score]
        + ev_component[need_score]
        + starter_bonus[need_score],
        1, 99
    )

    df["tier"] = np.select(
        [df["score"] >= 84, df["score"] >= 72, df["score"] >= 60],
        ["🟢 Tier 1", "🟡 Tier 2", "⚪ Tier 3"],
        default="🔴 Pass",
    )

    if "units" not in df.columns:
        df["units"] = np.nan
    need_units = df["units"].isna()
    df.loc[need_units & (df["score"] >= 84), "units"] = 1.0
    df.loc[need_units & (df["score"] >= 72) & (df["score"] < 84), "units"] = 0.5
    df.loc[need_units & (df["score"] >= 60) & (df["score"] < 72), "units"] = 0.25
    df.loc[need_units & (df["score"] < 60), "units"] = 0.0

    return df

def nba_only(df):
    out = build_engine(df)
    if "sport" in out.columns:
        return out[out["sport"].astype(str).str.upper().str.contains("NBA", na=False)].copy()
    if "league" in out.columns:
        return out[out["league"].astype(str).str.upper().str.contains("NBA", na=False)].copy()
    return out.copy()

def best_bets(df):
    out = df.copy()
    out = out[out["units"].fillna(0) > 0].copy()
    return out.sort_values(["multi_ai_score", "score", "ev_edge", "edge"], ascending=False)

def recommended_unit_multiplier(risk_mode, bankroll, drawdown_pct, roi_pct):
    base = {"Conservative": 0.75, "Balanced": 1.00, "Aggressive": 1.25}.get(risk_mode, 1.0)
    bankroll_factor = 1.00
    if bankroll < 100:
        bankroll_factor = 0.75
    elif bankroll >= 500:
        bankroll_factor = 1.10

    drawdown_factor = 1.00
    if drawdown_pct >= 15:
        drawdown_factor = 0.70
    elif drawdown_pct >= 8:
        drawdown_factor = 0.85

    performance_factor = 1.00
    if roi_pct >= 8:
        performance_factor = 1.10
    elif roi_pct <= -8:
        performance_factor = 0.85

    return round(base * bankroll_factor * drawdown_factor * performance_factor, 2)

def suggested_stake_from_units(base_units, bankroll, risk_mode, drawdown_pct, roi_pct):
    try:
        base_units = float(base_units)
    except Exception:
        base_units = 0.0
    unit_pct = {"Conservative": 0.01, "Balanced": 0.015, "Aggressive": 0.02}.get(risk_mode, 0.015)
    mult = recommended_unit_multiplier(risk_mode, bankroll, drawdown_pct, roi_pct)
    return round(max(1.0, bankroll * unit_pct * base_units * mult), 2)

def add_bet_to_log(row, stake, risk_mode, bankroll_snapshot):
    log = st.session_state.bet_log.copy()
    bet_id = f"BET-{len(log) + 1:04d}"
    new_row = {
        "bet_id": bet_id,
        "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "player": row.get("player", ""),
        "market": row.get("market", ""),
        "book": row.get("book", ""),
        "odds": row.get("odds", np.nan),
        "line": row.get("line", row.get("point", np.nan)),
        "stake": round(float(stake), 2),
        "score": row.get("score", np.nan),
        "tier": row.get("tier", ""),
        "units": row.get("units", np.nan),
        "game": row.get("game", ""),
        "bet_side": row.get("bet_side", ""),
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
        "clv_closing_line": np.nan,
        "clv_direction": row.get("bet_side", ""),
        "clv_diff": np.nan,
        "clv_win": "",
    }
    st.session_state.bet_log = pd.concat([log, pd.DataFrame([new_row])], ignore_index=True)

def refresh_bet_log_metrics():
    log = st.session_state.bet_log.copy()
    if log.empty:
        return {
            "total_bets": 0,
            "settled_bets": 0,
            "wins": 0,
            "losses": 0,
            "pushes": 0,
            "pending": 0,
            "total_staked": 0.0,
            "profit": 0.0,
            "roi": 0.0,
            "win_rate": 0.0,
        }

    settled = log[log["result"].isin(["Win", "Loss", "Push"])].copy()
    total_staked = pd.to_numeric(log["stake"], errors="coerce").fillna(0).sum()
    settled_profit = pd.to_numeric(settled["profit"], errors="coerce").fillna(0).sum()
    wins = int((log["result"] == "Win").sum())
    losses = int((log["result"] == "Loss").sum())
    pushes = int((log["result"] == "Push").sum())
    pending = int((log["result"] == "Pending").sum())
    settled_count = len(settled)
    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0.0
    roi = (settled_profit / total_staked * 100) if total_staked > 0 else 0.0

    return {
        "total_bets": len(log),
        "settled_bets": settled_count,
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "pending": pending,
        "total_staked": round(total_staked, 2),
        "profit": round(settled_profit, 2),
        "roi": round(roi, 2),
        "win_rate": round(win_rate, 2),
    }

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

path = "/mnt/data/streamlit_app_v11.py"

# ---------- APP ----------
st.title("Sports AI Dashboard V11")
st.caption("V11 adds Auto Unit Scaling AI, CLV tracking, and a Multi-AI model foundation without live APIs.")

tabs = st.tabs([
    "Dashboard",
    "Data Input",
    "NBA Props",
    "Auto Unit AI",
    "CLV Tracker",
    "Bet Tracker",
    "Performance",
    "Multi-AI Lab",
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
        df = nba_only(st.session_state.active_df)
        top = best_bets(df).head(5)
        st.subheader("Top Plays of the Day")
        if top.empty:
            st.info("No qualified plays yet.")
        else:
            show_cols = [c for c in [
                "player","market","book","odds","line","edge","hit_pct","ev_edge",
                "model_projection","model_price_ev","model_risk","model_market","model_history",
                "multi_ai_score","score","tier","units","game"
            ] if c in top.columns]
            st.dataframe(top[show_cols], use_container_width=True)

with tabs[1]:
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Load Sample Data", use_container_width=True):
            st.session_state.active_df = sample_data()
            st.session_state.active_source = "Sample"
            st.success("Sample data loaded.")
    with c2:
        if st.button("Clear Active Data", use_container_width=True):
            st.session_state.active_df = None
            st.session_state.active_source = "None"
            st.warning("Active data cleared.")

    st.markdown("### Upload File")
    uploaded_file = st.file_uploader("Choose CSV or Excel", type=["csv", "xlsx", "xls"])
    if uploaded_file is not None:
        df_upload, err = read_uploaded_file(uploaded_file)
        if err:
            st.error(err)
        else:
            st.session_state.active_df = df_upload
            st.session_state.active_source = f"Uploaded: {uploaded_file.name}"
            st.success("File loaded.")

    st.markdown("### Paste CSV")
    sample_text = '''player,market,odds,point,sport,league,book,projection,edge,hit_pct,is_starter,team,opponent,game
Stephen Curry,Points Over,-115,27.5,NBA,NBA,DraftKings,32.2,4.7,66.7,True,GSW,LAL,GSW @ LAL
LeBron James,PRA Over,-110,38.5,NBA,NBA,FanDuel,43.8,5.3,64.8,True,LAL,GSW,GSW @ LAL'''
    txt = st.text_area("Paste CSV here", value="", height=180, placeholder=sample_text)
    c3, c4 = st.columns(2)
    with c3:
        if st.button("Load Pasted Data", use_container_width=True):
            df_paste, err = parse_csv_text(txt)
            if err:
                st.error(err)
            else:
                st.session_state.active_df = df_paste
                st.session_state.active_source = "Pasted CSV"
                st.success("Pasted data loaded.")
    with c4:
        st.download_button(
            "Download Sample CSV",
            data=sample_data().to_csv(index=False).encode("utf-8"),
            file_name="v11_sample.csv",
            mime="text/csv",
            use_container_width=True
        )

    if st.session_state.active_df is not None:
        st.markdown("### Active Dataset Preview")
        preview = build_engine(st.session_state.active_df)
        st.dataframe(preview.head(30), use_container_width=True)

with tabs[2]:
    if st.session_state.active_df is None:
        st.info("Load data first.")
    else:
        df = nba_only(st.session_state.active_df)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            odds_min, odds_max = st.slider("Odds range", -300, 200, (-300, 200))
        with c2:
            market_options = sorted(df["market"].dropna().astype(str).unique().tolist()) if "market" in df.columns else []
            selected_markets = st.multiselect("Markets", market_options, default=market_options[:min(6, len(market_options))])
        with c3:
            min_score = st.slider("Min score", 0, 100, 60)
        with c4:
            starters_only = st.toggle("Starters only", value=False) if "is_starter" in df.columns else False

        filtered = df.copy()
        if "odds" in filtered.columns:
            filtered = filtered[filtered["odds"].between(odds_min, odds_max, inclusive="both")]
        if selected_markets:
            filtered = filtered[filtered["market"].astype(str).isin(selected_markets)]
        filtered = filtered[filtered["score"].fillna(0) >= min_score]
        if starters_only and "is_starter" in filtered.columns:
            filtered = filtered[filtered["is_starter"].apply(clean_bool)]
        filtered = filtered.sort_values(["multi_ai_score", "score", "ev_edge"], ascending=False)

        show_cols = [c for c in [
            "player","market","book","odds","line","edge","hit_pct","ev_edge",
            "multi_ai_score","score","tier","units","game"
        ] if c in filtered.columns]
        st.dataframe(filtered[show_cols], use_container_width=True)

with tabs[3]:
    st.subheader("Auto Unit Scaling AI")
    metrics = refresh_bet_log_metrics()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        bankroll = st.number_input("Current bankroll ($)", min_value=25.0, value=250.0, step=25.0)
    with c2:
        risk_mode = st.selectbox("Risk mode", ["Conservative", "Balanced", "Aggressive"], index=1)
    with c3:
        drawdown_pct = st.number_input("Current drawdown %", min_value=0.0, max_value=100.0, value=0.0, step=1.0)
    with c4:
        roi_input = st.number_input("Current ROI %", value=float(metrics["roi"]), step=0.5)

    mult = recommended_unit_multiplier(risk_mode, bankroll, drawdown_pct, roi_input)
    st.success(f"Recommended unit multiplier: {mult}x")

    if st.session_state.active_df is None:
        st.info("Load data first to get suggested stakes.")
    else:
        df = best_bets(nba_only(st.session_state.active_df)).reset_index(drop=True)
        if df.empty:
            st.info("No qualified plays available.")
        else:
            ai_df = df.copy()
            ai_df["suggested_stake"] = ai_df["units"].apply(lambda u: suggested_stake_from_units(u, bankroll, risk_mode, drawdown_pct, roi_input))
            show_cols = [c for c in [
                "player","market","book","odds","units","suggested_stake","multi_ai_score","score","tier","game"
            ] if c in ai_df.columns]
            st.dataframe(ai_df[show_cols].head(20), use_container_width=True)

            selected_idx = st.selectbox(
                "Select play to add with AI stake",
                options=list(ai_df.index),
                format_func=lambda i: f"{ai_df.loc[i, 'player']} — {ai_df.loc[i, 'market']} | {ai_df.loc[i, 'book']} | ${ai_df.loc[i, 'suggested_stake']:.2f}"
            )
            if st.button("Add Selected AI-Sized Bet to Tracker", use_container_width=True):
                chosen = ai_df.loc[selected_idx].to_dict()
                add_bet_to_log(chosen, ai_df.loc[selected_idx, "suggested_stake"], risk_mode, bankroll)
                st.success("AI-sized bet added to tracker.")

with tabs[4]:
    st.subheader("Closing Line Value (CLV) Tracker")
    log = st.session_state.bet_log.copy()

    if log.empty:
        st.info("No tracked bets yet.")
    else:
        editable_idx = st.selectbox(
            "Select tracked bet",
            options=list(log.index),
            format_func=lambda i: f"{log.loc[i, 'bet_id']} — {log.loc[i, 'player']} {log.loc[i, 'market']} | Open {log.loc[i, 'line']}"
        )
        current = log.loc[editable_idx]

        c1, c2 = st.columns(2)
        with c1:
            closing_line = st.number_input("Closing line", value=float(current["clv_closing_line"]) if pd.notna(current["clv_closing_line"]) else float(current["line"]) if pd.notna(current["line"]) else 0.0, step=0.5)
        with c2:
            st.write(f"Bet side: {current['bet_side']}")

        if st.button("Save CLV", use_container_width=True):
            st.session_state.bet_log.loc[editable_idx, "clv_closing_line"] = closing_line
            diff, result = clv_result(st.session_state.bet_log.loc[editable_idx])
            st.session_state.bet_log.loc[editable_idx, "clv_diff"] = diff
            st.session_state.bet_log.loc[editable_idx, "clv_win"] = result
            st.success("CLV updated.")

        clv_ready = st.session_state.bet_log.copy()
        st.dataframe(
            clv_ready[[
                c for c in [
                    "bet_id","player","market","bet_side","line","clv_closing_line","clv_diff","clv_win","book","result"
                ] if c in clv_ready.columns
            ]],
            use_container_width=True
        )

with tabs[5]:
    st.subheader("Bet Tracker")
    log = st.session_state.bet_log.copy()
    if log.empty:
        st.info("No bets tracked yet.")
    else:
        for i in range(len(log)):
            with st.expander(f"{log.loc[i, 'bet_id']} — {log.loc[i, 'player']} {log.loc[i, 'market']} ({log.loc[i, 'book']})", expanded=False):
                st.write(f"Odds: {log.loc[i, 'odds']} | Stake: ${float(log.loc[i, 'stake']):.2f} | Game: {log.loc[i, 'game']}")
                result = st.selectbox(
                    f"Result for {log.loc[i, 'bet_id']}",
                    ["Pending", "Win", "Loss", "Push"],
                    index=["Pending", "Win", "Loss", "Push"].index(log.loc[i, "result"]) if log.loc[i, "result"] in ["Pending", "Win", "Loss", "Push"] else 0,
                    key=f"result_{i}",
                )
                notes = st.text_input("Notes", value=str(log.loc[i, "notes"]), key=f"notes_{i}")
                if st.button(f"Save {log.loc[i, 'bet_id']}", key=f"save_{i}"):
                    log.loc[i, "result"] = result
                    log.loc[i, "notes"] = notes
                    log.loc[i, "profit"] = settle_profit(log.loc[i, "odds"], log.loc[i, "stake"], result)
                    st.session_state.bet_log = log.copy()
                    st.success("Bet updated.")
        st.dataframe(st.session_state.bet_log, use_container_width=True)
        st.download_button(
            "Download Bet Log CSV",
            st.session_state.bet_log.to_csv(index=False).encode("utf-8"),
            "v11_bet_log.csv",
            "text/csv"
        )

with tabs[6]:
    st.subheader("Performance Dashboard")
    metrics = refresh_bet_log_metrics()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Settled Bets", metrics["settled_bets"])
    c2.metric("Profit", f"${metrics['profit']:.2f}")
    c3.metric("ROI", f"{metrics['roi']:.2f}%")
    c4.metric("Win Rate", f"{metrics['win_rate']:.2f}%")

    log = st.session_state.bet_log.copy()
    if log.empty:
        st.info("No tracking data yet.")
    else:
        settled = log[log["result"].isin(["Win", "Loss", "Push"])].copy()
        if not settled.empty:
            st.markdown("### Performance by Tier")
            tier_perf = settled.groupby("tier", dropna=False).agg(
                bets=("bet_id", "count"),
                profit=("profit", "sum"),
                avg_score=("score", "mean"),
                avg_multi_ai=("multi_ai_score", "mean"),
            ).reset_index().sort_values("profit", ascending=False)
            st.dataframe(tier_perf, use_container_width=True)

            st.markdown("### CLV Summary")
            clv_df = settled[settled["clv_win"].astype(str) != ""].copy()
            if clv_df.empty:
                st.info("Add closing lines in CLV Tracker to see CLV summary.")
            else:
                clv_summary = clv_df.groupby("clv_win", dropna=False).agg(
                    bets=("bet_id", "count"),
                    avg_clv=("clv_diff", "mean"),
                    profit=("profit", "sum"),
                ).reset_index()
                st.dataframe(clv_summary, use_container_width=True)

with tabs[7]:
    st.subheader("Multi-AI Lab")
    if st.session_state.active_df is None:
        st.info("Load data first.")
    else:
        df = best_bets(nba_only(st.session_state.active_df)).reset_index(drop=True)
        if df.empty:
            st.info("No qualified plays available.")
        else:
            st.markdown("### Multi-AI Model Scores")
            show_cols = [c for c in [
                "player","market","book",
                "model_projection","model_price_ev","model_risk","model_market","model_history",
                "multi_ai_score","score","tier","units"
            ] if c in df.columns]
            st.dataframe(df[show_cols], use_container_width=True)

            st.markdown("### What each model means")
            st.write("Projection: how far projection beats the line.")
            st.write("Price/EV: how good the price looks versus expected hit rate.")
            st.write("Risk: lower-volatility profile and starter support.")
            st.write("Market: how much margin exists over break-even.")
            st.write("History: placeholder weighting until your tracked sample grows.")

st.success("V11 ready.")
