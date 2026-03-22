import io
import math
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Sports Betting AI Dashboard V28", layout="wide")

APP_TITLE = "🔥 Sports Betting AI Dashboard V28"
APP_SUBTITLE = "Execution Intelligence Engine"
BET_LOG_PATH = Path("bet_log.csv")
LEARNING_PROFILE_PATH = Path("learning_profile.csv")
SNAPSHOT_PATH = Path("snapshot.csv")


# -----------------------------
# Data helpers
# -----------------------------
def american_to_prob(odds):
    try:
        odds = float(odds)
        if odds < 0:
            return (-odds) / ((-odds) + 100)
        return 100 / (odds + 100)
    except Exception:
        return np.nan


def implied_edge(model_prob, odds):
    market_prob = american_to_prob(odds)
    if pd.isna(model_prob) or pd.isna(market_prob):
        return np.nan
    return (float(model_prob) - float(market_prob)) * 100


def odds_bucket(odds):
    try:
        o = float(odds)
    except Exception:
        return "unknown"
    if -115 <= o <= 105:
        return "coinflip"
    if o > 105:
        return "dog_live" if o <= 150 else "dog_long"
    return "fav_std" if o >= -175 else "fav_heavy"


def consensus_bucket(n):
    try:
        n = int(n)
    except Exception:
        return "lt3"
    if n >= 5:
        return "5of5"
    if n == 4:
        return "4of5"
    if n == 3:
        return "3of5"
    return "lt3"


def safe_float(x, default=0.0):
    try:
        if x is None or x == "":
            return default
        return float(x)
    except Exception:
        return default


def load_csv(file, fallback_df):
    try:
        if file is None:
            return fallback_df.copy()
        return pd.read_csv(file)
    except Exception:
        return fallback_df.copy()


def default_live_rows():
    return pd.DataFrame(
        [
            {
                "game": "Warriors vs Lakers",
                "market": "moneyline",
                "selection": "Warriors",
                "line": np.nan,
                "book": "FanDuel",
                "odds": -110,
                "consensus_price": -118,
                "consensus_count": 3,
                "sharp_score": 39.5,
                "model_prob": 0.542,
                "book_disagreement": 1,
                "clv_projection": 8.0,
                "rec_notes": "best market price • book disagreement",
                "prev_odds": -115,
                "closing_odds": -110,
            },
            {
                "game": "Warriors vs Lakers",
                "market": "moneyline",
                "selection": "Lakers",
                "line": np.nan,
                "book": "Caesars",
                "odds": 110,
                "consensus_price": 102,
                "consensus_count": 3,
                "sharp_score": 40.3,
                "model_prob": 0.492,
                "book_disagreement": 1,
                "clv_projection": 6.0,
                "rec_notes": "best market price • book disagreement",
                "prev_odds": 105,
                "closing_odds": 110,
            },
            {
                "game": "Warriors vs Lakers",
                "market": "total",
                "selection": "Over",
                "line": 229.5,
                "book": "DraftKings",
                "odds": -102,
                "consensus_price": -109,
                "consensus_count": 3,
                "sharp_score": 39.9,
                "model_prob": 0.521,
                "book_disagreement": 0,
                "clv_projection": 5.0,
                "rec_notes": "best market price",
                "prev_odds": -106,
                "closing_odds": -102,
            },
            {
                "game": "Warriors vs Lakers",
                "market": "spread",
                "selection": "Warriors",
                "line": -3.5,
                "book": "FanDuel",
                "odds": -105,
                "consensus_price": -110,
                "consensus_count": 3,
                "sharp_score": 40.2,
                "model_prob": 0.517,
                "book_disagreement": 0,
                "clv_projection": 3.0,
                "rec_notes": "best market price",
                "prev_odds": -108,
                "closing_odds": -105,
            },
            {
                "game": "Warriors vs Lakers",
                "market": "total",
                "selection": "Under",
                "line": 229.5,
                "book": "FanDuel",
                "odds": -110,
                "consensus_price": -108,
                "consensus_count": 3,
                "sharp_score": 41.9,
                "model_prob": 0.497,
                "book_disagreement": 0,
                "clv_projection": -1.0,
                "rec_notes": "watch only",
                "prev_odds": -110,
                "closing_odds": -110,
            },
            {
                "game": "Warriors vs Lakers",
                "market": "spread",
                "selection": "Lakers",
                "line": 3.5,
                "book": "DraftKings",
                "odds": -108,
                "consensus_price": -106,
                "consensus_count": 3,
                "sharp_score": 41.7,
                "model_prob": 0.496,
                "book_disagreement": 0,
                "clv_projection": 0.0,
                "rec_notes": "watch only",
                "prev_odds": -108,
                "closing_odds": -108,
            },
            {
                "game": "Celtics vs Heat",
                "market": "spread",
                "selection": "Celtics",
                "line": -5.5,
                "book": "FanDuel",
                "odds": -110,
                "consensus_price": -122,
                "consensus_count": 4,
                "sharp_score": 59.2,
                "model_prob": 0.585,
                "book_disagreement": 1,
                "clv_projection": 16.0,
                "rec_notes": "best market price • sharp support",
                "prev_odds": -118,
                "closing_odds": -110,
            },
            {
                "game": "Celtics vs Heat",
                "market": "total",
                "selection": "Under",
                "line": 221.5,
                "book": "Caesars",
                "odds": -105,
                "consensus_price": -111,
                "consensus_count": 4,
                "sharp_score": 54.8,
                "model_prob": 0.551,
                "book_disagreement": 0,
                "clv_projection": 10.0,
                "rec_notes": "best market price",
                "prev_odds": -109,
                "closing_odds": -105,
            },
            {
                "game": "Nuggets vs Suns",
                "market": "moneyline",
                "selection": "Nuggets",
                "line": np.nan,
                "book": "DraftKings",
                "odds": -132,
                "consensus_price": -145,
                "consensus_count": 5,
                "sharp_score": 62.4,
                "model_prob": 0.615,
                "book_disagreement": 1,
                "clv_projection": 20.0,
                "rec_notes": "best market price • consensus support",
                "prev_odds": -138,
                "closing_odds": -132,
            },
            {
                "game": "Nuggets vs Suns",
                "market": "spread",
                "selection": "Suns",
                "line": 4.5,
                "book": "FanDuel",
                "odds": -102,
                "consensus_price": -108,
                "consensus_count": 4,
                "sharp_score": 48.2,
                "model_prob": 0.515,
                "book_disagreement": 0,
                "clv_projection": 2.0,
                "rec_notes": "small edge",
                "prev_odds": -104,
                "closing_odds": -102,
            },
            {
                "game": "Rangers vs Bruins",
                "market": "moneyline",
                "selection": "Bruins",
                "line": np.nan,
                "book": "FanDuel",
                "odds": 118,
                "consensus_price": 105,
                "consensus_count": 4,
                "sharp_score": 57.5,
                "model_prob": 0.492,
                "book_disagreement": 1,
                "clv_projection": 12.0,
                "rec_notes": "dog price value",
                "prev_odds": 112,
                "closing_odds": 118,
            },
        ]
    )


# -----------------------------
# Scoring / classification
# -----------------------------
def add_derived_columns(df):
    df = df.copy()
    if df.empty:
        return df

    if "line" not in df.columns:
        df["line"] = np.nan
    for col in ["book_disagreement", "consensus_count", "sharp_score", "model_prob", "clv_projection"]:
        if col not in df.columns:
            df[col] = 0

    df["edge_pct"] = df.apply(lambda r: implied_edge(r.get("model_prob"), r.get("odds")), axis=1)
    df["consensus_bucket"] = df["consensus_count"].apply(consensus_bucket)
    df["odds_bucket"] = df["odds"].apply(odds_bucket)
    df["market_priority"] = df["market"].map({"moneyline": 3, "spread": 2, "total": 1}).fillna(0)
    df["activation_boost"] = (
        (df["book_disagreement"].fillna(0) * 2.5)
        + np.where(df["consensus_count"].fillna(0) >= 4, 3.0, 0.0)
        + (df["clv_projection"].fillna(0) * 0.35)
    )
    df["score"] = (
        45
        + (df["edge_pct"].fillna(0) * 10.0)
        + (df["sharp_score"].fillna(0) * 0.35)
        + df["activation_boost"].fillna(0)
    ).round(1)

    def label_conflict_key(row):
        line = row.get("line")
        if pd.isna(line):
            line = "ML"
        return f"{row.get('game')}|{row.get('market')}|{line}"

    df["conflict_key"] = df.apply(label_conflict_key, axis=1)
    df["selection_label"] = df.apply(
        lambda r: f"{r['selection']} {r['line']}" if pd.notna(r.get("line")) and str(r.get("market")) != "moneyline" else str(r["selection"]),
        axis=1,
    )
    df["stack_group"] = df["game"].astype(str) + "|" + df["market"].astype(str)
    return df



def assign_tier(row):
    edge = safe_float(row.get("edge_pct"))
    score = safe_float(row.get("score"))
    cons = safe_float(row.get("consensus_count"))
    clv = safe_float(row.get("clv_projection"))
    if edge >= 3.0 and score >= 78 and cons >= 4:
        return "A"
    if edge >= 1.8 and score >= 66:
        return "B"
    if edge >= 0.8 and score >= 54:
        return "C"
    return "Watch"



def add_explainability(row):
    reasons = []
    if safe_float(row.get("edge_pct")) >= 2.0:
        reasons.append("model edge")
    if safe_float(row.get("book_disagreement")) >= 1:
        reasons.append("book disagreement")
    if safe_float(row.get("consensus_count")) >= 4:
        reasons.append(f"{int(row.get('consensus_count', 0))}-book consensus")
    if safe_float(row.get("clv_projection")) >= 8:
        reasons.append("positive CLV projection")
    if safe_float(row.get("sharp_score")) >= 55:
        reasons.append("sharp support")
    if not reasons:
        reasons.append("watch only")
    return " • ".join(reasons[:4])



def compute_stackable(df):
    df = df.copy()
    df["stackable"] = True
    # opposing picks in same market/line are not stackable together
    for _, grp in df.groupby("conflict_key"):
        if len(grp) > 1:
            df.loc[grp.index, "stackable"] = False
    return df



def conflict_resolver(df, keep_per_game=2):
    df = df.copy()
    df["status"] = "Watch"
    df["best_bet_tag"] = ""

    keep_rows = []
    for game, grp in df.groupby("game", dropna=False):
        grp = grp.sort_values(["score", "edge_pct", "market_priority", "consensus_count"], ascending=False)

        selected = []
        used_conflicts = set()
        for idx, row in grp.iterrows():
            ck = row["conflict_key"]
            market = row["market"]
            if ck in used_conflicts:
                continue
            # allow at most one per exact conflict market/line, max keep_per_game total
            if len(selected) < keep_per_game:
                selected.append(idx)
                used_conflicts.add(ck)
                # if moneyline selected, block opposing spread only if same side logic not encoded; exact conflict only here

        if selected:
            best_idx = selected[0]
            df.loc[best_idx, "best_bet_tag"] = "🏆 Best Bet"
            keep_rows.extend(selected)

    df.loc[keep_rows, "status"] = "Active"
    return df



def build_board(df, aggressive=True):
    df = add_derived_columns(df)
    if df.empty:
        return df
    df["tier"] = df.apply(assign_tier, axis=1)
    df["why"] = df.apply(add_explainability, axis=1)
    df = compute_stackable(df)
    df = conflict_resolver(df, keep_per_game=2 if aggressive else 1)

    # force non-qualified low rows to watch
    qualify_mask = (df["tier"].isin(["A", "B", "C"])) & (df["status"] == "Active")
    df.loc[~qualify_mask, "status"] = "Watch"

    unit_base = df["tier"].map({"A": 1.0, "B": 0.5, "C": 0.18, "Watch": 0.05}).fillna(0.05)
    df["units"] = np.where(df["status"].eq("Active"), unit_base, np.minimum(unit_base, 0.05)).round(2)
    df.loc[(df["tier"] == "Watch") & (df["edge_pct"] <= 0), "units"] = 0.0

    df = df.sort_values(["status", "tier", "score", "edge_pct"], ascending=[True, True, False, False]).copy()
    return df


# -----------------------------
# Persistence
# -----------------------------
def ensure_bet_log():
    cols = [
        "timestamp", "game", "market", "selection", "line", "book", "bet_odds", "prev_odds",
        "consensus_price", "consensus_count", "closing_odds", "result", "units", "tier",
        "score", "edge_pct", "status", "why", "auto_logged"
    ]
    if BET_LOG_PATH.exists():
        try:
            return pd.read_csv(BET_LOG_PATH)
        except Exception:
            pass
    return pd.DataFrame(columns=cols)



def save_bet_log(df):
    df.to_csv(BET_LOG_PATH, index=False)



def auto_log_active_plays(board_df):
    log_df = ensure_bet_log()
    if board_df.empty:
        return log_df, 0

    key_cols = ["game", "market", "selection", "book", "bet_odds"]
    if log_df.empty:
        existing = set()
    else:
        existing = set(
            log_df[key_cols].fillna("NA").astype(str).agg("|".join, axis=1).tolist()
        )

    rows_to_add = []
    active = board_df[board_df["status"] == "Active"].copy()
    for _, row in active.iterrows():
        key = "|".join([
            str(row.get("game", "NA")),
            str(row.get("market", "NA")),
            str(row.get("selection", "NA")),
            str(row.get("book", "NA")),
            str(row.get("odds", "NA")),
        ])
        if key in existing:
            continue
        rows_to_add.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "game": row.get("game"),
            "market": row.get("market"),
            "selection": row.get("selection"),
            "line": row.get("line"),
            "book": row.get("book"),
            "bet_odds": row.get("odds"),
            "prev_odds": row.get("prev_odds"),
            "consensus_price": row.get("consensus_price"),
            "consensus_count": row.get("consensus_count"),
            "closing_odds": row.get("closing_odds"),
            "result": None,
            "units": row.get("units"),
            "tier": row.get("tier"),
            "score": row.get("score"),
            "edge_pct": row.get("edge_pct"),
            "status": row.get("status"),
            "why": row.get("why"),
            "auto_logged": True,
        })

    if rows_to_add:
        log_df = pd.concat([log_df, pd.DataFrame(rows_to_add)], ignore_index=True)
        save_bet_log(log_df)
    return log_df, len(rows_to_add)



def profit_from_row(row):
    result = str(row.get("result", "")).lower()
    units = safe_float(row.get("units"), 0)
    odds = safe_float(row.get("bet_odds"), 0)
    if result not in {"win", "loss", "push"}:
        return np.nan
    if result == "push":
        return 0.0
    if result == "loss":
        return -units
    if odds > 0:
        return units * (odds / 100)
    return units * (100 / abs(odds)) if odds != 0 else 0.0



def build_learning_profile(log_df):
    if log_df.empty:
        combos = []
        for market in ["moneyline", "spread", "total"]:
            for o in ["coinflip", "dog_live", "dog_long", "fav_std", "fav_heavy"]:
                for c in ["3of5", "4of5", "5of5", "lt3"]:
                    combos.append({"market": market, "odds_bucket": o, "consensus_bucket": c, "bets": 0, "wins": 0, "win_rate": 0.0})
        return pd.DataFrame(combos)

    temp = log_df.copy()
    temp["market"] = temp["market"].fillna("unknown")
    temp["odds_bucket"] = temp["bet_odds"].apply(odds_bucket)
    temp["consensus_bucket"] = temp["consensus_count"].apply(consensus_bucket)
    temp["is_win"] = temp["result"].astype(str).str.lower().eq("win").astype(int)
    settled = temp[temp["result"].astype(str).str.lower().isin(["win", "loss", "push"])].copy()

    if settled.empty:
        grouped = temp.groupby(["market", "odds_bucket", "consensus_bucket"], dropna=False).size().reset_index(name="bets")
        grouped["wins"] = 0
        grouped["win_rate"] = 0.0
        return grouped

    grouped = (
        settled.groupby(["market", "odds_bucket", "consensus_bucket"], dropna=False)
        .agg(bets=("result", "count"), wins=("is_win", "sum"))
        .reset_index()
    )
    grouped["win_rate"] = np.where(grouped["bets"] > 0, grouped["wins"] / grouped["bets"], 0.0)
    return grouped.sort_values(["market", "consensus_bucket", "odds_bucket"]).reset_index(drop=True)


# -----------------------------
# UI helpers
# -----------------------------
def inject_css():
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.3rem; padding-bottom: 2rem; max-width: 1100px;}
        .summary-card, .play-card {
            border: 1px solid rgba(49,51,63,0.18);
            border-radius: 20px;
            padding: 16px 18px;
            margin-bottom: 14px;
            background: rgba(255,255,255,0.02);
        }
        .summary-title {font-size: 1.05rem; font-weight: 700; margin-bottom: 8px;}
        .stat-label {font-size: 0.95rem; opacity: 0.8;}
        .stat-value {font-size: 1.2rem; font-weight: 700;}
        .play-title {font-size: 1.18rem; font-weight: 800; margin-bottom: 2px;}
        .play-sub {font-size: 0.98rem; opacity: 0.85; margin-bottom: 10px;}
        .pill {
            display:inline-block; padding: 4px 10px; border-radius: 999px;
            font-size: 0.9rem; font-weight: 700; margin-right: 6px; margin-bottom: 4px;
            background: rgba(120,120,120,0.12);
        }
        .pill-a {background: rgba(16,185,129,0.16);}
        .pill-b {background: rgba(59,130,246,0.14);}
        .pill-c {background: rgba(245,158,11,0.14);}
        .pill-watch {background: rgba(148,163,184,0.18);}
        .pill-active {background: rgba(245,158,11,0.16);}
        .pill-best {background: rgba(168,85,247,0.16);}
        .why {font-size: 0.95rem; opacity: 0.82; margin-top: 8px;}
        .section-h {font-size: 2.0rem; font-weight: 800; margin-top: 18px; margin-bottom: 12px;}
        @media (max-width: 768px) {
            .section-h {font-size: 1.4rem;}
            .play-title {font-size: 1.05rem;}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )



def pill_class(value):
    mapping = {"A": "pill-a", "B": "pill-b", "C": "pill-c", "Watch": "pill-watch"}
    return mapping.get(str(value), "pill-watch")



def render_summary(board_df, mode_label):
    live_rows = len(board_df)
    qualified = int(((board_df["status"] == "Active") & (board_df["tier"] != "Watch")).sum()) if not board_df.empty else 0
    watchlist = int((board_df["status"] != "Active").sum()) if not board_df.empty else 0
    tier_counts = board_df["tier"].value_counts().to_dict() if not board_df.empty else {}
    avg_edge = board_df.loc[board_df["status"] == "Active", "edge_pct"].mean() if not board_df.empty else 0

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f"""
            <div class='summary-card'>
                <div class='summary-title'>Market Snapshot</div>
                <div class='stat-label'>Live Rows: <span class='stat-value'>{live_rows}</span></div>
                <div class='stat-label'>Watchlist: <span class='stat-value'>{watchlist}</span></div>
                <div class='stat-label'>Qualified: <span class='stat-value'>{qualified}</span></div>
                <div class='stat-label'>Mode: <span class='stat-value'>{mode_label}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
            <div class='summary-card'>
                <div class='summary-title'>Tier Summary</div>
                <div class='stat-label'>Tier A: <span class='stat-value'>{tier_counts.get('A', 0)}</span></div>
                <div class='stat-label'>Tier B: <span class='stat-value'>{tier_counts.get('B', 0)}</span></div>
                <div class='stat-label'>Tier C: <span class='stat-value'>{tier_counts.get('C', 0)}</span></div>
                <div class='stat-label'>Avg Edge: <span class='stat-value'>{0 if pd.isna(avg_edge) else avg_edge:.2f}%</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )



def render_play_cards(df, title, active_only=False, limit=None):
    st.markdown(f"<div class='section-h'>{title}</div>", unsafe_allow_html=True)
    if df.empty:
        st.info("No rows to show.")
        return
    rows = df.copy()
    if active_only:
        rows = rows[rows["status"] == "Active"]
    if limit:
        rows = rows.head(limit)
    if rows.empty:
        st.info("No rows to show.")
        return

    for i, (_, row) in enumerate(rows.iterrows(), start=1):
        title_line = row["selection_label"]
        if pd.isna(row.get("line")) and row.get("market") == "total":
            title_line = str(row.get("selection"))
        best = row.get("best_bet_tag", "")
        badge_html = (
            f"<span class='pill {pill_class(row['tier'])}'>Tier {row['tier']}</span>"
            f"<span class='pill {'pill-active' if row['status']=='Active' else 'pill-watch'}'>{row['status']}</span>"
        )
        if best:
            badge_html += f"<span class='pill pill-best'>{best}</span>"
        st.markdown(
            f"""
            <div class='play-card'>
                <div>{badge_html}</div>
                <div class='play-title'>#{i} {title_line}</div>
                <div class='play-sub'>{row['game']}</div>
                <div style='display:grid;grid-template-columns:1fr 1fr;gap:8px;'>
                    <div>Book: <b>{row['book']}</b></div>
                    <div>Odds: <b>{int(row['odds']) if not pd.isna(row['odds']) else ''}</b></div>
                    <div>Units: <b>{safe_float(row['units']):.2f}u</b></div>
                    <div>Score: <b>{safe_float(row['score']):.1f}</b></div>
                    <div>Sharp: <b>{safe_float(row['sharp_score']):.1f}</b></div>
                    <div>Edge: <b>{safe_float(row['edge_pct']):.2f}%</b></div>
                    <div>Consensus: <b>{int(safe_float(row['consensus_count']))} books</b></div>
                    <div>Stackable: <b>{'Yes' if bool(row['stackable']) else 'No'}</b></div>
                </div>
                <div class='why'>{row['why']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# -----------------------------
# App body
# -----------------------------
inject_css()
st.title(APP_TITLE)
st.caption(APP_SUBTITLE)

with st.sidebar:
    st.header("V28 Controls")
    aggressive = st.toggle("Aggressive mode", value=True)
    auto_log = st.toggle("Auto-log active plays", value=True)
    keep_per_game = st.selectbox("Max active plays per game", [1, 2, 3], index=1)
    st.caption("Upload a CSV with live rows to replace the demo feed.")
    upload = st.file_uploader("Live rows CSV", type=["csv"])

raw_df = load_csv(upload, default_live_rows())
board_df = add_derived_columns(raw_df)
board_df = board_df.copy()
board_df = compute_stackable(board_df)
board_df = conflict_resolver(board_df, keep_per_game=keep_per_game)
board_df["tier"] = board_df.apply(assign_tier, axis=1)
board_df["why"] = board_df.apply(add_explainability, axis=1)
board_df = build_board(board_df, aggressive=aggressive)

render_summary(board_df, "Aggressive" if aggressive else "Standard")

with st.expander("🎛️ Adaptive Thresholds"):
    st.write("Execution engine logic:")
    st.write("• Resolves conflicting plays in the same game/market")
    st.write("• Tags one best bet per game")
    st.write("• Allows stackable plays only when they do not directly conflict")
    st.write("• Promotes tiers dynamically based on score, edge, consensus, and CLV")

active_df = board_df[(board_df["status"] == "Active") & (board_df["tier"] != "Watch")].copy()
watch_df = board_df[board_df["status"] != "Active"].copy()

render_play_cards(active_df, "🎯 Compact Top Plays", active_only=False)
render_play_cards(watch_df, "👀 Compact Watchlist", active_only=False)

st.markdown("<div class='section-h'>✅ Quick Table</div>", unsafe_allow_html=True)
quick_cols = [
    "tier", "status", "game", "market", "selection_label", "book", "odds", "units",
    "score", "edge_pct", "consensus_count", "best_bet_tag", "stackable"
]
st.dataframe(board_df[quick_cols].rename(columns={"selection_label": "selection"}), use_container_width=True, hide_index=True)

with st.expander("📊 Full Scored Rows"):
    st.dataframe(board_df, use_container_width=True, hide_index=True)

with st.expander("🛰️ Raw Live Rows"):
    st.dataframe(raw_df, use_container_width=True, hide_index=True)

if auto_log:
    bet_log_df, added_count = auto_log_active_plays(board_df)
    if added_count:
        st.success(f"Auto-logged {added_count} new active play(s).")
else:
    bet_log_df = ensure_bet_log()

st.markdown("<div class='section-h'>📝 Bet Log + Grading</div>", unsafe_allow_html=True)

with st.form("manual_bet_form"):
    c1, c2 = st.columns(2)
    with c1:
        game = st.text_input("Game", value="")
        market = st.selectbox("Market", ["moneyline", "spread", "total"], index=0)
        selection = st.text_input("Selection", value="")
        line = st.text_input("Line", value="")
        units = st.number_input("Units", min_value=0.0, step=0.05, value=0.0)
    with c2:
        book = st.text_input("Book", value="DraftKings")
        bet_odds = st.number_input("Bet Odds", step=1, value=-110)
        prev_odds = st.number_input("Previous Odds", step=1, value=-110)
        consensus_price = st.number_input("Consensus Price", step=1, value=-110)
        consensus_count = st.slider("Consensus Count", 1, 5, 3)
        closing_odds = st.number_input("Closing Odds", step=1, value=-110)
        result = st.selectbox("Result", ["", "win", "loss", "push"], index=0)

    submitted = st.form_submit_button("Add / Grade Bet")
    if submitted:
        new_row = pd.DataFrame([
            {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "game": game,
                "market": market,
                "selection": selection,
                "line": line if line != "" else np.nan,
                "book": book,
                "bet_odds": bet_odds,
                "prev_odds": prev_odds,
                "consensus_price": consensus_price,
                "consensus_count": consensus_count,
                "closing_odds": closing_odds,
                "result": result if result else None,
                "units": units,
                "tier": None,
                "score": None,
                "edge_pct": None,
                "status": "Manual",
                "why": "manual entry",
                "auto_logged": False,
            }
        ])
        bet_log_df = pd.concat([bet_log_df, new_row], ignore_index=True)
        save_bet_log(bet_log_df)
        st.success("Bet added to log.")

if not bet_log_df.empty:
    bet_log_df["profit"] = bet_log_df.apply(profit_from_row, axis=1)
    settled = bet_log_df[bet_log_df["result"].astype(str).str.lower().isin(["win", "loss", "push"])].copy()
    settled_bets = len(settled)
    wins = int(settled["result"].astype(str).str.lower().eq("win").sum()) if settled_bets else 0
    win_rate = (wins / settled_bets) if settled_bets else 0.0
    net_units = settled["profit"].sum() if settled_bets else 0.0

    clv_vals = []
    for _, r in settled.iterrows():
        bo = safe_float(r.get("bet_odds"), np.nan)
        co = safe_float(r.get("closing_odds"), np.nan)
        if not pd.isna(bo) and not pd.isna(co):
            clv_vals.append(american_to_prob(bo) - american_to_prob(co))
    avg_clv = (np.nanmean(clv_vals) * 100) if clv_vals else np.nan
else:
    settled_bets = 0
    win_rate = 0.0
    net_units = 0.0
    avg_clv = np.nan

m1, m2, m3, m4 = st.columns(4)
m1.metric("Settled Bets", settled_bets)
m2.metric("Win Rate", f"{win_rate*100:.1f}%")
m3.metric("Net Units", f"{net_units:.2f}u")
m4.metric("Avg CLV", "—" if pd.isna(avg_clv) else f"{avg_clv:.2f}%")

st.dataframe(bet_log_df, use_container_width=True, hide_index=True)

profile_df = build_learning_profile(bet_log_df)
profile_df.to_csv(LEARNING_PROFILE_PATH, index=False)
board_df.to_csv(SNAPSHOT_PATH, index=False)

st.markdown("<div class='section-h'>🧠 Adaptive Learning Profile</div>", unsafe_allow_html=True)
st.dataframe(profile_df, use_container_width=True, hide_index=True)

st.markdown("<div class='section-h'>💾 Export</div>", unsafe_allow_html=True)

bet_buf = io.BytesIO()
profile_buf = io.BytesIO()
snap_buf = io.BytesIO()

bet_log_df.to_csv(bet_buf, index=False)
profile_df.to_csv(profile_buf, index=False)
board_df.to_csv(snap_buf, index=False)

st.download_button("Download Bet Log CSV", bet_buf.getvalue(), file_name="bet_log.csv", mime="text/csv")
st.download_button("Download Learning Profile CSV", profile_buf.getvalue(), file_name="learning_profile.csv", mime="text/csv")
st.download_button("Download Snapshot CSV", snap_buf.getvalue(), file_name="snapshot.csv", mime="text/csv")

st.caption(
    "V28 adds conflict resolution, best-bet tagging, stackability logic, dynamic tier promotion, explainability notes, and auto-log execution tracking."
)
