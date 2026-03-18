import streamlit as st
import pandas as pd
import requests
from datetime import datetime

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

.ai-card {
    background: #111827;
    border: 1px solid #475569;
    padding: 14px;
    border-radius: 14px;
    margin-bottom: 12px;
    color: #F8FAFC;
    line-height: 1.6;
}

.ai-card-title {
    font-size: 1.05rem;
    font-weight: 800;
    margin-bottom: 8px;
    color: #FFFFFF;
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

.best-bet-card {
    background: #052e16;
    border: 2px solid #22c55e;
    padding: 18px;
    border-radius: 16px;
    margin-bottom: 12px;
    color: #DCFCE7;
    line-height: 1.7;
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
    '<div class="sub-title">Manual live odds scanner with dashboard, alerts, best plays, execution mode, actual plays mode, bet tracking, and NBA AI Engine V2</div>',
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


def safe_mean(values):
    vals = [float(v) for v in values if v is not None and pd.notna(v)]
    if not vals:
        return None
    return sum(vals) / len(vals)


def safe_std(values):
    vals = [float(v) for v in values if v is not None and pd.notna(v)]
    if len(vals) <= 1:
        return 0.0
    mean_val = sum(vals) / len(vals)
    variance = sum((v - mean_val) ** 2 for v in vals) / len(vals)
    return variance ** 0.5


def clamp(value, low, high):
    return max(low, min(high, value))


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
    return raw_fraction * kelly_multiplier


def score_arbitrage_row(profit_pct, guaranteed_profit):
    profit_pct = 0 if pd.isna(profit_pct) else float(profit_pct)
    guaranteed_profit = 0 if pd.isna(guaranteed_profit) else float(guaranteed_profit)
    return round((profit_pct * 4.0) + (guaranteed_profit * 0.4), 2)


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

    return round((middle_gap * 3.0) + bonus, 2)


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
        (filtered["type"] == "Middle")
        & (pd.to_numeric(filtered["middle_gap"], errors="coerce").fillna(0) >= actual_middle_min_gap)
        & (pd.to_numeric(filtered["score"], errors="coerce").fillna(0) >= actual_middle_min_score)
    )

    arb_mask = (
        (filtered["type"] == "Arbitrage")
        & (pd.to_numeric(filtered["profit_%"], errors="coerce").fillna(0) >= actual_arb_min_profit_pct)
        & (pd.to_numeric(filtered["guaranteed_profit"], errors="coerce").fillna(0) >= actual_arb_min_profit_dollars)
    )

    return filtered[middle_mask | arb_mask].copy()


# -----------------------------
# BET TRACKER HELPERS
# -----------------------------
def create_tracker_row_from_play(row):
    total_stake = (
        pd.to_numeric(pd.Series([row.get("stake_a")]), errors="coerce").fillna(0).iloc[0]
        + pd.to_numeric(pd.Series([row.get("stake_b")]), errors="coerce").fillna(0).iloc[0]
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
    if settled_stake > 0:
        roi = (total_profit / settled_stake) * 100

    return {
        "total_tracked": len(tracker_df),
        "wins": int((status_series == "Win").sum()),
        "losses": int((status_series == "Loss").sum()),
        "pushes": int((status_series == "Push").sum()),
        "pending": int((status_series == "Pending").sum()),
        "profit": round(float(total_profit), 2),
        "roi": round(float(roi), 2),
    }


# -----------------------------
# NBA AI ENGINE V2
# -----------------------------
def extract_nba_game_features(event):
    home_team = event.get("home_team")
    away_team = event.get("away_team")

    home_ml_odds = []
    away_ml_odds = []
    home_ml_probs = []
    away_ml_probs = []

    home_spread_points = []
    away_spread_points = []
    home_spread_prices = []
    away_spread_prices = []

    totals_points = []
    over_prices = []
    under_prices = []

    for bookmaker in event.get("bookmakers", []):
        h2h = get_market_map(bookmaker, "h2h")
        spreads = get_market_map(bookmaker, "spreads")
        totals = get_market_map(bookmaker, "totals")

        if home_team in h2h and h2h[home_team].get("price") is not None:
            price = h2h[home_team]["price"]
            home_ml_odds.append(price)
            home_ml_probs.append(implied_prob_from_american(price))

        if away_team in h2h and h2h[away_team].get("price") is not None:
            price = h2h[away_team]["price"]
            away_ml_odds.append(price)
            away_ml_probs.append(implied_prob_from_american(price))

        if home_team in spreads and spreads[home_team].get("point") is not None:
            home_spread_points.append(float(spreads[home_team]["point"]))
            home_spread_prices.append(spreads[home_team].get("price"))

        if away_team in spreads and spreads[away_team].get("point") is not None:
            away_spread_points.append(float(spreads[away_team]["point"]))
            away_spread_prices.append(spreads[away_team].get("price"))

        if "Over" in totals and totals["Over"].get("point") is not None:
            totals_points.append(float(totals["Over"]["point"]))
            over_prices.append(totals["Over"].get("price"))

        if "Under" in totals and totals["Under"].get("point") is not None:
            under_prices.append(totals["Under"].get("price"))

    consensus_home_prob = safe_mean(home_ml_probs)
    consensus_away_prob = safe_mean(away_ml_probs)

    consensus_home_spread = safe_mean(home_spread_points)
    consensus_away_spread = safe_mean(away_spread_points)
    consensus_total = safe_mean(totals_points)

    best_home_ml = max(home_ml_odds) if home_ml_odds else None
    best_away_ml = max(away_ml_odds) if away_ml_odds else None

    best_home_spread = max(home_spread_points) if home_spread_points else None
    best_away_spread = max(away_spread_points) if away_spread_points else None

    best_over_total = min(totals_points) if totals_points else None
    best_under_total = max(totals_points) if totals_points else None

    market_form_home = 0.0
    market_form_away = 0.0
    if consensus_home_prob is not None and consensus_away_prob is not None:
        market_form_home = (consensus_home_prob - 0.50) * 100
        market_form_away = (consensus_away_prob - 0.50) * 100

    power_edge = 0.0
    if consensus_home_prob is not None and consensus_away_prob is not None:
        power_edge = (consensus_home_prob - consensus_away_prob) * 100

    spread_edge = 0.0
    if consensus_home_spread is not None and best_home_spread is not None:
        spread_edge = best_home_spread - consensus_home_spread

    total_edge_over = 0.0
    total_edge_under = 0.0
    if consensus_total is not None and best_over_total is not None and best_under_total is not None:
        total_edge_over = consensus_total - best_over_total
        total_edge_under = best_under_total - consensus_total

    return {
        "home_team": home_team,
        "away_team": away_team,
        "consensus_home_prob": consensus_home_prob,
        "consensus_away_prob": consensus_away_prob,
        "consensus_home_spread": consensus_home_spread,
        "consensus_away_spread": consensus_away_spread,
        "consensus_total": consensus_total,
        "best_home_ml": best_home_ml,
        "best_away_ml": best_away_ml,
        "best_home_spread": best_home_spread,
        "best_away_spread": best_away_spread,
        "best_over_total": best_over_total,
        "best_under_total": best_under_total,
        "home_prob_std": safe_std(home_ml_probs),
        "away_prob_std": safe_std(away_ml_probs),
        "spread_std": safe_std(home_spread_points),
        "total_std": safe_std(totals_points),
        "books_count": len(event.get("bookmakers", [])),
        "market_form_home": round(market_form_home, 2),
        "market_form_away": round(market_form_away, 2),
        "power_edge": round(power_edge, 2),
        "spread_edge": round(spread_edge, 2),
        "total_edge_over": round(total_edge_over, 2),
        "total_edge_under": round(total_edge_under, 2),
    }


def nba_stats_ai_v2(features):
    home_team = features["home_team"]
    away_team = features["away_team"]
    power_edge = features["power_edge"]
    total_line = features["consensus_total"]
    home_spread = features["consensus_home_spread"]

    ml_pick = home_team if power_edge >= 0 else away_team
    ml_conf = clamp(round(56 + abs(power_edge) * 1.3, 1), 50, 92)

    if home_spread is None:
        spread_pick = "No spread edge"
        spread_conf = 50
    else:
        if home_spread < 0:
            spread_pick = f"{home_team} {home_spread:+.1f}"
        else:
            spread_pick = f"{away_team} {features['consensus_away_spread']:+.1f}"
        spread_conf = clamp(round(54 + abs(home_spread) * 2.0, 1), 50, 90)

    if total_line is None:
        total_pick = "No totals data"
        total_conf = 50
    else:
        if total_line >= 231:
            total_pick = f"Lean Under {round(total_line, 1)}"
        elif total_line <= 220:
            total_pick = f"Lean Over {round(total_line, 1)}"
        else:
            total_pick = f"Lean Pass / Slight Under {round(total_line, 1)}"
        total_conf = clamp(round(52 + abs(total_line - 225) * 0.8, 1), 50, 82)

    reason = (
        f"Power edge is {power_edge:+.2f} toward the {'home' if power_edge >= 0 else 'away'} side. "
        f"Consensus spread is {round(home_spread, 1) if home_spread is not None else 'N/A'} for the home team. "
        f"Consensus total is {round(total_line, 1) if total_line is not None else 'N/A'}."
    )

    return {
        "name": "Stats AI",
        "ml_pick": ml_pick,
        "spread_pick": spread_pick,
        "total_pick": total_pick,
        "ml_confidence": ml_conf,
        "spread_confidence": spread_conf,
        "total_confidence": total_conf,
        "reason": reason,
    }


def nba_matchup_ai_v2(features):
    home_team = features["home_team"]
    away_team = features["away_team"]

    adjusted_power_edge = features["power_edge"] + 2.0
    ml_pick = home_team if adjusted_power_edge >= 0 else away_team
    ml_conf = clamp(round(55 + abs(adjusted_power_edge) * 1.15, 1), 50, 88)

    home_spread = features["consensus_home_spread"]
    if home_spread is None:
        spread_pick = "No spread edge"
        spread_conf = 50
    else:
        adjusted_spread = home_spread - 1.0
        if adjusted_spread < 0:
            spread_pick = f"{home_team} {home_spread:+.1f}"
        else:
            spread_pick = f"{away_team} {features['consensus_away_spread']:+.1f}"
        spread_conf = clamp(round(53 + abs(adjusted_spread) * 2.1, 1), 50, 86)

    total_line = features["consensus_total"]
    if total_line is None:
        total_pick = "No totals data"
        total_conf = 50
    else:
        if 222 <= total_line <= 228:
            total_pick = f"Lean Under {round(total_line, 1)}"
        elif total_line < 222:
            total_pick = f"Lean Over {round(total_line, 1)}"
        else:
            total_pick = f"Lean Over {round(total_line, 1)}"
        total_conf = clamp(round(52 + abs(total_line - 225) * 0.75, 1), 50, 80)

    reason = (
        f"This model applies a home-court/context bump. "
        f"Adjusted power edge is {adjusted_power_edge:+.2f}. "
        f"It treats neutral totals around 225 as tighter and extreme totals as stronger leans."
    )

    return {
        "name": "Matchup AI",
        "ml_pick": ml_pick,
        "spread_pick": spread_pick,
        "total_pick": total_pick,
        "ml_confidence": ml_conf,
        "spread_confidence": spread_conf,
        "total_confidence": total_conf,
        "reason": reason,
    }


def nba_market_ai_v2(features):
    home_team = features["home_team"]
    away_team = features["away_team"]

    consensus_home_prob = features["consensus_home_prob"]
    consensus_away_prob = features["consensus_away_prob"]
    best_home_ml = features["best_home_ml"]
    best_away_ml = features["best_away_ml"]

    best_home_prob = implied_prob_from_american(best_home_ml) if best_home_ml is not None else None
    best_away_prob = implied_prob_from_american(best_away_ml) if best_away_ml is not None else None

    home_value = None
    away_value = None

    if consensus_home_prob is not None and best_home_prob is not None:
        home_value = consensus_home_prob - best_home_prob
    if consensus_away_prob is not None and best_away_prob is not None:
        away_value = consensus_away_prob - best_away_prob

    if home_value is None and away_value is None:
        ml_pick = "No edge"
        ml_conf = 50
    else:
        home_value = home_value if home_value is not None else -999
        away_value = away_value if away_value is not None else -999
        ml_pick = home_team if home_value >= away_value else away_team
        ml_conf = clamp(round(54 + max(home_value, away_value) * 260, 1), 50, 90)

    home_spread = features["consensus_home_spread"]
    away_spread = features["consensus_away_spread"]
    best_home_spread = features["best_home_spread"]
    best_away_spread = features["best_away_spread"]

    if home_spread is None or away_spread is None or best_home_spread is None or best_away_spread is None:
        spread_pick = "No spread edge"
        spread_conf = 50
    else:
        home_spread_edge = best_home_spread - home_spread
        away_spread_edge = best_away_spread - away_spread
        if home_spread_edge >= away_spread_edge:
            spread_pick = f"{home_team} {best_home_spread:+.1f}"
            spread_conf = clamp(round(53 + abs(home_spread_edge) * 12, 1), 50, 88)
        else:
            spread_pick = f"{away_team} {best_away_spread:+.1f}"
            spread_conf = clamp(round(53 + abs(away_spread_edge) * 12, 1), 50, 88)

    total_pick = "No totals data"
    total_conf = 50
    consensus_total = features["consensus_total"]
    over_edge = features["total_edge_over"]
    under_edge = features["total_edge_under"]

    if consensus_total is not None:
        if over_edge > under_edge and over_edge > 0:
            total_pick = f"Lean Over {round(features['best_over_total'], 1)}"
            total_conf = clamp(round(53 + over_edge * 10, 1), 50, 84)
        elif under_edge >= over_edge and under_edge > 0:
            total_pick = f"Lean Under {round(features['best_under_total'], 1)}"
            total_conf = clamp(round(53 + under_edge * 10, 1), 50, 84)
        else:
            total_pick = f"Lean Pass {round(consensus_total, 1)}"
            total_conf = 52

    reason = (
        "This model compares consensus numbers to the best available market prices and lines. "
        "It prefers the side or total with the strongest pricing edge."
    )

    return {
        "name": "Market AI",
        "ml_pick": ml_pick,
        "spread_pick": spread_pick,
        "total_pick": total_pick,
        "ml_confidence": ml_conf,
        "spread_confidence": spread_conf,
        "total_confidence": total_conf,
        "reason": reason,
    }


def nba_risk_ai_v2(features):
    risk_score = 0

    if features["books_count"] < 5:
        risk_score += 2
    if features["home_prob_std"] > 0.03:
        risk_score += 2
    if features["spread_std"] > 1.0:
        risk_score += 2
    if features["total_std"] > 2.0:
        risk_score += 2

    if risk_score <= 1:
        risk_level = "Low"
        confidence_adj = 0
    elif risk_score <= 3:
        risk_level = "Moderate"
        confidence_adj = -5
    else:
        risk_level = "High"
        confidence_adj = -10

    reason = (
        f"Books sampled: {features['books_count']}. "
        f"ML disagreement std: {round(features['home_prob_std'], 3)}. "
        f"Spread disagreement std: {round(features['spread_std'], 2)}. "
        f"Totals disagreement std: {round(features['total_std'], 2)}. "
        f"Risk level: {risk_level}."
    )

    return {
        "name": "Risk AI",
        "risk_level": risk_level,
        "confidence_adjustment": confidence_adj,
        "reason": reason,
    }


def parse_team_from_pick(pick_text, home_team, away_team):
    if isinstance(pick_text, str):
        if home_team in pick_text:
            return home_team
        if away_team in pick_text:
            return away_team
    return None


def summarize_votes(items):
    counts = {}
    for item in items:
        counts[item] = counts.get(item, 0) + 1
    return counts


def choose_best_bet(final_ml, final_spread, final_total):
    candidates = [
        {
            "bet_type": "Moneyline",
            "pick": final_ml["pick"],
            "confidence": final_ml["confidence"],
            "reason": final_ml["reason"]
        },
        {
            "bet_type": "Spread",
            "pick": final_spread["pick"],
            "confidence": final_spread["confidence"],
            "reason": final_spread["reason"]
        },
        {
            "bet_type": "Total",
            "pick": final_total["pick"],
            "confidence": final_total["confidence"],
            "reason": final_total["reason"]
        },
    ]

    filtered = [c for c in candidates if c["pick"] not in ["No edge", "No spread edge", "No totals data"]]
    if not filtered:
        return {
            "bet_type": "No Best Bet",
            "pick": "No strong edge",
            "confidence": 50,
            "reason": "The current market snapshot does not show a strong enough edge."
        }

    return max(filtered, key=lambda x: x["confidence"])


def nba_final_ai_v2(features, stats_ai, matchup_ai, market_ai, risk_ai):
    home_team = features["home_team"]
    away_team = features["away_team"]

    # ML
    ml_votes = {home_team: 0, away_team: 0}
    ml_picks = [stats_ai["ml_pick"], matchup_ai["ml_pick"], market_ai["ml_pick"]]
    for model_pick in ml_picks:
        if model_pick in ml_votes:
            ml_votes[model_pick] += 1

    final_ml_pick = max(ml_votes, key=ml_votes.get)
    base_ml_conf = safe_mean([
        stats_ai["ml_confidence"],
        matchup_ai["ml_confidence"],
        market_ai["ml_confidence"],
    ])
    base_ml_conf = 55 if base_ml_conf is None else base_ml_conf
    final_ml_conf = clamp(round(base_ml_conf + risk_ai["confidence_adjustment"], 1), 50, 95)
    final_ml = {
        "pick": final_ml_pick,
        "confidence": final_ml_conf,
        "reason": f"ML votes: {ml_votes}. Risk adjustment {risk_ai['confidence_adjustment']}."
    }

    # Spread
    spread_votes = {home_team: 0, away_team: 0}
    spread_picks = [stats_ai["spread_pick"], matchup_ai["spread_pick"], market_ai["spread_pick"]]
    for pick in spread_picks:
        team = parse_team_from_pick(pick, home_team, away_team)
        if team in spread_votes:
            spread_votes[team] += 1

    final_spread_team = max(spread_votes, key=spread_votes.get)
    if final_spread_team == home_team and features["best_home_spread"] is not None:
        final_spread_pick = f"{home_team} {features['best_home_spread']:+.1f}"
    elif final_spread_team == away_team and features["best_away_spread"] is not None:
        final_spread_pick = f"{away_team} {features['best_away_spread']:+.1f}"
    else:
        final_spread_pick = "No spread edge"

    base_spread_conf = safe_mean([
        stats_ai["spread_confidence"],
        matchup_ai["spread_confidence"],
        market_ai["spread_confidence"],
    ])
    base_spread_conf = 55 if base_spread_conf is None else base_spread_conf
    final_spread_conf = clamp(round(base_spread_conf + risk_ai["confidence_adjustment"], 1), 50, 95)
    final_spread = {
        "pick": final_spread_pick,
        "confidence": final_spread_conf,
        "reason": f"Spread votes: {spread_votes}. Risk adjustment {risk_ai['confidence_adjustment']}."
    }

    # Total
    total_picks = [stats_ai["total_pick"], matchup_ai["total_pick"], market_ai["total_pick"]]
    total_votes = summarize_votes(total_picks)
    final_total_pick = max(total_votes, key=total_votes.get) if total_votes else "No totals data"

    base_total_conf = safe_mean([
        stats_ai["total_confidence"],
        matchup_ai["total_confidence"],
        market_ai["total_confidence"],
    ])
    base_total_conf = 55 if base_total_conf is None else base_total_conf
    final_total_conf = clamp(round(base_total_conf + risk_ai["confidence_adjustment"], 1), 50, 95)
    final_total = {
        "pick": final_total_pick,
        "confidence": final_total_conf,
        "reason": f"Total votes: {total_votes}. Risk adjustment {risk_ai['confidence_adjustment']}."
    }

    best_bet = choose_best_bet(final_ml, final_spread, final_total)

    return {
        "ml": final_ml,
        "spread": final_spread,
        "total": final_total,
        "best_bet": best_bet,
        "summary_reason": (
            f"Final engine combined Stats AI, Matchup AI, and Market AI, then adjusted confidence for {risk_ai['risk_level']} risk."
        ),
    }


def run_nba_ai_engine_v2(event):
    features = extract_nba_game_features(event)
    stats_ai = nba_stats_ai_v2(features)
    matchup_ai = nba_matchup_ai_v2(features)
    market_ai = nba_market_ai_v2(features)
    risk_ai = nba_risk_ai_v2(features)
    final_ai = nba_final_ai_v2(features, stats_ai, matchup_ai, market_ai, risk_ai)

    return {
        "features": features,
        "stats_ai": stats_ai,
        "matchup_ai": matchup_ai,
        "market_ai": market_ai,
        "risk_ai": risk_ai,
        "final_ai": final_ai,
    }


# -----------------------------
# UI RENDER HELPERS
# -----------------------------
def render_ai_card(title, lines):
    body = "<br>".join(lines)
    st.markdown(
        f"""
        <div class="ai-card">
            <div class="ai-card-title">{title}</div>
            <div>{body}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


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


def render_execution_mode(final_df):
    st.markdown("### Execution Mode")

    if final_df.empty:
        st.info("No plays available for execution.")
        return

    working_df = final_df.reset_index(drop=True)
    options = [
        f"{idx + 1}. {row['type']} | {row['game']} | Score {row['score']}"
        for idx, row in working_df.iterrows()
    ]

    selected_label = st.selectbox("Choose a play to prepare", options=options)
    selected_index = options.index(selected_label)
    row = working_df.iloc[selected_index]

    type_label = row.get("type", "")
    game = row.get("game", "")
    score = row.get("score", "")
    bet_a = row.get("bet_a", "")
    book_a = row.get("book_a", "")
    odds_a = row.get("odds_a", "")
    stake_a = row.get("stake_a", "")
    bet_b = row.get("bet_b", "")
    book_b = row.get("book_b", "")
    odds_b = row.get("odds_b", "")
    stake_b = row.get("stake_b", "")

    if type_label == "Arbitrage":
        extra_details = (
            f"<b>Profit %:</b> {row.get('profit_%', '')}<br>"
            f"<b>Expected Payout:</b> ${row.get('expected_payout', '')}<br>"
            f"<b>Guaranteed Profit:</b> ${row.get('guaranteed_profit', '')}"
        )
    else:
        extra_details = (
            f"<b>Middle Gap:</b> {row.get('middle_gap', '')}<br>"
            f"<b>Strength:</b> {row.get('middle_strength', '')}<br>"
            f"<b>Kelly Stake Each:</b> ${row.get('kelly_stake_each', '')}"
        )

    st.markdown(
        f"""
        <div class="bet-slip">
            <div class="bet-slip-title">Bet Slip View</div>
            <div><b>Game:</b> {game}</div>
            <div><b>Type:</b> {type_label}</div>
            <div><b>Score:</b> {score}</div>

            <div class="bet-leg">
                <b>Bet A</b><br>
                <b>Play:</b> {bet_a}<br>
                <b>Sportsbook:</b> {book_a}<br>
                <b>Odds:</b> {odds_a}<br>
                <b>Stake:</b> ${stake_a}
            </div>

            <div class="bet-leg">
                <b>Bet B</b><br>
                <b>Play:</b> {bet_b}<br>
                <b>Sportsbook:</b> {book_b}<br>
                <b>Odds:</b> {odds_b}<br>
                <b>Stake:</b> ${stake_b}
            </div>

            <div>{extra_details}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if st.button("Add Selected Play to Bet Tracker"):
        new_row = create_tracker_row_from_play(row)
        st.session_state.tracker_df = pd.concat(
            [st.session_state.tracker_df, pd.DataFrame([new_row])],
            ignore_index=True
        )
        st.success("Selected play added to Bet Tracker.")


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
                home_prices.append({"book": book_title, "team": home_team, "odds": h2h[home_team]["price"]})

            if away_team in h2h and h2h[away_team].get("price") is not None:
                away_prices.append({"book": book_title, "team": away_team, "odds": h2h[away_team]["price"]})

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
if "tracker_df" not in st.session_state:
    st.session_state.tracker_df = pd.DataFrame(columns=[
        "date_added", "type", "game", "score",
        "bet_a", "book_a", "odds_a", "stake_a",
        "bet_b", "book_b", "odds_b", "stake_b",
        "middle_gap", "middle_strength",
        "expected_payout", "guaranteed_profit",
        "status", "actual_profit", "notes", "total_stake"
    ])
if "latest_filtered_events" not in st.session_state:
    st.session_state.latest_filtered_events = []
if "latest_sport_key" not in st.session_state:
    st.session_state.latest_sport_key = ""

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
            st.session_state.latest_filtered_events = filtered_events
            st.session_state.latest_sport_key = sport_key

        except Exception as e:
            st.error(f"Error fetching live odds: {e}")

# -----------------------------
# TABS
# -----------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Dashboard",
    "Middle Plays",
    "Arbitrage Plays",
    "Bet Tracker",
    "NBA AI Engine V2"
])

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
            render_execution_mode(final_df)

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
                "type", "score", "game",
                "bet_a", "book_a", "odds_a", "stake_a",
                "bet_b", "book_b", "odds_b", "stake_b",
                "middle_gap", "middle_strength",
                "kelly_note", "kelly_stake_each",
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
                "type", "score", "game", "profit_%",
                "bet_a", "book_a", "odds_a", "stake_a",
                "bet_b", "book_b", "odds_b", "stake_b",
                "expected_payout", "guaranteed_profit", "kelly_note",
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

with tab4:
    st.subheader("Bet Tracker")

    tracker_df = st.session_state.tracker_df.copy()
    summary = get_tracker_summary(tracker_df)

    t1, t2, t3, t4 = st.columns(4)
    t1.metric("Tracked Plays", summary["total_tracked"])
    t2.metric("Wins", summary["wins"])
    t3.metric("Losses", summary["losses"])
    t4.metric("Pending", summary["pending"])

    t5, t6, t7 = st.columns(3)
    t5.metric("Pushes", summary["pushes"])
    t6.metric("Total Profit ($)", summary["profit"])
    t7.metric("ROI %", summary["roi"])

    if tracker_df.empty:
        st.info("No tracked plays yet. Add a play from Execution Mode on the Dashboard.")
    else:
        st.markdown("### Update Tracked Play")

        tracker_options = [
            f"{i + 1}. {row['type']} | {row['game']} | {row['status']}"
            for i, row in tracker_df.reset_index(drop=True).iterrows()
        ]

        selected_tracker_label = st.selectbox("Choose tracked play", tracker_options)
        selected_tracker_index = tracker_options.index(selected_tracker_label)
        selected_tracker_row = tracker_df.reset_index(drop=True).iloc[selected_tracker_index]

        c1, c2 = st.columns(2)
        with c1:
            new_status = st.selectbox(
                "Update status",
                ["Pending", "Win", "Loss", "Push"],
                index=["Pending", "Win", "Loss", "Push"].index(selected_tracker_row["status"])
                if selected_tracker_row["status"] in ["Pending", "Win", "Loss", "Push"] else 0
            )
        with c2:
            new_actual_profit = st.number_input(
                "Actual Profit / Loss ($)",
                value=float(pd.to_numeric(pd.Series([selected_tracker_row["actual_profit"]]), errors="coerce").fillna(0).iloc[0]),
                step=1.0
            )

        new_notes = st.text_input("Notes", value=str(selected_tracker_row["notes"]))

        if st.button("Save Tracker Update"):
            st.session_state.tracker_df.loc[selected_tracker_index, "status"] = new_status
            st.session_state.tracker_df.loc[selected_tracker_index, "actual_profit"] = round(new_actual_profit, 2)
            st.session_state.tracker_df.loc[selected_tracker_index, "notes"] = new_notes
            st.success("Tracked play updated.")

        if st.button("Delete Selected Tracked Play"):
            st.session_state.tracker_df = st.session_state.tracker_df.drop(
                st.session_state.tracker_df.index[selected_tracker_index]
            ).reset_index(drop=True)
            st.success("Tracked play deleted.")

        st.markdown("### Tracked Bets Table")
        tracker_display_columns = [
            "date_added", "type", "game", "score",
            "bet_a", "book_a", "odds_a", "stake_a",
            "bet_b", "book_b", "odds_b", "stake_b",
            "status", "actual_profit", "notes", "total_stake"
        ]
        st.dataframe(
            st.session_state.tracker_df[tracker_display_columns],
            use_container_width=True,
        )

with tab5:
    st.subheader("NBA AI Engine V2")

    if not st.session_state.scan_complete:
        st.info("Run a scan first so the NBA AI Engine has games to analyze.")
    elif st.session_state.latest_sport_key != "basketball_nba":
        st.info("Switch the sport to NBA, run a scan, then come back to this tab.")
    else:
        nba_events = st.session_state.latest_filtered_events

        if not nba_events:
            st.warning("No NBA games are currently available in the latest scan.")
        else:
            nba_game_labels = [
                f"{event.get('away_team')} @ {event.get('home_team')}"
                for event in nba_events
            ]

            selected_game_label = st.selectbox("Choose NBA game to analyze", nba_game_labels)
            selected_game_index = nba_game_labels.index(selected_game_label)
            selected_event = nba_events[selected_game_index]

            ai_results = run_nba_ai_engine_v2(selected_event)
            features = ai_results["features"]
            stats_ai = ai_results["stats_ai"]
            matchup_ai = ai_results["matchup_ai"]
            market_ai = ai_results["market_ai"]
            risk_ai = ai_results["risk_ai"]
            final_ai = ai_results["final_ai"]
            best_bet = final_ai["best_bet"]

            top1, top2, top3, top4 = st.columns(4)
            top1.metric("Best ML", final_ai["ml"]["pick"])
            top2.metric("Best Spread", final_ai["spread"]["pick"])
            top3.metric("Best Total", final_ai["total"]["pick"])
            top4.metric("Best Bet Confidence", best_bet["confidence"])

            st.markdown(
                f"""
                <div class="best-bet-card">
                    <b>Final Recommended Best Bet:</b> {best_bet['bet_type']}<br>
                    <b>Pick:</b> {best_bet['pick']}<br>
                    <b>Confidence:</b> {best_bet['confidence']}<br>
                    <b>Reason:</b> {best_bet['reason']}
                </div>
                """,
                unsafe_allow_html=True
            )

            render_ai_card(
                "Stats AI",
                [
                    f"<b>ML Pick:</b> {stats_ai['ml_pick']} ({stats_ai['ml_confidence']})",
                    f"<b>Spread Pick:</b> {stats_ai['spread_pick']} ({stats_ai['spread_confidence']})",
                    f"<b>Total Pick:</b> {stats_ai['total_pick']} ({stats_ai['total_confidence']})",
                    f"<b>Reason:</b> {stats_ai['reason']}",
                ]
            )

            render_ai_card(
                "Matchup AI",
                [
                    f"<b>ML Pick:</b> {matchup_ai['ml_pick']} ({matchup_ai['ml_confidence']})",
                    f"<b>Spread Pick:</b> {matchup_ai['spread_pick']} ({matchup_ai['spread_confidence']})",
                    f"<b>Total Pick:</b> {matchup_ai['total_pick']} ({matchup_ai['total_confidence']})",
                    f"<b>Reason:</b> {matchup_ai['reason']}",
                ]
            )

            render_ai_card(
                "Market AI",
                [
                    f"<b>ML Pick:</b> {market_ai['ml_pick']} ({market_ai['ml_confidence']})",
                    f"<b>Spread Pick:</b> {market_ai['spread_pick']} ({market_ai['spread_confidence']})",
                    f"<b>Total Pick:</b> {market_ai['total_pick']} ({market_ai['total_confidence']})",
                    f"<b>Reason:</b> {market_ai['reason']}",
                ]
            )

            render_ai_card(
                "Risk AI",
                [
                    f"<b>Risk Level:</b> {risk_ai['risk_level']}",
                    f"<b>Confidence Adjustment:</b> {risk_ai['confidence_adjustment']}",
                    f"<b>Reason:</b> {risk_ai['reason']}",
                ]
            )

            render_ai_card(
                "Final AI Consensus",
                [
                    f"<b>Final ML:</b> {final_ai['ml']['pick']} ({final_ai['ml']['confidence']})",
                    f"<b>Final Spread:</b> {final_ai['spread']['pick']} ({final_ai['spread']['confidence']})",
                    f"<b>Final Total:</b> {final_ai['total']['pick']} ({final_ai['total']['confidence']})",
                    f"<b>Summary:</b> {final_ai['summary_reason']}",
                ]
            )

            st.markdown("### NBA Market Snapshot")
            snapshot_rows = pd.DataFrame([{
                "home_team": features["home_team"],
                "away_team": features["away_team"],
                "consensus_home_prob": round(features["consensus_home_prob"], 4) if features["consensus_home_prob"] is not None else None,
                "consensus_away_prob": round(features["consensus_away_prob"], 4) if features["consensus_away_prob"] is not None else None,
                "consensus_home_spread": round(features["consensus_home_spread"], 1) if features["consensus_home_spread"] is not None else None,
                "consensus_away_spread": round(features["consensus_away_spread"], 1) if features["consensus_away_spread"] is not None else None,
                "consensus_total": round(features["consensus_total"], 1) if features["consensus_total"] is not None else None,
                "power_edge": features["power_edge"],
                "market_form_home": features["market_form_home"],
                "market_form_away": features["market_form_away"],
                "spread_edge": features["spread_edge"],
                "total_edge_over": features["total_edge_over"],
                "total_edge_under": features["total_edge_under"],
                "books_count": features["books_count"],
            }])

            st.dataframe(snapshot_rows, use_container_width=True)
