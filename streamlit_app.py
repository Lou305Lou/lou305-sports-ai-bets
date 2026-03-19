
import math
from datetime import datetime
from typing import Dict, Optional

import numpy as np
import pandas as pd
import requests
import streamlit as st


# =========================================================
# PAGE SETUP
# =========================================================
st.set_page_config(
    page_title="Sports AI Betting Dashboard V5",
    page_icon="🏀",
    layout="wide",
)

st.title("🏀 Sports AI Betting Dashboard V5")
st.caption("API-Ready Structure • Odds API • Injury Feed • Snapshots • Auto Best Bets")


# =========================================================
# CONFIG / CONSTANTS
# =========================================================
DEFAULT_TIMEOUT = 20

SUPPORTED_PROP_SECTIONS = [
    ("Points", "points"),
    ("Rebounds", "rebounds"),
    ("Assists", "assists"),
    ("3PT Made", "3pt_made"),
]

# Example placeholder endpoints.
# Replace these in Streamlit secrets or sidebar fields with your real providers.
DEFAULT_ODDS_API_URL = "https://api.example.com/odds"
DEFAULT_PROPS_API_URL = "https://api.example.com/props"
DEFAULT_INJURY_API_URL = "https://api.example.com/injuries"


# =========================================================
# HELPERS
# =========================================================
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


def american_to_decimal(odds):
    try:
        odds = float(odds)
        if odds > 0:
            return 1 + (odds / 100)
        return 1 + (100 / abs(odds))
    except Exception:
        return np.nan


def implied_prob_american(odds):
    try:
        odds = float(odds)
        if odds > 0:
            return 100 / (odds + 100)
        return abs(odds) / (abs(odds) + 100)
    except Exception:
        return np.nan


def prob_to_american(prob):
    try:
        prob = float(prob)
        if prob <= 0 or prob >= 1:
            return np.nan
        if prob >= 0.5:
            return int(round(-(prob / (1 - prob)) * 100))
        return int(round(((1 - prob) / prob) * 100))
    except Exception:
        return np.nan


def clean_market_name(x):
    x = normalize_text(x)
    mapping = {
        "ml": "moneyline",
        "moneyline": "moneyline",
        "spread": "spreads",
        "spreads": "spreads",
        "total": "totals",
        "totals": "totals",
    }
    return mapping.get(x, x)


def add_missing_cols(df, cols_with_defaults):
    for col, default in cols_with_defaults.items():
        if col not in df.columns:
            df[col] = default
    return df


def edge_bucket(score):
    if score >= 86:
        return "🟢 A"
    if score >= 76:
        return "🟢 B"
    if score >= 66:
        return "🟡 C"
    return "🔴 Pass"


def current_ts_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def build_headers(api_key: str = ""):
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def fetch_json(url: str, api_key: str = "", params: Optional[dict] = None):
    if not url:
        return None, "Missing URL"
    try:
        response = requests.get(
            url,
            headers=build_headers(api_key),
            params=params or {},
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        return response.json(), None
    except Exception as e:
        return None, str(e)


def pull_list_from_json(payload):
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ["data", "results", "items", "rows", "props", "odds", "injuries"]:
            if key in payload and isinstance(payload[key], list):
                return payload[key]
    return []


# =========================================================
# SAMPLE DATA
# =========================================================
def sample_odds_data():
    rows = [
        ["NBA", "Heat", "Celtics", "BetMGM", "moneyline", np.nan, np.nan, "Heat", +145],
        ["NBA", "Heat", "Celtics", "DraftKings", "moneyline", np.nan, np.nan, "Celtics", -135],
        ["NBA", "Heat", "Celtics", "FanDuel", "spreads", -4.5, np.nan, "Celtics", -110],
        ["NBA", "Heat", "Celtics", "Caesars", "spreads", +6.5, np.nan, "Heat", -110],
        ["NBA", "Lakers", "Suns", "BookA", "moneyline", np.nan, np.nan, "Lakers", +140],
        ["NBA", "Lakers", "Suns", "BookB", "spreads", -2.5, np.nan, "Suns", -110],
    ]
    return pd.DataFrame(rows, columns=[
        "sport", "team_a", "team_b", "book", "market", "point", "total", "selection", "odds"
    ])


def sample_props_data():
    rows = [
        ["NBA", "Jalen Brunson", "Knicks", "Celtics", 1, "confirmed", 1, "points", 27.5, 31.2, 36, 32.1, 5, 1.07, 1.03, -115, "full_game", "DraftKings", "2026-03-19 08:00:00"],
        ["NBA", "Jalen Brunson", "Knicks", "Celtics", 1, "confirmed", 1, "points", 28.5, 31.2, 36, 32.1, 5, 1.07, 1.03, +100, "full_game", "FanDuel", "2026-03-19 08:00:00"],
        ["NBA", "Jayson Tatum", "Celtics", "Knicks", 1, "confirmed", 1, "rebounds", 8.5, 9.7, 37, 10.2, 5, 1.04, 1.02, -105, "full_game", "BetMGM", "2026-03-19 08:00:00"],
        ["NBA", "Tyrese Haliburton", "Pacers", "Cavs", 1, "expected", 1, "assists", 10.5, 11.8, 35, 12.1, 5, 1.05, 1.03, +125, "full_game", "FanDuel", "2026-03-19 08:00:00"],
        ["NBA", "Stephen Curry", "Warriors", "Lakers", 1, "confirmed", 1, "3pt_made", 1.5, 2.2, 10, 2.4, 5, 1.03, 1.01, -120, "1q", "DraftKings", "2026-03-19 08:00:00"],
    ]
    return pd.DataFrame(rows, columns=[
        "sport", "player", "team", "opponent", "is_starter", "starter_status", "starter_confirmed",
        "prop_type", "line", "projection", "minutes_projection", "recent_avg", "last_5_games",
        "pace_factor", "matchup_factor", "odds", "game_segment", "book", "source_time"
    ])


def sample_injuries_data():
    rows = [
        ["NBA", "Knicks", "Jalen Brunson", "available", "confirmed", "", "2026-03-19 08:00:00"],
        ["NBA", "Pacers", "Tyrese Haliburton", "questionable", "expected", "ankle", "2026-03-19 08:00:00"],
        ["NBA", "Warriors", "Stephen Curry", "available", "confirmed", "", "2026-03-19 08:00:00"],
    ]
    return pd.DataFrame(rows, columns=[
        "sport", "team", "player", "injury_status", "starter_status", "injury_note", "source_time"
    ])


# =========================================================
# API PARSERS
# Replace these with your provider-specific field mappings later
# =========================================================
def parse_odds_api_payload(payload, fallback_sport="NBA"):
    rows = []
    for item in pull_list_from_json(payload):
        rows.append({
            "sport": item.get("sport", fallback_sport),
            "team_a": item.get("team_a", item.get("home_team", "")),
            "team_b": item.get("team_b", item.get("away_team", "")),
            "book": item.get("book", item.get("sportsbook", "API")),
            "market": item.get("market", "moneyline"),
            "point": item.get("point", np.nan),
            "total": item.get("total", np.nan),
            "selection": item.get("selection", item.get("side", "")),
            "odds": item.get("odds", np.nan),
        })
    return pd.DataFrame(rows)


def parse_props_api_payload(payload, fallback_sport="NBA"):
    rows = []
    for item in pull_list_from_json(payload):
        rows.append({
            "sport": item.get("sport", fallback_sport),
            "player": item.get("player", ""),
            "team": item.get("team", ""),
            "opponent": item.get("opponent", ""),
            "is_starter": item.get("is_starter", 1),
            "starter_status": item.get("starter_status", "unknown"),
            "starter_confirmed": item.get("starter_confirmed", 0),
            "prop_type": item.get("prop_type", item.get("market", "points")),
            "line": item.get("line", np.nan),
            "projection": item.get("projection", np.nan),
            "minutes_projection": item.get("minutes_projection", np.nan),
            "recent_avg": item.get("recent_avg", np.nan),
            "last_5_games": item.get("last_5_games", 5),
            "pace_factor": item.get("pace_factor", 1.0),
            "matchup_factor": item.get("matchup_factor", 1.0),
            "odds": item.get("odds", np.nan),
            "game_segment": item.get("game_segment", "full_game"),
            "book": item.get("book", item.get("sportsbook", "API")),
            "source_time": item.get("source_time", current_ts_str()),
        })
    return pd.DataFrame(rows)


def parse_injury_api_payload(payload, fallback_sport="NBA"):
    rows = []
    for item in pull_list_from_json(payload):
        rows.append({
            "sport": item.get("sport", fallback_sport),
            "team": item.get("team", ""),
            "player": item.get("player", ""),
            "injury_status": item.get("injury_status", item.get("status", "unknown")),
            "starter_status": item.get("starter_status", "unknown"),
            "injury_note": item.get("injury_note", item.get("note", "")),
            "source_time": item.get("source_time", current_ts_str()),
        })
    return pd.DataFrame(rows)


# =========================================================
# DATA PREP
# =========================================================
def prepare_odds_df(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=["sport", "team_a", "team_b", "book", "market", "point", "total", "selection", "odds"])

    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    df = add_missing_cols(df, {
        "sport": "NBA",
        "team_a": "",
        "team_b": "",
        "book": "",
        "market": "",
        "point": np.nan,
        "total": np.nan,
        "selection": "",
        "odds": np.nan,
    })
    df["market"] = df["market"].apply(clean_market_name)
    df["selection"] = df["selection"].fillna("").astype(str)
    df["odds"] = pd.to_numeric(df["odds"], errors="coerce")
    df["point"] = pd.to_numeric(df["point"], errors="coerce")
    df["total"] = pd.to_numeric(df["total"], errors="coerce")
    df["dec_odds"] = df["odds"].apply(american_to_decimal)
    df["imp_prob"] = df["odds"].apply(implied_prob_american)
    return df


def prepare_props_df(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=[
            "sport", "player", "team", "opponent", "is_starter", "starter_status", "starter_confirmed",
            "prop_type", "line", "projection", "minutes_projection", "recent_avg", "last_5_games",
            "pace_factor", "matchup_factor", "odds", "game_segment", "book", "source_time"
        ])

    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    df = add_missing_cols(df, {
        "sport": "NBA",
        "player": "",
        "team": "",
        "opponent": "",
        "is_starter": 1,
        "starter_status": "unknown",
        "starter_confirmed": 0,
        "prop_type": "points",
        "line": np.nan,
        "projection": np.nan,
        "minutes_projection": np.nan,
        "recent_avg": np.nan,
        "last_5_games": 5,
        "pace_factor": 1.00,
        "matchup_factor": 1.00,
        "odds": np.nan,
        "game_segment": "full_game",
        "book": "Unknown",
        "source_time": "",
    })
    numeric_cols = [
        "is_starter", "starter_confirmed", "line", "projection", "minutes_projection",
        "recent_avg", "last_5_games", "pace_factor", "matchup_factor", "odds"
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ["player", "team", "opponent", "starter_status", "prop_type", "game_segment", "book", "source_time"]:
        df[col] = df[col].fillna("").astype(str)
    df["starter_status"] = df["starter_status"].apply(normalize_text)
    df["prop_type"] = df["prop_type"].apply(normalize_text)
    df["game_segment"] = df["game_segment"].apply(normalize_text)
    return df


def prepare_injuries_df(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=["sport", "team", "player", "injury_status", "starter_status", "injury_note", "source_time"])

    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    df = add_missing_cols(df, {
        "sport": "NBA",
        "team": "",
        "player": "",
        "injury_status": "unknown",
        "starter_status": "unknown",
        "injury_note": "",
        "source_time": "",
    })
    for col in ["sport", "team", "player", "injury_status", "starter_status", "injury_note", "source_time"]:
        df[col] = df[col].fillna("").astype(str)
    df["injury_status"] = df["injury_status"].apply(normalize_text)
    df["starter_status"] = df["starter_status"].apply(normalize_text)
    return df


def merge_props_with_injuries(props_df, injuries_df):
    if props_df.empty:
        return props_df.copy()

    merged = props_df.copy()
    if injuries_df.empty:
        merged["injury_status"] = "unknown"
        merged["injury_note"] = ""
        return merged

    inj_small = injuries_df[["player", "injury_status", "starter_status", "injury_note"]].copy()
    inj_small = inj_small.drop_duplicates(subset=["player"], keep="last")
    merged = merged.merge(inj_small, on="player", how="left", suffixes=("", "_inj"))

    merged["injury_status"] = merged["injury_status"].fillna("unknown")
    merged["injury_note"] = merged["injury_note"].fillna("")
    merged["starter_status"] = np.where(
        merged["starter_status_inj"].fillna("").astype(str).str.len() > 0,
        merged["starter_status_inj"],
        merged["starter_status"]
    )
    merged = merged.drop(columns=[c for c in ["starter_status_inj"] if c in merged.columns])
    return merged


# =========================================================
# SNAPSHOTS
# =========================================================
def append_snapshot(df, label):
    if df.empty:
        return df.copy()
    snap = df.copy()
    snap["snapshot_label"] = label
    snap["snapshot_time"] = current_ts_str()
    return snap


def save_snapshot_to_session(name, df):
    if "snapshots" not in st.session_state:
        st.session_state["snapshots"] = {}
    st.session_state["snapshots"][name] = df.copy()


def get_snapshot_from_session(name):
    if "snapshots" not in st.session_state:
        return pd.DataFrame()
    return st.session_state["snapshots"].get(name, pd.DataFrame())


def build_line_movement_from_snapshots(old_df, new_df):
    if old_df.empty or new_df.empty:
        return pd.DataFrame()

    keys = ["player", "prop_type", "game_segment", "book"]
    old_small = old_df[keys + ["line", "odds"]].copy().rename(columns={"line": "old_line", "odds": "old_odds"})
    new_small = new_df[keys + ["line", "odds"]].copy().rename(columns={"line": "new_line", "odds": "new_odds"})

    merged = new_small.merge(old_small, on=keys, how="left")
    merged["line_move"] = merged["new_line"] - merged["old_line"]
    merged["odds_move"] = merged["new_odds"] - merged["old_odds"]
    return merged


def apply_movement_to_props(props_df, movement_df):
    if props_df.empty:
        return props_df.copy()
    if movement_df.empty:
        props_df = props_df.copy()
        props_df["line_move"] = np.nan
        props_df["odds_move"] = np.nan
        return props_df

    keys = ["player", "prop_type", "game_segment", "book"]
    small = movement_df[keys + ["line_move", "odds_move"]].copy()
    out = props_df.merge(small, on=keys, how="left")
    return out


# =========================================================
# ARB / MIDDLE
# =========================================================
def find_moneyline_arbs(df):
    ml = df[df["market"] == "moneyline"].copy()
    results = []

    if ml.empty:
        return pd.DataFrame()

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
            results.append({
                "sport": keys[0],
                "matchup": f"{keys[1]} vs {keys[2]}",
                "side_1": r1["selection"],
                "book_1": r1["book"],
                "odds_1": int(r1["odds"]),
                "side_2": r2["selection"],
                "book_2": r2["book"],
                "odds_2": int(r2["odds"]),
                "arb_profit_pct": round((1 - inv_sum) * 100, 2),
            })

    return pd.DataFrame(results).sort_values("arb_profit_pct", ascending=False) if results else pd.DataFrame()


# =========================================================
# PROP ENGINE
# =========================================================
def hit_probability_from_edge(row):
    prop_type = normalize_text(row.get("prop_type", "points"))
    line = safe_float(row.get("line"))
    proj = safe_float(row.get("projection"))
    minutes = safe_float(row.get("minutes_projection"))
    recent_avg = safe_float(row.get("recent_avg"))
    segment = normalize_text(row.get("game_segment", "full_game"))

    if pd.isna(line) or pd.isna(proj):
        return np.nan

    sigma_map_full = {
        "points": 6.5, "rebounds": 3.0, "assists": 3.2, "3pt_made": 1.6, "threes": 1.6,
        "pra": 8.4, "pa": 7.0, "pr": 6.8, "ra": 5.2, "steals": 1.2, "blocks": 1.2,
    }
    sigma_map_1q = {
        "points": 2.6, "rebounds": 1.4, "assists": 1.5, "3pt_made": 0.9, "threes": 0.9,
        "pra": 3.0, "pa": 2.7, "pr": 2.5, "ra": 2.1, "steals": 0.6, "blocks": 0.5,
    }
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

    if not pd.isna(recent_avg):
        if abs(recent_avg - proj) <= 1:
            sigma *= 0.97
        elif abs(recent_avg - proj) >= 4:
            sigma *= 1.05

    z = (proj - line) / sigma if sigma > 0 else 0
    prob_over = 0.5 * (1 + math.erf(z / math.sqrt(2)))
    return max(0.01, min(0.99, prob_over))


def confidence_warning_label(row):
    warnings = []

    minutes = safe_float(row.get("minutes_projection"))
    is_starter = safe_float(row.get("is_starter"))
    recent_avg = safe_float(row.get("recent_avg"))
    projection = safe_float(row.get("projection"))
    line = safe_float(row.get("line"))
    segment = normalize_text(row.get("game_segment"))
    starter_status = normalize_text(row.get("starter_status", ""))
    starter_confirmed = safe_float(row.get("starter_confirmed"))
    injury_status = normalize_text(row.get("injury_status", ""))

    if injury_status in ["questionable", "doubtful", "out"]:
        warnings.append(f"Injury: {injury_status}")
    if not pd.isna(minutes):
        if segment == "1q" and minutes < 8:
            warnings.append("Low 1Q minutes")
        elif segment != "1q" and minutes < 26:
            warnings.append("Low minutes")
    if not pd.isna(is_starter) and is_starter < 1:
        warnings.append("Bench player")
    if starter_status not in ["confirmed", "expected", "probable", "starting"]:
        if pd.isna(starter_confirmed) or starter_confirmed < 1:
            warnings.append("Starter not confirmed")
    if not pd.isna(recent_avg) and not pd.isna(line) and abs(recent_avg - line) < 0.5:
        warnings.append("Thin recent edge")
    if not pd.isna(projection) and not pd.isna(line) and abs(projection - line) < 0.4:
        warnings.append("Thin model edge")

    return "Clear" if not warnings else " | ".join(warnings)


def confidence_status(row):
    note = confidence_warning_label(row)
    if note == "Clear":
        return "✅ Clear"
    if "Injury:" in note or "Starter not confirmed" in note or "Bench player" in note:
        return "⚠️ Caution"
    return "🟡 Watch"


def compute_prop_scores(df):
    if df.empty:
        return df.copy()

    df = df.copy()
    df["proj_edge"] = df["projection"] - df["line"]
    df["proj_edge_abs"] = df["proj_edge"].abs()
    df["recommended_side"] = np.where(df["projection"] > df["line"], "Over", "Under")
    df["hit_prob_over"] = df.apply(hit_probability_from_edge, axis=1)
    df["hit_prob_under"] = 1 - df["hit_prob_over"]
    df["hit_probability"] = np.where(df["recommended_side"] == "Over", df["hit_prob_over"], df["hit_prob_under"])
    df["book_implied_prob"] = df["odds"].apply(implied_prob_american)
    df["model_fair_odds"] = df["hit_probability"].apply(prob_to_american)
    df["expected_value_edge"] = ((df["hit_probability"] - df["book_implied_prob"]) * 100).round(2)

    minutes_score = np.where(
        df["game_segment"] == "1q",
        np.clip((df["minutes_projection"] / 12) * 16, 0, 16),
        np.clip((df["minutes_projection"] / 36) * 18, 0, 18)
    )
    edge_score_component = np.clip(df["proj_edge_abs"] * 6, 0, 24)
    recent_gap = (df["recent_avg"] - df["line"]).abs()
    recent_score = np.clip(recent_gap * 2.2, 0, 14)
    starter_score = np.where(df["is_starter"] >= 1, 10, 0)
    confirmed_bonus = np.where(df["starter_confirmed"] >= 1, 6, 0)
    pace_score = np.clip((df["pace_factor"] - 1.0) * 100, -4, 10)
    matchup_score = np.clip((df["matchup_factor"] - 1.0) * 100, -4, 12)
    probability_score = np.clip((df["hit_probability"] - 0.50) * 100, 0, 14)
    ev_score = np.clip(df["expected_value_edge"], 0, 10)

    price_score = np.select(
        [
            (df["odds"] >= -125) & (df["odds"] <= 140),
            (df["odds"] >= -150) & (df["odds"] < -125),
            (df["odds"] > 140) & (df["odds"] <= 200),
        ],
        [10, 7, 8],
        default=4
    )

    caution_penalty = np.select(
        [
            df["starter_confirmed"] < 1,
            df["injury_status"].fillna("").astype(str).str.lower().isin(["questionable", "doubtful"]),
            df["minutes_projection"] < np.where(df["game_segment"] == "1q", 8, 26),
        ],
        [6, 5, 4],
        default=0
    )

    df["edge_score"] = (
        minutes_score + edge_score_component + recent_score + starter_score + confirmed_bonus +
        pace_score + matchup_score + price_score + probability_score + ev_score - caution_penalty
    ).round(1)

    df["edge_score"] = np.clip(df["edge_score"], 0, 100)
    df["bet_grade"] = df["edge_score"].apply(edge_bucket)
    df["confidence_warning"] = df.apply(confidence_warning_label, axis=1)
    df["confidence_status"] = df.apply(confidence_status, axis=1)
    return df


def best_line_shop(df):
    if df.empty:
        return df.copy()

    rows = []
    group_cols = ["player", "team", "opponent", "prop_type", "game_segment", "recommended_side"]
    for _, group in df.groupby(group_cols, dropna=False):
        group = group.copy()
        side = group["recommended_side"].iloc[0]
        if side == "Over":
            group = group.sort_values(["line", "odds", "edge_score", "expected_value_edge"], ascending=[True, False, False, False])
        else:
            group = group.sort_values(["line", "odds", "edge_score", "expected_value_edge"], ascending=[False, False, False, False])
        rows.append(group.iloc[0])

    return pd.DataFrame(rows).reset_index(drop=True).sort_values(
        ["edge_score", "expected_value_edge", "hit_probability"],
        ascending=[False, False, False]
    )


def filter_props_base(df, sport="All", segment="All", starters_only=True, confirmed_only=False,
                      min_odds=-300, max_odds=200, min_edge=60, min_hit_prob=54,
                      min_ev=0, book="All", prop_type="All"):
    out = df.copy()

    if sport != "All":
        out = out[out["sport"] == sport]
    if segment != "All":
        out = out[out["game_segment"] == segment]
    if prop_type != "All":
        out = out[out["prop_type"] == prop_type]
    if starters_only:
        out = out[out["is_starter"] >= 1]
    if confirmed_only:
        out = out[out["starter_confirmed"] >= 1]
    if book != "All":
        out = out[out["book"] == book]

    out = out[(out["odds"] >= min_odds) & (out["odds"] <= max_odds)]
    out = out[out["edge_score"] >= min_edge]
    out = out[(out["hit_probability"] * 100) >= min_hit_prob]
    out = out[out["expected_value_edge"] >= min_ev]

    return out.sort_values(
        ["edge_score", "expected_value_edge", "hit_probability", "proj_edge_abs"],
        ascending=[False, False, False, False]
    )


def build_best_bets_dashboard(df):
    if df.empty:
        return pd.DataFrame()

    cols = [
        "player", "team", "opponent", "book", "game_segment", "prop_type", "recommended_side",
        "line", "odds", "projection", "proj_edge", "hit_probability", "expected_value_edge",
        "edge_score", "bet_grade", "confidence_status", "line_move", "odds_move", "source_time"
    ]
    use_cols = [c for c in cols if c in df.columns]
    return df.sort_values(
        ["edge_score", "expected_value_edge", "hit_probability"],
        ascending=[False, False, False]
    )[use_cols].head(20).copy()


def format_props_table(df):
    out = df.copy()
    if out.empty:
        return out
    if "hit_probability" in out.columns:
        out["hit_probability"] = (out["hit_probability"] * 100).round(1)
    if "book_implied_prob" in out.columns:
        out["book_implied_prob"] = (out["book_implied_prob"] * 100).round(1)
    return out


def render_top_play_card(row, rank_num):
    st.markdown(
        f"""
<div style="padding:14px;border:1px solid #333;border-radius:12px;margin-bottom:10px;">
  <div style="font-size:18px;font-weight:700;">#{rank_num} {row['player']} — {row['recommended_side']} {row['line']} {row['prop_type']}</div>
  <div style="margin-top:4px;">{row['team']} vs {row['opponent']} • {str(row['game_segment']).upper()} • {row['book']}</div>
  <div style="margin-top:8px;">
    <b>Projection:</b> {row['projection']:.2f} |
    <b>Edge:</b> {row['proj_edge']:.2f} |
    <b>Odds:</b> {int(row['odds']) if not pd.isna(row['odds']) else 'N/A'} |
    <b>Hit %:</b> {row['hit_probability']*100:.1f}% |
    <b>EV Edge:</b> {row['expected_value_edge']:.2f}% |
    <b>Score:</b> {row['edge_score']:.1f} ({row['bet_grade']})
  </div>
  <div style="margin-top:8px;">
    <b>Confidence:</b> {row['confidence_status']} |
    <b>Notes:</b> {row['confidence_warning']}
  </div>
  <div style="margin-top:8px;">
    <b>Line Move:</b> {row.get('line_move', np.nan)} |
    <b>Odds Move:</b> {row.get('odds_move', np.nan)} |
    <b>Source:</b> {row.get('source_time', '')}
  </div>
</div>
""",
        unsafe_allow_html=True
    )


# =========================================================
# API/CSV INGESTION
# =========================================================
@st.cache_data(ttl=90, show_spinner=False)
def load_all_data(
    use_api: bool,
    use_sample_fallback: bool,
    odds_url: str,
    props_url: str,
    injury_url: str,
    api_key: str,
    odds_file,
    props_file,
    injury_file,
    sport_for_api: str,
):
    source_notes = []

    # Odds
    if use_api:
        odds_payload, odds_err = fetch_json(odds_url, api_key=api_key, params={"sport": sport_for_api})
        if odds_payload is not None:
            odds_df = parse_odds_api_payload(odds_payload, fallback_sport=sport_for_api)
            source_notes.append("Odds: API")
        else:
            odds_df = pd.read_csv(odds_file) if odds_file is not None and str(odds_file.name).lower().endswith(".csv") else (
                pd.read_excel(odds_file) if odds_file is not None else (sample_odds_data() if use_sample_fallback else pd.DataFrame())
            )
            source_notes.append(f"Odds fallback: {'upload' if odds_file is not None else ('sample' if use_sample_fallback else 'missing')} | {odds_err}")
    else:
        odds_df = pd.read_csv(odds_file) if odds_file is not None and str(odds_file.name).lower().endswith(".csv") else (
            pd.read_excel(odds_file) if odds_file is not None else (sample_odds_data() if use_sample_fallback else pd.DataFrame())
        )
        source_notes.append(f"Odds: {'upload' if odds_file is not None else ('sample' if use_sample_fallback else 'missing')}")

    # Props
    if use_api:
        props_payload, props_err = fetch_json(props_url, api_key=api_key, params={"sport": sport_for_api})
        if props_payload is not None:
            props_df = parse_props_api_payload(props_payload, fallback_sport=sport_for_api)
            source_notes.append("Props: API")
        else:
            props_df = pd.read_csv(props_file) if props_file is not None and str(props_file.name).lower().endswith(".csv") else (
                pd.read_excel(props_file) if props_file is not None else (sample_props_data() if use_sample_fallback else pd.DataFrame())
            )
            source_notes.append(f"Props fallback: {'upload' if props_file is not None else ('sample' if use_sample_fallback else 'missing')} | {props_err}")
    else:
        props_df = pd.read_csv(props_file) if props_file is not None and str(props_file.name).lower().endswith(".csv") else (
            pd.read_excel(props_file) if props_file is not None else (sample_props_data() if use_sample_fallback else pd.DataFrame())
        )
        source_notes.append(f"Props: {'upload' if props_file is not None else ('sample' if use_sample_fallback else 'missing')}")

    # Injuries
    if use_api:
        injury_payload, injury_err = fetch_json(injury_url, api_key=api_key, params={"sport": sport_for_api})
        if injury_payload is not None:
            injuries_df = parse_injury_api_payload(injury_payload, fallback_sport=sport_for_api)
            source_notes.append("Injuries: API")
        else:
            injuries_df = pd.read_csv(injury_file) if injury_file is not None and str(injury_file.name).lower().endswith(".csv") else (
                pd.read_excel(injury_file) if injury_file is not None else (sample_injuries_data() if use_sample_fallback else pd.DataFrame())
            )
            source_notes.append(f"Injuries fallback: {'upload' if injury_file is not None else ('sample' if use_sample_fallback else 'missing')} | {injury_err}")
    else:
        injuries_df = pd.read_csv(injury_file) if injury_file is not None and str(injury_file.name).lower().endswith(".csv") else (
            pd.read_excel(injury_file) if injury_file is not None else (sample_injuries_data() if use_sample_fallback else pd.DataFrame())
        )
        source_notes.append(f"Injuries: {'upload' if injury_file is not None else ('sample' if use_sample_fallback else 'missing')}")

    return {
        "odds": odds_df,
        "props": props_df,
        "injuries": injuries_df,
        "notes": source_notes,
    }


# =========================================================
# SIDEBAR
# =========================================================
st.sidebar.header("V5 Data Control")

use_api_mode = st.sidebar.checkbox("Use API mode", value=False)
use_sample_fallback = st.sidebar.checkbox("Use sample fallback when missing", value=True)
sport_for_api = st.sidebar.selectbox("Primary sport", ["NBA", "NHL", "MLB", "NFL"], index=0)

default_api_key = ""
try:
    default_api_key = st.secrets.get("API_KEY", "")
except Exception:
    default_api_key = ""

default_odds_url = ""
default_props_url = ""
default_injury_url = ""
try:
    default_odds_url = st.secrets.get("ODDS_API_URL", DEFAULT_ODDS_API_URL)
    default_props_url = st.secrets.get("PROPS_API_URL", DEFAULT_PROPS_API_URL)
    default_injury_url = st.secrets.get("INJURY_API_URL", DEFAULT_INJURY_API_URL)
except Exception:
    default_odds_url = DEFAULT_ODDS_API_URL
    default_props_url = DEFAULT_PROPS_API_URL
    default_injury_url = DEFAULT_INJURY_API_URL

api_key = st.sidebar.text_input("API key", value=default_api_key, type="password")
odds_url = st.sidebar.text_input("Odds API URL", value=default_odds_url)
props_url = st.sidebar.text_input("Props API URL", value=default_props_url)
injury_url = st.sidebar.text_input("Injury API URL", value=default_injury_url)

st.sidebar.markdown("### CSV fallback uploads")
odds_file = st.sidebar.file_uploader("Upload odds file", type=["csv", "xlsx"], key="v5_odds")
props_file = st.sidebar.file_uploader("Upload props file", type=["csv", "xlsx"], key="v5_props")
injury_file = st.sidebar.file_uploader("Upload injury file", type=["csv", "xlsx"], key="v5_injury")

if st.sidebar.button("Refresh cached data"):
    st.cache_data.clear()

if st.sidebar.button("Save current props snapshot"):
    snapshot_label = f"manual_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if "latest_props_live" in st.session_state and not st.session_state["latest_props_live"].empty:
        save_snapshot_to_session(snapshot_label, append_snapshot(st.session_state["latest_props_live"], snapshot_label))
        st.sidebar.success(f"Saved {snapshot_label}")
    else:
        st.sidebar.warning("No live props available yet to snapshot.")


# =========================================================
# LOAD PIPELINE
# =========================================================
loaded = load_all_data(
    use_api=use_api_mode,
    use_sample_fallback=use_sample_fallback,
    odds_url=odds_url,
    props_url=props_url,
    injury_url=injury_url,
    api_key=api_key,
    odds_file=odds_file,
    props_file=props_file,
    injury_file=injury_file,
    sport_for_api=sport_for_api,
)

odds_df = prepare_odds_df(loaded["odds"])
props_df = prepare_props_df(loaded["props"])
injuries_df = prepare_injuries_df(loaded["injuries"])

props_merged = merge_props_with_injuries(props_df, injuries_df)
props_scored = compute_prop_scores(props_merged)

prev_snapshot = get_snapshot_from_session("latest_props_live")
movement_df = build_line_movement_from_snapshots(prev_snapshot, props_scored)
props_live = apply_movement_to_props(props_scored, movement_df)
props_shop = best_line_shop(props_live)

st.session_state["latest_props_live"] = append_snapshot(props_scored, "latest_props_live")

source_status = pd.DataFrame([
    ["Odds", len(odds_df), "API" if use_api_mode else ("Upload" if odds_file is not None else ("Sample" if use_sample_fallback else "Missing"))],
    ["Props", len(props_df), "API" if use_api_mode else ("Upload" if props_file is not None else ("Sample" if use_sample_fallback else "Missing"))],
    ["Injuries", len(injuries_df), "API" if use_api_mode else ("Upload" if injury_file is not None else ("Sample" if use_sample_fallback else "Missing"))],
], columns=["Feed", "Rows", "Source"])


# =========================================================
# TABS
# =========================================================
tab_home, tab_best, tab_sections, tab_injuries, tab_arb, tab_api = st.tabs([
    "Home",
    "Best Bets",
    "Prop Sections",
    "Injuries",
    "Arbitrage",
    "API Wiring",
])


# =========================================================
# HOME
# =========================================================
with tab_home:
    st.subheader("V5 API-Ready Dashboard")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Odds Rows", len(odds_df))
    c2.metric("Props Rows", len(props_live))
    c3.metric("Books", max(odds_df["book"].nunique() if not odds_df.empty else 0, props_live["book"].nunique() if not props_live.empty else 0))
    c4.metric("Updated", current_ts_str())

    st.markdown("### Feed status")
    st.dataframe(source_status, use_container_width=True)

    st.markdown("### Load notes")
    st.dataframe(pd.DataFrame({"status": loaded["notes"]}), use_container_width=True)

    st.markdown("### What V5 adds")
    st.write("• API mode toggle")
    st.write("• secrets-ready API fields")
    st.write("• CSV fallback mode")
    st.write("• current-session prop snapshots")
    st.write("• line movement from snapshots")
    st.write("• auto best bets board by market and sport")
    st.write("• provider-specific parser placeholders")

    with st.expander("Expected next custom step"):
        st.write("Replace the three parse_*_api_payload() functions with your real provider field mappings.")
        st.write("Then set API_KEY, ODDS_API_URL, PROPS_API_URL, and INJURY_API_URL in Streamlit secrets.")


# =========================================================
# BEST BETS
# =========================================================
with tab_best:
    st.subheader("Auto Best Bets Board")

    sport_opts = ["All"] + sorted(props_shop["sport"].dropna().astype(str).unique().tolist()) if not props_shop.empty else ["All"]
    segment_opts = ["All"] + sorted(props_shop["game_segment"].dropna().astype(str).unique().tolist()) if not props_shop.empty else ["All"]
    prop_opts = ["All"] + sorted(props_shop["prop_type"].dropna().astype(str).unique().tolist()) if not props_shop.empty else ["All"]
    book_opts = ["All"] + sorted(props_shop["book"].dropna().astype(str).unique().tolist()) if not props_shop.empty else ["All"]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        selected_sport = st.selectbox("Sport", sport_opts, key="v5_sport")
    with c2:
        selected_segment = st.selectbox("Segment", segment_opts, key="v5_segment")
    with c3:
        selected_prop = st.selectbox("Prop Type", prop_opts, key="v5_prop")
    with c4:
        selected_book = st.selectbox("Book", book_opts, key="v5_book")

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        starters_only = st.checkbox("Starters Only", value=True)
    with c6:
        confirmed_only = st.checkbox("Confirmed Only", value=False)
    with c7:
        best_shop_only = st.checkbox("Best Line Shop Only", value=True)
    with c8:
        min_edge = st.slider("Min Edge Score", 0, 100, 60, 5)

    c9, c10, c11 = st.columns(3)
    with c9:
        min_odds = st.slider("Min Odds", -300, 200, -300, 5)
    with c10:
        max_odds = st.slider("Max Odds", -300, 200, 200, 5)
    with c11:
        min_hit = st.slider("Min Hit %", 50, 95, 54, 1)

    min_ev = st.slider("Min EV Edge %", -10, 25, 0, 1)

    base_df = props_shop.copy() if best_shop_only else props_live.copy()
    filtered = filter_props_base(
        base_df,
        sport=selected_sport,
        segment=selected_segment,
        starters_only=starters_only,
        confirmed_only=confirmed_only,
        min_odds=min_odds,
        max_odds=max_odds,
        min_edge=min_edge,
        min_hit_prob=min_hit,
        min_ev=min_ev,
        book=selected_book,
        prop_type=selected_prop,
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Props Found", len(filtered))
    m2.metric("A-Grade", int((filtered["edge_score"] >= 86).sum()) if not filtered.empty else 0)
    m3.metric("Avg Edge", round(filtered["edge_score"].mean(), 1) if not filtered.empty else 0)
    m4.metric("Avg Hit %", f"{round(filtered['hit_probability'].mean() * 100, 1) if not filtered.empty else 0}%")

    if filtered.empty:
        st.warning("No props match the current filters.")
    else:
        st.markdown("### Top play cards")
        for idx, (_, row) in enumerate(filtered.head(10).iterrows(), start=1):
            render_top_play_card(row, idx)

        st.markdown("### Auto best bets table")
        st.dataframe(format_props_table(build_best_bets_dashboard(filtered)), use_container_width=True)


# =========================================================
# PROP SECTIONS
# =========================================================
with tab_sections:
    st.subheader("Prop Sections by Market")
    if props_live.empty:
        st.info("No props available.")
    else:
        table_cols = [
            "player", "team", "opponent", "book", "game_segment", "recommended_side",
            "line", "projection", "proj_edge", "odds", "hit_probability",
            "expected_value_edge", "edge_score", "bet_grade", "confidence_status",
            "line_move", "odds_move"
        ]
        for title, prop_key in SUPPORTED_PROP_SECTIONS:
            st.markdown(f"### {title}")
            section = props_live[props_live["prop_type"] == prop_key].copy()
            if section.empty:
                st.info(f"No {title.lower()} props loaded.")
            else:
                st.dataframe(format_props_table(section[table_cols]), use_container_width=True)


# =========================================================
# INJURIES
# =========================================================
with tab_injuries:
    st.subheader("Injury / Starter Feed")
    if injuries_df.empty:
        st.info("No injury feed loaded.")
    else:
        st.dataframe(injuries_df, use_container_width=True)

    st.markdown("### Props with caution flags")
    caution_df = props_live[props_live["confidence_status"] != "✅ Clear"].copy() if not props_live.empty else pd.DataFrame()
    if caution_df.empty:
        st.info("No caution flags.")
    else:
        cols = [
            "player", "team", "opponent", "book", "prop_type", "game_segment",
            "injury_status", "starter_status", "starter_confirmed",
            "confidence_status", "confidence_warning", "edge_score"
        ]
        st.dataframe(caution_df[cols], use_container_width=True)


# =========================================================
# ARBITRAGE
# =========================================================
with tab_arb:
    st.subheader("Moneyline Arbitrage")
    sports = ["All"] + sorted(odds_df["sport"].dropna().astype(str).unique().tolist()) if not odds_df.empty else ["All"]
    selected_arb_sport = st.selectbox("Sport", sports, key="v5_arb_sport")

    arb_base = odds_df.copy()
    if selected_arb_sport != "All":
        arb_base = arb_base[arb_base["sport"] == selected_arb_sport]

    arb_results = find_moneyline_arbs(arb_base)
    if arb_results.empty:
        st.warning("No moneyline arbitrage opportunities detected.")
    else:
        st.dataframe(arb_results, use_container_width=True)


# =========================================================
# API WIRING
# =========================================================
with tab_api:
    st.subheader("API Wiring Guide")
    st.markdown("### Current mode")
    st.write(f"API mode: {'ON' if use_api_mode else 'OFF'}")
    st.write(f"Odds URL: {odds_url}")
    st.write(f"Props URL: {props_url}")
    st.write(f"Injury URL: {injury_url}")

    st.markdown("### Streamlit secrets example")
    st.code(
        """API_KEY="your_real_key"
ODDS_API_URL="https://your-provider.com/odds"
PROPS_API_URL="https://your-provider.com/props"
INJURY_API_URL="https://your-provider.com/injuries" """,
        language="toml"
    )

    st.markdown("### What you change next")
    st.write("1. Put your real API URLs into Streamlit secrets or sidebar fields.")
    st.write("2. Put your real API key into Streamlit secrets.")
    st.write("3. Edit parse_odds_api_payload().")
    st.write("4. Edit parse_props_api_payload().")
    st.write("5. Edit parse_injury_api_payload().")
    st.write("6. If your provider needs custom headers, update build_headers().")

    st.markdown("### Snapshot status")
    snapshot_names = []
    if "snapshots" in st.session_state:
        snapshot_names = sorted(list(st.session_state["snapshots"].keys()))
    if not snapshot_names:
        st.info("No manual snapshots saved yet.")
    else:
        st.dataframe(pd.DataFrame({"snapshot_name": snapshot_names}), use_container_width=True)


st.markdown("---")
st.caption("V5 full clean build — API-ready structure with CSV fallbacks and session-based snapshots.")
