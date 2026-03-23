import hashlib
import random
from itertools import combinations

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Sports Betting AI Dashboard V31.9.1", layout="wide")

# =========================================================
# SESSION STATE
# =========================================================
if "is_mobile" not in st.session_state:
    st.session_state["is_mobile"] = True
if "bet_log" not in st.session_state:
    st.session_state["bet_log"] = []
if "auto_logged_ids" not in st.session_state:
    st.session_state["auto_logged_ids"] = set()
if "nav_choice" not in st.session_state:
    st.session_state["nav_choice"] = "Top Plays"
if "manual_results" not in st.session_state:
    st.session_state["manual_results"] = {}

st.sidebar.toggle("📱 Mobile Mode", key="is_mobile")


def is_mobile() -> bool:
    return st.session_state.get("is_mobile", True)


# =========================================================
# ENGINE SETTINGS
# =========================================================
MIN_ACTIVE_EDGE = 1.25
ACTIVE_EDGE_PROMOTION = 1.50
MAX_TOTAL_UNITS = 3.50
MAX_ACTIVE_PLAYS = 3
DEFAULT_ODDS_RANGE = (-200, 150)

QUALITY_ACTIVE_PRIMARY = 0.58
QUALITY_ACTIVE_SECONDARY = 0.64
QUALITY_FLOOR_FALLBACK = 0.54

MIN_PARLAY_LEGS = 2
MAX_PARLAY_LEGS = 3
MIN_PARLAY_ODDS = 200

SHARP_PARLAY_MIN_TRUE_CONF = 60.0
SHARP_PARLAY_MAX_PENALTY = 0.18
FALLBACK_PARLAY_MAX_PENALTY = 0.36

TEST_MODE = "Paper Test"
SINGLE_UNIT_MIN = 0.40
SINGLE_UNIT_MAX = 1.25
PARLAY_UNIT_SHARP = 0.60
PARLAY_UNIT_FALLBACK_2 = 0.35
PARLAY_UNIT_FALLBACK_3 = 0.20
TEST_DAILY_UNIT_CAP = 3.50

# =========================================================
# HELPERS
# =========================================================
def clamp(value, low, high):
    return max(low, min(high, value))


def american_to_int(odds_str):
    try:
        return int(str(odds_str).replace("+", "").strip())
    except Exception:
        return None


def in_allowed_odds_range(odds_str, min_odds=-200, max_odds=150):
    odds_val = american_to_int(odds_str)
    if odds_val is None:
        return False
    return min_odds <= odds_val <= max_odds


def american_to_decimal(odds_str):
    odds_val = american_to_int(odds_str)
    if odds_val is None:
        return None
    if odds_val > 0:
        return 1 + (odds_val / 100.0)
    return 1 + (100.0 / abs(odds_val))


def decimal_to_american(decimal_odds):
    if decimal_odds is None or decimal_odds <= 1:
        return None
    if decimal_odds >= 2:
        return int(round((decimal_odds - 1) * 100))
    return int(round(-100 / (decimal_odds - 1)))


def format_american(odds_val):
    if odds_val is None:
        return "N/A"
    if odds_val > 0:
        return f"+{int(odds_val)}"
    return str(int(odds_val))


def build_play_id(row_dict):
    raw = "|".join(
        [
            str(row_dict.get("game", "")),
            str(row_dict.get("market", "")),
            str(row_dict.get("selection", "")),
            str(row_dict.get("odds", "")),
        ]
    )
    return hashlib.md5(raw.encode()).hexdigest()


def confidence_fill_and_color(confidence: str):
    c = str(confidence).strip().lower()
    if c == "elite":
        return "92%", "#10b981"
    if c == "high":
        return "78%", "#22c55e"
    return "56%", "#f59e0b"


def tier_colors(tier: str):
    t = str(tier).upper()
    if t == "A":
        return "#d1fae5", "#065f46"
    if t == "B":
        return "#dbeafe", "#1d4ed8"
    return "#fef3c7", "#92400e"


def quality_label_from_tier(tier: str):
    tier = str(tier).upper()
    if tier == "A":
        return "Elite"
    if tier == "B":
        return "Strong"
    return "Watch"


def american_profit(odds, stake):
    odds_int = american_to_int(odds)
    if odds_int is None:
        return 0.0
    stake = float(stake)
    if odds_int > 0:
        return round(stake * (odds_int / 100.0), 2)
    return round(stake * (100.0 / abs(odds_int)), 2)


def settle_result_pnl(odds, units, result):
    result = str(result).strip().lower()
    units = float(units)
    if result == "win":
        return american_profit(odds, units)
    if result == "loss":
        return round(-units, 2)
    return 0.0


def market_family(market):
    m = str(market).lower()
    if "moneyline" in m:
        return "moneyline"
    if "spread" in m:
        return "spread"
    if "total" in m:
        return "total"
    return "other"


def scale_single_units(row):
    true_conf = float(row.get("true_confidence", 0))
    edge = float(row.get("edge", 0))
    price_edge = float(row.get("price_edge", 0))
    books_seen = int(row.get("books_seen", 1))

    strength = (
        (true_conf * 0.50)
        + (edge * 8.0)
        + (price_edge * 5.0)
        + (books_seen * 2.0)
    )
    raw_units = strength / 55.0
    return round(clamp(raw_units, SINGLE_UNIT_MIN, SINGLE_UNIT_MAX), 2)


def scale_parlay_units(parlay):
    if not parlay:
        return 0.0

    approval_type = parlay.get("approval_type", "")
    leg_count = int(parlay.get("leg_count", 2))
    avg_true_conf = float(parlay.get("avg_true_conf", 0))
    risk_label = str(parlay.get("risk_label", "Moderate"))

    if approval_type == "Sharp Approved":
        base_units = PARLAY_UNIT_SHARP
    elif leg_count == 2:
        base_units = PARLAY_UNIT_FALLBACK_2
    else:
        base_units = PARLAY_UNIT_FALLBACK_3

    if avg_true_conf >= 64:
        base_units += 0.10
    elif avg_true_conf < 58:
        base_units -= 0.05

    if risk_label == "Low":
        base_units += 0.05
    elif risk_label == "Elevated":
        base_units -= 0.10

    return round(clamp(base_units, 0.15, 0.75), 2)


# =========================================================
# LIVE SLATE INPUT (V31.9.1)
# =========================================================
def parse_today_games(games_text: str):
    games = []
    for line in str(games_text).splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue

        if " vs " in cleaned:
            parts = cleaned.split(" vs ")
        elif " VS " in cleaned:
            parts = cleaned.split(" VS ")
        else:
            continue

        if len(parts) != 2:
            continue

        away = parts[0].strip()
        home = parts[1].strip()

        if away and home:
            games.append(f"{away} vs {home}")

    return games


st.sidebar.markdown("### 🗓️ Today's Slate")
st.sidebar.text_area(
    "Enter today's real games (one per line)",
    key="today_games_text",
    height=180,
    placeholder="Spurs vs Heat\nLakers vs Warriors\nNuggets vs Suns",
)

today_games = parse_today_games(st.session_state.get("today_games_text", ""))


