
import math
import itertools
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Sports AI Betting Dashboard V8.4 FINAL", layout="wide")

# ============================================================
# Helpers
# ============================================================
def safe_float(v, default=np.nan):
    try:
        if pd.isna(v):
            return default
        return float(v)
    except Exception:
        return default


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def american_to_decimal(odds: float) -> float:
    odds = safe_float(odds)
    if pd.isna(odds):
        return np.nan
    return 1 + (odds / 100) if odds > 0 else 1 + (100 / abs(odds))


def american_to_implied_prob(odds: float) -> float:
    odds = safe_float(odds)
    if pd.isna(odds):
        return np.nan
    return 100 / (odds + 100) if odds > 0 else abs(odds) / (abs(odds) + 100)


def decimal_to_american(dec: float) -> float:
    dec = safe_float(dec)
    if pd.isna(dec) or dec <= 1:
        return np.nan
    if dec >= 2:
        return round((dec - 1) * 100)
    return round(-100 / (dec - 1))


def normal_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def fmt_american(v: float) -> str:
    if pd.isna(v):
        return "—"
    v = int(round(v))
    return f"+{v}" if v > 0 else str(v)


# ============================================================
# Styling
# ============================================================
st.markdown("""
<style>
.block-container {padding-top: 1rem; padding-bottom: 4rem; max-width: 1120px;}
.banner {
    border:1px solid rgba(148,163,184,.24);
    border-radius:22px;
    padding:16px;
    background: linear-gradient(135deg, #f8fafc 0%, #eff6ff 100%);
    margin-bottom: 14px;
}
.metric-box {
    border:1px solid rgba(148,163,184,.22);
    border-radius:18px;
    background: rgba(255,255,255,.98);
    padding:12px 14px;
    min-height: 86px;
    margin-bottom:10px;
}
.metric-label {font-size:.88rem; color:#6b7280; margin-bottom:6px;}
.metric-value {font-size:1.75rem; line-height:1.05; font-weight:800;}
.card {
    border:1px solid rgba(148,163,184,.22);
    border-radius:22px;
    background: linear-gradient(180deg, rgba(255,255,255,.98), rgba(248,250,252,.96));
    padding:16px;
    margin-bottom:14px;
}
.pill {
    display:inline-block;
    padding:6px 12px;
    border-radius:999px;
    font-weight:700;
    margin-right:8px;
    margin-bottom:8px;
    font-size:.92rem;
    border:1px solid rgba(148,163,184,.24);
}
.pill-green {background:#16a34a; color:white; border:none;}
.pill-yellow {background:#eab308; color:#111827; border:none;}
.pill-red {background:#dc2626; color:white; border:none;}
.pill-blue {background:#2563eb; color:white; border:none;}
.pill-gray {background:#f8fafc; color:#111827;}
.confbar-wrap {
    height: 12px;
    width: 100%;
    background: #e5e7eb;
    border-radius: 999px;
    overflow: hidden;
    margin: 10px 0 14px 0;
}
.confbar-fill {height:100%; border-radius:999px;}
.reason-box {
    border:1px solid rgba(148,163,184,.18);
    background:#fafafa;
    border-radius:16px;
    padding:12px 14px;
    margin-top:8px;
}
.small-muted {color:#6b7280; font-size:.95rem;}
</style>
""", unsafe_allow_html=True)

# ============================================================
# Data prep
# ============================================================
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
        "opening_odds": "open_odds",
        "current_odds": "odds",
        "opponent_dvp": "defense_rank",
        "dvp_rank": "defense_rank",
        "last_5_avg": "last5_avg",
        "last5": "last5_avg",
        "minutes_vol": "minutes_volatility",
        "book_fd": "odds_fanduel",
        "book_dk": "odds_draftkings",
        "book_mgm": "odds_betmgm",
        "book_caesars": "odds_caesars",
    }
    for old, new in aliases.items():
        if old in df.columns and new not in df.columns:
            df[new] = df[old]

    defaults = {
        "player": "", "team": "", "opponent": "", "matchup": "", "market": "",
        "bet_side": "", "line": np.nan, "projection": np.nan, "odds": np.nan,
        "book": "", "starter": False, "minutes": np.nan, "std_dev": np.nan,
        "spread": np.nan, "pace": np.nan, "usage": np.nan, "open_odds": np.nan,
        "best_odds": np.nan, "last5_avg": np.nan, "defense_rank": np.nan,
        "minutes_volatility": np.nan, "odds_fanduel": np.nan, "odds_draftkings": np.nan,
        "odds_betmgm": np.nan, "odds_caesars": np.nan
    }
    for col, val in defaults.items():
        if col not in df.columns:
            df[col] = val

    for c in ["player", "team", "opponent", "matchup", "market", "bet_side", "book"]:
        df[c] = df[c].fillna("").astype(str).str.strip()

    numeric_cols = [
        "line", "projection", "odds", "minutes", "std_dev", "spread", "pace", "usage",
        "open_odds", "best_odds", "last5_avg", "defense_rank", "minutes_volatility",
        "odds_fanduel", "odds_draftkings", "odds_betmgm", "odds_caesars"
    ]
    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df["starter"] = df["starter"].fillna(False).astype(bool)

    if (df["matchup"] == "").any():
        auto_match = df["team"].fillna("") + np.where(
            df["opponent"].fillna("") != "",
            " vs " + df["opponent"].fillna(""),
            ""
        )
        df.loc[df["matchup"] == "", "matchup"] = auto_match[df["matchup"] == ""]
    return df


def infer_market_std(row: pd.Series) -> float:
    supplied = row.get("std_dev")
    if pd.notna(supplied) and supplied > 0:
        return float(supplied)
    market = str(row.get("market", "")).lower()
    defaults = {
        "points": 8.5, "rebounds": 4.0, "assists": 3.6, "pra": 9.0,
        "pr": 8.0, "pa": 8.0, "threes": 2.4, "3pm": 2.4, "steals": 1.3,
        "blocks": 1.4, "turnovers": 1.9
    }
    for k, v in defaults.items():
        if k in market:
            return v
    return 7.5


def infer_bet_side(row: pd.Series) -> str:
    side = str(row.get("bet_side", "")).title()
    if side in {"Over", "Under"}:
        return side
    p, l = row.get("projection"), row.get("line")
    if pd.isna(p) or pd.isna(l):
        return "Over"
    return "Over" if p >= l else "Under"


def calculate_hit_probability(row: pd.Series) -> float:
    p, l = row.get("projection"), row.get("line")
    if pd.isna(p) or pd.isna(l):
        return np.nan
    std = infer_market_std(row)
    z = (p - l) / std if std > 0 else 0.0
    p_over = normal_cdf(z)
    return clamp01(1 - p_over if infer_bet_side(row) == "Under" else p_over)


def variance_note(row: pd.Series) -> str:
    market = str(row.get("market", "")).lower()
    std = infer_market_std(row)
    if "three" in market or "3pm" in market:
        return "High variance"
    if std >= 8.5:
        return "High-upside profile"
    if std <= 2.8:
        return "Lower variance"
    return "Neutral variance"


def script_note(row: pd.Series) -> Tuple[str, int]:
    pace = row.get("pace")
    usage = row.get("usage")
    spread = abs(row.get("spread")) if pd.notna(row.get("spread")) else 0
    score = 60
    label = "Neutral environment"

    if pd.notna(pace) and pace >= 101:
        score += 10
    elif pd.notna(pace) and pace <= 96:
        score -= 8

    if pd.notna(usage) and usage >= 29:
        score += 10
    elif pd.notna(usage) and usage <= 18:
        score -= 6

    if spread <= 5:
        score += 8
    elif spread >= 10:
        score -= 8

    market = str(row.get("market", "")).lower()
    if "points" in market or "pra" in market:
        score += 5

    score = int(max(35, min(92, score)))
    if score >= 80:
        label = "Track meet"
    elif score >= 68:
        label = "Playable pace"
    elif score <= 48:
        label = "Slow spot"
    return label, score


def grade_tier(score: float) -> Tuple[str, str]:
    if score >= 80:
        return "A+ ELITE", "pill-green"
    if score >= 72:
        return "A STRONG", "pill-green"
    if score >= 65:
        return "B+ VALUE", "pill-yellow"
    if score >= 60:
        return "B LEAN", "pill-yellow"
    return "C PASS", "pill-red"


def action_from_score(score: float, edge: float) -> str:
    if edge <= 0:
        return "Pass"
    if score >= 78 and edge >= 0.035:
        return "Bet"
    if score >= 64 and edge >= 0.015:
        return "Lean"
    return "Pass"


def movement_label(delta_implied_pct: float) -> str:
    if pd.isna(delta_implied_pct):
        return "No move"
    if delta_implied_pct >= 4:
        return "🔥 Strong steam"
    if delta_implied_pct >= 2:
        return "📈 Steam"
    if delta_implied_pct <= -4:
        return "🧊 Reverse move"
    if delta_implied_pct <= -2:
        return "↩️ Soft reverse"
    return "⏳ Stable"


def matchup_context(row: pd.Series) -> Tuple[str, float]:
    defense_rank = safe_float(row.get("defense_rank"), np.nan)
    last5_avg = safe_float(row.get("last5_avg"), np.nan)
    projection = safe_float(row.get("projection"), np.nan)
    minutes_volatility = safe_float(row.get("minutes_volatility"), np.nan)

    bonus = 0.0
    notes = []

    if not pd.isna(defense_rank):
        if defense_rank >= 24:
            bonus += 4.5
            notes.append("Soft opponent defense")
        elif defense_rank <= 8:
            bonus -= 4.0
            notes.append("Tough opponent defense")

    if not pd.isna(last5_avg) and not pd.isna(projection):
        diff = last5_avg - projection
        if diff >= 1.5:
            bonus += 2.5
            notes.append("Recent form above projection")
        elif diff <= -1.5:
            bonus -= 2.0
            notes.append("Recent form cooling")

    if not pd.isna(minutes_volatility):
        if minutes_volatility >= 6:
            bonus -= 2.5
            notes.append("High minutes volatility")
        elif minutes_volatility <= 2.5:
            bonus += 1.0
            notes.append("Stable minutes")

    label = " | ".join(notes) if notes else "Neutral matchup context"
    return label, bonus


def best_book_and_odds(row: pd.Series) -> Tuple[str, float]:
    books = {
        "FanDuel": safe_float(row.get("odds_fanduel"), np.nan),
        "DraftKings": safe_float(row.get("odds_draftkings"), np.nan),
        "BetMGM": safe_float(row.get("odds_betmgm"), np.nan),
        "Caesars": safe_float(row.get("odds_caesars"), np.nan),
    }
    valid = {k: v for k, v in books.items() if not pd.isna(v)}
    if not valid:
        current_book = str(row.get("book", "")) if str(row.get("book", "")).strip() else "Current Book"
        current_odds = safe_float(row.get("odds"), np.nan)
        return current_book, current_odds

    best_book = None
    best_prob = None
    best_odds = np.nan
    for bk, od in valid.items():
        ip = american_to_implied_prob(od)
        if pd.isna(ip):
            continue
        if best_prob is None or ip < best_prob:
            best_prob = ip
            best_book = bk
            best_odds = od

    if best_book is None:
        current_book = str(row.get("book", "")) if str(row.get("book", "")).strip() else "Current Book"
        current_odds = safe_float(row.get("odds"), np.nan)
        return current_book, current_odds
    return best_book, best_odds


def stale_line_flag(current_odds: float, best_odds: float) -> str:
    if pd.isna(current_odds) or pd.isna(best_odds):
        return ""
    curr_ip = american_to_implied_prob(current_odds)
    best_ip = american_to_implied_prob(best_odds)
    if pd.isna(curr_ip) or pd.isna(best_ip):
        return ""
    edge_gap = (curr_ip - best_ip) * 100
    if edge_gap >= 3:
        return "Stale line risk"
    if edge_gap <= 0.3:
        return "Current book in line"
    return "Shop books"


def ev_cap_adjustment(ev_pct: float) -> float:
    if pd.isna(ev_pct):
        return np.nan
    return min(ev_pct, 45.0)


def single_stake_units(row: pd.Series, bankroll: float, max_single_pct: float) -> Dict:
    prob = safe_float(row.get("realistic_hit_prob"), 0.0)
    dec = american_to_decimal(row.get("best_display_odds", row.get("odds")))
    if pd.isna(dec) or dec <= 1 or prob <= 0 or prob >= 1:
        return {"single_kelly_pct": 0.0, "single_bet_pct": 0.0, "single_stake_$": 0.0, "single_stake_u": 0.0}

    b = dec - 1
    q = 1 - prob
    raw_kelly = max(0.0, (b * prob - q) / b)
    grade = safe_float(row.get("consensus_score"), 0)
    mult = 0.42 if grade >= 78 else (0.30 if grade >= 68 else 0.18)
    frac = min(raw_kelly * mult, max_single_pct)
    stake_dollars = bankroll * frac
    stake_units = stake_dollars / (bankroll * 0.01) if bankroll > 0 else 0.0

    return {
        "single_kelly_pct": raw_kelly * 100,
        "single_bet_pct": frac * 100,
        "single_stake_$": stake_dollars,
        "single_stake_u": stake_units,
    }


def compute_scores(df: pd.DataFrame, bankroll: float = 1000, max_single_pct: float = 0.015) -> pd.DataFrame:
    out = df.copy()
    out["bet_side"] = out.apply(infer_bet_side, axis=1)
    out["hit_prob"] = out.apply(calculate_hit_probability, axis=1)
    out["hit_pct"] = (out["hit_prob"] * 100).round(1)

    bests = out.apply(best_book_and_odds, axis=1)
    out["best_book"] = [x[0] for x in bests]
    out["best_display_odds"] = [x[1] for x in bests]

    out["implied_prob"] = out["best_display_odds"].apply(american_to_implied_prob)
    out["true_edge"] = (out["hit_prob"] - out["implied_prob"]).round(4)

    dec = out["best_display_odds"].apply(american_to_decimal)
    out["raw_ev"] = (out["hit_prob"] * (dec - 1)) - (1 - out["hit_prob"])
    out["raw_ev_pct"] = (out["raw_ev"] * 100).round(2)

    out["realistic_hit_prob"] = (
        out["hit_prob"]
        - np.where(out["true_edge"] > 0.08, 0.03, 0.0)
        - np.where(out["true_edge"] > 0.12, 0.03, 0.0)
        - np.where(out["starter"], 0.0, 0.02)
    ).clip(lower=0.01, upper=0.95)

    open_ip = out["open_odds"].apply(american_to_implied_prob)
    curr_ip = out["odds"].apply(american_to_implied_prob)
    out["line_move_pct"] = ((curr_ip - open_ip) * 100).round(2)
    out["movement_note"] = out["line_move_pct"].apply(movement_label)
    out["stale_line_note"] = [stale_line_flag(o, b) for o, b in zip(out["odds"], out["best_display_odds"])]

    matchup_vals = out.apply(matchup_context, axis=1)
    out["matchup_context"] = [x[0] for x in matchup_vals]
    out["matchup_bonus"] = [x[1] for x in matchup_vals]

    out["realistic_hit_prob"] = (
        out["realistic_hit_prob"]
        + np.where(out["line_move_pct"] >= 2, 0.01, 0.0)
        - np.where(out["line_move_pct"] <= -2, 0.01, 0.0)
        + (out["matchup_bonus"] / 100.0)
    ).clip(lower=0.01, upper=0.95)

    out["realistic_ev"] = (out["realistic_hit_prob"] * (dec - 1)) - (1 - out["realistic_hit_prob"])
    out["realistic_ev_pct"] = (out["realistic_ev"] * 100).round(2)
    out["realistic_ev_pct"] = out["realistic_ev_pct"].apply(ev_cap_adjustment)

    script_vals = out.apply(script_note, axis=1)
    out["script_type"] = [x[0] for x in script_vals]
    out["script_score"] = [x[1] for x in script_vals]
    out["variance_note"] = out.apply(variance_note, axis=1)

    out["consensus_score"] = (
        out["hit_pct"] * 0.23
        + out["true_edge"].clip(lower=-0.05, upper=0.15) * 180
        + out["realistic_ev_pct"].clip(lower=-10, upper=22) * 0.82
        + np.where(out["starter"], 4, -8)
        + np.where(out["minutes"].fillna(0) >= 33, 5, np.where(out["minutes"].fillna(0) >= 28, 2, -5))
        + out["script_score"] * 0.14
        + out["matchup_bonus"]
        + np.where(out["line_move_pct"] >= 2, 2.0, 0.0)
        - np.where(out["line_move_pct"] <= -2, 2.0, 0.0)
        - np.where(abs(out["spread"].fillna(0)) >= 10, 4, 0)
    ).clip(0, 100).round(1)

    out["model_agreement_pct"] = np.select(
        [out["consensus_score"] >= 80, out["consensus_score"] >= 72, out["consensus_score"] >= 64],
        [80, 60, 40],
        default=20
    )
    out["consensus_action"] = [action_from_score(s, e) for s, e in zip(out["consensus_score"], out["true_edge"])]
    tiers = [grade_tier(s) for s in out["consensus_score"]]
    out["confidence_grade"] = [t[0] for t in tiers]
    out["confidence_class"] = [t[1] for t in tiers]

    stake_rows = [
        single_stake_units(row, bankroll=bankroll, max_single_pct=max_single_pct)
        for _, row in out.iterrows()
    ]
    out = pd.concat([out.reset_index(drop=True), pd.DataFrame(stake_rows)], axis=1)

    out["rank_score"] = (
        out["consensus_score"] * 0.46
        + out["realistic_ev_pct"].clip(lower=-10, upper=22) * 0.95
        + (out["true_edge"] * 100).clip(lower=-5, upper=18) * 1.05
        + (out["realistic_hit_prob"] * 100) * 0.16
        + np.where(out["line_move_pct"] >= 2, 1.8, 0.0)
    ).round(2)

    return out


# ============================================================
# Portfolio logic
# ============================================================
def approved_pool(df: pd.DataFrame) -> pd.DataFrame:
    primary = df[
        (
            (df["consensus_action"] == "Bet") |
            ((df["consensus_action"] == "Lean") & (df["model_agreement_pct"] >= 60))
        )
        & (df["true_edge"] >= 0.02)
        & (df["realistic_ev_pct"] >= 2.0)
    ].copy()

    if len(primary) < 2:
        fallback = df[
            (df["consensus_action"].isin(["Bet", "Lean"]))
            & (df["true_edge"] >= 0.015)
            & (df["consensus_score"] >= 62)
        ].copy()
        fallback["fallback_flag"] = True
        return fallback

    primary["fallback_flag"] = False
    return primary


def apply_game_exposure_limit(df: pd.DataFrame, max_per_game: int = 2) -> pd.DataFrame:
    if df.empty:
        return df
    counts = {}
    rows = []
    for _, row in df.sort_values(["rank_score", "realistic_ev_pct"], ascending=False).iterrows():
        matchup = str(row.get("matchup", ""))
        counts.setdefault(matchup, 0)
        if counts[matchup] < max_per_game:
            rows.append(row)
            counts[matchup] += 1
    return pd.DataFrame(rows).reset_index(drop=True)


def unique_top_plays(df: pd.DataFrame) -> Dict[str, pd.Series]:
    if df.empty:
        return {"best": pd.Series(dtype=object), "safe": pd.Series(dtype=object), "edge": pd.Series(dtype=object)}
    best = df.sort_values(["rank_score", "realistic_ev_pct"], ascending=False).iloc[0]
    safe = df.sort_values(["realistic_hit_prob", "consensus_score"], ascending=False).iloc[0]
    edge = df.sort_values(["true_edge", "realistic_ev_pct"], ascending=False).iloc[0]
    return {"best": best, "safe": safe, "edge": edge}


def same_game(a: pd.Series, b: pd.Series) -> bool:
    a_match = str(a.get("matchup", ""))
    b_match = str(b.get("matchup", ""))
    if a_match == b_match:
        return True
    a_team, a_opp = str(a.get("team", "")), str(a.get("opponent", ""))
    b_team, b_opp = str(b.get("team", "")), str(b.get("opponent", ""))
    return (a_team == b_opp and a_opp == b_team and a_team != "" and a_opp != "")


def same_team(a: pd.Series, b: pd.Series) -> bool:
    return str(a.get("team", "")) == str(b.get("team", ""))


def pair_corr_penalty(a: pd.Series, b: pd.Series) -> float:
    pen = 0.0
    if not same_game(a, b):
        return 0.0
    market_a = str(a.get("market", "")).lower()
    market_b = str(b.get("market", "")).lower()
    side_a = str(a.get("bet_side", "")).lower()
    side_b = str(b.get("bet_side", "")).lower()

    pen += 0.12
    if same_team(a, b):
        pen += 0.08
    if side_a == "over" and side_b == "over":
        if any(k in market_a for k in ["points", "pra", "assists"]) and any(k in market_b for k in ["points", "pra", "assists"]):
            pen += 0.08
        elif ("points" in market_a and "rebounds" in market_b) or ("rebounds" in market_a and "points" in market_b):
            pen += 0.04
    if side_a != side_b and same_team(a, b):
        pen -= 0.03
    return max(0.0, pen)


def combo_corr_penalty(rows: List[pd.Series]) -> float:
    total = 0.0
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            total += pair_corr_penalty(rows[i], rows[j])
    return total


def build_best_parlay(df: pd.DataFrame, leg_size: int = 2) -> Dict:
    if len(df) < leg_size:
        return {}
    top_rows = [r[1] for r in df.head(min(8, len(df))).iterrows()]
    best = None
    for combo in itertools.combinations(top_rows, leg_size):
        decs = [american_to_decimal(r["best_display_odds"]) for r in combo]
        probs = [r["realistic_hit_prob"] for r in combo]
        if any(pd.isna(x) for x in decs) or any(pd.isna(x) for x in probs):
            continue
        combined_dec = float(np.prod(decs))
        corr_pen = combo_corr_penalty(list(combo))
        hit_prob = clamp01(float(np.prod(probs)) * (1 - corr_pen))
        ev = hit_prob * (combined_dec - 1) - (1 - hit_prob)
        score = (min(ev * 100, 55) + hit_prob * 25 - corr_pen * 20)
        candidate = {
            "legs": list(combo),
            "odds": decimal_to_american(combined_dec),
            "hit_prob": hit_prob,
            "ev_pct": min(ev * 100, 60),
            "corr_pen": corr_pen,
            "score": score
        }
        if best is None or candidate["score"] > best["score"]:
            best = candidate
    return best or {}


# ============================================================
# Render helpers
# ============================================================
def render_metric_box(label: str, value: str):
    st.markdown(
        f"""<div class="metric-box"><div class="metric-label">{label}</div><div class="metric-value">{value}</div></div>""",
        unsafe_allow_html=True,
    )


def why_this_play(row: pd.Series) -> List[str]:
    projection = safe_float(row.get("projection"), np.nan)
    line = safe_float(row.get("line"), np.nan)
    proj_edge = projection - line if not pd.isna(projection) and not pd.isna(line) else np.nan
    model_agreement = int(safe_float(row.get("model_agreement_pct"), 0))
    true_edge = safe_float(row.get("true_edge"), 0) * 100
    script_type = row.get("script_type", "Neutral")
    script_score = int(safe_float(row.get("script_score"), 0))
    variance = row.get("variance_note", "Neutral")
    stake_u = safe_float(row.get("single_stake_u"), 0)
    matchup = row.get("matchup_context", "Neutral matchup context")
    movement = row.get("movement_note", "Stable")
    stale = row.get("stale_line_note", "")
    best_book = row.get("best_book", "")
    best_odds = fmt_american(row.get("best_display_odds", np.nan))

    notes = [
        f"Projection Edge: {proj_edge:+.1f} vs line" if not pd.isna(proj_edge) else "Projection Edge: N/A",
        f"Model Agreement: {model_agreement}% aligned",
        f"Market Inefficiency: true edge {true_edge:.1f}%",
        f"Game Script: {script_type} ({script_score})",
        f"Matchup Context: {matchup}",
        f"Line Movement: {movement}",
        f"Best Line Shop: {best_book} {best_odds}" if str(best_book).strip() else "Best Line Shop: Not available",
        f"Book Quality: {stale if stale else 'Current book acceptable'}",
        f"Risk: {variance}",
        f"Recommended stake: {stake_u:.2f}u",
    ]
    return notes


def render_best_bet(row: pd.Series):
    st.markdown("## 🔥 Best Bet")
    st.markdown(f"### {row['player']} — {row['bet_side']} {row['line']} {row['market']}")
    st.markdown(
        f"**Current Odds:** {fmt_american(row['odds'])} | "
        f"**Best Odds:** {fmt_american(row['best_display_odds'])} ({row['best_book']}) | "
        f"**EV:** {row['realistic_ev_pct']:.1f}%"
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        render_metric_box("Hit %", f"{row['realistic_hit_prob']*100:.0f}%")
    with c2:
        render_metric_box("Edge", f"{row['true_edge']*100:.1f}%")
    with c3:
        render_metric_box("Stake", f"{row['single_stake_u']:.2f}u")

    st.progress(float(row["realistic_hit_prob"]))

    with st.expander("📊 Why This Play", expanded=False):
        for r in why_this_play(row):
            st.write(f"• {r}")


def render_compact_play(row: pd.Series):
    st.markdown(f"**{row['player']} — {row['bet_side']} {row['line']} {row['market']}**")
    st.caption(
        f"Best {fmt_american(row['best_display_odds'])} ({row['best_book']}) | "
        f"EV {row['realistic_ev_pct']:.1f}% | Edge {row['true_edge']*100:.1f}% | "
        f"Stake {row['single_stake_u']:.2f}u | {row['movement_note']}"
    )
    st.divider()


# ============================================================
# Sample data
# ============================================================
def sample_data() -> pd.DataFrame:
    return pd.DataFrame([
        {"player": "Stephen Curry", "team": "GSW", "opponent": "LAL", "matchup": "Warriors vs Lakers", "market": "points", "bet_side": "Over", "line": 27.0, "projection": 32.2, "odds": -115, "open_odds": -102, "book": "DraftKings", "starter": True, "minutes": 35, "spread": -2.5, "pace": 102.4, "usage": 31.0, "last5_avg": 33.1, "defense_rank": 24, "minutes_volatility": 2.1, "odds_fanduel": -112, "odds_draftkings": -115, "odds_betmgm": -108, "odds_caesars": -110},
        {"player": "LeBron James", "team": "LAL", "opponent": "GSW", "matchup": "Lakers vs Warriors", "market": "pra", "bet_side": "Over", "line": 38.0, "projection": 43.8, "odds": -115, "open_odds": -105, "book": "DraftKings", "starter": True, "minutes": 36, "spread": 2.5, "pace": 101.9, "usage": 30.5, "last5_avg": 45.2, "defense_rank": 23, "minutes_volatility": 2.2, "odds_fanduel": -112, "odds_draftkings": -115, "odds_betmgm": -110, "odds_caesars": -111},
        {"player": "Anthony Davis", "team": "LAL", "opponent": "GSW", "matchup": "Lakers vs Warriors", "market": "rebounds", "bet_side": "Over", "line": 11.5, "projection": 13.1, "odds": -105, "open_odds": -104, "book": "FanDuel", "starter": True, "minutes": 35, "spread": 2.5, "pace": 101.9, "usage": 27.0, "last5_avg": 12.8, "defense_rank": 19, "minutes_volatility": 2.6, "odds_fanduel": -105, "odds_draftkings": -102, "odds_betmgm": 100, "odds_caesars": -101},
        {"player": "Austin Reaves", "team": "LAL", "opponent": "GSW", "matchup": "Lakers vs Warriors", "market": "assists", "bet_side": "Under", "line": 6.5, "projection": 5.2, "odds": -102, "open_odds": -110, "book": "BetMGM", "starter": True, "minutes": 34, "spread": 2.5, "pace": 101.9, "usage": 21.0, "last5_avg": 5.7, "defense_rank": 11, "minutes_volatility": 3.4, "odds_fanduel": -108, "odds_draftkings": -105, "odds_betmgm": -102, "odds_caesars": -104},
        {"player": "Jordan Poole", "team": "WAS", "opponent": "BKN", "matchup": "Wizards vs Nets", "market": "points", "bet_side": "Over", "line": 21.5, "projection": 24.4, "odds": 102, "open_odds": 108, "book": "Caesars", "starter": True, "minutes": 33, "spread": 5.0, "pace": 99.6, "usage": 30.0, "last5_avg": 25.8, "defense_rank": 25, "minutes_volatility": 4.2, "odds_fanduel": 100, "odds_draftkings": 101, "odds_betmgm": 103, "odds_caesars": 102},
        {"player": "Jalen Brunson", "team": "NYK", "opponent": "MIA", "matchup": "Knicks vs Heat", "market": "points", "bet_side": "Over", "line": 26.5, "projection": 29.7, "odds": -110, "open_odds": -101, "book": "FanDuel", "starter": True, "minutes": 36, "spread": -3.0, "pace": 98.7, "usage": 30.6, "last5_avg": 30.9, "defense_rank": 9, "minutes_volatility": 1.8, "odds_fanduel": -110, "odds_draftkings": -106, "odds_betmgm": -104, "odds_caesars": -108},
        {"player": "Jimmy Butler", "team": "MIA", "opponent": "NYK", "matchup": "Heat vs Knicks", "market": "assists", "bet_side": "Over", "line": 5.5, "projection": 6.7, "odds": 100, "open_odds": -105, "book": "DraftKings", "starter": True, "minutes": 35, "spread": 3.0, "pace": 98.7, "usage": 25.1, "last5_avg": 6.1, "defense_rank": 20, "minutes_volatility": 2.8, "odds_fanduel": 100, "odds_draftkings": 100, "odds_betmgm": 102, "odds_caesars": 101},
        {"player": "Bench Example", "team": "MIA", "opponent": "BOS", "matchup": "Heat vs Celtics", "market": "points", "bet_side": "Over", "line": 10.5, "projection": 13.2, "odds": -110, "open_odds": -112, "book": "DraftKings", "starter": False, "minutes": 24, "spread": 9.5, "pace": 95.8, "usage": 18.0, "last5_avg": 11.9, "defense_rank": 5, "minutes_volatility": 7.2, "odds_fanduel": -108, "odds_draftkings": -110, "odds_betmgm": -106, "odds_caesars": -109},
    ])


@st.cache_data(show_spinner=False)
def load_csv(file) -> pd.DataFrame:
    return pd.read_csv(file)


# ============================================================
# App
# ============================================================
st.title("🏀 Sports AI Betting Dashboard V8.4")
st.caption("FINAL: sharp mode, line shopping, market intelligence, exposure controls, and mobile-first layout.")

with st.sidebar:
    st.markdown("### Data")
    uploaded = st.file_uploader("Upload CSV", type=["csv"])
    use_sample = st.toggle("Use sample data", value=uploaded is None)

    st.markdown("### Bankroll")
    bankroll = st.number_input("Bankroll ($)", min_value=100, max_value=100000, value=1000, step=50)
    max_single_pct = st.slider("Max bankroll % per single", 0.25, 3.0, 1.25, 0.25) / 100.0

    st.markdown("### Engine")
    min_score = st.slider("Min approval score", 55, 90, 64)
    min_edge = st.slider("Min true edge %", 0.0, 15.0, 2.0, 0.5)
    min_ev = st.slider("Min EV %", 0.0, 25.0, 2.0, 0.5)
    sharp_mode = st.toggle("Sharp Mode", value=True)
    max_per_game = st.slider("Max plays per game", 1, 3, 2)

if uploaded and not use_sample:
    base_df = ensure_columns(load_csv(uploaded))
else:
    base_df = ensure_columns(sample_data())

scored = compute_scores(base_df, bankroll=float(bankroll), max_single_pct=float(max_single_pct))

with st.expander("⚙️ Filters", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        starters_only = st.toggle("Starters only", value=True)
    with c2:
        min_minutes = st.slider("Min minutes", 0, 40, 0)

    odds_preset = st.selectbox("Odds Range", ["All", "-300 to +200", "-200 to +150", "Plus Money Only"])

    c3, c4 = st.columns(2)
    with c3:
        market_options = sorted([x for x in scored["market"].dropna().astype(str).unique().tolist() if x.strip()])
        selected_markets = st.multiselect("Markets", market_options, default=[])
    with c4:
        side_filter = st.selectbox("Bet Side", ["All", "Over", "Under"])

    c5, c6 = st.columns(2)
    with c5:
        market_intel_filter = st.selectbox("Movement", ["All", "Steam only", "Reverse only", "Stable only"])
    with c6:
        stale_filter = st.selectbox("Book Quality", ["All", "Current book in line", "Shop books", "Stale line risk"])

filtered = scored.copy()

if starters_only:
    filtered = filtered[filtered["starter"] == True]
filtered = filtered[filtered["minutes"].fillna(0) >= min_minutes]

if odds_preset == "-300 to +200":
    filtered = filtered[filtered["best_display_odds"].between(-300, 200)]
elif odds_preset == "-200 to +150":
    filtered = filtered[filtered["best_display_odds"].between(-200, 150)]
elif odds_preset == "Plus Money Only":
    filtered = filtered[filtered["best_display_odds"] > 0]

if selected_markets:
    filtered = filtered[filtered["market"].isin(selected_markets)]
if side_filter != "All":
    filtered = filtered[filtered["bet_side"] == side_filter]

if market_intel_filter == "Steam only":
    filtered = filtered[filtered["movement_note"].astype(str).str.contains("Steam", case=False, na=False)]
elif market_intel_filter == "Reverse only":
    filtered = filtered[filtered["movement_note"].astype(str).str.contains("Reverse", case=False, na=False)]
elif market_intel_filter == "Stable only":
    filtered = filtered[filtered["movement_note"].astype(str).str.contains("Stable", case=False, na=False)]

if stale_filter != "All":
    filtered = filtered[filtered["stale_line_note"] == stale_filter]

pool = approved_pool(filtered)
pool = pool[
    (pool["consensus_score"] >= min_score)
    & ((pool["true_edge"] * 100) >= min_edge)
    & (pool["realistic_ev_pct"] >= min_ev)
].copy()

pool = apply_game_exposure_limit(pool, max_per_game=max_per_game)

if sharp_mode:
    pool = pool[
        (pool["confidence_grade"].isin(["A+ ELITE", "A STRONG"]))
        & (pool["consensus_action"] == "Bet")
    ].copy()
    pool = pool.sort_values(["rank_score", "realistic_ev_pct"], ascending=False).head(3)

if pool.empty:
    st.warning("No plays qualify under the current V8.4 FINAL filters.")
    st.stop()

pool = pool.sort_values(["rank_score", "realistic_ev_pct", "true_edge"], ascending=False).reset_index(drop=True)
tops = unique_top_plays(pool)
best_play = tops["best"]
safe_play = tops["safe"]
edge_play = tops["edge"]
best_parlay = build_best_parlay(pool, leg_size=2)

st.markdown(
    f"""
    <div class="banner">
        <div><b>Approved Plays:</b> {len(pool)}</div>
        <div><b>Best Play:</b> {best_play['player']} {best_play['bet_side']} {best_play['line']} {best_play['market']}</div>
        <div><b>Safest Play:</b> {safe_play['player']} ({safe_play['realistic_hit_prob']*100:.1f}%)</div>
        <div><b>Highest Edge:</b> {edge_play['player']} ({edge_play['true_edge']*100:.1f}%)</div>
        <div><b>Line Shop:</b> {best_play['best_book']} {fmt_american(best_play['best_display_odds'])} • {best_play['stale_line_note']}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

render_best_bet(best_play)

st.markdown("## 📋 Other Plays")
for _, row in pool.iloc[1:4].iterrows():
    render_compact_play(row)

st.markdown("## 💰 Bankroll")
c1, c2, c3 = st.columns(3)
with c1:
    render_metric_box("Top Stake", f"{best_play['single_stake_u']:.2f}u")
with c2:
    parlay_units = 0.75 if not best_parlay else min(1.00, max(0.25, best_parlay["ev_pct"] / 20))
    render_metric_box("Parlay Stake", f"{parlay_units:.2f}u")
with c3:
    roi_est = (best_play["realistic_ev_pct"] * 0.55) + ((best_parlay["ev_pct"] if best_parlay else 0) * 0.45)
    render_metric_box("ROI", f"{min(roi_est, 42.0):.1f}%")

with st.expander("🧠 Engine Details", expanded=False):
    engine_view = pool[[
        "player", "market", "bet_side", "line", "projection", "odds", "best_display_odds",
        "book", "best_book", "realistic_hit_prob", "true_edge", "realistic_ev_pct",
        "consensus_score", "model_agreement_pct", "single_stake_u", "movement_note",
        "stale_line_note", "matchup_context", "script_type", "variance_note"
    ]].copy()
    engine_view["odds"] = engine_view["odds"].apply(fmt_american)
    engine_view["best_display_odds"] = engine_view["best_display_odds"].apply(fmt_american)
    engine_view["realistic_hit_prob"] = (engine_view["realistic_hit_prob"] * 100).round(1).astype(str) + "%"
    engine_view["true_edge"] = (engine_view["true_edge"] * 100).round(1).astype(str) + "%"
    engine_view["realistic_ev_pct"] = engine_view["realistic_ev_pct"].round(1).astype(str) + "%"
    engine_view["single_stake_u"] = engine_view["single_stake_u"].round(2).astype(str) + "u"
    st.dataframe(engine_view, use_container_width=True, hide_index=True)

if best_parlay:
    legs_txt = " + ".join([f"{x['player']} {x['bet_side']} {x['line']}" for x in best_parlay["legs"]])
    st.markdown("## 🧩 Best 2-Leg Parlay")
    st.markdown(f"**Legs:** {legs_txt}")
    st.markdown(
        f"**Odds:** {fmt_american(best_parlay['odds'])} | "
        f"**Hit %:** {best_parlay['hit_prob']*100:.1f}% | "
        f"**EV:** {best_parlay['ev_pct']:.1f}% | "
        f"**Correlation Penalty:** {best_parlay['corr_pen']:.2f}"
    )

st.caption("V8.4 FINAL: sharp mode and line shopping active.")
