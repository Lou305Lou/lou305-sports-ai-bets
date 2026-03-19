import streamlit as st
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(page_title="Sports AI Betting Dashboard", layout="wide")

# -----------------------------
# UI
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
.play-card b { color: #FFFFFF; }
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
div[data-testid="stMetric"] label { color: #D1D5DB !important; }
div[data-testid="stMetric"] div { color: white !important; }
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
    '<div class="sub-title">Manual live odds scanner with dashboard, alerts, best plays, execution mode, actual plays mode, bet tracking, Unified AI Engine V7, and Performance Learning System V8</div>',
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

SPORT_LABEL_FROM_KEY = {v: k for k, v in SPORT_OPTIONS.items()}

if not API_KEY:
    st.error("Missing ODDS_API_KEY in Streamlit secrets.")
    st.stop()

# -----------------------------
# GENERIC HELPERS
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


def confidence_tier(conf):
    if conf >= 82:
        return "💎 Elite"
    if conf >= 74:
        return "🟢 Strong"
    if conf >= 64:
        return "🟡 Medium"
    return "🔴 Low"


def grade_play(conf):
    if conf >= 84:
        return "A"
    if conf >= 74:
        return "B"
    return "C"


def weighted_average_confidence(items):
    total_weight = sum(weight for _, weight in items)
    if total_weight <= 0:
        return 55.0
    return sum(conf * weight for conf, weight in items) / total_weight


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
# PERFORMANCE LEARNING V8 HELPERS
# -----------------------------
def get_market_key_from_bet_type(features, bet_type):
    if bet_type == "Moneyline":
        return "ml"
    if bet_type == "Total":
        return "total"
    return "spread"


def create_ai_performance_row(features, final_ai, stats_ai, matchup_ai, market_ai, momentum_ai):
    bet_type = final_ai["best_bet"]["type"]
    market_key = get_market_key_from_bet_type(features, bet_type)

    stats_pick = stats_ai[f"{market_key}_pick"]
    stats_conf = stats_ai[f"{market_key}_confidence"]

    matchup_pick = matchup_ai[f"{market_key}_pick"]
    matchup_conf = matchup_ai[f"{market_key}_confidence"]

    market_pick = market_ai[f"{market_key}_pick"]
    market_conf = market_ai[f"{market_key}_confidence"]

    momentum_pick = momentum_ai[f"{market_key}_pick"]
    momentum_conf = momentum_ai[f"{market_key}_confidence"]

    final_pick = final_ai["best_bet"]["pick"]

    supporters = []
    if stats_pick == final_pick:
        supporters.append("Stats")
    if matchup_pick == final_pick:
        supporters.append("Matchup")
    if market_pick == final_pick:
        supporters.append("Market")
    if momentum_pick == final_pick:
        supporters.append("Momentum")

    return {
        "date_added": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sport": features["sport_name"],
        "game": f"{features['away_team']} @ {features['home_team']}",
        "bet_type": bet_type,
        "pick": final_pick,
        "confidence": final_ai["best_bet"]["confidence"],
        "grade": final_ai["best_bet"]["grade"],
        "engine_score": final_ai["final_score"],
        "supporters": ", ".join(supporters) if supporters else "None",
        "support_count": len(supporters),
        "stats_pick": stats_pick,
        "stats_conf": stats_conf,
        "matchup_pick": matchup_pick,
        "matchup_conf": matchup_conf,
        "market_pick": market_pick,
        "market_conf": market_conf,
        "momentum_pick": momentum_pick,
        "momentum_conf": momentum_conf,
        "status": "Pending",
        "stake": 100.0,
        "actual_profit": 0.0,
        "notes": "",
    }


def get_ai_performance_summary(ai_perf_df):
    if ai_perf_df.empty:
        return {
            "total_picks": 0,
            "wins": 0,
            "losses": 0,
            "pushes": 0,
            "pending": 0,
            "profit": 0.0,
            "roi": 0.0,
            "avg_confidence": 0.0,
        }

    status_series = ai_perf_df["status"].astype(str)
    actual_profit = pd.to_numeric(ai_perf_df["actual_profit"], errors="coerce").fillna(0)
    stake = pd.to_numeric(ai_perf_df["stake"], errors="coerce").fillna(0)
    confidence = pd.to_numeric(ai_perf_df["confidence"], errors="coerce").fillna(0)

    settled_mask = status_series.isin(["Win", "Loss", "Push"])
    settled_stake = stake[settled_mask].sum()
    total_profit = actual_profit.sum()

    roi = 0.0
    if settled_stake > 0:
        roi = (total_profit / settled_stake) * 100

    return {
        "total_picks": len(ai_perf_df),
        "wins": int((status_series == "Win").sum()),
        "losses": int((status_series == "Loss").sum()),
        "pushes": int((status_series == "Push").sum()),
        "pending": int((status_series == "Pending").sum()),
        "profit": round(float(total_profit), 2),
        "roi": round(float(roi), 2),
        "avg_confidence": round(float(confidence.mean()), 2) if len(confidence) else 0.0,
    }


def build_group_performance_table(ai_perf_df, group_col):
    if ai_perf_df.empty or group_col not in ai_perf_df.columns:
        return pd.DataFrame()

    df = ai_perf_df.copy()
    df["stake"] = pd.to_numeric(df["stake"], errors="coerce").fillna(0)
    df["actual_profit"] = pd.to_numeric(df["actual_profit"], errors="coerce").fillna(0)

    rows = []
    for group_value, group_df in df.groupby(group_col):
        status_series = group_df["status"].astype(str)
        settled_mask = status_series.isin(["Win", "Loss", "Push"])

        settled_stake = group_df.loc[settled_mask, "stake"].sum()
        profit = group_df["actual_profit"].sum()
        roi = (profit / settled_stake * 100) if settled_stake > 0 else 0.0

        rows.append({
            group_col: group_value,
            "Picks": len(group_df),
            "Wins": int((status_series == "Win").sum()),
            "Losses": int((status_series == "Loss").sum()),
            "Pushes": int((status_series == "Push").sum()),
            "Pending": int((status_series == "Pending").sum()),
            "Profit ($)": round(float(profit), 2),
            "ROI %": round(float(roi), 2),
            "Avg Confidence": round(pd.to_numeric(group_df["confidence"], errors="coerce").fillna(0).mean(), 2),
        })

    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(by=["ROI %", "Profit ($)", "Picks"], ascending=[False, False, False]).reset_index(drop=True)
    return out


def confidence_bucket_label(conf):
    conf = float(conf)
    if conf >= 85:
        return "85+"
    if conf >= 75:
        return "75-84.9"
    if conf >= 65:
        return "65-74.9"
    return "Under 65"


def build_confidence_bucket_table(ai_perf_df):
    if ai_perf_df.empty:
        return pd.DataFrame()

    df = ai_perf_df.copy()
    df["confidence"] = pd.to_numeric(df["confidence"], errors="coerce").fillna(0)
    df["stake"] = pd.to_numeric(df["stake"], errors="coerce").fillna(0)
    df["actual_profit"] = pd.to_numeric(df["actual_profit"], errors="coerce").fillna(0)
    df["Confidence Bucket"] = df["confidence"].apply(confidence_bucket_label)

    rows = []
    for bucket, group_df in df.groupby("Confidence Bucket"):
        status_series = group_df["status"].astype(str)
        settled_mask = status_series.isin(["Win", "Loss", "Push"])

        settled_stake = group_df.loc[settled_mask, "stake"].sum()
        profit = group_df["actual_profit"].sum()
        roi = (profit / settled_stake * 100) if settled_stake > 0 else 0.0

        rows.append({
            "Confidence Bucket": bucket,
            "Picks": len(group_df),
            "Wins": int((status_series == "Win").sum()),
            "Losses": int((status_series == "Loss").sum()),
            "Pushes": int((status_series == "Push").sum()),
            "Pending": int((status_series == "Pending").sum()),
            "Profit ($)": round(float(profit), 2),
            "ROI %": round(float(roi), 2),
        })

    out = pd.DataFrame(rows)
    order = {"85+": 4, "75-84.9": 3, "65-74.9": 2, "Under 65": 1}
    if not out.empty:
        out["sort_order"] = out["Confidence Bucket"].map(order)
        out = out.sort_values(by="sort_order", ascending=False).drop(columns=["sort_order"]).reset_index(drop=True)
    return out


def build_model_performance_table(ai_perf_df):
    if ai_perf_df.empty:
        return pd.DataFrame()

    df = ai_perf_df.copy()
    df["stake"] = pd.to_numeric(df["stake"], errors="coerce").fillna(0)
    df["actual_profit"] = pd.to_numeric(df["actual_profit"], errors="coerce").fillna(0)

    model_specs = [
        ("Stats", "stats_pick", "stats_conf"),
        ("Matchup", "matchup_pick", "matchup_conf"),
        ("Market", "market_pick", "market_conf"),
        ("Momentum", "momentum_pick", "momentum_conf"),
    ]

    rows = []
    for model_name, pick_col, conf_col in model_specs:
        aligned_df = df[df[pick_col].astype(str) == df["pick"].astype(str)].copy()
        if aligned_df.empty:
            rows.append({
                "Model": model_name,
                "Supported Picks": 0,
                "Wins": 0,
                "Losses": 0,
                "Pushes": 0,
                "Pending": 0,
                "Profit ($)": 0.0,
                "ROI %": 0.0,
                "Avg Model Confidence": 0.0,
            })
            continue

        status_series = aligned_df["status"].astype(str)
        settled_mask = status_series.isin(["Win", "Loss", "Push"])
        settled_stake = aligned_df.loc[settled_mask, "stake"].sum()
        profit = aligned_df["actual_profit"].sum()
        roi = (profit / settled_stake * 100) if settled_stake > 0 else 0.0

        rows.append({
            "Model": model_name,
            "Supported Picks": len(aligned_df),
            "Wins": int((status_series == "Win").sum()),
            "Losses": int((status_series == "Loss").sum()),
            "Pushes": int((status_series == "Push").sum()),
            "Pending": int((status_series == "Pending").sum()),
            "Profit ($)": round(float(profit), 2),
            "ROI %": round(float(roi), 2),
            "Avg Model Confidence": round(pd.to_numeric(aligned_df[conf_col], errors="coerce").fillna(0).mean(), 2),
        })

    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(by=["ROI %", "Profit ($)", "Supported Picks"], ascending=[False, False, False]).reset_index(drop=True)
    return out


def recommend_v8_weights(model_perf_df, current_sport_key):
    profile = sport_profile(current_sport_key)
    if profile is None or model_perf_df.empty:
        return pd.DataFrame()

    base_map = profile["weights"]
    label_to_key = {
        "Stats": "stats",
        "Matchup": "matchup",
        "Market": "market",
        "Momentum": "momentum",
    }

    rows = []
    for _, row in model_perf_df.iterrows():
        model_label = row["Model"]
        model_key = label_to_key[model_label]
        base_weight = base_map[model_key]
        wins = float(row["Wins"])
        losses = float(row["Losses"])
        roi = float(row["ROI %"])

        settled = wins + losses + float(row["Pushes"])
        win_rate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0.0

        recommended_weight = base_weight
        note = "Keep base weight"

        if settled >= 5:
            if win_rate >= 58 and roi > 0:
                recommended_weight = round(base_weight + 0.10, 2)
                note = "Increase slightly"
            elif win_rate <= 45 or roi < -5:
                recommended_weight = round(max(0.75, base_weight - 0.10), 2)
                note = "Reduce slightly"
            else:
                recommended_weight = round(base_weight, 2)
                note = "Stable"

        rows.append({
            "Model": model_label,
            "Base Weight": base_weight,
            "Recommended Weight": recommended_weight,
            "Settled Picks": int(settled),
            "Win Rate %": round(win_rate, 2),
            "ROI %": round(roi, 2),
            "Note": note,
        })

    return pd.DataFrame(rows)
# -----------------------------
# AUTO-SAVE V8 HELPERS
# -----------------------------
def ai_pick_duplicate_exists(ai_perf_df, sport, game, bet_type, pick, scan_date):
    if ai_perf_df.empty:
        return False

    check_df = ai_perf_df.copy()
    check_df["scan_date_only"] = check_df["date_added"].astype(str).str[:10]

    return (
        (check_df["sport"] == sport) &
        (check_df["game"] == game) &
        (check_df["bet_type"] == bet_type) &
        (check_df["pick"] == pick) &
        (check_df["scan_date_only"] == scan_date)
    ).any()


def auto_save_ai_picks_to_v8(events, sport_key, ai_perf_df):
    if sport_key not in ["basketball_nba", "icehockey_nhl"]:
        return ai_perf_df, 0, 0

    updated_df = ai_perf_df.copy()
    auto_saved = 0
    duplicates = 0
    scan_date = datetime.now().strftime("%Y-%m-%d")

    for event in events:
        try:
            ai = run_unified_ai_engine_v7(event, sport_key)
            if ai is None:
                continue

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
                ai["stats_ai"],
                ai["matchup_ai"],
                ai["market_ai"],
                ai["momentum_ai"],
            )

            updated_df = pd.concat([updated_df, pd.DataFrame([new_row])], ignore_index=True)
            auto_saved += 1

        except:
            continue

    return updated_df, auto_saved, duplicates
# -----------------------------
# UNIFIED AI ENGINE V7
# -----------------------------
def sport_profile(sport_key):
    if sport_key == "basketball_nba":
        return {
            "sport_name": "NBA",
            "spread_label": "Spread",
            "spread_none": "No spread edge",
            "baseline_total": 225.0,
            "favorite_threshold": 0.53,
            "weights": {"stats": 1.15, "matchup": 1.00, "market": 1.20, "momentum": 0.95},
            "risk_thresholds": {"books_min": 5, "prob_std": 0.03, "spread_std": 1.0, "total_std": 2.0},
            "market_value_multiplier": 260.0,
            "final_form_mult": 0.55,
            "final_total_mult": 0.18,
            "final_stability_mult": 3.0,
            "spread_force_threshold": None,
        }

    if sport_key == "icehockey_nhl":
        return {
            "sport_name": "NHL",
            "spread_label": "Puck Line",
            "spread_none": "No puck line edge",
            "baseline_total": 6.0,
            "favorite_threshold": 0.53,
            "weights": {"stats": 1.10, "matchup": 1.00, "market": 1.15, "momentum": 0.95},
            "risk_thresholds": {"books_min": 5, "prob_std": 0.035, "spread_std": 0.8, "total_std": 0.8},
            "market_value_multiplier": 240.0,
            "final_form_mult": 0.60,
            "final_total_mult": 2.20,
            "final_stability_mult": 4.0,
            "spread_force_threshold": 6.0,
        }

    return None


def extract_unified_game_features(event, sport_key):
    profile = sport_profile(sport_key)
    if profile is None:
        return None

    home_team = event.get("home_team")
    away_team = event.get("away_team")

    home_ml_odds = []
    away_ml_odds = []
    home_ml_probs = []
    away_ml_probs = []
    home_spread_points = []
    away_spread_points = []
    totals_points = []

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

        if away_team in spreads and spreads[away_team].get("point") is not None:
            away_spread_points.append(float(spreads[away_team]["point"]))

        if "Over" in totals and totals["Over"].get("point") is not None:
            totals_points.append(float(totals["Over"]["point"]))

    consensus_home_prob = safe_mean(home_ml_probs)
    consensus_away_prob = safe_mean(away_ml_probs)
    consensus_home_spread = safe_mean(home_spread_points)
    consensus_away_spread = safe_mean(away_spread_points)
    consensus_total = safe_mean(totals_points)

    best_home_ml = max(home_ml_odds) if home_ml_odds else None
    best_away_ml = max(away_ml_odds) if away_ml_odds else None
    best_home_spread = max(home_spread_points) if home_spread_points else None
    best_away_spread = max(away_spread_points) if away_spread_points else None

    market_form_home = 0.0
    market_form_away = 0.0
    power_edge = 0.0

    if consensus_home_prob is not None and consensus_away_prob is not None:
        market_form_home = (consensus_home_prob - 0.50) * 100
        market_form_away = (consensus_away_prob - 0.50) * 100
        power_edge = (consensus_home_prob - consensus_away_prob) * 100

    if sport_key == "basketball_nba":
        home_strength_score = 50 + market_form_home + (power_edge * 0.6) + 2.0
        away_strength_score = 50 + market_form_away - (power_edge * 0.6)
    else:
        home_strength_score = 50 + market_form_home + (power_edge * 0.8) + 1.5
        away_strength_score = 50 + market_form_away - (power_edge * 0.8)

    form_gap = home_strength_score - away_strength_score

    baseline_total = profile["baseline_total"]
    totals_strength = abs(consensus_total - baseline_total) if consensus_total is not None else 0.0

    if sport_key == "basketball_nba":
        pace_factor = (consensus_total - baseline_total) / 2.5 if consensus_total is not None else 0.0
        environment_signal = pace_factor
    else:
        pace_factor = 0.0
        environment_signal = baseline_total - consensus_total if consensus_total is not None else 0.0

    home_favorite_flag = 1 if (consensus_home_prob is not None and consensus_home_prob > profile["favorite_threshold"]) else 0
    away_favorite_flag = 1 if (consensus_away_prob is not None and consensus_away_prob > profile["favorite_threshold"]) else 0

    ml_stability = 0.0
    if consensus_home_prob is not None and consensus_away_prob is not None:
        if sport_key == "basketball_nba":
            ml_stability = max(0.0, 1.0 - (safe_std(home_ml_probs + away_ml_probs) * 8.0))
        else:
            ml_stability = max(0.0, 1.0 - ((safe_std(home_ml_probs + away_ml_probs) * 8.0) + (safe_std(totals_points) * 0.18)))

    spread_pressure = abs(consensus_home_spread) if consensus_home_spread is not None else 0.0
    total_pressure = totals_strength

    return {
        "sport_key": sport_key,
        "sport_name": profile["sport_name"],
        "spread_label": profile["spread_label"],
        "spread_none": profile["spread_none"],
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
        "home_prob_std": safe_std(home_ml_probs),
        "away_prob_std": safe_std(away_ml_probs),
        "spread_std": safe_std(home_spread_points + away_spread_points),
        "total_std": safe_std(totals_points),
        "books_count": len(event.get("bookmakers", [])),
        "market_form_home": round(market_form_home, 2),
        "market_form_away": round(market_form_away, 2),
        "power_edge": round(power_edge, 2),
        "home_strength_score": round(home_strength_score, 2),
        "away_strength_score": round(away_strength_score, 2),
        "form_gap": round(form_gap, 2),
        "pace_factor": round(pace_factor, 2),
        "environment_signal": round(environment_signal, 2),
        "totals_strength": round(totals_strength, 2),
        "home_favorite_flag": home_favorite_flag,
        "away_favorite_flag": away_favorite_flag,
        "ml_stability": round(ml_stability, 3),
        "spread_pressure": round(spread_pressure, 2),
        "total_pressure": round(total_pressure, 2),
    }


def unified_stats_ai_v7(features):
    sport_key = features["sport_key"]
    home_team = features["home_team"]
    away_team = features["away_team"]

    ml_pick = home_team if features["form_gap"] >= 0 else away_team
    if sport_key == "basketball_nba":
        ml_conf = clamp(round(57 + abs(features["form_gap"]) * 1.1, 1), 50, 93)
    else:
        ml_conf = clamp(round(56 + abs(features["power_edge"]) * 1.15, 1), 50, 90)

    if features["consensus_home_spread"] is None:
        spread_pick = features["spread_none"]
        spread_conf = 50
    else:
        if sport_key == "basketball_nba":
            if features["consensus_home_spread"] < 0:
                spread_pick = f"{home_team} {features['consensus_home_spread']:+.1f}"
            else:
                spread_pick = f"{away_team} {features['consensus_away_spread']:+.1f}"
            spread_conf = clamp(round(54 + abs(features["consensus_home_spread"]) * 2.2 + abs(features["form_gap"]) * 0.4, 1), 50, 91)
        else:
            if features["consensus_home_spread"] < 0:
                spread_pick = f"{home_team} {features['consensus_home_spread']:+.1f}"
            else:
                spread_pick = f"{away_team} {features['consensus_away_spread']:+.1f}"
            spread_conf = clamp(round(53 + abs(features["consensus_home_spread"]) * 8.0 + abs(features["power_edge"]) * 0.2, 1), 50, 87)

    if features["consensus_total"] is None:
        total_pick = "No totals data"
        total_conf = 50
    else:
        if sport_key == "basketball_nba":
            if features["consensus_total"] >= 231:
                total_pick = f"Lean Under {round(features['consensus_total'], 1)}"
            elif features["consensus_total"] <= 220:
                total_pick = f"Lean Over {round(features['consensus_total'], 1)}"
            else:
                total_pick = f"Lean Pass / Slight Under {round(features['consensus_total'], 1)}"
            total_conf = clamp(round(52 + features["totals_strength"] * 0.9, 1), 50, 85)
        else:
            if features["consensus_total"] <= 5.5:
                total_pick = f"Lean Under {round(features['consensus_total'], 1)}"
            elif features["consensus_total"] >= 6.5:
                total_pick = f"Lean Over {round(features['consensus_total'], 1)}"
            else:
                total_pick = f"Lean Under {round(features['consensus_total'], 1)}"
            total_conf = clamp(round(52 + abs(features["environment_signal"]) * 6.5, 1), 50, 85)

    return {
        "name": "Stats AI",
        "ml_pick": ml_pick,
        "spread_pick": spread_pick,
        "total_pick": total_pick,
        "ml_confidence": ml_conf,
        "spread_confidence": spread_conf,
        "total_confidence": total_conf,
        "reason": (
            f"Home strength {features['home_strength_score']} vs away strength {features['away_strength_score']}. "
            f"Form gap {features['form_gap']:+.2f}. Environment signal {features['environment_signal']:+.2f}."
        ),
    }


def unified_matchup_ai_v7(features):
    sport_key = features["sport_key"]
    home_team = features["home_team"]
    away_team = features["away_team"]

    matchup_edge = features["form_gap"] + (2.0 if sport_key == "basketball_nba" else 1.0)
    ml_pick = home_team if matchup_edge >= 0 else away_team
    ml_conf = clamp(round((55 if sport_key == "basketball_nba" else 54) + abs(matchup_edge) * (1.0 if sport_key == "basketball_nba" else 0.9), 1), 50, 89)

    if features["consensus_home_spread"] is None:
        spread_pick = features["spread_none"]
        spread_conf = 50
    else:
        if features["consensus_home_spread"] < 0:
            spread_pick = f"{home_team} {features['consensus_home_spread']:+.1f}"
        else:
            spread_pick = f"{away_team} {features['consensus_away_spread']:+.1f}"

        if sport_key == "basketball_nba":
            signal = abs(features["consensus_home_spread"]) + abs(matchup_edge) * 0.3
            spread_conf = clamp(round(53 + signal * 2.0, 1), 50, 88)
        else:
            signal = abs(matchup_edge)
            spread_conf = clamp(round(52 + signal * 0.7 + 6.0, 1), 50, 84)

    if features["consensus_total"] is None:
        total_pick = "No totals data"
        total_conf = 50
    else:
        if sport_key == "basketball_nba":
            if features["pace_factor"] >= 1.5:
                total_pick = f"Lean Over {round(features['consensus_total'], 1)}"
            elif features["pace_factor"] <= -1.5:
                total_pick = f"Lean Under {round(features['consensus_total'], 1)}"
            elif features["consensus_total"] >= 228:
                total_pick = f"Lean Over {round(features['consensus_total'], 1)}"
            else:
                total_pick = f"Lean Under {round(features['consensus_total'], 1)}"
            total_conf = clamp(round(52 + abs(features["pace_factor"]) * 4.5, 1), 50, 83)
        else:
            if features["environment_signal"] > 0:
                total_pick = f"Lean Under {round(features['consensus_total'], 1)}"
            else:
                total_pick = f"Lean Over {round(features['consensus_total'], 1)}"
            total_conf = clamp(round(52 + abs(features["environment_signal"]) * 5.2, 1), 50, 82)

    return {
        "name": "Matchup AI",
        "ml_pick": ml_pick,
        "spread_pick": spread_pick,
        "total_pick": total_pick,
        "ml_confidence": ml_conf,
        "spread_confidence": spread_conf,
        "total_confidence": total_conf,
        "reason": f"Matchup edge {matchup_edge:+.2f}. Sport-adjusted context applied.",
    }


def unified_market_ai_v7(features):
    home_team = features["home_team"]
    away_team = features["away_team"]
    profile = sport_profile(features["sport_key"])

    best_home_prob = implied_prob_from_american(features["best_home_ml"]) if features["best_home_ml"] is not None else None
    best_away_prob = implied_prob_from_american(features["best_away_ml"]) if features["best_away_ml"] is not None else None

    home_value = None
    away_value = None
    if features["consensus_home_prob"] is not None and best_home_prob is not None:
        home_value = features["consensus_home_prob"] - best_home_prob
    if features["consensus_away_prob"] is not None and best_away_prob is not None:
        away_value = features["consensus_away_prob"] - best_away_prob

    if home_value is None and away_value is None:
        ml_pick = "No edge"
        ml_conf = 50
    else:
        home_value = home_value if home_value is not None else -999
        away_value = away_value if away_value is not None else -999
        ml_pick = home_team if home_value >= away_value else away_team
        ml_conf = clamp(round(54 + max(home_value, away_value) * profile["market_value_multiplier"], 1), 50, 91)

    if features["best_home_spread"] is None or features["best_away_spread"] is None:
        spread_pick = features["spread_none"]
        spread_conf = 50
    else:
        if profile["spread_force_threshold"] is not None and abs(features["power_edge"]) < profile["spread_force_threshold"]:
            spread_pick = features["spread_none"]
            spread_conf = 51
        else:
            if abs(features["best_home_spread"]) >= abs(features["best_away_spread"]):
                spread_pick = f"{home_team} {features['best_home_spread']:+.1f}"
            else:
                spread_pick = f"{away_team} {features['best_away_spread']:+.1f}"
            spread_conf = clamp(round(53 + abs(features["power_edge"]) * (0.8 if features["sport_key"] == "basketball_nba" else 0.7), 1), 50, 88)

    if features["consensus_total"] is None:
        total_pick = "No totals data"
        total_conf = 50
    else:
        if features["sport_key"] == "basketball_nba":
            if features["consensus_total"] >= 229:
                total_pick = f"Lean Under {round(features['consensus_total'], 1)}"
                total_conf = clamp(round(54 + features["totals_strength"] * 0.8, 1), 50, 86)
            elif features["consensus_total"] <= 221:
                total_pick = f"Lean Over {round(features['consensus_total'], 1)}"
                total_conf = clamp(round(54 + features["totals_strength"] * 0.8, 1), 50, 86)
            else:
                total_pick = f"Lean Pass {round(features['consensus_total'], 1)}"
                total_conf = 52
        else:
            if features["consensus_total"] <= 5.5:
                total_pick = f"Lean Under {round(features['consensus_total'], 1)}"
                total_conf = clamp(round(52 + abs(features["environment_signal"]) * 5.5, 1), 50, 83)
            elif features["consensus_total"] >= 6.5:
                total_pick = f"Lean Over {round(features['consensus_total'], 1)}"
                total_conf = clamp(round(52 + abs(features["environment_signal"]) * 5.5, 1), 50, 83)
            else:
                total_pick = f"Lean Pass {round(features['consensus_total'], 1)}"
                total_conf = 52

    return {
        "name": "Market AI",
        "ml_pick": ml_pick,
        "spread_pick": spread_pick,
        "total_pick": total_pick,
        "ml_confidence": ml_conf,
        "spread_confidence": spread_conf,
        "total_confidence": total_conf,
        "reason": (
            f"Market value home={round(home_value, 4) if home_value is not None else 'N/A'}, "
            f"away={round(away_value, 4) if away_value is not None else 'N/A'}."
        ),
    }


def unified_risk_ai_v7(features):
    profile = sport_profile(features["sport_key"])
    risk_score = 0

    if features["books_count"] < profile["risk_thresholds"]["books_min"]:
        risk_score += 2
    if features["home_prob_std"] > profile["risk_thresholds"]["prob_std"]:
        risk_score += 2
    if features["spread_std"] > profile["risk_thresholds"]["spread_std"]:
        risk_score += 2
    if features["total_std"] > profile["risk_thresholds"]["total_std"]:
        risk_score += 2

    if risk_score <= 1:
        risk_level = "Low"
        confidence_adj = 0
    elif risk_score <= 3:
        risk_level = "Moderate"
        confidence_adj = -5 if features["sport_key"] == "basketball_nba" else -4
    else:
        risk_level = "High"
        confidence_adj = -10 if features["sport_key"] == "basketball_nba" else -8

    return {
        "name": "Risk AI",
        "risk_level": risk_level,
        "confidence_adjustment": confidence_adj,
        "reason": (
            f"Books {features['books_count']}. ML std {round(features['home_prob_std'], 3)}. "
            f"{features['spread_label']} std {round(features['spread_std'], 2)}. "
            f"Total std {round(features['total_std'], 2)}."
        ),
    }


def unified_momentum_ai_v7(features):
    home_team = features["home_team"]
    away_team = features["away_team"]

    if features["sport_key"] == "basketball_nba":
        momentum_score = (
            features["power_edge"] * 0.7
            + (features["market_form_home"] - features["market_form_away"]) * 0.5
            + (features["ml_stability"] * 8.0)
        )
    else:
        momentum_score = (
            features["power_edge"]
            + (features["market_form_home"] - features["market_form_away"]) * 0.4
            + (features["ml_stability"] * 6.0)
            - (features["total_std"] * 0.8)
        )

    ml_pick = home_team if momentum_score >= 0 else away_team
    ml_conf = clamp(round((54 if features["sport_key"] == "basketball_nba" else 53) + abs(momentum_score) * (1.2 if features["sport_key"] == "basketball_nba" else 1.0), 1), 50, 90)

    if features["consensus_home_spread"] is None:
        spread_pick = features["spread_none"]
        spread_conf = 50
    else:
        if features["sport_key"] == "basketball_nba":
            if features["consensus_home_spread"] < 0:
                spread_pick = f"{home_team} {features['consensus_home_spread']:+.1f}"
            else:
                spread_pick = f"{away_team} {features['consensus_away_spread']:+.1f}"
            spread_conf = clamp(round(53 + (features["spread_pressure"] + abs(features["form_gap"]) * 0.15) * 1.6, 1), 50, 88)
        else:
            if abs(momentum_score) >= 6:
                spread_pick = f"{home_team if momentum_score >= 0 else away_team} -1.5"
                spread_conf = clamp(round(52 + abs(momentum_score) * 0.8, 1), 50, 84)
            else:
                spread_pick = features["spread_none"]
                spread_conf = 51

    if features["consensus_total"] is None:
        total_pick = "No totals data"
        total_conf = 50
    else:
        if features["sport_key"] == "basketball_nba":
            if features["total_pressure"] >= 5.0:
                total_pick = f"Lean {'Under' if features['consensus_total'] > 225 else 'Over'} {round(features['consensus_total'], 1)}"
            elif features["pace_factor"] > 0:
                total_pick = f"Lean Over {round(features['consensus_total'], 1)}"
            else:
                total_pick = f"Lean Under {round(features['consensus_total'], 1)}"
            total_conf = clamp(round(52 + features["total_pressure"] * 1.1 + features["ml_stability"] * 4.0, 1), 50, 86)
        else:
            if features["environment_signal"] > 0:
                total_pick = f"Lean Under {round(features['consensus_total'], 1)}"
            else:
                total_pick = f"Lean Over {round(features['consensus_total'], 1)}"
            total_conf = clamp(round(52 + abs(features["environment_signal"]) * 4.8 + features["ml_stability"] * 4.0, 1), 50, 84)

    return {
        "name": "Momentum AI",
        "ml_pick": ml_pick,
        "spread_pick": spread_pick,
        "total_pick": total_pick,
        "ml_confidence": ml_conf,
        "spread_confidence": spread_conf,
        "total_confidence": total_conf,
        "reason": (
            f"Momentum score {momentum_score:+.2f}. "
            f"Market stability {features['ml_stability']}."
        ),
    }


def unified_final_ai_v7(features, stats_ai, matchup_ai, market_ai, risk_ai, momentum_ai):
    profile = sport_profile(features["sport_key"])
    home_team = features["home_team"]
    away_team = features["away_team"]
    weights = profile["weights"]

    ml_weighted_votes = {home_team: 0.0, away_team: 0.0}
    for model_name, model in [
        ("stats", stats_ai),
        ("matchup", matchup_ai),
        ("market", market_ai),
        ("momentum", momentum_ai),
    ]:
        pick = model["ml_pick"]
        if pick in ml_weighted_votes:
            ml_weighted_votes[pick] += weights[model_name]

    ml_pick = max(ml_weighted_votes, key=ml_weighted_votes.get)
    ml_conf = weighted_average_confidence([
        (stats_ai["ml_confidence"], weights["stats"]),
        (matchup_ai["ml_confidence"], weights["matchup"]),
        (market_ai["ml_confidence"], weights["market"]),
        (momentum_ai["ml_confidence"], weights["momentum"]),
    ]) + risk_ai["confidence_adjustment"]
    ml_conf = clamp(round(ml_conf, 1), 50, 95)

    spread_pick = market_ai["spread_pick"] if market_ai["spread_pick"] != features["spread_none"] else stats_ai["spread_pick"]
    spread_conf = weighted_average_confidence([
        (stats_ai["spread_confidence"], weights["stats"]),
        (matchup_ai["spread_confidence"], weights["matchup"]),
        (market_ai["spread_confidence"], weights["market"]),
        (momentum_ai["spread_confidence"], weights["momentum"]),
    ]) + risk_ai["confidence_adjustment"]
    spread_conf = clamp(round(spread_conf, 1), 50, 95)

    total_pick = market_ai["total_pick"] if market_ai["total_pick"] != "No totals data" else stats_ai["total_pick"]
    total_conf = weighted_average_confidence([
        (stats_ai["total_confidence"], weights["stats"]),
        (matchup_ai["total_confidence"], weights["matchup"]),
        (market_ai["total_confidence"], weights["market"]),
        (momentum_ai["total_confidence"], weights["momentum"]),
    ]) + risk_ai["confidence_adjustment"]
    total_conf = clamp(round(total_conf, 1), 50, 95)

    best = max([
        ("Moneyline", ml_pick, ml_conf),
        (features["spread_label"], spread_pick, spread_conf),
        ("Total", total_pick, total_conf)
    ], key=lambda x: x[2])

    best_type, best_pick, best_conf = best

    final_score = round(
        best_conf
        + abs(features["form_gap"]) * profile["final_form_mult"]
        + features["totals_strength"] * profile["final_total_mult"]
        + features["ml_stability"] * profile["final_stability_mult"],
        1
    )

    return {
        "ml": {"pick": ml_pick, "confidence": ml_conf, "tier": confidence_tier(ml_conf)},
        "spread": {"pick": spread_pick, "confidence": spread_conf, "tier": confidence_tier(spread_conf)},
        "total": {"pick": total_pick, "confidence": total_conf, "tier": confidence_tier(total_conf)},
        "best_bet": {
            "type": best_type,
            "pick": best_pick,
            "confidence": best_conf,
            "grade": grade_play(best_conf),
        },
        "final_score": final_score,
        "debate_summary": (
            f"ML weighted votes {ml_weighted_votes}. "
            f"Stats={stats_ai['ml_pick']}, Matchup={matchup_ai['ml_pick']}, "
            f"Market={market_ai['ml_pick']}, Momentum={momentum_ai['ml_pick']}."
        ),
        "summary_reason": (
            f"Unified V7 used Stats, Matchup, Market, Momentum, and Risk AI for {profile['sport_name']}."
        ),
    }


def run_unified_ai_engine_v7(event, sport_key):
    features = extract_unified_game_features(event, sport_key)
    if features is None:
        return None

    stats_ai = unified_stats_ai_v7(features)
    matchup_ai = unified_matchup_ai_v7(features)
    market_ai = unified_market_ai_v7(features)
    risk_ai = unified_risk_ai_v7(features)
    momentum_ai = unified_momentum_ai_v7(features)
    final_ai = unified_final_ai_v7(features, stats_ai, matchup_ai, market_ai, risk_ai, momentum_ai)

    return {
        "features": features,
        "stats_ai": stats_ai,
        "matchup_ai": matchup_ai,
        "market_ai": market_ai,
        "risk_ai": risk_ai,
        "momentum_ai": momentum_ai,
        "final_ai": final_ai,
    }


def build_unified_v7_ranking_board(events, sport_key):
    rows = []
    for event in events:
        try:
            result = run_unified_ai_engine_v7(event, sport_key)
            if result is None:
                continue
            features = result["features"]
            final_ai = result["final_ai"]
            best_bet = final_ai["best_bet"]

            rows.append({
                "game": f"{features['away_team']} @ {features['home_team']}",
                "best_bet_type": best_bet["type"],
                "best_pick": best_bet["pick"],
                "confidence": best_bet["confidence"],
                "grade": best_bet["grade"],
                "ml_pick": final_ai["ml"]["pick"],
                "ml_conf": final_ai["ml"]["confidence"],
                f"{features['spread_label'].lower()}_pick": final_ai["spread"]["pick"],
                f"{features['spread_label'].lower()}_conf": final_ai["spread"]["confidence"],
                "total_pick": final_ai["total"]["pick"],
                "total_conf": final_ai["total"]["confidence"],
                "engine_score": final_ai["final_score"],
            })
        except Exception:
            continue

    board = pd.DataFrame(rows)
    if not board.empty:
        board = board.sort_values(by=["engine_score", "confidence"], ascending=[False, False]).reset_index(drop=True)
    return board


def get_unified_v7_top_plays(board_df):
    if board_df.empty:
        return None, None, None, None

    best_overall = board_df.sort_values(by=["engine_score", "confidence"], ascending=[False, False]).iloc[0]
    best_ml = board_df.sort_values(by=["ml_conf", "engine_score"], ascending=[False, False]).iloc[0]
    spread_conf_cols = [c for c in board_df.columns if c.endswith("_conf") and c not in ["ml_conf", "total_conf"]]
    spread_pick_cols = [c for c in board_df.columns if c.endswith("_pick") and c not in ["ml_pick", "total_pick"]]

    if spread_conf_cols and spread_pick_cols:
        spread_conf_col = spread_conf_cols[0]
        best_spread = board_df.sort_values(by=[spread_conf_col, "engine_score"], ascending=[False, False]).iloc[0]
    else:
        best_spread = best_overall

    best_total = board_df.sort_values(by=["total_conf", "engine_score"], ascending=[False, False]).iloc[0]
    return best_overall, best_ml, best_spread, best_total

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
                            home_offer["odds"], away_offer["odds"], bankroll
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
if "ai_perf_df" not in st.session_state:
    st.session_state.ai_perf_df = pd.DataFrame(columns=[
        "date_added", "sport", "game", "bet_type", "pick", "confidence", "grade", "engine_score",
        "supporters", "support_count",
        "stats_pick", "stats_conf",
        "matchup_pick", "matchup_conf",
        "market_pick", "market_conf",
        "momentum_pick", "momentum_conf",
        "status", "stake", "actual_profit", "notes"
    ])
if "auto_saved_ai_count" not in st.session_state:
    st.session_state.auto_saved_ai_count = 0

if "duplicate_ai_skipped_count" not in st.session_state:
    st.session_state.duplicate_ai_skipped_count = 0
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
# SPORTSBOOKS
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
# SCAN BUTTON LOGIC (CLEAN)
# -----------------------------
if scan_button:
    with st.spinner("Scanning live odds..."):
        try:
            raw_events = fetch_odds(sport_key)

            # Filter sportsbooks
            if selected_books:
                filtered_events = filter_events_by_books(raw_events, selected_books)
            else:
                filtered_events = raw_events

            raw_books_count = len(extract_available_books(raw_events))

            arb_df = pd.DataFrame()
            raw_mid_df = pd.DataFrame()
            mid_df = pd.DataFrame()
            results = []

            # Arbitrage
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

            # Middles
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
                    mid_df = mid_df[mid_df["middle_strength"].isin(["Medium", "Strong"])]

                if not mid_df.empty:
                    mid_df["rank"] = mid_df["middle_strength"].map({"Strong": 3, "Medium": 2, "Weak": 1})
                    mid_df = mid_df.sort_values(
                        by=["rank", "middle_gap", "score"],
                        ascending=[False, False, False]
                    ).drop(columns=["rank"])

            if not arb_df.empty:
                results.append(arb_df)
            if not mid_df.empty:
                results.append(mid_df)

            final_df = pd.concat(results, ignore_index=True) if results else pd.DataFrame()

            filtered_mid_df = final_df[final_df["type"] == "Middle"] if not final_df.empty else pd.DataFrame()
            filtered_arb_df = final_df[final_df["type"] == "Arbitrage"] if not final_df.empty else pd.DataFrame()

            # Save to session
            st.session_state.scan_complete = True
            st.session_state.final_df = final_df
            st.session_state.arb_df = filtered_arb_df
            st.session_state.mid_df = filtered_mid_df
            st.session_state.raw_mid_df = raw_mid_df
            st.session_state.raw_events_count = len(raw_events)
            st.session_state.raw_books_count = raw_books_count
            st.session_state.latest_filtered_events = filtered_events
            st.session_state.latest_sport_key = sport_key

            # AUTO SAVE AI PICKS (V8)
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
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Dashboard",
    "Middle Plays",
    "Arbitrage Plays",
    "Bet Tracker",
    "Unified AI Engine V7",
    "Performance Learning V8",
])

with tab1:
    st.subheader("Dashboard Summary")

    events_pulled = st.session_state.raw_events_count
    books_returned = st.session_state.raw_books_count
    arb_rows = len(st.session_state.arb_df)
    mid_rows = len(st.session_state.mid_df)

    arb_profit_total = (
        st.session_state.arb_df["profit_dollars"].sum()
        if not st.session_state.arb_df.empty else 0
    )

    kelly_mode = "Half Kelly"

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Events Pulled", events_pulled)
    m2.metric("Books Returned", books_returned)
    m3.metric("Arb Rows Found", arb_rows)
    m4.metric("Middle Rows Found", mid_rows)

    m5, m6, m7, m8 = st.columns(4)
    m5.metric("Total Arb Profit ($)", round(arb_profit_total, 2))
    m6.metric("Kelly Mode", kelly_mode)
    m7.metric("AI Picks Auto-Saved", st.session_state.auto_saved_ai_count)
    m8.metric("Duplicates Skipped", st.session_state.duplicate_ai_skipped_count)

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
            st.dataframe(display_mid_df.style.apply(highlight_rows, axis=1), use_container_width=True)

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
            st.dataframe(display_arb_df.style.apply(highlight_rows, axis=1), use_container_width=True)
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
        st.dataframe(st.session_state.tracker_df[tracker_display_columns], use_container_width=True)

with tab5:
    st.subheader("Unified AI Engine V7")

    if not st.session_state.scan_complete:
        st.info("Run a scan first so the AI engine has games to analyze.")
    elif st.session_state.latest_sport_key not in ["basketball_nba", "icehockey_nhl"]:
        st.info("Unified AI Engine V7 is currently tuned for NBA and NHL. Switch to NBA or NHL, run a scan, then return.")
    else:
        current_sport_key = st.session_state.latest_sport_key
        current_sport_name = SPORT_LABEL_FROM_KEY[current_sport_key]
        profile = sport_profile(current_sport_key)
        events = st.session_state.latest_filtered_events

        if not events:
            st.warning(f"No {current_sport_name} games are currently available in the latest scan.")
        else:
            ranking_board = build_unified_v7_ranking_board(events, current_sport_key)

            st.markdown(f"### {current_sport_name} Slate Ranking Board")
            if not ranking_board.empty:
                st.dataframe(ranking_board, use_container_width=True)

                best_overall, best_ml, best_spread, best_total = get_unified_v7_top_plays(ranking_board)
                spread_pick_col = [c for c in ranking_board.columns if c.endswith("_pick") and c not in ["ml_pick", "total_pick"]][0]
                spread_conf_col = [c for c in ranking_board.columns if c.endswith("_conf") and c not in ["ml_conf", "total_conf"]][0]

                st.markdown(f"### Top Overall Plays Across {current_sport_name} Slate")

                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.markdown(
                        f"""
                        <div class="best-bet-card">
                            <b>Best Overall Play</b><br>
                            <b>Game:</b> {best_overall['game']}<br>
                            <b>Type:</b> {best_overall['best_bet_type']}<br>
                            <b>Pick:</b> {best_overall['best_pick']}<br>
                            <b>Confidence:</b> {best_overall['confidence']} ({confidence_tier(best_overall['confidence'])})<br>
                            <b>Grade:</b> {best_overall['grade']}<br>
                            <b>Engine Score:</b> {best_overall['engine_score']}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                with c2:
                    st.markdown(
                        f"""
                        <div class="ai-card">
                            <div class="ai-card-title">Best Moneyline</div>
                            <div><b>Game:</b> {best_ml['game']}</div>
                            <div><b>Pick:</b> {best_ml['ml_pick']}</div>
                            <div><b>Confidence:</b> {best_ml['ml_conf']} ({confidence_tier(best_ml['ml_conf'])})</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                with c3:
                    st.markdown(
                        f"""
                        <div class="ai-card">
                            <div class="ai-card-title">Best {profile['spread_label']}</div>
                            <div><b>Game:</b> {best_spread['game']}</div>
                            <div><b>Pick:</b> {best_spread[spread_pick_col]}</div>
                            <div><b>Confidence:</b> {best_spread[spread_conf_col]} ({confidence_tier(best_spread[spread_conf_col])})</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                with c4:
                    st.markdown(
                        f"""
                        <div class="ai-card">
                            <div class="ai-card-title">Best Total</div>
                            <div><b>Game:</b> {best_total['game']}</div>
                            <div><b>Pick:</b> {best_total['total_pick']}</div>
                            <div><b>Confidence:</b> {best_total['total_conf']} ({confidence_tier(best_total['total_conf'])})</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            else:
                st.info("No ranking board available for the current scan.")

            game_labels = [f"{event.get('away_team')} @ {event.get('home_team')}" for event in events]
            selected_game_label = st.selectbox(f"Choose {current_sport_name} game to analyze", game_labels)
            selected_game_index = game_labels.index(selected_game_label)
            selected_event = events[selected_game_index]

            ai_results = run_unified_ai_engine_v7(selected_event, current_sport_key)
            features = ai_results["features"]
            stats_ai = ai_results["stats_ai"]
            matchup_ai = ai_results["matchup_ai"]
            market_ai = ai_results["market_ai"]
            risk_ai = ai_results["risk_ai"]
            momentum_ai = ai_results["momentum_ai"]
            final_ai = ai_results["final_ai"]
            best_bet = final_ai["best_bet"]

            top1, top2, top3, top4 = st.columns(4)
            top1.metric("Best ML", final_ai["ml"]["pick"])
            top2.metric(f"Best {profile['spread_label']}", final_ai["spread"]["pick"])
            top3.metric("Best Total", final_ai["total"]["pick"])
            top4.metric("Engine Score", final_ai["final_score"])

            st.markdown(
                f"""
                <div class="best-bet-card">
                    <b>Selected Game Best Bet:</b> {best_bet['type']}<br>
                    <b>Pick:</b> {best_bet['pick']}<br>
                    <b>Confidence:</b> {best_bet['confidence']} ({confidence_tier(best_bet['confidence'])})<br>
                    <b>Grade:</b> {best_bet['grade']}
                </div>
                """,
                unsafe_allow_html=True
            )

            if st.button("Save Selected AI Best Bet to Performance Learning V8"):
                new_ai_row = create_ai_performance_row(
                    features=features,
                    final_ai=final_ai,
                    stats_ai=stats_ai,
                    matchup_ai=matchup_ai,
                    market_ai=market_ai,
                    momentum_ai=momentum_ai,
                )
                st.session_state.ai_perf_df = pd.concat(
                    [st.session_state.ai_perf_df, pd.DataFrame([new_ai_row])],
                    ignore_index=True
                )
                st.success("AI pick saved to Performance Learning V8.")

            render_ai_card(
                "Final Unified Scorecards",
                [
                    f"<b>Moneyline:</b> {final_ai['ml']['pick']} | {final_ai['ml']['confidence']} | {final_ai['ml']['tier']}",
                    f"<b>{profile['spread_label']}:</b> {final_ai['spread']['pick']} | {final_ai['spread']['confidence']} | {final_ai['spread']['tier']}",
                    f"<b>Total:</b> {final_ai['total']['pick']} | {final_ai['total']['confidence']} | {final_ai['total']['tier']}",
                    f"<b>Engine Score:</b> {final_ai['final_score']}",
                    f"<b>Debate:</b> {final_ai['debate_summary']}",
                    f"<b>Summary:</b> {final_ai['summary_reason']}",
                ]
            )

            render_ai_card(
                "Stats AI",
                [
                    f"<b>ML Pick:</b> {stats_ai['ml_pick']} ({stats_ai['ml_confidence']})",
                    f"<b>{profile['spread_label']} Pick:</b> {stats_ai['spread_pick']} ({stats_ai['spread_confidence']})",
                    f"<b>Total Pick:</b> {stats_ai['total_pick']} ({stats_ai['total_confidence']})",
                    f"<b>Reason:</b> {stats_ai['reason']}",
                ]
            )

            render_ai_card(
                "Matchup AI",
                [
                    f"<b>ML Pick:</b> {matchup_ai['ml_pick']} ({matchup_ai['ml_confidence']})",
                    f"<b>{profile['spread_label']} Pick:</b> {matchup_ai['spread_pick']} ({matchup_ai['spread_confidence']})",
                    f"<b>Total Pick:</b> {matchup_ai['total_pick']} ({matchup_ai['total_confidence']})",
                    f"<b>Reason:</b> {matchup_ai['reason']}",
                ]
            )

            render_ai_card(
                "Market AI",
                [
                    f"<b>ML Pick:</b> {market_ai['ml_pick']} ({market_ai['ml_confidence']})",
                    f"<b>{profile['spread_label']} Pick:</b> {market_ai['spread_pick']} ({market_ai['spread_confidence']})",
                    f"<b>Total Pick:</b> {market_ai['total_pick']} ({market_ai['total_confidence']})",
                    f"<b>Reason:</b> {market_ai['reason']}",
                ]
            )

            render_ai_card(
                "Momentum AI",
                [
                    f"<b>ML Pick:</b> {momentum_ai['ml_pick']} ({momentum_ai['ml_confidence']})",
                    f"<b>{profile['spread_label']} Pick:</b> {momentum_ai['spread_pick']} ({momentum_ai['spread_confidence']})",
                    f"<b>Total Pick:</b> {momentum_ai['total_pick']} ({momentum_ai['total_confidence']})",
                    f"<b>Reason:</b> {momentum_ai['reason']}",
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

            st.markdown(f"### {current_sport_name} Market Snapshot")
            snapshot_rows = pd.DataFrame([{
                "sport": features["sport_name"],
                "home_team": features["home_team"],
                "away_team": features["away_team"],
                "consensus_home_prob": round(features["consensus_home_prob"], 4) if features["consensus_home_prob"] is not None else None,
                "consensus_away_prob": round(features["consensus_away_prob"], 4) if features["consensus_away_prob"] is not None else None,
                "consensus_home_spread": round(features["consensus_home_spread"], 1) if features["consensus_home_spread"] is not None else None,
                "consensus_away_spread": round(features["consensus_away_spread"], 1) if features["consensus_away_spread"] is not None else None,
                "consensus_total": round(features["consensus_total"], 1) if features["consensus_total"] is not None else None,
                "home_strength_score": features["home_strength_score"],
                "away_strength_score": features["away_strength_score"],
                "form_gap": features["form_gap"],
                "power_edge": features["power_edge"],
                "environment_signal": features["environment_signal"],
                "ml_stability": features["ml_stability"],
                "spread_pressure": features["spread_pressure"],
                "total_pressure": features["total_pressure"],
                "books_count": features["books_count"],
            }])

            st.dataframe(snapshot_rows, use_container_width=True)

with tab6:
    st.subheader("Performance Learning V8")

    ai_perf_df = st.session_state.ai_perf_df.copy()
    perf_summary = get_ai_performance_summary(ai_perf_df)

    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Tracked AI Picks", perf_summary["total_picks"])
    p2.metric("Wins", perf_summary["wins"])
    p3.metric("Losses", perf_summary["losses"])
    p4.metric("Pending", perf_summary["pending"])

    p5, p6, p7, p8 = st.columns(4)
    p5.metric("Pushes", perf_summary["pushes"])
    p6.metric("Total Profit ($)", perf_summary["profit"])
    p7.metric("ROI %", perf_summary["roi"])
    p8.metric("Avg Confidence", perf_summary["avg_confidence"])

    if ai_perf_df.empty:
        st.info("No AI picks saved yet. Save picks from Unified AI Engine V7 first.")
    else:
        st.markdown("### Update AI Pick Result")

        perf_options = [
            f"{i + 1}. {row['sport']} | {row['game']} | {row['bet_type']} | {row['pick']} | {row['status']}"
            for i, row in ai_perf_df.reset_index(drop=True).iterrows()
        ]

        selected_perf_label = st.selectbox("Choose AI tracked pick", perf_options)
        selected_perf_index = perf_options.index(selected_perf_label)
        selected_perf_row = ai_perf_df.reset_index(drop=True).iloc[selected_perf_index]

        c1, c2, c3 = st.columns(3)
        with c1:
            new_status = st.selectbox(
                "Update result status",
                ["Pending", "Win", "Loss", "Push"],
                index=["Pending", "Win", "Loss", "Push"].index(selected_perf_row["status"])
                if selected_perf_row["status"] in ["Pending", "Win", "Loss", "Push"] else 0,
                key="v8_status_select"
            )
        with c2:
            new_stake = st.number_input(
                "Stake ($)",
                value=float(pd.to_numeric(pd.Series([selected_perf_row["stake"]]), errors="coerce").fillna(100).iloc[0]),
                step=5.0,
                key="v8_stake_input"
            )
        with c3:
            new_actual_profit = st.number_input(
                "Actual Profit / Loss ($)",
                value=float(pd.to_numeric(pd.Series([selected_perf_row["actual_profit"]]), errors="coerce").fillna(0).iloc[0]),
                step=1.0,
                key="v8_profit_input"
            )

        new_notes = st.text_input(
            "Performance Notes",
            value=str(selected_perf_row["notes"]),
            key="v8_notes_input"
        )

        if st.button("Save Performance Update"):
            st.session_state.ai_perf_df.loc[selected_perf_index, "status"] = new_status
            st.session_state.ai_perf_df.loc[selected_perf_index, "stake"] = round(new_stake, 2)
            st.session_state.ai_perf_df.loc[selected_perf_index, "actual_profit"] = round(new_actual_profit, 2)
            st.session_state.ai_perf_df.loc[selected_perf_index, "notes"] = new_notes
            st.success("AI performance record updated.")

        if st.button("Delete Selected AI Performance Record"):
            st.session_state.ai_perf_df = st.session_state.ai_perf_df.drop(
                st.session_state.ai_perf_df.index[selected_perf_index]
            ).reset_index(drop=True)
            st.success("AI performance record deleted.")

        ai_perf_df = st.session_state.ai_perf_df.copy()

        st.markdown("### ROI by Sport")
        sport_perf_df = build_group_performance_table(ai_perf_df, "sport")
        if not sport_perf_df.empty:
            st.dataframe(sport_perf_df, use_container_width=True)

        st.markdown("### ROI by Bet Type")
        bet_type_perf_df = build_group_performance_table(ai_perf_df, "bet_type")
        if not bet_type_perf_df.empty:
            st.dataframe(bet_type_perf_df, use_container_width=True)

        st.markdown("### Confidence Bucket Tracking")
        conf_bucket_df = build_confidence_bucket_table(ai_perf_df)
        if not conf_bucket_df.empty:
            st.dataframe(conf_bucket_df, use_container_width=True)

        st.markdown("### Model Support Performance")
        model_perf_df = build_model_performance_table(ai_perf_df)
        if not model_perf_df.empty:
            st.dataframe(model_perf_df, use_container_width=True)

        if st.session_state.latest_sport_key in ["basketball_nba", "icehockey_nhl"]:
            current_sport_name = SPORT_LABEL_FROM_KEY[st.session_state.latest_sport_key]
            st.markdown(f"### Recommended Model Weights for {current_sport_name}")
            recommended_weights_df = recommend_v8_weights(model_perf_df, st.session_state.latest_sport_key)
            if not recommended_weights_df.empty:
                st.dataframe(recommended_weights_df, use_container_width=True)

        st.markdown("### AI Performance Records")
        perf_display_columns = [
            "date_added", "sport", "game", "bet_type", "pick", "confidence", "grade", "engine_score",
            "supporters", "support_count",
            "status", "stake", "actual_profit", "notes"
        ]
        st.dataframe(ai_perf_df[perf_display_columns], use_container_width=True)
