
# ============================================================
# SPORTS AI BETTING DASHBOARD — DEV MODE V17
# EV CURVE V1
# ============================================================
# Real working file
#
# What changed:
# - Replaces flat EV cap behavior with a curved EV model
# - Better separates strong plays from merely good plays
# - Makes 0.75u plays more meaningful
# - Keeps Model Variance V1, Tier System V2, Correlation Filter V3
# ============================================================

import math
from datetime import datetime
from io import BytesIO

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Sports AI Betting Dashboard DEV MODE V17", page_icon="🏀", layout="wide")
st.title("🏀 Sports AI Betting Dashboard — DEV MODE V17")
st.caption("EV CURVE V1")

SPORTS = ["NBA", "WNBA", "NHL", "MLB", "NFL"]
BOOKS = ["DraftKings", "FanDuel", "BetMGM"]

NBA_PLAYERS = [
    ("Giannis Antetokounmpo", "Bucks"),
    ("Tyrese Haliburton", "Pacers"),
    ("LeBron James", "Lakers"),
    ("Jayson Tatum", "Celtics"),
    ("Stephen Curry", "Warriors"),
]

PROP_TYPES_BY_SPORT = {
    "NBA": ["points", "rebounds", "assists", "3pt_made", "turnovers", "pra", "pr", "pa", "ra"]
}

TRACKER_COLUMNS = [
    "bet_id", "added_at", "sport", "player", "opponent", "book", "game_segment",
    "prop_type", "side", "line", "odds", "projection", "edge", "hit_probability",
    "ev_edge", "edge_score", "play_tier", "steam_flag", "bet_timing",
    "bet_size_units", "bet_size_label", "result", "profit_units", "actual_stat",
    "grade_source", "notes"
]

PLAYER_PROFILE = {
    "Giannis Antetokounmpo": {"points": 1.12, "rebounds": 1.13, "assists": 1.00, "pra": 1.10, "ra": 1.08},
    "Tyrese Haliburton": {"assists": 1.18, "points": 0.98, "pra": 1.08, "pa": 1.06},
    "LeBron James": {"points": 1.02, "rebounds": 1.03, "assists": 1.12, "pra": 1.07, "pa": 1.08},
    "Jayson Tatum": {"points": 1.08, "rebounds": 1.08, "assists": 0.95, "3pt_made": 1.10, "pr": 1.05},
    "Stephen Curry": {"points": 1.11, "3pt_made": 1.18, "assists": 0.93, "pr": 1.06},
}

TEAM_MATCHUP = {
    "Bucks": {"pace": 1.02, "matchup": 1.00},
    "Pacers": {"pace": 1.06, "matchup": 1.07},
    "Lakers": {"pace": 1.01, "matchup": 1.02},
    "Celtics": {"pace": 1.03, "matchup": 1.01},
    "Warriors": {"pace": 1.04, "matchup": 1.05},
}

SIGMA_MAP = {
    "points": 6.5, "rebounds": 3.0, "assists": 3.2, "3pt_made": 1.6,
    "turnovers": 1.8, "pra": 8.4, "pr": 6.8, "pa": 7.0, "ra": 5.2
}

PLAYER_VARIANCE = {
    "Giannis Antetokounmpo": 1.10,
    "Tyrese Haliburton": 1.08,
    "LeBron James": 1.04,
    "Jayson Tatum": 1.00,
    "Stephen Curry": 1.12,
}

PROP_VARIANCE = {
    "points": 1.05,
    "rebounds": 0.96,
    "assists": 1.00,
    "3pt_made": 1.14,
    "turnovers": 0.92,
    "pra": 1.08,
    "pr": 1.03,
    "pa": 1.01,
    "ra": 0.98,
}

TEAM_DISPERSION = {
    "Bucks": 1.02,
    "Pacers": 1.10,
    "Lakers": 1.03,
    "Celtics": 0.98,
    "Warriors": 1.08,
}

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

def american_to_decimal(odds):
    odds = safe_float(odds)
    if pd.isna(odds):
        return np.nan
    return 1 + (odds / 100.0) if odds > 0 else 1 + (100.0 / abs(odds))

def implied_prob_american(odds):
    odds = safe_float(odds)
    if pd.isna(odds):
        return np.nan
    return 100 / (odds + 100) if odds > 0 else abs(odds) / (abs(odds) + 100)

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

def edge_bucket(score):
    if score >= 86:
        return "🟢 A"
    if score >= 76:
        return "🟢 B"
    if score >= 66:
        return "🟡 C"
    return "🔴 Pass"

def tier_badge(tier):
    return {"Tier 1": "🟢 Tier 1", "Tier 2": "🟡 Tier 2", "Tier 3": "⚪ Tier 3"}.get(tier, tier)

def load_csv_or_empty(uploaded_file):
    if uploaded_file is None:
        return pd.DataFrame()
    try:
        if str(uploaded_file.name).lower().endswith(".csv"):
            return pd.read_csv(uploaded_file)
        return pd.read_excel(uploaded_file)
    except Exception:
        return pd.DataFrame()

def init_tracker_state():
    if "bet_tracker_df" not in st.session_state:
        st.session_state["bet_tracker_df"] = pd.DataFrame(columns=TRACKER_COLUMNS)

def make_sample_props_df():
    rows = []
    event_map = {
        "Bucks": ("nba_1", "Bucks vs Heat"),
        "Pacers": ("nba_2", "Cavaliers vs Pacers"),
        "Lakers": ("nba_3", "Warriors vs Lakers"),
        "Celtics": ("nba_4", "Knicks vs Celtics"),
        "Warriors": ("nba_3", "Warriors vs Lakers"),
    }
    stat_bases = {
        "points": 27.5, "rebounds": 7.5, "assists": 6.5, "3pt_made": 3.5,
        "turnovers": 2.5, "pra": 38.5, "pr": 32.5, "pa": 31.5, "ra": 13.5
    }
    for player, team in NBA_PLAYERS:
        event_id, opponent = event_map[team]
        for prop_type in PROP_TYPES_BY_SPORT["NBA"]:
            for book_idx, book in enumerate(BOOKS):
                line = stat_bases[prop_type] + (-0.5 + book_idx * 0.5)
                if book == "FanDuel" and prop_type in ["points", "pra", "assists"]:
                    line += 0.5
                if book == "BetMGM" and prop_type in ["3pt_made", "rebounds", "pr"]:
                    line -= 0.5
                odds = [-115, -105, 100][book_idx]
                rows.append({
                    "sport": "NBA",
                    "event_id": event_id,
                    "player": player,
                    "team": team,
                    "opponent": opponent,
                    "prop_type": prop_type,
                    "line": round(line, 1),
                    "projection": np.nan,
                    "odds": odds,
                    "game_segment": "full_game",
                    "book": book,
                })
    return pd.DataFrame(rows)

def sample_auto_grade_template():
    return pd.DataFrame([
        ["LeBron James", "pa", 34],
        ["Tyrese Haliburton", "points", 29],
    ], columns=["player", "prop_type", "actual_stat"])

def sample_bet_log_import_template():
    return pd.DataFrame([
        ["2026-03-19 09:00:00", "NBA", "LeBron James", "Warriors vs Lakers", "DraftKings", "full_game", "pa", "Over", 30.5, -115, 35.5, 5.0, 0.63, 9.1, 77.5, "Tier 2", "➖ Stable", "Okay now", 0.5, "0.5u Standard", "Win", 0.43, 34, "Import", "Imported historical bet"],
    ], columns=["added_at", "sport", "player", "opponent", "book", "game_segment", "prop_type", "side", "line", "odds", "projection", "edge", "hit_probability", "ev_edge", "edge_score", "play_tier", "steam_flag", "bet_timing", "bet_size_units", "bet_size_label", "result", "profit_units", "actual_stat", "grade_source", "notes"])

def apply_auto_projections(df, dev_strength):
    out = df.copy()
    projections = []
    variance_tags = []
    for _, row in out.iterrows():
        line = safe_float(row["line"])
        player = row["player"]
        prop_type = row["prop_type"]
        team = row["team"]

        base_multiplier = PLAYER_PROFILE.get(player, {}).get(prop_type, 1.0)
        pace = TEAM_MATCHUP.get(team, {}).get("pace", 1.0)
        matchup = TEAM_MATCHUP.get(team, {}).get("matchup", 1.0)

        player_var = PLAYER_VARIANCE.get(player, 1.0)
        prop_var = PROP_VARIANCE.get(prop_type, 1.0)
        team_var = TEAM_DISPERSION.get(team, 1.0)

        deterministic_seed = ((sum(ord(c) for c in player + prop_type + team) % 17) - 8) / 100.0
        shaped_variance = deterministic_seed * player_var * prop_var * team_var * dev_strength

        projection = line * base_multiplier * pace * matchup * (1 + shaped_variance)

        cap = {
            "points": 5.0, "pra": 5.5, "assists": 4.0, "rebounds": 4.2,
            "3pt_made": 1.9, "pr": 4.8, "pa": 4.8, "ra": 3.8
        }.get(prop_type, 4.0)
        projection = min(max(projection, line - cap), line + cap)
        projections.append(projection)

        if shaped_variance >= 0.05:
            variance_tags.append("High-upside profile")
        elif shaped_variance <= -0.04:
            variance_tags.append("Lower-volatility profile")
        else:
            variance_tags.append("Neutral variance")
    out["projection"] = projections
    out["variance_note"] = variance_tags
    return out

def calibrated_hit_probability(row):
    line = safe_float(row["line"])
    proj = safe_float(row["projection"])
    sigma = SIGMA_MAP.get(row["prop_type"], 5.5)

    player_var = PLAYER_VARIANCE.get(row["player"], 1.0)
    prop_var = PROP_VARIANCE.get(row["prop_type"], 1.0)
    team_var = TEAM_DISPERSION.get(row["team"], 1.0)

    sigma_adj = sigma / max(0.85, min(1.18, (player_var * 0.45 + prop_var * 0.35 + team_var * 0.20)))
    z = (proj - line) / sigma_adj if sigma_adj > 0 else 0

    raw = 0.5 * (1 + math.erf(z / math.sqrt(2)))

    compress = 0.52 + ((player_var - 1.0) * 0.10) + ((prop_var - 1.0) * 0.08) + ((team_var - 1.0) * 0.06)
    compress = max(0.46, min(0.62, compress))

    calibrated = 0.50 + (raw - 0.50) * compress
    calibrated = max(0.36, min(0.69, calibrated))
    return calibrated if proj > line else 1 - calibrated

# EV CURVE V1
def curved_ev_edge(prob, implied_prob, edge_abs, prop_type, variance_note):
    prob = safe_float(prob)
    implied_prob = safe_float(implied_prob)
    edge_abs = safe_float(edge_abs)
    if pd.isna(prob) or pd.isna(implied_prob):
        return np.nan

    raw_gap = (prob - implied_prob) * 100.0

    edge_factor = 1.0 + min(0.30, max(0.0, edge_abs) / 20.0)
    prop_factor = {
        "points": 1.04,
        "rebounds": 0.96,
        "assists": 0.99,
        "3pt_made": 1.08,
        "turnovers": 0.94,
        "pra": 1.03,
        "pr": 1.01,
        "pa": 1.00,
        "ra": 0.97,
    }.get(prop_type, 1.0)
    variance_factor = {
        "High-upside profile": 1.05,
        "Neutral variance": 1.00,
        "Lower-volatility profile": 0.95,
    }.get(str(variance_note), 1.0)

    shaped_gap = raw_gap * edge_factor * prop_factor * variance_factor

    if shaped_gap >= 0:
        curved = 13.5 * math.tanh(shaped_gap / 11.5)
    else:
        curved = -8.0 * math.tanh(abs(shaped_gap) / 8.5)

    return round(curved, 2)

def classify_play_tier(row):
    score = safe_float(row["edge_score"])
    hitp = safe_float(row["hit_probability"]) * 100
    ev = safe_float(row["expected_value_edge"])

    if score >= 81 and hitp >= 61 and ev >= 6.2:
        return "Tier 1", "Core play profile"
    if score >= 68 and hitp >= 57 and ev >= 2.5:
        return "Tier 2", "Strong secondary play"
    return "Tier 3", "Watchlist / lower conviction"

def compute_prop_scores(df):
    out = df.copy()
    out["proj_edge"] = out["projection"] - out["line"]
    out["recommended_side"] = np.where(out["projection"] > out["line"], "Over", "Under")
    out["hit_probability"] = out.apply(calibrated_hit_probability, axis=1)
    out["book_implied_prob"] = out["odds"].apply(implied_prob_american)

    out["expected_value_edge"] = out.apply(
        lambda r: curved_ev_edge(
            r["hit_probability"],
            r["book_implied_prob"],
            abs(safe_float(r["proj_edge"])),
            r["prop_type"],
            r.get("variance_note", "Neutral variance")
        ),
        axis=1
    )

    player_var_component = out["player"].map(lambda p: PLAYER_VARIANCE.get(p, 1.0))
    prop_var_component = out["prop_type"].map(lambda p: PROP_VARIANCE.get(p, 1.0))

    score = (
        np.clip(out["proj_edge"].abs() * 7.4, 0, 31) +
        np.clip((out["hit_probability"] - 0.50) * 126, 0, 24) +
        np.clip(out["expected_value_edge"] * 1.55, -6, 20) +
        np.clip((player_var_component - 1.0) * 18, -2, 3) +
        np.clip((prop_var_component - 1.0) * 14, -2, 3)
    )
    out["edge_score"] = np.clip(score, 0, 100).round(1)
    out["bet_grade"] = out["edge_score"].apply(edge_bucket)

    tiers = out.apply(classify_play_tier, axis=1, result_type="expand")
    out["play_tier"] = tiers[0]
    out["tier_reason"] = tiers[1]
    return out

def apply_line_shopping(df):
    parts = []
    for _, group in df.groupby(["player", "prop_type", "game_segment", "recommended_side"], dropna=False):
        side = group["recommended_side"].iloc[0]
        ordered = group.sort_values(["line", "odds", "edge_score"], ascending=[side == "Over", False, False])
        best = ordered.iloc[0]
        group = group.copy()
        group["best_book"] = best["book"]
        group["best_line"] = best["line"]
        group["best_odds"] = best["odds"]
        parts.append(group)
    return pd.concat(parts, ignore_index=True)

def best_line_shop(df):
    rows = []
    for _, group in df.groupby(["player", "prop_type", "game_segment", "recommended_side"], dropna=False):
        side = group["recommended_side"].iloc[0]
        ordered = group.sort_values(["line", "odds", "edge_score"], ascending=[side == "Over", False, False])
        rows.append(ordered.iloc[0])
    return pd.DataFrame(rows).reset_index(drop=True).sort_values(["bet_size_units", "edge_score"], ascending=[False, False])

def create_live_snapshot_variant(df):
    out = df.copy()
    new_lines = []
    new_odds = []
    for _, row in out.iterrows():
        variant = (sum(ord(c) for c in f"{row['player']}{row['prop_type']}{row['book']}") % 5) - 2
        new_lines.append(safe_float(row["line"]) + (0.5 if variant == 2 else (-0.5 if variant == -2 else 0.0)))
        new_odds.append(safe_float(row["odds"]) + (-8 if variant == 1 else (8 if variant == -1 else 0)))
    out["line"] = new_lines
    out["odds"] = new_odds
    return out

def apply_steam_signals(current_df, previous_df):
    cur = current_df.copy()
    if previous_df is None or previous_df.empty:
        cur["steam_flag"] = "➖ Stable"
        cur["bet_timing"] = "Okay now"
        return cur
    prev_small = previous_df[["player", "prop_type", "game_segment", "book", "line", "odds"]].rename(columns={"line": "prev_line", "odds": "prev_odds"})
    merged = cur.merge(prev_small, on=["player", "prop_type", "game_segment", "book"], how="left")
    line_move = merged["line"] - merged["prev_line"]
    odds_move = merged["prev_odds"] - merged["odds"]
    merged["steam_flag"] = np.where((line_move >= 0.5) | (odds_move >= 8), "📈 Steam", "➖ Stable")
    merged["bet_timing"] = np.where(merged["steam_flag"] == "📈 Steam", "Bet now", "Okay now")
    return merged.drop(columns=["prev_line", "prev_odds"])

def overlap_strength(prop_a, prop_b):
    pair = {normalize_text(prop_a), normalize_text(prop_b)}
    if prop_a == prop_b:
        return "strong"
    strong_pairs = [
        {"pra", "pa"}, {"pra", "pr"}, {"pra", "ra"},
        {"points", "pr"}, {"assists", "pa"}, {"rebounds", "ra"}
    ]
    medium_pairs = [
        {"points", "pa"}, {"points", "pra"}, {"assists", "pra"},
        {"rebounds", "pra"}, {"points", "3pt_made"}, {"assists", "pr"}
    ]
    if pair in strong_pairs:
        return "strong"
    if pair in medium_pairs:
        return "medium"
    return "weak"

def apply_correlation_filter_v3(df):
    out = df.copy()
    out["correlation_flag"] = ""
    out["correlation_rank_note"] = ""
    out["exposure_flag"] = ""
    out["correlation_penalty"] = 0.0

    parts = []
    for (player, game_segment), group in out.groupby(["player", "game_segment"], dropna=False):
        group = group.sort_values(["edge_score", "expected_value_edge", "hit_probability"], ascending=[False, False, False]).copy()
        if len(group) == 1:
            parts.append(group)
            continue

        anchor_idx = group.index[0]
        anchor_prop = group.loc[anchor_idx, "prop_type"]
        group.loc[anchor_idx, "correlation_rank_note"] = "Top same-player prop kept at full size"

        for idx in group.index[1:]:
            strength = overlap_strength(anchor_prop, group.loc[idx, "prop_type"])
            if strength == "strong":
                group.loc[idx, "correlation_penalty"] = 0.25
                group.loc[idx, "correlation_flag"] = "⚠️ Strong overlap"
                group.loc[idx, "exposure_flag"] = f"Reduced vs top prop: {anchor_prop}"
                group.loc[idx, "correlation_rank_note"] = "Heavy reduction"
            elif strength == "medium":
                group.loc[idx, "correlation_penalty"] = 0.15
                group.loc[idx, "correlation_flag"] = "⚠️ Medium overlap"
                group.loc[idx, "exposure_flag"] = f"Light reduction vs top prop: {anchor_prop}"
                group.loc[idx, "correlation_rank_note"] = "Light reduction"
            else:
                group.loc[idx, "correlation_rank_note"] = "No meaningful overlap"
        parts.append(group)

    return pd.concat(parts, ignore_index=True)

def kelly_fraction_from_row(row):
    p = safe_float(row["hit_probability"])
    dec = american_to_decimal(row["odds"])
    if pd.isna(p) or pd.isna(dec) or dec <= 1:
        return 0.0
    b = dec - 1
    q = 1 - p
    return max(0.0, (b * p - q) / b)

def base_bet_size(row):
    tier = row["play_tier"]
    steam = row["steam_flag"]
    units = 0.25
    reasons = []

    if tier == "Tier 1":
        units = 0.75
        reasons.append("Tier 1 base")
    elif tier == "Tier 2":
        units = 0.50
        reasons.append("Tier 2 base")
    else:
        units = 0.25
        reasons.append("Tier 3 base")

    if steam == "📈 Steam" and tier in ["Tier 1", "Tier 2"]:
        units += 0.25
        reasons.append("Steam boost")

    if safe_float(row["expected_value_edge"]) >= 7.5 and safe_float(row["edge_score"]) >= 77:
        units += 0.25
        reasons.append("High-quality boost")

    return units, reasons

def apply_bet_sizing(df):
    out = df.copy()
    out["kelly_fraction"] = out.apply(kelly_fraction_from_row, axis=1)

    final_units = []
    labels = []
    reasons_out = []

    for _, row in out.iterrows():
        units, reasons = base_bet_size(row)
        penalty = safe_float(row.get("correlation_penalty", 0.0))
        if penalty > 0:
            units -= penalty
            reasons.append(f"Correlation reduction ({penalty:.2f}u)")

        kelly = safe_float(row["kelly_fraction"])
        if kelly > 0:
            kelly_cap = min(1.0, max(0.25, round((kelly * 0.35) / 0.01) * 0.25))
            units = min(units, kelly_cap)
            reasons.append("Kelly cap")

        units = max(0.0, min(1.0, round(units * 20) / 20))
        if units >= 0.75:
            label = "0.75u Strong"
        elif units >= 0.50:
            label = "0.5u Standard"
        elif units >= 0.35:
            label = "0.35u Reduced"
        elif units >= 0.25:
            label = "0.25u Small"
        else:
            label = "Pass"

        final_units.append(units)
        labels.append(label)
        reasons_out.append(" | ".join(reasons))

    out["bet_size_units"] = final_units
    out["bet_size_label"] = labels
    out["bet_size_reason"] = reasons_out
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
    <b>Odds:</b> {int(row['odds'])} |
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
    <b>Best Odds:</b> {int(row['best_odds'])}
  </div>
  <div style="margin-top:8px;">
    <b>Bet Size:</b> {row['bet_size_label']} ({row['bet_size_units']:.2f}u) |
    <b>Kelly:</b> {row['kelly_fraction']*100:.2f}%
  </div>
  <div style="margin-top:8px;">
    <b>Variance:</b> {row['variance_note']} |
    <b>Correlation:</b> {row['correlation_flag'] if row['correlation_flag'] else 'None'}
  </div>
  <div style="margin-top:8px;">
    <b>Note:</b> {row['correlation_rank_note'] if row['correlation_rank_note'] else 'Top play or no issue'} |
    <b>Exposure:</b> {row['exposure_flag'] if row['exposure_flag'] else 'OK'}
  </div>
</div>
""",
        unsafe_allow_html=True
    )

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
        "actual_stat": np.nan,
        "grade_source": "",
        "notes": row.get("exposure_flag", ""),
    }
    st.session_state["bet_tracker_df"] = pd.concat([pd.DataFrame([new_row]), tracker], ignore_index=True)

def grade_result_from_actual(side, line, actual_stat):
    line = safe_float(line)
    actual_stat = safe_float(actual_stat)
    if pd.isna(line) or pd.isna(actual_stat):
        return "Open"
    if actual_stat == line:
        return "Push"
    return "Win" if ((side == "Over" and actual_stat > line) or (side != "Over" and actual_stat < line)) else "Loss"

def tracker_update_results(df):
    tracker = st.session_state["bet_tracker_df"].copy()
    for _, upd in df.iterrows():
        mask = tracker["bet_id"] == upd["bet_id"]
        tracker.loc[mask, "actual_stat"] = pd.to_numeric(pd.Series([upd["actual_stat"]]), errors="coerce").iloc[0]
        tracker.loc[mask, "result"] = upd["result"]
        tracker.loc[mask, "notes"] = upd["notes"]
        tracker.loc[mask, "grade_source"] = "Manual"
        tracker.loc[mask, "profit_units"] = profit_units_from_result(upd["result"], tracker.loc[mask, "odds"].iloc[0], tracker.loc[mask, "bet_size_units"].iloc[0])
    st.session_state["bet_tracker_df"] = tracker

def auto_grade_tracker_from_stats(stats_df):
    tracker = st.session_state["bet_tracker_df"].copy()
    stats = stats_df.copy()
    stats.columns = [c.strip().lower() for c in stats.columns]
    if not {"player", "prop_type", "actual_stat"}.issubset(set(stats.columns)):
        return -1
    stats["player"] = stats["player"].astype(str)
    stats["prop_type"] = stats["prop_type"].apply(normalize_text)
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

def normalize_import_log(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=TRACKER_COLUMNS)
    out = df.copy()
    out.columns = [c.strip().lower() for c in out.columns]
    rename_map = {
        "segment": "game_segment", "market": "prop_type", "recommended_side": "side",
        "units": "bet_size_units", "unit_label": "bet_size_label", "ev": "ev_edge",
        "score": "edge_score", "tier": "play_tier", "steam": "steam_flag",
        "timing": "bet_timing", "actual": "actual_stat", "grade": "result"
    }
    for old, new in rename_map.items():
        if old in out.columns and new not in out.columns:
            out = out.rename(columns={old: new})

    defaults = {c: np.nan for c in TRACKER_COLUMNS}
    defaults.update({"bet_id": "", "added_at": current_ts_str(), "result": "Open", "grade_source": "Import", "notes": ""})
    for col, val in defaults.items():
        if col not in out.columns:
            out[col] = val

    for col in ["line", "odds", "projection", "edge", "hit_probability", "ev_edge", "edge_score", "bet_size_units", "profit_units", "actual_stat"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    for col in ["bet_id", "added_at", "sport", "player", "opponent", "book", "game_segment", "prop_type", "side", "play_tier", "steam_flag", "bet_timing", "bet_size_label", "result", "grade_source", "notes"]:
        out[col] = out[col].fillna("").astype(str)

    out["prop_type"] = out["prop_type"].apply(normalize_text)
    out["game_segment"] = out["game_segment"].apply(normalize_text)
    out["bet_id"] = np.where(out["bet_id"].str.len() > 0, out["bet_id"], [f"IMPORT-{i+1:04d}" for i in range(len(out))])

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
    if replace_existing:
        st.session_state["bet_tracker_df"] = normalized
        return len(normalized)
    combined = pd.concat([st.session_state["bet_tracker_df"], normalized], ignore_index=True)
    combined = combined.drop_duplicates(subset=["bet_id"], keep="first")
    st.session_state["bet_tracker_df"] = combined
    return len(normalized)

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
        "bets": len(df),
        "open": int((df["result"] == "Open").sum()),
        "graded": len(graded),
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "win_rate": (wins / max(1, wins + losses)) * 100,
        "units": units,
        "roi": (units / max(1e-9, risked)) * 100 if risked > 0 else 0.0
    }

# Build live data
init_tracker_state()

st.sidebar.header("DEV MODE V17")
sport_name = st.sidebar.selectbox("Sport", SPORTS, index=0)
dev_strength = st.sidebar.slider("Auto projection aggressiveness", 0.50, 1.50, 1.00, 0.05)
projection_file = st.sidebar.file_uploader("Optional projection CSV override", type=["csv", "xlsx"])

props_df = make_sample_props_df()
props_df = props_df[props_df["sport"] == sport_name].copy()
props_df = apply_auto_projections(props_df, dev_strength)

if projection_file is not None:
    overlay = load_csv_or_empty(projection_file)
    if not overlay.empty:
        overlay.columns = [c.strip().lower() for c in overlay.columns]
        if {"player", "prop_type", "projection"}.issubset(set(overlay.columns)):
            overlay["prop_type"] = overlay["prop_type"].apply(normalize_text)
            props_df = props_df.merge(
                overlay[["player", "prop_type", "projection"]].drop_duplicates(),
                on=["player", "prop_type"],
                how="left",
                suffixes=("", "_ov")
            )
            props_df["projection"] = np.where(~pd.isna(props_df["projection_ov"]), props_df["projection_ov"], props_df["projection"])
            props_df = props_df.drop(columns=["projection_ov"])

base_scored = compute_prop_scores(props_df)
base_scored = apply_line_shopping(base_scored)

prev_snapshot = st.session_state.get("latest_props_live", pd.DataFrame())
live_market = create_live_snapshot_variant(base_scored)
live_market = compute_prop_scores(live_market)
live_market = apply_line_shopping(live_market)
live_market = apply_steam_signals(live_market, prev_snapshot)
live_market = apply_correlation_filter_v3(live_market)
live_market = apply_bet_sizing(live_market)
props_live = live_market.copy()
props_shop = best_line_shop(props_live)
st.session_state["latest_props_live"] = props_live.copy()

tab_home, tab_best, tab_tracker, tab_import, tab_templates = st.tabs([
    "Home", "Best Bets", "Bet Tracker", "Bet Log Import", "Templates"
])

with tab_home:
    st.subheader("EV Curve V1 audit")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Props Rows", len(props_live))
    c2.metric("Tier 1", int((props_live["play_tier"] == "Tier 1").sum()))
    c3.metric("Tier 2", int((props_live["play_tier"] == "Tier 2").sum()))
    c4.metric("0.75u", int((props_live["bet_size_units"] >= 0.75).sum()))
    audit = props_shop[[
        "player", "prop_type", "line", "projection", "hit_probability", "expected_value_edge",
        "edge_score", "play_tier", "bet_size_units", "variance_note"
    ]].head(12).copy()
    audit["hit_probability"] = (audit["hit_probability"] * 100).round(1)
    st.dataframe(audit, use_container_width=True)
    st.info("EV Curve V1 uses a nonlinear curve instead of a flat ceiling so top plays separate more cleanly and repeated EV plateaus show up less often.")

with tab_best:
    st.subheader("Best Bets")
    filtered = props_shop.head(15)
    if filtered.empty:
        st.warning("No props available.")
    else:
        for idx, (_, row) in enumerate(filtered.iterrows(), start=1):
            render_top_play_card(row, idx)

        show = filtered[[
            "player", "prop_type", "recommended_side", "line", "odds", "projection",
            "proj_edge", "hit_probability", "expected_value_edge", "edge_score",
            "play_tier", "steam_flag", "bet_size_units", "bet_size_label",
            "variance_note", "correlation_flag", "correlation_rank_note", "bet_size_reason"
        ]].copy()
        show["hit_probability"] = (show["hit_probability"] * 100).round(1)
        st.dataframe(show, use_container_width=True)

        options = [f"{r.player} | {r.recommended_side} {r.line} {r.prop_type} | {r.book} | {r.bet_size_units:.2f}u" for _, r in filtered.iterrows()]
        lookup = {options[i]: filtered.iloc[i] for i in range(len(options))}
        selected = st.selectbox("Add play to tracker", options)
        if st.button("Add selected play to tracker"):
            tracker_add_bet(lookup[selected])
            st.success("Play added to tracker")

with tab_tracker:
    st.subheader("Bet Tracker")
    tracker_df = st.session_state["bet_tracker_df"].copy()
    stats = tracker_summary(tracker_df)
    a, b, c, d, e = st.columns(5)
    a.metric("Total Bets", stats["bets"])
    b.metric("Open", stats["open"])
    c.metric("Win %", f"{stats['win_rate']:.1f}%")
    d.metric("Units", f"{stats['units']:.2f}")
    e.metric("ROI %", f"{stats['roi']:.1f}%")

    if tracker_df.empty:
        st.info("No tracked bets yet.")
    else:
        show = tracker_df.copy()
        show["hit_probability"] = (pd.to_numeric(show["hit_probability"], errors="coerce") * 100).round(1)
        st.dataframe(show, use_container_width=True)

        open_bets = tracker_df[tracker_df["result"] == "Open"].copy()
        if not open_bets.empty:
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
                key="grade_editor_v17"
            )
            if st.button("Save manual grading"):
                tracker_update_results(edited[["bet_id", "actual_stat", "result", "notes"]])
                st.success("Tracker updated")

        auto_template = sample_auto_grade_template()
        st.dataframe(auto_template, use_container_width=True)
        st.download_button("Download auto-grade template CSV", auto_template.to_csv(index=False).encode("utf-8"), "auto_grade_template.csv", "text/csv")
        auto_file = st.file_uploader("Upload stats file for auto-grading", type=["csv", "xlsx"], key="auto_grade_v17")
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

        st.download_button("Download bet tracker CSV", tracker_df.to_csv(index=False).encode("utf-8"), "bet_tracker_v17.csv", "text/csv")
        xlsx_buffer = BytesIO()
        with pd.ExcelWriter(xlsx_buffer, engine="openpyxl") as writer:
            tracker_df.to_excel(writer, sheet_name="Bets", index=False)
        st.download_button("Download bet tracker Excel", xlsx_buffer.getvalue(), "bet_tracker_v17.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

with tab_import:
    st.subheader("CSV Bet Log Import")
    template_df = sample_bet_log_import_template()
    st.dataframe(template_df, use_container_width=True)
    st.download_button("Download bet log import template CSV", template_df.to_csv(index=False).encode("utf-8"), "bet_log_import_template.csv", "text/csv")

    import_file = st.file_uploader("Upload historical bet log CSV or Excel", type=["csv", "xlsx"], key="bet_log_import_v17")
    replace_existing = st.checkbox("Replace existing tracker with imported file", value=False)
    if import_file is not None:
        import_df = load_csv_or_empty(import_file)
        if not import_df.empty:
            st.markdown("### Imported file preview")
            st.dataframe(import_df, use_container_width=True)
            normalized = normalize_import_log(import_df)
            st.markdown("### Normalized import preview")
            st.dataframe(normalized, use_container_width=True)
            if st.button("Import bet log into tracker"):
                count = import_bet_log_into_tracker(import_df, replace_existing=replace_existing)
                st.success(f"Imported {count} bet(s) into tracker.")

with tab_templates:
    st.subheader("Templates")
    t1 = sample_auto_grade_template()
    st.markdown("### Auto-grade template")
    st.dataframe(t1, use_container_width=True)
    t2 = sample_bet_log_import_template()
    st.markdown("### Bet log import template")
    st.dataframe(t2, use_container_width=True)
