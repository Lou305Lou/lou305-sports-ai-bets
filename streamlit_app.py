
import math
from datetime import datetime
from typing import Dict, Tuple

import numpy as np
import pandas as pd
import streamlit as st


# =========================================================
# PAGE SETUP
# =========================================================
st.set_page_config(
    page_title="Sports AI Betting Dashboard V4",
    page_icon="🏀",
    layout="wide",
)

st.title("🏀 Sports AI Betting Dashboard V4")
st.caption("Live Data Wiring Structure • APIs / CSVs • Line Movement • Starter / Injury Panel • Best Bets Dashboard")


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


def format_pct(x, digits=1):
    if pd.isna(x):
        return np.nan
    return round(float(x) * 100, digits)


def format_timestamp_now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


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
        ["NHL", "Panthers", "Rangers", "Book1", "moneyline", np.nan, np.nan, "Panthers", +125],
        ["NHL", "Panthers", "Rangers", "Book2", "moneyline", np.nan, np.nan, "Rangers", +130],
    ]
    return pd.DataFrame(rows, columns=[
        "sport", "team_a", "team_b", "book", "market", "point", "total", "selection", "odds"
    ])


def sample_props_data():
    rows = [
        ["NBA", "Jalen Brunson", "Knicks", "Celtics", 1, "confirmed", 1, "points", 27.5, 31.2, 36, 32.1, 5, 1.07, 1.03, -115, "full_game", "DraftKings", "2026-03-19 08:00"],
        ["NBA", "Jalen Brunson", "Knicks", "Celtics", 1, "confirmed", 1, "points", 28.5, 31.2, 36, 32.1, 5, 1.07, 1.03, +100, "full_game", "FanDuel", "2026-03-19 08:02"],
        ["NBA", "Jayson Tatum", "Celtics", "Knicks", 1, "confirmed", 1, "rebounds", 8.5, 9.7, 37, 10.2, 5, 1.04, 1.02, -105, "full_game", "BetMGM", "2026-03-19 08:03"],
        ["NBA", "Jayson Tatum", "Celtics", "Knicks", 1, "confirmed", 1, "rebounds", 9.5, 9.7, 37, 10.2, 5, 1.04, 1.02, +120, "full_game", "Caesars", "2026-03-19 08:04"],
        ["NBA", "Bam Adebayo", "Heat", "Bucks", 1, "expected", 1, "rebounds", 9.5, 11.1, 35, 11.0, 5, 1.06, 1.04, +110, "full_game", "DraftKings", "2026-03-19 08:05"],
        ["NBA", "Tyrese Haliburton", "Pacers", "Cavs", 1, "expected", 1, "assists", 10.5, 11.8, 35, 12.1, 5, 1.05, 1.03, +125, "full_game", "FanDuel", "2026-03-19 08:06"],
        ["NBA", "Stephen Curry", "Warriors", "Lakers", 1, "confirmed", 1, "3pt_made", 1.5, 2.2, 10, 2.4, 5, 1.03, 1.01, -120, "1q", "DraftKings", "2026-03-19 08:07"],
        ["NBA", "LeBron James", "Lakers", "Warriors", 1, "confirmed", 1, "points", 6.5, 7.8, 10, 8.4, 5, 1.04, 1.02, -110, "1q", "BetMGM", "2026-03-19 08:08"],
        ["NBA", "Questionable Starter", "TeamQ", "TeamZ", 1, "unknown", 0, "assists", 7.5, 8.1, 27, 8.2, 5, 1.01, 1.00, +110, "full_game", "BookY", "2026-03-19 08:09"],
    ]
    return pd.DataFrame(rows, columns=[
        "sport", "player", "team", "opponent", "is_starter", "starter_status", "starter_confirmed",
        "prop_type", "line", "projection", "minutes_projection", "recent_avg", "last_5_games",
        "pace_factor", "matchup_factor", "odds", "game_segment", "book", "source_time"
    ])


def sample_injuries_data():
    rows = [
        ["NBA", "Knicks", "Jalen Brunson", "available", "confirmed", "", "2026-03-19 08:00"],
        ["NBA", "Celtics", "Jayson Tatum", "available", "confirmed", "", "2026-03-19 08:00"],
        ["NBA", "Heat", "Bam Adebayo", "available", "expected", "", "2026-03-19 08:00"],
        ["NBA", "Pacers", "Tyrese Haliburton", "questionable", "expected", "ankle", "2026-03-19 08:00"],
        ["NBA", "Lakers", "LeBron James", "available", "confirmed", "", "2026-03-19 08:00"],
        ["NBA", "Warriors", "Stephen Curry", "available", "confirmed", "", "2026-03-19 08:00"],
    ]
    return pd.DataFrame(rows, columns=[
        "sport", "team", "player", "injury_status", "starter_status", "injury_note", "source_time"
    ])


def sample_line_history_data():
    rows = [
        ["Jalen Brunson", "points", "full_game", "DraftKings", 27.5, -115, "2026-03-19 06:00"],
        ["Jalen Brunson", "points", "full_game", "DraftKings", 28.5, -120, "2026-03-19 08:00"],
        ["Jalen Brunson", "points", "full_game", "FanDuel", 28.5, +100, "2026-03-19 06:00"],
        ["Jalen Brunson", "points", "full_game", "FanDuel", 28.5, -105, "2026-03-19 08:00"],
        ["Stephen Curry", "3pt_made", "1q", "DraftKings", 1.5, -110, "2026-03-19 06:00"],
        ["Stephen Curry", "3pt_made", "1q", "DraftKings", 1.5, -120, "2026-03-19 08:00"],
        ["LeBron James", "points", "1q", "BetMGM", 5.5, -105, "2026-03-19 06:00"],
        ["LeBron James", "points", "1q", "BetMGM", 6.5, -110, "2026-03-19 08:00"],
    ]
    return pd.DataFrame(rows, columns=[
        "player", "prop_type", "game_segment", "book", "line", "odds", "timestamp"
    ])


# =========================================================
# LIVE DATA WIRING LAYER
# =========================================================
def load_csv_or_sample(uploaded_file, sample_func):
    if uploaded_file is None:
        return sample_func()
    try:
        if str(uploaded_file.name).lower().endswith(".csv"):
            return pd.read_csv(uploaded_file)
        return pd.read_excel(uploaded_file)
    except Exception:
        return sample_func()


@st.cache_data(ttl=90, show_spinner=False)
def ingest_data_sources(
    odds_file,
    props_file,
    injuries_file,
    history_file,
    use_sample_when_missing=True,
):
    odds_raw = load_csv_or_sample(odds_file, sample_odds_data) if use_sample_when_missing else load_csv_or_sample(odds_file, lambda: pd.DataFrame())
    props_raw = load_csv_or_sample(props_file, sample_props_data) if use_sample_when_missing else load_csv_or_sample(props_file, lambda: pd.DataFrame())
    injuries_raw = load_csv_or_sample(injuries_file, sample_injuries_data) if use_sample_when_missing else load_csv_or_sample(injuries_file, lambda: pd.DataFrame())
    history_raw = load_csv_or_sample(history_file, sample_line_history_data) if use_sample_when_missing else load_csv_or_sample(history_file, lambda: pd.DataFrame())

    return {
        "odds": odds_raw.copy(),
        "props": props_raw.copy(),
        "injuries": injuries_raw.copy(),
        "history": history_raw.copy(),
    }


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
    df["odds"] = pd.to_numeric(df["odds"], errors="coerce")
    df["point"] = pd.to_numeric(df["point"], errors="coerce")
    df["total"] = pd.to_numeric(df["total"], errors="coerce")
    df["selection"] = df["selection"].fillna("").astype(str)
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


def prepare_history_df(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=["player", "prop_type", "game_segment", "book", "line", "odds", "timestamp"])

    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    df = add_missing_cols(df, {
        "player": "",
        "prop_type": "points",
        "game_segment": "full_game",
        "book": "Unknown",
        "line": np.nan,
        "odds": np.nan,
        "timestamp": "",
    })
    for col in ["player", "prop_type", "game_segment", "book", "timestamp"]:
        df[col] = df[col].fillna("").astype(str)
    for col in ["line", "odds"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["prop_type"] = df["prop_type"].apply(normalize_text)
    df["game_segment"] = df["game_segment"].apply(normalize_text)
    df["ts"] = pd.to_datetime(df["timestamp"], errors="coerce")
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

    if not results:
        return pd.DataFrame()
    return pd.DataFrame(results).sort_values("arb_profit_pct", ascending=False)


def find_spread_middles(df):
    spreads = df[df["market"] == "spreads"].copy()
    results = []

    if spreads.empty:
        return pd.DataFrame()

    for keys, group in spreads.groupby(["sport", "team_a", "team_b"], dropna=False):
        rows = group.dropna(subset=["point"]).copy()
        if len(rows) < 2:
            continue

        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                r1 = rows.iloc[i]
                r2 = rows.iloc[j]
                p1 = safe_float(r1["point"])
                p2 = safe_float(r2["point"])

                if pd.isna(p1) or pd.isna(p2):
                    continue

                if p1 < 0 and p2 > 0 and abs(p1) < abs(p2):
                    width = p2 - abs(p1)
                    if width > 0:
                        results.append({
                            "sport": keys[0],
                            "matchup": f"{keys[1]} vs {keys[2]}",
                            "bet_1": f"{r1['selection']} {p1} ({r1['book']} {int(r1['odds'])})",
                            "bet_2": f"{r2['selection']} +{p2} ({r2['book']} {int(r2['odds'])})",
                            "middle_window_points": round(width, 2),
                        })

    if not results:
        return pd.DataFrame()
    return pd.DataFrame(results).sort_values("middle_window_points", ascending=False).drop_duplicates()


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
        "points": 6.5,
        "rebounds": 3.0,
        "assists": 3.2,
        "3pt_made": 1.6,
        "threes": 1.6,
        "pra": 8.4,
        "pa": 7.0,
        "pr": 6.8,
        "ra": 5.2,
        "steals": 1.2,
        "blocks": 1.2,
    }
    sigma_map_1q = {
        "points": 2.6,
        "rebounds": 1.4,
        "assists": 1.5,
        "3pt_made": 0.9,
        "threes": 0.9,
        "pra": 3.0,
        "pa": 2.7,
        "pr": 2.5,
        "ra": 2.1,
        "steals": 0.6,
        "blocks": 0.5,
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
        minutes_score
        + edge_score_component
        + recent_score
        + starter_score
        + confirmed_bonus
        + pace_score
        + matchup_score
        + price_score
        + probability_score
        + ev_score
        - caution_penalty
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
            group = group.sort_values(
                ["line", "odds", "edge_score", "expected_value_edge"],
                ascending=[True, False, False, False]
            )
        else:
            group = group.sort_values(
                ["line", "odds", "edge_score", "expected_value_edge"],
                ascending=[False, False, False, False]
            )
        rows.append(group.iloc[0])

    return pd.DataFrame(rows).reset_index(drop=True).sort_values(
        ["edge_score", "expected_value_edge", "hit_probability"],
        ascending=[False, False, False]
    )


# =========================================================
# LINE MOVEMENT
# =========================================================
def build_line_movement_summary(history_df):
    if history_df.empty:
        return pd.DataFrame()

    history_df = history_df.sort_values(["player", "prop_type", "game_segment", "book", "ts"])
    rows = []

    for keys, group in history_df.groupby(["player", "prop_type", "game_segment", "book"], dropna=False):
        group = group.dropna(subset=["ts"]).copy()
        if group.empty:
            continue

        first = group.iloc[0]
        last = group.iloc[-1]

        rows.append({
            "player": keys[0],
            "prop_type": keys[1],
            "game_segment": keys[2],
            "book": keys[3],
            "open_line": first["line"],
            "current_line": last["line"],
            "line_move": round(last["line"] - first["line"], 2) if not pd.isna(first["line"]) and not pd.isna(last["line"]) else np.nan,
            "open_odds": first["odds"],
            "current_odds": last["odds"],
            "odds_move": round(last["odds"] - first["odds"], 2) if not pd.isna(first["odds"]) and not pd.isna(last["odds"]) else np.nan,
            "last_update": last["timestamp"],
        })

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["player", "prop_type", "book"])


def latest_compare_table(scored_props, movement_summary):
    if scored_props.empty:
        return scored_props.copy()

    out = scored_props.copy()
    if movement_summary.empty:
        out["line_move"] = np.nan
        out["odds_move"] = np.nan
        out["last_update"] = ""
        return out

    merge_cols = ["player", "prop_type", "game_segment", "book"]
    small = movement_summary[merge_cols + ["line_move", "odds_move", "last_update"]].copy()
    out = out.merge(small, on=merge_cols, how="left")
    return out


# =========================================================
# FILTERS / CARDS
# =========================================================
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
    <b>Updated:</b> {row.get('last_update', '')}
  </div>
</div>
""",
        unsafe_allow_html=True
    )


def format_props_table(df):
    out = df.copy()
    if out.empty:
        return out
    if "hit_probability" in out.columns:
        out["hit_probability"] = (out["hit_probability"] * 100).round(1)
    if "book_implied_prob" in out.columns:
        out["book_implied_prob"] = (out["book_implied_prob"] * 100).round(1)
    return out


def build_best_bets_dashboard(df):
    if df.empty:
        return pd.DataFrame()

    best = df.copy().sort_values(
        ["edge_score", "expected_value_edge", "hit_probability"],
        ascending=[False, False, False]
    ).head(15)

    cols = [
        "player", "team", "opponent", "book", "game_segment", "prop_type", "recommended_side",
        "line", "odds", "projection", "proj_edge", "hit_probability",
        "expected_value_edge", "edge_score", "bet_grade", "confidence_status",
        "line_move", "odds_move", "last_update"
    ]
    return best[cols].copy()


# =========================================================
# SIDEBAR: LIVE DATA WIRING
# =========================================================
st.sidebar.header("Live Data Wiring")

data_mode = st.sidebar.radio(
    "Data source mode",
    ["Sample fallback", "Uploaded files only"],
    index=0,
)

odds_file = st.sidebar.file_uploader("Upload odds file", type=["csv", "xlsx"], key="odds")
props_file = st.sidebar.file_uploader("Upload props file", type=["csv", "xlsx"], key="props")
injuries_file = st.sidebar.file_uploader("Upload injury / starter file", type=["csv", "xlsx"], key="inj")
history_file = st.sidebar.file_uploader("Upload line history file", type=["csv", "xlsx"], key="hist")

refresh_button = st.sidebar.button("Refresh cached data")
if refresh_button:
    st.cache_data.clear()

sources = ingest_data_sources(
    odds_file=odds_file,
    props_file=props_file,
    injuries_file=injuries_file,
    history_file=history_file,
    use_sample_when_missing=(data_mode == "Sample fallback"),
)

odds_df = prepare_odds_df(sources["odds"])
props_df = prepare_props_df(sources["props"])
injuries_df = prepare_injuries_df(sources["injuries"])
history_df = prepare_history_df(sources["history"])

props_merged = merge_props_with_injuries(props_df, injuries_df)
props_scored = compute_prop_scores(props_merged)
movement_summary = build_line_movement_summary(history_df)
props_live = latest_compare_table(props_scored, movement_summary)
props_shop = best_line_shop(props_live)

source_status = pd.DataFrame([
    ["Odds", len(odds_df), "Uploaded" if odds_file is not None else ("Sample" if data_mode == "Sample fallback" else "Missing")],
    ["Props", len(props_df), "Uploaded" if props_file is not None else ("Sample" if data_mode == "Sample fallback" else "Missing")],
    ["Injuries", len(injuries_df), "Uploaded" if injuries_file is not None else ("Sample" if data_mode == "Sample fallback" else "Missing")],
    ["Line history", len(history_df), "Uploaded" if history_file is not None else ("Sample" if data_mode == "Sample fallback" else "Missing")],
], columns=["Feed", "Rows", "Status"])


# =========================================================
# TABS
# =========================================================
tab_home, tab_arb, tab_mid, tab_live, tab_inj, tab_lines = st.tabs([
    "Home",
    "Arbitrage",
    "Middles",
    "Best Bets",
    "Injuries / Starters",
    "Line Movement",
])


# =========================================================
# HOME
# =========================================================
with tab_home:
    st.subheader("V4 Live Data Structure")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Odds Rows", len(odds_df))
    c2.metric("Props Rows", len(props_live))
    c3.metric("Books", max(odds_df["book"].nunique() if not odds_df.empty else 0, props_live["book"].nunique() if not props_live.empty else 0))
    c4.metric("Updated", format_timestamp_now())

    st.markdown("### Feed status")
    st.dataframe(source_status, use_container_width=True)

    st.markdown("### What V4 adds")
    st.write("• separate ingestion layer for odds, props, injuries, and line history")
    st.write("• cache refresh button")
    st.write("• injury / starter panel")
    st.write("• line movement summary")
    st.write("• best bets dashboard at the top")
    st.write("• merge structure for future CSV/API swaps")

    with st.expander("Expected file ideas"):
        st.write("Odds file: sport, team_a, team_b, book, market, point, total, selection, odds")
        st.write("Props file: player, team, opponent, prop_type, line, projection, minutes_projection, recent_avg, odds, book, game_segment")
        st.write("Injury file: player, team, injury_status, starter_status, injury_note")
        st.write("History file: player, prop_type, game_segment, book, line, odds, timestamp")


# =========================================================
# ARBITRAGE
# =========================================================
with tab_arb:
    st.subheader("Moneyline Arbitrage Scanner")
    sports = ["All"] + sorted(odds_df["sport"].dropna().astype(str).unique().tolist()) if not odds_df.empty else ["All"]
    selected_sport = st.selectbox("Sport", sports, key="arb_sport")

    arb_base = odds_df.copy()
    if selected_sport != "All":
        arb_base = arb_base[arb_base["sport"] == selected_sport]

    arb_results = find_moneyline_arbs(arb_base)
    if arb_results.empty:
        st.warning("No moneyline arbitrage opportunities detected.")
    else:
        st.success(f"Found {len(arb_results)} arbitrage opportunity(s).")
        st.dataframe(arb_results, use_container_width=True)


# =========================================================
# MIDDLES
# =========================================================
with tab_mid:
    st.subheader("Spread Middle Detection")
    selected_mid_sport = st.selectbox("Sport ", sports, key="mid_sport")

    mid_base = odds_df.copy()
    if selected_mid_sport != "All":
        mid_base = mid_base[mid_base["sport"] == selected_mid_sport]

    spread_mids = find_spread_middles(mid_base)
    if spread_mids.empty:
        st.info("No spread middles found.")
    else:
        st.dataframe(spread_mids, use_container_width=True)


# =========================================================
# BEST BETS
# =========================================================
with tab_live:
    st.subheader("Best Bets Dashboard")

    sport_opts = ["All"] + sorted(props_shop["sport"].dropna().astype(str).unique().tolist()) if not props_shop.empty else ["All"]
    segment_opts = ["All"] + sorted(props_shop["game_segment"].dropna().astype(str).unique().tolist()) if not props_shop.empty else ["All"]
    prop_opts = ["All"] + sorted(props_shop["prop_type"].dropna().astype(str).unique().tolist()) if not props_shop.empty else ["All"]
    book_opts = ["All"] + sorted(props_shop["book"].dropna().astype(str).unique().tolist()) if not props_shop.empty else ["All"]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        selected_prop_sport = st.selectbox("Sport", sport_opts, key="bb_sport")
    with c2:
        selected_segment = st.selectbox("Segment", segment_opts, key="bb_segment")
    with c3:
        selected_prop_type = st.selectbox("Prop Type", prop_opts, key="bb_type")
    with c4:
        selected_book = st.selectbox("Book", book_opts, key="bb_book")

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        starters_only = st.checkbox("Starters Only", value=True)
    with c6:
        confirmed_only = st.checkbox("Confirmed Only", value=False)
    with c7:
        min_edge = st.slider("Min Edge Score", 0, 100, 60, 5)
    with c8:
        best_shop_only = st.checkbox("Best Line Shop Only", value=True)

    c9, c10, c11 = st.columns(3)
    with c9:
        min_odds = st.slider("Min Odds", -300, 200, -300, 5)
    with c10:
        max_odds = st.slider("Max Odds", -300, 200, 200, 5)
    with c11:
        min_hit = st.slider("Min Hit %", 50, 95, 54, 1)

    min_ev = st.slider("Min EV Edge %", -10, 25, 0, 1)

    base_source = props_shop.copy() if best_shop_only else props_live.copy()
    filtered = filter_props_base(
        base_source,
        sport=selected_prop_sport,
        segment=selected_segment,
        starters_only=starters_only,
        confirmed_only=confirmed_only,
        min_odds=min_odds,
        max_odds=max_odds,
        min_edge=min_edge,
        min_hit_prob=min_hit,
        min_ev=min_ev,
        book=selected_book,
        prop_type=selected_prop_type,
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Props Found", len(filtered))
    m2.metric("A-Grade", int((filtered["edge_score"] >= 86).sum()) if not filtered.empty else 0)
    m3.metric("Avg Edge", round(filtered["edge_score"].mean(), 1) if not filtered.empty else 0)
    m4.metric("Avg Hit %", f"{round(filtered['hit_probability'].mean()*100, 1) if not filtered.empty else 0}%")

    if filtered.empty:
        st.warning("No props match the current filters.")
    else:
        st.markdown("### Top plays cards")
        for idx, (_, row) in enumerate(filtered.head(10).iterrows(), start=1):
            render_top_play_card(row, idx)

        st.markdown("### Best bets table")
        dashboard_df = build_best_bets_dashboard(filtered)
        st.dataframe(format_props_table(dashboard_df), use_container_width=True)


# =========================================================
# INJURIES / STARTERS
# =========================================================
with tab_inj:
    st.subheader("Injuries / Starter Status Panel")

    if injuries_df.empty:
        st.info("No injury/starter feed loaded.")
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
# LINE MOVEMENT
# =========================================================
with tab_lines:
    st.subheader("Line Movement Tracker")

    if movement_summary.empty:
        st.info("No line history feed loaded.")
    else:
        st.dataframe(movement_summary, use_container_width=True)

    st.markdown("### Compare latest props with movement")
    if props_live.empty:
        st.info("No props available.")
    else:
        cols = [
            "player", "team", "opponent", "book", "prop_type", "game_segment",
            "line", "odds", "line_move", "odds_move", "last_update",
            "projection", "recommended_side", "edge_score", "expected_value_edge"
        ]
        st.dataframe(format_props_table(props_live[cols]), use_container_width=True)


st.markdown("---")
st.caption("V4 full clean build — live-data wiring structure for future CSV/API upgrades.")
