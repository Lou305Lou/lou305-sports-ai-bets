import io
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Sports Betting AI Dashboard V28.3", layout="wide")

APP_TITLE = "🔥 Sports Betting AI Dashboard V28.3"
APP_SUBTITLE = "Profit Optimization Engine"
BET_LOG_PATH = Path("bet_log.csv")
LEARNING_PROFILE_PATH = Path("learning_profile.csv")
SNAPSHOT_PATH = Path("snapshot.csv")

MIN_ACTIVE_EDGE = 1.75
MAX_BEST_BETS = 3
MAX_TIER_A = 3
MAX_ACTIVE_PLAYS = 3
MAX_TOTAL_UNITS = 3.5
SCORE_CAP = 100.0


# -----------------------------
# Math helpers
# -----------------------------
def safe_float(x, default=0.0):
    try:
        if x is None or x == "":
            return default
        return float(x)
    except Exception:
        return default


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
    return (float(model_prob) - float(market_prob)) * 100.0


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


# -----------------------------
# Data loading
# -----------------------------
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
                "prev_odds": 112,
                "closing_odds": 118,
            },
        ]
    )


# -----------------------------
# Board building
# -----------------------------
def prepare_rows(df):
    df = df.copy()
    if df.empty:
        return df

    for col in ["line", "consensus_price", "consensus_count", "sharp_score", "model_prob", "book_disagreement", "clv_projection", "prev_odds", "closing_odds"]:
        if col not in df.columns:
            df[col] = np.nan

    df["edge_pct"] = df.apply(lambda r: implied_edge(r.get("model_prob"), r.get("odds")), axis=1)
    df["odds_bucket"] = df["odds"].apply(odds_bucket)
    df["consensus_bucket"] = df["consensus_count"].apply(consensus_bucket)
    df["market_priority"] = df["market"].map({"moneyline": 3, "spread": 2, "total": 1}).fillna(0)
    df["consensus_boost"] = np.where(df["consensus_count"].fillna(0) >= 5, 14, np.where(df["consensus_count"].fillna(0) >= 4, 9, np.where(df["consensus_count"].fillna(0) >= 3, 4, 0)))
    df["clv_boost"] = np.clip(df["clv_projection"].fillna(0), -5, 20) * 0.7
    df["disagreement_boost"] = df["book_disagreement"].fillna(0) * 6.5
    df["sharp_component"] = np.clip((df["sharp_score"].fillna(0) - 35) * 1.35, 0, 40)
    df["edge_component"] = np.clip(df["edge_pct"].fillna(0) * 11.5, -20, 45)
    df["raw_score"] = 26 + df["edge_component"] + df["sharp_component"] + df["consensus_boost"] + df["clv_boost"] + df["disagreement_boost"]
    max_raw = max(float(df["raw_score"].max()), 1.0)
    min_raw = float(df["raw_score"].min())
    spread = max(max_raw - min_raw, 1.0)
    normalized = 35 + ((df["raw_score"] - min_raw) / spread) * 65
    df["score"] = np.clip(normalized, 0, SCORE_CAP).round(1)

    def conflict_key(row):
        line = row.get("line")
        if pd.isna(line):
            line = "ML"
        return f"{row.get('game')}|{row.get('market')}|{line}"

    df["conflict_key"] = df.apply(conflict_key, axis=1)
    df["selection_label"] = df.apply(
        lambda r: f"{r['selection']} {r['line']}" if pd.notna(r.get("line")) and str(r.get("market")) != "moneyline" else str(r["selection"]),
        axis=1,
    )
    return df


def assign_tier(row):
    edge = safe_float(row.get("edge_pct"))
    score = safe_float(row.get("score"))
    consensus = safe_float(row.get("consensus_count"))
    if edge >= 3.0 and score >= 86 and consensus >= 4:
        return "A"
    if edge >= 1.8 and score >= 74:
        return "B"
    if edge >= 1.0 and score >= 62:
        return "C"
    return "Watch"


def correlation_tag(row):
    market = str(row.get("market", ""))
    selection = str(row.get("selection", "")).lower()
    line = row.get("line")

    if market == "total":
        return "Neutral"
    if market == "spread":
        if (not pd.isna(line)) and safe_float(line) < 0:
            return "Favorite side"
        if (not pd.isna(line)) and safe_float(line) > 0:
            return "Dog side"
    if market == "moneyline":
        odds = safe_float(row.get("odds"))
        return "Favorite side" if odds < 0 else "Dog side"
    return "Neutral"




def confidence_label(row):
    score = safe_float(row.get("score"))
    if score >= 90:
        return "Elite"
    if score >= 75:
        return "High"
    if score >= 60:
        return "Medium"
    return "Low"

def explainability(row):
    reasons = []
    if safe_float(row.get("edge_pct")) >= 2.0:
        reasons.append("model edge")
    if safe_float(row.get("book_disagreement")) >= 1:
        reasons.append("book disagreement")
    if safe_float(row.get("consensus_count")) >= 4:
        reasons.append(f"{int(safe_float(row.get('consensus_count')))}-book consensus")
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
    for _, grp in df.groupby("conflict_key"):
        if len(grp) > 1:
            df.loc[grp.index, "stackable"] = False
    return df


def final_rank_score(row):
    edge = max(0.0, safe_float(row.get("edge_pct")))
    clv = max(0.0, safe_float(row.get("clv_projection")))
    consensus = min(5.0, max(0.0, safe_float(row.get("consensus_count"))))
    score = (edge * 0.5) + (clv * 0.3) + (consensus * 0.2)
    return round(score, 3)


def apply_correlation_risk_adjustment(df):
    df = df.copy()
    active_idx = df.index[df["status"].eq("Active")].tolist()
    if not active_idx:
        return df

    for game, grp in df.loc[active_idx].groupby("game", dropna=False):
        if len(grp) <= 1:
            continue
        positive_mask = grp["correlation"].isin(["Favorite side", "Dog side"])
        if positive_mask.any():
            idxs = grp.index[positive_mask]
            df.loc[idxs, "units"] = (df.loc[idxs, "units"] * 0.80).round(2)
            df.loc[idxs, "why"] = df.loc[idxs, "why"].astype(str) + " • correlation risk adjusted"
    return df


def apply_variance_control(df, max_total_units=MAX_TOTAL_UNITS):
    df = df.copy()
    active_mask = df["status"].eq("Active")
    total_units = safe_float(df.loc[active_mask, "units"].sum())
    if total_units > max_total_units and total_units > 0:
        scale = max_total_units / total_units
        df.loc[active_mask, "units"] = (df.loc[active_mask, "units"] * scale).round(2)
        df.loc[active_mask, "why"] = df.loc[active_mask, "why"].astype(str) + " • variance scaled"
    return df


def dynamic_units(row):
    tier = str(row.get("tier"))
    status = str(row.get("status"))
    edge = safe_float(row.get("edge_pct"))
    score = safe_float(row.get("score"))

    if status != "Active":
        return 0.05 if edge > 0 else 0.00

    if tier == "A":
        units = 0.75 + min(0.50, max(0.0, (edge - 3.0) * 0.12) + max(0.0, (score - 86.0) * 0.01))
        return round(min(1.25, units), 2)
    if tier == "B":
        units = 0.40 + min(0.35, max(0.0, (edge - 1.8) * 0.10) + max(0.0, (score - 74.0) * 0.008))
        return round(min(0.75, units), 2)
    if tier == "C":
        units = 0.10 + min(0.30, max(0.0, (edge - 1.0) * 0.08) + max(0.0, (score - 62.0) * 0.006))
        return round(min(0.40, units), 2)
    return 0.00


def resolve_board(
    df,
    aggressive=True,
    keep_per_game=2,
    best_bet_cap=MAX_BEST_BETS,
    max_tier_a=MAX_TIER_A,
    skip_games_without_ab=True,
    elite_only=False,
    max_active_plays=MAX_ACTIVE_PLAYS,
    max_total_units=MAX_TOTAL_UNITS,
):
    df = prepare_rows(df)
    if df.empty:
        return df

    df["tier"] = df.apply(assign_tier, axis=1)
    tier_a_rank = df[df["tier"].eq("A")].sort_values(["score", "edge_pct", "consensus_count"], ascending=False)
    if len(tier_a_rank) > max_tier_a:
        demote_idxs = tier_a_rank.iloc[max_tier_a:].index
        df.loc[demote_idxs, "tier"] = "B"

    df["why"] = df.apply(explainability, axis=1)
    df["correlation"] = df.apply(correlation_tag, axis=1)
    df = compute_stackable(df)
    df["final_rank"] = df.apply(final_rank_score, axis=1)
    df["status"] = "Watch"
    df["best_bet_tag"] = ""
    df["skip_game"] = False

    candidates = df[(df["tier"].isin(["A", "B", "C"])) & (df["edge_pct"].fillna(-999) >= MIN_ACTIVE_EDGE)].copy()
    if elite_only:
        candidates = candidates[candidates["tier"].isin(["A", "B"]) & (candidates["score"] >= 75)].copy()

    max_per_game = keep_per_game if aggressive else 1
    chosen = []

    for game, grp in candidates.groupby("game", dropna=False):
        grp = grp.sort_values(["final_rank", "score", "edge_pct", "consensus_count", "market_priority"], ascending=False)

        game_has_ab = grp["tier"].isin(["A", "B"]).any()
        max_game_clv = safe_float(grp["clv_projection"].max())
        max_game_consensus = safe_float(grp["consensus_count"].max())
        if skip_games_without_ab and ((not game_has_ab) or (max_game_clv < 4.0) or (max_game_consensus < 3)):
            df.loc[df["game"].eq(game), "skip_game"] = True
            df.loc[df["game"].eq(game), "why"] = "skip game • weak game quality"
            continue

        used_conflicts = set()
        game_selected = []
        for idx, row in grp.iterrows():
            if len(game_selected) >= max_per_game:
                break
            if row["conflict_key"] in used_conflicts:
                continue
            game_selected.append(idx)
            used_conflicts.add(row["conflict_key"])

        chosen.extend(game_selected)

    if chosen:
        ranked_all = df.loc[chosen].sort_values(["final_rank", "score", "edge_pct", "clv_projection", "consensus_count"], ascending=False)
        chosen = ranked_all.head(max_active_plays).index.tolist()

    df.loc[chosen, "status"] = "Active"

    if chosen:
        best_pool = df.loc[chosen].sort_values(["final_rank", "score", "edge_pct", "clv_projection", "consensus_count"], ascending=False)
        for idx in best_pool.head(best_bet_cap).index:
            df.loc[idx, "best_bet_tag"] = "🏆 Best Bet"

    df.loc[df["edge_pct"].fillna(-999) < MIN_ACTIVE_EDGE, "status"] = "Watch"
    df.loc[df["skip_game"], "status"] = "Watch"

    df["units"] = df.apply(dynamic_units, axis=1)
    df = apply_correlation_risk_adjustment(df)
    df = apply_variance_control(df, max_total_units=max_total_units)
    df["confidence"] = df.apply(confidence_label, axis=1)

    watch_mask = df["status"].eq("Watch")
    df.loc[watch_mask & (df["why"] == "watch only"), "why"] = "watch only"

    tier_sort = {"A": 0, "B": 1, "C": 2, "Watch": 3}
    df["tier_sort"] = df["tier"].map(tier_sort).fillna(9)
    df["status_sort"] = np.where(df["status"].eq("Active"), 0, 1)
    df = df.sort_values(["status_sort", "tier_sort", "final_rank", "score", "edge_pct"], ascending=[True, True, False, False, False]).drop(columns=["tier_sort", "status_sort"])
    return df.reset_index(drop=True)




def parlay_payout_multiplier(odds):
    odds = safe_float(odds, 0)
    if odds > 0:
        return 1 + (odds / 100.0)
    if odds < 0:
        return 1 + (100.0 / abs(odds))
    return 1.0


def payout_to_american(mult):
    mult = safe_float(mult, 1.0)
    if mult <= 1:
        return 0
    profit = mult - 1
    if profit >= 1:
        return int(round(profit * 100))
    return int(round(-100 / profit))


def build_ai_bet_slip(board_df):
    active = board_df[
        (board_df["status"] == "Active")
        & (board_df["tier"].isin(["A", "B"]))
        & (board_df["clv_projection"].fillna(0) >= 8)
    ].copy()
    if active.empty:
        return None

    active = active.sort_values(["final_rank", "score", "edge_pct", "clv_projection", "consensus_count"], ascending=False)

    picks = []
    used_games = set()
    used_conflicts = set()
    used_correlations = []

    for _, row in active.iterrows():
        if row["game"] in used_games:
            continue
        if row["conflict_key"] in used_conflicts:
            continue
        if not bool(row.get("stackable", False)) and picks:
            continue
        corr = str(row.get("correlation", "Neutral"))
        if corr != "Neutral" and corr in used_correlations:
            continue
        picks.append(row)
        used_games.add(row["game"])
        used_conflicts.add(row["conflict_key"])
        if corr != "Neutral":
            used_correlations.append(corr)
        if len(picks) >= 2:
            break

    if not picks:
        return None

    mult = 1.0
    min_score = 999.0
    for row in picks:
        mult *= parlay_payout_multiplier(row["odds"])
        min_score = min(min_score, safe_float(row["score"], 0))

    parlay_odds = payout_to_american(mult) if len(picks) >= 2 else int(safe_float(picks[0]["odds"], 0))

    if min_score >= 90:
        slip_conf = "Elite"
    elif min_score >= 75:
        slip_conf = "High"
    elif min_score >= 60:
        slip_conf = "Medium"
    else:
        slip_conf = "Low"

    return {
        "picks": picks,
        "parlay_odds": parlay_odds,
        "confidence": slip_conf,
        "stackable_ok": len(picks) >= 2,
        "risk_level": "Controlled" if len(picks) >= 2 else "Low",
    }

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
    key_cols = ["game", "market", "selection", "book", "bet_odds"]
    existing = set()
    if not log_df.empty:
        existing = set(log_df[key_cols].fillna("NA").astype(str).agg("|".join, axis=1).tolist())

    rows_to_add = []
    for _, row in board_df[board_df["status"] == "Active"].iterrows():
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
        return pd.DataFrame(columns=["market", "odds_bucket", "consensus_bucket", "bets", "wins", "win_rate"])

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
        return grouped.sort_values(["market", "consensus_bucket", "odds_bucket"]).reset_index(drop=True)

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
    return {"A": "pill-a", "B": "pill-b", "C": "pill-c", "Watch": "pill-watch"}.get(str(value), "pill-watch")


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


def render_play_cards(df, title):
    st.markdown(f"<div class='section-h'>{title}</div>", unsafe_allow_html=True)
    if df.empty:
        st.info("No rows to show.")
        return

    for i, (_, row) in enumerate(df.iterrows(), start=1):
        badge_html = (
            f"<span class='pill {pill_class(row['tier'])}'>Tier {row['tier']}</span>"
            f"<span class='pill {'pill-active' if row['status']=='Active' else 'pill-watch'}'>{row['status']}</span>"
        )
        if row.get("best_bet_tag"):
            badge_html += f"<span class='pill pill-best'>{row['best_bet_tag']}</span>"

        st.markdown(
            f"""
            <div class='play-card'>
                <div>{badge_html}</div>
                <div class='play-title'>#{i} {row['selection_label']}</div>
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
                    <div>Confidence: <b>{row['confidence']}</b></div>
                    <div>Correlation: <b>{row['correlation']}</b></div>
                    <div>CLV Proj: <b>{safe_float(row['clv_projection']):.1f}</b></div>
                    <div>Skip Game: <b>{'Yes' if bool(row.get('skip_game', False)) else 'No'}</b></div>
                </div>
                <div class='why'>{row['why']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# -----------------------------
# App
# -----------------------------
inject_css()
st.title(APP_TITLE)
st.caption(APP_SUBTITLE)

with st.sidebar:
    st.header("V28.3 Controls")
    aggressive = st.toggle("Aggressive mode", value=True)
    auto_log = st.toggle("Auto-log active plays", value=True)
    elite_only = st.toggle("Elite plays only", value=False)
    keep_per_game = st.selectbox("Max active plays per game", [1, 2, 3], index=1)
    max_active_plays = st.selectbox("Max total active plays", [2, 3, 4, 5], index=1)
    best_bet_cap = st.selectbox("Max best bets on slate", [1, 2, 3], index=1)
    max_tier_a = st.selectbox("Max Tier A plays", [1, 2, 3, 4], index=2)
    max_total_units = st.selectbox("Max total slate units", [2.5, 3.0, 3.5, 4.0], index=2)
    skip_games_without_ab = st.toggle("Skip weak games", value=True)
    st.caption("Upload a CSV with live rows to replace the demo feed.")
    upload = st.file_uploader("Live rows CSV", type=["csv"])

raw_df = load_csv(upload, default_live_rows())
board_df = resolve_board(raw_df, aggressive=aggressive, keep_per_game=keep_per_game, best_bet_cap=best_bet_cap, max_tier_a=max_tier_a, skip_games_without_ab=skip_games_without_ab, elite_only=elite_only, max_active_plays=max_active_plays, max_total_units=max_total_units)

render_summary(board_df, "Aggressive" if aggressive else "Standard")

with st.expander("🎛️ Adaptive Thresholds"):
    st.write(f"• Minimum active edge: {MIN_ACTIVE_EDGE:.2f}%")
    st.write(f"• Best bet cap: {best_bet_cap}")
    st.write(f"• Max Tier A plays: {max_tier_a}")
    st.write(f"• Max active plays: {max_active_plays}")
    st.write(f"• Max total units: {max_total_units:.1f}u")
    st.write(f"• Elite only mode: {'On' if elite_only else 'Off'}")
    st.write("• Ranking weights: edge 50% • CLV 30% • consensus 20%")
    st.write("• Positive same-game correlation triggers unit reduction")
    st.write(f"• Skip weak games: {'On' if skip_games_without_ab else 'Off'}")

active_df = board_df[(board_df["status"] == "Active") & (board_df["tier"] != "Watch")].copy()
watch_df = board_df[board_df["status"] != "Active"].copy()

render_play_cards(active_df, "🎯 Compact Top Plays")
render_play_cards(watch_df, "👀 Compact Watchlist")


slip = build_ai_bet_slip(board_df)
if slip:
    st.markdown("<div class='section-h'>🎯 AI Bet Slip</div>", unsafe_allow_html=True)
    lines = []
    for i, row in enumerate(slip["picks"], start=1):
        lines.append(f"{i}. {row['selection_label']} ({row['game']})")
    slip_text = "<br>".join(lines)
    parlay_display = f"+{slip['parlay_odds']}" if slip['parlay_odds'] > 0 else str(slip['parlay_odds'])
    st.markdown(f"""
        <div class='summary-card'>
            <div class='summary-title'>Recommended Slip</div>
            <div class='stat-label'>{slip_text}</div>
            <div class='stat-label' style='margin-top:8px;'>Projected Odds: <span class='stat-value'>{parlay_display}</span></div>
            <div class='stat-label'>Confidence: <span class='stat-value'>{slip['confidence']}</span></div>
            <div class='stat-label'>Type: <span class='stat-value'>{'Parlay' if slip['stackable_ok'] else 'Single best bet'}</span></div>
            <div class='stat-label'>Risk Level: <span class='stat-value'>{slip['risk_level']}</span></div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<div class='section-h'>✅ Quick Table</div>", unsafe_allow_html=True)
quick_cols = [
    "tier", "status", "game", "market", "selection_label", "book", "odds", "units",
    "score", "final_rank", "edge_pct", "clv_projection", "confidence", "consensus_count", "best_bet_tag", "stackable", "correlation", "skip_game"
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
m2.metric("Win Rate", f"{win_rate * 100:.1f}%")
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
    "V28.3 adds CLV-weighted ranking, elite-only mode, overbet protection, correlation risk adjustment, variance control, and a smarter AI bet slip builder."
)
