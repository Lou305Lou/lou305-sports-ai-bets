
# ============================================================
# SPORTS AI BETTING DASHBOARD — DEV MODE V11 CSV BET LOG IMPORT
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
# - AUTO-GRADING V1
# - CSV BET LOG IMPORT V1
# - Clear step markers throughout
# ============================================================

import math
from datetime import datetime, timedelta
from io import BytesIO

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Sports AI Betting Dashboard DEV MODE V11", page_icon="🏀", layout="wide")
st.title("🏀 Sports AI Betting Dashboard — DEV MODE V11")
st.caption("CSV BET LOG IMPORT V1 • Picks + tracker + auto-grading + historical import")

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
    "bet_size_units", "bet_size_label", "result", "profit_units", "actual_stat",
    "grade_source", "notes"
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
    "Jalen Brunson": {"points": 1.10, "assists": 1.12, "rebounds": 0.95, "3pt_made": 1.08, "turnovers": 1.02, "pra": 1.06},
    "Jayson Tatum": {"points": 1.08, "rebounds": 1.08, "assists": 0.95, "3pt_made": 1.12, "blocks": 1.05, "pr": 1.04},
    "Giannis Antetokounmpo": {"points": 1.14, "rebounds": 1.15, "assists": 1.00, "3pt_made": 0.70, "pra": 1.12, "ra": 1.10},
    "Jimmy Butler": {"points": 0.96, "assists": 1.02, "steals": 1.12, "3pt_made": 0.82},
    "Donovan Mitchell": {"points": 1.09, "3pt_made": 1.15, "assists": 0.94, "turnovers": 1.05, "pr": 1.05},
    "Tyrese Haliburton": {"assists": 1.20, "points": 0.97, "3pt_made": 1.00, "turnovers": 1.06, "pra": 1.10, "pa": 1.08},
    "Tyrese Maxey": {"points": 1.08, "3pt_made": 1.10, "assists": 0.96},
    "Paolo Banchero": {"points": 1.04, "rebounds": 1.05, "assists": 1.00, "turnovers": 1.03, "pra": 1.05},
    "Stephen Curry": {"points": 1.12, "3pt_made": 1.22, "assists": 0.92, "turnovers": 1.04, "pr": 1.08, "pa": 1.01},
    "LeBron James": {"points": 1.02, "rebounds": 1.03, "assists": 1.14, "3pt_made": 0.96, "pra": 1.08, "pa": 1.10},
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

def load_csv_or_empty(uploaded_file):
    if uploaded_file is None:
        return pd.DataFrame()
    try:
        if str(uploaded_file.name).lower().endswith(".csv"):
            return pd.read_csv(uploaded_file)
        return pd.read_excel(uploaded_file)
    except Exception:
        return pd.DataFrame()

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
    stat_bases = {"points": 26.5, "rebounds": 6.5, "assists": 5.5, "3pt_made": 2.5, "blocks": 0.5, "steals": 1.0, "turnovers": 2.5, "pra": 38.5, "pr": 32.5, "pa": 31.5, "ra": 12.5}
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
        ["NBA", "Jayson Tatum", "points", "full_game", 30.1, 36, 29.4, 1.03, 1.01, "Celtics"],
        ["NBA", "Stephen Curry", "3pt_made", "full_game", 4.3, 35, 4.1, 1.03, 1.01, "Warriors"],
    ]
    return pd.DataFrame(rows, columns=["sport", "player", "prop_type", "game_segment", "projection", "minutes_projection", "recent_avg", "pace_factor", "matchup_factor", "team"])

def sample_auto_grade_template():
    return pd.DataFrame([
        ["Jayson Tatum", "points", 31],
        ["Stephen Curry", "3pt_made", 5],
    ], columns=["player", "prop_type", "actual_stat"])

def sample_bet_log_import_template():
    return pd.DataFrame([
        ["2026-03-19 09:00:00", "NBA", "Jayson Tatum", "Knicks vs Celtics", "DraftKings", "full_game", "points", "Over", 26.0, -115, 30.26, 4.26, 0.74, 20.51, 85.2, "Tier 2", "➖ Stable", "Okay now", 0.75, "0.75u Strong", "Win", 0.65, 31, "Import", "Imported historical bet"],
        ["2026-03-19 09:15:00", "NBA", "Stephen Curry", "Warriors vs Lakers", "FanDuel", "full_game", "3pt_made", "Over", 4.5, 105, 4.90, 0.40, 0.58, 6.20, 71.0, "Tier 3", "📈 Steam", "Bet now", 0.25, "0.25u Small", "Loss", -0.25, 3, "Import", "Imported historical bet"],
    ], columns=["added_at", "sport", "player", "opponent", "book", "game_segment", "prop_type", "side", "line", "odds", "projection", "edge", "hit_probability", "ev_edge", "edge_score", "play_tier", "steam_flag", "bet_timing", "bet_size_units", "bet_size_label", "result", "profit_units", "actual_stat", "grade_source", "notes"])

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
    line = safe_float(row["line"])
    base_multiplier = PLAYER_PROFILE.get(player, {}).get(prop_type, 1.0)
    pace = TEAM_MATCHUP.get(team, {}).get("pace", 1.0)
    matchup = TEAM_MATCHUP.get(team, {}).get("matchup", 1.0)
    mins = 35.0
    deterministic_bump = (((sum(ord(c) for c in player + prop_type + team) % 9) - 4) * 0.012 * dev_strength)
    projection = line * base_multiplier * pace * matchup * (1 + deterministic_bump)
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
# STEP 8 — SCORING / SHOPPING / STEAM / BET SIZING
# ============================================================

def hit_probability_from_edge(row):
    line = safe_float(row.get("line"))
    proj = safe_float(row.get("projection"))
    prop_type = normalize_text(row.get("prop_type", "points"))
    if pd.isna(line) or pd.isna(proj):
        return np.nan
    sigma_map = {"points": 6.5, "rebounds": 3.0, "assists": 3.2, "3pt_made": 1.6, "turnovers": 1.8, "pra": 8.4, "pr": 6.8, "pa": 7.0, "ra": 5.2}
    sigma = sigma_map.get(prop_type, 5.5)
    z = (proj - line) / sigma if sigma > 0 else 0
    prob_over = 0.5 * (1 + math.erf(z / math.sqrt(2)))
    if SHARP_MODE:
        prob_over = max(0.05, min(0.85, prob_over))
    if SUPER_SHARP_MODE:
        prob_over = max(SUPER_SHARP_HIT_CLAMP["min"], min(SUPER_SHARP_HIT_CLAMP["max"], prob_over))
    return max(0.01, min(0.99, prob_over))

def confidence_warning_label(row):
    warnings = []
    if abs(safe_float(row.get("projection")) - safe_float(row.get("line"))) < 0.4:
        warnings.append("Thin model edge")
    return "Clear" if not warnings else " | ".join(warnings)

def confidence_status(row):
    note = confidence_warning_label(row)
    return "✅ Clear" if note == "Clear" else "🟡 Watch"

def compute_prop_scores(df):
    out = prepare_props_df(df)
    if out.empty:
        return out
    out["projection"] = np.where(pd.isna(out["projection"]), out["line"], out["projection"])
    out["proj_edge"] = out["projection"] - out["line"]
    out["proj_edge_abs"] = out["proj_edge"].abs()
    out["recommended_side"] = np.where(out["projection"] > out["line"], "Over", "Under")
    out["hit_prob_over"] = out.apply(hit_probability_from_edge, axis=1)
    out["hit_prob_under"] = 1 - out["hit_prob_over"]
    out["hit_probability"] = np.where(out["recommended_side"] == "Over", out["hit_prob_over"], out["hit_prob_under"])
    out["book_implied_prob"] = out["odds"].apply(implied_prob_american)
    out["model_fair_odds"] = out["hit_probability"].apply(prob_to_american)
    out["expected_value_edge"] = ((out["hit_probability"] - out["book_implied_prob"]) * 100).round(2)
    out["confidence_warning"] = out.apply(confidence_warning_label, axis=1)
    out["confidence_status"] = out.apply(confidence_status, axis=1)
    out["edge_score"] = np.clip((out["proj_edge_abs"] * 10) + ((out["hit_probability"] - 0.5) * 60) + np.clip(out["expected_value_edge"], 0, 12), 0, 100).round(1)
    out["bet_grade"] = out["edge_score"].apply(edge_bucket)
    tiers = out.apply(classify_play_tier, axis=1, result_type="expand")
    out["play_tier"] = tiers[0]
    out["tier_reason"] = tiers[1]
    return out

def apply_line_shopping(df):
    out = prepare_props_df(df)
    if out.empty:
        return out
    result_parts = []
    for _, group in out.groupby(["player", "prop_type", "game_segment", "recommended_side"], dropna=False):
        side = group["recommended_side"].iloc[0]
        if side == "Over":
            best_group = group.sort_values(["line", "odds", "edge_score"], ascending=[True, False, False])
        else:
            best_group = group.sort_values(["line", "odds", "edge_score"], ascending=[False, False, False])
        best_row = best_group.iloc[0]
        group = group.copy()
        group["best_book"] = best_row["book"]
        group["best_line"] = best_row["line"]
        group["best_odds"] = best_row["odds"]
        group["line_edge_diff"] = group["line"] - best_row["line"] if side == "Over" else best_row["line"] - group["line"]
        group["tier_improved"] = np.where(group["book"] == best_row["book"], "Best current book", "NO")
        result_parts.append(group)
    return pd.concat(result_parts, ignore_index=True)

def create_live_snapshot_variant(df):
    out = prepare_props_df(df).copy()
    rows = []
    for _, row in out.iterrows():
        key_num = sum(ord(c) for c in f"{row['player']}{row['prop_type']}{row['book']}")
        variant = (key_num % 7) - 3
        new_row = row.copy()
        if row["recommended_side"] == "Over":
            new_row["line"] = safe_float(row["line"]) + (0.5 if variant in [2, 3] else (-0.5 if variant in [-2, -3] else 0))
            new_row["odds"] = safe_float(row["odds"]) + (-10 if variant in [2,3] else (10 if variant in [-2,-3] else 0))
        rows.append(new_row)
    return prepare_props_df(pd.DataFrame(rows))

def apply_steam_signals(current_df, previous_df):
    cur = prepare_props_df(current_df).copy()
    prev = prepare_props_df(previous_df).copy()
    if cur.empty or prev.empty:
        cur["line_move"] = 0.0
        cur["odds_move_signal"] = 0.0
        cur["steam_flag"] = "➖ Stable"
        cur["bet_timing"] = "Okay now"
        cur["movement_summary"] = "No prior snapshot"
        return cur
    prev_small = prev[["player", "prop_type", "game_segment", "book", "recommended_side", "line", "odds"]].rename(columns={"line":"prev_line","odds":"prev_odds"})
    merged = cur.merge(prev_small, on=["player","prop_type","game_segment","book","recommended_side"], how="left")
    line_move = merged["line"] - merged["prev_line"]
    odds_move = merged["prev_odds"] - merged["odds"]
    merged["line_move"] = line_move.fillna(0)
    merged["odds_move_signal"] = odds_move.fillna(0)
    merged["steam_flag"] = np.where((merged["line_move"] >= 0.5) | (merged["odds_move_signal"] >= 8), "📈 Steam", "➖ Stable")
    merged["bet_timing"] = np.where(merged["steam_flag"] == "📈 Steam", "Bet now", "Okay now")
    merged["movement_summary"] = "Line move " + merged["line_move"].round(1).astype(str) + " | Odds move " + merged["odds_move_signal"].round(0).astype(int).astype(str)
    return prepare_props_df(merged.drop(columns=["prev_line","prev_odds"]))

def kelly_fraction_from_row(row):
    p = safe_float(row.get("hit_probability"))
    odds = safe_float(row.get("odds"))
    dec = american_to_decimal(odds)
    if pd.isna(p) or pd.isna(dec) or dec <= 1:
        return 0.0
    b = dec - 1
    q = 1 - p
    return max(0.0, float((b * p - q) / b))

def bet_size_from_row(row):
    tier = str(row.get("play_tier", "Tier 3"))
    steam = str(row.get("steam_flag", ""))
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
    if steam == "📈 Steam" and tier in ["Tier 1", "Tier 2"]:
        units += 0.25; reasons.append("Steam boost")
    if ev >= 12 and score >= 85:
        units += 0.25; reasons.append("High EV/score boost")
    if kelly > 0:
        kelly_units_cap = min(1.25, max(0.25, round((kelly * 0.5) / 0.01) * 0.25))
        units = min(units, kelly_units_cap); reasons.append("Kelly cap")
    units = max(0.0, min(1.25, round(units * 4) / 4))
    label = "Pass"
    if units >= 1.0: label = "1.0u+ Core"
    elif units >= 0.75: label = "0.75u Strong"
    elif units >= 0.5: label = "0.5u Standard"
    elif units >= 0.25: label = "0.25u Small"
    return units, label, " | ".join(reasons)

def apply_bet_sizing(df):
    out = prepare_props_df(df).copy()
    out["kelly_fraction"] = out.apply(kelly_fraction_from_row, axis=1)
    sizes = out.apply(bet_size_from_row, axis=1, result_type="expand")
    out["bet_size_units"] = sizes[0]
    out["bet_size_label"] = sizes[1]
    out["bet_size_reason"] = sizes[2]
    return out

# ============================================================
# STEP 9 — BET TRACKER + AUTO-GRADING
# ============================================================

def tracker_add_bet(row):
    init_tracker_state()
    tracker = st.session_state["bet_tracker_df"].copy()
    bet_id = f"BET-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')[:-3]}"
    new_row = {
        "bet_id": bet_id, "added_at": current_ts_str(), "sport": row["sport"], "player": row["player"],
        "opponent": row["opponent"], "book": row["book"], "game_segment": row["game_segment"],
        "prop_type": row["prop_type"], "side": row["recommended_side"], "line": safe_float(row["line"]),
        "odds": safe_float(row["odds"]), "projection": safe_float(row["projection"]), "edge": safe_float(row["proj_edge"]),
        "hit_probability": safe_float(row["hit_probability"]), "ev_edge": safe_float(row["expected_value_edge"]),
        "edge_score": safe_float(row["edge_score"]), "play_tier": row["play_tier"], "steam_flag": row["steam_flag"],
        "bet_timing": row["bet_timing"], "bet_size_units": safe_float(row["bet_size_units"]),
        "bet_size_label": row["bet_size_label"], "result": "Open", "profit_units": np.nan,
        "actual_stat": np.nan, "grade_source": "", "notes": ""
    }
    st.session_state["bet_tracker_df"] = pd.concat([pd.DataFrame([new_row]), tracker], ignore_index=True)

def tracker_update_results(df):
    tracker = st.session_state["bet_tracker_df"].copy()
    for _, upd in df.iterrows():
        mask = tracker["bet_id"] == upd["bet_id"]
        tracker.loc[mask, "result"] = upd["result"]
        tracker.loc[mask, "notes"] = upd["notes"]
        tracker.loc[mask, "actual_stat"] = pd.to_numeric(pd.Series([upd["actual_stat"]]), errors="coerce").iloc[0]
        tracker.loc[mask, "grade_source"] = "Manual"
        tracker.loc[mask, "profit_units"] = profit_units_from_result(
            upd["result"], tracker.loc[mask, "odds"].iloc[0], tracker.loc[mask, "bet_size_units"].iloc[0]
        )
    st.session_state["bet_tracker_df"] = tracker

def grade_result_from_actual(side, line, actual_stat):
    line = safe_float(line); actual_stat = safe_float(actual_stat)
    if pd.isna(line) or pd.isna(actual_stat):
        return "Open"
    if actual_stat == line:
        return "Push"
    return "Win" if ((side == "Over" and actual_stat > line) or (side != "Over" and actual_stat < line)) else "Loss"

def auto_grade_tracker_from_stats(stats_df):
    tracker = st.session_state["bet_tracker_df"].copy()
    stats = stats_df.copy()
    stats.columns = [c.strip().lower() for c in stats.columns]
    required = {"player", "prop_type", "actual_stat"}
    if not required.issubset(set(stats.columns)):
        return -1
    stats["player"] = stats["player"].astype(str)
    stats["prop_type"] = stats["prop_type"].astype(str).apply(normalize_text)
    stats["actual_stat"] = pd.to_numeric(stats["actual_stat"], errors="coerce")
    updates = 0
    for idx, row in tracker.iterrows():
        if row["result"] != "Open":
            continue
        matches = stats[(stats["player"] == str(row["player"])) & (stats["prop_type"] == normalize_text(row["prop_type"]))]
        if matches.empty:
            continue
        actual = matches.iloc[-1]["actual_stat"]
        result = grade_result_from_actual(row["side"], row["line"], actual)
        if result != "Open":
            tracker.loc[idx, "actual_stat"] = actual
            tracker.loc[idx, "result"] = result
            tracker.loc[idx, "grade_source"] = "Auto"
            tracker.loc[idx, "profit_units"] = profit_units_from_result(result, row["odds"], row["bet_size_units"])
            updates += 1
    st.session_state["bet_tracker_df"] = tracker
    return updates

def tracker_summary(df):
    if df.empty:
        return {"bets": 0, "open": 0, "graded": 0, "wins": 0, "losses": 0, "pushes": 0, "win_rate": 0.0, "units": 0.0, "roi": 0.0}
    graded = df[df["result"].isin(["Win", "Loss", "Push"])].copy()
    wins = int((graded["result"] == "Win").sum())
    losses = int((graded["result"] == "Loss").sum())
    pushes = int((graded["result"] == "Push").sum())
    risked = graded["bet_size_units"].fillna(0).sum()
    units = graded["profit_units"].fillna(0).sum()
    return {
        "bets": len(df), "open": int((df["result"] == "Open").sum()), "graded": len(graded),
        "wins": wins, "losses": losses, "pushes": pushes,
        "win_rate": (wins / max(1, wins + losses)) * 100,
        "units": units, "roi": (units / max(1e-9, risked)) * 100 if risked > 0 else 0.0
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
            group_col: key, "Bets": len(grp), "Wins": wins, "Losses": losses, "Pushes": pushes,
            "Win %": round((wins / max(1, wins + losses)) * 100, 1),
            "Units": round(units, 2), "ROI %": round((units / max(1e-9, risked)) * 100, 1) if risked > 0 else 0.0
        })
    return pd.DataFrame(rows).sort_values(["Units", "ROI %"], ascending=[False, False])

# ============================================================
# STEP 10 — CSV BET LOG IMPORT V1
# ============================================================

def normalize_import_log(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=TRACKER_COLUMNS)
    out = df.copy()
    out.columns = [c.strip().lower() for c in out.columns]

    rename_map = {
        "segment": "game_segment",
        "market": "prop_type",
        "recommended_side": "side",
        "units": "bet_size_units",
        "stake_units": "bet_size_units",
        "unit_label": "bet_size_label",
        "ev": "ev_edge",
        "score": "edge_score",
        "tier": "play_tier",
        "steam": "steam_flag",
        "timing": "bet_timing",
        "actual": "actual_stat",
        "grade": "result",
    }
    for old, new in rename_map.items():
        if old in out.columns and new not in out.columns:
            out = out.rename(columns={old: new})

    defaults = {c: np.nan for c in TRACKER_COLUMNS}
    defaults.update({
        "bet_id": "", "added_at": current_ts_str(), "sport": "", "player": "", "opponent": "", "book": "",
        "game_segment": "full_game", "prop_type": "", "side": "Over", "play_tier": "", "steam_flag": "",
        "bet_timing": "", "bet_size_label": "", "result": "Open", "grade_source": "Import", "notes": ""
    })
    out = add_missing_cols(out, defaults)

    text_cols = ["bet_id", "added_at", "sport", "player", "opponent", "book", "game_segment", "prop_type", "side", "play_tier", "steam_flag", "bet_timing", "bet_size_label", "result", "grade_source", "notes"]
    for col in text_cols:
        out[col] = out[col].fillna("").astype(str)

    num_cols = ["line", "odds", "projection", "edge", "hit_probability", "ev_edge", "edge_score", "bet_size_units", "profit_units", "actual_stat"]
    for col in num_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    out["prop_type"] = out["prop_type"].apply(normalize_text)
    out["game_segment"] = out["game_segment"].apply(normalize_text)
    out["result"] = out["result"].replace({"win": "Win", "loss": "Loss", "push": "Push", "open": "Open", "WIN":"Win","LOSS":"Loss","PUSH":"Push","OPEN":"Open"})
    out["grade_source"] = np.where(out["grade_source"].astype(str).str.len() == 0, "Import", out["grade_source"])

    out["bet_id"] = np.where(
        out["bet_id"].astype(str).str.len() > 0,
        out["bet_id"].astype(str),
        ["IMPORT-" + datetime.now().strftime("%Y%m%d") + f"-{i+1:04d}" for i in range(len(out))]
    )

    missing_profit = out["profit_units"].isna() & out["result"].isin(["Win", "Loss", "Push"])
    out.loc[missing_profit, "profit_units"] = out.loc[missing_profit].apply(
        lambda r: profit_units_from_result(r["result"], r["odds"], r["bet_size_units"]), axis=1
    )

    return out[TRACKER_COLUMNS].copy()

def import_bet_log_into_tracker(import_df, replace_existing=False):
    init_tracker_state()
    normalized = normalize_import_log(import_df)
    if normalized.empty:
        return 0
    current = st.session_state["bet_tracker_df"].copy()

    if replace_existing:
        st.session_state["bet_tracker_df"] = normalized.copy()
        return len(normalized)

    combined = pd.concat([current, normalized], ignore_index=True)
    combined = combined.drop_duplicates(subset=["bet_id"], keep="first")
    st.session_state["bet_tracker_df"] = combined
    return len(normalized)

# ============================================================
# STEP 11 — FILTERS / DISPLAY HELPERS
# ============================================================

def best_line_shop(df):
    out = prepare_props_df(df)
    if out.empty:
        return out
    rows = []
    for _, group in out.groupby(["player", "prop_type", "game_segment", "recommended_side"], dropna=False):
        side = group["recommended_side"].iloc[0]
        if side == "Over":
            group = group.sort_values(["line", "odds", "edge_score"], ascending=[True, False, False])
        else:
            group = group.sort_values(["line", "odds", "edge_score"], ascending=[False, False, False])
        rows.append(group.iloc[0])
    return pd.DataFrame(rows).reset_index(drop=True).sort_values(["bet_size_units", "edge_score"], ascending=[False, False])

def filter_props_base(df, sport="All", segment="All", starters_only=True, confirmed_only=False, min_odds=-300, max_odds=200, min_edge=60, min_hit_prob=50, min_ev=-5, book="All", prop_type="All", tier="All", improved="All", steam="All", min_units=0.0):
    out = prepare_props_df(df)
    if sport != "All": out = out[out["sport"] == sport]
    if segment != "All": out = out[out["game_segment"] == segment]
    if prop_type != "All": out = out[out["prop_type"] == prop_type]
    if book != "All": out = out[out["book"] == book]
    if tier != "All": out = out[out["play_tier"] == tier]
    if steam != "All": out = out[out["steam_flag"] == steam]
    out = out[out["bet_size_units"] >= min_units]
    out = out[(out["odds"] >= min_odds) & (out["odds"] <= max_odds)]
    out = out[out["edge_score"] >= min_edge]
    out = out[(out["hit_probability"] * 100) >= min_hit_prob]
    out = out[out["expected_value_edge"] >= min_ev]
    return out.sort_values(["bet_size_units", "edge_score"], ascending=[False, False])

def build_best_bets_dashboard(df):
    out = prepare_props_df(df)
    cols = ["player", "opponent", "book", "best_book", "game_segment", "prop_type", "recommended_side", "line", "best_line", "odds", "best_odds", "projection", "proj_edge", "hit_probability", "expected_value_edge", "edge_score", "play_tier", "steam_flag", "bet_timing", "bet_size_units", "bet_size_label"]
    if out.empty:
        return pd.DataFrame(columns=cols)
    return out.sort_values(["bet_size_units", "edge_score"], ascending=[False, False])[cols].head(20).copy()

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
# STEP 12 — SIDEBAR CONTROLS
# ============================================================

st.sidebar.header("DEV MODE V11")
st.sidebar.success("CSV BET LOG IMPORT V1 enabled.")
sport_name = st.sidebar.selectbox("Sport", SPORTS, index=0)
best_shop_only = st.sidebar.checkbox("Best line shop only", value=True)
projection_mode = st.sidebar.selectbox("Projection source", ["Auto Projections V1", "Upload CSV Override"], index=0)
dev_strength = st.sidebar.slider("Auto projection aggressiveness", 0.50, 1.50, 1.00, 0.05)
projection_file = st.sidebar.file_uploader("Optional projection CSV override", type=["csv", "xlsx"])

# ============================================================
# STEP 13 — LOAD / BUILD DATA
# ============================================================

init_tracker_state()

props_df = prepare_props_df(make_sample_props_df())
injuries_df = make_sample_injuries_df()
proj_df = prepare_projection_overlay_df(load_csv_or_empty(projection_file))

props_df = props_df[props_df["sport"] == sport_name].copy()
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
    ["Mode", "DEV MODE V11", "Active"],
    ["Projection Source", projection_mode, "Active"],
    ["CSV Bet Log Import V1", "ON", "Active"],
    ["Props Rows", len(props_live), "Sample"],
    ["Tracked Bets", len(st.session_state["bet_tracker_df"]), "Session"],
], columns=["Feed", "Value", "Status"])

# ============================================================
# STEP 14 — UI TABS
# ============================================================

tab_home, tab_best, tab_sections, tab_tracker, tab_import, tab_inj, tab_template = st.tabs([
    "Home", "Best Bets", "Prop Sections", "Bet Tracker", "Bet Log Import", "Injuries / Starters", "Templates"
])

with tab_home:
    st.subheader("DEV MODE V11 Home")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Props Rows", len(props_live))
    c2.metric("Books", props_live["book"].nunique() if not props_live.empty else 0)
    c3.metric("Tracked Bets", len(st.session_state["bet_tracker_df"]))
    c4.metric("Imported Bets", int((st.session_state["bet_tracker_df"]["grade_source"] == "Import").sum()) if not st.session_state["bet_tracker_df"].empty else 0)
    st.dataframe(source_status, use_container_width=True)

    tracker_stats = tracker_summary(st.session_state["bet_tracker_df"])
    a, b, c, d = st.columns(4)
    a.metric("Open Bets", tracker_stats["open"])
    b.metric("Graded Bets", tracker_stats["graded"])
    c.metric("Units", f"{tracker_stats['units']:.2f}")
    d.metric("ROI %", f"{tracker_stats['roi']:.1f}%")

with tab_best:
    st.subheader("Auto Best Bets Board")
    base_df = props_shop.copy() if best_shop_only else props_live.copy()

    sport_opts = ["All"] + sorted(base_df["sport"].dropna().astype(str).unique().tolist()) if not base_df.empty else ["All"]
    segment_opts = ["All"] + sorted(base_df["game_segment"].dropna().astype(str).unique().tolist()) if not base_df.empty else ["All"]
    prop_opts = ["All"] + sorted(base_df["prop_type"].dropna().astype(str).unique().tolist()) if not base_df.empty else ["All"]
    book_opts = ["All"] + sorted(base_df["book"].dropna().astype(str).unique().tolist()) if not base_df.empty else ["All"]
    tier_opts = ["All", "Tier 1", "Tier 2", "Tier 3"]
    steam_opts = ["All", "📈 Steam", "➖ Stable"]

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1: selected_sport = st.selectbox("Sport", sport_opts)
    with c2: selected_segment = st.selectbox("Segment", segment_opts)
    with c3: selected_prop = st.selectbox("Prop Type", prop_opts)
    with c4: selected_book = st.selectbox("Book", book_opts)
    with c5: selected_tier = st.selectbox("Tier", tier_opts)
    with c6: selected_steam = st.selectbox("Steam", steam_opts)

    c7, c8, c9, c10 = st.columns(4)
    with c7: min_edge = st.slider("Min Edge Score", 0, 100, 60, 5)
    with c8: min_hit = st.slider("Min Hit %", 50, 95, 54, 1)
    with c9: min_ev = st.slider("Min EV Edge %", -10, 25, 0, 1)
    with c10: min_units = st.slider("Min Units", 0.0, 1.25, 0.25, 0.25)

    filtered = filter_props_base(base_df, selected_sport, selected_segment, True, False, -300, 200, min_edge, min_hit, min_ev, selected_book, selected_prop, selected_tier, "All", selected_steam, min_units)

    if filtered.empty:
        st.warning("No props match the current filters")
    else:
        for idx, (_, row) in enumerate(filtered.head(10).iterrows(), start=1):
            render_top_play_card(row, idx)

        add_options = [f"{r.player} | {r.recommended_side} {r.line} {r.prop_type} | {r.book} | {r.bet_size_units:.2f}u" for _, r in filtered.head(20).iterrows()]
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
        st.dataframe(format_props_table(props_live[["player","book","prop_type","recommended_side","line","projection","proj_edge","hit_probability","expected_value_edge","edge_score","play_tier","steam_flag","bet_size_units","bet_size_label"]]), use_container_width=True)

with tab_tracker:
    st.subheader("Bet Tracker")
    tracker_df = st.session_state["bet_tracker_df"].copy()
    stats = tracker_summary(tracker_df)
    t1, t2, t3, t4, t5 = st.columns(5)
    t1.metric("Total Bets", stats["bets"])
    t2.metric("Open", stats["open"])
    t3.metric("Win %", f"{stats['win_rate']:.1f}%")
    t4.metric("Units", f"{stats['units']:.2f}")
    t5.metric("ROI %", f"{stats['roi']:.1f}%")

    if tracker_df.empty:
        st.info("No tracked bets yet.")
    else:
        display_df = tracker_df.copy()
        display_df["hit_probability"] = (pd.to_numeric(display_df["hit_probability"], errors="coerce") * 100).round(1)
        st.dataframe(display_df, use_container_width=True)

        st.markdown("### Manual grading")
        open_bets = tracker_df[tracker_df["result"] == "Open"].copy()
        if open_bets.empty:
            st.info("No open bets to grade.")
        else:
            grade_df = open_bets[["bet_id", "player", "prop_type", "side", "line", "odds", "bet_size_units", "actual_stat", "result", "notes"]].copy()
            grade_df["result"] = "Open"
            edited = st.data_editor(
                grade_df,
                num_rows="fixed",
                use_container_width=True,
                column_config={
                    "result": st.column_config.SelectboxColumn("result", options=["Open", "Win", "Loss", "Push"]),
                    "notes": st.column_config.TextColumn("notes")
                },
                key="grade_editor_v11"
            )
            if st.button("Save manual grading updates"):
                tracker_update_results(edited[["bet_id", "actual_stat", "result", "notes"]])
                st.success("Tracker updated")

        st.markdown("### Auto-grading")
        auto_template = sample_auto_grade_template()
        st.dataframe(auto_template, use_container_width=True)
        auto_csv = auto_template.to_csv(index=False).encode("utf-8")
        st.download_button("Download auto-grade template CSV", auto_csv, "auto_grade_template.csv", "text/csv")
        auto_file = st.file_uploader("Upload stats file for auto-grading", type=["csv", "xlsx"], key="auto_grade_uploader_v11")
        if auto_file is not None:
            auto_df = load_csv_or_empty(auto_file)
            if not auto_df.empty:
                st.dataframe(auto_df, use_container_width=True)
                if st.button("Run auto-grading"):
                    updated = auto_grade_tracker_from_stats(auto_df)
                    if updated == -1:
                        st.error("Stats file must include: player, prop_type, actual_stat")
                    else:
                        st.success(f"Auto-graded {updated} bet(s).")

        st.markdown("### Performance by tier")
        st.dataframe(tracker_group_summary(st.session_state["bet_tracker_df"], "play_tier"), use_container_width=True)
        st.markdown("### Performance by steam flag")
        st.dataframe(tracker_group_summary(st.session_state["bet_tracker_df"], "steam_flag"), use_container_width=True)
        st.markdown("### Performance by prop type")
        st.dataframe(tracker_group_summary(st.session_state["bet_tracker_df"], "prop_type"), use_container_width=True)
        st.markdown("### Performance by book")
        st.dataframe(tracker_group_summary(st.session_state["bet_tracker_df"], "book"), use_container_width=True)

        csv_bytes = st.session_state["bet_tracker_df"].to_csv(index=False).encode("utf-8")
        st.download_button("Download bet tracker CSV", csv_bytes, "bet_tracker_v11.csv", "text/csv")

        xlsx_buffer = BytesIO()
        with pd.ExcelWriter(xlsx_buffer, engine="openpyxl") as writer:
            st.session_state["bet_tracker_df"].to_excel(writer, sheet_name="Bets", index=False)
            tracker_group_summary(st.session_state["bet_tracker_df"], "play_tier").to_excel(writer, sheet_name="By Tier", index=False)
            tracker_group_summary(st.session_state["bet_tracker_df"], "steam_flag").to_excel(writer, sheet_name="By Steam", index=False)
            tracker_group_summary(st.session_state["bet_tracker_df"], "prop_type").to_excel(writer, sheet_name="By Prop", index=False)
            tracker_group_summary(st.session_state["bet_tracker_df"], "book").to_excel(writer, sheet_name="By Book", index=False)
        st.download_button("Download bet tracker Excel", xlsx_buffer.getvalue(), "bet_tracker_v11.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

with tab_import:
    st.subheader("CSV BET LOG IMPORT V1")
    template_df = sample_bet_log_import_template()
    st.markdown("### Import template preview")
    st.dataframe(template_df, use_container_width=True)
    template_csv = template_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download bet log import template CSV", template_csv, "bet_log_import_template.csv", "text/csv")

    import_file = st.file_uploader("Upload historical bet log CSV or Excel", type=["csv", "xlsx"], key="bet_log_import_uploader")
    replace_existing = st.checkbox("Replace existing tracker with imported file", value=False)

    if import_file is not None:
        import_df = load_csv_or_empty(import_file)
        if not import_df.empty:
            st.markdown("### Imported file preview")
            st.dataframe(import_df, use_container_width=True)
            normalized_preview = normalize_import_log(import_df)
            st.markdown("### Normalized import preview")
            st.dataframe(normalized_preview, use_container_width=True)
            if st.button("Import bet log into tracker"):
                count = import_bet_log_into_tracker(import_df, replace_existing=replace_existing)
                st.success(f"Imported {count} bet(s) into tracker.")

with tab_inj:
    st.subheader("Injuries / Starters")
    st.dataframe(injuries_df, use_container_width=True)

with tab_template:
    st.subheader("Templates")
    proj_template = sample_full_props_projection_template()
    st.markdown("### Projection template")
    st.dataframe(proj_template, use_container_width=True)
    st.download_button("Download projection template CSV", proj_template.to_csv(index=False).encode("utf-8"), "full_props_projection_template.csv", "text/csv")
    st.markdown("### Auto-grade template")
    ag_template = sample_auto_grade_template()
    st.dataframe(ag_template, use_container_width=True)
    st.download_button("Download auto-grade template CSV", ag_template.to_csv(index=False).encode("utf-8"), "auto_grade_template.csv", "text/csv")
