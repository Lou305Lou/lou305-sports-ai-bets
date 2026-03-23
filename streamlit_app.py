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

# =========================================================
# SMART DECISION LAYER
# =========================================================
def books_score(books_seen):
    if books_seen >= 4:
        return 1.00
    if books_seen == 3:
        return 0.82
    if books_seen == 2:
        return 0.60
    return 0.35


def consensus_score(consensus):
    consensus = str(consensus).strip().lower()
    if consensus == "strong":
        return 1.00
    if consensus == "fair":
        return 0.68
    return 0.38


def confidence_score(confidence):
    confidence = str(confidence).strip().lower()
    if confidence == "elite":
        return 1.00
    if confidence == "high":
        return 0.76
    return 0.52


def edge_score(edge):
    return clamp(edge / 5.0, 0.0, 1.0)


def price_edge_score(price_edge):
    return clamp(price_edge / 2.6, 0.0, 1.0)


def model_score(score):
    return clamp((score - 80.0) / 20.0, 0.0, 1.0)


def detect_traps(row):
    penalties = 0.0
    trap_flags = []

    edge = float(row["edge"])
    books_seen = int(row["books_seen"])
    consensus = str(row["consensus"])
    confidence = str(row["confidence"])
    price_edge = float(row["price_edge"])

    if consensus == "Thin" and edge >= 3.0:
        penalties += 0.14
        trap_flags.append("thin consensus trap")
    if books_seen <= 1 and edge >= 2.0:
        penalties += 0.14
        trap_flags.append("low book count trap")
    if books_seen <= 2 and consensus == "Thin":
        penalties += 0.11
        trap_flags.append("weak market structure")
    if confidence == "Medium" and edge >= 3.5:
        penalties += 0.06
        trap_flags.append("edge-confidence mismatch")
    if price_edge < 0.80 and edge >= 3.0:
        penalties += 0.05
        trap_flags.append("weak price support")

    return clamp(penalties, 0.0, 0.35), trap_flags


def compute_true_confidence(row):
    ms = model_score(float(row["score"]))
    es = edge_score(float(row["edge"]))
    ps = price_edge_score(float(row["price_edge"]))
    bs = books_score(int(row["books_seen"]))
    cs = consensus_score(row["consensus"])
    cfs = confidence_score(row["confidence"])

    penalty, trap_flags = detect_traps(row)

    raw_quality = (
        ms * 0.25
        + es * 0.22
        + ps * 0.14
        + bs * 0.16
        + cs * 0.13
        + cfs * 0.10
    )
    adjusted_quality = clamp(raw_quality - penalty, 0.0, 1.0)
    true_confidence = round(adjusted_quality * 100.0, 1)

    reasons = []
    if bs >= 0.82:
        reasons.append("multi-book support")
    if cs >= 1.0:
        reasons.append("strong consensus")
    elif cs >= 0.68:
        reasons.append("usable consensus")
    if ps >= 0.58:
        reasons.append("price support")
    if ms >= 0.65:
        reasons.append("strong model score")
    if cfs >= 0.76:
        reasons.append("high confidence")
    reasons.extend(trap_flags)

    return true_confidence, adjusted_quality, reasons


# =========================================================
# DATA GENERATION (LIVE SLATE FIX)
# =========================================================
def generate_ai_plays():
    empty_cols = [
        "game",
        "market",
        "selection",
        "odds",
        "edge",
        "score",
        "units",
        "tier",
        "quality_label",
        "status",
        "confidence",
        "books_seen",
        "best_price",
        "consensus",
        "price_edge",
        "ai_tags",
        "true_confidence",
        "quality_score",
        "decision_reasons",
        "rank_score",
        "play_id",
    ]

    if not today_games:
        return pd.DataFrame(columns=empty_cols)

    market_templates = [
        ("moneyline", lambda g: g.split(" vs ")[1]),
        ("moneyline", lambda g: g.split(" vs ")[0]),
        ("total", lambda g: "Over 221.5"),
        ("total", lambda g: "Under 221.5"),
        ("spread", lambda g: f"{g.split(' vs ')[1]} -4.5"),
        ("spread", lambda g: f"{g.split(' vs ')[0]} +4.5"),
    ]

    odds_pool = ["-132", "-118", "-110", "-105", "-102", "+100", "+110", "+120", "+135"]
    consensus_pool = ["Strong", "Fair", "Thin"]
    confidence_pool = ["Medium", "High", "Elite"]

    rows = []
    random.seed(31)

    for game in today_games:
        for market, selection_fn in market_templates:
            edge = round(random.uniform(0.80, 5.20), 2)
            score = round(random.uniform(80.0, 99.5), 1)
            confidence = random.choices(confidence_pool, weights=[3, 5, 2], k=1)[0]
            books_seen = random.randint(1, 4)
            odds = random.choice(odds_pool)
            consensus = random.choices(consensus_pool, weights=[3, 5, 2], k=1)[0]
            price_edge = round(random.uniform(0.40, 2.60), 2)

            if edge < MIN_ACTIVE_EDGE:
                continue
            if not in_allowed_odds_range(odds, *DEFAULT_ODDS_RANGE):
                continue

            row = {
                "game": game,
                "market": market,
                "selection": selection_fn(game),
                "odds": odds,
                "edge": edge,
                "score": score,
                "units": 0.0,
                "tier": "C",
                "quality_label": "Watch",
                "status": "Watch",
                "confidence": confidence,
                "books_seen": books_seen,
                "best_price": "Yes" if price_edge >= 1.25 else "No",
                "consensus": consensus,
                "price_edge": price_edge,
                "ai_tags": ["AI generated", "live slate"],
            }

            tc, qs, reasons = compute_true_confidence(row)
            row["true_confidence"] = tc
            row["quality_score"] = qs
            row["decision_reasons"] = reasons
            row["units"] = scale_single_units(row)

            tags = ["AI generated", "live slate"]
            for reason in reasons:
                if reason not in tags:
                    tags.append(reason)
            row["ai_tags"] = tags[:6]

            rows.append(row)

    df = pd.DataFrame(rows)

    if df.empty:
        return pd.DataFrame(columns=empty_cols)

    df["rank_score"] = (
        df["quality_score"] * 100.0 * 0.55
        + df["score"] * 0.15
        + df["edge"] * 6.0
        + df["price_edge"] * 4.0
        + df["books_seen"] * 1.5
    )

    def decide_status(row):
        q = float(row["quality_score"])
        e = float(row["edge"])
        b = int(row["books_seen"])
        c = str(row["consensus"])

        if q >= QUALITY_ACTIVE_PRIMARY and e >= ACTIVE_EDGE_PROMOTION:
            return "Active"
        if q >= QUALITY_ACTIVE_SECONDARY and e >= MIN_ACTIVE_EDGE:
            return "Active"
        if q >= 0.61 and e >= 1.40 and b >= 3 and c in ["Strong", "Fair"]:
            return "Active"
        return "Watch"

    df["status"] = df.apply(decide_status, axis=1)

    def tier_from_true_conf(tc):
        if tc >= 78:
            return "A"
        if tc >= 60:
            return "B"
        return "C"

    df["tier"] = df["true_confidence"].apply(tier_from_true_conf)
    df["quality_label"] = df["tier"].apply(quality_label_from_tier)

    df["play_id"] = df.apply(
        lambda r: build_play_id(
            {
                "game": r["game"],
                "market": r["market"],
                "selection": r["selection"],
                "odds": r["odds"],
            }
        ),
        axis=1,
    )

    active_df_local = df[df["status"] == "Active"].copy().sort_values("rank_score", ascending=False)
    watch_df_local = df[df["status"] == "Watch"].copy().sort_values("rank_score", ascending=False)

    active_rows = []
    running_units = 0.0

    for _, row in active_df_local.iterrows():
        proposed_units = float(row["units"])
        if len(active_rows) >= MAX_ACTIVE_PLAYS or running_units + proposed_units > MAX_TOTAL_UNITS:
            row2 = row.copy()
            row2["status"] = "Watch"
            watch_df_local = pd.concat([watch_df_local, pd.DataFrame([row2])], ignore_index=True)
            continue
        active_rows.append(row)
        running_units += proposed_units

    active_final = pd.DataFrame(active_rows) if active_rows else pd.DataFrame(columns=df.columns)
    combined = pd.concat([active_final, watch_df_local], ignore_index=True)

    if combined.empty:
        return pd.DataFrame(columns=empty_cols)

    return combined.sort_values(["status", "rank_score"], ascending=[True, False]).reset_index(drop=True)
