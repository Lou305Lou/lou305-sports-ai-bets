
# streamlit_app_v24.py
# V24 Auto Mode - Sports Betting AI Dashboard
#
# This version upgrades the toy V23 structure into a more decision-oriented app:
# - auto bet filtering
# - self-learning weight adjustments by market / odds bucket / consensus tier
# - sharp money score
# - market inefficiency scoring
# - auto-generated top plays
# - bankroll-based unit sizing
# - bet log persistence (CSV import/export)
#
# Note:
# This is still a local dashboard framework. It does not fetch live sportsbook APIs by itself.
# You can load your own candidate plays CSV and let the app score, filter, and rank them.

import io
import math
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd
import streamlit as st


# ------------------------------------------------------------
# Page setup
# ------------------------------------------------------------
st.set_page_config(
    page_title="Sports Betting AI Dashboard V24 Auto Mode",
    layout="wide",
)

st.title("🔥 Sports Betting AI Dashboard V24")
st.caption("Auto Mode: score → filter → size → rank top plays")


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
DATA_DIR = Path(".")
BET_LOG_PATH = DATA_DIR / "bet_log_v24.csv"
MODEL_PROFILE_PATH = DATA_DIR / "model_profile_v24.csv"


def safe_read_csv(path: Path, fallback: pd.DataFrame) -> pd.DataFrame:
    try:
        if path.exists():
            return pd.read_csv(path)
    except Exception:
        pass
    return fallback.copy()


def safe_save_csv(df: pd.DataFrame, path: Path) -> None:
    try:
        df.to_csv(path, index=False)
    except Exception:
        pass


def american_to_implied_prob(odds: float) -> float:
    try:
        odds = float(odds)
        if odds > 0:
            return 100.0 / (odds + 100.0)
        return abs(odds) / (abs(odds) + 100.0)
    except Exception:
        return np.nan


def american_to_decimal(odds: float) -> float:
    try:
        odds = float(odds)
        if odds > 0:
            return 1 + odds / 100.0
        return 1 + 100.0 / abs(odds)
    except Exception:
        return np.nan


def odds_bucket(odds: float) -> str:
    try:
        odds = float(odds)
    except Exception:
        return "unknown"

    if odds <= -200:
        return "fav_heavy"
    if -199 <= odds <= -121:
        return "fav_std"
    if -120 <= odds <= 100:
        return "coinflip"
    if 101 <= odds <= 150:
        return "dog_live"
    return "dog_long"


def consensus_bucket(consensus_count: int) -> str:
    try:
        x = int(consensus_count)
    except Exception:
        return "unknown"

    if x >= 5:
        return "5of5"
    if x == 4:
        return "4of5"
    if x == 3:
        return "3of5"
    return "lt3"


def normalize_0_100(value: float, min_v: float, max_v: float) -> float:
    if max_v <= min_v:
        return 50.0
    pct = (value - min_v) / (max_v - min_v)
    return float(np.clip(pct * 100.0, 0.0, 100.0))


def kelly_fraction(win_prob: float, odds: float) -> float:
    """
    Kelly fraction for decimal payout net odds.
    Returns raw fraction of bankroll.
    """
    try:
        dec = american_to_decimal(odds)
        if np.isnan(dec):
            return 0.0
        b = dec - 1.0
        p = float(win_prob)
        q = 1.0 - p
        if b <= 0:
            return 0.0
        frac = (b * p - q) / b
        return max(0.0, frac)
    except Exception:
        return 0.0


def infer_side_from_movement(open_odds: float, current_odds: float) -> float:
    """
    Simple line movement signal:
    More negative current odds than open odds = steam toward this side.
    Positive score means movement supports the side.
    """
    try:
        return float(open_odds) - float(current_odds)
    except Exception:
        return 0.0


def compute_sharp_score(row: pd.Series) -> float:
    """
    Approximate sharp score using:
    - reverse line movement (current vs opening)
    - public betting imbalance
    - steam magnitude
    - optional line velocity proxy
    """
    try:
        public_pct = float(row.get("public_bet_pct", 50))
        open_odds = float(row.get("opening_odds", row.get("odds", -110)))
        current_odds = float(row.get("odds", -110))
        velocity = float(row.get("line_velocity", 0))
    except Exception:
        return 50.0

    movement = infer_side_from_movement(open_odds, current_odds)
    movement_strength = abs(movement)

    # Reverse line movement proxy:
    # If public is heavy but line moved *toward* this side, it could still be strong support.
    # If public is low and line moves toward this side, that often suggests sharper action.
    public_fade_bonus = 0.0
    if public_pct <= 45 and movement > 0:
        public_fade_bonus = 20.0
    elif public_pct >= 65 and movement > 0:
        public_fade_bonus = 10.0
    elif public_pct >= 65 and movement < 0:
        public_fade_bonus = -10.0

    movement_component = normalize_0_100(movement_strength, 0, 40) * 0.35
    direction_component = 20.0 if movement > 0 else 0.0
    public_component = normalize_0_100(100 - abs(public_pct - 50) * 2, 0, 100) * 0.10
    velocity_component = normalize_0_100(abs(velocity), 0, 10) * 0.15

    raw = 20 + movement_component + direction_component + public_component + velocity_component + public_fade_bonus
    return float(np.clip(raw, 0, 100))


def compute_market_inefficiency(row: pd.Series) -> Tuple[float, float]:
    """
    Returns:
    - inefficiency score (0-100)
    - edge_pct estimate

    Uses:
    - best offered odds vs consensus fair odds
    - model win probability vs implied probability
    """
    try:
        odds = float(row.get("odds", -110))
        consensus_fair_odds = float(row.get("consensus_fair_odds", odds))
        model_win_prob = float(row.get("model_win_prob", np.nan))
    except Exception:
        return 0.0, 0.0

    implied = american_to_implied_prob(odds)
    fair_implied = american_to_implied_prob(consensus_fair_odds)

    edge_pct = 0.0
    if not np.isnan(model_win_prob):
        edge_pct = (model_win_prob - implied) * 100.0
    elif not np.isnan(fair_implied):
        edge_pct = (fair_implied - implied) * 100.0

    pricing_gap = abs(implied - fair_implied) * 100.0 if not np.isnan(fair_implied) else 0.0
    score = np.clip(pricing_gap * 8 + max(edge_pct, 0) * 6, 0, 100)
    return float(score), float(edge_pct)


def default_candidate_plays() -> pd.DataFrame:
    data = [
        {
            "game": "Warriors vs Lakers",
            "market": "player_props",
            "selection": "Stephen Curry Over 27.5 Points",
            "book": "DraftKings",
            "odds": -115,
            "opening_odds": -108,
            "public_bet_pct": 68,
            "line_velocity": 4.0,
            "consensus_count": 4,
            "base_model_score": 74,
            "model_win_prob": 0.585,
            "consensus_fair_odds": -132,
        },
        {
            "game": "Celtics vs Heat",
            "market": "spreads",
            "selection": "Celtics -4.5",
            "book": "FanDuel",
            "odds": -110,
            "opening_odds": -103,
            "public_bet_pct": 51,
            "line_velocity": 3.0,
            "consensus_count": 5,
            "base_model_score": 81,
            "model_win_prob": 0.596,
            "consensus_fair_odds": -128,
        },
        {
            "game": "Nuggets vs Suns",
            "market": "totals",
            "selection": "Over 228.5",
            "book": "BetMGM",
            "odds": -105,
            "opening_odds": -110,
            "public_bet_pct": 73,
            "line_velocity": 2.0,
            "consensus_count": 3,
            "base_model_score": 66,
            "model_win_prob": 0.535,
            "consensus_fair_odds": -114,
        },
        {
            "game": "Bruins vs Rangers",
            "market": "moneyline",
            "selection": "Bruins ML",
            "book": "Caesars",
            "odds": 122,
            "opening_odds": 132,
            "public_bet_pct": 39,
            "line_velocity": 6.0,
            "consensus_count": 4,
            "base_model_score": 72,
            "model_win_prob": 0.488,
            "consensus_fair_odds": 108,
        },
        {
            "game": "Mavericks vs Clippers",
            "market": "moneyline",
            "selection": "Clippers ML",
            "book": "ESPN BET",
            "odds": -145,
            "opening_odds": -150,
            "public_bet_pct": 77,
            "line_velocity": 1.0,
            "consensus_count": 2,
            "base_model_score": 58,
            "model_win_prob": 0.567,
            "consensus_fair_odds": -149,
        },
        {
            "game": "Panthers vs Leafs",
            "market": "totals",
            "selection": "Under 6.5",
            "book": "DraftKings",
            "odds": 105,
            "opening_odds": 118,
            "public_bet_pct": 42,
            "line_velocity": 5.0,
            "consensus_count": 5,
            "base_model_score": 79,
            "model_win_prob": 0.535,
            "consensus_fair_odds": -103,
        },
    ]
    return pd.DataFrame(data)


def default_bet_log() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "date",
        "game",
        "market",
        "selection",
        "book",
        "odds",
        "opening_odds",
        "public_bet_pct",
        "consensus_count",
        "base_model_score",
        "sharp_score",
        "inefficiency_score",
        "edge_pct",
        "final_score",
        "recommended_units",
        "result",
        "closing_odds",
        "clv",
    ])


def default_model_profile() -> pd.DataFrame:
    rows = []
    for market in ["moneyline", "spreads", "totals", "player_props"]:
        for o_bucket in ["fav_heavy", "fav_std", "coinflip", "dog_live", "dog_long"]:
            for c_bucket in ["5of5", "4of5", "3of5", "lt3"]:
                rows.append({
                    "market": market,
                    "odds_bucket": o_bucket,
                    "consensus_bucket": c_bucket,
                    "bets": 0,
                    "wins": 0,
                    "roi_units": 0.0,
                    "weight": 1.0,
                })
    return pd.DataFrame(rows)


def ensure_columns(df: pd.DataFrame, required: Dict[str, object]) -> pd.DataFrame:
    out = df.copy()
    for col, default in required.items():
        if col not in out.columns:
            out[col] = default
    return out


def profit_in_units(odds: float, result: str) -> float:
    if result == "win":
        dec = american_to_decimal(odds)
        return (dec - 1.0) if not np.isnan(dec) else 0.0
    if result == "loss":
        return -1.0
    return 0.0


def clv_from_odds(bet_odds: float, closing_odds: float) -> float:
    """
    Positive CLV means your number was better than close.
    For both sides, lower implied probability cost is generally better for the bettor.
    """
    try:
        return (american_to_implied_prob(closing_odds) - american_to_implied_prob(bet_odds)) * 100.0
    except Exception:
        return 0.0


def update_profile_from_bet_log(bet_log: pd.DataFrame, profile: pd.DataFrame) -> pd.DataFrame:
    prof = profile.copy()

    if bet_log.empty:
        return prof

    settled = bet_log[bet_log["result"].isin(["win", "loss"])].copy()
    if settled.empty:
        return prof

    settled["odds_bucket"] = settled["odds"].apply(odds_bucket)
    settled["consensus_bucket"] = settled["consensus_count"].apply(consensus_bucket)
    settled["roi_units_single"] = settled.apply(lambda r: profit_in_units(r["odds"], r["result"]), axis=1)

    grouped = (
        settled.groupby(["market", "odds_bucket", "consensus_bucket"], dropna=False)
        .agg(
            bets=("result", "size"),
            wins=("result", lambda s: (s == "win").sum()),
            roi_units=("roi_units_single", "sum"),
        )
        .reset_index()
    )

    prof = prof.drop(columns=["bets", "wins", "roi_units", "weight"], errors="ignore")
    prof = prof.merge(grouped, how="left", on=["market", "odds_bucket", "consensus_bucket"])

    prof["bets"] = prof["bets"].fillna(0).astype(int)
    prof["wins"] = prof["wins"].fillna(0).astype(int)
    prof["roi_units"] = prof["roi_units"].fillna(0.0)

    # Weight logic:
    # - Needs sample size
    # - Reward proven profitability modestly
    # - Penalize losing buckets
    weights = []
    for _, r in prof.iterrows():
        bets = int(r["bets"])
        wins = int(r["wins"])
        roi = float(r["roi_units"])
        if bets < 5:
            weight = 1.0
        else:
            win_rate = wins / bets if bets > 0 else 0.5
            roi_per_bet = roi / bets if bets > 0 else 0.0
            weight = 1.0 + (win_rate - 0.5) * 1.2 + roi_per_bet * 0.9
            weight = float(np.clip(weight, 0.70, 1.35))
        weights.append(weight)

    prof["weight"] = weights
    return prof


def attach_learning_weight(candidates: pd.DataFrame, profile: pd.DataFrame) -> pd.DataFrame:
    df = candidates.copy()
    df["odds_bucket"] = df["odds"].apply(odds_bucket)
    df["consensus_bucket"] = df["consensus_count"].apply(consensus_bucket)

    prof_small = profile[["market", "odds_bucket", "consensus_bucket", "weight"]].copy()
    df = df.merge(prof_small, how="left", on=["market", "odds_bucket", "consensus_bucket"])
    df["weight"] = df["weight"].fillna(1.0)
    return df


def score_candidates(candidates: pd.DataFrame, bankroll: float, max_unit_cap: float) -> pd.DataFrame:
    df = candidates.copy()

    sharp_scores = []
    ineff_scores = []
    edge_pcts = []
    final_scores = []
    units = []
    reasons = []

    for _, row in df.iterrows():
        sharp = compute_sharp_score(row)
        ineff, edge_pct = compute_market_inefficiency(row)

        base_model_score = float(row.get("base_model_score", 50))
        consensus_count = int(row.get("consensus_count", 0))
        learning_weight = float(row.get("weight", 1.0))
        model_win_prob = float(row.get("model_win_prob", 0.50))

        consensus_bonus = {5: 14, 4: 9, 3: 4}.get(consensus_count, -8)
        edge_bonus = np.clip(edge_pct * 2.2, -15, 20)

        raw_score = (
            base_model_score * 0.42
            + sharp * 0.24
            + ineff * 0.20
            + 25 * learning_weight * 0.14
            + consensus_bonus
            + edge_bonus
        )

        final_score = float(np.clip(raw_score, 0, 100))

        raw_kelly = kelly_fraction(model_win_prob, float(row.get("odds", -110)))
        # conservative fraction for real-world survivability
        unit_fraction = raw_kelly * 0.30
        unit_size = bankroll * unit_fraction
        recommended_units = unit_size / 100.0  # 1u = $100
        recommended_units = float(np.clip(recommended_units, 0.0, max_unit_cap))

        reason_bits = []
        if consensus_count >= 4:
            reason_bits.append(f"{consensus_count}/5 consensus")
        if sharp >= 70:
            reason_bits.append("sharp support")
        if edge_pct >= 3:
            reason_bits.append(f"+{edge_pct:.1f}% edge")
        if learning_weight > 1.05:
            reason_bits.append("profitable bucket")
        if not reason_bits:
            reason_bits.append("borderline")

        sharp_scores.append(round(sharp, 1))
        ineff_scores.append(round(ineff, 1))
        edge_pcts.append(round(edge_pct, 2))
        final_scores.append(round(final_score, 1))
        units.append(round(recommended_units, 2))
        reasons.append(" • ".join(reason_bits))

    df["sharp_score"] = sharp_scores
    df["inefficiency_score"] = ineff_scores
    df["edge_pct"] = edge_pcts
    df["final_score"] = final_scores
    df["recommended_units"] = units
    df["decision_reason"] = reasons
    return df


def filter_auto_mode(df: pd.DataFrame, min_consensus: int, min_sharp: float, min_edge: float, min_final: float) -> pd.DataFrame:
    out = df.copy()

    out["auto_qualified"] = (
        (out["consensus_count"] >= min_consensus)
        & (out["sharp_score"] >= min_sharp)
        & (out["edge_pct"] >= min_edge)
        & (out["final_score"] >= min_final)
        & (out["recommended_units"] > 0)
    )
    return out


# ------------------------------------------------------------
# Load / initialize state
# ------------------------------------------------------------
if "bet_log_v24" not in st.session_state:
    st.session_state.bet_log_v24 = safe_read_csv(BET_LOG_PATH, default_bet_log())

if "model_profile_v24" not in st.session_state:
    st.session_state.model_profile_v24 = safe_read_csv(MODEL_PROFILE_PATH, default_model_profile())

bet_log = st.session_state.bet_log_v24.copy()
model_profile = st.session_state.model_profile_v24.copy()

bet_log = ensure_columns(
    bet_log,
    {
        "date": "",
        "game": "",
        "market": "",
        "selection": "",
        "book": "",
        "odds": np.nan,
        "opening_odds": np.nan,
        "public_bet_pct": np.nan,
        "consensus_count": np.nan,
        "base_model_score": np.nan,
        "sharp_score": np.nan,
        "inefficiency_score": np.nan,
        "edge_pct": np.nan,
        "final_score": np.nan,
        "recommended_units": np.nan,
        "result": "",
        "closing_odds": np.nan,
        "clv": np.nan,
    },
)

model_profile = ensure_columns(
    model_profile,
    {
        "market": "",
        "odds_bucket": "",
        "consensus_bucket": "",
        "bets": 0,
        "wins": 0,
        "roi_units": 0.0,
        "weight": 1.0,
    },
)


# ------------------------------------------------------------
# Sidebar controls
# ------------------------------------------------------------
st.sidebar.header("⚙️ Auto Mode Controls")

bankroll = st.sidebar.number_input("Bankroll ($)", min_value=100, value=1000, step=100)
max_unit_cap = st.sidebar.number_input("Max Recommended Units", min_value=0.25, value=2.00, step=0.25)
min_consensus = st.sidebar.slider("Min Consensus Count", 2, 5, 4)
min_sharp = st.sidebar.slider("Min Sharp Score", 0, 100, 65)
min_edge = st.sidebar.slider("Min Edge %", 0.0, 10.0, 2.5, 0.5)
min_final = st.sidebar.slider("Min Final Score", 0, 100, 72)
auto_save_qualified = st.sidebar.checkbox("Auto-save qualified plays to Bet Log", value=False)

st.sidebar.markdown("---")
st.sidebar.subheader("📂 Candidate Plays")
uploaded_candidates = st.sidebar.file_uploader("Upload candidate plays CSV", type=["csv"])

st.sidebar.caption(
    "Required columns for best results: game, market, selection, book, odds, opening_odds, "
    "public_bet_pct, line_velocity, consensus_count, base_model_score, model_win_prob, consensus_fair_odds"
)

sample_df = default_candidate_plays()
if uploaded_candidates is not None:
    try:
        candidate_df = pd.read_csv(uploaded_candidates)
        st.sidebar.success("Candidate file loaded")
    except Exception as e:
        st.sidebar.error(f"Could not read CSV: {e}")
        candidate_df = sample_df.copy()
else:
    candidate_df = sample_df.copy()

candidate_df = ensure_columns(
    candidate_df,
    {
        "game": "",
        "market": "moneyline",
        "selection": "",
        "book": "",
        "odds": -110,
        "opening_odds": -110,
        "public_bet_pct": 50,
        "line_velocity": 0.0,
        "consensus_count": 3,
        "base_model_score": 50,
        "model_win_prob": 0.50,
        "consensus_fair_odds": -110,
    },
)


# ------------------------------------------------------------
# Refresh learning model
# ------------------------------------------------------------
col_a, col_b, col_c = st.columns([1, 1, 2])

with col_a:
    if st.button("🧠 Refresh Self-Learning Weights", use_container_width=True):
        model_profile = update_profile_from_bet_log(bet_log, model_profile)
        st.session_state.model_profile_v24 = model_profile.copy()
        safe_save_csv(model_profile, MODEL_PROFILE_PATH)
        st.success("Learning profile updated")

with col_b:
    if st.button("🧹 Reset Learning Profile", use_container_width=True):
        model_profile = default_model_profile()
        st.session_state.model_profile_v24 = model_profile.copy()
        safe_save_csv(model_profile, MODEL_PROFILE_PATH)
        st.warning("Learning profile reset")

with col_c:
    st.info("Auto Mode uses historical result buckets to gently boost or penalize future candidate plays.")


# ------------------------------------------------------------
# Score pipeline
# ------------------------------------------------------------
candidate_df = attach_learning_weight(candidate_df, model_profile)
scored_df = score_candidates(candidate_df, bankroll=bankroll, max_unit_cap=max_unit_cap)
scored_df = filter_auto_mode(
    scored_df,
    min_consensus=min_consensus,
    min_sharp=min_sharp,
    min_edge=min_edge,
    min_final=min_final,
)
scored_df = scored_df.sort_values(["auto_qualified", "final_score", "edge_pct"], ascending=[False, False, False]).reset_index(drop=True)

qualified_df = scored_df[scored_df["auto_qualified"]].copy()


# ------------------------------------------------------------
# KPI row
# ------------------------------------------------------------
k1, k2, k3, k4 = st.columns(4)
k1.metric("Candidate Plays", len(scored_df))
k2.metric("Qualified Plays", len(qualified_df))
k3.metric("Avg Qualified Score", f"{qualified_df['final_score'].mean():.1f}" if len(qualified_df) else "—")
k4.metric("Avg Qualified Edge", f"{qualified_df['edge_pct'].mean():.2f}%" if len(qualified_df) else "—")


# ------------------------------------------------------------
# Top plays
# ------------------------------------------------------------
st.subheader("🎯 Auto Mode Top Plays")

if qualified_df.empty:
    st.warning("No plays met the current Auto Mode thresholds.")
else:
    top_n = min(5, len(qualified_df))
    for i, row in qualified_df.head(top_n).iterrows():
        box = st.container(border=True)
        with box:
            st.markdown(f"### #{i+1} {row['selection']}")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Game", row["game"])
            c2.metric("Book", row["book"])
            c3.metric("Odds", f"{int(row['odds'])}" if pd.notna(row["odds"]) else "—")
            c4.metric("Units", f"{row['recommended_units']:.2f}u")

            d1, d2, d3, d4 = st.columns(4)
            d1.metric("Final Score", f"{row['final_score']:.1f}")
            d2.metric("Sharp Score", f"{row['sharp_score']:.1f}")
            d3.metric("Edge", f"{row['edge_pct']:.2f}%")
            d4.metric("Consensus", f"{int(row['consensus_count'])}/5")

            st.caption(f"Reason: {row['decision_reason']}")


# ------------------------------------------------------------
# Qualified plays table
# ------------------------------------------------------------
st.subheader("✅ Qualified Plays")
st.dataframe(
    qualified_df[[
        "game", "market", "selection", "book", "odds", "consensus_count",
        "sharp_score", "inefficiency_score", "edge_pct", "final_score",
        "recommended_units", "decision_reason"
    ]],
    use_container_width=True,
    hide_index=True,
)

# Auto-save qualified plays
if auto_save_qualified and not qualified_df.empty:
    existing_keys = set(
        (
            bet_log["game"].astype(str)
            + " | " + bet_log["selection"].astype(str)
            + " | " + bet_log["book"].astype(str)
            + " | " + bet_log["odds"].astype(str)
        ).tolist()
    )

    rows_to_add = []
    for _, row in qualified_df.iterrows():
        key = f"{row['game']} | {row['selection']} | {row['book']} | {row['odds']}"
        if key not in existing_keys:
            rows_to_add.append({
                "date": pd.Timestamp.now().strftime("%Y-%m-%d"),
                "game": row["game"],
                "market": row["market"],
                "selection": row["selection"],
                "book": row["book"],
                "odds": row["odds"],
                "opening_odds": row["opening_odds"],
                "public_bet_pct": row["public_bet_pct"],
                "consensus_count": row["consensus_count"],
                "base_model_score": row["base_model_score"],
                "sharp_score": row["sharp_score"],
                "inefficiency_score": row["inefficiency_score"],
                "edge_pct": row["edge_pct"],
                "final_score": row["final_score"],
                "recommended_units": row["recommended_units"],
                "result": "",
                "closing_odds": np.nan,
                "clv": np.nan,
            })

    if rows_to_add:
        bet_log = pd.concat([bet_log, pd.DataFrame(rows_to_add)], ignore_index=True)
        st.session_state.bet_log_v24 = bet_log.copy()
        safe_save_csv(bet_log, BET_LOG_PATH)
        st.success(f"Auto-saved {len(rows_to_add)} new qualified play(s) to Bet Log.")


# ------------------------------------------------------------
# Full scored board
# ------------------------------------------------------------
with st.expander("📊 View All Scored Candidates", expanded=False):
    st.dataframe(
        scored_df[[
            "game", "market", "selection", "book", "odds", "opening_odds",
            "public_bet_pct", "consensus_count", "base_model_score", "weight",
            "sharp_score", "inefficiency_score", "edge_pct", "final_score",
            "recommended_units", "auto_qualified"
        ]],
        use_container_width=True,
        hide_index=True,
    )


# ------------------------------------------------------------
# Manual bet log entry
# ------------------------------------------------------------
st.subheader("📒 Bet Log")

with st.form("manual_bet_entry"):
    m1, m2, m3 = st.columns(3)
    game = m1.text_input("Game")
    market = m2.selectbox("Market", ["moneyline", "spreads", "totals", "player_props"])
    selection = m3.text_input("Selection")

    n1, n2, n3, n4 = st.columns(4)
    book = n1.text_input("Book", value="DraftKings")
    odds = n2.number_input("Bet Odds", value=-110)
    opening_odds = n3.number_input("Opening Odds", value=-110)
    public_bet_pct = n4.slider("Public Betting %", 0, 100, 50)

    p1, p2, p3, p4 = st.columns(4)
    consensus_count = p1.slider("Consensus Count", 1, 5, 3)
    base_model_score = p2.slider("Base Model Score", 0, 100, 60)
    closing_odds = p3.number_input("Closing Odds", value=-110)
    result = p4.selectbox("Result", ["", "win", "loss"])

    submit_manual = st.form_submit_button("Add / Update Bet Log")
    if submit_manual:
        sharp_score = compute_sharp_score(pd.Series({
            "public_bet_pct": public_bet_pct,
            "opening_odds": opening_odds,
            "odds": odds,
            "line_velocity": 0,
        }))
        ineff_score, edge_pct = compute_market_inefficiency(pd.Series({
            "odds": odds,
            "consensus_fair_odds": closing_odds,
            "model_win_prob": np.nan,
        }))
        final_score = np.clip(
            base_model_score * 0.50 + sharp_score * 0.25 + ineff_score * 0.15 + consensus_count * 2.0,
            0,
            100,
        )
        clv = clv_from_odds(odds, closing_odds)

        new_row = pd.DataFrame([{
            "date": pd.Timestamp.now().strftime("%Y-%m-%d"),
            "game": game,
            "market": market,
            "selection": selection,
            "book": book,
            "odds": odds,
            "opening_odds": opening_odds,
            "public_bet_pct": public_bet_pct,
            "consensus_count": consensus_count,
            "base_model_score": base_model_score,
            "sharp_score": round(sharp_score, 1),
            "inefficiency_score": round(ineff_score, 1),
            "edge_pct": round(edge_pct, 2),
            "final_score": round(float(final_score), 1),
            "recommended_units": round(float(np.clip(kelly_fraction(0.54, odds) * 0.30 * bankroll / 100.0, 0, max_unit_cap)), 2),
            "result": result,
            "closing_odds": closing_odds,
            "clv": round(float(clv), 2),
        }])

        bet_log = pd.concat([bet_log, new_row], ignore_index=True)
        st.session_state.bet_log_v24 = bet_log.copy()
        safe_save_csv(bet_log, BET_LOG_PATH)
        st.success("Bet added to log.")


# ------------------------------------------------------------
# Bet log display
# ------------------------------------------------------------
st.dataframe(bet_log, use_container_width=True, hide_index=True)

d1, d2, d3 = st.columns(3)

settled = bet_log[bet_log["result"].isin(["win", "loss"])].copy()
wins = (settled["result"] == "win").sum()
losses = (settled["result"] == "loss").sum()
win_rate = (wins / len(settled) * 100.0) if len(settled) else 0.0

roi_units = 0.0
if len(settled):
    roi_units = settled.apply(lambda r: profit_in_units(r["odds"], r["result"]), axis=1).sum()

avg_clv = settled["clv"].mean() if ("clv" in settled.columns and len(settled)) else 0.0

d1.metric("Settled Bets", len(settled))
d2.metric("Win Rate", f"{win_rate:.1f}%")
d3.metric("Net Units", f"{roi_units:.2f}u")

e1, e2, e3 = st.columns(3)
e1.metric("Wins", int(wins))
e2.metric("Losses", int(losses))
e3.metric("Avg CLV", f"{avg_clv:.2f}" if len(settled) else "—")


# ------------------------------------------------------------
# Learning profile views
# ------------------------------------------------------------
st.subheader("🧠 Self-Learning Profile")

lp1, lp2 = st.columns(2)

with lp1:
    st.markdown("#### Current Weight Table")
    st.dataframe(
        model_profile.sort_values(["market", "consensus_bucket", "odds_bucket"]).reset_index(drop=True),
        use_container_width=True,
        hide_index=True,
    )

with lp2:
    if not settled.empty:
        view = (
            settled.assign(
                odds_bucket=settled["odds"].apply(odds_bucket),
                consensus_bucket=settled["consensus_count"].apply(consensus_bucket),
                single_units=settled.apply(lambda r: profit_in_units(r["odds"], r["result"]), axis=1),
            )
            .groupby(["market", "consensus_count"], dropna=False)
            .agg(
                bets=("result", "size"),
                wins=("result", lambda s: (s == "win").sum()),
                net_units=("single_units", "sum"),
                avg_clv=("clv", "mean"),
            )
            .reset_index()
        )
        st.markdown("#### Performance by Market / Consensus")
        st.dataframe(view, use_container_width=True, hide_index=True)
    else:
        st.info("Add settled bets to activate self-learning analytics.")


# ------------------------------------------------------------
# Export section
# ------------------------------------------------------------
st.subheader("💾 Export")

exp1, exp2 = st.columns(2)
with exp1:
    bet_log_csv = bet_log.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download Bet Log CSV",
        data=bet_log_csv,
        file_name="bet_log_v24.csv",
        mime="text/csv",
        use_container_width=True,
    )

with exp2:
    profile_csv = model_profile.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download Learning Profile CSV",
        data=profile_csv,
        file_name="model_profile_v24.csv",
        mime="text/csv",
        use_container_width=True,
    )

st.caption(
    "V24 Auto Mode is decision-focused and usable today with uploaded candidate plays. "
    "The next major leap would be connecting real sportsbook/API feeds so the scanner and auto mode work live."
)
