# =========================================================
# IMPORTS + PAGE SETUP
# =========================================================
import hashlib
import random
from itertools import combinations

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Sports Betting AI Dashboard V33.1", layout="wide")

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
MIN_ACTIVE_EDGE = 4.00
MIN_WATCH_EDGE = 2.25
ACTIVE_EDGE_PROMOTION = 4.50

MIN_ACTIVE_TRUE_CONF = 70.0
MIN_WATCH_TRUE_CONF = 55.0

MIN_ACTIVE_BOOKS = 3
MIN_WATCH_BOOKS = 2

MAX_TOTAL_UNITS = 4.25
MAX_ACTIVE_PLAYS = 10
TOP_PLAYS_LIMIT = 10
WATCHLIST_LIMIT = 18

DEFAULT_ODDS_RANGE = (-200, 150)

MIN_PARLAY_LEGS = 2
MAX_PARLAY_LEGS = 3
MIN_PARLAY_ODDS = 200

SHARP_PARLAY_MIN_TRUE_CONF = 70.0
SHARP_PARLAY_MAX_PENALTY = 0.16
FALLBACK_PARLAY_MAX_PENALTY = 0.28

TEST_MODE = "Paper Test"
SINGLE_UNIT_MIN = 0.40
SINGLE_UNIT_MAX = 1.25
PARLAY_UNIT_SHARP = 0.60
PARLAY_UNIT_FALLBACK_2 = 0.35
PARLAY_UNIT_FALLBACK_3 = 0.20
TEST_DAILY_UNIT_CAP = 4.50

ENABLE_PLAYER_PROPS = True
PROPS_ONLY_STARTERS = True

PROP_TYPES = ["points", "rebounds", "assists", "pra"]
PROP_ODDS_RANGE = (-200, 150)
MAX_PROP_PLAYS_PER_GAME = 8
MAX_PLAYS_PER_PLAYER = 1

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


def confidence_bucket_from_true_conf(true_conf):
    tc = float(true_conf)
    if tc >= 75:
        return "Elite"
    if tc >= 70:
        return "High"
    if tc >= 65:
        return "Medium"
    return "Low"


def confidence_fill_and_color(true_conf):
    tc = float(true_conf)
    width = f"{int(clamp(tc, 0, 100))}%"
    if tc >= 75:
        return width, "#10b981", "Elite"
    if tc >= 70:
        return width, "#22c55e", "High"
    if tc >= 65:
        return width, "#f59e0b", "Medium"
    return width, "#ef4444", "Low"


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
    if "prop_" in m:
        return "prop"
    return "other"


def scale_single_units(row):
    true_conf = float(row.get("true_confidence", 0))
    edge = float(row.get("edge", 0))
    books_seen = int(row.get("books_seen", 1))

    base = (
        (true_conf * 0.55)
        + (edge * 6.5)
        + (books_seen * 3.0)
    ) / 55.0

    return round(clamp(base, SINGLE_UNIT_MIN, SINGLE_UNIT_MAX), 2)


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

    if avg_true_conf >= 75:
        base_units += 0.10
    elif avg_true_conf < 68:
        base_units -= 0.08

    if risk_label == "Low":
        base_units += 0.05
    elif risk_label == "Elevated":
        base_units -= 0.10

    return round(clamp(base_units, 0.15, 0.75), 2)


def normalize_team_name(team_name: str):
    team_name = str(team_name).strip()
    alias_map = {
        "ATL": "Hawks",
        "BOS": "Celtics",
        "BKN": "Nets",
        "BRK": "Nets",
        "CHA": "Hornets",
        "CHI": "Bulls",
        "CLE": "Cavaliers",
        "DAL": "Mavericks",
        "DEN": "Nuggets",
        "DET": "Pistons",
        "GSW": "Warriors",
        "HOU": "Rockets",
        "IND": "Pacers",
        "LAC": "Clippers",
        "LAL": "Lakers",
        "MEM": "Grizzlies",
        "MIA": "Heat",
        "MIL": "Bucks",
        "MIN": "Timberwolves",
        "NOP": "Pelicans",
        "NO": "Pelicans",
        "NYK": "Knicks",
        "OKC": "Thunder",
        "ORL": "Magic",
        "PHI": "76ers",
        "PHX": "Suns",
        "PHO": "Suns",
        "POR": "Trail Blazers",
        "SAC": "Kings",
        "SAS": "Spurs",
        "SA": "Spurs",
        "TOR": "Raptors",
        "UTA": "Jazz",
        "UTH": "Jazz",
        "WAS": "Wizards",
    }
    return alias_map.get(team_name.upper(), team_name)


def team_names_from_game(game: str):
    parts = str(game).split(" vs ")
    if len(parts) == 2:
        return normalize_team_name(parts[0]), normalize_team_name(parts[1])
    return "Away", "Home"


def starter_pool_for_team(team_name: str):
    normalized = normalize_team_name(team_name)

    starters_map = {
        "Knicks": ["Jalen Brunson", "Donte DiVincenzo", "Josh Hart", "OG Anunoby", "Julius Randle"],
        "Pelicans": ["CJ McCollum", "Brandon Ingram", "Herb Jones", "Zion Williamson", "Jonas Valanciunas"],
        "Magic": ["Jalen Suggs", "Franz Wagner", "Paolo Banchero", "Jonathan Isaac", "Wendell Carter Jr."],
        "Cavaliers": ["Darius Garland", "Donovan Mitchell", "Max Strus", "Evan Mobley", "Jarrett Allen"],
        "Nuggets": ["Jamal Murray", "Kentavious Caldwell-Pope", "Michael Porter Jr.", "Aaron Gordon", "Nikola Jokic"],
        "Suns": ["Bradley Beal", "Devin Booker", "Grayson Allen", "Kevin Durant", "Jusuf Nurkic"],
        "Spurs": ["Tre Jones", "Devin Vassell", "Keldon Johnson", "Jeremy Sochan", "Victor Wembanyama"],
        "Hornets": ["LaMelo Ball", "Terry Rozier", "Brandon Miller", "Miles Bridges", "Mark Williams"],
        "Lakers": ["D'Angelo Russell", "Austin Reaves", "LeBron James", "Rui Hachimura", "Anthony Davis"],
        "Warriors": ["Stephen Curry", "Klay Thompson", "Andrew Wiggins", "Draymond Green", "Jonathan Kuminga"],
        "Heat": ["Terry Rozier", "Tyler Herro", "Jimmy Butler", "Nikola Jovic", "Bam Adebayo"],
        "Celtics": ["Jrue Holiday", "Derrick White", "Jaylen Brown", "Jayson Tatum", "Kristaps Porzingis"],
    }

    if normalized in starters_map:
        return starters_map[normalized]

    return [
        f"{normalized} Starter 1",
        f"{normalized} Starter 2",
        f"{normalized} Starter 3",
        f"{normalized} Starter 4",
        f"{normalized} Starter 5",
    ]


def prop_line_for_type(prop_type: str):
    default_lines = {
        "points": [17.5, 19.5, 21.5, 23.5, 25.5, 27.5],
        "rebounds": [5.5, 6.5, 7.5, 8.5, 9.5, 10.5],
        "assists": [4.5, 5.5, 6.5, 7.5, 8.5],
        "pra": [28.5, 31.5, 34.5, 37.5, 40.5],
    }
    return random.choice(default_lines.get(prop_type, [10.5, 12.5]))


def build_prop_selection(player_name: str, prop_type: str):
    line = prop_line_for_type(prop_type)
    label_map = {
        "points": "Points",
        "rebounds": "Rebounds",
        "assists": "Assists",
        "pra": "PRA",
    }
    direction = random.choice(["Over", "Under"])
    return f"{player_name} {direction} {line} {label_map.get(prop_type, prop_type.title())}"


def is_prop_market(market: str):
    return str(market).lower().startswith("prop_")


def prop_market_label(market: str):
    m = str(market).lower()
    if m == "prop_points":
        return "Player Props • Points"
    if m == "prop_rebounds":
        return "Player Props • Rebounds"
    if m == "prop_assists":
        return "Player Props • Assists"
    if m == "prop_pra":
        return "Player Props • PRA"
    return str(market).replace("_", " ").title()


# =========================================================
# LIVE SLATE INPUT
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
    placeholder="SAS vs CHA\nNOP vs NYK\nORL vs CLE\nDEN vs PHX",
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
        return 0.56
    return 0.22


def consensus_score(consensus):
    consensus = str(consensus).strip().lower()
    if consensus == "strong":
        return 1.00
    if consensus == "fair":
        return 0.66
    return 0.30


def edge_score(edge):
    return clamp(edge / 6.0, 0.0, 1.0)


def price_edge_score(price_edge):
    return clamp(price_edge / 3.0, 0.0, 1.0)


def model_score(score):
    return clamp((float(score) - 78.0) / 22.0, 0.0, 1.0)


def detect_traps(row):
    penalties = 0.0
    trap_flags = []

    edge = float(row["edge"])
    books_seen = int(row["books_seen"])
    consensus = str(row["consensus"])
    price_edge = float(row["price_edge"])

    if edge < 3.0:
        penalties += 0.12
        trap_flags.append("weak edge")
    if books_seen <= 1:
        penalties += 0.18
        trap_flags.append("single-book risk")
    elif books_seen == 2:
        penalties += 0.08
        trap_flags.append("limited book support")
    if consensus == "Thin":
        penalties += 0.14
        trap_flags.append("thin consensus")
    if price_edge < 1.0:
        penalties += 0.08
        trap_flags.append("weak price support")

    return clamp(penalties, 0.0, 0.40), trap_flags


def compute_true_confidence(row):
    ms = model_score(row["score"])
    es = edge_score(row["edge"])
    ps = price_edge_score(row["price_edge"])
    bs = books_score(row["books_seen"])
    cs = consensus_score(row["consensus"])

    penalty, trap_flags = detect_traps(row)

    raw_quality = (
        ms * 0.30
        + es * 0.28
        + ps * 0.12
        + bs * 0.15
        + cs * 0.15
    )

    adjusted_quality = clamp(raw_quality - penalty, 0.0, 1.0)
    true_confidence = round(adjusted_quality * 100.0, 1)

    reasons = []
    if row["books_seen"] >= 3:
        reasons.append("multi-book support")
    if str(row["consensus"]).lower() == "strong":
        reasons.append("strong consensus")
    elif str(row["consensus"]).lower() == "fair":
        reasons.append("usable consensus")
    if float(row["price_edge"]) >= 1.25:
        reasons.append("price support")
    if float(row["score"]) >= 88:
        reasons.append("strong model score")
    if float(row["edge"]) >= 4.0:
        reasons.append("sharp edge")
    reasons.extend(trap_flags)

    return true_confidence, adjusted_quality, reasons


def tier_from_true_conf(tc):
    if tc >= 78:
        return "A"
    if tc >= 65:
        return "B"
    return "C"


# =========================================================
# DATA BUILD
# =========================================================
def generate_ai_plays():
    empty_cols = [
        "game", "market", "selection", "odds", "edge", "score", "units", "tier",
        "quality_label", "status", "confidence", "books_seen", "best_price",
        "consensus", "price_edge", "ai_tags", "true_confidence", "quality_score",
        "decision_reasons", "rank_score", "play_id"
    ]

    if not today_games:
        return pd.DataFrame(columns=empty_cols)

    team_market_templates = [
        ("moneyline", lambda g: normalize_team_name(g.split(" vs ")[1])),
        ("moneyline", lambda g: normalize_team_name(g.split(" vs ")[0])),
        ("total", lambda g: "Over 221.5"),
        ("total", lambda g: "Under 221.5"),
        ("spread", lambda g: f"{normalize_team_name(g.split(' vs ')[1])} -4.5"),
        ("spread", lambda g: f"{normalize_team_name(g.split(' vs ')[0])} +4.5"),
    ]

    odds_pool = ["-132", "-118", "-110", "-105", "-102", "+100", "+110", "+120", "+135"]
    consensus_pool = ["Strong", "Fair", "Thin"]

    rows = []
    random.seed(331)

    for game in today_games:
        away_team, home_team = team_names_from_game(game)

        # ---------------------------
        # TEAM MARKETS
        # ---------------------------
        for market, selection_fn in team_market_templates:
            edge = round(random.uniform(1.50, 5.60), 2)
            score = round(random.uniform(79.0, 99.5), 1)
            books_seen = random.randint(1, 4)
            odds = random.choice(odds_pool)
            consensus = random.choices(consensus_pool, weights=[4, 4, 2], k=1)[0]
            price_edge = round(random.uniform(0.50, 2.80), 2)

            if edge < MIN_WATCH_EDGE:
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
                "confidence": "Low",
                "books_seen": books_seen,
                "best_price": "Yes" if price_edge >= 1.25 else "No",
                "consensus": consensus,
                "price_edge": price_edge,
                "ai_tags": ["AI generated", "live slate", "team market"],
            }

            tc, qs, reasons = compute_true_confidence(row)
            row["true_confidence"] = tc
            row["quality_score"] = qs
            row["decision_reasons"] = reasons
            row["confidence"] = confidence_bucket_from_true_conf(tc)
            row["units"] = scale_single_units(row)

            tags = ["AI generated", "live slate", "team market"]
            for reason in reasons:
                if reason not in tags:
                    tags.append(reason)
            row["ai_tags"] = tags[:6]
            rows.append(row)

        # ---------------------------
        # PLAYER PROPS
        # ---------------------------
        if ENABLE_PLAYER_PROPS:
            prop_rows_this_game = 0

            for team_name in [away_team, home_team]:
                players = starter_pool_for_team(team_name)

                if PROPS_ONLY_STARTERS:
                    players = players[:5]

                for player_name in players:
                    if prop_rows_this_game >= MAX_PROP_PLAYS_PER_GAME:
                        break

                    player_plays_added = 0
                    prop_types_this_player = PROP_TYPES.copy()
                    random.shuffle(prop_types_this_player)

                    for prop_type in prop_types_this_player:
                        if prop_rows_this_game >= MAX_PROP_PLAYS_PER_GAME:
                            break
                        if player_plays_added >= MAX_PLAYS_PER_PLAYER:
                            break

                        edge = round(random.uniform(1.60, 5.80), 2)
                        score = round(random.uniform(79.0, 99.5), 1)
                        books_seen = random.randint(1, 4)
                        odds = random.choice(odds_pool)
                        consensus = random.choices(consensus_pool, weights=[4, 4, 2], k=1)[0]
                        price_edge = round(random.uniform(0.50, 2.90), 2)

                        if edge < MIN_WATCH_EDGE:
                            continue
                        if not in_allowed_odds_range(odds, *PROP_ODDS_RANGE):
                            continue

                        selection = build_prop_selection(player_name, prop_type)

                        row = {
                            "game": game,
                            "market": f"prop_{prop_type}",
                            "selection": selection,
                            "odds": odds,
                            "edge": edge,
                            "score": score,
                            "units": 0.0,
                            "tier": "C",
                            "quality_label": "Watch",
                            "status": "Watch",
                            "confidence": "Low",
                            "books_seen": books_seen,
                            "best_price": "Yes" if price_edge >= 1.25 else "No",
                            "consensus": consensus,
                            "price_edge": price_edge,
                            "ai_tags": ["AI generated", "live slate", "player prop"],
                        }

                        tc, qs, reasons = compute_true_confidence(row)
                        row["true_confidence"] = tc
                        row["quality_score"] = qs
                        row["decision_reasons"] = reasons
                        row["confidence"] = confidence_bucket_from_true_conf(tc)
                        row["units"] = scale_single_units(row)

                        tags = ["AI generated", "live slate", "player prop"]
                        for reason in reasons:
                            if reason not in tags:
                                tags.append(reason)
                        row["ai_tags"] = tags[:6]

                        rows.append(row)
                        prop_rows_this_game += 1
                        player_plays_added += 1

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=empty_cols)

    df["rank_score"] = (
        df["true_confidence"] * 0.55
        + df["edge"] * 7.0
        + df["price_edge"] * 3.5
        + df["books_seen"] * 2.0
        + df["score"] * 0.08
    )

    def decide_status(row):
        if (
            float(row["edge"]) >= MIN_ACTIVE_EDGE
            and float(row["true_confidence"]) >= MIN_ACTIVE_TRUE_CONF
            and int(row["books_seen"]) >= MIN_ACTIVE_BOOKS
            and str(row["consensus"]) in ["Strong", "Fair"]
        ):
            return "Active"

        if (
            float(row["edge"]) >= MIN_WATCH_EDGE
            and float(row["true_confidence"]) >= MIN_WATCH_TRUE_CONF
            and int(row["books_seen"]) >= MIN_WATCH_BOOKS
        ):
            return "Watch"

        return "Discard"

    df["status"] = df.apply(decide_status, axis=1)
    df = df[df["status"] != "Discard"].copy()

    if df.empty:
        return pd.DataFrame(columns=empty_cols)

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

    active_local = (
        df[df["status"] == "Active"]
        .sort_values(["rank_score", "true_confidence"], ascending=False)
        .head(TOP_PLAYS_LIMIT)
        .copy()
    )

    watch_local = (
        df[df["status"] == "Watch"]
        .sort_values(["rank_score", "true_confidence"], ascending=False)
        .head(WATCHLIST_LIMIT)
        .copy()
    )

    active_rows = []
    running_units = 0.0

    for _, row in active_local.iterrows():
        proposed_units = float(row["units"])

        if len(active_rows) >= MAX_ACTIVE_PLAYS:
            row2 = row.copy()
            row2["status"] = "Watch"
            watch_local = pd.concat([watch_local, pd.DataFrame([row2])], ignore_index=True)
            continue

        if running_units + proposed_units > MAX_TOTAL_UNITS:
            row2 = row.copy()
            row2["status"] = "Watch"
            watch_local = pd.concat([watch_local, pd.DataFrame([row2])], ignore_index=True)
            continue

        active_rows.append(row)
        running_units += proposed_units

    active_final = pd.DataFrame(active_rows) if active_rows else pd.DataFrame(columns=df.columns)
    combined = pd.concat([active_final, watch_local], ignore_index=True)

    if combined.empty:
        return pd.DataFrame(columns=empty_cols)

    return combined.sort_values(["status", "rank_score"], ascending=[True, False]).reset_index(drop=True)
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

            if same_game:
                score -= 1.0
                if market_a == market_b:
                    score -= 0.5
            else:
                score += 0.5
    return score


def selections_conflict(row_a, row_b):
    if row_a["game"] != row_b["game"]:
        return False

    sel_a = str(row_a["selection"]).lower()
    sel_b = str(row_b["selection"]).lower()

    if row_a["market"] == row_b["market"] and row_a["selection"] != row_b["selection"]:
        return True
    if ("over" in sel_a and "under" in sel_b) or ("under" in sel_a and "over" in sel_b):
        return True

    return False


def pair_correlation_penalty(row_a, row_b):
    penalty = 0.0
    reasons = []

    if selections_conflict(row_a, row_b):
        return 1.0, ["conflicting legs"]

    if row_a["game"] == row_b["game"]:
        penalty += 0.22
        reasons.append("same-game correlation")

    return clamp(penalty, 0.0, 1.0), reasons


def score_parlay_combo(combo):
    total_penalty = 0.0
    penalty_reasons = []

    for a, b in combinations(combo, 2):
        penalty, reasons = pair_correlation_penalty(a, b)
        if penalty >= 1.0:
            return None
        total_penalty += penalty
        penalty_reasons.extend(reasons)

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

    distinct_games = len(set(leg["game"] for leg in combo))
    cross_game = distinct_games == len(combo)
    correlation_score = calculate_correlation_score(list(combo))

    score = (
        avg_true_conf * 0.65
        + avg_edge * 7.0
        + avg_books * 1.5
        + (4 if cross_game else -6)
        - (total_penalty * 35)
        + (correlation_score * 4)
    )

    if total_penalty <= 0.10 and avg_true_conf >= 74:
        risk_label = "Low"
    elif total_penalty <= 0.20 and avg_true_conf >= 70:
        risk_label = "Moderate"
    else:
        risk_label = "Elevated"

    reasons = []
    if cross_game:
        reasons.append("cross-game diversification")
    if avg_true_conf >= 72:
        reasons.append("strong true confidence")
    if avg_edge >= 4.2:
        reasons.append("sharp average edge")
    if avg_books >= 3:
        reasons.append("broad book support")
    reasons.extend(penalty_reasons)

    return {
        "legs": list(combo),
        "leg_count": len(combo),
        "combined_odds": format_american(combined_american),
        "combined_odds_int": combined_american,
        "avg_true_conf": round(avg_true_conf, 1),
        "avg_edge": round(avg_edge, 2),
        "avg_books": round(avg_books, 2),
        "total_penalty": round(total_penalty, 3),
        "cross_game": cross_game,
        "correlation_score": round(correlation_score, 2),
        "score": round(score, 1),
        "display_score": round(score, 1),
        "risk_label": risk_label,
        "reasons": reasons[:6],
    }


def build_all_parlay_candidates(active_df):
    if active_df.empty or len(active_df) < 2:
        return []

    rows = active_df.to_dict("records")
    candidates = []

    for leg_count in range(MIN_PARLAY_LEGS, min(MAX_PARLAY_LEGS, len(rows)) + 1):
        for combo in combinations(rows, leg_count):
            if any(float(leg["edge"]) < 4.0 for leg in combo):
                continue
            if any(float(leg["true_confidence"]) < 70.0 for leg in combo):
                continue
            if any(int(leg["books_seen"]) < 3 for leg in combo):
                continue

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
            c["avg_true_conf"] >= 68
            and c["total_penalty"] <= FALLBACK_PARLAY_MAX_PENALTY
            and c["combined_odds_int"] >= MIN_PARLAY_ODDS
        )

        if sharp_ok:
            c1 = c.copy()
            c1["approval_type"] = "Sharp Approved"
            sharp_candidates.append(c1)

        if fallback_ok:
            c2 = c.copy()
            c2["approval_type"] = "Balanced Fallback"
            fallback_candidates.append(c2)

    sharp_candidates.sort(key=lambda x: (x["score"], x["avg_true_conf"]), reverse=True)
    fallback_candidates.sort(key=lambda x: (x["score"], x["avg_true_conf"]), reverse=True)
    return sharp_candidates, fallback_candidates


def choose_best_parlay(active_df):
    all_candidates = build_all_parlay_candidates(active_df)
    sharp_candidates, fallback_candidates = classify_parlay_candidates(all_candidates)

    if sharp_candidates:
        return sharp_candidates[0], sharp_candidates, fallback_candidates
    if fallback_candidates:
        return fallback_candidates[0], sharp_candidates, fallback_candidates
    return None, sharp_candidates, fallback_candidates


# =========================================================
# AUTO-LOG ACTIVE PLAYS
# =========================================================
def auto_log_active_plays(df):
    if df.empty:
        return 0

    count_added = 0
    active_only = df[df["status"] == "Active"].copy()

    for _, row in active_only.iterrows():
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

    fill_width, fill_color, conf_label = confidence_fill_and_color(row["true_confidence"])
    edge_color = "#4ade80" if float(row["edge"]) >= 4 else "#fbbf24"

    visible_tags = list(row["ai_tags"])[:3]
    tags_html = ""
    for tag in visible_tags:
        tags_html += f"""
        <span style="background:#1e2638;color:#d8e0ec;border:1px solid #2a3448;border-radius:999px;
        padding:3px 7px;font-size:10px;line-height:1;display:inline-block;margin-right:5px;margin-bottom:4px;white-space:nowrap;">{tag}</span>
        """

    html = f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1" /></head>
    <body style="margin:0;background:transparent;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
    <div style="background:linear-gradient(180deg, #151b29 0%, #0e1422 100%);
    border:1px solid #243047;border-radius:22px;padding:12px;color:#ffffff;box-sizing:border-box;">

        <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:7px;">
            <span style="background:{badge_bg};color:{badge_fg};padding:5px 9px;border-radius:999px;font-size:10px;font-weight:800;">Tier {row['tier']}</span>
            <span style="background:{status_bg};color:{status_fg};padding:5px 9px;border-radius:999px;font-size:10px;font-weight:800;">{row['status']}</span>
            <span style="background:#efe2ff;color:#6b21a8;padding:4px 8px;border-radius:999px;font-size:9px;font-weight:800;display:{best_display};">🏆 Best Bet</span>
        </div>

        <div style="font-size:21px;font-weight:800;margin-bottom:5px;">{row['selection']}</div>
        <div style="color:#d4dbe8;font-size:12px;margin-bottom:8px;">{row['game']} • {prop_market_label(row['market']) if is_prop_market(row['market']) else str(row['market']).title()}</div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px 12px;margin-bottom:6px;">
            <div><div style="color:#91a0b7;font-size:10px;">Odds</div><div style="font-weight:700;">{row['odds']}</div></div>
            <div><div style="color:#91a0b7;font-size:10px;">AI Score</div><div style="color:#60a5fa;font-weight:700;">{row['score']}</div></div>
            <div><div style="color:#91a0b7;font-size:10px;">Edge</div><div style="color:{edge_color};font-weight:700;">{row['edge']:.2f}%</div></div>
            <div><div style="color:#91a0b7;font-size:10px;">Units</div><div style="font-weight:700;">{row['units']:.2f}u</div></div>
            <div><div style="color:#91a0b7;font-size:10px;">Consensus</div><div style="font-weight:700;">{row['consensus']}</div></div>
            <div><div style="color:#91a0b7;font-size:10px;">Books</div><div style="font-weight:700;">{row['books_seen']}</div></div>
            <div><div style="color:#91a0b7;font-size:10px;">True Conf</div><div style="font-weight:700;">{row['true_confidence']:.1f}</div></div>
            <div><div style="color:#91a0b7;font-size:10px;">Quality</div><div style="font-weight:700;">{row['quality_label']}</div></div>
        </div>

        <div style="height:1px;background:#283550;margin:6px 0;"></div>

        <div style="color:#91a0b7;font-size:10px;">Confidence • {conf_label}</div>
        <div style="width:100%;height:5px;background:#24324b;border-radius:999px;">
            <div style="width:{fill_width};height:5px;background:{fill_color};border-radius:999px;"></div>
        </div>

        <div style="margin-top:6px;">{tags_html}</div>

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

    risk_color = {
        "Low": "#10b981",
        "Moderate": "#f59e0b",
        "Elevated": "#ef4444",
    }.get(parlay["risk_label"], "#94a3b8")

    legs_html = ""
    for i, leg in enumerate(parlay["legs"], start=1):
        legs_html += f"""
        <div style="padding:6px 0;border-bottom:1px solid #243047;">
            <div style="font-weight:800;">{i}. {leg['selection']}</div>
            <div style="font-size:12px;color:#cbd5e1;">
                {leg['game']} • {prop_market_label(leg['market']) if is_prop_market(leg['market']) else "Team Market"} • {leg['odds']}
            </div>
        </div>
        """

    html = f"""
    <html>
    <body style="margin:0;font-family:sans-serif;">
        <div style="background:#0e1422;border-radius:20px;padding:12px;border:1px solid #243047;color:white;">
            <div style="font-weight:800;margin-bottom:6px;">🔥 AI PARLAY</div>
            <div style="margin-bottom:6px;">{parlay['approval_type']}</div>
            <div style="margin-bottom:6px;">Odds: {parlay['combined_odds']} | Conf: {parlay['avg_true_conf']}</div>
            <div style="color:{risk_color};font-weight:800;margin-bottom:10px;">Risk: {parlay['risk_label']}</div>
            {legs_html}
        </div>
    </body>
    </html>
    """

    components.html(html, height=260, scrolling=False)

# =========================================================
# TABLE RENDER HELPERS
# =========================================================
def render_parlay_table(candidates, title):
    st.markdown(f"**{title}**")

    if not candidates:
        st.info("No candidates.")
        return

    rows = []
    for p in candidates[:5]:
        rows.append(
            {
                "Legs": p.get("leg_count"),
                "Odds": p.get("combined_odds"),
                "Avg Conf": round(p.get("avg_true_conf", 0), 1),
                "Score": round(p.get("display_score", p.get("score", 0)), 1),
                "Risk": p.get("risk_label"),
            }
        )

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_table_desktop(df: pd.DataFrame):
    cols = [
        "tier", "quality_label", "status", "game", "market", "selection",
        "odds", "edge", "score", "units", "confidence", "true_confidence",
        "books_seen", "best_price", "consensus", "price_edge"
    ]
    existing_cols = [c for c in cols if c in df.columns]
    st.dataframe(df[existing_cols], use_container_width=True, hide_index=True)


def render_mobile_or_table(df: pd.DataFrame, best_first: bool = False):
    if df.empty:
        st.info("No plays available.")
        return

    if is_mobile():
        for idx, (_, row) in enumerate(df.iterrows()):
            render_play_card(row, show_best_badge=(best_first and idx == 0))
    else:
        render_table_desktop(df)


# =========================================================
# PORTFOLIO LAYER
# =========================================================
def build_ai_portfolio(best_single, chosen_parlay, parlay_candidates):
    portfolio = []
    used_keys = set()
    running_units = 0.0

    if best_single is not None:
        units = scale_single_units(best_single)
        key = f"single::{best_single.get('play_id', best_single.get('selection', ''))}"

        if running_units + units <= TEST_DAILY_UNIT_CAP:
            portfolio.append(
                {
                    "type": "Single",
                    "label": "Core Play",
                    "units": units,
                    "data": best_single,
                }
            )
            used_keys.add(key)
            running_units += units

    if chosen_parlay is not None:
        units = scale_parlay_units(chosen_parlay)
        key = "parlay::" + "|".join([leg.get("selection", "") for leg in chosen_parlay.get("legs", [])])

        if key not in used_keys and running_units + units <= TEST_DAILY_UNIT_CAP:
            portfolio.append(
                {
                    "type": "Parlay",
                    "label": chosen_parlay.get("approval_type", "Primary"),
                    "units": units,
                    "data": chosen_parlay,
                }
            )
            used_keys.add(key)
            running_units += units

    return portfolio

# =========================================================
# DATA BUILD
# =========================================================
def generate_ai_plays():
    empty_cols = [
        "game", "market", "selection", "odds", "edge", "score", "units", "tier",
        "quality_label", "status", "confidence", "books_seen", "best_price",
        "consensus", "price_edge", "ai_tags", "true_confidence", "quality_score",
        "decision_reasons", "rank_score", "play_id"
    ]

    if not today_games:
        return pd.DataFrame(columns=empty_cols)

    team_market_templates = [
        ("moneyline", lambda g: normalize_team_name(g.split(" vs ")[1])),
        ("moneyline", lambda g: normalize_team_name(g.split(" vs ")[0])),
        ("total", lambda g: "Over 221.5"),
        ("total", lambda g: "Under 221.5"),
        ("spread", lambda g: f"{normalize_team_name(g.split(' vs ')[1])} -4.5"),
        ("spread", lambda g: f"{normalize_team_name(g.split(' vs ')[0])} +4.5"),
    ]

    odds_pool = ["-132", "-118", "-110", "-105", "-102", "+100", "+110", "+120", "+135"]
    consensus_pool = ["Strong", "Fair", "Thin"]

    rows = []
    random.seed(331)

    for game in today_games:
        away_team, home_team = team_names_from_game(game)

        # ---------------------------
        # TEAM MARKETS
        # ---------------------------
        for market, selection_fn in team_market_templates:
            edge = round(random.uniform(1.50, 5.60), 2)
            score = round(random.uniform(79.0, 99.5), 1)
            books_seen = random.randint(1, 4)
            odds = random.choice(odds_pool)
            consensus = random.choices(consensus_pool, weights=[4, 4, 2], k=1)[0]
            price_edge = round(random.uniform(0.50, 2.80), 2)

            if edge < MIN_WATCH_EDGE:
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
                "confidence": "Low",
                "books_seen": books_seen,
                "best_price": "Yes" if price_edge >= 1.25 else "No",
                "consensus": consensus,
                "price_edge": price_edge,
                "ai_tags": ["AI generated", "live slate", "team market"],
            }

            tc, qs, reasons = compute_true_confidence(row)
            row["true_confidence"] = tc
            row["quality_score"] = qs
            row["decision_reasons"] = reasons
            row["confidence"] = confidence_bucket_from_true_conf(tc)
            row["units"] = scale_single_units(row)

            tags = ["AI generated", "live slate", "team market"]
            for reason in reasons:
                if reason not in tags:
                    tags.append(reason)
            row["ai_tags"] = tags[:6]
            rows.append(row)

        # ---------------------------
        # PLAYER PROPS
        # ---------------------------
        if ENABLE_PLAYER_PROPS:
            prop_rows_this_game = 0

            for team_name in [away_team, home_team]:
                players = starter_pool_for_team(team_name)

                if PROPS_ONLY_STARTERS:
                    players = players[:5]

                for player_name in players:
                    if prop_rows_this_game >= MAX_PROP_PLAYS_PER_GAME:
                        break

                    player_plays_added = 0
                    prop_types_this_player = PROP_TYPES.copy()
                    random.shuffle(prop_types_this_player)

                    for prop_type in prop_types_this_player:
                        if prop_rows_this_game >= MAX_PROP_PLAYS_PER_GAME:
                            break
                        if player_plays_added >= MAX_PLAYS_PER_PLAYER:
                            break

                        edge = round(random.uniform(1.60, 5.80), 2)
                        score = round(random.uniform(79.0, 99.5), 1)
                        books_seen = random.randint(1, 4)
                        odds = random.choice(odds_pool)
                        consensus = random.choices(consensus_pool, weights=[4, 4, 2], k=1)[0]
                        price_edge = round(random.uniform(0.50, 2.90), 2)

                        if edge < MIN_WATCH_EDGE:
                            continue
                        if not in_allowed_odds_range(odds, *PROP_ODDS_RANGE):
                            continue

                        selection = build_prop_selection(player_name, prop_type)

                        row = {
                            "game": game,
                            "market": f"prop_{prop_type}",
                            "selection": selection,
                            "odds": odds,
                            "edge": edge,
                            "score": score,
                            "units": 0.0,
                            "tier": "C",
                            "quality_label": "Watch",
                            "status": "Watch",
                            "confidence": "Low",
                            "books_seen": books_seen,
                            "best_price": "Yes" if price_edge >= 1.25 else "No",
                            "consensus": consensus,
                            "price_edge": price_edge,
                            "ai_tags": ["AI generated", "live slate", "player prop"],
                        }

                        tc, qs, reasons = compute_true_confidence(row)
                        row["true_confidence"] = tc
                        row["quality_score"] = qs
                        row["decision_reasons"] = reasons
                        row["confidence"] = confidence_bucket_from_true_conf(tc)
                        row["units"] = scale_single_units(row)

                        tags = ["AI generated", "live slate", "player prop"]
                        for reason in reasons:
                            if reason not in tags:
                                tags.append(reason)
                        row["ai_tags"] = tags[:6]

                        rows.append(row)
                        prop_rows_this_game += 1
                        player_plays_added += 1

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=empty_cols)

    df["rank_score"] = (
        df["true_confidence"] * 0.55
        + df["edge"] * 7.0
        + df["price_edge"] * 3.5
        + df["books_seen"] * 2.0
        + df["score"] * 0.08
    )

    def decide_status(row):
        if (
            float(row["edge"]) >= MIN_ACTIVE_EDGE
            and float(row["true_confidence"]) >= MIN_ACTIVE_TRUE_CONF
            and int(row["books_seen"]) >= MIN_ACTIVE_BOOKS
            and str(row["consensus"]) in ["Strong", "Fair"]
        ):
            return "Active"

        if (
            float(row["edge"]) >= MIN_WATCH_EDGE
            and float(row["true_confidence"]) >= MIN_WATCH_TRUE_CONF
            and int(row["books_seen"]) >= MIN_WATCH_BOOKS
        ):
            return "Watch"

        return "Discard"

    df["status"] = df.apply(decide_status, axis=1)
    df = df[df["status"] != "Discard"].copy()

    if df.empty:
        return pd.DataFrame(columns=empty_cols)

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

    active_local = (
        df[df["status"] == "Active"]
        .sort_values(["rank_score", "true_confidence"], ascending=False)
        .head(TOP_PLAYS_LIMIT)
        .copy()
    )

    watch_local = (
        df[df["status"] == "Watch"]
        .sort_values(["rank_score", "true_confidence"], ascending=False)
        .head(WATCHLIST_LIMIT)
        .copy()
    )

    active_rows = []
    running_units = 0.0

    for _, row in active_local.iterrows():
        proposed_units = float(row["units"])

        if len(active_rows) >= MAX_ACTIVE_PLAYS:
            row2 = row.copy()
            row2["status"] = "Watch"
            watch_local = pd.concat([watch_local, pd.DataFrame([row2])], ignore_index=True)
            continue

        if running_units + proposed_units > MAX_TOTAL_UNITS:
            row2 = row.copy()
            row2["status"] = "Watch"
            watch_local = pd.concat([watch_local, pd.DataFrame([row2])], ignore_index=True)
            continue

        active_rows.append(row)
        running_units += proposed_units

    active_final = pd.DataFrame(active_rows) if active_rows else pd.DataFrame(columns=df.columns)
    combined = pd.concat([active_final, watch_local], ignore_index=True)

    if combined.empty:
        return pd.DataFrame(columns=empty_cols)

    return combined.sort_values(["status", "rank_score"], ascending=[True, False]).reset_index(drop=True)

# =========================================================
# PAGE STYLES
# =========================================================
st.markdown(
    """
<style>
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
.stApp {
    background-color: #f6f7fb;
}
.block-container {
    max-width: 880px;
    padding-top: 0.85rem;
    padding-bottom: 1.8rem;
}
h1, h2, h3 {
    letter-spacing: -0.02em;
    color: #202533;
}
.metric-panel {
    background: #ffffff;
    border: 1px solid #e7ebf2;
    border-radius: 18px;
    padding: 10px 12px;
    margin-bottom: 10px;
}
.metric-panel-title {
    color: #1f2937;
    font-weight: 800;
    font-size: 0.94rem;
    margin-bottom: 6px;
}
.metric-mini-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px 12px;
}
.metric-mini-label {
    font-size: 0.75rem;
    color: #6b7280;
}
.metric-mini-value {
    font-size: 0.98rem;
    font-weight: 800;
    color: #111827;
}
.nav-wrap {
    background: #ffffff;
    border: 1px solid #e6eaf2;
    border-radius: 18px;
    padding: 10px 12px 7px 12px;
    margin-bottom: 12px;
}
.section-title {
    font-size: 0.98rem;
    font-weight: 800;
    margin-bottom: 0.25rem;
    color: #1e2430;
}
.slip-card {
    background: linear-gradient(180deg, #151b29 0%, #0e1422 100%);
    border: 1px solid #243047;
    border-radius: 22px;
    padding: 13px;
    margin-bottom: 10px;
    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.14);
}
.slip-kicker {
    color: #fbbf24;
    font-size: 0.82rem;
    font-weight: 800;
    margin-bottom: 5px;
}
.slip-title {
    color: #ffffff;
    font-size: 1.35rem;
    font-weight: 800;
    margin-bottom: 5px;
    letter-spacing: -0.03em;
}
.slip-meta {
    color: #d6deea;
    font-size: 0.86rem;
    margin-bottom: 3px;
}
.bet-form-wrap {
    background: #ffffff;
    border: 1px solid #e7ebf2;
    border-radius: 20px;
    padding: 14px;
    margin-bottom: 14px;
}
.notice-box {
    background: #ecfdf5;
    border: 1px solid #a7f3d0;
    color: #065f46;
    border-radius: 16px;
    padding: 10px 12px;
    margin-bottom: 10px;
    font-weight: 700;
}
</style>
""",
    unsafe_allow_html=True,
)

# =========================================================
# HEADER
# =========================================================
st.title("🔥 Sports Betting AI Dashboard V33.1")
st.caption("Real Player Fix • Smart Filter Engine • True Confidence Cleanup • Top Plays Cap")

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
    st.caption("Up to 10 qualified plays only. No filler.")

    if not today_games:
        st.warning("Enter today's real games in the sidebar to generate plays.")
    else:
        top_df = (
            active_df.sort_values(["rank_score", "true_confidence"], ascending=False)
            .head(TOP_PLAYS_LIMIT)
            .reset_index(drop=True)
        )

        if top_df.empty:
            st.info("No plays met the active criteria for this slate.")
        else:
            render_mobile_or_table(top_df, best_first=True)

# =========================================================
# WATCHLIST
# =========================================================
elif nav == "Watchlist":
    st.header("👀 Watchlist")
    st.caption("Near-qualified plays only.")

    if not today_games:
        st.warning("Enter today's real games in the sidebar to generate plays.")
    else:
        wl_df = (
            watch_df.sort_values(["rank_score", "true_confidence"], ascending=False)
            .head(WATCHLIST_LIMIT)
            .reset_index(drop=True)
        )

        render_mobile_or_table(wl_df)

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
        risk_level = "Low" if float(best_row["units"]) <= 0.60 else "Moderate"

        st.markdown(
            f"""
            <div class="slip-card">
                <div class="slip-kicker">🔥 AI Recommended Single</div>
                <div class="slip-title">{best_row['selection']}</div>
                <div class="slip-meta">{best_row['game']} • {prop_market_label(best_row['market']) if is_prop_market(best_row['market']) else str(best_row['market']).title()}</div>
                <div class="slip-meta"><strong>Confidence:</strong> {best_row['confidence']}</div>
                <div class="slip-meta"><strong>True Confidence:</strong> {best_row['true_confidence']:.1f}</div>
                <div class="slip-meta"><strong>Quality Label:</strong> {best_row['quality_label']}</div>
                <div class="slip-meta"><strong>Odds:</strong> {best_row['odds']}</div>
                <div class="slip-meta"><strong>Type:</strong> Single best bet</div>
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
        st.info("Not enough qualifying legs.")
    else:
        render_parlay_card(best_parlay)

    with st.expander("Show top parlay candidates", expanded=False):
        render_parlay_table(sharp_candidates, "Sharp Approved")
        render_parlay_table(fallback_candidates, "Fallback")

    st.subheader("🧠 AI Portfolio Allocation")

    if not portfolio:
        st.info("No portfolio available.")
    else:
        rows = []

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

            rows.append(
                {
                    "Label": item["label"],
                    "Type": item["type"],
                    "Units": item["units"],
                    "Odds": odds,
                    "Confidence": conf,
                    "Summary": summary,
                }
            )

        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# =========================================================
# BET LOG
# =========================================================
elif nav == "Bet Log":
    st.header("🧾 Bet Log")

    if len(st.session_state["bet_log"]) == 0:
        st.info("No bets logged yet.")
    else:
        log_df = pd.DataFrame(st.session_state["bet_log"]).copy()

        for idx in log_df.index:
            pid = log_df.loc[idx, "play_id"]
            if pid in st.session_state["manual_results"]:
                result = st.session_state["manual_results"][pid]
                log_df.loc[idx, "result"] = result
                log_df.loc[idx, "profit"] = settle_result_pnl(
                    log_df.loc[idx, "odds"],
                    log_df.loc[idx, "units"],
                    result,
                )

        st.dataframe(log_df, use_container_width=True, hide_index=True)

        st.subheader("Update Results")

        options = [f"{r['selection']} | {r['game']} | {r['play_id']}" for _, r in log_df.iterrows()]
        selected = st.selectbox("Select Bet", options)
        selected_id = selected.split(" | ")[-1]
        result_choice = st.selectbox("Result", ["Pending", "Win", "Loss", "Push"])

        if st.button("Save Result"):
            st.session_state["manual_results"][selected_id] = result_choice
            st.success("Updated.")
            st.rerun()

    st.markdown('<div class="bet-form-wrap">', unsafe_allow_html=True)

    with st.form("manual_bet", clear_on_submit=True):
        c1, c2 = st.columns(2)

        with c1:
            game = st.text_input("Game")
            market = st.selectbox("Market", ["moneyline", "spread", "total", "prop_points", "prop_rebounds", "prop_assists", "prop_pra"])
            units = st.number_input("Units", 0.0, 10.0, 0.5)

        with c2:
            selection = st.text_input("Selection")
            odds = st.text_input("Odds")
            confidence = st.selectbox("Confidence", ["Low", "Medium", "High", "Elite"])

        submit = st.form_submit_button("Add Bet")

        if submit:
            new = {
                "play_id": build_play_id({"game": game, "market": market, "selection": selection, "odds": odds}),
                "game": game,
                "market": market,
                "selection": selection,
                "odds": odds,
                "units": units,
                "confidence": confidence,
                "result": "Pending",
                "profit": 0.0,
                "mode": TEST_MODE,
            }

            st.session_state["bet_log"].append(new)
            st.success("Bet added.")

    st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# ADAPTIVE SETTINGS
# =========================================================
with st.expander("⚙️ Adaptive Settings", expanded=False):
    c1, c2 = st.columns(2)

    with c1:
        st.write(f"Min Active Edge: {MIN_ACTIVE_EDGE}")
        st.write(f"Min Watch Edge: {MIN_WATCH_EDGE}")
        st.write(f"Min Active True Conf: {MIN_ACTIVE_TRUE_CONF}")
        st.write(f"Min Active Books: {MIN_ACTIVE_BOOKS}")

    with c2:
        st.write(f"Max Top Plays: {TOP_PLAYS_LIMIT}")
        st.write(f"Max Active Plays: {MAX_ACTIVE_PLAYS}")
        st.write(f"Max Total Units: {MAX_TOTAL_UNITS}")
        st.write(f"Min Parlay Odds: +{MIN_PARLAY_ODDS}")
