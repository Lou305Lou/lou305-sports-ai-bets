
import math
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st


# =========================================================
# PAGE SETUP
# =========================================================
st.set_page_config(
    page_title="Sports AI Betting Dashboard",
    page_icon="🏀",
    layout="wide",
)

st.title("🏀 Sports AI Betting Dashboard")
st.caption("Arbitrage • Middles • NBA Player Props V2 (Starters Only + 1Q)")

# =========================================================
# HELPERS
# =========================================================
def american_to_decimal(odds):
    try:
        odds = float(odds)
        if odds > 0:
            return 1 + (odds / 100)
        return 1 + (100 / abs(odds))
    except Exception:
        return np.nan


def implied_prob_american(odds):
    try:
        odds = float(odds)
        if odds > 0:
            return 100 / (odds + 100)
        return abs(odds) / (abs(odds) + 100)
    except Exception:
        return np.nan


def safe_float(x):
    try:
        if pd.isna(x):
            return np.nan
        return float(x)
    except Exception:
        return np.nan


def normalize_text(x):
    if pd.isna(x):
        return ""
    return str(x).strip().lower()


def clean_market_name(x):
    x = normalize_text(x)
    replacements = {
        "moneyline": "moneyline",
        "ml": "moneyline",
        "spread": "spreads",
        "spreads": "spreads",
        "totals": "totals",
        "total": "totals",
    }
    return replacements.get(x, x)


def odds_filter_label(min_odds, max_odds):
    return f"{min_odds} to +{max_odds}" if max_odds > 0 else f"{min_odds} to {max_odds}"


def edge_bucket(score):
    if score >= 75:
        return "🟢 High Probability"
    if score >= 60:
        return "🟡 Lean"
    return "🔴 Avoid"


def add_missing_cols(df, cols_with_defaults):
    for col, default in cols_with_defaults.items():
        if col not in df.columns:
            df[col] = default
    return df


# =========================================================
# SAMPLE DATA
# =========================================================
def sample_odds_data():
    rows = [
        # NBA moneyline pair
        ["NBA", "Heat", "Celtics", "BetA", "moneyline", np.nan, np.nan, "Heat", +145],
        ["NBA", "Heat", "Celtics", "BetB", "moneyline", np.nan, np.nan, "Celtics", -135],

        # NBA spread pair for middles
        ["NBA", "Heat", "Celtics", "BetA", "spreads", -4.5, np.nan, "Celtics", -110],
        ["NBA", "Heat", "Celtics", "BetB", "spreads", +6.5, np.nan, "Heat", -110],

        # NBA mainline + spread middle concept
        ["NBA", "Lakers", "Suns", "BetA", "moneyline", np.nan, np.nan, "Lakers", +140],
        ["NBA", "Lakers", "Suns", "BetB", "spreads", -2.5, np.nan, "Suns", -110],

        # NHL moneyline arb sample
        ["NHL", "Panthers", "Rangers", "Book1", "moneyline", np.nan, np.nan, "Panthers", +125],
        ["NHL", "Panthers", "Rangers", "Book2", "moneyline", np.nan, np.nan, "Rangers", +130],

        # Totals sample
        ["NBA", "Knicks", "Bulls", "BetA", "totals", np.nan, 221.5, "Over", -105],
        ["NBA", "Knicks", "Bulls", "BetB", "totals", np.nan, 223.5, "Under", -105],
    ]
    df = pd.DataFrame(rows, columns=[
        "sport", "team_a", "team_b", "book", "market", "point", "total", "selection", "odds"
    ])
    return df


def sample_props_data():
    rows = [
        ["NBA", "Jalen Brunson", "Knicks", "Celtics", 1, "points", 27.5, 31.2, 36, 32.1, 5, 1.07, 1.03, -115, "full_game"],
        ["NBA", "Jayson Tatum", "Celtics", "Knicks", 1, "rebounds", 8.5, 9.7, 37, 34.8, 5, 1.04, 1.02, -105, "full_game"],
        ["NBA", "Bam Adebayo", "Heat", "Bucks", 1, "rebounds", 9.5, 11.1, 35, 31.6, 5, 1.06, 1.04, +110, "full_game"],
        ["NBA", "Tyrese Haliburton", "Pacers", "Cavs", 1, "assists", 10.5, 11.8, 35, 30.9, 5, 1.05, 1.03, +125, "full_game"],
        ["NBA", "Stephen Curry", "Warriors", "Lakers", 1, "3pt_made", 1.5, 2.2, 10, 31.5, 5, 1.03, 1.01, -120, "1Q"],
        ["NBA", "LeBron James", "Lakers", "Warriors", 1, "points", 6.5, 7.8, 10, 34.2, 5, 1.04, 1.02, -110, "1Q"],
        ["NBA", "Bench Example", "TeamX", "TeamY", 0, "points", 8.5, 10.2, 24, 18.0, 5, 1.02, 1.00, +150, "full_game"],
    ]
    df = pd.DataFrame(rows, columns=[
        "sport", "player", "team", "opponent", "is_starter", "prop_type", "line",
        "projection", "minutes_projection", "recent_avg", "last_5_games",
        "pace_factor", "matchup_factor", "odds", "game_segment"
    ])
    return df


# =========================================================
# DATA LOADING
# =========================================================
def load_odds_data(uploaded_file):
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
        except Exception:
            df = pd.read_excel(uploaded_file)
    else:
        df = sample_odds_data()

    df.columns = [c.strip().lower() for c in df.columns]

    df = add_missing_cols(df, {
        "sport": "NBA",
        "team_a": "",
        "team_b": "",
        "book": "",
        "market": "",
        "point": np.nan,
        "total": np.nan,
        "selection": "",
        "odds": np.nan,
    })

    df["market"] = df["market"].apply(clean_market_name)
    df["selection_norm"] = df["selection"].apply(normalize_text)
    df["odds"] = pd.to_numeric(df["odds"], errors="coerce")
    df["point"] = pd.to_numeric(df["point"], errors="coerce")
    df["total"] = pd.to_numeric(df["total"], errors="coerce")
    df["dec_odds"] = df["odds"].apply(american_to_decimal)
    df["imp_prob"] = df["odds"].apply(implied_prob_american)

    return df


def load_props_data(uploaded_file):
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
        except Exception:
            df = pd.read_excel(uploaded_file)
    else:
        df = sample_props_data()

    df.columns = [c.strip().lower() for c in df.columns]

    df = add_missing_cols(df, {
        "sport": "NBA",
        "player": "",
        "team": "",
        "opponent": "",
        "is_starter": 1,
        "prop_type": "points",
        "line": np.nan,
        "projection": np.nan,
        "minutes_projection": np.nan,
        "recent_avg": np.nan,
        "last_5_games": 5,
        "pace_factor": 1.00,
        "matchup_factor": 1.00,
        "odds": np.nan,
        "game_segment": "full_game",
    })

    numeric_cols = ["is_starter", "line", "projection", "minutes_projection", "recent_avg", "last_5_games", "pace_factor", "matchup_factor", "odds"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["prop_type"] = df["prop_type"].apply(normalize_text)
    df["game_segment"] = df["game_segment"].apply(normalize_text)
    df["player"] = df["player"].fillna("").astype(str)
    df["team"] = df["team"].fillna("").astype(str)
    df["opponent"] = df["opponent"].fillna("").astype(str)

    return df


# =========================================================
# ARBITRAGE ENGINE
# =========================================================
def find_moneyline_arbs(df):
    ml = df[df["market"] == "moneyline"].copy()
    results = []

    if ml.empty:
        return pd.DataFrame()

    group_cols = ["sport", "team_a", "team_b"]
    for keys, group in ml.groupby(group_cols, dropna=False):
        selections = group["selection"].dropna().unique()
        if len(selections) < 2:
            continue

        best_rows = []
        for selection in selections:
            subset = group[group["selection"] == selection].copy()
            if subset.empty:
                continue
            idx = subset["dec_odds"].idxmax()
            best_rows.append(subset.loc[idx])

        if len(best_rows) != 2:
            continue

        row1, row2 = best_rows
        inv_sum = (1 / row1["dec_odds"]) + (1 / row2["dec_odds"])
        arb_pct = (1 - inv_sum) * 100

        if inv_sum < 1:
            results.append({
                "sport": keys[0],
                "matchup": f"{keys[1]} vs {keys[2]}",
                "side_1": row1["selection"],
                "book_1": row1["book"],
                "odds_1": int(row1["odds"]),
                "side_2": row2["selection"],
                "book_2": row2["book"],
                "odds_2": int(row2["odds"]),
                "arb_profit_pct": round(arb_pct, 2),
            })

    return pd.DataFrame(results).sort_values("arb_profit_pct", ascending=False)


# =========================================================
# MIDDLE ENGINE
# =========================================================
def find_spread_middles(df):
    spreads = df[df["market"] == "spreads"].copy()
    results = []

    if spreads.empty:
        return pd.DataFrame()

    for keys, group in spreads.groupby(["sport", "team_a", "team_b"], dropna=False):
        if group["point"].notna().sum() < 2:
            continue

        rows = group.dropna(subset=["point"]).copy()
        if len(rows) < 2:
            continue

        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                r1 = rows.iloc[i]
                r2 = rows.iloc[j]

                p1 = safe_float(r1["point"])
                p2 = safe_float(r2["point"])

                if pd.isna(p1) or pd.isna(p2):
                    continue

                # opposite signs / gap creates a middle
                if p1 < 0 and p2 > 0 and abs(p1) < abs(p2):
                    width = p2 - abs(p1)
                    if width > 0:
                        results.append({
                            "sport": keys[0],
                            "matchup": f"{keys[1]} vs {keys[2]}",
                            "bet_1": f"{r1['selection']} {p1} ({r1['book']} {int(r1['odds'])})",
                            "bet_2": f"{r2['selection']} +{p2} ({r2['book']} {int(r2['odds'])})",
                            "middle_window_points": round(width, 2),
                            "middle_type": "Spread vs Spread",
                        })

                elif p2 < 0 and p1 > 0 and abs(p2) < abs(p1):
                    width = p1 - abs(p2)
                    if width > 0:
                        results.append({
                            "sport": keys[0],
                            "matchup": f"{keys[1]} vs {keys[2]}",
                            "bet_1": f"{r2['selection']} {p2} ({r2['book']} {int(r2['odds'])})",
                            "bet_2": f"{r1['selection']} +{p1} ({r1['book']} {int(r1['odds'])})",
                            "middle_window_points": round(width, 2),
                            "middle_type": "Spread vs Spread",
                        })

    out = pd.DataFrame(results)
    if not out.empty:
        out = out.sort_values("middle_window_points", ascending=False).drop_duplicates()
    return out


def find_moneyline_spread_middles(df):
    ml = df[df["market"] == "moneyline"].copy()
    spreads = df[df["market"] == "spreads"].copy()
    results = []

    if ml.empty or spreads.empty:
        return pd.DataFrame()

    for keys, group_ml in ml.groupby(["sport", "team_a", "team_b"], dropna=False):
        group_sp = spreads[
            (spreads["sport"] == keys[0]) &
            (spreads["team_a"] == keys[1]) &
            (spreads["team_b"] == keys[2])
        ].copy()

        if group_sp.empty:
            continue

        for _, ml_row in group_ml.iterrows():
            ml_selection = normalize_text(ml_row["selection"])

            for _, sp_row in group_sp.iterrows():
                spread_selection = normalize_text(sp_row["selection"])
                point = safe_float(sp_row["point"])

                if pd.isna(point):
                    continue

                # Favorite ML + opponent plus points
                if ml_selection != spread_selection and point > 0:
                    results.append({
                        "sport": keys[0],
                        "matchup": f"{keys[1]} vs {keys[2]}",
                        "bet_1": f"{ml_row['selection']} ML ({ml_row['book']} {int(ml_row['odds'])})",
                        "bet_2": f"{sp_row['selection']} +{point} ({sp_row['book']} {int(sp_row['odds'])})",
                        "middle_window_points": round(point - 1, 2) if point > 1 else 0,
                        "middle_type": "Moneyline vs Spread",
                        "notes": "Middle hits if ML side wins by fewer than spread points.",
                    })

    out = pd.DataFrame(results)
    if not out.empty:
        out = out.sort_values("middle_window_points", ascending=False).drop_duplicates()
    return out


# =========================================================
# PROP ENGINE
# =========================================================
def compute_prop_scores(df):
    df = df.copy()

    df["proj_edge"] = df["projection"] - df["line"]
    df["proj_edge_pct"] = np.where(df["line"] > 0, (df["proj_edge"] / df["line"]) * 100, 0)

    # Core score inputs
    df["minutes_score"] = np.clip((df["minutes_projection"] / 36) * 20, 0, 20)
    df["edge_score_component"] = np.clip(df["proj_edge_pct"], 0, 20)
    df["recent_form_component"] = np.clip(((df["recent_avg"] - df["line"]) / df["line"].replace(0, np.nan)) * 20, 0, 20).fillna(0)
    df["starter_component"] = np.where(df["is_starter"] >= 1, 15, 0)
    df["pace_component"] = np.clip((df["pace_factor"] - 1.0) * 100, -5, 10)
    df["matchup_component"] = np.clip((df["matchup_factor"] - 1.0) * 100, -5, 15)
    df["odds_component"] = np.where((df["odds"] >= -130) & (df["odds"] <= 150), 10, 5)

    df["edge_score"] = (
        df["minutes_score"]
        + df["edge_score_component"]
        + df["recent_form_component"]
        + df["starter_component"]
        + df["pace_component"]
        + df["matchup_component"]
        + df["odds_component"]
    ).round(1)

    df["edge_score"] = np.clip(df["edge_score"], 0, 100)
    df["bet_grade"] = df["edge_score"].apply(edge_bucket)

    # Simple recommendation direction
    df["recommended_side"] = np.where(df["projection"] > df["line"], "Over", "Under")

    return df


# =========================================================
# SIDEBAR
# =========================================================
st.sidebar.header("Controls")

odds_file = st.sidebar.file_uploader(
    "Upload odds file (CSV/XLSX)",
    type=["csv", "xlsx"],
    help="Expected columns: sport, team_a, team_b, book, market, point, total, selection, odds"
)

props_file = st.sidebar.file_uploader(
    "Upload props file (CSV/XLSX)",
    type=["csv", "xlsx"],
    help="Expected columns: player, team, opponent, is_starter, prop_type, line, projection, minutes_projection, recent_avg, pace_factor, matchup_factor, odds, game_segment"
)

odds_df = load_odds_data(odds_file)
props_df = load_props_data(props_file)
props_scored = compute_prop_scores(props_df)

# =========================================================
# TABS
# =========================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "Home",
    "Arbitrage",
    "Middles",
    "NBA Player Props V2",
])

# =========================================================
# HOME TAB
# =========================================================
with tab1:
    st.subheader("Project Status")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Odds Rows", len(odds_df))
    c2.metric("Props Rows", len(props_df))
    c3.metric("Books", odds_df["book"].nunique())
    c4.metric("Updated", datetime.now().strftime("%Y-%m-%d %H:%M"))

    st.markdown("### What this build includes")
    st.write("• Moneyline arbitrage scanner")
    st.write("• Spread-vs-spread middle scanner")
    st.write("• Moneyline-vs-spread middle scanner")
    st.write("• NBA Player Props V2")
    st.write("• Starters-only filter")
    st.write("• Odds filter")
    st.write("• 1Q props filter")
    st.write("• Edge Score Engine V1")

    st.markdown("### Sample file format")
    with st.expander("View expected odds columns"):
        st.dataframe(sample_odds_data(), use_container_width=True)

    with st.expander("View expected props columns"):
        st.dataframe(sample_props_data(), use_container_width=True)


# =========================================================
# ARBITRAGE TAB
# =========================================================
with tab2:
    st.subheader("Moneyline Arbitrage Scanner")

    sport_options = ["All"] + sorted(odds_df["sport"].dropna().astype(str).unique().tolist())
    selected_sport_arb = st.selectbox("Sport", sport_options, key="arb_sport")

    arb_df_base = odds_df.copy()
    if selected_sport_arb != "All":
        arb_df_base = arb_df_base[arb_df_base["sport"] == selected_sport_arb]

    arb_results = find_moneyline_arbs(arb_df_base)

    if arb_results.empty:
        st.warning("No moneyline arbitrage opportunities detected.")
    else:
        st.success(f"Found {len(arb_results)} arbitrage opportunity(s).")
        st.dataframe(arb_results, use_container_width=True)

        st.markdown("### Best Arbitrage")
        st.dataframe(arb_results.head(10), use_container_width=True)


# =========================================================
# MIDDLES TAB
# =========================================================
with tab3:
    st.subheader("Middle Detection")

    selected_sport_mid = st.selectbox("Sport ", sport_options, key="mid_sport")

    mid_df_base = odds_df.copy()
    if selected_sport_mid != "All":
        mid_df_base = mid_df_base[mid_df_base["sport"] == selected_sport_mid]

    spread_middles = find_spread_middles(mid_df_base)
    ml_spread_middles = find_moneyline_spread_middles(mid_df_base)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Spread vs Spread Middles")
        if spread_middles.empty:
            st.info("No spread-vs-spread middles found.")
        else:
            st.dataframe(spread_middles, use_container_width=True)

    with col2:
        st.markdown("### Moneyline vs Spread Middles")
        if ml_spread_middles.empty:
            st.info("No moneyline-vs-spread middles found.")
        else:
            st.dataframe(ml_spread_middles, use_container_width=True)


# =========================================================
# PROPS TAB
# =========================================================
with tab4:
    st.subheader("NBA Player Props Tab V2 — Starters Only + 1Q + Edge Score")

    prop_sport_options = ["All"] + sorted(props_scored["sport"].dropna().astype(str).unique().tolist())
    prop_types = ["All"] + sorted(props_scored["prop_type"].dropna().astype(str).unique().tolist())
    segments = ["All", "full_game", "1q"]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        selected_prop_sport = st.selectbox("Sport", prop_sport_options, key="prop_sport")
    with col2:
        selected_prop_type = st.selectbox("Prop Type", prop_types, key="prop_type")
    with col3:
        starters_only = st.checkbox("Starters Only", value=True)
    with col4:
        selected_segment = st.selectbox("Game Segment", segments, key="prop_segment")

    col5, col6, col7 = st.columns(3)
    with col5:
        min_odds = st.slider("Min Odds", min_value=-300, max_value=200, value=-300, step=5)
    with col6:
        max_odds = st.slider("Max Odds", min_value=-300, max_value=200, value=200, step=5)
    with col7:
        min_edge_score = st.slider("Minimum Edge Score", min_value=0, max_value=100, value=60, step=5)

    filtered = props_scored.copy()

    if selected_prop_sport != "All":
        filtered = filtered[filtered["sport"] == selected_prop_sport]

    if selected_prop_type != "All":
        filtered = filtered[filtered["prop_type"] == selected_prop_type]

    if starters_only:
        filtered = filtered[filtered["is_starter"] >= 1]

    if selected_segment != "All":
        filtered = filtered[filtered["game_segment"] == selected_segment]

    filtered = filtered[(filtered["odds"] >= min_odds) & (filtered["odds"] <= max_odds)]
    filtered = filtered[filtered["edge_score"] >= min_edge_score]

    display_cols = [
        "player", "team", "opponent", "prop_type", "game_segment", "line", "projection",
        "proj_edge", "minutes_projection", "recent_avg", "odds", "recommended_side",
        "edge_score", "bet_grade"
    ]

    st.markdown("### Best Prop Looks")
    if filtered.empty:
        st.warning("No props match the current filters.")
    else:
        filtered = filtered.sort_values(["edge_score", "proj_edge"], ascending=[False, False])
        st.dataframe(filtered[display_cols], use_container_width=True)

        st.markdown("### Top 10 Plays")
        st.dataframe(filtered[display_cols].head(10), use_container_width=True)

        st.markdown("### High Probability Props Only")
        high_prob = filtered[filtered["bet_grade"] == "🟢 High Probability"]
        if high_prob.empty:
            st.info("No High Probability props under the current filter settings.")
        else:
            st.dataframe(high_prob[display_cols], use_container_width=True)

    with st.expander("Edge Score Formula (V1)"):
        st.write("Edge Score = minutes + projection edge + recent form + starter bonus + pace + matchup + odds quality")
        st.write("This version is intentionally simple and fast so we can keep improving it.")


st.markdown("---")
st.caption("Built for quick copy/paste deployment on Streamlit Cloud.")
