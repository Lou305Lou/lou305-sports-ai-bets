import math
from typing import Tuple

import numpy as np
import pandas as pd
import streamlit as st


# ============================================================
# Sports AI Betting Dashboard — V7 Step 1
# Multi-AI Consensus Engine
# ============================================================

st.set_page_config(page_title="Sports AI Betting Dashboard", layout="wide")


# -----------------------------
# Helpers
# -----------------------------
def american_to_decimal(odds: float) -> float:
    try:
        odds = float(odds)
    except Exception:
        return np.nan
    if odds > 0:
        return 1 + (odds / 100)
    return 1 + (100 / abs(odds))


def american_to_implied_prob(odds: float) -> float:
    try:
        odds = float(odds)
    except Exception:
        return np.nan
    if odds > 0:
        return 100 / (odds + 100)
    return abs(odds) / (abs(odds) + 100)


def normal_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def prob_over_normal(mean_proj: float, line: float, std_dev: float) -> float:
    if std_dev <= 0:
        return 0.5
    z = (mean_proj - line) / std_dev
    return normal_cdf(z)


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def safe_float(x, default=np.nan):
    try:
        if pd.isna(x):
            return default
        return float(x)
    except Exception:
        return default


def safe_bool(x) -> bool:
    if isinstance(x, bool):
        return x
    if pd.isna(x):
        return False
    s = str(x).strip().lower()
    return s in {"1", "true", "yes", "y", "starter", "starting"}


def bounded_component(series: pd.Series, low: float, high: float, max_points: float) -> pd.Series:
    clipped = series.clip(lower=low, upper=high)
    return ((clipped - low) / (high - low) * max_points).clip(lower=0, upper=max_points)


def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    aliases = {
        "player_name": "player",
        "name": "player",
        "sportsbook": "book",
        "sports_book": "book",
        "team_name": "team",
        "opp": "opponent",
        "market_type": "market",
        "bet_type": "bet_side",
        "selection": "bet_side",
        "odds_american": "odds",
        "american_odds": "odds",
        "proj": "projection",
        "projected": "projection",
        "prop_line": "line",
        "is_starter": "starter",
        "starts": "starter",
        "game": "matchup",
    }

    for old, new in aliases.items():
        if old in df.columns and new not in df.columns:
            df[new] = df[old]

    defaults = {
        "player": "",
        "team": "",
        "opponent": "",
        "matchup": "",
        "market": "",
        "bet_side": "",
        "line": np.nan,
        "projection": np.nan,
        "odds": np.nan,
        "book": "",
        "starter": False,
        "minutes": np.nan,
        "std_dev": np.nan,
        "game_total": np.nan,
        "spread": np.nan,
        "game_time": "",
    }

    for col, val in defaults.items():
        if col not in df.columns:
            df[col] = val

    for c in ["player", "team", "opponent", "matchup", "market", "bet_side", "book", "game_time"]:
        df[c] = df[c].fillna("").astype(str).str.strip()

    for c in ["line", "projection", "odds", "minutes", "std_dev", "game_total", "spread"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df["starter"] = df["starter"].apply(safe_bool)

    if (df["matchup"] == "").any():
        auto_matchup = df["team"].fillna("") + np.where(df["opponent"].fillna("") != "", " vs " + df["opponent"].fillna(""), "")
        df.loc[df["matchup"] == "", "matchup"] = auto_matchup[df["matchup"] == ""]

    return df


def infer_market_std(row: pd.Series) -> float:
    market = str(row.get("market", "")).lower()
    supplied = safe_float(row.get("std_dev"), np.nan)
    if not np.isnan(supplied) and supplied > 0:
        return supplied

    defaults = {
        "points": 8.5,
        "rebounds": 4.0,
        "assists": 3.6,
        "pra": 9.0,
        "threes": 2.3,
        "3pm": 2.3,
        "blocks": 1.4,
        "steals": 1.5,
        "pts+reb+ast": 9.0,
    }
    for key, val in defaults.items():
        if key in market:
            return val
    return 7.5


def infer_bet_side(row: pd.Series) -> str:
    side = str(row.get("bet_side", "")).strip().title()
    if side in {"Over", "Under"}:
        return side
    projection = safe_float(row.get("projection"), np.nan)
    line = safe_float(row.get("line"), np.nan)
    if np.isnan(projection) or np.isnan(line):
        return "Over"
    return "Over" if projection >= line else "Under"


def calculate_hit_probability(row: pd.Series) -> float:
    projection = safe_float(row.get("projection"), np.nan)
    line = safe_float(row.get("line"), np.nan)
    if np.isnan(projection) or np.isnan(line):
        return np.nan
    std_dev = infer_market_std(row)
    side = infer_bet_side(row)
    p_over = prob_over_normal(projection, line, std_dev)
    return clamp01(1 - p_over if side == "Under" else p_over)


def grade_from_score(score: float) -> str:
    if score >= 87:
        return "🟢 A"
    if score >= 79:
        return "🟢 B"
    if score >= 71:
        return "🟡 C"
    if score >= 63:
        return "🟠 D"
    return "🔴 F"


def tier_from_score(score: float) -> str:
    if score >= 87:
        return "🟢 Tier 1"
    if score >= 78:
        return "🟡 Tier 2"
    if score >= 69:
        return "⚪ Tier 3"
    return "⚫ Pass"


def unit_size_from_score(score: float) -> float:
    if score >= 89:
        return 1.00
    if score >= 83:
        return 0.75
    if score >= 76:
        return 0.50
    if score >= 69:
        return 0.25
    return 0.00


def variance_label(std_dev: float, market: str) -> str:
    market = str(market).lower()
    if std_dev >= 8.5:
        return "High-upside profile"
    if "three" in market or "3pm" in market:
        return "High variance"
    if std_dev <= 2.5:
        return "Lower variance"
    return "Neutral variance"


def matchup_label(row: pd.Series) -> str:
    total = safe_float(row.get("game_total"), np.nan)
    spread = abs(safe_float(row.get("spread"), np.nan))
    minutes = safe_float(row.get("minutes"), np.nan)

    if not np.isnan(total) and total >= 236 and (np.isnan(spread) or spread <= 7):
        return "Strong matchup"
    if not np.isnan(minutes) and minutes >= 34:
        return "Stable role"
    if not np.isnan(spread) and spread >= 12:
        return "Blowout risk"
    return "Neutral matchup"


def portfolio_flag(score: float, ev_edge: float, hit_pct: float) -> str:
    if score >= 76 and ev_edge >= 2.5 and hit_pct >= 55:
        return "Selected"
    return "Pass"


# -----------------------------
# Game Script AI
# -----------------------------
def script_type_for_row(row: pd.Series) -> str:
    total = safe_float(row.get("game_total"), np.nan)
    spread = abs(safe_float(row.get("spread"), np.nan))

    if not np.isnan(total) and total >= 238 and (np.isnan(spread) or spread <= 4):
        return "Track meet"
    if not np.isnan(total) and total >= 232 and (np.isnan(spread) or spread <= 7):
        return "Competitive shootout"
    if not np.isnan(total) and total <= 220 and not np.isnan(spread) and spread <= 7:
        return "Slow grind"
    if not np.isnan(spread) and spread >= 12:
        return "Blowout risk"
    return "Neutral environment"


def script_confidence_for_row(row: pd.Series) -> int:
    total = safe_float(row.get("game_total"), np.nan)
    spread = abs(safe_float(row.get("spread"), np.nan))

    score = 50
    if not np.isnan(total):
        if total >= 238:
            score += 20
        elif total >= 232:
            score += 12
        elif total <= 220:
            score += 14

    if not np.isnan(spread):
        if spread <= 3:
            score += 18
        elif spread <= 6:
            score += 10
        elif spread >= 12:
            score += 15
        elif spread >= 9:
            score += 8

    return int(max(40, min(95, score)))


def blowout_risk_label(row: pd.Series) -> str:
    spread = abs(safe_float(row.get("spread"), np.nan))
    if np.isnan(spread):
        return "Unknown"
    if spread >= 14:
        return "High"
    if spread >= 10:
        return "Medium"
    return "Low"


def market_script_direction(row: pd.Series) -> float:
    market = str(row.get("market", "")).lower()
    side = str(row.get("bet_side", "")).lower()
    script_type = str(row.get("script_type", ""))
    starter = safe_bool(row.get("starter"))
    minutes = safe_float(row.get("minutes"), 0)

    boost = 0.0

    if side == "over":
        if script_type == "Track meet":
            boost += 4.0 if any(k in market for k in ["points", "pra", "assists"]) else 2.5
        elif script_type == "Competitive shootout":
            boost += 2.5 if any(k in market for k in ["points", "pra", "assists"]) else 1.5
        elif script_type == "Slow grind":
            boost -= 3.0 if any(k in market for k in ["points", "pra", "assists"]) else -1.5
        elif script_type == "Blowout risk":
            boost -= 4.0 if starter and minutes >= 30 else -1.0

    if side == "under":
        if script_type == "Slow grind":
            boost += 3.0 if any(k in market for k in ["points", "pra", "assists"]) else 1.5
        elif script_type == "Blowout risk":
            boost += 3.5 if starter else 1.5
        elif script_type == "Track meet":
            boost -= 2.5 if any(k in market for k in ["points", "pra", "assists"]) else -1.0

    if "rebounds" in market:
        boost *= 0.7

    return round(boost, 2)


def correlation_group_for_row(row: pd.Series) -> str:
    return f"{row.get('matchup', '')} | {row.get('team', '')} | {row.get('bet_side', '')}"


def correlation_penalty(df: pd.DataFrame) -> pd.Series:
    keys = df["correlation_group"].fillna("")
    counts = keys.map(keys.value_counts())
    minutes = df["minutes"].fillna(0)

    penalty = np.where(
        counts >= 3,
        np.where(minutes >= 32, 4.0, 2.5),
        np.where(counts == 2, np.where(minutes >= 32, 2.0, 1.0), 0.0)
    )
    return pd.Series(penalty, index=df.index)


def market_edge_component(row: pd.Series) -> float:
    edge = safe_float(row.get("projection_edge"), np.nan)
    market = str(row.get("market", "")).lower()
    if np.isnan(edge):
        return 0.0

    if "points" in market or "pra" in market:
        capped = min(edge, 4.5)
        return float(np.interp(capped, [0.5, 1.0, 2.0, 3.0, 4.5], [0, 3, 8, 12, 15]))
    capped = min(edge, 3.0)
    return float(np.interp(capped, [0.3, 0.7, 1.2, 2.0, 3.0], [0, 3, 7, 11, 14]))


def realism_penalty_from_edge_z(z: float) -> float:
    if np.isnan(z):
        return 0.0
    if z <= 0.9:
        return 0.0
    if z <= 1.15:
        return 2.0
    if z <= 1.35:
        return 5.0
    if z <= 1.55:
        return 8.0
    return 11.0


def realism_penalty_from_hit(hit_pct: float) -> float:
    if np.isnan(hit_pct):
        return 0.0
    if hit_pct <= 64:
        return 0.0
    if hit_pct <= 67:
        return 2.0
    if hit_pct <= 70:
        return 4.0
    if hit_pct <= 73:
        return 7.0
    return 10.0


def realism_penalty_from_ev(ev_pct: float) -> float:
    if np.isnan(ev_pct):
        return 0.0
    if ev_pct <= 10:
        return 0.0
    if ev_pct <= 15:
        return 2.0
    if ev_pct <= 20:
        return 4.0
    if ev_pct <= 25:
        return 7.0
    if ev_pct <= 30:
        return 10.0
    return 13.0


# -----------------------------
# Multi-AI model scores
# -----------------------------
def projection_model_score(row: pd.Series) -> float:
    score = 40.0
    edge = safe_float(row.get("projection_edge"), 0)
    edge_z = safe_float(row.get("edge_z"), 0)
    market = str(row.get("market", "")).lower()

    score += min(edge * 8.5, 22)
    score += min(edge_z * 16, 18)

    if any(k in market for k in ["points", "pra", "assists"]):
        score -= max(edge - 4.5, 0) * 2.5
    else:
        score -= max(edge - 3.0, 0) * 2.0

    return round(float(np.clip(score, 0, 100)), 1)


def script_model_score(row: pd.Series) -> float:
    score = 48.0
    score += safe_float(row.get("game_script_boost"), 0) * 4.5
    score += (safe_float(row.get("script_confidence"), 50) - 50) * 0.45

    blowout = str(row.get("blowout_risk", ""))
    if blowout == "High":
        score -= 10
    elif blowout == "Medium":
        score -= 4
    else:
        score += 2

    return round(float(np.clip(score, 0, 100)), 1)


def risk_model_score(row: pd.Series) -> float:
    score = 55.0
    minutes = safe_float(row.get("minutes"), 0)
    starter = safe_bool(row.get("starter"))
    corr_pen = safe_float(row.get("correlation_penalty"), 0)
    variance = str(row.get("variance_note", ""))

    if starter:
        score += 12
    else:
        score -= 15

    if minutes >= 36:
        score += 12
    elif minutes >= 33:
        score += 9
    elif minutes >= 30:
        score += 5
    elif minutes >= 27:
        score += 1
    else:
        score -= 10

    if variance == "High-upside profile":
        score -= 5
    elif variance == "High variance":
        score -= 7
    elif variance == "Lower variance":
        score += 5

    score -= corr_pen * 3

    return round(float(np.clip(score, 0, 100)), 1)


def market_model_score(row: pd.Series) -> float:
    score = 52.0
    ev = safe_float(row.get("ev_edge_pct"), 0)
    hit = safe_float(row.get("hit_pct"), 0)
    realism = str(row.get("realism_flag", ""))

    score += min(ev, 15) * 1.8
    score += max(min(hit, 68) - 55, 0) * 1.25

    if realism == "Review":
        score -= 12
    else:
        score += 4

    score -= max(ev - 20, 0) * 1.3
    score -= max(hit - 70, 0) * 1.5

    return round(float(np.clip(score, 0, 100)), 1)


def portfolio_model_score(row: pd.Series) -> float:
    score = 56.0
    corr_pen = safe_float(row.get("correlation_penalty"), 0)
    status = str(row.get("portfolio_status", ""))
    blowout = str(row.get("blowout_risk", ""))

    if status == "Selected":
        score += 14
    else:
        score -= 12

    score -= corr_pen * 5

    if blowout == "High":
        score -= 8
    elif blowout == "Medium":
        score -= 3
    else:
        score += 2

    return round(float(np.clip(score, 0, 100)), 1)


def consensus_tier(score: float) -> str:
    if score >= 84:
        return "🟢 Strong Buy"
    if score >= 75:
        return "🟡 Buy"
    if score >= 66:
        return "⚪ Lean"
    return "🔴 Pass"


def consensus_action(score: float, agreement: float, review_flag: str) -> str:
    if review_flag == "Review" and score < 78:
        return "Pass"
    if score >= 84 and agreement >= 80:
        return "Bet"
    if score >= 75 and agreement >= 65:
        return "Bet"
    if score >= 66:
        return "Lean"
    return "Pass"


def add_multi_ai_consensus(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    out["projection_model"] = out.apply(projection_model_score, axis=1)
    out["script_model"] = out.apply(script_model_score, axis=1)
    out["risk_model"] = out.apply(risk_model_score, axis=1)
    out["market_model"] = out.apply(market_model_score, axis=1)
    out["portfolio_model"] = out.apply(portfolio_model_score, axis=1)

    model_cols = ["projection_model", "script_model", "risk_model", "market_model", "portfolio_model"]
    out["consensus_score"] = (
        out["projection_model"] * 0.25
        + out["script_model"] * 0.18
        + out["risk_model"] * 0.20
        + out["market_model"] * 0.22
        + out["portfolio_model"] * 0.15
    ).round(1)

    out["model_agreement_pct"] = (
        (out[model_cols] >= 65).sum(axis=1) / len(model_cols) * 100
    ).round(0)

    out["consensus_tier"] = out["consensus_score"].apply(consensus_tier)
    out["consensus_action"] = out.apply(
        lambda r: consensus_action(r["consensus_score"], r["model_agreement_pct"], str(r["realism_flag"])),
        axis=1,
    )

    out["consensus_rank"] = out["consensus_score"].rank(method="dense", ascending=False).astype(int)

    return out


def compute_edges(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    out["bet_side"] = out.apply(infer_bet_side, axis=1)
    out["std_dev_used"] = out.apply(infer_market_std, axis=1)
    out["hit_prob"] = out.apply(calculate_hit_probability, axis=1)
    out["hit_pct"] = (out["hit_prob"] * 100).round(1)

    out["implied_prob"] = out["odds"].apply(american_to_implied_prob)
    out["projection_edge"] = (out["projection"] - out["line"]).round(2)
    under_mask = out["bet_side"].eq("Under")
    out.loc[under_mask, "projection_edge"] = (out.loc[under_mask, "line"] - out.loc[under_mask, "projection"]).round(2)

    dec = out["odds"].apply(american_to_decimal)
    out["ev"] = (out["hit_prob"] * (dec - 1)) - (1 - out["hit_prob"])
    out["ev_edge_pct"] = (out["ev"] * 100).round(2)

    out["edge_z"] = (out["projection_edge"] / out["std_dev_used"]).replace([np.inf, -np.inf], np.nan)
    out["edge_z"] = out["edge_z"].round(3)

    out["script_type"] = out.apply(script_type_for_row, axis=1)
    out["script_confidence"] = out.apply(script_confidence_for_row, axis=1)
    out["blowout_risk"] = out.apply(blowout_risk_label, axis=1)
    out["game_script_boost"] = out.apply(market_script_direction, axis=1)
    out["correlation_group"] = out.apply(correlation_group_for_row, axis=1)
    out["correlation_penalty"] = correlation_penalty(out)

    hit_component = bounded_component(out["hit_pct"], 53, 66, 20)
    ev_component = bounded_component(out["ev_edge_pct"], 0, 12, 12)
    edge_component = out.apply(market_edge_component, axis=1)

    starter_bonus = np.where(out["starter"], 3.0, -10.0)

    minutes_bonus = np.select(
        [
            out["minutes"].fillna(0) >= 36,
            out["minutes"].fillna(0) >= 33,
            out["minutes"].fillna(0) >= 30,
            out["minutes"].fillna(0) >= 27,
        ],
        [7.0, 5.0, 3.0, 1.5],
        default=-3.0,
    )

    matchup_bonus = np.select(
        [
            (out["game_total"].fillna(0) >= 236) & (abs(out["spread"].fillna(0)) <= 7),
            out["game_total"].fillna(0) >= 230,
        ],
        [3.0, 1.0],
        default=0.0,
    )

    price_bonus = np.select(
        [
            (out["odds"] >= -125) & (out["odds"] <= 110),
            (out["odds"] >= -145) & (out["odds"] <= 125),
        ],
        [2.0, 1.0],
        default=0.0,
    )

    spread_penalty = np.select(
        [
            abs(out["spread"].fillna(0)) >= 14,
            abs(out["spread"].fillna(0)) >= 10,
            abs(out["spread"].fillna(0)) >= 8,
        ],
        [6.0, 3.5, 1.5],
        default=0.0,
    )

    edge_z_penalty = out["edge_z"].apply(realism_penalty_from_edge_z)
    hit_realism_penalty = out["hit_pct"].apply(realism_penalty_from_hit)
    ev_realism_penalty = out["ev_edge_pct"].apply(realism_penalty_from_ev)

    combo_penalty = np.where(
        (out["hit_pct"] >= 68) & (out["ev_edge_pct"] >= 20),
        5.0,
        np.where((out["hit_pct"] >= 66) & (out["ev_edge_pct"] >= 15), 2.5, 0.0)
    )

    nonstarter_minutes_penalty = np.where(
        (~out["starter"]) & (out["minutes"].fillna(0) < 28),
        4.0,
        0.0,
    )

    weak_edge_penalty = np.where(out["projection_edge"] < 0.75, 4.0, 0.0)

    out["score"] = (
        42.0
        + hit_component
        + ev_component
        + edge_component
        + starter_bonus
        + minutes_bonus
        + matchup_bonus
        + price_bonus
        + out["game_script_boost"]
        - spread_penalty
        - edge_z_penalty
        - hit_realism_penalty
        - ev_realism_penalty
        - combo_penalty
        - nonstarter_minutes_penalty
        - weak_edge_penalty
        - out["correlation_penalty"]
    ).clip(lower=0, upper=96).round(1)

    out["grade"] = out["score"].apply(grade_from_score)
    out["tier"] = out["score"].apply(tier_from_score)
    out["model_size_u"] = out["score"].apply(unit_size_from_score)
    out["portfolio_size_u"] = np.where(
        out["score"] >= 87, out["model_size_u"] + 0.10,
        np.where(out["score"] >= 78, out["model_size_u"] + 0.05, out["model_size_u"])
    ).round(2)

    out["matchup_note"] = out.apply(matchup_label, axis=1)
    out["variance_note"] = out.apply(lambda r: variance_label(r["std_dev_used"], r["market"]), axis=1)
    out["portfolio_status"] = out.apply(lambda r: portfolio_flag(r["score"], r["ev_edge_pct"], r["hit_pct"]), axis=1)

    out["realism_flag"] = np.where(
        (out["ev_edge_pct"] >= 20) | (out["hit_pct"] >= 68) | (out["edge_z"] >= 1.15),
        "Review",
        "Normal"
    )

    out = add_multi_ai_consensus(out)
    return out


def inject_ui_css():
    st.markdown(
        """
        <style>
        div.block-container {
            padding-top: 1.0rem;
            padding-bottom: 2rem;
        }
        .metric-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 10px;
            margin: 6px 0 18px 0;
        }
        .metric-grid.three {
            grid-template-columns: repeat(3, minmax(0, 1fr));
        }
        .metric-card {
            border: 1px solid rgba(128,128,128,0.20);
            border-radius: 16px;
            padding: 12px 12px 10px 12px;
            background: rgba(250,250,250,0.72);
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        }
        .metric-label {
            font-size: 0.76rem;
            opacity: 0.72;
            margin-bottom: 6px;
        }
        .metric-value {
            font-size: 1.35rem;
            font-weight: 700;
            line-height: 1.05;
        }
        .consensus-card {
            border: 1px solid rgba(128,128,128,0.22);
            border-radius: 16px;
            padding: 14px;
            margin-bottom: 12px;
            background: rgba(250,250,250,0.78);
        }
        .consensus-title {
            font-size: 1rem;
            font-weight: 700;
            margin-bottom: 5px;
        }
        .mini-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0,1fr));
            gap: 8px;
            margin-top: 8px;
        }
        .mini-stat {
            border-radius: 10px;
            padding: 7px 8px;
            background: rgba(0,0,0,0.035);
            font-size: 0.74rem;
            line-height: 1.25;
        }
        .pill {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 700;
            margin-right: 6px;
            margin-bottom: 6px;
            border: 1px solid rgba(128,128,128,0.25);
            background: rgba(0,0,0,0.03);
        }
        @media (max-width: 768px) {
            .metric-grid, .metric-grid.three, .mini-grid {
                grid-template-columns: repeat(2, minmax(0,1fr));
            }
            .metric-value {
                font-size: 1.15rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_metric_boxes(items, three=False):
    cols = 3 if three else 4
    grid = st.columns(cols)
    for i, (label, value) in enumerate(items):
        with grid[i % cols]:
            st.markdown(
                f"""
                <div style="
                    border:1px solid rgba(128,128,128,0.22);
                    border-radius:14px;
                    padding:12px;
                    background:rgba(250,250,250,0.75);
                ">
                    <div style="font-size:12px; opacity:0.72;">{label}</div>
                    <div style="font-size:22px; font-weight:700; line-height:1.05;">{value}</div>
                </div>
                """,
                unsafe_allow_html=True
            )


def render_consensus_cards(df: pd.DataFrame, top_n: int = 6):
    if df.empty:
        st.info("No plays match the current filters.")
        return

    show = df.sort_values(["consensus_score", "model_agreement_pct"], ascending=False).head(top_n).reset_index(drop=True)
    for _, row in show.iterrows():
        html = f"""
        <div class="consensus-card">
            <div class="consensus-title">#{int(row['consensus_rank'])} {row['player']} — {row['bet_side']} {row['line']} {str(row['market']).title()}</div>
            <div style="font-size:0.78rem; opacity:0.8; margin-bottom:6px;">{row['matchup']} • {row['book']}</div>
            <div>
                <span class="pill">{row['consensus_tier']}</span>
                <span class="pill">{row['consensus_action']}</span>
                <span class="pill">{int(row['model_agreement_pct'])}% Agreement</span>
            </div>
            <div class="mini-grid">
                <div class="mini-stat"><b>Projection AI</b><br>{row['projection_model']:.1f}</div>
                <div class="mini-stat"><b>Script AI</b><br>{row['script_model']:.1f}</div>
                <div class="mini-stat"><b>Risk AI</b><br>{row['risk_model']:.1f}</div>
                <div class="mini-stat"><b>Market AI</b><br>{row['market_model']:.1f}</div>
                <div class="mini-stat"><b>Portfolio AI</b><br>{row['portfolio_model']:.1f}</div>
                <div class="mini-stat"><b>Consensus</b><br>{row['consensus_score']:.1f}</div>
            </div>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)


def sample_data() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "player": "Stephen Curry", "team": "GSW", "opponent": "LAL", "matchup": "Warriors vs Lakers",
            "market": "points", "bet_side": "Over", "line": 27.0, "projection": 32.2, "odds": -115,
            "book": "DraftKings", "starter": True, "minutes": 35, "std_dev": 8.0, "game_total": 238.5, "spread": -2.5,
        },
        {
            "player": "LeBron James", "team": "LAL", "opponent": "GSW", "matchup": "Lakers vs Warriors",
            "market": "pra", "bet_side": "Over", "line": 38.0, "projection": 43.8, "odds": -115,
            "book": "DraftKings", "starter": True, "minutes": 36, "std_dev": 8.8, "game_total": 238.5, "spread": 2.5,
        },
        {
            "player": "Anthony Davis", "team": "LAL", "opponent": "GSW", "matchup": "Lakers vs Warriors",
            "market": "rebounds", "bet_side": "Over", "line": 11.5, "projection": 13.1, "odds": -105,
            "book": "FanDuel", "starter": True, "minutes": 35, "std_dev": 3.5, "game_total": 238.5, "spread": 2.5,
        },
        {
            "player": "Austin Reaves", "team": "LAL", "opponent": "GSW", "matchup": "Lakers vs Warriors",
            "market": "assists", "bet_side": "Under", "line": 6.5, "projection": 5.2, "odds": -102,
            "book": "BetMGM", "starter": True, "minutes": 34, "std_dev": 2.8, "game_total": 238.5, "spread": 2.5,
        },
        {
            "player": "Jordan Poole", "team": "WAS", "opponent": "BKN", "matchup": "Wizards vs Nets",
            "market": "points", "bet_side": "Over", "line": 21.5, "projection": 24.4, "odds": +102,
            "book": "Caesars", "starter": True, "minutes": 33, "std_dev": 7.8, "game_total": 229.0, "spread": 5.0,
        },
        {
            "player": "Bench Example", "team": "MIA", "opponent": "BOS", "matchup": "Heat vs Celtics",
            "market": "points", "bet_side": "Over", "line": 10.5, "projection": 13.2, "odds": -110,
            "book": "DraftKings", "starter": False, "minutes": 24, "std_dev": 5.5, "game_total": 220.5, "spread": 9.5,
        },
    ])


@st.cache_data(show_spinner=False)
def load_csv(file) -> pd.DataFrame:
    return pd.read_csv(file)


# -----------------------------
# App
# -----------------------------
inject_ui_css()

st.title("🏀 Sports AI Betting Dashboard")
st.caption("V7 Step 1: Multi-AI Consensus Engine added before the parlay optimizer layer.")

with st.sidebar:
    st.header("Data")
    uploaded = st.file_uploader("Upload your bets CSV", type=["csv"])
    use_sample = st.toggle("Use sample data", value=uploaded is None)

if uploaded is not None:
    try:
        raw_df = load_csv(uploaded)
        source_label = f"Uploaded file: {uploaded.name}"
    except Exception as e:
        st.error(f"Could not read file: {e}")
        st.stop()
elif use_sample:
    raw_df = sample_data()
    source_label = "Built-in sample data"
else:
    st.warning("Upload a CSV or turn on sample data.")
    st.stop()

df = ensure_columns(raw_df)
model_df = compute_edges(df)

st.success(f"Loaded source: {source_label}")

c1, c2, c3, c4 = st.columns(4)
with c1:
    books = sorted([b for b in model_df["book"].dropna().unique().tolist() if b != ""])
    selected_books = st.multiselect("Sportsbooks", books, default=books)
with c2:
    markets = sorted([m for m in model_df["market"].dropna().unique().tolist() if m != ""])
    selected_markets = st.multiselect("Markets", markets, default=markets)
with c3:
    only_starters_global = st.toggle("Starters only (global)", value=False)
with c4:
    min_consensus = st.slider("Minimum consensus", 0, 95, 55)

filtered = model_df.copy()
if selected_books:
    filtered = filtered[filtered["book"].isin(selected_books)]
if selected_markets:
    filtered = filtered[filtered["market"].isin(selected_markets)]
if only_starters_global:
    filtered = filtered[filtered["starter"] == True]
filtered = filtered[filtered["consensus_score"] >= min_consensus].copy()

render_metric_boxes([
    ("Bets Loaded", f"{len(model_df)}"),
    ("Filtered Bets", f"{len(filtered)}"),
    ("Avg Consensus", f"{filtered['consensus_score'].mean():.1f}" if not filtered.empty else "N/A"),
    ("Avg Agreement", f"{filtered['model_agreement_pct'].mean():.0f}%" if not filtered.empty else "N/A"),
])

tabs = st.tabs(["🤖 Multi-AI Consensus", "🔥 Best Consensus Plays", "🎮 Model Breakdown", "🗂️ Raw Data"])

with tabs[0]:
    st.subheader("Multi-AI Consensus")
    left, right = st.columns([1, 2])

    with left:
        min_agreement = st.slider("Minimum agreement %", 0, 100, 50)
        action_filter = st.multiselect(
            "Consensus action",
            ["Bet", "Lean", "Pass"],
            default=["Bet", "Lean", "Pass"],
        )
        consensus_df = filtered[
            (filtered["model_agreement_pct"] >= min_agreement) &
            (filtered["consensus_action"].isin(action_filter))
        ].copy()

    with right:
        if consensus_df.empty:
            st.warning("No plays match filters — showing top available plays instead.")
            consensus_df = filtered.sort_values(["consensus_score"], ascending=False).head(5)
        else:
            ranked = consensus_df.sort_values(["consensus_score", "model_agreement_pct"], ascending=False)
            st.dataframe(
                ranked[[
                    "consensus_rank", "player", "matchup", "market", "bet_side", "line", "odds",
                    "projection_model", "script_model", "risk_model", "market_model", "portfolio_model",
                    "consensus_score", "model_agreement_pct", "consensus_tier", "consensus_action"
                ]],
                use_container_width=True,
                hide_index=True,
            )

    st.markdown("### Consensus Cards")
    render_consensus_cards(consensus_df if 'consensus_df' in locals() else filtered)

with tabs[1]:
    st.subheader("Best Consensus Plays")
    best = filtered.sort_values(["consensus_score", "model_agreement_pct"], ascending=False).copy()
    st.dataframe(
        best[[
            "player", "matchup", "market", "bet_side", "line", "odds", "score",
            "consensus_score", "model_agreement_pct", "consensus_tier", "consensus_action",
            "script_type", "realism_flag"
        ]],
        use_container_width=True,
        hide_index=True,
    )

with tabs[2]:
    st.subheader("Model Breakdown")
    render_metric_boxes([
        ("Avg Projection AI", f"{filtered['projection_model'].mean():.1f}" if not filtered.empty else "N/A"),
        ("Avg Script AI", f"{filtered['script_model'].mean():.1f}" if not filtered.empty else "N/A"),
        ("Avg Risk AI", f"{filtered['risk_model'].mean():.1f}" if not filtered.empty else "N/A"),
        ("Avg Market AI", f"{filtered['market_model'].mean():.1f}" if not filtered.empty else "N/A"),
    ])

    st.dataframe(
        filtered[[
            "player", "projection_model", "script_model", "risk_model", "market_model",
            "portfolio_model", "consensus_score", "model_agreement_pct", "consensus_action"
        ]].sort_values(["consensus_score"], ascending=False),
        use_container_width=True,
        hide_index=True,
    )

with tabs[3]:
    st.subheader("Model Data")
    st.dataframe(model_df, use_container_width=True, hide_index=True)

    csv = model_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download scored bets CSV",
        data=csv,
        file_name="scored_bets_v7_step1_multi_ai_consensus.csv",
        mime="text/csv",
    )

st.markdown("---")
st.caption("Next step after this: use the consensus-approved pool to build a parlay optimizer.")
