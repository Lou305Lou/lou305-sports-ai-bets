import math
import itertools
from typing import List, Dict

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Sports AI Betting Dashboard", layout="wide")


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


# ============================================================
# Styling
# ============================================================
st.markdown("""
<style>
.block-container {padding-top: 1.2rem; padding-bottom: 3rem;}
.small-muted {color: rgba(49,51,63,0.68); font-size: 0.95rem;}
.section-card {
    border:1px solid rgba(128,128,128,0.22);
    border-radius:18px;
    padding:14px 16px;
    background: rgba(250,250,250,0.78);
    margin-bottom: 12px;
}
.metric-box {
    border:1px solid rgba(128,128,128,0.22);
    border-radius:16px;
    padding:12px 14px;
    background: rgba(250,250,250,0.78);
    min-height: 86px;
}
.metric-label {
    font-size: 0.90rem;
    color: rgba(49,51,63,0.70);
    margin-bottom: 6px;
}
.metric-value {
    font-size: 1.9rem;
    font-weight: 800;
    line-height: 1.1;
}
.pill {
    display:inline-block;
    padding:6px 10px;
    border-radius:999px;
    font-weight:700;
    font-size:0.95rem;
    margin-right:6px;
    margin-bottom:6px;
    border:1px solid rgba(128,128,128,0.20);
}
.pill-green {background:#16a34a; color:white; border:none;}
.pill-yellow {background:#eab308; color:#111827; border:none;}
.pill-red {background:#dc2626; color:white; border:none;}
.pill-gray {background:#f3f4f6; color:#111827;}
.play-card {
    border:1px solid rgba(128,128,128,0.20);
    border-radius:18px;
    padding:16px;
    background: rgba(250,250,250,0.82);
    margin-bottom: 14px;
}
.play-title {
    font-size: 1.65rem;
    font-weight: 800;
    line-height: 1.15;
    margin-bottom: 6px;
}
.play-sub {
    color: rgba(49,51,63,0.76);
    font-size: 1rem;
    margin-bottom: 10px;
}
.kpi-grid {
    display:grid;
    grid-template-columns: repeat(2, minmax(0,1fr));
    gap:10px;
    margin-top: 8px;
    margin-bottom: 10px;
}
.kpi-cell {
    border:1px solid rgba(128,128,128,0.16);
    background:#f7f7f8;
    border-radius:14px;
    padding:10px 12px;
}
.kpi-name {
    font-size: 0.85rem;
    color: rgba(49,51,63,0.68);
}
.kpi-value {
    font-size: 1.35rem;
    font-weight: 800;
    margin-top: 3px;
}
.confbar-wrap {
    height: 10px;
    border-radius: 999px;
    background: #ececec;
    overflow: hidden;
    margin-top: 8px;
    margin-bottom: 10px;
}
.confbar-fill {
    height: 10px;
    border-radius: 999px;
}
.parlay-card {
    border:2px solid rgba(128,128,128,0.18);
    border-radius:20px;
    padding:16px;
    margin-bottom: 16px;
    background: rgba(250,250,250,0.82);
}
.parlay-safe {border-color:#16a34a;}
.parlay-balanced {border-color:#eab308;}
.parlay-aggressive {border-color:#dc2626;}
.legs-list li {margin-bottom: 8px;}
.summary-banner {
    border-radius:18px;
    padding:16px;
    background: linear-gradient(135deg, rgba(248,250,252,1), rgba(240,249,255,1));
    border:1px solid rgba(148,163,184,0.22);
    margin-bottom: 14px;
}
@media (max-width: 768px) {
  .play-title {font-size: 1.35rem;}
  .metric-value {font-size: 1.55rem;}
  .kpi-grid {grid-template-columns: repeat(2, minmax(0,1fr));}
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
        "player": "", "team": "", "opponent": "", "matchup": "",
        "market": "", "bet_side": "", "line": np.nan, "projection": np.nan,
        "odds": np.nan, "book": "", "starter": False, "minutes": np.nan,
        "std_dev": np.nan, "game_total": np.nan, "spread": np.nan,
    }
    for col, val in defaults.items():
        if col not in df.columns:
            df[col] = val

    for c in ["player", "team", "opponent", "matchup", "market", "bet_side", "book"]:
        df[c] = df[c].fillna("").astype(str).str.strip()

    for c in ["line", "projection", "odds", "minutes", "std_dev", "game_total", "spread"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df["starter"] = df["starter"].fillna(False).astype(bool)

    if (df["matchup"] == "").any():
        auto_matchup = df["team"].fillna("") + np.where(
            df["opponent"].fillna("") != "", " vs " + df["opponent"].fillna(""), ""
        )
        df.loc[df["matchup"] == "", "matchup"] = auto_matchup[df["matchup"] == ""]

    return df


def infer_market_std(row: pd.Series) -> float:
    supplied = row.get("std_dev")
    if pd.notna(supplied) and supplied > 0:
        return float(supplied)
    market = str(row.get("market", "")).lower()
    defaults = {
        "points": 8.5, "rebounds": 4.0, "assists": 3.6,
        "pra": 9.0, "threes": 2.4, "3pm": 2.4
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


def compute_scores(df: pd.DataFrame) -> pd.DataFrame:
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

    out["consensus_score"] = (
        out["hit_pct"] * 0.35
        + out["true_edge"].clip(lower=-0.05, upper=0.15) * 180
        + out["realistic_ev_pct"].clip(lower=-10, upper=20) * 0.8
        + np.where(out["starter"], 4, -8)
        + np.where(out["minutes"].fillna(0) >= 33, 4, np.where(out["minutes"].fillna(0) >= 28, 1, -4))
        - np.where(abs(out["spread"].fillna(0)) >= 10, 4, 0)
    ).clip(0, 100).round(1)

    out["model_agreement_pct"] = np.select(
        [out["consensus_score"] >= 78, out["consensus_score"] >= 70, out["consensus_score"] >= 63],
        [80, 60, 40],
        default=20
    )

    def action(row):
        if row["true_edge"] <= 0:
            return "Pass"
        if row["consensus_score"] >= 78 and row["model_agreement_pct"] >= 60:
            return "Bet"
        if row["consensus_score"] >= 66 and row["true_edge"] >= 0.025:
            return "Lean"
        return "Pass"

    out["consensus_action"] = out.apply(action, axis=1)

    def variance_note(row):
        std = infer_market_std(row)
        market = str(row.get("market", "")).lower()
        if "three" in market or "3pm" in market:
            return "High variance"
        if std >= 8.5:
            return "High-upside profile"
        if std <= 2.8:
            return "Lower variance"
        return "Neutral variance"

    out["variance_note"] = out.apply(variance_note, axis=1)
    return out


def approved_pool(df: pd.DataFrame) -> pd.DataFrame:
    primary = df[
        (
            (df["consensus_action"] == "Bet") |
            ((df["consensus_action"] == "Lean") & (df["model_agreement_pct"] >= 60))
        ) &
        (df["true_edge"] >= 0.02) &
        (df["realistic_ev_pct"] >= 2.0)
    ].copy()

    if len(primary) < 2:
        fallback = df[
            (df["consensus_action"].isin(["Bet", "Lean"])) &
            (df["true_edge"] >= 0.015) &
            (df["consensus_score"] >= 62)
        ].copy()
        fallback["fallback_flag"] = True
        return fallback

    primary["fallback_flag"] = False
    return primary


# ============================================================
# Singles logic
# ============================================================
def confidence_badge(row: pd.Series) -> str:
    score = float(row["consensus_score"])
    edge = float(row["true_edge"]) * 100
    if score >= 80 and edge >= 10:
        return "🔥 ELITE PLAY"
    if score >= 72 and edge >= 5:
        return "🟡 SOLID EDGE"
    return "⚠️ LEAN ONLY"


def unique_top_plays(df: pd.DataFrame) -> Dict[str, pd.Series]:
    used = set()
    plays = {}
    sort_modes = {
        "ev": ["realistic_ev_pct", "true_edge", "consensus_score"],
        "safe": ["realistic_hit_prob", "consensus_score", "true_edge"],
        "edge": ["true_edge", "realistic_ev_pct", "consensus_score"],
    }
    for key in ["ev", "safe", "edge"]:
        sorted_df = df.sort_values(sort_modes[key], ascending=False)
        chosen = None
        for _, row in sorted_df.iterrows():
            if row["player"] not in used:
                chosen = row
                used.add(row["player"])
                break
        if chosen is None and not sorted_df.empty:
            chosen = sorted_df.iloc[0]
        plays[key] = chosen if chosen is not None else pd.Series(dtype=object)
    return plays


# ============================================================
# Correlation + bankroll
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
    same_g = same_game(a, b)
    same_t = same_team(a, b)
    if not same_g:
        return 0.0

    market_a = str(a.get("market", "")).lower()
    market_b = str(b.get("market", "")).lower()
    side_a = str(a.get("bet_side", "")).lower()
    side_b = str(b.get("bet_side", "")).lower()

    pen += 0.12
    if same_t:
        pen += 0.08

    if side_a == "over" and side_b == "over":
        if any(k in market_a for k in ["points", "pra", "assists"]) and any(k in market_b for k in ["points", "pra", "assists"]):
            pen += 0.08
        elif ("points" in market_a and "rebounds" in market_b) or ("rebounds" in market_a and "points" in market_b):
            pen += 0.04

    if side_a != side_b and same_t:
        pen -= 0.03

    return max(0.0, pen)


def combo_corr_penalty(rows: List[pd.Series]) -> float:
    total = 0.0
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            total += pair_corr_penalty(rows[i], rows[j])
    return total


def kelly_fraction(prob: float, decimal_odds: float) -> float:
    if decimal_odds <= 1 or prob <= 0 or prob >= 1:
        return 0.0
    b = decimal_odds - 1
    q = 1 - prob
    frac = (b * prob - q) / b
    return max(0.0, frac)


def stake_from_kelly(prob: float, decimal_odds: float, parlay_type: str, bankroll: float, max_fraction: float) -> Dict:
    raw = kelly_fraction(prob, decimal_odds)
    type_mult = {"Safe": 0.35, "Balanced": 0.22, "Aggressive": 0.10}.get(parlay_type, 0.15)
    frac = min(raw * type_mult, max_fraction)
    dollars = bankroll * frac
    units = dollars / (bankroll * 0.01) if bankroll > 0 else 0
    return {
        "kelly_raw_pct": raw * 100,
        "kelly_bet_pct": frac * 100,
        "stake_$": dollars,
        "stake_u": units,
    }


# ============================================================
# Parlays
# ============================================================
def tag_parlay_type(metrics: Dict) -> str:
    hp = metrics["hit_pct"]
    ev = metrics["ev_pct"]
    odds = metrics["combined_american"]
    if hp >= 42 and odds <= 300:
        return "Safe"
    if hp >= 28 and ev >= 6:
        return "Balanced"
    return "Aggressive"


def build_parlay_metrics(rows: List[pd.Series], bankroll: float, max_fraction: float) -> Dict:
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

    if p_adj < 0.12 or ev_pct < 2.0:
        return {}

    base = {
        "legs": rows,
        "combined_decimal": combined_dec,
        "combined_american": combined_amer,
        "hit_prob": p_adj,
        "hit_pct": p_adj * 100,
        "ev": ev,
        "ev_pct": ev_pct,
        "corr_pen": corr_pen,
    }
    base["parlay_type"] = tag_parlay_type(base)
    base.update(stake_from_kelly(base["hit_prob"], base["combined_decimal"], base["parlay_type"], bankroll, max_fraction))
    return base


def generate_parlays(df: pd.DataFrame, k: int, bankroll: float, max_fraction: float, max_results: int = 30) -> List[Dict]:
    rows = [r[1] for r in df.iterrows()]
    results = []
    for combo in itertools.combinations(rows, k):
        m = build_parlay_metrics(list(combo), bankroll, max_fraction)
        if m:
            results.append(m)
    results = sorted(results, key=lambda x: (x["ev_pct"], x["hit_pct"]), reverse=True)
    return results[:max_results]


def apply_total_exposure_cap(parlays: List[Dict], bankroll: float, exposure_cap_pct: float) -> List[Dict]:
    remaining = bankroll * exposure_cap_pct
    approved = []
    for p in parlays:
        if p["stake_$"] <= remaining + 1e-9:
            approved.append(p)
            remaining -= p["stake_$"]
    return approved


def select_best_by_type(parlays: List[Dict]) -> Dict[str, Dict]:
    buckets = {"Safe": None, "Balanced": None, "Aggressive": None}
    for t in buckets:
        subset = [p for p in parlays if p["parlay_type"] == t]
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
# Render helpers
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


def render_metric_grid(items: List[tuple], cols_per_row: int = 4):
    for i in range(0, len(items), cols_per_row):
        chunk = items[i:i+cols_per_row]
        cols = st.columns(len(chunk))
        for col, (label, value) in zip(cols, chunk):
            with col:
                metric_box(label, value)


def ev_color(ev_pct: float) -> str:
    if ev_pct > 10:
        return "#16a34a"
    if ev_pct >= 5:
        return "#eab308"
    return "#dc2626"


def conf_color(score: float) -> str:
    if score >= 80:
        return "#16a34a"
    if score >= 70:
        return "#eab308"
    return "#f97316"


def render_summary_banner(play_ev: pd.Series, play_safe: pd.Series, parlay: Dict | None):
    best_play_text = f"{play_ev['player']} {play_ev['bet_side']} {play_ev['line']} {play_ev['market']}" if not play_ev.empty else "N/A"
    safest_text = f"{play_safe['player']} ({play_safe['realistic_hit_prob']*100:.1f}%)" if not play_safe.empty else "N/A"
    parlay_text = f"{parlay['parlay_type']} +{int(parlay['combined_american'])}" if parlay else "None"
    st.markdown(
        f"""
        <div class="summary-banner">
            <div style="font-size:1.25rem;font-weight:800;margin-bottom:10px;">📊 TODAY'S EDGE SUMMARY</div>
            <div style="margin-bottom:6px;"><b>Best Play:</b> {best_play_text}</div>
            <div style="margin-bottom:6px;"><b>Highest EV:</b> {play_ev['realistic_ev_pct']:.1f}%</div>
            <div style="margin-bottom:6px;"><b>Safest Hit:</b> {safest_text}</div>
            <div><b>Recommended:</b> 1 Single • 1 Parlay ({parlay_text})</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_compact_play_card(row: pd.Series, title: str):
    if row.empty:
        return
    badge = confidence_badge(row)
    action = str(row["consensus_action"])
    action_class = "pill-green" if action == "Bet" else ("pill-yellow" if action == "Lean" else "pill-red")
    fill = conf_color(float(row["consensus_score"]))
    pct = max(8, min(100, int(round(float(row["consensus_score"])))))
    st.markdown(
        f"""
        <div class="play-card">
            <div class="play-title">{title}</div>
            <div class="play-sub">{row['player']} — {row['bet_side']} {row['line']} {row['market']}</div>
            <div>
                <span class="pill {action_class}">{action}</span>
                <span class="pill pill-gray">{badge}</span>
                <span class="pill pill-gray">{int(row['model_agreement_pct'])}% Agreement</span>
            </div>
            <div class="confbar-wrap"><div class="confbar-fill" style="width:{pct}%; background:{fill};"></div></div>
            <div class="kpi-grid">
                <div class="kpi-cell"><div class="kpi-name">Hit %</div><div class="kpi-value">{row['realistic_hit_prob']*100:.1f}%</div></div>
                <div class="kpi-cell"><div class="kpi-name">Realistic EV</div><div class="kpi-value" style="color:{ev_color(float(row['realistic_ev_pct']))};">{row['realistic_ev_pct']:.1f}%</div></div>
                <div class="kpi-cell"><div class="kpi-name">True Edge</div><div class="kpi-value">{row['true_edge']*100:.1f}%</div></div>
                <div class="kpi-cell"><div class="kpi-name">Odds</div><div class="kpi-value">{int(row['odds']) if not pd.isna(row['odds']) else '—'}</div></div>
                <div class="kpi-cell"><div class="kpi-name">Score</div><div class="kpi-value">{row['consensus_score']:.1f}</div></div>
                <div class="kpi-cell"><div class="kpi-name">Variance</div><div class="kpi-value" style="font-size:1.05rem;">{row['variance_note']}</div></div>
            </div>
            <div class="small-muted">{row['matchup']} • {row['book']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_parlay_pro_card(p: Dict, title: str):
    if not p:
        return
    ptype = p["parlay_type"]
    border_cls = "parlay-safe" if ptype == "Safe" else ("parlay-balanced" if ptype == "Balanced" else "parlay-aggressive")
    pill_cls = "pill-green" if ptype == "Safe" else ("pill-yellow" if ptype == "Balanced" else "pill-red")
    confidence = int(max(10, min(100, round((p["hit_pct"] * 0.65) + (max(0, p["ev_pct"]) * 0.8)))))
    fill = "#16a34a" if ptype == "Safe" else ("#eab308" if ptype == "Balanced" else "#dc2626")
    risk_tag = "Low Risk" if ptype == "Safe" else ("Medium Risk" if ptype == "Balanced" else "High Risk")

    legs_html = "".join([f"<li>{leg['player']} — {leg['bet_side']} {leg['line']} {leg['market']} ({int(leg['odds']) if not pd.isna(leg['odds']) else 'N/A'})</li>" for leg in p["legs"]])

    st.markdown(
        f"""
        <div class="parlay-card {border_cls}">
            <div class="play-title">{title}</div>
            <div>
                <span class="pill {pill_cls}">{ptype}</span>
                <span class="pill pill-gray">{risk_tag}</span>
                <span class="pill pill-gray">Odds {int(p['combined_american']) if not pd.isna(p['combined_american']) else '—'}</span>
                <span class="pill pill-gray">{p['stake_u']:.2f}u</span>
            </div>
            <div class="small-muted">Confidence: {confidence}%</div>
            <div class="confbar-wrap"><div class="confbar-fill" style="width:{confidence}%; background:{fill};"></div></div>
            <div class="kpi-grid">
                <div class="kpi-cell"><div class="kpi-name">Hit %</div><div class="kpi-value">{p['hit_pct']:.1f}%</div></div>
                <div class="kpi-cell"><div class="kpi-name">EV %</div><div class="kpi-value" style="color:{ev_color(float(p['ev_pct']))};">{p['ev_pct']:.1f}%</div></div>
                <div class="kpi-cell"><div class="kpi-name">Kelly Raw</div><div class="kpi-value">{p['kelly_raw_pct']:.1f}%</div></div>
                <div class="kpi-cell"><div class="kpi-name">Bet %</div><div class="kpi-value">{p['kelly_bet_pct']:.2f}%</div></div>
                <div class="kpi-cell"><div class="kpi-name">Stake $</div><div class="kpi-value">${p['stake_$']:.2f}</div></div>
                <div class="kpi-cell"><div class="kpi-name">Corr Penalty</div><div class="kpi-value">{p['corr_pen']:.2f}</div></div>
            </div>
            <div class="small-muted" style="margin-bottom:6px;"><b>Legs</b></div>
            <ul class="legs-list">{legs_html}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# Sample data
# ============================================================
def sample_data() -> pd.DataFrame:
    return pd.DataFrame([
        {"player": "Stephen Curry", "team": "GSW", "opponent": "LAL", "matchup": "Warriors vs Lakers", "market": "points", "bet_side": "Over", "line": 27.0, "projection": 32.2, "odds": -115, "book": "DraftKings", "starter": True, "minutes": 35, "spread": -2.5},
        {"player": "LeBron James", "team": "LAL", "opponent": "GSW", "matchup": "Lakers vs Warriors", "market": "pra", "bet_side": "Over", "line": 38.0, "projection": 43.8, "odds": -115, "book": "DraftKings", "starter": True, "minutes": 36, "spread": 2.5},
        {"player": "Anthony Davis", "team": "LAL", "opponent": "GSW", "matchup": "Lakers vs Warriors", "market": "rebounds", "bet_side": "Over", "line": 11.5, "projection": 13.1, "odds": -105, "book": "FanDuel", "starter": True, "minutes": 35, "spread": 2.5},
        {"player": "Austin Reaves", "team": "LAL", "opponent": "GSW", "matchup": "Lakers vs Warriors", "market": "assists", "bet_side": "Under", "line": 6.5, "projection": 5.2, "odds": -102, "book": "BetMGM", "starter": True, "minutes": 34, "spread": 2.5},
        {"player": "Jordan Poole", "team": "WAS", "opponent": "BKN", "matchup": "Wizards vs Nets", "market": "points", "bet_side": "Over", "line": 21.5, "projection": 24.4, "odds": 102, "book": "Caesars", "starter": True, "minutes": 33, "spread": 5.0},
        {"player": "Bench Example", "team": "MIA", "opponent": "BOS", "matchup": "Heat vs Celtics", "market": "points", "bet_side": "Over", "line": 10.5, "projection": 13.2, "odds": -110, "book": "DraftKings", "starter": False, "minutes": 24, "spread": 9.5},
    ])


@st.cache_data(show_spinner=False)
def load_csv(file) -> pd.DataFrame:
    return pd.read_csv(file)


# ============================================================
# App
# ============================================================
st.title("🏀 Sports AI Betting Dashboard")
st.caption("V7.6 UI Pro: compact mobile layout, sharper visual hierarchy, unique top plays, and sportsbook-style cards.")

with st.sidebar:
    uploaded = st.file_uploader("Upload CSV", type=["csv"])
    use_sample = st.toggle("Use sample data", value=uploaded is None)
    parlay_size = st.selectbox("Parlay size", [2, 3], index=0)
    max_results = st.slider("Max parlay combos", 5, 40, 20)
    bankroll = st.number_input("Bankroll ($)", min_value=100, max_value=100000, value=1000, step=50)
    max_bet_pct = st.slider("Max bankroll % per parlay", 0.25, 3.0, 1.0, 0.25) / 100.0
    exposure_cap_pct = st.slider("Total parlay exposure cap %", 1.0, 10.0, 3.0, 0.5) / 100.0

if uploaded:
    df = ensure_columns(load_csv(uploaded))
else:
    df = ensure_columns(sample_data())

df = compute_scores(df)
pool = approved_pool(df)

if pool.empty:
    st.warning("No plays qualify for UI Pro Sharp Mode.")
    st.stop()

st.markdown("## Approved Pool")
pool_show = pool[[
    "player", "market", "bet_side", "line", "odds",
    "true_edge", "realistic_ev_pct", "consensus_score", "model_agreement_pct", "consensus_action"
]].copy()
pool_show["true_edge"] = (pool_show["true_edge"] * 100).round(1).astype(str) + "%"
pool_show["realistic_ev_pct"] = pool_show["realistic_ev_pct"].round(1).astype(str) + "%"
pool_show["model_agreement_pct"] = pool_show["model_agreement_pct"].astype(int).astype(str) + "%"
st.dataframe(pool_show, use_container_width=True, hide_index=True)

top_plays = unique_top_plays(pool)

all_parlays = generate_parlays(pool, k=parlay_size, bankroll=float(bankroll), max_fraction=float(max_bet_pct), max_results=max_results)
parlays = apply_total_exposure_cap(all_parlays, float(bankroll), float(exposure_cap_pct))
best = select_best_by_type(parlays)

best_parlay = best["Safe"] or best["Balanced"] or best["Aggressive"]
render_summary_banner(top_plays["ev"], top_plays["safe"], best_parlay)

st.markdown("## 🔍 Top Plays Panel")
tab1, tab2, tab3 = st.tabs(["🔥 Best Single", "🔒 Safest Play", "⚡ Highest Edge"])
with tab1:
    render_compact_play_card(top_plays["ev"], "Best Single (EV)")
with tab2:
    render_compact_play_card(top_plays["safe"], "Safest Play")
with tab3:
    render_compact_play_card(top_plays["edge"], "Highest Edge Play")

st.markdown("## 🛡️ Best Conservative Parlay")
render_metric_grid([
    ("Approved Plays", f"{len(pool)}"),
    ("Parlay Size", f"{parlay_size}-leg"),
    ("Bankroll", f"${float(bankroll):,.0f}"),
    ("Exposure Cap", f"{exposure_cap_pct*100:.1f}%"),
], cols_per_row=4)

if not parlays:
    st.info("No parlays survived UI Pro sharp rules.")
else:
    if best["Safe"] is not None:
        render_parlay_pro_card(best["Safe"], "🟢 Safe Parlay")
    if best["Balanced"] is not None and best["Balanced"] is not best["Safe"]:
        render_parlay_pro_card(best["Balanced"], "🟡 Balanced Parlay")
    if best["Aggressive"] is not None and best["Aggressive"] not in [best["Safe"], best["Balanced"]]:
        render_parlay_pro_card(best["Aggressive"], "🔴 Aggressive Parlay")

st.markdown("## All Approved Parlays")
if parlays:
    rows = []
    for i, p in enumerate(parlays, 1):
        rows.append({
            "Rank": i,
            "Type": p["parlay_type"],
            "Odds": int(p["combined_american"]) if not pd.isna(p["combined_american"]) else np.nan,
            "Hit %": round(p["hit_pct"], 1),
            "EV %": round(p["ev_pct"], 1),
            "Kelly %": round(p["kelly_raw_pct"], 2),
            "Bet %": round(p["kelly_bet_pct"], 2),
            "Stake u": round(p["stake_u"], 2),
            "Stake $": round(p["stake_$"], 2),
            "Corr": round(p["corr_pen"], 2),
            "Legs": " | ".join([f"{x['player']} {x['bet_side']} {x['line']}" for x in p["legs"]]),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
else:
    st.info("No approved parlays available.")

st.caption("Next upgrade: same-game parlay mode, live odds, and slate-level exposure controls.")
