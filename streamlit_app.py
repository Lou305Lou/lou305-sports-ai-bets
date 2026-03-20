import math
import itertools
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Sports AI Betting Dashboard V8", layout="wide")

# ============================================================
# Helpers
# ============================================================
def american_to_decimal(odds: float) -> float:
    try:
        odds = float(odds)
    except Exception:
        return np.nan
    return 1 + (odds / 100) if odds > 0 else 1 + (100 / abs(odds))


def american_to_implied_prob(odds: float) -> float:
    try:
        odds = float(odds)
    except Exception:
        return np.nan
    return 100 / (odds + 100) if odds > 0 else abs(odds) / (abs(odds) + 100)


def decimal_to_american(dec: float) -> float:
    if dec is None or pd.isna(dec) or dec <= 1:
        return np.nan
    if dec >= 2:
        return round((dec - 1) * 100)
    return round(-100 / (dec - 1))


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def normal_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def fmt_american(v: float) -> str:
    if pd.isna(v):
        return "—"
    v = int(round(v))
    return f"+{v}" if v > 0 else str(v)


def safe_float(v, default=0.0):
    try:
        if pd.isna(v):
            return default
        return float(v)
    except Exception:
        return default


# ============================================================
# Styling
# ============================================================
st.markdown("""
<style>
.block-container {padding-top: 1.05rem; padding-bottom: 4rem; max-width: 1450px;}
.small-muted {color:#6b7280; font-size:0.96rem;}
.rule {height:1px; background:#d1d5db; margin:1.0rem 0 1.2rem 0;}

.banner {
    border:1px solid rgba(148,163,184,.28);
    border-radius:20px;
    padding:18px;
    background: linear-gradient(135deg, #f8fafc 0%, #eff6ff 100%);
    margin-bottom: 14px;
}
.banner-title {font-size:1.35rem; font-weight:800; margin-bottom:10px;}

.metric-box {
    border:1px solid rgba(128,128,128,.18);
    border-radius:18px;
    background: rgba(250,250,250,.95);
    padding:14px 16px;
    min-height: 90px;
    box-shadow: 0 6px 18px rgba(15,23,42,.04);
}
.metric-label {font-size:.92rem; color:#6b7280; margin-bottom:6px;}
.metric-value {font-size:1.85rem; line-height:1.05; font-weight:800;}

.card {
    border:1px solid rgba(128,128,128,.20);
    border-radius:22px;
    background: linear-gradient(180deg, rgba(255,255,255,.96), rgba(248,250,252,.92));
    padding:16px;
    box-shadow: 0 10px 24px rgba(15,23,42,.05);
    margin-bottom: 16px;
}
.card-title {font-size:1.50rem; font-weight:800; margin-bottom:6px;}
.card-sub {font-size:1rem; color:#4b5563; margin-bottom:10px;}

.pill {
    display:inline-block;
    padding:6px 12px;
    border-radius:999px;
    border:1px solid rgba(128,128,128,.24);
    font-weight:700;
    margin-right:8px;
    margin-bottom:8px;
    font-size:.95rem;
}
.pill-green {background:#16a34a; color:white; border:none;}
.pill-yellow {background:#eab308; color:#111827; border:none;}
.pill-red {background:#dc2626; color:white; border:none;}
.pill-gray {background:#f3f4f6; color:#111827;}
.pill-blue {background:#2563eb; color:white; border:none;}

.confbar-wrap {
    height: 11px;
    width: 100%;
    background: #e5e7eb;
    border-radius: 999px;
    overflow: hidden;
    margin: 8px 0 8px 0;
}
.confbar-fill {height:100%; border-radius:999px;}

.compact-grid {
    display:grid;
    grid-template-columns: 1fr 1fr;
    gap:10px;
    margin-top:8px;
    margin-bottom:10px;
}
.compact-cell {
    border:1px solid rgba(128,128,128,.16);
    background: rgba(243,244,246,.82);
    border-radius:16px;
    padding:11px 12px;
}
.compact-label {font-size:.85rem; color:#6b7280;}
.compact-value {font-size:1.20rem; font-weight:800; margin-top:4px;}

.reason-box {
    border:1px solid rgba(128,128,128,.16);
    background: #fafafa;
    border-radius:16px;
    padding:12px 14px;
    margin-top:10px;
    margin-bottom:6px;
}

.parlay-safe {border:2px solid #16a34a;}
.parlay-balanced {border:2px solid #d4a514;}
.parlay-aggressive {border:2px solid #dc2626;}

.bet-slip-wrap {
    border:1px solid rgba(128,128,128,.18);
    border-radius:20px;
    padding:14px;
    background: linear-gradient(135deg, #fff7ed 0%, #fffbeb 100%);
    margin-bottom: 16px;
}
.legs-list li {margin-bottom:8px;}
.table-note {font-size:.92rem; color:#6b7280; margin-top:4px;}
.section-header {font-size:1.15rem; font-weight:800; margin-bottom:8px; margin-top:4px;}
.rank-box {
    border:1px solid rgba(128,128,128,.16);
    border-radius:16px;
    padding:12px 14px;
    background:#ffffff;
    margin-bottom:10px;
}

.ev-green {color:#16a34a;}
.ev-yellow {color:#ca8a04;}
.ev-red {color:#dc2626;}

@media (max-width: 768px) {
    .card-title {font-size:1.30rem;}
    .metric-value {font-size:1.45rem;}
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# Data prep
# ============================================================
def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    aliases = {
        "player_name": "player", "name": "player",
        "sportsbook": "book", "sports_book": "book",
        "team_name": "team", "opp": "opponent",
        "market_type": "market", "bet_type": "bet_side",
        "selection": "bet_side", "odds_american": "odds",
        "american_odds": "odds", "proj": "projection",
        "projected": "projection", "prop_line": "line",
        "is_starter": "starter", "starts": "starter", "game": "matchup",
    }
    for old, new in aliases.items():
        if old in df.columns and new not in df.columns:
            df[new] = df[old]

    defaults = {
        "player": "", "team": "", "opponent": "", "matchup": "", "market": "",
        "bet_side": "", "line": np.nan, "projection": np.nan, "odds": np.nan,
        "book": "", "starter": False, "minutes": np.nan, "std_dev": np.nan,
        "spread": np.nan, "pace": np.nan, "usage": np.nan
    }
    for col, val in defaults.items():
        if col not in df.columns:
            df[col] = val

    for c in ["player", "team", "opponent", "matchup", "market", "bet_side", "book"]:
        df[c] = df[c].fillna("").astype(str).str.strip()

    for c in ["line", "projection", "odds", "minutes", "std_dev", "spread", "pace", "usage"]:
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
        "points": 8.5,
        "rebounds": 4.0,
        "assists": 3.6,
        "pra": 9.0,
        "threes": 2.4,
        "3pm": 2.4,
        "steals": 1.3,
        "blocks": 1.4,
        "turnovers": 1.9,
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
    z = (p - l) / std if std > 0 else 0
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
        return "A+ ELITE", "🟢"
    if score >= 72:
        return "A STRONG", "🟢"
    if score >= 65:
        return "B+ VALUE", "🟡"
    if score >= 60:
        return "B LEAN", "🟡"
    return "C PASS", "⚪"


def action_from_score(score: float, edge: float) -> str:
    if edge <= 0:
        return "Pass"
    if score >= 78 and edge >= 0.035:
        return "Bet"
    if score >= 64 and edge >= 0.015:
        return "Lean"
    return "Pass"


def movement_note(edge_pct: float) -> str:
    if edge_pct >= 10:
        return "🔥 Steam detected"
    if edge_pct >= 5:
        return "📈 Edge holding"
    if edge_pct >= 2:
        return "⚠️ Edge can move fast"
    return "⏳ Thin edge"


def single_stake_units(row: pd.Series, bankroll: float, max_single_pct: float) -> Dict:
    prob = safe_float(row.get("realistic_hit_prob"), 0.0)
    dec = american_to_decimal(row.get("odds"))
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
    out["implied_prob"] = out["odds"].apply(american_to_implied_prob)
    out["true_edge"] = (out["hit_prob"] - out["implied_prob"]).round(4)

    dec = out["odds"].apply(american_to_decimal)
    out["raw_ev"] = (out["hit_prob"] * (dec - 1)) - (1 - out["hit_prob"])
    out["raw_ev_pct"] = (out["raw_ev"] * 100).round(2)

    out["realistic_hit_prob"] = (
        out["hit_prob"]
        - np.where(out["true_edge"] > 0.08, 0.03, 0.0)
        - np.where(out["true_edge"] > 0.12, 0.03, 0.0)
        - np.where(out["starter"], 0.0, 0.02)
    ).clip(lower=0.01, upper=0.95)

    out["realistic_ev"] = (out["realistic_hit_prob"] * (dec - 1)) - (1 - out["realistic_hit_prob"])
    out["realistic_ev_pct"] = (out["realistic_ev"] * 100).round(2)

    script_vals = out.apply(script_note, axis=1)
    out["script_type"] = [x[0] for x in script_vals]
    out["script_score"] = [x[1] for x in script_vals]
    out["variance_note"] = out.apply(variance_note, axis=1)

    out["consensus_score"] = (
        out["hit_pct"] * 0.28
        + out["true_edge"].clip(lower=-0.05, upper=0.15) * 180
        + out["realistic_ev_pct"].clip(lower=-10, upper=20) * 0.85
        + np.where(out["starter"], 4, -8)
        + np.where(out["minutes"].fillna(0) >= 33, 5, np.where(out["minutes"].fillna(0) >= 28, 2, -5))
        + out["script_score"] * 0.16
        - np.where(abs(out["spread"].fillna(0)) >= 10, 4, 0)
    ).clip(0, 100).round(1)

    out["model_agreement_pct"] = np.select(
        [out["consensus_score"] >= 78, out["consensus_score"] >= 70, out["consensus_score"] >= 63],
        [80, 60, 40],
        default=20
    )

    out["consensus_action"] = [action_from_score(s, e) for s, e in zip(out["consensus_score"], out["true_edge"])]
    out["confidence_grade"] = [grade_tier(s)[0] for s in out["consensus_score"]]
    out["confidence_emoji"] = [grade_tier(s)[1] for s in out["consensus_score"]]
    out["movement_note"] = [movement_note(e * 100) for e in out["true_edge"]]

    stake_rows = [
        single_stake_units(row, bankroll=bankroll, max_single_pct=max_single_pct)
        for _, row in out.iterrows()
    ]
    stake_df = pd.DataFrame(stake_rows)
    out = pd.concat([out.reset_index(drop=True), stake_df.reset_index(drop=True)], axis=1)

    out["rank_score"] = (
        out["consensus_score"] * 0.42
        + out["realistic_ev_pct"].clip(lower=-10, upper=25) * 1.05
        + (out["true_edge"] * 100).clip(lower=-5, upper=18) * 1.10
        + (out["realistic_hit_prob"] * 100) * 0.22
    ).round(2)

    return out


# ============================================================
# Pool / plays
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


def unique_top_plays(df: pd.DataFrame) -> Dict[str, pd.Series]:
    if df.empty:
        return {
            "ev": pd.Series(dtype=object),
            "safe": pd.Series(dtype=object),
            "edge": pd.Series(dtype=object),
            "balanced": pd.Series(dtype=object),
        }

    used = set()
    modes = {
        "ev": ["realistic_ev_pct", "true_edge", "consensus_score"],
        "safe": ["realistic_hit_prob", "consensus_score", "true_edge"],
        "edge": ["true_edge", "realistic_ev_pct", "consensus_score"],
        "balanced": ["rank_score", "consensus_score", "realistic_ev_pct"],
    }
    out = {}
    for key, cols in modes.items():
        choice = pd.Series(dtype=object)
        for _, row in df.sort_values(cols, ascending=False).iterrows():
            player_key = f"{row['player']}-{row['market']}"
            if player_key not in used:
                choice = row
                used.add(player_key)
                break
        if choice.empty:
            choice = df.sort_values(cols, ascending=False).iloc[0]
        out[key] = choice
    return out


def why_this_play(row: pd.Series) -> List[str]:
    projection = safe_float(row.get("projection"), np.nan)
    line = safe_float(row.get("line"), np.nan)
    proj_edge = projection - line if not pd.isna(projection) and not pd.isna(line) else np.nan

    model_agreement = int(safe_float(row.get("model_agreement_pct"), 0))
    true_edge = safe_float(row.get("true_edge"), 0) * 100
    script_type = row.get("script_type", "Neutral environment")
    script_score = int(safe_float(row.get("script_score"), 0))
    variance = row.get("variance_note", "Neutral variance")
    stake_u = safe_float(row.get("single_stake_u"), 0)

    notes = [
        f"Projection Edge: {proj_edge:+.1f} vs line" if not pd.isna(proj_edge) else "Projection Edge: N/A",
        f"Model Agreement: {model_agreement}% aligned",
        f"Market Inefficiency: true edge {true_edge:.1f}%",
        f"Game Script: {script_type} ({script_score})" if script_score > 0 else f"Game Script: {script_type}",
        f"Risk: {variance}",
        f"Recommended stake: {stake_u:.2f}u",
    ]
    return notes


# ============================================================
# Correlation / parlay / bankroll
# ============================================================
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


def correlation_summary(pen: float) -> str:
    if pen <= 0.05:
        return "Low"
    if pen <= 0.20:
        return "Medium"
    return "High"


def kelly_fraction(prob: float, decimal_odds: float) -> float:
    if decimal_odds <= 1 or prob <= 0 or prob >= 1:
        return 0.0
    b = decimal_odds - 1
    q = 1 - prob
    return max(0.0, (b * prob - q) / b)


def stake_from_kelly(prob: float, decimal_odds: float, parlay_type: str, bankroll: float, max_fraction: float) -> Dict:
    raw = kelly_fraction(prob, decimal_odds)
    type_mult = {"Safe": 0.35, "Balanced": 0.22, "Aggressive": 0.10}.get(parlay_type, 0.15)
    frac = min(raw * type_mult, max_fraction)
    dollars = bankroll * frac
    units = dollars / (bankroll * 0.01) if bankroll > 0 else 0
    return {
        "kelly_raw_pct": raw * 100,
        "bet_pct": frac * 100,
        "stake_$": dollars,
        "stake_u": units,
    }


def parlay_type(metrics: Dict) -> str:
    hp = metrics["hit_pct"]
    ev = metrics["ev_pct"]
    odds = metrics["combined_american"]
    if hp >= 42 and odds <= 300:
        return "Safe"
    if hp >= 28 and ev >= 6:
        return "Balanced"
    return "Aggressive"


def build_parlay(rows: List[pd.Series], bankroll: float, max_fraction: float) -> Dict:
    decs = [american_to_decimal(r["odds"]) for r in rows]
    probs = [r["realistic_hit_prob"] for r in rows]
    if any(pd.isna(x) for x in decs) or any(pd.isna(x) for x in probs):
        return {}

    combined_dec = float(np.prod(decs))
    combined_amer = decimal_to_american(combined_dec)
    p_ind = float(np.prod(probs))
    corr_pen = combo_corr_penalty(rows)
    p_adj = clamp01(p_ind * (1 - corr_pen))
    ev = p_adj * (combined_dec - 1) - (1 - p_adj)
    ev_pct = ev * 100

    if p_adj < 0.10 or ev_pct < 1.5:
        return {}

    out = {
        "legs": rows,
        "combined_decimal": combined_dec,
        "combined_american": combined_amer,
        "hit_prob": p_adj,
        "hit_pct": p_adj * 100,
        "ev_pct": ev_pct,
        "corr_pen": corr_pen,
        "corr_level": correlation_summary(corr_pen),
    }
    out["type"] = parlay_type(out)
    out.update(stake_from_kelly(out["hit_prob"], out["combined_decimal"], out["type"], bankroll, max_fraction))
    return out


def generate_parlays(df: pd.DataFrame, leg_size: int, bankroll: float, max_fraction: float, max_results: int = 30) -> List[Dict]:
    rows = [r[1] for r in df.iterrows()]
    results = []
    for combo in itertools.combinations(rows, leg_size):
        p = build_parlay(list(combo), bankroll, max_fraction)
        if p:
            results.append(p)
    results = sorted(results, key=lambda x: (x["ev_pct"], x["hit_pct"]), reverse=True)
    return results[:max_results]


def apply_exposure_cap(parlays: List[Dict], bankroll: float, cap_pct: float) -> List[Dict]:
    remaining = bankroll * cap_pct
    out = []
    for p in parlays:
        if p["stake_$"] <= remaining + 1e-9:
            out.append(p)
            remaining -= p["stake_$"]
    return out


def select_best_by_type(parlays: List[Dict]) -> Dict[str, Dict]:
    buckets = {"Safe": None, "Balanced": None, "Aggressive": None}
    for t in buckets:
        subset = [p for p in parlays if p["type"] == t]
        if subset:
            if t == "Safe":
                subset = sorted(subset, key=lambda x: (x["hit_pct"], x["ev_pct"]), reverse=True)
            elif t == "Balanced":
                subset = sorted(subset, key=lambda x: (x["ev_pct"] + x["hit_pct"] * 0.25), reverse=True)
            else:
                subset = sorted(subset, key=lambda x: (x["combined_american"], x["ev_pct"]), reverse=True)
            buckets[t] = subset[0]
    return buckets


# ============================================================
# UI render
# ============================================================
def metric_box(label: str, value: str):
    st.markdown(
        f"""
        <div class="metric-box">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_row(items: List[Tuple[str, str]]):
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items):
        with col:
            metric_box(label, value)


def ev_color_class(v: float) -> str:
    if v > 10:
        return "ev-green"
    if v >= 5:
        return "ev-yellow"
    return "ev-red"


def conf_fill(score: float) -> Tuple[str, float]:
    if score >= 80:
        return "#16a34a", score
    if score >= 68:
        return "#eab308", score
    return "#f97316", score


def badge_class_from_action(action: str) -> str:
    if action == "Bet":
        return "pill-green"
    if action == "Lean":
        return "pill-yellow"
    return "pill-red"


def render_summary_banner(best_ev: pd.Series, safest: pd.Series, best_parlay: Dict | None):
    parlay_txt = f"{best_parlay['type']} {fmt_american(best_parlay['combined_american'])}" if best_parlay else "None"
    st.markdown(
        f"""
        <div class="banner">
            <div class="banner-title">📊 TODAY'S EDGE SUMMARY</div>
            <div style="margin-bottom:8px;"><b>Best Play:</b> {best_ev['player']} {best_ev['bet_side']} {best_ev['line']} {best_ev['market']}</div>
            <div style="margin-bottom:8px;"><b>Highest EV:</b> {best_ev['realistic_ev_pct']:.1f}%</div>
            <div style="margin-bottom:8px;"><b>Safest Hit:</b> {safest['player']} ({safest['realistic_hit_prob']*100:.1f}%)</div>
            <div><b>Recommended:</b> 1 Single • 1 Parlay ({parlay_txt})</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_compact_metrics(items: List[Tuple[str, str, str]]):
    parts = ['<div class="compact-grid">']
    for label, value, cls in items:
        parts.append(
            f'<div class="compact-cell"><div class="compact-label">{label}</div><div class="compact-value {cls}">{value}</div></div>'
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def render_play_card(row: pd.Series, title: str):
    if row.empty:
        return
    bar_color, bar_pct = conf_fill(float(row["consensus_score"]))
    reasons = why_this_play(row)

    st.markdown(
        f'<div class="card"><div class="card-title">{title}</div><div class="card-sub">{row["player"]} — {row["bet_side"]} {row["line"]} {row["market"]}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<span class="pill {badge_class_from_action(row["consensus_action"])}">{row["consensus_action"]}</span>'
        f'<span class="pill pill-gray">{row["confidence_emoji"]} {row["confidence_grade"]}</span>'
        f'<span class="pill pill-gray">{int(row["model_agreement_pct"])}% Agreement</span>'
        f'<span class="pill pill-blue">{row["single_stake_u"]:.2f}u</span>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="confbar-wrap"><div class="confbar-fill" style="width:{bar_pct:.1f}%; background:{bar_color};"></div></div>',
        unsafe_allow_html=True,
    )
    render_compact_metrics([
        ("Hit %", f'{row["realistic_hit_prob"]*100:.1f}%', ""),
        ("Realistic EV", f'{row["realistic_ev_pct"]:.1f}%', ev_color_class(float(row["realistic_ev_pct"]))),
        ("True Edge", f'{row["true_edge"]*100:.1f}%', ""),
        ("Odds", fmt_american(row["odds"]), ""),
        ("Score", f'{row["consensus_score"]:.1f}', ""),
        ("Stake", f'${row["single_stake_$"]:.0f} / {row["single_stake_u"]:.2f}u', ""),
    ])
    st.markdown(
        "<div class='reason-box'><div style='font-weight:800; margin-bottom:6px;'>📊 WHY THIS PLAY</div>"
        + "".join([f"<div style='margin-bottom:5px;'>• {r}</div>" for r in reasons])
        + "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(f"<div class='small-muted'>{row['matchup']} • {row['book']} • {row['movement_note']}</div></div>", unsafe_allow_html=True)


def render_parlay_card(p: Dict, title: str):
    if not p:
        return
    cls = "parlay-safe" if p["type"] == "Safe" else ("parlay-balanced" if p["type"] == "Balanced" else "parlay-aggressive")
    pill_cls = "pill-green" if p["type"] == "Safe" else ("pill-yellow" if p["type"] == "Balanced" else "pill-red")
    conf_pct = max(10, min(100, p["hit_pct"] + (max(0, p["ev_pct"]) * 0.7)))
    conf_color = "#16a34a" if p["type"] == "Safe" else ("#eab308" if p["type"] == "Balanced" else "#dc2626")

    st.markdown(f'<div class="card {cls}"><div class="card-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<span class="pill {pill_cls}">{p["type"]}</span>'
        f'<span class="pill pill-gray">{p["corr_level"]} Corr</span>'
        f'<span class="pill pill-gray">{fmt_american(p["combined_american"])}</span>'
        f'<span class="pill pill-gray">{p["stake_u"]:.2f}u</span>',
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="small-muted">Confidence: {conf_pct:.0f}%</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="confbar-wrap"><div class="confbar-fill" style="width:{conf_pct:.1f}%; background:{conf_color};"></div></div>', unsafe_allow_html=True)

    render_compact_metrics([
        ("Hit %", f'{p["hit_pct"]:.1f}%', ""),
        ("EV %", f'{p["ev_pct"]:.1f}%', ev_color_class(float(p["ev_pct"]))),
        ("Kelly Raw", f'{p["kelly_raw_pct"]:.1f}%', ""),
        ("Bet %", f'{p["bet_pct"]:.2f}%', ""),
        ("Stake $", f'${p["stake_$"]:.2f}', ""),
        ("Corr Penalty", f'{p["corr_pen"]:.2f}', ""),
    ])

    st.markdown(
        f"<div class='reason-box'><div style='font-weight:800; margin-bottom:6px;'>🧩 CORRELATION INTELLIGENCE</div>"
        f"<div>• Correlation: {p['corr_level']} ({p['corr_pen']:.2f})</div>"
        f"<div>• {'Same game exposure present' if p['corr_pen'] > 0 else 'Cross-game build'}</div>"
        f"<div>• Kelly-lite sizing keeps stake controlled</div></div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div style='font-weight:800; margin-top:8px;'>Legs</div>", unsafe_allow_html=True)
    st.markdown(
        "<ul class='legs-list'>" + "".join(
            [f"<li>{leg['player']} — {leg['bet_side']} {leg['line']} {leg['market']} ({fmt_american(leg['odds'])})</li>" for leg in p["legs"]]
        ) + "</ul></div>",
        unsafe_allow_html=True,
    )


# ============================================================
# Sample data / load
# ============================================================
def sample_data() -> pd.DataFrame:
    return pd.DataFrame([
        {"player": "Stephen Curry", "team": "GSW", "opponent": "LAL", "matchup": "Warriors vs Lakers", "market": "points", "bet_side": "Over", "line": 27.0, "projection": 32.2, "odds": -115, "book": "DraftKings", "starter": True, "minutes": 35, "spread": -2.5, "pace": 102.4, "usage": 31.0},
        {"player": "LeBron James", "team": "LAL", "opponent": "GSW", "matchup": "Lakers vs Warriors", "market": "pra", "bet_side": "Over", "line": 38.0, "projection": 43.8, "odds": -115, "book": "DraftKings", "starter": True, "minutes": 36, "spread": 2.5, "pace": 101.9, "usage": 30.5},
        {"player": "Anthony Davis", "team": "LAL", "opponent": "GSW", "matchup": "Lakers vs Warriors", "market": "rebounds", "bet_side": "Over", "line": 11.5, "projection": 13.1, "odds": -105, "book": "FanDuel", "starter": True, "minutes": 35, "spread": 2.5, "pace": 101.9, "usage": 27.0},
        {"player": "Austin Reaves", "team": "LAL", "opponent": "GSW", "matchup": "Lakers vs Warriors", "market": "assists", "bet_side": "Under", "line": 6.5, "projection": 5.2, "odds": -102, "book": "BetMGM", "starter": True, "minutes": 34, "spread": 2.5, "pace": 101.9, "usage": 21.0},
        {"player": "Jordan Poole", "team": "WAS", "opponent": "BKN", "matchup": "Wizards vs Nets", "market": "points", "bet_side": "Over", "line": 21.5, "projection": 24.4, "odds": 102, "book": "Caesars", "starter": True, "minutes": 33, "spread": 5.0, "pace": 99.6, "usage": 30.0},
        {"player": "Jalen Brunson", "team": "NYK", "opponent": "MIA", "matchup": "Knicks vs Heat", "market": "points", "bet_side": "Over", "line": 26.5, "projection": 29.7, "odds": -110, "book": "FanDuel", "starter": True, "minutes": 36, "spread": -3.0, "pace": 98.7, "usage": 30.6},
        {"player": "Jimmy Butler", "team": "MIA", "opponent": "NYK", "matchup": "Heat vs Knicks", "market": "assists", "bet_side": "Over", "line": 5.5, "projection": 6.7, "odds": 100, "book": "DraftKings", "starter": True, "minutes": 35, "spread": 3.0, "pace": 98.7, "usage": 25.1},
        {"player": "Bench Example", "team": "MIA", "opponent": "BOS", "matchup": "Heat vs Celtics", "market": "points", "bet_side": "Over", "line": 10.5, "projection": 13.2, "odds": -110, "book": "DraftKings", "starter": False, "minutes": 24, "spread": 9.5, "pace": 95.8, "usage": 18.0},
    ])


@st.cache_data(show_spinner=False)
def load_csv(file) -> pd.DataFrame:
    return pd.read_csv(file)


# ============================================================
# App header
# ============================================================
st.title("🏀 Sports AI Betting Dashboard")
st.caption("Build V8: enhanced filters, single-bet sizing, better ranking engine, upgraded parlay lab, and cleaner mobile-first workflow.")

# ============================================================
# Sidebar controls
# ============================================================
with st.sidebar:
    st.markdown("### Data")
    uploaded = st.file_uploader("Upload CSV", type=["csv"])
    use_sample = st.toggle("Use sample data", value=uploaded is None)

    st.markdown("### Parlay Controls")
    leg_size = st.selectbox("Parlay size", [2, 3], index=0)
    bankroll = st.number_input("Bankroll ($)", min_value=100, max_value=100000, value=1000, step=50)
    max_bet_pct = st.slider("Max bankroll % per parlay", 0.25, 3.0, 1.0, 0.25) / 100.0
    max_single_pct = st.slider("Max bankroll % per single", 0.25, 3.0, 1.25, 0.25) / 100.0
    exposure_cap_pct = st.slider("Total parlay exposure cap %", 1.0, 10.0, 3.0, 0.5) / 100.0
    max_parlays = st.slider("Max parlay combos", 5, 50, 25)

    st.markdown("### Approval Engine")
    min_approval_score = st.slider("Min approval score", 60, 85, 64)
    min_edge_pct = st.slider("Min true edge %", 0.0, 12.0, 2.0, 0.5)
    min_ev_pct = st.slider("Min realistic EV %", 0.0, 20.0, 2.0, 0.5)

    st.markdown("### UI")
    bet_slip_mode = st.toggle("Enable Bet Slip Mode", value=True)
    show_full_table = st.toggle("Show full raw model table", value=False)

# ============================================================
# Load and score data
# ============================================================
if uploaded and not use_sample:
    df = ensure_columns(load_csv(uploaded))
else:
    df = ensure_columns(sample_data())

df = compute_scores(df, bankroll=float(bankroll), max_single_pct=float(max_single_pct))

# ============================================================
# Dynamic filters
# ============================================================
with st.expander("🎛️ Advanced Filters", expanded=True):
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        markets = sorted([x for x in df["market"].dropna().astype(str).unique().tolist() if x.strip() != ""])
        selected_markets = st.multiselect("Market", markets, default=[])

    with c2:
        books = sorted([x for x in df["book"].dropna().astype(str).unique().tolist() if x.strip() != ""])
        selected_books = st.multiselect("Sportsbook", books, default=[])

    with c3:
        teams = sorted([x for x in df["team"].dropna().astype(str).unique().tolist() if x.strip() != ""])
        selected_teams = st.multiselect("Team", teams, default=[])

    with c4:
        side_filter = st.selectbox("Bet Side", ["All", "Over", "Under"], index=0)

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        starter_only = st.toggle("Starters only", value=False)
    with c6:
        min_minutes = st.slider("Min minutes", 0, 40, 0, 1)
    with c7:
        odds_min = st.number_input("Min American odds", value=-300, step=5)
    with c8:
        odds_max = st.number_input("Max American odds", value=200, step=5)

filtered_df = df.copy()

if selected_markets:
    filtered_df = filtered_df[filtered_df["market"].isin(selected_markets)]
if selected_books:
    filtered_df = filtered_df[filtered_df["book"].isin(selected_books)]
if selected_teams:
    filtered_df = filtered_df[filtered_df["team"].isin(selected_teams)]
if side_filter != "All":
    filtered_df = filtered_df[filtered_df["bet_side"] == side_filter]
if starter_only:
    filtered_df = filtered_df[filtered_df["starter"] == True]
filtered_df = filtered_df[filtered_df["minutes"].fillna(0) >= min_minutes]
filtered_df = filtered_df[
    filtered_df["odds"].fillna(0).between(min(odds_min, odds_max), max(odds_min, odds_max))
]

pool = approved_pool(filtered_df)
pool = pool[
    (pool["consensus_score"] >= min_approval_score)
    & ((pool["true_edge"] * 100) >= min_edge_pct)
    & (pool["realistic_ev_pct"] >= min_ev_pct)
].copy()

if pool.empty:
    st.warning("No plays qualify under the current Build V8 filters.")
    st.stop()

pool = pool.sort_values(["rank_score", "realistic_ev_pct", "consensus_score"], ascending=False).reset_index(drop=True)

top = unique_top_plays(pool)
all_parlays = generate_parlays(pool, leg_size=leg_size, bankroll=float(bankroll), max_fraction=float(max_bet_pct), max_results=max_parlays)
approved_parlays = apply_exposure_cap(all_parlays, float(bankroll), float(exposure_cap_pct))
best_by_type = select_best_by_type(approved_parlays)
featured_parlay = best_by_type["Safe"] or best_by_type["Balanced"] or best_by_type["Aggressive"]

# ============================================================
# Overview metrics
# ============================================================
best_single = top["ev"]
safest_play = top["safe"]

today_single_units = safe_float(best_single.get("single_stake_u"), 0.0) if not best_single.empty else 0.0
today_parlay_units = featured_parlay["stake_u"] if featured_parlay else 0.0
expected_roi = (
    (safe_float(best_single.get("realistic_ev_pct"), 0.0) * 0.5)
    + ((featured_parlay["ev_pct"] if featured_parlay else 0.0) * 0.5)
)
risk_label = "Moderate" if featured_parlay else "Light"

render_metric_row([
    ("Approved Plays", str(len(pool))),
    ("Recommended Singles", f"{today_single_units:.2f}u"),
    ("Recommended Parlays", f"{today_parlay_units:.2f}u"),
    ("Expected ROI", f"{expected_roi:.1f}%"),
])

render_summary_banner(best_single, safest_play, featured_parlay)

# ============================================================
# Main tabs
# ============================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏠 Dashboard",
    "🔥 Singles Lab",
    "🧩 Parlay Lab",
    "🎯 Bet Slip",
    "📋 Data View",
])

# ============================================================
# Dashboard
# ============================================================
with tab1:
    st.markdown("## Approved Pool")
    pool_show = pool[[
        "player", "team", "matchup", "market", "bet_side", "line", "odds", "true_edge",
        "realistic_ev_pct", "realistic_hit_prob", "consensus_score",
        "model_agreement_pct", "single_stake_u", "consensus_action"
    ]].copy()

    pool_show["odds"] = pool_show["odds"].apply(fmt_american)
    pool_show["true_edge"] = (pool_show["true_edge"] * 100).round(1).astype(str) + "%"
    pool_show["realistic_ev_pct"] = pool_show["realistic_ev_pct"].round(1).astype(str) + "%"
    pool_show["realistic_hit_prob"] = (pool_show["realistic_hit_prob"] * 100).round(1).astype(str) + "%"
    pool_show["model_agreement_pct"] = pool_show["model_agreement_pct"].astype(int).astype(str) + "%"
    pool_show["single_stake_u"] = pool_show["single_stake_u"].round(2).astype(str) + "u"

    st.dataframe(pool_show, use_container_width=True, hide_index=True)

    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
    st.markdown("## Top Plays Panel")

    a, b, c, d = st.tabs(["🔥 Best Single", "🔒 Safest Play", "⚡ Highest Edge", "🎯 Best Balanced"])
    with a:
        render_play_card(top["ev"], "Best Single (Highest EV)")
    with b:
        render_play_card(top["safe"], "Safest Play")
    with c:
        render_play_card(top["edge"], "Highest Edge Play")
    with d:
        render_play_card(top["balanced"], "Best Balanced Play")

    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
    st.markdown("## Bankroll Strategy")
    render_metric_row([
        ("Singles Risk", risk_label),
        ("Top Single Stake", f"{today_single_units:.2f}u"),
        ("Top Parlay Stake", f"{today_parlay_units:.2f}u"),
        ("Parlays Available", str(len(approved_parlays))),
    ])

# ============================================================
# Singles Lab
# ============================================================
with tab2:
    st.markdown("## 🔥 Singles Lab")
    st.caption("Sorted by Build V8 ranking engine: score + EV + edge + realistic hit rate.")

    singles_df = pool[[
        "player", "team", "matchup", "market", "bet_side", "line", "projection",
        "odds", "realistic_hit_prob", "true_edge", "realistic_ev_pct",
        "consensus_score", "model_agreement_pct", "single_stake_u", "single_stake_$",
        "confidence_grade", "consensus_action", "book", "movement_note",
        "script_type", "script_score", "variance_note", "confidence_emoji"
    ]].copy()

    singles_df["odds_display"] = singles_df["odds"].apply(fmt_american)
    singles_df["hit_display"] = (singles_df["realistic_hit_prob"] * 100).round(1)
    singles_df["edge_display"] = (singles_df["true_edge"] * 100).round(1)
    singles_df["ev_display"] = singles_df["realistic_ev_pct"].round(1)

    top_n = st.slider("Show top N singles", 3, min(25, len(singles_df)), min(10, len(singles_df)))
    for _, row in singles_df.head(top_n).iterrows():
        render_play_card(row, f"Ranked Single • {row['player']}")

# ============================================================
# Parlay Lab
# ============================================================
with tab3:
    st.markdown("## 🧩 Parlay Lab")

    s1, s2, s3 = st.columns(3)
    with s1:
        if best_by_type["Safe"]:
            render_parlay_card(best_by_type["Safe"], "Best Safe Parlay")
        else:
            st.info("No Safe parlay found.")
    with s2:
        if best_by_type["Balanced"]:
            render_parlay_card(best_by_type["Balanced"], "Best Balanced Parlay")
        else:
            st.info("No Balanced parlay found.")
    with s3:
        if best_by_type["Aggressive"]:
            render_parlay_card(best_by_type["Aggressive"], "Best Aggressive Parlay")
        else:
            st.info("No Aggressive parlay found.")

    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
    st.markdown("## All Approved Parlays")

    if approved_parlays:
        rows = []
        for i, p in enumerate(approved_parlays, 1):
            rows.append({
                "Rank": i,
                "Type": p["type"],
                "Odds": fmt_american(p["combined_american"]),
                "Hit %": round(p["hit_pct"], 1),
                "EV %": round(p["ev_pct"], 1),
                "Kelly %": round(p["kelly_raw_pct"], 2),
                "Bet %": round(p["bet_pct"], 2),
                "Stake u": round(p["stake_u"], 2),
                "Stake $": round(p["stake_$"], 2),
                "Corr": round(p["corr_pen"], 2),
                "Legs": " | ".join([f"{x['player']} {x['bet_side']} {x['line']}" for x in p["legs"]]),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.caption("Sharper builds rise after EV, hit-rate, and correlation controls.")
    else:
        st.info("No approved parlays available.")

# ============================================================
# Bet Slip
# ============================================================
with tab4:
    st.markdown("## 🎯 Bet Slip Builder")

    if not bet_slip_mode:
        st.info("Enable Bet Slip Mode in the sidebar to use this tab.")
    else:
        st.markdown(
            '<div class="bet-slip-wrap">Select approved plays below and Build V8 will price your custom parlay with correlation control.</div>',
            unsafe_allow_html=True,
        )

        selections = []
        for idx, row in pool.sort_values(["rank_score", "realistic_ev_pct"], ascending=False).iterrows():
            label = (
                f"{row['player']} — {row['bet_side']} {row['line']} {row['market']} "
                f"({fmt_american(row['odds'])}) • EV {row['realistic_ev_pct']:.1f}% • {row['single_stake_u']:.2f}u"
            )
            if st.checkbox(label, key=f"bet_slip_{idx}"):
                selections.append(row)

        st.caption(f"Selected plays: {len(selections)}")
        if len(selections) >= 2:
            custom_leg_size = st.selectbox("Custom parlay leg count", [2, 3], index=0, key="custom_leg_size")
            chosen = selections[:custom_leg_size]
            custom = build_parlay(chosen, float(bankroll), float(max_bet_pct))
            if custom:
                render_parlay_card(custom, "Custom Bet Slip Parlay")
            else:
                st.warning("Selected combination did not pass custom parlay thresholds.")
        else:
            st.caption("Select at least two plays to build a custom parlay.")

# ============================================================
# Data view
# ============================================================
with tab5:
    st.markdown("## 📋 Model Data View")
    if show_full_table:
        raw_show = filtered_df.copy()
        if "odds" in raw_show.columns:
            raw_show["odds_display"] = raw_show["odds"].apply(fmt_american)
        st.dataframe(raw_show, use_container_width=True, hide_index=True)
    else:
        data_view = pool[[
            "player", "team", "opponent", "matchup", "market", "bet_side", "line",
            "projection", "odds", "hit_prob", "realistic_hit_prob", "implied_prob",
            "true_edge", "raw_ev_pct", "realistic_ev_pct", "consensus_score",
            "rank_score", "confidence_grade", "model_agreement_pct", "single_stake_u",
            "book", "starter", "minutes", "script_type", "script_score", "variance_note"
        ]].copy()
        data_view["odds"] = data_view["odds"].apply(fmt_american)
        st.dataframe(data_view, use_container_width=True, hide_index=True)

st.caption("Next upgrade target: NBA Props V9 with starters-only prop engine, alternate odds filters, 1Q props logic, and slate exposure controls.")
