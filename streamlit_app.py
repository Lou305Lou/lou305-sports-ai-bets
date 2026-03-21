
import io
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Sports AI Dashboard V10 Tracker", layout="wide")

# ---------- SESSION ----------
if "active_df" not in st.session_state:
    st.session_state.active_df = None
if "active_source" not in st.session_state:
    st.session_state.active_source = "None"
if "bet_log" not in st.session_state:
    st.session_state.bet_log = pd.DataFrame(columns=[
        "bet_id", "added_at", "player", "market", "book", "odds", "line",
        "stake", "score", "tier", "units", "game", "bet_side", "result",
        "profit", "notes"
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

    if "score" not in df.columns:
        df["score"] = np.nan

    need_score = df["score"].isna()
    edge_component = np.clip(df["edge"].fillna(0) * 6, -10, 35)
    hit_component = np.clip((df["hit_pct"].fillna(50) - 50) * 1.5, -10, 35)
    ev_component = np.clip(df["ev_edge"].fillna(0) * 0.8, -10, 30)
    starter_bonus = 0
    if "is_starter" in df.columns:
        starter_bonus = df["is_starter"].apply(clean_bool).astype(int) * 4
    df.loc[need_score, "score"] = np.clip(45 + edge_component[need_score] + hit_component[need_score] + ev_component[need_score] + starter_bonus[need_score], 1, 99)

    df["tier"] = np.select(
        [df["score"] >= 82, df["score"] >= 70, df["score"] >= 58],
        ["🟢 Tier 1", "🟡 Tier 2", "⚪ Tier 3"],
        default="🔴 Pass",
    )

    if "units" not in df.columns:
        df["units"] = np.nan
    need_units = df["units"].isna()
    df.loc[need_units & (df["score"] >= 82), "units"] = 1.0
    df.loc[need_units & (df["score"] >= 70) & (df["score"] < 82), "units"] = 0.5
    df.loc[need_units & (df["score"] >= 58) & (df["score"] < 70), "units"] = 0.25
    df.loc[need_units & (df["score"] < 58), "units"] = 0.0

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
    return out.sort_values(["score", "ev_edge", "edge"], ascending=False)

def add_bet_to_log(row, stake):
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

# ---------- APP ----------
st.title("Sports AI Dashboard V10 Tracker")
st.caption("Mobile-proof version with V9 engine plus manual bet tracking, grading, and performance dashboard.")

tabs = st.tabs(["Dashboard", "Data Input", "NBA Props", "Bet Slip Builder", "Bet Tracker", "Performance"])

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
            for _, r in top.iterrows():
                st.write(
                    f"{r.get('player','')} — {r.get('market','')} | {r.get('book','')} | "
                    f"Odds {r.get('odds','')} | Score {r.get('score', np.nan):.1f} | "
                    f"{r.get('tier','')} | {r.get('units',0):.2f}u"
                )
            show_cols = [c for c in ["player","market","book","odds","line","edge","hit_pct","ev_edge","score","tier","units","game"] if c in top.columns]
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
            file_name="v10_sample.csv",
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
            min_score = st.slider("Min score", 0, 100, 58)
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
        filtered = filtered.sort_values(["score", "ev_edge", "edge"], ascending=False)

        c5, c6, c7, c8 = st.columns(4)
        c5.metric("Filtered Props", len(filtered))
        c6.metric("Tier 1", int((filtered["tier"] == "🟢 Tier 1").sum()) if "tier" in filtered.columns else 0)
        c7.metric("Positive EV", int((filtered["ev_edge"].fillna(0) > 0).sum()) if "ev_edge" in filtered.columns else 0)
        c8.metric("Avg Score", f"{filtered['score'].mean():.1f}" if len(filtered) else "0.0")

        show_cols = [c for c in ["player","market","book","odds","line","projection","edge","hit_pct","break_even_pct","ev_edge","score","tier","units","team","opponent","game"] if c in filtered.columns]
        st.dataframe(filtered[show_cols], use_container_width=True)
        st.download_button("Download Filtered Props CSV", filtered.to_csv(index=False).encode("utf-8"), "v10_filtered_props.csv", "text/csv")

with tabs[3]:
    if st.session_state.active_df is None:
        st.info("Load data first.")
    else:
        df = best_bets(nba_only(st.session_state.active_df)).reset_index(drop=True)

        if df.empty:
            st.info("No qualified bets available.")
        else:
            st.subheader("Quick Add Bets")
            st.caption("Choose a recommended play and add it to your manual bet tracker.")

            selected_idx = st.selectbox(
                "Select a play",
                options=list(df.index),
                format_func=lambda i: f"{df.loc[i, 'player']} — {df.loc[i, 'market']} | {df.loc[i, 'book']} | Odds {df.loc[i, 'odds']} | Score {df.loc[i, 'score']:.1f}"
            )
            default_stake = float(df.loc[selected_idx, "units"] if pd.notna(df.loc[selected_idx, "units"]) else 1.0) * 10.0
            stake = st.number_input("Stake ($)", min_value=1.0, value=max(1.0, round(default_stake, 2)), step=1.0)

            if st.button("Add Selected Bet to Tracker", use_container_width=True):
                add_bet_to_log(df.loc[selected_idx], stake)
                st.success("Bet added to tracker.")

            st.markdown("### Recommended Plays")
            show_cols = [c for c in ["player","market","book","odds","line","score","tier","units","ev_edge","game"] if c in df.columns]
            st.dataframe(df[show_cols].head(20), use_container_width=True)

with tabs[4]:
    st.subheader("Bet Tracker")

    log = st.session_state.bet_log.copy()
    if log.empty:
        st.info("No bets tracked yet. Add bets from Bet Slip Builder.")
    else:
        st.caption("Update results manually after games finish.")

        for i in range(len(log)):
            with st.expander(f"{log.loc[i, 'bet_id']} — {log.loc[i, 'player']} {log.loc[i, 'market']} ({log.loc[i, 'book']})", expanded=False):
                st.write(f"Odds: {log.loc[i, 'odds']} | Stake: ${log.loc[i, 'stake']:.2f} | Game: {log.loc[i, 'game']}")
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

        st.markdown("### Current Log")
        st.dataframe(st.session_state.bet_log, use_container_width=True)
        st.download_button(
            "Download Bet Log CSV",
            st.session_state.bet_log.to_csv(index=False).encode("utf-8"),
            "v10_bet_log.csv",
            "text/csv"
        )

with tabs[5]:
    st.subheader("Performance Dashboard")

    metrics = refresh_bet_log_metrics()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Settled Bets", metrics["settled_bets"])
    c2.metric("Wins-Losses-Pushes", f"{metrics['wins']}-{metrics['losses']}-{metrics['pushes']}")
    c3.metric("Profit", f"${metrics['profit']:.2f}")
    c4.metric("ROI", f"{metrics['roi']:.2f}%")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Pending", metrics["pending"])
    c6.metric("Total Staked", f"${metrics['total_staked']:.2f}")
    c7.metric("Win Rate", f"{metrics['win_rate']:.2f}%")
    c8.metric("Tracked Bets", metrics["total_bets"])

    log = st.session_state.bet_log.copy()
    if log.empty:
        st.info("No tracking data yet.")
    else:
        settled = log[log["result"].isin(["Win", "Loss", "Push"])].copy()

        st.markdown("### Performance by Market")
        if not settled.empty and "market" in settled.columns:
            market_perf = settled.groupby("market", dropna=False).agg(
                bets=("bet_id", "count"),
                profit=("profit", "sum"),
                avg_stake=("stake", "mean"),
            ).reset_index().sort_values("profit", ascending=False)
            st.dataframe(market_perf, use_container_width=True)

        st.markdown("### Performance by Book")
        if not settled.empty and "book" in settled.columns:
            book_perf = settled.groupby("book", dropna=False).agg(
                bets=("bet_id", "count"),
                profit=("profit", "sum"),
                avg_stake=("stake", "mean"),
            ).reset_index().sort_values("profit", ascending=False)
            st.dataframe(book_perf, use_container_width=True)

        st.markdown("### Full Settled Log")
        st.dataframe(settled, use_container_width=True)

st.success("V10 Tracker ready.")
