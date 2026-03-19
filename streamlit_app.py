
# ============================================================
# SPORTS AI BETTING DASHBOARD — DEV MODE V9 BET TRACKER
# ============================================================
# REAL WORKING FILE
#
# INCLUDED FEATURES
# - DEV MODE sample odds and props
# - AUTO PROJECTIONS V1
# - SHARP MODE V1
# - SUPER SHARP V1
# - TIER SYSTEM V1
# - LINE SHOPPING V1
# - STEAM / LINE MOVEMENT V1
# - BET SIZING V1
# - BET TRACKER V1
# - Best Bets board
# - Prop Sections
# - Arbitrage tab
# - Injuries / caution flags
# - Projection CSV override
# - Clear step markers throughout
# ============================================================

import math
from datetime import datetime, timedelta
from io import BytesIO

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Sports AI Betting Dashboard DEV MODE V9", page_icon="🏀", layout="wide")
st.title("🏀 Sports AI Betting Dashboard — DEV MODE V9")
st.caption("BET TRACKER V1 • Picks + steam + sizing + tracked results")

# ============================================================
# STEP 1 — CORE SETTINGS
# ============================================================

SPORTS = ["NBA", "WNBA", "NHL", "MLB", "NFL"]
BOOKS = ["DraftKings", "FanDuel", "BetMGM", "Caesars", "ESPN BET", "Fanatics"]

NBA_PLAYERS = [
    ("Jalen Brunson", "Knicks"),
    ("Jayson Tatum", "Celtics"),
    ("Giannis Antetokounmpo", "Bucks"),
    ("Jimmy Butler", "Heat"),
    ("Donovan Mitchell", "Cavaliers"),
    ("Tyrese Haliburton", "Pacers"),
    ("Tyrese Maxey", "76ers"),
    ("Paolo Banchero", "Magic"),
    ("Stephen Curry", "Warriors"),
    ("LeBron James", "Lakers"),
]

PROP_TYPES_BY_SPORT = {
    "NBA": ["points", "rebounds", "assists", "3pt_made", "blocks", "steals", "turnovers", "pra", "pr", "pa", "ra"],
}

TRACKER_COLUMNS = [
    "bet_id", "added_at", "sport", "player", "opponent", "book", "game_segment",
    "prop_type", "side", "line", "odds", "projection", "edge", "hit_probability",
    "ev_edge", "edge_score", "play_tier", "steam_flag", "bet_timing",
    "bet_size_units", "bet_size_label", "result", "profit_units", "notes"
]

DEFAULT_PROPS_COLS = [
    "sport", "event_id", "player", "team", "opponent", "is_starter", "starter_status",
    "starter_confirmed", "prop_type", "line", "projection", "minutes_projection",
    "recent_avg", "last_5_games", "pace_factor", "matchup_factor", "odds",
    "game_segment", "book", "recommended_side_from_book", "source_time",
    "injury_status", "injury_note", "proj_edge", "proj_edge_abs", "recommended_side",
    "hit_prob_over", "hit_prob_under", "hit_probability", "book_implied_prob",
    "model_fair_odds", "expected_value_edge", "edge_score", "bet_grade",
    "confidence_warning", "confidence_status", "odds_move", "play_tier", "tier_reason",
    "best_book", "best_line", "best_odds", "line_edge_diff", "tier_improved",
    "best_play_tier", "best_tier_reason", "line_move", "odds_move_signal",
    "steam_flag", "bet_timing", "movement_summary", "bet_size_units", "bet_size_label",
    "kelly_fraction", "bet_size_reason"
]

PLAYER_PROFILE = {
    "Jalen Brunson": {"points": 1.10, "assists": 1.12, "rebounds": 0.95, "3pt_made": 1.08, "turnovers": 1.02},
    "Jayson Tatum": {"points": 1.08, "rebounds": 1.08, "assists": 0.95, "3pt_made": 1.12, "blocks": 1.05},
    "Giannis Antetokounmpo": {"points": 1.14, "rebounds": 1.15, "assists": 1.00, "3pt_made": 0.70, "pra": 1.12},
    "Jimmy Butler": {"points": 0.96, "assists": 1.02, "steals": 1.12, "3pt_made": 0.82},
    "Donovan Mitchell": {"points": 1.09, "3pt_made": 1.15, "assists": 0.94, "turnovers": 1.05},
    "Tyrese Haliburton": {"assists": 1.20, "points": 0.97, "3pt_made": 1.00, "turnovers": 1.06, "pra": 1.10},
    "Tyrese Maxey": {"points": 1.08, "3pt_made": 1.10, "assists": 0.96},
    "Paolo Banchero": {"points": 1.04, "rebounds": 1.05, "assists": 1.00, "turnovers": 1.03},
    "Stephen Curry": {"points": 1.12, "3pt_made": 1.22, "assists": 0.92, "turnovers": 1.04, "pr": 1.08},
    "LeBron James": {"points": 1.02, "rebounds": 1.03, "assists": 1.14, "3pt_made": 0.96, "pra": 1.08},
}

TEAM_MATCHUP = {
    "Knicks": {"pace": 0.99, "matchup": 1.02},
    "Celtics": {"pace": 1.03, "matchup": 1.01},
    "Bucks": {"pace": 1.02, "matchup": 1.00},
    "Heat": {"pace": 0.96, "matchup": 0.97},
    "Cavaliers": {"pace": 0.98, "matchup": 1.00},
    "Pacers": {"pace": 1.06, "matchup": 1.07},
    "76ers": {"pace": 0.99, "matchup": 1.01},
    "Magic": {"pace": 0.97, "matchup": 0.98},
    "Warriors": {"pace": 1.04, "matchup": 1.05},
    "Lakers": {"pace": 1.01, "matchup": 1.02},
}

# ============================================================
# STEP 2 — SHARP / SUPER SHARP SETTINGS
# ============================================================

SHARP_MODE = True
SUPER_SHARP_MODE = True

MAX_EDGE_CAP = {
    "points": 5.5, "pra": 6.0, "assists": 4.0, "rebounds": 4.5, "3pt_made": 2.0,
    "turnovers": 2.5, "blocks": 1.8, "steals": 1.8, "pr": 5.0, "pa": 5.0, "ra": 4.0,
}
EDGE_SOFT_CAP = {
    "points": 4.5, "pra": 5.0, "assists": 3.5, "rebounds": 4.0, "3pt_made": 1.8,
    "turnovers": 2.0, "blocks": 1.4, "steals": 1.4, "pr": 4.5, "pa": 4.5, "ra": 3.5,
}
SUPER_SHARP_HIT_CLAMP = {"min": 0.07, "max": 0.74}

# ============================================================
# STEP 3 — HELPERS
# ============================================================

def normalize_text(x):
    if pd.isna(x):
        return ""
    return str(x).strip().lower()

def safe_float(x):
    try:
        if pd.isna(x):
            return np.nan
        return float(x)
    except Exception:
        return np.nan

def current_ts_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def add_missing_cols(df, defaults):
    for col, default in defaults.items():
        if col not in df.columns:
            df[col] = default
    return df

def american_to_decimal(odds):
    try:
        odds = float(odds)
        return 1 + (odds / 100) if odds > 0 else 1 + (100 / abs(odds))
    except Exception:
        return np.nan

def implied_prob_american(odds):
    try:
        odds = float(odds)
        return 100 / (odds + 100) if odds > 0 else abs(odds) / (abs(odds) + 100)
    except Exception:
        return np.nan

def profit_units_from_result(result, odds, stake_units):
    odds = safe_float(odds)
    stake_units = safe_float(stake_units)
    if pd.isna(odds) or pd.isna(stake_units):
        return np.nan
    if result == "Win":
        return stake_units * (odds / 100.0) if odds > 0 else stake_units * (100.0 / abs(odds))
    if result == "Loss":
        return -stake_units
    if result == "Push":
        return 0.0
    return np.nan

def prob_to_american(prob):
    try:
        prob = float(prob)
        if prob <= 0 or prob >= 1:
            return np.nan
        return int(round(-(prob / (1 - prob)) * 100)) if prob >= 0.5 else int(round(((1 - prob) / prob) * 100))
    except Exception:
        return np.nan

def edge_bucket(score):
    if score >= 86:
        return "🟢 A"
    if score >= 76:
        return "🟢 B"
    if score >= 66:
        return "🟡 C"
    return "🔴 Pass"

def tier_badge(tier):
    mapping = {"Tier 1": "🟢 Tier 1", "Tier 2": "🟡 Tier 2", "Tier 3": "⚪ Tier 3"}
    return mapping.get(tier, tier)

def tier_rank(tier):
    return {"Tier 1": 3, "Tier 2": 2, "Tier 3": 1}.get(str(tier), 0)

def init_tracker_state():
    if "bet_tracker_df" not in st.session_state:
        st.session_state["bet_tracker_df"] = pd.DataFrame(columns=TRACKER_COLUMNS)

# ============================================================
# STEP 4 — TIER SYSTEM V1
# ============================================================

def classify_play_tier(row):
    score = safe_float(row.get("edge_score"))
    hitp = safe_float(row.get("hit_probability")) * 100
    ev = safe_float(row.get("expected_value_edge"))
    conf = str(row.get("confidence_status", ""))
    odds = safe_float(row.get("odds"))
    edge = safe_float(row.get("proj_edge_abs"))

    if conf != "✅ Clear":
        return "Tier 3", "Non-clear confidence"
    if score >= 88 and hitp >= 66 and ev >= 8 and edge >= 2.0 and odds >= -150:
        return "Tier 1", "Core play profile"
    if score >= 78 and hitp >= 60 and ev >= 4 and edge >= 1.2:
        return "Tier 2", "Strong secondary play"
    return "Tier 3", "Watchlist / lower conviction"

# ============================================================
# STEP 5 — SAMPLE DATA GENERATORS
# ============================================================

def make_sample_odds_df():
    rows = []
    games = [
        ("NBA", "nba_1", "Knicks", "Celtics"),
        ("NBA", "nba_2", "Bucks", "Heat"),
        ("NBA", "nba_3", "Warriors", "Lakers"),
    ]
    now = datetime.now()
    for idx, (sport, event_id, away, home) in enumerate(games):
        for book_i, book in enumerate(BOOKS[:4]):
            ml_home = [-125, -130, -122, -128][book_i]
            ml_away = [110, 115, 108, 112][book_i]
            spread = [-2.5, -3.0, -2.0, -2.5][book_i]
            total = [228.5, 229.5, 227.5, 228.0][book_i]
            rows += [
                {"sport": sport, "event_id": event_id, "team_a": away, "team_b": home, "book": book, "market": "moneyline", "point": np.nan, "total": np.nan, "selection": away, "odds": ml_away, "commence_time": (now + timedelta(hours=idx + 2)).isoformat(), "book_last_update": current_ts_str()},
                {"sport": sport, "event_id": event_id, "team_a": away, "team_b": home, "book": book, "market": "moneyline", "point": np.nan, "total": np.nan, "selection": home, "odds": ml_home, "commence_time": (now + timedelta(hours=idx + 2)).isoformat(), "book_last_update": current_ts_str()},
                {"sport": sport, "event_id": event_id, "team_a": away, "team_b": home, "book": book, "market": "spreads", "point": spread, "total": np.nan, "selection": home, "odds": -110, "commence_time": (now + timedelta(hours=idx + 2)).isoformat(), "book_last_update": current_ts_str()},
                {"sport": sport, "event_id": event_id, "team_a": away, "team_b": home, "book": book, "market": "spreads", "point": -spread, "total": np.nan, "selection": away, "odds": -110, "commence_time": (now + timedelta(hours=idx + 2)).isoformat(), "book_last_update": current_ts_str()},
                {"sport": sport, "event_id": event_id, "team_a": away, "team_b": home, "book": book, "market": "totals", "point": np.nan, "total": total, "selection": "Over", "odds": -110, "commence_time": (now + timedelta(hours=idx + 2)).isoformat(), "book_last_update": current_ts_str()},
                {"sport": sport, "event_id": event_id, "team_a": away, "team_b": home, "book": book, "market": "totals", "point": np.nan, "total": total, "selection": "Under", "odds": -110, "commence_time": (now + timedelta(hours=idx + 2)).isoformat(), "book_last_update": current_ts_str()},
            ]
    out = pd.DataFrame(rows)
    out["dec_odds"] = out["odds"].apply(american_to_decimal)
    out["imp_prob"] = out["odds"].apply(implied_prob_american)
    return out

def make_sample_props_df():
    rows = []
    event_map = {
        "Knicks": ("nba_1", "Knicks vs Celtics"),
        "Celtics": ("nba_1", "Knicks vs Celtics"),
        "Bucks": ("nba_2", "Bucks vs Heat"),
        "Heat": ("nba_2", "Bucks vs Heat"),
        "Warriors": ("nba_3", "Warriors vs Lakers"),
        "Lakers": ("nba_3", "Warriors vs Lakers"),
        "Cavaliers": ("nba_4", "Cavaliers vs Pacers"),
        "Pacers": ("nba_4", "Cavaliers vs Pacers"),
        "76ers": ("nba_5", "76ers vs Magic"),
        "Magic": ("nba_5", "76ers vs Magic"),
    }
    stat_bases = {
        "points": 26.5, "rebounds": 6.5, "assists": 5.5, "3pt_made": 2.5,
        "blocks": 0.5, "steals": 1.0, "turnovers": 2.5, "pra": 38.5,
        "pr": 32.5, "pa": 31.5, "ra": 12.5
    }
    for player, team in NBA_PLAYERS:
        event_id, opponent = event_map[team]
        for prop_type in PROP_TYPES_BY_SPORT["NBA"]:
            line_base = stat_bases.get(prop_type, 10.5)
            for book_idx, book in enumerate(BOOKS[:3]):
                base_line = round(line_base + (-0.5 + book_idx * 0.5), 1)
                if book == "FanDuel" and prop_type in ["points", "pra", "assists"]:
                    base_line += 0.5
                if book == "BetMGM" and prop_type in ["3pt_made", "rebounds", "pr"]:
                    base_line -= 0.5
                odds = [-115, -110, 100][book_idx]
                if book == "FanDuel" and prop_type in ["points", "3pt_made"]:
                    odds = -105
                if book == "BetMGM" and prop_type in ["pra", "assists"]:
                    odds = 105
                rows.append({
                    "sport": "NBA", "event_id": event_id, "player": player, "team": team, "opponent": opponent,
                    "is_starter": 1, "starter_status": "confirmed", "starter_confirmed": 1, "prop_type": prop_type,
                    "line": base_line, "projection": np.nan, "minutes_projection": np.nan, "recent_avg": np.nan,
                    "last_5_games": 5, "pace_factor": 1.00, "matchup_factor": 1.00, "odds": odds,
                    "game_segment": "full_game", "book": book, "recommended_side_from_book": "Over",
                    "source_time": current_ts_str(), "injury_status": "available", "injury_note": "",
                })
        rows.append({
            "sport": "NBA", "event_id": event_id, "player": player, "team": team, "opponent": opponent,
            "is_starter": 1, "starter_status": "confirmed", "starter_confirmed": 1, "prop_type": "points",
            "line": 7.5, "projection": np.nan, "minutes_projection": np.nan, "recent_avg": np.nan,
            "last_5_games": 5, "pace_factor": 1.00, "matchup_factor": 1.00, "odds": -110,
            "game_segment": "1q", "book": "DraftKings", "recommended_side_from_book": "Over",
            "source_time": current_ts_str(), "injury_status": "available", "injury_note": "",
        })
    return pd.DataFrame(rows)

def make_sample_injuries_df():
    rows = [
        ["NBA", "Knicks", "Jalen Brunson", "available", "confirmed", "", current_ts_str()],
        ["NBA", "Heat", "Jimmy Butler", "questionable", "expected", "knee", current_ts_str()],
        ["NBA", "Warriors", "Stephen Curry", "available", "confirmed", "", current_ts_str()],
    ]
    return pd.DataFrame(rows, columns=["sport", "team", "player", "injury_status", "starter_status", "injury_note", "source_time"])

def sample_full_props_projection_template():
    rows = [
        ["NBA", "Jalen Brunson", "points", "full_game", 30.4, 36, 31.1, 1.04, 1.02, "Knicks"],
        ["NBA", "Jalen Brunson", "assists", "full_game", 7.8, 36, 7.2, 1.04, 1.02, "Knicks"],
        ["NBA", "Jalen Brunson", "3pt_made", "full_game", 2.9, 36, 2.7, 1.04, 1.02, "Knicks"],
        ["NBA", "Jalen Brunson", "pra", "full_game", 44.6, 36, 43.0, 1.04, 1.02, "Knicks"],
        ["NBA", "Stephen Curry", "points", "1q", 8.2, 10, 7.7, 1.03, 1.01, "Warriors"],
        ["NBA", "Stephen Curry", "3pt_made", "1q", 1.7, 10, 1.5, 1.03, 1.01, "Warriors"],
    ]
    return pd.DataFrame(rows, columns=["sport", "player", "prop_type", "game_segment", "projection", "minutes_projection", "recent_avg", "pace_factor", "matchup_factor", "team"])

# ============================================================
# STEP 6 — PREP FUNCTIONS
# ============================================================

def prepare_props_df(df):
    defaults = {col: np.nan for col in DEFAULT_PROPS_COLS}
    defaults.update({
        "sport": "", "event_id": "", "player": "", "team": "", "opponent": "",
        "is_starter": 1, "starter_status": "unknown", "starter_confirmed": 0,
        "prop_type": "", "game_segment": "full_game", "book": "Unknown",
        "recommended_side_from_book": "", "source_time": "", "injury_status": "unknown",
        "injury_note": "", "recommended_side": "", "bet_grade": "", "confidence_warning": "",
        "confidence_status": "", "play_tier": "", "tier_reason": "", "best_book": "",
        "best_play_tier": "", "best_tier_reason": "", "tier_improved": "", "steam_flag": "",
        "bet_timing": "", "movement_summary": "", "bet_size_label": "", "bet_size_reason": "",
        "last_5_games": 5, "pace_factor": 1.0, "matchup_factor": 1.0,
    })
    if df is None or df.empty:
        return pd.DataFrame(columns=DEFAULT_PROPS_COLS)
    out = df.copy()
    out.columns = [c.strip().lower() for c in out.columns]
    out = add_missing_cols(out, defaults)

    num_cols = ["is_starter", "starter_confirmed", "line", "projection", "minutes_projection",
                "recent_avg", "last_5_games", "pace_factor", "matchup_factor", "odds",
                "proj_edge", "proj_edge_abs", "hit_prob_over", "hit_prob_under",
                "hit_probability", "book_implied_prob", "model_fair_odds",
                "expected_value_edge", "edge_score", "odds_move", "best_line", "best_odds",
                "line_edge_diff", "line_move", "bet_size_units", "kelly_fraction", "odds_move_signal"]
    for col in num_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    text_cols = ["sport", "event_id", "player", "team", "opponent", "starter_status",
                 "prop_type", "game_segment", "book", "recommended_side_from_book",
                 "source_time", "injury_status", "injury_note", "recommended_side",
                 "bet_grade", "confidence_warning", "confidence_status", "play_tier",
                 "tier_reason", "best_book", "tier_improved", "best_play_tier",
                 "best_tier_reason", "steam_flag", "bet_timing", "movement_summary",
                 "bet_size_label", "bet_size_reason"]
    for col in text_cols:
        out[col] = out[col].fillna("").astype(str)

    out["prop_type"] = out["prop_type"].apply(normalize_text)
    out["game_segment"] = out["game_segment"].apply(normalize_text)
    out["starter_status"] = out["starter_status"].apply(normalize_text)
    out["injury_status"] = out["injury_status"].apply(normalize_text)
    return out

def load_csv_or_empty(uploaded_file):
    if uploaded_file is None:
        return pd.DataFrame()
    try:
        if str(uploaded_file.name).lower().endswith(".csv"):
            return pd.read_csv(uploaded_file)
        return pd.read_excel(uploaded_file)
    except Exception:
        return pd.DataFrame()

def prepare_projection_overlay_df(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=["sport", "player", "prop_type", "game_segment", "projection", "minutes_projection", "recent_avg", "pace_factor", "matchup_factor", "team"])
    out = df.copy()
    out.columns = [c.strip().lower() for c in out.columns]
    out = add_missing_cols(out, {"sport": "", "player": "", "prop_type": "", "game_segment": "full_game", "projection": np.nan, "minutes_projection": np.nan, "recent_avg": np.nan, "pace_factor": np.nan, "matchup_factor": np.nan, "team": ""})
    for col in ["projection", "minutes_projection", "recent_avg", "pace_factor", "matchup_factor"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    for col in ["sport", "player", "prop_type", "game_segment", "team"]:
        out[col] = out[col].fillna("").astype(str)
    out["prop_type"] = out["prop_type"].apply(normalize_text)
    out["game_segment"] = out["game_segment"].apply(normalize_text)
    return out

def apply_projection_overlay(props_df, overlay_df):
    if props_df.empty or overlay_df.empty:
        return props_df.copy()
    keys = ["player", "prop_type", "game_segment"]
    overlay = overlay_df.drop_duplicates(subset=keys, keep="last")
    merged = props_df.merge(overlay, on=keys, how="left", suffixes=("", "_overlay"))
    for col in ["projection", "minutes_projection", "recent_avg", "pace_factor", "matchup_factor", "team"]:
        overlay_col = f"{col}_overlay"
        if merged[col].dtype == object:
            merged[col] = np.where(merged[overlay_col].fillna("").astype(str).str.len() > 0, merged[overlay_col], merged[col])
        else:
            merged[col] = np.where(~pd.isna(merged[overlay_col]), merged[overlay_col], merged[col])
    return merged.drop(columns=[c for c in merged.columns if c.endswith("_overlay")])

def apply_injuries(props_df, injuries_df):
    if props_df.empty or injuries_df is None or injuries_df.empty:
        return props_df.copy()
    inj = injuries_df[["player", "injury_status", "starter_status", "injury_note"]].drop_duplicates(subset=["player"], keep="last")
    merged = props_df.merge(inj, on="player", how="left", suffixes=("", "_inj"))
    merged["injury_status"] = np.where(merged["injury_status_inj"].fillna("").astype(str).str.len() > 0, merged["injury_status_inj"], merged["injury_status"])
    merged["starter_status"] = np.where(merged["starter_status_inj"].fillna("").astype(str).str.len() > 0, merged["starter_status_inj"], merged["starter_status"])
    merged["injury_note"] = np.where(merged["injury_note_inj"].fillna("").astype(str).str.len() > 0, merged["injury_note_inj"], merged["injury_note"])
    return merged.drop(columns=[c for c in merged.columns if c.endswith("_inj")])

# ============================================================
# STEP 7 — AUTO PROJECTIONS + SHARP CONTROL
# ============================================================

def auto_projection_row(row, dev_strength: float):
    player = row["player"]
    team = row["team"]
    prop_type = row["prop_type"]
    seg = row["game_segment"]
    line = safe_float(row["line"])

    base_multiplier = PLAYER_PROFILE.get(player, {}).get(prop_type, 1.0)
    pace = TEAM_MATCHUP.get(team, {}).get("pace", 1.0)
    matchup = TEAM_MATCHUP.get(team, {}).get("matchup", 1.0)

    if seg == "1q":
        segment_multiplier = 1.02
        mins = 9.5 if row["is_starter"] >= 1 else 6.5
    else:
        segment_multiplier = 1.00
        mins = 35.0 if row["is_starter"] >= 1 else 24.0

    player_hash = (sum(ord(c) for c in player + prop_type + team) % 9) - 4
    deterministic_bump = player_hash * 0.012 * dev_strength
    projection = line * base_multiplier * pace * matchup * segment_multiplier * (1 + deterministic_bump)

    if normalize_text(row.get("injury_status", "")) in ["questionable", "doubtful"]:
        projection *= 0.96
        mins *= 0.94

    if SHARP_MODE and not pd.isna(line):
        hard_cap = MAX_EDGE_CAP.get(prop_type, 5.0)
        soft_cap = EDGE_SOFT_CAP.get(prop_type, hard_cap - 1)
        edge = projection - line
        if edge > hard_cap:
            projection = line + hard_cap
        elif edge < -hard_cap:
            projection = line - hard_cap
        elif abs(edge) > soft_cap:
            excess = abs(edge) - soft_cap
            dampened = soft_cap + (excess * 0.4)
            projection = line + dampened if edge > 0 else line - dampened

    if SUPER_SHARP_MODE and not pd.isna(line):
        super_cap = MAX_EDGE_CAP.get(prop_type, 5.0) - 0.5
        projection = min(projection, line + super_cap)
        projection = max(projection, line - super_cap)

    recent_avg = projection * (0.97 + ((sum(ord(c) for c in player) % 4) * 0.01))
    return projection, mins, recent_avg, pace, matchup, base_multiplier

def apply_auto_projections(props_df, dev_strength: float):
    if props_df.empty:
        return props_df.copy()
    out = props_df.copy()
    generated = out.apply(lambda r: auto_projection_row(r, dev_strength), axis=1, result_type="expand")
    generated.columns = ["auto_projection", "auto_minutes", "auto_recent_avg", "auto_pace", "auto_matchup", "driver_multiplier"]
    out["projection"] = np.where(pd.isna(out["projection"]), generated["auto_projection"], out["projection"])
    out["minutes_projection"] = np.where(pd.isna(out["minutes_projection"]), generated["auto_minutes"], out["minutes_projection"])
    out["recent_avg"] = np.where(pd.isna(out["recent_avg"]), generated["auto_recent_avg"], out["recent_avg"])
    out["pace_factor"] = np.where(pd.isna(out["pace_factor"]), generated["auto_pace"], out["pace_factor"])
    out["matchup_factor"] = np.where(pd.isna(out["matchup_factor"]), generated["auto_matchup"], out["matchup_factor"])
    out["driver_multiplier"] = generated["driver_multiplier"]
    return out

# ============================================================
# STEP 8 — HIT PROBABILITY / CONFIDENCE
# ============================================================

def hit_probability_from_edge(row):
    prop_type = normalize_text(row.get("prop_type", "points"))
    line = safe_float(row.get("line"))
    proj = safe_float(row.get("projection"))
    minutes = safe_float(row.get("minutes_projection"))
    segment = normalize_text(row.get("game_segment", "full_game"))
    if pd.isna(line) or pd.isna(proj):
        return np.nan

    sigma_map_full = {
        "points": 6.5, "rebounds": 3.0, "assists": 3.2, "3pt_made": 1.6,
        "blocks": 1.2, "steals": 1.2, "blocks_steals": 1.8, "turnovers": 1.8,
        "pra": 8.4, "pr": 6.8, "pa": 7.0, "ra": 5.2,
    }
    sigma_map_1q = {"points": 2.6, "rebounds": 1.4, "assists": 1.5, "3pt_made": 0.9}
    sigma = (sigma_map_1q if segment == "1q" else sigma_map_full).get(prop_type, 5.5 if segment != "1q" else 2.3)

    if not pd.isna(minutes):
        if segment == "1q":
            if minutes < 8:
                sigma *= 1.10
            elif minutes >= 11:
                sigma *= 0.96
        else:
            if minutes < 24:
                sigma *= 1.18
            elif minutes < 30:
                sigma *= 1.08
            elif minutes >= 36:
                sigma *= 0.95

    z = (proj - line) / sigma if sigma > 0 else 0
    prob_over = 0.5 * (1 + math.erf(z / math.sqrt(2)))
    if SHARP_MODE:
        prob_over = max(0.05, min(0.85, prob_over))
    if SUPER_SHARP_MODE:
        prob_over = max(SUPER_SHARP_HIT_CLAMP["min"], min(SUPER_SHARP_HIT_CLAMP["max"], prob_over))
    return max(0.01, min(0.99, prob_over))

def confidence_warning_label(row):
    warnings = []
    if normalize_text(row.get("injury_status", "")) in ["questionable", "doubtful", "out"]:
        warnings.append(f"Injury: {row.get('injury_status', '')}")
    if safe_float(row.get("starter_confirmed")) < 1:
        warnings.append("Starter not confirmed")
    if safe_float(row.get("minutes_projection")) < (8 if normalize_text(row.get("game_segment", "")) == "1q" else 26):
        warnings.append("Low minutes")
    if not pd.isna(safe_float(row.get("projection"))) and not pd.isna(safe_float(row.get("line"))):
        if abs(safe_float(row.get("projection")) - safe_float(row.get("line"))) < 0.4:
            warnings.append("Thin model edge")
    return "Clear" if not warnings else " | ".join(warnings)

def confidence_status(row):
    note = confidence_warning_label(row)
    if note == "Clear":
        return "✅ Clear"
    if "Injury:" in note or "Starter not confirmed" in note:
        return "⚠️ Caution"
    return "🟡 Watch"

# ============================================================
# STEP 9 — SUPER SHARP SCORING + TIER CLASSIFICATION
# ============================================================

def compute_prop_scores(df):
    out = prepare_props_df(df)
    if out.empty:
        return out

    out["projection"] = np.where(pd.isna(out["projection"]), out["line"], out["projection"])
    out["minutes_projection"] = np.where(pd.isna(out["minutes_projection"]), np.where(out["game_segment"] == "1q", 9, 32), out["minutes_projection"])
    out["recent_avg"] = np.where(pd.isna(out["recent_avg"]), out["line"], out["recent_avg"])
    out["pace_factor"] = np.where(pd.isna(out["pace_factor"]), 1.0, out["pace_factor"])
    out["matchup_factor"] = np.where(pd.isna(out["matchup_factor"]), 1.0, out["matchup_factor"])
    out["is_starter"] = np.where(pd.isna(out["is_starter"]), 1, out["is_starter"])
    out["starter_confirmed"] = np.where(pd.isna(out["starter_confirmed"]), 1, out["starter_confirmed"])

    if "driver_multiplier" not in out.columns:
        out["driver_multiplier"] = 1.0

    out["proj_edge"] = out["projection"] - out["line"]
    out["proj_edge_abs"] = out["proj_edge"].abs()
    out["recommended_side"] = np.where(out["projection"] > out["line"], "Over", "Under")
    out["hit_prob_over"] = out.apply(hit_probability_from_edge, axis=1)
    out["hit_prob_under"] = 1 - out["hit_prob_over"]
    out["hit_probability"] = np.where(out["recommended_side"] == "Over", out["hit_prob_over"], out["hit_prob_under"])
    out["book_implied_prob"] = out["odds"].apply(implied_prob_american)
    out["model_fair_odds"] = out["hit_probability"].apply(prob_to_american)
    out["expected_value_edge"] = ((out["hit_probability"] - out["book_implied_prob"]) * 100).round(2)

    minutes_score = np.where(out["game_segment"] == "1q", np.clip((out["minutes_projection"] / 12) * 15, 0, 15), np.clip((out["minutes_projection"] / 36) * 17, 0, 17))
    edge_score_component = np.clip(out["proj_edge_abs"] * 5.0, 0, 20)
    recent_gap = (out["recent_avg"] - out["line"]).abs()
    recent_score = np.clip(recent_gap * 1.8, 0, 10)
    starter_score = np.where(out["is_starter"] >= 1, 8, 0)
    confirmed_bonus = np.where(out["starter_confirmed"] >= 1, 5, 0)
    pace_score = np.clip((out["pace_factor"] - 1.0) * 100, -3, 8)
    matchup_score = np.clip((out["matchup_factor"] - 1.0) * 100, -3, 10)
    probability_score = np.clip((out["hit_probability"] - 0.50) * 85, 0, 11)
    ev_score = np.clip(out["expected_value_edge"] * 0.6, 0, 8)
    price_score = np.select(
        [(out["odds"] >= -125) & (out["odds"] <= 140), (out["odds"] >= -150) & (out["odds"] < -125), (out["odds"] > 140) & (out["odds"] <= 200)],
        [9, 6, 7],
        default=4,
    )
    caution_penalty = np.select(
        [out["starter_confirmed"] < 1, out["injury_status"].isin(["questionable", "doubtful"]), out["minutes_projection"] < np.where(out["game_segment"] == "1q", 8, 26)],
        [6, 5, 4],
        default=0,
    )
    extreme_penalty = 0
    if SHARP_MODE:
        extreme_penalty = np.where(out["proj_edge_abs"] > 6, 6, np.where(out["proj_edge_abs"] > 5, 3, 0))
    if SUPER_SHARP_MODE:
        extreme_penalty = extreme_penalty + np.where(out["proj_edge_abs"] > 4.5, 2, 0)

    multiplier_penalty = np.where(out["driver_multiplier"] > 1.14, 3, np.where(out["driver_multiplier"] > 1.10, 1.5, 0)) if SUPER_SHARP_MODE else 0

    raw_score = (
        minutes_score + edge_score_component + recent_score + starter_score + confirmed_bonus +
        pace_score + matchup_score + price_score + probability_score + ev_score -
        caution_penalty - extreme_penalty - multiplier_penalty
    )

    if SUPER_SHARP_MODE:
        compressed = np.where(raw_score > 88, 88 + (raw_score - 88) * 0.35, raw_score)
        compressed = np.where(compressed > 94, 94 + (compressed - 94) * 0.20, compressed)
        out["edge_score"] = compressed.round(1)
    else:
        out["edge_score"] = raw_score.round(1)

    out["edge_score"] = np.clip(out["edge_score"], 0, 100)
    out["bet_grade"] = out["edge_score"].apply(edge_bucket)
    out["confidence_warning"] = out.apply(confidence_warning_label, axis=1)
    out["confidence_status"] = out.apply(confidence_status, axis=1)

    tiers = out.apply(classify_play_tier, axis=1, result_type="expand")
    out["play_tier"] = tiers[0]
    out["tier_reason"] = tiers[1]
    return out

# ============================================================
# STEP 10 — LINE SHOPPING V1
# ============================================================

def apply_line_shopping(df):
    out = prepare_props_df(df)
    if out.empty:
        return out
    result_parts = []
    keys = ["player", "prop_type", "game_segment", "recommended_side"]
    for _, group in out.groupby(keys, dropna=False):
        group = group.copy()
        side = str(group["recommended_side"].iloc[0])

        if side == "Over":
            best_group = group.sort_values(["line", "odds", "edge_score", "expected_value_edge"], ascending=[True, False, False, False])
        else:
            best_group = group.sort_values(["line", "odds", "edge_score", "expected_value_edge"], ascending=[False, False, False, False])

        best_row = best_group.iloc[0]
        best_book = best_row["book"]
        best_line = best_row["line"]
        best_odds = best_row["odds"]
        best_tier = best_row["play_tier"]
        best_reason = best_row["tier_reason"]

        line_diff_series = group["line"] - best_line if side == "Over" else best_line - group["line"]
        group["best_book"] = best_book
        group["best_line"] = best_line
        group["best_odds"] = best_odds
        group["line_edge_diff"] = line_diff_series
        group["best_play_tier"] = best_tier
        group["best_tier_reason"] = best_reason

        improvement = []
        for _, row in group.iterrows():
            current_rank = tier_rank(row["play_tier"])
            best_rank = tier_rank(best_tier)
            if row["book"] == best_book:
                improvement.append("Best current book")
            elif best_rank > current_rank:
                improvement.append("YES")
            else:
                improvement.append("NO")
        group["tier_improved"] = improvement
        result_parts.append(group)
    return pd.concat(result_parts, ignore_index=True) if result_parts else out

# ============================================================
# STEP 11 — STEAM / LINE MOVEMENT V1
# ============================================================

def create_live_snapshot_variant(df):
    out = prepare_props_df(df).copy()
    if out.empty:
        return out
    rows = []
    for _, row in out.iterrows():
        key_num = sum(ord(c) for c in f"{row['player']}{row['prop_type']}{row['book']}{row['game_segment']}")
        variant = (key_num % 7) - 3
        line_shift = 0.0
        odds_shift = 0
        if row["recommended_side"] == "Over":
            if variant in [2, 3]:
                line_shift = 0.5
                odds_shift = -10
            elif variant == 1:
                odds_shift = -8
            elif variant == -1:
                odds_shift = 8
            elif variant in [-2, -3]:
                line_shift = -0.5
                odds_shift = 10
        else:
            if variant in [2, 3]:
                line_shift = -0.5
                odds_shift = -10
            elif variant == 1:
                odds_shift = -8
            elif variant == -1:
                odds_shift = 8
            elif variant in [-2, -3]:
                line_shift = 0.5
                odds_shift = 10
        new_row = row.copy()
        new_row["line"] = safe_float(row["line"]) + line_shift
        new_row["odds"] = safe_float(row["odds"]) + odds_shift
        rows.append(new_row)
    return prepare_props_df(pd.DataFrame(rows))

def movement_for_side(prev_line, prev_odds, cur_line, cur_odds, side):
    prev_line = safe_float(prev_line); prev_odds = safe_float(prev_odds)
    cur_line = safe_float(cur_line); cur_odds = safe_float(cur_odds)
    if pd.isna(prev_line) or pd.isna(cur_line):
        return 0.0, 0.0
    line_move = cur_line - prev_line if side == "Over" else prev_line - cur_line
    odds_move = 0.0 if pd.isna(prev_odds) or pd.isna(cur_odds) else (prev_odds - cur_odds)
    return line_move, odds_move

def label_steam(line_move, odds_move):
    strength = 0
    if line_move >= 1.0: strength += 2
    elif line_move >= 0.5: strength += 1
    if odds_move >= 15: strength += 2
    elif odds_move >= 8: strength += 1
    if strength >= 3: return "🔥 Strong steam"
    if strength >= 2: return "📈 Steam"
    if line_move <= -1.0 or odds_move <= -15: return "🔻 Against model"
    if line_move <= -0.5 or odds_move <= -8: return "↘️ Cooling"
    return "➖ Stable"

def timing_label(flag):
    if flag in ["🔥 Strong steam", "📈 Steam"]: return "Bet now"
    if flag in ["🔻 Against model", "↘️ Cooling"]: return "Wait / monitor"
    return "Okay now"

def apply_steam_signals(current_df, previous_df):
    cur = prepare_props_df(current_df).copy()
    prev = prepare_props_df(previous_df).copy()
    if cur.empty:
        return cur
    if prev.empty:
        cur["line_move"] = 0.0
        cur["odds_move_signal"] = 0.0
        cur["steam_flag"] = "➖ Stable"
        cur["bet_timing"] = "Okay now"
        cur["movement_summary"] = "No prior snapshot"
        return cur
    key_cols = ["player", "prop_type", "game_segment", "book", "recommended_side"]
    prev_small = prev[key_cols + ["line", "odds"]].rename(columns={"line": "prev_line", "odds": "prev_odds"})
    merged = cur.merge(prev_small, on=key_cols, how="left")

    line_moves = []; odds_moves = []; flags = []; timing = []; summaries = []
    for _, row in merged.iterrows():
        lm, om = movement_for_side(row.get("prev_line"), row.get("prev_odds"), row.get("line"), row.get("odds"), row.get("recommended_side"))
        flag = label_steam(lm, om)
        line_moves.append(lm); odds_moves.append(om); flags.append(flag); timing.append(timing_label(flag))
        summaries.append(f"Line move {lm:+.1f} | Odds move {om:+.0f}")
    merged["line_move"] = line_moves
    merged["odds_move_signal"] = odds_moves
    merged["steam_flag"] = flags
    merged["bet_timing"] = timing
    merged["movement_summary"] = summaries
    return prepare_props_df(merged.drop(columns=["prev_line", "prev_odds"]))

# ============================================================
# STEP 12 — BET SIZING V1
# ============================================================

def kelly_fraction_from_row(row):
    p = safe_float(row.get("hit_probability"))
    odds = safe_float(row.get("odds"))
    dec = american_to_decimal(odds)
    if pd.isna(p) or pd.isna(dec) or dec <= 1:
        return 0.0
    b = dec - 1
    q = 1 - p
    kelly = (b * p - q) / b if b > 0 else 0.0
    return max(0.0, float(kelly))

def bet_size_from_row(row):
    tier = str(row.get("play_tier", "Tier 3"))
    steam = str(row.get("steam_flag", ""))
    timing = str(row.get("bet_timing", ""))
    conf = str(row.get("confidence_status", ""))
    score = safe_float(row.get("edge_score"))
    ev = safe_float(row.get("expected_value_edge"))
    kelly = safe_float(row.get("kelly_fraction"))

    if conf != "✅ Clear":
        return 0.0, "Pass", "Confidence not clear"

    if tier == "Tier 1":
        units = 1.0; reasons = ["Tier 1 base"]
    elif tier == "Tier 2":
        units = 0.5; reasons = ["Tier 2 base"]
    else:
        units = 0.25; reasons = ["Tier 3 base"]

    if steam in ["🔥 Strong steam", "📈 Steam"] and tier in ["Tier 1", "Tier 2"]:
        units += 0.25; reasons.append("Steam boost")
    elif steam in ["🔻 Against model", "↘️ Cooling"]:
        units -= 0.25; reasons.append("Steam caution")

    if ev >= 12 and score >= 85:
        units += 0.25; reasons.append("High EV/score boost")
    if timing == "Wait / monitor":
        units -= 0.25; reasons.append("Wait signal")

    if kelly > 0:
        kelly_units_cap = min(1.25, max(0.25, round((kelly * 0.5) / 0.01) * 0.25))
        units = min(units, kelly_units_cap); reasons.append("Kelly cap")

    units = max(0.0, min(1.25, round(units * 4) / 4))
    if units >= 1.0: label = "1.0u+ Core"
    elif units >= 0.75: label = "0.75u Strong"
    elif units >= 0.5: label = "0.5u Standard"
    elif units >= 0.25: label = "0.25u Small"
    else: label = "Pass"
    return units, label, " | ".join(reasons)

def apply_bet_sizing(df):
    out = prepare_props_df(df).copy()
    if out.empty:
        return out
    out["kelly_fraction"] = out.apply(kelly_fraction_from_row, axis=1)
    sizes = out.apply(bet_size_from_row, axis=1, result_type="expand")
    out["bet_size_units"] = sizes[0]
    out["bet_size_label"] = sizes[1]
    out["bet_size_reason"] = sizes[2]
    return out

# ============================================================
# STEP 13 — BET TRACKER V1
# ============================================================

def tracker_add_bet(row):
    init_tracker_state()
    tracker = st.session_state["bet_tracker_df"].copy()
    bet_id = f"BET-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')[:-3]}"
    new_row = {
        "bet_id": bet_id,
        "added_at": current_ts_str(),
        "sport": row["sport"],
        "player": row["player"],
        "opponent": row["opponent"],
        "book": row["book"],
        "game_segment": row["game_segment"],
        "prop_type": row["prop_type"],
        "side": row["recommended_side"],
        "line": safe_float(row["line"]),
        "odds": safe_float(row["odds"]),
        "projection": safe_float(row["projection"]),
        "edge": safe_float(row["proj_edge"]),
        "hit_probability": safe_float(row["hit_probability"]),
        "ev_edge": safe_float(row["expected_value_edge"]),
        "edge_score": safe_float(row["edge_score"]),
        "play_tier": row["play_tier"],
        "steam_flag": row["steam_flag"],
        "bet_timing": row["bet_timing"],
        "bet_size_units": safe_float(row["bet_size_units"]),
        "bet_size_label": row["bet_size_label"],
        "result": "Open",
        "profit_units": np.nan,
        "notes": ""
    }
    tracker = pd.concat([pd.DataFrame([new_row]), tracker], ignore_index=True)
    st.session_state["bet_tracker_df"] = tracker

def tracker_update_results(df):
    tracker = st.session_state["bet_tracker_df"].copy()
    if tracker.empty:
        return
    updates = df.copy()
    for _, upd in updates.iterrows():
        mask = tracker["bet_id"] == upd["bet_id"]
        tracker.loc[mask, "result"] = upd["result"]
        tracker.loc[mask, "notes"] = upd["notes"]
        tracker.loc[mask, "profit_units"] = profit_units_from_result(
            upd["result"],
            tracker.loc[mask, "odds"].iloc[0],
            tracker.loc[mask, "bet_size_units"].iloc[0]
        )
    st.session_state["bet_tracker_df"] = tracker

def tracker_summary(df):
    if df.empty:
        return {
            "bets": 0, "open": 0, "graded": 0, "wins": 0, "losses": 0, "pushes": 0,
            "win_rate": 0.0, "units": 0.0, "roi": 0.0
        }
    graded = df[df["result"].isin(["Win", "Loss", "Push"])].copy()
    wins = int((graded["result"] == "Win").sum())
    losses = int((graded["result"] == "Loss").sum())
    pushes = int((graded["result"] == "Push").sum())
    graded_count = len(graded)
    risked = graded["bet_size_units"].fillna(0).sum()
    units = graded["profit_units"].fillna(0).sum()
    return {
        "bets": len(df),
        "open": int((df["result"] == "Open").sum()),
        "graded": graded_count,
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "win_rate": (wins / max(1, wins + losses)) * 100,
        "units": units,
        "roi": (units / max(1e-9, risked)) * 100 if risked > 0 else 0.0
    }

def tracker_group_summary(df, group_col):
    graded = df[df["result"].isin(["Win", "Loss", "Push"])].copy()
    if graded.empty:
        return pd.DataFrame(columns=[group_col, "Bets", "Wins", "Losses", "Pushes", "Win %", "Units", "ROI %"])
    rows = []
    for key, grp in graded.groupby(group_col, dropna=False):
        wins = int((grp["result"] == "Win").sum())
        losses = int((grp["result"] == "Loss").sum())
        pushes = int((grp["result"] == "Push").sum())
        risked = grp["bet_size_units"].fillna(0).sum()
        units = grp["profit_units"].fillna(0).sum()
        rows.append({
            group_col: key,
            "Bets": len(grp),
            "Wins": wins,
            "Losses": losses,
            "Pushes": pushes,
            "Win %": round((wins / max(1, wins + losses)) * 100, 1),
            "Units": round(units, 2),
            "ROI %": round((units / max(1e-9, risked)) * 100, 1) if risked > 0 else 0.0,
        })
    return pd.DataFrame(rows).sort_values(["Units", "ROI %"], ascending=[False, False])

# ============================================================
# STEP 14 — FILTERS / DISPLAY HELPERS
# ============================================================

def best_line_shop(df):
    out = prepare_props_df(df)
    if out.empty:
        return out
    rows = []
    for _, group in out.groupby(["player", "prop_type", "game_segment", "recommended_side"], dropna=False):
        side = group["recommended_side"].iloc[0]
        if side == "Over":
            group = group.sort_values(["line", "odds", "edge_score", "expected_value_edge"], ascending=[True, False, False, False])
        else:
            group = group.sort_values(["line", "odds", "edge_score", "expected_value_edge"], ascending=[False, False, False, False])
        rows.append(group.iloc[0])
    return pd.DataFrame(rows).reset_index(drop=True).sort_values(["bet_size_units", "edge_score", "expected_value_edge", "hit_probability"], ascending=[False, False, False, False])

def filter_props_base(df, sport="All", segment="All", starters_only=True, confirmed_only=False, min_odds=-300, max_odds=200, min_edge=60, min_hit_prob=50, min_ev=-5, book="All", prop_type="All", tier="All", improved="All", steam="All", min_units=0.0):
    out = prepare_props_df(df)
    if sport != "All": out = out[out["sport"] == sport]
    if segment != "All": out = out[out["game_segment"] == segment]
    if prop_type != "All": out = out[out["prop_type"] == prop_type]
    if starters_only: out = out[out["is_starter"] >= 1]
    if confirmed_only: out = out[out["starter_confirmed"] >= 1]
    if book != "All": out = out[out["book"] == book]
    if tier != "All": out = out[out["play_tier"] == tier]
    if improved == "YES":
        out = out[out["tier_improved"] == "YES"]
    elif improved == "Best current book":
        out = out[out["tier_improved"] == "Best current book"]
    if steam != "All": out = out[out["steam_flag"] == steam]
    out = out[out["bet_size_units"] >= min_units]
    out = out[(out["odds"] >= min_odds) & (out["odds"] <= max_odds)]
    out = out[out["edge_score"] >= min_edge]
    out = out[(out["hit_probability"] * 100) >= min_hit_prob]
    out = out[out["expected_value_edge"] >= min_ev]
    return out.sort_values(["bet_size_units", "edge_score", "expected_value_edge", "hit_probability"], ascending=[False, False, False, False])

def build_best_bets_dashboard(df):
    out = prepare_props_df(df)
    cols = ["player", "opponent", "book", "best_book", "game_segment", "prop_type", "recommended_side", "line", "best_line", "line_move", "odds", "best_odds", "projection", "proj_edge", "hit_probability", "expected_value_edge", "edge_score", "play_tier", "steam_flag", "bet_timing", "bet_size_units", "bet_size_label", "confidence_status"]
    if out.empty:
        return pd.DataFrame(columns=cols)
    return out.sort_values(["bet_size_units", "edge_score", "expected_value_edge", "hit_probability"], ascending=[False, False, False, False])[cols].head(20).copy()

def format_props_table(df):
    out = df.copy()
    if out.empty:
        return out
    if "hit_probability" in out.columns:
        out["hit_probability"] = (out["hit_probability"] * 100).round(1)
    if "kelly_fraction" in out.columns:
        out["kelly_fraction"] = (out["kelly_fraction"] * 100).round(2)
    return out

def render_top_play_card(row, rank_num):
    st.markdown(
        f"""
<div style="padding:14px;border:1px solid #333;border-radius:12px;margin-bottom:10px;">
  <div style="font-size:18px;font-weight:700;">#{rank_num} {row['player']} — {row['recommended_side']} {row['line']} {row['prop_type']}</div>
  <div style="margin-top:4px;">{row['opponent']} • {str(row['game_segment']).upper()} • {row['book']}</div>
  <div style="margin-top:8px;">
    <b>Projection:</b> {row['projection']:.2f} |
    <b>Edge:</b> {row['proj_edge']:.2f} |
    <b>Odds:</b> {int(row['odds']) if not pd.isna(row['odds']) else 'N/A'} |
    <b>Hit %:</b> {row['hit_probability']*100:.1f}% |
    <b>EV Edge:</b> {row['expected_value_edge']:.2f}% |
    <b>Score:</b> {row['edge_score']:.1f} ({row['bet_grade']})
  </div>
  <div style="margin-top:8px;">
    <b>Tier:</b> {tier_badge(row['play_tier'])} |
    <b>Steam:</b> {row['steam_flag']} |
    <b>Timing:</b> {row['bet_timing']}
  </div>
  <div style="margin-top:8px;">
    <b>Best Book:</b> {row['best_book']} |
    <b>Best Line:</b> {row['best_line']} |
    <b>Best Odds:</b> {int(row['best_odds']) if not pd.isna(row['best_odds']) else 'N/A'}
  </div>
  <div style="margin-top:8px;">
    <b>Bet Size:</b> {row['bet_size_label']} ({row['bet_size_units']:.2f}u) |
    <b>Kelly:</b> {row['kelly_fraction']*100:.2f}% |
    <b>Why:</b> {row['bet_size_reason']}
  </div>
  <div style="margin-top:8px;">
    <b>Confidence:</b> {row['confidence_status']} |
    <b>Notes:</b> {row['confidence_warning']}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

# ============================================================
# STEP 15 — SIDEBAR CONTROLS
# ============================================================

st.sidebar.header("DEV MODE V9")
st.sidebar.success("BET TRACKER V1 enabled.")
sport_name = st.sidebar.selectbox("Sport", SPORTS, index=0)
best_shop_only = st.sidebar.checkbox("Best line shop only", value=True)
projection_mode = st.sidebar.selectbox("Projection source", ["Auto Projections V1", "Upload CSV Override"], index=0)
dev_strength = st.sidebar.slider("Auto projection aggressiveness", 0.50, 1.50, 1.00, 0.05)
projection_file = st.sidebar.file_uploader("Optional projection CSV override", type=["csv", "xlsx"])

if st.sidebar.button("Save current props snapshot"):
    if "latest_props_live" in st.session_state and not st.session_state["latest_props_live"].empty:
        st.session_state["latest_snapshot"] = st.session_state["latest_props_live"].copy()
        st.sidebar.success("Snapshot saved")
    else:
        st.sidebar.warning("No props loaded yet.")

if st.sidebar.button("Generate moved market"):
    st.session_state["use_moved_market"] = True
    st.sidebar.success("Moved market generated")

if st.sidebar.button("Reset moved market"):
    st.session_state["use_moved_market"] = False
    st.sidebar.success("Moved market reset")

# ============================================================
# STEP 16 — LOAD / BUILD DATA
# ============================================================

init_tracker_state()

odds_df = make_sample_odds_df()
props_df = prepare_props_df(make_sample_props_df())
injuries_df = make_sample_injuries_df()
proj_df = prepare_projection_overlay_df(load_csv_or_empty(projection_file))

props_df = props_df[props_df["sport"] == sport_name].copy()
odds_df = odds_df[odds_df["sport"] == sport_name].copy()

props_df = apply_injuries(props_df, injuries_df)
props_df = apply_auto_projections(props_df, dev_strength)

if projection_mode == "Upload CSV Override" and not proj_df.empty:
    props_df = apply_projection_overlay(props_df, proj_df)

props_scored = compute_prop_scores(props_df)

base_snapshot = st.session_state.get("base_market_snapshot", pd.DataFrame())
if base_snapshot.empty:
    st.session_state["base_market_snapshot"] = props_scored.copy()
    base_snapshot = props_scored.copy()

use_moved = st.session_state.get("use_moved_market", False)
current_market = create_live_snapshot_variant(base_snapshot) if use_moved else base_snapshot.copy()

proj_cols = ["player", "prop_type", "game_segment", "book", "projection", "minutes_projection", "recent_avg", "pace_factor", "matchup_factor", "injury_status", "injury_note", "confidence_warning", "confidence_status", "play_tier", "tier_reason", "driver_multiplier"]
scored_small = props_scored[proj_cols].drop_duplicates(subset=["player", "prop_type", "game_segment", "book"])
current_market = current_market.drop(columns=[c for c in proj_cols if c in current_market.columns and c not in ["player","prop_type","game_segment","book"]], errors="ignore")
current_market = current_market.merge(scored_small, on=["player", "prop_type", "game_segment", "book"], how="left")
current_market = compute_prop_scores(current_market)

previous_snapshot = st.session_state.get("latest_snapshot", base_snapshot.copy())
current_market = apply_line_shopping(current_market)
current_market = apply_steam_signals(current_market, previous_snapshot)
current_market = apply_bet_sizing(current_market)
props_live = prepare_props_df(current_market)
props_shop = best_line_shop(props_live)
st.session_state["latest_props_live"] = props_live.copy()

source_status = pd.DataFrame([
    ["Mode", "DEV MODE V9", "Active"],
    ["Projection Source", projection_mode, "Active"],
    ["Sharp Mode", "ON" if SHARP_MODE else "OFF", "Active"],
    ["Super Sharp", "ON" if SUPER_SHARP_MODE else "OFF", "Active"],
    ["Tier System", "ON", "Active"],
    ["Line Shopping", "ON", "Active"],
    ["Steam V1", "ON", "Active"],
    ["Bet Sizing V1", "ON", "Active"],
    ["Bet Tracker V1", "ON", "Active"],
    ["Market State", "Moved" if use_moved else "Base", "Sample"],
    ["Props Rows", len(props_live), "Sample"],
    ["Tracked Bets", len(st.session_state['bet_tracker_df']), "Session"],
], columns=["Feed", "Value", "Status"])

# ============================================================
# STEP 17 — UI TABS
# ============================================================

tab_home, tab_best, tab_sections, tab_tracker, tab_arb, tab_inj, tab_template = st.tabs([
    "Home", "Best Bets", "Prop Sections", "Bet Tracker", "Arbitrage", "Injuries / Starters", "Projection Template"
])

with tab_home:
    st.subheader("DEV MODE V9 Home")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Props Rows", len(props_live))
    c2.metric("Books", props_live["book"].nunique() if not props_live.empty else 0)
    c3.metric("Bet Now", int((props_live["bet_timing"] == "Bet now").sum()) if not props_live.empty else 0)
    c4.metric("Tracked Bets", len(st.session_state["bet_tracker_df"]))
    st.markdown("### Feed status")
    st.dataframe(source_status, use_container_width=True)

    tracker_stats = tracker_summary(st.session_state["bet_tracker_df"])
    a, b, c, d = st.columns(4)
    a.metric("Open Bets", tracker_stats["open"])
    b.metric("Graded Bets", tracker_stats["graded"])
    c.metric("Units", f"{tracker_stats['units']:.2f}")
    d.metric("ROI %", f"{tracker_stats['roi']:.1f}%")
    st.info("Use Best Bets to add plays to the tracker, then grade them in the Bet Tracker tab.")

with tab_best:
    st.subheader("Auto Best Bets Board")
    base_df = props_shop.copy() if best_shop_only else props_live.copy()

    sport_opts = ["All"] + sorted(base_df["sport"].dropna().astype(str).unique().tolist()) if not base_df.empty else ["All"]
    segment_opts = ["All"] + sorted(base_df["game_segment"].dropna().astype(str).unique().tolist()) if not base_df.empty else ["All"]
    prop_opts = ["All"] + sorted(base_df["prop_type"].dropna().astype(str).unique().tolist()) if not base_df.empty else ["All"]
    book_opts = ["All"] + sorted(base_df["book"].dropna().astype(str).unique().tolist()) if not base_df.empty else ["All"]
    tier_opts = ["All", "Tier 1", "Tier 2", "Tier 3"]
    improved_opts = ["All", "YES", "Best current book"]
    steam_opts = ["All", "🔥 Strong steam", "📈 Steam", "➖ Stable", "↘️ Cooling", "🔻 Against model"]

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1: selected_sport = st.selectbox("Sport", sport_opts)
    with c2: selected_segment = st.selectbox("Segment", segment_opts)
    with c3: selected_prop = st.selectbox("Prop Type", prop_opts)
    with c4: selected_book = st.selectbox("Book", book_opts)
    with c5: selected_tier = st.selectbox("Tier", tier_opts)
    with c6: selected_improved = st.selectbox("Line Shop", improved_opts)

    c7, c8, c9, c10, c11 = st.columns(5)
    with c7: selected_steam = st.selectbox("Steam", steam_opts)
    with c8: starters_only = st.checkbox("Starters Only", value=True)
    with c9: confirmed_only = st.checkbox("Confirmed Only", value=False)
    with c10: min_edge = st.slider("Min Edge Score", 0, 100, 60, 5)
    with c11: min_hit = st.slider("Min Hit %", 50, 95, 54, 1)

    c12, c13, c14, c15 = st.columns(4)
    with c12: min_odds = st.slider("Min Odds", -300, 200, -300, 5)
    with c13: max_odds = st.slider("Max Odds", -300, 200, 200, 5)
    with c14: min_ev = st.slider("Min EV Edge %", -10, 25, 0, 1)
    with c15: min_units = st.slider("Min Units", 0.0, 1.25, 0.25, 0.25)

    filtered = filter_props_base(
        base_df, selected_sport, selected_segment, starters_only, confirmed_only,
        min_odds, max_odds, min_edge, min_hit, min_ev, selected_book,
        selected_prop, selected_tier, selected_improved, selected_steam, min_units
    )

    if filtered.empty:
        st.warning("No props match the current filters")
    else:
        for idx, (_, row) in enumerate(filtered.head(10).iterrows(), start=1):
            render_top_play_card(row, idx)

        add_options = [
            f"{r.player} | {r.recommended_side} {r.line} {r.prop_type} | {r.book} | {r.bet_size_units:.2f}u"
            for _, r in filtered.head(20).iterrows()
        ]
        row_lookup = {add_options[i]: filtered.head(20).iloc[i] for i in range(len(add_options))}
        selected_add = st.selectbox("Add play to tracker", add_options)
        if st.button("Add selected play to tracker"):
            tracker_add_bet(row_lookup[selected_add])
            st.success("Play added to tracker")

        st.dataframe(format_props_table(build_best_bets_dashboard(filtered)), use_container_width=True)

with tab_sections:
    st.subheader("Prop Sections")
    if props_live.empty:
        st.info("No props loaded.")
    else:
        table_cols = [
            "player", "opponent", "book", "best_book", "game_segment", "recommended_side",
            "line", "best_line", "line_move", "odds", "best_odds", "projection",
            "proj_edge", "hit_probability", "expected_value_edge", "edge_score",
            "play_tier", "steam_flag", "bet_timing", "bet_size_units", "bet_size_label"
        ]
        for title, prop_key, seg in [
            ("Points", "points", None), ("Rebounds", "rebounds", None), ("Assists", "assists", None),
            ("3PT Made", "3pt_made", None), ("Blocks", "blocks", None), ("Steals", "steals", None),
            ("Turnovers", "turnovers", None), ("PRA", "pra", None), ("PR", "pr", None),
            ("PA", "pa", None), ("RA", "ra", None), ("1Q Only", None, "1q"),
        ]:
            section = props_live.copy()
            if prop_key is not None:
                section = section[section["prop_type"] == prop_key]
            if seg is not None:
                section = section[section["game_segment"] == seg]
            st.markdown(f"### {title}")
            if section.empty:
                st.info(f"No {title.lower()} props loaded.")
            else:
                st.dataframe(format_props_table(section[table_cols]), use_container_width=True)

with tab_tracker:
    st.subheader("Bet Tracker V1")
    tracker_df = st.session_state["bet_tracker_df"].copy()

    stats = tracker_summary(tracker_df)
    t1, t2, t3, t4, t5 = st.columns(5)
    t1.metric("Total Bets", stats["bets"])
    t2.metric("Open", stats["open"])
    t3.metric("Win %", f"{stats['win_rate']:.1f}%")
    t4.metric("Units", f"{stats['units']:.2f}")
    t5.metric("ROI %", f"{stats['roi']:.1f}%")

    if tracker_df.empty:
        st.info("No tracked bets yet. Add plays from the Best Bets tab.")
    else:
        st.markdown("### Open / all tracked bets")
        display_df = tracker_df.copy()
        display_df["hit_probability"] = (pd.to_numeric(display_df["hit_probability"], errors="coerce") * 100).round(1)
        st.dataframe(display_df, use_container_width=True)

        st.markdown("### Grade open bets")
        open_bets = tracker_df[tracker_df["result"] == "Open"].copy()
        if open_bets.empty:
            st.info("No open bets to grade.")
        else:
            grade_df = open_bets[["bet_id", "player", "prop_type", "side", "line", "odds", "bet_size_units", "result", "notes"]].copy()
            grade_df["result"] = "Open"
            edited = st.data_editor(
                grade_df,
                num_rows="fixed",
                use_container_width=True,
                column_config={
                    "result": st.column_config.SelectboxColumn("result", options=["Open", "Win", "Loss", "Push"]),
                    "notes": st.column_config.TextColumn("notes")
                },
                key="grade_editor"
            )
            if st.button("Save grading updates"):
                tracker_update_results(edited[["bet_id", "result", "notes"]])
                st.success("Tracker updated")

        tracker_df = st.session_state["bet_tracker_df"].copy()
        st.markdown("### Performance by tier")
        st.dataframe(tracker_group_summary(tracker_df, "play_tier"), use_container_width=True)

        st.markdown("### Performance by steam flag")
        st.dataframe(tracker_group_summary(tracker_df, "steam_flag"), use_container_width=True)

        st.markdown("### Performance by prop type")
        st.dataframe(tracker_group_summary(tracker_df, "prop_type"), use_container_width=True)

        st.markdown("### Performance by book")
        st.dataframe(tracker_group_summary(tracker_df, "book"), use_container_width=True)

        csv_bytes = tracker_df.to_csv(index=False).encode("utf-8")
        st.download_button("Download bet tracker CSV", csv_bytes, "bet_tracker_v1.csv", "text/csv")

        xlsx_buffer = BytesIO()
        with pd.ExcelWriter(xlsx_buffer, engine="openpyxl") as writer:
            tracker_df.to_excel(writer, sheet_name="Bets", index=False)
            tracker_group_summary(tracker_df, "play_tier").to_excel(writer, sheet_name="By Tier", index=False)
            tracker_group_summary(tracker_df, "steam_flag").to_excel(writer, sheet_name="By Steam", index=False)
            tracker_group_summary(tracker_df, "prop_type").to_excel(writer, sheet_name="By Prop", index=False)
            tracker_group_summary(tracker_df, "book").to_excel(writer, sheet_name="By Book", index=False)
        st.download_button(
            "Download bet tracker Excel",
            xlsx_buffer.getvalue(),
            "bet_tracker_v1.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

with tab_arb:
    st.subheader("Moneyline Arbitrage")
    arb_results = []
    ml = odds_df[odds_df["market"] == "moneyline"].copy()
    for keys, group in ml.groupby(["sport", "team_a", "team_b"], dropna=False):
        selections = group["selection"].dropna().unique()
        if len(selections) < 2:
            continue
        best_rows = []
        for selection in selections:
            sub = group[group["selection"] == selection].copy()
            if sub.empty:
                continue
            best_rows.append(sub.loc[sub["dec_odds"].idxmax()])
        if len(best_rows) != 2:
            continue
        r1, r2 = best_rows
        inv_sum = (1 / r1["dec_odds"]) + (1 / r2["dec_odds"])
        if inv_sum < 1:
            arb_results.append({
                "sport": keys[0], "matchup": f"{keys[1]} vs {keys[2]}",
                "side_1": r1["selection"], "book_1": r1["book"], "odds_1": int(r1["odds"]),
                "side_2": r2["selection"], "book_2": r2["book"], "odds_2": int(r2["odds"]),
                "arb_profit_pct": round((1 - inv_sum) * 100, 2),
            })
    arb_df = pd.DataFrame(arb_results)
    if arb_df.empty:
        st.warning("No moneyline arbitrage opportunities detected.")
    else:
        st.dataframe(arb_df, use_container_width=True)

with tab_inj:
    st.subheader("Injuries / Starters")
    left, right = st.columns(2)
    with left:
        st.markdown("### Injuries")
        st.dataframe(injuries_df, use_container_width=True)
    with right:
        st.markdown("### Props with caution flags")
        caution_df = props_live[props_live["confidence_status"] != "✅ Clear"].copy() if not props_live.empty else pd.DataFrame()
        if caution_df.empty:
            st.info("No caution flags.")
        else:
            cols = ["player", "book", "best_book", "prop_type", "game_segment", "line", "best_line", "odds", "injury_status", "play_tier", "steam_flag", "bet_timing", "bet_size_label", "confidence_status", "confidence_warning", "edge_score"]
            st.dataframe(caution_df[cols], use_container_width=True)

with tab_template:
    st.subheader("Full Props Projection CSV Template")
    template_df = sample_full_props_projection_template()
    st.dataframe(template_df, use_container_width=True)
    csv_bytes = template_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download projection template CSV", csv_bytes, "full_props_projection_template.csv", "text/csv")
    st.write("Required columns: player, prop_type, game_segment, projection")
    st.write("Recommended columns: minutes_projection, recent_avg, pace_factor, matchup_factor, team")
