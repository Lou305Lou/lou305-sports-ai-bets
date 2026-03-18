import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Sports AI Betting Dashboard", layout="wide")

# -----------------------------
# UI STYLING
# -----------------------------
st.markdown("""
<style>
.block-container {
    padding-top: 1.2rem;
    padding-bottom: 2rem;
    max-width: 1400px;
}

.main-title {
    font-size: 2rem;
    font-weight: 800;
    margin-bottom: 0.2rem;
    color: #111827;
}

.sub-title {
    color: #475569;
    margin-bottom: 1rem;
}

.section-card {
    background: #0F172A;
    border: 1px solid #334155;
    padding: 16px;
    border-radius: 16px;
    margin-bottom: 14px;
    color: #F8FAFC;
}

.play-card {
    background: #111827;
    border: 1px solid #475569;
    padding: 14px;
    border-radius: 14px;
    margin-bottom: 10px;
    color: #F8FAFC;
    line-height: 1.6;
    font-size: 0.98rem;
}

.play-card b {
    color: #FFFFFF;
}

.alert-green {
    background: #052e16;
    border: 1px solid #166534;
    color: #DCFCE7;
    padding: 12px;
    border-radius: 12px;
    margin-bottom: 10px;
    font-weight: 600;
}

.alert-yellow {
    background: #3f2f00;
    border: 1px solid #a16207;
    color: #FEF3C7;
    padding: 12px;
    border-radius: 12px;
    margin-bottom: 10px;
    font-weight: 600;
}

.alert-blue {
    background: #172554;
    border: 1px solid #1d4ed8;
    color: #DBEAFE;
    padding: 12px;
    border-radius: 12px;
    margin-bottom: 10px;
    font-weight: 600;
}

div[data-testid="stMetric"] {
    background-color: #111827;
    border: 1px solid #374151;
    padding: 14px;
    border-radius: 14px;
}

div[data-testid="stMetric"] label {
    color: #D1D5DB !important;
}

div[data-testid="stMetric"] div {
    color: white !important;
}

.stButton > button {
    border-radius: 12px;
    font-weight: 700;
    padding: 0.7rem 1rem;
}

.small-note {
    color: #CBD5E1;
    font-size: 0.9rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">Sports AI Betting Dashboard</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">Manual live odds scanner with dashboard, alerts, best plays, actual plays mode, middle plays, and arbitrage plays</div>',
    unsafe_allow_html=True
)

API_KEY = st.secrets.get("ODDS_API_KEY", "")

SPORT_OPTIONS = {
    "NBA": "basketball_nba",
    "NHL": "icehockey_nhl",
    "NFL": "americanfootball_nfl",
    "MLB": "baseball_mlb",
    "NCAAF": "americanfootball_ncaaf",
}

if not API_KEY:
    st.error("Missing ODDS_API_KEY in Streamlit secrets.")
    st.stop()


# -----------------------------
# HELPERS
# -----------------------------
def american_to_decimal(odds):
    if odds is None:
        return None

    try:
        odds = float(odds)
    except Exception:
        return None

    if odds > 0:
        return (odds / 100.0) + 1.0
    if odds < 0:
        return (100.0 / abs(odds)) + 1.0
    return None


def implied_prob_from_american(odds):
    dec = american_to_decimal(odds)
    if dec is None or dec <= 1:
        return None
    return 1 / dec


def calculate_arb_stakes(odds_a, odds_b, bankroll):
    dec_a = american_to_decimal(odds_a)
    dec_b = american_to_decimal(odds_b)

    if dec_a is None or dec_b is None or bankroll <= 0:
        return None, None, None, None

    inv_a = 1 / dec_a
    inv_b = 1 / dec_b
    total_inv = inv_a + inv_b

    if total_inv >= 1:
        return None, None, None, None

    stake_a = bankroll * (inv_a / total_inv)
    stake_b = bankroll * (inv_b / total_inv)
    payout = stake_a * dec_a
    profit = payout - bankroll

    return round(stake_a, 2), round(stake_b, 2), round(payout, 2), round(profit, 2)


def fetch_odds(sport_key, regions="us", markets="h2h,spreads"):
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
    params = {
        "apiKey": API_KEY,
        "regions": regions,
        "markets": markets,
        "oddsFormat": "american",
    }

    response = requests.get(url, params=params, timeout=30)

    if response.status_code != 200:
        raise Exception(f"API error {response.status_code}: {response.text}")

    return response.json()


def extract_available_books(events):
    books = {}
    for event in events:
        for bookmaker in event.get("bookmakers", []):
            key = bookmaker.get("key")
            title = bookmaker.get("title")
            if key and title:
                books[key] = title
    return dict(sorted(books.items(), key=lambda x: x[1].lower()))


def filter_events_by_books(events, selected_book_keys):
    if not selected_book_keys:
        return events

    filtered_events = []

    for event in events:
        filtered_bookmakers = [
            b for b in event.get("bookmakers", [])
            if b.get("key") in selected_book_keys
        ]

        if filtered_bookmakers:
            new_event = event.copy()
            new_event["bookmakers"] = filtered_bookmakers
            filtered_events.append(new_event)

    return filtered_events


def get_market_map(bookmaker, market_key):
    market_map = {}

    for market in bookmaker.get("markets", []):
        if market.get("key") == market_key:
            for outcome in market.get("outcomes", []):
                name = outcome.get("name")
                if name is not None:
                    market_map[name] = {
                        "price": outcome.get("price"),
                        "point": outcome.get("point"),
                    }

    return market_map


def kelly_fraction_from_edge(edge_pct, kelly_multiplier):
    edge_decimal = edge_pct / 100.0
    raw_fraction = max(edge_decimal, 0.0)
    adjusted_fraction = raw_fraction * kelly_multiplier
    return adjusted_fraction


def score_arbitrage_row(profit_pct, guaranteed_profit):
    profit_pct = 0 if pd.isna(profit_pct) else float(profit_pct)
    guaranteed_profit = 0 if pd.isna(guaranteed_profit) else float(guaranteed_profit)
    score = (profit_pct * 4.0) + (guaranteed_profit * 0.4)
    return round(score, 2)


def score_middle_row(middle_gap, odds_a, odds_b):
    middle_gap = 0 if pd.isna(middle_gap) else float(middle_gap)
    bonus = 0

    try:
        if float(odds_a) > 0:
            bonus += 0.5
    except Exception:
        pass

    try:
        if float(odds_b) > 0:
            bonus += 0.5
    except Exception:
        pass

    score = (middle_gap * 3.0) + bonus
    return round(score, 2)


def classify_middle_strength(gap, medium_threshold, strong_threshold):
    if gap >= strong_threshold:
        return "Strong"
    if gap >= medium_threshold:
        return "Medium"
    return "Weak"


def build_middle_distribution(raw_mid_df):
    if raw_mid_df.empty or "middle_gap" not in raw_mid_df.columns:
        return pd.DataFrame(columns=["Gap Range", "Count"])

    gap_values = pd.to_numeric(raw_mid_df["middle_gap"], errors="coerce").dropna()

    bins = [
        ("0.5 - 0.99", (gap_values >= 0.5) & (gap_values < 1.0)),
        ("1.0 - 1.49", (gap_values >= 1.0) & (gap_values < 1.5)),
        ("1.5 - 1.99", (gap_values >= 1.5) & (gap_values < 2.0)),
        ("2.0 - 2.99", (gap_values >= 2.0) & (gap_values < 3.0)),
        ("3.0+", (gap_values >= 3.0)),
    ]

    rows = []
    for label, mask in bins:
        rows.append({"Gap Range": label, "Count": int(mask.sum())})

    return pd.DataFrame(rows)


def apply_actual_plays_filter(
    df,
    actual_plays_only,
    actual_middle_min_gap,
    actual_middle_min_score,
    actual_arb_min_profit_pct,
    actual_arb_min_profit_dollars,
):
    if df.empty or not actual_plays_only:
        return df.copy()

    filtered = df.copy()

    middle_mask = (
        (filtered["type"] == "Middle") &
        (pd.to_numeric(filtered["middle_gap"], errors="coerce").fillna(0) >= actual_middle_min_gap) &
        (pd.to_numeric(filtered["score"], errors="coerce").fillna(0) >= actual_middle_min_score)
    )

    arb_mask = (
        (filtered["type"] == "Arbitrage") &
        (pd.to_numeric(filtered["profit_%"], errors="coerce").fillna(0) >= actual_arb_min_profit_pct) &
        (pd.to_numeric(filtered["guaranteed_profit"], errors="coerce").fillna(0) >= actual_arb_min_profit_dollars)
    )

    return filtered[middle_mask | arb_mask].copy()


def render_top_play_cards(final_df):
    if final_df.empty:
        st.info("No top plays to show.")
        return

    top_df = final_df.sort_values(by="score", ascending=False).head(3).reset_index(drop=True)

    st.markdown("### Best Plays")

    for idx, (_, row) in enumerate(top_df.iterrows(), start=1):
        type_label = row.get("type", "")
        game = row.get("game", "")
        score = row.get("score", "")
        bet_a = row.get("bet_a", "")
        book_a = row.get("book_a", "")
        odds_a = row.get("odds_a", "")
        bet_b = row.get("bet_b", "")
        book_b = row.get("book_b", "")
        odds_b = row.get("odds_b", "")

        if type_label == "Arbitrage":
            details = f"Profit %: {row.get('profit_%', '')} | Guaranteed Profit: ${row.get('guaranteed_profit', '')}"
        else:
            details = f"Middle Gap: {row.get('middle_gap', '')} | Strength: {row.get('middle_strength', '')}"

        st.markdown(
            f"""
            <div class="play-card">
                <div><b>#{idx} {type_label}</b> | <b>Score:</b> {score}</div>
                <div><b>Game:</b> {game}</div>
                <div><b>Play A:</b> {bet_a} @ {book_a} ({odds_a})</div>
                <div><b>Play B:</b> {bet_b} @ {book_b} ({odds_b})</div>
                <div><b>Details:</b> {details}</div>
            </div>
            """,
            unsafe_allow_html=True
        )


def render_alerts(arb_df, raw_mid_df, shown_df, arb_alert_profit, middle_alert_gap):
    st.markdown("### Alerts")
    alert_count = 0

    if not arb_df.empty:
        arb_hits = arb_df[pd.to_numeric(arb_df["profit_%"], errors="coerce") >= arb_alert_profit]
        if not arb_hits.empty:
            best_arb = arb_hits.sort_values(by="score", ascending=False).iloc[0]
            st.markdown(
                f"""
                <div class="alert-green">
                🚨 Arbitrage Alert: {best_arb['game']} | Profit {best_arb['profit_%']}% | Guaranteed Profit ${best_arb['guaranteed_profit']}
                </div>
                """,
                unsafe_allow_html=True
            )
            alert_count += 1

    if not raw_mid_df.empty:
        middle_hits = raw_mid_df[pd.to_numeric(raw_mid_df["middle_gap"], errors="coerce") >= middle_alert_gap]
        if not middle_hits.empty:
            best_mid = middle_hits.sort_values(by="score", ascending=False).iloc[0]
            st.markdown(
                f"""
                <div class="alert-yellow">
                🎯 Middle Alert: {best_mid['game']} | Gap {best_mid['middle_gap']} | Strength {best_mid['middle_strength']}
                </div>
                """,
                unsafe_allow_html=True
            )
            alert_count += 1

    if not shown_df.empty:
        st.markdown(
            f"""
            <div class="alert-blue">
            ℹ️ Playable Rows Available: {len(shown_df)} shown after current filters.
            </div>
            """,
            unsafe_allow_html=True
        )
        alert_count += 1

    if alert_count == 0:
        st.info("No alerts triggered with current settings.")


# -----------------------------
# DETECTORS
# -----------------------------
def detect_arbitrage(events, bankroll, min_profit=0.0, min_profit_dollars=0.0, min_stake_filter=1.0):
    rows = []

    for event in events:
        home_team = event.get("home_team")
        away_team = event.get("away_team")
        game = f"{away_team} @ {home_team}"

        home_prices = []
        away_prices = []

        for bookmaker in event.get("bookmakers", []):
            h2h = get_market_map(bookmaker, "h2h")
            book_title = bookmaker.get("title", "Unknown")

            if home_team in h2h and h2h[home_team].get("price") is not None:
                home_prices.append({
                    "book": book_title,
                    "team": home_team,
                    "odds": h2h[home_team]["price"],
                })

            if away_team in h2h and h2h[away_team].get("price") is not None:
                away_prices.append({
                    "book": book_title,
                    "team": away_team,
                    "odds": h2h[away_team]["price"],
                })

        for home_offer in home_prices:
            for away_offer in away_prices:
                if home_offer["book"] == away_offer["book"]:
                    continue

                p1 = implied_prob_from_american(home_offer["odds"])
                p2 = implied_prob_from_american(away_offer["odds"])

                if p1 is None or p2 is None:
                    continue

                total_prob = p1 + p2

                if total_prob < 1:
                    profit_pct = round((1 - total_prob) * 100, 2)

                    if profit_pct >= min_profit:
                        stake_a, stake_b, payout, guaranteed_profit = calculate_arb_stakes(
                            home_offer["odds"],
                            away_offer["odds"],
                            bankroll,
                        )

                        if guaranteed_profit is None:
                            continue
                        if guaranteed_profit < min_profit_dollars:
                            continue
                        if stake_a < min_stake_filter or stake_b < min_stake_filter:
                            continue

                        score = score_arbitrage_row(profit_pct, guaranteed_profit)

                        rows.append({
                            "type": "Arbitrage",
                            "score": score,
                            "game": game,
                            "profit_%": profit_pct,
                            "bet_a": home_offer["team"],
                            "book_a": home_offer["book"],
                            "odds_a": home_offer["odds"],
                            "stake_a": stake_a,
                            "bet_b": away_offer["team"],
                            "book_b": away_offer["book"],
                            "odds_b": away_offer["odds"],
                            "stake_b": stake_b,
                            "middle_gap": None,
                            "middle_strength": None,
                            "kelly_note": "Use arb split",
                            "kelly_stake_each": None,
                            "expected_payout": payout,
                            "guaranteed_profit": guaranteed_profit,
                        })

    return pd.DataFrame(rows)


def detect_spread_middles(
    events,
    middle_stake,
    min_gap=1.0,
    middle_edge_pct=2.0,
    middle_kelly_bankroll=500.0,
    kelly_multiplier=0.5,
    medium_threshold=1.0,
    strong_threshold=2.0,
):
    rows = []

    kelly_fraction = kelly_fraction_from_edge(middle_edge_pct, kelly_multiplier)
    kelly_total_stake = round(middle_kelly_bankroll * kelly_fraction, 2)
    kelly_stake_each = round(kelly_total_stake / 2, 2)

    for event in events:
        home_team = event.get("home_team")
        away_team = event.get("away_team")
        game = f"{away_team} @ {home_team}"

        by_book = []

        for bookmaker in event.get("bookmakers", []):
            spreads = get_market_map(bookmaker, "spreads")
            book_title = bookmaker.get("title", "Unknown")

            home_data = spreads.get(home_team)
            away_data = spreads.get(away_team)

            if (
                home_data
                and away_data
                and home_data.get("point") is not None
                and away_data.get("point") is not None
            ):
                by_book.append({
                    "book": book_title,
                    "home_team": home_team,
                    "away_team": away_team,
                    "home_price": home_data.get("price"),
                    "away_price": away_data.get("price"),
                    "home_point": float(home_data.get("point")),
                    "away_point": float(away_data.get("point")),
                })

        for a in by_book:
            for b in by_book:
                if a["book"] == b["book"]:
                    continue

                home_gap = a["home_point"] - b["home_point"]
                if home_gap >= min_gap:
                    gap = round(home_gap, 2)
                    strength = classify_middle_strength(gap, medium_threshold, strong_threshold)
                    score = score_middle_row(gap, a["home_price"], b["away_price"])

                    rows.append({
                        "type": "Middle",
                        "score": score,
                        "game": game,
                        "profit_%": None,
                        "bet_a": f"{home_team} {a['home_point']:+}",
                        "book_a": a["book"],
                        "odds_a": a["home_price"],
                        "stake_a": round(middle_stake, 2),
                        "bet_b": f"{away_team} {b['away_point']:+}",
                        "book_b": b["book"],
                        "odds_b": b["away_price"],
                        "stake_b": round(middle_stake, 2),
                        "middle_gap": gap,
                        "middle_strength": strength,
                        "kelly_note": "Kelly-style middle cap",
                        "kelly_stake_each": kelly_stake_each,
                        "expected_payout": None,
                        "guaranteed_profit": None,
                    })

                away_gap = a["away_point"] - b["away_point"]
                if away_gap >= min_gap:
                    gap = round(away_gap, 2)
                    strength = classify_middle_strength(gap, medium_threshold, strong_threshold)
                    score = score_middle_row(gap, a["away_price"], b["home_price"])

                    rows.append({
                        "type": "Middle",
                        "score": score,
                        "game": game,
                        "profit_%": None,
                        "bet_a": f"{away_team} {a['away_point']:+}",
                        "book_a": a["book"],
                        "odds_a": a["away_price"],
                        "stake_a": round(middle_stake, 2),
                        "bet_b": f"{home_team} {b['home_point']:+}",
                        "book_b": b["book"],
                        "odds_b": b["home_price"],
                        "stake_b": round(middle_stake, 2),
                        "middle_gap": gap,
                        "middle_strength": strength,
                        "kelly_note": "Kelly-style middle cap",
                        "kelly_stake_each": kelly_stake_each,
                        "expected_payout": None,
                        "guaranteed_profit": None,
                    })

    return pd.DataFrame(rows)


def highlight_rows(row):
    if row["type"] == "Arbitrage":
        return ["background-color: #DCFCE7"] * len(row)
    if row["type"] == "Middle":
        return ["background-color: #FEF9C3"] * len(row)
    return [""] * len(row)


# -----------------------------
# SESSION STATE
# -----------------------------
if "available_books" not in st.session_state:
    st.session_state.available_books = {}
if "selected_books" not in st.session_state:
    st.session_state.selected_books = []
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

# -----------------------------
# CONTROLS
# -----------------------------
st.markdown('<div class="section-card">', unsafe_allow_html=True)

r1c1, r1c2, r1c3 = st.columns(3)
with r1c1:
    sport_label = st.selectbox("Choose sport", list(SPORT_OPTIONS.keys()), index=0)
    sport_key = SPORT_OPTIONS[sport_label]
with r1c2:
    show_arbs = st.checkbox("Scan Arbitrage", value=True)
with r1c3:
    show_middles = st.checkbox("Scan Middles", value=True)

r2c1, r2c2, r2c3 = st.columns(3)
with r2c1:
    middle_focus_mode = st.checkbox("Middle Focus Mode", value=True)
with r2c2:
    actual_plays_only = st.checkbox("Actual Plays Only", value=False)
with r2c3:
    kelly_mode = st.selectbox("Kelly Mode", ["Quarter Kelly", "Half Kelly", "Full Kelly"], index=1)

if kelly_mode == "Quarter Kelly":
    kelly_multiplier = 0.25
elif kelly_mode == "Half Kelly":
    kelly_multiplier = 0.50
else:
    kelly_multiplier = 1.00

r3c1, r3c2, r3c3 = st.columns(3)
with r3c1:
    min_profit = st.number_input("Min Arb Profit %", min_value=0.0, value=0.0, step=0.5)
with r3c2:
    min_profit_dollars = st.number_input("Min Arb Profit ($)", min_value=0.0, value=0.0, step=0.5)
with r3c3:
    min_stake_filter = st.number_input("Min Bet Size ($)", min_value=0.0, value=1.0, step=1.0)

r4c1, r4c2 = st.columns(2)
with r4c1:
    bankroll = st.number_input("Arbitrage Bankroll ($)", min_value=1.0, value=100.0, step=10.0)
with r4c2:
    middle_stake = st.number_input("Middle Stake Per Side ($)", min_value=1.0, value=25.0, step=5.0)

r5c1, r5c2, r5c3 = st.columns(3)
with r5c1:
    min_gap = st.number_input("Min Middle Gap", min_value=0.5, value=1.0, step=0.5)
with r5c2:
    middle_edge_pct = st.number_input("Estimated Middle Edge %", min_value=0.0, value=2.0, step=0.5)
with r5c3:
    middle_kelly_bankroll = st.number_input("Middle Kelly Bankroll ($)", min_value=1.0, value=500.0, step=25.0)

r6c1, r6c2 = st.columns(2)
with r6c1:
    medium_threshold = st.number_input("Medium Middle Threshold", min_value=0.5, value=1.0, step=0.5)
with r6c2:
    strong_threshold = st.number_input("Strong Middle Threshold", min_value=0.5, value=2.0, step=0.5)

if strong_threshold <= medium_threshold:
    st.warning("Strong Middle Threshold must be greater than Medium Middle Threshold.")
    st.stop()

r7c1, r7c2 = st.columns(2)
with r7c1:
    arb_alert_profit = st.number_input("Arb Alert Profit %", min_value=0.0, value=1.0, step=0.5)
with r7c2:
    middle_alert_gap = st.number_input("Middle Alert Gap", min_value=0.5, value=1.0, step=0.5)

st.markdown("#### Actual Plays Rules")
r8c1, r8c2 = st.columns(2)
with r8c1:
    actual_middle_min_gap = st.number_input("Actual Middle Min Gap", min_value=0.5, value=1.0, step=0.5)
with r8c2:
    actual_middle_min_score = st.number_input("Actual Middle Min Score", min_value=0.0, value=2.0, step=0.5)

r9c1, r9c2 = st.columns(2)
with r9c1:
    actual_arb_min_profit_pct = st.number_input("Actual Arb Min Profit %", min_value=0.0, value=1.0, step=0.5)
with r9c2:
    actual_arb_min_profit_dollars = st.number_input("Actual Arb Min Profit ($)", min_value=0.0, value=1.0, step=0.5)

st.markdown(
    '<div class="small-note">Arbitrage uses the exact arb split. Kelly is used as a conservative middle stake cap. Manual scan only.</div>',
    unsafe_allow_html=True,
)

st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------
# SPORTSBOOK SELECTION
# -----------------------------
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown("### Sportsbook Selection")

load_books = st.button("Load Available Sportsbooks")
if load_books:
    with st.spinner("Loading sportsbooks..."):
        try:
            preview_events = fetch_odds(sport_key)
            books = extract_available_books(preview_events)
            st.session_state.available_books = books
            st.session_state.selected_books = list(books.keys())

            if books:
                st.success(f"Loaded {len(books)} sportsbooks for {sport_label}.")
            else:
                st.warning("No sportsbooks returned for this sport right now.")
        except Exception as e:
            st.error(f"Error loading sportsbooks: {e}")

if st.session_state.available_books:
    selected_books = st.multiselect(
        "Choose the sportsbooks available to you",
        options=list(st.session_state.available_books.keys()),
        default=st.session_state.selected_books,
        format_func=lambda x: st.session_state.available_books[x],
    )
else:
    selected_books = []
    st.info("Press 'Load Available Sportsbooks' first, then choose the books you want to use.")

st.markdown('</div>', unsafe_allow_html=True)

scan_button = st.button("Scan Live Odds", type="primary")
st.info("The app only scans when you press the button. No automatic refresh is running.")

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
                    min_profit=min_profit,
                    min_profit_dollars=min_profit_dollars,
                    min_stake_filter=min_stake_filter,
                )
                if not arb_df.empty:
                    arb_df = arb_df.sort_values(by="score", ascending=False)

            if show_middles:
                raw_mid_df = detect_spread_middles(
                    filtered_events,
                    middle_stake=middle_stake,
                    min_gap=min_gap,
                    middle_edge_pct=middle_edge_pct,
                    middle_kelly_bankroll=middle_kelly_bankroll,
                    kelly_multiplier=kelly_multiplier,
                    medium_threshold=medium_threshold,
                    strong_threshold=strong_threshold,
                )

                mid_df = raw_mid_df.copy()

                if not mid_df.empty and middle_focus_mode:
                    mid_df = mid_df[mid_df["middle_strength"].isin(["Medium", "Strong"])].copy()

                if not mid_df.empty:
                    mid_df["strength_rank"] = mid_df["middle_strength"].map({
                        "Strong": 3,
                        "Medium": 2,
                        "Weak": 1
                    })
                    mid_df = mid_df.sort_values(
                        by=["strength_rank", "middle_gap", "score"],
                        ascending=[False, False, False]
                    ).drop(columns=["strength_rank"])

            if not arb_df.empty:
                results.append(arb_df)
            if not mid_df.empty:
                results.append(mid_df)

            final_df = pd.concat(results, ignore_index=True) if results else pd.DataFrame()
            distribution_df = build_middle_distribution(raw_mid_df)

            final_df = apply_actual_plays_filter(
                final_df,
                actual_plays_only=actual_plays_only,
                actual_middle_min_gap=actual_middle_min_gap,
                actual_middle_min_score=actual_middle_min_score,
                actual_arb_min_profit_pct=actual_arb_min_profit_pct,
                actual_arb_min_profit_dollars=actual_arb_min_profit_dollars,
            )

            filtered_mid_df = pd.DataFrame()
            filtered_arb_df = pd.DataFrame()

            if not final_df.empty:
                filtered_mid_df = final_df[final_df["type"] == "Middle"].copy()
                filtered_arb_df = final_df[final_df["type"] == "Arbitrage"].copy()

            st.session_state.scan_complete = True
            st.session_state.final_df = final_df
            st.session_state.arb_df = filtered_arb_df
            st.session_state.mid_df = filtered_mid_df
            st.session_state.raw_mid_df = raw_mid_df
            st.session_state.distribution_df = distribution_df
            st.session_state.raw_events_count = len(raw_events)
            st.session_state.raw_books_count = raw_books_count

        except Exception as e:
            st.error(f"Error fetching live odds: {e}")

# -----------------------------
# TABS
# -----------------------------
tab1, tab2, tab3 = st.tabs(["Dashboard", "Middle Plays", "Arbitrage Plays"])

with tab1:
    st.subheader("Dashboard Summary")

    if st.session_state.scan_complete:
        final_df = st.session_state.final_df
        arb_df = st.session_state.arb_df
        raw_mid_df = st.session_state.raw_mid_df
        mid_df = st.session_state.mid_df
        distribution_df = st.session_state.distribution_df

        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Events Pulled", st.session_state.raw_events_count)
        s2.metric("Books Returned", st.session_state.raw_books_count)
        s3.metric("Arb Rows Found", len(arb_df))
        s4.metric("Raw Middle Rows Found", len(raw_mid_df))

        s5, s6 = st.columns(2)
        s5.metric("Filtered Middle Rows", len(mid_df))
        s6.metric("Actual Plays Only", "ON" if actual_plays_only else "OFF")

        if not final_df.empty:
            arb_count = int((final_df["type"] == "Arbitrage").sum()) if "type" in final_df.columns else 0
            middle_count = int((final_df["type"] == "Middle").sum()) if "type" in final_df.columns else 0
            best_score = round(final_df["score"].max(), 2) if "score" in final_df.columns else 0

            arb_profit_total = 0.0
            if "guaranteed_profit" in final_df.columns:
                arb_profit_total = pd.to_numeric(final_df["guaranteed_profit"], errors="coerce").fillna(0).sum()

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Opportunities", len(final_df))
            m2.metric("Arbitrage Rows", arb_count)
            m3.metric("Middle Rows Shown", middle_count)
            m4.metric("Best Score", best_score)

            m5, m6 = st.columns(2)
            m5.metric("Total Arb Profit ($)", round(arb_profit_total, 2))
            m6.metric("Kelly Mode", kelly_mode)

            if selected_books:
                chosen_names = [
                    st.session_state.available_books[b]
                    for b in selected_books
                    if b in st.session_state.available_books
                ]
                st.caption("Using sportsbooks: " + ", ".join(chosen_names))

            render_alerts(arb_df, raw_mid_df, final_df, arb_alert_profit, middle_alert_gap)
            render_top_play_cards(final_df)

            st.markdown("### Middle Gap Distribution")
            if not distribution_df.empty:
                st.dataframe(distribution_df, use_container_width=True)
            else:
                st.info("No middle gap distribution available for this scan.")

            st.success(f"Found {len(final_df)} opportunity rows.")
        else:
            if len(raw_mid_df) > 0 and len(mid_df) == 0 and (middle_focus_mode or actual_plays_only):
                st.warning("Rows were found before filtering, but current focus or actual-play filters removed them.")
            else:
                st.warning("No live opportunities found with the current settings and selected sportsbooks.")
    else:
        st.info("Run a scan to populate the dashboard.")

with tab2:
    st.subheader("Middle Plays")

    if st.session_state.scan_complete:
        raw_mid_df = st.session_state.raw_mid_df
        mid_df = st.session_state.mid_df
        distribution_df = st.session_state.distribution_df

        if len(raw_mid_df) > 0 and len(mid_df) == 0 and (middle_focus_mode or actual_plays_only):
            st.warning("Middle rows exist before filtering, but current focus or actual-play filters removed them.")
            st.info("Lower your middle thresholds or turn off one of the filters and scan again.")
        elif not mid_df.empty:
            middle_display_columns = [
                "type",
                "score",
                "game",
                "bet_a",
                "book_a",
                "odds_a",
                "stake_a",
                "bet_b",
                "book_b",
                "odds_b",
                "stake_b",
                "middle_gap",
                "middle_strength",
                "kelly_note",
                "kelly_stake_each",
            ]

            display_mid_df = mid_df[middle_display_columns].reset_index(drop=True)
            st.success(f"Found {len(display_mid_df)} middle rows.")
            st.dataframe(
                display_mid_df.style.apply(highlight_rows, axis=1),
                use_container_width=True,
            )

            st.markdown("### Middle Gap Distribution")
            if not distribution_df.empty:
                st.dataframe(distribution_df, use_container_width=True)
        else:
            st.warning("No middle plays found for the current scan.")
    else:
        st.info("Run a scan to view middle plays.")

with tab3:
    st.subheader("Arbitrage Plays")

    if st.session_state.scan_complete:
        arb_df = st.session_state.arb_df

        if not arb_df.empty:
            arb_display_columns = [
                "type",
                "score",
                "game",
                "profit_%",
                "bet_a",
                "book_a",
                "odds_a",
                "stake_a",
                "bet_b",
                "book_b",
                "odds_b",
                "stake_b",
                "expected_payout",
                "guaranteed_profit",
                "kelly_note",
            ]

            display_arb_df = arb_df[arb_display_columns].reset_index(drop=True)
            st.success(f"Found {len(display_arb_df)} arbitrage rows.")
            st.dataframe(
                display_arb_df.style.apply(highlight_rows, axis=1),
                use_container_width=True,
            )
        else:
            st.warning("No arbitrage plays found for the current scan.")
    else:
        st.info("Run a scan to view arbitrage plays.")
