import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from statistics import mean

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

.bet-slip {
    background: #0B1220;
    border: 2px solid #334155;
    padding: 18px;
    border-radius: 16px;
    margin-top: 10px;
    margin-bottom: 10px;
    color: #F8FAFC;
    line-height: 1.7;
    font-size: 1rem;
}

.bet-slip-title {
    font-size: 1.2rem;
    font-weight: 800;
    margin-bottom: 10px;
    color: #FFFFFF;
}

.bet-leg {
    background: #111827;
    border: 1px solid #475569;
    padding: 12px;
    border-radius: 12px;
    margin-top: 10px;
    margin-bottom: 10px;
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

.alert-gray {
    background: #1f2937;
    border: 1px solid #4b5563;
    color: #f3f4f6;
    padding: 12px;
    border-radius: 12px;
    margin-bottom: 10px;
    font-weight: 600;
}

.ai-card {
    background: #111827;
    border: 1px solid #475569;
    padding: 14px;
    border-radius: 14px;
    margin-bottom: 10px;
    color: #F8FAFC;
    line-height: 1.6;
}

.ai-final-card {
    background: #0B1220;
    border: 2px solid #2563EB;
    padding: 18px;
    border-radius: 16px;
    margin-bottom: 12px;
    color: #F8FAFC;
    line-height: 1.7;
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
    '<div class="sub-title">Manual live odds scanner with dashboard, alerts, best plays, execution mode, actual plays mode, bet tracking, and NBA AI Engine V1</div>',
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
# GENERAL HELPERS
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


def fetch_odds(sport_key, regions="us", markets="h2h,spreads,totals"):
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


# -----------------------------
# BET TRACKER HELPERS
# -----------------------------
def create_tracker_row_from_play(row):
    total_stake = (
        pd.to_numeric(pd.Series([row.get("stake_a")]), errors="coerce").fillna(0).iloc[0] +
        pd.to_numeric(pd.Series([row.get("stake_b")]), errors="coerce").fillna(0).iloc[0]
    )

    return {
        "date_added": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "type": row.get("type", ""),
        "game": row.get("game", ""),
        "score": row.get("score", ""),
        "bet_a": row.get("bet_a", ""),
        "book_a": row.get("book_a", ""),
        "odds_a": row.get("odds_a", ""),
        "stake_a": row.get("stake_a", ""),
        "bet_b": row.get("bet_b", ""),
        "book_b": row.get("book_b", ""),
        "odds_b": row.get("odds_b", ""),
        "stake_b": row.get("stake_b", ""),
        "middle_gap": row.get("middle_gap", ""),
        "middle_strength": row.get("middle_strength", ""),
        "expected_payout": row.get("expected_payout", ""),
        "guaranteed_profit": row.get("guaranteed_profit", ""),
        "status": "Pending",
        "actual_profit": 0.0,
        "notes": "",
        "total_stake": round(total_stake, 2),
    }


def get_tracker_summary(tracker_df):
    if tracker_df.empty:
        return {
            "total_tracked": 0,
            "wins": 0,
            "losses": 0,
            "pushes": 0,
            "pending": 0,
            "profit": 0.0,
            "roi": 0.0,
        }

    status_series = tracker_df["status"].astype(str)
    actual_profit = pd.to_numeric(tracker_df["actual_profit"], errors="coerce").fillna(0)
    total_stake = pd.to_numeric(tracker_df["total_stake"], errors="coerce").fillna(0)

    settled_mask = status_series.isin(["Win", "Loss", "Push"])
    settled_stake = total_stake[settled_mask].sum()
    total_profit = actual_profit.sum()

    roi = 0.0
    if settled_stake > 
