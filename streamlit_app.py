
import io
from itertools import combinations

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Sports AI Dashboard V9 Pro", layout="wide")

# ---------- SESSION ----------
if "active_df" not in st.session_state:
    st.session_state.active_df = None
if "active_source" not in st.session_state:
    st.session_state.active_source = "None"

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

# ---------- SAMPLE DATA ----------
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

# ---------- ENGINE ----------
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

    if "variance" not in df.columns:
        df["variance"] = "Neutral"
        if "odds" in df.columns:
            df.loc[df["odds"] >= 130, "variance"] = "High"
            df.loc[df["odds"] <= -180, "variance"] = "Low"

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
        default="🔴 Pass"
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

def portfolio_builder(df, bankroll, max_plays, tier1_mult, tier2_mult, tier3_mult):
    plays = best_bets(df).head(max_plays).copy()
    if plays.empty:
        return plays

    mult_map = {"🟢 Tier 1": tier1_mult, "🟡 Tier 2": tier2_mult, "⚪ Tier 3": tier3_mult, "🔴 Pass": 0}
    plays["portfolio_mult"] = plays["tier"].map(mult_map).fillna(0)
    plays["portfolio_units"] = plays["units"] * plays["portfolio_mult"]

    total_units = plays["portfolio_units"].sum()
    if total_units <= 0:
        plays["recommended_stake"] = 0.0
    else:
        unit_value = bankroll / total_units
        plays["recommended_stake"] = plays["portfolio_units"] * unit_value

    plays["recommended_stake"] = plays["recommended_stake"].round(2)
    return plays

def find_arbitrage(df):
    needed = {"player", "market_family", "bet_side", "odds"}
    if not needed.issubset(df.columns):
        return pd.DataFrame()

    rows = []
    grouped = df.dropna(subset=["player", "market_family", "bet_side", "odds"]).groupby(["player", "market_family"])
    for (player, fam), g in grouped:
        overs = g[g["bet_side"].astype(str).str.lower() == "over"]
        unders = g[g["bet_side"].astype(str).str.lower() == "under"]
        if overs.empty or unders.empty:
            continue

        best_over = overs.loc[overs["odds"].idxmax()]
        best_under = unders.loc[unders["odds"].idxmax()]

        p1 = implied_prob(best_over["odds"])
        p2 = implied_prob(best_under["odds"])
        if pd.isna(p1) or pd.isna(p2):
            continue

        total = p1 + p2
        if total < 1:
            rows.append({
                "player": player,
                "market_family": fam,
                "over_book": best_over.get("book", ""),
                "over_line": best_over.get("line", np.nan),
                "over_odds": best_over["odds"],
                "under_book": best_under.get("book", ""),
                "under_line": best_under.get("line", np.nan),
                "under_odds": best_under["odds"],
                "arb_margin_pct": round((1 - total) * 100, 2),
            })
    return pd.DataFrame(rows).sort_values("arb_margin_pct", ascending=False) if rows else pd.DataFrame()

def find_middles(df):
    needed = {"player", "market_family", "bet_side", "line", "odds"}
    if not needed.issubset(df.columns):
        return pd.DataFrame()

    rows = []
    grouped = df.dropna(subset=["player", "market_family", "bet_side", "line", "odds"]).groupby(["player", "market_family"])
    for (player, fam), g in grouped:
        overs = g[g["bet_side"].astype(str).str.lower() == "over"]
        unders = g[g["bet_side"].astype(str).str.lower() == "under"]
        if overs.empty or unders.empty:
            continue

        over_row = overs.loc[overs["line"].idxmin()]
        under_row = unders.loc[unders["line"].idxmax()]

        if pd.notna(over_row["line"]) and pd.notna(under_row["line"]) and under_row["line"] > over_row["line"]:
            rows.append({
                "player": player,
                "market_family": fam,
                "over_book": over_row.get("book", ""),
                "over_line": over_row["line"],
                "over_odds": over_row["odds"],
                "under_book": under_row.get("book", ""),
                "under_line": under_row["line"],
                "under_odds": under_row["odds"],
                "middle_window": round(under_row["line"] - over_row["line"], 2),
            })
    return pd.DataFrame(rows).sort_values("middle_window", ascending=False) if rows else pd.DataFrame()

def parlay_estimator(df, legs=2, top_n=8):
    base = best_bets(df).copy()
    base = base[base["ev_edge"].fillna(0) > 0].head(top_n)
    if len(base) < legs:
        return pd.DataFrame()

    rows = []
    for combo in combinations(base.index.tolist(), legs):
        subset = base.loc[list(combo)].copy()
        names = " + ".join(subset["player"].astype(str) + " " + subset["market"].astype(str))
        decimal_odds = subset["odds"].apply(american_to_decimal)
        hit_probs = subset["hit_pct"] / 100.0

        if decimal_odds.isna().any() or hit_probs.isna().any():
            continue

        combined_decimal = decimal_odds.prod()
        combined_hit = hit_probs.prod()
        parlay_ev = ((combined_hit * combined_decimal) - 1) * 100

        rows.append({
            "legs": legs,
            "combo": names,
            "combined_decimal_odds": round(combined_decimal, 2),
            "est_hit_pct": round(combined_hit * 100, 2),
            "est_ev_pct": round(parlay_ev, 2),
            "avg_score": round(subset["score"].mean(), 1),
        })

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["est_ev_pct", "avg_score"], ascending=False).head(15)

def render_summary(df):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows", len(df))
    c2.metric("Books", df["book"].nunique() if "book" in df.columns else 0)
    c3.metric("Players", df["player"].nunique() if "player" in df.columns else 0)
    c4.metric("Markets", df["market"].nunique() if "market" in df.columns else 0)

# ---------- APP ----------
st.title("Sports AI Dashboard V9 Pro")
st.caption("Mobile-proof version with V8 scoring plus arbitrage, middles, portfolio tools, and parlay lab.")

tabs = st.tabs(["Dashboard", "Data Input", "NBA Props", "Market Edge Lab", "Portfolio Builder", "Parlay Lab"])

# ---------- DASHBOARD ----------
with tabs[0]:
    st.write("Active Source:", st.session_state.active_source)

    if st.session_state.active_df is None:
        st.info("Load data in Data Input to begin.")
    else:
        df = nba_only(st.session_state.active_df)
        render_summary(df)

        top = best_bets(df).head(5)
        st.subheader("Top Plays of the Day")
        if top.empty:
            st.info("No qualified plays yet.")
        else:
            for _, r in top.iterrows():
                st.write(
                    f"{r.get('player','')} — {r.get('market','')} | {r.get('book','')} | "
                    f"Projection {r.get('projection', np.nan):.2f} | Edge {r.get('edge', np.nan):.2f} | "
                    f"Odds {r.get('odds','')} | Hit % {r.get('hit_pct', np.nan):.1f}% | "
                    f"EV {r.get('ev_edge', np.nan):.2f}% | Score {r.get('score', np.nan):.1f} | "
                    f"{r.get('tier','')} | {r.get('units',0):.2f}u"
                )

            show_cols = [c for c in [
                "player", "market", "book", "odds", "line", "projection", "edge",
                "hit_pct", "break_even_pct", "ev_edge", "score", "tier", "units", "game"
            ] if c in top.columns]
            st.dataframe(top[show_cols], use_container_width=True)

# ---------- DATA INPUT ----------
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
Stephen Curry,Points Over,-108,27.0,NBA,NBA,Caesars,32.2,5.2,66.7,True,GSW,LAL,GSW @ LAL
Stephen Curry,Points Under,-105,30.5,NBA,NBA,BetMGM,26.9,3.6,58.5,True,GSW,LAL,GSW @ LAL
LeBron James,PRA Over,-110,38.5,NBA,NBA,FanDuel,43.8,5.3,64.8,True,LAL,GSW,GSW @ LAL'''
    txt = st.text_area("Paste CSV here", value="", height=220, placeholder=sample_text)

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
            file_name="v9_pro_sample.csv",
            mime="text/csv",
            use_container_width=True
        )

    if st.session_state.active_df is not None:
        st.markdown("### Active Dataset Preview")
        preview = build_engine(st.session_state.active_df)
        st.dataframe(preview.head(30), use_container_width=True)

# ---------- NBA PROPS ----------
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

        show_cols = [c for c in [
            "player", "market", "book", "odds", "line", "projection", "edge", "hit_pct",
            "break_even_pct", "ev_edge", "score", "tier", "units", "team", "opponent", "game"
        ] if c in filtered.columns]
        st.dataframe(filtered[show_cols], use_container_width=True)

        st.download_button("Download Filtered Props CSV", filtered.to_csv(index=False).encode("utf-8"), "v9_filtered_props.csv", "text/csv")

# ---------- MARKET EDGE LAB ----------
with tabs[3]:
    if st.session_state.active_df is None:
        st.info("Load data first.")
    else:
        df = nba_only(st.session_state.active_df)
        arb = find_arbitrage(df)
        mid = find_middles(df)

        st.subheader("Arbitrage Detector")
        if arb.empty:
            st.info("No arbitrage detected.")
        else:
            st.success(f"{len(arb)} arbitrage opportunity(s) found.")
            st.dataframe(arb, use_container_width=True)

        st.subheader("Middling Detector")
        if mid.empty:
            st.info("No middle windows detected.")
        else:
            st.success(f"{len(mid)} middle opportunity(s) found.")
            st.dataframe(mid, use_container_width=True)

# ---------- PORTFOLIO BUILDER ----------
with tabs[4]:
    if st.session_state.active_df is None:
        st.info("Load data first.")
    else:
        df = nba_only(st.session_state.active_df)

        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            bankroll = st.number_input("Bankroll ($)", min_value=10.0, value=100.0, step=10.0)
        with c2:
            max_plays = st.number_input("Max plays", min_value=1, max_value=25, value=5, step=1)
        with c3:
            tier1_mult = st.number_input("Tier 1 multiplier", min_value=0.0, value=1.0, step=0.1)
        with c4:
            tier2_mult = st.number_input("Tier 2 multiplier", min_value=0.0, value=1.0, step=0.1)
        with c5:
            tier3_mult = st.number_input("Tier 3 multiplier", min_value=0.0, value=1.0, step=0.1)

        port = portfolio_builder(df, bankroll, int(max_plays), tier1_mult, tier2_mult, tier3_mult)

        if port.empty:
            st.info("No plays available for the portfolio.")
        else:
            total_stake = port["recommended_stake"].sum()
            st.success(f"Portfolio built. Total suggested stake: ${total_stake:.2f}")

            show_cols = [c for c in [
                "player", "market", "book", "odds", "score", "tier", "units",
                "portfolio_units", "recommended_stake", "ev_edge", "game"
            ] if c in port.columns]
            st.dataframe(port[show_cols], use_container_width=True)

            st.download_button("Download Portfolio CSV", port.to_csv(index=False).encode("utf-8"), "v9_portfolio.csv", "text/csv")

# ---------- PARLAY LAB ----------
with tabs[5]:
    if st.session_state.active_df is None:
        st.info("Load data first.")
    else:
        df = nba_only(st.session_state.active_df)

        c1, c2 = st.columns(2)
        with c1:
            legs = st.selectbox("Parlay legs", [2, 3], index=0)
        with c2:
            top_n = st.slider("Use top N plays", min_value=4, max_value=12, value=8)

        parlays = parlay_estimator(df, legs=legs, top_n=top_n)
        if parlays.empty:
            st.info("Not enough qualified plays to estimate parlays.")
        else:
            st.dataframe(parlays, use_container_width=True)
            st.download_button("Download Parlay Lab CSV", parlays.to_csv(index=False).encode("utf-8"), "v9_parlays.csv", "text/csv")

st.success("V9 Pro ready.")
