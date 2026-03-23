import hashlib
import random
from itertools import combinations

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Sports Betting AI Dashboard V31.9", layout="wide")

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
    placeholder="Spurs vs Heat\nLakers vs Warriors\nNuggets vs Suns"
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
        ms * 0.25 + es * 0.22 + ps * 0.14 + bs * 0.16 + cs * 0.13 + cfs * 0.10
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
# DATA BUILD
# =========================================================
df = generate_ai_plays()

if df is None or df.empty:
    df = pd.DataFrame(columns=[
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
        "price_edge",
        "true_confidence",
        "quality_score",
        "rank_score",
        "play_id",
        "ai_tags",
    ])

auto_logged_count = auto_log_active_plays(df)

active_df = df[df["status"] == "Active"].copy().reset_index(drop=True)
watch_df = df[df["status"] == "Watch"].copy().reset_index(drop=True)

best_row = None
if not active_df.empty:
    best_row = active_df.sort_values(
        ["rank_score", "true_confidence"],
        ascending=False
    ).iloc[0]

best_parlay, sharp_candidates, fallback_candidates = choose_best_parlay(active_df)
all_portfolio_candidates = [*sharp_candidates, *fallback_candidates]
portfolio = build_ai_portfolio(best_row, best_parlay, all_portfolio_candidates)

avg_active_edge = active_df["edge"].mean() if not active_df.empty else 0.0
best_score = best_row["score"] if best_row is not None else "—"
avg_true_conf = active_df["true_confidence"].mean() if not active_df.empty else 0.0
total_units = active_df["units"].sum() if not active_df.empty else 0.0

# =========================================================
# PARLAY INTELLIGENCE
# =========================================================
def calculate_correlation_score(legs):
    score = 0.0
    for i in range(len(legs)):
        for j in range(i + 1, len(legs)):
            a = legs[i]
            b = legs[j]
            same_game = a.get("game") == b.get("game")
            market_a = market_family(a.get("market"))
            market_b = market_family(b.get("market"))
            sel_a = str(a.get("selection", "")).lower()
            sel_b = str(b.get("selection", "")).lower()

            if same_game:
                if {market_a, market_b} == {"spread", "total"}:
                    if ("under" in sel_a) or ("under" in sel_b):
                        score += 1.5
                    elif ("over" in sel_a) or ("over" in sel_b):
                        score -= 2.0
                elif {market_a, market_b} == {"moneyline", "total"}:
                    score += 0.25
                elif market_a == market_b:
                    score -= 1.0
            else:
                score += 0.5
    return score


def selections_conflict(row_a, row_b):
    if row_a["game"] != row_b["game"]:
        return False

    fam_a = market_family(row_a["market"])
    fam_b = market_family(row_b["market"])
    sel_a = str(row_a["selection"]).lower()
    sel_b = str(row_b["selection"]).lower()

    if fam_a == fam_b and row_a["selection"] != row_b["selection"]:
        return True
    if "over" in sel_a and "under" in sel_b:
        return True
    if "under" in sel_a and "over" in sel_b:
        return True

    teams = [t.strip().lower() for t in str(row_a["game"]).split("vs")]
    if len(teams) == 2:
        t1, t2 = teams[0], teams[1]
        if (t1 in sel_a and t2 in sel_b) or (t2 in sel_a and t1 in sel_b):
            return True
    return False


def pair_correlation_penalty(row_a, row_b):
    penalty = 0.0
    reasons = []
    if selections_conflict(row_a, row_b):
        return 1.0, ["conflicting legs"]

    if row_a["game"] == row_b["game"]:
        penalty += 0.18
        reasons.append("same-game correlation")
        fam_a = market_family(row_a["market"])
        fam_b = market_family(row_b["market"])
        if fam_a == fam_b:
            penalty += 0.12
            reasons.append("same-market overlap")
        if {fam_a, fam_b} == {"moneyline", "spread"}:
            penalty += 0.08
            reasons.append("side correlation")

    return clamp(penalty, 0.0, 1.0), reasons


def score_parlay_combo(combo):
    total_penalty = 0.0
    penalty_reasons = []
    valid = True

    for a, b in combinations(combo, 2):
        penalty, reasons = pair_correlation_penalty(a, b)
        if penalty >= 1.0:
            valid = False
            break
        total_penalty += penalty
        penalty_reasons.extend(reasons)

    if not valid:
        return None

    decimal_odds = 1.0
    for leg in combo:
        dec = american_to_decimal(leg["odds"])
        if dec is None:
            return None
        decimal_odds *= dec

    combined_american = decimal_to_american(decimal_odds)
    if combined_american is None or combined_american < MIN_PARLAY_ODDS:
        return None

    avg_true_conf = sum(float(leg["true_confidence"]) for leg in combo) / len(combo)
    avg_edge = sum(float(leg["edge"]) for leg in combo) / len(combo)
    avg_books = sum(float(leg["books_seen"]) for leg in combo) / len(combo)
    avg_price_edge = sum(float(leg["price_edge"]) for leg in combo) / len(combo)

    distinct_games = len(set(leg["game"] for leg in combo))
    cross_game = distinct_games == len(combo)
    game_diversity_bonus = 0.12 if cross_game else 0.02

    raw_score = (
        avg_true_conf * 0.55
        + avg_edge * 6.0
        + avg_price_edge * 4.0
        + avg_books * 1.2
        + (game_diversity_bonus * 100)
    )
    correlation_score = calculate_correlation_score(list(combo))
    conservative_score = raw_score - (total_penalty * 30) + (correlation_score * 5)
    fallback_score = (raw_score * (1 - total_penalty)) + (correlation_score * 5)

    if total_penalty <= 0.08 and avg_true_conf >= 64:
        risk_label = "Low"
    elif total_penalty <= 0.22 and avg_true_conf >= 58:
        risk_label = "Moderate"
    else:
        risk_label = "Elevated"

    reasons = []
    if cross_game:
        reasons.append("cross-game diversification")
    else:
        reasons.append("same-game correlation adjusted")
    if correlation_score > 1:
        reasons.append("positive correlation")
    elif correlation_score < -1:
        reasons.append("conflict risk")
    if avg_true_conf >= 62:
        reasons.append("high true confidence")
    elif avg_true_conf >= 57:
        reasons.append("solid true confidence")
    if avg_books >= 3:
        reasons.append("broad book support")
    if avg_price_edge >= 1.2:
        reasons.append("price support")

    return {
        "legs": list(combo),
        "leg_count": len(combo),
        "combined_odds": format_american(combined_american),
        "combined_odds_int": combined_american,
        "avg_true_conf": round(avg_true_conf, 1),
        "avg_edge": round(avg_edge, 2),
        "avg_books": round(avg_books, 2),
        "avg_price_edge": round(avg_price_edge, 2),
        "total_penalty": round(total_penalty, 3),
        "cross_game": cross_game,
        "correlation_score": round(correlation_score, 2),
        "conservative_score": round(conservative_score, 1),
        "fallback_score": round(fallback_score, 1),
        "score": round(fallback_score, 1),
        "display_score": round(fallback_score, 1),
        "risk_label": risk_label,
        "reasons": (reasons + penalty_reasons)[:6],
    }


def build_all_parlay_candidates(active_df):
    if active_df.empty or len(active_df) < 2:
        return []
    rows = active_df.to_dict("records")
    candidates = []
    for leg_count in range(MIN_PARLAY_LEGS, min(MAX_PARLAY_LEGS, len(rows)) + 1):
        for combo in combinations(rows, leg_count):
            scored = score_parlay_combo(combo)
            if scored is not None:
                candidates.append(scored)
    return candidates


def classify_parlay_candidates(candidates):
    sharp_candidates = []
    fallback_candidates = []
    for c in candidates:
        sharp_ok = (
            c["avg_true_conf"] >= SHARP_PARLAY_MIN_TRUE_CONF
            and c["total_penalty"] <= SHARP_PARLAY_MAX_PENALTY
            and c["cross_game"]
            and c["correlation_score"] >= 0
        )
        fallback_ok = (
            c["total_penalty"] <= (FALLBACK_PARLAY_MAX_PENALTY + 0.08)
            and c["combined_odds_int"] >= (MIN_PARLAY_ODDS + 40)
            and c["avg_true_conf"] >= 55
        )

        if sharp_ok:
            sharp_copy = c.copy()
            sharp_copy["approval_type"] = "Sharp Approved"
            sharp_copy["display_score"] = sharp_copy["conservative_score"]
            sharp_copy["score"] = sharp_copy["conservative_score"]
            sharp_candidates.append(sharp_copy)

        if fallback_ok:
            fallback_copy = c.copy()
            fallback_copy["approval_type"] = "Balanced Fallback"
            fallback_copy["display_score"] = fallback_copy["fallback_score"]
            fallback_copy["score"] = fallback_copy["fallback_score"]
            fallback_candidates.append(fallback_copy)

    sharp_candidates.sort(
        key=lambda x: (x["conservative_score"], x["avg_true_conf"], x["combined_odds_int"]),
        reverse=True,
    )
    fallback_candidates.sort(
        key=lambda x: (x["fallback_score"], x["avg_true_conf"], x["combined_odds_int"]),
        reverse=True,
    )
    return sharp_candidates, fallback_candidates


def choose_best_parlay(active_df):
    all_candidates = build_all_parlay_candidates(active_df)
    sharp_candidates, fallback_candidates = classify_parlay_candidates(all_candidates)

    sharp_best = sharp_candidates[0] if sharp_candidates else None
    fallback_best = fallback_candidates[0] if fallback_candidates else None

    if sharp_best is not None:
        chosen = sharp_best.copy()
        chosen["approval_type"] = "Sharp Approved"
        chosen["display_score"] = chosen["conservative_score"]
        chosen["score"] = chosen["conservative_score"]
        return chosen, sharp_candidates, fallback_candidates

    if fallback_best is not None:
        chosen = fallback_best.copy()
        chosen["approval_type"] = "Balanced Fallback"
        chosen["display_score"] = chosen["fallback_score"]
        chosen["score"] = chosen["fallback_score"]
        return chosen, sharp_candidates, fallback_candidates

    return None, sharp_candidates, fallback_candidates


# =========================================================
# AUTO-LOG ACTIVE PLAYS
# =========================================================
def auto_log_active_plays(df):
    if df.empty:
        return 0

    count_added = 0
    active_df = df[df["status"] == "Active"].copy()
    for _, row in active_df.iterrows():
        play_id = row["play_id"]
        if play_id in st.session_state["auto_logged_ids"]:
            continue

        log_row = {
            "play_id": play_id,
            "game": row["game"],
            "market": row["market"],
            "selection": row["selection"],
            "odds": row["odds"],
            "edge": row["edge"],
            "score": row["score"],
            "units": row["units"],
            "confidence": row["confidence"],
            "true_confidence": row["true_confidence"],
            "tier": row["tier"],
            "quality_label": row["quality_label"],
            "status": row["status"],
            "result": "Pending",
            "profit": 0.0,
            "mode": TEST_MODE,
        }
        st.session_state["bet_log"].append(log_row)
        st.session_state["auto_logged_ids"].add(play_id)
        count_added += 1
    return count_added


# =========================================================
# PLAY CARD RENDER
# =========================================================
def render_play_card(row: pd.Series, show_best_badge: bool = False):
    badge_bg, badge_fg = tier_colors(row["tier"])
    status_bg = "#f59e0b" if str(row["status"]) == "Active" else "#64748b"
    status_fg = "#111827" if str(row["status"]) == "Active" else "#f8fafc"
    best_display = "inline-flex" if show_best_badge else "none"
    fill_width, fill_color = confidence_fill_and_color(row["confidence"])
    edge_color = "#4ade80" if float(row["edge"]) >= 2 else "#fbbf24"

    visible_tags = list(row["ai_tags"])[:3]
    tags_html = ""
    for tag in visible_tags:
        tags_html += f'''
        <span style="background:#1e2638;color:#d8e0ec;border:1px solid #2a3448;border-radius:999px;
        padding:3px 7px;font-size:10px;line-height:1;display:inline-block;margin-right:5px;margin-bottom:4px;white-space:nowrap;">{tag}</span>
        '''

    true_conf = row.get("true_confidence", None)
    quality_label = row.get("quality_label", "")
    tc_html = (
        f'<div><div style="color:#91a0b7;font-size:10px;margin-bottom:1px;">True Conf</div><div style="color:#f8fafc;font-size:14px;font-weight:700;">{true_conf:.1f}</div></div>'
        if true_conf is not None else ""
    )
    ql_html = (
        f'<div><div style="color:#91a0b7;font-size:10px;margin-bottom:1px;">Quality</div><div style="color:#f8fafc;font-size:14px;font-weight:700;">{quality_label}</div></div>'
        if quality_label else ""
    )

    html = f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1" /></head>
    <body style="margin:0;background:transparent;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
    <div style="background:linear-gradient(180deg, #151b29 0%, #0e1422 100%);border:1px solid #243047;border-radius:22px;padding:12px;color:#ffffff;box-sizing:border-box;">
        <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:7px;">
            <span style="background:{badge_bg};color:{badge_fg};padding:5px 9px;border-radius:999px;font-size:10px;font-weight:800;">Tier {row['tier']}</span>
            <span style="background:{status_bg};color:{status_fg};padding:5px 9px;border-radius:999px;font-size:10px;font-weight:800;">{row['status']}</span>
            <span style="background:#efe2ff;color:#6b21a8;padding:4px 8px;border-radius:999px;font-size:9px;font-weight:800;display:{best_display};align-items:center;">🏆 Best Bet</span>
        </div>
        <div style="font-size:21px;line-height:1.0;font-weight:800;margin:0 0 5px 0;letter-spacing:-0.03em;color:#ffffff;">{row['selection']}</div>
        <div style="color:#d4dbe8;font-size:12px;margin-bottom:8px;">{row['game']} • {str(row['market']).title()}</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px 12px;margin-bottom:6px;">
            <div><div style="color:#91a0b7;font-size:10px;">Odds</div><div style="color:#f8fafc;font-size:14px;font-weight:700;">{row['odds']}</div></div>
            <div><div style="color:#91a0b7;font-size:10px;">AI Score</div><div style="color:#60a5fa;font-size:14px;font-weight:700;">{row['score']}</div></div>
            <div><div style="color:#91a0b7;font-size:10px;">Edge</div><div style="color:{edge_color};font-size:14px;font-weight:700;">{row['edge']:.2f}%</div></div>
            <div><div style="color:#91a0b7;font-size:10px;">Units</div><div style="color:#f8fafc;font-size:14px;font-weight:700;">{row['units']:.2f}u</div></div>
            <div><div style="color:#91a0b7;font-size:10px;">Consensus</div><div style="color:#f8fafc;font-size:14px;font-weight:700;">{row['consensus']}</div></div>
            <div><div style="color:#91a0b7;font-size:10px;">Books</div><div style="color:#f8fafc;font-size:14px;font-weight:700;">{row['books_seen']}</div></div>
            <div><div style="color:#91a0b7;font-size:10px;">Best Price</div><div style="color:#f8fafc;font-size:14px;font-weight:700;">{row['best_price']}</div></div>
            <div><div style="color:#91a0b7;font-size:10px;">Price Edge</div><div style="color:#f8fafc;font-size:14px;font-weight:700;">{row['price_edge']:.2f}%</div></div>
            {tc_html}
            {ql_html}
        </div>
        <div style="height:1px;background:#283550;margin:6px 0 7px 0;"></div>
        <div><div style="color:#91a0b7;font-size:10px;margin-bottom:4px;">Confidence • {row['confidence']}</div>
        <div style="width:100%;height:5px;background:#24324b;border-radius:999px;overflow:hidden;"><div style="width:{fill_width};height:5px;background:{fill_color};border-radius:999px;"></div></div></div>
        <div style="height:7px;"></div>
        <div style="overflow:hidden;max-height:22px;">{tags_html}</div>
    </div></body></html>
    """
    components.html(html, height=285 if is_mobile() else 340, scrolling=False)


# =========================================================
# PARLAY CARD RENDER
# =========================================================
def render_parlay_card(parlay):
    if not parlay:
        st.info("No qualifying parlay available.")
        return

    risk_color = {"Low": "#10b981", "Moderate": "#f59e0b", "Elevated": "#ef4444"}.get(parlay["risk_label"], "#94a3b8")
    approval_bg = "#dcfce7" if parlay["approval_type"] == "Sharp Approved" else "#fef3c7"
    approval_fg = "#166534" if parlay["approval_type"] == "Sharp Approved" else "#92400e"

    legs_html = ""
    for i, leg in enumerate(parlay["legs"], start=1):
        legs_html += f'''
        <div style="padding:8px 0; border-bottom:1px solid #243047;">
            <div style="color:#ffffff; font-size:15px; font-weight:800;">{i}. {leg['selection']}</div>
            <div style="color:#cbd5e1; font-size:12px;">{leg['game']} • {str(leg['market']).title()} • {leg['odds']}</div>
            <div style="color:#93c5fd; font-size:12px; margin-top:2px;">True Conf {leg['true_confidence']:.1f} • {leg['quality_label']}</div>
        </div>
        '''

    reasons_html = ""
    for reason in parlay["reasons"][:4]:
        reasons_html += f'<span style="background:#1e2638;color:#d8e0ec;border:1px solid #2a3448;border-radius:999px;padding:4px 8px;font-size:10px;line-height:1;display:inline-block;margin-right:5px;margin-bottom:5px;white-space:nowrap;">{reason}</span>'

    parlay_score_value = parlay.get("display_score", parlay.get("score", "—"))

    html = f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1" /></head>
    <body style="margin:0;background:transparent;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
        <div style="background:linear-gradient(180deg, #151b29 0%, #0e1422 100%);border:1px solid #243047;border-radius:22px;padding:14px;color:#ffffff;box-sizing:border-box;">
            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:6px;">
                <div style="color:#fbbf24;font-size:12px;font-weight:800;">🔥 AI PARLAY ENGINE</div>
                <span style="background:{approval_bg};color:{approval_fg};border-radius:999px;padding:4px 8px;font-size:10px;font-weight:800;">{parlay['approval_type']}</span>
            </div>
            <div style="font-size:22px;font-weight:800;margin-bottom:5px;">Recommended {parlay['leg_count']}-Leg Slip</div>
            <div style="color:#d4dbe8;font-size:13px;margin-bottom:10px;">Combined Odds: <span style="color:#ffffff;font-weight:800;">{parlay['combined_odds']}</span> • Avg True Conf: <span style="color:#ffffff;font-weight:800;">{parlay['avg_true_conf']:.1f}</span></div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px 12px;margin-bottom:10px;">
                <div><div style="color:#91a0b7;font-size:10px;">Parlay Score</div><div style="font-size:15px;font-weight:800;">{parlay_score_value}</div></div>
                <div><div style="color:#91a0b7;font-size:10px;">Risk</div><div style="font-size:15px;font-weight:800;color:{risk_color};">{parlay['risk_label']}</div></div>
            </div>
            <div style="margin-bottom:10px;">{legs_html}</div>
            <div style="height:6px;"></div>
            <div>{reasons_html}</div>
        </div>
    </body></html>
    """
    components.html(html, height=395 if is_mobile() else 420, scrolling=False)


def render_parlay_table(candidates, score_key, title):
    st.markdown(f"**{title}**")
    if not candidates:
        st.info("No candidates.")
        return

    rows = []
    for p in candidates[:5]:
        score_value = p.get(score_key) or p.get("display_score") or p.get("score")
        rows.append(
            {
                "legs": p.get("leg_count"),
                "combined_odds": p.get("combined_odds"),
                "avg_true_conf": round(p.get("avg_true_conf", 0), 1),
                "score": round(score_value, 1) if isinstance(score_value, (int, float)) else "—",
                "risk": p.get("risk_label"),
            }
        )

    out_df = pd.DataFrame(rows)
    st.dataframe(out_df, use_container_width=True, hide_index=True)


def render_table_desktop(dataframe: pd.DataFrame):
    cols = [
        "tier", "quality_label", "status", "game", "market", "selection", "odds", "edge",
        "score", "units", "confidence", "true_confidence", "books_seen",
        "best_price", "consensus", "price_edge"
    ]
    out = dataframe[cols].copy()
    st.dataframe(out, use_container_width=True, hide_index=True)


def render_mobile_or_table(dataframe: pd.DataFrame, best_first: bool = False):
    if dataframe.empty:
        st.info("No plays available.")
        return
    if is_mobile():
        for idx, (_, row) in enumerate(dataframe.iterrows()):
            render_play_card(row, show_best_badge=(best_first and idx == 0))
    else:
        render_table_desktop(dataframe)


# =========================================================
# V31.9 SMART UNIT SCALING + TEST TRACKING LAYER
# =========================================================
def build_ai_portfolio(best_single, chosen_parlay, parlay_candidates):
    portfolio = []
    used_keys = set()
    running_units = 0.0

    if best_single is not None:
        single_units = scale_single_units(best_single)
        single_key = f"single::{best_single.get('play_id', best_single.get('selection', ''))}"
        if running_units + single_units <= TEST_DAILY_UNIT_CAP:
            portfolio.append(
                {
                    "type": "Single",
                    "label": "Core Play",
                    "units": single_units,
                    "data": best_single,
                }
            )
            used_keys.add(single_key)
            running_units += single_units

    if chosen_parlay is not None:
        parlay_units = scale_parlay_units(chosen_parlay)
        parlay_key = "parlay::" + "|".join([leg.get("selection", "") for leg in chosen_parlay.get("legs", [])])
        if parlay_key not in used_keys and running_units + parlay_units <= TEST_DAILY_UNIT_CAP:
            portfolio.append(
                {
                    "type": "Parlay",
                    "label": chosen_parlay.get("approval_type", "Sharp"),
                    "units": parlay_units,
                    "data": chosen_parlay,
                }
            )
            used_keys.add(parlay_key)
            running_units += parlay_units

    fallback_2 = [
        c for c in parlay_candidates
        if c.get("leg_count") == 2 and c.get("approval_type") == "Balanced Fallback"
    ]
    if fallback_2:
        p = fallback_2[0]
        p_units = scale_parlay_units(p)
        p_key = "parlay::" + "|".join([leg.get("selection", "") for leg in p.get("legs", [])])
        if p_key not in used_keys and running_units + p_units <= TEST_DAILY_UNIT_CAP:
            portfolio.append(
                {
                    "type": "Parlay",
                    "label": "Fallback 2-Leg",
                    "units": p_units,
                    "data": p,
                }
            )
            used_keys.add(p_key)
            running_units += p_units

    fallback_3 = [
        c for c in parlay_candidates
        if c.get("leg_count") == 3 and c.get("approval_type") == "Balanced Fallback"
    ]
    if fallback_3:
        p = fallback_3[0]
        p_units = scale_parlay_units(p)
        p_key = "parlay::" + "|".join([leg.get("selection", "") for leg in p.get("legs", [])])
        if p_key not in used_keys and running_units + p_units <= TEST_DAILY_UNIT_CAP:
            portfolio.append(
                {
                    "type": "Parlay",
                    "label": "Fallback 3-Leg",
                    "units": p_units,
                    "data": p,
                }
            )
            used_keys.add(p_key)
            running_units += p_units

    return portfolio

# =========================================================
# DATA GENERATION (LIVE SLATE FIX)
# =========================================================
def generate_ai_plays():
    if not today_games:
        return pd.DataFrame(columns=[
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
        ])

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
        return pd.DataFrame(columns=[
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
        ])

    df["rank_score"] = (
        df["quality_score"] * 100 * 0.55
        + df["score"] * 0.15
        + df["edge"] * 6
        + df["price_edge"] * 4
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

    df["tier"] = df.apply(
        lambda r: "A" if r["true_confidence"] >= 78 else ("B" if r["true_confidence"] >= 60 else "C"),
        axis=1,
    )
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

    return df.sort_values(["status", "rank_score"], ascending=[True, False]).reset_index(drop=True)
# =========================================================
# DATA BUILD
# =========================================================
df = generate_ai_plays()
auto_logged_count = auto_log_active_plays(df)

active_df = df[df["status"] == "Active"].copy().reset_index(drop=True)
watch_df = df[df["status"] == "Watch"].copy().reset_index(drop=True)

best_row = None
if not active_df.empty:
    best_row = active_df.sort_values(["rank_score", "true_confidence"], ascending=False).iloc[0]

best_parlay, sharp_candidates, fallback_candidates = choose_best_parlay(active_df)
all_portfolio_candidates = [*sharp_candidates, *fallback_candidates]
portfolio = build_ai_portfolio(best_row, best_parlay, all_portfolio_candidates)

avg_active_edge = active_df["edge"].mean() if not active_df.empty else 0.0
best_score = best_row["score"] if best_row is not None else "—"
avg_true_conf = active_df["true_confidence"].mean() if not active_df.empty else 0.0
total_units = active_df["units"].sum() if not active_df.empty else 0.0


# =========================================================
# PAGE STYLES
# =========================================================
st.markdown(
    """
<style>
html, body, [class*="css"] {font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;}
.stApp {background-color: #f6f7fb;}
.block-container {max-width: 880px; padding-top: 0.85rem; padding-bottom: 1.8rem;}
h1, h2, h3 {letter-spacing: -0.02em; color: #202533;}
.metric-panel {background: #ffffff; border: 1px solid #e7ebf2; border-radius: 18px; padding: 10px 12px; margin-bottom: 10px;}
.metric-panel-title {color: #1f2937; font-weight: 800; font-size: 0.94rem; margin-bottom: 6px;}
.metric-mini-grid {display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px 12px;}
.metric-mini-label {font-size: 0.75rem; color: #6b7280;}
.metric-mini-value {font-size: 0.98rem; font-weight: 800; color: #111827;}
.nav-wrap {background: #ffffff; border: 1px solid #e6eaf2; border-radius: 18px; padding: 10px 12px 7px 12px; margin-bottom: 12px;}
.section-title {font-size: 0.98rem; font-weight: 800; margin-bottom: 0.25rem; color: #1e2430;}
.slip-card {background: linear-gradient(180deg, #151b29 0%, #0e1422 100%); border: 1px solid #243047; border-radius: 22px; padding: 13px; margin-bottom: 10px; box-shadow: 0 10px 24px rgba(0, 0, 0, 0.14);}
.slip-kicker {color: #fbbf24; font-size: 0.82rem; font-weight: 800; margin-bottom: 5px;}
.slip-title {color: #ffffff; font-size: 1.35rem; font-weight: 800; margin-bottom: 5px; letter-spacing: -0.03em;}
.slip-meta {color: #d6deea; font-size: 0.86rem; margin-bottom: 3px;}
.bet-form-wrap {background: #ffffff; border: 1px solid #e7ebf2; border-radius: 20px; padding: 14px; margin-bottom: 14px;}
.notice-box {background: #ecfdf5; border: 1px solid #a7f3d0; color: #065f46; border-radius: 16px; padding: 10px 12px; margin-bottom: 10px; font-weight: 700;}
.small-muted {color: #6b7280; font-size: 0.84rem;}
</style>
""",
    unsafe_allow_html=True,
)


# =========================================================
# HEADER
# =========================================================
st.title("🔥 Sports Betting AI Dashboard V31.9")
st.caption("Smart Unit Scaling + Test Tracking Layer • AI Parlay Intelligence • Auto Bet Log")
if auto_logged_count > 0:
    st.markdown(
        f'<div class="notice-box">Auto-logged {auto_logged_count} new active play(s).</div>',
        unsafe_allow_html=True,
    )


# =========================================================
# SNAPSHOT
# =========================================================
st.markdown('<div class="metric-panel">', unsafe_allow_html=True)
st.markdown('<div class="metric-panel-title">Market Snapshot</div>', unsafe_allow_html=True)
st.markdown(
    f"""
    <div class="metric-mini-grid">
        <div><div class="metric-mini-label">Active Plays</div><div class="metric-mini-value">{len(active_df)}</div></div>
        <div><div class="metric-mini-label">Watchlist</div><div class="metric-mini-value">{len(watch_df)}</div></div>
        <div><div class="metric-mini-label">Best Score</div><div class="metric-mini-value">{best_score}</div></div>
        <div><div class="metric-mini-label">Avg Active Edge</div><div class="metric-mini-value">{avg_active_edge:.2f}%</div></div>
        <div><div class="metric-mini-label">Avg True Conf</div><div class="metric-mini-value">{avg_true_conf:.1f}</div></div>
        <div><div class="metric-mini-label">Total Active Units</div><div class="metric-mini-value">{total_units:.2f}u</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# NAVIGATION
# =========================================================
st.markdown('<div class="nav-wrap">', unsafe_allow_html=True)
st.markdown('<div class="section-title">🚀 Navigation</div>', unsafe_allow_html=True)
nav = st.radio(
    "Navigation",
    ["Top Plays", "Watchlist", "AI Slip", "Bet Log"],
    horizontal=True,
    label_visibility="collapsed",
    key="nav_choice_native",
)
st.session_state["nav_choice"] = nav
st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# TOP PLAYS
# =========================================================
if nav == "Top Plays":
    st.header("🎯 Top Plays")
    st.caption("Live slate driven plays.")

    if not today_games:
        st.warning("Enter today's real games in the sidebar to generate plays.")
    else:
        top_df = active_df.sort_values(["rank_score", "true_confidence"], ascending=False).reset_index(drop=True)
        render_mobile_or_table(top_df, best_first=True)

# =========================================================
# WATCHLIST
# =========================================================
elif nav == "Watchlist":
    st.header("👀 Watchlist")
    st.caption("Downgraded, near-qualified, or structurally weaker plays to monitor.")
    wl_df = watch_df.sort_values(["rank_score", "true_confidence"], ascending=False).reset_index(drop=True)
    render_mobile_or_table(wl_df, best_first=False)


# =========================================================
# AI SLIP + PARLAY INTELLIGENCE
# =========================================================
elif nav == "AI Slip":
    st.header("🧠 AI Slip")

    if today_games:
        st.caption("Live Slate: " + " | ".join(today_games))
    else:
        st.warning("No live slate entered.")

    if best_row is not None:
        slip_type = "Single best bet"
        risk_level = "Low" if float(best_row["units"]) <= 0.50 else "Moderate"
        st.markdown(
            f"""
            <div class="slip-card">
                <div class="slip-kicker">🔥 AI Recommended Single</div>
                <div class="slip-title">{best_row['selection']}</div>
                <div class="slip-meta">{best_row['game']} • {str(best_row['market']).title()}</div>
                <div class="slip-meta"><strong>Confidence:</strong> {best_row['confidence']}</div>
                <div class="slip-meta"><strong>True Confidence:</strong> {best_row['true_confidence']:.1f}</div>
                <div class="slip-meta"><strong>Quality Label:</strong> {best_row['quality_label']}</div>
                <div class="slip-meta"><strong>Projected Odds:</strong> {best_row['odds']}</div>
                <div class="slip-meta"><strong>Type:</strong> {slip_type}</div>
                <div class="slip-meta"><strong>Risk Level:</strong> {risk_level}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_play_card(best_row, show_best_badge=True)
    else:
        st.info("No active AI single available.")

    st.subheader("🎯 AI Parlay Intelligence")
    if best_parlay is None:
        st.info("Not enough qualifying active legs for a recommended parlay.")
    else:
        render_parlay_card(best_parlay)

    with st.expander("Show top parlay candidates", expanded=False):
        render_parlay_table(
            sharp_candidates,
            "display_score",
            "Sharp Approved Candidates"
        )
        render_parlay_table(
            fallback_candidates,
            "display_score",
            "Balanced Fallback Candidates"
        )

    st.subheader("🧠 AI Portfolio Allocation")
    if not portfolio:
        st.info("No AI portfolio available.")
    else:
        portfolio_rows = []
        for item in portfolio:
            data = item["data"]
            if item["type"] == "Single":
                summary = f"{data['selection']} ({data['game']})"
                odds = data["odds"]
                conf = data["true_confidence"]
            else:
                summary = " | ".join([leg["selection"] for leg in data["legs"]])
                odds = data["combined_odds"]
                conf = data["avg_true_conf"]

            portfolio_rows.append(
                {
                    "Label": item["label"],
                    "Type": item["type"],
                    "Units": item["units"],
                    "Odds": odds,
                    "Confidence": conf,
                    "Summary": summary,
                }
            )

        st.dataframe(pd.DataFrame(portfolio_rows), use_container_width=True, hide_index=True)


# =========================================================
# BET LOG
# =========================================================
elif nav == "Bet Log":
    st.header("🧾 Bet Log")
    st.caption("Auto-logged active plays plus manual paper-test tracking.")

    if len(st.session_state["bet_log"]) == 0:
        st.info("No bets logged yet.")
    else:
        log_df = pd.DataFrame(st.session_state["bet_log"]).copy()

        for idx in log_df.index:
            play_id = log_df.loc[idx, "play_id"]
            saved_result = st.session_state["manual_results"].get(play_id)
            if saved_result:
                log_df.loc[idx, "result"] = saved_result
                log_df.loc[idx, "profit"] = settle_result_pnl(
                    log_df.loc[idx, "odds"],
                    log_df.loc[idx, "units"],
                    saved_result,
                )

        display_cols = [
            "game", "market", "selection", "odds", "units",
            "confidence", "true_confidence", "tier", "status",
            "result", "profit", "mode"
        ]
        for col in display_cols:
            if col not in log_df.columns:
                log_df[col] = None
        st.dataframe(log_df[display_cols], use_container_width=True, hide_index=True)

        st.subheader("Update paper-test results")
        options = [
            f"{row['selection']} | {row['game']} | {row['odds']} | {row['play_id']}"
            for _, row in log_df.iterrows()
        ]
        selected_option = st.selectbox("Choose logged bet", options)
        selected_play_id = selected_option.split(" | ")[-1]
        result_choice = st.selectbox("Result", ["Pending", "Win", "Loss", "Push"], key="result_choice")

        if st.button("Save Result"):
            st.session_state["manual_results"][selected_play_id] = result_choice
            st.success("Bet result updated.")
            st.rerun()

    st.markdown('<div class="bet-form-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="small-muted">Manual paper-test bet entry</div>', unsafe_allow_html=True)
    with st.form("bet_log_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            game = st.text_input("Game")
            market = st.selectbox("Market", ["moneyline", "spread", "total", "prop"])
            units = st.number_input("Units", min_value=0.0, max_value=10.0, value=0.50, step=0.05)
        with col2:
            selection = st.text_input("Selection")
            odds = st.text_input("Odds", value="")
            confidence = st.selectbox("Confidence", ["Medium", "High", "Elite"])
        submitted = st.form_submit_button("Save Bet")

        if submitted:
            manual_row = {
                "play_id": build_play_id({"game": game, "market": market, "selection": selection, "odds": odds}),
                "game": game or "N/A",
                "market": market,
                "selection": selection or "N/A",
                "odds": odds or "N/A",
                "edge": None,
                "score": None,
                "units": units,
                "confidence": confidence,
                "true_confidence": None,
                "tier": "Manual",
                "quality_label": "Manual",
                "status": "Manual",
                "result": "Pending",
                "profit": 0.0,
                "mode": TEST_MODE,
            }
            st.session_state["bet_log"].append(manual_row)
            st.success("Manual test bet saved.")
    st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# ADAPTIVE SETTINGS
# =========================================================
with st.expander("⚙️ Adaptive Settings", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        st.write(f"**Min Active Edge:** {MIN_ACTIVE_EDGE:.2f}%")
        st.write(f"**Primary Quality Threshold:** {QUALITY_ACTIVE_PRIMARY:.2f}")
        st.write(f"**Secondary Quality Threshold:** {QUALITY_ACTIVE_SECONDARY:.2f}")
        st.write(f"**Fallback Quality Floor:** {QUALITY_FLOOR_FALLBACK:.2f}")
        st.write(f"**Sharp Parlay Min True Conf:** {SHARP_PARLAY_MIN_TRUE_CONF:.1f}")
        st.write(f"**Test Mode:** {TEST_MODE}")
    with c2:
        st.write(f"**Active Promotion Edge:** {ACTIVE_EDGE_PROMOTION:.2f}%")
        st.write(f"**Max Active Plays:** {MAX_ACTIVE_PLAYS}")
        st.write(f"**Max Total Units:** {MAX_TOTAL_UNITS:.1f}u")
        st.write(f"**Min Parlay Odds:** +{MIN_PARLAY_ODDS}")
        st.write(f"**Test Daily Unit Cap:** {TEST_DAILY_UNIT_CAP:.2f}u")
        st.write("**CLV Priority:** Delayed until more free books/APIs are added")
