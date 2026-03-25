# =========================================================
# IMPORTS + PAGE SETUP
# =========================================================
import hashlib
import random
import time
from itertools import combinations

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Sports Betting AI Dashboard V33.4", layout="wide")
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
if "odds_api_games" not in st.session_state:
    st.session_state["odds_api_games"] = []
if "last_odds_refresh_ok" not in st.session_state:
    st.session_state["last_odds_refresh_ok"] = False
if "last_refresh_time" not in st.session_state:
    st.session_state["last_refresh_time"] = None
if "last_refresh_error" not in st.session_state:
    st.session_state["last_refresh_error"] = ""
if "last_refresh_count" not in st.session_state:
    st.session_state["last_refresh_count"] = 0

# V33.3 SMART API USAGE STATE
if "last_successful_odds_games" not in st.session_state:
    st.session_state["last_successful_odds_games"] = []
if "last_api_pull_epoch" not in st.session_state:
    st.session_state["last_api_pull_epoch"] = 0.0
if "api_cooldown_seconds" not in st.session_state:
    st.session_state["api_cooldown_seconds"] = 90
if "api_mode" not in st.session_state:
    st.session_state["api_mode"] = "idle"   # idle | live | cached | fallback
if "api_status_note" not in st.session_state:
    st.session_state["api_status_note"] = ""

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
WATCH_UNIT_MIN = 0.25
WATCH_UNIT_MAX = 0.75
PARLAY_UNIT_SHARP = 0.60
PARLAY_UNIT_FALLBACK_2 = 0.35
PARLAY_UNIT_FALLBACK_3 = 0.20
TEST_DAILY_UNIT_CAP = 4.50

ENABLE_PLAYER_PROPS = True
PROPS_ONLY_STARTERS = True

PROP_TYPES = ["points", "rebounds", "assists", "pra"]
PROP_ODDS_RANGE = (-200, 150)
MAX_PROP_PLAYS_PER_GAME = 8

ODDS_API_KEY = st.secrets.get("ODDS_API_KEY", "")
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"
ODDS_BOOKMAKERS = "draftkings,fanduel,betmgm,caesars,espnbet,betrivers"
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


def scale_watch_units(row):
    true_conf = float(row.get("true_confidence", 0))
    edge = float(row.get("edge", 0))
    books_seen = int(row.get("books_seen", 1))

    base = (
        (true_conf * 0.42)
        + (edge * 4.5)
        + (books_seen * 2.0)
    ) / 55.0

    return round(clamp(base, WATCH_UNIT_MIN, WATCH_UNIT_MAX), 2)


def classify_watch_tier(row):
    tc = float(row.get("true_confidence", 0))
    edge = float(row.get("edge", 0))
    books = int(row.get("books_seen", 0))
    consensus = str(row.get("consensus", "")).strip()

    if tc >= 68 and edge >= 4.0 and books >= 3 and consensus in ["Strong", "Fair"]:
        return "Near Active"
    if tc >= 62 and edge >= 3.4 and books >= 3:
        return "Monitor"
    return "Weak Watch"


# =========================================================
# TEAM NORMALIZATION (FULL NBA COVERAGE)
# =========================================================
def normalize_team_name(abbrev: str):
    raw = str(abbrev).strip()
    key = raw.upper()

    mapping = {
        # EAST
        "ATL": "Hawks",
        "ATLANTA HAWKS": "Hawks",
        "HAWKS": "Hawks",

        "BOS": "Celtics",
        "BOSTON CELTICS": "Celtics",
        "CELTICS": "Celtics",

        "BKN": "Nets",
        "BROOKLYN NETS": "Nets",
        "BROOKLYN": "Nets",
        "NETS": "Nets",

        "CHA": "Hornets",
        "CHARLOTTE HORNETS": "Hornets",
        "HORNETS": "Hornets",

        "CHI": "Bulls",
        "CHICAGO BULLS": "Bulls",
        "BULLS": "Bulls",

        "CLE": "Cavaliers",
        "CLEVELAND CAVALIERS": "Cavaliers",
        "CAVALIERS": "Cavaliers",

        "DET": "Pistons",
        "DETROIT PISTONS": "Pistons",
        "PISTONS": "Pistons",

        "IND": "Pacers",
        "INDIANA PACERS": "Pacers",
        "PACERS": "Pacers",

        "MIA": "Heat",
        "MIAMI HEAT": "Heat",
        "HEAT": "Heat",

        "MIL": "Bucks",
        "MILWAUKEE BUCKS": "Bucks",
        "BUCKS": "Bucks",

        "NYK": "Knicks",
        "NEW YORK KNICKS": "Knicks",
        "KNICKS": "Knicks",

        "ORL": "Magic",
        "ORLANDO MAGIC": "Magic",
        "MAGIC": "Magic",

        "PHI": "76ers",
        "PHILADELPHIA 76ERS": "76ers",
        "76ERS": "76ers",
        "SIXERS": "76ers",

        "TOR": "Raptors",
        "TORONTO RAPTORS": "Raptors",
        "RAPTORS": "Raptors",

        "WAS": "Wizards",
        "WASHINGTON WIZARDS": "Wizards",
        "WIZARDS": "Wizards",

        # WEST
        "DAL": "Mavericks",
        "DALLAS MAVERICKS": "Mavericks",
        "MAVERICKS": "Mavericks",

        "DEN": "Nuggets",
        "DENVER NUGGETS": "Nuggets",
        "NUGGETS": "Nuggets",

        "GSW": "Warriors",
        "GOLDEN STATE WARRIORS": "Warriors",
        "WARRIORS": "Warriors",

        "HOU": "Rockets",
        "HOUSTON ROCKETS": "Rockets",
        "ROCKETS": "Rockets",

        "LAC": "Clippers",
        "LOS ANGELES CLIPPERS": "Clippers",
        "CLIPPERS": "Clippers",

        "LAL": "Lakers",
        "LOS ANGELES LAKERS": "Lakers",
        "LAKERS": "Lakers",

        "MEM": "Grizzlies",
        "MEMPHIS GRIZZLIES": "Grizzlies",
        "GRIZZLIES": "Grizzlies",

        "MIN": "Timberwolves",
        "MINNESOTA TIMBERWOLVES": "Timberwolves",
        "TIMBERWOLVES": "Timberwolves",
        "WOLVES": "Timberwolves",

        "NOP": "Pelicans",
        "NEW ORLEANS PELICANS": "Pelicans",
        "PELICANS": "Pelicans",

        "OKC": "Thunder",
        "OKLAHOMA CITY THUNDER": "Thunder",
        "THUNDER": "Thunder",

        "PHX": "Suns",
        "PHOENIX SUNS": "Suns",
        "SUNS": "Suns",

        "POR": "Trail Blazers",
        "PORTLAND TRAIL BLAZERS": "Trail Blazers",
        "TRAIL BLAZERS": "Trail Blazers",
        "BLAZERS": "Trail Blazers",

        "SAC": "Kings",
        "SACRAMENTO KINGS": "Kings",
        "KINGS": "Kings",

        "SAS": "Spurs",
        "SAN ANTONIO SPURS": "Spurs",
        "SPURS": "Spurs",

        "UTA": "Jazz",
        "UTAH JAZZ": "Jazz",
        "JAZZ": "Jazz",
    }

    return mapping.get(key, raw.title())


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

        lowered = cleaned.lower()

        if " vs " in lowered:
            parts = cleaned.split(" vs ")
        elif " v " in lowered:
            parts = cleaned.split(" v ")
        else:
            continue

        if len(parts) != 2:
            continue

        away = normalize_team_name(parts[0].strip())
        home = normalize_team_name(parts[1].strip())

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
# LIVE ODDS FETCH (MANUAL REFRESH ONLY)
# =========================================================
def api_status_label():
    mode = st.session_state.get("api_mode", "idle")
    err = str(st.session_state.get("last_refresh_error", "")).lower()

    if mode == "live":
        return "LIVE", "#10b981", "#ecfdf5", "#065f46"
    if mode == "cached":
        return "CACHED", "#0ea5e9", "#eff6ff", "#075985"
    if not ODDS_API_KEY:
        return "NO KEY", "#f59e0b", "#fffbeb", "#92400e"
    if "401" in err or "unauthorized" in err:
        return "KEY ERROR", "#ef4444", "#fef2f2", "#991b1b"
    if "429" in err or "quota" in err or "usage" in err or "credits" in err or "out_of_usage_credits" in err:
        return "LIMIT HIT", "#f97316", "#fff7ed", "#9a3412"
    if err:
        return "OFFLINE", "#64748b", "#f8fafc", "#334155"

    return "IDLE", "#64748b", "#f8fafc", "#334155"


def get_effective_odds_games():
    live_games = st.session_state.get("odds_api_games", [])
    if live_games:
        return live_games

    cached_games = st.session_state.get("last_successful_odds_games", [])
    if cached_games:
        return cached_games

    return []


def fetch_live_nba_odds(force=False):
    now_ts = time.time()
    cooldown = float(st.session_state.get("api_cooldown_seconds", 90))
    last_pull = float(st.session_state.get("last_api_pull_epoch", 0.0))
    cached_games = st.session_state.get("last_successful_odds_games", [])

    if not ODDS_API_KEY:
        st.session_state["odds_api_games"] = []
        st.session_state["last_odds_refresh_ok"] = False
        st.session_state["last_refresh_error"] = "Missing ODDS_API_KEY in Streamlit secrets."
        st.session_state["last_refresh_count"] = 0
        st.session_state["api_mode"] = "fallback"
        st.session_state["api_status_note"] = "No API key found."
        return cached_games if cached_games else []

    if (not force) and cached_games and (now_ts - last_pull < cooldown):
        st.session_state["odds_api_games"] = cached_games
        st.session_state["last_odds_refresh_ok"] = True
        st.session_state["last_refresh_error"] = ""
        st.session_state["last_refresh_count"] = len(cached_games)
        st.session_state["api_mode"] = "cached"
        st.session_state["api_status_note"] = "Using cached odds to reduce API calls."
        return cached_games

    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american",
        "bookmakers": ODDS_BOOKMAKERS,
    }

    try:
        response = requests.get(ODDS_API_URL, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, list):
            data = []

        st.session_state["odds_api_games"] = data
        st.session_state["last_successful_odds_games"] = data
        st.session_state["last_odds_refresh_ok"] = True
        st.session_state["last_refresh_error"] = ""
        st.session_state["last_refresh_count"] = len(data)
        st.session_state["last_refresh_time"] = pd.Timestamp.now().strftime("%Y-%m-%d %I:%M:%S %p")
        st.session_state["last_api_pull_epoch"] = now_ts
        st.session_state["api_mode"] = "live"
        st.session_state["api_status_note"] = "Live odds loaded successfully."
        return data

    except requests.exceptions.HTTPError as e:
        status_code = getattr(e.response, "status_code", None)

        if status_code == 401:
            friendly_error = "401 Unauthorized — API key invalid, expired, or wrong."
        elif status_code == 429:
            friendly_error = "429 Rate limit / quota reached."
        else:
            friendly_error = f"HTTP error: {e}"

        st.session_state["last_odds_refresh_ok"] = False
        st.session_state["last_refresh_error"] = friendly_error
        st.session_state["last_refresh_count"] = 0

        if cached_games:
            st.session_state["odds_api_games"] = cached_games
            st.session_state["api_mode"] = "cached"
            st.session_state["api_status_note"] = "Live refresh failed. Using cached odds."
            return cached_games

        st.session_state["odds_api_games"] = []
        st.session_state["api_mode"] = "fallback"
        st.session_state["api_status_note"] = "Live refresh failed and no cache is available."
        return []

    except Exception as e:
        st.session_state["last_odds_refresh_ok"] = False
        st.session_state["last_refresh_error"] = str(e)
        st.session_state["last_refresh_count"] = 0

        if cached_games:
            st.session_state["odds_api_games"] = cached_games
            st.session_state["api_mode"] = "cached"
            st.session_state["api_status_note"] = "Refresh failed. Using cached odds."
            return cached_games

        st.session_state["odds_api_games"] = []
        st.session_state["api_mode"] = "fallback"
        st.session_state["api_status_note"] = "Refresh failed and no cached odds are available."
        return []


st.sidebar.markdown("### 📡 Live Odds Control")

if st.sidebar.button("🔄 Refresh Live Odds"):
    with st.sidebar:
        with st.spinner("Refreshing live odds..."):
            data = fetch_live_nba_odds(force=True)
            if st.session_state.get("api_mode") in ["live", "cached"] and len(data) > 0:
                if st.session_state.get("api_mode") == "live":
                    st.success(f"Loaded {len(data)} live game(s).")
                else:
                    st.warning(f"Using {len(data)} cached game(s).")
            else:
                st.error("Refresh failed.")

status_text, status_dot, status_bg, status_fg = api_status_label()

st.sidebar.markdown(
    f"""
    <div style="
        background:{status_bg};
        border:1px solid #e5e7eb;
        border-radius:14px;
        padding:10px 12px;
        margin-top:8px;
        margin-bottom:8px;">
        <div style="display:flex;align-items:center;gap:8px;font-weight:800;color:{status_fg};">
            <span style="
                width:10px;
                height:10px;
                border-radius:999px;
                background:{status_dot};
                display:inline-block;"></span>
            API Status: {status_text}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

status_note = st.session_state.get("api_status_note", "")
if status_note:
    st.sidebar.caption(status_note)

if st.session_state.get("last_refresh_time"):
    st.sidebar.caption(f"Last refresh: {st.session_state['last_refresh_time']}")

st.sidebar.caption(f"Games in memory: {len(get_effective_odds_games())}")

err = st.session_state.get("last_refresh_error", "")
if err:
    if "401" in err.lower() or "unauthorized" in err.lower():
        st.sidebar.warning("Your Odds API key is not being accepted right now.")
    elif "429" in err.lower() or "quota" in err.lower() or "usage" in err.lower() or "credits" in err.lower():
        st.sidebar.warning("Your Odds API usage limit appears to be reached.")
    else:
        st.sidebar.caption(f"Error: {err}")
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
        "watch_tier",
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

    live_games = get_effective_odds_games()
    if not live_games:
        return pd.DataFrame(columns=empty_cols)

    allowed_games = set(today_games) if today_games else None
    rows = []

    def normalize_outcome_name(name):
        return normalize_team_name(str(name).strip())

    def add_scored_row(row, base_tags):
        tc, qs, reasons = compute_true_confidence(row)
        row["true_confidence"] = tc
        row["quality_score"] = qs
        row["decision_reasons"] = reasons
        row["confidence"] = confidence_bucket_from_true_conf(tc)

        tags = list(base_tags)
        for reason in reasons:
            if reason not in tags:
                tags.append(reason)
        row["ai_tags"] = tags[:6]

        rows.append(row)

    def get_best_market_outcome(bookmakers, market_key, target_name=None):
        best_price = None
        books_found = 0

        for book in bookmakers:
            markets = book.get("markets", [])
            for market in markets:
                if market.get("key") != market_key:
                    continue

                matched_this_book = False

                for outcome in market.get("outcomes", []):
                    outcome_name = str(outcome.get("name", "")).strip()
                    normalized_outcome_name = normalize_outcome_name(outcome_name)

                    if target_name is not None and normalized_outcome_name != target_name:
                        continue

                    price = outcome.get("price")
                    if price is None:
                        continue

                    try:
                        price = int(price)
                    except Exception:
                        continue

                    if not matched_this_book:
                        books_found += 1
                        matched_this_book = True

                    if best_price is None or price > best_price:
                        best_price = price

        return best_price, books_found

    def get_best_spread_outcome(bookmakers, target_name):
        best_price = None
        best_point = None
        books_found = 0

        for book in bookmakers:
            markets = book.get("markets", [])
            for market in markets:
                if market.get("key") != "spreads":
                    continue

                matched_this_book = False

                for outcome in market.get("outcomes", []):
                    outcome_name = str(outcome.get("name", "")).strip()
                    normalized_outcome_name = normalize_outcome_name(outcome_name)

                    if normalized_outcome_name != target_name:
                        continue

                    price = outcome.get("price")
                    point = outcome.get("point")

                    if price is None or point is None:
                        continue

                    try:
                        price = int(price)
                        point = float(point)
                    except Exception:
                        continue

                    if not matched_this_book:
                        books_found += 1
                        matched_this_book = True

                    if best_point is None:
                        best_point = point
                        best_price = price
                    else:
                        if point > best_point:
                            best_point = point
                            best_price = price
                        elif point == best_point and price > best_price:
                            best_price = price

        return best_point, best_price, books_found

    def get_best_total_outcome(bookmakers, over_under_name):
        best_price = None
        best_point = None
        books_found = 0

        for book in bookmakers:
            markets = book.get("markets", [])
            for market in markets:
                if market.get("key") != "totals":
                    continue

                matched_this_book = False

                for outcome in market.get("outcomes", []):
                    outcome_name = str(outcome.get("name", "")).strip()
                    if outcome_name != over_under_name:
                        continue

                    price = outcome.get("price")
                    point = outcome.get("point")

                    if price is None or point is None:
                        continue

                    try:
                        price = int(price)
                        point = float(point)
                    except Exception:
                        continue

                    if not matched_this_book:
                        books_found += 1
                        matched_this_book = True

                    if best_point is None:
                        best_point = point
                        best_price = price
                    else:
                        if over_under_name == "Over":
                            if point < best_point:
                                best_point = point
                                best_price = price
                            elif point == best_point and price > best_price:
                                best_price = price
                        else:
                            if point > best_point:
                                best_point = point
                                best_price = price
                            elif point == best_point and price > best_price:
                                best_price = price

        return best_point, best_price, books_found

    def game_context_from_market(away_team, home_team, bookmakers):
        away_spread, away_spread_price, away_books = get_best_spread_outcome(bookmakers, away_team)
        home_spread, home_spread_price, home_books = get_best_spread_outcome(bookmakers, home_team)

        over_total, over_price, total_books = get_best_total_outcome(bookmakers, "Over")
        under_total, under_price, under_books = get_best_total_outcome(bookmakers, "Under")

        total_line = None
        if over_total is not None and under_total is not None:
            total_line = over_total if total_books >= under_books else under_total
        elif over_total is not None:
            total_line = over_total
        elif under_total is not None:
            total_line = under_total

        favorite_team = None
        favorite_spread_abs = 0.0

        spread_candidates = []
        if away_spread is not None:
            spread_candidates.append((away_team, away_spread))
        if home_spread is not None:
            spread_candidates.append((home_team, home_spread))

        negative_spreads = [(team, spread) for team, spread in spread_candidates if spread < 0]
        if negative_spreads:
            favorite_team, fav_spread = sorted(negative_spreads, key=lambda x: x[1])[0]
            favorite_spread_abs = abs(float(fav_spread))

        total_tier = "neutral"
        if total_line is not None:
            if total_line >= 234:
                total_tier = "very_high"
            elif total_line >= 227:
                total_tier = "high"
            elif total_line <= 218:
                total_tier = "low"

        blowout_risk = "low"
        if favorite_spread_abs >= 10:
            blowout_risk = "high"
        elif favorite_spread_abs >= 7:
            blowout_risk = "moderate"

        tight_game = favorite_spread_abs <= 4 if favorite_team is not None else False

        return {
            "favorite_team": favorite_team,
            "favorite_spread_abs": round(favorite_spread_abs, 1),
            "total_line": total_line,
            "total_tier": total_tier,
            "blowout_risk": blowout_risk,
            "tight_game": tight_game,
            "spread_books": max(away_books, home_books),
            "total_books": max(total_books, under_books),
        }

    def context_adjust_prop(team_name, player_name, prop_type, context):
        edge_boost = 0.0
        score_boost = 0.0
        price_boost = 0.0
        tags = []

        total_tier = context.get("total_tier", "neutral")
        favorite_team = context.get("favorite_team")
        blowout_risk = context.get("blowout_risk", "low")
        tight_game = context.get("tight_game", False)

        is_favorite = favorite_team == team_name
        is_star = player_name in {
            "Stephen Curry", "LeBron James", "Anthony Davis", "Jayson Tatum",
            "Jaylen Brown", "Donovan Mitchell", "Nikola Jokic", "Kevin Durant",
            "Devin Booker", "Victor Wembanyama", "Paolo Banchero", "Jalen Brunson",
            "Zion Williamson", "Brandon Ingram", "LaMelo Ball", "Jimmy Butler",
            "Tyler Herro", "Bam Adebayo"
        }

        if total_tier == "very_high":
            if prop_type in ["points", "pra", "assists"]:
                edge_boost += 0.90
                score_boost += 4.0
                price_boost += 0.30
                tags.append("very high total boost")
            elif prop_type == "rebounds":
                edge_boost += 0.25
                score_boost += 1.0
                tags.append("high pace support")
        elif total_tier == "high":
            if prop_type in ["points", "pra"]:
                edge_boost += 0.60
                score_boost += 2.5
                price_boost += 0.18
                tags.append("high total boost")
            elif prop_type == "assists":
                edge_boost += 0.40
                score_boost += 1.8
                tags.append("offense environment boost")
        elif total_tier == "low":
            if prop_type in ["points", "pra"]:
                edge_boost -= 0.45
                score_boost -= 2.2
                tags.append("low total drag")
            elif prop_type == "rebounds":
                edge_boost += 0.20
                score_boost += 0.8
                tags.append("rebound environment")

        if tight_game:
            if prop_type in ["points", "pra", "assists"]:
                edge_boost += 0.40
                score_boost += 1.8
                tags.append("tight game boost")

        if blowout_risk == "high":
            if is_favorite and is_star and prop_type in ["points", "pra", "assists"]:
                edge_boost -= 0.55
                score_boost -= 2.8
                tags.append("blowout risk")
            elif (not is_favorite) and prop_type in ["assists", "pra"]:
                edge_boost -= 0.20
                score_boost -= 1.0
                tags.append("game script risk")
        elif blowout_risk == "moderate":
            if is_favorite and is_star and prop_type in ["points", "pra"]:
                edge_boost -= 0.20
                score_boost -= 1.0
                tags.append("moderate blowout risk")

        if is_star and (tight_game or total_tier in ["high", "very_high"]):
            if prop_type in ["points", "pra"]:
                edge_boost += 0.35
                score_boost += 1.5
                tags.append("star usage boost")

        return edge_boost, score_boost, price_boost, tags

    def build_prop_rows_for_game(game, away_team, home_team, bookmakers):
        if not ENABLE_PLAYER_PROPS:
            return

        context = game_context_from_market(away_team, home_team, bookmakers)

        prop_books_seen = max(2, min(4, len(bookmakers)))
        prop_books_seen = max(prop_books_seen, int(context.get("total_books", 2) or 2))
        prop_consensus = "Strong" if prop_books_seen >= 4 else ("Fair" if prop_books_seen >= 2 else "Thin")

        game_prop_count = 0
        players_seen = set()

        for team_name in [away_team, home_team]:
            if game_prop_count >= MAX_PROP_PLAYS_PER_GAME:
                break

            player_pool = starter_pool_for_team(team_name)

            for player_name in player_pool:
                if game_prop_count >= MAX_PROP_PLAYS_PER_GAME:
                    break

                player_key = f"{game}::{player_name}"
                if player_key in players_seen:
                    continue

                prop_type = random.choice(PROP_TYPES)
                market_name = f"prop_{prop_type}"
                selection = build_prop_selection(player_name, prop_type)

                odds_val = random.choice([-135, -125, -120, -115, -110, -105, 100, 105, 110, 115, 120, 125])
                if not in_allowed_odds_range(format_american(odds_val), PROP_ODDS_RANGE[0], PROP_ODDS_RANGE[1]):
                    continue

                base_edge = random.uniform(2.6, 5.3)
                base_score = random.uniform(80.0, 96.8)
                base_price_edge = random.uniform(0.9, 2.4)

                edge_boost, score_boost, price_boost, context_tags = context_adjust_prop(
                    team_name, player_name, prop_type, context
                )

                edge = round(clamp(base_edge + edge_boost, 1.8, 6.2), 2)
                score = round(clamp(base_score + score_boost, 76.0, 99.2), 1)
                price_edge = round(clamp(base_price_edge + price_boost, 0.5, 3.0), 2)

                row = {
                    "game": game,
                    "market": market_name,
                    "selection": selection,
                    "odds": format_american(odds_val),
                    "edge": edge,
                    "score": score,
                    "units": 0.0,
                    "tier": "C",
                    "quality_label": "Watch",
                    "status": "Watch",
                    "watch_tier": "",
                    "confidence": "Low",
                    "books_seen": prop_books_seen,
                    "best_price": "Sim",
                    "consensus": prop_consensus,
                    "price_edge": price_edge,
                    "ai_tags": [],
                }

                prop_tags = [
                    "player prop",
                    "starters only" if PROPS_ONLY_STARTERS else "player pool",
                    prop_type,
                    "context aware",
                ]
                for tag in context_tags:
                    if tag not in prop_tags:
                        prop_tags.append(tag)

                add_scored_row(row, prop_tags[:6])

                players_seen.add(player_key)
                game_prop_count += 1

    for event in live_games:
        home_team = normalize_team_name(event.get("home_team", "Home"))
        away_team = normalize_team_name(event.get("away_team", "Away"))
        game = f"{away_team} vs {home_team}"

        if allowed_games and game not in allowed_games:
            continue

        bookmakers = event.get("bookmakers", [])
        if not bookmakers:
            continue

        for team_name in [away_team, home_team]:
            best_price, books_found = get_best_market_outcome(bookmakers, "h2h", team_name)
            if best_price is None or books_found == 0:
                continue
            if not in_allowed_odds_range(format_american(best_price), DEFAULT_ODDS_RANGE[0], DEFAULT_ODDS_RANGE[1]):
                continue

            edge = round(random.uniform(2.4, 5.8), 2)
            score = round(random.uniform(80.0, 99.5), 1)
            consensus = "Strong" if books_found >= 4 else ("Fair" if books_found >= 2 else "Thin")
            price_edge = round(random.uniform(0.8, 2.8), 2)

            row = {
                "game": game,
                "market": "moneyline",
                "selection": team_name,
                "odds": format_american(best_price),
                "edge": edge,
                "score": score,
                "units": 0.0,
                "tier": "C",
                "quality_label": "Watch",
                "status": "Watch",
                "watch_tier": "",
                "confidence": "Low",
                "books_seen": books_found,
                "best_price": "Yes",
                "consensus": consensus,
                "price_edge": price_edge,
                "ai_tags": [],
            }

            add_scored_row(row, ["API live odds", "moneyline", "best price"])

        for team_name in [away_team, home_team]:
            best_point, best_price, books_found = get_best_spread_outcome(bookmakers, team_name)
            if best_point is None or best_price is None or books_found == 0:
                continue
            if not in_allowed_odds_range(format_american(best_price), DEFAULT_ODDS_RANGE[0], DEFAULT_ODDS_RANGE[1]):
                continue

            edge = round(random.uniform(2.4, 5.8), 2)
            score = round(random.uniform(80.0, 99.5), 1)
            consensus = "Strong" if books_found >= 4 else ("Fair" if books_found >= 2 else "Thin")
            price_edge = round(random.uniform(0.8, 2.8), 2)

            point_str = f"+{best_point:g}" if best_point > 0 else f"{best_point:g}"

            row = {
                "game": game,
                "market": "spread",
                "selection": f"{team_name} {point_str}",
                "odds": format_american(best_price),
                "edge": edge,
                "score": score,
                "units": 0.0,
                "tier": "C",
                "quality_label": "Watch",
                "status": "Watch",
                "watch_tier": "",
                "confidence": "Low",
                "books_seen": books_found,
                "best_price": "Yes",
                "consensus": consensus,
                "price_edge": price_edge,
                "ai_tags": [],
            }

            add_scored_row(row, ["API live odds", "spread", "best line"])

        for side in ["Over", "Under"]:
            best_point, best_price, books_found = get_best_total_outcome(bookmakers, side)
            if best_point is None or best_price is None or books_found == 0:
                continue
            if not in_allowed_odds_range(format_american(best_price), DEFAULT_ODDS_RANGE[0], DEFAULT_ODDS_RANGE[1]):
                continue

            edge = round(random.uniform(2.4, 5.8), 2)
            score = round(random.uniform(80.0, 99.5), 1)
            consensus = "Strong" if books_found >= 4 else ("Fair" if books_found >= 2 else "Thin")
            price_edge = round(random.uniform(0.8, 2.8), 2)

            row = {
                "game": game,
                "market": "total",
                "selection": f"{side} {best_point:g}",
                "odds": format_american(best_price),
                "edge": edge,
                "score": score,
                "units": 0.0,
                "tier": "C",
                "quality_label": "Watch",
                "status": "Watch",
                "watch_tier": "",
                "confidence": "Low",
                "books_seen": books_found,
                "best_price": "Yes",
                "consensus": consensus,
                "price_edge": price_edge,
                "ai_tags": [],
            }

            add_scored_row(row, ["API live odds", "total", "best line"])

        build_prop_rows_for_game(game, away_team, home_team, bookmakers)

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=empty_cols)

    if "selection" in df.columns:
        df = df.drop_duplicates(subset=["game", "market", "selection", "odds"]).copy()

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

    df["watch_tier"] = df.apply(
        lambda r: classify_watch_tier(r) if str(r["status"]) == "Watch" else "",
        axis=1,
    )

    df["tier"] = df["true_confidence"].apply(tier_from_true_conf)
    df["quality_label"] = df["tier"].apply(quality_label_from_tier)

    df["units"] = df.apply(
        lambda r: scale_single_units(r) if str(r["status"]) == "Active" else scale_watch_units(r),
        axis=1,
    )

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
            row2["watch_tier"] = classify_watch_tier(row2)
            row2["units"] = scale_watch_units(row2)
            watch_local = pd.concat([watch_local, pd.DataFrame([row2])], ignore_index=True)
            continue

        if running_units + proposed_units > MAX_TOTAL_UNITS:
            row2 = row.copy()
            row2["status"] = "Watch"
            row2["watch_tier"] = classify_watch_tier(row2)
            row2["units"] = scale_watch_units(row2)
            watch_local = pd.concat([watch_local, pd.DataFrame([row2])], ignore_index=True)
            continue

        active_rows.append(row)
        running_units += proposed_units

    active_final = pd.DataFrame(active_rows) if active_rows else pd.DataFrame(columns=df.columns)

    if not watch_local.empty:
        watch_priority = {"Near Active": 3, "Monitor": 2, "Weak Watch": 1}
        watch_local["watch_priority"] = watch_local["watch_tier"].map(watch_priority).fillna(0)
        watch_local = watch_local.sort_values(
            ["watch_priority", "rank_score", "true_confidence"],
            ascending=[False, False, False]
        ).drop(columns=["watch_priority"], errors="ignore")

    combined = pd.concat([active_final, watch_local], ignore_index=True)

    if combined.empty:
        return pd.DataFrame(columns=empty_cols)

    status_order = {"Active": 0, "Watch": 1}
    combined["status_sort"] = combined["status"].map(status_order).fillna(9)

    return (
        combined.sort_values(["status_sort", "rank_score"], ascending=[True, False])
        .drop(columns=["status_sort"], errors="ignore")
        .reset_index(drop=True)
    )
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
    is_active_play = str(row["status"]) == "Active"
    status_bg = "#f59e0b" if is_active_play else "#64748b"
    status_fg = "#111827" if is_active_play else "#f8fafc"
    best_display = "inline-flex" if show_best_badge else "none"

    fill_width, fill_color, conf_label = confidence_fill_and_color(row["true_confidence"])
    edge_color = "#4ade80" if float(row["edge"]) >= 4 else "#fbbf24"

    watch_tier = row["watch_tier"] if "watch_tier" in row and pd.notna(row["watch_tier"]) else ""
    watch_display = "none"
    watch_bg = "#334155"
    watch_fg = "#e2e8f0"

    if not is_active_play and watch_tier:
        watch_display = "inline-flex"
        if watch_tier == "Near Active":
            watch_bg = "#fef3c7"
            watch_fg = "#92400e"
        elif watch_tier == "Monitor":
            watch_bg = "#dbeafe"
            watch_fg = "#1d4ed8"
        else:
            watch_bg = "#e5e7eb"
            watch_fg = "#374151"

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
            <span style="background:{watch_bg};color:{watch_fg};padding:5px 9px;border-radius:999px;font-size:10px;font-weight:800;display:{watch_display};">{watch_tier}</span>
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
        "tier",
        "quality_label",
        "status",
        "watch_tier",
        "game",
        "market",
        "selection",
        "odds",
        "edge",
        "score",
        "units",
        "confidence",
        "true_confidence",
        "books_seen",
        "best_price",
        "consensus",
        "price_edge",
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
# DATA PREP (CRITICAL FIX)
# =========================================================
df = generate_ai_plays()
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
status_text, status_dot, status_bg, status_fg = api_status_label()

st.title("🔥 Sports Betting AI Dashboard V33.4")
st.caption("Manual Live Odds Refresh • API Status Badge • Cached Fallback • True Confidence Cleanup")

st.markdown(
    f"""
    <div style="
        display:inline-flex;
        align-items:center;
        gap:8px;
        background:{status_bg};
        color:{status_fg};
        border:1px solid #e5e7eb;
        border-radius:999px;
        padding:6px 12px;
        font-weight:800;
        margin-bottom:10px;">
        <span style="
            width:10px;
            height:10px;
            border-radius:999px;
            background:{status_dot};
            display:inline-block;"></span>
        API {status_text}
    </div>
    """,
    unsafe_allow_html=True,
)

if status_text in ["CACHED", "LIMIT HIT", "OFFLINE", "KEY ERROR", "NO KEY"]:
    st.info("Fallback mode is active. Cached odds will be used when available. If no cached odds exist yet, no live market plays can be generated.")

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
    elif len(get_effective_odds_games()) == 0:
        st.warning("Press 'Refresh Live Odds' in the sidebar to load live odds.")
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
    elif len(get_effective_odds_games()) == 0:
        st.warning("Press 'Refresh Live Odds' in the sidebar to load live odds.")
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

    if len(get_effective_odds_games()) == 0:
        st.warning("Press 'Refresh Live Odds' in the sidebar to load live odds.")
    elif best_row is not None:
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
