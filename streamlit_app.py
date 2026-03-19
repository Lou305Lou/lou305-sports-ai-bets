import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(layout="wide")

# -----------------------------
# TITLE
# -----------------------------
st.title("Sports AI Betting Dashboard")

st.markdown(
    '<div class="sub-title">Live odds, AI engine, tracking, and performance system</div>',
    unsafe_allow_html=True
)

# -----------------------------
# SESSION STATE
# -----------------------------
if "scan_complete" not in st.session_state:
    st.session_state.scan_complete = False

if "final_df" not in st.session_state:
    st.session_state.final_df = pd.DataFrame()

if "arb_df" not in st.session_state:
    st.session_state.arb_df = pd.DataFrame()

if "mid_df" not in st.session_state:
    st.session_state.mid_df = pd.DataFrame()

if "raw_mid_df" not in st.session_state:
    st.session_state.raw_mid_df = pd.DataFrame()

if "distribution_df" not in st.session_state:
    st.session_state.distribution_df = pd.DataFrame()

if "raw_events_count" not in st.session_state:
    st.session_state.raw_events_count = 0

if "raw_books_count" not in st.session_state:
    st.session_state.raw_books_count = 0

if "latest_filtered_events" not in st.session_state:
    st.session_state.latest_filtered_events = []

if "latest_sport_key" not in st.session_state:
    st.session_state.latest_sport_key = None

# AI PERFORMANCE (V8)
if "ai_perf_df" not in st.session_state:
    st.session_state.ai_perf_df = pd.DataFrame(columns=[
        "date_added","sport","game","bet_type","pick",
        "confidence","grade","engine_score",
        "status","stake","actual_profit"
    ])

if "auto_saved_ai_count" not in st.session_state:
    st.session_state.auto_saved_ai_count = 0

if "duplicate_ai_skipped_count" not in st.session_state:
    st.session_state.duplicate_ai_skipped_count = 0

# -----------------------------
# MOCK FUNCTIONS (SAFE VERSION)
# -----------------------------
def fetch_odds(sport_key):
    return [
        {"home_team": "Celtics", "away_team": "Lakers"},
        {"home_team": "Heat", "away_team": "Bulls"},
    ]

def extract_available_books(events):
    return ["DraftKings","FanDuel"]

def filter_events_by_books(events, books):
    return events

def detect_arbitrage(*args, **kwargs):
    return pd.DataFrame()

def detect_spread_middles(*args, **kwargs):
    return pd.DataFrame()

def apply_actual_plays_filter(df, **kwargs):
    return df

def build_middle_distribution(df):
    return pd.DataFrame()

# -----------------------------
# SIMPLE AI ENGINE
# -----------------------------
def run_unified_ai_engine_v7(event, sport_key):
    home = event["home_team"]
    away = event["away_team"]

    pick = home if np.random.rand() > 0.5 else away

    return {
        "features": {
            "sport_name": "NBA" if sport_key=="basketball_nba" else "NHL",
            "home_team": home,
            "away_team": away
        },
        "final_ai": {
            "best_bet": {
                "type": "Moneyline",
                "pick": pick,
                "confidence": round(np.random.uniform(60,85),1),
                "grade": "B"
            },
            "final_score": round(np.random.uniform(60,90),1)
        },
        "stats_ai": {},
        "matchup_ai": {},
        "market_ai": {},
        "momentum_ai": {}
    }

def create_ai_performance_row(features, final_ai, *args):
    return {
        "date_added": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sport": features["sport_name"],
        "game": f"{features['away_team']} @ {features['home_team']}",
        "bet_type": final_ai["best_bet"]["type"],
        "pick": final_ai["best_bet"]["pick"],
        "confidence": final_ai["best_bet"]["confidence"],
        "grade": final_ai["best_bet"]["grade"],
        "engine_score": final_ai["final_score"],
        "status": "Pending",
        "stake": 100,
        "actual_profit": 0
    }
    # -----------------------------
# AUTO-SAVE V8 HELPERS
# -----------------------------
def ai_pick_duplicate_exists(ai_perf_df, sport, game, bet_type, pick, scan_date):
    if ai_perf_df.empty:
        return False

    check_df = ai_perf_df.copy()
    check_df["scan_date_only"] = check_df["date_added"].astype(str).str[:10]

    duplicate_mask = (
        (check_df["sport"].astype(str) == str(sport)) &
        (check_df["game"].astype(str) == str(game)) &
        (check_df["bet_type"].astype(str) == str(bet_type)) &
        (check_df["pick"].astype(str) == str(pick)) &
        (check_df["scan_date_only"].astype(str) == str(scan_date))
    )

    return bool(duplicate_mask.any())


def auto_save_ai_picks_to_v8(events, sport_key, ai_perf_df):
    if sport_key not in ["basketball_nba", "icehockey_nhl"]:
        return ai_perf_df.copy(), 0, 0

    updated_df = ai_perf_df.copy()
    auto_saved = 0
    duplicates = 0
    scan_date = datetime.now().strftime("%Y-%m-%d")

    for event in events:
        try:
            ai = run_unified_ai_engine_v7(event, sport_key)
            features = ai["features"]
            final_ai = ai["final_ai"]

            sport = features["sport_name"]
            game = f"{features['away_team']} @ {features['home_team']}"
            bet_type = final_ai["best_bet"]["type"]
            pick = final_ai["best_bet"]["pick"]

            if ai_pick_duplicate_exists(updated_df, sport, game, bet_type, pick, scan_date):
                duplicates += 1
                continue

            new_row = create_ai_performance_row(
                features,
                final_ai,
                ai.get("stats_ai", {}),
                ai.get("matchup_ai", {}),
                ai.get("market_ai", {}),
                ai.get("momentum_ai", {})
            )

            updated_df = pd.concat(
                [updated_df, pd.DataFrame([new_row])],
                ignore_index=True
            )
            auto_saved += 1

        except Exception:
            continue

    return updated_df, auto_saved, duplicates


# -----------------------------
# CONTROLS
# -----------------------------
SPORT_OPTIONS = {
    "NBA": "basketball_nba",
    "NHL": "icehockey_nhl",
    "NFL": "americanfootball_nfl",
    "MLB": "baseball_mlb",
}

c1, c2, c3 = st.columns(3)
with c1:
    sport_label = st.selectbox("Choose sport", list(SPORT_OPTIONS.keys()), index=0)
    sport_key = SPORT_OPTIONS[sport_label]

with c2:
    show_arbs = st.checkbox("Scan Arbitrage", value=True)

with c3:
    show_middles = st.checkbox("Scan Middles", value=True)

d1, d2, d3 = st.columns(3)
with d1:
    selected_books = st.multiselect(
        "Sportsbooks",
        ["DraftKings", "FanDuel", "BetMGM"],
        default=["DraftKings", "FanDuel"]
    )

with d2:
    middle_focus_mode = st.checkbox("Middle Focus Mode", value=True)

with d3:
    actual_plays_only = st.checkbox("Actual Plays Only", value=False)

e1, e2, e3 = st.columns(3)
with e1:
    bankroll = st.number_input("Bankroll", min_value=1, value=100, step=10)

with e2:
    min_profit = st.number_input("Min Arb Profit %", min_value=0.0, value=0.0, step=0.5)

with e3:
    min_gap = st.number_input("Min Middle Gap", min_value=0.5, value=1.0, step=0.5)

scan_button = st.button("Scan Live Odds", type="primary")
st.info("Manual scan only. No auto-refresh is running.")

# -----------------------------
# SCAN
# -----------------------------
if scan_button:
    with st.spinner("Scanning live odds..."):
        try:
            raw_events = fetch_odds(sport_key)
            raw_books_count = len(extract_available_books(raw_events))
            filtered_events = filter_events_by_books(raw_events, selected_books) if selected_books else raw_events

            arb_df = pd.DataFrame()
            raw_mid_df = pd.DataFrame()
            mid_df = pd.DataFrame()
            results = []

            if show_arbs:
                arb_df = detect_arbitrage(
                    filtered_events,
                    bankroll=bankroll,
                    min_profit=min_profit
                )
                if not arb_df.empty:
                    arb_df = arb_df.sort_values(by="score", ascending=False)

            if show_middles:
                raw_mid_df = detect_spread_middles(
                    filtered_events,
                    min_gap=min_gap
                )

                mid_df = raw_mid_df.copy()

                if not mid_df.empty and middle_focus_mode and "middle_strength" in mid_df.columns:
                    mid_df = mid_df[mid_df["middle_strength"].isin(["Medium", "Strong"])].copy()

            if not arb_df.empty:
                results.append(arb_df)
            if not mid_df.empty:
                results.append(mid_df)

            final_df = pd.concat(results, ignore_index=True) if results else pd.DataFrame()
            distribution_df = build_middle_distribution(raw_mid_df)

            final_df = apply_actual_plays_filter(
                final_df,
                actual_plays_only=actual_plays_only,
                actual_middle_min_gap=1.0,
                actual_middle_min_score=2.0,
                actual_arb_min_profit_pct=1.0,
                actual_arb_min_profit_dollars=1.0,
            )

            filtered_mid_df = final_df[final_df["type"] == "Middle"].copy() if (not final_df.empty and "type" in final_df.columns) else pd.DataFrame()
            filtered_arb_df = final_df[final_df["type"] == "Arbitrage"].copy() if (not final_df.empty and "type" in final_df.columns) else pd.DataFrame()

            st.session_state.scan_complete = True
            st.session_state.final_df = final_df
            st.session_state.arb_df = filtered_arb_df
            st.session_state.mid_df = filtered_mid_df
            st.session_state.raw_mid_df = raw_mid_df
            st.session_state.distribution_df = distribution_df
            st.session_state.raw_events_count = len(raw_events)
            st.session_state.raw_books_count = raw_books_count
            st.session_state.latest_filtered_events = filtered_events
            st.session_state.latest_sport_key = sport_key

            updated_df, auto_saved, duplicates = auto_save_ai_picks_to_v8(
                filtered_events,
                sport_key,
                st.session_state.ai_perf_df
            )

            st.session_state.ai_perf_df = updated_df
            st.session_state.auto_saved_ai_count = auto_saved
            st.session_state.duplicate_ai_skipped_count = duplicates

        except Exception as e:
            st.error(f"Error fetching live odds: {e}")

# -----------------------------
# TABS
# -----------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "Dashboard",
    "Unified AI Engine V7",
    "Performance Learning V8",
    "Raw Tables"
])

with tab1:
    st.subheader("Dashboard Summary")

    events_pulled = st.session_state.raw_events_count
    books_returned = st.session_state.raw_books_count
    arb_rows = len(st.session_state.arb_df)
    mid_rows = len(st.session_state.mid_df)

    arb_profit_total = 0.0
    if not st.session_state.arb_df.empty and "profit_dollars" in st.session_state.arb_df.columns:
        arb_profit_total = pd.to_numeric(
            st.session_state.arb_df["profit_dollars"], errors="coerce"
        ).fillna(0).sum()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Events Pulled", events_pulled)
    m2.metric("Books Returned", books_returned)
    m3.metric("Arb Rows Found", arb_rows)
    m4.metric("Middle Rows Found", mid_rows)

    m5, m6, m7, m8 = st.columns(4)
    m5.metric("Total Arb Profit ($)", round(float(arb_profit_total), 2))
    m6.metric("Kelly Mode", "Half Kelly")
    m7.metric("AI Picks Auto-Saved", st.session_state.auto_saved_ai_count)
    m8.metric("Duplicates Skipped", st.session_state.duplicate_ai_skipped_count)

    if st.session_state.scan_complete:
        st.success("Scan complete.")
    else:
        st.info("Run a scan to populate the dashboard.")

with tab2:
    st.subheader("Unified AI Engine V7")

    if not st.session_state.scan_complete:
        st.info("Run a scan first.")
    elif st.session_state.latest_sport_key not in ["basketball_nba", "icehockey_nhl"]:
        st.info("Unified AI is currently set up for NBA and NHL in this version.")
    elif not st.session_state.latest_filtered_events:
        st.info("No events available from the last scan.")
    else:
        game_labels = [
            f"{event['away_team']} @ {event['home_team']}"
            for event in st.session_state.latest_filtered_events
        ]

        selected_game = st.selectbox("Choose game", game_labels)
        selected_index = game_labels.index(selected_game)
        selected_event = st.session_state.latest_filtered_events[selected_index]

        ai = run_unified_ai_engine_v7(selected_event, st.session_state.latest_sport_key)
        features = ai["features"]
        final_ai = ai["final_ai"]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Sport", features["sport_name"])
        c2.metric("Best Bet Type", final_ai["best_bet"]["type"])
        c3.metric("Pick", final_ai["best_bet"]["pick"])
        c4.metric("Confidence", final_ai["best_bet"]["confidence"])

        st.markdown("### Selected Game Best Bet")
        st.write(f"**Game:** {features['away_team']} @ {features['home_team']}")
        st.write(f"**Bet Type:** {final_ai['best_bet']['type']}")
        st.write(f"**Pick:** {final_ai['best_bet']['pick']}")
        st.write(f"**Confidence:** {final_ai['best_bet']['confidence']}")
        st.write(f"**Grade:** {final_ai['best_bet']['grade']}")
        st.write(f"**Engine Score:** {final_ai['final_score']}")

        if st.button("Save Selected AI Best Bet to Performance Learning V8"):
            new_row = create_ai_performance_row(
                features,
                final_ai,
                ai.get("stats_ai", {}),
                ai.get("matchup_ai", {}),
                ai.get("market_ai", {}),
                ai.get("momentum_ai", {}),
            )
            st.session_state.ai_perf_df = pd.concat(
                [st.session_state.ai_perf_df, pd.DataFrame([new_row])],
                ignore_index=True
            )
            st.success("AI pick saved manually to V8.")

with tab3:
    st.subheader("Performance Learning V8")

    ai_perf_df = st.session_state.ai_perf_df.copy()

    total_picks = len(ai_perf_df)
    wins = int((ai_perf_df["status"] == "Win").sum()) if not ai_perf_df.empty else 0
    losses = int((ai_perf_df["status"] == "Loss").sum()) if not ai_perf_df.empty else 0
    pending = int((ai_perf_df["status"] == "Pending").sum()) if not ai_perf_df.empty else 0
    profit = pd.to_numeric(ai_perf_df["actual_profit"], errors="coerce").fillna(0).sum() if not ai_perf_df.empty else 0.0

    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Tracked AI Picks", total_picks)
    p2.metric("Wins", wins)
    p3.metric("Losses", losses)
    p4.metric("Pending", pending)

    p5, p6 = st.columns(2)
    p5.metric("Total Profit ($)", round(float(profit), 2))
    p6.metric("Average Confidence", round(pd.to_numeric(ai_perf_df["confidence"], errors="coerce").fillna(0).mean(), 2) if not ai_perf_df.empty else 0.0)

    if ai_perf_df.empty:
        st.info("No AI picks saved yet. Scan NBA or NHL to auto-save picks.")
    else:
        st.markdown("### Update AI Pick Result")

        options = [
            f"{i+1}. {row['sport']} | {row['game']} | {row['bet_type']} | {row['pick']} | {row['status']}"
            for i, row in ai_perf_df.reset_index(drop=True).iterrows()
        ]

        selected_label = st.selectbox("Choose AI tracked pick", options)
        selected_index = options.index(selected_label)
        selected_row = ai_perf_df.reset_index(drop=True).iloc[selected_index]

        u1, u2, u3 = st.columns(3)
        with u1:
            new_status = st.selectbox(
                "Update result status",
                ["Pending", "Win", "Loss", "Push"],
                index=["Pending", "Win", "Loss", "Push"].index(selected_row["status"]) if selected_row["status"] in ["Pending", "Win", "Loss", "Push"] else 0
            )
        with u2:
            new_stake = st.number_input(
                "Stake ($)",
                value=float(pd.to_numeric(pd.Series([selected_row["stake"]]), errors="coerce").fillna(100).iloc[0]),
                step=5.0
            )
        with u3:
            new_actual_profit = st.number_input(
                "Actual Profit / Loss ($)",
                value=float(pd.to_numeric(pd.Series([selected_row["actual_profit"]]), errors="coerce").fillna(0).iloc[0]),
                step=1.0
            )

        if st.button("Save Performance Update"):
            st.session_state.ai_perf_df.loc[selected_index, "status"] = new_status
            st.session_state.ai_perf_df.loc[selected_index, "stake"] = round(new_stake, 2)
            st.session_state.ai_perf_df.loc[selected_index, "actual_profit"] = round(new_actual_profit, 2)
            st.success("Performance record updated.")

        st.markdown("### AI Performance Records")
        st.dataframe(st.session_state.ai_perf_df, use_container_width=True)

with tab4:
    st.subheader("Raw Tables")

    st.markdown("### Final Opportunities")
    st.dataframe(st.session_state.final_df, use_container_width=True)

    st.markdown("### Arbitrage Rows")
    st.dataframe(st.session_state.arb_df, use_container_width=True)

    st.markdown("### Middle Rows")
    st.dataframe(st.session_state.mid_df, use_container_width=True)

    st.markdown("### AI Performance Table")
    st.dataframe(st.session_state.ai_perf_df, use_container_width=True)
