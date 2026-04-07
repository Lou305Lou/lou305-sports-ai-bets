import streamlit as st
from datetime import date

st.set_page_config(
    page_title="Sports Betting AI Dashboard V36",
    layout="wide",
)

# ------------- STATE & CONSTANTS -------------

NAV_TABS = ["Top Plays", "Watchlist", "AI Slip", "Bet Log"]
SPORTS = ["NBA", "NFL", "MLB", "NHL"]

if "selected_tab" not in st.session_state:
    st.session_state.selected_tab = "Top Plays"

if "selected_sport" not in st.session_state:
    st.session_state.selected_sport = "NBA"

if "today" not in st.session_state:
    st.session_state.today = date.today()

# This will hold today's plays only (no stale carryover)
if "today_plays" not in st.session_state:
    st.session_state.today_plays = {
        "Top Plays": [],
        "Watchlist": [],
        "AI Slip": [],
    }

# This will hold historical bets (append-only)
if "bet_log" not in st.session_state:
    st.session_state.bet_log = []


# ------------- HELPERS -------------

def full_refresh():
    """
    Unified refresh:
    - Pull odds
    - Pull SportsDataIO context
    - Call AI
    - Overwrite today's plays (no duplicates, no stale data)
    """
    # TODO: integrate real APIs here
    # For now, just clear and leave placeholders
    for key in ["Top Plays", "Watchlist", "AI Slip"]:
        st.session_state.today_plays[key] = []

    st.success("Full refresh completed (stub). No plays yet for snapshot.")


def render_top_plays():
    plays = st.session_state.today_plays["Top Plays"]
    if not plays:
        st.info("No plays available for snapshot.")
        st.write("No data available.")
        return
    st.write("Top Plays table coming soon…")


def render_watchlist():
    plays = st.session_state.today_plays["Watchlist"]
    if not plays:
        st.info("No watchlist entries yet.")
        return
    st.write("Watchlist table coming soon…")


def render_ai_slip():
    plays = st.session_state.today_plays["AI Slip"]
    if not plays:
        st.info("No AI slip generated yet.")
        return
    st.write("AI Slip details coming soon…")


def render_bet_log():
    log = st.session_state.bet_log
    if not log:
        st.info("No settled bets in Bet Log yet.")
        return
    st.write("Bet Log table coming soon…")


# ------------- LAYOUT -------------

st.title("Sports Betting AI Dashboard V36")

top_bar = st.container()
with top_bar:
    col_left, col_right = st.columns([3, 1])

    with col_left:
        st.subheader("Select Sport")
        sport = st.selectbox(
            "Sport",
            SPORTS,
            index=SPORTS.index(st.session_state.selected_sport),
            label_visibility="collapsed",
        )
        st.session_state.selected_sport = sport

        st.markdown("### Navigation")
        nav_choice = st.radio(
            "Navigation",
            NAV_TABS,
            index=NAV_TABS.index(st.session_state.selected_tab),
            horizontal=True,
            label_visibility="collapsed",
        )
        st.session_state.selected_tab = nav_choice

    with col_right:
        st.markdown("### Actions")
        if st.button("Full Refresh (Odds + SportsDataIO + AI)", use_container_width=True):
            full_refresh()

st.markdown("---")

# ------------- MAIN CONTENT AREA -------------

if st.session_state.selected_tab == "Top Plays":
    st.header("Top Plays")
    render_top_plays()

elif st.session_state.selected_tab == "Watchlist":
    st.header("Watchlist")
    render_watchlist()

elif st.session_state.selected_tab == "AI Slip":
    st.header("AI Slip")
    render_ai_slip()

elif st.session_state.selected_tab == "Bet Log":
    st.header("Bet Log")
    render_bet_log()
# =========================
# Chunk 2 – State & Layout
# =========================

import enum
from typing import List, Dict, Any, Optional

# ---------- Navigation model ----------

class NavView(str, enum.Enum):
    TOP_PLAYS = "Top Plays"
    WATCHLIST = "Watchlist"
    AI_SLIP = "AI Slip"
    BET_LOG = "Bet Log"


SPORT_OPTIONS = ["NBA", "NFL", "MLB", "NHL"]

# ---------- Session state keys ----------

SS_NAV_VIEW = "nav_view"
SS_SELECTED_SPORT = "selected_sport"
SS_TODAY_DATE = "today_date"
SS_TOP_PLAYS = "top_plays"
SS_WATCHLIST = "watchlist"
SS_AI_SLIP = "ai_slip"
SS_BET_LOG = "bet_log"
SS_LAST_REFRESH_AT = "last_refresh_at"
SS_REFRESH_IN_PROGRESS = "refresh_in_progress"


def init_session_state() -> None:
    """Initialize all session_state keys with clean defaults."""
    if SS_NAV_VIEW not in st.session_state:
        st.session_state[SS_NAV_VIEW] = NavView.TOP_PLAYS

    if SS_SELECTED_SPORT not in st.session_state:
        st.session_state[SS_SELECTED_SPORT] = "NBA"

    if SS_TODAY_DATE not in st.session_state:
        st.session_state[SS_TODAY_DATE] = datetime.date.today()

    if SS_TOP_PLAYS not in st.session_state:
        st.session_state[SS_TOP_PLAYS] = []  # list of dicts

    if SS_WATCHLIST not in st.session_state:
        st.session_state[SS_WATCHLIST] = []  # list of dicts

    if SS_AI_SLIP not in st.session_state:
        st.session_state[SS_AI_SLIP] = []  # list of dicts

    if SS_BET_LOG not in st.session_state:
        st.session_state[SS_BET_LOG] = []  # list of dicts (historical)

    if SS_LAST_REFRESH_AT not in st.session_state:
        st.session_state[SS_LAST_REFRESH_AT] = None

    if SS_REFRESH_IN_PROGRESS not in st.session_state:
        st.session_state[SS_REFRESH_IN_PROGRESS] = False


# ---------- Layout scaffolding ----------

def render_header() -> None:
    col_title, col_refresh = st.columns([4, 2])
    with col_title:
        st.markdown("### Sports Betting AI Dashboard V36")
    with col_refresh:
        disabled = st.session_state[SS_REFRESH_IN_PROGRESS]
        if st.button(
            "Full Refresh (Odds + SportsDataIO + AI)",
            type="primary",
            use_container_width=True,
            disabled=disabled,
        ):
            st.session_state[SS_REFRESH_IN_PROGRESS] = True
            # The actual refresh pipeline will be wired in a later chunk.
            st.experimental_rerun()


def render_top_bar() -> None:
    col_sport, col_nav = st.columns([1.2, 3])

    with col_sport:
        st.markdown("**Select Sport**")
        st.session_state[SS_SELECTED_SPORT] = st.selectbox(
            label="",
            options=SPORT_OPTIONS,
            index=SPORT_OPTIONS.index(st.session_state[SS_SELECTED_SPORT]),
            label_visibility="collapsed",
        )

    with col_nav:
        st.markdown("**Navigation**")
        nav_cols = st.columns(4)
        nav_items = [
            NavView.TOP_PLAYS,
            NavView.WATCHLIST,
            NavView.AI_SLIP,
            NavView.BET_LOG,
        ]

        for col, nav_item in zip(nav_cols, nav_items):
            with col:
                is_active = st.session_state[SS_NAV_VIEW] == nav_item
                btn_label = nav_item.value
                if st.button(
                    btn_label,
                    type="secondary" if is_active else "tertiary",
                    use_container_width=True,
                ):
                    st.session_state[SS_NAV_VIEW] = nav_item
                    st.experimental_rerun()


def render_view_container() -> None:
    """Placeholder router for the main content area."""
    st.markdown("---")
    view = st.session_state[SS_NAV_VIEW]

    if view == NavView.TOP_PLAYS:
        st.markdown("#### Top Plays")
        st.info("No data available yet. Run a full refresh to populate today's plays.")
    elif view == NavView.WATCHLIST:
        st.markdown("#### Watchlist")
        st.info("No watchlist entries yet.")
    elif view == NavView.AI_SLIP:
        st.markdown("#### AI Slip")
        st.info("No AI slip generated yet.")
    elif view == NavView.BET_LOG:
        st.markdown("#### Bet Log")
        st.info("No historical bets logged yet.")


# ---------- Page entrypoint wiring for this chunk ----------

def render_app_shell() -> None:
    """Base shell: state init + header + nav + empty views."""
    init_session_state()
    render_header()
    render_top_bar()
    render_view_container()


# In your main file, after st.set_page_config(...), you will call:
# render_app_shell()
# ============================================================
# ENGINE V36 — UNIFIED AI ENGINE (QWEN + CONTEXT + LEARNING)
# ============================================================

import os
import json
import hashlib
import requests
import pandas as pd
from datetime import datetime
from itertools import combinations

from utils_v36 import (
    safe_float, safe_int, clamp,
    american_to_int, american_to_implied_prob,
    calculate_market_signal, calculate_matchup_score,
    calculate_historical_score, calculate_true_confidence,
    normalize_dataframe_for_selected_sport,
    recalc_rank_metrics_v36,
)

from learning_v36 import (
    enrich_play_learning_v36,
    apply_learning_filters_v36,
    load_learning_state,
    save_learning_state,
)

from qwen_v36 import (
    qwen_reasoning_on_play,
    qwen_reasoning_on_parlay,
    qwen_reasoning_on_slate,
)

from context_v36 import (
    fetch_news_context,
    fetch_x_context,
    fetch_injury_context,
    fetch_line_movement_context,
)

# ============================================================
# MAIN ENGINE ENTRY
# ============================================================

def run_engine_v36(plays_df, sport):
    """
    Full unified engine pipeline:
    1. Normalize + recalc metrics
    2. Add contextual signals (news, X, injuries, line movement)
    3. Apply learning engine
    4. Qwen reasoning on each play
    5. Rank + filter
    6. Build AI Slip
    7. Build Parlay candidates
    """

    if plays_df is None or plays_df.empty:
        return {
            "engine_state": "NO_PLAYS",
            "notes": ["No plays available from odds API."],
            "strong_cards": [],
            "parlay_suggestions": [],
        }

    # --------------------------------------------------------
    # STEP 1 — Normalize + recalc metrics
    # --------------------------------------------------------
    df = normalize_dataframe_for_selected_sport(plays_df, sport)
    df = recalc_rank_metrics_v36(df)

    # --------------------------------------------------------
    # STEP 2 — Add contextual signals
    # --------------------------------------------------------
    news_ctx = fetch_news_context(sport)
    x_ctx = fetch_x_context(sport)
    injury_ctx = fetch_injury_context(sport)
    line_ctx = fetch_line_movement_context(sport)

    df["context_score"] = 0.0
    df["context_note"] = ""

    for idx, row in df.iterrows():
        notes = []

        # News
        if row["team"] in news_ctx:
            df.at[idx, "context_score"] += 4
            notes.append("News boost")

        # X sentiment
        if row["team"] in x_ctx:
            df.at[idx, "context_score"] += 3
            notes.append("X sentiment")

        # Injuries
        if row["team"] in injury_ctx:
            df.at[idx, "context_score"] -= 5
            notes.append("Injury risk")

        # Line movement
        if row["game"] in line_ctx:
            df.at[idx, "context_score"] += line_ctx[row["game"]]
            notes.append("Line movement")

        df.at[idx, "context_note"] = ", ".join(notes)

    # --------------------------------------------------------
    # STEP 3 — Apply learning engine
    # --------------------------------------------------------
    learning_state = load_learning_state(sport)

    filtered_rows = []
    for _, row in df.iterrows():
        enriched = enrich_play_learning_v36(row.to_dict(), sport)
        allowed, reason = apply_learning_filters_v36(enriched, learning_state)

        if allowed:
            enriched["learning_reason"] = reason
            filtered_rows.append(enriched)

    df = pd.DataFrame(filtered_rows)

    if df.empty:
        return {
            "engine_state": "FILTERED_OUT",
            "notes": ["Learning engine filtered all plays."],
            "strong_cards": [],
            "parlay_suggestions": [],
        }

    # --------------------------------------------------------
    # STEP 4 — Qwen reasoning on each play
    # --------------------------------------------------------
    qwen_notes = []
    qwen_scores = []

    for idx, row in df.iterrows():
        reasoning = qwen_reasoning_on_play(row)
        df.at[idx, "qwen_score"] = reasoning["score"]
        df.at[idx, "qwen_note"] = reasoning["note"]
        qwen_notes.append(reasoning["note"])
        qwen_scores.append(reasoning["score"])

    # --------------------------------------------------------
    # STEP 5 — Final ranking
    # --------------------------------------------------------
    df["final_score"] = (
        df["rank_score"] * 0.55 +
        df["context_score"] * 0.15 +
        df["qwen_score"] * 0.30
    )

    df = df.sort_values("final_score", ascending=False).reset_index(drop=True)

    # --------------------------------------------------------
    # STEP 6 — Build AI Slip (top 5)
    # --------------------------------------------------------
    ai_slip = df.head(5).to_dict("records")

    # --------------------------------------------------------
    # STEP 7 — Build Parlay candidates
    # --------------------------------------------------------
    parlay_candidates = []
    rows = df.head(12).to_dict("records")

    for combo_size in [2, 3]:
        for combo in combinations(rows, combo_size):
            reasoning = qwen_reasoning_on_parlay(combo)
            if reasoning["approved"]:
                parlay_candidates.append(reasoning)

    # --------------------------------------------------------
    # FINAL OUTPUT
    # --------------------------------------------------------
    return {
        "engine_state": "OK",
        "notes": qwen_notes[:10],
        "strong_cards": df.head(12).to_dict("records"),
        "ai_slip": ai_slip,
        "parlay_suggestions": parlay_candidates[:5],
    }
# ------------- CHUNK 4: AI ENGINE (TRUE PROBABILITY + CONFIDENCE + EDGE) -------------

import math

# Weight configuration (will later be adaptive)
WEIGHTS = {
    "true_prob": 0.30,
    "price_edge": 0.25,
    "market_signal": 0.15,
    "matchup_quality": 0.15,
    "historical": 0.15,
}

# Odds → implied probability
def implied_probability(odds: int) -> float:
    if odds > 0:
        return 100 / (odds + 100)
    return abs(odds) / (abs(odds) + 100)


# Core true probability model (stub until Qwen integration)
def compute_true_probability(odds: int, books: int = 3, consensus: float = 0.55) -> float:
    imp = implied_probability(odds)

    # Market bonuses
    books_bonus = min(0.03, books * 0.004)
    consensus_bonus = (consensus - 0.50) * 0.10  # 50% baseline
    base_true = imp + books_bonus + consensus_bonus

    return max(0.02, min(0.95, base_true))


# Edge calculation (true_prob - implied_prob)
def compute_edge(odds: int, true_prob: float) -> float:
    imp = implied_probability(odds)
    return round((true_prob - imp) * 100, 2)


# Market signal (books + edge)
def compute_market_signal(books: int, edge: float) -> float:
    return round((books * 4.5) + (edge * 2.0), 1)


# Matchup quality (stub)
def compute_matchup_quality(market: str) -> float:
    m = market.lower()
    if "spread" in m:
        return 67
    if "total" in m:
        return 63
    if "moneyline" in m or "ml" in m:
        return 61
    return 55


# Historical performance (stub)
def compute_historical_score() -> float:
    return 58.0


# True confidence (weighted)
def compute_true_confidence(true_prob: float, edge: float, books: int, market_signal: float) -> float:
    tp = true_prob * 100
    edge_score = min(100, edge * 8)
    books_score = min(100, books * 12)
    matchup_score = 65
    historical_score = 58

    weighted = (
        tp * WEIGHTS["true_prob"]
        + edge_score * WEIGHTS["price_edge"]
        + market_signal * WEIGHTS["market_signal"]
        + matchup_score * WEIGHTS["matchup_quality"]
        + historical_score * WEIGHTS["historical"]
    )

    # Penalties
    if books < 2:
        weighted -= 8
    if edge < 2:
        weighted -= 6
    if tp < 54:
        weighted -= 5

    return round(max(0, min(99, weighted)), 1)


# AI Slip scoring (for ranking)
def compute_ai_slip_score(play: dict) -> float:
    return (
        play["true_confidence"] * 0.60
        + play["edge"] * 4.0
        + 2.0
    )


# Apply AI engine to a play dict
def enrich_play(play: dict) -> dict:
    odds = play["odds"]
    books = 3
    consensus = 0.55

    true_prob = compute_true_probability(odds, books, consensus)
    edge = compute_edge(odds, true_prob)
    market_signal = compute_market_signal(books, edge)
    true_conf = compute_true_confidence(true_prob, edge, books, market_signal)

    play["true_prob"] = round(true_prob * 100, 2)
    play["edge"] = edge
    play["market_signal"] = market_signal
    play["true_confidence"] = true_conf
    play["ai_score"] = compute_ai_slip_score(play)

    return play


# Apply AI engine to all plays in a list
def enrich_play_list(plays: list) -> list:
    return [enrich_play(p) for p in plays]
# ------------- CHUNK 5: AI-INTEGRATED REFRESH + SNAPSHOT BUILDER -------------

def _dedupe_by_id(plays: list) -> list:
    """Remove duplicates by play['id'] while preserving order."""
    seen = set()
    out = []
    for p in plays:
        pid = p.get("id")
        if pid not in seen:
            seen.add(pid)
            out.append(p)
    return out


def _sort_top_plays(plays: list) -> list:
    """Sort by true_confidence → edge → ai_score."""
    return sorted(
        plays,
        key=lambda p: (
            p.get("true_confidence", 0),
            p.get("edge", 0),
            p.get("ai_score", 0),
        ),
        reverse=True,
    )


def _sort_watchlist(plays: list) -> list:
    """Watchlist sorted slightly softer than Top Plays."""
    return sorted(
        plays,
        key=lambda p: (
            p.get("true_confidence", 0),
            p.get("edge", 0),
        ),
        reverse=True,
    )


def _sort_ai_slip(plays: list) -> list:
    """AI Slip sorted by ai_score only."""
    return sorted(
        plays,
        key=lambda p: p.get("ai_score", 0),
        reverse=True,
    )


def _apply_ai_to_all_categories():
    """Enrich all categories with AI engine."""
    for key in ["Top Plays", "Watchlist", "AI Slip"]:
        raw = st.session_state.today_plays.get(key, [])
        enriched = enrich_play_list(raw)
        st.session_state.today_plays[key] = enriched


def _rebuild_snapshots():
    """Sort, dedupe, and finalize today's snapshot."""
    top_raw = st.session_state.today_plays["Top Plays"]
    watch_raw = st.session_state.today_plays["Watchlist"]
    slip_raw = st.session_state.today_plays["AI Slip"]

    # Deduplicate
    top_raw = _dedupe_by_id(top_raw)
    watch_raw = _dedupe_by_id(watch_raw)
    slip_raw = _dedupe_by_id(slip_raw)

    # Sort
    top_sorted = _sort_top_plays(top_raw)
    watch_sorted = _sort_watchlist(watch_raw)
    slip_sorted = _sort_ai_slip(slip_raw)

    # Limit sizes
    top_sorted = top_sorted[:10]
    watch_sorted = watch_sorted[:18]
    slip_sorted = slip_sorted[:5]

    # Save back
    st.session_state.today_plays["Top Plays"] = top_sorted
    st.session_state.today_plays["Watchlist"] = watch_sorted
    st.session_state.today_plays["AI Slip"] = slip_sorted


def full_refresh():
    """
    Unified refresh:
    - Reset if new date
    - Pull odds (stub)
    - Pull SportsDataIO context (stub)
    - Generate raw plays (mock for now)
    - Apply AI engine (true prob, edge, confidence)
    - Sort + dedupe + finalize snapshot
    """
    _reset_today_if_new_date()

    sport = st.session_state.selected_sport

    # STEP 1 — Generate raw mock plays (will be replaced with real API data)
    top_raw = [_generate_mock_play(i, sport, "Top") for i in range(1, 8)]
    watch_raw = [_generate_mock_play(i, sport, "Watch") for i in range(1, 10)]
    slip_raw = [_generate_mock_play(i, sport, "Slip") for i in range(1, 6)]

    st.session_state.today_plays["Top Plays"] = top_raw
    st.session_state.today_plays["Watchlist"] = watch_raw
    st.session_state.today_plays["AI Slip"] = slip_raw

    # STEP 2 — Apply AI engine
    _apply_ai_to_all_categories()

    # STEP 3 — Sort + dedupe + finalize snapshot
    _rebuild_snapshots()

    st.success("Full refresh completed. AI snapshot rebuilt for today.")
# ------------- CHUNK 6: DATA PIPELINE HOOKS (ODDS API + SDIO + QWEN) -------------

import random
import uuid

# -----------------------------
# PLAY OBJECT BUILDER (UNIFIED)
# -----------------------------
def _build_play(
    sport: str,
    game: str,
    market: str,
    selection: str,
    odds: int,
    source="mock",
):
    """
    Unified play object used across:
    - Odds API
    - SportsDataIO
    - Qwen reasoning
    - Mock generator
    """
    return {
        "id": str(uuid.uuid4()),
        "sport": sport,
        "game": game,
        "market": market,
        "selection": selection,
        "odds": odds,
        "source": source,
    }


# -----------------------------
# MOCK PLAY GENERATOR (TEMP)
# -----------------------------
def _generate_mock_play(i: int, sport: str, tier: str):
    """
    Temporary mock generator until real API data is wired in.
    """
    game = f"Team {i} @ Team {i+1}"
    market = random.choice(["moneyline", "spread", "total"])
    selection = random.choice(["Over", "Under", "Home", "Away"])
    odds = random.choice([-120, -115, -110, -105, 100, 110, 120])

    return _build_play(
        sport=sport,
        game=game,
        market=market,
        selection=selection,
        odds=odds,
        source="mock",
    )


# -----------------------------
# ODDS API HOOK (STUB)
# -----------------------------
def _fetch_odds_api(sport: str) -> list:
    """
    Placeholder for real Odds API integration.
    Should return a list of unified play objects.
    """
    # TODO: Replace with real Odds API call
    return []


# -----------------------------
# SPORTSDATAIO HOOK (STUB)
# -----------------------------
def _fetch_sportsdataio_context(sport: str) -> dict:
    """
    Placeholder for real SportsDataIO integration.
    Should return context such as:
    - injuries
    - lineups
    - weather
    - matchup notes
    """
    # TODO: Replace with real SDIO call
    return {}


# -----------------------------
# QWEN REASONING HOOK (STUB)
# -----------------------------
def _apply_qwen_reasoning(plays: list, context: dict) -> list:
    """
    Placeholder for Qwen 3.6 reasoning layer.
    Should:
    - analyze plays
    - adjust confidence
    - add tags
    - filter out bad plays
    """
    # TODO: Replace with real Qwen call
    # For now, return plays unchanged
    return plays


# -----------------------------
# UNIFIED DATA PIPELINE
# -----------------------------
def _pipeline_generate_raw_plays(sport: str) -> dict:
    """
    Returns:
        {
            "Top Plays": [...],
            "Watchlist": [...],
            "AI Slip": [...],
        }
    """

    # STEP 1 — Odds API (stub)
    odds_plays = _fetch_odds_api(sport)

    # STEP 2 — SportsDataIO context (stub)
    context = _fetch_sportsdataio_context(sport)

    # STEP 3 — Qwen reasoning (stub)
    enriched = _apply_qwen_reasoning(odds_plays, context)

    # STEP 4 — TEMP: fallback to mock plays if no real data yet
    if not enriched:
        top_raw = [_generate_mock_play(i, sport, "Top") for i in range(1, 8)]
        watch_raw = [_generate_mock_play(i, sport, "Watch") for i in range(1, 10)]
        slip_raw = [_generate_mock_play(i, sport, "Slip") for i in range(1, 6)]
    else:
        # When real data arrives, categorize here
        top_raw = enriched[:10]
        watch_raw = enriched[10:28]
        slip_raw = enriched[:5]

    return {
        "Top Plays": top_raw,
        "Watchlist": watch_raw,
        "AI Slip": slip_raw,
    }


# -----------------------------
# DAILY RESET HANDLER
# -----------------------------
def _reset_today_if_new_date():
    today = date.today()
    if st.session_state.today != today:
        st.session_state.today = today
        st.session_state.today_plays = {
            "Top Plays": [],
            "Watchlist": [],
            "AI Slip": [],
        }
# ------------- CHUNK 7: CATEGORIZATION ENGINE (TOP / WATCHLIST / AI SLIP) -------------

# Thresholds (can be made adaptive later)
THRESHOLDS = {
    "top_conf": 70,        # minimum true_confidence for Top Plays
    "top_edge": 3.0,       # minimum edge %
    "watch_conf": 55,      # minimum true_confidence for Watchlist
    "watch_edge": 1.0,     # minimum edge %
    "slip_conf": 75,       # minimum true_confidence for AI Slip
    "slip_edge": 4.0,      # minimum edge %
}


def _categorize_play(play: dict) -> str:
    """
    Decide whether a play belongs in:
    - Top Plays
    - Watchlist
    - AI Slip
    """

    conf = play.get("true_confidence", 0)
    edge = play.get("edge", 0)

    # AI Slip (highest tier)
    if conf >= THRESHOLDS["slip_conf"] and edge >= THRESHOLDS["slip_edge"]:
        return "AI Slip"

    # Top Plays
    if conf >= THRESHOLDS["top_conf"] and edge >= THRESHOLDS["top_edge"]:
        return "Top Plays"

    # Watchlist
    if conf >= THRESHOLDS["watch_conf"] and edge >= THRESHOLDS["watch_edge"]:
        return "Watchlist"

    # Otherwise ignore
    return "IGNORE"


def _categorize_all_plays(plays: list) -> dict:
    """
    Takes a list of enriched plays and returns:
    {
        "Top Plays": [...],
        "Watchlist": [...],
        "AI Slip": [...],
    }
    """

    buckets = {
        "Top Plays": [],
        "Watchlist": [],
        "AI Slip": [],
    }

    for p in plays:
        tier = _categorize_play(p)
        if tier in buckets:
            buckets[tier].append(p)

    return buckets


def _merge_pipeline_with_ai(sport: str):
    """
    Full categorization pipeline:
    1. Generate raw plays (Odds API + SDIO + Qwen stub)
    2. Enrich with AI engine (true prob, edge, confidence)
    3. Categorize into Top / Watchlist / Slip
    4. Sort + dedupe (Chunk 5)
    """

    # STEP 1 — raw plays
    raw_dict = _pipeline_generate_raw_plays(sport)

    # Combine all raw plays into one list for AI enrichment
    combined_raw = (
        raw_dict["Top Plays"]
        + raw_dict["Watchlist"]
        + raw_dict["AI Slip"]
    )

    # STEP 2 — AI enrichment
    enriched = enrich_play_list(combined_raw)

    # STEP 3 — Categorize
    categorized = _categorize_all_plays(enriched)

    # STEP 4 — Save into session_state
    st.session_state.today_plays["Top Plays"] = categorized["Top Plays"]
    st.session_state.today_plays["Watchlist"] = categorized["Watchlist"]
    st.session_state.today_plays["AI Slip"] = categorized["AI Slip"]

    # STEP 5 — Sort + dedupe (Chunk 5)
    _rebuild_snapshots()
# ------------- CHUNK 8: FINAL V36 REFRESH PIPELINE -------------

def full_refresh():
    """
    FINAL V36 REFRESH PIPELINE
    --------------------------------
    This is the real unified refresh:
    1. Reset if new date
    2. Generate raw plays (Odds API + SDIO + Qwen stubs)
    3. Enrich with AI engine (true prob, edge, confidence)
    4. Categorize (Top / Watchlist / Slip)
    5. Sort + dedupe + finalize snapshot
    6. Update session state cleanly
    """

    # STEP 0 — Daily reset
    _reset_today_if_new_date()

    sport = st.session_state.selected_sport

    # STEP 1–5 — Full pipeline
    _merge_pipeline_with_ai(sport)

    # STEP 6 — Success message
    st.success(f"V36 Refresh complete — snapshot rebuilt for {sport}.")
# ------------- CHUNK 9: PARLAY ENGINE V36 (CORRELATION + RISK + UNIT SIZING) -------------

import itertools

# Parlay configuration
PARLAY_CONFIG = {
    "max_legs": 4,
    "min_conf": 65,        # minimum true_confidence for a leg
    "min_edge": 2.0,       # minimum edge for a leg
    "max_risk_score": 75,  # maximum allowed risk score for a parlay
}


def _parlay_leg_ok(play: dict) -> bool:
    """Check if a play is eligible to be a parlay leg."""
    return (
        play.get("true_confidence", 0) >= PARLAY_CONFIG["min_conf"]
        and play.get("edge", 0) >= PARLAY_CONFIG["min_edge"]
    )


def _compute_leg_risk(play: dict) -> float:
    """
    Risk score for a single leg.
    Lower is better.
    """
    conf = play.get("true_confidence", 0)
    edge = play.get("edge", 0)

    # Lower confidence → higher risk
    risk = 100 - conf

    # Low edge → penalty
    if edge < 3:
        risk += 8

    # Moneyline favorites get slight bonus
    if play.get("odds", 0) < 0:
        risk -= 3

    return max(0, min(100, risk))


def _compute_parlay_correlation(legs: list) -> float:
    """
    Correlation score between legs.
    Higher correlation = higher risk.
    """
    score = 0

    for a, b in itertools.combinations(legs, 2):
        # Same game → high correlation
        if a["game"] == b["game"]:
            score += 25

        # Same team → moderate correlation
        if a["selection"] == b["selection"]:
            score += 10

        # Same market type → small correlation
        if a["market"] == b["market"]:
            score += 5

    return score


def _compute_parlay_risk(legs: list) -> float:
    """
    Total parlay risk score:
    - Leg risk
    - Correlation risk
    """
    leg_risk = sum(_compute_leg_risk(p) for p in legs)
    corr_risk = _compute_parlay_correlation(legs)

    total = leg_risk + corr_risk
    return max(0, min(200, total))


def _compute_parlay_units(risk_score: float) -> float:
    """
    Unit sizing based on risk.
    Lower risk → higher units.
    """
    if risk_score < 60:
        return 1.0
    if risk_score < 90:
        return 0.5
    return 0.25


def _build_parlay_object(legs: list) -> dict:
    """Return a clean parlay object."""
    risk = _compute_parlay_risk(legs)
    units = _compute_parlay_units(risk)

    return {
        "legs": legs,
        "risk_score": risk,
        "units": units,
        "num_legs": len(legs),
    }


def generate_parlay_candidates():
    """
    Build parlay candidates from today's Top Plays + AI Slip.
    """
    top_plays = st.session_state.today_plays.get("Top Plays", [])
    slip_plays = st.session_state.today_plays.get("AI Slip", [])

    # Combine eligible plays
    eligible = [p for p in (top_plays + slip_plays) if _parlay_leg_ok(p)]

    if len(eligible) < 2:
        return []

    parlays = []

    # Build 2–4 leg parlays
    for r in range(2, PARLAY_CONFIG["max_legs"] + 1):
        for combo in itertools.combinations(eligible, r):
            legs = list(combo)
            parlay = _build_parlay_object(legs)

            # Risk filter
            if parlay["risk_score"] <= PARLAY_CONFIG["max_risk_score"]:
                parlays.append(parlay)

    # Sort by lowest risk
    parlays = sorted(parlays, key=lambda p: p["risk_score"])

    # Limit to top 10
    return parlays[:10]
# ------------- CHUNK 10: PARLAY UI RENDERER + LOGGING -------------

def _log_parlay(parlay: dict):
    """
    Append-only parlay logging.
    Prevents duplicates for the same parlay on the same date.
    """
    today = st.session_state.today.isoformat()

    # Create a stable parlay signature
    leg_ids = tuple(sorted([leg["id"] for leg in parlay["legs"]]))
    signature = (leg_ids, today)

    existing = {
        (tuple(sorted(b.get("leg_ids", []))), b["date"])
        for b in st.session_state.bet_log
        if b.get("is_parlay")
    }

    if signature in existing:
        st.warning("This parlay is already logged for today.")
        return

    st.session_state.bet_log.append(
        {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "date": today,
            "is_parlay": True,
            "leg_ids": list(leg_ids),
            "legs": parlay["legs"],
            "risk_score": parlay["risk_score"],
            "units": parlay["units"],
            "num_legs": parlay["num_legs"],
            "result": None,
        }
    )

    st.success("Parlay added to Bet Log.")


def render_parlay_section():
    """
    UI renderer for parlay candidates.
    """
    st.header("Parlay Builder (AI‑Assisted)")
    st.caption("Automatically generated parlays based on confidence, edge, and correlation.")

    parlays = generate_parlay_candidates()

    if not parlays:
        st.info("No eligible parlay candidates today.")
        return

    for idx, parlay in enumerate(parlays):
        with st.container():
            st.subheader(f"Parlay #{idx + 1} — {parlay['num_legs']} legs")

            # Risk + units
            cols = st.columns([2, 2, 2])
            with cols[0]:
                st.metric("Risk Score", parlay["risk_score"])
            with cols[1]:
                st.metric("Units", parlay["units"])
            with cols[2]:
                st.metric("Legs", parlay["num_legs"])

            st.markdown("**Legs:**")

            # Display each leg
            for leg in parlay["legs"]:
                with st.container():
                    leg_cols = st.columns([3, 2, 2, 2])
                    with leg_cols[0]:
                        st.markdown(f"**{leg['selection']}**")
                        st.caption(f"{leg['game']} • {leg['market']}")
                    with leg_cols[1]:
                        st.metric("Odds", leg["odds"])
                    with leg_cols[2]:
                        st.metric("Conf.", leg.get("true_confidence", 0))
                    with leg_cols[3]:
                        st.metric("Edge %", leg.get("edge", 0))

            # Log parlay button
            if st.button(
                f"Log Parlay #{idx + 1}",
                key=f"log_parlay_{idx}",
                use_container_width=True,
            ):
                _log_parlay(parlay)

        st.markdown("---")
# ------------- CHUNK 11: PARLAY TAB INTEGRATION -------------

# Extend navigation tabs
if "nav_tabs_extended" not in st.session_state:
    # Only extend once
    NAV_TABS.append("Parlay Builder")
    st.session_state.nav_tabs_extended = True


# Update navigation rendering to include Parlay Builder
def render_navigation():
    st.markdown("### Navigation")
    nav_choice = st.radio(
        "Navigation",
        NAV_TABS,
        index=NAV_TABS.index(st.session_state.selected_tab),
        horizontal=True,
        label_visibility="collapsed",
    )
    st.session_state.selected_tab = nav_choice


# Replace your old nav radio with this call:
# (You can simply swap the old radio block with render_navigation())

# ------------- MAIN ROUTER EXTENSION -------------

def render_main_router():
    """
    Unified router including the new Parlay Builder tab.
    """
    tab = st.session_state.selected_tab

    if tab == "Top Plays":
        st.header("Top Plays")
        render_top_plays()

    elif tab == "Watchlist":
        st.header("Watchlist")
        render_watchlist()

    elif tab == "AI Slip":
        st.header("AI Slip")
        render_ai_slip()

    elif tab == "Bet Log":
        st.header("Bet Log")
        render_bet_log()

    elif tab == "Parlay Builder":
        render_parlay_section()
# ------------- CHUNK 12: BET SETTLEMENT ENGINE + ROI TRACKING -------------

def _settle_single_bet(bet: dict, result: str):
    """
    Settle a single-leg bet.
    result ∈ {"WIN", "LOSS", "PUSH"}
    """
    odds = bet.get("odds", 0)
    stake = bet.get("stake", 0)

    if result == "WIN":
        # American odds payout
        if odds > 0:
            profit = stake * (odds / 100)
        else:
            profit = stake / (abs(odds) / 100)
    elif result == "LOSS":
        profit = -stake
    else:  # PUSH
        profit = 0

    bet["result"] = result
    bet["profit"] = round(profit, 2)
    bet["roi"] = round((profit / stake) * 100, 2) if stake > 0 else 0


def _settle_parlay(bet: dict, result: str):
    """
    Settle a parlay.
    result ∈ {"WIN", "LOSS", "PUSH"}
    """
    units = bet.get("units", 1.0)
    stake = units  # 1 unit = 1 stake

    if result == "WIN":
        # Simple parlay payout multiplier (stub)
        multiplier = 2.5 + (0.25 * bet.get("num_legs", 2))
        profit = stake * multiplier
    elif result == "LOSS":
        profit = -stake
    else:  # PUSH
        profit = 0

    bet["result"] = result
    bet["profit"] = round(profit, 2)
    bet["roi"] = round((profit / stake) * 100, 2) if stake > 0 else 0


def render_settlement_controls():
    """
    UI for settling bets and parlays.
    """
    st.header("Settle Bets")
    st.caption("Mark bets as WIN / LOSS / PUSH to update ROI and history.")

    log = st.session_state.bet_log

    if not log:
        st.info("No bets to settle yet.")
        return

    for idx, bet in enumerate(log):
        with st.container():
            st.markdown(f"### Bet #{idx + 1}")

            # Display bet summary
            if bet.get("is_parlay"):
                st.markdown("**Parlay**")
                st.write(f"Legs: {bet['num_legs']}")
                st.write(f"Units: {bet['units']}")
                st.write(f"Risk Score: {bet['risk_score']}")
            else:
                st.markdown(f"**{bet.get('selection', 'Unknown')}**")
                st.caption(f"{bet.get('sport', '')} • {bet.get('market', '')}")
                st.write(f"Odds: {bet.get('odds')}")
                st.write(f"Stake: {bet.get('stake')}")

            # Already settled?
            if bet.get("result") is not None:
                st.success(f"Settled: {bet['result']} • Profit: {bet['profit']} • ROI: {bet['roi']}%")
                st.markdown("---")
                continue

            # Settlement buttons
            cols = st.columns(3)
            if cols[0].button("WIN", key=f"settle_win_{idx}"):
                if bet.get("is_parlay"):
                    _settle_parlay(bet, "WIN")
                else:
                    _settle_single_bet(bet, "WIN")
                st.experimental_rerun()

            if cols[1].button("LOSS", key=f"settle_loss_{idx}"):
                if bet.get("is_parlay"):
                    _settle_parlay(bet, "LOSS")
                else:
                    _settle_single_bet(bet, "LOSS")
                st.experimental_rerun()

            if cols[2].button("PUSH", key=f"settle_push_{idx}"):
                if bet.get("is_parlay"):
                    _settle_parlay(bet, "PUSH")
                else:
                    _settle_single_bet(bet, "PUSH")
                st.experimental_rerun()

        st.markdown("---")
# ------------- CHUNK 13: ROI DASHBOARD + PERFORMANCE ANALYTICS -------------

def _compute_performance_metrics():
    """
    Computes:
    - total bets
    - win rate
    - total profit
    - total units risked
    - ROI %
    - parlay vs single performance
    """
    log = st.session_state.bet_log
    if not log:
        return None

    total_bets = len(log)
    settled = [b for b in log if b.get("result") is not None]

    if not settled:
        return None

    wins = [b for b in settled if b["result"] == "WIN"]
    losses = [b for b in settled if b["result"] == "LOSS"]
    pushes = [b for b in settled if b["result"] == "PUSH"]

    total_profit = sum(b.get("profit", 0) for b in settled)

    # Units risked
    total_units = 0
    for b in settled:
        if b.get("is_parlay"):
            total_units += b.get("units", 1.0)
        else:
            total_units += b.get("stake", 0)

    roi = (total_profit / total_units) * 100 if total_units > 0 else 0

    # Parlay performance
    parlay_settled = [b for b in settled if b.get("is_parlay")]
    single_settled = [b for b in settled if not b.get("is_parlay")]

    parlay_profit = sum(b.get("profit", 0) for b in parlay_settled)
    single_profit = sum(b.get("profit", 0) for b in single_settled)

    return {
        "total_bets": total_bets,
        "settled": len(settled),
        "wins": len(wins),
        "losses": len(losses),
        "pushes": len(pushes),
        "win_rate": round((len(wins) / len(settled)) * 100, 2),
        "total_profit": round(total_profit, 2),
        "total_units": round(total_units, 2),
        "roi": round(roi, 2),
        "parlay_profit": round(parlay_profit, 2),
        "single_profit": round(single_profit, 2),
    }


def render_roi_dashboard():
    """
    UI for performance analytics.
    """
    st.header("Performance Dashboard")
    st.caption("Track ROI, win rate, and profitability across all bets.")

    metrics = _compute_performance_metrics()

    if not metrics:
        st.info("No settled bets yet — settle bets to unlock analytics.")
        return

    # Top-level metrics
    cols = st.columns(4)
    with cols[0]:
        st.metric("Total Bets", metrics["total_bets"])
    with cols[1]:
        st.metric("Settled", metrics["settled"])
    with cols[2]:
        st.metric("Win Rate", f"{metrics['win_rate']}%")
    with cols[3]:
        st.metric("ROI", f"{metrics['roi']}%")

    st.markdown("---")

    # Profit metrics
    cols2 = st.columns(3)
    with cols2[0]:
        st.metric("Total Profit", metrics["total_profit"])
    with cols2[1]:
        st.metric("Single Bet Profit", metrics["single_profit"])
    with cols2[2]:
        st.metric("Parlay Profit", metrics["parlay_profit"])

    st.markdown("---")

    # Breakdown
    st.subheader("Breakdown")
    st.write(f"**Wins:** {metrics['wins']}")
    st.write(f"**Losses:** {metrics['losses']}")
    st.write(f"**Pushes:** {metrics['pushes']}")

    st.markdown("---")

    st.caption("Analytics update automatically as bets are settled.")
# ------------- CHUNK 14: VISUALIZATION LAYER (CHARTS + GRAPHS) -------------

import pandas as pd
import altair as alt


def _build_bet_dataframe():
    """
    Convert bet_log into a clean DataFrame for charting.
    Only settled bets are included.
    """
    log = st.session_state.bet_log
    settled = [b for b in log if b.get("result") is not None]

    if not settled:
        return None

    rows = []
    for b in settled:
        is_parlay = b.get("is_parlay", False)
        stake = b.get("units", 1.0) if is_parlay else b.get("stake", 0)
        profit = b.get("profit", 0)

        rows.append({
            "date": b["date"],
            "timestamp": b["timestamp"],
            "is_parlay": is_parlay,
            "stake": stake,
            "profit": profit,
            "roi": b.get("roi", 0),
            "result": b["result"],
        })

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    return df


def render_visualizations():
    """
    Visualization layer for performance analytics.
    """
    st.header("Performance Visualizations")
    st.caption("Charts update automatically as bets are settled.")

    df = _build_bet_dataframe()
    if df is None or df.empty:
        st.info("No settled bets yet — settle bets to unlock charts.")
        return

    # -----------------------------
    # Profit Over Time
    # -----------------------------
    df["cumulative_profit"] = df["profit"].cumsum()

    st.subheader("Profit Over Time")
    profit_chart = (
        alt.Chart(df)
        .mark_line(point=True)
        .encode(
            x="date:T",
            y="cumulative_profit:Q",
            tooltip=["date:T", "cumulative_profit:Q"],
        )
        .properties(height=300)
    )
    st.altair_chart(profit_chart, use_container_width=True)

    st.markdown("---")

    # -----------------------------
    # ROI Over Time
    # -----------------------------
    df["cumulative_units"] = df["stake"].cumsum()
    df["cumulative_roi"] = (df["cumulative_profit"] / df["cumulative_units"]) * 100

    st.subheader("ROI Over Time")
    roi_chart = (
        alt.Chart(df)
        .mark_line(point=True, color="green")
        .encode(
            x="date:T",
            y="cumulative_roi:Q",
            tooltip=["date:T", "cumulative_roi:Q"],
        )
        .properties(height=300)
    )
    st.altair_chart(roi_chart, use_container_width=True)

    st.markdown("---")

    # -----------------------------
    # Win/Loss Streak Chart
    # -----------------------------
    df["streak_value"] = df["result"].apply(
        lambda r: 1 if r == "WIN" else (-1 if r == "LOSS" else 0)
    )
    df["streak"] = df["streak_value"].cumsum()

    st.subheader("Win/Loss Streak")
    streak_chart = (
        alt.Chart(df)
        .mark_line(point=True, color="orange")
        .encode(
            x="date:T",
            y="streak:Q",
            tooltip=["date:T", "result:N", "streak:Q"],
        )
        .properties(height=300)
    )
    st.altair_chart(streak_chart, use_container_width=True)

    st.markdown("---")

    # -----------------------------
    # Parlay vs Single Profit
    # -----------------------------
    st.subheader("Parlay vs Single Profit")

    df_type = df.copy()
    df_type["type"] = df_type["is_parlay"].apply(lambda x: "Parlay" if x else "Single")

    type_chart = (
        alt.Chart(df_type)
        .mark_bar()
        .encode(
            x="type:N",
            y="profit:Q",
            color="type:N",
            tooltip=["type:N", "profit:Q"],
        )
        .properties(height=300)
    )
    st.altair_chart(type_chart, use_container_width=True)

    st.markdown("---")

    st.caption("Visualizations powered by Altair.")
# ------------- CHUNK 15: SETTINGS PANEL (V36 CONTROL CENTER) -------------

# Default settings (only initialized once)
DEFAULT_SETTINGS = {
    "odds_min": -200,
    "odds_max": 300,
    "top_conf": 70,
    "top_edge": 3.0,
    "watch_conf": 55,
    "watch_edge": 1.0,
    "slip_conf": 75,
    "slip_edge": 4.0,
    "parlay_max_risk": 75,
    "parlay_max_legs": 4,
    "enable_qwen": True,
    "enable_sdio": True,
}

if "settings" not in st.session_state:
    st.session_state.settings = DEFAULT_SETTINGS.copy()


def render_settings_panel():
    """
    UI for adjusting V36 engine settings.
    """
    st.header("Settings (V36 Control Center)")
    st.caption("Tune AI thresholds, odds bands, parlay rules, and data sources.")

    s = st.session_state.settings

    # -----------------------------
    # Odds Band
    # -----------------------------
    st.subheader("Odds Band")
    col1, col2 = st.columns(2)
    with col1:
        s["odds_min"] = st.number_input(
            "Minimum Odds",
            value=s["odds_min"],
            step=5,
        )
    with col2:
        s["odds_max"] = st.number_input(
            "Maximum Odds",
            value=s["odds_max"],
            step=5,
        )

    st.markdown("---")

    # -----------------------------
    # Confidence & Edge Thresholds
    # -----------------------------
    st.subheader("AI Thresholds")

    st.markdown("**Top Plays**")
    col3, col4 = st.columns(2)
    with col3:
        s["top_conf"] = st.number_input(
            "Top Plays — Min Confidence",
            value=s["top_conf"],
            step=1,
        )
    with col4:
        s["top_edge"] = st.number_input(
            "Top Plays — Min Edge %",
            value=s["top_edge"],
            step=0.5,
        )

    st.markdown("**Watchlist**")
    col5, col6 = st.columns(2)
    with col5:
        s["watch_conf"] = st.number_input(
            "Watchlist — Min Confidence",
            value=s["watch_conf"],
            step=1,
        )
    with col6:
        s["watch_edge"] = st.number_input(
            "Watchlist — Min Edge %",
            value=s["watch_edge"],
            step=0.5,
        )

    st.markdown("**AI Slip**")
    col7, col8 = st.columns(2)
    with col7:
        s["slip_conf"] = st.number_input(
            "AI Slip — Min Confidence",
            value=s["slip_conf"],
            step=1,
        )
    with col8:
        s["slip_edge"] = st.number_input(
            "AI Slip — Min Edge %",
            value=s["slip_edge"],
            step=0.5,
        )

    st.markdown("---")

    # -----------------------------
    # Parlay Settings
    # -----------------------------
    st.subheader("Parlay Settings")

    col9, col10 = st.columns(2)
    with col9:
        s["parlay_max_legs"] = st.number_input(
            "Max Parlay Legs",
            value=s["parlay_max_legs"],
            min_value=2,
            max_value=8,
            step=1,
        )
    with col10:
        s["parlay_max_risk"] = st.number_input(
            "Max Allowed Risk Score",
            value=s["parlay_max_risk"],
            step=5,
        )

    st.markdown("---")

    # -----------------------------
    # Data Source Toggles
    # -----------------------------
    st.subheader("Data Sources")

    s["enable_qwen"] = st.checkbox(
        "Enable Qwen Reasoning",
        value=s["enable_qwen"],
    )

    s["enable_sdio"] = st.checkbox(
        "Enable SportsDataIO Context",
        value=s["enable_sdio"],
    )

    st.markdown("---")

    st.success("Settings updated. These values persist for the session.")
# ------------- CHUNK 16: SETTINGS INTEGRATION LAYER -------------

def _apply_settings_to_thresholds():
    """
    Inject settings into categorization thresholds.
    """
    s = st.session_state.settings

    THRESHOLDS["top_conf"] = s["top_conf"]
    THRESHOLDS["top_edge"] = s["top_edge"]
    THRESHOLDS["watch_conf"] = s["watch_conf"]
    THRESHOLDS["watch_edge"] = s["watch_edge"]
    THRESHOLDS["slip_conf"] = s["slip_conf"]
    THRESHOLDS["slip_edge"] = s["slip_edge"]


def _apply_settings_to_parlay_engine():
    """
    Inject settings into parlay configuration.
    """
    s = st.session_state.settings

    PARLAY_CONFIG["max_legs"] = s["parlay_max_legs"]
    PARLAY_CONFIG["max_risk_score"] = s["parlay_max_risk"]


def _filter_by_odds_band(plays: list) -> list:
    """
    Remove plays outside the user-defined odds band.
    """
    s = st.session_state.settings
    min_odds = s["odds_min"]
    max_odds = s["odds_max"]

    filtered = []
    for p in plays:
        o = p.get("odds", 0)
        if min_odds <= o <= max_odds:
            filtered.append(p)

    return filtered


def _apply_settings_to_pipeline(raw_dict: dict) -> dict:
    """
    Apply odds band filtering to raw plays before AI enrichment.
    """
    for key in raw_dict:
        raw_dict[key] = _filter_by_odds_band(raw_dict[key])
    return raw_dict


def _maybe_apply_qwen(plays: list, context: dict) -> list:
    """
    Apply Qwen reasoning only if enabled.
    """
    if not st.session_state.settings["enable_qwen"]:
        return plays
    return _apply_qwen_reasoning(plays, context)


def _maybe_fetch_sdio(sport: str) -> dict:
    """
    Fetch SportsDataIO context only if enabled.
    """
    if not st.session_state.settings["enable_sdio"]:
        return {}
    return _fetch_sportsdataio_context(sport)


# -----------------------------
# OVERRIDE: Unified pipeline with settings
# -----------------------------
def _pipeline_generate_raw_plays(sport: str) -> dict:
    """
    Settings-aware pipeline:
    - Odds API (stub)
    - SportsDataIO (optional)
    - Qwen reasoning (optional)
    - Odds band filtering
    """

    # STEP 1 — Odds API (stub)
    odds_plays = _fetch_odds_api(sport)

    # STEP 2 — SportsDataIO (optional)
    context = _maybe_fetch_sdio(sport)

    # STEP 3 — Qwen reasoning (optional)
    enriched = _maybe_apply_qwen(odds_plays, context)

    # STEP 4 — TEMP fallback to mock plays
    if not enriched:
        top_raw = [_generate_mock_play(i, sport, "Top") for i in range(1, 8)]
        watch_raw = [_generate_mock_play(i, sport, "Watch") for i in range(1, 10)]
        slip_raw = [_generate_mock_play(i, sport, "Slip") for i in range(1, 6)]
    else:
        top_raw = enriched[:10]
        watch_raw = enriched[10:28]
        slip_raw = enriched[:5]

    raw_dict = {
        "Top Plays": top_raw,
        "Watchlist": watch_raw,
        "AI Slip": slip_raw,
    }

    # STEP 5 — Apply odds band filtering
    raw_dict = _apply_settings_to_pipeline(raw_dict)

    return raw_dict


# -----------------------------
# Inject settings into categorization + parlay engine
# -----------------------------
def _apply_all_settings():
    _apply_settings_to_thresholds()
    _apply_settings_to_parlay_engine()
# ------------- CHUNK 17: SETTINGS-AWARE REFRESH PIPELINE -------------

def full_refresh():
    """
    FINAL V36 REFRESH (SETTINGS-AWARE)
    ----------------------------------
    1. Apply all settings (thresholds, odds band, parlay rules)
    2. Reset if new date
    3. Generate raw plays (Odds API + SDIO + Qwen, all settings-aware)
    4. Apply AI engine (true prob, edge, confidence)
    5. Categorize plays (Top / Watchlist / Slip) using dynamic thresholds
    6. Sort + dedupe + finalize snapshot
    7. Success message
    """

    # STEP 1 — Apply settings to all engines
    _apply_all_settings()

    # STEP 2 — Daily reset
    _reset_today_if_new_date()

    sport = st.session_state.selected_sport

    # STEP 3 — Generate raw plays (settings-aware pipeline)
    raw_dict = _pipeline_generate_raw_plays(sport)

    # Combine raw plays for AI enrichment
    combined_raw = (
        raw_dict["Top Plays"]
        + raw_dict["Watchlist"]
        + raw_dict["AI Slip"]
    )

    # STEP 4 — AI enrichment
    enriched = enrich_play_list(combined_raw)

    # STEP 5 — Categorization (settings-aware)
    categorized = _categorize_all_plays(enriched)

    st.session_state.today_plays["Top Plays"] = categorized["Top Plays"]
    st.session_state.today_plays["Watchlist"] = categorized["Watchlist"]
    st.session_state.today_plays["AI Slip"] = categorized["AI Slip"]

    # STEP 6 — Sort + dedupe + finalize snapshot
    _rebuild_snapshots()

    # STEP 7 — Success message
    st.success(f"V36 Refresh complete — settings applied for {sport}.")
# ------------- CHUNK 18: MOBILE OPTIMIZATION LAYER -------------

def is_mobile_view():
    """
    Detect mobile layout by checking viewport width.
    Streamlit doesn't expose width directly, so we infer from user agent.
    """
    try:
        ua = st.context.headers.get("User-Agent", "").lower()
        return "iphone" in ua or "android" in ua or "mobile" in ua
    except:
        return False


def mobile_container():
    """
    Wrapper for mobile-friendly spacing.
    """
    st.markdown(
        """
        <style>
        .mobile-card {
            padding: 0.75rem 1rem;
            border-radius: 10px;
            background-color: #111111;
            margin-bottom: 0.75rem;
            border: 1px solid #333333;
        }
        .mobile-button button {
            padding: 0.6rem 0.8rem !important;
            font-size: 0.9rem !important;
        }
        .mobile-metric {
            font-size: 0.9rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_mobile_play_card(play: dict, source_tab: str, idx: int):
    """
    Compact mobile card for Top Plays / Watchlist / AI Slip.
    """
    with st.container():
        st.markdown('<div class="mobile-card">', unsafe_allow_html=True)

        st.markdown(f"**{play['selection']}**")
        st.caption(f"{play['game']} • {play['market']}")

        cols = st.columns(3)
        with cols[0]:
            st.metric("Odds", play["odds"])
        with cols[1]:
            st.metric("Conf.", play.get("true_confidence", 0))
        with cols[2]:
            st.metric("Edge %", play.get("edge", 0))

        stake = st.number_input(
            f"Stake_mobile_{source_tab}_{idx}",
            min_value=0.0,
            value=0.0,
            step=1.0,
            label_visibility="collapsed",
        )

        if st.button(
            "Log Bet",
            key=f"log_mobile_{source_tab}_{play['id']}",
            use_container_width=True,
        ):
            if stake <= 0:
                st.warning("Enter a stake greater than 0.")
            else:
                _log_bet(play, stake, source_tab)

        st.markdown("</div>", unsafe_allow_html=True)


def render_mobile_parlay_card(parlay: dict, idx: int):
    """
    Compact mobile card for parlays.
    """
    with st.container():
        st.markdown('<div class="mobile-card">', unsafe_allow_html=True)

        st.subheader(f"Parlay #{idx + 1}")
        st.caption(f"{parlay['num_legs']} legs • Risk {parlay['risk_score']} • Units {parlay['units']}")

        for leg in parlay["legs"]:
            st.markdown(f"**{leg['selection']}**")
            st.caption(f"{leg['game']} • {leg['market']} • Odds {leg['odds']}")

        if st.button(
            f"Log Parlay #{idx + 1}",
            key=f"log_mobile_parlay_{idx}",
            use_container_width=True,
        ):
            _log_parlay(parlay)

        st.markdown("</div>", unsafe_allow_html=True)
# ------------- CHUNK 19: MOBILE-AWARE ROUTER -------------

def render_mobile_tab(tab: str):
    """
    Mobile version of each tab.
    Uses compact cards from Chunk 18.
    """

    # -----------------------------
    # TOP PLAYS
    # -----------------------------
    if tab == "Top Plays":
        st.header("Top Plays (Mobile)")
        plays = st.session_state.today_plays.get("Top Plays", [])
        if not plays:
            st.info("No Top Plays available.")
            return
        for idx, p in enumerate(plays):
            render_mobile_play_card(p, "Top Plays", idx)

    # -----------------------------
    # WATCHLIST
    # -----------------------------
    elif tab == "Watchlist":
        st.header("Watchlist (Mobile)")
        plays = st.session_state.today_plays.get("Watchlist", [])
        if not plays:
            st.info("No Watchlist plays available.")
            return
        for idx, p in enumerate(plays):
            render_mobile_play_card(p, "Watchlist", idx)

    # -----------------------------
    # AI SLIP
    # -----------------------------
    elif tab == "AI Slip":
        st.header("AI Slip (Mobile)")
        plays = st.session_state.today_plays.get("AI Slip", [])
        if not plays:
            st.info("No AI Slip plays available.")
            return
        for idx, p in enumerate(plays):
            render_mobile_play_card(p, "AI Slip", idx)

    # -----------------------------
    # PARLAY BUILDER
    # -----------------------------
    elif tab == "Parlay Builder":
        st.header("Parlay Builder (Mobile)")
        parlays = generate_parlay_candidates()
        if not parlays:
            st.info("No parlay candidates available.")
            return
        for idx, parlay in enumerate(parlays):
            render_mobile_parlay_card(parlay, idx)

    # -----------------------------
    # BET LOG
    # -----------------------------
    elif tab == "Bet Log":
        st.header("Bet Log (Mobile)")
        log = st.session_state.bet_log
        if not log:
            st.info("No bets logged yet.")
            return

        for idx, bet in enumerate(log):
            with st.container():
                st.markdown('<div class="mobile-card">', unsafe_allow_html=True)

                if bet.get("is_parlay"):
                    st.markdown(f"**Parlay — {bet['num_legs']} legs**")
                    st.caption(f"Units: {bet['units']} • Risk: {bet['risk_score']}")
                else:
                    st.markdown(f"**{bet.get('selection', 'Unknown')}**")
                    st.caption(f"{bet.get('sport', '')} • {bet.get('market', '')}")
                    st.write(f"Odds: {bet.get('odds')}")
                    st.write(f"Stake: {bet.get('stake')}")

                if bet.get("result") is not None:
                    st.success(f"{bet['result']} • Profit {bet['profit']} • ROI {bet['roi']}%")
                else:
                    cols = st.columns(3)
                    if cols[0].button("WIN", key=f"mobile_win_{idx}"):
                        if bet.get("is_parlay"):
                            _settle_parlay(bet, "WIN")
                        else:
                            _settle_single_bet(bet, "WIN")
                        st.experimental_rerun()

                    if cols[1].button("LOSS", key=f"mobile_loss_{idx}"):
                        if bet.get("is_parlay"):
                            _settle_parlay(bet, "LOSS")
                        else:
                            _settle_single_bet(bet, "LOSS")
                        st.experimental_rerun()

                    if cols[2].button("PUSH", key=f"mobile_push_{idx}"):
                        if bet.get("is_parlay"):
                            _settle_parlay(bet, "PUSH")
                        else:
                            _settle_single_bet(bet, "PUSH")
                        st.experimental_rerun()

                st.markdown("</div>", unsafe_allow_html=True)


def render_main_router():
    """
    AUTO-SWITCHING ROUTER
    Desktop → full UI
    Mobile → compact UI
    """
    tab = st.session_state.selected_tab

    if is_mobile_view():
        mobile_container()
        render_mobile_tab(tab)
    else:
        # Desktop router (from Chunk 11)
        if tab == "Top Plays":
            st.header("Top Plays")
            render_top_plays()

        elif tab == "Watchlist":
            st.header("Watchlist")
            render_watchlist()

        elif tab == "AI Slip":
            st.header("AI Slip")
            render_ai_slip()

        elif tab == "Bet Log":
            st.header("Bet Log")
            render_bet_log()

        elif tab == "Parlay Builder":
            render_parlay_section()
# ------------- CHUNK 20: THEME ENGINE (DARK MODE + LIGHT MODE) -------------

# Default theme
if "theme" not in st.session_state:
    st.session_state.theme = "dark"   # default V36 look


def apply_theme():
    """
    Inject global CSS based on selected theme.
    """
    theme = st.session_state.theme

    if theme == "dark":
        st.markdown(
            """
            <style>
            body, .stApp {
                background-color: #0d0d0d !important;
                color: #f0f0f0 !important;
            }
            .stButton>button {
                background-color: #222222 !important;
                color: #ffffff !important;
                border-radius: 8px !important;
                border: 1px solid #444444 !important;
            }
            .stButton>button:hover {
                background-color: #333333 !important;
            }
            .stMetric {
                background-color: #111111 !important;
                border-radius: 10px !important;
                padding: 0.5rem !important;
            }
            .mobile-card {
                background-color: #111111 !important;
                border: 1px solid #333333 !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

    else:  # LIGHT MODE
        st.markdown(
            """
            <style>
            body, .stApp {
                background-color: #ffffff !important;
                color: #000000 !important;
            }
            .stButton>button {
                background-color: #f2f2f2 !important;
                color: #000000 !important;
                border-radius: 8px !important;
                border: 1px solid #cccccc !important;
            }
            .stButton>button:hover {
                background-color: #e6e6e6 !important;
            }
            .stMetric {
                background-color: #fafafa !important;
                border-radius: 10px !important;
                padding: 0.5rem !important;
            }
            .mobile-card {
                background-color: #fafafa !important;
                border: 1px solid #dddddd !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )


def render_theme_toggle():
    """
    UI toggle for switching between Dark and Light mode.
    """
    st.sidebar.markdown("### Theme")
    mode = st.sidebar.radio(
        "Appearance",
        ["dark", "light"],
        index=0 if st.session_state.theme == "dark" else 1,
        horizontal=True,
    )
    st.session_state.theme = mode
# ------------- CHUNK 21: THEME-AWARE COMPONENTS -------------

def themed_card_container():
    """
    Wraps content in a theme-aware card.
    """
    theme = st.session_state.theme
    if theme == "dark":
        bg = "#111111"
        border = "#333333"
        text = "#f0f0f0"
    else:
        bg = "#fafafa"
        border = "#dddddd"
        text = "#000000"

    st.markdown(
        f"""
        <style>
        .themed-card {{
            background-color: {bg};
            border: 1px solid {border};
            border-radius: 10px;
            padding: 1rem;
            margin-bottom: 1rem;
            color: {text};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def themed_metric(label: str, value, delta=None):
    """
    Theme-aware metric block.
    """
    theme = st.session_state.theme
    if theme == "dark":
        bg = "#111111"
        text = "#ffffff"
    else:
        bg = "#f5f5f5"
        text = "#000000"

    st.markdown(
        f"""
        <div style="
            background-color:{bg};
            padding:0.75rem;
            border-radius:10px;
            margin-bottom:0.5rem;
            color:{text};
        ">
            <div style="font-size:0.85rem; opacity:0.8;">{label}</div>
            <div style="font-size:1.4rem; font-weight:600;">{value}</div>
            {"<div style='font-size:0.8rem; opacity:0.7;'>"+delta+"</div>" if delta else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )


def themed_table(df):
    """
    Theme-aware table styling.
    """
    theme = st.session_state.theme
    if theme == "dark":
        header_bg = "#222222"
        row_bg = "#111111"
        text = "#ffffff"
    else:
        header_bg = "#f2f2f2"
        row_bg = "#ffffff"
        text = "#000000"

    st.markdown(
        f"""
        <style>
        .themed-table thead tr {{
            background-color: {header_bg} !important;
            color: {text} !important;
        }}
        .themed-table tbody tr {{
            background-color: {row_bg} !important;
            color: {text} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.table(df.style.set_table_attributes('class="themed-table"'))


def themed_parlay_card(parlay: dict, idx: int):
    """
    Theme-aware parlay card for desktop.
    """
    themed_card_container()

    with st.container():
        st.markdown('<div class="themed-card">', unsafe_allow_html=True)

        st.subheader(f"Parlay #{idx + 1}")
        st.caption(f"{parlay['num_legs']} legs • Risk {parlay['risk_score']} • Units {parlay['units']}")

        for leg in parlay["legs"]:
            st.markdown(f"**{leg['selection']}**")
            st.caption(f"{leg['game']} • {leg['market']} • Odds {leg['odds']}")

        if st.button(
            f"Log Parlay #{idx + 1}",
            key=f"log_parlay_themed_{idx}",
            use_container_width=True,
        ):
            _log_parlay(parlay)

        st.markdown("</div>", unsafe_allow_html=True)
# ------------- CHUNK 22: THEME-AWARE MOBILE COMPONENTS -------------

def themed_mobile_card(play_or_parlay: dict, is_parlay=False):
    """
    Theme-aware mobile card wrapper.
    """
    theme = st.session_state.theme

    if theme == "dark":
        bg = "#111111"
        border = "#333333"
        text = "#ffffff"
        subtext = "#cccccc"
    else:
        bg = "#fafafa"
        border = "#dddddd"
        text = "#000000"
        subtext = "#444444"

    st.markdown(
        f"""
        <style>
        .themed-mobile-card {{
            background-color: {bg};
            border: 1px solid {border};
            border-radius: 12px;
            padding: 1rem;
            margin-bottom: 1rem;
            color: {text};
        }}
        .themed-mobile-sub {{
            color: {subtext};
            font-size: 0.8rem;
        }}
        .themed-mobile-button button {{
            background-color: {border} !important;
            color: {text} !important;
            border-radius: 8px !important;
            padding: 0.6rem 0.8rem !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="themed-mobile-card">', unsafe_allow_html=True)

    # -----------------------------
    # PARLAY CARD
    # -----------------------------
    if is_parlay:
        st.subheader(f"Parlay — {play_or_parlay['num_legs']} legs")
        st.caption(f"Risk {play_or_parlay['risk_score']} • Units {play_or_parlay['units']}")

        for leg in play_or_parlay["legs"]:
            st.markdown(f"**{leg['selection']}**")
            st.markdown(
                f"<div class='themed-mobile-sub'>{leg['game']} • {leg['market']} • Odds {leg['odds']}</div>",
                unsafe_allow_html=True,
            )

        if st.button(
            "Log Parlay",
            key=f"log_parlay_mobile_themed_{play_or_parlay['num_legs']}",
            use_container_width=True,
        ):
            _log_parlay(play_or_parlay)

    # -----------------------------
    # SINGLE PLAY CARD
    # -----------------------------
    else:
        st.markdown(f"**{play_or_parlay['selection']}**")
        st.markdown(
            f"<div class='themed-mobile-sub'>{play_or_parlay['game']} • {play_or_parlay['market']}</div>",
            unsafe_allow_html=True,
        )

        cols = st.columns(3)
        with cols[0]:
            st.metric("Odds", play_or_parlay["odds"])
        with cols[1]:
            st.metric("Conf.", play_or_parlay.get("true_confidence", 0))
        with cols[2]:
            st.metric("Edge %", play_or_parlay.get("edge", 0))

        stake = st.number_input(
            f"stake_mobile_themed_{play_or_parlay['id']}",
            min_value=0.0,
            value=0.0,
            step=1.0,
            label_visibility="collapsed",
        )

        if st.button(
            "Log Bet",
            key=f"log_mobile_themed_{play_or_parlay['id']}",
            use_container_width=True,
        ):
            if stake <= 0:
                st.warning("Enter a stake greater than 0.")
            else:
                _log_bet(play_or_parlay, stake, "Mobile")

    st.markdown("</div>", unsafe_allow_html=True)


def render_mobile_tab_themed(tab: str):
    """
    Mobile router using theme-aware mobile components.
    """

    # TOP PLAYS
    if tab == "Top Plays":
        st.header("Top Plays (Mobile)")
        plays = st.session_state.today_plays.get("Top Plays", [])
        for p in plays:
            themed_mobile_card(p)

    # WATCHLIST
    elif tab == "Watchlist":
        st.header("Watchlist (Mobile)")
        plays = st.session_state.today_plays.get("Watchlist", [])
        for p in plays:
            themed_mobile_card(p)

    # AI SLIP
    elif tab == "AI Slip":
        st.header("AI Slip (Mobile)")
        plays = st.session_state.today_plays.get("AI Slip", [])
        for p in plays:
            themed_mobile_card(p)

    # PARLAY BUILDER
    elif tab == "Parlay Builder":
        st.header("Parlay Builder (Mobile)")
        parlays = generate_parlay_candidates()
        for parlay in parlays:
            themed_mobile_card(parlay, is_parlay=True)

    # BET LOG
    elif tab == "Bet Log":
        st.header("Bet Log (Mobile)")
        for bet in st.session_state.bet_log:
            themed_mobile_card(bet, is_parlay=bet.get("is_parlay", False))
# ------------- CHUNK 23: UNIFIED THEME-AWARE ROUTER -------------

def render_main_router():
    """
    FINAL V36 ROUTER
    ----------------
    - Applies theme
    - Detects mobile vs desktop
    - Routes to themed mobile or desktop UI
    """

    # Always apply theme first
    apply_theme()

    tab = st.session_state.selected_tab

    # MOBILE MODE
    if is_mobile_view():
        # Use the themed mobile renderer from Chunk 22
        render_mobile_tab_themed(tab)
        return

    # DESKTOP MODE (theme-aware)
    themed_card_container()  # ensures desktop cards match theme

    if tab == "Top Plays":
        st.header("Top Plays")
        render_top_plays()

    elif tab == "Watchlist":
        st.header("Watchlist")
        render_watchlist()

    elif tab == "AI Slip":
        st.header("AI Slip")
        render_ai_slip()

    elif tab == "Bet Log":
        st.header("Bet Log")
        render_bet_log()

    elif tab == "Parlay Builder":
        render_parlay_section()

    elif tab == "Settings":
        render_settings_panel()

    elif tab == "Performance":
        render_roi_dashboard()
# ------------- CHUNK 24: HYBRID NAVIGATION SYSTEM -------------

NAV_ITEMS = [
    "Top Plays",
    "Watchlist",
    "AI Slip",
    "Parlay Builder",
    "Bet Log",
    "Performance",
    "Settings",
]


def apply_nav_styles():
    """
    Theme-aware navigation styling.
    """
    theme = st.session_state.theme

    if theme == "dark":
        bg = "#0d0d0d"
        text = "#ffffff"
        hover = "#222222"
        border = "#333333"
    else:
        bg = "#ffffff"
        text = "#000000"
        hover = "#f2f2f2"
        border = "#cccccc"

    st.markdown(
        f"""
        <style>
        .topbar {{
            display: flex;
            gap: 1rem;
            padding: 0.75rem 1rem;
            background-color: {bg};
            border-bottom: 1px solid {border};
        }}
        .topbar-item {{
            padding: 0.5rem 0.75rem;
            border-radius: 6px;
            cursor: pointer;
            color: {text};
            font-weight: 500;
        }}
        .topbar-item:hover {{
            background-color: {hover};
        }}
        .topbar-active {{
            background-color: {hover};
            font-weight: 700;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_topbar_navigation():
    """
    Desktop topbar navigation.
    """
    apply_nav_styles()

    st.markdown('<div class="topbar">', unsafe_allow_html=True)

    for item in NAV_ITEMS:
        active = "topbar-active" if st.session_state.selected_tab == item else "topbar-item"
        if st.markdown(
            f"<span class='{active}'>{item}</span>",
            unsafe_allow_html=True,
        ):
            pass

    st.markdown("</div>", unsafe_allow_html=True)

    # Click detection hack (Streamlit limitation)
    clicked = st.radio(
        "Navigation",
        NAV_ITEMS,
        index=NAV_ITEMS.index(st.session_state.selected_tab),
        label_visibility="collapsed",
        horizontal=True,
    )
    st.session_state.selected_tab = clicked


def render_sidebar_navigation():
    """
    Mobile sidebar navigation.
    """
    st.sidebar.markdown("### Navigation")

    choice = st.sidebar.radio(
        "Go to",
        NAV_ITEMS,
        index=NAV_ITEMS.index(st.session_state.selected_tab),
    )
    st.session_state.selected_tab = choice
# ------------- CHUNK 25: DAILY SNAPSHOT SYSTEM -------------

# Initialize snapshot storage
if "snapshots" not in st.session_state:
    st.session_state.snapshots = {}   # { "YYYY-MM-DD": { ...plays... } }


def _save_daily_snapshot():
    """
    Save today's plays into a historical snapshot.
    Called automatically after full_refresh().
    """
    today = st.session_state.today.isoformat()

    snapshot = {
        "Top Plays": st.session_state.today_plays.get("Top Plays", []),
        "Watchlist": st.session_state.today_plays.get("Watchlist", []),
        "AI Slip": st.session_state.today_plays.get("AI Slip", []),
        "Parlays": generate_parlay_candidates(),  # snapshot parlay candidates too
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    st.session_state.snapshots[today] = snapshot


def _load_snapshot(date_str: str):
    """
    Return snapshot for a given date.
    """
    return st.session_state.snapshots.get(date_str)


def render_snapshot_viewer():
    """
    UI for browsing historical snapshots.
    """
    st.header("Historical Snapshots")
    st.caption("View past days of Top Plays, Watchlist, AI Slip, and Parlay candidates.")

    if not st.session_state.snapshots:
        st.info("No snapshots saved yet.")
        return

    # Sort dates newest → oldest
    dates = sorted(st.session_state.snapshots.keys(), reverse=True)

    selected_date = st.selectbox("Select a date", dates)

    snap = _load_snapshot(selected_date)
    if not snap:
        st.warning("Snapshot not found.")
        return

    st.subheader(f"Snapshot for {selected_date}")
    st.caption(f"Saved at {snap['timestamp']}")

    st.markdown("---")

    # Top Plays
    st.markdown("### Top Plays")
    for p in snap["Top Plays"]:
        themed_card_container()
        st.markdown(f"**{p['selection']}** — Odds {p['odds']} • Conf {p.get('true_confidence', 0)} • Edge {p.get('edge', 0)}")

    st.markdown("---")

    # Watchlist
    st.markdown("### Watchlist")
    for p in snap["Watchlist"]:
        themed_card_container()
        st.markdown(f"**{p['selection']}** — Odds {p['odds']} • Conf {p.get('true_confidence', 0)} • Edge {p.get('edge', 0)}")

    st.markdown("---")

    # AI Slip
    st.markdown("### AI Slip")
    for p in snap["AI Slip"]:
        themed_card_container()
        st.markdown(f"**{p['selection']}** — Odds {p['odds']} • Conf {p.get('true_confidence', 0)} • Edge {p.get('edge', 0)}")

    st.markdown("---")

    # Parlays
    st.markdown("### Parlay Candidates")
    for idx, parlay in enumerate(snap["Parlays"]):
        themed_parlay_card(parlay, idx)


# -----------------------------
# Inject snapshot saving into refresh pipeline
# -----------------------------
_prev_full_refresh = full_refresh

def full_refresh():
    """
    Wrap original full_refresh with snapshot saving.
    """
    _prev_full_refresh()   # run original logic
    _save_daily_snapshot() # save snapshot after refresh
# ------------- CHUNK 26: SNAPSHOT COMPARISON ENGINE -------------

def _compare_play_lists(list_a: list, list_b: list):
    """
    Compare two lists of plays and return:
    - added plays
    - removed plays
    - unchanged plays
    """
    ids_a = {p["id"]: p for p in list_a}
    ids_b = {p["id"]: p for p in list_b}

    added = [ids_b[i] for i in ids_b if i not in ids_a]
    removed = [ids_a[i] for i in ids_a if i not in ids_b]
    unchanged = [ids_a[i] for i in ids_a if i in ids_b]

    return added, removed, unchanged


def _compare_parlays(parlays_a: list, parlays_b: list):
    """
    Compare parlay candidates by leg signatures.
    """
    def sig(parlay):
        return tuple(sorted([leg["id"] for leg in parlay["legs"]]))

    sig_a = {sig(p): p for p in parlays_a}
    sig_b = {sig(p): p for p in parlays_b}

    added = [sig_b[s] for s in sig_b if s not in sig_a]
    removed = [sig_a[s] for s in sig_a if s not in sig_b]
    unchanged = [sig_a[s] for s in sig_a if s in sig_b]

    return added, removed, unchanged


def render_snapshot_comparison():
    """
    UI for comparing two historical snapshots.
    """
    st.header("Snapshot Comparison")
    st.caption("Compare two days of AI output to see what changed.")

    snaps = st.session_state.snapshots
    if not snaps:
        st.info("No snapshots available.")
        return

    dates = sorted(snaps.keys(), reverse=True)

    col1, col2 = st.columns(2)
    with col1:
        date_a = st.selectbox("Snapshot A", dates)
    with col2:
        date_b = st.selectbox("Snapshot B", dates, index=1 if len(dates) > 1 else 0)

    if date_a == date_b:
        st.warning("Select two different dates.")
        return

    snap_a = snaps[date_a]
    snap_b = snaps[date_b]

    st.markdown(f"### Comparing {date_a} → {date_b}")
    st.markdown("---")

    # -----------------------------
    # TOP PLAYS
    # -----------------------------
    st.subheader("Top Plays")
    added, removed, _ = _compare_play_lists(snap_a["Top Plays"], snap_b["Top Plays"])

    st.markdown("**Added**")
    if added:
        for p in added:
            themed_card_container()
            st.markdown(f"**{p['selection']}** — Odds {p['odds']} • Conf {p.get('true_confidence', 0)}")
    else:
        st.caption("None")

    st.markdown("**Removed**")
    if removed:
        for p in removed:
            themed_card_container()
            st.markdown(f"**{p['selection']}** — Odds {p['odds']} • Conf {p.get('true_confidence', 0)}")
    else:
        st.caption("None")

    st.markdown("---")

    # -----------------------------
    # WATCHLIST
    # -----------------------------
    st.subheader("Watchlist")
    added, removed, _ = _compare_play_lists(snap_a["Watchlist"], snap_b["Watchlist"])

    st.markdown("**Added**")
    if added:
        for p in added:
            themed_card_container()
            st.markdown(f"**{p['selection']}** — Odds {p['odds']}")
    else:
        st.caption("None")

    st.markdown("**Removed**")
    if removed:
        for p in removed:
            themed_card_container()
            st.markdown(f"**{p['selection']}** — Odds {p['odds']}")
    else:
        st.caption("None")

    st.markdown("---")

    # -----------------------------
    # AI SLIP
    # -----------------------------
    st.subheader("AI Slip")
    added, removed, _ = _compare_play_lists(snap_a["AI Slip"], snap_b["AI Slip"])

    st.markdown("**Added**")
    if added:
        for p in added:
            themed_card_container()
            st.markdown(f"**{p['selection']}** — Edge {p.get('edge', 0)}")
    else:
        st.caption("None")

    st.markdown("**Removed**")
    if removed:
        for p in removed:
            themed_card_container()
            st.markdown(f"**{p['selection']}** — Edge {p.get('edge', 0)}")
    else:
        st.caption("None")

    st.markdown("---")

    # -----------------------------
    # PARLAYS
    # -----------------------------
    st.subheader("Parlay Candidates")
    added, removed, _ = _compare_parlays(snap_a["Parlays"], snap_b["Parlays"])

    st.markdown("**Added**")
    if added:
        for idx, parlay in enumerate(added):
            themed_parlay_card(parlay, idx)
    else:
        st.caption("None")

    st.markdown("**Removed**")
    if removed:
        for idx, parlay in enumerate(removed):
            themed_parlay_card(parlay, idx)
    else:
        st.caption("None")

    st.markdown("---")

    st.success("Snapshot comparison complete.")
# ------------- CHUNK 27: SNAPSHOT PERFORMANCE COMPARISON ENGINE -------------

def _compute_snapshot_performance(snapshot: dict):
    """
    Compute performance metrics for a snapshot:
    - total bets
    - wins / losses / pushes
    - total profit
    - units risked
    - ROI
    - parlay profit
    - single profit
    """
    bets = snapshot.get("bets", [])  # optional future extension
    # For now, we compute performance from the bet log filtered by date

    # Filter bet log by snapshot date
    date_str = snapshot["timestamp"].split(" ")[0]
    log = [
        b for b in st.session_state.bet_log
        if b["timestamp"].startswith(date_str)
        and b.get("result") is not None
    ]

    if not log:
        return {
            "total_bets": 0,
            "wins": 0,
            "losses": 0,
            "pushes": 0,
            "profit": 0,
            "units": 0,
            "roi": 0,
            "parlay_profit": 0,
            "single_profit": 0,
        }

    wins = [b for b in log if b["result"] == "WIN"]
    losses = [b for b in log if b["result"] == "LOSS"]
    pushes = [b for b in log if b["result"] == "PUSH"]

    total_profit = sum(b["profit"] for b in log)

    units = 0
    parlay_profit = 0
    single_profit = 0

    for b in log:
        if b.get("is_parlay"):
            units += b.get("units", 1.0)
            parlay_profit += b["profit"]
        else:
            units += b.get("stake", 0)
            single_profit += b["profit"]

    roi = (total_profit / units) * 100 if units > 0 else 0

    return {
        "total_bets": len(log),
        "wins": len(wins),
        "losses": len(losses),
        "pushes": len(pushes),
        "profit": round(total_profit, 2),
        "units": round(units, 2),
        "roi": round(roi, 2),
        "parlay_profit": round(parlay_profit, 2),
        "single_profit": round(single_profit, 2),
    }


def render_snapshot_performance_comparison():
    """
    UI for comparing performance between two snapshot days.
    """
    st.header("Snapshot Performance Comparison")
    st.caption("Compare ROI, profit, win rate, and parlay/single performance between two days.")

    snaps = st.session_state.snapshots
    if not snaps:
        st.info("No snapshots available.")
        return

    dates = sorted(snaps.keys(), reverse=True)

    col1, col2 = st.columns(2)
    with col1:
        date_a = st.selectbox("Snapshot A", dates)
    with col2:
        date_b = st.selectbox("Snapshot B", dates, index=1 if len(dates) > 1 else 0)

    if date_a == date_b:
        st.warning("Select two different dates.")
        return

    snap_a = snaps[date_a]
    snap_b = snaps[date_b]

    perf_a = _compute_snapshot_performance(snap_a)
    perf_b = _compute_snapshot_performance(snap_b)

    st.markdown(f"### Performance: {date_a} → {date_b}")
    st.markdown("---")

    # -----------------------------
    # METRICS COMPARISON
    # -----------------------------
    def delta(a, b):
        d = b - a
        sign = "+" if d > 0 else ""
        return f"{sign}{round(d, 2)}"

    cols = st.columns(3)
    with cols[0]:
        themed_metric("Profit A", perf_a["profit"])
        themed_metric("Profit B", perf_b["profit"])
        themed_metric("Δ Profit", delta(perf_a["profit"], perf_b["profit"]))

    with cols[1]:
        themed_metric("ROI A", f"{perf_a['roi']}%")
        themed_metric("ROI B", f"{perf_b['roi']}%")
        themed_metric("Δ ROI", f"{delta(perf_a['roi'], perf_b['roi'])}%")

    with cols[2]:
        winrate_a = (perf_a["wins"] / perf_a["total_bets"] * 100) if perf_a["total_bets"] else 0
        winrate_b = (perf_b["wins"] / perf_b["total_bets"] * 100) if perf_b["total_bets"] else 0
        themed_metric("Win Rate A", f"{round(winrate_a, 2)}%")
        themed_metric("Win Rate B", f"{round(winrate_b, 2)}%")
        themed_metric("Δ Win Rate", f"{delta(winrate_a, winrate_b)}%")

    st.markdown("---")

    # -----------------------------
    # PARLAY VS SINGLE DELTAS
    # -----------------------------
    st.subheader("Parlay vs Single Performance")

    cols2 = st.columns(2)
    with cols2[0]:
        themed_metric("Parlay Profit A", perf_a["parlay_profit"])
        themed_metric("Parlay Profit B", perf_b["parlay_profit"])
        themed_metric("Δ Parlay Profit", delta(perf_a["parlay_profit"], perf_b["parlay_profit"]))

    with cols2[1]:
        themed_metric("Single Profit A", perf_a["single_profit"])
        themed_metric("Single Profit B", perf_b["single_profit"])
        themed_metric("Δ Single Profit", delta(perf_a["single_profit"], perf_b["single_profit"]))

    st.success("Performance comparison complete.")
# ------------- CHUNK 28: EXPORT ENGINE (CSV + JSON EXPORTS) -------------

import json
import io
import pandas as pd


def _export_bet_log_csv():
    """
    Convert bet log to CSV bytes.
    """
    log = st.session_state.bet_log
    if not log:
        return None

    df = pd.DataFrame(log)
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    return csv_bytes


def _export_bet_log_json():
    """
    Convert bet log to JSON bytes.
    """
    log = st.session_state.bet_log
    if not log:
        return None

    json_bytes = json.dumps(log, indent=2).encode("utf-8")
    return json_bytes


def _export_snapshots_json():
    """
    Export all snapshots as JSON.
    """
    snaps = st.session_state.snapshots
    if not snaps:
        return None

    json_bytes = json.dumps(snaps, indent=2).encode("utf-8")
    return json_bytes


def _export_performance_report_json():
    """
    Export performance metrics (all-time) as JSON.
    """
    metrics = _compute_performance_metrics()
    if not metrics:
        return None

    json_bytes = json.dumps(metrics, indent=2).encode("utf-8")
    return json_bytes


def render_export_center():
    """
    UI for exporting logs, snapshots, and performance.
    """
    st.header("Export Center")
    st.caption("Download your data for external analysis or backup.")

    st.markdown("### Bet Log Exports")

    col1, col2 = st.columns(2)
    with col1:
        csv_bytes = _export_bet_log_csv()
        if csv_bytes:
            st.download_button(
                "Download Bet Log (CSV)",
                data=csv_bytes,
                file_name="bet_log.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.caption("No bet log available.")

    with col2:
        json_bytes = _export_bet_log_json()
        if json_bytes:
            st.download_button(
                "Download Bet Log (JSON)",
                data=json_bytes,
                file_name="bet_log.json",
                mime="application/json",
                use_container_width=True,
            )
        else:
            st.caption("No bet log available.")

    st.markdown("---")

    st.markdown("### Snapshot Exports")
    snaps_bytes = _export_snapshots_json()
    if snaps_bytes:
        st.download_button(
            "Download Snapshots (JSON)",
            data=snaps_bytes,
            file_name="snapshots.json",
            mime="application/json",
            use_container_width=True,
        )
    else:
        st.caption("No snapshots available.")

    st.markdown("---")

    st.markdown("### Performance Report Export")
    perf_bytes = _export_performance_report_json()
    if perf_bytes:
        st.download_button(
            "Download Performance Report (JSON)",
            data=perf_bytes,
            file_name="performance_report.json",
            mime="application/json",
            use_container_width=True,
        )
    else:
        st.caption("No performance data available.")
# ------------- CHUNK 29: IMPORT ENGINE (RESTORE SYSTEM) -------------

def _validate_json_structure(data, expected_type):
    """
    Basic schema validation to prevent corrupt imports.
    """
    if not isinstance(data, expected_type):
        return False
    return True


def _import_bet_log(json_bytes):
    """
    Import bet log from JSON.
    """
    try:
        data = json.loads(json_bytes.decode("utf-8"))
        if not _validate_json_structure(data, list):
            return False, "Invalid bet log format."

        # Ensure each entry has required fields
        for entry in data:
            if not isinstance(entry, dict):
                return False, "Invalid bet log entry."

        st.session_state.bet_log = data
        return True, "Bet log imported successfully."

    except Exception as e:
        return False, f"Error importing bet log: {e}"


def _import_snapshots(json_bytes):
    """
    Import snapshots from JSON.
    """
    try:
        data = json.loads(json_bytes.decode("utf-8"))
        if not _validate_json_structure(data, dict):
            return False, "Invalid snapshot format."

        # Validate snapshot structure
        for date, snap in data.items():
            if not isinstance(snap, dict):
                return False, f"Snapshot for {date} is invalid."

        st.session_state.snapshots = data
        return True, "Snapshots imported successfully."

    except Exception as e:
        return False, f"Error importing snapshots: {e}"


def _import_settings(json_bytes):
    """
    Import settings from JSON.
    """
    try:
        data = json.loads(json_bytes.decode("utf-8"))
        if not _validate_json_structure(data, dict):
            return False, "Invalid settings format."

        # Only import keys that exist in DEFAULT_SETTINGS
        for key in DEFAULT_SETTINGS:
            if key in data:
                st.session_state.settings[key] = data[key]

        return True, "Settings imported successfully."

    except Exception as e:
        return False, f"Error importing settings: {e}"


def render_import_center():
    """
    UI for importing logs, snapshots, and settings.
    """
    st.header("Import Center")
    st.caption("Restore bet logs, snapshots, or settings from JSON files.")

    st.markdown("### Import Bet Log")
    bet_file = st.file_uploader("Upload bet_log.json", type=["json"], key="import_bet_log")
    if bet_file:
        success, msg = _import_bet_log(bet_file.read())
        if success:
            st.success(msg)
        else:
            st.error(msg)

    st.markdown("---")

    st.markdown("### Import Snapshots")
    snap_file = st.file_uploader("Upload snapshots.json", type=["json"], key="import_snapshots")
    if snap_file:
        success, msg = _import_snapshots(snap_file.read())
        if success:
            st.success(msg)
        else:
            st.error(msg)

    st.markdown("---")

    st.markdown("### Import Settings")
    settings_file = st.file_uploader("Upload settings.json", type=["json"], key="import_settings")
    if settings_file:
        success, msg = _import_settings(settings_file.read())
        if success:
            st.success(msg)
        else:
            st.error(msg)
# ------------- CHUNK 30: FULL BACKUP & RESTORE SUITE -------------

def _generate_full_backup():
    """
    Create a single JSON backup containing:
    - bet_log
    - snapshots
    - settings
    - performance metrics
    - today's plays
    """
    backup = {
        "bet_log": st.session_state.bet_log,
        "snapshots": st.session_state.snapshots,
        "settings": st.session_state.settings,
        "performance": _compute_performance_metrics(),
        "today_plays": st.session_state.today_plays,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    return json.dumps(backup, indent=2).encode("utf-8")


def _restore_full_backup(json_bytes):
    """
    Restore full system state from a backup JSON.
    """
    try:
        data = json.loads(json_bytes.decode("utf-8"))
        if not isinstance(data, dict):
            return False, "Invalid backup format."

        # Validate keys
        required_keys = ["bet_log", "snapshots", "settings", "today_plays"]
        for k in required_keys:
            if k not in data:
                return False, f"Missing key in backup: {k}"

        # Restore components
        if isinstance(data["bet_log"], list):
            st.session_state.bet_log = data["bet_log"]

        if isinstance(data["snapshots"], dict):
            st.session_state.snapshots = data["snapshots"]

        if isinstance(data["settings"], dict):
            for key in DEFAULT_SETTINGS:
                if key in data["settings"]:
                    st.session_state.settings[key] = data["settings"][key]

        if isinstance(data["today_plays"], dict):
            st.session_state.today_plays = data["today_plays"]

        return True, "Full system restore completed."

    except Exception as e:
        return False, f"Error restoring backup: {e}"


def render_backup_restore_center():
    """
    UI for one-click backup and restore.
    """
    st.header("Backup & Restore")
    st.caption("Create a full backup or restore your entire system from a single file.")

    st.markdown("### Create Full Backup")

    backup_bytes = _generate_full_backup()
    st.download_button(
        "Download Full Backup (JSON)",
        data=backup_bytes,
        file_name="v36_backup.json",
        mime="application/json",
        use_container_width=True,
    )

    st.markdown("---")

    st.markdown("### Restore From Backup")

    uploaded = st.file_uploader("Upload v36_backup.json", type=["json"], key="restore_backup")
    if uploaded:
        success, msg = _restore_full_backup(uploaded.read())
        if success:
            st.success(msg)
        else:
            st.error(msg)
# ------------- CHUNK 31: AI INSIGHTS PANEL (QWEN-POWERED) -------------

def _qwen_insight_prompt(plays, category_name):
    """
    Build a structured prompt for Qwen to generate insights.
    """
    prompt = f"""
You are an expert sports betting analyst. Provide concise, high-signal insights.

CATEGORY: {category_name}

PLAYS:
{json.dumps(plays, indent=2)}

TASKS:
1. Explain the key reasons these plays stand out.
2. Identify any trends across the plays (teams, markets, odds ranges, confidence patterns).
3. Highlight any risk factors.
4. Provide 2–3 actionable insights for the bettor.
5. Keep the tone analytical, not hype-driven.
6. Keep the output under 200 words.
"""
    return prompt


def _generate_ai_insights(plays, category_name):
    """
    Call Qwen to generate insights for a category.
    """
    if not plays:
        return "No plays available for insights."

    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_insight_prompt(plays, category_name)
    response = _call_qwen(prompt)  # Uses your existing Qwen wrapper
    return response or "No insights generated."


def render_ai_insights_panel():
    """
    Full AI Insights Panel UI.
    """
    st.header("AI Insights Panel")
    st.caption("Qwen-powered explanations, trends, and risk analysis.")

    # -----------------------------
    # TOP PLAYS INSIGHTS
    # -----------------------------
    st.subheader("Top Plays — AI Insights")
    top_plays = st.session_state.today_plays.get("Top Plays", [])
    insights_top = _generate_ai_insights(top_plays, "Top Plays")
    themed_card_container()
    st.markdown(insights_top)

    st.markdown("---")

    # -----------------------------
    # WATCHLIST INSIGHTS
    # -----------------------------
    st.subheader("Watchlist — AI Insights")
    watchlist = st.session_state.today_plays.get("Watchlist", [])
    insights_watch = _generate_ai_insights(watchlist, "Watchlist")
    themed_card_container()
    st.markdown(insights_watch)

    st.markdown("---")

    # -----------------------------
    # AI SLIP INSIGHTS
    # -----------------------------
    st.subheader("AI Slip — AI Insights")
    slip = st.session_state.today_plays.get("AI Slip", [])
    insights_slip = _generate_ai_insights(slip, "AI Slip")
    themed_card_container()
    st.markdown(insights_slip)

    st.markdown("---")

    # -----------------------------
    # PARLAY SYNERGY INSIGHTS
    # -----------------------------
    st.subheader("Parlay Synergy Insights")
    parlays = generate_parlay_candidates()

    if parlays:
        # Build a compact representation for Qwen
        parlay_summary = []
        for p in parlays:
            parlay_summary.append({
                "num_legs": p["num_legs"],
                "risk_score": p["risk_score"],
                "legs": [
                    {
                        "selection": leg["selection"],
                        "market": leg["market"],
                        "odds": leg["odds"],
                        "edge": leg.get("edge", 0),
                    }
                    for leg in p["legs"]
                ]
            })

        prompt = f"""
You are an expert sports betting analyst.

Analyze the following parlay candidates:

{json.dumps(parlay_summary, indent=2)}

TASKS:
1. Identify synergy between legs.
2. Highlight risk factors.
3. Explain which parlays are strongest and why.
4. Provide 2–3 actionable insights.
5. Keep output under 200 words.
"""

        insights_parlay = _call_qwen(prompt)
        themed_card_container()
        st.markdown(insights_parlay or "No parlay insights generated.")
    else:
        st.info("No parlay candidates available.")
# ------------- CHUNK 32: AI TREND ENGINE (MULTI-DAY TRENDS) -------------

def _collect_multi_day_snapshot_data():
    """
    Aggregate plays across all snapshots for multi-day trend analysis.
    Returns a compact structure for Qwen.
    """
    snaps = st.session_state.snapshots
    if not snaps:
        return None

    aggregated = []

    for date, snap in snaps.items():
        day_entry = {
            "date": date,
            "top": [
                {
                    "selection": p["selection"],
                    "market": p["market"],
                    "odds": p["odds"],
                    "edge": p.get("edge", 0),
                    "confidence": p.get("true_confidence", 0),
                }
                for p in snap.get("Top Plays", [])
            ],
            "watchlist": [
                {
                    "selection": p["selection"],
                    "market": p["market"],
                    "odds": p["odds"],
                    "edge": p.get("edge", 0),
                    "confidence": p.get("true_confidence", 0),
                }
                for p in snap.get("Watchlist", [])
            ],
            "slip": [
                {
                    "selection": p["selection"],
                    "market": p["market"],
                    "odds": p["odds"],
                    "edge": p.get("edge", 0),
                    "confidence": p.get("true_confidence", 0),
                }
                for p in snap.get("AI Slip", [])
            ],
        }

        aggregated.append(day_entry)

    return aggregated


def _qwen_trend_prompt(aggregated):
    """
    Build a structured prompt for Qwen to analyze multi-day trends.
    """
    prompt = f"""
You are an elite sports betting analyst.

Analyze MULTI-DAY TRENDS across the following snapshots:

{json.dumps(aggregated, indent=2)}

TASKS:
1. Identify long-term profitable patterns (teams, markets, odds ranges, confidence levels).
2. Identify cold patterns (losing or low-edge trends).
3. Detect hidden correlations across days.
4. Highlight which markets are consistently strong vs weak.
5. Provide actionable insights for future betting decisions.
6. Keep output under 250 words.
7. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_multi_day_trends():
    """
    Call Qwen to generate multi-day trend insights.
    """
    aggregated = _collect_multi_day_snapshot_data()
    if not aggregated:
        return "No snapshots available for trend analysis."

    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_trend_prompt(aggregated)
    response = _call_qwen(prompt)
    return response or "No trend insights generated."


def render_ai_trend_engine():
    """
    Full UI for multi-day trend analysis.
    """
    st.header("AI Trend Engine")
    st.caption("Qwen-powered multi-day trend detection across snapshots.")

    aggregated = _collect_multi_day_snapshot_data()
    if not aggregated:
        st.info("No snapshots available.")
        return

    # Show number of days analyzed
    st.markdown(f"Analyzing **{len(aggregated)} days** of snapshots.")
    st.markdown("---")

    # Generate insights
    insights = _generate_multi_day_trends()

    themed_card_container()
    st.markdown(insights)
# ------------- CHUNK 33: RISK DASHBOARD (EXPOSURE + VOLATILITY) -------------

def _compute_risk_metrics():
    """
    Compute risk metrics from the bet log:
    - exposure by team
    - exposure by market
    - volatility score
    - parlay risk
    """
    log = st.session_state.bet_log
    if not log:
        return {
            "team_exposure": {},
            "market_exposure": {},
            "volatility": 0,
            "parlay_risk": 0,
        }

    team_exp = {}
    market_exp = {}
    parlay_units = 0
    single_units = 0
    odds_list = []

    for b in log:
        # Track exposure by team
        team = b.get("team") or b.get("selection", "").split(" ")[0]
        units = b.get("units", b.get("stake", 0))
        team_exp[team] = team_exp.get(team, 0) + units

        # Track exposure by market
        market = b.get("market", "Unknown")
        market_exp[market] = market_exp.get(market, 0) + units

        # Track volatility (odds-based)
        odds_list.append(abs(b.get("odds", 0)))

        # Track parlay vs single exposure
        if b.get("is_parlay"):
            parlay_units += units
        else:
            single_units += units

    # Volatility score = std deviation of odds
    volatility = round(float(np.std(odds_list)), 3) if odds_list else 0

    # Parlay risk = % of total units tied to parlays
    total_units = parlay_units + single_units
    parlay_risk = round((parlay_units / total_units) * 100, 2) if total_units > 0 else 0

    return {
        "team_exposure": team_exp,
        "market_exposure": market_exp,
        "volatility": volatility,
        "parlay_risk": parlay_risk,
    }


def _render_exposure_table(title, exposure_dict):
    """
    Render a theme-aware exposure table.
    """
    st.subheader(title)

    if not exposure_dict:
        st.caption("No data.")
        return

    df = pd.DataFrame(
        [{"Name": k, "Units": v} for k, v in exposure_dict.items()]
    ).sort_values("Units", ascending=False)

    themed_table(df)


def render_risk_dashboard():
    """
    Full V36 Risk Dashboard UI.
    """
    st.header("Risk Dashboard")
    st.caption("Volatility, exposure, and market risk analytics.")

    metrics = _compute_risk_metrics()

    # -----------------------------
    # TOP METRICS
    # -----------------------------
    cols = st.columns(3)
    with cols[0]:
        themed_metric("Volatility Score", metrics["volatility"])
    with cols[1]:
        themed_metric("Parlay Risk %", f"{metrics['parlay_risk']}%")
    with cols[2]:
        total_markets = len(metrics["market_exposure"])
        themed_metric("Active Markets", total_markets)

    st.markdown("---")

    # -----------------------------
    # TEAM EXPOSURE
    # -----------------------------
    _render_exposure_table("Team Exposure", metrics["team_exposure"])

    st.markdown("---")

    # -----------------------------
    # MARKET EXPOSURE
    # -----------------------------
    _render_exposure_table("Market Exposure", metrics["market_exposure"])

    st.markdown("---")

    # -----------------------------
    # PARLAY RISK HEATMAP (TEXT-BASED)
    # -----------------------------
    st.subheader("Parlay Risk Heatmap")

    if metrics["parlay_risk"] >= 50:
        themed_card_container()
        st.markdown("🔥 **High parlay exposure detected.** Consider reducing correlated risk.")
    elif metrics["parlay_risk"] >= 25:
        themed_card_container()
        st.markdown("⚠️ **Moderate parlay exposure.** Monitor volatility.")
    else:
        themed_card_container()
        st.markdown("🟢 **Low parlay exposure.** Risk is well-balanced.")

    st.success("Risk analysis complete.")
# ------------- CHUNK 34: EXPOSURE FORECASTING ENGINE -------------

def _collect_exposure_history():
    """
    Build a multi-day exposure history from snapshots + bet log.
    Used as input for forecasting.
    """
    snaps = st.session_state.snapshots
    if not snaps:
        return None

    history = []

    for date, snap in snaps.items():
        # Compute risk metrics for that day
        date_str = date
        day_log = [
            b for b in st.session_state.bet_log
            if b["timestamp"].startswith(date_str)
        ]

        team_exp = {}
        market_exp = {}
        parlay_units = 0
        single_units = 0

        for b in day_log:
            team = b.get("team") or b.get("selection", "").split(" ")[0]
            units = b.get("units", b.get("stake", 0))
            team_exp[team] = team_exp.get(team, 0) + units

            market = b.get("market", "Unknown")
            market_exp[market] = market_exp.get(market, 0) + units

            if b.get("is_parlay"):
                parlay_units += units
            else:
                single_units += units

        total_units = parlay_units + single_units
        parlay_risk = round((parlay_units / total_units) * 100, 2) if total_units > 0 else 0

        history.append({
            "date": date,
            "team_exposure": team_exp,
            "market_exposure": market_exp,
            "parlay_risk": parlay_risk,
        })

    return history


def _qwen_forecast_prompt(history):
    """
    Build a structured prompt for Qwen to forecast future exposure.
    """
    prompt = f"""
You are an expert sports betting risk analyst.

Analyze the following multi-day exposure history:

{json.dumps(history, indent=2)}

TASKS:
1. Identify exposure trends (teams, markets, parlays).
2. Predict where exposure is likely to increase over the next 1–3 days.
3. Identify potential upcoming risk spikes.
4. Highlight markets or teams trending toward overexposure.
5. Provide actionable risk-management recommendations.
6. Keep output under 250 words.
7. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_exposure_forecast():
    """
    Call Qwen to generate predictive exposure insights.
    """
    history = _collect_exposure_history()
    if not history:
        return "No exposure history available for forecasting."

    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_forecast_prompt(history)
    response = _call_qwen(prompt)
    return response or "No forecast generated."


def render_exposure_forecasting_engine():
    """
    Full UI for predictive exposure modeling.
    """
    st.header("Exposure Forecasting Engine")
    st.caption("Qwen-powered predictive risk modeling for upcoming exposure trends.")

    history = _collect_exposure_history()
    if not history:
        st.info("Not enough historical data for forecasting.")
        return

    st.markdown(f"Analyzing **{len(history)} days** of exposure history.")
    st.markdown("---")

    forecast = _generate_exposure_forecast()

    themed_card_container()
    st.markdown(forecast)
# ------------- CHUNK 35: MARKET HEATMAP (MSI + VOLATILITY) -------------

def _compute_market_strength_index():
    """
    Compute Market Strength Index (MSI) for each market:
    - win rate
    - ROI
    - volatility (odds std dev)
    - volume (units)
    """
    log = st.session_state.bet_log
    if not log:
        return pd.DataFrame(columns=["Market", "WinRate", "ROI", "Volatility", "Units"])

    market_stats = {}

    for b in log:
        market = b.get("market", "Unknown")
        if market not in market_stats:
            market_stats[market] = {
                "wins": 0,
                "losses": 0,
                "pushes": 0,
                "profit": 0,
                "units": 0,
                "odds": [],
            }

        entry = market_stats[market]

        # Count results
        if b.get("result") == "WIN":
            entry["wins"] += 1
        elif b.get("result") == "LOSS":
            entry["losses"] += 1
        elif b.get("result") == "PUSH":
            entry["pushes"] += 1

        # Profit + units
        entry["profit"] += b.get("profit", 0)
        entry["units"] += b.get("units", b.get("stake", 0))

        # Volatility
        entry["odds"].append(abs(b.get("odds", 0)))

    # Build DataFrame
    rows = []
    for market, stats in market_stats.items():
        total_bets = stats["wins"] + stats["losses"] + stats["pushes"]
        winrate = (stats["wins"] / total_bets * 100) if total_bets else 0
        roi = (stats["profit"] / stats["units"] * 100) if stats["units"] > 0 else 0
        vol = float(np.std(stats["odds"])) if stats["odds"] else 0

        rows.append({
            "Market": market,
            "WinRate": round(winrate, 2),
            "ROI": round(roi, 2),
            "Volatility": round(vol, 3),
            "Units": round(stats["units"], 2),
        })

    df = pd.DataFrame(rows)

    # Market Strength Index = weighted blend
    df["MSI"] = (
        df["WinRate"] * 0.4 +
        df["ROI"] * 0.4 -
        df["Volatility"] * 0.2
    ).round(2)

    return df.sort_values("MSI", ascending=False)


def _render_market_heatmap(df):
    """
    Render a theme-aware heatmap using color scaling.
    """
    theme = st.session_state.theme

    if theme == "dark":
        good = "#2ecc71"
        neutral = "#f1c40f"
        bad = "#e74c3c"
        bg = "#111111"
        text = "#ffffff"
    else:
        good = "#27ae60"
        neutral = "#d4ac0d"
        bad = "#c0392b"
        bg = "#fafafa"
        text = "#000000"

    st.markdown(
        f"""
        <style>
        .heatmap-table td {{
            padding: 0.5rem;
            border: 1px solid #44444422;
            background-color: {bg};
            color: {text};
        }}
        .heatmap-table th {{
            padding: 0.5rem;
            background-color: {bg};
            color: {text};
            border-bottom: 1px solid #44444455;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Color scale for MSI
    def color_for_msi(msi):
        if msi >= 20:
            return good
        elif msi >= 5:
            return neutral
        else:
            return bad

    styled = df.style.apply(
        lambda row: [
            f"background-color: {color_for_msi(row['MSI'])}; color: white;"
            if col == "MSI" else ""
            for col in row.index
        ],
        axis=1,
    ).set_table_attributes('class="heatmap-table"')

    st.table(styled)


def render_market_heatmap():
    """
    Full UI for Market Strength Index + Volatility Heatmap.
    """
    st.header("Market Heatmap")
    st.caption("Market Strength Index (MSI) with volatility overlay.")

    df = _compute_market_strength_index()
    if df.empty:
        st.info("No market data available.")
        return

    # Top metrics
    cols = st.columns(3)
    with cols[0]:
        themed_metric("Strongest Market", df.iloc[0]["Market"])
    with cols[1]:
        themed_metric("Highest MSI", df.iloc[0]["MSI"])
    with cols[2]:
        themed_metric("Most Volatile Market", df.sort_values("Volatility", ascending=False).iloc[0]["Market"])

    st.markdown("---")

    _render_market_heatmap(df)

    st.success("Market heatmap generated.")
# ------------- CHUNK 36: PARLAY HEATMAP (SYNERGY + CORRELATION) -------------

def _collect_parlay_leg_data():
    """
    Extract all legs from all parlay candidates and build a correlation-ready dataset.
    """
    parlays = generate_parlay_candidates()
    if not parlays:
        return None

    legs = []
    for p in parlays:
        for leg in p["legs"]:
            legs.append({
                "selection": leg["selection"],
                "market": leg["market"],
                "team": leg.get("team") or leg["selection"].split(" ")[0],
                "odds": leg["odds"],
                "edge": leg.get("edge", 0),
                "confidence": leg.get("true_confidence", 0),
            })

    return legs


def _compute_leg_correlation_matrix(legs):
    """
    Build a correlation matrix based on:
    - edge
    - confidence
    - odds
    - team/market similarity
    """
    if not legs:
        return pd.DataFrame()

    df = pd.DataFrame(legs)

    # Encode categorical fields
    df["team_code"] = df["team"].astype("category").cat.codes
    df["market_code"] = df["market"].astype("category").cat.codes

    # Numeric fields for correlation
    corr_df = df[["edge", "confidence", "odds", "team_code", "market_code"]]

    corr_matrix = corr_df.corr().round(3)
    return corr_matrix


def _render_parlay_heatmap(corr_matrix):
    """
    Render a theme-aware correlation heatmap.
    """
    theme = st.session_state.theme

    if theme == "dark":
        high = "#2ecc71"
        mid = "#f1c40f"
        low = "#e74c3c"
        bg = "#111111"
        text = "#ffffff"
    else:
        high = "#27ae60"
        mid = "#d4ac0d"
        low = "#c0392b"
        bg = "#fafafa"
        text = "#000000"

    st.markdown(
        f"""
        <style>
        .parlay-heatmap td {{
            padding: 0.5rem;
            border: 1px solid #44444422;
            background-color: {bg};
            color: {text};
        }}
        .parlay-heatmap th {{
            padding: 0.5rem;
            background-color: {bg};
            color: {text};
            border-bottom: 1px solid #44444455;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Color scale
    def color_for_value(v):
        if v >= 0.5:
            return high
        elif v >= 0.2:
            return mid
        else:
            return low

    styled = corr_matrix.style.apply(
        lambda row: [
            f"background-color: {color_for_value(row[col])}; color: white;"
            for col in row.index
        ],
        axis=1,
    ).set_table_attributes('class="parlay-heatmap"')

    st.table(styled)


def render_parlay_heatmap():
    """
    Full UI for Parlay Synergy Matrix + Correlation Map.
    """
    st.header("Parlay Heatmap")
    st.caption("Leg synergy matrix and correlation map for parlay construction.")

    legs = _collect_parlay_leg_data()
    if not legs:
        st.info("No parlay candidates available.")
        return

    corr_matrix = _compute_leg_correlation_matrix(legs)
    if corr_matrix.empty:
        st.info("Not enough data to compute correlations.")
        return

    # Top synergy metrics
    st.subheader("Synergy Summary")

    avg_corr = corr_matrix.mean().mean().round(3)
    max_corr = corr_matrix.max().max().round(3)
    min_corr = corr_matrix.min().min().round(3)

    cols = st.columns(3)
    with cols[0]:
        themed_metric("Avg Synergy", avg_corr)
    with cols[1]:
        themed_metric("Max Correlation", max_corr)
    with cols[2]:
        themed_metric("Min Correlation", min_corr)

    st.markdown("---")

    # Render heatmap
    _render_parlay_heatmap(corr_matrix)

    st.success("Parlay heatmap generated.")
# ------------- CHUNK 37: PERFORMANCE HEATMAP (TEAM + MARKET ROI) -------------

def _compute_team_performance():
    """
    Compute team-level performance:
    - wins, losses, pushes
    - profit
    - units
    - ROI
    """
    log = st.session_state.bet_log
    if not log:
        return pd.DataFrame(columns=["Team", "WinRate", "ROI", "Units"])

    team_stats = {}

    for b in log:
        team = b.get("team") or b.get("selection", "").split(" ")[0]
        if team not in team_stats:
            team_stats[team] = {
                "wins": 0,
                "losses": 0,
                "pushes": 0,
                "profit": 0,
                "units": 0,
            }

        entry = team_stats[team]

        # Count results
        if b.get("result") == "WIN":
            entry["wins"] += 1
        elif b.get("result") == "LOSS":
            entry["losses"] += 1
        elif b.get("result") == "PUSH":
            entry["pushes"] += 1

        # Profit + units
        entry["profit"] += b.get("profit", 0)
        entry["units"] += b.get("units", b.get("stake", 0))

    rows = []
    for team, stats in team_stats.items():
        total_bets = stats["wins"] + stats["losses"] + stats["pushes"]
        winrate = (stats["wins"] / total_bets * 100) if total_bets else 0
        roi = (stats["profit"] / stats["units"] * 100) if stats["units"] > 0 else 0

        rows.append({
            "Team": team,
            "WinRate": round(winrate, 2),
            "ROI": round(roi, 2),
            "Units": round(stats["units"], 2),
        })

    return pd.DataFrame(rows).sort_values("ROI", ascending=False)


def _compute_market_performance():
    """
    Compute market-level performance:
    - wins, losses, pushes
    - profit
    - units
    - ROI
    """
    log = st.session_state.bet_log
    if not log:
        return pd.DataFrame(columns=["Market", "WinRate", "ROI", "Units"])

    market_stats = {}

    for b in log:
        market = b.get("market", "Unknown")
        if market not in market_stats:
            market_stats[market] = {
                "wins": 0,
                "losses": 0,
                "pushes": 0,
                "profit": 0,
                "units": 0,
            }

        entry = market_stats[market]

        # Count results
        if b.get("result") == "WIN":
            entry["wins"] += 1
        elif b.get("result") == "LOSS":
            entry["losses"] += 1
        elif b.get("result") == "PUSH":
            entry["pushes"] += 1

        # Profit + units
        entry["profit"] += b.get("profit", 0)
        entry["units"] += b.get("units", b.get("stake", 0))

    rows = []
    for market, stats in market_stats.items():
        total_bets = stats["wins"] + stats["losses"] + stats["pushes"]
        winrate = (stats["wins"] / total_bets * 100) if total_bets else 0
        roi = (stats["profit"] / stats["units"] * 100) if stats["units"] > 0 else 0

        rows.append({
            "Market": market,
            "WinRate": round(winrate, 2),
            "ROI": round(roi, 2),
            "Units": round(stats["units"], 2),
        })

    return pd.DataFrame(rows).sort_values("ROI", ascending=False)


def _render_performance_heatmap(df, label):
    """
    Render a theme-aware heatmap for ROI.
    """
    theme = st.session_state.theme

    if theme == "dark":
        high = "#2ecc71"
        mid = "#f1c40f"
        low = "#e74c3c"
        bg = "#111111"
        text = "#ffffff"
    else:
        high = "#27ae60"
        mid = "#d4ac0d"
        low = "#c0392b"
        bg = "#fafafa"
        text = "#000000"

    st.subheader(label)

    if df.empty:
        st.caption("No data available.")
        return

    st.markdown(
        f"""
        <style>
        .perf-heatmap td {{
            padding: 0.5rem;
            border: 1px solid #44444422;
            background-color: {bg};
            color: {text};
        }}
        .perf-heatmap th {{
            padding: 0.5rem;
            background-color: {bg};
            color: {text};
            border-bottom: 1px solid #44444455;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Color scale for ROI
    def color_for_roi(roi):
        if roi >= 10:
            return high
        elif roi >= 0:
            return mid
        else:
            return low

    styled = df.style.apply(
        lambda row: [
            f"background-color: {color_for_roi(row['ROI'])}; color: white;"
            if col == "ROI" else ""
            for col in row.index
        ],
        axis=1,
    ).set_table_attributes('class="perf-heatmap"')

    st.table(styled)


def render_performance_heatmap():
    """
    Full UI for team-level and market-level ROI heatmaps.
    """
    st.header("Performance Heatmap")
    st.caption("Team-level and market-level ROI matrices.")

    # TEAM PERFORMANCE
    team_df = _compute_team_performance()
    _render_performance_heatmap(team_df, "Team ROI Heatmap")

    st.markdown("---")

    # MARKET PERFORMANCE
    market_df = _compute_market_performance()
    _render_performance_heatmap(market_df, "Market ROI Heatmap")

    st.success("Performance heatmaps generated.")
# ------------- CHUNK 38: UNIT ALLOCATION OPTIMIZER (KELLY + RISK ADJUSTED) -------------

def _kelly_fraction(prob, odds_decimal):
    """
    Compute Kelly fraction:
    f* = (bp - q) / b
    where:
    - b = odds_decimal - 1
    - p = win probability
    - q = 1 - p
    """
    b = odds_decimal - 1
    p = prob
    q = 1 - p

    k = (b * p - q) / b if b != 0 else 0
    return max(0, k)  # no negative Kelly


def _risk_adjust_kelly(kelly, volatility, parlay_risk):
    """
    Adjust Kelly fraction based on:
    - volatility (higher volatility → smaller bet)
    - parlay risk (higher parlay exposure → smaller bet)
    """
    vol_factor = max(0.2, 1 - (volatility / 10))  # volatility dampens sizing
    parlay_factor = max(0.3, 1 - (parlay_risk / 100))  # parlay exposure dampens sizing

    return kelly * vol_factor * parlay_factor


def _compute_unit_recommendation(play, risk_metrics):
    """
    Compute recommended units for a single play.
    """
    prob = play.get("true_confidence", 0) / 100
    if prob <= 0:
        return 0

    odds = play.get("odds", 0)
    if odds == 0:
        return 0

    # Convert American odds → decimal
    if odds > 0:
        decimal = 1 + (odds / 100)
    else:
        decimal = 1 + (100 / abs(odds))

    # Base Kelly
    kelly = _kelly_fraction(prob, decimal)

    # Risk adjustments
    volatility = risk_metrics["volatility"]
    parlay_risk = risk_metrics["parlay_risk"]

    adj_kelly = _risk_adjust_kelly(kelly, volatility, parlay_risk)

    # Convert to units (base unit = 1)
    units = adj_kelly * st.session_state.settings.get("base_unit", 1)

    return round(units, 3)


def render_unit_allocation_optimizer():
    """
    Full UI for Kelly-based, risk-adjusted unit sizing.
    """
    st.header("Unit Allocation Optimizer")
    st.caption("Kelly-based, risk-adjusted unit sizing for today's plays.")

    plays = st.session_state.today_plays.get("Top Plays", [])
    if not plays:
        st.info("No plays available for unit sizing.")
        return

    # Get risk metrics
    risk_metrics = _compute_risk_metrics()

    st.markdown("### Recommended Unit Sizes")
    st.caption("Based on Kelly fraction, volatility, and parlay exposure.")

    for play in plays:
        units = _compute_unit_recommendation(play, risk_metrics)

        themed_card_container()
        st.markdown(f"""
        **{play['selection']}**  
        Odds: {play['odds']}  
        Confidence: {play.get('true_confidence', 0)}%  
        **Recommended Units: {units}**
        """)

    st.success("Unit sizing complete.")
# ------------- CHUNK 39: AI BET COMMENTARY ENGINE -------------

def _qwen_commentary_prompt(play):
    """
    Build a structured prompt for Qwen to generate commentary for a single play.
    """
    prompt = f"""
You are an expert sports betting analyst.

Provide concise, high-signal commentary for the following play:

PLAY:
{json.dumps(play, indent=2)}

TASKS:
1. Explain why this play is appealing.
2. Interpret the odds and what they imply.
3. Interpret the confidence/edge and what it means.
4. Highlight any risk factors.
5. Provide 1–2 actionable notes.
6. Keep output under 120 words.
7. Tone: analytical, concise, not hype-driven.
"""
    return prompt


def _generate_play_commentary(play):
    """
    Call Qwen to generate commentary for a single play.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_commentary_prompt(play)
    response = _call_qwen(prompt)
    return response or "No commentary generated."


def render_ai_bet_commentary():
    """
    Full UI for Qwen-generated commentary for each play.
    """
    st.header("AI Bet Commentary")
    st.caption("Qwen-powered commentary for each individual play.")

    plays = st.session_state.today_plays.get("Top Plays", [])
    if not plays:
        st.info("No plays available for commentary.")
        return

    for play in plays:
        commentary = _generate_play_commentary(play)

        themed_card_container()
        st.markdown(f"""
        ### {play['selection']}
        Odds: {play['odds']}  
        Confidence: {play.get('true_confidence', 0)}%  
        Edge: {play.get('edge', 0)}  

        **AI Commentary:**  
        {commentary}
        """)

    st.success("AI commentary generated.")
# ------------- CHUNK 40: AI MARKET COMMENTARY ENGINE -------------

def _collect_market_summary():
    """
    Build a compact summary of today's markets for Qwen.
    """
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    if not plays:
        return None

    summary = {}

    for p in plays:
        market = p.get("market", "Unknown")
        if market not in summary:
            summary[market] = []

        summary[market].append({
            "selection": p["selection"],
            "odds": p["odds"],
            "edge": p.get("edge", 0),
            "confidence": p.get("true_confidence", 0),
        })

    return summary


def _qwen_market_prompt(market, plays):
    """
    Build a structured prompt for Qwen to analyze a single market.
    """
    prompt = f"""
You are an expert sports betting analyst.

Analyze the following MARKET:

MARKET: {market}

PLAYS:
{json.dumps(plays, indent=2)}

TASKS:
1. Explain what defines this market (spread, total, props, etc.).
2. Identify trends across the plays (odds ranges, confidence patterns, team tendencies).
3. Highlight market-specific risks.
4. Provide 2–3 actionable insights for bettors.
5. Keep output under 150 words.
6. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_commentary(market, plays):
    """
    Call Qwen to generate commentary for a market.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_market_prompt(market, plays)
    response = _call_qwen(prompt)
    return response or "No commentary generated."


def render_ai_market_commentary():
    """
    Full UI for Qwen-generated market-level insights.
    """
    st.header("AI Market Commentary")
    st.caption("Qwen-powered insights for spreads, totals, props, and more.")

    summary = _collect_market_summary()
    if not summary:
        st.info("No market data available for commentary.")
        return

    for market, plays in summary.items():
        commentary = _generate_market_commentary(market, plays)

        themed_card_container()
        st.markdown(f"""
        ## {market}
        **Plays in this market:** {len(plays)}

        **AI Market Commentary:**  
        {commentary}
        """)

    st.success("Market commentary generated.")
# ------------- CHUNK 41: AI OPPONENT MODELING ENGINE -------------

def _collect_team_behavior_history():
    """
    Build a multi-day team behavior dataset from snapshots + bet log.
    """
    snaps = st.session_state.snapshots
    if not snaps:
        return None

    team_history = {}

    for date, snap in snaps.items():
        # Plays from all categories
        plays = (
            snap.get("Top Plays", []) +
            snap.get("Watchlist", []) +
            snap.get("AI Slip", [])
        )

        for p in plays:
            team = p.get("team") or p["selection"].split(" ")[0]
            if team not in team_history:
                team_history[team] = []

            team_history[team].append({
                "date": date,
                "market": p.get("market", "Unknown"),
                "odds": p.get("odds", 0),
                "edge": p.get("edge", 0),
                "confidence": p.get("true_confidence", 0),
            })

    return team_history


def _qwen_team_profile_prompt(team, history):
    """
    Build a structured prompt for Qwen to generate a team behavioral profile.
    """
    prompt = f"""
You are an elite sports betting analyst.

Analyze the following TEAM BEHAVIORAL HISTORY:

TEAM: {team}

HISTORY:
{json.dumps(history, indent=2)}

TASKS:
1. Identify the team's betting tendencies (spread, totals, props, etc.).
2. Highlight strengths and weaknesses across markets.
3. Identify patterns in odds, confidence, and edge.
4. Detect volatility or inconsistency.
5. Provide actionable insights for betting on or against this team.
6. Keep output under 180 words.
7. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_team_profile(team, history):
    """
    Call Qwen to generate a behavioral profile for a team.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_team_profile_prompt(team, history)
    response = _call_qwen(prompt)
    return response or "No profile generated."


def render_ai_opponent_modeling():
    """
    Full UI for team-level behavioral profiles.
    """
    st.header("AI Opponent Modeling")
    st.caption("Qwen-powered team behavioral profiles and tendencies.")

    team_history = _collect_team_behavior_history()
    if not team_history:
        st.info("No historical data available for opponent modeling.")
        return

    # Sort teams alphabetically for clean UI
    teams = sorted(team_history.keys())

    selected_team = st.selectbox("Select a team", teams)
    history = team_history[selected_team]

    profile = _generate_team_profile(selected_team, history)

    themed_card_container()
    st.markdown(f"""
    ## {selected_team} — Behavioral Profile

    **AI Team Analysis:**  
    {profile}
    """)

    st.success("Team profile generated.")
# ------------- CHUNK 42: MATCHUP INTELLIGENCE ENGINE -------------

def _collect_matchup_history(team_a, team_b):
    """
    Build a combined history of both teams across snapshots.
    """
    snaps = st.session_state.snapshots
    if not snaps:
        return None

    history = {
        "team_a": [],
        "team_b": []
    }

    for date, snap in snaps.items():
        plays = (
            snap.get("Top Plays", []) +
            snap.get("Watchlist", []) +
            snap.get("AI Slip", [])
        )

        for p in plays:
            team = p.get("team") or p["selection"].split(" ")[0]

            entry = {
                "date": date,
                "market": p.get("market", "Unknown"),
                "odds": p.get("odds", 0),
                "edge": p.get("edge", 0),
                "confidence": p.get("true_confidence", 0),
            }

            if team == team_a:
                history["team_a"].append(entry)
            elif team == team_b:
                history["team_b"].append(entry)

    return history


def _qwen_matchup_prompt(team_a, team_b, history):
    """
    Build a structured prompt for Qwen to analyze a matchup.
    """
    prompt = f"""
You are an elite sports betting analyst.

Analyze the following TEAM MATCHUP:

TEAM A: {team_a}
TEAM B: {team_b}

MATCHUP HISTORY:
{json.dumps(history, indent=2)}

TASKS:
1. Identify head-to-head tendencies between these teams.
2. Compare strengths and weaknesses across markets.
3. Highlight market-specific matchup patterns (spread, totals, props).
4. Identify volatility or risk factors.
5. Provide actionable insights for betting this matchup.
6. Keep output under 200 words.
7. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_matchup_analysis(team_a, team_b, history):
    """
    Call Qwen to generate matchup intelligence.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_matchup_prompt(team_a, team_b, history)
    response = _call_qwen(prompt)
    return response or "No matchup analysis generated."


def render_matchup_intelligence_engine():
    """
    Full UI for team-vs-team matchup analysis.
    """
    st.header("Matchup Intelligence Engine")
    st.caption("Qwen-powered team-vs-team matchup breakdowns.")

    # Collect all teams from snapshots
    snaps = st.session_state.snapshots
    if not snaps:
        st.info("No snapshots available.")
        return

    teams = set()
    for date, snap in snaps.items():
        plays = (
            snap.get("Top Plays", []) +
            snap.get("Watchlist", []) +
            snap.get("AI Slip", [])
        )
        for p in plays:
            team = p.get("team") or p["selection"].split(" ")[0]
            teams.add(team)

    teams = sorted(list(teams))
    if len(teams) < 2:
        st.info("Not enough teams for matchup analysis.")
        return

    col1, col2 = st.columns(2)
    with col1:
        team_a = st.selectbox("Team A", teams)
    with col2:
        team_b = st.selectbox("Team B", teams)

    if team_a == team_b:
        st.warning("Select two different teams.")
        return

    history = _collect_matchup_history(team_a, team_b)
    if not history:
        st.info("No matchup history available.")
        return

    analysis = _generate_matchup_analysis(team_a, team_b, history)

    themed_card_container()
    st.markdown(f"""
    ## {team_a} vs {team_b} — Matchup Analysis

    **AI Matchup Breakdown:**  
    {analysis}
    """)

    st.success("Matchup analysis generated.")
# ------------- CHUNK 43: AI LINE MOVEMENT ANALYZER -------------

def _collect_line_movement_data():
    """
    Collect line movement data from today's plays.
    Requires plays to include:
    - opening_odds
    - current_odds
    """
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    movement = []

    for p in plays:
        if "opening_odds" not in p or "current_odds" not in p:
            continue

        movement.append({
            "selection": p["selection"],
            "market": p.get("market", "Unknown"),
            "opening_odds": p["opening_odds"],
            "current_odds": p["current_odds"],
            "edge": p.get("edge", 0),
            "confidence": p.get("true_confidence", 0),
        })

    return movement if movement else None


def _qwen_line_movement_prompt(movement):
    """
    Build a structured prompt for Qwen to analyze line movement.
    """
    prompt = f"""
You are an elite sports betting analyst.

Analyze the following LINE MOVEMENT DATA:

{json.dumps(movement, indent=2)}

TASKS:
1. Identify sharp vs public movement.
2. Explain why each line likely moved.
3. Highlight market-specific movement patterns.
4. Identify risk implications of the movement.
5. Provide actionable insights for bettors.
6. Keep output under 220 words.
7. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_line_movement_analysis(movement):
    """
    Call Qwen to generate line movement insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_line_movement_prompt(movement)
    response = _call_qwen(prompt)
    return response or "No line movement analysis generated."


def render_line_movement_analyzer():
    """
    Full UI for Qwen-powered line movement interpretation.
    """
    st.header("AI Line Movement Analyzer")
    st.caption("Qwen-powered interpretation of sharp vs public line movement.")

    movement = _collect_line_movement_data()
    if not movement:
        st.info("No line movement data available.")
        return

    analysis = _generate_line_movement_analysis(movement)

    themed_card_container()
    st.markdown(f"""
    ## Line Movement Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Line movement analysis generated.")
# ------------- CHUNK 44: INJURY IMPACT ANALYZER -------------

def _collect_injury_data():
    """
    Collect injury-related data from today's plays.
    Plays must include:
    - injury_notes (string)
    - injury_severity (0–10)
    """
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    injuries = []

    for p in plays:
        if "injury_notes" not in p or "injury_severity" not in p:
            continue

        injuries.append({
            "selection": p["selection"],
            "team": p.get("team") or p["selection"].split(" ")[0],
            "market": p.get("market", "Unknown"),
            "odds": p.get("odds", 0),
            "confidence": p.get("true_confidence", 0),
            "edge": p.get("edge", 0),
            "injury_notes": p["injury_notes"],
            "injury_severity": p["injury_severity"],
        })

    return injuries if injuries else None


def _qwen_injury_prompt(injuries):
    """
    Build a structured prompt for Qwen to analyze injury impact.
    """
    prompt = f"""
You are an elite sports betting analyst.

Analyze the following INJURY IMPACT DATA:

{json.dumps(injuries, indent=2)}

TASKS:
1. Identify how each injury affects the team's performance.
2. Explain market-specific injury effects (spread, totals, props).
3. Highlight volatility and risk implications.
4. Identify which injuries are most impactful.
5. Provide actionable insights for bettors.
6. Keep output under 220 words.
7. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_injury_analysis(injuries):
    """
    Call Qwen to generate injury impact insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_injury_prompt(injuries)
    response = _call_qwen(prompt)
    return response or "No injury analysis generated."


def render_injury_impact_analyzer():
    """
    Full UI for Qwen-powered injury impact modeling.
    """
    st.header("Injury Impact Analyzer")
    st.caption("Qwen-powered modeling of injury effects on markets and volatility.")

    injuries = _collect_injury_data()
    if not injuries:
        st.info("No injury data available.")
        return

    analysis = _generate_injury_analysis(injuries)

    themed_card_container()
    st.markdown(f"""
    ## Injury Impact Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Injury impact analysis generated.")
# ------------- CHUNK 45: WEATHER IMPACT ANALYZER -------------

def _collect_weather_data():
    """
    Collect weather-related data from today's plays.
    Plays must include:
    - weather (dict)
        - temp
        - wind
        - precipitation
        - humidity
        - conditions (string)
    """
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    weather_data = []

    for p in plays:
        if "weather" not in p:
            continue

        w = p["weather"]

        weather_data.append({
            "selection": p["selection"],
            "team": p.get("team") or p["selection"].split(" ")[0],
            "market": p.get("market", "Unknown"),
            "odds": p.get("odds", 0),
            "confidence": p.get("true_confidence", 0),
            "edge": p.get("edge", 0),
            "temp": w.get("temp"),
            "wind": w.get("wind"),
            "precipitation": w.get("precipitation"),
            "humidity": w.get("humidity"),
            "conditions": w.get("conditions"),
        })

    return weather_data if weather_data else None


def _qwen_weather_prompt(weather_data):
    """
    Build a structured prompt for Qwen to analyze weather impact.
    """
    prompt = f"""
You are an elite sports betting analyst.

Analyze the following WEATHER IMPACT DATA:

{json.dumps(weather_data, indent=2)}

TASKS:
1. Identify how weather affects each play (spread, totals, props).
2. Explain how wind, temperature, precipitation, and humidity influence market behavior.
3. Highlight volatility and risk implications.
4. Identify which plays are most affected by weather.
5. Provide actionable insights for bettors.
6. Keep output under 220 words.
7. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_weather_analysis(weather_data):
    """
    Call Qwen to generate weather impact insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_weather_prompt(weather_data)
    response = _call_qwen(prompt)
    return response or "No weather analysis generated."


def render_weather_impact_analyzer():
    """
    Full UI for Qwen-powered weather impact modeling.
    """
    st.header("Weather Impact Analyzer")
    st.caption("Qwen-powered modeling of weather effects on markets and volatility.")

    weather_data = _collect_weather_data()
    if not weather_data:
        st.info("No weather data available.")
        return

    analysis = _generate_weather_analysis(weather_data)

    themed_card_container()
    st.markdown(f"""
    ## Weather Impact Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Weather impact analysis generated.")
# ------------- CHUNK 46: CONFIDENCE CALIBRATION ENGINE -------------

def _collect_confidence_calibration_data():
    """
    Collect confidence-related data from today's plays + historical performance.
    """
    plays = st.session_state.today_plays.get("Top Plays", [])
    if not plays:
        return None

    # Historical performance from bet log
    log = st.session_state.bet_log

    history = []
    for b in log:
        history.append({
            "selection": b.get("selection"),
            "market": b.get("market"),
            "odds": b.get("odds"),
            "confidence": b.get("true_confidence", 0),
            "result": b.get("result"),
            "profit": b.get("profit", 0),
        })

    return {
        "today": plays,
        "history": history,
        "volatility": _compute_risk_metrics()["volatility"]
    }


def _qwen_confidence_prompt(data):
    """
    Build a structured prompt for Qwen to analyze confidence calibration.
    """
    prompt = f"""
You are an elite sports betting analyst.

Analyze the following CONFIDENCE CALIBRATION DATA:

DATA:
{json.dumps(data, indent=2)}

TASKS:
1. Identify whether today's confidence values appear overconfident or underconfident.
2. Compare today's confidence to historical performance patterns.
3. Highlight market-specific calibration issues.
4. Explain how volatility should adjust confidence.
5. Provide recommended confidence adjustments (increase/decrease/hold).
6. Keep output under 220 words.
7. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_confidence_calibration(data):
    """
    Call Qwen to generate confidence calibration insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_confidence_prompt(data)
    response = _call_qwen(prompt)
    return response or "No confidence calibration generated."


def render_confidence_calibration_engine():
    """
    Full UI for Qwen-powered confidence calibration.
    """
    st.header("Confidence Calibration Engine")
    st.caption("Qwen-powered detection of overconfidence and underconfidence.")

    data = _collect_confidence_calibration_data()
    if not data:
        st.info("No confidence data available.")
        return

    analysis = _generate_confidence_calibration(data)

    themed_card_container()
    st.markdown(f"""
    ## Confidence Calibration Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Confidence calibration complete.")
# ------------- CHUNK 47: PROBABILITY RECALIBRATION ENGINE -------------

def _collect_probability_recalibration_data():
    """
    Collect probability-related data from today's plays + historical performance.
    """
    plays = st.session_state.today_plays.get("Top Plays", [])
    if not plays:
        return None

    log = st.session_state.bet_log

    history = []
    for b in log:
        history.append({
            "selection": b.get("selection"),
            "market": b.get("market"),
            "odds": b.get("odds"),
            "true_prob": b.get("true_confidence", 0),
            "result": b.get("result"),
            "profit": b.get("profit", 0),
        })

    return {
        "today": plays,
        "history": history,
        "volatility": _compute_risk_metrics()["volatility"],
        "parlay_risk": _compute_risk_metrics()["parlay_risk"],
    }


def _qwen_probability_prompt(data):
    """
    Build a structured prompt for Qwen to analyze probability calibration.
    """
    prompt = f"""
You are an elite sports betting analyst.

Analyze the following PROBABILITY CALIBRATION DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Identify whether today's true probabilities appear inflated or undervalued.
2. Compare today's probabilities to historical outcomes.
3. Detect mispriced edges (false positives or false negatives).
4. Explain how volatility and parlay exposure should adjust true probability.
5. Provide recommended probability adjustments (increase/decrease/hold).
6. Keep output under 220 words.
7. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_probability_recalibration(data):
    """
    Call Qwen to generate probability recalibration insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_probability_prompt(data)
    response = _call_qwen(prompt)
    return response or "No probability recalibration generated."


def render_probability_recalibration_engine():
    """
    Full UI for Qwen-powered true probability recalibration.
    """
    st.header("Probability Recalibration Engine")
    st.caption("Qwen-powered detection of mispriced edges and probability correction.")

    data = _collect_probability_recalibration_data()
    if not data:
        st.info("No probability data available.")
        return

    analysis = _generate_probability_recalibration(data)

    themed_card_container()
    st.markdown(f"""
    ## Probability Recalibration Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Probability recalibration complete.")
# ------------- CHUNK 48: MARKET EFFICIENCY SCANNER -------------

def _collect_market_efficiency_data():
    """
    Collect data needed to detect market mispricing:
    - today's plays
    - historical performance
    - true probability vs implied probability
    - edge patterns
    """
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    if not plays:
        return None

    log = st.session_state.bet_log

    history = []
    for b in log:
        implied_prob = None
        if b.get("odds") is not None:
            odds = b["odds"]
            if odds > 0:
                implied_prob = 100 / (odds + 100)
            else:
                implied_prob = abs(odds) / (abs(odds) + 100)

        history.append({
            "selection": b.get("selection"),
            "market": b.get("market"),
            "odds": b.get("odds"),
            "implied_prob": implied_prob,
            "true_prob": b.get("true_confidence", 0),
            "result": b.get("result"),
            "profit": b.get("profit", 0),
        })

    # Compute implied probability for today's plays
    today = []
    for p in plays:
        odds = p.get("odds")
        if odds is None:
            continue

        if odds > 0:
            implied_prob = 100 / (odds + 100)
        else:
            implied_prob = abs(odds) / (abs(odds) + 100)

        today.append({
            "selection": p["selection"],
            "market": p.get("market", "Unknown"),
            "odds": odds,
            "implied_prob": implied_prob,
            "true_prob": p.get("true_confidence", 0) / 100,
            "edge": p.get("edge", 0),
        })

    return {
        "today": today,
        "history": history,
        "volatility": _compute_risk_metrics()["volatility"],
        "parlay_risk": _compute_risk_metrics()["parlay_risk"],
    }


def _qwen_market_efficiency_prompt(data):
    """
    Build a structured prompt for Qwen to analyze market efficiency.
    """
    prompt = f"""
You are an elite sports betting analyst.

Analyze the following MARKET EFFICIENCY DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Identify overpriced and underpriced markets.
2. Detect mispriced edges (false positives or hidden value).
3. Compare implied probability vs true probability.
4. Highlight market-specific inefficiencies.
5. Explain how volatility and parlay exposure affect pricing accuracy.
6. Provide actionable insights for bettors.
7. Keep output under 230 words.
8. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_efficiency_analysis(data):
    """
    Call Qwen to generate market efficiency insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_market_efficiency_prompt(data)
    response = _call_qwen(prompt)
    return response or "No market efficiency analysis generated."


def render_market_efficiency_scanner():
    """
    Full UI for Qwen-powered market mispricing detection.
    """
    st.header("Market Efficiency Scanner")
    st.caption("Qwen-powered detection of overpriced and underpriced markets.")

    data = _collect_market_efficiency_data()
    if not data:
        st.info("No market efficiency data available.")
        return

    analysis = _generate_market_efficiency_analysis(data)

    themed_card_container()
    st.markdown(f"""
    ## Market Efficiency Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Market efficiency scan complete.")
# ------------- CHUNK 49: BET QUALITY GRADER (A–F + QWEN JUSTIFICATION) -------------

def _collect_bet_quality_data():
    """
    Collect data needed to grade today's plays:
    - odds
    - true probability
    - implied probability
    - edge
    - volatility
    - market type
    """
    plays = st.session_state.today_plays.get("Top Plays", [])
    if not plays:
        return None

    risk = _compute_risk_metrics()

    graded = []

    for p in plays:
        odds = p.get("odds")
        if odds is None:
            continue

        # Compute implied probability
        if odds > 0:
            implied_prob = 100 / (odds + 100)
        else:
            implied_prob = abs(odds) / (abs(odds) + 100)

        graded.append({
            "selection": p["selection"],
            "market": p.get("market", "Unknown"),
            "odds": odds,
            "true_prob": p.get("true_confidence", 0) / 100,
            "implied_prob": implied_prob,
            "edge": p.get("edge", 0),
            "volatility": risk["volatility"],
            "parlay_risk": risk["parlay_risk"],
        })

    return graded


def _qwen_grade_prompt(play):
    """
    Build a structured prompt for Qwen to grade a single play.
    """
    prompt = f"""
You are an elite sports betting analyst.

GRADE THE FOLLOWING PLAY:

{json.dumps(play, indent=2)}

TASKS:
1. Assign a letter grade (A, B, C, D, or F).
2. Justify the grade using:
   - true probability vs implied probability
   - edge quality
   - market type
   - volatility
   - parlay exposure
3. Identify strengths and weaknesses of the play.
4. Provide 1–2 actionable notes.
5. Keep output under 140 words.
6. Tone: analytical, concise, high-signal.
7. Start with: "GRADE: X"
"""
    return prompt


def _generate_bet_grade(play):
    """
    Call Qwen to generate a grade + justification.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "GRADE: N/A — Qwen disabled."

    prompt = _qwen_grade_prompt(play)
    response = _call_qwen(prompt)
    return response or "GRADE: N/A — No grade generated."


def render_bet_quality_grader():
    """
    Full UI for Qwen-powered A–F grading of today's plays.
    """
    st.header("Bet Quality Grader")
    st.caption("Qwen-powered A–F grading system with justification.")

    plays = _collect_bet_quality_data()
    if not plays:
        st.info("No plays available for grading.")
        return

    for play in plays:
        grade_text = _generate_bet_grade(play)

        themed_card_container()
        st.markdown(f"""
        ### {play['selection']}
        Market: {play['market']}  
        Odds: {play['odds']}  
        True Probability: {round(play['true_prob'] * 100, 1)}%  
        Implied Probability: {round(play['implied_prob'] * 100, 1)}%  
        Edge: {play['edge']}  

        **AI Grade & Justification:**  
        {grade_text}
        """)

    st.success("Bet quality grading complete.")
# ------------- CHUNK 50: AI RISK COMMENTARY ENGINE -------------

def _collect_slate_risk_data():
    """
    Collect full-slate risk data:
    - volatility
    - parlay exposure
    - market concentration
    - team concentration
    - edge distribution
    - confidence distribution
    """
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    if not plays:
        return None

    risk = _compute_risk_metrics()

    markets = {}
    teams = {}
    edges = []
    confs = []

    for p in plays:
        market = p.get("market", "Unknown")
        team = p.get("team") or p["selection"].split(" ")[0]

        markets[market] = markets.get(market, 0) + 1
        teams[team] = teams.get(team, 0) + 1

        edges.append(p.get("edge", 0))
        confs.append(p.get("true_confidence", 0))

    return {
        "volatility": risk["volatility"],
        "parlay_risk": risk["parlay_risk"],
        "market_concentration": markets,
        "team_concentration": teams,
        "edge_distribution": edges,
        "confidence_distribution": confs,
        "num_plays": len(plays),
    }


def _qwen_risk_prompt(data):
    """
    Build a structured prompt for Qwen to analyze slate-level risk.
    """
    prompt = f"""
You are an elite sports betting risk analyst.

Analyze the following FULL-SLATE RISK DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Provide a macro-level risk assessment of today's slate.
2. Identify volatility-driven risks.
3. Identify parlay exposure risks.
4. Highlight market concentration and team concentration risks.
5. Evaluate edge and confidence distribution for hidden risk.
6. Provide actionable risk management recommendations.
7. Keep output under 230 words.
8. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_slate_risk_commentary(data):
    """
    Call Qwen to generate slate-level risk commentary.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_risk_prompt(data)
    response = _call_qwen(prompt)
    return response or "No risk commentary generated."


def render_ai_risk_commentary_engine():
    """
    Full UI for Qwen-powered slate-level risk commentary.
    """
    st.header("AI Risk Commentary Engine")
    st.caption("Qwen-powered macro-level risk analysis for the entire slate.")

    data = _collect_slate_risk_data()
    if not data:
        st.info("No slate data available for risk commentary.")
        return

    commentary = _generate_slate_risk_commentary(data)

    themed_card_container()
    st.markdown(f"""
    ## Slate Risk Commentary

    **AI Interpretation:**  
    {commentary}
    """)

    st.success("Slate-level risk commentary generated.")
# ------------- CHUNK 51: AI SLATE SUMMARY ENGINE -------------

def _collect_slate_summary_data():
    """
    Collect full-slate summary data:
    - number of plays
    - distribution by market
    - distribution by team
    - average edge
    - average confidence
    - volatility
    - parlay exposure
    - top edges
    - weakest edges
    """
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    if not plays:
        return None

    risk = _compute_risk_metrics()

    markets = {}
    teams = {}
    edges = []
    confs = []

    for p in plays:
        market = p.get("market", "Unknown")
        team = p.get("team") or p["selection"].split(" ")[0]

        markets[market] = markets.get(market, 0) + 1
        teams[team] = teams.get(team, 0) + 1

        edges.append(p.get("edge", 0))
        confs.append(p.get("true_confidence", 0))

    # Identify top and bottom edges
    sorted_edges = sorted(plays, key=lambda x: x.get("edge", 0), reverse=True)
    top_edges = sorted_edges[:3]
    bottom_edges = sorted_edges[-3:]

    return {
        "num_plays": len(plays),
        "market_distribution": markets,
        "team_distribution": teams,
        "avg_edge": round(sum(edges) / len(edges), 2) if edges else 0,
        "avg_confidence": round(sum(confs) / len(confs), 2) if confs else 0,
        "volatility": risk["volatility"],
        "parlay_risk": risk["parlay_risk"],
        "top_edges": top_edges,
        "bottom_edges": bottom_edges,
    }


def _qwen_slate_summary_prompt(data):
    """
    Build a structured prompt for Qwen to generate a slate summary.
    """
    prompt = f"""
You are an elite sports betting analyst.

Provide a DAILY SLATE SUMMARY based on the following data:

{json.dumps(data, indent=2)}

TASKS:
1. Provide a concise overview of today's slate.
2. Highlight key opportunities (strong edges, strong markets).
3. Highlight key risks (volatility, concentration, weak edges).
4. Identify market-level and slate-level themes.
5. Provide 3–5 actionable notes for bettors.
6. Keep output under 230 words.
7. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_slate_summary(data):
    """
    Call Qwen to generate the slate summary.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_slate_summary_prompt(data)
    response = _call_qwen(prompt)
    return response or "No slate summary generated."


def render_slate_summary_engine():
    """
    Full UI for Qwen-powered daily slate summary.
    """
    st.header("AI Slate Summary")
    st.caption("Qwen-powered daily overview of the entire slate.")

    data = _collect_slate_summary_data()
    if not data:
        st.info("No slate data available for summary.")
        return

    summary = _generate_slate_summary(data)

    themed_card_container()
    st.markdown(f"""
    ## Daily Slate Summary

    **AI Interpretation:**  
    {summary}
    """)

    st.success("Slate summary generated.")
# ------------- CHUNK 52: BETTING STYLE PROFILER (USER BEHAVIOR ANALYSIS) -------------

def _collect_user_behavior_history():
    """
    Build a dataset of the user's betting behavior from the bet log:
    - preferred markets
    - preferred teams
    - average odds
    - average confidence
    - average edge
    - volatility of results
    - profit distribution
    """
    log = st.session_state.bet_log
    if not log:
        return None

    markets = {}
    teams = {}
    odds_list = []
    conf_list = []
    edge_list = []
    profits = []

    for b in log:
        market = b.get("market", "Unknown")
        team = b.get("team") or (b.get("selection", "").split(" ")[0])

        markets[market] = markets.get(market, 0) + 1
        teams[team] = teams.get(team, 0) + 1

        if b.get("odds") is not None:
            odds_list.append(b["odds"])

        conf_list.append(b.get("true_confidence", 0))
        edge_list.append(b.get("edge", 0))
        profits.append(b.get("profit", 0))

    return {
        "market_preferences": markets,
        "team_preferences": teams,
        "avg_odds": round(sum(odds_list) / len(odds_list), 2) if odds_list else 0,
        "avg_confidence": round(sum(conf_list) / len(conf_list), 2) if conf_list else 0,
        "avg_edge": round(sum(edge_list) / len(edge_list), 2) if edge_list else 0,
        "profit_distribution": profits,
        "volatility": _compute_risk_metrics()["volatility"],
    }


def _qwen_user_profile_prompt(data):
    """
    Build a structured prompt for Qwen to analyze the user's betting style.
    """
    prompt = f"""
You are an elite sports betting analyst.

Analyze the following USER BETTING HISTORY:

{json.dumps(data, indent=2)}

TASKS:
1. Identify the user's betting tendencies (markets, teams, odds ranges).
2. Highlight strengths and weaknesses in their betting style.
3. Identify risk patterns (volatility, concentration, edge quality).
4. Provide a clear betting style profile (e.g., conservative, aggressive, value-driven).
5. Provide 3–5 actionable recommendations to improve performance.
6. Keep output under 230 words.
7. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_user_betting_profile(data):
    """
    Call Qwen to generate the user's betting style profile.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_user_profile_prompt(data)
    response = _call_qwen(prompt)
    return response or "No betting style profile generated."


def render_betting_style_profiler():
    """
    Full UI for Qwen-powered user betting behavior analysis.
    """
    st.header("Betting Style Profiler")
    st.caption("Qwen-powered analysis of your betting tendencies and strengths.")

    data = _collect_user_behavior_history()
    if not data:
        st.info("No betting history available for profiling.")
        return

    profile = _generate_user_betting_profile(data)

    themed_card_container()
    st.markdown(f"""
    ## Your Betting Style Profile

    **AI Interpretation:**  
    {profile}
    """)

    st.success("Betting style profile generated.")
# ------------- CHUNK 53: BANKROLL HEALTH MONITOR -------------

def _collect_bankroll_health_data():
    """
    Collect bankroll-related data:
    - bankroll history (from bet log cumulative profit)
    - win/loss streaks
    - volatility
    - unit sizing patterns
    - risk exposure
    """
    log = st.session_state.bet_log
    if not log:
        return None

    bankroll_curve = []
    cumulative = 0
    streak = 0
    max_streak = 0
    min_streak = 0

    unit_sizes = []
    results = []

    for b in log:
        profit = b.get("profit", 0)
        cumulative += profit
        bankroll_curve.append(cumulative)

        # Track streaks
        if profit > 0:
            streak = streak + 1 if streak >= 0 else 1
        elif profit < 0:
            streak = streak - 1 if streak <= 0 else -1
        else:
            streak = 0

        max_streak = max(max_streak, streak)
        min_streak = min(min_streak, streak)

        # Track unit sizes
        if "units" in b:
            unit_sizes.append(b["units"])

        results.append(profit)

    risk = _compute_risk_metrics()

    return {
        "bankroll_curve": bankroll_curve,
        "max_streak": max_streak,
        "min_streak": min_streak,
        "unit_sizes": unit_sizes,
        "volatility": risk["volatility"],
        "parlay_risk": risk["parlay_risk"],
        "results": results,
    }


def _qwen_bankroll_prompt(data):
    """
    Build a structured prompt for Qwen to analyze bankroll health.
    """
    prompt = f"""
You are an elite sports betting bankroll analyst.

Analyze the following BANKROLL HEALTH DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Evaluate the user's bankroll stability and trend.
2. Identify risk-of-ruin factors (volatility, streaks, exposure).
3. Assess whether unit sizing is healthy or risky.
4. Highlight bankroll vulnerabilities (overbetting, variance sensitivity).
5. Provide 3–5 actionable recommendations to improve bankroll health.
6. Keep output under 230 words.
7. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_bankroll_health_analysis(data):
    """
    Call Qwen to generate bankroll health commentary.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_bankroll_prompt(data)
    response = _call_qwen(prompt)
    return response or "No bankroll health analysis generated."


def render_bankroll_health_monitor():
    """
    Full UI for Qwen-powered bankroll stability analysis.
    """
    st.header("Bankroll Health Monitor")
    st.caption("Qwen-powered analysis of bankroll stability, risk, and unit sizing.")

    data = _collect_bankroll_health_data()
    if not data:
        st.info("No bankroll data available.")
        return

    analysis = _generate_bankroll_health_analysis(data)

    themed_card_container()
    st.markdown(f"""
    ## Bankroll Health Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Bankroll health analysis complete.")
# ------------- CHUNK 54: PERFORMANCE ATTRIBUTION ENGINE -------------

def _collect_performance_attribution_data():
    """
    Build a dataset explaining why the user won or lost:
    - performance by market
    - performance by team
    - performance by odds range
    - performance by confidence bucket
    - performance by edge bucket
    """
    log = st.session_state.bet_log
    if not log:
        return None

    markets = {}
    teams = {}
    odds_ranges = {"plus_long": [], "plus_short": [], "minus_short": [], "minus_long": []}
    conf_buckets = {"low": [], "mid": [], "high": []}
    edge_buckets = {"negative": [], "small": [], "medium": [], "large": []}

    for b in log:
        profit = b.get("profit", 0)
        odds = b.get("odds")
        conf = b.get("true_confidence", 0)
        edge = b.get("edge", 0)
        team = b.get("team") or (b.get("selection", "").split(" ")[0])
        market = b.get("market", "Unknown")

        # Market attribution
        markets.setdefault(market, []).append(profit)

        # Team attribution
        teams.setdefault(team, []).append(profit)

        # Odds range attribution
        if odds is not None:
            if odds >= +150:
                odds_ranges["plus_long"].append(profit)
            elif +100 <= odds < +150:
                odds_ranges["plus_short"].append(profit)
            elif -150 <= odds < 0:
                odds_ranges["minus_short"].append(profit)
            elif odds < -150:
                odds_ranges["minus_long"].append(profit)

        # Confidence bucket attribution
        if conf < 55:
            conf_buckets["low"].append(profit)
        elif 55 <= conf < 70:
            conf_buckets["mid"].append(profit)
        else:
            conf_buckets["high"].append(profit)

        # Edge bucket attribution
        if edge < 0:
            edge_buckets["negative"].append(profit)
        elif 0 <= edge < 3:
            edge_buckets["small"].append(profit)
        elif 3 <= edge < 7:
            edge_buckets["medium"].append(profit)
        else:
            edge_buckets["large"].append(profit)

    return {
        "markets": markets,
        "teams": teams,
        "odds_ranges": odds_ranges,
        "confidence_buckets": conf_buckets,
        "edge_buckets": edge_buckets,
    }


def _qwen_performance_attribution_prompt(data):
    """
    Build a structured prompt for Qwen to explain why the user won or lost.
    """
    prompt = f"""
You are an elite sports betting performance analyst.

Analyze the following PERFORMANCE ATTRIBUTION DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Explain WHY the user won or lost overall.
2. Identify which markets contributed most to profit or loss.
3. Identify which teams contributed most to profit or loss.
4. Identify which odds ranges were profitable or unprofitable.
5. Identify which confidence and edge buckets performed best/worst.
6. Provide 3–5 actionable recommendations to improve future performance.
7. Keep output under 240 words.
8. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_performance_attribution(data):
    """
    Call Qwen to generate performance attribution commentary.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_performance_attribution_prompt(data)
    response = _call_qwen(prompt)
    return response or "No performance attribution generated."


def render_performance_attribution_engine():
    """
    Full UI for Qwen-powered performance attribution.
    """
    st.header("Performance Attribution Engine")
    st.caption("Qwen-powered analysis explaining why you won or lost.")

    data = _collect_performance_attribution_data()
    if not data:
        st.info("No performance data available.")
        return

    analysis = _generate_performance_attribution(data)

    themed_card_container()
    st.markdown(f"""
    ## Performance Attribution

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Performance attribution analysis complete.")
# ------------- CHUNK 55: PREDICTIVE COMMENTARY ENGINE -------------

def _collect_predictive_commentary_data():
    """
    Collect data needed for forward-looking predictive insights:
    - today's plays
    - historical performance
    - volatility
    - market trends
    - edge trends
    - confidence trends
    """
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    log = st.session_state.bet_log

    if not plays or not log:
        return None

    # Extract trends from historical log
    edges = [b.get("edge", 0) for b in log]
    confs = [b.get("true_confidence", 0) for b in log]
    profits = [b.get("profit", 0) for b in log]

    risk = _compute_risk_metrics()

    return {
        "today": plays,
        "historical_edges": edges,
        "historical_confidence": confs,
        "historical_profits": profits,
        "volatility": risk["volatility"],
        "parlay_risk": risk["parlay_risk"],
    }


def _qwen_predictive_prompt(data):
    """
    Build a structured prompt for Qwen to generate forward-looking insights.
    """
    prompt = f"""
You are an elite sports betting analyst.

Provide FORWARD-LOOKING PREDICTIVE COMMENTARY based on the following data:

{json.dumps(data, indent=2)}

TASKS:
1. Identify emerging trends from today's slate and historical patterns.
2. Predict which markets are likely to be profitable or risky moving forward.
3. Highlight forward-looking volatility risks.
4. Identify potential opportunities based on edge and confidence trends.
5. Provide 3–5 actionable forward-looking recommendations.
6. Keep output under 240 words.
7. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_predictive_commentary(data):
    """
    Call Qwen to generate predictive insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_predictive_prompt(data)
    response = _call_qwen(prompt)
    return response or "No predictive commentary generated."


def render_predictive_commentary_engine():
    """
    Full UI for Qwen-powered forward-looking predictive insights.
    """
    st.header("Predictive Commentary Engine")
    st.caption("Qwen-powered forward-looking insights for upcoming slates.")

    data = _collect_predictive_commentary_data()
    if not data:
        st.info("Not enough data for predictive commentary.")
        return

    commentary = _generate_predictive_commentary(data)

    themed_card_container()
    st.markdown(f"""
    ## Predictive Commentary

    **AI Interpretation:**  
    {commentary}
    """)

    st.success("Predictive commentary generated.")
# ------------- CHUNK 56: MARKET REGIME DETECTOR -------------

def _collect_market_regime_data():
    """
    Collect data needed to classify the current market regime:
    - volatility
    - parlay exposure
    - average edge
    - edge variance
    - confidence variance
    - market distribution
    - historical profit trend
    """
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    log = st.session_state.bet_log

    if not plays or not log:
        return None

    risk = _compute_risk_metrics()

    # Market distribution
    markets = {}
    for p in plays:
        m = p.get("market", "Unknown")
        markets[m] = markets.get(m, 0) + 1

    # Edge and confidence variance
    edges = [p.get("edge", 0) for p in plays]
    confs = [p.get("true_confidence", 0) for p in plays]

    edge_var = float(np.var(edges)) if edges else 0
    conf_var = float(np.var(confs)) if confs else 0

    # Historical profit trend
    profits = [b.get("profit", 0) for b in log]
    cumulative = np.cumsum(profits).tolist() if profits else []

    return {
        "volatility": risk["volatility"],
        "parlay_risk": risk["parlay_risk"],
        "market_distribution": markets,
        "avg_edge": round(sum(edges) / len(edges), 2) if edges else 0,
        "edge_variance": edge_var,
        "confidence_variance": conf_var,
        "profit_trend": cumulative,
    }


def _qwen_market_regime_prompt(data):
    """
    Build a structured prompt for Qwen to classify the market regime.
    """
    prompt = f"""
You are an elite sports betting macro-market analyst.

Classify the CURRENT MARKET REGIME using the following data:

{json.dumps(data, indent=2)}

TASKS:
1. Identify the current market regime:
   - Hot (edges hitting, stable confidence)
   - Cold (edges failing, negative drift)
   - Volatile (high variance, unstable edges)
   - Stable (low variance, predictable markets)
2. Explain WHY the market is in this regime.
3. Highlight risks associated with this regime.
4. Highlight opportunities associated with this regime.
5. Provide regime-specific strategy recommendations.
6. Keep output under 240 words.
7. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_regime_analysis(data):
    """
    Call Qwen to generate market regime classification.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_market_regime_prompt(data)
    response = _call_qwen(prompt)
    return response or "No market regime analysis generated."


def render_market_regime_detector():
    """
    Full UI for Qwen-powered market regime detection.
    """
    st.header("Market Regime Detector")
    st.caption("Qwen-powered classification of current market state.")

    data = _collect_market_regime_data()
    if not data:
        st.info("Not enough data for market regime detection.")
        return

    regime = _generate_market_regime_analysis(data)

    themed_card_container()
    st.markdown(f"""
    ## Market Regime Analysis

    **AI Interpretation:**  
    {regime}
    """)

    st.success("Market regime detection complete.")
# ------------- CHUNK 57: MARKET CORRELATION ENGINE -------------

def _collect_market_correlation_data():
    """
    Build a dataset for correlation analysis:
    - correlations between markets
    - correlations between teams
    - correlations between odds ranges
    - correlations between confidence buckets
    - correlations between edge buckets
    """
    log = st.session_state.bet_log
    if not log:
        return None

    # Prepare buckets
    market_profits = {}
    team_profits = {}
    odds_buckets = {"plus_long": [], "plus_short": [], "minus_short": [], "minus_long": []}
    conf_buckets = {"low": [], "mid": [], "high": []}
    edge_buckets = {"negative": [], "small": [], "medium": [], "large": []}

    for b in log:
        profit = b.get("profit", 0)
        odds = b.get("odds")
        conf = b.get("true_confidence", 0)
        edge = b.get("edge", 0)
        team = b.get("team") or (b.get("selection", "").split(" ")[0])
        market = b.get("market", "Unknown")

        # Market-level profit tracking
        market_profits.setdefault(market, []).append(profit)

        # Team-level profit tracking
        team_profits.setdefault(team, []).append(profit)

        # Odds bucket correlation
        if odds is not None:
            if odds >= +150:
                odds_buckets["plus_long"].append(profit)
            elif +100 <= odds < +150:
                odds_buckets["plus_short"].append(profit)
            elif -150 <= odds < 0:
                odds_buckets["minus_short"].append(profit)
            elif odds < -150:
                odds_buckets["minus_long"].append(profit)

        # Confidence bucket correlation
        if conf < 55:
            conf_buckets["low"].append(profit)
        elif 55 <= conf < 70:
            conf_buckets["mid"].append(profit)
        else:
            conf_buckets["high"].append(profit)

        # Edge bucket correlation
        if edge < 0:
            edge_buckets["negative"].append(profit)
        elif 0 <= edge < 3:
            edge_buckets["small"].append(profit)
        elif 3 <= edge < 7:
            edge_buckets["medium"].append(profit)
        else:
            edge_buckets["large"].append(profit)

    return {
        "market_profits": market_profits,
        "team_profits": team_profits,
        "odds_buckets": odds_buckets,
        "confidence_buckets": conf_buckets,
        "edge_buckets": edge_buckets,
    }


def _qwen_correlation_prompt(data):
    """
    Build a structured prompt for Qwen to analyze market correlations.
    """
    prompt = f"""
You are an elite sports betting macro-risk analyst.

Analyze the following MARKET CORRELATION DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Identify correlated markets (positive and negative).
2. Identify correlated teams (risk clusters).
3. Identify correlated odds ranges, confidence buckets, and edge buckets.
4. Highlight hidden risk clusters and diversification gaps.
5. Provide 3–5 actionable diversification recommendations.
6. Keep output under 240 words.
7. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_correlation_analysis(data):
    """
    Call Qwen to generate correlation mapping insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_correlation_prompt(data)
    response = _call_qwen(prompt)
    return response or "No correlation analysis generated."


def render_market_correlation_engine():
    """
    Full UI for Qwen-powered correlation mapping.
    """
    st.header("Market Correlation Engine")
    st.caption("Qwen-powered detection of correlated markets and hidden risk clusters.")

    data = _collect_market_correlation_data()
    if not data:
        st.info("Not enough data for correlation analysis.")
        return

    analysis = _generate_market_correlation_analysis(data)

    themed_card_container()
    st.markdown(f"""
    ## Market Correlation Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Market correlation analysis complete.")
# ------------- CHUNK 58: MARKET SENSITIVITY ENGINE -------------

def _collect_market_sensitivity_data():
    """
    Collect data needed for sensitivity analysis:
    - today's plays
    - odds movement potential
    - volatility exposure
    - confidence drift exposure
    - edge compression/expansion exposure
    """
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    if not plays:
        return None

    risk = _compute_risk_metrics()

    sensitivity_dataset = []

    for p in plays:
        odds = p.get("odds")
        true_prob = p.get("true_confidence", 0)
        edge = p.get("edge", 0)

        # Compute implied probability
        if odds is not None:
            if odds > 0:
                implied_prob = 100 / (odds + 100)
            else:
                implied_prob = abs(odds) / (abs(odds) + 100)
        else:
            implied_prob = None

        sensitivity_dataset.append({
            "selection": p["selection"],
            "market": p.get("market", "Unknown"),
            "odds": odds,
            "implied_prob": implied_prob,
            "true_prob": true_prob / 100,
            "edge": edge,
            "volatility": risk["volatility"],
            "parlay_risk": risk["parlay_risk"],
        })

    return sensitivity_dataset


def _qwen_sensitivity_prompt(data):
    """
    Build a structured prompt for Qwen to analyze sensitivity.
    """
    prompt = f"""
You are an elite sports betting macro-risk analyst.

Analyze the following MARKET SENSITIVITY DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Evaluate sensitivity to odds movement (which plays break if odds shift).
2. Evaluate sensitivity to volatility (which plays become unstable).
3. Evaluate sensitivity to confidence drift (which plays lose value).
4. Evaluate sensitivity to edge compression/expansion.
5. Identify the most fragile and most robust plays.
6. Provide 3–5 actionable sensitivity management recommendations.
7. Keep output under 240 words.
8. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_sensitivity_analysis(data):
    """
    Call Qwen to generate sensitivity insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_sensitivity_prompt(data)
    response = _call_qwen(prompt)
    return response or "No sensitivity analysis generated."


def render_market_sensitivity_engine():
    """
    Full UI for Qwen-powered sensitivity analysis.
    """
    st.header("Market Sensitivity Engine")
    st.caption("Qwen-powered sensitivity analysis for odds, volatility, confidence, and edge.")

    data = _collect_market_sensitivity_data()
    if not data:
        st.info("No data available for sensitivity analysis.")
        return

    analysis = _generate_market_sensitivity_analysis(data)

    themed_card_container()
    st.markdown(f"""
    ## Market Sensitivity Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Market sensitivity analysis complete.")
# ------------- CHUNK 59: MARKET PRESSURE ENGINE -------------

def _collect_market_pressure_data():
    """
    Collect data needed to detect market pressure:
    - volatility
    - parlay exposure
    - market concentration
    - edge compression
    - confidence compression
    - slate-wide fragility indicators
    """
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    if not plays:
        return None

    risk = _compute_risk_metrics()

    markets = {}
    edges = []
    confs = []

    for p in plays:
        m = p.get("market", "Unknown")
        markets[m] = markets.get(m, 0) + 1

        edges.append(p.get("edge", 0))
        confs.append(p.get("true_confidence", 0))

    # Edge compression = edges clustering tightly
    edge_compression = float(np.var(edges)) if edges else 0

    # Confidence compression = confidence clustering tightly
    conf_compression = float(np.var(confs)) if confs else 0

    return {
        "volatility": risk["volatility"],
        "parlay_risk": risk["parlay_risk"],
        "market_concentration": markets,
        "edge_compression": edge_compression,
        "confidence_compression": conf_compression,
        "num_plays": len(plays),
    }


def _qwen_market_pressure_prompt(data):
    """
    Build a structured prompt for Qwen to analyze market pressure.
    """
    prompt = f"""
You are an elite sports betting macro-risk analyst.

Analyze the following MARKET PRESSURE DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Identify pressure points across the slate (markets under stress).
2. Identify systemic risk factors (volatility, concentration, compression).
3. Highlight which markets are most stress-sensitive.
4. Highlight which markets are most resilient.
5. Provide 3–5 actionable recommendations to manage market pressure.
6. Keep output under 240 words.
7. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_pressure_analysis(data):
    """
    Call Qwen to generate market pressure insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_market_pressure_prompt(data)
    response = _call_qwen(prompt)
    return response or "No market pressure analysis generated."


def render_market_pressure_engine():
    """
    Full UI for Qwen-powered market pressure detection.
    """
    st.header("Market Pressure Engine")
    st.caption("Qwen-powered detection of market stress and systemic risk.")

    data = _collect_market_pressure_data()
    if not data:
        st.info("No data available for market pressure analysis.")
        return

    analysis = _generate_market_pressure_analysis(data)

    themed_card_container()
    st.markdown(f"""
    ## Market Pressure Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Market pressure analysis complete.")
# ------------- CHUNK 60: MARKET STABILITY ENGINE -------------

def _collect_market_stability_data():
    """
    Collect data needed to classify market stability:
    - volatility
    - parlay exposure
    - edge variance
    - confidence variance
    - market-level performance consistency
    - historical stability patterns
    """
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    log = st.session_state.bet_log

    if not plays or not log:
        return None

    risk = _compute_risk_metrics()

    # Market-level performance consistency
    market_perf = {}
    for b in log:
        market = b.get("market", "Unknown")
        profit = b.get("profit", 0)
        market_perf.setdefault(market, []).append(profit)

    # Compute variance per market
    market_variances = {
        m: float(np.var(v)) if len(v) > 1 else 0
        for m, v in market_perf.items()
    }

    # Edge and confidence variance for today's slate
    edges = [p.get("edge", 0) for p in plays]
    confs = [p.get("true_confidence", 0) for p in plays]

    edge_var = float(np.var(edges)) if edges else 0
    conf_var = float(np.var(confs)) if confs else 0

    return {
        "volatility": risk["volatility"],
        "parlay_risk": risk["parlay_risk"],
        "market_variances": market_variances,
        "edge_variance": edge_var,
        "confidence_variance": conf_var,
        "num_plays": len(plays),
    }


def _qwen_market_stability_prompt(data):
    """
    Build a structured prompt for Qwen to classify market stability.
    """
    prompt = f"""
You are an elite sports betting macro-market analyst.

Classify MARKET STABILITY using the following data:

{json.dumps(data, indent=2)}

TASKS:
1. Identify which markets are stable vs unstable.
2. Explain WHY each market is stable or unstable.
3. Highlight reliability patterns across the slate.
4. Identify stability-driven opportunities and risks.
5. Provide 3–5 stability-based strategy recommendations.
6. Keep output under 240 words.
7. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_stability_analysis(data):
    """
    Call Qwen to generate market stability insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_market_stability_prompt(data)
    response = _call_qwen(prompt)
    return response or "No market stability analysis generated."


def render_market_stability_engine():
    """
    Full UI for Qwen-powered market stability classification.
    """
    st.header("Market Stability Engine")
    st.caption("Qwen-powered classification of stable vs unstable markets.")

    data = _collect_market_stability_data()
    if not data:
        st.info("No data available for market stability analysis.")
        return

    analysis = _generate_market_stability_analysis(data)

    themed_card_container()
    st.markdown(f"""
    ## Market Stability Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Market stability analysis complete.")
# ------------- CHUNK 61: MARKET DRIFT ENGINE -------------

def _collect_market_drift_data():
    """
    Collect data needed to detect drift:
    - historical edge trend
    - historical confidence trend
    - historical profit trend
    - today's edge distribution
    - today's confidence distribution
    - volatility and parlay exposure
    """
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    log = st.session_state.bet_log

    if not plays or not log:
        return None

    # Historical trends
    hist_edges = [b.get("edge", 0) for b in log]
    hist_conf = [b.get("true_confidence", 0) for b in log]
    hist_profit = [b.get("profit", 0) for b in log]

    # Today's distributions
    today_edges = [p.get("edge", 0) for p in plays]
    today_conf = [p.get("true_confidence", 0) for p in plays]

    risk = _compute_risk_metrics()

    return {
        "historical_edges": hist_edges,
        "historical_confidence": hist_conf,
        "historical_profit": hist_profit,
        "today_edges": today_edges,
        "today_confidence": today_conf,
        "volatility": risk["volatility"],
        "parlay_risk": risk["parlay_risk"],
    }


def _qwen_market_drift_prompt(data):
    """
    Build a structured prompt for Qwen to analyze drift.
    """
    prompt = f"""
You are an elite sports betting macro-market analyst.

Analyze the following MARKET DRIFT DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Identify drift in edges (positive, negative, or neutral).
2. Identify drift in confidence (inflation, deflation, or stability).
3. Identify drift in market behavior (profit trend, variance trend).
4. Highlight risks associated with negative drift.
5. Highlight opportunities associated with positive drift.
6. Provide 3–5 actionable drift-management recommendations.
7. Keep output under 240 words.
8. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_drift_analysis(data):
    """
    Call Qwen to generate drift insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_market_drift_prompt(data)
    response = _call_qwen(prompt)
    return response or "No market drift analysis generated."


def render_market_drift_engine():
    """
    Full UI for Qwen-powered drift detection.
    """
    st.header("Market Drift Engine")
    st.caption("Qwen-powered detection of drift in edges, confidence, and market behavior.")

    data = _collect_market_drift_data()
    if not data:
        st.info("No data available for market drift analysis.")
        return

    analysis = _generate_market_drift_analysis(data)

    themed_card_container()
    st.markdown(f"""
    ## Market Drift Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Market drift analysis complete.")
# ------------- CHUNK 62: MARKET MOMENTUM ENGINE -------------

def _collect_market_momentum_data():
    """
    Collect data needed to detect market momentum:
    - historical edge trend
    - historical confidence trend
    - historical profit trend
    - rolling momentum windows
    - today's edge and confidence distributions
    - volatility and parlay exposure
    """
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    log = st.session_state.bet_log

    if not plays or not log:
        return None

    # Historical trends
    hist_edges = [b.get("edge", 0) for b in log]
    hist_conf = [b.get("true_confidence", 0) for b in log]
    hist_profit = [b.get("profit", 0) for b in log]

    # Rolling momentum windows (simple)
    def rolling_avg(arr, window=5):
        if len(arr) < window:
            return []
        return [sum(arr[i:i+window]) / window for i in range(len(arr) - window + 1)]

    edge_momentum = rolling_avg(hist_edges, window=5)
    conf_momentum = rolling_avg(hist_conf, window=5)
    profit_momentum = rolling_avg(hist_profit, window=5)

    # Today's distributions
    today_edges = [p.get("edge", 0) for p in plays]
    today_conf = [p.get("true_confidence", 0) for p in plays]

    risk = _compute_risk_metrics()

    return {
        "historical_edges": hist_edges,
        "historical_confidence": hist_conf,
        "historical_profit": hist_profit,
        "edge_momentum": edge_momentum,
        "confidence_momentum": conf_momentum,
        "profit_momentum": profit_momentum,
        "today_edges": today_edges,
        "today_confidence": today_conf,
        "volatility": risk["volatility"],
        "parlay_risk": risk["parlay_risk"],
    }


def _qwen_market_momentum_prompt(data):
    """
    Build a structured prompt for Qwen to analyze market momentum.
    """
    prompt = f"""
You are an elite sports betting macro-market analyst.

Analyze the following MARKET MOMENTUM DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Identify positive vs negative momentum in:
   - edges
   - confidence
   - profit trend
2. Identify acceleration vs deceleration in market behavior.
3. Highlight momentum-driven opportunities.
4. Highlight momentum-driven risks.
5. Provide 3–5 actionable momentum-based strategy recommendations.
6. Keep output under 240 words.
7. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_momentum_analysis(data):
    """
    Call Qwen to generate momentum insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_market_momentum_prompt(data)
    response = _call_qwen(prompt)
    return response or "No market momentum analysis generated."


def render_market_momentum_engine():
    """
    Full UI for Qwen-powered momentum detection.
    """
    st.header("Market Momentum Engine")
    st.caption("Qwen-powered detection of positive/negative momentum and acceleration trends.")

    data = _collect_market_momentum_data()
    if not data:
        st.info("No data available for market momentum analysis.")
        return

    analysis = _generate_market_momentum_analysis(data)

    themed_card_container()
    st.markdown(f"""
    ## Market Momentum Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Market momentum analysis complete.")
# ------------- CHUNK 63: MARKET NOISE FILTER -------------

def _collect_market_noise_data():
    """
    Collect data needed to detect noise vs signal:
    - today's edges
    - today's confidence values
    - historical edge variance
    - historical confidence variance
    - historical profit volatility
    - slate-level volatility and parlay exposure
    """
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    log = st.session_state.bet_log

    if not plays or not log:
        return None

    # Today's distributions
    today_edges = [p.get("edge", 0) for p in plays]
    today_conf = [p.get("true_confidence", 0) for p in plays]

    # Historical distributions
    hist_edges = [b.get("edge", 0) for b in log]
    hist_conf = [b.get("true_confidence", 0) for b in log]
    hist_profit = [b.get("profit", 0) for b in log]

    # Variance metrics
    edge_var_hist = float(np.var(hist_edges)) if hist_edges else 0
    conf_var_hist = float(np.var(hist_conf)) if hist_conf else 0
    profit_var_hist = float(np.var(hist_profit)) if hist_profit else 0

    risk = _compute_risk_metrics()

    return {
        "today_edges": today_edges,
        "today_confidence": today_conf,
        "historical_edge_variance": edge_var_hist,
        "historical_confidence_variance": conf_var_hist,
        "historical_profit_variance": profit_var_hist,
        "volatility": risk["volatility"],
        "parlay_risk": risk["parlay_risk"],
    }


def _qwen_noise_filter_prompt(data):
    """
    Build a structured prompt for Qwen to analyze noise vs signal.
    """
    prompt = f"""
You are an elite sports betting signal-processing analyst.

Analyze the following MARKET NOISE DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Identify which parts of today's slate are noise vs signal.
2. Detect misleading edges (variance-driven or unstable).
3. Detect false confidence (inflated or unreliable).
4. Highlight noise-driven risks across the slate.
5. Highlight signal-driven opportunities.
6. Provide 3–5 actionable noise-filtering recommendations.
7. Keep output under 240 words.
8. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_noise_filter_analysis(data):
    """
    Call Qwen to generate noise vs signal insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_noise_filter_prompt(data)
    response = _call_qwen(prompt)
    return response or "No noise-filter analysis generated."


def render_market_noise_filter():
    """
    Full UI for Qwen-powered noise vs signal detection.
    """
    st.header("Market Noise Filter")
    st.caption("Qwen-powered detection of noise vs signal across today's slate.")

    data = _collect_market_noise_data()
    if not data:
        st.info("No data available for noise filtering.")
        return

    analysis = _generate_noise_filter_analysis(data)

    themed_card_container()
    st.markdown(f"""
    ## Market Noise Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Market noise filtering complete.")
# ------------- CHUNK 64: MARKET INTEGRITY ENGINE -------------

def _collect_market_integrity_data():
    """
    Collect data needed to evaluate market integrity:
    - historical market performance variance
    - today's market distribution
    - edge stability
    - confidence stability
    - volatility and parlay exposure
    - structural consistency indicators
    """
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    log = st.session_state.bet_log

    if not plays or not log:
        return None

    # Historical market performance
    market_perf = {}
    for b in log:
        market = b.get("market", "Unknown")
        profit = b.get("profit", 0)
        market_perf.setdefault(market, []).append(profit)

    # Compute variance per market (integrity indicator)
    market_variances = {
        m: float(np.var(v)) if len(v) > 1 else 0
        for m, v in market_perf.items()
    }

    # Today's market distribution
    today_markets = {}
    for p in plays:
        m = p.get("market", "Unknown")
        today_markets[m] = today_markets.get(m, 0) + 1

    # Edge and confidence stability
    today_edges = [p.get("edge", 0) for p in plays]
    today_conf = [p.get("true_confidence", 0) for p in plays]

    edge_var = float(np.var(today_edges)) if today_edges else 0
    conf_var = float(np.var(today_conf)) if today_conf else 0

    risk = _compute_risk_metrics()

    return {
        "market_variances": market_variances,
        "today_market_distribution": today_markets,
        "edge_variance": edge_var,
        "confidence_variance": conf_var,
        "volatility": risk["volatility"],
        "parlay_risk": risk["parlay_risk"],
    }


def _qwen_market_integrity_prompt(data):
    """
    Build a structured prompt for Qwen to analyze market integrity.
    """
    prompt = f"""
You are an elite sports betting macro-market reliability analyst.

Analyze the following MARKET INTEGRITY DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Identify which markets have high integrity (reliable, consistent).
2. Identify which markets have low integrity (unreliable, unstable).
3. Detect inconsistent edges and confidence patterns.
4. Highlight structural instability across the slate.
5. Provide 3–5 actionable integrity-based strategy recommendations.
6. Keep output under 240 words.
7. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_integrity_analysis(data):
    """
    Call Qwen to generate integrity insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_market_integrity_prompt(data)
    response = _call_qwen(prompt)
    return response or "No market integrity analysis generated."


def render_market_integrity_engine():
    """
    Full UI for Qwen-powered market integrity scoring.
    """
    st.header("Market Integrity Engine")
    st.caption("Qwen-powered scoring of market reliability and structural stability.")

    data = _collect_market_integrity_data()
    if not data:
        st.info("No data available for market integrity analysis.")
        return

    analysis = _generate_market_integrity_analysis(data)

    themed_card_container()
    st.markdown(f"""
    ## Market Integrity Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Market integrity analysis complete.")
# ------------- CHUNK 65: MARKET RELIABILITY ENGINE -------------

def _collect_market_reliability_data():
    """
    Collect data needed to forecast market reliability:
    - historical market variance trend
    - rolling variance windows
    - today's market distribution
    - edge stability trend
    - confidence stability trend
    - volatility and parlay exposure
    """
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    log = st.session_state.bet_log

    if not plays or not log:
        return None

    # Historical market performance
    market_perf = {}
    for b in log:
        market = b.get("market", "Unknown")
        profit = b.get("profit", 0)
        market_perf.setdefault(market, []).append(profit)

    # Rolling variance trend per market
    def rolling_var(arr, window=5):
        if len(arr) < window:
            return []
        return [float(np.var(arr[i:i+window])) for i in range(len(arr) - window + 1)]

    market_variance_trends = {
        m: rolling_var(v, window=5)
        for m, v in market_perf.items()
    }

    # Today's market distribution
    today_markets = {}
    for p in plays:
        m = p.get("market", "Unknown")
        today_markets[m] = today_markets.get(m, 0) + 1

    # Edge and confidence stability trends
    hist_edges = [b.get("edge", 0) for b in log]
    hist_conf = [b.get("true_confidence", 0) for b in log]

    edge_var_trend = rolling_var(hist_edges, window=5)
    conf_var_trend = rolling_var(hist_conf, window=5)

    risk = _compute_risk_metrics()

    return {
        "market_variance_trends": market_variance_trends,
        "today_market_distribution": today_markets,
        "edge_variance_trend": edge_var_trend,
        "confidence_variance_trend": conf_var_trend,
        "volatility": risk["volatility"],
        "parlay_risk": risk["parlay_risk"],
    }


def _qwen_market_reliability_prompt(data):
    """
    Build a structured prompt for Qwen to analyze reliability forecasting.
    """
    prompt = f"""
You are an elite sports betting macro-market reliability forecaster.

Analyze the following MARKET RELIABILITY DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Forecast which markets are becoming more reliable.
2. Forecast which markets are experiencing reliability decay.
3. Identify strengthening vs weakening edge stability.
4. Identify strengthening vs weakening confidence stability.
5. Highlight forward-looking reliability risks and opportunities.
6. Provide 3–5 reliability-based strategy recommendations.
7. Keep output under 240 words.
8. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_reliability_analysis(data):
    """
    Call Qwen to generate reliability forecasting insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_market_reliability_prompt(data)
    response = _call_qwen(prompt)
    return response or "No market reliability analysis generated."


def render_market_reliability_engine():
    """
    Full UI for Qwen-powered reliability forecasting.
    """
    st.header("Market Reliability Engine")
    st.caption("Qwen-powered forecasting of future market reliability and decay.")

    data = _collect_market_reliability_data()
    if not data:
        st.info("No data available for market reliability forecasting.")
        return

    analysis = _generate_market_reliability_analysis(data)

    themed_card_container()
    st.markdown(f"""
    ## Market Reliability Forecast

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Market reliability forecasting complete.")
# ------------- CHUNK 66: MARKET STRESS-TEST ENGINE -------------

def _collect_market_stress_test_data():
    """
    Collect data needed for multi-scenario stress testing:
    - today's plays
    - odds sensitivity
    - volatility sensitivity
    - confidence drift sensitivity
    - edge compression sensitivity
    - historical volatility patterns
    - parlay amplification risk
    """
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    log = st.session_state.bet_log

    if not plays:
        return None

    # Historical volatility patterns
    hist_profit = [b.get("profit", 0) for b in log] if log else []
    hist_volatility = float(np.var(hist_profit)) if hist_profit else 0

    risk = _compute_risk_metrics()

    stress_dataset = []

    for p in plays:
        odds = p.get("odds")
        true_prob = p.get("true_confidence", 0)
        edge = p.get("edge", 0)

        # Compute implied probability
        if odds is not None:
            if odds > 0:
                implied_prob = 100 / (odds + 100)
            else:
                implied_prob = abs(odds) / (abs(odds) + 100)
        else:
            implied_prob = None

        stress_dataset.append({
            "selection": p["selection"],
            "market": p.get("market", "Unknown"),
            "odds": odds,
            "implied_prob": implied_prob,
            "true_prob": true_prob / 100,
            "edge": edge,
            "volatility": risk["volatility"],
            "parlay_risk": risk["parlay_risk"],
            "historical_volatility": hist_volatility,
        })

    return stress_dataset


def _qwen_stress_test_prompt(data):
    """
    Build a structured prompt for Qwen to run multi-scenario stress simulations.
    """
    prompt = f"""
You are an elite sports betting macro-risk simulation analyst.

Run MULTI-SCENARIO STRESS TESTING using the following data:

{json.dumps(data, indent=2)}

SCENARIOS TO SIMULATE:
1. Odds worsen by 10–20%.
2. Odds improve by 10–20%.
3. Volatility spikes sharply.
4. Confidence drifts downward.
5. Edge compresses across the slate.
6. Parlay amplification increases systemic risk.

TASKS:
1. Identify which plays and markets are most scenario-sensitive.
2. Identify which plays and markets are most scenario-robust.
3. Highlight systemic risks across scenarios.
4. Highlight scenario-driven opportunities.
5. Provide 3–5 actionable stress-test strategy recommendations.
6. Keep output under 260 words.
7. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_stress_test_analysis(data):
    """
    Call Qwen to generate multi-scenario stress-test insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_stress_test_prompt(data)
    response = _call_qwen(prompt)
    return response or "No stress-test analysis generated."


def render_market_stress_test_engine():
    """
    Full UI for Qwen-powered multi-scenario stress testing.
    """
    st.header("Market Stress-Test Engine")
    st.caption("Qwen-powered multi-scenario stress simulation and fragility detection.")

    data = _collect_market_stress_test_data()
    if not data:
        st.info("No data available for stress testing.")
        return

    analysis = _generate_market_stress_test_analysis(data)

    themed_card_container()
    st.markdown(f"""
    ## Market Stress-Test Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Market stress testing complete.")
# ------------- CHUNK 67: MARKET SHOCK ENGINE -------------

def _collect_market_shock_data():
    """
    Collect data needed for shock-event simulation:
    - today's plays
    - implied probability vs true probability gaps
    - edge fragility indicators
    - confidence fragility indicators
    - volatility exposure
    - parlay amplification exposure
    - historical shock sensitivity (profit tail variance)
    """
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    log = st.session_state.bet_log

    if not plays:
        return None

    # Historical tail variance (shock sensitivity indicator)
    hist_profit = [b.get("profit", 0) for b in log] if log else []
    tail_variance = float(np.var(hist_profit[-10:])) if len(hist_profit) >= 10 else 0

    risk = _compute_risk_metrics()

    shock_dataset = []

    for p in plays:
        odds = p.get("odds")
        true_prob = p.get("true_confidence", 0)
        edge = p.get("edge", 0)

        # Compute implied probability
        if odds is not None:
            if odds > 0:
                implied_prob = 100 / (odds + 100)
            else:
                implied_prob = abs(odds) / (abs(odds) + 100)
        else:
            implied_prob = None

        shock_dataset.append({
            "selection": p["selection"],
            "market": p.get("market", "Unknown"),
            "odds": odds,
            "implied_prob": implied_prob,
            "true_prob": true_prob / 100,
            "edge": edge,
            "volatility": risk["volatility"],
            "parlay_risk": risk["parlay_risk"],
            "tail_variance": tail_variance,
        })

    return shock_dataset


def _qwen_shock_prompt(data):
    """
    Build a structured prompt for Qwen to simulate shock events.
    """
    prompt = f"""
You are an elite sports betting macro-risk shock-event analyst.

Simulate SHOCK EVENTS using the following data:

{json.dumps(data, indent=2)}

SHOCK SCENARIOS TO SIMULATE:
1. Sudden odds collapse (sharp movement against the user).
2. Sudden odds spike (sharp movement in user's favor).
3. Market-wide volatility explosion.
4. Confidence collapse (sharp drop in true probability).
5. Edge inversion (edges flip negative).
6. Parlay shock amplification.

TASKS:
1. Identify shock-fragile plays and markets.
2. Identify shock-resilient plays and markets.
3. Highlight systemic shock risks.
4. Highlight shock-driven opportunities.
5. Provide 3–5 actionable shock-event strategy recommendations.
6. Keep output under 260 words.
7. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_shock_analysis(data):
    """
    Call Qwen to generate shock-event insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_shock_prompt(data)
    response = _call_qwen(prompt)
    return response or "No shock-event analysis generated."


def render_market_shock_engine():
    """
    Full UI for Qwen-powered shock-event simulation.
    """
    st.header("Market Shock Engine")
    st.caption("Qwen-powered simulation of sudden market shocks and fragility detection.")

    data = _collect_market_shock_data()
    if not data:
        st.info("No data available for shock-event simulation.")
        return

    analysis = _generate_market_shock_analysis(data)

    themed_card_container()
    st.markdown(f"""
    ## Market Shock Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Market shock simulation complete.")
# ------------- CHUNK 68: MARKET CASCADE ENGINE -------------

def _collect_market_cascade_data():
    """
    Collect data needed for cascade failure detection:
    - correlations between markets (from historical performance)
    - correlations between teams
    - odds-range correlations
    - confidence and edge correlations
    - volatility exposure
    - parlay amplification exposure
    - tail-risk indicators
    """
    log = st.session_state.bet_log
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    if not log or not plays:
        return None

    # Historical profit by market
    market_profits = {}
    team_profits = {}

    for b in log:
        profit = b.get("profit", 0)
        market = b.get("market", "Unknown")
        team = b.get("team") or (b.get("selection", "").split(" ")[0])

        market_profits.setdefault(market, []).append(profit)
        team_profits.setdefault(team, []).append(profit)

    # Compute simple correlation proxies (variance as instability indicator)
    market_variances = {
        m: float(np.var(v)) if len(v) > 1 else 0
        for m, v in market_profits.items()
    }

    team_variances = {
        t: float(np.var(v)) if len(v) > 1 else 0
        for t, v in team_profits.items()
    }

    # Tail-risk indicator (last 10 bets)
    hist_profit = [b.get("profit", 0) for b in log]
    tail_variance = float(np.var(hist_profit[-10:])) if len(hist_profit) >= 10 else 0

    risk = _compute_risk_metrics()

    return {
        "market_variances": market_variances,
        "team_variances": team_variances,
        "tail_variance": tail_variance,
        "volatility": risk["volatility"],
        "parlay_risk": risk["parlay_risk"],
        "num_plays": len(plays),
    }


def _qwen_cascade_prompt(data):
    """
    Build a structured prompt for Qwen to analyze cascade failure risk.
    """
    prompt = f"""
You are an elite sports betting macro-systemic risk analyst.

Analyze the following MARKET CASCADE DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Identify markets with high domino-risk (cascade fragility).
2. Identify markets with low domino-risk (cascade resilience).
3. Detect potential cascade chains (if X fails, Y likely fails).
4. Highlight systemic cascade risks (market-wide chain reactions).
5. Highlight cascade-driven opportunities (markets that hedge others).
6. Provide 3–5 actionable cascade-risk strategy recommendations.
7. Keep output under 260 words.
8. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_cascade_analysis(data):
    """
    Call Qwen to generate cascade failure insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_cascade_prompt(data)
    response = _call_qwen(prompt)
    return response or "No cascade analysis generated."


def render_market_cascade_engine():
    """
    Full UI for Qwen-powered cascade failure detection.
    """
    st.header("Market Cascade Engine")
    st.caption("Qwen-powered detection of cascading failure chains and domino-risk markets.")

    data = _collect_market_cascade_data()
    if not data:
        st.info("No data available for cascade analysis.")
        return

    analysis = _generate_market_cascade_analysis(data)

    themed_card_container()
    st.markdown(f"""
    ## Market Cascade Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Market cascade analysis complete.")
# ------------- CHUNK 69: MARKET FRAGILITY ENGINE -------------

def _collect_market_fragility_data():
    """
    Collect data needed to score market fragility:
    - historical variance per market
    - historical variance per team
    - edge instability indicators
    - confidence instability indicators
    - volatility exposure
    - parlay amplification exposure
    - tail-risk indicators (shock fragility)
    """
    log = st.session_state.bet_log
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    if not log or not plays:
        return None

    # Historical profit by market and team
    market_perf = {}
    team_perf = {}

    for b in log:
        profit = b.get("profit", 0)
        market = b.get("market", "Unknown")
        team = b.get("team") or (b.get("selection", "").split(" ")[0])

        market_perf.setdefault(market, []).append(profit)
        team_perf.setdefault(team, []).append(profit)

    # Variance = fragility indicator
    market_fragility_scores = {
        m: float(np.var(v)) if len(v) > 1 else 0
        for m, v in market_perf.items()
    }

    team_fragility_scores = {
        t: float(np.var(v)) if len(v) > 1 else 0
        for t, v in team_perf.items()
    }

    # Edge & confidence instability (today)
    today_edges = [p.get("edge", 0) for p in plays]
    today_conf = [p.get("true_confidence", 0) for p in plays]

    edge_instability = float(np.var(today_edges)) if today_edges else 0
    conf_instability = float(np.var(today_conf)) if today_conf else 0

    # Tail-risk indicator (last 10 bets)
    hist_profit = [b.get("profit", 0) for b in log]
    tail_risk = float(np.var(hist_profit[-10:])) if len(hist_profit) >= 10 else 0

    risk = _compute_risk_metrics()

    return {
        "market_fragility_scores": market_fragility_scores,
        "team_fragility_scores": team_fragility_scores,
        "edge_instability": edge_instability,
        "confidence_instability": conf_instability,
        "tail_risk": tail_risk,
        "volatility": risk["volatility"],
        "parlay_risk": risk["parlay_risk"],
    }


def _qwen_fragility_prompt(data):
    """
    Build a structured prompt for Qwen to analyze fragility.
    """
    prompt = f"""
You are an elite sports betting macro-structural risk analyst.

Analyze the following MARKET FRAGILITY DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Identify the most fragile markets (high structural instability).
2. Identify the most resilient markets (low fragility).
3. Detect fragility drivers:
   - variance
   - edge instability
   - confidence instability
   - tail-risk exposure
4. Highlight fragility-driven risks across the slate.
5. Highlight fragility-driven opportunities (markets to trust).
6. Provide 3–5 actionable fragility-based strategy recommendations.
7. Keep output under 260 words.
8. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_fragility_analysis(data):
    """
    Call Qwen to generate fragility insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_fragility_prompt(data)
    response = _call_qwen(prompt)
    return response or "No fragility analysis generated."


def render_market_fragility_engine():
    """
    Full UI for Qwen-powered fragility scoring.
    """
    st.header("Market Fragility Engine")
    st.caption("Qwen-powered scoring of structural fragility across markets and teams.")

    data = _collect_market_fragility_data()
    if not data:
        st.info("No data available for fragility analysis.")
        return

    analysis = _generate_market_fragility_analysis(data)

    themed_card_container()
    st.markdown(f"""
    ## Market Fragility Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Market fragility scoring complete.")
# ------------- CHUNK 70: MARKET STABILITY FORECAST ENGINE -------------

def _collect_market_stability_forecast_data():
    """
    Collect data needed to forecast future market stability:
    - historical variance per market
    - rolling variance trends
    - today's market distribution
    - edge stability trends
    - confidence stability trends
    - volatility exposure
    - parlay amplification exposure
    - structural stability indicators
    """
    log = st.session_state.bet_log
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    if not log or not plays:
        return None

    # Historical market performance
    market_perf = {}
    for b in log:
        market = b.get("market", "Unknown")
        profit = b.get("profit", 0)
        market_perf.setdefault(market, []).append(profit)

    # Rolling variance trend per market
    def rolling_var(arr, window=5):
        if len(arr) < window:
            return []
        return [float(np.var(arr[i:i+window])) for i in range(len(arr) - window + 1)]

    market_stability_trends = {
        m: rolling_var(v, window=5)
        for m, v in market_perf.items()
    }

    # Today's market distribution
    today_markets = {}
    for p in plays:
        m = p.get("market", "Unknown")
        today_markets[m] = today_markets.get(m, 0) + 1

    # Edge & confidence stability trends
    hist_edges = [b.get("edge", 0) for b in log]
    hist_conf = [b.get("true_confidence", 0) for b in log]

    edge_stability_trend = rolling_var(hist_edges, window=5)
    conf_stability_trend = rolling_var(hist_conf, window=5)

    risk = _compute_risk_metrics()

    return {
        "market_stability_trends": market_stability_trends,
        "today_market_distribution": today_markets,
        "edge_stability_trend": edge_stability_trend,
        "confidence_stability_trend": conf_stability_trend,
        "volatility": risk["volatility"],
        "parlay_risk": risk["parlay_risk"],
    }


def _qwen_stability_forecast_prompt(data):
    """
    Build a structured prompt for Qwen to forecast future stability.
    """
    prompt = f"""
You are an elite sports betting macro-market stability forecaster.

Analyze the following MARKET STABILITY FORECAST DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Forecast which markets are becoming more stable.
2. Forecast which markets are entering stability decay.
3. Identify strengthening vs weakening edge stability.
4. Identify strengthening vs weakening confidence stability.
5. Highlight forward-looking stability risks and opportunities.
6. Provide 3–5 actionable stability-based strategy recommendations.
7. Keep output under 260 words.
8. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_stability_forecast(data):
    """
    Call Qwen to generate future stability insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_stability_forecast_prompt(data)
    response = _call_qwen(prompt)
    return response or "No stability forecast generated."


def render_market_stability_forecast_engine():
    """
    Full UI for Qwen-powered future stability projection.
    """
    st.header("Market Stability Forecast Engine")
    st.caption("Qwen-powered projection of future market stability and decay.")

    data = _collect_market_stability_forecast_data()
    if not data:
        st.info("No data available for stability forecasting.")
        return

    analysis = _generate_market_stability_forecast(data)

    themed_card_container()
    st.markdown(f"""
    ## Market Stability Forecast

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Market stability forecasting complete.")
# ------------- CHUNK 71: MARKET VOLATILITY FORECAST ENGINE -------------

def _collect_market_volatility_forecast_data():
    """
    Collect data needed to forecast future volatility:
    - historical profit variance
    - rolling volatility trend
    - market-level variance trends
    - edge volatility trend
    - confidence volatility trend
    - today's slate volatility exposure
    - parlay amplification exposure
    """
    log = st.session_state.bet_log
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    if not log or not plays:
        return None

    # Historical profit volatility
    hist_profit = [b.get("profit", 0) for b in log]

    def rolling_var(arr, window=5):
        if len(arr) < window:
            return []
        return [float(np.var(arr[i:i+window])) for i in range(len(arr) - window + 1)]

    volatility_trend = rolling_var(hist_profit, window=5)

    # Market-level volatility trends
    market_perf = {}
    for b in log:
        market = b.get("market", "Unknown")
        profit = b.get("profit", 0)
        market_perf.setdefault(market, []).append(profit)

    market_volatility_trends = {
        m: rolling_var(v, window=5)
        for m, v in market_perf.items()
    }

    # Edge & confidence volatility trends
    hist_edges = [b.get("edge", 0) for b in log]
    hist_conf = [b.get("true_confidence", 0) for b in log]

    edge_volatility_trend = rolling_var(hist_edges, window=5)
    conf_volatility_trend = rolling_var(hist_conf, window=5)

    risk = _compute_risk_metrics()

    return {
        "volatility_trend": volatility_trend,
        "market_volatility_trends": market_volatility_trends,
        "edge_volatility_trend": edge_volatility_trend,
        "confidence_volatility_trend": conf_volatility_trend,
        "today_volatility": risk["volatility"],
        "parlay_risk": risk["parlay_risk"],
    }


def _qwen_volatility_forecast_prompt(data):
    """
    Build a structured prompt for Qwen to forecast future volatility.
    """
    prompt = f"""
You are an elite sports betting macro-volatility forecaster.

Analyze the following MARKET VOLATILITY FORECAST DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Forecast future volatility direction (spike, decay, or stable).
2. Identify markets most sensitive to future volatility.
3. Identify markets most resilient to future volatility.
4. Detect strengthening vs weakening volatility trends in:
   - profit
   - edges
   - confidence
   - markets
5. Highlight forward-looking volatility risks and opportunities.
6. Provide 3–5 actionable volatility-based strategy recommendations.
7. Keep output under 260 words.
8. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_volatility_forecast(data):
    """
    Call Qwen to generate future volatility insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_volatility_forecast_prompt(data)
    response = _call_qwen(prompt)
    return response or "No volatility forecast generated."


def render_market_volatility_forecast_engine():
    """
    Full UI for Qwen-powered future volatility projection.
    """
    st.header("Market Volatility Forecast Engine")
    st.caption("Qwen-powered projection of future volatility spikes and decay.")

    data = _collect_market_volatility_forecast_data()
    if not data:
        st.info("No data available for volatility forecasting.")
        return

    analysis = _generate_market_volatility_forecast(data)

    themed_card_container()
    st.markdown(f"""
    ## Market Volatility Forecast

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Market volatility forecasting complete.")
# ------------- CHUNK 72: MARKET COMPRESSION ENGINE -------------

def _collect_market_compression_data():
    """
    Collect data needed to detect compression:
    - edge compression (tight clustering of edges)
    - confidence compression (tight clustering of confidence)
    - market-level compression (variance collapse)
    - historical compression trends
    - volatility exposure
    - parlay amplification exposure
    """
    log = st.session_state.bet_log
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    if not log or not plays:
        return None

    # Today's distributions
    today_edges = [p.get("edge", 0) for p in plays]
    today_conf = [p.get("true_confidence", 0) for p in plays]

    edge_compression = float(np.var(today_edges)) if today_edges else 0
    conf_compression = float(np.var(today_conf)) if today_conf else 0

    # Historical compression trends
    hist_edges = [b.get("edge", 0) for b in log]
    hist_conf = [b.get("true_confidence", 0) for b in log]

    def rolling_var(arr, window=5):
        if len(arr) < window:
            return []
        return [float(np.var(arr[i:i+window])) for i in range(len(arr) - window + 1)]

    edge_compression_trend = rolling_var(hist_edges, window=5)
    conf_compression_trend = rolling_var(hist_conf, window=5)

    # Market-level compression (variance collapse)
    market_perf = {}
    for b in log:
        m = b.get("market", "Unknown")
        profit = b.get("profit", 0)
        market_perf.setdefault(m, []).append(profit)

    market_compression_scores = {
        m: float(np.var(v)) if len(v) > 1 else 0
        for m, v in market_perf.items()
    }

    risk = _compute_risk_metrics()

    return {
        "edge_compression": edge_compression,
        "confidence_compression": conf_compression,
        "edge_compression_trend": edge_compression_trend,
        "confidence_compression_trend": conf_compression_trend,
        "market_compression_scores": market_compression_scores,
        "volatility": risk["volatility"],
        "parlay_risk": risk["parlay_risk"],
    }


def _qwen_compression_prompt(data):
    """
    Build a structured prompt for Qwen to analyze compression.
    """
    prompt = f"""
You are an elite sports betting macro-signal compression analyst.

Analyze the following MARKET COMPRESSION DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Identify edge compression (tight clustering of edges).
2. Identify confidence compression (tight clustering of confidence).
3. Identify market-level compression (variance collapse).
4. Highlight compression-driven risks (signal collapse, false edges).
5. Highlight compression-driven opportunities (markets resisting compression).
6. Provide 3–5 actionable compression-based strategy recommendations.
7. Keep output under 260 words.
8. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_compression_analysis(data):
    """
    Call Qwen to generate compression insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_compression_prompt(data)
    response = _call_qwen(prompt)
    return response or "No compression analysis generated."


def render_market_compression_engine():
    """
    Full UI for Qwen-powered compression detection.
    """
    st.header("Market Compression Engine")
    st.caption("Qwen-powered detection of edge, confidence, and market-level compression.")

    data = _collect_market_compression_data()
    if not data:
        st.info("No data available for compression analysis.")
        return

    analysis = _generate_market_compression_analysis(data)

    themed_card_container()
    st.markdown(f"""
    ## Market Compression Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Market compression analysis complete.")
# ------------- CHUNK 73: MARKET EXPANSION ENGINE -------------

def _collect_market_expansion_data():
    """
    Collect data needed to detect expansion:
    - edge expansion (edges spreading wider)
    - confidence expansion (confidence spreading wider)
    - market-level expansion (variance widening)
    - historical expansion trends
    - volatility exposure
    - parlay amplification exposure
    """
    log = st.session_state.bet_log
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    if not log or not plays:
        return None

    # Today's distributions
    today_edges = [p.get("edge", 0) for p in plays]
    today_conf = [p.get("true_confidence", 0) for p in plays]

    edge_expansion = float(np.var(today_edges)) if today_edges else 0
    conf_expansion = float(np.var(today_conf)) if today_conf else 0

    # Historical expansion trends
    hist_edges = [b.get("edge", 0) for b in log]
    hist_conf = [b.get("true_confidence", 0) for b in log]

    def rolling_var(arr, window=5):
        if len(arr) < window:
            return []
        return [float(np.var(arr[i:i+window])) for i in range(len(arr) - window + 1)]

    edge_expansion_trend = rolling_var(hist_edges, window=5)
    conf_expansion_trend = rolling_var(hist_conf, window=5)

    # Market-level expansion (variance widening)
    market_perf = {}
    for b in log:
        m = b.get("market", "Unknown")
        profit = b.get("profit", 0)
        market_perf.setdefault(m, []).append(profit)

    market_expansion_scores = {
        m: float(np.var(v)) if len(v) > 1 else 0
        for m, v in market_perf.items()
    }

    risk = _compute_risk_metrics()

    return {
        "edge_expansion": edge_expansion,
        "confidence_expansion": conf_expansion,
        "edge_expansion_trend": edge_expansion_trend,
        "confidence_expansion_trend": conf_expansion_trend,
        "market_expansion_scores": market_expansion_scores,
        "volatility": risk["volatility"],
        "parlay_risk": risk["parlay_risk"],
    }


def _qwen_expansion_prompt(data):
    """
    Build a structured prompt for Qwen to analyze expansion.
    """
    prompt = f"""
You are an elite sports betting macro-signal expansion analyst.

Analyze the following MARKET EXPANSION DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Identify edge expansion (edges widening).
2. Identify confidence expansion (confidence widening).
3. Identify market-level expansion (variance widening).
4. Highlight expansion-driven opportunities (new edges forming).
5. Highlight expansion-driven risks (false expansion, unstable widening).
6. Provide 3–5 actionable expansion-based strategy recommendations.
7. Keep output under 260 words.
8. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_expansion_analysis(data):
    """
    Call Qwen to generate expansion insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_expansion_prompt(data)
    response = _call_qwen(prompt)
    return response or "No expansion analysis generated."


def render_market_expansion_engine():
    """
    Full UI for Qwen-powered expansion detection.
    """
    st.header("Market Expansion Engine")
    st.caption("Qwen-powered detection of edge, confidence, and market-level expansion.")

    data = _collect_market_expansion_data()
    if not data:
        st.info("No data available for expansion analysis.")
        return

    analysis = _generate_market_expansion_analysis(data)

    themed_card_container()
    st.markdown(f"""
    ## Market Expansion Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Market expansion analysis complete.")
# ------------- CHUNK 74: MARKET DIVERGENCE ENGINE -------------

def _collect_market_divergence_data():
    """
    Collect data needed to detect divergence:
    - implied probability vs true probability gaps
    - edge vs confidence divergence
    - market-level divergence (variance mismatch)
    - historical divergence trends
    - volatility exposure
    - parlay amplification exposure
    """
    log = st.session_state.bet_log
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    if not plays:
        return None

    # Today's divergence metrics
    divergence_dataset = []

    for p in plays:
        odds = p.get("odds")
        true_prob = p.get("true_confidence", 0)
        edge = p.get("edge", 0)

        # Compute implied probability
        if odds is not None:
            if odds > 0:
                implied_prob = 100 / (odds + 100)
            else:
                implied_prob = abs(odds) / (abs(odds) + 100)
        else:
            implied_prob = None

        divergence_dataset.append({
            "selection": p["selection"],
            "market": p.get("market", "Unknown"),
            "odds": odds,
            "implied_prob": implied_prob,
            "true_prob": true_prob / 100,
            "edge": edge,
            "confidence": true_prob,
        })

    # Historical divergence trends
    if log:
        hist_edges = [b.get("edge", 0) for b in log]
        hist_conf = [b.get("true_confidence", 0) for b in log]

        def rolling_diff(arr1, arr2, window=5):
            if len(arr1) < window or len(arr2) < window:
                return []
            diffs = []
            for i in range(len(arr1) - window + 1):
                seg1 = arr1[i:i+window]
                seg2 = arr2[i:i+window]
                diffs.append(float(np.mean([abs(a - b) for a, b in zip(seg1, seg2)])))
            return diffs

        divergence_trend = rolling_diff(hist_edges, hist_conf, window=5)
    else:
        divergence_trend = []

    risk = _compute_risk_metrics()

    return {
        "divergence_dataset": divergence_dataset,
        "divergence_trend": divergence_trend,
        "volatility": risk["volatility"],
        "parlay_risk": risk["parlay_risk"],
    }


def _qwen_divergence_prompt(data):
    """
    Build a structured prompt for Qwen to analyze divergence.
    """
    prompt = f"""
You are an elite sports betting macro-signal divergence analyst.

Analyze the following MARKET DIVERGENCE DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Identify implied-vs-true probability divergence.
2. Identify edge-vs-confidence divergence.
3. Identify market-level divergence (variance mismatch).
4. Highlight divergence-driven risks (false edges, unstable signals).
5. Highlight divergence-driven opportunities (mispriced markets).
6. Provide 3–5 actionable divergence-based strategy recommendations.
7. Keep output under 260 words.
8. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_divergence_analysis(data):
    """
    Call Qwen to generate divergence insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_divergence_prompt(data)
    response = _call_qwen(prompt)
    return response or "No divergence analysis generated."


def render_market_divergence_engine():
    """
    Full UI for Qwen-powered divergence detection.
    """
    st.header("Market Divergence Engine")
    st.caption("Qwen-powered detection of implied-vs-true probability and edge-vs-confidence divergence.")

    data = _collect_market_divergence_data()
    if not data:
        st.info("No data available for divergence analysis.")
        return

    analysis = _generate_market_divergence_analysis(data)

    themed_card_container()
    st.markdown(f"""
    ## Market Divergence Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Market divergence analysis complete.")
# ------------- CHUNK 75: MARKET CONVERGENCE ENGINE -------------

def _collect_market_convergence_data():
    """
    Collect data needed to detect convergence:
    - implied probability vs true probability alignment
    - edge vs confidence alignment
    - market-level convergence (variance tightening)
    - historical convergence trends
    - volatility exposure
    - parlay amplification exposure
    """
    log = st.session_state.bet_log
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    if not plays:
        return None

    convergence_dataset = []

    for p in plays:
        odds = p.get("odds")
        true_prob = p.get("true_confidence", 0)
        edge = p.get("edge", 0)

        # Compute implied probability
        if odds is not None:
            if odds > 0:
                implied_prob = 100 / (odds + 100)
            else:
                implied_prob = abs(odds) / (abs(odds) + 100)
        else:
            implied_prob = None

        convergence_dataset.append({
            "selection": p["selection"],
            "market": p.get("market", "Unknown"),
            "odds": odds,
            "implied_prob": implied_prob,
            "true_prob": true_prob / 100,
            "edge": edge,
            "confidence": true_prob,
        })

    # Historical convergence trends
    if log:
        hist_edges = [b.get("edge", 0) for b in log]
        hist_conf = [b.get("true_confidence", 0) for b in log]

        def rolling_alignment(arr1, arr2, window=5):
            if len(arr1) < window or len(arr2) < window:
                return []
            aligns = []
            for i in range(len(arr1) - window + 1):
                seg1 = arr1[i:i+window]
                seg2 = arr2[i:i+window]
                aligns.append(float(np.mean([1 - abs(a - b) for a, b in zip(seg1, seg2)])))
            return aligns

        convergence_trend = rolling_alignment(hist_edges, hist_conf, window=5)
    else:
        convergence_trend = []

    risk = _compute_risk_metrics()

    return {
        "convergence_dataset": convergence_dataset,
        "convergence_trend": convergence_trend,
        "volatility": risk["volatility"],
        "parlay_risk": risk["parlay_risk"],
    }


def _qwen_convergence_prompt(data):
    """
    Build a structured prompt for Qwen to analyze convergence.
    """
    prompt = f"""
You are an elite sports betting macro-signal convergence analyst.

Analyze the following MARKET CONVERGENCE DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Identify implied-vs-true probability convergence.
2. Identify edge-vs-confidence convergence.
3. Identify market-level convergence (variance tightening).
4. Highlight convergence-driven opportunities (markets aligning with model).
5. Highlight convergence-driven risks (false convergence, unstable alignment).
6. Provide 3–5 actionable convergence-based strategy recommendations.
7. Keep output under 260 words.
8. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_convergence_analysis(data):
    """
    Call Qwen to generate convergence insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_convergence_prompt(data)
    response = _call_qwen(prompt)
    return response or "No convergence analysis generated."


def render_market_convergence_engine():
    """
    Full UI for Qwen-powered convergence detection.
    """
    st.header("Market Convergence Engine")
    st.caption("Qwen-powered detection of implied-vs-true probability and edge-vs-confidence convergence.")

    data = _collect_market_convergence_data()
    if not data:
        st.info("No data available for convergence analysis.")
        return

    analysis = _generate_market_convergence_analysis(data)

    themed_card_container()
    st.markdown(f"""
    ## Market Convergence Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Market convergence analysis complete.")
# ------------- CHUNK 76: MARKET SYNCHRONIZATION ENGINE -------------

def _collect_market_synchronization_data():
    """
    Collect data needed to detect cross-market synchronization:
    - synchronized edge movement
    - synchronized confidence movement
    - synchronized volatility patterns
    - historical cross-market correlations
    - market-level alignment indicators
    - parlay amplification exposure
    """
    log = st.session_state.bet_log
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    if not log or not plays:
        return None

    # Historical profit by market
    market_perf = {}
    for b in log:
        market = b.get("market", "Unknown")
        profit = b.get("profit", 0)
        market_perf.setdefault(market, []).append(profit)

    # Compute simple correlation proxies (variance similarity)
    market_sync_scores = {}
    markets = list(market_perf.keys())

    for i in range(len(markets)):
        for j in range(i + 1, len(markets)):
            m1, m2 = markets[i], markets[j]
            v1, v2 = market_perf[m1], market_perf[m2]

            # Use variance similarity as a proxy for synchronization
            if len(v1) > 1 and len(v2) > 1:
                diff = abs(np.var(v1) - np.var(v2))
                sync_score = 1 / (1 + diff)  # smaller diff = higher sync
            else:
                sync_score = 0

            market_sync_scores[f"{m1}__{m2}"] = float(sync_score)

    # Today's synchronized movement indicators
    today_edges = [p.get("edge", 0) for p in plays]
    today_conf = [p.get("true_confidence", 0) for p in plays]

    edge_sync = float(np.var(today_edges)) if today_edges else 0
    conf_sync = float(np.var(today_conf)) if today_conf else 0

    risk = _compute_risk_metrics()

    return {
        "market_sync_scores": market_sync_scores,
        "edge_sync": edge_sync,
        "confidence_sync": conf_sync,
        "volatility": risk["volatility"],
        "parlay_risk": risk["parlay_risk"],
    }


def _qwen_synchronization_prompt(data):
    """
    Build a structured prompt for Qwen to analyze cross-market synchronization.
    """
    prompt = f"""
You are an elite sports betting macro-synchronization analyst.

Analyze the following MARKET SYNCHRONIZATION DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Identify synchronized markets (moving together).
2. Identify desynchronized markets (moving independently).
3. Detect synchronized volatility, edges, and confidence.
4. Highlight synchronization-driven risks (systemic alignment, correlated losses).
5. Highlight synchronization-driven opportunities (aligned edges, correlated wins).
6. Provide 3–5 actionable synchronization-based strategy recommendations.
7. Keep output under 260 words.
8. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_synchronization_analysis(data):
    """
    Call Qwen to generate synchronization insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_synchronization_prompt(data)
    response = _call_qwen(prompt)
    return response or "No synchronization analysis generated."


def render_market_synchronization_engine():
    """
    Full UI for Qwen-powered cross-market synchronization detection.
    """
    st.header("Market Synchronization Engine")
    st.caption("Qwen-powered detection of synchronized market behavior and cross-market alignment.")

    data = _collect_market_synchronization_data()
    if not data:
        st.info("No data available for synchronization analysis.")
        return

    analysis = _generate_market_synchronization_analysis(data)

    themed_card_container()
    st.markdown(f"""
    ## Market Synchronization Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Market synchronization analysis complete.")
# ------------- CHUNK 77: MARKET ANTI-CORRELATION ENGINE -------------

def _collect_market_anti_correlation_data():
    """
    Collect data needed to detect anti-correlation:
    - historical profit divergence between markets
    - historical profit divergence between teams
    - edge divergence patterns
    - confidence divergence patterns
    - anti-correlation clusters
    - volatility exposure
    - parlay amplification exposure
    """
    log = st.session_state.bet_log
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    if not log or not plays:
        return None

    # Historical profit by market
    market_perf = {}
    for b in log:
        market = b.get("market", "Unknown")
        profit = b.get("profit", 0)
        market_perf.setdefault(market, []).append(profit)

    # Compute anti-correlation proxy (variance difference)
    market_anti_corr_scores = {}
    markets = list(market_perf.keys())

    for i in range(len(markets)):
        for j in range(i + 1, len(markets)):
            m1, m2 = markets[i], markets[j]
            v1, v2 = market_perf[m1], market_perf[m2]

            if len(v1) > 1 and len(v2) > 1:
                diff = abs(np.var(v1) - np.var(v2))
                anti_corr_score = diff  # larger diff = stronger anti-correlation
            else:
                anti_corr_score = 0

            market_anti_corr_scores[f"{m1}__{m2}"] = float(anti_corr_score)

    # Today's divergence indicators
    today_edges = [p.get("edge", 0) for p in plays]
    today_conf = [p.get("true_confidence", 0) for p in plays]

    edge_divergence = float(np.var(today_edges)) if today_edges else 0
    conf_divergence = float(np.var(today_conf)) if today_conf else 0

    risk = _compute_risk_metrics()

    return {
        "market_anti_corr_scores": market_anti_corr_scores,
        "edge_divergence": edge_divergence,
        "confidence_divergence": conf_divergence,
        "volatility": risk["volatility"],
        "parlay_risk": risk["parlay_risk"],
    }


def _qwen_anti_correlation_prompt(data):
    """
    Build a structured prompt for Qwen to analyze anti-correlation.
    """
    prompt = f"""
You are an elite sports betting macro-hedging and anti-correlation analyst.

Analyze the following MARKET ANTI-CORRELATION DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Identify anti-correlated markets (moving opposite each other).
2. Identify divergence clusters (groups of markets diverging together).
3. Detect natural hedges (markets that offset each other's risk).
4. Highlight anti-correlation-driven risks (false hedges, unstable divergence).
5. Highlight anti-correlation-driven opportunities (hedge pairs, risk dampeners).
6. Provide 3–5 actionable anti-correlation strategy recommendations.
7. Keep output under 260 words.
8. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_anti_correlation_analysis(data):
    """
    Call Qwen to generate anti-correlation insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_anti_correlation_prompt(data)
    response = _call_qwen(prompt)
    return response or "No anti-correlation analysis generated."


def render_market_anti_correlation_engine():
    """
    Full UI for Qwen-powered anti-correlation detection.
    """
    st.header("Market Anti-Correlation Engine")
    st.caption("Qwen-powered detection of divergent markets and natural hedges.")

    data = _collect_market_anti_correlation_data()
    if not data:
        st.info("No data available for anti-correlation analysis.")
        return

    analysis = _generate_market_anti_correlation_analysis(data)

    themed_card_container()
    st.markdown(f"""
    ## Market Anti-Correlation Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Market anti-correlation analysis complete.")
# ------------- CHUNK 78: MARKET REGIME SHIFT ENGINE -------------

def _collect_market_regime_shift_data():
    """
    Collect data needed to detect regime shifts:
    - long-term variance trends
    - medium-term variance trends
    - short-term variance trends
    - edge regime transitions
    - confidence regime transitions
    - market-level structural transitions
    - volatility exposure
    - parlay amplification exposure
    """
    log = st.session_state.bet_log
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    if not log or not plays:
        return None

    hist_profit = [b.get("profit", 0) for b in log]
    hist_edges = [b.get("edge", 0) for b in log]
    hist_conf = [b.get("true_confidence", 0) for b in log]

    def rolling_var(arr, window):
        if len(arr) < window:
            return []
        return [float(np.var(arr[i:i+window])) for i in range(len(arr) - window + 1)]

    # Multi‑horizon variance trends
    long_term_vol = rolling_var(hist_profit, window=20)
    med_term_vol = rolling_var(hist_profit, window=10)
    short_term_vol = rolling_var(hist_profit, window=5)

    # Edge & confidence regime transitions
    long_edge = rolling_var(hist_edges, window=20)
    med_edge = rolling_var(hist_edges, window=10)
    short_edge = rolling_var(hist_edges, window=5)

    long_conf = rolling_var(hist_conf, window=20)
    med_conf = rolling_var(hist_conf, window=10)
    short_conf = rolling_var(hist_conf, window=5)

    # Market-level structural transitions
    market_perf = {}
    for b in log:
        m = b.get("market", "Unknown")
        profit = b.get("profit", 0)
        market_perf.setdefault(m, []).append(profit)

    market_regime_scores = {
        m: float(np.var(v)) if len(v) > 1 else 0
        for m, v in market_perf.items()
    }

    risk = _compute_risk_metrics()

    return {
        "long_term_vol": long_term_vol,
        "med_term_vol": med_term_vol,
        "short_term_vol": short_term_vol,
        "long_edge": long_edge,
        "med_edge": med_edge,
        "short_edge": short_edge,
        "long_conf": long_conf,
        "med_conf": med_conf,
        "short_conf": short_conf,
        "market_regime_scores": market_regime_scores,
        "volatility": risk["volatility"],
        "parlay_risk": risk["parlay_risk"],
    }


def _qwen_regime_shift_prompt(data):
    """
    Build a structured prompt for Qwen to analyze regime shifts.
    """
    prompt = f"""
You are an elite sports betting macro-regime analyst.

Analyze the following MARKET REGIME SHIFT DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Identify if a regime shift is occurring (macro-environment change).
2. Identify markets currently transitioning between regimes.
3. Detect regime-driven risks (instability, volatility, edge collapse).
4. Detect regime-driven opportunities (new edges, new stability pockets).
5. Map long-term vs medium-term vs short-term regime signals.
6. Provide 3–5 actionable regime-shift strategy recommendations.
7. Keep output under 280 words.
8. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_regime_shift_analysis(data):
    """
    Call Qwen to generate regime-shift insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_regime_shift_prompt(data)
    response = _call_qwen(prompt)
    return response or "No regime-shift analysis generated."


def render_market_regime_shift_engine():
    """
    Full UI for Qwen-powered regime shift detection.
    """
    st.header("Market Regime Shift Engine")
    st.caption("Qwen-powered detection of macro-environment regime changes.")

    data = _collect_market_regime_shift_data()
    if not data:
        st.info("No data available for regime-shift analysis.")
        return

    analysis = _generate_market_regime_shift_analysis(data)

    themed_card_container()
    st.markdown(f"""
    ## Market Regime Shift Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Market regime-shift analysis complete.")
# ------------- CHUNK 79: MARKET PHASE DETECTION ENGINE -------------

def _collect_market_phase_data():
    """
    Collect data needed to classify market phases:
    - expansion indicators
    - compression indicators
    - volatility indicators
    - stability indicators
    - drift indicators
    - shock indicators
    - historical phase patterns
    - parlay amplification exposure
    """
    log = st.session_state.bet_log
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    if not log or not plays:
        return None

    # Today's distributions
    today_edges = [p.get("edge", 0) for p in plays]
    today_conf = [p.get("true_confidence", 0) for p in plays]

    edge_var = float(np.var(today_edges)) if today_edges else 0
    conf_var = float(np.var(today_conf)) if today_conf else 0

    # Historical volatility
    hist_profit = [b.get("profit", 0) for b in log]
    hist_vol = float(np.var(hist_profit)) if hist_profit else 0

    # Drift indicator = slow directional change in confidence
    if len(today_conf) > 1:
        drift_indicator = float(np.mean(np.diff(today_conf)))
    else:
        drift_indicator = 0

    # Shock indicator = tail variance
    tail_var = float(np.var(hist_profit[-10:])) if len(hist_profit) >= 10 else 0

    risk = _compute_risk_metrics()

    return {
        "edge_variance": edge_var,
        "confidence_variance": conf_var,
        "historical_volatility": hist_vol,
        "drift_indicator": drift_indicator,
        "shock_indicator": tail_var,
        "volatility": risk["volatility"],
        "parlay_risk": risk["parlay_risk"],
    }


def _qwen_phase_prompt(data):
    """
    Build a structured prompt for Qwen to classify market phases.
    """
    prompt = f"""
You are an elite sports betting macro-phase analyst.

Classify the current MARKET PHASE using the following data:

{json.dumps(data, indent=2)}

PHASES TO CONSIDER:
1. Expansion (edges widening, confidence widening)
2. Compression (edges tightening, confidence tightening)
3. Volatility (variance rising, instability increasing)
4. Stability (variance falling, consistency rising)
5. Drift (slow directional movement in confidence)
6. Shock (tail-risk spike, sudden instability)

TASKS:
1. Identify the dominant phase today.
2. Identify secondary or emerging phases.
3. Highlight phase-driven risks.
4. Highlight phase-driven opportunities.
5. Provide 3–5 actionable phase-based strategy recommendations.
6. Keep output under 280 words.
7. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_phase_analysis(data):
    """
    Call Qwen to generate phase classification insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_phase_prompt(data)
    response = _call_qwen(prompt)
    return response or "No phase analysis generated."


def render_market_phase_engine():
    """
    Full UI for Qwen-powered market phase detection.
    """
    st.header("Market Phase Detection Engine")
    st.caption("Qwen-powered classification of today's macro market phase.")

    data = _collect_market_phase_data()
    if not data:
        st.info("No data available for phase detection.")
        return

    analysis = _generate_market_phase_analysis(data)

    themed_card_container()
    st.markdown(f"""
    ## Market Phase Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Market phase detection complete.")
# ------------- CHUNK 80: MARKET REGIME STABILITY ENGINE -------------

def _collect_market_regime_stability_data():
    """
    Collect data needed to score regime stability:
    - long-term variance stability
    - medium-term variance stability
    - short-term variance stability
    - edge stability across horizons
    - confidence stability across horizons
    - market-level structural stability
    - volatility exposure
    - parlay amplification exposure
    """
    log = st.session_state.bet_log
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    if not log or not plays:
        return None

    hist_profit = [b.get("profit", 0) for b in log]
    hist_edges = [b.get("edge", 0) for b in log]
    hist_conf = [b.get("true_confidence", 0) for b in log]

    def rolling_var(arr, window):
        if len(arr) < window:
            return []
        return [float(np.var(arr[i:i+window])) for i in range(len(arr) - window + 1)]

    # Multi-horizon stability indicators (inverse of variance)
    long_term_stability = [1 / (1 + v) for v in rolling_var(hist_profit, window=20)]
    med_term_stability = [1 / (1 + v) for v in rolling_var(hist_profit, window=10)]
    short_term_stability = [1 / (1 + v) for v in rolling_var(hist_profit, window=5)]

    # Edge stability
    long_edge_stability = [1 / (1 + v) for v in rolling_var(hist_edges, window=20)]
    med_edge_stability = [1 / (1 + v) for v in rolling_var(hist_edges, window=10)]
    short_edge_stability = [1 / (1 + v) for v in rolling_var(hist_edges, window=5)]

    # Confidence stability
    long_conf_stability = [1 / (1 + v) for v in rolling_var(hist_conf, window=20)]
    med_conf_stability = [1 / (1 + v) for v in rolling_var(hist_conf, window=10)]
    short_conf_stability = [1 / (1 + v) for v in rolling_var(hist_conf, window=5)]

    # Market-level structural stability
    market_perf = {}
    for b in log:
        m = b.get("market", "Unknown")
        profit = b.get("profit", 0)
        market_perf.setdefault(m, []).append(profit)

    market_stability_scores = {
        m: 1 / (1 + float(np.var(v))) if len(v) > 1 else 1
        for m, v in market_perf.items()
    }

    risk = _compute_risk_metrics()

    return {
        "long_term_stability": long_term_stability,
        "med_term_stability": med_term_stability,
        "short_term_stability": short_term_stability,
        "long_edge_stability": long_edge_stability,
        "med_edge_stability": med_edge_stability,
        "short_edge_stability": short_edge_stability,
        "long_conf_stability": long_conf_stability,
        "med_conf_stability": med_conf_stability,
        "short_conf_stability": short_conf_stability,
        "market_stability_scores": market_stability_scores,
        "volatility": risk["volatility"],
        "parlay_risk": risk["parlay_risk"],
    }


def _qwen_regime_stability_prompt(data):
    """
    Build a structured prompt for Qwen to analyze regime stability.
    """
    prompt = f"""
You are an elite sports betting macro-regime stability analyst.

Analyze the following MARKET REGIME STABILITY DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Score the stability of the current regime.
2. Identify whether the regime is strengthening or weakening.
3. Detect regime-stability risks (instability, variance creep, edge decay).
4. Detect regime-stability opportunities (durable edges, stable markets).
5. Compare long-term vs medium-term vs short-term stability signals.
6. Provide 3–5 actionable regime-stability strategy recommendations.
7. Keep output under 280 words.
8. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_regime_stability_analysis(data):
    """
    Call Qwen to generate regime-stability insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_regime_stability_prompt(data)
    response = _call_qwen(prompt)
    return response or "No regime-stability analysis generated."


def render_market_regime_stability_engine():
    """
    Full UI for Qwen-powered regime stability scoring.
    """
    st.header("Market Regime Stability Engine")
    st.caption("Qwen-powered scoring of regime stability and durability.")

    data = _collect_market_regime_stability_data()
    if not data:
        st.info("No data available for regime-stability analysis.")
        return

    analysis = _generate_market_regime_stability_analysis(data)

    themed_card_container()
    st.markdown(f"""
    ## Market Regime Stability Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Market regime-stability analysis complete.")
# ------------- CHUNK 81: MARKET DRIFT ENGINE -------------

def _collect_market_drift_data():
    """
    Collect data needed to detect and forecast drift:
    - directional drift in confidence
    - directional drift in edges
    - drift velocity (rate of change)
    - drift acceleration (change in velocity)
    - historical drift patterns
    - volatility exposure
    - parlay amplification exposure
    """
    log = st.session_state.bet_log
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    if not log or not plays:
        return None

    # Today's distributions
    today_edges = [p.get("edge", 0) for p in plays]
    today_conf = [p.get("true_confidence", 0) for p in plays]

    # Drift = directional change
    def compute_drift(arr):
        if len(arr) < 2:
            return 0
        return float(np.mean(np.diff(arr)))

    edge_drift = compute_drift(today_edges)
    conf_drift = compute_drift(today_conf)

    # Drift velocity = magnitude of drift
    def compute_velocity(arr):
        if len(arr) < 2:
            return 0
        return float(np.mean([abs(arr[i+1] - arr[i]) for i in range(len(arr)-1)]))

    edge_velocity = compute_velocity(today_edges)
    conf_velocity = compute_velocity(today_conf)

    # Drift acceleration = change in velocity
    def compute_acceleration(arr):
        if len(arr) < 3:
            return 0
        vels = [abs(arr[i+1] - arr[i]) for i in range(len(arr)-1)]
        return float(np.mean(np.diff(vels)))

    edge_accel = compute_acceleration(today_edges)
    conf_accel = compute_acceleration(today_conf)

    # Historical drift patterns
    hist_conf = [b.get("true_confidence", 0) for b in log]
    hist_edges = [b.get("edge", 0) for b in log]

    def rolling_drift(arr, window=5):
        if len(arr) < window:
            return []
        drifts = []
        for i in range(len(arr) - window + 1):
            seg = arr[i:i+window]
            drifts.append(float(np.mean(np.diff(seg))))
        return drifts

    hist_conf_drift = rolling_drift(hist_conf, window=5)
    hist_edge_drift = rolling_drift(hist_edges, window=5)

    risk = _compute_risk_metrics()

    return {
        "edge_drift": edge_drift,
        "conf_drift": conf_drift,
        "edge_velocity": edge_velocity,
        "conf_velocity": conf_velocity,
        "edge_acceleration": edge_accel,
        "conf_acceleration": conf_accel,
        "historical_conf_drift": hist_conf_drift,
        "historical_edge_drift": hist_edge_drift,
        "volatility": risk["volatility"],
        "parlay_risk": risk["parlay_risk"],
    }


def _qwen_drift_prompt(data):
    """
    Build a structured prompt for Qwen to analyze drift and forecast continuation or reversal.
    """
    prompt = f"""
You are an elite sports betting macro-drift analyst.

Analyze the following MARKET DRIFT DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Identify directional drift in edges and confidence.
2. Determine whether drift is strengthening, weakening, or reversing.
3. Detect drift velocity (speed) and drift acceleration (momentum).
4. Highlight drift-driven risks (false drift, unstable drift, reversal risk).
5. Highlight drift-driven opportunities (momentum edges, aligned plays).
6. Provide 3–5 actionable drift-based strategy recommendations.
7. Keep output under 280 words.
8. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_drift_analysis(data):
    """
    Call Qwen to generate drift insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_drift_prompt(data)
    response = _call_qwen(prompt)
    return response or "No drift analysis generated."


def render_market_drift_engine():
    """
    Full UI for Qwen-powered drift detection and forecasting.
    """
    st.header("Market Drift Engine")
    st.caption("Qwen-powered detection and forecasting of directional drift.")

    data = _collect_market_drift_data()
    if not data:
        st.info("No data available for drift analysis.")
        return

    analysis = _generate_market_drift_analysis(data)

    themed_card_container()
    st.markdown(f"""
    ## Market Drift Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Market drift analysis complete.")
# ------------- CHUNK 82: MARKET MOMENTUM ENGINE -------------

def _collect_market_momentum_data():
    """
    Collect data needed to detect and forecast momentum:
    - momentum in edges
    - momentum in confidence
    - momentum strength (velocity)
    - momentum decay or acceleration
    - historical momentum patterns
    - volatility exposure
    - parlay amplification exposure
    """
    log = st.session_state.bet_log
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    if not log or not plays:
        return None

    # Today's distributions
    today_edges = [p.get("edge", 0) for p in plays]
    today_conf = [p.get("true_confidence", 0) for p in plays]

    # Momentum = consistent directional movement
    def compute_momentum(arr):
        if len(arr) < 3:
            return 0
        diffs = np.diff(arr)
        return float(np.mean(diffs))

    edge_momentum = compute_momentum(today_edges)
    conf_momentum = compute_momentum(today_conf)

    # Momentum strength (velocity)
    def compute_velocity(arr):
        if len(arr) < 2:
            return 0
        return float(np.mean([abs(arr[i+1] - arr[i]) for i in range(len(arr)-1)]))

    edge_velocity = compute_velocity(today_edges)
    conf_velocity = compute_velocity(today_conf)

    # Momentum acceleration (is momentum increasing?)
    def compute_acceleration(arr):
        if len(arr) < 3:
            return 0
        vels = [abs(arr[i+1] - arr[i]) for i in range(len(arr)-1)]
        return float(np.mean(np.diff(vels)))

    edge_accel = compute_acceleration(today_edges)
    conf_accel = compute_acceleration(today_conf)

    # Historical momentum patterns
    hist_edges = [b.get("edge", 0) for b in log]
    hist_conf = [b.get("true_confidence", 0) for b in log]

    def rolling_momentum(arr, window=5):
        if len(arr) < window:
            return []
        moms = []
        for i in range(len(arr) - window + 1):
            seg = arr[i:i+window]
            moms.append(float(np.mean(np.diff(seg))))
        return moms

    hist_edge_momentum = rolling_momentum(hist_edges, window=5)
    hist_conf_momentum = rolling_momentum(hist_conf, window=5)

    risk = _compute_risk_metrics()

    return {
        "edge_momentum": edge_momentum,
        "conf_momentum": conf_momentum,
        "edge_velocity": edge_velocity,
        "conf_velocity": conf_velocity,
        "edge_acceleration": edge_accel,
        "conf_acceleration": conf_accel,
        "historical_edge_momentum": hist_edge_momentum,
        "historical_conf_momentum": hist_conf_momentum,
        "volatility": risk["volatility"],
        "parlay_risk": risk["parlay_risk"],
    }


def _qwen_momentum_prompt(data):
    """
    Build a structured prompt for Qwen to analyze momentum and forecast continuation or decay.
    """
    prompt = f"""
You are an elite sports betting macro-momentum analyst.

Analyze the following MARKET MOMENTUM DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Identify momentum in edges and confidence.
2. Determine whether momentum is strengthening, weakening, or reversing.
3. Detect momentum velocity (strength) and acceleration (momentum build-up).
4. Highlight momentum-driven risks (false momentum, exhaustion, reversal).
5. Highlight momentum-driven opportunities (momentum edges, aligned plays).
6. Provide 3–5 actionable momentum-based strategy recommendations.
7. Keep output under 280 words.
8. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_momentum_analysis(data):
    """
    Call Qwen to generate momentum insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_momentum_prompt(data)
    response = _call_qwen(prompt)
    return response or "No momentum analysis generated."


def render_market_momentum_engine():
    """
    Full UI for Qwen-powered momentum detection and forecasting.
    """
    st.header("Market Momentum Engine")
    st.caption("Qwen-powered detection and forecasting of market momentum.")

    data = _collect_market_momentum_data()
    if not data:
        st.info("No data available for momentum analysis.")
        return

    analysis = _generate_market_momentum_analysis(data)

    themed_card_container()
    st.markdown(f"""
    ## Market Momentum Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Market momentum analysis complete.")
# ------------- CHUNK 83: MARKET OVEREXTENSION ENGINE -------------

def _collect_market_overextension_data():
    """
    Collect data needed to detect overextension:
    - overextended edges (edges too high or stretched)
    - overextended confidence (confidence too high or stretched)
    - market-level overextension (variance spike)
    - exhaustion signals (momentum collapse)
    - historical overextension patterns
    - volatility exposure
    - parlay amplification exposure
    """
    log = st.session_state.bet_log
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    if not log or not plays:
        return None

    # Today's distributions
    today_edges = [p.get("edge", 0) for p in plays]
    today_conf = [p.get("true_confidence", 0) for p in plays]

    # Overextension = extreme values or stretched distributions
    def compute_overextension(arr):
        if not arr:
            return 0
        mean = np.mean(arr)
        max_val = max(arr)
        return float(max_val - mean)

    edge_overext = compute_overextension(today_edges)
    conf_overext = compute_overextension(today_conf)

    # Market-level overextension (variance spike)
    hist_profit = [b.get("profit", 0) for b in log]
    market_overext = float(np.var(hist_profit[-10:])) if len(hist_profit) >= 10 else 0

    # Exhaustion signals = momentum collapse
    def compute_momentum(arr):
        if len(arr) < 3:
            return 0
        diffs = np.diff(arr)
        return float(np.mean(diffs))

    edge_momentum = compute_momentum(today_edges)
    conf_momentum = compute_momentum(today_conf)

    exhaustion_signal = float(-(edge_momentum + conf_momentum))

    # Historical overextension patterns
    def rolling_overext(arr, window=5):
        if len(arr) < window:
            return []
        vals = []
        for i in range(len(arr) - window + 1):
            seg = arr[i:i+window]
            vals.append(float(max(seg) - np.mean(seg)))
        return vals

    hist_edge_overext = rolling_overext([b.get("edge", 0) for b in log], window=5)
    hist_conf_overext = rolling_overext([b.get("true_confidence", 0) for b in log], window=5)

    risk = _compute_risk_metrics()

    return {
        "edge_overextension": edge_overext,
        "confidence_overextension": conf_overext,
        "market_overextension": market_overext,
        "exhaustion_signal": exhaustion_signal,
        "historical_edge_overextension": hist_edge_overext,
        "historical_conf_overextension": hist_conf_overext,
        "volatility": risk["volatility"],
        "parlay_risk": risk["parlay_risk"],
    }


def _qwen_overextension_prompt(data):
    """
    Build a structured prompt for Qwen to analyze overextension.
    """
    prompt = f"""
You are an elite sports betting macro-overextension analyst.

Analyze the following MARKET OVEREXTENSION DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Identify overextended edges, confidence, and markets.
2. Determine whether overextension is increasing or decreasing.
3. Detect exhaustion signals (momentum collapse, stretched distributions).
4. Highlight overextension-driven risks (false edges, collapse risk, instability).
5. Highlight overextension-driven opportunities (fade points, reversal setups).
6. Provide 3–5 actionable overextension-based strategy recommendations.
7. Keep output under 280 words.
8. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_overextension_analysis(data):
    """
    Call Qwen to generate overextension insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_overextension_prompt(data)
    response = _call_qwen(prompt)
    return response or "No overextension analysis generated."


def render_market_overextension_engine():
    """
    Full UI for Qwen-powered overextension detection.
    """
    st.header("Market Overextension Engine")
    st.caption("Qwen-powered detection of overextended edges, confidence, and markets.")

    data = _collect_market_overextension_data()
    if not data:
        st.info("No data available for overextension analysis.")
        return

    analysis = _generate_market_overextension_analysis(data)

    themed_card_container()
    st.markdown(f"""
    ## Market Overextension Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Market overextension analysis complete.")
# ------------- CHUNK 84: MARKET EXHAUSTION ENGINE -------------

def _collect_market_exhaustion_data():
    """
    Collect data needed to detect exhaustion:
    - exhaustion in edges (momentum collapse)
    - exhaustion in confidence (momentum collapse)
    - market-level exhaustion (variance decay after spike)
    - exhaustion reversal signals
    - historical exhaustion patterns
    - volatility exposure
    - parlay amplification exposure
    """
    log = st.session_state.bet_log
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    if not log or not plays:
        return None

    # Today's distributions
    today_edges = [p.get("edge", 0) for p in plays]
    today_conf = [p.get("true_confidence", 0) for p in plays]

    # Exhaustion = momentum collapse
    def compute_momentum(arr):
        if len(arr) < 3:
            return 0
        diffs = np.diff(arr)
        return float(np.mean(diffs))

    edge_momentum = compute_momentum(today_edges)
    conf_momentum = compute_momentum(today_conf)

    # Exhaustion score = negative momentum
    edge_exhaustion = float(-edge_momentum)
    conf_exhaustion = float(-conf_momentum)

    # Market-level exhaustion = variance spike followed by decay
    hist_profit = [b.get("profit", 0) for b in log]
    if len(hist_profit) >= 15:
        recent_var = np.var(hist_profit[-5:])
        prev_var = np.var(hist_profit[-15:-5])
        market_exhaustion = float(prev_var - recent_var)
    else:
        market_exhaustion = 0

    # Exhaustion reversal signals = momentum turning positive after exhaustion
    def compute_reversal(arr):
        if len(arr) < 4:
            return 0
        diffs = np.diff(arr)
        return float(np.mean(diffs[-2:]))

    edge_reversal = compute_reversal(today_edges)
    conf_reversal = compute_reversal(today_conf)

    # Historical exhaustion patterns
    def rolling_exhaustion(arr, window=5):
        if len(arr) < window:
            return []
        vals = []
        for i in range(len(arr) - window + 1):
            seg = arr[i:i+window]
            diffs = np.diff(seg)
            vals.append(float(-np.mean(diffs)))
        return vals

    hist_edge_exhaustion = rolling_exhaustion([b.get("edge", 0) for b in log], window=5)
    hist_conf_exhaustion = rolling_exhaustion([b.get("true_confidence", 0) for b in log], window=5)

    risk = _compute_risk_metrics()

    return {
        "edge_exhaustion": edge_exhaustion,
        "confidence_exhaustion": conf_exhaustion,
        "market_exhaustion": market_exhaustion,
        "edge_reversal_signal": edge_reversal,
        "confidence_reversal_signal": conf_reversal,
        "historical_edge_exhaustion": hist_edge_exhaustion,
        "historical_conf_exhaustion": hist_conf_exhaustion,
        "volatility": risk["volatility"],
        "parlay_risk": risk["parlay_risk"],
    }


def _qwen_exhaustion_prompt(data):
    """
    Build a structured prompt for Qwen to analyze exhaustion.
    """
    prompt = f"""
You are an elite sports betting macro-exhaustion analyst.

Analyze the following MARKET EXHAUSTION DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Identify exhaustion in edges, confidence, and markets.
2. Determine whether exhaustion is deepening or recovering.
3. Detect exhaustion reversal signals (momentum turning positive).
4. Highlight exhaustion-driven risks (collapse, false edges, instability).
5. Highlight exhaustion-driven opportunities (reversal setups, fade setups).
6. Provide 3–5 actionable exhaustion-based strategy recommendations.
7. Keep output under 280 words.
8. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_exhaustion_analysis(data):
    """
    Call Qwen to generate exhaustion insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_exhaustion_prompt(data)
    response = _call_qwen(prompt)
    return response or "No exhaustion analysis generated."


def render_market_exhaustion_engine():
    """
    Full UI for Qwen-powered exhaustion detection.
    """
    st.header("Market Exhaustion Engine")
    st.caption("Qwen-powered detection of exhaustion and exhaustion reversals.")

    data = _collect_market_exhaustion_data()
    if not data:
        st.info("No data available for exhaustion analysis.")
        return

    analysis = _generate_market_exhaustion_analysis(data)

    themed_card_container()
    st.markdown(f"""
    ## Market Exhaustion Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Market exhaustion analysis complete.")
# ------------- CHUNK 85: MARKET SHOCK ENGINE -------------

def _collect_market_shock_data():
    """
    Collect data needed to detect shock events:
    - shock volatility (sudden variance spikes)
    - shock reversals (snapbacks after spikes)
    - shock-driven instability
    - shock clusters (multiple markets spiking together)
    - historical shock patterns
    - volatility exposure
    - parlay amplification exposure
    """
    log = st.session_state.bet_log
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    if not log or not plays:
        return None

    hist_profit = [b.get("profit", 0) for b in log]

    # Shock volatility = sudden variance spike
    if len(hist_profit) >= 15:
        recent_var = np.var(hist_profit[-5:])
        prev_var = np.var(hist_profit[-15:-5])
        shock_volatility = float(recent_var - prev_var)
    else:
        shock_volatility = 0

    # Shock reversal = variance spike followed by collapse
    if len(hist_profit) >= 20:
        var_1 = np.var(hist_profit[-5:])
        var_2 = np.var(hist_profit[-10:-5])
        var_3 = np.var(hist_profit[-15:-10])
        shock_reversal = float((var_2 - var_3) - (var_1 - var_2))
    else:
        shock_reversal = 0

    # Shock clusters = multiple markets spiking together
    market_perf = {}
    for b in log:
        m = b.get("market", "Unknown")
        profit = b.get("profit", 0)
        market_perf.setdefault(m, []).append(profit)

    market_shock_scores = {}
    for m, v in market_perf.items():
        if len(v) >= 10:
            recent = np.var(v[-5:])
            prev = np.var(v[-10:-5])
            market_shock_scores[m] = float(recent - prev)
        else:
            market_shock_scores[m] = 0

    # Shock-driven instability = extreme edge/confidence swings
    today_edges = [p.get("edge", 0) for p in plays]
    today_conf = [p.get("true_confidence", 0) for p in plays]

    def compute_instability(arr):
        if len(arr) < 2:
            return 0
        diffs = np.diff(arr)
        return float(np.mean([abs(x) for x in diffs]))

    edge_instability = compute_instability(today_edges)
    conf_instability = compute_instability(today_conf)

    # Historical shock patterns
    def rolling_shock(arr, window=5):
        if len(arr) < window * 2:
            return []
        vals = []
        for i in range(len(arr) - window * 2 + 1):
            seg1 = arr[i:i+window]
            seg2 = arr[i+window:i+window*2]
            vals.append(float(np.var(seg2) - np.var(seg1)))
        return vals

    hist_shock = rolling_shock(hist_profit, window=5)

    risk = _compute_risk_metrics()

    return {
        "shock_volatility": shock_volatility,
        "shock_reversal": shock_reversal,
        "market_shock_scores": market_shock_scores,
        "edge_instability": edge_instability,
        "confidence_instability": conf_instability,
        "historical_shock": hist_shock,
        "volatility": risk["volatility"],
        "parlay_risk": risk["parlay_risk"],
    }


def _qwen_shock_prompt(data):
    """
    Build a structured prompt for Qwen to analyze shock events.
    """
    prompt = f"""
You are an elite sports betting macro-shock analyst.

Analyze the following MARKET SHOCK DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Identify shock volatility (sudden variance spikes).
2. Identify shock reversals (snapbacks after spikes).
3. Detect shock clusters (multiple markets spiking together).
4. Highlight shock-driven risks (instability, collapse, false edges).
5. Highlight shock-driven opportunities (reversal setups, volatility fades).
6. Provide 3–5 actionable shock-based strategy recommendations.
7. Keep output under 280 words.
8. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_shock_analysis(data):
    """
    Call Qwen to generate shock insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_shock_prompt(data)
    response = _call_qwen(prompt)
    return response or "No shock analysis generated."


def render_market_shock_engine():
    """
    Full UI for Qwen-powered shock detection.
    """
    st.header("Market Shock Engine")
    st.caption("Qwen-powered detection of shock volatility and shock reversals.")

    data = _collect_market_shock_data()
    if not data:
        st.info("No data available for shock analysis.")
        return

    analysis = _generate_market_shock_analysis(data)

    themed_card_container()
    st.markdown(f"""
    ## Market Shock Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Market shock analysis complete.")
# ------------- CHUNK 86: MARKET INSTABILITY ENGINE -------------

def _collect_market_instability_data():
    """
    Collect data needed to detect instability:
    - instability in edges (erratic swings)
    - instability in confidence (erratic swings)
    - market-level instability (variance turbulence)
    - instability clusters (multiple markets destabilizing together)
    - historical instability patterns
    - volatility exposure
    - parlay amplification exposure
    """
    log = st.session_state.bet_log
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    if not log or not plays:
        return None

    # Today's distributions
    today_edges = [p.get("edge", 0) for p in plays]
    today_conf = [p.get("true_confidence", 0) for p in plays]

    # Instability = erratic movement (high absolute diffs)
    def compute_instability(arr):
        if len(arr) < 2:
            return 0
        diffs = np.diff(arr)
        return float(np.mean([abs(x) for x in diffs]))

    edge_instability = compute_instability(today_edges)
    conf_instability = compute_instability(today_conf)

    # Market-level instability = turbulence in recent variance
    hist_profit = [b.get("profit", 0) for b in log]
    if len(hist_profit) >= 15:
        var1 = np.var(hist_profit[-5:])
        var2 = np.var(hist_profit[-10:-5])
        var3 = np.var(hist_profit[-15:-10])
        market_instability = float(abs(var1 - var2) + abs(var2 - var3))
    else:
        market_instability = 0

    # Instability clusters = multiple markets destabilizing together
    market_perf = {}
    for b in log:
        m = b.get("market", "Unknown")
        profit = b.get("profit", 0)
        market_perf.setdefault(m, []).append(profit)

    market_instability_scores = {}
    for m, v in market_perf.items():
        if len(v) >= 10:
            var1 = np.var(v[-5:])
            var2 = np.var(v[-10:-5])
            market_instability_scores[m] = float(abs(var1 - var2))
        else:
            market_instability_scores[m] = 0

    # Historical instability patterns
    def rolling_instability(arr, window=5):
        if len(arr) < window:
            return []
        vals = []
        for i in range(len(arr) - window + 1):
            seg = arr[i:i+window]
            diffs = np.diff(seg)
            vals.append(float(np.mean([abs(x) for x in diffs])))
        return vals

    hist_edge_instability = rolling_instability([b.get("edge", 0) for b in log], window=5)
    hist_conf_instability = rolling_instability([b.get("true_confidence", 0) for b in log], window=5)

    risk = _compute_risk_metrics()

    return {
        "edge_instability": edge_instability,
        "confidence_instability": conf_instability,
        "market_instability": market_instability,
        "market_instability_scores": market_instability_scores,
        "historical_edge_instability": hist_edge_instability,
        "historical_conf_instability": hist_conf_instability,
        "volatility": risk["volatility"],
        "parlay_risk": risk["parlay_risk"],
    }


def _qwen_instability_prompt(data):
    """
    Build a structured prompt for Qwen to analyze instability.
    """
    prompt = f"""
You are an elite sports betting macro-instability analyst.

Analyze the following MARKET INSTABILITY DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Identify instability in edges, confidence, and markets.
2. Determine whether instability is increasing or decreasing.
3. Detect instability clusters (multiple markets destabilizing together).
4. Highlight instability-driven risks (chaos, false edges, volatility traps).
5. Highlight instability-driven opportunities (mispriced edges, reversal setups).
6. Provide 3–5 actionable instability-based strategy recommendations.
7. Keep output under 280 words.
8. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_instability_analysis(data):
    """
    Call Qwen to generate instability insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_instability_prompt(data)
    response = _call_qwen(prompt)
    return response or "No instability analysis generated."


def render_market_instability_engine():
    """
    Full UI for Qwen-powered instability detection.
    """
    st.header("Market Instability Engine")
    st.caption("Qwen-powered detection of instability and instability clusters.")

    data = _collect_market_instability_data()
    if not data:
        st.info("No data available for instability analysis.")
        return

    analysis = _generate_market_instability_analysis(data)

    themed_card_container()
    st.markdown(f"""
    ## Market Instability Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Market instability analysis complete.")
# ------------- CHUNK 87: MARKET TURBULENCE ENGINE -------------

def _collect_market_turbulence_data():
    """
    Collect data needed to detect turbulence:
    - turbulence in edges (wild swings)
    - turbulence in confidence (wild swings)
    - market-level turbulence (variance whiplash)
    - turbulence cycles (repeating instability patterns)
    - historical turbulence patterns
    - volatility exposure
    - parlay amplification exposure
    """
    log = st.session_state.bet_log
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    if not log or not plays:
        return None

    # Today's distributions
    today_edges = [p.get("edge", 0) for p in plays]
    today_conf = [p.get("true_confidence", 0) for p in plays]

    # Turbulence = wild, repeated swings (high variance of diffs)
    def compute_turbulence(arr):
        if len(arr) < 3:
            return 0
        diffs = np.diff(arr)
        return float(np.var(diffs))

    edge_turbulence = compute_turbulence(today_edges)
    conf_turbulence = compute_turbulence(today_conf)

    # Market-level turbulence = variance whiplash
    hist_profit = [b.get("profit", 0) for b in log]
    if len(hist_profit) >= 20:
        var1 = np.var(hist_profit[-5:])
        var2 = np.var(hist_profit[-10:-5])
        var3 = np.var(hist_profit[-15:-10])
        market_turbulence = float(abs(var1 - var2) + abs(var2 - var3))
    else:
        market_turbulence = 0

    # Turbulence cycles = repeating instability patterns
    def compute_cycle_strength(arr, window=5):
        if len(arr) < window * 2:
            return 0
        seg1 = arr[-window:]
        seg2 = arr[-window*2:-window]
        return float(abs(np.var(seg1) - np.var(seg2)))

    turbulence_cycle_strength = compute_cycle_strength(hist_profit, window=5)

    # Historical turbulence patterns
    def rolling_turbulence(arr, window=5):
        if len(arr) < window:
            return []
        vals = []
        for i in range(len(arr) - window + 1):
            seg = arr[i:i+window]
            diffs = np.diff(seg)
            vals.append(float(np.var(diffs)))
        return vals

    hist_edge_turbulence = rolling_turbulence([b.get("edge", 0) for b in log], window=5)
    hist_conf_turbulence = rolling_turbulence([b.get("true_confidence", 0) for b in log], window=5)

    risk = _compute_risk_metrics()

    return {
        "edge_turbulence": edge_turbulence,
        "confidence_turbulence": conf_turbulence,
        "market_turbulence": market_turbulence,
        "turbulence_cycle_strength": turbulence_cycle_strength,
        "historical_edge_turbulence": hist_edge_turbulence,
        "historical_conf_turbulence": hist_conf_turbulence,
        "volatility": risk["volatility"],
        "parlay_risk": risk["parlay_risk"],
    }


def _qwen_turbulence_prompt(data):
    """
    Build a structured prompt for Qwen to analyze turbulence.
    """
    prompt = f"""
You are an elite sports betting macro-turbulence analyst.

Analyze the following MARKET TURBULENCE DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Identify turbulence in edges, confidence, and markets.
2. Determine whether turbulence is increasing, decreasing, or cycling.
3. Detect turbulence cycles (repeating instability patterns).
4. Highlight turbulence-driven risks (chaos, whiplash, false edges).
5. Highlight turbulence-driven opportunities (mispricing, reversal setups).
6. Provide 3–5 actionable turbulence-based strategy recommendations.
7. Keep output under 280 words.
8. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_turbulence_analysis(data):
    """
    Call Qwen to generate turbulence insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_turbulence_prompt(data)
    response = _call_qwen(prompt)
    return response or "No turbulence analysis generated."


def render_market_turbulence_engine():
    """
    Full UI for Qwen-powered turbulence detection.
    """
    st.header("Market Turbulence Engine")
    st.caption("Qwen-powered detection of turbulence and turbulence cycles.")

    data = _collect_market_turbulence_data()
    if not data:
        st.info("No data available for turbulence analysis.")
        return

    analysis = _generate_market_turbulence_analysis(data)

    themed_card_container()
    st.markdown(f"""
    ## Market Turbulence Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Market turbulence analysis complete.")
# ------------- CHUNK 88: MARKET VOLATILITY CYCLE ENGINE -------------

def _collect_market_volatility_cycle_data():
    """
    Collect data needed to detect volatility cycles:
    - volatility expansion (variance rising)
    - volatility compression (variance falling)
    - volatility wave strength
    - volatility wave direction
    - historical volatility cycles
    - volatility exposure
    - parlay amplification exposure
    """
    log = st.session_state.bet_log
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    if not log or not plays:
        return None

    hist_profit = [b.get("profit", 0) for b in log]

    # Volatility expansion/compression = variance change across windows
    def compute_vol_cycle(arr):
        if len(arr) < 20:
            return 0, 0, 0
        var1 = np.var(arr[-5:])
        var2 = np.var(arr[-10:-5])
        var3 = np.var(arr[-15:-10])

        expansion = float(var1 - var2)
        compression = float(var2 - var1)
        wave_strength = float(abs(var1 - var2) + abs(var2 - var3))

        return expansion, compression, wave_strength

    vol_expansion, vol_compression, vol_wave_strength = compute_vol_cycle(hist_profit)

    # Volatility wave direction = expansion vs compression dominance
    if abs(vol_expansion) > abs(vol_compression):
        wave_direction = "expansion"
    elif abs(vol_compression) > abs(vol_expansion):
        wave_direction = "compression"
    else:
        wave_direction = "neutral"

    # Historical volatility cycles
    def rolling_vol_cycle(arr, window=5):
        if len(arr) < window * 2:
            return []
        vals = []
        for i in range(len(arr) - window * 2 + 1):
            seg1 = arr[i:i+window]
            seg2 = arr[i+window:i+window*2]
            vals.append(float(np.var(seg2) - np.var(seg1)))
        return vals

    hist_vol_cycles = rolling_vol_cycle(hist_profit, window=5)

    risk = _compute_risk_metrics()

    return {
        "volatility_expansion": vol_expansion,
        "volatility_compression": vol_compression,
        "volatility_wave_strength": vol_wave_strength,
        "volatility_wave_direction": wave_direction,
        "historical_volatility_cycles": hist_vol_cycles,
        "volatility": risk["volatility"],
        "parlay_risk": risk["parlay_risk"],
    }


def _qwen_volatility_cycle_prompt(data):
    """
    Build a structured prompt for Qwen to analyze volatility cycles.
    """
    prompt = f"""
You are an elite sports betting macro-volatility-cycle analyst.

Analyze the following MARKET VOLATILITY CYCLE DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Identify volatility expansion and volatility compression.
2. Determine the current volatility wave direction.
3. Evaluate volatility wave strength (cycle amplitude).
4. Highlight volatility-cycle risks (expansion traps, compression traps).
5. Highlight volatility-cycle opportunities (breakouts, fades, cycle reversals).
6. Provide 3–5 actionable volatility-cycle strategy recommendations.
7. Keep output under 280 words.
8. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_volatility_cycle_analysis(data):
    """
    Call Qwen to generate volatility-cycle insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_volatility_cycle_prompt(data)
    response = _call_qwen(prompt)
    return response or "No volatility-cycle analysis generated."


def render_market_volatility_cycle_engine():
    """
    Full UI for Qwen-powered volatility cycle detection.
    """
    st.header("Market Volatility Cycle Engine")
    st.caption("Qwen-powered detection of volatility expansion/compression cycles.")

    data = _collect_market_volatility_cycle_data()
    if not data:
        st.info("No data available for volatility-cycle analysis.")
        return

    analysis = _generate_market_volatility_cycle_analysis(data)

    themed_card_container()
    st.markdown(f"""
    ## Market Volatility Cycle Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Market volatility-cycle analysis complete.")
# ------------- CHUNK 89: MARKET COMPRESSION ENGINE -------------

def _collect_market_compression_data():
    """
    Collect data needed to detect compression:
    - compression in edges (tightening distributions)
    - compression in confidence (tightening distributions)
    - market-level compression (variance collapse)
    - compression breakout signals
    - historical compression patterns
    - volatility exposure
    - parlay amplification exposure
    """
    log = st.session_state.bet_log
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    if not log or not plays:
        return None

    # Today's distributions
    today_edges = [p.get("edge", 0) for p in plays]
    today_conf = [p.get("true_confidence", 0) for p in plays]

    # Compression = variance collapse
    def compute_compression(arr):
        if len(arr) < 2:
            return 0
        return float(np.var(arr))

    edge_compression = compute_compression(today_edges)
    conf_compression = compute_compression(today_conf)

    # Market-level compression = variance collapse across windows
    hist_profit = [b.get("profit", 0) for b in log]
    if len(hist_profit) >= 15:
        var1 = np.var(hist_profit[-5:])
        var2 = np.var(hist_profit[-10:-5])
        market_compression = float(var2 - var1)
    else:
        market_compression = 0

    # Compression breakout = variance collapse followed by expansion
    if len(hist_profit) >= 20:
        var_a = np.var(hist_profit[-5:])
        var_b = np.var(hist_profit[-10:-5])
        var_c = np.var(hist_profit[-15:-10])
        compression_breakout = float((var_b - var_c) - (var_a - var_b))
    else:
        compression_breakout = 0

    # Historical compression patterns
    def rolling_compression(arr, window=5):
        if len(arr) < window:
            return []
        vals = []
        for i in range(len(arr) - window + 1):
            seg = arr[i:i+window]
            vals.append(float(np.var(seg)))
        return vals

    hist_edge_compression = rolling_compression([b.get("edge", 0) for b in log], window=5)
    hist_conf_compression = rolling_compression([b.get("true_confidence", 0) for b in log], window=5)

    risk = _compute_risk_metrics()

    return {
        "edge_compression": edge_compression,
        "confidence_compression": conf_compression,
        "market_compression": market_compression,
        "compression_breakout_signal": compression_breakout,
        "historical_edge_compression": hist_edge_compression,
        "historical_conf_compression": hist_conf_compression,
        "volatility": risk["volatility"],
        "parlay_risk": risk["parlay_risk"],
    }


def _qwen_compression_prompt(data):
    """
    Build a structured prompt for Qwen to analyze compression.
    """
    prompt = f"""
You are an elite sports betting macro-compression analyst.

Analyze the following MARKET COMPRESSION DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Identify compression in edges, confidence, and markets.
2. Determine whether compression is tightening or loosening.
3. Detect compression breakout signals (variance collapse → expansion).
4. Highlight compression-driven risks (false stability, breakout traps).
5. Highlight compression-driven opportunities (breakouts, fades, coil setups).
6. Provide 3–5 actionable compression-based strategy recommendations.
7. Keep output under 280 words.
8. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_compression_analysis(data):
    """
    Call Qwen to generate compression insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_compression_prompt(data)
    response = _call_qwen(prompt)
    return response or "No compression analysis generated."


def render_market_compression_engine():
    """
    Full UI for Qwen-powered compression detection.
    """
    st.header("Market Compression Engine")
    st.caption("Qwen-powered detection of compression and compression breakouts.")

    data = _collect_market_compression_data()
    if not data:
        st.info("No data available for compression analysis.")
        return

    analysis = _generate_market_compression_analysis(data)

    themed_card_container()
    st.markdown(f"""
    ## Market Compression Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Market compression analysis complete.")
# ------------- CHUNK 90: MARKET EXPANSION ENGINE -------------

def _collect_market_expansion_data():
    """
    Collect data needed to detect expansion:
    - expansion in edges (widening distributions)
    - expansion in confidence (widening distributions)
    - market-level expansion (variance surge)
    - expansion exhaustion signals
    - historical expansion patterns
    - volatility exposure
    - parlay amplification exposure
    """
    log = st.session_state.bet_log
    plays = (
        st.session_state.today_plays.get("Top Plays", []) +
        st.session_state.today_plays.get("Watchlist", []) +
        st.session_state.today_plays.get("AI Slip", [])
    )

    if not log or not plays:
        return None

    # Today's distributions
    today_edges = [p.get("edge", 0) for p in plays]
    today_conf = [p.get("true_confidence", 0) for p in plays]

    # Expansion = variance widening
    def compute_expansion(arr):
        if len(arr) < 2:
            return 0
        return float(np.var(arr))

    edge_expansion = compute_expansion(today_edges)
    conf_expansion = compute_expansion(today_conf)

    # Market-level expansion = variance surge across windows
    hist_profit = [b.get("profit", 0) for b in log]
    if len(hist_profit) >= 15:
        var1 = np.var(hist_profit[-5:])
        var2 = np.var(hist_profit[-10:-5])
        market_expansion = float(var1 - var2)
    else:
        market_expansion = 0

    # Expansion exhaustion = variance surge followed by collapse
    if len(hist_profit) >= 20:
        var_a = np.var(hist_profit[-5:])
        var_b = np.var(hist_profit[-10:-5])
        var_c = np.var(hist_profit[-15:-10])
        expansion_exhaustion = float((var_a - var_b) - (var_b - var_c))
    else:
        expansion_exhaustion = 0

    # Historical expansion patterns
    def rolling_expansion(arr, window=5):
        if len(arr) < window:
            return []
        vals = []
        for i in range(len(arr) - window + 1):
            seg = arr[i:i+window]
            vals.append(float(np.var(seg)))
        return vals

    hist_edge_expansion = rolling_expansion([b.get("edge", 0) for b in log], window=5)
    hist_conf_expansion = rolling_expansion([b.get("true_confidence", 0) for b in log], window=5)

    risk = _compute_risk_metrics()

    return {
        "edge_expansion": edge_expansion,
        "confidence_expansion": conf_expansion,
        "market_expansion": market_expansion,
        "expansion_exhaustion_signal": expansion_exhaustion,
        "historical_edge_expansion": hist_edge_expansion,
        "historical_conf_expansion": hist_conf_expansion,
        "volatility": risk["volatility"],
        "parlay_risk": risk["parlay_risk"],
    }


def _qwen_expansion_prompt(data):
    """
    Build a structured prompt for Qwen to analyze expansion.
    """
    prompt = f"""
You are an elite sports betting macro-expansion analyst.

Analyze the following MARKET EXPANSION DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Identify expansion in edges, confidence, and markets.
2. Determine whether expansion is strengthening or weakening.
3. Detect expansion exhaustion signals (variance surge → collapse).
4. Highlight expansion-driven risks (false breakouts, exhaustion traps).
5. Highlight expansion-driven opportunities (breakouts, momentum edges).
6. Provide 3–5 actionable expansion-based strategy recommendations.
7. Keep output under 280 words.
8. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_expansion_analysis(data):
    """
    Call Qwen to generate expansion insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_expansion_prompt(data)
    response = _call_qwen(prompt)
    return response or "No expansion analysis generated."


def render_market_expansion_engine():
    """
    Full UI for Qwen-powered expansion detection.
    """
    st.header("Market Expansion Engine")
    st.caption("Qwen-powered detection of expansion and expansion exhaustion.")

    data = _collect_market_expansion_data()
    if not data:
        st.info("No data available for expansion analysis.")
        return

    analysis = _generate_market_expansion_analysis(data)

    themed_card_container()
    st.markdown(f"""
    ## Market Expansion Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Market expansion analysis complete.")
# ------------- CHUNK 91: MARKET REGIME MAP ENGINE -------------

def _collect_market_regime_map_data():
    """
    Collect data needed to map all regimes simultaneously:
    - volatility regime signals
    - expansion/compression regime signals
    - drift regime signals
    - momentum regime signals
    - overextension regime signals
    - exhaustion regime signals
    - shock regime signals
    - instability regime signals
    - turbulence regime signals
    - volatility cycle regime signals
    - regime overlaps
    - regime conflicts
    - regime dominance
    """
    # Pull from previously computed modules if available
    # If not available, compute minimal signals inline

    def safe_get(key, default=0):
        return st.session_state.get(key, default)

    regime_data = {
        "volatility": safe_get("volatility"),
        "parlay_risk": safe_get("parlay_risk"),

        # Expansion / Compression
        "expansion": safe_get("edge_expansion"),
        "compression": safe_get("edge_compression"),

        # Drift / Momentum
        "drift": safe_get("edge_drift"),
        "momentum": safe_get("edge_momentum"),

        # Overextension / Exhaustion
        "overextension": safe_get("edge_overextension"),
        "exhaustion": safe_get("edge_exhaustion"),

        # Shock / Instability / Turbulence
        "shock": safe_get("shock_volatility"),
        "instability": safe_get("edge_instability"),
        "turbulence": safe_get("edge_turbulence"),

        # Volatility cycles
        "volatility_expansion": safe_get("volatility_expansion"),
        "volatility_compression": safe_get("volatility_compression"),
        "volatility_wave_strength": safe_get("volatility_wave_strength"),
    }

    # Compute regime overlaps
    overlaps = []
    if regime_data["expansion"] > 0 and regime_data["momentum"] > 0:
        overlaps.append("Expansion + Momentum")
    if regime_data["compression"] > 0 and regime_data["instability"] > 0:
        overlaps.append("Compression + Instability")
    if regime_data["shock"] > 0 and regime_data["turbulence"] > 0:
        overlaps.append("Shock + Turbulence")
    if regime_data["overextension"] > 0 and regime_data["exhaustion"] > 0:
        overlaps.append("Overextension + Exhaustion")

    # Compute regime conflicts
    conflicts = []
    if regime_data["expansion"] > 0 and regime_data["compression"] > 0:
        conflicts.append("Expansion vs Compression")
    if regime_data["momentum"] > 0 and regime_data["drift"] < 0:
        conflicts.append("Momentum vs Drift")
    if regime_data["shock"] > 0 and regime_data["stability"] if "stability" in regime_data else False:
        conflicts.append("Shock vs Stability")

    # Compute regime dominance (largest magnitude)
    abs_vals = {k: abs(v) for k, v in regime_data.items()}
    dominant_regime = max(abs_vals, key=abs_vals.get)

    return {
        "regime_data": regime_data,
        "regime_overlaps": overlaps,
        "regime_conflicts": conflicts,
        "dominant_regime": dominant_regime,
    }


def _qwen_regime_map_prompt(data):
    """
    Build a structured prompt for Qwen to analyze multi-regime mapping.
    """
    prompt = f"""
You are an elite sports betting macro-regime mapping analyst.

Analyze the following MULTI-REGIME MAP DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Identify all active regimes.
2. Identify regime overlaps (multiple regimes active simultaneously).
3. Identify regime conflicts (regimes pushing in opposite directions).
4. Identify the dominant regime (largest macro force).
5. Highlight regime-map risks (conflict traps, overlap instability).
6. Highlight regime-map opportunities (alignment edges, regime synergy).
7. Provide 3–5 actionable regime-map strategy recommendations.
8. Keep output under 300 words.
9. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_regime_map_analysis(data):
    """
    Call Qwen to generate multi-regime mapping insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_regime_map_prompt(data)
    response = _call_qwen(prompt)
    return response or "No regime-map analysis generated."


def render_market_regime_map_engine():
    """
    Full UI for Qwen-powered multi-regime mapping.
    """
    st.header("Market Regime Map Engine")
    st.caption("Qwen-powered mapping of all active market regimes.")

    data = _collect_market_regime_map_data()
    if not data:
        st.info("No data available for regime-map analysis.")
        return

    analysis = _generate_market_regime_map_analysis(data)

    themed_card_container()
    st.markdown(f"""
    ## Market Regime Map Analysis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Market regime-map analysis complete.")
# ------------- CHUNK 92: MARKET ENVIRONMENT SUMMARY ENGINE -------------

def _collect_market_environment_summary_data():
    """
    Collect all macro-environment signals from previous modules:
    - regime signals
    - phase signals
    - drift signals
    - momentum signals
    - overextension signals
    - exhaustion signals
    - shock signals
    - instability signals
    - turbulence signals
    - volatility cycle signals
    - expansion/compression signals
    - dominant regime
    - regime overlaps
    - regime conflicts
    """
    def safe_get(key, default=0):
        return st.session_state.get(key, default)

    summary = {
        # Regime-level signals
        "regime_dominant": safe_get("dominant_regime"),
        "regime_overlaps": safe_get("regime_overlaps", []),
        "regime_conflicts": safe_get("regime_conflicts", []),

        # Phase-level signals
        "volatility": safe_get("volatility"),
        "parlay_risk": safe_get("parlay_risk"),

        # Expansion / Compression
        "expansion": safe_get("edge_expansion"),
        "compression": safe_get("edge_compression"),

        # Drift / Momentum
        "drift": safe_get("edge_drift"),
        "momentum": safe_get("edge_momentum"),

        # Overextension / Exhaustion
        "overextension": safe_get("edge_overextension"),
        "exhaustion": safe_get("edge_exhaustion"),

        # Shock / Instability / Turbulence
        "shock": safe_get("shock_volatility"),
        "instability": safe_get("edge_instability"),
        "turbulence": safe_get("edge_turbulence"),

        # Volatility cycles
        "volatility_expansion": safe_get("volatility_expansion"),
        "volatility_compression": safe_get("volatility_compression"),
        "volatility_wave_strength": safe_get("volatility_wave_strength"),
        "volatility_wave_direction": safe_get("volatility_wave_direction"),
    }

    return summary


def _qwen_environment_summary_prompt(data):
    """
    Build a structured prompt for Qwen to generate a unified macro-environment summary.
    """
    prompt = f"""
You are an elite sports betting macro-environment analyst.

Analyze the following FULL MACRO ENVIRONMENT DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Provide a unified macro-environment summary.
2. Identify the dominant macro forces shaping today's environment.
3. Identify environment-driven risks (macro traps, instability pockets, regime conflicts).
4. Identify environment-driven opportunities (alignment edges, macro synergy).
5. Provide 3–6 actionable macro-environment strategy recommendations.
6. Keep output under 300 words.
7. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_environment_summary(data):
    """
    Call Qwen to generate the macro-environment summary.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_environment_summary_prompt(data)
    response = _call_qwen(prompt)
    return response or "No macro-environment summary generated."


def render_market_environment_summary_engine():
    """
    Full UI for Qwen-powered macro-environment summary.
    """
    st.header("Market Environment Summary Engine")
    st.caption("Qwen-powered unified macro-environment interpretation.")

    data = _collect_market_environment_summary_data()
    if not data:
        st.info("No data available for macro-environment summary.")
        return

    analysis = _generate_market_environment_summary(data)

    themed_card_container()
    st.markdown(f"""
    ## Macro Environment Summary

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Macro environment summary complete.")
# ------------- CHUNK 93: MARKET ENVIRONMENT FORECAST ENGINE -------------

def _collect_market_environment_forecast_data():
    """
    Collect all macro signals needed for forecasting:
    - regime strength trends
    - volatility cycle direction
    - drift direction & acceleration
    - momentum direction & acceleration
    - expansion/compression trajectory
    - overextension/exhaustion trajectory
    - shock/instability/turbulence trajectory
    - dominant regime trajectory
    - historical macro patterns
    """
    def safe_get(key, default=0):
        return st.session_state.get(key, default)

    forecast = {
        # Regime-level signals
        "dominant_regime": safe_get("dominant_regime"),
        "regime_overlaps": safe_get("regime_overlaps", []),
        "regime_conflicts": safe_get("regime_conflicts", []),

        # Drift / Momentum
        "drift": safe_get("edge_drift"),
        "momentum": safe_get("edge_momentum"),
        "drift_acceleration": safe_get("conf_acceleration", 0),
        "momentum_acceleration": safe_get("edge_acceleration", 0),

        # Expansion / Compression
        "expansion": safe_get("edge_expansion"),
        "compression": safe_get("edge_compression"),

        # Overextension / Exhaustion
        "overextension": safe_get("edge_overextension"),
        "exhaustion": safe_get("edge_exhaustion"),

        # Shock / Instability / Turbulence
        "shock": safe_get("shock_volatility"),
        "instability": safe_get("edge_instability"),
        "turbulence": safe_get("edge_turbulence"),

        # Volatility cycles
        "volatility_expansion": safe_get("volatility_expansion"),
        "volatility_compression": safe_get("volatility_compression"),
        "volatility_wave_strength": safe_get("volatility_wave_strength"),
        "volatility_wave_direction": safe_get("volatility_wave_direction"),

        # Historical patterns (if available)
        "historical_vol_cycles": safe_get("historical_volatility_cycles", []),
        "historical_drift": safe_get("historical_conf_drift", []),
        "historical_momentum": safe_get("historical_edge_momentum", []),
    }

    return forecast


def _qwen_environment_forecast_prompt(data):
    """
    Build a structured prompt for Qwen to generate a macro-environment forecast.
    """
    prompt = f"""
You are an elite sports betting macro-forecasting analyst.

Analyze the following FULL MACRO FORECAST DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Forecast the direction of the macro environment over the next cycle.
2. Identify which macro forces are strengthening vs weakening.
3. Predict volatility cycle continuation or reversal.
4. Predict drift/momentum continuation or reversal.
5. Highlight forward-looking macro risks (shock risk, instability risk, exhaustion risk).
6. Highlight forward-looking macro opportunities (alignment edges, regime synergy, cycle setups).
7. Provide 3–6 actionable macro-forecast strategy recommendations.
8. Keep output under 320 words.
9. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_environment_forecast(data):
    """
    Call Qwen to generate the macro-environment forecast.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_environment_forecast_prompt(data)
    response = _call_qwen(prompt)
    return response or "No macro-environment forecast generated."


def render_market_environment_forecast_engine():
    """
    Full UI for Qwen-powered macro-environment forecasting.
    """
    st.header("Market Environment Forecast Engine")
    st.caption("Qwen-powered forecasting of macro-environment direction and regime trajectory.")

    data = _collect_market_environment_forecast_data()
    if not data:
        st.info("No data available for macro-environment forecasting.")
        return

    analysis = _generate_market_environment_forecast(data)

    themed_card_container()
    st.markdown(f"""
    ## Macro Environment Forecast

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Macro environment forecast complete.")
# ------------- CHUNK 94: MARKET ENVIRONMENT CONFIDENCE ENGINE -------------

def _collect_market_environment_confidence_data():
    """
    Collect all macro signals and compute confidence scores:
    - regime confidence
    - volatility cycle confidence
    - drift/momentum confidence
    - expansion/compression confidence
    - overextension/exhaustion confidence
    - shock/instability/turbulence confidence
    - macro forecast confidence
    - macro environment confidence
    """

    def safe_get(key, default=0):
        return st.session_state.get(key, default)

    # Pull all macro signals
    data = {
        "drift": safe_get("edge_drift"),
        "momentum": safe_get("edge_momentum"),
        "drift_accel": safe_get("drift_acceleration", 0),
        "momentum_accel": safe_get("momentum_acceleration", 0),

        "expansion": safe_get("edge_expansion"),
        "compression": safe_get("edge_compression"),

        "overextension": safe_get("edge_overextension"),
        "exhaustion": safe_get("edge_exhaustion"),

        "shock": safe_get("shock_volatility"),
        "instability": safe_get("edge_instability"),
        "turbulence": safe_get("edge_turbulence"),

        "vol_expansion": safe_get("volatility_expansion"),
        "vol_compression": safe_get("volatility_compression"),
        "vol_wave_strength": safe_get("volatility_wave_strength"),
        "vol_wave_direction": safe_get("volatility_wave_direction"),

        "dominant_regime": safe_get("dominant_regime"),
        "regime_overlaps": safe_get("regime_overlaps", []),
        "regime_conflicts": safe_get("regime_conflicts", []),
    }

    # Confidence scoring logic
    # Higher variance → lower confidence
    # Stronger alignment → higher confidence
    # More conflicts → lower confidence

    def normalize(x):
        return float(1 / (1 + abs(x)))

    regime_conf = normalize(len(data["regime_conflicts"])) * 0.5 + \
                  normalize(len(data["regime_overlaps"])) * 0.5

    vol_cycle_conf = normalize(data["vol_wave_strength"])

    drift_conf = normalize(data["drift"]) * 0.5 + normalize(data["drift_accel"]) * 0.5
    momentum_conf = normalize(data["momentum"]) * 0.5 + normalize(data["momentum_accel"]) * 0.5

    expansion_conf = normalize(data["expansion"])
    compression_conf = normalize(data["compression"])

    overext_conf = normalize(data["overextension"])
    exhaustion_conf = normalize(data["exhaustion"])

    shock_conf = normalize(data["shock"])
    instability_conf = normalize(data["instability"])
    turbulence_conf = normalize(data["turbulence"])

    # Macro environment confidence = weighted blend
    macro_env_conf = float((
        regime_conf +
        vol_cycle_conf +
        drift_conf +
        momentum_conf +
        expansion_conf +
        compression_conf +
        overext_conf +
        exhaustion_conf +
        shock_conf +
        instability_conf +
        turbulence_conf
    ) / 11)

    # Macro forecast confidence = forward‑looking blend
    macro_forecast_conf = float((
        drift_conf +
        momentum_conf +
        vol_cycle_conf +
        instability_conf +
        turbulence_conf
    ) / 5)

    return {
        "regime_confidence": regime_conf,
        "volatility_cycle_confidence": vol_cycle_conf,
        "drift_confidence": drift_conf,
        "momentum_confidence": momentum_conf,
        "expansion_confidence": expansion_conf,
        "compression_confidence": compression_conf,
        "overextension_confidence": overext_conf,
        "exhaustion_confidence": exhaustion_conf,
        "shock_confidence": shock_conf,
        "instability_confidence": instability_conf,
        "turbulence_confidence": turbulence_conf,
        "macro_environment_confidence": macro_env_conf,
        "macro_forecast_confidence": macro_forecast_conf,
        "raw_data": data,
    }


def _qwen_environment_confidence_prompt(data):
    """
    Build a structured prompt for Qwen to analyze macro confidence.
    """
    prompt = f"""
You are an elite sports betting macro-confidence analyst.

Analyze the following MACRO CONFIDENCE DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Score confidence in the macro environment.
2. Score confidence in the macro forecast.
3. Identify which macro signals have high vs low confidence.
4. Highlight confidence-driven risks (low-confidence traps, unstable signals).
5. Highlight confidence-driven opportunities (high-confidence alignment edges).
6. Provide 3–6 actionable confidence-weighted strategy recommendations.
7. Keep output under 300 words.
8. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_environment_confidence(data):
    """
    Call Qwen to generate macro-confidence insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_environment_confidence_prompt(data)
    response = _call_qwen(prompt)
    return response or "No macro-confidence analysis generated."


def render_market_environment_confidence_engine():
    """
    Full UI for Qwen-powered macro-confidence scoring.
    """
    st.header("Market Environment Confidence Engine")
    st.caption("Qwen-powered scoring of macro-environment and macro-forecast confidence.")

    data = _collect_market_environment_confidence_data()
    if not data:
        st.info("No data available for macro-confidence scoring.")
        return

    analysis = _generate_market_environment_confidence(data)

    themed_card_container()
    st.markdown(f"""
    ## Macro Environment Confidence

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Macro environment confidence scoring complete.")
# ------------- CHUNK 95: MARKET ENVIRONMENT RISK ENGINE -------------

def _collect_market_environment_risk_data():
    """
    Collect all macro signals and compute macro risk scores:
    - regime conflict risk
    - volatility risk
    - drift/momentum risk
    - expansion/compression risk
    - overextension/exhaustion risk
    - shock/instability/turbulence risk
    - volatility cycle risk
    - macro risk clusters
    - macro environment risk score
    """

    def safe_get(key, default=0):
        return st.session_state.get(key, default)

    # Pull macro signals
    data = {
        "drift": safe_get("edge_drift"),
        "momentum": safe_get("edge_momentum"),
        "drift_accel": safe_get("drift_acceleration", 0),
        "momentum_accel": safe_get("momentum_acceleration", 0),

        "expansion": safe_get("edge_expansion"),
        "compression": safe_get("edge_compression"),

        "overextension": safe_get("edge_overextension"),
        "exhaustion": safe_get("edge_exhaustion"),

        "shock": safe_get("shock_volatility"),
        "instability": safe_get("edge_instability"),
        "turbulence": safe_get("edge_turbulence"),

        "vol_expansion": safe_get("volatility_expansion"),
        "vol_compression": safe_get("volatility_compression"),
        "vol_wave_strength": safe_get("volatility_wave_strength"),
        "vol_wave_direction": safe_get("volatility_wave_direction"),

        "regime_overlaps": safe_get("regime_overlaps", []),
        "regime_conflicts": safe_get("regime_conflicts", []),
    }

    # Risk scoring logic
    # Higher variance → higher risk
    # More conflicts → higher risk
    # Stronger instability → higher risk

    def risk_scale(x):
        return float(abs(x) / (1 + abs(x)))

    regime_conflict_risk = float(len(data["regime_conflicts"])) * 0.8
    regime_overlap_risk = float(len(data["regime_overlaps"])) * 0.4

    volatility_risk = risk_scale(data["vol_wave_strength"])

    drift_risk = risk_scale(data["drift"]) + risk_scale(data["drift_accel"])
    momentum_risk = risk_scale(data["momentum"]) + risk_scale(data["momentum_accel"])

    expansion_risk = risk_scale(data["expansion"])
    compression_risk = risk_scale(data["compression"])

    overextension_risk = risk_scale(data["overextension"])
    exhaustion_risk = risk_scale(data["exhaustion"])

    shock_risk = risk_scale(data["shock"])
    instability_risk = risk_scale(data["instability"])
    turbulence_risk = risk_scale(data["turbulence"])

    # Macro risk clusters
    clusters = []
    if shock_risk > 0.5 and turbulence_risk > 0.5:
        clusters.append("Shock + Turbulence Cluster")
    if instability_risk > 0.5 and compression_risk > 0.5:
        clusters.append("Instability + Compression Cluster")
    if overextension_risk > 0.5 and exhaustion_risk > 0.5:
        clusters.append("Overextension + Exhaustion Cluster")
    if drift_risk > 0.5 and momentum_risk > 0.5:
        clusters.append("Directional Risk Cluster")

    # Macro environment risk score
    macro_risk_score = float((
        regime_conflict_risk +
        regime_overlap_risk +
        volatility_risk +
        drift_risk +
        momentum_risk +
        expansion_risk +
        compression_risk +
        overextension_risk +
        exhaustion_risk +
        shock_risk +
        instability_risk +
        turbulence_risk
    ) / 12)

    return {
        "regime_conflict_risk": regime_conflict_risk,
        "regime_overlap_risk": regime_overlap_risk,
        "volatility_risk": volatility_risk,
        "drift_risk": drift_risk,
        "momentum_risk": momentum_risk,
        "expansion_risk": expansion_risk,
        "compression_risk": compression_risk,
        "overextension_risk": overextension_risk,
        "exhaustion_risk": exhaustion_risk,
        "shock_risk": shock_risk,
        "instability_risk": instability_risk,
        "turbulence_risk": turbulence_risk,
        "macro_risk_score": macro_risk_score,
        "macro_risk_clusters": clusters,
        "raw_data": data,
    }


def _qwen_environment_risk_prompt(data):
    """
    Build a structured prompt for Qwen to analyze macro risk.
    """
    prompt = f"""
You are an elite sports betting macro-risk analyst.

Analyze the following MACRO RISK DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Score macro-environment risk.
2. Identify macro risk clusters.
3. Identify high-risk vs low-risk macro conditions.
4. Highlight risk-driven traps (shock traps, instability traps, conflict traps).
5. Highlight risk-driven opportunities (risk fades, risk hedges, risk reversals).
6. Provide 3–6 actionable macro-risk strategy recommendations.
7. Keep output under 300 words.
8. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_environment_risk(data):
    """
    Call Qwen to generate macro-risk insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_environment_risk_prompt(data)
    response = _call_qwen(prompt)
    return response or "No macro-risk analysis generated."


def render_market_environment_risk_engine():
    """
    Full UI for Qwen-powered macro-risk scoring.
    """
    st.header("Market Environment Risk Engine")
    st.caption("Qwen-powered scoring of macro-environment risk and risk clusters.")

    data = _collect_market_environment_risk_data()
    if not data:
        st.info("No data available for macro-risk scoring.")
        return

    analysis = _generate_market_environment_risk(data)

    themed_card_container()
    st.markdown(f"""
    ## Macro Environment Risk

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Macro environment risk scoring complete.")
# ------------- CHUNK 96: MARKET ENVIRONMENT OPPORTUNITY ENGINE -------------

def _collect_market_environment_opportunity_data():
    """
    Collect all macro signals and compute macro opportunity scores:
    - drift/momentum opportunity
    - expansion/compression opportunity
    - overextension/exhaustion opportunity
    - volatility cycle opportunity
    - shock/instability/turbulence opportunity
    - regime alignment opportunity
    - macro opportunity clusters
    - macro environment opportunity score
    """

    def safe_get(key, default=0):
        return st.session_state.get(key, default)

    # Pull macro signals
    data = {
        "drift": safe_get("edge_drift"),
        "momentum": safe_get("edge_momentum"),
        "drift_accel": safe_get("drift_acceleration", 0),
        "momentum_accel": safe_get("momentum_acceleration", 0),

        "expansion": safe_get("edge_expansion"),
        "compression": safe_get("edge_compression"),

        "overextension": safe_get("edge_overextension"),
        "exhaustion": safe_get("edge_exhaustion"),

        "shock": safe_get("shock_volatility"),
        "instability": safe_get("edge_instability"),
        "turbulence": safe_get("edge_turbulence"),

        "vol_expansion": safe_get("volatility_expansion"),
        "vol_compression": safe_get("volatility_compression"),
        "vol_wave_strength": safe_get("volatility_wave_strength"),
        "vol_wave_direction": safe_get("volatility_wave_direction"),

        "regime_overlaps": safe_get("regime_overlaps", []),
        "dominant_regime": safe_get("dominant_regime"),
    }

    # Opportunity scoring logic
    # Strong alignment → high opportunity
    # Strong directional acceleration → high opportunity
    # Compression → breakout opportunity
    # Exhaustion → reversal opportunity
    # Shock → volatility fade opportunity

    def opp_scale(x):
        return float(abs(x) / (1 + abs(x)))

    drift_opp = opp_scale(data["drift"]) + opp_scale(data["drift_accel"])
    momentum_opp = opp_scale(data["momentum"]) + opp_scale(data["momentum_accel"])

    expansion_opp = opp_scale(data["expansion"])
    compression_opp = opp_scale(data["compression"])

    overextension_opp = opp_scale(data["overextension"])
    exhaustion_opp = opp_scale(data["exhaustion"])

    shock_opp = opp_scale(data["shock"])
    instability_opp = opp_scale(data["instability"])
    turbulence_opp = opp_scale(data["turbulence"])

    vol_cycle_opp = opp_scale(data["vol_wave_strength"])

    regime_alignment_opp = float(len(data["regime_overlaps"])) * 0.6

    # Macro opportunity clusters
    clusters = []
    if compression_opp > 0.5 and momentum_opp > 0.5:
        clusters.append("Compression Breakout Opportunity Cluster")
    if exhaustion_opp > 0.5 and drift_opp > 0.5:
        clusters.append("Exhaustion Reversal Opportunity Cluster")
    if shock_opp > 0.5 and volatility_opp := vol_cycle_opp > 0.5:
        clusters.append("Shock Fade Opportunity Cluster")
    if regime_alignment_opp > 0.5 and momentum_opp > 0.5:
        clusters.append("Regime Alignment Opportunity Cluster")

    # Macro environment opportunity score
    macro_opp_score = float((
        drift_opp +
        momentum_opp +
        expansion_opp +
        compression_opp +
        overextension_opp +
        exhaustion_opp +
        shock_opp +
        instability_opp +
        turbulence_opp +
        vol_cycle_opp +
        regime_alignment_opp
    ) / 11)

    return {
        "drift_opportunity": drift_opp,
        "momentum_opportunity": momentum_opp,
        "expansion_opportunity": expansion_opp,
        "compression_opportunity": compression_opp,
        "overextension_opportunity": overextension_opp,
        "exhaustion_opportunity": exhaustion_opp,
        "shock_opportunity": shock_opp,
        "instability_opportunity": instability_opp,
        "turbulence_opportunity": turbulence_opp,
        "volatility_cycle_opportunity": vol_cycle_opp,
        "regime_alignment_opportunity": regime_alignment_opp,
        "macro_opportunity_score": macro_opp_score,
        "macro_opportunity_clusters": clusters,
        "raw_data": data,
    }


def _qwen_environment_opportunity_prompt(data):
    """
    Build a structured prompt for Qwen to analyze macro opportunity.
    """
    prompt = f"""
You are an elite sports betting macro-opportunity analyst.

Analyze the following MACRO OPPORTUNITY DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Score macro-environment opportunity.
2. Identify macro opportunity clusters.
3. Identify high-opportunity vs low-opportunity macro conditions.
4. Highlight opportunity-driven setups (breakouts, reversals, alignment edges).
5. Highlight opportunity-driven risks (false breakouts, unstable setups).
6. Provide 3–6 actionable macro-opportunity strategy recommendations.
7. Keep output under 300 words.
8. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_environment_opportunity(data):
    """
    Call Qwen to generate macro-opportunity insights.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_environment_opportunity_prompt(data)
    response = _call_qwen(prompt)
    return response or "No macro-opportunity analysis generated."


def render_market_environment_opportunity_engine():
    """
    Full UI for Qwen-powered macro-opportunity scoring.
    """
    st.header("Market Environment Opportunity Engine")
    st.caption("Qwen-powered scoring of macro-environment opportunity and opportunity clusters.")

    data = _collect_market_environment_opportunity_data()
    if not data:
        st.info("No data available for macro-opportunity scoring.")
        return

    analysis = _generate_market_environment_opportunity(data)

    themed_card_container()
    st.markdown(f"""
    ## Macro Environment Opportunity

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Macro environment opportunity scoring complete.")
# ------------- CHUNK 97: MARKET ENVIRONMENT SYNTHESIS ENGINE -------------

def _collect_market_environment_synthesis_data():
    """
    Collect all macro components for synthesis:
    - macro risk score
    - macro opportunity score
    - macro confidence score
    - macro forecast confidence
    - dominant regime
    - regime overlaps
    - regime conflicts
    - volatility cycle direction & strength
    - drift/momentum signals
    - overextension/exhaustion signals
    - shock/instability/turbulence signals
    """

    def safe_get(key, default=0):
        return st.session_state.get(key, default)

    synthesis = {
        # Core macro scores
        "macro_risk_score": safe_get("macro_risk_score"),
        "macro_opportunity_score": safe_get("macro_opportunity_score"),
        "macro_environment_confidence": safe_get("macro_environment_confidence"),
        "macro_forecast_confidence": safe_get("macro_forecast_confidence"),

        # Regime structure
        "dominant_regime": safe_get("dominant_regime"),
        "regime_overlaps": safe_get("regime_overlaps", []),
        "regime_conflicts": safe_get("regime_conflicts", []),

        # Drift / Momentum
        "drift": safe_get("edge_drift"),
        "momentum": safe_get("edge_momentum"),

        # Expansion / Compression
        "expansion": safe_get("edge_expansion"),
        "compression": safe_get("edge_compression"),

        # Overextension / Exhaustion
        "overextension": safe_get("edge_overextension"),
        "exhaustion": safe_get("edge_exhaustion"),

        # Shock / Instability / Turbulence
        "shock": safe_get("shock_volatility"),
        "instability": safe_get("edge_instability"),
        "turbulence": safe_get("edge_turbulence"),

        # Volatility cycles
        "vol_wave_strength": safe_get("volatility_wave_strength"),
        "vol_wave_direction": safe_get("volatility_wave_direction"),
    }

    # Compute synthesis score
    # Opportunity - Risk, weighted by confidence
    opp = synthesis["macro_opportunity_score"]
    risk = synthesis["macro_risk_score"]
    conf = synthesis["macro_environment_confidence"]

    synthesis_score = float((opp - risk) * conf)

    synthesis["macro_synthesis_score"] = synthesis_score

    return synthesis


def _qwen_environment_synthesis_prompt(data):
    """
    Build a structured prompt for Qwen to generate a macro synthesis read.
    """
    prompt = f"""
You are an elite sports betting macro-synthesis analyst.

Analyze the following FULL MACRO SYNTHESIS DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Provide a unified macro-synthesis read combining risk, opportunity, confidence, and forecast.
2. Identify the dominant macro forces shaping the synthesis.
3. Identify synthesis-driven risks (macro traps, conflict zones, instability pockets).
4. Identify synthesis-driven opportunities (alignment edges, synergy setups, cycle plays).
5. Provide 4–8 actionable synthesis-weighted strategy recommendations.
6. Keep output under 350 words.
7. Tone: analytical, concise, high-signal.
"""
    return prompt


def _generate_market_environment_synthesis(data):
    """
    Call Qwen to generate the macro synthesis interpretation.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_environment_synthesis_prompt(data)
    response = _call_qwen(prompt)
    return response or "No macro-synthesis analysis generated."


def render_market_environment_synthesis_engine():
    """
    Full UI for Qwen-powered macro synthesis.
    """
    st.header("Market Environment Synthesis Engine")
    st.caption("Qwen-powered synthesis of macro risk, opportunity, confidence, and forecast.")

    data = _collect_market_environment_synthesis_data()
    if not data:
        st.info("No data available for macro-synthesis analysis.")
        return

    analysis = _generate_market_environment_synthesis(data)

    themed_card_container()
    st.markdown(f"""
    ## Macro Environment Synthesis

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Macro environment synthesis complete.")
# ------------- CHUNK 98: MARKET ENVIRONMENT NARRATIVE ENGINE -------------

def _collect_market_environment_narrative_data():
    """
    Collect all macro components needed to generate a narrative:
    - macro synthesis score
    - macro risk score
    - macro opportunity score
    - macro confidence score
    - macro forecast confidence
    - dominant regime
    - regime overlaps & conflicts
    - drift/momentum signals
    - expansion/compression signals
    - overextension/exhaustion signals
    - shock/instability/turbulence signals
    - volatility cycle direction & strength
    """

    def safe_get(key, default=0):
        return st.session_state.get(key, default)

    narrative = {
        "macro_synthesis_score": safe_get("macro_synthesis_score"),
        "macro_risk_score": safe_get("macro_risk_score"),
        "macro_opportunity_score": safe_get("macro_opportunity_score"),
        "macro_environment_confidence": safe_get("macro_environment_confidence"),
        "macro_forecast_confidence": safe_get("macro_forecast_confidence"),

        "dominant_regime": safe_get("dominant_regime"),
        "regime_overlaps": safe_get("regime_overlaps", []),
        "regime_conflicts": safe_get("regime_conflicts", []),

        "drift": safe_get("edge_drift"),
        "momentum": safe_get("edge_momentum"),

        "expansion": safe_get("edge_expansion"),
        "compression": safe_get("edge_compression"),

        "overextension": safe_get("edge_overextension"),
        "exhaustion": safe_get("edge_exhaustion"),

        "shock": safe_get("shock_volatility"),
        "instability": safe_get("edge_instability"),
        "turbulence": safe_get("edge_turbulence"),

        "vol_wave_strength": safe_get("volatility_wave_strength"),
        "vol_wave_direction": safe_get("volatility_wave_direction"),
    }

    return narrative


def _qwen_environment_narrative_prompt(data):
    """
    Build a structured prompt for Qwen to generate a macro narrative.
    """
    prompt = f"""
You are an elite sports betting macro-narrative analyst.

Write a high-signal MACRO ENVIRONMENT NARRATIVE using the following data:

{json.dumps(data, indent=2)}

TASKS:
1. Convert the macro synthesis into a coherent narrative storyline.
2. Describe the current macro environment in narrative form.
3. Describe the forward macro environment (forecast) in narrative form.
4. Highlight narrative-driven risks (macro traps, instability pockets, regime conflicts).
5. Highlight narrative-driven opportunities (alignment edges, cycle setups, synergy plays).
6. Provide 4–8 narrative-aligned strategy recommendations.
7. Tone: professional macro analyst, concise, high-signal, narrative-driven.
8. Keep output under 380 words.
"""
    return prompt


def _generate_market_environment_narrative(data):
    """
    Call Qwen to generate the macro narrative.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_environment_narrative_prompt(data)
    response = _call_qwen(prompt)
    return response or "No macro narrative generated."


def render_market_environment_narrative_engine():
    """
    Full UI for Qwen-powered macro narrative generation.
    """
    st.header("Market Environment Narrative Engine")
    st.caption("Qwen-powered macro narrative generator.")

    data = _collect_market_environment_narrative_data()
    if not data:
        st.info("No data available for macro narrative generation.")
        return

    analysis = _generate_market_environment_narrative(data)

    themed_card_container()
    st.markdown(f"""
    ## Macro Environment Narrative

    **AI Interpretation:**  
    {analysis}
    """)

    st.success("Macro environment narrative generation complete.")
# ------------- CHUNK 99: MARKET ENVIRONMENT DASHBOARD ENGINE -------------

def _collect_market_environment_dashboard_data():
    """
    Collect all macro components for the unified dashboard:
    - synthesis
    - narrative
    - risk
    - opportunity
    - confidence
    - forecast confidence
    - regimes
    - cycles
    - drift/momentum
    - instability/shock/turbulence
    """

    def safe_get(key, default=None):
        return st.session_state.get(key, default)

    dashboard = {
        "macro_synthesis_score": safe_get("macro_synthesis_score"),
        "macro_risk_score": safe_get("macro_risk_score"),
        "macro_opportunity_score": safe_get("macro_opportunity_score"),
        "macro_environment_confidence": safe_get("macro_environment_confidence"),
        "macro_forecast_confidence": safe_get("macro_forecast_confidence"),

        "dominant_regime": safe_get("dominant_regime"),
        "regime_overlaps": safe_get("regime_overlaps", []),
        "regime_conflicts": safe_get("regime_conflicts", []),

        "vol_wave_strength": safe_get("volatility_wave_strength"),
        "vol_wave_direction": safe_get("volatility_wave_direction"),

        "drift": safe_get("edge_drift"),
        "momentum": safe_get("edge_momentum"),

        "shock": safe_get("shock_volatility"),
        "instability": safe_get("edge_instability"),
        "turbulence": safe_get("edge_turbulence"),

        "expansion": safe_get("edge_expansion"),
        "compression": safe_get("edge_compression"),

        # Narrative (generated in Chunk 98)
        "macro_narrative": safe_get("macro_narrative_text", None),
    }

    return dashboard


def render_macro_dashboard_card(title, value, description=None):
    """
    Helper to render a clean macro dashboard card.
    """
    themed_card_container()
    st.markdown(f"""
    ### **{title}**
    **Value:** `{value}`  
    {description or ""}
    """)


def render_market_environment_dashboard_engine():
    """
    Full UI for the unified macro dashboard.
    """
    st.header("Unified Macro Environment Dashboard")
    st.caption("Top-level macro panel combining synthesis, narrative, risk, opportunity, confidence, and forecast.")

    data = _collect_market_environment_dashboard_data()
    if not data:
        st.info("No macro dashboard data available.")
        return

    # --- SYNTHESIS PANEL ---
    render_macro_dashboard_card(
        "Macro Synthesis Score",
        data["macro_synthesis_score"],
        "Weighted blend of opportunity, risk, and confidence."
    )

    # --- RISK PANEL ---
    render_macro_dashboard_card(
        "Macro Risk Score",
        data["macro_risk_score"],
        "Higher = more dangerous macro environment."
    )

    # --- OPPORTUNITY PANEL ---
    render_macro_dashboard_card(
        "Macro Opportunity Score",
        data["macro_opportunity_score"],
        "Higher = more upside potential in the macro environment."
    )

    # --- CONFIDENCE PANEL ---
    render_macro_dashboard_card(
        "Macro Environment Confidence",
        data["macro_environment_confidence"],
        "How reliable the macro read is."
    )

    render_macro_dashboard_card(
        "Macro Forecast Confidence",
        data["macro_forecast_confidence"],
        "How reliable the forward macro prediction is."
    )

    # --- REGIME PANEL ---
    render_macro_dashboard_card(
        "Dominant Regime",
        data["dominant_regime"],
        "The strongest macro force shaping today's environment."
    )

    render_macro_dashboard_card(
        "Regime Overlaps",
        ", ".join(data["regime_overlaps"]) if data["regime_overlaps"] else "None",
        "Multiple regimes active simultaneously."
    )

    render_macro_dashboard_card(
        "Regime Conflicts",
        ", ".join(data["regime_conflicts"]) if data["regime_conflicts"] else "None",
        "Regimes pushing in opposite directions."
    )

    # --- VOLATILITY CYCLE PANEL ---
    render_macro_dashboard_card(
        "Volatility Wave Direction",
        data["vol_wave_direction"],
        "Expansion vs compression."
    )

    render_macro_dashboard_card(
        "Volatility Wave Strength",
        data["vol_wave_strength"],
        "Strength of the volatility cycle."
    )

    # --- INSTABILITY PANEL ---
    render_macro_dashboard_card(
        "Shock Level",
        data["shock"],
        "Shock-driven volatility."
    )

    render_macro_dashboard_card(
        "Instability Level",
        data["instability"],
        "Erratic movement in edges/confidence."
    )

    render_macro_dashboard_card(
        "Turbulence Level",
        data["turbulence"],
        "Wild swings and variance whiplash."
    )

    # --- EXPANSION / COMPRESSION PANEL ---
    render_macro_dashboard_card(
        "Expansion Level",
        data["expansion"],
        "Variance widening."
    )

    render_macro_dashboard_card(
        "Compression Level",
        data["compression"],
        "Variance tightening."
    )

    # --- NARRATIVE PANEL ---
    if data["macro_narrative"]:
        themed_card_container()
        st.markdown(f"""
        ## Macro Narrative  
        {data["macro_narrative"]}
        """)
    else:
        st.info("Macro narrative not yet generated.")

    st.success("Unified macro dashboard loaded.")
# ------------- CHUNK 100: MARKET ENVIRONMENT MASTER ENGINE -------------

def _collect_market_environment_master_data():
    """
    Collect ALL macro components for the master engine:
    - synthesis score
    - risk score
    - opportunity score
    - environment confidence
    - forecast confidence
    - dominant regime
    - regime overlaps & conflicts
    - volatility cycle direction & strength
    - drift/momentum
    - expansion/compression
    - overextension/exhaustion
    - shock/instability/turbulence
    - macro narrative (if available)
    """

    def safe_get(key, default=None):
        return st.session_state.get(key, default)

    master = {
        "macro_synthesis_score": safe_get("macro_synthesis_score"),
        "macro_risk_score": safe_get("macro_risk_score"),
        "macro_opportunity_score": safe_get("macro_opportunity_score"),
        "macro_environment_confidence": safe_get("macro_environment_confidence"),
        "macro_forecast_confidence": safe_get("macro_forecast_confidence"),

        "dominant_regime": safe_get("dominant_regime"),
        "regime_overlaps": safe_get("regime_overlaps", []),
        "regime_conflicts": safe_get("regime_conflicts", []),

        "vol_wave_strength": safe_get("volatility_wave_strength"),
        "vol_wave_direction": safe_get("volatility_wave_direction"),

        "drift": safe_get("edge_drift"),
        "momentum": safe_get("edge_momentum"),

        "expansion": safe_get("edge_expansion"),
        "compression": safe_get("edge_compression"),

        "overextension": safe_get("edge_overextension"),
        "exhaustion": safe_get("edge_exhaustion"),

        "shock": safe_get("shock_volatility"),
        "instability": safe_get("edge_instability"),
        "turbulence": safe_get("edge_turbulence"),

        "macro_narrative": safe_get("macro_narrative_text", None),
    }

    # MASTER STATE CLASSIFICATION
    # Uses synthesis score + risk + opportunity + confidence

    syn = master["macro_synthesis_score"]
    risk = master["macro_risk_score"]
    opp = master["macro_opportunity_score"]
    conf = master["macro_environment_confidence"]

    if syn is None:
        master_state = "Unknown"
    else:
        if syn > 0.35:
            master_state = "Bullish Macro Environment"
        elif syn > 0.1:
            master_state = "Mildly Bullish Macro Environment"
        elif syn > -0.1:
            master_state = "Neutral Macro Environment"
        elif syn > -0.35:
            master_state = "Mildly Bearish Macro Environment"
        else:
            master_state = "Bearish Macro Environment"

    master["master_state"] = master_state

    return master


def _qwen_environment_master_prompt(data):
    """
    Build a structured prompt for Qwen to generate the master macro interpretation.
    """
    prompt = f"""
You are an elite sports betting macro-master analyst.

Analyze the following FULL MACRO BRAIN DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Provide a MASTER-LEVEL macro interpretation.
2. Classify the macro environment into a master state (bullish, neutral, bearish).
3. Identify the strongest macro forces driving the master state.
4. Identify master-level risks (macro traps, regime conflicts, instability pockets).
5. Identify master-level opportunities (alignment edges, synergy setups, cycle plays).
6. Provide 5–10 MASTER-LEVEL strategy recommendations.
7. Tone: elite macro analyst, concise, high-signal, authoritative.
8. Keep output under 420 words.
"""
    return prompt


def _generate_market_environment_master(data):
    """
    Call Qwen to generate the master macro interpretation.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_environment_master_prompt(data)
    response = _call_qwen(prompt)
    return response or "No master macro analysis generated."


def render_market_environment_master_engine():
    """
    Full UI for Qwen-powered master macro engine.
    """
    st.header("Market Environment Master Engine")
    st.caption("Qwen-powered full macro brain integration layer.")

    data = _collect_market_environment_master_data()
    if not data:
        st.info("No data available for master macro analysis.")
        return

    analysis = _generate_market_environment_master(data)

    # --- MASTER STATE PANEL ---
    themed_card_container()
    st.markdown(f"""
    ## Master Macro State  
    **{data['master_state']}**
    """)

    # --- MASTER INTERPRETATION ---
    themed_card_container()
    st.markdown(f"""
    ## Master Macro Interpretation  
    {analysis}
    """)

    st.success("Master macro engine complete.")
# ------------- CHUNK 101: MARKET ENVIRONMENT META-ENGINE -------------

def _collect_market_environment_meta_data():
    """
    Collect all components needed for the META-level engine:
    - master macro state
    - synthesis score
    - risk score
    - opportunity score
    - environment confidence
    - forecast confidence
    - regime structure
    - volatility cycles
    - instability/shock/turbulence
    - meta contradictions
    - meta alignments
    """

    def safe_get(key, default=None):
        return st.session_state.get(key, default)

    meta = {
        "master_state": safe_get("master_state"),
        "macro_synthesis_score": safe_get("macro_synthesis_score"),
        "macro_risk_score": safe_get("macro_risk_score"),
        "macro_opportunity_score": safe_get("macro_opportunity_score"),
        "macro_environment_confidence": safe_get("macro_environment_confidence"),
        "macro_forecast_confidence": safe_get("macro_forecast_confidence"),

        "dominant_regime": safe_get("dominant_regime"),
        "regime_overlaps": safe_get("regime_overlaps", []),
        "regime_conflicts": safe_get("regime_conflicts", []),

        "vol_wave_strength": safe_get("volatility_wave_strength"),
        "vol_wave_direction": safe_get("volatility_wave_direction"),

        "shock": safe_get("shock_volatility"),
        "instability": safe_get("edge_instability"),
        "turbulence": safe_get("edge_turbulence"),
    }

    # META-LEVEL CONTRADICTIONS
    contradictions = []

    # Example: bullish master state but high risk score
    if meta["master_state"] in ["Bullish Macro Environment", "Mildly Bullish Macro Environment"] and meta["macro_risk_score"] > 0.5:
        contradictions.append("Bullish state with elevated macro risk")

    # Example: bearish state but high opportunity score
    if meta["master_state"] in ["Bearish Macro Environment", "Mildly Bearish Macro Environment"] and meta["macro_opportunity_score"] > 0.5:
        contradictions.append("Bearish state with strong opportunity pockets")

    # Example: high confidence but high instability
    if meta["macro_environment_confidence"] > 0.6 and meta["instability"] > 0.5:
        contradictions.append("High confidence with high instability")

    # META-LEVEL ALIGNMENTS
    alignments = []

    if meta["macro_synthesis_score"] > 0.25 and meta["macro_opportunity_score"] > meta["macro_risk_score"]:
        alignments.append("Positive synthesis alignment")

    if meta["macro_synthesis_score"] < -0.25 and meta["macro_risk_score"] > meta["macro_opportunity_score"]:
        alignments.append("Negative synthesis alignment")

    if meta["vol_wave_direction"] == "expansion" and meta["momentum"] if "momentum" in meta else False:
        alignments.append("Volatility expansion + momentum alignment")

    meta["meta_contradictions"] = contradictions
    meta["meta_alignments"] = alignments

    # META-STATE CLASSIFICATION
    if contradictions and len(contradictions) >= 2:
        meta_state = "Meta-Conflicted Environment"
    elif alignments and len(alignments) >= 2:
        meta_state = "Meta-Aligned Environment"
    else:
        meta_state = "Meta-Neutral Environment"

    meta["meta_state"] = meta_state

    return meta


def _qwen_environment_meta_prompt(data):
    """
    Build a structured prompt for Qwen to generate the meta-level macro interpretation.
    """
    prompt = f"""
You are an elite sports betting MACRO-META analyst.

Analyze the following META-LEVEL MACRO DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Provide a META-LEVEL macro interpretation (above the master engine).
2. Identify meta-level contradictions and explain their implications.
3. Identify meta-level alignments and explain their implications.
4. Classify the environment into a meta-state (aligned, neutral, conflicted).
5. Highlight meta-level risks (macro brain misalignment, synthesis contradictions).
6. Highlight meta-level opportunities (meta-synergy, meta-alignment edges).
7. Provide 5–10 META-LEVEL strategy recommendations.
8. Tone: elite macro meta-analyst, concise, high-signal, authoritative.
9. Keep output under 450 words.
"""
    return prompt


def _generate_market_environment_meta(data):
    """
    Call Qwen to generate the meta-level macro interpretation.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_environment_meta_prompt(data)
    response = _call_qwen(prompt)
    return response or "No meta-level macro analysis generated."


def render_market_environment_meta_engine():
    """
    Full UI for Qwen-powered meta-level macro engine.
    """
    st.header("Market Environment Meta-Engine")
    st.caption("Qwen-powered meta-brain layer above the master engine.")

    data = _collect_market_environment_meta_data()
    if not data:
        st.info("No data available for meta-level macro analysis.")
        return

    analysis = _generate_market_environment_meta(data)

    # --- META STATE PANEL ---
    themed_card_container()
    st.markdown(f"""
    ## Meta-Macro State  
    **{data['meta_state']}**
    """)

    # --- META INTERPRETATION ---
    themed_card_container()
    st.markdown(f"""
    ## Meta-Level Macro Interpretation  
    {analysis}
    """)

    st.success("Meta-level macro engine complete.")
# ------------- CHUNK 102: MARKET ENVIRONMENT META-STABILITY ENGINE -------------

def _collect_market_environment_meta_stability_data():
    """
    Collect all components needed for META-STABILITY analysis:
    - meta-state
    - master-state
    - synthesis score
    - risk score
    - opportunity score
    - environment confidence
    - forecast confidence
    - regime conflicts & overlaps
    - volatility wave direction & strength
    - instability / shock / turbulence
    - meta contradictions
    - meta alignments
    """

    def safe_get(key, default=None):
        return st.session_state.get(key, default)

    meta_stab = {
        "meta_state": safe_get("meta_state"),
        "master_state": safe_get("master_state"),

        "macro_synthesis_score": safe_get("macro_synthesis_score"),
        "macro_risk_score": safe_get("macro_risk_score"),
        "macro_opportunity_score": safe_get("macro_opportunity_score"),
        "macro_environment_confidence": safe_get("macro_environment_confidence"),
        "macro_forecast_confidence": safe_get("macro_forecast_confidence"),

        "regime_overlaps": safe_get("regime_overlaps", []),
        "regime_conflicts": safe_get("regime_conflicts", []),

        "vol_wave_strength": safe_get("volatility_wave_strength"),
        "vol_wave_direction": safe_get("volatility_wave_direction"),

        "shock": safe_get("shock_volatility"),
        "instability": safe_get("edge_instability"),
        "turbulence": safe_get("edge_turbulence"),

        "meta_contradictions": safe_get("meta_contradictions", []),
        "meta_alignments": safe_get("meta_alignments", []),
    }

    # META-STABILITY SCORE
    # Stability = low contradictions + high confidence + low instability + aligned regimes
    contradictions = len(meta_stab["meta_contradictions"])
    alignments = len(meta_stab["meta_alignments"])
    conf = meta_stab["macro_environment_confidence"] or 0
    instab = meta_stab["instability"] or 0
    turb = meta_stab["turbulence"] or 0
    shock = meta_stab["shock"] or 0

    stability_score = float(
        (alignments * 0.6 + conf * 0.8) -
        (contradictions * 0.7 + instab * 0.5 + turb * 0.5 + shock * 0.5)
    )

    meta_stab["meta_stability_score"] = stability_score

    # META-STABILITY CLASSIFICATION
    if stability_score > 0.35:
        meta_stability_state = "Meta-Stable Environment"
    elif stability_score > -0.15:
        meta_stability_state = "Meta-Transition Environment"
    else:
        meta_stability_state = "Meta-Fragile Environment"

    meta_stab["meta_stability_state"] = meta_stability_state

    return meta_stab


def _qwen_environment_meta_stability_prompt(data):
    """
    Build a structured prompt for Qwen to generate the meta-stability interpretation.
    """
    prompt = f"""
You are an elite sports betting MACRO META-STABILITY analyst.

Analyze the following META-STABILITY DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Provide a META-STABILITY interpretation (stability, fragility, transition).
2. Identify the forces increasing stability vs decreasing stability.
3. Identify meta-stability risks (fragility pockets, transition traps, volatility shocks).
4. Identify meta-stability opportunities (resilience edges, alignment setups).
5. Provide 5–10 META-STABILITY strategy recommendations.
6. Tone: elite macro stability analyst, concise, high-signal, authoritative.
7. Keep output under 420 words.
"""
    return prompt


def _generate_market_environment_meta_stability(data):
    """
    Call Qwen to generate the meta-stability interpretation.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_environment_meta_stability_prompt(data)
    response = _call_qwen(prompt)
    return response or "No meta-stability analysis generated."


def render_market_environment_meta_stability_engine():
    """
    Full UI for Qwen-powered meta-stability engine.
    """
    st.header("Market Environment Meta-Stability Engine")
    st.caption("Qwen-powered macro stability sentinel above the meta-engine.")

    data = _collect_market_environment_meta_stability_data()
    if not data:
        st.info("No data available for meta-stability analysis.")
        return

    analysis = _generate_market_environment_meta_stability(data)

    # --- META-STABILITY STATE PANEL ---
    themed_card_container()
    st.markdown(f"""
    ## Meta-Stability State  
    **{data['meta_stability_state']}**
    """)

    # --- META-STABILITY INTERPRETATION ---
    themed_card_container()
    st.markdown(f"""
    ## Meta-Stability Interpretation  
    {analysis}
    """)

    st.success("Meta-stability engine complete.")
# ------------- CHUNK 103: MARKET ENVIRONMENT SUPER-META ENGINE -------------

def _collect_market_environment_super_meta_data():
    """
    Collect all components needed for SUPER-META analysis:
    - meta-stability state
    - meta-state
    - master-state
    - synthesis score
    - risk score
    - opportunity score
    - environment confidence
    - forecast confidence
    - regime conflicts & overlaps
    - volatility wave direction & strength
    - instability / shock / turbulence
    - meta contradictions & alignments
    - meta-stability score
    """

    def safe_get(key, default=None):
        return st.session_state.get(key, default)

    super_meta = {
        "meta_stability_state": safe_get("meta_stability_state"),
        "meta_state": safe_get("meta_state"),
        "master_state": safe_get("master_state"),

        "macro_synthesis_score": safe_get("macro_synthesis_score"),
        "macro_risk_score": safe_get("macro_risk_score"),
        "macro_opportunity_score": safe_get("macro_opportunity_score"),
        "macro_environment_confidence": safe_get("macro_environment_confidence"),
        "macro_forecast_confidence": safe_get("macro_forecast_confidence"),

        "regime_overlaps": safe_get("regime_overlaps", []),
        "regime_conflicts": safe_get("regime_conflicts", []),

        "vol_wave_strength": safe_get("volatility_wave_strength"),
        "vol_wave_direction": safe_get("volatility_wave_direction"),

        "shock": safe_get("shock_volatility"),
        "instability": safe_get("edge_instability"),
        "turbulence": safe_get("edge_turbulence"),

        "meta_contradictions": safe_get("meta_contradictions", []),
        "meta_alignments": safe_get("meta_alignments", []),

        "meta_stability_score": safe_get("meta_stability_score"),
    }

    # SUPER-META COHERENCE SCORE
    contradictions = len(super_meta["meta_contradictions"])
    alignments = len(super_meta["meta_alignments"])
    meta_stab = super_meta["meta_stability_score"] or 0
    conf = super_meta["macro_environment_confidence"] or 0
    instab = super_meta["instability"] or 0
    turb = super_meta["turbulence"] or 0
    shock = super_meta["shock"] or 0

    coherence_score = float(
        (alignments * 0.7 + meta_stab * 0.8 + conf * 0.6) -
        (contradictions * 0.8 + instab * 0.5 + turb * 0.5 + shock * 0.5)
    )

    super_meta["super_meta_coherence_score"] = coherence_score

    # SUPER-META STATE CLASSIFICATION
    if coherence_score > 0.45:
        super_meta_state = "Super-Meta Coherent Environment"
    elif coherence_score > -0.2:
        super_meta_state = "Super-Meta Transitional Environment"
    else:
        super_meta_state = "Super-Meta Fragmented Environment"

    super_meta["super_meta_state"] = super_meta_state

    return super_meta


def _qwen_environment_super_meta_prompt(data):
    """
    Build a structured prompt for Qwen to generate the super-meta interpretation.
    """
    prompt = f"""
You are an elite sports betting MACRO SUPER-META analyst.

Analyze the following SUPER-META MACRO DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Provide a SUPER-META macro interpretation (above meta-stability).
2. Identify super-meta coherence vs fragmentation.
3. Identify super-meta risks (macro brain breakdown, resonance failure).
4. Identify super-meta opportunities (resonance alignment, coherence edges).
5. Classify the environment into a super-meta state (coherent, transitional, fragmented).
6. Provide 6–12 SUPER-META strategy recommendations.
7. Tone: elite macro super-meta analyst, concise, high-signal, authoritative.
8. Keep output under 480 words.
"""
    return prompt


def _generate_market_environment_super_meta(data):
    """
    Call Qwen to generate the super-meta macro interpretation.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_environment_super_meta_prompt(data)
    response = _call_qwen(prompt)
    return response or "No super-meta macro analysis generated."


def render_market_environment_super_meta_engine():
    """
    Full UI for Qwen-powered super-meta macro engine.
    """
    st.header("Market Environment Super-Meta Engine")
    st.caption("Qwen-powered macro oversight layer above the meta-stability engine.")

    data = _collect_market_environment_super_meta_data()
    if not data:
        st.info("No data available for super-meta macro analysis.")
        return

    analysis = _generate_market_environment_super_meta(data)

    # --- SUPER-META STATE PANEL ---
    themed_card_container()
    st.markdown(f"""
    ## Super-Meta State  
    **{data['super_meta_state']}**
    """)

    # --- SUPER-META INTERPRETATION ---
    themed_card_container()
    st.markdown(f"""
    ## Super-Meta Macro Interpretation  
    {analysis}
    """)

    st.success("Super-meta macro engine complete.")
# ------------- CHUNK 104: MARKET ENVIRONMENT HYPER-META ENGINE -------------

def _collect_market_environment_hyper_meta_data():
    """
    Collect all components needed for HYPER-META analysis:
    - super-meta state
    - meta-stability state
    - meta-state
    - master-state
    - synthesis score
    - risk score
    - opportunity score
    - environment confidence
    - forecast confidence
    - regime conflicts & overlaps
    - volatility wave direction & strength
    - instability / shock / turbulence
    - meta contradictions & alignments
    - meta-stability score
    - super-meta coherence score
    """

    def safe_get(key, default=None):
        return st.session_state.get(key, default)

    hyper = {
        "super_meta_state": safe_get("super_meta_state"),
        "meta_stability_state": safe_get("meta_stability_state"),
        "meta_state": safe_get("meta_state"),
        "master_state": safe_get("master_state"),

        "macro_synthesis_score": safe_get("macro_synthesis_score"),
        "macro_risk_score": safe_get("macro_risk_score"),
        "macro_opportunity_score": safe_get("macro_opportunity_score"),
        "macro_environment_confidence": safe_get("macro_environment_confidence"),
        "macro_forecast_confidence": safe_get("macro_forecast_confidence"),

        "regime_overlaps": safe_get("regime_overlaps", []),
        "regime_conflicts": safe_get("regime_conflicts", []),

        "vol_wave_strength": safe_get("volatility_wave_strength"),
        "vol_wave_direction": safe_get("volatility_wave_direction"),

        "shock": safe_get("shock_volatility"),
        "instability": safe_get("edge_instability"),
        "turbulence": safe_get("edge_turbulence"),

        "meta_contradictions": safe_get("meta_contradictions", []),
        "meta_alignments": safe_get("meta_alignments", []),

        "meta_stability_score": safe_get("meta_stability_score"),
        "super_meta_coherence_score": safe_get("super_meta_coherence_score"),
    }

    # HYPER-META INTEGRITY SCORE
    contradictions = len(hyper["meta_contradictions"])
    alignments = len(hyper["meta_alignments"])
    meta_stab = hyper["meta_stability_score"] or 0
    super_meta_coh = hyper["super_meta_coherence_score"] or 0
    conf = hyper["macro_environment_confidence"] or 0
    instab = hyper["instability"] or 0
    turb = hyper["turbulence"] or 0
    shock = hyper["shock"] or 0

    integrity_score = float(
        (alignments * 0.6 + meta_stab * 0.7 + super_meta_coh * 0.9 + conf * 0.5) -
        (contradictions * 0.8 + instab * 0.5 + turb * 0.5 + shock * 0.5)
    )

    hyper["hyper_meta_integrity_score"] = integrity_score

    # HYPER-META STATE CLASSIFICATION
    if integrity_score > 0.55:
        hyper_state = "Hyper-Meta Coherent Environment"
    elif integrity_score > -0.25:
        hyper_state = "Hyper-Meta Transitional Environment"
    else:
        hyper_state = "Hyper-Meta Degraded Environment"

    hyper["hyper_meta_state"] = hyper_state

    return hyper


def _qwen_environment_hyper_meta_prompt(data):
    """
    Build a structured prompt for Qwen to generate the hyper-meta interpretation.
    """
    prompt = f"""
You are an elite sports betting MACRO HYPER-META analyst.

Analyze the following HYPER-META MACRO DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Provide a HYPER-META macro interpretation (above super-meta).
2. Identify hyper-meta coherence vs degradation.
3. Identify hyper-meta risks (systemic breakdown, resonance collapse).
4. Identify hyper-meta opportunities (high-order alignment, structural resonance).
5. Classify the environment into a hyper-meta state (coherent, transitional, degraded).
6. Provide 6–12 HYPER-META strategy recommendations.
7. Tone: elite macro hyper-meta analyst, concise, high-signal, authoritative.
8. Keep output under 500 words.
"""
    return prompt


def _generate_market_environment_hyper_meta(data):
    """
    Call Qwen to generate the hyper-meta macro interpretation.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_environment_hyper_meta_prompt(data)
    response = _call_qwen(prompt)
    return response or "No hyper-meta macro analysis generated."


def render_market_environment_hyper_meta_engine():
    """
    Full UI for Qwen-powered hyper-meta macro engine.
    """
    st.header("Market Environment Hyper-Meta Engine")
    st.caption("Qwen-powered macro oversight layer above the super-meta engine.")

    data = _collect_market_environment_hyper_meta_data()
    if not data:
        st.info("No data available for hyper-meta macro analysis.")
        return

    analysis = _generate_market_environment_hyper_meta(data)

    # --- HYPER-META STATE PANEL ---
    themed_card_container()
    st.markdown(f"""
    ## Hyper-Meta State  
    **{data['hyper_meta_state']}**
    """)

    # --- HYPER-META INTERPRETATION ---
    themed_card_container()
    st.markdown(f"""
    ## Hyper-Meta Macro Interpretation  
    {analysis}
    """)

    st.success("Hyper-meta macro engine complete.")
# ------------- CHUNK 105: MARKET ENVIRONMENT OMNI-MACRO ENGINE -------------

def _collect_market_environment_omni_macro_data():
    """
    Collect all components needed for OMNI-MACRO analysis:
    - hyper-meta state
    - super-meta state
    - meta-stability state
    - meta-state
    - master-state
    - synthesis score
    - risk score
    - opportunity score
    - environment confidence
    - forecast confidence
    - regime conflicts & overlaps
    - volatility wave direction & strength
    - instability / shock / turbulence
    - meta contradictions & alignments
    - meta-stability score
    - super-meta coherence score
    - hyper-meta integrity score
    """

    def safe_get(key, default=None):
        return st.session_state.get(key, default)

    omni = {
        "hyper_meta_state": safe_get("hyper_meta_state"),
        "super_meta_state": safe_get("super_meta_state"),
        "meta_stability_state": safe_get("meta_stability_state"),
        "meta_state": safe_get("meta_state"),
        "master_state": safe_get("master_state"),

        "macro_synthesis_score": safe_get("macro_synthesis_score"),
        "macro_risk_score": safe_get("macro_risk_score"),
        "macro_opportunity_score": safe_get("macro_opportunity_score"),
        "macro_environment_confidence": safe_get("macro_environment_confidence"),
        "macro_forecast_confidence": safe_get("macro_forecast_confidence"),

        "regime_overlaps": safe_get("regime_overlaps", []),
        "regime_conflicts": safe_get("regime_conflicts", []),

        "vol_wave_strength": safe_get("volatility_wave_strength"),
        "vol_wave_direction": safe_get("volatility_wave_direction"),

        "shock": safe_get("shock_volatility"),
        "instability": safe_get("edge_instability"),
        "turbulence": safe_get("edge_turbulence"),

        "meta_contradictions": safe_get("meta_contradictions", []),
        "meta_alignments": safe_get("meta_alignments", []),

        "meta_stability_score": safe_get("meta_stability_score"),
        "super_meta_coherence_score": safe_get("super_meta_coherence_score"),
        "hyper_meta_integrity_score": safe_get("hyper_meta_integrity_score"),
    }

    # OMNI-MACRO UNITY SCORE
    contradictions = len(omni["meta_contradictions"])
    alignments = len(omni["meta_alignments"])
    meta_stab = omni["meta_stability_score"] or 0
    super_meta_coh = omni["super_meta_coherence_score"] or 0
    hyper_meta_int = omni["hyper_meta_integrity_score"] or 0
    conf = omni["macro_environment_confidence"] or 0
    instab = omni["instability"] or 0
    turb = omni["turbulence"] or 0
    shock = omni["shock"] or 0

    unity_score = float(
        (alignments * 0.5 +
         meta_stab * 0.6 +
         super_meta_coh * 0.7 +
         hyper_meta_int * 0.9 +
         conf * 0.4)
        -
        (contradictions * 0.7 +
         instab * 0.5 +
         turb * 0.5 +
         shock * 0.5)
    )

    omni["omni_macro_unity_score"] = unity_score

    # OMNI-MACRO STATE CLASSIFICATION
    if unity_score > 0.65:
        omni_state = "Omni-Coherent Macro Environment"
    elif unity_score > -0.2:
        omni_state = "Omni-Transitional Macro Environment"
    else:
        omni_state = "Omni-Degraded Macro Environment"

    omni["omni_macro_state"] = omni_state

    return omni


def _qwen_environment_omni_macro_prompt(data):
    """
    Build a structured prompt for Qwen to generate the omni-macro interpretation.
    """
    prompt = f"""
You are an elite sports betting MACRO OMNI-ANALYST.

Analyze the following OMNI-MACRO DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Provide an OMNI-MACRO interpretation (above hyper-meta).
2. Identify omni-level coherence vs degradation.
3. Identify omni-level risks (system-wide breakdown, macro-brain collapse).
4. Identify omni-level opportunities (system-wide alignment, omni-resonance).
5. Classify the environment into an omni-macro state (coherent, transitional, degraded).
6. Provide 8–14 OMNI-MACRO strategy recommendations.
7. Tone: elite omni-macro analyst, concise, high-signal, authoritative.
8. Keep output under 520 words.
"""
    return prompt


def _generate_market_environment_omni_macro(data):
    """
    Call Qwen to generate the omni-macro macro interpretation.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_environment_omni_macro_prompt(data)
    response = _call_qwen(prompt)
    return response or "No omni-macro analysis generated."


def render_market_environment_omni_macro_engine():
    """
    Full UI for Qwen-powered omni-macro engine.
    """
    st.header("Market Environment Omni-Macro Engine")
    st.caption("Qwen-powered final macro integration layer above all macro engines.")

    data = _collect_market_environment_omni_macro_data()
    if not data:
        st.info("No data available for omni-macro analysis.")
        return

    analysis = _generate_market_environment_omni_macro(data)

    # --- OMNI-MACRO STATE PANEL ---
    themed_card_container()
    st.markdown(f"""
    ## Omni-Macro State  
    **{data['omni_macro_state']}**
    """)

    # --- OMNI-MACRO INTERPRETATION ---
    themed_card_container()
    st.markdown(f"""
    ## Omni-Macro Interpretation  
    {analysis}
    """)

    st.success("Omni-macro engine complete.")
# ------------- CHUNK 106: MARKET ENVIRONMENT FINAL INTEGRATION ENGINE -------------

def _collect_market_environment_final_data():
    """
    Collect ALL macro layers for final integration:
    - omni-macro state
    - hyper-meta state
    - super-meta state
    - meta-stability state
    - meta-state
    - master-state
    - synthesis score
    - risk score
    - opportunity score
    - environment confidence
    - forecast confidence
    - regime conflicts & overlaps
    - volatility wave direction & strength
    - instability / shock / turbulence
    - meta contradictions & alignments
    - meta-stability score
    - super-meta coherence score
    - hyper-meta integrity score
    - omni-macro unity score
    """

    def safe_get(key, default=None):
        return st.session_state.get(key, default)

    final = {
        "omni_macro_state": safe_get("omni_macro_state"),
        "hyper_meta_state": safe_get("hyper_meta_state"),
        "super_meta_state": safe_get("super_meta_state"),
        "meta_stability_state": safe_get("meta_stability_state"),
        "meta_state": safe_get("meta_state"),
        "master_state": safe_get("master_state"),

        "macro_synthesis_score": safe_get("macro_synthesis_score"),
        "macro_risk_score": safe_get("macro_risk_score"),
        "macro_opportunity_score": safe_get("macro_opportunity_score"),
        "macro_environment_confidence": safe_get("macro_environment_confidence"),
        "macro_forecast_confidence": safe_get("macro_forecast_confidence"),

        "regime_overlaps": safe_get("regime_overlaps", []),
        "regime_conflicts": safe_get("regime_conflicts", []),

        "vol_wave_strength": safe_get("volatility_wave_strength"),
        "vol_wave_direction": safe_get("volatility_wave_direction"),

        "shock": safe_get("shock_volatility"),
        "instability": safe_get("edge_instability"),
        "turbulence": safe_get("edge_turbulence"),

        "meta_contradictions": safe_get("meta_contradictions", []),
        "meta_alignments": safe_get("meta_alignments", []),

        "meta_stability_score": safe_get("meta_stability_score"),
        "super_meta_coherence_score": safe_get("super_meta_coherence_score"),
        "hyper_meta_integrity_score": safe_get("hyper_meta_integrity_score"),
        "omni_macro_unity_score": safe_get("omni_macro_unity_score"),
    }

    # FINAL MACRO SCORE
    contradictions = len(final["meta_contradictions"])
    alignments = len(final["meta_alignments"])

    meta_stab = final["meta_stability_score"] or 0
    super_meta = final["super_meta_coherence_score"] or 0
    hyper_meta = final["hyper_meta_integrity_score"] or 0
    omni_unity = final["omni_macro_unity_score"] or 0

    conf = final["macro_environment_confidence"] or 0
    instab = final["instability"] or 0
    turb = final["turbulence"] or 0
    shock = final["shock"] or 0

    final_score = float(
        (alignments * 0.4 +
         meta_stab * 0.5 +
         super_meta * 0.6 +
         hyper_meta * 0.8 +
         omni_unity * 1.0 +
         conf * 0.3)
        -
        (contradictions * 0.6 +
         instab * 0.4 +
         turb * 0.4 +
         shock * 0.4)
    )

    final["final_macro_score"] = final_score

    # FINAL MACRO STATE CLASSIFICATION
    if final_score > 0.75:
        final_state = "Unified Bullish Macro Environment"
    elif final_score > 0.25:
        final_state = "Constructive Macro Environment"
    elif final_score > -0.25:
        final_state = "Neutral Macro Environment"
    elif final_score > -0.75:
        final_state = "Defensive Macro Environment"
    else:
        final_state = "Unified Bearish Macro Environment"

    final["final_macro_state"] = final_state

    return final


def _qwen_environment_final_prompt(data):
    """
    Build a structured prompt for Qwen to generate the final macro directive.
    """
    prompt = f"""
You are an elite sports betting MACRO GRANDMASTER.

Analyze the following FULL MACRO STACK (ALL LAYERS):

{json.dumps(data, indent=2)}

TASKS:
1. Provide the FINAL MACRO INTERPRETATION (the macro seal).
2. Explain the final macro state and why it was chosen.
3. Identify system-wide risks (cross-layer breakdown, omni-fragility).
4. Identify system-wide opportunities (cross-layer alignment, omni-resonance).
5. Provide the FINAL MACRO DIRECTIVE (the single most important macro takeaway).
6. Provide 8–16 FINAL MACRO STRATEGY RECOMMENDATIONS.
7. Tone: elite macro grandmaster, concise, high-signal, authoritative.
8. Keep output under 600 words.
"""
    return prompt


def _generate_market_environment_final(data):
    """
    Call Qwen to generate the final macro interpretation.
    """
    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_environment_final_prompt(data)
    response = _call_qwen(prompt)
    return response or "No final macro analysis generated."


def render_market_environment_final_engine():
    """
    Full UI for Qwen-powered final macro integration engine.
    """
    st.header("Final Macro Integration Engine")
    st.caption("The macro seal layer — the final unified macro interpretation.")

    data = _collect_market_environment_final_data()
    if not data:
        st.info("No data available for final macro analysis.")
        return

    analysis = _generate_market_environment_final(data)

    # --- FINAL MACRO STATE PANEL ---
    themed_card_container()
    st.markdown(f"""
    ## Final Macro State  
    **{data['final_macro_state']}**
    """)

    # --- FINAL MACRO INTERPRETATION ---
    themed_card_container()
    st.markdown(f"""
    ## Final Macro Interpretation  
    {analysis}
    """)

    st.success("Final macro integration complete.")
# ------------- CHUNK 107: MICRO ENVIRONMENT ENGINE -------------

def _collect_micro_environment_data():
    """
    Collect all micro-level signals for the micro environment engine:
    - micro drift
    - micro momentum
    - micro volatility
    - micro instability
    - micro expansion / compression
    - micro overextension / exhaustion
    - micro shock
    - micro turbulence
    - micro cycle direction
    - micro cycle strength
    """

    def safe_get(key, default=0):
        return st.session_state.get(key, default)

    micro = {
        "micro_drift": safe_get("micro_drift"),
        "micro_momentum": safe_get("micro_momentum"),
        "micro_volatility": safe_get("micro_volatility"),
        "micro_instability": safe_get("micro_instability"),
        "micro_expansion": safe_get("micro_expansion"),
        "micro_compression": safe_get("micro_compression"),
        "micro_overextension": safe_get("micro_overextension"),
        "micro_exhaustion": safe_get("micro_exhaustion"),
        "micro_shock": safe_get("micro_shock"),
        "micro_turbulence": safe_get("micro_turbulence"),
        "micro_cycle_direction": safe_get("micro_cycle_direction"),
        "micro_cycle_strength": safe_get("micro_cycle_strength"),
    }

    return micro


def _compute_micro_environment_score(data):
    """
    Compute a unified micro environment score.
    Higher = favorable micro environment.
    Lower = unstable or dangerous micro environment.
    """

    drift = abs(data["micro_drift"] or 0)
    momentum = abs(data["micro_momentum"] or 0)
    vol = data["micro_volatility"] or 0
    instab = data["micro_instability"] or 0
    exp = data["micro_expansion"] or 0
    comp = data["micro_compression"] or 0
    overext = data["micro_overextension"] or 0
    exhaust = data["micro_exhaustion"] or 0
    shock = data["micro_shock"] or 0
    turb = data["micro_turbulence"] or 0
    cycle_strength = data["micro_cycle_strength"] or 0

    score = float(
        (drift * 0.4 + momentum * 0.4 + cycle_strength * 0.5 + exp * 0.3) -
        (vol * 0.3 + instab * 0.4 + comp * 0.3 + overext * 0.4 + exhaust * 0.4 + shock * 0.5 + turb * 0.5)
    )

    return score


def _classify_micro_environment(score):
    """
    Classify the micro environment into one of five states.
    """

    if score > 0.6:
        return "Favorable Micro Environment"
    elif score > 0.2:
        return "Constructive Micro Environment"
    elif score > -0.2:
        return "Neutral Micro Environment"
    elif score > -0.6:
        return "Unfavorable Micro Environment"
    else:
        return "Hostile Micro Environment"


def render_micro_environment_engine():
    """
    Full UI for the micro environment engine.
    """
    st.header("Micro Environment Engine")
    st.caption("Evaluates micro-level drift, momentum, volatility, instability, and cycles.")

    data = _collect_micro_environment_data()
    if not data:
        st.info("No micro environment data available.")
        return

    score = _compute_micro_environment_score(data)
    state = _classify_micro_environment(score)

    themed_card_container()
    st.markdown(f"""
    ## Micro Environment State  
    **{state}**

    **Micro Environment Score:** `{score:.4f}`
    """)

    # Display raw micro signals
    themed_card_container()
    st.markdown("### Micro Signals")
    st.json(data)

    st.success("Micro environment analysis complete.")
# ------------- CHUNK 108: MICRO RISK ENGINE -------------

def _collect_micro_risk_data():
    """
    Collect all micro-level signals needed for micro risk scoring:
    - micro volatility
    - micro instability
    - micro shock
    - micro turbulence
    - micro compression
    - micro overextension
    - micro exhaustion
    - micro cycle strength
    - micro drift
    - micro momentum
    """

    def safe_get(key, default=0):
        return st.session_state.get(key, default)

    risk = {
        "micro_volatility": safe_get("micro_volatility"),
        "micro_instability": safe_get("micro_instability"),
        "micro_shock": safe_get("micro_shock"),
        "micro_turbulence": safe_get("micro_turbulence"),
        "micro_compression": safe_get("micro_compression"),
        "micro_overextension": safe_get("micro_overextension"),
        "micro_exhaustion": safe_get("micro_exhaustion"),
        "micro_cycle_strength": safe_get("micro_cycle_strength"),
        "micro_drift": safe_get("micro_drift"),
        "micro_momentum": safe_get("micro_momentum"),
    }

    return risk


def _compute_micro_risk_score(data):
    """
    Compute a unified micro risk score.
    Higher = more dangerous micro environment.
    """

    vol = data["micro_volatility"] or 0
    instab = data["micro_instability"] or 0
    shock = data["micro_shock"] or 0
    turb = data["micro_turbulence"] or 0
    comp = data["micro_compression"] or 0
    overext = data["micro_overextension"] or 0
    exhaust = data["micro_exhaustion"] or 0
    cycle_strength = data["micro_cycle_strength"] or 0

    drift = abs(data["micro_drift"] or 0)
    momentum = abs(data["micro_momentum"] or 0)

    score = float(
        (vol * 0.4 +
         instab * 0.5 +
         shock * 0.6 +
         turb * 0.6 +
         comp * 0.4 +
         overext * 0.5 +
         exhaust * 0.5 +
         cycle_strength * 0.3)
        -
        (drift * 0.2 + momentum * 0.2)
    )

    return score


def _identify_micro_risk_clusters(data):
    """
    Identify micro-level risk clusters.
    """

    clusters = []

    if (data["micro_shock"] or 0) > 0.5 and (data["micro_turbulence"] or 0) > 0.5:
        clusters.append("Shock + Turbulence Cluster")

    if (data["micro_instability"] or 0) > 0.5 and (data["micro_compression"] or 0) > 0.5:
        clusters.append("Instability + Compression Cluster")

    if (data["micro_overextension"] or 0) > 0.5 and (data["micro_exhaustion"] or 0) > 0.5:
        clusters.append("Overextension + Exhaustion Cluster")

    if (data["micro_volatility"] or 0) > 0.5 and (data["micro_cycle_strength"] or 0) > 0.5:
        clusters.append("Volatility Cycle Risk Cluster")

    return clusters


def _classify_micro_risk(score):
    """
    Classify the micro risk environment.
    """

    if score > 0.7:
        return "High-Risk Micro Environment"
    elif score > 0.3:
        return "Elevated Micro Risk"
    elif score > -0.1:
        return "Moderate Micro Risk"
    elif score > -0.5:
        return "Low Micro Risk"
    else:
        return "Minimal Micro Risk"


def render_micro_risk_engine():
    """
    Full UI for the micro risk engine.
    """
    st.header("Micro Risk Engine")
    st.caption("Evaluates micro-level volatility, instability, shock, turbulence, and risk clusters.")

    data = _collect_micro_risk_data()
    if not data:
        st.info("No micro risk data available.")
        return

    score = _compute_micro_risk_score(data)
    state = _classify_micro_risk(score)
    clusters = _identify_micro_risk_clusters(data)

    themed_card_container()
    st.markdown(f"""
    ## Micro Risk State  
    **{state}**

    **Micro Risk Score:** `{score:.4f}`  
    """)

    themed_card_container()
    st.markdown("### Micro Risk Clusters")
    if clusters:
        for c in clusters:
            st.markdown(f"- **{c}**")
    else:
        st.markdown("No significant micro risk clusters detected.")

    themed_card_container()
    st.markdown("### Micro Risk Signals")
    st.json(data)

    st.success("Micro risk analysis complete.")
# ------------- CHUNK 109: MICRO OPPORTUNITY ENGINE -------------

def _collect_micro_opportunity_data():
    """
    Collect all micro-level signals needed for micro opportunity scoring:
    - micro drift
    - micro momentum
    - micro expansion
    - micro compression
    - micro overextension
    - micro exhaustion
    - micro cycle direction
    - micro cycle strength
    - micro volatility
    - micro instability
    """

    def safe_get(key, default=0):
        return st.session_state.get(key, default)

    opp = {
        "micro_drift": safe_get("micro_drift"),
        "micro_momentum": safe_get("micro_momentum"),
        "micro_expansion": safe_get("micro_expansion"),
        "micro_compression": safe_get("micro_compression"),
        "micro_overextension": safe_get("micro_overextension"),
        "micro_exhaustion": safe_get("micro_exhaustion"),
        "micro_cycle_direction": safe_get("micro_cycle_direction"),
        "micro_cycle_strength": safe_get("micro_cycle_strength"),
        "micro_volatility": safe_get("micro_volatility"),
        "micro_instability": safe_get("micro_instability"),
    }

    return opp


def _compute_micro_opportunity_score(data):
    """
    Compute a unified micro opportunity score.
    Higher = more upside potential in the micro environment.
    """

    drift = abs(data["micro_drift"] or 0)
    momentum = abs(data["micro_momentum"] or 0)
    expansion = data["micro_expansion"] or 0
    compression = data["micro_compression"] or 0
    overext = data["micro_overextension"] or 0
    exhaust = data["micro_exhaustion"] or 0
    cycle_strength = data["micro_cycle_strength"] or 0
    vol = data["micro_volatility"] or 0
    instab = data["micro_instability"] or 0

    score = float(
        (drift * 0.4 +
         momentum * 0.5 +
         expansion * 0.4 +
         compression * 0.3 +
         cycle_strength * 0.5)
        -
        (overext * 0.3 +
         exhaust * 0.3 +
         vol * 0.2 +
         instab * 0.2)
    )

    return score


def _identify_micro_opportunity_clusters(data):
    """
    Identify micro-level opportunity clusters.
    """

    clusters = []

    if (data["micro_compression"] or 0) > 0.5 and (data["micro_momentum"] or 0) > 0.5:
        clusters.append("Compression Breakout Opportunity Cluster")

    if (data["micro_exhaustion"] or 0) > 0.5 and (data["micro_drift"] or 0) > 0.5:
        clusters.append("Exhaustion Reversal Opportunity Cluster")

    if (data["micro_cycle_strength"] or 0) > 0.5 and (data["micro_drift"] or 0) > 0.5:
        clusters.append("Cycle Continuation Opportunity Cluster")

    if (data["micro_expansion"] or 0) > 0.5 and (data["micro_momentum"] or 0) > 0.5:
        clusters.append("Expansion Momentum Opportunity Cluster")

    return clusters


def _classify_micro_opportunity(score):
    """
    Classify the micro opportunity environment.
    """

    if score > 0.7:
        return "High-Opportunity Micro Environment"
    elif score > 0.3:
        return "Constructive Micro Opportunity"
    elif score > -0.1:
        return "Moderate Micro Opportunity"
    elif score > -0.5:
        return "Weak Micro Opportunity"
    else:
        return "Minimal Micro Opportunity"


def render_micro_opportunity_engine():
    """
    Full UI for the micro opportunity engine.
    """
    st.header("Micro Opportunity Engine")
    st.caption("Evaluates micro-level drift, momentum, compression, expansion, and opportunity clusters.")

    data = _collect_micro_opportunity_data()
    if not data:
        st.info("No micro opportunity data available.")
        return

    score = _compute_micro_opportunity_score(data)
    state = _classify_micro_opportunity(score)
    clusters = _identify_micro_opportunity_clusters(data)

    themed_card_container()
    st.markdown(f"""
    ## Micro Opportunity State  
    **{state}**

    **Micro Opportunity Score:** `{score:.4f}`
    """)

    themed_card_container()
    st.markdown("### Micro Opportunity Clusters")
    if clusters:
        for c in clusters:
            st.markdown(f"- **{c}**")
    else:
        st.markdown("No significant micro opportunity clusters detected.")

    themed_card_container()
    st.markdown("### Micro Opportunity Signals")
    st.json(data)

    st.success("Micro opportunity analysis complete.")
# ------------- CHUNK 110: MICRO CONFIDENCE ENGINE -------------

def _collect_micro_confidence_data():
    """
    Collect all micro-level signals needed for micro confidence scoring:
    - micro environment score
    - micro risk score
    - micro opportunity score
    - micro cycle strength
    - micro drift
    - micro momentum
    - micro volatility
    - micro instability
    """

    def safe_get(key, default=0):
        return st.session_state.get(key, default)

    conf = {
        "micro_environment_score": safe_get("micro_environment_score"),
        "micro_risk_score": safe_get("micro_risk_score"),
        "micro_opportunity_score": safe_get("micro_opportunity_score"),
        "micro_cycle_strength": safe_get("micro_cycle_strength"),
        "micro_drift": safe_get("micro_drift"),
        "micro_momentum": safe_get("micro_momentum"),
        "micro_volatility": safe_get("micro_volatility"),
        "micro_instability": safe_get("micro_instability"),
    }

    return conf


def _compute_micro_confidence_score(data):
    """
    Compute a unified micro confidence score.
    Higher = more reliable micro signals.
    """

    env = data["micro_environment_score"] or 0
    risk = data["micro_risk_score"] or 0
    opp = data["micro_opportunity_score"] or 0
    cycle = data["micro_cycle_strength"] or 0
    drift = abs(data["micro_drift"] or 0)
    momentum = abs(data["micro_momentum"] or 0)
    vol = data["micro_volatility"] or 0
    instab = data["micro_instability"] or 0

    score = float(
        (env * 0.5 +
         opp * 0.4 +
         cycle * 0.4 +
         drift * 0.3 +
         momentum * 0.3)
        -
        (risk * 0.4 +
         vol * 0.3 +
         instab * 0.3)
    )

    return score
# ------------- CHUNK 111: MICRO FORECAST ENGINE -------------

def _collect_micro_forecast_data():
    """
    Collect all micro-level signals needed for micro forecasting:
    - micro environment score
    - micro risk score
    - micro opportunity score
    - micro confidence score
    - micro drift
    - micro momentum
    - micro cycle direction
    - micro cycle strength
    - micro volatility
    - micro instability
    """

    def safe_get(key, default=0):
        return st.session_state.get(key, default)

    fc = {
        "micro_environment_score": safe_get("micro_environment_score"),
        "micro_risk_score": safe_get("micro_risk_score"),
        "micro_opportunity_score": safe_get("micro_opportunity_score"),
        "micro_confidence_score": safe_get("micro_confidence_score"),
        "micro_drift": safe_get("micro_drift"),
        "micro_momentum": safe_get("micro_momentum"),
        "micro_cycle_direction": safe_get("micro_cycle_direction"),
        "micro_cycle_strength": safe_get("micro_cycle_strength"),
        "micro_volatility": safe_get("micro_volatility"),
        "micro_instability": safe_get("micro_instability"),
    }

    return fc


def _compute_micro_forecast_score(data):
    """
    Compute a unified micro forecast score.
    Higher = favorable micro forecast.
    Lower = negative or unstable micro forecast.
    """

    env = data["micro_environment_score"] or 0
    risk = data["micro_risk_score"] or 0
    opp = data["micro_opportunity_score"] or 0
    conf = data["micro_confidence_score"]

# ------------- CHUNK 112: MICRO NARRATIVE ENGINE -------------

def _collect_micro_narrative_data():
    """
    Collect all micro-level signals needed for narrative generation:
    - micro environment state
    - micro environment score
    - micro risk state
    - micro risk score
    - micro opportunity state
    - micro opportunity score
    - micro confidence state
    - micro confidence score
    - micro forecast state
    - micro forecast score
    - micro drift
    - micro momentum
    - micro cycle direction
    - micro cycle strength
    - micro volatility
    - micro instability
    - micro shock
    - micro turbulence
    """

    def safe_get(key, default=None):
        return st.session_state.get(key, default)

    data = {
        "micro_environment_state": safe_get("micro_environment_state"),
        "micro_environment_score": safe_get("micro_environment_score"),

        "micro_risk_state": safe_get("micro_risk_state"),
        "micro_risk_score": safe_get("micro_risk_score"),

        "micro_opportunity_state": safe_get("micro_opportunity_state"),
        "micro_opportunity_score": safe_get("micro_opportunity_score"),

        "micro_confidence_state": safe_get("micro_confidence_state"),
        "micro_confidence_score": safe_get("micro_confidence_score"),

        "micro_forecast_state": safe_get("micro_forecast_state"),
        "micro_forecast_score": safe_get("micro_forecast_score"),

        "micro_drift": safe_get("micro_drift"),
        "micro_momentum": safe_get("micro_momentum"),
        "micro_cycle_direction": safe_get("micro_cycle_direction"),
        "micro_cycle_strength": safe_get("micro_cycle_strength"),
        "micro_volatility": safe_get("micro_volatility"),
        "micro_instability": safe_get("micro_instability"),
        "micro_shock": safe_get("micro_shock"),
        "micro_turbulence": safe_get("micro_turbulence"),
    }

    return data


def _qwen_micro_narrative_prompt(data):
    """
    Build a structured prompt for Qwen to generate the micro narrative.
    """

    prompt = f"""
You are an elite MICRO-LEVEL sports betting analyst.

Analyze the following MICRO DATA:

{json.dumps(data, indent=2)}

TASKS:
1. Provide a MICRO NARRATIVE explaining the current micro environment.
2. Identify the dominant micro drivers (momentum, drift, cycles, volatility, instability).
3. Explain micro risks and why they matter.
4. Explain micro opportunities and why they matter.
5. Explain the micro forecast and what is likely next.
6. Provide a MICRO STRATEGY SUMMARY (6–12 bullet points).
7. Tone: elite micro analyst, concise, high-signal, authoritative.
8. Keep output under 450 words.
"""

    return prompt


def _generate_micro_narrative(data):
    """
    Call Qwen to generate the micro narrative.
    """

    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _qwen_micro_narrative_prompt(data)
    response = _call_qwen(prompt)
    return response or "No micro narrative generated."


def render_micro_narrative_engine():
    """
    Full UI for the micro narrative engine.
    """
    st.header("Micro Narrative Engine")
    st.caption("Explains the story behind the micro environment, risks, opportunities, and forecast.")

    data = _collect_micro_narrative_data()
    if not data:
        st.info("No micro narrative data available.")
        return

    narrative = _generate_micro_narrative(data)

    themed_card_container()
    st.markdown("## Micro Narrative")
    st.markdown(narrative)

    themed_card_container()
    st.markdown("### Micro Narrative Inputs")
    st.json(data)

    st.success("Micro narrative generation complete.")
# ------------- CHUNK 113: MICRO MASTER ENGINE -------------

def _collect_micro_master_data():
    """
    Collect all micro-level signals needed for the micro master engine:
    - micro environment score/state
    - micro risk score/state
    - micro opportunity score/state
    - micro confidence score/state
    - micro forecast score/state
    - micro drift
    - micro momentum
    - micro cycle direction
    - micro cycle strength
    - micro volatility
    - micro instability
    - micro shock
    - micro turbulence
    """

    def safe_get(key, default=None):
        return st.session_state.get(key, default)

    data = {
        "micro_environment_score": safe_get("micro_environment_score"),
        "micro_environment_state": safe_get("micro_environment_state"),

        "micro_risk_score": safe_get("micro_risk_score"),
        "micro_risk_state": safe_get("micro_risk_state"),

        "micro_opportunity_score": safe_get("micro_opportunity_score"),
        "micro_opportunity_state": safe_get("micro_opportunity_state"),

        "micro_confidence_score": safe_get("micro_confidence_score"),
        "micro_confidence_state": safe_get("micro_confidence_state"),

        "micro_forecast_score": safe_get("micro_forecast_score"),
        "micro_forecast_state": safe_get("micro_forecast_state"),

        "micro_drift": safe_get("micro_drift"),
        "micro_momentum": safe_get("micro_momentum"),
        "micro_cycle_direction": safe_get("micro_cycle_direction"),
        "micro_cycle_strength": safe_get("micro_cycle_strength"),
        "micro_volatility": safe_get("micro_volatility"),
        "micro_instability": safe_get("micro_instability"),
        "micro_shock": safe_get("micro_shock"),
        "micro_turbulence": safe_get("micro_turbulence"),
    }

    return data


def _compute_micro_master_score(data):
    """
    Compute the unified micro master score.
    This is the authoritative micro-level signal.
    """

    env = data["micro_environment_score"] or 0
    risk = data["micro_risk_score"] or 0
    opp = data["micro_opportunity_score"] or 0
    conf = data["micro_confidence_score"] or 0
    fc = data["micro_forecast_score"] or 0

    drift = abs(data["micro_drift"] or 0)
    momentum = abs(data["micro_momentum"] or 0)
    cycle_dir = data["micro_cycle_direction"] or 0
    cycle_strength = data["micro_cycle_strength"] or 0

    vol = data["micro_volatility"] or 0
    instab = data["micro_instability"] or 0
    shock = data["micro_shock"] or 0
    turb = data["micro_turbulence"] or 0

    score = float(
        (env * 0.4 +
         opp * 0.5 +
         conf * 0.5 +
         fc * 0.6 +
         drift * 0.3 +
         momentum * 0.4 +
         cycle_dir * 0.4 +
         cycle_strength * 0.5)
        -
        (risk * 0.5 +
         vol * 0.3 +
         instab * 0.3 +
         shock * 0.4 +
         turb * 0.4)
    )

    return score


def _classify_micro_master_state(score):
    """
    Classify the unified micro master environment.
    """

    if score > 0.75:
        return "Strong Bullish Micro Environment"
    elif score > 0.35:
        return "Constructive Bullish Micro Environment"
    elif score > -0.15:
        return "Neutral Micro Environment"
    elif score > -0.55:
        return "Constructive Bearish Micro Environment"
    else:
        return "Strong Bearish Micro Environment"


def render_micro_master_engine():
    """
    Full UI for the micro master engine.
    """
    st.header("Micro Master Engine")
    st.caption("Synthesizes all micro engines into one unified micro master state.")

    data = _collect_micro_master_data()
    if not data:
        st.info("No micro master data available.")
        return

    score = _compute_micro_master_score(data)
    state = _classify_micro_master_state(score)

    # Save for downstream engines
    st.session_state["micro_master_score"] = score
    st.session_state["micro_master_state"] = state

    themed_card_container()
    st.markdown(f"""
    ## Micro Master State  
    **{state}**

    **Micro Master Score:** `{score:.4f}`
    """)

    themed_card_container()
    st.markdown("### Micro Master Inputs")
    st.json(data)

    st.success("Micro master analysis complete.")
# ------------- CHUNK 114: MICRO META ENGINE -------------

def _collect_micro_meta_data():
    """
    Collect all micro-level signals needed for the micro meta engine:
    - micro master score/state
    - micro environment score/state
    - micro risk score/state
    - micro opportunity score/state
    - micro confidence score/state
    - micro forecast score/state
    - micro drift
    - micro momentum
    - micro cycle direction
    - micro cycle strength
    - micro volatility
    - micro instability
    """

    def safe_get(key, default=None):
        return st.session_state.get(key, default)

    meta = {
        "micro_master_score": safe_get("micro_master_score"),
        "micro_master_state": safe_get("micro_master_state"),

        "micro_environment_score": safe_get("micro_environment_score"),
        "micro_environment_state": safe_get("micro_environment_state"),

        "micro_risk_score": safe_get("micro_risk_score"),
        "micro_risk_state": safe_get("micro_risk_state"),

        "micro_opportunity_score": safe_get("micro_opportunity_score"),
        "micro_opportunity_state": safe_get("micro_opportunity_state"),

        "micro_confidence_score": safe_get("micro_confidence_score"),
        "micro_confidence_state": safe_get("micro_confidence_state"),

        "micro_forecast_score": safe_get("micro_forecast_score"),
        "micro_forecast_state": safe_get("micro_forecast_state"),

        "micro_drift": safe_get("micro_drift"),
        "micro_momentum": safe_get("micro_momentum"),
        "micro_cycle_direction": safe_get("micro_cycle_direction"),
        "micro_cycle_strength": safe_get("micro_cycle_strength"),
        "micro_volatility": safe_get("micro_volatility"),
        "micro_instability": safe_get("micro_instability"),
    }

    return meta


def _compute_micro_meta_integrity(meta):
    """
    Compute the micro meta integrity score.
    Measures coherence vs contradiction across micro layers.
    """

    # Positive alignment factors
    env = meta["micro_environment_score"] or 0
    opp = meta["micro_opportunity_score"] or 0
    conf = meta["micro_confidence_score"] or 0
    fc = meta["micro_forecast_score"] or 0
    master = meta["micro_master_score"] or 0
    cycle_strength = meta["micro_cycle_strength"] or 0
    drift = abs(meta["micro_drift"] or 0)
    momentum = abs(meta["micro_momentum"] or 0)

    # Negative contradiction factors
    risk = meta["micro_risk_score"] or 0
    vol = meta["micro_volatility"] or 0
    instab = meta["micro_instability"] or 0

    integrity = float(
        (env * 0.4 +
         opp * 0.5 +
         conf * 0.5 +
         fc * 0.6 +
         master * 0.7 +
         cycle_strength * 0.4 +
         drift * 0.3 +
         momentum * 0.3)
        -
        (risk * 0.5 +
         vol * 0.3 +
         instab * 0.3)
    )

    return integrity


def _classify_micro_meta_state(score):
    """
    Classify the micro meta environment.
    """

    if score > 0.65:
        return "Micro Coherent Environment"
    elif score > -0.15:
        return "Micro Transitional Environment"
    else:
        return "Micro Degraded Environment"


def render_micro_meta_engine():
    """
    Full UI for the micro meta engine.
    """
    st.header("Micro Meta Engine")
    st.caption("Evaluates micro-level coherence, contradictions, and structural alignment.")

    meta = _collect_micro_meta_data()
    if not meta:
        st.info("No micro meta data available.")
        return

    score = _compute_micro_meta_integrity(meta)
    state = _classify_micro_meta_state(score)

    # Save for downstream engines
    st.session_state["micro_meta_score"] = score
    st.session_state["micro_meta_state"] = state

    themed_card_container()
    st.markdown(f"""
    ## Micro Meta State  
    **{state}**

    **Micro Meta Integrity Score:** `{score:.4f}`
    """)

    themed_card_container()
    st.markdown("### Micro Meta Inputs")
    st.json(meta)

    st.success("Micro meta analysis complete.")
# ------------- CHUNK 115: MICRO META-STABILITY ENGINE -------------

def _collect_micro_meta_stability_data():
    """
    Collect all micro-level signals needed for the micro meta-stability engine:
    - micro meta score/state
    - micro master score/state
    - micro environment score/state
    - micro risk score/state
    - micro opportunity score/state
    - micro confidence score/state
    - micro forecast score/state
    - micro volatility
    - micro instability
    - micro shock
    - micro turbulence
    - micro cycle strength
    """

    def safe_get(key, default=None):
        return st.session_state.get(key, default)

    data = {
        "micro_meta_score": safe_get("micro_meta_score"),
        "micro_meta_state": safe_get("micro_meta_state"),

        "micro_master_score": safe_get("micro_master_score"),
        "micro_master_state": safe_get("micro_master_state"),

        "micro_environment_score": safe_get("micro_environment_score"),
        "micro_environment_state": safe_get("micro_environment_state"),

        "micro_risk_score": safe_get("micro_risk_score"),
        "micro_risk_state": safe_get("micro_risk_state"),

        "micro_opportunity_score": safe_get("micro_opportunity_score"),
        "micro_opportunity_state": safe_get("micro_opportunity_state"),

        "micro_confidence_score": safe_get("micro_confidence_score"),
        "micro_confidence_state": safe_get("micro_confidence_state"),

        "micro_forecast_score": safe_get("micro_forecast_score"),
        "micro_forecast_state": safe_get("micro_forecast_state"),

        "micro_volatility": safe_get("micro_volatility"),
        "micro_instability": safe_get("micro_instability"),
        "micro_shock": safe_get("micro_shock"),
        "micro_turbulence": safe_get("micro_turbulence"),

        "micro_cycle_strength": safe_get("micro_cycle_strength"),
    }

    return data


def _compute_micro_meta_stability_score(data):
    """
    Compute the micro meta-stability score.
    Measures stability vs fragility across micro layers.
    """

    # Stability contributors
    meta = data["micro_meta_score"] or 0
    master = data["micro_master_score"] or 0
    env = data["micro_environment_score"] or 0
    opp = data["micro_opportunity_score"] or 0
    conf = data["micro_confidence_score"] or 0
    fc = data["micro_forecast_score"] or 0
    cycle_strength = data["micro_cycle_strength"] or 0

    # Fragility contributors
    risk = data["micro_risk_score"] or 0
    vol = data["micro_volatility"] or 0
    instab = data["micro_instability"] or 0
    shock = data["micro_shock"] or 0
    turb = data["micro_turbulence"] or 0

    score = float(
        (meta * 0.5 +
         master * 0.6 +
         env * 0.4 +
         opp * 0.4 +
         conf * 0.5 +
         fc * 0.5 +
         cycle_strength * 0.4)
        -
        (risk * 0.5 +
         vol * 0.4 +
         instab * 0.4 +
         shock * 0.5 +
         turb * 0.5)
    )

    return score


def _classify_micro_meta_stability_state(score):
    """
    Classify the micro meta-stability environment.
    """

    if score > 0.55:
        return "Micro Stable Environment"
    elif score > -0.15:
        return "Micro Fragile Environment"
    else:
        return "Micro Unstable Environment"


def render_micro_meta_stability_engine():
    """
    Full UI for the micro meta-stability engine.
    """
    st.header("Micro Meta-Stability Engine")
    st.caption("Evaluates micro-level stability, fragility, and resilience.")

    data = _collect_micro_meta_stability_data()
    if not data:
        st.info("No micro meta-stability data available.")
        return

    score = _compute_micro_meta_stability_score(data)
    state = _classify_micro_meta_stability_state(score)

    # Save for downstream engines
    st.session_state["micro_meta_stability_score"] = score
    st.session_state["micro_meta_stability_state"] = state

    themed_card_container()
    st.markdown(f"""
    ## Micro Meta-Stability State  
    **{state}**

    **Micro Meta-Stability Score:** `{score:.4f}`
    """)

    themed_card_container()
    st.markdown("### Micro Meta-Stability Inputs")
    st.json(data)

    st.success("Micro meta-stability analysis complete.")
# ------------- CHUNK 116: MICRO SUPER-META ENGINE -------------

def _collect_micro_super_meta_data():
    """
    Collect all micro-level signals needed for the micro super-meta engine:
    - micro master score/state
    - micro meta score/state
    - micro meta-stability score/state
    - micro environment score/state
    - micro risk score/state
    - micro opportunity score/state
    - micro confidence score/state
    - micro forecast score/state
    - micro volatility
    - micro instability
    - micro shock
    - micro turbulence
    - micro cycle strength
    """

    def safe_get(key, default=None):
        return st.session_state.get(key, default)

    data = {
        "micro_master_score": safe_get("micro_master_score"),
        "micro_master_state": safe_get("micro_master_state"),

        "micro_meta_score": safe_get("micro_meta_score"),
        "micro_meta_state": safe_get("micro_meta_state"),

        "micro_meta_stability_score": safe_get("micro_meta_stability_score"),
        "micro_meta_stability_state": safe_get("micro_meta_stability_state"),

        "micro_environment_score": safe_get("micro_environment_score"),
        "micro_risk_score": safe_get("micro_risk_score"),
        "micro_opportunity_score": safe_get("micro_opportunity_score"),
        "micro_confidence_score": safe_get("micro_confidence_score"),
        "micro_forecast_score": safe_get("micro_forecast_score"),

        "micro_volatility": safe_get("micro_volatility"),
        "micro_instability": safe_get("micro_instability"),
        "micro_shock": safe_get("micro_shock"),
        "micro_turbulence": safe_get("micro_turbulence"),

        "micro_cycle_strength": safe_get("micro_cycle_strength"),
    }

    return data


def _compute_micro_super_meta_score(data):
    """
    Compute the micro super-meta score.
    Measures system-wide micro coherence across master + meta + meta-stability.
    """

    master = data["micro_master_score"] or 0
    meta = data["micro_meta_score"] or 0
    meta_stab = data["micro_meta_stability_score"] or 0

    env = data["micro_environment_score"] or 0
    opp = data["micro_opportunity_score"] or 0
    conf = data["micro_confidence_score"] or 0
    fc = data["micro_forecast_score"] or 0
    cycle_strength = data["micro_cycle_strength"] or 0

    risk = data["micro_risk_score"] or 0
    vol = data["micro_volatility"] or 0
    instab = data["micro_instability"] or 0
    shock = data["micro_shock"] or 0
    turb = data["micro_turbulence"] or 0

    score = float(
        (master * 0.6 +
         meta * 0.5 +
         meta_stab * 0.6 +
         env * 0.4 +
         opp * 0.4 +
         conf * 0.5 +
         fc * 0.5 +
         cycle_strength * 0.4)
        -
        (risk * 0.5 +
         vol * 0.4 +
         instab * 0.4 +
         shock * 0.5 +
         turb * 0.5)
    )

    return score


def _classify_micro_super_meta_state(score):
    """
    Classify the micro super-meta environment.
    """

    if score > 0.55:
        return "Micro System-Aligned Environment"
    elif score > -0.15:
        return "Micro System-Mixed Environment"
    else:
        return "Micro System-Conflicted Environment"


def render_micro_super_meta_engine():
    """
    Full UI for the micro super-meta engine.
    """
    st.header("Micro Super-Meta Engine")
    st.caption("Evaluates system-wide micro coherence across master, meta, and meta-stability layers.")

    data = _collect_micro_super_meta_data()
    if not data:
        st.info("No micro super-meta data available.")
        return

    score = _compute_micro_super_meta_score(data)
    state = _classify_micro_super_meta_state(score)

    # Save for downstream engines
    st.session_state["micro_super_meta_score"] = score
    st.session_state["micro_super_meta_state"] = state

    themed_card_container()
    st.markdown(f"""
    ## Micro Super-Meta State  
    **{state}**

    **Micro Super-Meta Score:** `{score:.4f}`
    """)

    themed_card_container()
    st.markdown("### Micro Super-Meta Inputs")
    st.json(data)

    st.success("Micro super-meta analysis complete.")
# ------------- CHUNK 117: MICRO HYPER-META ENGINE -------------

def _collect_micro_hyper_meta_data():
    """
    Collect all micro-level signals needed for the micro hyper-meta engine:
    - micro super-meta score/state
    - micro meta-stability score/state
    - micro meta score/state
    - micro master score/state
    - micro environment score/state
    - micro risk score/state
    - micro opportunity score/state
    - micro confidence score/state
    - micro forecast score/state
    - micro volatility
    - micro instability
    - micro shock
    - micro turbulence
    - micro cycle strength
    """

    def safe_get(key, default=None):
        return st.session_state.get(key, default)

    data = {
        "micro_super_meta_score": safe_get("micro_super_meta_score"),
        "micro_super_meta_state": safe_get("micro_super_meta_state"),

        "micro_meta_stability_score": safe_get("micro_meta_stability_score"),
        "micro_meta_stability_state": safe_get("micro_meta_stability_state"),

        "micro_meta_score": safe_get("micro_meta_score"),
        "micro_meta_state": safe_get("micro_meta_state"),

        "micro_master_score": safe_get("micro_master_score"),
        "micro_master_state": safe_get("micro_master_state"),

        "micro_environment_score": safe_get("micro_environment_score"),
        "micro_risk_score": safe_get("micro_risk_score"),
        "micro_opportunity_score": safe_get("micro_opportunity_score"),
        "micro_confidence_score": safe_get("micro_confidence_score"),
        "micro_forecast_score": safe_get("micro_forecast_score"),

        "micro_volatility": safe_get("micro_volatility"),
        "micro_instability": safe_get("micro_instability"),
        "micro_shock": safe_get("micro_shock"),
        "micro_turbulence": safe_get("micro_turbulence"),

        "micro_cycle_strength": safe_get("micro_cycle_strength"),
    }

    return data


def _compute_micro_hyper_meta_score(data):
    """
    Compute the micro hyper-meta score.
    This measures the highest-level structural integrity of the micro system.
    """

    super_meta = data["micro_super_meta_score"] or 0
    meta_stab = data["micro_meta_stability_score"] or 0
    meta = data["micro_meta_score"] or 0
    master = data["micro_master_score"] or 0

    env = data["micro_environment_score"] or 0
    opp = data["micro_opportunity_score"] or 0
    conf = data["micro_confidence_score"] or 0
    fc = data["micro_forecast_score"] or 0
    cycle_strength = data["micro_cycle_strength"] or 0

    risk = data["micro_risk_score"] or 0
    vol = data["micro_volatility"] or 0
    instab = data["micro_instability"] or 0
    shock = data["micro_shock"] or 0
    turb = data["micro_turbulence"] or 0

    score = float(
        (super_meta * 0.7 +
         meta_stab * 0.6 +
         meta * 0.5 +
         master * 0.6 +
         env * 0.4 +
         opp * 0.4 +
         conf * 0.5 +
         fc * 0.5 +
         cycle_strength * 0.4)
        -
        (risk * 0.5 +
         vol * 0.4 +
         instab * 0.4 +
         shock * 0.5 +
         turb * 0.5)
    )

    return score


def _classify_micro_hyper_meta_state(score):
    """
    Classify the micro hyper-meta environment.
    """

    if score > 0.55:
        return "Micro System-Integrated Environment"
    elif score > -0.15:
        return "Micro System-Fragmented Environment"
    else:
        return "Micro System-Degraded Environment"


def render_micro_hyper_meta_engine():
    """
    Full UI for the micro hyper-meta engine.
    """
    st.header("Micro Hyper-Meta Engine")
    st.caption("Evaluates highest-level micro system integrity across all micro engines.")

    data = _collect_micro_hyper_meta_data()
    if not data:
        st.info("No micro hyper-meta data available.")
        return

    score = _compute_micro_hyper_meta_score(data)
    state = _classify_micro_hyper_meta_state(score)

    # Save for downstream engines
    st.session_state["micro_hyper_meta_score"] = score
    st.session_state["micro_hyper_meta_state"] = state

    themed_card_container()
    st.markdown(f"""
    ## Micro Hyper-Meta State  
    **{state}**

    **Micro Hyper-Meta Score:** `{score:.4f}`
    """)

    themed_card_container()
    st.markdown("### Micro Hyper-Meta Inputs")
    st.json(data)

    st.success("Micro hyper-meta analysis complete.")
# ------------- CHUNK 118: MICRO OMNI ENGINE -------------

def _collect_micro_omni_data():
    """
    Collect all micro-level signals needed for the micro omni engine:
    - micro hyper-meta score/state
    - micro super-meta score/state
    - micro meta-stability score/state
    - micro meta score/state
    - micro master score/state
    - micro environment score/state
    - micro risk score/state
    - micro opportunity score/state
    - micro confidence score/state
    - micro forecast score/state
    - micro drift
    - micro momentum
    - micro cycle direction
    - micro cycle strength
    - micro volatility
    - micro instability
    - micro shock
    - micro turbulence
    """

    def safe_get(key, default=None):
        return st.session_state.get(key, default)

    data = {
        "micro_hyper_meta_score": safe_get("micro_hyper_meta_score"),
        "micro_hyper_meta_state": safe_get("micro_hyper_meta_state"),

        "micro_super_meta_score": safe_get("micro_super_meta_score"),
        "micro_super_meta_state": safe_get("micro_super_meta_state"),

        "micro_meta_stability_score": safe_get("micro_meta_stability_score"),
        "micro_meta_stability_state": safe_get("micro_meta_stability_state"),

        "micro_meta_score": safe_get("micro_meta_score"),
        "micro_meta_state": safe_get("micro_meta_state"),

        "micro_master_score": safe_get("micro_master_score"),
        "micro_master_state": safe_get("micro_master_state"),

        "micro_environment_score": safe_get("micro_environment_score"),
        "micro_environment_state": safe_get("micro_environment_state"),

        "micro_risk_score": safe_get("micro_risk_score"),
        "micro_risk_state": safe_get("micro_risk_state"),

        "micro_opportunity_score": safe_get("micro_opportunity_score"),
        "micro_opportunity_state": safe_get("micro_opportunity_state"),

        "micro_confidence_score": safe_get("micro_confidence_score"),
        "micro_confidence_state": safe_get("micro_confidence_state"),

        "micro_forecast_score": safe_get("micro_forecast_score"),
        "micro_forecast_state": safe_get("micro_forecast_state"),

        "micro_drift": safe_get("micro_drift"),
        "micro_momentum": safe_get("micro_momentum"),
        "micro_cycle_direction": safe_get("micro_cycle_direction"),
        "micro_cycle_strength": safe_get("micro_cycle_strength"),

        "micro_volatility": safe_get("micro_volatility"),
        "micro_instability": safe_get("micro_instability"),
        "micro_shock": safe_get("micro_shock"),
        "micro_turbulence": safe_get("micro_turbulence"),
    }

    return data


def _compute_micro_omni_score(data):
    """
    Compute the micro omni score.
    This is the highest-level synthesis of the entire micro system.
    """

    hyper = data["micro_hyper_meta_score"] or 0
    super_meta = data["micro_super_meta_score"] or 0
    meta_stab = data["micro_meta_stability_score"] or 0
    meta = data["micro_meta_score"] or 0
    master = data["micro_master_score"] or 0

    env = data["micro_environment_score"] or 0
    opp = data["micro_opportunity_score"] or 0
    conf = data["micro_confidence_score"] or 0
    fc = data["micro_forecast_score"] or 0
    cycle_strength = data["micro_cycle_strength"] or 0

    drift = abs(data["micro_drift"] or 0)
    momentum = abs(data["micro_momentum"] or 0)

    risk = data["micro_risk_score"] or 0
    vol = data["micro_volatility"] or 0
    instab = data["micro_instability"] or 0
    shock = data["micro_shock"] or 0
    turb = data["micro_turbulence"] or 0

    score = float(
        (hyper * 0.8 +
         super_meta * 0.7 +
         meta_stab * 0.6 +
         meta * 0.5 +
         master * 0.6 +
         env * 0.4 +
         opp * 0.4 +
         conf * 0.5 +
         fc * 0.5 +
         cycle_strength * 0.4 +
         drift * 0.3 +
         momentum * 0.3)
        -
        (risk * 0.5 +
         vol * 0.4 +
         instab * 0.4 +
         shock * 0.5 +
         turb * 0.5)
    )

    return score


def _classify_micro_omni_state(score):
    """
    Classify the micro omni environment.
    """

    if score > 0.55:
        return "Micro Omni-Positive Environment"
    elif score > -0.15:
        return "Micro Omni-Neutral Environment"
    else:
        return "Micro Omni-Negative Environment"


def render_micro_omni_engine():
    """
    Full UI for the micro omni engine.
    """
    st.header("Micro Omni Engine")
    st.caption("Final synthesis of the entire micro system into one unified omni state.")

    data = _collect_micro_omni_data()
    if not data:
        st.info("No micro omni data available.")
        return

    score = _compute_micro_omni_score(data)
    state = _classify_micro_omni_state(score)

    # Save final micro omni outputs
    st.session_state["micro_omni_score"] = score
    st.session_state["micro_omni_state"] = state

    themed_card_container()
    st.markdown(f"""
    ## Micro Omni State  
    **{state}**

    **Micro Omni Score:** `{score:.4f}`
    """)

    themed_card_container()
    st.markdown("### Micro Omni Inputs")
    st.json(data)

    st.success("Micro omni analysis complete.")
# ------------- CHUNK 119: MICRO FINAL INTEGRATION LAYER (MICRO SEAL) -------------

def _collect_micro_seal_data():
    """
    Collect all final micro-level outputs for sealing:
    - micro omni score/state
    - micro hyper-meta score/state
    - micro super-meta score/state
    - micro meta-stability score/state
    - micro meta score/state
    - micro master score/state
    - micro environment score/state
    - micro risk score/state
    - micro opportunity score/state
    - micro confidence score/state
    - micro forecast score/state
    """

    def safe_get(key, default=None):
        return st.session_state.get(key, default)

    data = {
        "micro_omni_score": safe_get("micro_omni_score"),
        "micro_omni_state": safe_get("micro_omni_state"),

        "micro_hyper_meta_score": safe_get("micro_hyper_meta_score"),
        "micro_hyper_meta_state": safe_get("micro_hyper_meta_state"),

        "micro_super_meta_score": safe_get("micro_super_meta_score"),
        "micro_super_meta_state": safe_get("micro_super_meta_state"),

        "micro_meta_stability_score": safe_get("micro_meta_stability_score"),
        "micro_meta_stability_state": safe_get("micro_meta_stability_state"),

        "micro_meta_score": safe_get("micro_meta_score"),
        "micro_meta_state": safe_get("micro_meta_state"),

        "micro_master_score": safe_get("micro_master_score"),
        "micro_master_state": safe_get("micro_master_state"),

        "micro_environment_score": safe_get("micro_environment_score"),
        "micro_environment_state": safe_get("micro_environment_state"),

        "micro_risk_score": safe_get("micro_risk_score"),
        "micro_risk_state": safe_get("micro_risk_state"),

        "micro_opportunity_score": safe_get("micro_opportunity_score"),
        "micro_opportunity_state": safe_get("micro_opportunity_state"),

        "micro_confidence_score": safe_get("micro_confidence_score"),
        "micro_confidence_state": safe_get("micro_confidence_state"),

        "micro_forecast_score": safe_get("micro_forecast_score"),
        "micro_forecast_state": safe_get("micro_forecast_state"),
    }

    return data


def _normalize_micro_scores(data):
    """
    Normalize all micro scores into a consistent 0–1 range.
    """

    def normalize(x):
        if x is None:
            return None
        return max(0.0, min(1.0, (x + 1) / 2))

    normalized = {}
    for key, value in data.items():
        if key.endswith("_score"):
            normalized[key + "_normalized"] = normalize(value)

    return normalized


def _build_micro_export_object(data, normalized):
    """
    Build the final micro export object.
    This is consumed by:
    - Macro–Micro Fusion Engine
    - Slip Engine
    - AI Commentary Engine
    - Analytics Layers
    """

    export = {
        "raw": data,
        "normalized": normalized,
        "micro_final_state": data.get("micro_omni_state"),
        "micro_final_score": data.get("micro_omni_score"),
    }

    return export


def render_micro_final_integration_layer():
    """
    Full UI for the micro final integration layer.
    """
    st.header("Micro Final Integration Layer (Micro Seal)")
    st.caption("Seals the entire micro system into a unified exportable structure.")

    data = _collect_micro_seal_data()
    if not data:
        st.info("No micro seal data available.")
        return

    normalized = _normalize_micro_scores(data)
    export = _build_micro_export_object(data, normalized)

    # Save final micro export
    st.session_state["micro_export"] = export

    themed_card_container()
    st.markdown("## Micro Final State")
    st.markdown(f"**{export['micro_final_state']}**")

    themed_card_container()
    st.markdown("### Micro Final Score")
    st.markdown(f"`{export['micro_final_score']:.4f}`")

    themed_card_container()
    st.markdown("### Micro Export Object")
    st.json(export)

    st.success("Micro system sealed successfully.")
# ------------- CHUNK 120: MACRO–MICRO FUSION ENGINE -------------

def _collect_fusion_data():
    """
    Collect macro and micro export objects.
    These must already exist:
    - st.session_state["macro_export"]
    - st.session_state["micro_export"]
    """

    macro = st.session_state.get("macro_export")
    micro = st.session_state.get("micro_export")

    return macro, micro


def _compute_macro_micro_alignment(macro, micro):
    """
    Compute alignment between macro and micro systems.
    Measures:
    - directional alignment
    - state alignment
    - normalized score alignment
    """

    try:
        macro_score = macro["normalized"]["macro_omni_score_normalized"]
        micro_score = micro["normalized"]["micro_omni_score_normalized"]
    except:
        macro_score = 0.5
        micro_score = 0.5

    alignment = 1 - abs(macro_score - micro_score)
    return alignment


def _compute_macro_micro_fusion_score(macro, micro, alignment):
    """
    Compute the unified macro–micro fusion score.
    """

    try:
        macro_raw = macro["raw"]["macro_omni_score"]
        micro_raw = micro["raw"]["micro_omni_score"]
    except:
        macro_raw = 0
        micro_raw = 0

    score = float(
        (macro_raw * 0.55) +
        (micro_raw * 0.45) +
        (alignment * 0.6)
    )

    return score


def _classify_fusion_state(score):
    """
    Classify the unified macro–micro fusion environment.
    """

    if score > 0.65:
        return "Unified Bullish Environment"
    elif score > 0.15:
        return "Constructive Unified Environment"
    elif score > -0.15:
        return "Neutral Unified Environment"
    elif score > -0.55:
        return "Constructive Bearish Unified Environment"
    else:
        return "Unified Bearish Environment"


def _build_fusion_export(macro, micro, score, state, alignment):
    """
    Build the final fusion export object.
    """

    export = {
        "macro": macro,
        "micro": micro,
        "fusion_score": score,
        "fusion_state": state,
        "macro_micro_alignment": alignment,
    }

    return export


def render_macro_micro_fusion_engine():
    """
    Full UI for the macro–micro fusion engine.
    """
    st.header("Macro–Micro Fusion Engine")
    st.caption("Unifies macro and micro systems into a single fused environment.")

    macro, micro = _collect_fusion_data()
    if not macro or not micro:
        st.info("Macro or Micro export objects not found.")
        return

    alignment = _compute_macro_micro_alignment(macro, micro)
    score = _compute_macro_micro_fusion_score(macro, micro, alignment)
    state = _classify_fusion_state(score)

    export = _build_fusion_export(macro, micro, score, state, alignment)

    # Save fusion export
    st.session_state["fusion_export"] = export

    themed_card_container()
    st.markdown(f"""
    ## Unified Fusion State  
    **{state}**

    **Fusion Score:** `{score:.4f}`  
    **Macro–Micro Alignment:** `{alignment:.4f}`
    """)

    themed_card_container()
    st.markdown("### Fusion Export Object")
    st.json(export)

    st.success("Macro–micro fusion complete.")
# ------------- CHUNK 121: SLIP INTEGRATION LAYER 2.0 -------------

def _collect_slip_inputs():
    """
    Collect all upstream exports:
    - macro_export
    - micro_export
    - fusion_export
    """

    macro = st.session_state.get("macro_export")
    micro = st.session_state.get("micro_export")
    fusion = st.session_state.get("fusion_export")

    return macro, micro, fusion


def _compute_slip_probability(fusion):
    """
    Convert fusion score into slip-ready probability.
    """

    score = fusion.get("fusion_score", 0)
    prob = max(0.0, min(1.0, (score + 1) / 2))
    return prob


def _compute_slip_confidence(macro, micro):
    """
    Combine macro + micro confidence into slip confidence.
    """

    try:
        macro_conf = macro["normalized"]["macro_confidence_score_normalized"]
        micro_conf = micro["normalized"]["micro_confidence_score_normalized"]
    except:
        macro_conf = 0.5
        micro_conf = 0.5

    confidence = (macro_conf * 0.55) + (micro_conf * 0.45)
    return confidence


def _compute_slip_environment_tags(macro, micro, fusion):
    """
    Generate environment tags for the slip engine.
    """

    tags = [
        macro.get("raw", {}).get("macro_omni_state", "Unknown Macro State"),
        micro.get("raw", {}).get("micro_omni_state", "Unknown Micro State"),
        fusion.get("fusion_state", "Unknown Fusion State"),
    ]

    return tags


def _compute_slip_risk_flag(macro, micro):
    """
    Determine slip-level risk flag.
    """

    try:
        macro_risk = macro["raw"]["macro_risk_score"]
        micro_risk = micro["raw"]["micro_risk_score"]
    except:
        macro_risk = 0
        micro_risk = 0

    combined = (macro_risk * 0.6) + (micro_risk * 0.4)

    if combined > 0.5:
        return "High Risk"
    elif combined > 0.15:
        return "Moderate Risk"
    else:
        return "Low Risk"


def _compute_slip_opportunity_flag(macro, micro):
    """
    Determine slip-level opportunity flag.
    """

    try:
        macro_opp = macro["raw"]["macro_opportunity_score"]
        micro_opp = micro["raw"]["micro_opportunity_score"]
    except:
        macro_opp = 0
        micro_opp = 0

    combined = (macro_opp * 0.55) + (micro_opp * 0.45)

    if combined > 0.5:
        return "High Opportunity"
    elif combined > 0.15:
        return "Moderate Opportunity"
    else:
        return "Low Opportunity"


def _build_slip_export_object(prob, conf, tags, risk_flag, opp_flag, fusion):
    """
    Build the final slip export object.
    """

    export = {
        "slip_probability": prob,
        "slip_confidence": conf,
        "slip_environment_tags": tags,
        "slip_risk_flag": risk_flag,
        "slip_opportunity_flag": opp_flag,
        "fusion_state": fusion.get("fusion_state"),
        "fusion_score": fusion.get("fusion_score"),
    }

    return export


def render_slip_integration_layer():
    """
    Full UI for the slip integration layer.
    """
    st.header("Slip Integration Layer 2.0")
    st.caption("Transforms macro + micro + fusion into slip-ready signals.")

    macro, micro, fusion = _collect_slip_inputs()
    if not macro or not micro or not fusion:
        st.info("Missing macro, micro, or fusion export objects.")
        return

    prob = _compute_slip_probability(fusion)
    conf = _compute_slip_confidence(macro, micro)
    tags = _compute_slip_environment_tags(macro, micro, fusion)
    risk_flag = _compute_slip_risk_flag(macro, micro)
    opp_flag = _compute_slip_opportunity_flag(macro, micro)

    export = _build_slip_export_object(prob, conf, tags, risk_flag, opp_flag, fusion)

    # Save slip export
    st.session_state["slip_export"] = export

    themed_card_container()
    st.markdown("## Slip Probability")
    st.markdown(f"`{prob:.4f}`")

    themed_card_container()
    st.markdown("## Slip Confidence")
    st.markdown(f"`{conf:.4f}`")

    themed_card_container()
    st.markdown("### Slip Environment Tags")
    st.json(tags)

    themed_card_container()
    st.markdown("### Slip Export Object")
    st.json(export)

    st.success("Slip integration complete.")
# ------------- CHUNK 122: AI COMMENTARY ENGINE 2.0 -------------

def _collect_commentary_inputs():
    """
    Collect all upstream exports:
    - macro_export
    - micro_export
    - fusion_export
    - slip_export
    """

    macro = st.session_state.get("macro_export")
    micro = st.session_state.get("micro_export")
    fusion = st.session_state.get("fusion_export")
    slip = st.session_state.get("slip_export")

    return macro, micro, fusion, slip


def _build_commentary_prompt(macro, micro, fusion, slip):
    """
    Build a structured prompt for Qwen to generate elite commentary.
    """

    prompt = f"""
You are an elite sports betting analyst.

You are given the following system outputs:

MACRO EXPORT:
{json.dumps(macro, indent=2)}

MICRO EXPORT:
{json.dumps(micro, indent=2)}

FUSION EXPORT:
{json.dumps(fusion, indent=2)}

SLIP EXPORT:
{json.dumps(slip, indent=2)}

TASKS:
1. Provide a high-signal, concise commentary explaining:
   - macro environment
   - micro environment
   - fusion environment
   - slip probability
   - slip confidence
   - risk flag
   - opportunity flag

2. Explain the dominant forces driving the environment:
   - momentum
   - drift
   - cycles
   - volatility
   - instability
   - shock/turbulence

3. Provide a final recommendation summary (5–10 bullets).

4. Tone:
   - elite analyst
   - authoritative
   - concise
   - no fluff
   - no filler
   - high signal density

5. Keep output under 350 words.
"""

    return prompt


def _generate_commentary(macro, micro, fusion, slip):
    """
    Call Qwen to generate commentary.
    """

    if not st.session_state.settings.get("enable_qwen", True):
        return "Qwen is disabled in settings."

    prompt = _build_commentary_prompt(macro, micro, fusion, slip)
    response = _call_qwen(prompt)
    return response or "No commentary generated."


def render_ai_commentary_engine():
    """
    Full UI for the AI Commentary Engine 2.0.
    """
    st.header("AI Commentary Engine 2.0")
    st.caption("Generates elite, high-signal commentary from macro + micro + fusion + slip.")

    macro, micro, fusion, slip = _collect_commentary_inputs()
    if not macro or not micro or not fusion or not slip:
        st.info("Missing macro, micro, fusion, or slip export objects.")
        return

    commentary = _generate_commentary(macro, micro, fusion, slip)

    themed_card_container()
    st.markdown("## AI Commentary")
    st.markdown(commentary)

    themed_card_container()
    st.markdown("### Commentary Inputs")
    st.json({
        "macro": macro,
        "micro": micro,
        "fusion": fusion,
        "slip": slip
    })

    st.success("AI commentary generation complete.")
# ------------- CHUNK 123: SLIP ENGINE 2.0 (BET GENERATOR) -------------

def _collect_slip_engine_inputs():
    """
    Collect all upstream exports:
    - fusion_export
    - slip_export
    - macro_export
    - micro_export
    """

    fusion = st.session_state.get("fusion_export")
    slip = st.session_state.get("slip_export")
    macro = st.session_state.get("macro_export")
    micro = st.session_state.get("micro_export")

    return fusion, slip, macro, micro


def _compute_final_bet_score(fusion, slip):
    """
    Combine fusion score + slip probability + slip confidence
    into a unified bet score.
    """

    fusion_score = fusion.get("fusion_score", 0)
    prob = slip.get("slip_probability", 0.5)
    conf = slip.get("slip_confidence", 0.5)

    final_score = float(
        (fusion_score * 0.55) +
        (prob * 0.25) +
        (conf * 0.20)
    )

    return final_score


def _classify_bet_decision(score, risk_flag, opp_flag):
    """
    Convert final score + risk/opportunity flags into a bet/no-bet decision.
    """

    # Risk overrides
    if risk_flag == "High Risk" and score < 0.65:
        return "NO BET"

    # Opportunity overrides
    if opp_flag == "High Opportunity" and score > 0.25:
        return "BET"

    # Score-based logic
    if score > 0.55:
        return "BET"
    elif score > 0.15:
        return "LEAN BET"
    else:
        return "NO BET"


def _build_slip_card(fusion, slip, final_score, decision):
    """
    Build the final slip card object.
    """

    card = {
        "decision": decision,
        "final_score": final_score,
        "slip_probability": slip.get("slip_probability"),
        "slip_confidence": slip.get("slip_confidence"),
        "risk_flag": slip.get("slip_risk_flag"),
        "opportunity_flag": slip.get("slip_opportunity_flag"),
        "fusion_state": fusion.get("fusion_state"),
        "fusion_score": fusion.get("fusion_score"),
        "environment_tags": slip.get("slip_environment_tags"),
    }

    return card


def render_slip_engine():
    """
    Full UI for the Slip Engine 2.0.
    """
    st.header("Slip Engine 2.0 (Bet Generator)")
    st.caption("Generates the final bet card using fusion + slip + macro + micro signals.")

    fusion, slip, macro, micro = _collect_slip_engine_inputs()
    if not fusion or not slip or not macro or not micro:
        st.info("Missing fusion, slip, macro, or micro export objects.")
        return

    final_score = _compute_final_bet_score(fusion, slip)
    decision = _classify_bet_decision(
        final_score,
        slip.get("slip_risk_flag"),
        slip.get("slip_opportunity_flag")
    )

    card = _build_slip_card(fusion, slip, final_score, decision)

    # Save slip card
    st.session_state["slip_card"] = card

    themed_card_container()
    st.markdown(f"## Final Decision: **{decision}**")

    themed_card_container()
    st.markdown("### Final Bet Score")
    st.markdown(f"`{final_score:.4f}`")

    themed_card_container()
    st.markdown("### Slip Card")
    st.json(card)

    st.success("Slip Engine 2.0 complete.")
# ------------- CHUNK 124: FINAL DECISION ENGINE (DECISION BRAIN 2.0) -------------

def _collect_final_decision_inputs():
    """
    Collect all upstream objects:
    - slip_card
    - fusion_export
    - macro_export
    - micro_export
    """

    slip_card = st.session_state.get("slip_card")
    fusion = st.session_state.get("fusion_export")
    macro = st.session_state.get("macro_export")
    micro = st.session_state.get("micro_export")

    return slip_card, fusion, macro, micro


def _apply_global_safety_checks(slip_card, fusion, macro, micro):
    """
    Apply global vetoes and safety rules.
    """

    final_score = slip_card.get("final_score", 0)
    risk_flag = slip_card.get("risk_flag", "Low Risk")

    # Extract volatility/instability/shock/turbulence
    vol = micro["raw"].get("micro_volatility", 0)
    instab = micro["raw"].get("micro_instability", 0)
    shock = micro["raw"].get("micro_shock", 0)
    turb = micro["raw"].get("micro_turbulence", 0)

    # Extract macro–micro alignment
    alignment = fusion.get("macro_micro_alignment", 0)

    # Global veto: extreme instability
    if instab > 0.65 or shock > 0.55 or turb > 0.55:
        return "NO BET (System Instability Veto)"

    # Global veto: extreme volatility
    if vol > 0.70:
        return "NO BET (Volatility Veto)"

    # Global veto: macro–micro conflict
    if alignment < 0.25:
        return "NO BET (Macro–Micro Conflict)"

    # Global veto: high risk + low score
    if risk_flag == "High Risk" and final_score < 0.70:
        return "NO BET (High Risk Veto)"

    return None  # No veto triggered


def _apply_final_decision_logic(slip_card):
    """
    If no vetoes triggered, finalize the decision.
    """

    decision = slip_card.get("decision", "NO BET")
    final_score = slip_card.get("final_score", 0)

    # Strengthen decision based on score
    if decision == "BET" and final_score > 0.75:
        return "STRONG BET"

    if decision == "LEAN BET" and final_score > 0.55:
        return "BET"

    return decision


def _build_final_decision_object(slip_card, final_decision, veto_reason=None):
    """
    Build the final decision object.
    """

    return {
        "final_decision": final_decision,
        "veto_reason": veto_reason,
        "slip_card": slip_card,
        "final_score": slip_card.get("final_score"),
        "risk_flag": slip_card.get("risk_flag"),
        "opportunity_flag": slip_card.get("opportunity_flag"),
        "fusion_state": slip_card.get("fusion_state"),
        "environment_tags": slip_card.get("environment_tags"),
    }


def render_final_decision_engine():
    """
    Full UI for the Final Decision Engine.
    """
    st.header("Final Decision Engine (Decision Brain 2.0)")
    st.caption("Applies global safety rules, overrides, and final decision logic.")

    slip_card, fusion, macro, micro = _collect_final_decision_inputs()
    if not slip_card or not fusion or not macro or not micro:
        st.info("Missing slip card, fusion, macro, or micro export objects.")
        return

    # Step 1: Apply global vetoes
    veto = _apply_global_safety_checks(slip_card, fusion, macro, micro)

    if veto:
        final_decision = "NO BET"
        final_obj = _build_final_decision_object(slip_card, final_decision, veto)
    else:
        # Step 2: Apply final decision logic
        final_decision = _apply_final_decision_logic(slip_card)
        final_obj = _build_final_decision_object(slip_card, final_decision)

    # Save final decision
    st.session_state["final_decision"] = final_obj

    themed_card_container()
    st.markdown(f"## Final Decision: **{final_obj['final_decision']}**")

    if final_obj["veto_reason"]:
        st.error(f"**Veto Reason:** {final_obj['veto_reason']}")

    themed_card_container()
    st.markdown("### Final Decision Object")
    st.json(final_obj)

    st.success("Final Decision Engine complete.")
# ------------- CHUNK 125: RISK MANAGER 2.0 (UNIT SIZING + EXPOSURE CONTROL) -------------

def _collect_risk_manager_inputs():
    """
    Collect all upstream objects:
    - final_decision
    - slip_card
    - fusion_export
    - macro_export
    - micro_export
    """

    final_decision = st.session_state.get("final_decision")
    slip_card = st.session_state.get("slip_card")
    fusion = st.session_state.get("fusion_export")
    macro = st.session_state.get("macro_export")
    micro = st.session_state.get("micro_export")

    return final_decision, slip_card, fusion, macro, micro


def _compute_base_unit(final_decision):
    """
    Base unit sizing based on decision strength.
    """

    decision = final_decision.get("final_decision", "NO BET")

    if decision == "STRONG BET":
        return 1.50
    if decision == "BET":
        return 1.00
    if decision == "LEAN BET":
        return 0.50

    return 0.00  # NO BET


def _apply_risk_modifiers(base_unit, slip_card, micro):
    """
    Adjust unit size based on risk, volatility, instability, shock, turbulence.
    """

    risk_flag = slip_card.get("risk_flag", "Low Risk")

    vol = micro["raw"].get("micro_volatility", 0)
    instab = micro["raw"].get("micro_instability", 0)
    shock = micro["raw"].get("micro_shock", 0)
    turb = micro["raw"].get("micro_turbulence", 0)

    unit = base_unit

    # Risk flag adjustments
    if risk_flag == "High Risk":
        unit *= 0.40
    elif risk_flag == "Moderate Risk":
        unit *= 0.70

    # Volatility adjustments
    if vol > 0.60:
        unit *= 0.60
    elif vol > 0.40:
        unit *= 0.80

    # Instability adjustments
    if instab > 0.50:
        unit *= 0.50

    # Shock/turbulence adjustments
    if shock > 0.45 or turb > 0.45:
        unit *= 0.60

    return unit


def _apply_opportunity_modifiers(unit, slip_card):
    """
    Boost unit size based on opportunity.
    """

    opp_flag = slip_card.get("opportunity_flag", "Low Opportunity")

    if opp_flag == "High Opportunity":
        unit *= 1.25
    elif opp_flag == "Moderate Opportunity":
        unit *= 1.10

    return unit


def _apply_confidence_modifiers(unit, slip_card):
    """
    Adjust unit size based on slip confidence.
    """

    conf = slip_card.get("slip_confidence", 0.5)

    if conf > 0.75:
        unit *= 1.20
    elif conf > 0.60:
        unit *= 1.10
    elif conf < 0.40:
        unit *= 0.80

    return unit


def _finalize_unit_size(unit):
    """
    Clamp unit size to safe bounds.
    """

    unit = max(0.0, min(unit, 2.0))  # Never exceed 2 units
    return round(unit, 2)


def _build_risk_manager_export(final_decision, unit):
    """
    Build the final risk manager export object.
    """

    return {
        "final_decision": final_decision.get("final_decision"),
        "veto_reason": final_decision.get("veto_reason"),
        "unit_size": unit,
        "slip_card": final_decision.get("slip_card"),
    }


def render_risk_manager():
    """
    Full UI for the Risk Manager 2.0.
    """
    st.header("Risk Manager 2.0 (Unit Sizing + Exposure Control)")
    st.caption("Determines how much to bet based on risk, volatility, confidence, and opportunity.")

    final_decision, slip_card, fusion, macro, micro = _collect_risk_manager_inputs()
    if not final_decision or not slip_card or not fusion or not macro or not micro:
        st.info("Missing final decision, slip card, fusion, macro, or micro export objects.")
        return

    # Step 1: Base unit from decision strength
    base_unit = _compute_base_unit(final_decision)

    # Step 2: Apply risk modifiers
    unit = _apply_risk_modifiers(base_unit, slip_card, micro)

    # Step 3: Apply opportunity modifiers
    unit = _apply_opportunity_modifiers(unit, slip_card)

    # Step 4: Apply confidence modifiers
    unit = _apply_confidence_modifiers(unit, slip_card)

    # Step 5: Final clamp
    unit = _finalize_unit_size(unit)

    export = _build_risk_manager_export(final_decision, unit)

    # Save risk manager export
    st.session_state["risk_export"] = export

    themed_card_container()
    st.markdown(f"## Unit Size: **{unit} units**")

    themed_card_container()
    st.markdown("### Risk Manager Export")
    st.json(export)

    st.success("Risk Manager 2.0 complete.")
# ------------- CHUNK 126: OPPORTUNITY ENGINE 2.0 -------------

def _collect_opportunity_inputs():
    """
    Collect all upstream objects:
    - macro_export
    - micro_export
    - fusion_export
    - slip_export
    - risk_export
    """

    macro = st.session_state.get("macro_export")
    micro = st.session_state.get("micro_export")
    fusion = st.session_state.get("fusion_export")
    slip = st.session_state.get("slip_export")
    risk = st.session_state.get("risk_export")

    return macro, micro, fusion, slip, risk


def _compute_opportunity_score(macro, micro, fusion, slip):
    """
    Compute the unified opportunity score.
    """

    try:
        macro_opp = macro["raw"]["macro_opportunity_score"]
        micro_opp = micro["raw"]["micro_opportunity_score"]
    except:
        macro_opp = 0
        micro_opp = 0

    fusion_score = fusion.get("fusion_score", 0)
    slip_prob = slip.get("slip_probability", 0.5)
    slip_conf = slip.get("slip_confidence", 0.5)

    score = float(
        (macro_opp * 0.35) +
        (micro_opp * 0.35) +
        (fusion_score * 0.20) +
        (slip_prob * 0.05) +
        (slip_conf * 0.05)
    )

    return score


def _classify_opportunity_state(score):
    """
    Classify the opportunity environment.
    """

    if score > 0.65:
        return "High Opportunity Environment"
    elif score > 0.25:
        return "Moderate Opportunity Environment"
    else:
        return "Low Opportunity Environment"


def _compute_opportunity_alignment(macro, micro):
    """
    Measure macro–micro opportunity alignment.
    """

    try:
        macro_opp = macro["normalized"]["macro_opportunity_score_normalized"]
        micro_opp = micro["normalized"]["micro_opportunity_score_normalized"]
    except:
        return 0.5

    alignment = 1 - abs(macro_opp - micro_opp)
    return alignment


def _build_opportunity_export(score, state, alignment):
    """
    Build the final opportunity export object.
    """

    return {
        "opportunity_score": score,
        "opportunity_state": state,
        "opportunity_alignment": alignment,
    }


def render_opportunity_engine():
    """
    Full UI for the Opportunity Engine 2.0.
    """
    st.header("Opportunity Engine 2.0")
    st.caption("Identifies and quantifies the highest-value opportunities in the environment.")

    macro, micro, fusion, slip, risk = _collect_opportunity_inputs()
    if not macro or not micro or not fusion or not slip or not risk:
        st.info("Missing macro, micro, fusion, slip, or risk export objects.")
        return

    score = _compute_opportunity_score(macro, micro, fusion, slip)
    state = _classify_opportunity_state(score)
    alignment = _compute_opportunity_alignment(macro, micro)

    export = _build_opportunity_export(score, state, alignment)

    # Save opportunity export
    st.session_state["opportunity_export"] = export

    themed_card_container()
    st.markdown(f"## Opportunity State: **{state}**")

    themed_card_container()
    st.markdown("### Opportunity Score")
    st.markdown(f"`{score:.4f}`")

    themed_card_container()
    st.markdown("### Opportunity Alignment")
    st.markdown(f"`{alignment:.4f}`")

    themed_card_container()
    st.markdown("### Opportunity Export Object")
    st.json(export)

    st.success("Opportunity Engine 2.0 complete.")
# ------------- CHUNK 127: PARLAY ENGINE 2.0 -------------

def _collect_parlay_inputs():
    """
    Collect all upstream objects:
    - slip_card (current play)
    - risk_export
    - opportunity_export
    - fusion_export
    - macro_export
    - micro_export

    In the future, this will collect multiple slip cards (multi-game).
    """

    slip = st.session_state.get("slip_card")
    risk = st.session_state.get("risk_export")
    opp = st.session_state.get("opportunity_export")
    fusion = st.session_state.get("fusion_export")
    macro = st.session_state.get("macro_export")
    micro = st.session_state.get("micro_export")

    return slip, risk, opp, fusion, macro, micro


def _compute_leg_quality(slip, risk, opp):
    """
    Compute quality of a single leg.
    """

    final_score = slip.get("final_score", 0)
    unit = risk.get("unit_size", 0)
    opp_score = opp.get("opportunity_score", 0)

    quality = float(
        (final_score * 0.50) +
        (unit * 0.30) +
        (opp_score * 0.20)
    )

    return quality


def _compute_correlation_penalty(macro, micro):
    """
    Penalize parlays when macro–micro signals are unstable or conflicting.
    """

    try:
        macro_state = macro["raw"]["macro_omni_state"]
        micro_state = micro["raw"]["micro_omni_state"]
    except:
        return 0.0

    if "Bearish" in macro_state and "Bullish" in micro_state:
        return -0.25
    if "Bullish" in macro_state and "Bearish" in micro_state:
        return -0.25

    return 0.0


def _compute_parlay_score(leg_quality, opp, fusion, corr_penalty):
    """
    Compute the unified parlay score.
    """

    opp_score = opp.get("opportunity_score", 0)
    fusion_score = fusion.get("fusion_score", 0)

    score = float(
        (leg_quality * 0.50) +
        (opp_score * 0.25) +
        (fusion_score * 0.25) +
        corr_penalty
    )

    return score


def _classify_parlay_state(score):
    """
    Classify the parlay environment.
    """

    if score > 0.65:
        return "High-Value Parlay"
    elif score > 0.25:
        return "Moderate-Value Parlay"
    else:
        return "Low-Value Parlay"


def _build_parlay_export(score, state, leg_quality, corr_penalty):
    """
    Build the final parlay export object.
    """

    return {
        "parlay_score": score,
        "parlay_state": state,
        "leg_quality": leg_quality,
        "correlation_penalty": corr_penalty,
    }


def render_parlay_engine():
    """
    Full UI for the Parlay Engine 2.0.
    """
    st.header("Parlay Engine 2.0")
    st.caption("Builds multi-leg parlays using correlation-aware, opportunity-weighted logic.")

    slip, risk, opp, fusion, macro, micro = _collect_parlay_inputs()
    if not slip or not risk or not opp or not fusion or not macro or not micro:
        st.info("Missing slip, risk, opportunity, fusion, macro, or micro export objects.")
        return

    # Step 1: Leg quality
    leg_quality = _compute_leg_quality(slip, risk, opp)

    # Step 2: Correlation penalty
    corr_penalty = _compute_correlation_penalty(macro, micro)

    # Step 3: Parlay score
    score = _compute_parlay_score(leg_quality, opp, fusion, corr_penalty)

    # Step 4: Parlay state
    state = _classify_parlay_state(score)

    # Step 5: Build export
    export = _build_parlay_export(score, state, leg_quality, corr_penalty)

    # Save parlay export
    st.session_state["parlay_export"] = export

    themed_card_container()
    st.markdown(f"## Parlay State: **{state}**")

    themed_card_container()
    st.markdown("### Parlay Score")
    st.markdown(f"`{score:.4f}`")

    themed_card_container()
    st.markdown("### Leg Quality")
    st.markdown(f"`{leg_quality:.4f}`")

    themed_card_container()
    st.markdown("### Correlation Penalty")
    st.markdown(f"`{corr_penalty:.4f}`")

    themed_card_container()
    st.markdown("### Parlay Export Object")
    st.json(export)

    st.success("Parlay Engine 2.0 complete.")
# ------------- CHUNK 128: LEARNING ENGINE 2.0 -------------

def _collect_learning_inputs():
    """
    Collect all upstream objects:
    - final_decision
    - risk_export
    - parlay_export
    - opportunity_export
    - fusion_export
    """

    final_decision = st.session_state.get("final_decision")
    risk = st.session_state.get("risk_export")
    parlay = st.session_state.get("parlay_export")
    opp = st.session_state.get("opportunity_export")
    fusion = st.session_state.get("fusion_export")

    return final_decision, risk, parlay, opp, fusion


def _compute_reinforcement_signal(final_decision, risk, parlay):
    """
    Compute reinforcement signal based on:
    - decision strength
    - unit size
    - parlay quality
    """

    decision = final_decision.get("final_decision", "NO BET")
    unit = risk.get("unit_size", 0)
    parlay_score = parlay.get("parlay_score", 0)

    # Decision strength mapping
    decision_strength = {
        "STRONG BET": 1.0,
        "BET": 0.75,
        "LEAN BET": 0.50,
        "NO BET": 0.0
    }.get(decision, 0.0)

    signal = float(
        (decision_strength * 0.50) +
        (unit * 0.30) +
        (parlay_score * 0.20)
    )

    return signal


def _compute_learning_adjustments(signal, opp, fusion):
    """
    Convert reinforcement signal into learning adjustments.
    """

    opp_score = opp.get("opportunity_score", 0)
    fusion_score = fusion.get("fusion_score", 0)

    # Positive reinforcement
    if signal > 0.65:
        return {
            "threshold_shift": +0.05,
            "confidence_boost": +0.04,
            "risk_tolerance_shift": +0.03,
            "opportunity_weight_shift": +0.05,
            "fusion_weight_shift": +0.04,
        }

    # Moderate reinforcement
    if signal > 0.25:
        return {
            "threshold_shift": +0.02,
            "confidence_boost": +0.02,
            "risk_tolerance_shift": +0.01,
            "opportunity_weight_shift": +0.02,
            "fusion_weight_shift": +0.02,
        }

    # Negative reinforcement
    return {
        "threshold_shift": -0.03,
        "confidence_boost": -0.02,
        "risk_tolerance_shift": -0.03,
        "opportunity_weight_shift": -0.02,
        "fusion_weight_shift": -0.02,
    }


def _build_learning_export(signal, adjustments):
    """
    Build the final learning export object.
    """

    return {
        "reinforcement_signal": signal,
        "adjustments": adjustments,
    }


def render_learning_engine():
    """
    Full UI for the Learning Engine 2.0.
    """
    st.header("Learning Engine 2.0")
    st.caption("Self-adjusts thresholds and weights using reinforcement signals.")

    final_decision, risk, parlay, opp, fusion = _collect_learning_inputs()
    if not final_decision or not risk or not parlay or not opp or not fusion:
        st.info("Missing final decision, risk, parlay, opportunity, or fusion export objects.")
        return

    # Step 1: Compute reinforcement signal
    signal = _compute_reinforcement_signal(final_decision, risk, parlay)

    # Step 2: Compute learning adjustments
    adjustments = _compute_learning_adjustments(signal, opp, fusion)

    # Step 3: Build export
    export = _build_learning_export(signal, adjustments)

    # Save learning export
    st.session_state["learning_export"] = export

    themed_card_container()
    st.markdown("## Reinforcement Signal")
    st.markdown(f"`{signal:.4f}`")

    themed_card_container()
    st.markdown("### Learning Adjustments")
    st.json(adjustments)

    themed_card_container()
    st.markdown("### Learning Export Object")
    st.json(export)

    st.success("Learning Engine 2.0 complete.")
# ------------- CHUNK 129: HISTORICAL LOG ENGINE 2.0 -------------

def _collect_log_inputs():
    """
    Collect all upstream objects:
    - final_decision
    - risk_export
    - parlay_export
    - opportunity_export
    - learning_export
    - fusion_export
    - macro_export
    - micro_export
    """

    final_decision = st.session_state.get("final_decision")
    risk = st.session_state.get("risk_export")
    parlay = st.session_state.get("parlay_export")
    opp = st.session_state.get("opportunity_export")
    learning = st.session_state.get("learning_export")
    fusion = st.session_state.get("fusion_export")
    macro = st.session_state.get("macro_export")
    micro = st.session_state.get("micro_export")

    return final_decision, risk, parlay, opp, learning, fusion, macro, micro


def _build_log_entry(final_decision, risk, parlay, opp, learning, fusion, macro, micro):
    """
    Build a clean, structured log entry.
    """

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    entry = {
        "timestamp": timestamp,
        "final_decision": final_decision,
        "risk_export": risk,
        "parlay_export": parlay,
        "opportunity_export": opp,
        "learning_export": learning,
        "fusion_export": fusion,
        "macro_export": macro,
        "micro_export": micro,
    }

    return entry


def _append_log_entry(entry):
    """
    Append entry to historical log with zero duplication.
    """

    if "historical_log" not in st.session_state:
        st.session_state["historical_log"] = []

    log = st.session_state["historical_log"]

    # Prevent duplicates by checking timestamp + decision hash
    entry_hash = hash(json.dumps(entry, sort_keys=True))

    if "historical_hashes" not in st.session_state:
        st.session_state["historical_hashes"] = set()

    if entry_hash in st.session_state["historical_hashes"]:
        return False  # Duplicate detected

    # Append entry
    log.append(entry)
    st.session_state["historical_hashes"].add(entry_hash)

    return True


def render_historical_log_engine():
    """
    Full UI for the Historical Log Engine 2.0.
    """
    st.header("Historical Log Engine 2.0")
    st.caption("Zero-duplication, clean, structured logging of all decisions.")

    final_decision, risk, parlay, opp, learning, fusion, macro, micro = _collect_log_inputs()
    if not final_decision or not risk or not parlay or not opp or not learning or not fusion or not macro or not micro:
        st.info("Missing one or more required export objects.")
        return

    entry = _build_log_entry(final_decision, risk, parlay, opp, learning, fusion, macro, micro)
    added = _append_log_entry(entry)

    if added:
        st.success("Log entry added successfully.")
    else:
        st.warning("Duplicate entry detected — not added.")

    themed_card_container()
    st.markdown("### Latest Log Entry")
    st.json(entry)

    themed_card_container()
    st.markdown("### Full Historical Log")
    st.json(st.session_state.get("historical_log", []))
# ------------- CHUNK 130: MOBILE OPTIMIZATION LAYER -------------

def inject_mobile_responsive_css():
    """
    Inject responsive CSS to optimize the entire V36 dashboard for mobile devices.
    """

    st.markdown("""
    <style>

    /* Remove horizontal scroll everywhere */
    html, body, [class*="css"]  {
        overflow-x: hidden !important;
    }

    /* Make all cards full-width on mobile */
    @media (max-width: 768px) {
        .block-container {
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
        }

        /* Headings scale down */
        h1, h2, h3, h4 {
            font-size: 90% !important;
        }

        /* Buttons scale and stack */
        button, .stButton>button {
            width: 100% !important;
            margin-top: 0.4rem !important;
        }

        /* JSON blocks shrink properly */
        .stJson {
            font-size: 85% !important;
        }

        /* Cards spacing */
        .themed-card-container {
            margin-bottom: 1.2rem !important;
        }

        /* Tables scroll cleanly */
        table {
            display: block;
            overflow-x: auto;
            white-space: nowrap;
        }
    }

    /* Ultra-small screens */
    @media (max-width: 480px) {
        h1, h2 {
            font-size: 80% !important;
        }
        h3, h4 {
            font-size: 75% !important;
        }
        .stJson {
            font-size: 80% !important;
        }
    }

    </style>
    """, unsafe_allow_html=True)


def render_mobile_optimization_layer():
    """
    Full UI for the Mobile Optimization Layer.
    """
    st.header("Mobile Optimization Layer")
    st.caption("Ensures the entire V36 dashboard is fully responsive and mobile-friendly.")

    inject_mobile_responsive_css()

    themed_card_container()
    st.markdown("""
    ### Mobile Optimization Active  
    The dashboard now adapts automatically to:
    - phones  
    - tablets  
    - small laptop screens  
    """)

    st.success("Mobile optimization layer applied successfully.")
# ------------- CHUNK 131: DIAGNOSTICS & ERROR PANEL (SYSTEM HEALTH ENGINE) -------------

def _check_export(name):
    """
    Check if an export object exists and is valid.
    """

    obj = st.session_state.get(name)
    if obj is None:
        return {"status": "MISSING", "detail": f"{name} not found."}

    if isinstance(obj, dict) and len(obj.keys()) == 0:
        return {"status": "EMPTY", "detail": f"{name} is empty."}

    return {"status": "OK", "detail": f"{name} loaded successfully."}


def _check_qwen_status():
    """
    Check if Qwen is enabled and functioning.
    """

    enabled = st.session_state.settings.get("enable_qwen", True)

    if not enabled:
        return {"status": "DISABLED", "detail": "Qwen disabled in settings."}

    # We cannot test Qwen directly, so we assume OK if enabled.
    return {"status": "OK", "detail": "Qwen enabled."}


def _check_api_data():
    """
    Check if odds + SportsDataIO data exists.
    """

    odds = st.session_state.get("odds_data")
    sd = st.session_state.get("sportsdataio_data")

    if odds is None:
        return {"status": "MISSING", "detail": "Odds data missing."}

    if sd is None:
        return {"status": "MISSING", "detail": "SportsDataIO data missing."}

    return {"status": "OK", "detail": "API data loaded."}


def _check_macro_micro_sync():
    """
    Ensure macro and micro systems both produced final exports.
    """

    macro = st.session_state.get("macro_export")
    micro = st.session_state.get("micro_export")

    if macro is None and micro is None:
        return {"status": "MISSING", "detail": "Both macro and micro exports missing."}

    if macro is None:
        return {"status": "MISSING", "detail": "Macro export missing."}

    if micro is None:
        return {"status": "MISSING", "detail": "Micro export missing."}

    return {"status": "OK", "detail": "Macro + Micro synchronized."}


def _build_diagnostics_report():
    """
    Build a full diagnostics report for all major engines.
    """

    checks = {
        "macro_export": _check_export("macro_export"),
        "micro_export": _check_export("micro_export"),
        "fusion_export": _check_export("fusion_export"),
        "slip_export": _check_export("slip_export"),
        "slip_card": _check_export("slip_card"),
        "final_decision": _check_export("final_decision"),
        "risk_export": _check_export("risk_export"),
        "opportunity_export": _check_export("opportunity_export"),
        "parlay_export": _check_export("parlay_export"),
        "learning_export": _check_export("learning_export"),
        "historical_log": _check_export("historical_log"),
        "qwen_status": _check_qwen_status(),
        "api_data": _check_api_data(),
        "macro_micro_sync": _check_macro_micro_sync(),
    }

    return checks


def render_diagnostics_panel():
    """
    Full UI for the Diagnostics & Error Panel.
    """
    st.header("Diagnostics & Error Panel (System Health Engine)")
    st.caption("Centralized system health checks for all V36 engines.")

    report = _build_diagnostics_report()

    themed_card_container()
    st.markdown("## System Health Report")
    st.json(report)

    # Summary
    errors = [k for k, v in report.items() if v["status"] != "OK"]

    if len(errors) == 0:
        st.success("All systems operational.")
    else:
        st.error(f"Issues detected in: {', '.join(errors)}")
# ------------- CHUNK 200: META-LEARNING CORE (V37 INIT ENGINE) -------------

def _collect_meta_learning_inputs():
    """
    Collect all major exports from V36:
    - macro_export
    - micro_export
    - fusion_export
    - slip_export
    - final_decision
    - risk_export
    - parlay_export
    - opportunity_export
    - learning_export
    - historical_log
    """

    return {
        "macro": st.session_state.get("macro_export"),
        "micro": st.session_state.get("micro_export"),
        "fusion": st.session_state.get("fusion_export"),
        "slip": st.session_state.get("slip_export"),
        "decision": st.session_state.get("final_decision"),
        "risk": st.session_state.get("risk_export"),
        "parlay": st.session_state.get("parlay_export"),
        "opp": st.session_state.get("opportunity_export"),
        "learning": st.session_state.get("learning_export"),
        "log": st.session_state.get("historical_log", []),
    }


def _compute_meta_stability(log):
    """
    Compute long-horizon stability:
    - variance of final scores
    - variance of unit sizes
    - variance of opportunity scores
    - variance of parlay scores
    """

    if len(log) < 5:
        return 0.5  # Not enough data yet

    try:
        final_scores = [e["final_decision"]["final_score"] for e in log]
        units = [e["risk_export"]["unit_size"] for e in log]
        opps = [e["opportunity_export"]["opportunity_score"] for e in log]
        parlays = [e["parlay_export"]["parlay_score"] for e in log]

        import numpy as np
        var_final = np.var(final_scores)
        var_units = np.var(units)
        var_opp = np.var(opps)
        var_parlay = np.var(parlays)

        stability = 1 - float(
            (var_final * 0.35) +
            (var_units * 0.25) +
            (var_opp * 0.20) +
            (var_parlay * 0.20)
        )

        return max(0.0, min(stability, 1.0))

    except:
        return 0.5


def _compute_meta_drift(macro, micro, fusion):
    """
    Measure long-term drift between macro, micro, and fusion signals.
    """

    try:
        macro_score = macro["normalized"]["macro_omni_score_normalized"]
        micro_score = micro["normalized"]["micro_omni_score_normalized"]
        fusion_score = fusion["fusion_score"]
    except:
        return 0.5

    drift = abs(macro_score - micro_score) * 0.6 + abs(fusion_score - macro_score) * 0.4
    drift = 1 - drift
    return max(0.0, min(drift, 1.0))


def _compute_meta_signal_strength(stability, drift):
    """
    Combine stability + drift into a unified meta-signal.
    """

    strength = float(
        (stability * 0.55) +
        (drift * 0.45)
    )

    return max(0.0, min(strength, 1.0))


def _build_meta_export(stability, drift, strength):
    """
    Build the final meta-learning export object.
    """

    return {
        "meta_stability": stability,
        "meta_drift": drift,
        "meta_signal_strength": strength,
    }


def render_meta_learning_core():
    """
    Full UI for the Meta-Learning Core (V37 Init Engine).
    """
    st.header("Meta-Learning Core (V37)")
    st.caption("The brain above all brains — long-horizon learning, drift modeling, and stability analysis.")

    data = _collect_meta_learning_inputs()

    stability = _compute_meta_stability(data["log"])
    drift = _compute_meta_drift(data["macro"], data["micro"], data["fusion"])
    strength = _compute_meta_signal_strength(stability, drift)

    export = _build_meta_export(stability, drift, strength)

    # Save meta export
    st.session_state["meta_export"] = export

    themed_card_container()
    st.markdown(f"## Meta Stability: `{stability:.4f}`")

    themed_card_container()
    st.markdown(f"## Meta Drift: `{drift:.4f}`")

    themed_card_container()
    st.markdown(f"## Meta Signal Strength: `{strength:.4f}`")

    themed_card_container()
    st.markdown("### Meta Export Object")
    st.json(export)

    st.success("Meta-Learning Core initialized.")
# ------------- CHUNK 201: TEMPORAL DRIFT ENGINE (V37) -------------

def _collect_temporal_drift_inputs():
    """
    Collect historical log + current macro/micro/fusion exports.
    """

    log = st.session_state.get("historical_log", [])
    macro = st.session_state.get("macro_export")
    micro = st.session_state.get("micro_export")
    fusion = st.session_state.get("fusion_export")

    return log, macro, micro, fusion


def _extract_historical_series(log):
    """
    Extract historical macro/micro/fusion scores from the log.
    """

    macro_series = []
    micro_series = []
    fusion_series = []

    for entry in log:
        try:
            macro_series.append(entry["macro_export"]["normalized"]["macro_omni_score_normalized"])
            micro_series.append(entry["micro_export"]["normalized"]["micro_omni_score_normalized"])
            fusion_series.append(entry["fusion_export"]["fusion_score"])
        except:
            continue

    return macro_series, micro_series, fusion_series


def _compute_series_drift(series):
    """
    Compute drift for a single series:
    - recent average vs long-term average
    - variance
    - directional slope
    """

    if len(series) < 5:
        return 0.5  # Not enough data

    import numpy as np

    arr = np.array(series)

    long_avg = np.mean(arr)
    recent_avg = np.mean(arr[-3:])
    variance = np.var(arr)

    # Directional slope (trend)
    x = np.arange(len(arr))
    slope = np.polyfit(x, arr, 1)[0]

    drift = float(
        (1 - abs(recent_avg - long_avg)) * 0.45 +
        (1 - variance) * 0.30 +
        (1 if slope > 0 else 0) * 0.25
    )

    return max(0.0, min(drift, 1.0))


def _compute_temporal_drift(macro_series, micro_series, fusion_series):
    """
    Combine macro/micro/fusion drift into unified temporal drift score.
    """

    macro_drift = _compute_series_drift(macro_series)
    micro_drift = _compute_series_drift(micro_series)
    fusion_drift = _compute_series_drift(fusion_series)

    score = float(
        (macro_drift * 0.40) +
        (micro_drift * 0.40) +
        (fusion_drift * 0.20)
    )

    return score, macro_drift, micro_drift, fusion_drift


def _classify_temporal_drift_state(score):
    """
    Classify the temporal drift environment.
    """

    if score > 0.70:
        return "Stable Long-Horizon Environment"
    elif score > 0.35:
        return "Moderate Drift Environment"
    else:
        return "High Drift / Unstable Environment"


def _build_temporal_drift_export(score, state, macro_drift, micro_drift, fusion_drift):
    """
    Build the final temporal drift export object.
    """

    return {
        "temporal_drift_score": score,
        "temporal_drift_state": state,
        "macro_drift": macro_drift,
        "micro_drift": micro_drift,
        "fusion_drift": fusion_drift,
    }


def render_temporal_drift_engine():
    """
    Full UI for the Temporal Drift Engine (V37).
    """
    st.header("Temporal Drift Engine (V37)")
    st.caption("Tracks long-horizon macro–micro–fusion evolution and drift.")

    log, macro, micro, fusion = _collect_temporal_drift_inputs()

    macro_series, micro_series, fusion_series = _extract_historical_series(log)

    score, macro_drift, micro_drift, fusion_drift = _compute_temporal_drift(
        macro_series, micro_series, fusion_series
    )

    state = _classify_temporal_drift_state(score)

    export = _build_temporal_drift_export(score, state, macro_drift, micro_drift, fusion_drift)

    # Save export
    st.session_state["temporal_drift_export"] = export

    themed_card_container()
    st.markdown(f"## Temporal Drift State: **{state}**")

    themed_card_container()
    st.markdown("### Temporal Drift Score")
    st.markdown(f"`{score:.4f}`")

    themed_card_container()
    st.markdown("### Drift Breakdown")
    st.json({
        "macro_drift": macro_drift,
        "micro_drift": micro_drift,
        "fusion_drift": fusion_drift
    })

    themed_card_container()
    st.markdown("### Temporal Drift Export Object")
    st.json(export)

    st.success("Temporal Drift Engine complete.")
# ------------- CHUNK 202: VOLATILITY CYCLE PREDICTOR (V37) -------------

def _collect_volatility_inputs():
    """
    Collect historical log + current micro export.
    """

    log = st.session_state.get("historical_log", [])
    micro = st.session_state.get("micro_export")

    return log, micro


def _extract_volatility_series(log):
    """
    Extract historical volatility values from the log.
    """

    series = []

    for entry in log:
        try:
            vol = entry["micro_export"]["raw"]["micro_volatility"]
            series.append(vol)
        except:
            continue

    return series


def _compute_cycle_metrics(series):
    """
    Compute cycle metrics:
    - short-term average
    - long-term average
    - cycle amplitude
    - cycle slope
    - compression/expansion detection
    """

    if len(series) < 5:
        return {
            "short_avg": 0.5,
            "long_avg": 0.5,
            "amplitude": 0.1,
            "slope": 0.0,
            "compression": False,
            "expansion": False,
        }

    import numpy as np

    arr = np.array(series)

    short_avg = np.mean(arr[-3:])
    long_avg = np.mean(arr)
    amplitude = float(np.max(arr[-5:]) - np.min(arr[-5:]))

    # Slope (trend)
    x = np.arange(len(arr))
    slope = np.polyfit(x, arr, 1)[0]

    # Compression / Expansion
    compression = amplitude < 0.10 and slope < 0.02
    expansion = amplitude > 0.25 or slope > 0.05

    return {
        "short_avg": short_avg,
        "long_avg": long_avg,
        "amplitude": amplitude,
        "slope": slope,
        "compression": compression,
        "expansion": expansion,
    }


def _compute_volatility_cycle_score(metrics):
    """
    Combine cycle metrics into a unified volatility cycle score.
    """

    short_avg = metrics["short_avg"]
    long_avg = metrics["long_avg"]
    amplitude = metrics["amplitude"]
    slope = metrics["slope"]

    score = float(
        (short_avg * 0.30) +
        (long_avg * 0.20) +
        (amplitude * 0.30) +
        (max(0, slope) * 0.20)
    )

    return max(0.0, min(score, 1.0))


def _classify_volatility_cycle_state(score, metrics):
    """
    Classify volatility cycle environment.
    """

    if metrics["compression"]:
        return "Volatility Compression (Breakout Likely Soon)"

    if metrics["expansion"]:
        return "Volatility Expansion (High Chaos)"

    if score > 0.65:
        return "High Volatility Cycle"

    if score > 0.35:
        return "Moderate Volatility Cycle"

    return "Low Volatility Cycle"


def _build_volatility_cycle_export(score, state, metrics):
    """
    Build the final volatility cycle export object.
    """

    return {
        "volatility_cycle_score": score,
        "volatility_cycle_state": state,
        "cycle_metrics": metrics,
    }


def render_volatility_cycle_predictor():
    """
    Full UI for the Volatility Cycle Predictor (V37).
    """
    st.header("Volatility Cycle Predictor (V37)")
    st.caption("Detects volatility cycles, compression, expansion, and forecasts regime shifts.")

    log, micro = _collect_volatility_inputs()

    series = _extract_volatility_series(log)
    metrics = _compute_cycle_metrics(series)
    score = _compute_volatility_cycle_score(metrics)
    state = _classify_volatility_cycle_state(score, metrics)

    export = _build_volatility_cycle_export(score, state, metrics)

    # Save export
    st.session_state["volatility_cycle_export"] = export

    themed_card_container()
    st.markdown(f"## Volatility Cycle State: **{state}**")

    themed_card_container()
    st.markdown("### Volatility Cycle Score")
    st.markdown(f"`{score:.4f}`")

    themed_card_container()
    st.markdown("### Cycle Metrics")
    st.json(metrics)

    themed_card_container()
    st.markdown("### Volatility Cycle Export Object")
    st.json(export)

    st.success("Volatility Cycle Predictor complete.")
# ------------- CHUNK 203: INSTABILITY FORECASTING ENGINE (V37) -------------

def _collect_instability_inputs():
    """
    Collect all upstream V37 + V36 signals:
    - temporal_drift_export
    - volatility_cycle_export
    - micro_export
    - macro_export
    - fusion_export
    - historical_log
    """

    return {
        "temporal": st.session_state.get("temporal_drift_export"),
        "volatility": st.session_state.get("volatility_cycle_export"),
        "micro": st.session_state.get("micro_export"),
        "macro": st.session_state.get("macro_export"),
        "fusion": st.session_state.get("fusion_export"),
        "log": st.session_state.get("historical_log", []),
    }


def _extract_instability_series(log):
    """
    Extract historical instability values from the log.
    """

    series = []

    for entry in log:
        try:
            instab = entry["micro_export"]["raw"]["micro_instability"]
            series.append(instab)
        except:
            continue

    return series


def _compute_instability_trend(series):
    """
    Compute instability trend:
    - short-term average
    - long-term average
    - slope
    - acceleration
    """

    if len(series) < 5:
        return {
            "short_avg": 0.5,
            "long_avg": 0.5,
            "slope": 0.0,
            "acceleration": 0.0,
        }

    import numpy as np

    arr = np.array(series)

    short_avg = np.mean(arr[-3:])
    long_avg = np.mean(arr)
    x = np.arange(len(arr))

    # Slope (trend)
    slope = np.polyfit(x, arr, 1)[0]

    # Acceleration (second derivative)
    if len(arr) >= 3:
        acceleration = (arr[-1] - arr[-2]) - (arr[-2] - arr[-3])
    else:
        acceleration = 0.0

    return {
        "short_avg": short_avg,
        "long_avg": long_avg,
        "slope": slope,
        "acceleration": acceleration,
    }


def _compute_instability_forecast(temporal, volatility, trend):
    """
    Combine:
    - temporal drift
    - volatility cycle state
    - instability trend
    into a unified instability forecast score.
    """

    temporal_score = temporal.get("temporal_drift_score", 0.5)
    vol_score = volatility.get("volatility_cycle_score", 0.5)

    short_avg = trend["short_avg"]
    slope = trend["slope"]
    acceleration = trend["acceleration"]

    forecast = float(
        (1 - temporal_score) * 0.30 +   # low temporal stability increases instability
        (vol_score * 0.25) +            # high volatility increases instability
        (short_avg * 0.20) +            # recent instability
        (max(0, slope) * 0.15) +        # upward trend
        (max(0, acceleration) * 0.10)   # accelerating instability
    )

    return max(0.0, min(forecast, 1.0))


def _classify_instability_state(score):
    """
    Classify instability forecast environment.
    """

    if score > 0.70:
        return "High Instability Forecast (Danger Zone)"

    if score > 0.40:
        return "Moderate Instability Forecast"

    return "Low Instability Forecast"


def _build_instability_export(score, state, trend):
    """
    Build the final instability forecast export object.
    """

    return {
        "instability_forecast_score": score,
        "instability_forecast_state": state,
        "instability_trend": trend,
    }


def render_instability_forecasting_engine():
    """
    Full UI for the Instability Forecasting Engine (V37).
    """
    st.header("Instability Forecasting Engine (V37)")
    st.caption("Predicts instability before it happens using drift, volatility cycles, and trend analysis.")

    data = _collect_instability_inputs()

    trend = _compute_instability_trend(_extract_instability_series(data["log"]))
    score = _compute_instability_forecast(data["temporal"], data["volatility"], trend)
    state = _classify_instability_state(score)

    export = _build_instability_export(score, state, trend)

    # Save export
    st.session_state["instability_export"] = export

    themed_card_container()
    st.markdown(f"## Instability Forecast State: **{state}**")

    themed_card_container()
    st.markdown("### Instability Forecast Score")
    st.markdown(f"`{score:.4f}`")

    themed_card_container()
    st.markdown("### Instability Trend")
    st.json(trend)

    themed_card_container()
    st.markdown("### Instability Forecast Export Object")
    st.json(export)

    st.success("Instability Forecasting Engine complete.")
# ------------- CHUNK 204: SHOCK & TURBULENCE EARLY-WARNING SYSTEM (V37) -------------

def _collect_shock_inputs():
    """
    Collect all upstream V37 + V36 signals:
    - instability_export
    - volatility_cycle_export
    - temporal_drift_export
    - micro_export
    - macro_export
    - fusion_export
    - historical_log
    """

    return {
        "instability": st.session_state.get("instability_export"),
        "volatility": st.session_state.get("volatility_cycle_export"),
        "temporal": st.session_state.get("temporal_drift_export"),
        "micro": st.session_state.get("micro_export"),
        "macro": st.session_state.get("macro_export"),
        "fusion": st.session_state.get("fusion_export"),
        "log": st.session_state.get("historical_log", []),
    }


def _extract_shock_series(log):
    """
    Extract historical shock values from the log.
    """

    series = []

    for entry in log:
        try:
            shock = entry["micro_export"]["raw"]["micro_shock"]
            series.append(shock)
        except:
            continue

    return series


def _compute_shock_trend(series):
    """
    Compute shock trend:
    - short-term average
    - long-term average
    - slope
    - acceleration
    - clustering (shock frequency)
    """

    if len(series) < 5:
        return {
            "short_avg": 0.4,
            "long_avg": 0.4,
            "slope": 0.0,
            "acceleration": 0.0,
            "cluster_factor": 0.1,
        }

    import numpy as np

    arr = np.array(series)

    short_avg = np.mean(arr[-3:])
    long_avg = np.mean(arr)
    x = np.arange(len(arr))

    # Slope (trend)
    slope = np.polyfit(x, arr, 1)[0]

    # Acceleration (second derivative)
    if len(arr) >= 3:
        acceleration = (arr[-1] - arr[-2]) - (arr[-2] - arr[-3])
    else:
        acceleration = 0.0

    # Shock clustering (frequency of spikes)
    cluster_factor = float(np.sum(arr[-5:] > 0.55) / 5)

    return {
        "short_avg": short_avg,
        "long_avg": long_avg,
        "slope": slope,
        "acceleration": acceleration,
        "cluster_factor": cluster_factor,
    }


def _compute_shock_forecast(instability, volatility, temporal, trend):
    """
    Combine:
    - instability forecast
    - volatility cycle expansion
    - temporal drift decay
    - shock trend
    into a unified shock forecast score.
    """

    instab_score = instability.get("instability_forecast_score", 0.5)
    vol_score = volatility.get("volatility_cycle_score", 0.5)
    temporal_score = temporal.get("temporal_drift_score", 0.5)

    short_avg = trend["short_avg"]
    slope = trend["slope"]
    acceleration = trend["acceleration"]
    cluster = trend["cluster_factor"]

    forecast = float(
        (instab_score * 0.30) +
        (vol_score * 0.20) +
        ((1 - temporal_score) * 0.15) +
        (short_avg * 0.15) +
        (max(0, slope) * 0.10) +
        (max(0, acceleration) * 0.05) +
        (cluster * 0.05)
    )

    return max(0.0, min(forecast, 1.0))


def _classify_shock_state(score):
    """
    Classify shock/turbulence forecast environment.
    """

    if score > 0.70:
        return "High Shock/Turbulence Forecast (Critical Warning)"

    if score > 0.40:
        return "Moderate Shock/Turbulence Forecast"

    return "Low Shock/Turbulence Forecast"


def _build_shock_export(score, state, trend):
    """
    Build the final shock forecast export object.
    """

    return {
        "shock_forecast_score": score,
        "shock_forecast_state": state,
        "shock_trend": trend,
    }


def render_shock_forecasting_engine():
    """
    Full UI for the Shock & Turbulence Early-Warning System (V37).
    """
    st.header("Shock & Turbulence Early-Warning System (V37)")
    st.caption("Predicts shock/turbulence before it happens using instability, volatility cycles, and drift decay.")

    data = _collect_shock_inputs()

    trend = _compute_shock_trend(_extract_shock_series(data["log"]))
    score = _compute_shock_forecast(
        data["instability"],
        data["volatility"],
        data["temporal"],
        trend
    )
    state = _classify_shock_state(score)

    export = _build_shock_export(score, state, trend)

    # Save export
    st.session_state["shock_export"] = export

    themed_card_container()
    st.markdown(f"## Shock/Turbulence Forecast State: **{state}**")

    themed_card_container()
    st.markdown("### Shock/Turbulence Forecast Score")
    st.markdown(f"`{score:.4f}`")

    themed_card_container()
    st.markdown("### Shock Trend")
    st.json(trend)

    themed_card_container()
    st.markdown("### Shock Forecast Export Object")
    st.json(export)

    st.success("Shock & Turbulence Early-Warning System complete.")
# ------------- CHUNK 205: DYNAMIC THRESHOLD EVOLUTION ENGINE (V37) -------------

def _collect_threshold_inputs():
    """
    Collect all upstream V37 signals:
    - meta_export
    - temporal_drift_export
    - volatility_cycle_export
    - instability_export
    - shock_export
    - learning_export
    - historical_log
    """

    return {
        "meta": st.session_state.get("meta_export"),
        "temporal": st.session_state.get("temporal_drift_export"),
        "volatility": st.session_state.get("volatility_cycle_export"),
        "instability": st.session_state.get("instability_export"),
        "shock": st.session_state.get("shock_export"),
        "learning": st.session_state.get("learning_export"),
        "log": st.session_state.get("historical_log", []),
    }


def _compute_environment_pressure(meta, temporal, volatility, instability, shock):
    """
    Compute environment pressure:
    - low stability increases pressure
    - high drift increases pressure
    - volatility expansion increases pressure
    - instability forecast increases pressure
    - shock forecast increases pressure
    """

    stability = meta.get("meta_stability", 0.5)
    drift = temporal.get("temporal_drift_score", 0.5)
    vol = volatility.get("volatility_cycle_score", 0.5)
    instab = instability.get("instability_forecast_score", 0.5)
    shock_score = shock.get("shock_forecast_score", 0.5)

    pressure = float(
        ((1 - stability) * 0.30) +
        ((1 - drift) * 0.20) +
        (vol * 0.20) +
        (instab * 0.15) +
        (shock_score * 0.15)
    )

    return max(0.0, min(pressure, 1.0))


def _compute_learning_pressure(learning):
    """
    Convert reinforcement adjustments into learning pressure.
    """

    adj = learning.get("adjustments", {})

    threshold_shift = adj.get("threshold_shift", 0)
    confidence_boost = adj.get("confidence_boost", 0)
    risk_shift = adj.get("risk_tolerance_shift", 0)

    # Positive reinforcement reduces pressure
    # Negative reinforcement increases pressure
    learning_pressure = float(
        (-threshold_shift * 0.5) +
        (-confidence_boost * 0.3) +
        (-risk_shift * 0.2)
    )

    return max(-0.5, min(learning_pressure, 0.5))


def _compute_dynamic_thresholds(env_pressure, learning_pressure):
    """
    Combine environment pressure + learning pressure
    into dynamic threshold evolution.
    """

    # Base thresholds
    base = {
        "bet_threshold": 0.60,
        "strong_bet_threshold": 0.75,
        "risk_tolerance": 1.00,
        "opportunity_weight": 1.00,
        "fusion_weight": 1.00,
        "volatility_sensitivity": 1.00,
        "instability_sensitivity": 1.00,
        "shock_sensitivity": 1.00,
    }

    # Environment pressure increases thresholds (more conservative)
    # Learning pressure can offset or amplify this
    adj_factor = env_pressure + learning_pressure

    return {
        "bet_threshold": base["bet_threshold"] + (adj_factor * 0.10),
        "strong_bet_threshold": base["strong_bet_threshold"] + (adj_factor * 0.10),
        "risk_tolerance": base["risk_tolerance"] - (env_pressure * 0.20),
        "opportunity_weight": base["opportunity_weight"] + (learning_pressure * 0.15),
        "fusion_weight": base["fusion_weight"] + (learning_pressure * 0.10),
        "volatility_sensitivity": base["volatility_sensitivity"] + (env_pressure * 0.25),
        "instability_sensitivity": base["instability_sensitivity"] + (env_pressure * 0.25),
        "shock_sensitivity": base["shock_sensitivity"] + (env_pressure * 0.25),
    }


def _build_threshold_export(env_pressure, learning_pressure, thresholds):
    """
    Build the final dynamic threshold export object.
    """

    return {
        "environment_pressure": env_pressure,
        "learning_pressure": learning_pressure,
        "dynamic_thresholds": thresholds,
    }


def render_dynamic_threshold_evolution_engine():
    """
    Full UI for the Dynamic Threshold Evolution Engine (V37).
    """
    st.header("Dynamic Threshold Evolution Engine (V37)")
    st.caption("Self-tunes thresholds using environment pressure + reinforcement learning.")

    data = _collect_threshold_inputs()

    env_pressure = _compute_environment_pressure(
        data["meta"],
        data["temporal"],
        data["volatility"],
        data["instability"],
        data["shock"]
    )

    learning_pressure = _compute_learning_pressure(data["learning"])

    thresholds = _compute_dynamic_thresholds(env_pressure, learning_pressure)

    export = _build_threshold_export(env_pressure, learning_pressure, thresholds)

    # Save export
    st.session_state["threshold_export"] = export

    themed_card_container()
    st.markdown("## Environment Pressure")
    st.markdown(f"`{env_pressure:.4f}`")

    themed_card_container()
    st.markdown("## Learning Pressure")
    st.markdown(f"`{learning_pressure:.4f}`")

    themed_card_container()
    st.markdown("## Dynamic Thresholds")
    st.json(thresholds)

    themed_card_container()
    st.markdown("### Threshold Export Object")
    st.json(export)

    st.success("Dynamic Threshold Evolution Engine complete.")
# ------------- CHUNK 206: PREDICTIVE FUSION ENGINE (V37) -------------

def _collect_predictive_fusion_inputs():
    """
    Collect all upstream V37 signals:
    - meta_export
    - temporal_drift_export
    - volatility_cycle_export
    - instability_export
    - shock_export
    - threshold_export
    - macro_export
    - micro_export
    - fusion_export (V36 fusion)
    """

    return {
        "meta": st.session_state.get("meta_export"),
        "temporal": st.session_state.get("temporal_drift_export"),
        "volatility": st.session_state.get("volatility_cycle_export"),
        "instability": st.session_state.get("instability_export"),
        "shock": st.session_state.get("shock_export"),
        "thresholds": st.session_state.get("threshold_export"),
        "macro": st.session_state.get("macro_export"),
        "micro": st.session_state.get("micro_export"),
        "fusion": st.session_state.get("fusion_export"),
    }


def _compute_predictive_components(data):
    """
    Compute predictive components:
    - macro forward signal
    - micro forward signal
    - drift-adjusted fusion
    - volatility-adjusted fusion
    - instability-adjusted fusion
    - shock-adjusted fusion
    """

    macro_score = data["macro"]["normalized"]["macro_omni_score_normalized"]
    micro_score = data["micro"]["normalized"]["micro_omni_score_normalized"]
    fusion_score = data["fusion"]["fusion_score"]

    drift = data["temporal"]["temporal_drift_score"]
    vol = data["volatility"]["volatility_cycle_score"]
    instab = data["instability"]["instability_forecast_score"]
    shock = data["shock"]["shock_forecast_score"]

    # Forward macro/micro signals (anticipatory)
    macro_forward = float(macro_score * drift)
    micro_forward = float(micro_score * drift)

    # Adjust fusion based on environment
    fusion_forward = float(
        fusion_score
        * (1 - vol * 0.25)
        * (1 - instab * 0.25)
        * (1 - shock * 0.25)
    )

    return macro_forward, micro_forward, fusion_forward


def _compute_predictive_fusion_score(macro_fwd, micro_fwd, fusion_fwd, thresholds):
    """
    Combine predictive components into unified predictive fusion score.
    """

    fusion_weight = thresholds["dynamic_thresholds"]["fusion_weight"]

    score = float(
        (macro_fwd * 0.35) +
        (micro_fwd * 0.35) +
        (fusion_fwd * 0.30 * fusion_weight)
    )

    return max(0.0, min(score, 1.0))


def _classify_predictive_fusion_state(score):
    """
    Classify predictive fusion environment.
    """

    if score > 0.70:
        return "Strong Predictive Alignment"

    if score > 0.40:
        return "Moderate Predictive Alignment"

    return "Weak Predictive Alignment"


def _build_predictive_fusion_export(score, state, macro_fwd, micro_fwd, fusion_fwd):
    """
    Build the final predictive fusion export object.
    """

    return {
        "predictive_fusion_score": score,
        "predictive_fusion_state": state,
        "macro_forward": macro_fwd,
        "micro_forward": micro_fwd,
        "fusion_forward": fusion_fwd,
    }


def render_predictive_fusion_engine():
    """
    Full UI for the Predictive Fusion Engine (V37).
    """
    st.header("Predictive Fusion Engine (V37)")
    st.caption("Next-gen fusion model combining macro/micro evolution, drift, volatility, instability, and shock forecasts.")

    data = _collect_predictive_fusion_inputs()

    macro_fwd, micro_fwd, fusion_fwd = _compute_predictive_components(data)

    score = _compute_predictive_fusion_score(
        macro_fwd,
        micro_fwd,
        fusion_fwd,
        data["thresholds"]
    )

    state = _classify_predictive_fusion_state(score)

    export = _build_predictive_fusion_export(score, state, macro_fwd, micro_fwd, fusion_fwd)

    # Save export
    st.session_state["predictive_fusion_export"] = export

    themed_card_container()
    st.markdown(f"## Predictive Fusion State: **{state}**")

    themed_card_container()
    st.markdown("### Predictive Fusion Score")
    st.markdown(f"`{score:.4f}`")

    themed_card_container()
    st.markdown("### Predictive Components")
    st.json({
        "macro_forward": macro_fwd,
        "micro_forward": micro_fwd,
        "fusion_forward": fusion_fwd,
    })

    themed_card_container()
    st.markdown("### Predictive Fusion Export Object")
    st.json(export)

    st.success("Predictive Fusion Engine complete.")
# ------------- CHUNK 207: ADAPTIVE RISK ENGINE (V37) -------------

def _collect_adaptive_risk_inputs():
    """
    Collect all upstream V37 signals:
    - predictive_fusion_export
    - threshold_export
    - volatility_cycle_export
    - instability_export
    - shock_export
    - meta_export
    - temporal_drift_export
    - opportunity_export
    - parlay_export
    """

    return {
        "predictive_fusion": st.session_state.get("predictive_fusion_export"),
        "thresholds": st.session_state.get("threshold_export"),
        "volatility": st.session_state.get("volatility_cycle_export"),
        "instability": st.session_state.get("instability_export"),
        "shock": st.session_state.get("shock_export"),
        "meta": st.session_state.get("meta_export"),
        "temporal": st.session_state.get("temporal_drift_export"),
        "opportunity": st.session_state.get("opportunity_export"),
        "parlay": st.session_state.get("parlay_export"),
    }


def _compute_environment_risk_pressure(volatility, instability, shock, meta, temporal):
    """
    Compute environment risk pressure:
    - volatility expansion increases risk pressure
    - instability forecast increases risk pressure
    - shock forecast increases risk pressure
    - low meta stability increases risk pressure
    - low temporal drift increases risk pressure
    """

    vol = volatility.get("volatility_cycle_score", 0.5)
    instab = instability.get("instability_forecast_score", 0.5)
    shock_score = shock.get("shock_forecast_score", 0.5)
    stability = meta.get("meta_stability", 0.5)
    drift = temporal.get("temporal_drift_score", 0.5)

    pressure = float(
        (vol * 0.25) +
        (instab * 0.25) +
        (shock_score * 0.25) +
        ((1 - stability) * 0.15) +
        ((1 - drift) * 0.10)
    )

    return max(0.0, min(pressure, 1.0))


def _compute_signal_strength(predictive_fusion, opportunity, parlay):
    """
    Compute signal strength:
    - predictive fusion score
    - opportunity score
    - parlay score
    """

    fusion_score = predictive_fusion.get("predictive_fusion_score", 0.5)
    opp_score = opportunity.get("opportunity_score", 0.5)
    parlay_score = parlay.get("parlay_score", 0.5)

    strength = float(
        (fusion_score * 0.45) +
        (opp_score * 0.35) +
        (parlay_score * 0.20)
    )

    return max(0.0, min(strength, 1.0))


def _compute_adaptive_unit_size(strength, pressure, thresholds):
    """
    Compute adaptive unit size:
    - increases with signal strength
    - decreases with environment pressure
    - scaled by dynamic risk tolerance
    """

    risk_tol = thresholds["dynamic_thresholds"]["risk_tolerance"]

    raw = float(
        (strength * 1.25) -
        (pressure * 1.00)
    )

    unit = raw * risk_tol
    return max(0.10, min(unit, 2.00))  # bounded between 0.1 and 2 units


def _compute_exposure_limit(unit, pressure):
    """
    Exposure limit shrinks in dangerous environments.
    """

    base = 3.0  # 3 units max exposure baseline

    limit = float(
        base -
        (pressure * 2.0)
    )

    return max(0.5, min(limit, 3.0))


def _build_adaptive_risk_export(unit, limit, strength, pressure):
    """
    Build the final adaptive risk export object.
    """

    return {
        "adaptive_unit_size": unit,
        "exposure_limit": limit,
        "signal_strength": strength,
        "environment_risk_pressure": pressure,
    }


def render_adaptive_risk_engine():
    """
    Full UI for the Adaptive Risk Engine (V37).
    """
    st.header("Adaptive Risk Engine (V37)")
    st.caption("Environment-aware, self-tuning risk sizing model.")

    data = _collect_adaptive_risk_inputs()

    pressure = _compute_environment_risk_pressure(
        data["volatility"],
        data["instability"],
        data["shock"],
        data["meta"],
        data["temporal"]
    )

    strength = _compute_signal_strength(
        data["predictive_fusion"],
        data["opportunity"],
        data["parlay"]
    )

    unit = _compute_adaptive_unit_size(strength, pressure, data["thresholds"])
    limit = _compute_exposure_limit(unit, pressure)

    export = _build_adaptive_risk_export(unit, limit, strength, pressure)

    # Save export
    st.session_state["adaptive_risk_export"] = export

    themed_card_container()
    st.markdown("## Environment Risk Pressure")
    st.markdown(f"`{pressure:.4f}`")

    themed_card_container()
    st.markdown("## Signal Strength")
    st.markdown(f"`{strength:.4f}`")

    themed_card_container()
    st.markdown("## Adaptive Unit Size")
    st.markdown(f"`{unit:.4f}`")

    themed_card_container()
    st.markdown("## Exposure Limit")
    st.markdown(f"`{limit:.4f}`")

    themed_card_container()
    st.markdown("### Adaptive Risk Export Object")
    st.json(export)

    st.success("Adaptive Risk Engine complete.")
# ------------- CHUNK 208: ADAPTIVE OPPORTUNITY ENGINE (V37) -------------

def _collect_adaptive_opportunity_inputs():
    """
    Collect all upstream V37 signals:
    - predictive_fusion_export
    - threshold_export
    - volatility_cycle_export
    - instability_export
    - shock_export
    - meta_export
    - temporal_drift_export
    - opportunity_export (V36)
    """

    return {
        "predictive_fusion": st.session_state.get("predictive_fusion_export"),
        "thresholds": st.session_state.get("threshold_export"),
        "volatility": st.session_state.get("volatility_cycle_export"),
        "instability": st.session_state.get("instability_export"),
        "shock": st.session_state.get("shock_export"),
        "meta": st.session_state.get("meta_export"),
        "temporal": st.session_state.get("temporal_drift_export"),
        "opportunity": st.session_state.get("opportunity_export"),
    }


def _compute_opportunity_environment_pressure(volatility, instability, shock, meta, temporal):
    """
    Compute opportunity environment pressure:
    - volatility expansion reduces opportunity confidence
    - instability forecast reduces opportunity confidence
    - shock forecast reduces opportunity confidence
    - low meta stability reduces opportunity confidence
    - low temporal drift reduces opportunity confidence
    """

    vol = volatility.get("volatility_cycle_score", 0.5)
    instab = instability.get("instability_forecast_score", 0.5)
    shock_score = shock.get("shock_forecast_score", 0.5)
    stability = meta.get("meta_stability", 0.5)
    drift = temporal.get("temporal_drift_score", 0.5)

    pressure = float(
        (vol * 0.30) +
        (instab * 0.25) +
        (shock_score * 0.25) +
        ((1 - stability) * 0.10) +
        ((1 - drift) * 0.10)
    )

    return max(0.0, min(pressure, 1.0))


def _compute_opportunity_signal_strength(predictive_fusion, opportunity):
    """
    Compute opportunity signal strength:
    - predictive fusion score
    - raw opportunity score
    """

    fusion_score = predictive_fusion.get("predictive_fusion_score", 0.5)
    opp_score = opportunity.get("opportunity_score", 0.5)

    strength = float(
        (fusion_score * 0.55) +
        (opp_score * 0.45)
    )

    return max(0.0, min(strength, 1.0))


def _compute_adaptive_opportunity_weight(strength, pressure, thresholds):
    """
    Compute adaptive opportunity weight:
    - increases with signal strength
    - decreases with environment pressure
    - scaled by dynamic opportunity weight
    """

    base_weight = thresholds["dynamic_thresholds"]["opportunity_weight"]

    raw = float(
        (strength * 1.20) -
        (pressure * 1.00)
    )

    weight = raw * base_weight
    return max(0.25, min(weight, 2.00))  # bounded between 0.25 and 2.0


def _compute_opportunity_confidence(strength, weight, pressure):
    """
    Compute opportunity confidence:
    - increases with strength
    - increases with weight
    - decreases with pressure
    """

    confidence = float(
        (strength * 0.50) +
        (weight * 0.30) -
        (pressure * 0.20)
    )

    return max(0.0, min(confidence, 1.0))


def _build_adaptive_opportunity_export(weight, confidence, strength, pressure):
    """
    Build the final adaptive opportunity export object.
    """

    return {
        "adaptive_opportunity_weight": weight,
        "adaptive_opportunity_confidence": confidence,
        "opportunity_signal_strength": strength,
        "opportunity_environment_pressure": pressure,
    }


def render_adaptive_opportunity_engine():
    """
    Full UI for the Adaptive Opportunity Engine (V37).
    """
    st.header("Adaptive Opportunity Engine (V37)")
    st.caption("Environment-aware, self-tuning opportunity model.")

    data = _collect_adaptive_opportunity_inputs()

    pressure = _compute_opportunity_environment_pressure(
        data["volatility"],
        data["instability"],
        data["shock"],
        data["meta"],
        data["temporal"]
    )

    strength = _compute_opportunity_signal_strength(
        data["predictive_fusion"],
        data["opportunity"]
    )

    weight = _compute_adaptive_opportunity_weight(
        strength,
        pressure,
        data["thresholds"]
    )

    confidence = _compute_opportunity_confidence(
        strength,
        weight,
        pressure
    )

    export = _build_adaptive_opportunity_export(
        weight,
        confidence,
        strength,
        pressure
    )

    # Save export
    st.session_state["adaptive_opportunity_export"] = export

    themed_card_container()
    st.markdown("## Opportunity Environment Pressure")
    st.markdown(f"`{pressure:.4f}`")

    themed_card_container()
    st.markdown("## Opportunity Signal Strength")
    st.markdown(f"`{strength:.4f}`")

    themed_card_container()
    st.markdown("## Adaptive Opportunity Weight")
    st.markdown(f"`{weight:.4f}`")

    themed_card_container()
    st.markdown("## Opportunity Confidence")
    st.markdown(f"`{confidence:.4f}`")

    themed_card_container()
    st.markdown("### Adaptive Opportunity Export Object")
    st.json(export)

    st.success("Adaptive Opportunity Engine complete.")
# ------------- CHUNK 209: META-STABILITY ENGINE (V37) -------------

def _collect_meta_stability_inputs():
    """
    Collect all upstream V37 signals:
    - meta_export
    - temporal_drift_export
    - volatility_cycle_export
    - instability_export
    - shock_export
    - predictive_fusion_export
    - adaptive_risk_export
    - adaptive_opportunity_export
    - historical_log
    """

    return {
        "meta": st.session_state.get("meta_export"),
        "temporal": st.session_state.get("temporal_drift_export"),
        "volatility": st.session_state.get("volatility_cycle_export"),
        "instability": st.session_state.get("instability_export"),
        "shock": st.session_state.get("shock_export"),
        "predictive_fusion": st.session_state.get("predictive_fusion_export"),
        "risk": st.session_state.get("adaptive_risk_export"),
        "opportunity": st.session_state.get("adaptive_opportunity_export"),
        "log": st.session_state.get("historical_log", []),
    }


def _compute_stability_components(data):
    """
    Compute stability components:
    - meta stability
    - temporal drift stability
    - volatility stability
    - instability stability
    - shock stability
    - predictive fusion stability
    - risk stability
    - opportunity stability
    """

    meta_stab = data["meta"].get("meta_stability", 0.5)
    drift = data["temporal"].get("temporal_drift_score", 0.5)
    vol = 1 - data["volatility"].get("volatility_cycle_score", 0.5)
    instab = 1 - data["instability"].get("instability_forecast_score", 0.5)
    shock = 1 - data["shock"].get("shock_forecast_score", 0.5)

    fusion_stab = data["predictive_fusion"].get("predictive_fusion_score", 0.5)
    risk_stab = 1 - data["risk"].get("environment_risk_pressure", 0.5)
    opp_stab = 1 - data["opportunity"].get("opportunity_environment_pressure", 0.5)

    return {
        "meta": meta_stab,
        "drift": drift,
        "volatility": vol,
        "instability": instab,
        "shock": shock,
        "fusion": fusion_stab,
        "risk": risk_stab,
        "opportunity": opp_stab,
    }


def _compute_meta_stability_score(components):
    """
    Combine stability components into unified meta-stability score.
    """

    score = float(
        (components["meta"] * 0.20) +
        (components["drift"] * 0.15) +
        (components["volatility"] * 0.15) +
        (components["instability"] * 0.15) +
        (components["shock"] * 0.15) +
        (components["fusion"] * 0.10) +
        (components["risk"] * 0.05) +
        (components["opportunity"] * 0.05)
    )

    return max(0.0, min(score, 1.0))


def _classify_meta_stability_state(score):
    """
    Classify meta-stability environment.
    """

    if score > 0.70:
        return "High Meta-Stability (Favorable Environment)"

    if score > 0.40:
        return "Moderate Meta-Stability (Neutral Environment)"

    return "Low Meta-Stability (Unstable Environment)"


def _build_meta_stability_export(score, state, components):
    """
    Build the final meta-stability export object.
    """

    return {
        "meta_stability_score": score,
        "meta_stability_state": state,
        "stability_components": components,
    }


def render_meta_stability_engine():
    """
    Full UI for the Meta-Stability Engine (V37).
    """
    st.header("Meta-Stability Engine (V37)")
    st.caption("Long-horizon stability + predictive stability model.")

    data = _collect_meta_stability_inputs()

    components = _compute_stability_components(data)
    score = _compute_meta_stability_score(components)
    state = _classify_meta_stability_state(score)

    export = _build_meta_stability_export(score, state, components)

    # Save export
    st.session_state["meta_stability_export"] = export

    themed_card_container()
    st.markdown(f"## Meta-Stability State: **{state}**")

    themed_card_container()
    st.markdown("### Meta-Stability Score")
    st.markdown(f"`{score:.4f}`")

    themed_card_container()
    st.markdown("### Stability Components")
    st.json(components)

    themed_card_container()
    st.markdown("### Meta-Stability Export Object")
    st.json(export)

    st.success("Meta-Stability Engine complete.")
# ------------- CHUNK 210: ADAPTIVE PARLAY ENGINE (V37) -------------

def _collect_adaptive_parlay_inputs():
    """
    Collect all upstream V37 signals:
    - predictive_fusion_export
    - threshold_export
    - volatility_cycle_export
    - instability_export
    - shock_export
    - meta_stability_export
    - adaptive_risk_export
    - adaptive_opportunity_export
    - parlay_export (V36)
    """

    return {
        "predictive_fusion": st.session_state.get("predictive_fusion_export"),
        "thresholds": st.session_state.get("threshold_export"),
        "volatility": st.session_state.get("volatility_cycle_export"),
        "instability": st.session_state.get("instability_export"),
        "shock": st.session_state.get("shock_export"),
        "meta_stability": st.session_state.get("meta_stability_export"),
        "risk": st.session_state.get("adaptive_risk_export"),
        "opportunity": st.session_state.get("adaptive_opportunity_export"),
        "parlay": st.session_state.get("parlay_export"),
    }


def _compute_parlay_environment_pressure(volatility, instability, shock, meta_stability):
    """
    Compute parlay environment pressure:
    - volatility expansion increases pressure
    - instability forecast increases pressure
    - shock forecast increases pressure
    - low meta-stability increases pressure
    """

    vol = volatility.get("volatility_cycle_score", 0.5)
    instab = instability.get("instability_forecast_score", 0.5)
    shock_score = shock.get("shock_forecast_score", 0.5)
    meta = meta_stability.get("meta_stability_score", 0.5)

    pressure = float(
        (vol * 0.30) +
        (instab * 0.25) +
        (shock_score * 0.25) +
        ((1 - meta) * 0.20)
    )

    return max(0.0, min(pressure, 1.0))


def _compute_parlay_signal_strength(predictive_fusion, opportunity, parlay):
    """
    Compute parlay signal strength:
    - predictive fusion score
    - opportunity confidence
    - raw parlay score
    """

    fusion_score = predictive_fusion.get("predictive_fusion_score", 0.5)
    opp_conf = opportunity.get("adaptive_opportunity_confidence", 0.5)
    parlay_score = parlay.get("parlay_score", 0.5)

    strength = float(
        (fusion_score * 0.40) +
        (opp_conf * 0.35) +
        (parlay_score * 0.25)
    )

    return max(0.0, min(strength, 1.0))


def _compute_adaptive_parlay_weight(strength, pressure, thresholds):
    """
    Compute adaptive parlay weight:
    - increases with signal strength
    - decreases with environment pressure
    - scaled by dynamic thresholds
    """

    base_weight = thresholds["dynamic_thresholds"]["fusion_weight"]

    raw = float(
        (strength * 1.30) -
        (pressure * 1.10)
    )

    weight = raw * base_weight
    return max(0.10, min(weight, 2.50))  # bounded between 0.1 and 2.5


def _compute_parlay_confidence(strength, weight, pressure):
    """
    Compute parlay confidence:
    - increases with strength
    - increases with weight
    - decreases with pressure
    """

    confidence = float(
        (strength * 0.50) +
        (weight * 0.30) -
        (pressure * 0.20)
    )

    return max(0.0, min(confidence, 1.0))


def _build_adaptive_parlay_export(weight, confidence, strength, pressure):
    """
    Build the final adaptive parlay export object.
    """

    return {
        "adaptive_parlay_weight": weight,
        "adaptive_parlay_confidence": confidence,
        "parlay_signal_strength": strength,
        "parlay_environment_pressure": pressure,
    }


def render_adaptive_parlay_engine():
    """
    Full UI for the Adaptive Parlay Engine (V37).
    """
    st.header("Adaptive Parlay Engine (V37)")
    st.caption("Environment-aware, predictive parlay intelligence model.")

    data = _collect_adaptive_parlay_inputs()

    pressure = _compute_parlay_environment_pressure(
        data["volatility"],
        data["instability"],
        data["shock"],
        data["meta_stability"]
    )

    strength = _compute_parlay_signal_strength(
        data["predictive_fusion"],
        data["opportunity"],
        data["parlay"]
    )

    weight = _compute_adaptive_parlay_weight(
        strength,
        pressure,
        data["thresholds"]
    )

    confidence = _compute_parlay_confidence(
        strength,
        weight,
        pressure
    )

    export = _build_adaptive_parlay_export(
        weight,
        confidence,
        strength,
        pressure
    )

    # Save export
    st.session_state["adaptive_parlay_export"] = export

    themed_card_container()
    st.markdown("## Parlay Environment Pressure")
    st.markdown(f"`{pressure:.4f}`")

    themed_card_container()
    st.markdown("## Parlay Signal Strength")
    st.markdown(f"`{strength:.4f}`")

    themed_card_container()
    st.markdown("## Adaptive Parlay Weight")
    st.markdown(f"`{weight:.4f}`")

    themed_card_container()
    st.markdown("## Parlay Confidence")
    st.markdown(f"`{confidence:.4f}`")

    themed_card_container()
    st.markdown("### Adaptive Parlay Export Object")
    st.json(export)

    st.success("Adaptive Parlay Engine complete.")
# ------------- CHUNK 211: MULTI-GAME SLIP GENERATOR (V37) -------------

def _collect_multi_game_inputs():
    """
    Collect all upstream V37 signals:
    - predictive_fusion_export
    - adaptive_risk_export
    - adaptive_opportunity_export
    - adaptive_parlay_export
    - meta_stability_export
    - threshold_export
    - final_decision (V36)
    - slip_export (V36)
    """

    return {
        "predictive_fusion": st.session_state.get("predictive_fusion_export"),
        "risk": st.session_state.get("adaptive_risk_export"),
        "opportunity": st.session_state.get("adaptive_opportunity_export"),
        "parlay": st.session_state.get("adaptive_parlay_export"),
        "meta_stability": st.session_state.get("meta_stability_export"),
        "thresholds": st.session_state.get("threshold_export"),
        "decision": st.session_state.get("final_decision"),
        "slip": st.session_state.get("slip_export"),
    }


def _compute_game_priority_score(predictive_fusion, opportunity, parlay, meta_stability):
    """
    Compute game priority score:
    - predictive fusion (forward signal)
    - opportunity confidence
    - parlay confidence
    - meta-stability (environment quality)
    """

    fusion = predictive_fusion.get("predictive_fusion_score", 0.5)
    opp_conf = opportunity.get("adaptive_opportunity_confidence", 0.5)
    parlay_conf = parlay.get("adaptive_parlay_confidence", 0.5)
    meta = meta_stability.get("meta_stability_score", 0.5)

    score = float(
        (fusion * 0.40) +
        (opp_conf * 0.30) +
        (parlay_conf * 0.20) +
        (meta * 0.10)
    )

    return max(0.0, min(score, 1.0))


def _compute_slip_confidence(priority_score, risk, opportunity, parlay):
    """
    Compute slip confidence:
    - game priority score
    - adaptive unit size
    - opportunity weight
    - parlay weight
    """

    unit = risk.get("adaptive_unit_size", 1.0)
    opp_weight = opportunity.get("adaptive_opportunity_weight", 1.0)
    parlay_weight = parlay.get("adaptive_parlay_weight", 1.0)

    confidence = float(
        (priority_score * 0.50) +
        (unit * 0.20) +
        (opp_weight * 0.15) +
        (parlay_weight * 0.15)
    )

    return max(0.0, min(confidence, 1.0))


def _compute_slip_size(confidence, risk):
    """
    Compute slip size:
    - increases with slip confidence
    - bounded by exposure limit
    """

    exposure_limit = risk.get("exposure_limit", 2.0)

    size = float(confidence * exposure_limit)
    return max(0.10, min(size, exposure_limit))


def _build_multi_game_slip(priority_score, confidence, size, decision, slip):
    """
    Build the final multi-game slip export object.
    """

    return {
        "multi_game_priority_score": priority_score,
        "multi_game_slip_confidence": confidence,
        "multi_game_slip_size": size,
        "primary_game_decision": decision,
        "primary_game_slip": slip,
    }


def render_multi_game_slip_generator():
    """
    Full UI for the Multi-Game Slip Generator (V37).
    """
    st.header("Multi-Game Slip Generator (V37)")
    st.caption("Generates multi-game slips using predictive fusion, adaptive risk, and adaptive opportunity.")

    data = _collect_multi_game_inputs()

    priority_score = _compute_game_priority_score(
        data["predictive_fusion"],
        data["opportunity"],
        data["parlay"],
        data["meta_stability"]
    )

    confidence = _compute_slip_confidence(
        priority_score,
        data["risk"],
        data["opportunity"],
        data["parlay"]
    )

    size = _compute_slip_size(confidence, data["risk"])

    export = _build_multi_game_slip(
        priority_score,
        confidence,
        size,
        data["decision"],
        data["slip"]
    )

    # Save export
    st.session_state["multi_game_slip_export"] = export

    themed_card_container()
    st.markdown("## Multi-Game Priority Score")
    st.markdown(f"`{priority_score:.4f}`")

    themed_card_container()
    st.markdown("## Multi-Game Slip Confidence")
    st.markdown(f"`{confidence:.4f}`")

    themed_card_container()
    st.markdown("## Multi-Game Slip Size")
    st.markdown(f"`{size:.4f}`")

    themed_card_container()
    st.markdown("### Multi-Game Slip Export Object")
    st.json(export)

    st.success("Multi-Game Slip Generator complete.")
# ------------- CHUNK 212: V37 FINAL DECISION ENGINE -------------

def _collect_v37_decision_inputs():
    """
    Collect all upstream V37 signals:
    - predictive_fusion_export
    - adaptive_risk_export
    - adaptive_opportunity_export
    - adaptive_parlay_export
    - multi_game_slip_export
    - meta_stability_export
    - threshold_export
    - final_decision (V36 baseline)
    """

    return {
        "predictive_fusion": st.session_state.get("predictive_fusion_export"),
        "risk": st.session_state.get("adaptive_risk_export"),
        "opportunity": st.session_state.get("adaptive_opportunity_export"),
        "parlay": st.session_state.get("adaptive_parlay_export"),
        "multi_slip": st.session_state.get("multi_game_slip_export"),
        "meta_stability": st.session_state.get("meta_stability_export"),
        "thresholds": st.session_state.get("threshold_export"),
        "baseline": st.session_state.get("final_decision"),
    }


def _compute_environment_quality(meta_stability, risk, opportunity, parlay):
    """
    Compute environment quality:
    - meta-stability (long horizon)
    - risk pressure (inverse)
    - opportunity pressure (inverse)
    - parlay pressure (inverse)
    """

    meta = meta_stability.get("meta_stability_score", 0.5)
    risk_inv = 1 - risk.get("environment_risk_pressure", 0.5)
    opp_inv = 1 - opportunity.get("opportunity_environment_pressure", 0.5)
    parlay_inv = 1 - parlay.get("parlay_environment_pressure", 0.5)

    quality = float(
        (meta * 0.40) +
        (risk_inv * 0.25) +
        (opp_inv * 0.20) +
        (parlay_inv * 0.15)
    )

    return max(0.0, min(quality, 1.0))


def _compute_predictive_strength(predictive_fusion, opportunity, parlay, multi_slip):
    """
    Compute predictive strength:
    - predictive fusion score
    - opportunity confidence
    - parlay confidence
    - multi-game slip confidence
    """

    fusion = predictive_fusion.get("predictive_fusion_score", 0.5)
    opp_conf = opportunity.get("adaptive_opportunity_confidence", 0.5)
    parlay_conf = parlay.get("adaptive_parlay_confidence", 0.5)
    slip_conf = multi_slip.get("multi_game_slip_confidence", 0.5)

    strength = float(
        (fusion * 0.40) +
        (opp_conf * 0.25) +
        (parlay_conf * 0.20) +
        (slip_conf * 0.15)
    )

    return max(0.0, min(strength, 1.0))


def _compute_final_decision_score(env_quality, predictive_strength, thresholds):
    """
    Compute final decision score:
    - increases with predictive strength
    - increases with environment quality
    - adjusted by dynamic thresholds
    """

    bet_threshold = thresholds["dynamic_thresholds"]["bet_threshold"]
    strong_threshold = thresholds["dynamic_thresholds"]["strong_bet_threshold"]

    raw = float(
        (predictive_strength * 0.60) +
        (env_quality * 0.40)
    )

    # Normalize to 0–1
    score = max(0.0, min(raw, 1.0))

    # Classification
    if score >= strong_threshold:
        decision = "STRONG BET"
    elif score >= bet_threshold:
        decision = "BET"
    else:
        decision = "PASS"

    return score, decision


def _build_v37_decision_export(score, decision, env_quality, predictive_strength, multi_slip):
    """
    Build the final V37 decision export object.
    """

    return {
        "v37_final_score": score,
        "v37_final_decision": decision,
        "environment_quality": env_quality,
        "predictive_strength": predictive_strength,
        "multi_game_slip": multi_slip,
    }


def render_v37_final_decision_engine():
    """
    Full UI for the V37 Final Decision Engine.
    """
    st.header("V37 Final Decision Engine")
    st.caption("Predictive, multi-game, environment-aware decision intelligence.")

    data = _collect_v37_decision_inputs()

    env_quality = _compute_environment_quality(
        data["meta_stability"],
        data["risk"],
        data["opportunity"],
        data["parlay"]
    )

    predictive_strength = _compute_predictive_strength(
        data["predictive_fusion"],
        data["opportunity"],
        data["parlay"],
        data["multi_slip"]
    )

    score, decision = _compute_final_decision_score(
        env_quality,
        predictive_strength,
        data["thresholds"]
    )

    export = _build_v37_decision_export(
        score,
        decision,
        env_quality,
        predictive_strength,
        data["multi_slip"]
    )

    # Save export
    st.session_state["v37_final_decision_export"] = export

    themed_card_container()
    st.markdown(f"## V37 Final Decision: **{decision}**")

    themed_card_container()
    st.markdown("### V37 Final Score")
    st.markdown(f"`{score:.4f}`")

    themed_card_container()
    st.markdown("### Environment Quality")
    st.markdown(f"`{env_quality:.4f}`")

    themed_card_container()
    st.markdown("### Predictive Strength")
    st.markdown(f"`{predictive_strength:.4f}`")

    themed_card_container()
    st.markdown("### Multi-Game Slip")
    st.json(data["multi_slip"])

    themed_card_container()
    st.markdown("### V37 Final Decision Export Object")
    st.json(export)

    st.success("V37 Final Decision Engine complete.")
# ------------- CHUNK 213: V37 MASTER ENGINE (GLOBAL ORCHESTRATOR) -------------

def _collect_master_inputs():
    """
    Collect all upstream V37 signals:
    - v37_final_decision_export
    - predictive_fusion_export
    - adaptive_risk_export
    - adaptive_opportunity_export
    - adaptive_parlay_export
    - multi_game_slip_export
    - meta_stability_export
    - threshold_export
    - volatility_cycle_export
    - instability_export
    - shock_export
    - temporal_drift_export
    - meta_export
    """

    return {
        "final": st.session_state.get("v37_final_decision_export"),
        "fusion": st.session_state.get("predictive_fusion_export"),
        "risk": st.session_state.get("adaptive_risk_export"),
        "opportunity": st.session_state.get("adaptive_opportunity_export"),
        "parlay": st.session_state.get("adaptive_parlay_export"),
        "slip": st.session_state.get("multi_game_slip_export"),
        "meta_stability": st.session_state.get("meta_stability_export"),
        "thresholds": st.session_state.get("threshold_export"),
        "volatility": st.session_state.get("volatility_cycle_export"),
        "instability": st.session_state.get("instability_export"),
        "shock": st.session_state.get("shock_export"),
        "temporal": st.session_state.get("temporal_drift_export"),
        "meta": st.session_state.get("meta_export"),
    }


def _compute_global_environment_state(meta_stability, volatility, instability, shock, temporal):
    """
    Compute global environment state:
    - meta-stability (long horizon)
    - volatility cycle (inverse)
    - instability forecast (inverse)
    - shock forecast (inverse)
    - temporal drift
    """

    meta = meta_stability.get("meta_stability_score", 0.5)
    vol = 1 - volatility.get("volatility_cycle_score", 0.5)
    instab = 1 - instability.get("instability_forecast_score", 0.5)
    shock_inv = 1 - shock.get("shock_forecast_score", 0.5)
    drift = temporal.get("temporal_drift_score", 0.5)

    state = float(
        (meta * 0.35) +
        (vol * 0.20) +
        (instab * 0.20) +
        (shock_inv * 0.15) +
        (drift * 0.10)
    )

    return max(0.0, min(state, 1.0))


def _compute_global_predictive_strength(fusion, opportunity, parlay, slip, final):
    """
    Compute global predictive strength:
    - predictive fusion
    - opportunity confidence
    - parlay confidence
    - multi-game slip confidence
    - final decision score
    """

    fusion_score = fusion.get("predictive_fusion_score", 0.5)
    opp_conf = opportunity.get("adaptive_opportunity_confidence", 0.5)
    parlay_conf = parlay.get("adaptive_parlay_confidence", 0.5)
    slip_conf = slip.get("multi_game_slip_confidence", 0.5)
    final_score = final.get("v37_final_score", 0.5)

    strength = float(
        (fusion_score * 0.35) +
        (opp_conf * 0.25) +
        (parlay_conf * 0.20) +
        (slip_conf * 0.10) +
        (final_score * 0.10)
    )

    return max(0.0, min(strength, 1.0))


def _compute_global_system_pressure(volatility, instability, shock, risk, opportunity, parlay):
    """
    Compute global system pressure:
    - volatility expansion
    - instability forecast
    - shock forecast
    - risk pressure
    - opportunity pressure
    - parlay pressure
    """

    vol = volatility.get("volatility_cycle_score", 0.5)
    instab = instability.get("instability_forecast_score", 0.5)
    shock_score = shock.get("shock_forecast_score", 0.5)
    risk_p = risk.get("environment_risk_pressure", 0.5)
    opp_p = opportunity.get("opportunity_environment_pressure", 0.5)
    parlay_p = parlay.get("parlay_environment_pressure", 0.5)

    pressure = float(
        (vol * 0.25) +
        (instab * 0.20) +
        (shock_score * 0.20) +
        (risk_p * 0.15) +
        (opp_p * 0.10) +
        (parlay_p * 0.10)
    )

    return max(0.0, min(pressure, 1.0))


def _compute_master_score(env_state, predictive_strength, pressure):
    """
    Compute the V37 Master Score:
    - increases with environment quality
    - increases with predictive strength
    - decreases with system pressure
    """

    raw = float(
        (env_state * 0.45) +
        (predictive_strength * 0.45) -
        (pressure * 0.30)
    )

    return max(0.0, min(raw, 1.0))


def _classify_master_state(score):
    """
    Classify the global system state.
    """

    if score > 0.70:
        return "Favorable System State (Green Zone)"

    if score > 0.40:
        return "Neutral System State (Yellow Zone)"

    return "Unfavorable System State (Red Zone)"


def _build_master_export(score, state, env_state, predictive_strength, pressure, final, slip):
    """
    Build the final V37 Master Export Object.
    """

    return {
        "v37_master_score": score,
        "v37_master_state": state,
        "environment_state": env_state,
        "predictive_strength": predictive_strength,
        "system_pressure": pressure,
        "final_decision": final,
        "multi_game_slip": slip,
    }


def render_v37_master_engine():
    """
    Full UI for the V37 Master Engine.
    """
    st.header("V37 Master Engine")
    st.caption("Global orchestrator for all V37 predictive intelligence.")

    data = _collect_master_inputs()

    env_state = _compute_global_environment_state(
        data["meta_stability"],
        data["volatility"],
        data["instability"],
        data["shock"],
        data["temporal"]
    )

    predictive_strength = _compute_global_predictive_strength(
        data["fusion"],
        data["opportunity"],
        data["parlay"],
        data["slip"],
        data["final"]
    )

    pressure = _compute_global_system_pressure(
        data["volatility"],
        data["instability"],
        data["shock"],
        data["risk"],
        data["opportunity"],
        data["parlay"]
    )

    score = _compute_master_score(env_state, predictive_strength, pressure)
    state = _classify_master_state(score)

    export = _build_master_export(
        score,
        state,
        env_state,
        predictive_strength,
        pressure,
        data["final"],
        data["slip"]
    )

    # Save export
    st.session_state["v37_master_export"] = export

    themed_card_container()
    st.markdown(f"## V37 Master State: **{state}**")

    themed_card_container()
    st.markdown("### V37 Master Score")
    st.markdown(f"`{score:.4f}`")

    themed_card_container()
    st.markdown("### Environment State")
    st.markdown(f"`{env_state:.4f}`")

    themed_card_container()
    st.markdown("### Predictive Strength")
    st.markdown(f"`{predictive_strength:.4f}`")

    themed_card_container()
    st.markdown("### System Pressure")
    st.markdown(f"`{pressure:.4f}`")

    themed_card_container()
    st.markdown("### V37 Master Export Object")
    st.json(export)

    st.success("V37 Master Engine complete.")
# ------------- CHUNK 214: V37 NARRATIVE ENGINE (AI COMMENTARY 3.0) -------------

def _collect_narrative_inputs():
    """
    Collect all upstream V37 signals:
    - v37_master_export
    - v37_final_decision_export
    - predictive_fusion_export
    - adaptive_risk_export
    - adaptive_opportunity_export
    - adaptive_parlay_export
    - multi_game_slip_export
    - meta_stability_export
    - volatility_cycle_export
    - instability_export
    - shock_export
    - temporal_drift_export
    - meta_export
    """

    return {
        "master": st.session_state.get("v37_master_export"),
        "final": st.session_state.get("v37_final_decision_export"),
        "fusion": st.session_state.get("predictive_fusion_export"),
        "risk": st.session_state.get("adaptive_risk_export"),
        "opportunity": st.session_state.get("adaptive_opportunity_export"),
        "parlay": st.session_state.get("adaptive_parlay_export"),
        "slip": st.session_state.get("multi_game_slip_export"),
        "meta_stability": st.session_state.get("meta_stability_export"),
        "volatility": st.session_state.get("volatility_cycle_export"),
        "instability": st.session_state.get("instability_export"),
        "shock": st.session_state.get("shock_export"),
        "temporal": st.session_state.get("temporal_drift_export"),
        "meta": st.session_state.get("meta_export"),
    }


def _narrative_environment_section(data):
    """
    Generate environment commentary.
    """

    env_state = data["master"]["environment_state"]
    vol_state = data["volatility"]["volatility_cycle_state"]
    instab_state = data["instability"]["instability_forecast_state"]
    shock_state = data["shock"]["shock_forecast_state"]
    meta_state = data["meta_stability"]["meta_stability_state"]

    return f"""
### 🌍 Environment Overview
- **Meta-Stability:** {meta_state}
- **Volatility Cycle:** {vol_state}
- **Instability Forecast:** {instab_state}
- **Shock/Turbulence Forecast:** {shock_state}
- **Global Environment Score:** `{env_state:.4f}`

The environment summary reflects long-horizon stability, volatility cycles, predictive instability, and shock risk.
"""


def _narrative_predictive_section(data):
    """
    Generate predictive commentary.
    """

    fusion_state = data["fusion"]["predictive_fusion_state"]
    opp_conf = data["opportunity"]["adaptive_opportunity_confidence"]
    parlay_conf = data["parlay"]["adaptive_parlay_confidence"]
    slip_conf = data["slip"]["multi_game_slip_confidence"]
    pred_strength = data["master"]["predictive_strength"]

    return f"""
### 🔮 Predictive Intelligence
- **Predictive Fusion:** {fusion_state}
- **Opportunity Confidence:** `{opp_conf:.4f}`
- **Parlay Confidence:** `{parlay_conf:.4f}`
- **Slip Confidence:** `{slip_conf:.4f}`
- **Global Predictive Strength:** `{pred_strength:.4f}`

Predictive intelligence blends forward macro/micro evolution, opportunity alignment, parlay quality, and multi-game slip strength.
"""


def _narrative_risk_section(data):
    """
    Generate risk commentary.
    """

    unit = data["risk"]["adaptive_unit_size"]
    limit = data["risk"]["exposure_limit"]
    pressure = data["risk"]["environment_risk_pressure"]

    return f"""
### ⚠️ Risk Intelligence
- **Adaptive Unit Size:** `{unit:.4f}`
- **Exposure Limit:** `{limit:.4f}`
- **Risk Pressure:** `{pressure:.4f}`

Risk intelligence dynamically adjusts sizing and exposure based on volatility, instability, shock risk, and long-horizon stability.
"""


def _narrative_opportunity_section(data):
    """
    Generate opportunity commentary.
    """

    weight = data["opportunity"]["adaptive_opportunity_weight"]
    conf = data["opportunity"]["adaptive_opportunity_confidence"]
    pressure = data["opportunity"]["opportunity_environment_pressure"]

    return f"""
### 🎯 Opportunity Intelligence
- **Opportunity Weight:** `{weight:.4f}`
- **Opportunity Confidence:** `{conf:.4f}`
- **Opportunity Pressure:** `{pressure:.4f}`

Opportunity intelligence adapts to predictive fusion, environment pressure, and opportunity strength.
"""


def _narrative_parlay_section(data):
    """
    Generate parlay commentary.
    """

    weight = data["parlay"]["adaptive_parlay_weight"]
    conf = data["parlay"]["adaptive_parlay_confidence"]
    pressure = data["parlay"]["parlay_environment_pressure"]

    return f"""
### 🔗 Parlay Intelligence
- **Parlay Weight:** `{weight:.4f}`
- **Parlay Confidence:** `{conf:.4f}`
- **Parlay Pressure:** `{pressure:.4f}`

Parlay intelligence scales based on predictive alignment, environment quality, and correlation risk.
"""


def _narrative_final_decision_section(data):
    """
    Generate final decision commentary.
    """

    decision = data["final"]["v37_final_decision"]
    score = data["final"]["v37_final_score"]

    return f"""
### 🧠 Final Decision
- **Decision:** **{decision}**
- **Final Score:** `{score:.4f}`

The final decision synthesizes predictive strength, environment quality, and dynamic thresholds.
"""


def _narrative_master_section(data):
    """
    Generate master-level commentary.
    """

    state = data["master"]["v37_master_state"]
    score = data["master"]["v37_master_score"]
    pressure = data["master"]["system_pressure"]

    return f"""
### 🏆 Master System Summary
- **Master State:** {state}
- **Master Score:** `{score:.4f}`
- **System Pressure:** `{pressure:.4f}`

The Master Engine integrates all V37 intelligence layers into a unified global system state.
"""


def _build_narrative_export(text):
    """
    Build the final narrative export object.
    """

    return {
        "v37_narrative": text
    }


def render_v37_narrative_engine():
    """
    Full UI for the V37 Narrative Engine.
    """
    st.header("V37 Narrative Engine (AI Commentary 3.0)")
    st.caption("Generates human-readable commentary based on all V37 intelligence layers.")

    data = _collect_narrative_inputs()

    narrative = (
        _narrative_environment_section(data)
        + _narrative_predictive_section(data)
        + _narrative_risk_section(data)
        + _narrative_opportunity_section(data)
        + _narrative_parlay_section(data)
        + _narrative_final_decision_section(data)
        + _narrative_master_section(data)
    )

    export = _build_narrative_export(narrative)

    # Save export
    st.session_state["v37_narrative_export"] = export

    themed_card_container()
    st.markdown("## V37 Narrative")
    st.markdown(narrative)

    themed_card_container()
    st.markdown("### Narrative Export Object")
    st.json(export)

    st.success("V37 Narrative Engine complete.")
# ------------- CHUNK 215: V37 REINFORCEMENT ENGINE (SELF-LEARNING FEEDBACK BRAIN) -------------

def _collect_reinforcement_inputs():
    """
    Collect all upstream V37 signals:
    - v37_master_export
    - v37_final_decision_export
    - v37_narrative_export
    - threshold_export
    - adaptive_risk_export
    - adaptive_opportunity_export
    - adaptive_parlay_export
    - predictive_fusion_export
    - actual_outcome (win/loss/push) — provided by user or log
    """

    return {
        "master": st.session_state.get("v37_master_export"),
        "final": st.session_state.get("v37_final_decision_export"),
        "narrative": st.session_state.get("v37_narrative_export"),
        "thresholds": st.session_state.get("threshold_export"),
        "risk": st.session_state.get("adaptive_risk_export"),
        "opportunity": st.session_state.get("adaptive_opportunity_export"),
        "parlay": st.session_state.get("adaptive_parlay_export"),
        "fusion": st.session_state.get("predictive_fusion_export"),
        "outcome": st.session_state.get("actual_outcome", None),  # "WIN", "LOSS", "PUSH"
    }


def _compute_outcome_score(outcome):
    """
    Convert outcome into reinforcement signal.
    """

    if outcome == "WIN":
        return 1.0
    if outcome == "LOSS":
        return 0.0
    if outcome == "PUSH":
        return 0.5

    return 0.5  # default neutral


def _compute_reinforcement_signal(master, final, outcome_score):
    """
    Compute reinforcement signal:
    - positive when system was correct
    - negative when system was wrong
    - scaled by master score and final decision strength
    """

    master_score = master.get("v37_master_score", 0.5)
    final_score = final.get("v37_final_score", 0.5)

    # If system was confident and wrong → strong negative reinforcement
    # If system was confident and right → strong positive reinforcement
    # If system was unsure → mild reinforcement
    signal = float(
        (outcome_score * 1.25 * final_score) -
        ((1 - outcome_score) * 1.25 * final_score) +
        (master_score * 0.25)
    )

    return max(-1.0, min(signal, 1.0))


def _compute_threshold_adjustments(signal):
    """
    Convert reinforcement signal into threshold adjustments.
    """

    return {
        "threshold_shift": signal * -0.05,          # negative signal → raise thresholds
        "confidence_boost": signal * 0.05,          # positive signal → boost confidence
        "risk_tolerance_shift": signal * 0.04,      # positive signal → increase risk tolerance
    }


def _compute_weight_adjustments(signal):
    """
    Adjust opportunity, parlay, and fusion weights.
    """

    return {
        "opportunity_weight_shift": signal * 0.06,
        "parlay_weight_shift": signal * 0.05,
        "fusion_weight_shift": signal * 0.04,
    }


def _compute_environment_sensitivity_adjustments(signal):
    """
    Adjust sensitivity to volatility, instability, and shock.
    """

    return {
        "volatility_sensitivity_shift": signal * -0.05,
        "instability_sensitivity_shift": signal * -0.05,
        "shock_sensitivity_shift": signal * -0.05,
    }


def _build_reinforcement_export(signal, outcome_score, thresholds, weights, sensitivity):
    """
    Build the final reinforcement export object.
    """

    return {
        "reinforcement_signal": signal,
        "outcome_score": outcome_score,
        "threshold_adjustments": thresholds,
        "weight_adjustments": weights,
        "sensitivity_adjustments": sensitivity,
    }


def render_v37_reinforcement_engine():
    """
    Full UI for the V37 Reinforcement Engine.
    """
    st.header("V37 Reinforcement Engine (Self-Learning)")
    st.caption("Learns from outcomes and adjusts thresholds, weights, and sensitivities.")

    data = _collect_reinforcement_inputs()

    outcome_score = _compute_outcome_score(data["outcome"])
    signal = _compute_reinforcement_signal(data["master"], data["final"], outcome_score)

    thresholds = _compute_threshold_adjustments(signal)
    weights = _compute_weight_adjustments(signal)
    sensitivity = _compute_environment_sensitivity_adjustments(signal)

    export = _build_reinforcement_export(signal, outcome_score, thresholds, weights, sensitivity)

    # Save export
    st.session_state["v37_reinforcement_export"] = export

    themed_card_container()
    st.markdown("## Reinforcement Signal")
    st.markdown(f"`{signal:.4f}`")

    themed_card_container()
    st.markdown("### Outcome Score")
    st.markdown(f"`{outcome_score:.4f}`")

    themed_card_container()
    st.markdown("### Threshold Adjustments")
    st.json(thresholds)

    themed_card_container()
    st.markdown("### Weight Adjustments")
    st.json(weights)

    themed_card_container()
    st.markdown("### Sensitivity Adjustments")
    st.json(sensitivity)

    themed_card_container()
    st.markdown("### Reinforcement Export Object")
    st.json(export)

    st.success("V37 Reinforcement Engine complete.")
# ------------- CHUNK 216: V37 SYSTEM MONITOR (GLOBAL DIAGNOSTICS ENGINE) -------------

def _collect_system_monitor_inputs():
    """
    Collect all upstream V37 signals:
    - v37_master_export
    - v37_final_decision_export
    - v37_reinforcement_export
    - predictive_fusion_export
    - adaptive_risk_export
    - adaptive_opportunity_export
    - adaptive_parlay_export
    - multi_game_slip_export
    - meta_stability_export
    - volatility_cycle_export
    - instability_export
    - shock_export
    - temporal_drift_export
    - threshold_export
    """

    return {
        "master": st.session_state.get("v37_master_export"),
        "final": st.session_state.get("v37_final_decision_export"),
        "reinforcement": st.session_state.get("v37_reinforcement_export"),
        "fusion": st.session_state.get("predictive_fusion_export"),
        "risk": st.session_state.get("adaptive_risk_export"),
        "opportunity": st.session_state.get("adaptive_opportunity_export"),
        "parlay": st.session_state.get("adaptive_parlay_export"),
        "slip": st.session_state.get("multi_game_slip_export"),
        "meta_stability": st.session_state.get("meta_stability_export"),
        "volatility": st.session_state.get("volatility_cycle_export"),
        "instability": st.session_state.get("instability_export"),
        "shock": st.session_state.get("shock_export"),
        "temporal": st.session_state.get("temporal_drift_export"),
        "thresholds": st.session_state.get("threshold_export"),
    }


def _compute_engine_alignment(fusion, risk, opportunity, parlay, slip):
    """
    Compute alignment between predictive engines:
    - predictive fusion
    - adaptive risk
    - adaptive opportunity
    - adaptive parlay
    - multi-game slip
    """

    fusion_score = fusion.get("predictive_fusion_score", 0.5)
    opp_conf = opportunity.get("adaptive_opportunity_confidence", 0.5)
    parlay_conf = parlay.get("adaptive_parlay_confidence", 0.5)
    slip_conf = slip.get("multi_game_slip_confidence", 0.5)
    unit = risk.get("adaptive_unit_size", 1.0)

    # High alignment = engines pointing in same direction
    alignment = float(
        (fusion_score * 0.35) +
        (opp_conf * 0.25) +
        (parlay_conf * 0.20) +
        (slip_conf * 0.10) +
        (unit * 0.10)
    )

    return max(0.0, min(alignment, 1.0))


def _compute_environment_stress(volatility, instability, shock, meta_stability, temporal):
    """
    Compute environment stress:
    - volatility expansion
    - instability forecast
    - shock forecast
    - low meta-stability
    - low temporal drift
    """

    vol = volatility.get("volatility_cycle_score", 0.5)
    instab = instability.get("instability_forecast_score", 0.5)
    shock_score = shock.get("shock_forecast_score", 0.5)
    meta = 1 - meta_stability.get("meta_stability_score", 0.5)
    drift = 1 - temporal.get("temporal_drift_score", 0.5)

    stress = float(
        (vol * 0.25) +
        (instab * 0.25) +
        (shock_score * 0.20) +
        (meta * 0.15) +
        (drift * 0.15)
    )

    return max(0.0, min(stress, 1.0))


def _compute_system_pressure(risk, opportunity, parlay):
    """
    Compute internal system pressure:
    - risk pressure
    - opportunity pressure
    - parlay pressure
    """

    risk_p = risk.get("environment_risk_pressure", 0.5)
    opp_p = opportunity.get("opportunity_environment_pressure", 0.5)
    parlay_p = parlay.get("parlay_environment_pressure", 0.5)

    pressure = float(
        (risk_p * 0.40) +
        (opp_p * 0.30) +
        (parlay_p * 0.30)
    )

    return max(0.0, min(pressure, 1.0))


def _compute_system_health_score(alignment, stress, pressure, master):
    """
    Compute global system health:
    - increases with engine alignment
    - decreases with environment stress
    - decreases with system pressure
    - influenced by master score
    """

    master_score = master.get("v37_master_score", 0.5)

    raw = float(
        (alignment * 0.45) +
        (master_score * 0.25) -
        (stress * 0.20) -
        (pressure * 0.10)
    )

    return max(0.0, min(raw, 1.0))


def _classify_system_health_state(score):
    """
    Classify system health.
    """

    if score > 0.70:
        return "Healthy System State (Optimal)"

    if score > 0.40:
        return "Moderate System State (Caution)"

    return "Unhealthy System State (Critical)"


def _build_system_monitor_export(score, state, alignment, stress, pressure):
    """
    Build the final system monitor export object.
    """

    return {
        "system_health_score": score,
        "system_health_state": state,
        "engine_alignment": alignment,
        "environment_stress": stress,
        "system_pressure": pressure,
    }


def render_v37_system_monitor():
    """
    Full UI for the V37 System Monitor.
    """
    st.header("V37 System Monitor")
    st.caption("Global diagnostics, engine alignment, environment stress, and system health.")

    data = _collect_system_monitor_inputs()

    alignment = _compute_engine_alignment(
        data["fusion"],
        data["risk"],
        data["opportunity"],
        data["parlay"],
        data["slip"]
    )

    stress = _compute_environment_stress(
        data["volatility"],
        data["instability"],
        data["shock"],
        data["meta_stability"],
        data["temporal"]
    )

    pressure = _compute_system_pressure(
        data["risk"],
        data["opportunity"],
        data["parlay"]
    )

    score = _compute_system_health_score(
        alignment,
        stress,
        pressure,
        data["master"]
    )

    state = _classify_system_health_state(score)

    export = _build_system_monitor_export(
        score,
        state,
        alignment,
        stress,
        pressure
    )

    # Save export
    st.session_state["v37_system_monitor_export"] = export

    themed_card_container()
    st.markdown(f"## System Health State: **{state}**")

    themed_card_container()
    st.markdown("### System Health Score")
    st.markdown(f"`{score:.4f}`")

    themed_card_container()
    st.markdown("### Engine Alignment")
    st.markdown(f"`{alignment:.4f}`")

    themed_card_container()
    st.markdown("### Environment Stress")
    st.markdown(f"`{stress:.4f}`")

    themed_card_container()
    st.markdown("### System Pressure")
    st.markdown(f"`{pressure:.4f}`")

    themed_card_container()
    st.markdown("### System Monitor Export Object")
    st.json(export)

    st.success("V37 System Monitor complete.")
# ------------- CHUNK 217: V37 META-BRAIN (GLOBAL SYNTHESIS ENGINE) -------------

def _collect_meta_brain_inputs():
    """
    Collect all upstream V37 signals:
    - v37_master_export
    - v37_system_monitor_export
    - v37_final_decision_export
    - v37_narrative_export
    - v37_reinforcement_export
    - predictive_fusion_export
    - adaptive_risk_export
    - adaptive_opportunity_export
    - adaptive_parlay_export
    - multi_game_slip_export
    - meta_stability_export
    """

    return {
        "master": st.session_state.get("v37_master_export"),
        "monitor": st.session_state.get("v37_system_monitor_export"),
        "final": st.session_state.get("v37_final_decision_export"),
        "narrative": st.session_state.get("v37_narrative_export"),
        "reinforcement": st.session_state.get("v37_reinforcement_export"),
        "fusion": st.session_state.get("predictive_fusion_export"),
        "risk": st.session_state.get("adaptive_risk_export"),
        "opportunity": st.session_state.get("adaptive_opportunity_export"),
        "parlay": st.session_state.get("adaptive_parlay_export"),
        "slip": st.session_state.get("multi_game_slip_export"),
        "meta_stability": st.session_state.get("meta_stability_export"),
    }


def _compute_meta_alignment(master, monitor, fusion, risk, opportunity, parlay):
    """
    Meta-alignment measures:
    - master score alignment
    - system health alignment
    - predictive fusion alignment
    - risk/opportunity/parlay coherence
    """

    master_score = master.get("v37_master_score", 0.5)
    health = monitor.get("system_health_score", 0.5)
    fusion_score = fusion.get("predictive_fusion_score", 0.5)

    risk_unit = risk.get("adaptive_unit_size", 1.0)
    opp_conf = opportunity.get("adaptive_opportunity_confidence", 0.5)
    parlay_conf = parlay.get("adaptive_parlay_confidence", 0.5)

    alignment = float(
        (master_score * 0.30) +
        (health * 0.25) +
        (fusion_score * 0.20) +
        (opp_conf * 0.10) +
        (parlay_conf * 0.10) +
        (risk_unit * 0.05)
    )

    return max(0.0, min(alignment, 1.0))


def _compute_meta_pressure(master, monitor, risk, opportunity, parlay):
    """
    Meta-pressure measures:
    - system pressure (monitor)
    - environment pressure (master)
    - risk/opportunity/parlay pressure
    """

    sys_pressure = monitor.get("system_pressure", 0.5)
    env_state = 1 - master.get("environment_state", 0.5)

    risk_p = risk.get("environment_risk_pressure", 0.5)
    opp_p = opportunity.get("opportunity_environment_pressure", 0.5)
    parlay_p = parlay.get("parlay_environment_pressure", 0.5)

    pressure = float(
        (sys_pressure * 0.35) +
        (env_state * 0.25) +
        (risk_p * 0.15) +
        (opp_p * 0.15) +
        (parlay_p * 0.10)
    )

    return max(0.0, min(pressure, 1.0))


def _compute_meta_confidence(alignment, pressure, master):
    """
    Meta-confidence measures:
    - increases with alignment
    - decreases with pressure
    - influenced by master score
    """

    master_score = master.get("v37_master_score", 0.5)

    raw = float(
        (alignment * 0.50) +
        (master_score * 0.30) -
        (pressure * 0.20)
    )

    return max(0.0, min(raw, 1.0))


def _classify_meta_state(confidence):
    """
    Classify meta-brain state.
    """

    if confidence > 0.70:
        return "High Meta-Confidence (System Coherent)"

    if confidence > 0.40:
        return "Moderate Meta-Confidence (System Stable)"

    return "Low Meta-Confidence (System Fragmented)"


def _build_meta_brain_export(alignment, pressure, confidence, state):
    """
    Build the final meta-brain export object.
    """

    return {
        "meta_alignment": alignment,
        "meta_pressure": pressure,
        "meta_confidence": confidence,
        "meta_state": state,
    }


def render_v37_meta_brain():
    """
    Full UI for the V37 Meta-Brain.
    """
    st.header("V37 Meta-Brain")
    st.caption("Global synthesis, meta-reasoning, and system-wide coherence engine.")

    data = _collect_meta_brain_inputs()

    alignment = _compute_meta_alignment(
        data["master"],
        data["monitor"],
        data["fusion"],
        data["risk"],
        data["opportunity"],
        data["parlay"]
    )

    pressure = _compute_meta_pressure(
        data["master"],
        data["monitor"],
        data["risk"],
        data["opportunity"],
        data["parlay"]
    )

    confidence = _compute_meta_confidence(
        alignment,
        pressure,
        data["master"]
    )

    state = _classify_meta_state(confidence)

    export = _build_meta_brain_export(
        alignment,
        pressure,
        confidence,
        state
    )

    # Save export
    st.session_state["v37_meta_brain_export"] = export

    themed_card_container()
    st.markdown(f"## Meta-Brain State: **{state}**")

    themed_card_container()
    st.markdown("### Meta-Confidence")
    st.markdown(f"`{confidence:.4f}`")

    themed_card_container()
    st.markdown("### Meta-Alignment")
    st.markdown(f"`{alignment:.4f}`")

    themed_card_container()
    st.markdown("### Meta-Pressure")
    st.markdown(f"`{pressure:.4f}`")

    themed_card_container()
    st.markdown("### Meta-Brain Export Object")
    st.json(export)

    st.success("V37 Meta-Brain complete.")
# ------------- CHUNK 218: V37 SYSTEM DASHBOARD (UI LAYER) -------------

def render_v37_system_dashboard():
    """
    Unified UI dashboard for all V37 engines.
    Displays:
    - Master Engine
    - Final Decision Engine
    - System Monitor
    - Meta-Brain
    - Predictive Fusion
    - Risk / Opportunity / Parlay
    - Multi-Game Slip
    - Narrative
    - Reinforcement
    """

    st.title("V37 System Dashboard")
    st.caption("Unified control panel for all V37 predictive intelligence engines.")

    # --- Load all exports ---
    master = st.session_state.get("v37_master_export")
    final = st.session_state.get("v37_final_decision_export")
    monitor = st.session_state.get("v37_system_monitor_export")
    meta_brain = st.session_state.get("v37_meta_brain_export")
    narrative = st.session_state.get("v37_narrative_export")
    reinforcement = st.session_state.get("v37_reinforcement_export")
    fusion = st.session_state.get("predictive_fusion_export")
    risk = st.session_state.get("adaptive_risk_export")
    opportunity = st.session_state.get("adaptive_opportunity_export")
    parlay = st.session_state.get("adaptive_parlay_export")
    slip = st.session_state.get("multi_game_slip_export")
    meta_stability = st.session_state.get("meta_stability_export")

    # --- MASTER ENGINE ---
    with st.expander("🏆 V37 Master Engine", expanded=True):
        st.json(master)

    # --- FINAL DECISION ENGINE ---
    with st.expander("🧠 Final Decision Engine"):
        st.json(final)

    # --- SYSTEM MONITOR ---
    with st.expander("🩺 System Monitor (Diagnostics)"):
        st.json(monitor)

    # --- META-BRAIN ---
    with st.expander("🧬 Meta-Brain (Global Synthesis)"):
        st.json(meta_brain)

    # --- PREDICTIVE FUSION ---
    with st.expander("🔮 Predictive Fusion Engine"):
        st.json(fusion)

    # --- RISK ENGINE ---
    with st.expander("⚠️ Adaptive Risk Engine"):
        st.json(risk)

    # --- OPPORTUNITY ENGINE ---
    with st.expander("🎯 Adaptive Opportunity Engine"):
        st.json(opportunity)

    # --- PARLAY ENGINE ---
    with st.expander("🔗 Adaptive Parlay Engine"):
        st.json(parlay)

    # --- MULTI-GAME SLIP ---
    with st.expander("🎟️ Multi-Game Slip Generator"):
        st.json(slip)

    # --- META-STABILITY ---
    with st.expander("🌍 Meta-Stability Engine"):
        st.json(meta_stability)

    # --- NARRATIVE ENGINE ---
    with st.expander("📝 Narrative Engine (AI Commentary 3.0)"):
        st.markdown(narrative["v37_narrative"])

    # --- REINFORCEMENT ENGINE ---
    with st.expander("🔁 Reinforcement Engine (Self-Learning)"):
        st.json(reinforcement)

    st.success("V37 System Dashboard loaded.")
# ------------- CHUNK 219: V37 ALERTS ENGINE (REAL-TIME WARNINGS) -------------

def _collect_alert_inputs():
    """
    Collect all upstream V37 signals:
    - v37_master_export
    - v37_system_monitor_export
    - v37_meta_brain_export
    - v37_final_decision_export
    - predictive_fusion_export
    - adaptive_risk_export
    - adaptive_opportunity_export
    - adaptive_parlay_export
    - multi_game_slip_export
    - meta_stability_export
    - volatility_cycle_export
    - instability_export
    - shock_export
    """

    return {
        "master": st.session_state.get("v37_master_export"),
        "monitor": st.session_state.get("v37_system_monitor_export"),
        "meta_brain": st.session_state.get("v37_meta_brain_export"),
        "final": st.session_state.get("v37_final_decision_export"),
        "fusion": st.session_state.get("predictive_fusion_export"),
        "risk": st.session_state.get("adaptive_risk_export"),
        "opportunity": st.session_state.get("adaptive_opportunity_export"),
        "parlay": st.session_state.get("adaptive_parlay_export"),
        "slip": st.session_state.get("multi_game_slip_export"),
        "meta_stability": st.session_state.get("meta_stability_export"),
        "volatility": st.session_state.get("volatility_cycle_export"),
        "instability": st.session_state.get("instability_export"),
        "shock": st.session_state.get("shock_export"),
    }


def _alert_if(condition, message, alerts):
    """
    Helper to append alerts.
    """
    if condition:
        alerts.append(message)


def _compute_alerts(data):
    """
    Generate alerts based on system conditions.
    """

    alerts = []

    # --- ENVIRONMENT ALERTS ---
    _alert_if(
        data["volatility"]["volatility_cycle_score"] > 0.70,
        "High Volatility Cycle — environment unstable.",
        alerts
    )

    _alert_if(
        data["instability"]["instability_forecast_score"] > 0.70,
        "High Instability Forecast — predictive signals unreliable.",
        alerts
    )

    _alert_if(
        data["shock"]["shock_forecast_score"] > 0.70,
        "High Shock/Turbulence Forecast — avoid aggressive plays.",
        alerts
    )

    _alert_if(
        data["meta_stability"]["meta_stability_score"] < 0.30,
        "Low Meta-Stability — long-horizon environment collapsing.",
        alerts
    )

    # --- SYSTEM PRESSURE ALERTS ---
    _alert_if(
        data["monitor"]["system_pressure"] > 0.70,
        "System Pressure Critical — risk, opportunity, and parlay engines overloaded.",
        alerts
    )

    # --- ENGINE ALIGNMENT ALERTS ---
    _alert_if(
        data["monitor"]["engine_alignment"] < 0.30,
        "Engine Misalignment — predictive engines disagree strongly.",
        alerts
    )

    # --- META-BRAIN ALERTS ---
    _alert_if(
        data["meta_brain"]["meta_confidence"] < 0.30,
        "Meta-Brain Fragmentation — system coherence breaking down.",
        alerts
    )

    # --- RISK ALERTS ---
    _alert_if(
        data["risk"]["adaptive_unit_size"] > 1.75,
        "High Unit Size — system taking aggressive risk.",
        alerts
    )

    # --- OPPORTUNITY ALERTS ---
    _alert_if(
        data["opportunity"]["adaptive_opportunity_confidence"] < 0.20,
        "Weak Opportunity Confidence — opportunities unreliable.",
        alerts
    )

    # --- PARLAY ALERTS ---
    _alert_if(
        data["parlay"]["adaptive_parlay_confidence"] > 0.80,
        "High Parlay Confidence — check correlation risk.",
        alerts
    )

    # --- SLIP ALERTS ---
    _alert_if(
        data["slip"]["multi_game_slip_confidence"] < 0.20,
        "Weak Slip Confidence — multi-game slip not aligned.",
        alerts
    )

    # --- MASTER ENGINE ALERTS ---
    _alert_if(
        data["master"]["v37_master_score"] < 0.30,
        "Master Score Low — global system state unfavorable.",
        alerts
    )

    return alerts


def render_v37_alerts_engine():
    """
    Full UI for the V37 Alerts Engine.
    """
    st.header("V37 Alerts Engine")
    st.caption("Real-time warnings and system alerts based on all V37 intelligence layers.")

    data = _collect_alert_inputs()
    alerts = _compute_alerts(data)

    if len(alerts) == 0:
        st.success("No alerts — system stable.")
        return

    themed_card_container()
    st.markdown("## ⚠️ Active Alerts")

    for alert in alerts:
        st.error(f"• {alert}")

    st.session_state["v37_alerts_export"] = {"alerts": alerts}

    themed_card_container()
    st.markdown("### Alerts Export Object")
    st.json(st.session_state["v37_alerts_export"])

    st.success("V37 Alerts Engine complete.")
# ------------- CHUNK 220: V37 OPERATOR CONSOLE (INTERACTIVE CONTROL PANEL) -------------

def render_v37_operator_console():
    """
    Interactive control panel for V37.
    Allows:
    - Manual outcome entry
    - System resets
    - Engine toggles
    - Forced recalculations
    - Manual overrides
    - Diagnostics on demand
    """

    st.title("V37 Operator Console")
    st.caption("Interactive control panel for managing and controlling the V37 system.")

    # --- ENGINE TOGGLES ---
    st.subheader("Engine Toggles")

    engine_states = {
        "Predictive Fusion": st.checkbox("Enable Predictive Fusion Engine", value=True),
        "Adaptive Risk": st.checkbox("Enable Adaptive Risk Engine", value=True),
        "Adaptive Opportunity": st.checkbox("Enable Adaptive Opportunity Engine", value=True),
        "Adaptive Parlay": st.checkbox("Enable Adaptive Parlay Engine", value=True),
        "Multi-Game Slip": st.checkbox("Enable Multi-Game Slip Engine", value=True),
        "Final Decision": st.checkbox("Enable Final Decision Engine", value=True),
        "Master Engine": st.checkbox("Enable Master Engine", value=True),
        "Narrative Engine": st.checkbox("Enable Narrative Engine", value=True),
        "Reinforcement Engine": st.checkbox("Enable Reinforcement Engine", value=True),
        "System Monitor": st.checkbox("Enable System Monitor", value=True),
        "Meta-Brain": st.checkbox("Enable Meta-Brain", value=True),
        "Alerts Engine": st.checkbox("Enable Alerts Engine", value=True),
    }

    st.session_state["v37_engine_toggles"] = engine_states

    # --- OUTCOME ENTRY ---
    st.subheader("Outcome Entry (For Reinforcement Learning)")

    outcome = st.selectbox(
        "Select Outcome",
        ["NONE", "WIN", "LOSS", "PUSH"],
        index=0
    )

    if outcome != "NONE":
        st.session_state["actual_outcome"] = outcome
        st.success(f"Outcome recorded: {outcome}")

    # --- MANUAL OVERRIDES ---
    st.subheader("Manual Overrides")

    override_decision = st.selectbox(
        "Override Final Decision",
        ["NONE", "PASS", "BET", "STRONG BET"],
        index=0
    )

    if override_decision != "NONE":
        st.session_state["v37_manual_override"] = override_decision
        st.warning(f"Manual override applied: {override_decision}")

    # --- SYSTEM ACTIONS ---
    st.subheader("System Actions")

    if st.button("Force Recalculate All Engines"):
        st.session_state["v37_force_recalc"] = True
        st.info("Recalculation triggered.")

    if st.button("Reset All V37 State"):
        keys = [k for k in st.session_state.keys() if k.startswith("v37_") or k.endswith("_export")]
        for k in keys:
            del st.session_state[k]
        st.error("All V37 state has been reset.")

    # --- SYSTEM SUMMARY ---
    st.subheader("System Summary")

    summary = {
        "Final Decision": st.session_state.get("v37_final_decision_export"),
        "Master Engine": st.session_state.get("v37_master_export"),
        "System Health": st.session_state.get("v37_system_monitor_export"),
        "Meta-Brain": st.session_state.get("v37_meta_brain_export"),
        "Alerts": st.session_state.get("v37_alerts_export"),
    }

    st.json(summary)

    st.success("V37 Operator Console loaded.")
# ------------- CHUNK 221: V37 AUTONOMOUS MODE ENGINE (AUTO-PILOT BRAIN) -------------

def _collect_autonomous_inputs():
    """
    Collect all upstream V37 signals:
    - v37_master_export
    - v37_system_monitor_export
    - v37_meta_brain_export
    - v37_alerts_export
    - v37_final_decision_export
    - v37_engine_toggles
    - v37_manual_override
    """

    return {
        "master": st.session_state.get("v37_master_export"),
        "monitor": st.session_state.get("v37_system_monitor_export"),
        "meta_brain": st.session_state.get("v37_meta_brain_export"),
        "alerts": st.session_state.get("v37_alerts_export", {"alerts": []}),
        "final": st.session_state.get("v37_final_decision_export"),
        "toggles": st.session_state.get("v37_engine_toggles", {}),
        "override": st.session_state.get("v37_manual_override", None),
    }


def _compute_autonomous_readiness(master, monitor, meta_brain):
    """
    Compute readiness for autonomous mode:
    - high master score
    - high system health
    - high meta-confidence
    """

    master_score = master.get("v37_master_score", 0.5)
    health = monitor.get("system_health_score", 0.5)
    meta_conf = meta_brain.get("meta_confidence", 0.5)

    readiness = float(
        (master_score * 0.40) +
        (health * 0.35) +
        (meta_conf * 0.25)
    )

    return max(0.0, min(readiness, 1.0))


def _compute_autonomous_risk(monitor, alerts):
    """
    Compute autonomous risk:
    - system pressure
    - environment stress
    - number of alerts
    """

    pressure = monitor.get("system_pressure", 0.5)
    stress = monitor.get("environment_stress", 0.5)
    alert_count = len(alerts)

    risk = float(
        (pressure * 0.40) +
        (stress * 0.40) +
        (min(alert_count, 10) * 0.02)
    )

    return max(0.0, min(risk, 1.0))


def _classify_autonomous_state(readiness, risk, override):
    """
    Determine autonomous mode state:
    - AUTO (system acts automatically)
    - CONFIRM (system requests operator confirmation)
    - MANUAL (system requires operator control)
    - SAFE MODE (system suppresses actions)
    """

    if override is not None:
        return "MANUAL OVERRIDE"

    if risk > 0.70:
        return "SAFE MODE"

    if readiness > 0.70 and risk < 0.40:
        return "AUTO"

    if readiness > 0.40:
        return "CONFIRM"

    return "MANUAL"


def _build_autonomous_export(state, readiness, risk, alerts):
    """
    Build the final autonomous mode export object.
    """

    return {
        "autonomous_state": state,
        "autonomous_readiness": readiness,
        "autonomous_risk": risk,
        "active_alerts": alerts,
    }


def render_v37_autonomous_mode():
    """
    Full UI for the V37 Autonomous Mode Engine.
    """
    st.header("V37 Autonomous Mode")
    st.caption("Determines whether the system should act automatically, request confirmation, or enter safe mode.")

    data = _collect_autonomous_inputs()

    readiness = _compute_autonomous_readiness(
        data["master"],
        data["monitor"],
        data["meta_brain"]
    )

    risk = _compute_autonomous_risk(
        data["monitor"],
        data["alerts"]["alerts"]
    )

    state = _classify_autonomous_state(
        readiness,
        risk,
        data["override"]
    )

    export = _build_autonomous_export(
        state,
        readiness,
        risk,
        data["alerts"]["alerts"]
    )

    # Save export
    st.session_state["v37_autonomous_export"] = export

    themed_card_container()
    st.markdown(f"## Autonomous Mode State: **{state}**")

    themed_card_container()
    st.markdown("### Autonomous Readiness")
    st.markdown(f"`{readiness:.4f}`")

    themed_card_container()
    st.markdown("### Autonomous Risk")
    st.markdown(f"`{risk:.4f}`")

    themed_card_container()
    st.markdown("### Active Alerts")
    st.json(data["alerts"]["alerts"])

    themed_card_container()
    st.markdown("### Autonomous Mode Export Object")
    st.json(export)

    st.success("V37 Autonomous Mode Engine complete.")
# ------------- CHUNK 222: V37 SAFE MODE ENGINE (EMERGENCY SUPPRESSION LAYER) -------------

def _collect_safe_mode_inputs():
    """
    Collect all upstream V37 signals:
    - v37_autonomous_export
    - v37_alerts_export
    - v37_system_monitor_export
    - v37_meta_brain_export
    - v37_master_export
    - v37_final_decision_export
    - v37_engine_toggles
    """

    return {
        "auto": st.session_state.get("v37_autonomous_export"),
        "alerts": st.session_state.get("v37_alerts_export", {"alerts": []}),
        "monitor": st.session_state.get("v37_system_monitor_export"),
        "meta_brain": st.session_state.get("v37_meta_brain_export"),
        "master": st.session_state.get("v37_master_export"),
        "final": st.session_state.get("v37_final_decision_export"),
        "toggles": st.session_state.get("v37_engine_toggles", {}),
    }


def _compute_safe_mode_trigger(auto, alerts, monitor, meta_brain, master):
    """
    Determine whether safe mode should activate.
    Safe mode triggers when ANY of the following are true:
    - Autonomous mode state = SAFE MODE
    - System pressure > 0.80
    - Environment stress > 0.80
    - Meta-confidence < 0.20
    - Master score < 0.20
    - More than 5 alerts active
    """

    # Autonomous mode already decided it's unsafe
    if auto.get("autonomous_state") == "SAFE MODE":
        return True

    # System Monitor danger thresholds
    if monitor.get("system_pressure", 0.0) > 0.80:
        return True

    if monitor.get("environment_stress", 0.0) > 0.80:
        return True

    # Meta-Brain collapse
    if meta_brain.get("meta_confidence", 1.0) < 0.20:
        return True

    # Master Engine collapse
    if master.get("v37_master_score", 1.0) < 0.20:
        return True

    # Alert overload
    if len(alerts.get("alerts", [])) > 5:
        return True

    return False


def _build_safe_mode_export(triggered, alerts, monitor, meta_brain, master):
    """
    Build the final safe mode export object.
    """

    return {
        "safe_mode_active": triggered,
        "active_alerts": alerts.get("alerts", []),
        "system_pressure": monitor.get("system_pressure"),
        "environment_stress": monitor.get("environment_stress"),
        "meta_confidence": meta_brain.get("meta_confidence"),
        "master_score": master.get("v37_master_score"),
    }


def render_v37_safe_mode_engine():
    """
    Full UI for the V37 Safe Mode Engine.
    """
    st.header("V37 Safe Mode Engine")
    st.caption("Emergency suppression layer that prevents system actions in dangerous conditions.")

    data = _collect_safe_mode_inputs()

    triggered = _compute_safe_mode_trigger(
        data["auto"],
        data["alerts"],
        data["monitor"],
        data["meta_brain"],
        data["master"]
    )

    export = _build_safe_mode_export(
        triggered,
        data["alerts"],
        data["monitor"],
        data["meta_brain"],
        data["master"]
    )

    # Save export
    st.session_state["v37_safe_mode_export"] = export

    if triggered:
        themed_card_container()
        st.error("🚨 SAFE MODE ACTIVATED — All autonomous actions suppressed.")
    else:
        themed_card_container()
        st.success("Safe Mode NOT active — system operating normally.")

    themed_card_container()
    st.markdown("### Safe Mode Export Object")
    st.json(export)

    st.success("V37 Safe Mode Engine complete.")
# ------------- CHUNK 223: V37 SYSTEM ORCHESTRATOR (UNIFIED EXECUTION PIPELINE) -------------

def _collect_orchestrator_inputs():
    """
    Collect all relevant V37 signals:
    - engine toggles
    - safe mode export
    - autonomous mode export
    - manual override
    - force recalc flag
    """

    return {
        "toggles": st.session_state.get("v37_engine_toggles", {}),
        "safe": st.session_state.get("v37_safe_mode_export", {"safe_mode_active": False}),
        "auto": st.session_state.get("v37_autonomous_export", {}),
        "override": st.session_state.get("v37_manual_override", None),
        "force_recalc": st.session_state.get("v37_force_recalc", False),
    }


def _determine_execution_mode(safe, auto, override):
    """
    Determine execution mode:
    - SAFE MODE
    - MANUAL OVERRIDE
    - AUTO
    - CONFIRM
    - MANUAL
    """

    if safe.get("safe_mode_active"):
        return "SAFE MODE"

    if override is not None:
        return "MANUAL OVERRIDE"

    return auto.get("autonomous_state", "MANUAL")


def _should_execute_engine(engine_name, toggles, mode):
    """
    Determine if an engine should run based on:
    - engine toggles
    - execution mode
    """

    if not toggles.get(engine_name, True):
        return False

    if mode == "SAFE MODE":
        return engine_name in ["System Monitor", "Meta-Brain", "Alerts Engine"]

    return True


def _build_orchestrator_export(mode, executed, skipped):
    """
    Build the final orchestrator export object.
    """

    return {
        "execution_mode": mode,
        "engines_executed": executed,
        "engines_skipped": skipped,
    }


def render_v37_system_orchestrator():
    """
    Unified execution pipeline for V37.
    Controls:
    - Engine execution order
    - Safe mode suppression
    - Autonomous mode behavior
    - Manual overrides
    - Forced recalculations
    """

    st.header("V37 System Orchestrator")
    st.caption("Unified execution pipeline for all V37 engines.")

    data = _collect_orchestrator_inputs()

    mode = _determine_execution_mode(
        data["safe"],
        data["auto"],
        data["override"]
    )

    toggles = data["toggles"]

    executed = []
    skipped = []

    # --- ENGINE EXECUTION ORDER ---
    engine_order = [
        ("Predictive Fusion", "predictive_fusion_export"),
        ("Adaptive Risk", "adaptive_risk_export"),
        ("Adaptive Opportunity", "adaptive_opportunity_export"),
        ("Adaptive Parlay", "adaptive_parlay_export"),
        ("Multi-Game Slip", "multi_game_slip_export"),
        ("Final Decision", "v37_final_decision_export"),
        ("Master Engine", "v37_master_export"),
        ("System Monitor", "v37_system_monitor_export"),
        ("Meta-Brain", "v37_meta_brain_export"),
        ("Narrative Engine", "v37_narrative_export"),
        ("Reinforcement Engine", "v37_reinforcement_export"),
        ("Alerts Engine", "v37_alerts_export"),
        ("Autonomous Mode", "v37_autonomous_export"),
        ("Safe Mode", "v37_safe_mode_export"),
    ]

    for engine_name, export_key in engine_order:
        if _should_execute_engine(engine_name, toggles, mode):
            executed.append(engine_name)
        else:
            skipped.append(engine_name)

    export = _build_orchestrator_export(mode, executed, skipped)

    # Save export
    st.session_state["v37_orchestrator_export"] = export

    themed_card_container()
    st.markdown(f"## Execution Mode: **{mode}**")

    themed_card_container()
    st.markdown("### Engines Executed")
    st.json(executed)

    themed_card_container()
    st.markdown("### Engines Skipped")
    st.json(skipped)

    themed_card_container()
    st.markdown("### Orchestrator Export Object")
    st.json(export)

    st.success("V37 System Orchestrator complete.")
# ------------- CHUNK 224: V37 SYSTEM SUMMARY ENGINE (GLOBAL SNAPSHOT GENERATOR) -------------

def _collect_summary_inputs():
    """
    Collect all major V37 exports:
    - v37_master_export
    - v37_final_decision_export
    - v37_system_monitor_export
    - v37_meta_brain_export
    - v37_alerts_export
    - v37_autonomous_export
    - v37_safe_mode_export
    - v37_reinforcement_export
    """

    return {
        "master": st.session_state.get("v37_master_export"),
        "final": st.session_state.get("v37_final_decision_export"),
        "monitor": st.session_state.get("v37_system_monitor_export"),
        "meta_brain": st.session_state.get("v37_meta_brain_export"),
        "alerts": st.session_state.get("v37_alerts_export", {"alerts": []}),
        "auto": st.session_state.get("v37_autonomous_export"),
        "safe": st.session_state.get("v37_safe_mode_export"),
        "reinforcement": st.session_state.get("v37_reinforcement_export"),
    }


def _build_summary_text(data):
    """
    Build a clean, human-readable summary of the entire system.
    """

    master = data["master"]
    final = data["final"]
    monitor = data["monitor"]
    meta = data["meta_brain"]
    alerts = data["alerts"]["alerts"]
    auto = data["auto"]
    safe = data["safe"]
    reinforce = data["reinforcement"]

    summary = f"""
# 🧩 V37 System Summary

## 🏆 Master Engine
- **Master State:** {master.get("v37_master_state")}
- **Master Score:** `{master.get("v37_master_score"):.4f}`

## 🧠 Final Decision
- **Decision:** {final.get("v37_final_decision")}
- **Score:** `{final.get("v37_final_score"):.4f}`

## 🩺 System Health
- **Health State:** {monitor.get("system_health_state")}
- **Health Score:** `{monitor.get("system_health_score"):.4f}`
- **Engine Alignment:** `{monitor.get("engine_alignment"):.4f}`
- **Environment Stress:** `{monitor.get("environment_stress"):.4f}`
- **System Pressure:** `{monitor.get("system_pressure"):.4f}`

## 🧬 Meta-Brain
- **Meta State:** {meta.get("meta_state")}
- **Meta Confidence:** `{meta.get("meta_confidence"):.4f}`
- **Meta Alignment:** `{meta.get("meta_alignment"):.4f}`
- **Meta Pressure:** `{meta.get("meta_pressure"):.4f}`

## ⚠️ Alerts
- **Active Alerts:** {len(alerts)}
"""

    if len(alerts) > 0:
        for a in alerts:
            summary += f"  - {a}\n"

    summary += f"""
## 🤖 Autonomous Mode
- **Autonomous State:** {auto.get("autonomous_state")}
- **Readiness:** `{auto.get("autonomous_readiness"):.4f}`
- **Risk:** `{auto.get("autonomous_risk"):.4f}`

## 🚨 Safe Mode
- **Safe Mode Active:** {safe.get("safe_mode_active")}

## 🔁 Reinforcement
- **Reinforcement Signal:** `{reinforce.get("reinforcement_signal"):.4f}`
- **Outcome Score:** `{reinforce.get("outcome_score"):.4f}`

---
This summary provides a complete snapshot of the V37 system at a glance.
"""

    return summary


def _build_summary_export(text):
    """
    Build the final summary export object.
    """

    return {
        "v37_system_summary": text
    }


def render_v37_system_summary_engine():
    """
    Full UI for the V37 System Summary Engine.
    """
    st.header("V37 System Summary Engine")
    st.caption("Generates a unified snapshot of all V37 intelligence layers.")

    data = _collect_summary_inputs()

    summary_text = _build_summary_text(data)
    export = _build_summary_export(summary_text)

    # Save export
    st.session_state["v37_system_summary_export"] = export

    themed_card_container()
    st.markdown("## V37 System Summary")
    st.markdown(summary_text)

    themed_card_container()
    st.markdown("### Summary Export Object")
    st.json(export)

    st.success("V37 System Summary Engine complete.")
# ------------- CHUNK 225: V37 MOBILE DASHBOARD (MOBILE UI LAYER) -------------

def _mobile_card(title, content):
    """
    Helper to render a mobile-friendly card.
    """
    st.markdown(
        f"""
        <div style="
            padding: 14px;
            border-radius: 12px;
            background-color: rgba(255,255,255,0.08);
            margin-bottom: 14px;
            border: 1px solid rgba(255,255,255,0.15);
        ">
            <h4 style="margin-top: 0; margin-bottom: 6px;">{title}</h4>
            <div style="font-size: 0.95rem; line-height: 1.35;">
                {content}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_v37_mobile_dashboard():
    """
    Mobile-optimized dashboard for V37.
    Displays condensed summaries of:
    - Master Engine
    - Final Decision
    - System Health
    - Meta-Brain
    - Autonomous Mode
    - Safe Mode
    - Alerts
    """

    st.title("📱 V37 Mobile Dashboard")
    st.caption("Mobile-optimized control panel for all V37 intelligence layers.")

    # --- Load all exports ---
    master = st.session_state.get("v37_master_export")
    final = st.session_state.get("v37_final_decision_export")
    monitor = st.session_state.get("v37_system_monitor_export")
    meta = st.session_state.get("v37_meta_brain_export")
    auto = st.session_state.get("v37_autonomous_export")
    safe = st.session_state.get("v37_safe_mode_export")
    alerts = st.session_state.get("v37_alerts_export", {"alerts": []})

    # --- MASTER ENGINE ---
    _mobile_card(
        "🏆 Master Engine",
        f"""
        <b>State:</b> {master.get("v37_master_state")}<br>
        <b>Score:</b> {master.get("v37_master_score"):.4f}
        """
    )

    # --- FINAL DECISION ---
    _mobile_card(
        "🧠 Final Decision",
        f"""
        <b>Decision:</b> {final.get("v37_final_decision")}<br>
        <b>Score:</b> {final.get("v37_final_score"):.4f}
        """
    )

    # --- SYSTEM HEALTH ---
    _mobile_card(
        "🩺 System Health",
        f"""
        <b>Health:</b> {monitor.get("system_health_state")}<br>
        <b>Score:</b> {monitor.get("system_health_score"):.4f}<br>
        <b>Alignment:</b> {monitor.get("engine_alignment"):.4f}<br>
        <b>Stress:</b> {monitor.get("environment_stress"):.4f}<br>
        <b>Pressure:</b> {monitor.get("system_pressure"):.4f}
        """
    )

    # --- META-BRAIN ---
    _mobile_card(
        "🧬 Meta-Brain",
        f"""
        <b>State:</b> {meta.get("meta_state")}<br>
        <b>Confidence:</b> {meta.get("meta_confidence"):.4f}<br>
        <b>Alignment:</b> {meta.get("meta_alignment"):.4f}<br>
        <b>Pressure:</b> {meta.get("meta_pressure"):.4f}
        """
    )

    # --- AUTONOMOUS MODE ---
    _mobile_card(
        "🤖 Autonomous Mode",
        f"""
        <b>State:</b> {auto.get("autonomous_state")}<br>
        <b>Readiness:</b> {auto.get("autonomous_readiness"):.4f}<br>
        <b>Risk:</b> {auto.get("autonomous_risk"):.4f}
        """
    )

    # --- SAFE MODE ---
    _mobile_card(
        "🚨 Safe Mode",
        f"""
        <b>Active:</b> {safe.get("safe_mode_active")}
        """
    )

    # --- ALERTS ---
    alert_count = len(alerts.get("alerts", []))
    alert_list = alerts.get("alerts", [])

    alert_html = "<br>".join([f"• {a}" for a in alert_list]) if alert_count > 0 else "No active alerts."

    _mobile_card(
        "⚠️ Alerts",
        f"""
        <b>Active Alerts:</b> {alert_count}<br>
        {alert_html}
        """
    )

    # Save export
    st.session_state["v37_mobile_dashboard_export"] = {
        "mobile_dashboard_loaded": True,
        "alert_count": alert_count
    }

    st.success("V37 Mobile Dashboard loaded.")
# ------------- CHUNK 226: V37 MINIMAL MODE (ULTRA-COMPACT UI) -------------

def _minimal_chip(label, value, color):
    """
    Render a compact colored chip for minimal mode.
    """
    st.markdown(
        f"""
        <div style="
            display: inline-block;
            padding: 6px 12px;
            margin: 4px 6px 4px 0;
            border-radius: 20px;
            background-color: {color};
            color: white;
            font-size: 0.85rem;
            font-weight: 600;
        ">
            {label}: {value}
        </div>
        """,
        unsafe_allow_html=True
    )


def render_v37_minimal_mode():
    """
    Ultra-compact minimal UI for fast scanning.
    Displays only the most essential metrics:
    - Final Decision
    - Master State
    - System Health
    - Meta-Confidence
    - Autonomous Mode
    - Safe Mode
    - Alerts Count
    """

    st.title("⚡ V37 Minimal Mode")
    st.caption("Ultra-compact, high-signal interface for rapid scanning.")

    # Load exports
    master = st.session_state.get("v37_master_export")
    final = st.session_state.get("v37_final_decision_export")
    monitor = st.session_state.get("v37_system_monitor_export")
    meta = st.session_state.get("v37_meta_brain_export")
    auto = st.session_state.get("v37_autonomous_export")
    safe = st.session_state.get("v37_safe_mode_export")
    alerts = st.session_state.get("v37_alerts_export", {"alerts": []})

    # Determine colors
    def color_for_state(state):
        if "Strong" in state or "Favorable" in state or "High" in state or "Optimal" in state:
            return "#2ecc71"  # green
        if "Neutral" in state or "Moderate" in state or "Stable" in state:
            return "#f1c40f"  # yellow
        return "#e74c3c"      # red

    # --- FINAL DECISION ---
    _minimal_chip(
        "Decision",
        final.get("v37_final_decision"),
        color_for_state(final.get("v37_final_decision"))
    )

    # --- MASTER STATE ---
    _minimal_chip(
        "Master",
        master.get("v37_master_state"),
        color_for_state(master.get("v37_master_state"))
    )

    # --- SYSTEM HEALTH ---
    _minimal_chip(
        "Health",
        monitor.get("system_health_state"),
        color_for_state(monitor.get("system_health_state"))
    )

    # --- META-CONFIDENCE ---
    meta_conf = meta.get("meta_confidence")
    meta_color = "#2ecc71" if meta_conf > 0.70 else "#f1c40f" if meta_conf > 0.40 else "#e74c3c"

    _minimal_chip(
        "Meta",
        f"{meta_conf:.2f}",
        meta_color
    )

    # --- AUTONOMOUS MODE ---
    auto_state = auto.get("autonomous_state")
    auto_color = "#2ecc71" if auto_state == "AUTO" else "#f1c40f" if auto_state == "CONFIRM" else "#e74c3c"

    _minimal_chip(
        "Auto",
        auto_state,
        auto_color
    )

    # --- SAFE MODE ---
    safe_color = "#e74c3c" if safe.get("safe_mode_active") else "#2ecc71"

    _minimal_chip(
        "Safe",
        "ON" if safe.get("safe_mode_active") else "OFF",
        safe_color
    )

    # --- ALERT COUNT ---
    alert_count = len(alerts.get("alerts", []))
    alert_color = "#e74c3c" if alert_count > 3 else "#f1c40f" if alert_count > 0 else "#2ecc71"

    _minimal_chip(
        "Alerts",
        str(alert_count),
        alert_color
    )

    # Save export
    st.session_state["v37_minimal_mode_export"] = {
        "minimal_mode_loaded": True,
        "alert_count": alert_count
    }

    st.success("V37 Minimal Mode loaded.")
# ------------- CHUNK 227: V37 THEME ENGINE (GLOBAL VISUAL STYLING) -------------

def _get_theme_css(theme):
    """
    Return CSS for the selected theme.
    Supported themes:
    - dark
    - light
    - neon
    - pro
    """

    if theme == "light":
        return """
        <style>
            body, .stApp {
                background-color: #f5f5f5 !important;
                color: #222 !important;
            }
            .themed-card {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 12px;
                padding: 16px;
                margin-bottom: 16px;
            }
        </style>
        """

    if theme == "neon":
        return """
        <style>
            body, .stApp {
                background-color: #000000 !important;
                color: #39ff14 !important;
            }
            .themed-card {
                background-color: rgba(0,255,0,0.08);
                border: 1px solid #39ff14;
                border-radius: 12px;
                padding: 16px;
                margin-bottom: 16px;
            }
        </style>
        """

    if theme == "pro":
        return """
        <style>
            body, .stApp {
                background-color: #1c1f26 !important;
                color: #e0e3e7 !important;
                font-family: 'Inter', sans-serif;
            }
            .themed-card {
                background-color: #262a33;
                border: 1px solid #3a3f4b;
                border-radius: 14px;
                padding: 18px;
                margin-bottom: 18px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.25);
            }
        </style>
        """

    # Default = dark
    return """
    <style>
        body, .stApp {
            background-color: #0e1117 !important;
            color: #fafafa !important;
        }
        .themed-card {
            background-color: #161b22;
            border: 1px solid #30363d;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 16px;
        }
    </style>
    """


def apply_v37_theme():
    """
    Apply the selected V37 theme.
    """

    theme = st.session_state.get("v37_theme", "dark")
    css = _get_theme_css(theme)
    st.markdown(css, unsafe_allow_html=True)

    st.session_state["v37_theme_export"] = {
        "theme": theme,
        "css_applied": True
    }


def render_v37_theme_selector():
    """
    UI for selecting the global V37 theme.
    """

    st.header("🎨 V37 Theme Engine")
    st.caption("Select a global theme for all V37 dashboards and UI modules.")

    theme = st.selectbox(
        "Choose Theme",
        ["dark", "light", "neon", "pro"],
        index=["dark", "light", "neon", "pro"].index(
            st.session_state.get("v37_theme", "dark")
        )
    )

    st.session_state["v37_theme"] = theme
    apply_v37_theme()

    themed_card_container()
    st.markdown(f"### Current Theme: **{theme.upper()}**")

    themed_card_container()
    st.markdown("### Theme Export Object")
    st.json(st.session_state["v37_theme_export"])

    st.success("V37 Theme Engine applied.")
# ------------- CHUNK 228: V37 LAYOUT ENGINE (GLOBAL NAVIGATION + STRUCTURE) -------------

def _render_nav_button(label, page_key, current_page):
    """
    Helper to render a navigation button.
    """
    active = (page_key == current_page)
    style = (
        "background-color: #2ecc71; color: black; font-weight: 700;"
        if active else
        "background-color: rgba(255,255,255,0.08); color: white;"
    )

    st.markdown(
        f"""
        <div style="
            padding: 10px 14px;
            border-radius: 8px;
            margin-bottom: 8px;
            cursor: pointer;
            {style}
        " onclick="window.location.href='?page={page_key}'">
            {label}
        </div>
        """,
        unsafe_allow_html=True
    )


def render_v37_layout_engine():
    """
    Global layout engine for V37.
    Provides:
    - Sidebar navigation
    - Page routing
    - Theme application
    """

    # Apply theme
    apply_v37_theme()

    # Determine current page
    query_params = st.experimental_get_query_params()
    current_page = query_params.get("page", ["dashboard"])[0]

    st.sidebar.title("V37 Navigation")

    # Navigation buttons
    _render_nav_button("Dashboard", "dashboard", current_page)
    _render_nav_button("Mobile Dashboard", "mobile", current_page)
    _render_nav_button("Minimal Mode", "minimal", current_page)
    _render_nav_button("Operator Console", "console", current_page)
    _render_nav_button("Alerts", "alerts", current_page)
    _render_nav_button("Autonomous Mode", "auto", current_page)
    _render_nav_button("Safe Mode", "safe", current_page)
    _render_nav_button("System Summary", "summary", current_page)
    _render_nav_button("Theme Engine", "theme", current_page)

    # Page routing
    if current_page == "dashboard":
        render_v37_system_dashboard()
    elif current_page == "mobile":
        render_v37_mobile_dashboard()
    elif current_page == "minimal":
        render_v37_minimal_mode()
    elif current_page == "console":
        render_v37_operator_console()
    elif current_page == "alerts":
        render_v37_alerts_engine()
    elif current_page == "auto":
        render_v37_autonomous_mode()
    elif current_page == "safe":
        render_v37_safe_mode_engine()
    elif current_page == "summary":
        render_v37_system_summary_engine()
    elif current_page == "theme":
        render_v37_theme_selector()
    else:
        st.error("Unknown page.")

    # Export
    st.session_state["v37_layout_export"] = {
        "current_page": current_page,
        "navigation_loaded": True
    }

    st.success("V37 Layout Engine loaded.")
# ------------- CHUNK 229: V37 PAGE REGISTRY (DYNAMIC PAGE LOADER + PLUGIN SYSTEM) -------------

def _default_v37_pages():
    """
    Built-in V37 pages.
    These are the core system pages.
    """

    return {
        "dashboard": {
            "label": "Dashboard",
            "renderer": render_v37_system_dashboard
        },
        "mobile": {
            "label": "Mobile Dashboard",
            "renderer": render_v37_mobile_dashboard
        },
        "minimal": {
            "label": "Minimal Mode",
            "renderer": render_v37_minimal_mode
        },
        "console": {
            "label": "Operator Console",
            "renderer": render_v37_operator_console
        },
        "alerts": {
            "label": "Alerts",
            "renderer": render_v37_alerts_engine
        },
        "auto": {
            "label": "Autonomous Mode",
            "renderer": render_v37_autonomous_mode
        },
        "safe": {
            "label": "Safe Mode",
            "renderer": render_v37_safe_mode_engine
        },
        "summary": {
            "label": "System Summary",
            "renderer": render_v37_system_summary_engine
        },
        "theme": {
            "label": "Theme Engine",
            "renderer": render_v37_theme_selector
        },
    }


def register_v37_page(key, label, renderer):
    """
    Register a new page dynamically.
    Allows plugins and custom modules to add pages.
    """

    if "v37_page_registry" not in st.session_state:
        st.session_state["v37_page_registry"] = _default_v37_pages()

    st.session_state["v37_page_registry"][key] = {
        "label": label,
        "renderer": renderer
    }


def get_v37_page_registry():
    """
    Return the full page registry.
    """

    if "v37_page_registry" not in st.session_state:
        st.session_state["v37_page_registry"] = _default_v37_pages()

    return st.session_state["v37_page_registry"]


def render_v37_page_registry():
    """
    UI for viewing the page registry.
    """

    st.header("📚 V37 Page Registry")
    st.caption("Dynamic page loader and plugin system for V37.")

    registry = get_v37_page_registry()

    themed_card_container()
    st.markdown("### Registered Pages")
    st.json({k: v["label"] for k, v in registry.items()})

    st.session_state["v37_page_registry_export"] = {
        "registered_pages": list(registry.keys()),
        "count": len(registry)
    }

    themed_card_container()
    st.markdown("### Page Registry Export Object")
    st.json(st.session_state["v37_page_registry_export"])

    st.success("V37 Page Registry loaded.")
# ------------- CHUNK 230: V37 PLUGIN LOADER (DYNAMIC MODULE IMPORTER) -------------

import importlib
import types
import traceback

def load_v37_plugin(module_name, page_key=None, page_label=None, renderer_name=None):
    """
    Dynamically import a plugin module and register its page.
    Supports:
    - External modules
    - Custom pages
    - Experimental engines
    """

    if "v37_plugin_log" not in st.session_state:
        st.session_state["v37_plugin_log"] = []

    try:
        module = importlib.import_module(module_name)

        # If the module defines a page renderer, auto-register it
        if page_key and page_label and renderer_name:
            if hasattr(module, renderer_name):
                renderer = getattr(module, renderer_name)
                register_v37_page(page_key, page_label, renderer)
                st.session_state["v37_plugin_log"].append(
                    f"Plugin loaded: {module_name} → page '{page_key}' registered."
                )
            else:
                st.session_state["v37_plugin_log"].append(
                    f"Plugin loaded but renderer '{renderer_name}' not found in {module_name}."
                )
        else:
            st.session_state["v37_plugin_log"].append(
                f"Plugin loaded: {module_name} (no page registered)."
            )

        return True

    except Exception as e:
        st.session_state["v37_plugin_log"].append(
            f"Plugin load failed: {module_name} — {str(e)}\n{traceback.format_exc()}"
        )
        return False


def render_v37_plugin_loader():
    """
    UI for loading plugins dynamically.
    """

    st.header("🔌 V37 Plugin Loader")
    st.caption("Dynamically import external modules and register new pages.")

    st.subheader("Load Plugin Module")

    module_name = st.text_input("Module Name (e.g., my_plugin_module)")
    page_key = st.text_input("Page Key (optional)")
    page_label = st.text_input("Page Label (optional)")
    renderer_name = st.text_input("Renderer Function Name (optional)")

    if st.button("Load Plugin"):
        success = load_v37_plugin(
            module_name,
            page_key if page_key else None,
            page_label if page_label else None,
            renderer_name if renderer_name else None
        )

        if success:
            st.success(f"Plugin '{module_name}' loaded.")
        else:
            st.error(f"Failed to load plugin '{module_name}'.")

    st.subheader("Plugin Log")
    st.json(st.session_state.get("v37_plugin_log", []))

    # Export
    st.session_state["v37_plugin_loader_export"] = {
        "plugin_count": len(st.session_state.get("v37_plugin_log", [])),
        "log": st.session_state.get("v37_plugin_log", [])
    }

    themed_card_container()
    st.markdown("### Plugin Loader Export Object")
    st.json(st.session_state["v37_plugin_loader_export"])

    st.success("V37 Plugin Loader ready.")
# ------------- CHUNK 231: V37 DEVELOPER CONSOLE (DEBUG + INSPECTION TOOLS) -------------

def _filter_v37_keys():
    """
    Return all session_state keys relevant to V37.
    """

    keys = []
    for k in st.session_state.keys():
        if (
            k.startswith("v37_")
            or k.endswith("_export")
            or k in [
                "predictive_fusion_export",
                "adaptive_risk_export",
                "adaptive_opportunity_export",
                "adaptive_parlay_export",
                "multi_game_slip_export",
                "meta_stability_export",
                "volatility_cycle_export",
                "instability_export",
                "shock_export",
            ]
        ):
            keys.append(k)
    return sorted(keys)


def render_v37_developer_console():
    """
    Full developer console for inspecting V37 internals.
    Provides:
    - Session state explorer
    - Export inspector
    - Raw JSON viewer
    - Plugin logs
    - Orchestrator state
    - Debug sandbox
    """

    st.title("🛠️ V37 Developer Console")
    st.caption("Deep inspection tools for debugging and internal engine visibility.")

    # --- SESSION STATE KEYS ---
    st.subheader("🔑 V37 Session State Keys")

    v37_keys = _filter_v37_keys()
    st.json(v37_keys)

    # --- EXPORT INSPECTOR ---
    st.subheader("📦 Export Inspector")

    selected_key = st.selectbox("Select Export Key", v37_keys)

    if selected_key:
        themed_card_container()
        st.markdown(f"### Export: `{selected_key}`")
        st.json(st.session_state.get(selected_key))

    # --- PLUGIN LOGS ---
    st.subheader("🔌 Plugin Log")

    plugin_log = st.session_state.get("v37_plugin_log", [])
    st.json(plugin_log)

    # --- ORCHESTRATOR STATE ---
    st.subheader("🧩 Orchestrator State")

    orchestrator = st.session_state.get("v37_orchestrator_export")
    st.json(orchestrator)

    # --- DEBUG SANDBOX ---
    st.subheader("🧪 Debug Sandbox")

    debug_code = st.text_area(
        "Run Python (sandboxed, no imports):",
        height=150,
        placeholder="Example: {'health': st.session_state['v37_system_monitor_export']}"
    )

    if st.button("Execute Debug Code"):
        try:
            # Safe eval: no globals, no builtins, only session_state
            result = eval(
                debug_code,
                {"__builtins__": {}},
                {"st": st, "session": st.session_state}
            )
            st.success("Execution Result:")
            st.json(result)
        except Exception as e:
            st.error(f"Error: {str(e)}")

    # --- EXPORT OBJECT ---
    st.session_state["v37_developer_console_export"] = {
        "keys": v37_keys,
        "plugin_log_count": len(plugin_log),
        "orchestrator_mode": orchestrator.get("execution_mode") if orchestrator else None,
        "console_loaded": True
    }

    themed_card_container()
    st.markdown("### Developer Console Export Object")
    st.json(st.session_state["v37_developer_console_export"])

    st.success("V37 Developer Console loaded.")
# ------------- CHUNK 232: V37 ENGINE PROFILER (PERFORMANCE + TIMING ANALYZER) -------------

import time

def _profile_engine(name, func, results):
    """
    Profile a single engine by measuring execution time.
    """
    start = time.time()
    try:
        func()
        duration = time.time() - start
        results[name] = duration
    except Exception as e:
        results[name] = f"ERROR: {str(e)}"


def render_v37_engine_profiler():
    """
    Full performance profiler for V37.
    Measures:
    - Execution time of each engine
    - Slowest engines
    - Bottlenecks
    """

    st.title("⏱️ V37 Engine Profiler")
    st.caption("Performance and timing analyzer for all V37 engines.")

    st.info("Press the button below to run a full profiling pass.")

    if st.button("Run Engine Profiling"):
        results = {}

        # Profile each engine by calling its renderer
        engines = {
            "Master Engine": render_v37_system_dashboard,
            "Mobile Dashboard": render_v37_mobile_dashboard,
            "Minimal Mode": render_v37_minimal_mode,
            "Operator Console": render_v37_operator_console,
            "Alerts Engine": render_v37_alerts_engine,
            "Autonomous Mode": render_v37_autonomous_mode,
            "Safe Mode": render_v37_safe_mode_engine,
            "System Summary": render_v37_system_summary_engine,
            "Theme Engine": render_v37_theme_selector,
            "Plugin Loader": render_v37_plugin_loader,
            "Developer Console": render_v37_developer_console,
        }

        for name, func in engines.items():
            _profile_engine(name, func, results)

        # Sort by duration
        sorted_results = dict(
            sorted(
                results.items(),
                key=lambda x: float(x[1]) if isinstance(x[1], float) else 9999,
                reverse=True
            )
        )

        st.subheader("📊 Engine Timing Results")
        st.json(sorted_results)

        # Save export
        st.session_state["v37_engine_profiler_export"] = {
            "results": sorted_results,
            "slowest_engine": next(iter(sorted_results)),
            "profiler_loaded": True
        }

        themed_card_container()
        st.markdown("### Engine Profiler Export Object")
        st.json(st.session_state["v37_engine_profiler_export"])

        st.success("Engine profiling complete.")
# ------------- CHUNK 233: V37 ENGINE SCHEDULER (SMART EXECUTION OPTIMIZER) -------------

def _collect_scheduler_inputs():
    """
    Collect all relevant signals:
    - profiler results
    - orchestrator mode
    - safe mode
    - autonomous mode
    - engine toggles
    """

    return {
        "profiler": st.session_state.get("v37_engine_profiler_export", {}),
        "orchestrator": st.session_state.get("v37_orchestrator_export", {}),
        "safe": st.session_state.get("v37_safe_mode_export", {}),
        "auto": st.session_state.get("v37_autonomous_export", {}),
        "toggles": st.session_state.get("v37_engine_toggles", {}),
    }


def _compute_engine_costs(profiler):
    """
    Convert profiler results into cost weights.
    Higher duration = higher cost.
    """

    results = profiler.get("results", {})
    costs = {}

    for engine, duration in results.items():
        if isinstance(duration, float):
            # Normalize cost to 0–1 range
            costs[engine] = min(duration / 2.0, 1.0)
        else:
            costs[engine] = 1.0  # treat errors as high cost

    return costs


def _compute_engine_priority(mode, safe_active):
    """
    Determine priority levels based on system mode.
    """

    if safe_active:
        return {
            "System Monitor": 1.0,
            "Meta-Brain": 1.0,
            "Alerts Engine": 1.0,
        }

    if mode == "AUTO":
        return {
            "Final Decision": 1.0,
            "Master Engine": 1.0,
            "Predictive Fusion": 0.9,
            "Adaptive Risk": 0.9,
            "Adaptive Opportunity": 0.9,
            "Adaptive Parlay": 0.8,
            "Multi-Game Slip": 0.8,
        }

    if mode == "CONFIRM":
        return {
            "Final Decision": 1.0,
            "Master Engine": 1.0,
            "Predictive Fusion": 0.8,
        }

    # MANUAL or OVERRIDE
    return {
        "Final Decision": 1.0,
        "Master Engine": 1.0,
    }


def _decide_engine_execution(costs, priority, toggles):
    """
    Decide which engines should run based on:
    - cost (lower = better)
    - priority (higher = better)
    - toggles (must be enabled)
    """

    decisions = {}

    for engine in toggles.keys():
        if not toggles[engine]:
            decisions[engine] = False
            continue

        cost = costs.get(engine, 0.5)
        prio = priority.get(engine, 0.3)

        # Weighted decision
        score = prio - cost

        decisions[engine] = score > -0.2  # threshold

    return decisions


def render_v37_engine_scheduler():
    """
    Smart execution optimizer for V37.
    Uses profiler + orchestrator + safe mode to decide which engines should run.
    """

    st.title("🧠 V37 Engine Scheduler")
    st.caption("Smart execution optimizer that reduces latency and prioritizes critical engines.")

    data = _collect_scheduler_inputs()

    costs = _compute_engine_costs(data["profiler"])
    priority = _compute_engine_priority(
        data["orchestrator"].get("execution_mode"),
        data["safe"].get("safe_mode_active")
    )

    decisions = _decide_engine_execution(
        costs,
        priority,
        data["toggles"]
    )

    st.subheader("⚙️ Engine Execution Decisions")
    st.json(decisions)

    st.subheader("💰 Engine Cost Weights")
    st.json(costs)

    st.subheader("🎯 Engine Priority Weights")
    st.json(priority)

    # Export
    st.session_state["v37_engine_scheduler_export"] = {
        "decisions": decisions,
        "costs": costs,
        "priority": priority,
        "scheduler_loaded": True
    }

    themed_card_container()
    st.markdown("### Scheduler Export Object")
    st.json(st.session_state["v37_engine_scheduler_export"])

    st.success("V37 Engine Scheduler complete.")
# ------------- CHUNK 234: V37 MEMORY ENGINE (LONG-HORIZON SYSTEM MEMORY) -------------

import datetime

def _collect_memory_snapshot():
    """
    Collect a full snapshot of the V37 system state.
    """

    return {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "master": st.session_state.get("v37_master_export"),
        "final": st.session_state.get("v37_final_decision_export"),
        "monitor": st.session_state.get("v37_system_monitor_export"),
        "meta": st.session_state.get("v37_meta_brain_export"),
        "alerts": st.session_state.get("v37_alerts_export"),
        "auto": st.session_state.get("v37_autonomous_export"),
        "safe": st.session_state.get("v37_safe_mode_export"),
        "reinforcement": st.session_state.get("v37_reinforcement_export"),
    }


def _append_to_memory(snapshot):
    """
    Append snapshot to memory buffer.
    Maintain a rolling window of the last 500 entries.
    """

    if "v37_memory_buffer" not in st.session_state:
        st.session_state["v37_memory_buffer"] = []

    buffer = st.session_state["v37_memory_buffer"]
    buffer.append(snapshot)

    # Keep last 500 entries
    if len(buffer) > 500:
        buffer.pop(0)

    st.session_state["v37_memory_buffer"] = buffer


def _compute_memory_stats(buffer):
    """
    Compute long-horizon statistics:
    - average master score
    - average system health
    - average meta-confidence
    - alert frequency
    - safe mode frequency
    - autonomous mode distribution
    """

    if len(buffer) == 0:
        return {}

    master_scores = []
    health_scores = []
    meta_conf = []
    alert_counts = []
    safe_mode_count = 0
    auto_states = {}

    for snap in buffer:
        master_scores.append(snap["master"].get("v37_master_score", 0))
        health_scores.append(snap["monitor"].get("system_health_score", 0))
        meta_conf.append(snap["meta"].get("meta_confidence", 0))

        alert_counts.append(len(snap["alerts"].get("alerts", [])))

        if snap["safe"].get("safe_mode_active"):
            safe_mode_count += 1

        state = snap["auto"].get("autonomous_state", "UNKNOWN")
        auto_states[state] = auto_states.get(state, 0) + 1

    return {
        "avg_master_score": sum(master_scores) / len(master_scores),
        "avg_health_score": sum(health_scores) / len(health_scores),
        "avg_meta_confidence": sum(meta_conf) / len(meta_conf),
        "avg_alert_count": sum(alert_counts) / len(alert_counts),
        "safe_mode_frequency": safe_mode_count / len(buffer),
        "autonomous_state_distribution": auto_states,
        "memory_length": len(buffer),
    }


def render_v37_memory_engine():
    """
    Full UI for the V37 Memory Engine.
    """

    st.title("🧠 V37 Memory Engine")
    st.caption("Long-horizon memory system for storing and analyzing historical V37 states.")

    # Create snapshot
    snapshot = _collect_memory_snapshot()

    # Append to memory
    _append_to_memory(snapshot)

    buffer = st.session_state["v37_memory_buffer"]
    stats = _compute_memory_stats(buffer)

    st.subheader("📚 Memory Buffer (Last 500 Snapshots)")
    st.json(buffer[-10:])  # show last 10 entries

    st.subheader("📈 Long-Horizon Statistics")
    st.json(stats)

    # Export
    st.session_state["v37_memory_export"] = {
        "stats": stats,
        "memory_length": len(buffer),
        "memory_active": True
    }

    themed_card_container()
    st.markdown("### Memory Export Object")
    st.json(st.session_state["v37_memory_export"])

    st.success("V37 Memory Engine complete.")
# ------------- CHUNK 235: V37 MEMORY VISUALIZER (HISTORICAL CHARTS + TRENDS) -------------

import pandas as pd
import plotly.express as px

def _memory_to_dataframe(buffer):
    """
    Convert memory buffer into a pandas DataFrame for charting.
    """

    rows = []
    for snap in buffer:
        rows.append({
            "timestamp": snap["timestamp"],
            "master_score": snap["master"].get("v37_master_score", 0),
            "health_score": snap["monitor"].get("system_health_score", 0),
            "meta_confidence": snap["meta"].get("meta_confidence", 0),
            "alert_count": len(snap["alerts"].get("alerts", [])),
            "safe_mode": 1 if snap["safe"].get("safe_mode_active") else 0,
            "auto_state": snap["auto"].get("autonomous_state", "UNKNOWN"),
        })

    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def render_v37_memory_visualizer():
    """
    Full UI for the V37 Memory Visualizer.
    Creates:
    - Master score trend
    - System health trend
    - Meta-confidence trend
    - Alert frequency chart
    - Safe mode timeline
    - Autonomous mode distribution
    """

    st.title("📊 V37 Memory Visualizer")
    st.caption("Historical charts and long-horizon trend analysis for V37.")

    buffer = st.session_state.get("v37_memory_buffer", [])

    if len(buffer) < 5:
        st.warning("Not enough memory snapshots to generate charts yet.")
        return

    df = _memory_to_dataframe(buffer)

    # --- MASTER SCORE TREND ---
    st.subheader("🏆 Master Score Trend")
    fig = px.line(df, x="timestamp", y="master_score", title="Master Score Over Time")
    st.plotly_chart(fig, use_container_width=True)

    # --- SYSTEM HEALTH TREND ---
    st.subheader("🩺 System Health Trend")
    fig = px.line(df, x="timestamp", y="health_score", title="System Health Over Time")
    st.plotly_chart(fig, use_container_width=True)

    # --- META-CONFIDENCE TREND ---
    st.subheader("🧬 Meta-Confidence Trend")
    fig = px.line(df, x="timestamp", y="meta_confidence", title="Meta-Confidence Over Time")
    st.plotly_chart(fig, use_container_width=True)

    # --- ALERT COUNT TREND ---
    st.subheader("⚠️ Alert Frequency")
    fig = px.bar(df, x="timestamp", y="alert_count", title="Alert Count Over Time")
    st.plotly_chart(fig, use_container_width=True)

    # --- SAFE MODE TIMELINE ---
    st.subheader("🚨 Safe Mode Activation Timeline")
    fig = px.area(df, x="timestamp", y="safe_mode", title="Safe Mode Activation")
    st.plotly_chart(fig, use_container_width=True)

    # --- AUTONOMOUS MODE DISTRIBUTION ---
    st.subheader("🤖 Autonomous Mode Distribution")
    fig = px.pie(
        df,
        names="auto_state",
        title="Autonomous Mode State Distribution"
    )
    st.plotly_chart(fig, use_container_width=True)

    # Export
    st.session_state["v37_memory_visualizer_export"] = {
        "charts_rendered": True,
        "memory_length": len(buffer)
    }

    themed_card_container()
    st.markdown("### Memory Visualizer Export Object")
    st.json(st.session_state["v37_memory_visualizer_export"])

    st.success("V37 Memory Visualizer complete.")
# ------------- CHUNK 236: V37 MEMORY INSIGHTS ENGINE (AI-GENERATED HISTORICAL INSIGHTS) -------------

def _generate_memory_insights(stats):
    """
    Generate AI-style insights based on long-horizon statistics.
    """

    if not stats or stats.get("memory_length", 0) < 5:
        return "Not enough historical data to generate insights."

    insights = []

    # --- MASTER SCORE ---
    ms = stats["avg_master_score"]
    if ms > 0.75:
        insights.append("Master Engine performance has been consistently strong over the observed period.")
    elif ms > 0.50:
        insights.append("Master Engine performance has been stable with moderate fluctuations.")
    else:
        insights.append("Master Engine performance shows signs of instability or weak alignment.")

    # --- SYSTEM HEALTH ---
    hs = stats["avg_health_score"]
    if hs > 0.75:
        insights.append("System Health has remained high, indicating strong engine alignment.")
    elif hs > 0.50:
        insights.append("System Health has been moderate, with occasional stress events.")
    else:
        insights.append("System Health has been low, suggesting persistent misalignment or pressure.")

    # --- META-CONFIDENCE ---
    mc = stats["avg_meta_confidence"]
    if mc > 0.70:
        insights.append("Meta-Brain confidence has remained high, supporting reliable decision-making.")
    elif mc > 0.40:
        insights.append("Meta-Brain confidence has been mixed, with periods of uncertainty.")
    else:
        insights.append("Meta-Brain confidence has been low, indicating unstable predictive conditions.")

    # --- ALERTS ---
    ac = stats["avg_alert_count"]
    if ac > 3:
        insights.append("Alert frequency has been high, suggesting volatile or unstable conditions.")
    elif ac > 1:
        insights.append("Alert frequency has been moderate, with occasional spikes.")
    else:
        insights.append("Alert frequency has remained low, indicating stable operating conditions.")

    # --- SAFE MODE ---
    sm = stats["safe_mode_frequency"]
    if sm > 0.20:
        insights.append("Safe Mode has been triggered frequently, indicating recurring high-risk conditions.")
    elif sm > 0.05:
        insights.append("Safe Mode has been triggered occasionally, typically during stress events.")
    else:
        insights.append("Safe Mode has rarely been activated, suggesting stable system behavior.")

    # --- AUTONOMOUS MODE ---
    auto_dist = stats["autonomous_state_distribution"]
    auto_insight = max(auto_dist, key=auto_dist.get)

    insights.append(f"Autonomous Mode most frequently operated in: **{auto_insight}**.")

    return "\n\n".join(insights)


def render_v37_memory_insights_engine():
    """
    Full UI for the V37 Memory Insights Engine.
    Generates AI-style insights from long-horizon memory.
    """

    st.title("🧠📈 V37 Memory Insights Engine")
    st.caption("AI-generated historical insights based on long-horizon memory trends.")

    stats = st.session_state.get("v37_memory_export", {}).get("stats")

    if not stats:
        st.warning("No memory statistics available yet.")
        return

    insights = _generate_memory_insights(stats)

    themed_card_container()
    st.markdown("## Historical Insights")
    st.markdown(insights)

    # Export
    st.session_state["v37_memory_insights_export"] = {
        "insights": insights,
        "memory_length": stats.get("memory_length"),
        "insights_ready": True
    }

    themed_card_container()
    st.markdown("### Memory Insights Export Object")
    st.json(st.session_state["v37_memory_insights_export"])

    st.success("V37 Memory Insights Engine complete.")
# ------------- CHUNK 237: V37 OPERATOR REPORT GENERATOR (DAILY/WEEKLY AUTO-REPORTS) -------------

import datetime

def _generate_daily_report(stats, insights):
    """
    Generate a structured daily operator report.
    """

    date = datetime.datetime.utcnow().strftime("%Y-%m-%d")

    # Compute this outside the f-string to avoid nested braces
    auto_dist = stats.get("autonomous_state_distribution", {"UNKNOWN": 1})
    most_frequent_state = max(auto_dist, key=auto_dist.get)

    return f"""
# 📅 V37 Daily Operator Report — {date}

## 🏆 Master Engine
- Average Master Score: `{stats.get("avg_master_score", 0):.4f}`

## 🩺 System Health
- Average Health Score: `{stats.get("avg_health_score", 0):.4f}`
- Average Alert Count: `{stats.get("avg_alert_count", 0):.2f}`

## 🧬 Meta-Brain
- Average Meta-Confidence: `{stats.get("avg_meta_confidence", 0):.4f}`

## 🚨 Safe Mode
- Safe Mode Frequency: `{stats.get("safe_mode_frequency", 0):.2%}`

## 🤖 Autonomous Mode
- Most Frequent State: **{most_frequent_state}**

## 🧠 AI Insights
{insights}

---
Generated automatically by the V37 Operator Report Engine.
"""


def _generate_weekly_report(stats, insights):
    """
    Generate a structured weekly operator report.
    """

    date = datetime.datetime.utcnow().strftime("%Y-%m-%d")

    return f"""
# 📊 V37 Weekly Operator Report — Week Ending {date}

## 🔎 System Overview
This weekly report summarizes long-horizon performance, stability, and risk conditions across the V37 architecture.

## 🏆 Master Engine Performance
- Average Master Score: `{stats.get("avg_master_score", 0):.4f}`
- Interpretation: {"Strong" if stats.get("avg_master_score",0)>0.75 else "Moderate" if stats.get("avg_master_score",0)>0.50 else "Weak"}

## 🩺 System Health & Stability
- Average Health Score: `{stats.get("avg_health_score", 0):.4f}`
- Average Alert Count: `{stats.get("avg_alert_count", 0):.2f}`
- Safe Mode Frequency: `{stats.get("safe_mode_frequency", 0):.2%}`

## 🧬 Meta-Brain Confidence
- Average Meta-Confidence: `{stats.get("avg_meta_confidence", 0):.4f}`

## 🤖 Autonomous Mode Behavior
- State Distribution:
{stats.get("autonomous_state_distribution", {})}

## 🧠 AI Insights
{insights}

---
Generated automatically by the V37 Operator Report Engine.
"""


# ------------- CHUNK 238: V37 NOTIFICATION ENGINE (EMAIL/SMS/PUSH ROUTING) -------------

import datetime

def _default_notification_channels():
    """
    Default notification channels.
    These are abstracted - actual delivery is handled externally.
    """

    return {
        "email": True,
        "sms": False,
        "push": True,
    }

# ------------- CHUNK 239: V37 OPERATOR CONSOLE 2.0 (UNIFIED CONTROL ROOM) -------------

def render_v37_operator_console_v2():
    """
    Unified operator control room for V37.
    Combines:
    - System state
    - Alerts
    - Notifications
    - Memory insights
    - Reports
    - Scheduler decisions
    - Orchestrator mode
    """

    st.title("🖥️ V37 Operator Console 2.0")
    st.caption("Unified control room for monitoring, insights, reports, and system actions.")

    # --- SYSTEM SNAPSHOT ---
    st.subheader("📌 System Snapshot")

    master = st.session_state.get("v37_master_export")
    final = st.session_state.get("v37_final_decision_export")
    monitor = st.session_state.get("v37_system_monitor_export")
    meta = st.session_state.get("v37_meta_brain_export")
    auto = st.session_state.get("v37_autonomous_export")
    safe = st.session_state.get("v37_safe_mode_export")

    snapshot = {
        "Master State": master.get("v37_master_state"),
        "Master Score": master.get("v37_master_score"),
        "Final Decision": final.get("v37_final_decision"),
        "Final Score": final.get("v37_final_score"),
        "System Health": monitor.get("system_health_state"),
        "Health Score": monitor.get("system_health_score"),
        "Meta Confidence": meta.get("meta_confidence"),
        "Autonomous Mode": auto.get("autonomous_state"),
        "Safe Mode Active": safe.get("safe_mode_active"),
    }

    themed_card_container()
    st.json(snapshot)

    # --- ALERTS ---
    st.subheader("⚠️ Active Alerts")

    alerts = st.session_state.get("v37_alerts_export", {}).get("alerts", [])
    if alerts:
        st.json(alerts)
    else:
        st.success("No active alerts.")

    # --- NOTIFICATIONS ---
    st.subheader("📣 Recent Notifications")

    notif_log = st.session_state.get("v37_notification_log", [])
    st.json(notif_log[-10:])  # last 10

    # --- MEMORY INSIGHTS ---
    st.subheader("🧠 Memory Insights")

    insights = st.session_state.get("v37_memory_insights_export", {}).get("insights")
    if insights:
        themed_card_container()
        st.markdown(insights)
    else:
        st.info("Memory insights not available yet.")

    # --- REPORTS ---
    st.subheader("📝 Reports")

    reports = st.session_state.get("v37_operator_report_export", {})
    if reports.get("reports_ready"):
        with st.expander("Daily Report"):
            st.markdown(reports["daily_report"])
        with st.expander("Weekly Report"):
            st.markdown(reports["weekly_report"])
    else:
        st.info("Reports not generated yet.")

    # --- SCHEDULER DECISIONS ---
    st.subheader("⚙️ Scheduler Decisions")

    scheduler = st.session_state.get("v37_engine_scheduler_export")
    st.json(scheduler)

    # --- ORCHESTRATOR MODE ---
    st.subheader("🧩 Orchestrator Mode")

    orchestrator = st.session_state.get("v37_orchestrator_export")
    st.json(orchestrator)

    # --- OPERATOR ACTIONS ---
    st.subheader("🛠️ Operator Actions")

    if st.button("Send System Status Notification"):
        msg = f"System Status — Master: {snapshot['Master State']}, Final: {snapshot['Final Decision']}"
        delivered = send_v37_notification(msg, "INFO")
        st.success(f"Delivered via: {delivered}")

    if st.button("Send Critical Alert Notification"):
        delivered = send_v37_notification("Critical system alert triggered.", "CRITICAL")
        st.error(f"Delivered via: {delivered}")

    # --- EXPORT ---
    st.session_state["v37_operator_console_v2_export"] = {
        "snapshot": snapshot,
        "alerts": alerts,
        "notifications": notif_log[-10:],
        "insights_available": insights is not None,
        "reports_available": reports.get("reports_ready", False),
        "scheduler": scheduler,
        "orchestrator": orchestrator,
        "console_ready": True
    }

    themed_card_container()
    st.markdown("### Operator Console 2.0 Export Object")
    st.json(st.session_state["v37_operator_console_v2_export"])

    st.success("V37 Operator Console 2.0 loaded.")
# ------------- CHUNK 240: V37 SYSTEM SUMMARY ENGINE 2.0 (UNIFIED INTELLIGENCE SUMMARY) -------------

def _build_summary_section(title, content_dict):
    """
    Render a clean, themed summary section.
    """
    themed_card_container()
    st.markdown(f"## {title}")
    st.json(content_dict)


def render_v37_system_summary_engine_v2():
    """
    Unified intelligence summary for V37.
    Combines:
    - Master Engine
    - Final Decision
    - System Health
    - Meta-Brain
    - Alerts
    - Memory Insights
    - Scheduler Decisions
    - Orchestrator Mode
    - Notification State
    """

    st.title("📘 V37 System Summary 2.0")
    st.caption("Unified intelligence summary across all V37 engines and layers.")

    # --- COLLECT ALL SIGNALS ---
    master = st.session_state.get("v37_master_export")
    final = st.session_state.get("v37_final_decision_export")
    monitor = st.session_state.get("v37_system_monitor_export")
    meta = st.session_state.get("v37_meta_brain_export")
    alerts = st.session_state.get("v37_alerts_export", {}).get("alerts", [])
    insights = st.session_state.get("v37_memory_insights_export", {}).get("insights")
    scheduler = st.session_state.get("v37_engine_scheduler_export")
    orchestrator = st.session_state.get("v37_orchestrator_export")
    notifications = st.session_state.get("v37_notification_log", [])[-10:]

    # --- SUMMARY SECTIONS ---
    _build_summary_section("🏆 Master Engine", {
        "State": master.get("v37_master_state"),
        "Score": master.get("v37_master_score"),
    })

    _build_summary_section("🎯 Final Decision", {
        "Decision": final.get("v37_final_decision"),
        "Score": final.get("v37_final_score"),
    })

    _build_summary_section("🩺 System Health", {
        "Health State": monitor.get("system_health_state"),
        "Health Score": monitor.get("system_health_score"),
        "Active Alerts": len(alerts),
    })

    _build_summary_section("🧬 Meta-Brain", {
        "Meta Confidence": meta.get("meta_confidence"),
        "Meta State": meta.get("meta_state"),
    })

    _build_summary_section("⚠️ Alerts", {
        "Alert Count": len(alerts),
        "Alerts": alerts,
    })

    _build_summary_section("🧠 Memory Insights", {
        "Insights": insights or "Not available",
    })

    _build_summary_section("⚙️ Scheduler Decisions", scheduler)

    _build_summary_section("🧩 Orchestrator Mode", orchestrator)

    _build_summary_section("📣 Recent Notifications", {
        "Last 10 Notifications": notifications
    })

    # --- EXPORT ---
    st.session_state["v37_system_summary_v2_export"] = {
        "master": master,
        "final": final,
        "monitor": monitor,
        "meta": meta,
        "alerts": alerts,
        "insights": insights,
        "scheduler": scheduler,
        "orchestrator": orchestrator,
        "notifications": notifications,
        "summary_ready": True
    }

    themed_card_container()
    st.markdown("### Unified Summary Export Object")
    st.json(st.session_state["v37_system_summary_v2_export"])

    st.success("V37 System Summary 2.0 loaded.")
# ------------- CHUNK 241: V37 META-DIAGNOSTICS ENGINE (SELF-DIAGNOSIS + ROOT-CAUSE ANALYSIS) -------------

def _diagnose_master(master):
    score = master.get("v37_master_score", 0)
    state = master.get("v37_master_state")

    if score < 0.35:
        return "Master Engine is in a degraded state. Low alignment and weak predictive coherence detected."
    if score < 0.55:
        return "Master Engine is moderately unstable. Fluctuating predictive alignment observed."
    return f"Master Engine stable ({state})."


def _diagnose_health(monitor):
    score = monitor.get("system_health_score", 0)
    state = monitor.get("system_health_state")

    if score < 0.40:
        return "System Health is critically low. Multiple engines show misalignment or stress."
    if score < 0.65:
        return "System Health is moderate. Occasional stress events detected."
    return f"System Health stable ({state})."


def _diagnose_meta(meta):
    conf = meta.get("meta_confidence", 0)

    if conf < 0.30:
        return "Meta-Brain confidence is critically low. Predictive uncertainty is high."
    if conf < 0.55:
        return "Meta-Brain confidence is moderate with intermittent uncertainty."
    return "Meta-Brain confidence stable."


def _diagnose_alerts(alerts):
    count = len(alerts)

    if count > 5:
        return "High alert volume detected. System experiencing volatile or unstable conditions."
    if count > 1:
        return "Moderate alert activity. Occasional instability detected."
    return "Low alert activity. System stable."


def _diagnose_safe_mode(safe):
    if safe.get("safe_mode_active"):
        return "Safe Mode is currently active due to detected high-risk conditions."
    return "Safe Mode inactive."


def _diagnose_autonomous(auto):
    state = auto.get("autonomous_state", "UNKNOWN")

    if state == "HALT":
        return "Autonomous Mode halted due to critical conditions."
    if state == "LIMITED":
        return "Autonomous Mode operating in limited capacity."
    if state == "FULL":
        return "Autonomous Mode fully active."
    return f"Autonomous Mode state: {state}."


def _diagnose_memory(stats):
    if not stats:
        return "No long-horizon memory available."

    if stats.get("avg_master_score", 0) < 0.45:
        return "Historical trend shows persistent Master Engine weakness."

    if stats.get("avg_health_score", 0) < 0.50:
        return "Historical trend indicates systemic instability."

    if stats.get("safe_mode_frequency", 0) > 0.20:
        return "Frequent Safe Mode activations detected historically."

    return "Historical trends stable."


def _generate_root_cause(master_diag, health_diag, meta_diag, alert_diag, memory_diag):
    """
    Combine diagnostics into a root-cause analysis.
    """

    issues = []

    for diag in [master_diag, health_diag, meta_diag, alert_diag, memory_diag]:
        if "low" in diag.lower() or "critical" in diag.lower() or "unstable" in diag.lower():
            issues.append(diag)

    if not issues:
        return "No significant root causes detected. System operating normally."

    return "Root Cause Analysis:\n\n- " + "\n- ".join(issues)


def _generate_recommendations(master_diag, health_diag, meta_diag, alert_diag, memory_diag):
    """
    Generate corrective recommendations based on diagnostics.
    """

    recs = []

    if "Master Engine" in master_diag and "degraded" in master_diag:
        recs.append("Increase predictive smoothing and reduce volatility weighting.")

    if "System Health" in health_diag and "low" in health_diag:
        recs.append("Recalibrate engine alignment and reduce cross-engine variance.")

    if "Meta-Brain" in meta_diag and "low" in meta_diag:
        recs.append("Increase meta-confidence weighting and reduce uncertainty penalties.")

    if "alert" in alert_diag.lower() and "high" in alert_diag.lower():
        recs.append("Investigate alert clusters and reduce threshold sensitivity.")

    if "historical" in memory_diag.lower() and "weakness" in memory_diag.lower():
        recs.append("Apply long-horizon stabilization routines.")

    if not recs:
        recs.append("No corrective action required.")

    return recs


def render_v37_meta_diagnostics_engine():
    """
    Full UI for the V37 Meta-Diagnostics Engine.
    """

    st.title("🧪 V37 Meta-Diagnostics Engine")
    st.caption("Self-diagnosis, root-cause analysis, and corrective recommendations.")

    master = st.session_state.get("v37_master_export", {})
    final = st.session_state.get("v37_final_decision_export", {})
    monitor = st.session_state.get("v37_system_monitor_export", {})
    meta = st.session_state.get("v37_meta_brain_export", {})
    alerts = st.session_state.get("v37_alerts_export", {}).get("alerts", [])
    auto = st.session_state.get("v37_autonomous_export", {})
    safe = st.session_state.get("v37_safe_mode_export", {})
    memory_stats = st.session_state.get("v37_memory_export", {}).get("stats")

    # --- DIAGNOSTICS ---
    master_diag = _diagnose_master(master)
    health_diag = _diagnose_health(monitor)
    meta_diag = _diagnose_meta(meta)
    alert_diag = _diagnose_alerts(alerts)
    safe_diag = _diagnose_safe_mode(safe)
    auto_diag = _diagnose_autonomous(auto)
    memory_diag = _diagnose_memory(memory_stats)

    # --- ROOT CAUSE ---
    root_cause = _generate_root_cause(
        master_diag, health_diag, meta_diag, alert_diag, memory_diag
    )

    # --- RECOMMENDATIONS ---
    recs = _generate_recommendations(
        master_diag, health_diag, meta_diag, alert_diag, memory_diag
    )

    # --- RENDER ---
    themed_card_container()
    st.markdown("## 🔍 Diagnostics")
    st.json({
        "Master Engine": master_diag,
        "System Health": health_diag,
        "Meta-Brain": meta_diag,
        "Alerts": alert_diag,
        "Safe Mode": safe_diag,
        "Autonomous Mode": auto_diag,
        "Memory Trends": memory_diag,
    })

    themed_card_container()
    st.markdown("## 🧠 Root Cause Analysis")
    st.markdown(root_cause)

    themed_card_container()
    st.markdown("## 🛠️ Recommendations")
    st.json(recs)

    # --- EXPORT ---
    st.session_state["v37_meta_diagnostics_export"] = {
        "diagnostics": {
            "master": master_diag,
            "health": health_diag,
            "meta": meta_diag,
            "alerts": alert_diag,
            "safe": safe_diag,
            "auto": auto_diag,
            "memory": memory_diag,
        },
        "root_cause": root_cause,
        "recommendations": recs,
        "diagnostics_ready": True
    }

    themed_card_container()
    st.markdown("### Meta-Diagnostics Export Object")
    st.json(st.session_state["v37_meta_diagnostics_export"])

    st.success("V37 Meta-Diagnostics Engine complete.")
# ------------- CHUNK 242: V37 SELF-HEALING ENGINE (AUTOMATIC CORRECTIONS + ADAPTIVE STABILIZATION) -------------

import datetime

def _default_healing_state():
    return {
        "volatility_weight": 1.0,
        "alignment_weight": 1.0,
        "meta_confidence_weight": 1.0,
        "alert_threshold": 1.0,
        "long_horizon_stability": 1.0,
    }


def _log_healing_action(action, details):
    """
    Append a healing action to the log.
    """

    if "v37_self_healing_log" not in st.session_state:
        st.session_state["v37_self_healing_log"] = []

    st.session_state["v37_self_healing_log"].append({
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "action": action,
        "details": details
    })


def _apply_master_stabilization(healing_state):
    healing_state["alignment_weight"] *= 1.10
    healing_state["volatility_weight"] *= 0.90
    _log_healing_action("Master Stabilization", healing_state)


def _apply_health_stabilization(healing_state):
    healing_state["alignment_weight"] *= 1.15
    healing_state["alert_threshold"] *= 1.20
    _log_healing_action("Health Stabilization", healing_state)


def _apply_meta_stabilization(healing_state):
    healing_state["meta_confidence_weight"] *= 1.25
    healing_state["volatility_weight"] *= 0.85
    _log_healing_action("Meta-Brain Stabilization", healing_state)


def _apply_alert_stabilization(healing_state):
    healing_state["alert_threshold"] *= 1.30
    healing_state["volatility_weight"] *= 0.90
    _log_healing_action("Alert Stabilization", healing_state)


def _apply_long_horizon_stabilization(healing_state):
    healing_state["long_horizon_stability"] *= 1.20
    healing_state["alignment_weight"] *= 1.10
    _log_healing_action("Long-Horizon Stabilization", healing_state)


def _apply_self_healing(diagnostics):
    """
    Apply healing routines based on diagnostics.
    """

    healing_state = st.session_state.get("v37_self_healing_state", _default_healing_state())

    # Master Engine
    if "degraded" in diagnostics["master"].lower():
        _apply_master_stabilization(healing_state)

    # System Health
    if "low" in diagnostics["health"].lower():
        _apply_health_stabilization(healing_state)

    # Meta-Brain
    if "low" in diagnostics["meta"].lower():
        _apply_meta_stabilization(healing_state)

    # Alerts
    if "high" in diagnostics["alerts"].lower():
        _apply_alert_stabilization(healing_state)

    # Memory Trends
    if "historical" in diagnostics["memory"].lower():
        _apply_long_horizon_stabilization(healing_state)

    st.session_state["v37_self_healing_state"] = healing_state
    return healing_state


def render_v37_self_healing_engine():
    """
    Full UI for the V37 Self-Healing Engine.
    """

    st.title("🩹 V37 Self-Healing Engine")
    st.caption("Automatic corrections and adaptive stabilization based on diagnostics.")

    diagnostics = st.session_state.get("v37_meta_diagnostics_export", {}).get("diagnostics")

    if not diagnostics:
        st.warning("Diagnostics not available yet.")
        return

    # Apply healing
    healing_state = _apply_self_healing(diagnostics)

    # Render healing state
    themed_card_container()
    st.markdown("## Healing State")
    st.json(healing_state)

    # Render healing log
    st.subheader("📜 Healing Log")
    st.json(st.session_state.get("v37_self_healing_log", []))

    # Export
    st.session_state["v37_self_healing_export"] = {
        "healing_state": healing_state,
        "log": st.session_state.get("v37_self_healing_log", []),
        "healing_ready": True
    }

    themed_card_container()
    st.markdown("### Self-Healing Export Object")
    st.json(st.session_state["v37_self_healing_export"])

    st.success("V37 Self-Healing Engine complete.")
# ------------- CHUNK 243: V37 ADAPTIVE OPTIMIZATION ENGINE (CONTINUOUS SELF-TUNING) -------------

import datetime

def _default_optimization_state():
    return {
        "predictive_weight": 1.0,
        "risk_weight": 1.0,
        "opportunity_weight": 1.0,
        "parlay_weight": 1.0,
        "meta_weight": 1.0,
        "volatility_sensitivity": 1.0,
        "alignment_sensitivity": 1.0,
        "confidence_curve": 1.0,
        "stability_curve": 1.0,
    }


def _log_optimization(action, details):
    """
    Append an optimization action to the log.
    """

    if "v37_optimization_log" not in st.session_state:
        st.session_state["v37_optimization_log"] = []

    st.session_state["v37_optimization_log"].append({
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "action": action,
        "details": details
    })


def _apply_predictive_optimization(opt_state, healing_state):
    opt_state["predictive_weight"] *= 1.0 + (healing_state["alignment_weight"] - 1.0) * 0.25
    opt_state["volatility_sensitivity"] *= 1.0 - (1.0 - healing_state["volatility_weight"]) * 0.25
    _log_optimization("Predictive Optimization", opt_state)


def _apply_risk_optimization(opt_state, diagnostics):
    if "low" in diagnostics["health"].lower():
        opt_state["risk_weight"] *= 1.15
        opt_state["alignment_sensitivity"] *= 1.10
        _log_optimization("Risk Optimization", opt_state)


def _apply_opportunity_optimization(opt_state, diagnostics):
    if "moderate" in diagnostics["meta"].lower():
        opt_state["opportunity_weight"] *= 1.10
        opt_state["confidence_curve"] *= 1.05
        _log_optimization("Opportunity Optimization", opt_state)


def _apply_parlay_optimization(opt_state, diagnostics):
    if "high" in diagnostics["alerts"].lower():
        opt_state["parlay_weight"] *= 0.85
        opt_state["volatility_sensitivity"] *= 0.90
        _log_optimization("Parlay Optimization", opt_state)


def _apply_long_horizon_optimization(opt_state, memory_stats):
    if not memory_stats:
        return

    if memory_stats.get("avg_master_score", 1) < 0.50:
        opt_state["stability_curve"] *= 1.20
        opt_state["alignment_sensitivity"] *= 1.15
        _log_optimization("Long-Horizon Optimization", opt_state)


def _apply_adaptive_optimization(diagnostics, healing_state, memory_stats):
    """
    Apply continuous optimization routines.
    """

    opt_state = st.session_state.get("v37_optimization_state", _default_optimization_state())

    _apply_predictive_optimization(opt_state, healing_state)
    _apply_risk_optimization(opt_state, diagnostics)
    _apply_opportunity_optimization(opt_state, diagnostics)
    _apply_parlay_optimization(opt_state, diagnostics)
    _apply_long_horizon_optimization(opt_state, memory_stats)

    st.session_state["v37_optimization_state"] = opt_state
    return opt_state


def render_v37_adaptive_optimization_engine():
    """
    Full UI for the V37 Adaptive Optimization Engine.
    """

    st.title("⚙️ V37 Adaptive Optimization Engine")
    st.caption("Continuous self-tuning based on diagnostics, healing, and long-horizon memory.")

    diagnostics = st.session_state.get("v37_meta_diagnostics_export", {}).get("diagnostics")
    healing_state = st.session_state.get("v37_self_healing_export", {}).get("healing_state")
    memory_stats = st.session_state.get("v37_memory_export", {}).get("stats")

    if not diagnostics or not healing_state:
        st.warning("Diagnostics or healing state not available yet.")
        return

    # Apply optimization
    opt_state = _apply_adaptive_optimization(diagnostics, healing_state, memory_stats)

    # Render optimization state
    themed_card_container()
    st.markdown("## Optimization State")
    st.json(opt_state)

    # Render optimization log
    st.subheader("📜 Optimization Log")
    st.json(st.session_state.get("v37_optimization_log", []))

    # Export
    st.session_state["v37_adaptive_optimization_export"] = {
        "optimization_state": opt_state,
        "log": st.session_state.get("v37_optimization_log", []),
        "optimization_ready": True
    }

    themed_card_container()
    st.markdown("### Adaptive Optimization Export Object")
    st.json(st.session_state["v37_adaptive_optimization_export"])

    st.success("V37 Adaptive Optimization Engine complete.")
# ------------- CHUNK 244: V37 AUTONOMOUS AGENT LAYER (SELF-DIRECTED SYSTEM BEHAVIOR) -------------

import datetime

def _default_agent_state():
    return {
        "agent_mode": "IDLE",  # IDLE, ACTIVE, ESCALATING, HALT
        "last_action": None,
        "action_count": 0,
        "escalation_count": 0,
        "halt_triggered": False,
    }


def _log_agent_action(action, details):
    """
    Append an autonomous agent action to the log.
    """

    if "v37_agent_log" not in st.session_state:
        st.session_state["v37_agent_log"] = []

    st.session_state["v37_agent_log"].append({
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "action": action,
        "details": details
    })


def _determine_agent_mode(diagnostics, healing_state, opt_state):
    """
    # Determine the agent's operating mode.
    """

    # Critical conditions → HALT
    if (
        "critical" in diagnostics["health"].lower()
        or "halt" in diagnostics["auto"].lower()
        or healing_state["volatility_weight"] < 0.5
    ):
        return "HALT"

    # High alert or unstable → ESCALATING
    if (
        "high" in diagnostics["alerts"].lower()
        or "unstable" in diagnostics["master"].lower()
        or opt_state["volatility_sensitivity"] > 1.3
    ):
        return "ESCALATING"

    # Stable → ACTIVE
    if (
        "stable" in diagnostics["master"].lower()
        and "stable" in diagnostics["health"].lower()
        and "stable" in diagnostics["meta"].lower()
    ):
        return "ACTIVE"

    # Default
    return "IDLE"


def _execute_agent_action(mode, diagnostics, healing_state, opt_state):
    """
    Execute an autonomous action based on the agent mode.
    """

    if mode == "HALT":
        _log_agent_action("HALT_TRIGGERED", {
            "reason": "Critical system conditions detected.",
            "diagnostics": diagnostics
        })
        return "HALT_TRIGGERED"

    if mode == "ESCALATING":
        send_v37_notification(
            "System entering escalation mode due to instability.",
            "CRITICAL"
        )
        _log_agent_action("ESCALATION_NOTICE", diagnostics)
        return "ESCALATION_NOTICE"

    if mode == "ACTIVE":
        send_v37_notification(
            "System operating in stable autonomous mode.",
            "INFO"
        )
        _log_agent_action("ACTIVE_STATUS", {
            "healing_state": healing_state,
            "optimization_state": opt_state
        })
        return "ACTIVE_STATUS"

    # IDLE
    _log_agent_action("IDLE_STATUS", diagnostics)
    return "IDLE_STATUS"


def render_v37_autonomous_agent_layer():
    """
    Full UI for the V37 Autonomous Agent Layer.
    """

    st.title("🤖 V37 Autonomous Agent Layer")
    st.caption("Self-directed system behavior based on diagnostics, healing, and optimization.")

    diagnostics = st.session_state.get("v37_meta_diagnostics_export", {}).get("diagnostics")
    healing_state = st.session_state.get("v37_self_healing_export", {}).get("healing_state")
    opt_state = st.session_state.get("v37_adaptive_optimization_export", {}).get("optimization_state")

    if not diagnostics or not healing_state or not opt_state:
        st.warning("Diagnostics, healing state, or optimization state not available yet.")
        return

    # Load or initialize agent state
    agent_state = st.session_state.get("v37_agent_state", _default_agent_state())

    # Determine mode
    mode = _determine_agent_mode(diagnostics, healing_state, opt_state)
    agent_state["agent_mode"] = mode

    # Execute action
    action = _execute_agent_action(mode, diagnostics, healing_state, opt_state)
    agent_state["last_action"] = action
    agent_state["action_count"] += 1

    if mode == "ESCALATING":
        agent_state["escalation_count"] += 1
    if mode == "HALT":
        agent_state["halt_triggered"] = True

    st.session_state["v37_agent_state"] = agent_state

    # Render agent state
    themed_card_container()
    st.markdown("## Agent State")
    st.json(agent_state)

    # Render agent log
    st.subheader("📜 Agent Log")
    st.json(st.session_state.get("v37_agent_log", []))

    # Export
    st.session_state["v37_autonomous_agent_export"] = {
        "agent_state": agent_state,
        "log": st.session_state.get("v37_agent_log", []),
        "agent_ready": True
    }

    themed_card_container()
    st.markdown("### Autonomous Agent Export Object")
    st.json(st.session_state["v37_autonomous_agent_export"])

    st.success("V37 Autonomous Agent Layer complete.")
# ------------- CHUNK 245: V37 AUTONOMOUS AGENT DASHBOARD (REAL-TIME VISUALIZATION) -------------

import pandas as pd
import plotly.express as px

def _agent_log_to_dataframe(log):
    """
    Convert agent log into a DataFrame for visualization.
    """

    if not log:
        return pd.DataFrame([])

    rows = []
    for entry in log:
        rows.append({
            "timestamp": entry["timestamp"],
            "action": entry["action"],
            "details": str(entry["details"]),
        })

    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def render_v37_autonomous_agent_dashboard():
    """
    Real-time visualization dashboard for the V37 Autonomous Agent.
    """

    st.title("🤖📊 V37 Autonomous Agent Dashboard")
    st.caption("Real-time visualization of autonomous agent behavior, actions, and stability.")

    agent_state = st.session_state.get("v37_agent_state")
    agent_log = st.session_state.get("v37_agent_log", [])

    if not agent_state:
        st.warning("Autonomous agent state not available yet.")
        return

    # --- AGENT STATE ---
    st.subheader("🧠 Current Agent State")
    themed_card_container()
    st.json(agent_state)

    # --- AGENT LOG ---
    st.subheader("📜 Agent Action Log")
    st.json(agent_log[-15:])  # last 15 entries

    # --- VISUALIZATION ---
    df = _agent_log_to_dataframe(agent_log)

    if df.empty:
        st.info("No agent actions recorded yet.")
    else:
        # ACTION FREQUENCY
        st.subheader("📈 Action Frequency Over Time")
        fig = px.histogram(
            df,
            x="timestamp",
            color="action",
            title="Agent Actions Over Time",
            nbins=20
        )
        st.plotly_chart(fig, use_container_width=True)

        # ACTION TIMELINE
        st.subheader("🕒 Action Timeline")
        fig = px.scatter(
            df,
            x="timestamp",
            y="action",
            title="Agent Action Timeline",
            color="action",
            hover_data=["details"]
        )
        st.plotly_chart(fig, use_container_width=True)

        # ESCALATION VS NORMAL
        st.subheader("🚨 Escalation vs Normal Actions")
        df["is_escalation"] = df["action"].apply(lambda x: "ESCALATION" if "ESCALATION" in x else "NORMAL")
        fig = px.pie(
            df,
            names="is_escalation",
            title="Escalation vs Normal Behavior"
        )
        st.plotly_chart(fig, use_container_width=True)

    # --- EXPORT ---
    st.session_state["v37_autonomous_agent_dashboard_export"] = {
        "agent_state": agent_state,
        "log_length": len(agent_log),
        "dashboard_ready": True
    }

    themed_card_container()
    st.markdown("### Agent Dashboard Export Object")
    st.json(st.session_state["v37_autonomous_agent_dashboard_export"])

    st.success("V37 Autonomous Agent Dashboard loaded.")
# ------------- CHUNK 246: V37 FULL AUTO-PILOT MODE (HANDS-OFF SYSTEM OPERATION) -------------

import datetime

def _default_autopilot_state():
    return {
        "autopilot_active": False,
        "cycle_count": 0,
        "last_cycle": None,
        "last_action": None,
        "halted": False,
        "escalations": 0,
    }


def _log_autopilot_cycle(action, diagnostics, agent_state):
    """
    Log each auto-pilot cycle.
    """

    if "v37_autopilot_log" not in st.session_state:
        st.session_state["v37_autopilot_log"] = []

    st.session_state["v37_autopilot_log"].append({
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "action": action,
        "diagnostics": diagnostics,
        "agent_state": agent_state,
    })


def _run_autopilot_cycle():
    """
    Executes a full auto-pilot cycle:
    - Diagnostics
    - Healing
    - Optimization
    - Agent action
    """

    diagnostics = st.session_state.get("v37_meta_diagnostics_export", {}).get("diagnostics")
    healing_state = st.session_state.get("v37_self_healing_export", {}).get("healing_state")
    opt_state = st.session_state.get("v37_adaptive_optimization_export", {}).get("optimization_state")
    agent_state = st.session_state.get("v37_agent_state")

    if not diagnostics or not healing_state or not opt_state or not agent_state:
        return "MISSING_STATE"

    # Determine agent mode
    mode = agent_state["agent_mode"]

    # Determine action based on mode
    if mode == "HALT":
        action = "HALT_TRIGGERED"
    elif mode == "ESCALATING":
        action = "ESCALATION_NOTICE"
    elif mode == "ACTIVE":
        action = "ACTIVE_STATUS"
    else:
        action = "IDLE_STATUS"

    # Log cycle
    _log_autopilot_cycle(action, diagnostics, agent_state)

    return action


def render_v37_full_autopilot_mode():
    """
    Full UI for V37 Full Auto-Pilot Mode.
    """

    st.title("🛫 V37 Full Auto-Pilot Mode")
    st.caption("Hands-off system operation with continuous autonomous cycles.")

    # Load or initialize autopilot state
    autopilot = st.session_state.get("v37_autopilot_state", _default_autopilot_state())

    # --- TOGGLE AUTOPILOT ---
    st.subheader("⚙️ Auto-Pilot Control")

    activate = st.checkbox("Enable Full Auto-Pilot Mode", value=autopilot["autopilot_active"])

    autopilot["autopilot_active"] = activate

    if activate:
        # Run a cycle
        action = _run_autopilot_cycle()
        autopilot["cycle_count"] += 1
        autopilot["last_cycle"] = datetime.datetime.utcnow().isoformat()
        autopilot["last_action"] = action

        if action == "HALT_TRIGGERED":
            autopilot["halted"] = True

        if action == "ESCALATION_NOTICE":
            autopilot["escalations"] += 1

        st.success(f"Auto-Pilot Cycle Executed — Action: {action}")
    else:
        st.info("Auto-Pilot is currently disabled.")

    st.session_state["v37_autopilot_state"] = autopilot

    # --- AUTOPILOT STATE ---
    st.subheader("🧠 Auto-Pilot State")
    themed_card_container()
    st.json(autopilot)

    # --- AUTOPILOT LOG ---
    st.subheader("📜 Auto-Pilot Log (Last 20 Cycles)")
    st.json(st.session_state.get("v37_autopilot_log", [])[-20:])

    # --- EXPORT ---
    st.session_state["v37_full_autopilot_export"] = {
        "autopilot_state": autopilot,
        "log_length": len(st.session_state.get("v37_autopilot_log", [])),
        "autopilot_ready": True
    }

    themed_card_container()
    st.markdown("### Full Auto-Pilot Export Object")
    st.json(st.session_state["v37_full_autopilot_export"])

    st.success("V37 Full Auto-Pilot Mode loaded.")
# ------------- CHUNK 247: V37 AUTO-PILOT SAFETY LAYER (FAIL-SAFE + GUARDRAILS) -------------

import datetime

def _default_safety_state():
    return {
        "safety_engaged": False,
        "unsafe_cycles": 0,
        "max_unsafe_cycles": 5,
        "max_escalations": 3,
        "max_halt_events": 1,
        "last_safety_event": None,
        "halt_events": 0,
        "escalation_events": 0,
    }


def _log_safety_event(event, details):
    """
    Append a safety event to the safety log.
    """

    if "v37_safety_log" not in st.session_state:
        st.session_state["v37_safety_log"] = []

    st.session_state["v37_safety_log"].append({
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "event": event,
        "details": details
    })


def _check_for_halt(agent_state, safety_state):
    """
    Detect repeated HALT triggers.
    """

    if agent_state.get("halt_triggered"):
        safety_state["halt_events"] += 1
        _log_safety_event("HALT_DETECTED", agent_state)

        if safety_state["halt_events"] > safety_state["max_halt_events"]:
            return True

    return False


def _check_for_escalation(agent_state, safety_state):
    """
    Detect excessive escalation behavior.
    """

    if agent_state.get("agent_mode") == "ESCALATING":
        safety_state["escalation_events"] += 1
        _log_safety_event("ESCALATION_DETECTED", agent_state)

        if safety_state["escalation_events"] > safety_state["max_escalations"]:
            return True

    return False


def _check_for_unsafe_cycles(autopilot_state, safety_state):
    """
    Detect repeated unsafe cycles.
    """

    if autopilot_state.get("last_action") in ["HALT_TRIGGERED", "ESCALATION_NOTICE"]:
        safety_state["unsafe_cycles"] += 1

        if safety_state["unsafe_cycles"] > safety_state["max_unsafe_cycles"]:
            return True

    return False


def _engage_safety_shutdown(safety_state):
    """
    Disable auto-pilot and notify operators.
    """

    safety_state["safety_engaged"] = True
    safety_state["last_safety_event"] = datetime.datetime.utcnow().isoformat()

    # Disable auto-pilot
    if "v37_autopilot_state" in st.session_state:
        st.session_state["v37_autopilot_state"]["autopilot_active"] = False

    # Notify operator
    send_v37_notification(
        "⚠️ Auto-Pilot Safety Shutdown Activated — Unsafe autonomous behavior detected.",
        "CRITICAL"
    )

    _log_safety_event("SAFETY_SHUTDOWN", safety_state)


def _run_safety_checks():
    """
    Run all safety checks and engage shutdown if needed.
    """

    safety_state = st.session_state.get("v37_safety_state", _default_safety_state())
    agent_state = st.session_state.get("v37_agent_state", {})
    autopilot_state = st.session_state.get("v37_autopilot_state", {})

    # Check conditions
    halt_issue = _check_for_halt(agent_state, safety_state)
    escalation_issue = _check_for_escalation(agent_state, safety_state)
    unsafe_cycle_issue = _check_for_unsafe_cycles(autopilot_state, safety_state)

    if halt_issue or escalation_issue or unsafe_cycle_issue:
        _engage_safety_shutdown(safety_state)

    st.session_state["v37_safety_state"] = safety_state
    return safety_state


def render_v37_autopilot_safety_layer():
    """
    Full UI for the V37 Auto-Pilot Safety Layer.
    """

    st.title("🛡️ V37 Auto-Pilot Safety Layer")
    st.caption("Fail-safe guardrails for autonomous operation.")

    # Run safety checks
    safety_state = _run_safety_checks()

    # Render safety state
    themed_card_container()
    st.markdown("## Safety State")
    st.json(safety_state)

    # Render safety log
    st.subheader("📜 Safety Log")
    st.json(st.session_state.get("v37_safety_log", []))

    # Export
    st.session_state["v37_autopilot_safety_export"] = {
        "safety_state": safety_state,
        "log": st.session_state.get("v37_safety_log", []),
        "safety_ready": True
    }

    themed_card_container()
    st.markdown("### Auto-Pilot Safety Export Object")
    st.json(st.session_state["v37_autopilot_safety_export"])

    st.success("V37 Auto-Pilot Safety Layer complete.")
# ------------- CHUNK 248: V37 MANUAL OVERRIDE PANEL (OPERATOR INTERVENTION LAYER) -------------

import datetime

def _log_override_event(event, details):
    """
    Append a manual override event to the override log.
    """

    if "v37_override_log" not in st.session_state:
        st.session_state["v37_override_log"] = []

    st.session_state["v37_override_log"].append({
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "event": event,
        "details": details
    })


def _force_agent_mode(mode):
    """
    Force the autonomous agent into a specific mode.
    """

    if "v37_agent_state" not in st.session_state:
        return

    st.session_state["v37_agent_state"]["agent_mode"] = mode
    st.session_state["v37_agent_state"]["last_action"] = f"FORCED_{mode}"
    _log_override_event("FORCE_AGENT_MODE", {"mode": mode})


def _clear_safety_lock():
    """
    Clear safety shutdown and allow auto-pilot to resume.
    """

    safety = st.session_state.get("v37_safety_state")
    if safety:
        safety["safety_engaged"] = False
        safety["unsafe_cycles"] = 0
        safety["halt_events"] = 0
        safety["escalation_events"] = 0
        safety["last_safety_event"] = None

    if "v37_autopilot_state" in st.session_state:
        st.session_state["v37_autopilot_state"]["autopilot_active"] = False

    _log_override_event("CLEAR_SAFETY_LOCK", safety)


def _reset_agent_state():
    """
    Reset the autonomous agent to default state.
    """

    st.session_state["v37_agent_state"] = {
        "agent_mode": "IDLE",
        "last_action": None,
        "action_count": 0,
        "escalation_count": 0,
        "halt_triggered": False,
    }

    _log_override_event("RESET_AGENT_STATE", st.session_state["v37_agent_state"])


def _reset_healing_and_optimization():
    """
    Reset healing and optimization states.
    """

    st.session_state["v37_self_healing_state"] = {
        "volatility_weight": 1.0,
        "alignment_weight": 1.0,
        "meta_confidence_weight": 1.0,
        "alert_threshold": 1.0,
        "long_horizon_stability": 1.0,
    }

    st.session_state["v37_optimization_state"] = {
        "predictive_weight": 1.0,
        "risk_weight": 1.0,
        "opportunity_weight": 1.0,
        "parlay_weight": 1.0,
        "meta_weight": 1.0,
        "volatility_sensitivity": 1.0,
        "alignment_sensitivity": 1.0,
        "confidence_curve": 1.0,
        "stability_curve": 1.0,
    }

    _log_override_event("RESET_HEALING_OPTIMIZATION", {
        "healing": st.session_state["v37_self_healing_state"],
        "optimization": st.session_state["v37_optimization_state"]
    })


def render_v37_manual_override_panel():
    """
    Full UI for the V37 Manual Override Panel.
    """

    st.title("🛠️ V37 Manual Override Panel")
    st.caption("Operator intervention controls for autonomous and safety systems.")

    # --- FORCE AGENT MODE ---
    st.subheader("🎛️ Force Agent Mode")

    if st.button("Force ACTIVE Mode"):
        _force_agent_mode("ACTIVE")
        st.success("Agent forced into ACTIVE mode.")

    if st.button("Force ESCALATING Mode"):
        _force_agent_mode("ESCALATING")
        st.warning("Agent forced into ESCALATING mode.")

    if st.button("Force HALT Mode"):
        _force_agent_mode("HALT")
        st.error("Agent forced into HALT mode.")

    if st.button("Force IDLE Mode"):
        _force_agent_mode("IDLE")
        st.info("Agent forced into IDLE mode.")

    # --- SAFETY OVERRIDES ---
    st.subheader("🛡️ Safety Overrides")

    if st.button("Clear Safety Lock"):
        _clear_safety_lock()
        st.success("Safety lock cleared. Auto-pilot can be re-enabled.")

    # --- RESET CONTROLS ---
    st.subheader("🔄 Reset Controls")

    if st.button("Reset Agent State"):
        _reset_agent_state()
        st.success("Agent state reset.")

    if st.button("Reset Healing & Optimization"):
        _reset_healing_and_optimization()
        st.success("Healing and optimization reset.")

    # --- MANUAL NOTIFICATION ---
    st.subheader("📣 Manual Notification")

    msg = st.text_input("Message", "Manual operator notification.")
    severity = st.selectbox("Severity", ["INFO", "WARNING", "CRITICAL"])

    if st.button("Send Manual Notification"):
        delivered = send_v37_notification(msg, severity)
        _log_override_event("MANUAL_NOTIFICATION", {"msg": msg, "severity": severity})
        st.success(f"Delivered via: {delivered}")

    # --- OVERRIDE LOG ---
    st.subheader("📜 Override Log")
    st.json(st.session_state.get("v37_override_log", []))

    # --- EXPORT ---
    st.session_state["v37_manual_override_export"] = {
        "override_log": st.session_state.get("v37_override_log", []),
        "override_ready": True
    }

    themed_card_container()
    st.markdown("### Manual Override Export Object")
    st.json(st.session_state["v37_manual_override_export"])

    st.success("V37 Manual Override Panel complete.")
# ------------- CHUNK 249: V37 SYSTEM RESET & RECOVERY ENGINE (FULL SYSTEM RECOVERY LAYER) -------------

import datetime

def _log_recovery_event(event, details):
    """
    Append a recovery event to the recovery log.
    """

    if "v37_recovery_log" not in st.session_state:
        st.session_state["v37_recovery_log"] = []

    st.session_state["v37_recovery_log"].append({
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "event": event,
        "details": details
    })


# ---------------- RESET HELPERS ---------------- #

def _soft_reset():
    """
    Soft reset:
    - Clears agent mode
    - Clears last actions
    - Clears unsafe cycle counters
    - Leaves logs intact
    """

    if "v37_agent_state" in st.session_state:
        st.session_state["v37_agent_state"].update({
            "agent_mode": "IDLE",
            "last_action": None,
            "halt_triggered": False,
        })

    if "v37_safety_state" in st.session_state:
        st.session_state["v37_safety_state"].update({
            "unsafe_cycles": 0,
            "halt_events": 0,
            "escalation_events": 0,
            "safety_engaged": False,
        })

    _log_recovery_event("SOFT_RESET", {
        "agent_state": st.session_state.get("v37_agent_state"),
        "safety_state": st.session_state.get("v37_safety_state")
    })


def _hard_reset():
    """
    Hard reset:
    - Resets agent state
    - Resets healing state
    - Resets optimization state
    - Resets safety state
    - Disables auto-pilot
    - Leaves logs intact
    """

    st.session_state["v37_agent_state"] = {
        "agent_mode": "IDLE",
        "last_action": None,
        "action_count": 0,
        "escalation_count": 0,
        "halt_triggered": False,
    }

    st.session_state["v37_self_healing_state"] = {
        "volatility_weight": 1.0,
        "alignment_weight": 1.0,
        "meta_confidence_weight": 1.0,
        "alert_threshold": 1.0,
        "long_horizon_stability": 1.0,
    }

    st.session_state["v37_optimization_state"] = {
        "predictive_weight": 1.0,
        "risk_weight": 1.0,
        "opportunity_weight": 1.0,
        "parlay_weight": 1.0,
        "meta_weight": 1.0,
        "volatility_sensitivity": 1.0,
        "alignment_sensitivity": 1.0,
        "confidence_curve": 1.0,
        "stability_curve": 1.0,
    }

    st.session_state["v37_safety_state"] = {
        "safety_engaged": False,
        "unsafe_cycles": 0,
        "max_unsafe_cycles": 5,
        "max_escalations": 3,
        "max_halt_events": 1,
        "last_safety_event": None,
        "halt_events": 0,
        "escalation_events": 0,
    }

    if "v37_autopilot_state" in st.session_state:
        st.session_state["v37_autopilot_state"]["autopilot_active"] = False

    _log_recovery_event("HARD_RESET", {
        "agent_state": st.session_state["v37_agent_state"],
        "healing_state": st.session_state["v37_self_healing_state"],
        "optimization_state": st.session_state["v37_optimization_state"],
        "safety_state": st.session_state["v37_safety_state"],
    })


def _full_system_recovery():
    """
    Full system recovery:
    - Performs hard reset
    - Clears all logs
    - Reinitializes all states
    """

    _hard_reset()

    # Clear logs
    for key in [
        "v37_agent_log",
        "v37_autopilot_log",
        "v37_safety_log",
        "v37_override_log",
        "v37_recovery_log",
        "v37_self_healing_log",
        "v37_optimization_log",
    ]:
        if key in st.session_state:
            st.session_state[key] = []

    _log_recovery_event("FULL_SYSTEM_RECOVERY", {
        "message": "All states and logs cleared. System fully reinitialized."
    })


# ---------------- UI LAYER ---------------- #

def render_v37_system_reset_recovery_engine():
    """
    Full UI for the V37 System Reset & Recovery Engine.
    """

    st.title("🔄 V37 System Reset & Recovery Engine")
    st.caption("Full system reset, recovery, and reinitialization controls.")

    # --- SOFT RESET ---
    st.subheader("🟦 Soft Reset")
    st.write("Resets agent + safety counters without clearing logs.")

    if st.button("Perform Soft Reset"):
        _soft_reset()
        st.success("Soft reset completed.")

    # --- HARD RESET ---
    st.subheader("🟧 Hard Reset")
    st.write("Resets agent, healing, optimization, safety, and disables auto-pilot.")

    if st.button("Perform Hard Reset"):
        _hard_reset()
        st.success("Hard reset completed.")

    # --- FULL SYSTEM RECOVERY ---
    st.subheader("🟥 Full System Recovery")
    st.write("Full reinitialization. Clears all logs and resets all states.")

    if st.button("Perform Full System Recovery"):
        _full_system_recovery()
        st.error("Full system recovery completed. All logs cleared.")

    # --- RECOVERY LOG ---
    st.subheader("📜 Recovery Log")
    st.json(st.session_state.get("v37_recovery_log", []))

    # --- EXPORT ---
    st.session_state["v37_system_recovery_export"] = {
        "recovery_log": st.session_state.get("v37_recovery_log", []),
        "recovery_ready": True
    }

    themed_card_container()
    st.markdown("### System Recovery Export Object")
    st.json(st.session_state["v37_system_recovery_export"])

    st.success("V37 System Reset & Recovery Engine complete.")
# ------------- CHUNK 250: V37 FINAL INTEGRATION LAYER (UNIFIED NAVIGATION + FULL INTEGRATION) -------------

def render_v37_final_integration_layer():
    """
    The master integration layer that connects all V37 modules into a unified system.
    Provides:
    - Unified navigation
    - Page routing
    - Full system integration
    """

    st.title("🧩 V37 Final Integration Layer")
    st.caption("Unified navigation and full system integration for all V37 modules.")

    st.markdown("### Select a V37 Module")

    page = st.selectbox(
        "Choose a module to view:",
        [
            "Master Engine",
            "Final Decision Engine",
            "System Monitor",
            "Meta-Brain",
            "Alerts Engine",
            "Memory Engine",
            "Memory Insights",
            "Engine Scheduler",
            "Orchestrator",
            "Notification Engine",
            "Operator Console 2.0",
            "System Summary 2.0",
            "Meta-Diagnostics Engine",
            "Self-Healing Engine",
            "Adaptive Optimization Engine",
            "Autonomous Agent Layer",
            "Autonomous Agent Dashboard",
            "Full Auto-Pilot Mode",
            "Auto-Pilot Safety Layer",
            "Manual Override Panel",
            "System Reset & Recovery Engine",
        ]
    )

    # ROUTING
    if page == "Master Engine":
        render_v37_master_engine()

    elif page == "Final Decision Engine":
        render_v37_final_decision_engine()

    elif page == "System Monitor":
        render_v37_system_monitor()

    elif page == "Meta-Brain":
        render_v37_meta_brain()

    elif page == "Alerts Engine":
        render_v37_alerts_engine()

    elif page == "Memory Engine":
        render_v37_memory_engine()

    elif page == "Memory Insights":
        render_v37_memory_insights_engine()

    elif page == "Engine Scheduler":
        render_v37_engine_scheduler()

    elif page == "Orchestrator":
        render_v37_orchestrator()

    elif page == "Notification Engine":
        render_v37_notification_engine()

    elif page == "Operator Console 2.0":
        render_v37_operator_console_v2()

    elif page == "System Summary 2.0":
        render_v37_system_summary_engine_v2()

    elif page == "Meta-Diagnostics Engine":
        render_v37_meta_diagnostics_engine()

    elif page == "Self-Healing Engine":
        render_v37_self_healing_engine()

    elif page == "Adaptive Optimization Engine":
        render_v37_adaptive_optimization_engine()

    elif page == "Autonomous Agent Layer":
        render_v37_autonomous_agent_layer()

    elif page == "Autonomous Agent Dashboard":
        render_v37_autonomous_agent_dashboard()

    elif page == "Full Auto-Pilot Mode":
        render_v37_full_autopilot_mode()

    elif page == "Auto-Pilot Safety Layer":
        render_v37_autopilot_safety_layer()

    elif page == "Manual Override Panel":
        render_v37_manual_override_panel()

    elif page == "System Reset & Recovery Engine":
        render_v37_system_reset_recovery_engine()

    # EXPORT
    st.session_state["v37_final_integration_export"] = {
        "navigation_ready": True,
        "modules_registered": True,
        "integration_complete": True
    }

    themed_card_container()
    st.markdown("### Final Integration Export Object")
    st.json(st.session_state["v37_final_integration_export"])

    st.success("V37 Final Integration Layer loaded.")
# ------------- CHUNK 251: V37 PERFORMANCE MONITOR 2.0 (REAL-TIME METRICS + VISUALIZATION) -------------

import pandas as pd
import plotly.express as px
import datetime

def _default_performance_state():
    return {
        "performance_snapshots": [],
        "snapshot_limit": 200,
    }


def _capture_performance_snapshot():
    """
    Capture a real-time snapshot of system performance.
    """

    master = st.session_state.get("v37_master_export", {})
    final = st.session_state.get("v37_final_decision_export", {})
    monitor = st.session_state.get("v37_system_monitor_export", {})
    meta = st.session_state.get("v37_meta_brain_export", {})
    healing = st.session_state.get("v37_self_healing_export", {}).get("healing_state", {})
    opt = st.session_state.get("v37_adaptive_optimization_export", {}).get("optimization_state", {})
    agent = st.session_state.get("v37_agent_state", {})

    snapshot = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "master_score": master.get("v37_master_score"),
        "final_score": final.get("v37_final_score"),
        "health_score": monitor.get("system_health_score"),
        "meta_confidence": meta.get("meta_confidence"),
        "volatility_weight": healing.get("volatility_weight"),
        "alignment_weight": healing.get("alignment_weight"),
        "meta_weight": opt.get("meta_weight"),
        "agent_mode": agent.get("agent_mode"),
    }

    return snapshot


def _append_snapshot(perf_state, snapshot):
    """
    Append snapshot to performance state with limit.
    """

    perf_state["performance_snapshots"].append(snapshot)

    # Enforce limit
    if len(perf_state["performance_snapshots"]) > perf_state["snapshot_limit"]:
        perf_state["performance_snapshots"] = perf_state["performance_snapshots"][-perf_state["snapshot_limit"]:]

    return perf_state


def _snapshots_to_dataframe(perf_state):
    """
    Convert snapshots to DataFrame for visualization.
    """

    if not perf_state["performance_snapshots"]:
        return pd.DataFrame([])

    df = pd.DataFrame(perf_state["performance_snapshots"])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def render_v37_performance_monitor_v2():
    """
    Full UI for the V37 Performance Monitor 2.0.
    """

    st.title("📊 V37 Performance Monitor 2.0")
    st.caption("Real-time engine performance, stability metrics, and autonomous behavior analytics.")

    # Load or initialize performance state
    perf_state = st.session_state.get("v37_performance_state", _default_performance_state())

    # Capture new snapshot
    snapshot = _capture_performance_snapshot()
    perf_state = _append_snapshot(perf_state, snapshot)
    st.session_state["v37_performance_state"] = perf_state

    # Convert to DataFrame
    df = _snapshots_to_dataframe(perf_state)

    # --- RAW SNAPSHOT ---
    st.subheader("🧩 Latest Performance Snapshot")
    themed_card_container()
    st.json(snapshot)

    if df.empty:
        st.info("No performance data available yet.")
        return

    # --- MASTER SCORE TREND ---
    st.subheader("🏆 Master Score Trend")
    fig = px.line(df, x="timestamp", y="master_score", title="Master Engine Score Over Time")
    st.plotly_chart(fig, use_container_width=True)

    # --- FINAL SCORE TREND ---
    st.subheader("🎯 Final Decision Score Trend")
    fig = px.line(df, x="timestamp", y="final_score", title="Final Decision Score Over Time")
    st.plotly_chart(fig, use_container_width=True)

    # --- SYSTEM HEALTH TREND ---
    st.subheader("🩺 System Health Trend")
    fig = px.line(df, x="timestamp", y="health_score", title="System Health Score Over Time")
    st.plotly_chart(fig, use_container_width=True)

    # --- META CONFIDENCE TREND ---
    st.subheader("🧬 Meta-Brain Confidence Trend")
    fig = px.line(df, x="timestamp", y="meta_confidence", title="Meta Confidence Over Time")
    st.plotly_chart(fig, use_container_width=True)

    # --- HEALING + OPTIMIZATION TRENDS ---
    st.subheader("🛠️ Healing & Optimization Trends")
    fig = px.line(
        df,
        x="timestamp",
        y=["volatility_weight", "alignment_weight", "meta_weight"],
        title="Healing & Optimization Weights Over Time"
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- AGENT MODE TIMELINE ---
    st.subheader("🤖 Agent Mode Timeline")
    fig = px.scatter(
        df,
        x="timestamp",
        y="agent_mode",
        color="agent_mode",
        title="Agent Mode Over Time",
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- EXPORT ---
    st.session_state["v37_performance_monitor_export"] = {
        "snapshot_count": len(perf_state["performance_snapshots"]),
        "latest_snapshot": snapshot,
        "monitor_ready": True
    }

    themed_card_container()
    st.markdown("### Performance Monitor Export Object")
    st.json(st.session_state["v37_performance_monitor_export"])

    st.success("V37 Performance Monitor 2.0 loaded.")
# ------------- CHUNK 252: V37 ENGINE HEATMAP 2.0 (STABILITY MAP + CORRELATION GRID) -------------

import pandas as pd
import numpy as np
import plotly.express as px

def _collect_heatmap_metrics():
    """
    Collects the latest metrics needed for heatmap generation.
    """

    master = st.session_state.get("v37_master_export", {})
    final = st.session_state.get("v37_final_decision_export", {})
    monitor = st.session_state.get("v37_system_monitor_export", {})
    meta = st.session_state.get("v37_meta_brain_export", {})
    healing = st.session_state.get("v37_self_healing_export", {}).get("healing_state", {})
    opt = st.session_state.get("v37_adaptive_optimization_export", {}).get("optimization_state", {})

    return {
        "Master Score": master.get("v37_master_score"),
        "Final Score": final.get("v37_final_score"),
        "Health Score": monitor.get("system_health_score"),
        "Meta Confidence": meta.get("meta_confidence"),
        "Volatility Weight": healing.get("volatility_weight"),
        "Alignment Weight": healing.get("alignment_weight"),
        "Meta Weight": opt.get("meta_weight"),
        "Stability Curve": opt.get("stability_curve"),
    }


def _build_heatmap_dataframe(metrics):
    """
    Converts metrics into a DataFrame suitable for correlation heatmaps.
    """

    df = pd.DataFrame([metrics])
    return df.corr()


def render_v37_engine_heatmap_v2():
    """
    Full UI for the V37 Engine Heatmap 2.0.
    """

    st.title("🔥 V37 Engine Heatmap 2.0")
    st.caption("Visual stability map, engine correlation grid, and anomaly detection.")

    # Collect metrics
    metrics = _collect_heatmap_metrics()

    st.subheader("📊 Latest Metrics")
    themed_card_container()
    st.json(metrics)

    # Build correlation matrix
    corr_df = _build_heatmap_dataframe(metrics)

    if corr_df.empty:
        st.info("Not enough data to generate heatmap yet.")
        return

    # --- CORRELATION HEATMAP ---
    st.subheader("🧩 Engine Correlation Heatmap")
    fig = px.imshow(
        corr_df,
        text_auto=True,
        color_continuous_scale="RdBu",
        title="Engine Correlation Matrix"
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- STABILITY HEATMAP ---
    st.subheader("🟩 Stability Heatmap")

    stability_matrix = pd.DataFrame({
        "Engine": list(metrics.keys()),
        "Stability": [
            metrics["Master Score"],
            metrics["Final Score"],
            metrics["Health Score"],
            metrics["Meta Confidence"],
            1 - abs(1 - metrics["Volatility Weight"]),
            1 - abs(1 - metrics["Alignment Weight"]),
            metrics["Meta Weight"],
            metrics["Stability Curve"],
        ]
    })

    fig = px.imshow(
        stability_matrix[["Stability"]].T,
        labels=dict(x="Engine", y="Metric"),
        x=stability_matrix["Engine"],
        color_continuous_scale="Greens",
        title="Engine Stability Map"
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- ANOMALY DETECTION ---
    st.subheader("⚠️ Anomaly Detection")

    anomalies = []
    for key, value in metrics.items():
        if value is None:
            continue
        if value < 0.25:
            anomalies.append(f"{key}: CRITICAL LOW")
        elif value < 0.45:
            anomalies.append(f"{key}: LOW")
        elif value > 1.75:
            anomalies.append(f"{key}: ABNORMALLY HIGH")

    if anomalies:
        st.error("Anomalies detected:")
        st.json(anomalies)
    else:
        st.success("No anomalies detected.")

    # --- EXPORT ---
    st.session_state["v37_engine_heatmap_export"] = {
        "correlation_matrix": corr_df.to_dict(),
        "anomalies": anomalies,
        "heatmap_ready": True
    }

    themed_card_container()
    st.markdown("### Engine Heatmap Export Object")
    st.json(st.session_state["v37_engine_heatmap_export"])

    st.success("V37 Engine Heatmap 2.0 loaded.")
# ------------- CHUNK 253: V37 BEHAVIOR REPLAY ENGINE (TIMELINE RECONSTRUCTION + PLAYBACK) -------------

import pandas as pd
import plotly.express as px

def _collect_replay_logs():
    """
    Collect all logs relevant to replay:
    - Agent log
    - Auto-pilot log
    - Safety log
    - Healing log
    - Optimization log
    """

    return {
        "agent": st.session_state.get("v37_agent_log", []),
        "autopilot": st.session_state.get("v37_autopilot_log", []),
        "safety": st.session_state.get("v37_safety_log", []),
        "healing": st.session_state.get("v37_self_healing_log", []),
        "optimization": st.session_state.get("v37_optimization_log", []),
    }


def _merge_logs_for_timeline(logs):
    """
    Merge all logs into a single timeline DataFrame.
    """

    rows = []

    for log_type, entries in logs.items():
        for entry in entries:
            rows.append({
                "timestamp": entry["timestamp"],
                "type": log_type.upper(),
                "event": entry.get("action") or entry.get("event"),
                "details": str(entry.get("details")),
            })

    if not rows:
        return pd.DataFrame([])

    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp")
    return df


def render_v37_behavior_replay_engine():
    """
    Full UI for the V37 Behavior Replay Engine.
    """

    st.title("🎞️ V37 Behavior Replay Engine")
    st.caption("Replay past autonomous cycles, actions, and system behavior.")

    # Collect logs
    logs = _collect_replay_logs()

    st.subheader("📦 Collected Logs")
    themed_card_container()
    st.json({k: len(v) for k, v in logs.items()})

    # Merge into timeline
    df = _merge_logs_for_timeline(logs)

    if df.empty:
        st.info("No behavior logs available yet.")
        return

    # --- TIMELINE SCRUBBER ---
    st.subheader("🕒 Timeline Scrubber")

    timestamps = df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S").tolist()
    selected = st.select_slider("Select a point in time", options=timestamps)

    selected_ts = pd.to_datetime(selected)
    replay_df = df[df["timestamp"] <= selected_ts]

    st.markdown(f"### Events up to: **{selected}**")
    st.json(replay_df.tail(10).to_dict(orient="records"))

    # --- FULL TIMELINE VISUALIZATION ---
    st.subheader("📈 Behavior Timeline")
    fig = px.scatter(
        df,
        x="timestamp",
        y="type",
        color="type",
        hover_data=["event", "details"],
        title="V37 Behavior Timeline",
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- EVENT FREQUENCY ---
    st.subheader("📊 Event Frequency")
    freq = df["type"].value_counts().reset_index()
    freq.columns = ["Event Type", "Count"]

    fig = px.bar(
        freq,
        x="Event Type",
        y="Count",
        title="Event Frequency by Type",
        color="Event Type"
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- ANOMALY MARKERS ---
    st.subheader("⚠️ Anomaly Markers")

    anomalies = df[df["event"].str.contains("HALT|ESCALATION|CRITICAL", case=False, na=False)]

    if anomalies.empty:
        st.success("No anomalies detected in replay timeline.")
    else:
        st.error("Anomalies detected:")
        st.json(anomalies.to_dict(orient="records"))

    # --- EXPORT ---
    st.session_state["v37_behavior_replay_export"] = {
        "timeline_length": len(df),
        "anomaly_count": len(anomalies),
        "replay_ready": True
    }

    themed_card_container()
    st.markdown("### Behavior Replay Export Object")
    st.json(st.session_state["v37_behavior_replay_export"])

    st.success("V37 Behavior Replay Engine loaded.")
# ------------- CHUNK 254: V37 AUTONOMOUS STRATEGY ENGINE (HIGH-LEVEL PLANNING) -------------

import datetime

def _default_strategy_state():
    return {
        "current_strategy": "NEUTRAL",  # NEUTRAL, AGGRESSIVE, DEFENSIVE, RECOVERY, OBSERVATION
        "last_update": None,
        "strategy_log": [],
    }


def _log_strategy_event(strategy_state, strategy, reason):
    """
    Append a strategy decision to the strategy log.
    """

    entry = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "strategy": strategy,
        "reason": reason
    }

    strategy_state["strategy_log"].append(entry)
    return strategy_state


def _determine_strategy(diagnostics, healing_state, opt_state, agent_state):
    """
    Determine the best high-level strategy based on system conditions.
    """

    # Critical → RECOVERY
    if (
        "critical" in diagnostics["health"].lower()
        or agent_state.get("agent_mode") == "HALT"
        or healing_state["volatility_weight"] < 0.6
    ):
        return "RECOVERY", "Critical system conditions detected."

    # High alert → DEFENSIVE
    if (
        "high" in diagnostics["alerts"].lower()
        or agent_state.get("agent_mode") == "ESCALATING"
    ):
        return "DEFENSIVE", "High alert activity or instability detected."

    # Strong stability → AGGRESSIVE
    if (
        "stable" in diagnostics["master"].lower()
        and "stable" in diagnostics["health"].lower()
        and "stable" in diagnostics["meta"].lower()
        and opt_state["confidence_curve"] > 1.1
    ):
        return "AGGRESSIVE", "System stability high and confidence strong."

    # Moderate uncertainty → OBSERVATION
    if (
        "moderate" in diagnostics["meta"].lower()
        or "moderate" in diagnostics["health"].lower()
    ):
        return "OBSERVATION", "Moderate uncertainty detected."

    # Default
    return "NEUTRAL", "No strong strategic signal detected."


def _apply_strategy_effects(strategy, healing_state, opt_state):
    """
    Adjust engine weights based on chosen strategy.
    """

    if strategy == "AGGRESSIVE":
        opt_state["opportunity_weight"] *= 1.15
        opt_state["confidence_curve"] *= 1.10

    elif strategy == "DEFENSIVE":
        healing_state["volatility_weight"] *= 0.85
        healing_state["alignment_weight"] *= 1.10
        opt_state["risk_weight"] *= 1.20

    elif strategy == "RECOVERY":
        healing_state["long_horizon_stability"] *= 1.25
        healing_state["alignment_weight"] *= 1.20
        opt_state["stability_curve"] *= 1.30

    elif strategy == "OBSERVATION":
        healing_state["meta_confidence_weight"] *= 1.05

    # NEUTRAL → no changes

    return healing_state, opt_state


def render_v37_autonomous_strategy_engine():
    """
    Full UI for the V37 Autonomous Strategy Engine.
    """

    st.title("🧭 V37 Autonomous Strategy Engine")
    st.caption("High-level planning and strategic behavior for autonomous operation.")

    diagnostics = st.session_state.get("v37_meta_diagnostics_export", {}).get("diagnostics")
    healing_state = st.session_state.get("v37_self_healing_export", {}).get("healing_state")
    opt_state = st.session_state.get("v37_adaptive_optimization_export", {}).get("optimization_state")
    agent_state = st.session_state.get("v37_agent_state")

    if not diagnostics or not healing_state or not opt_state or not agent_state:
        st.warning("Required system states not available yet.")
        return

    # Load or initialize strategy state
    strategy_state = st.session_state.get("v37_strategy_state", _default_strategy_state())

    # Determine strategy
    strategy, reason = _determine_strategy(diagnostics, healing_state, opt_state, agent_state)

    # Apply strategy effects
    healing_state, opt_state = _apply_strategy_effects(strategy, healing_state, opt_state)

    # Update state
    strategy_state["current_strategy"] = strategy
    strategy_state["last_update"] = datetime.datetime.utcnow().isoformat()
    strategy_state = _log_strategy_event(strategy_state, strategy, reason)

    st.session_state["v37_strategy_state"] = strategy_state
    st.session_state["v37_self_healing_state"] = healing_state
    st.session_state["v37_optimization_state"] = opt_state

    # --- RENDER ---
    themed_card_container()
    st.markdown("## Current Strategy")
    st.json({
        "strategy": strategy,
        "reason": reason,
        "last_update": strategy_state["last_update"]
    })

    st.subheader("📜 Strategy Log")
    st.json(strategy_state["strategy_log"][-20:])

    # --- EXPORT ---
    st.session_state["v37_strategy_export"] = {
        "current_strategy": strategy,
        "log": strategy_state["strategy_log"],
        "strategy_ready": True
    }

    themed_card_container()
    st.markdown("### Strategy Export Object")
    st.json(st.session_state["v37_strategy_export"])

    st.success("V37 Autonomous Strategy Engine complete.")
# ------------- CHUNK 255: V37 OPERATOR AI ASSISTANT (CONVERSATIONAL CONTROL INTERFACE) -------------

import datetime

def _default_operator_assistant_state():
    return {
        "interaction_log": [],
        "last_response": None,
    }


def _log_operator_interaction(query, response):
    """
    Log operator queries and assistant responses.
    """

    if "v37_operator_assistant_state" not in st.session_state:
        st.session_state["v37_operator_assistant_state"] = _default_operator_assistant_state()

    st.session_state["v37_operator_assistant_state"]["interaction_log"].append({
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "query": query,
        "response": response
    })


def _interpret_operator_query(query):
    """
    Interpret operator intent and route to appropriate module.
    """

    q = query.lower()

    # --- SYSTEM SUMMARIES ---
    if "summary" in q or "status" in q:
        return "SYSTEM_SUMMARY"

    # --- PERFORMANCE ---
    if "performance" in q or "scores" in q:
        return "PERFORMANCE"

    # --- STRATEGY ---
    if "strategy" in q:
        return "STRATEGY"

    # --- AGENT ---
    if "agent" in q or "mode" in q:
        return "AGENT"

    # --- AUTOPILOT ---
    if "autopilot" in q or "auto-pilot" in q:
        return "AUTOPILOT"

    # --- SAFETY ---
    if "safety" in q or "unsafe" in q:
        return "SAFETY"

    # --- RESET ---
    if "reset" in q or "recover" in q:
        return "RESET"

    # --- HEALING / OPTIMIZATION ---
    if "healing" in q or "optimiz" in q:
        return "HEALING_OPT"

    # --- DEFAULT ---
    return "UNKNOWN"


def _generate_operator_response(intent):
    """
    Generate a response based on interpreted intent.
    """

    if intent == "SYSTEM_SUMMARY":
        return st.session_state.get("v37_system_summary_export", {})

    if intent == "PERFORMANCE":
        return st.session_state.get("v37_performance_monitor_export", {})

    if intent == "STRATEGY":
        return st.session_state.get("v37_strategy_export", {})

    if intent == "AGENT":
        return st.session_state.get("v37_agent_state", {})

    if intent == "AUTOPILOT":
        return st.session_state.get("v37_full_autopilot_export", {})

    if intent == "SAFETY":
        return st.session_state.get("v37_autopilot_safety_export", {})

    if intent == "RESET":
        return st.session_state.get("v37_system_recovery_export", {})

    if intent == "HEALING_OPT":
        return {
            "healing": st.session_state.get("v37_self_healing_export", {}),
            "optimization": st.session_state.get("v37_adaptive_optimization_export", {})
        }

    return {"message": "I didn't understand that request. Try asking about system status, performance, strategy, agent mode, safety, or auto-pilot."}


def render_v37_operator_ai_assistant():
    """
    Full UI for the V37 Operator AI Assistant.
    Conversational control interface for the entire V37 system.
    """

    st.title("V37 Operator AI Assistant")
    st.caption("Conversational control interface for the entire V37 system.")

    # Load or initialize state
    if "v37_operator_assistant_state" not in st.session_state:
        st.session_state["v37_operator_assistant_state"] = _default_operator_assistant_state()

    # --- INPUT ---
    query = st.text_input("Ask the system anything:", "")

    if query:
        intent = _interpret_operator_query(query)
        response = _generate_operator_response(intent)

        _log_operator_interaction(query, response)

        st.subheader("Assistant Response")
        themed_card_container()
        st.json(response)

    # --- LOG ---
    st.subheader("Interaction Log")
    st.json(st.session_state["v37_operator_assistant_state"]["interaction_log"][-20:])

    # --- EXPORT ---
    st.session_state["v37_operator_assistant_export"] = {
        "interaction_log": st.session_state["v37_operator_assistant_state"]["interaction_log"],
        "assistant_ready": True
    }

    themed_card_container()
    st.markdown("### Operator Assistant Export Object")
    st.json(st.session_state["v37_operator_assistant_export"])

    st.success("V37 Operator AI Assistant loaded.")
