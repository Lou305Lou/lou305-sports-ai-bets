
"""
V31: CLV Tracking Engine (Critical Edge)
=======================================

Purpose
-------
Drop-in module for your Sports Betting AI Dashboard that adds:
1) Opening / current / closing line tracking
2) Bet-level CLV scoring
3) CLV hit-rate metrics
4) Snapshot history logging
5) Streamlit-ready summary helpers

How to integrate
----------------
1) Save this file as: v31_clv_engine.py
2) Import in your main app:
       from v31_clv_engine import (
           ensure_clv_columns,
           append_market_snapshot,
           update_bet_log_with_closing_lines,
           compute_bet_clv,
           build_clv_dashboard_metrics,
           build_clv_detail_table,
           render_clv_streamlit_section,
       )

3) When you have your live scored rows dataframe (example: scored_df), call:
       append_market_snapshot(scored_df, "market_snapshots.csv")

4) Before rendering Bet Log + Grading, call:
       bet_log_df = ensure_clv_columns(bet_log_df)
       bet_log_df = update_bet_log_with_closing_lines(
           bet_log_df=bet_log_df,
           snapshots_path="market_snapshots.csv",
       )
       bet_log_df = compute_bet_clv(bet_log_df)

5) Save bet_log_df back to CSV after updates.

Expected columns in bet_log_df
------------------------------
Recommended minimum:
- timestamp
- game
- market
- selection
- line
- book
- odds
- previous_odds
- result

Expected columns in scored_df / live rows
-----------------------------------------
Recommended minimum:
- game
- market
- selection
- line
- book
- odds

Notes
-----
- Moneyline CLV uses odds / implied-prob movement.
- Spread / total CLV uses both line movement and odds movement.
- Positive CLV means your number beat the market close.
- This module is defensive and will create missing columns when possible.
"""

from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------
# Column / schema helpers
# ---------------------------------------------------------------------

REQUIRED_CLV_COLUMNS = [
    "bet_odds",
    "opening_odds",
    "closing_odds",
    "bet_line_value",
    "opening_line_value",
    "closing_line_value",
    "clv_points",
    "clv_odds_delta",
    "clv_implied_prob_delta",
    "clv_score",
    "clv_result",
    "clv_hit",
    "clv_market_key",
    "closing_timestamp",
]


def ensure_clv_columns(df: Optional[pd.DataFrame]) -> pd.DataFrame:
    if df is None or len(df) == 0:
        df = pd.DataFrame()

    df = df.copy()

    for col in REQUIRED_CLV_COLUMNS:
        if col not in df.columns:
            df[col] = np.nan

    if "odds" in df.columns and "bet_odds" in df.columns:
        missing_mask = df["bet_odds"].isna()
        df.loc[missing_mask, "bet_odds"] = pd.to_numeric(df.loc[missing_mask, "odds"], errors="coerce")

    if "line" in df.columns and "bet_line_value" in df.columns:
        line_numeric = pd.to_numeric(df["line"], errors="coerce")
        missing_mask = df["bet_line_value"].isna()
        df.loc[missing_mask, "bet_line_value"] = line_numeric[missing_mask]

    return df


# ---------------------------------------------------------------------
# Parsing / normalization
# ---------------------------------------------------------------------

def safe_str(x: Any) -> str:
    if pd.isna(x):
        return ""
    return str(x).strip()


def normalize_text(x: Any) -> str:
    s = safe_str(x).lower()
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def normalize_game(game: Any) -> str:
    s = normalize_text(game)
    s = s.replace(" at ", " vs ")
    s = s.replace("@", " vs ")
    s = re.sub(r"\s+vs\s+", " vs ", s)
    return s


def parse_timestamp(value: Any) -> pd.Timestamp:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return pd.NaT
    try:
        return pd.to_datetime(value, errors="coerce", utc=False)
    except Exception:
        return pd.NaT


def extract_selection_side(selection: Any, market: Any) -> str:
    sel = normalize_text(selection)
    mkt = normalize_text(market)

    if mkt == "total":
        if sel.startswith("over"):
            return "over"
        if sel.startswith("under"):
            return "under"

    # Spread or moneyline team side
    # Strip trailing line like "celtics -5.5"
    team = re.sub(r"\s*[+-]?\d+(\.\d+)?\s*$", "", sel).strip()
    return team


def extract_numeric_line(selection: Any, line: Any) -> float:
    # Prefer provided line column
    line_num = pd.to_numeric(pd.Series([line]), errors="coerce").iloc[0]
    if pd.notna(line_num):
        return float(line_num)

    sel = safe_str(selection)
    match = re.search(r"([+-]?\d+(?:\.\d+)?)\s*$", sel)
    if match:
        try:
            return float(match.group(1))
        except Exception:
            pass
    return np.nan


def build_market_key(game: Any, market: Any, selection: Any) -> str:
    game_n = normalize_game(game)
    market_n = normalize_text(market)
    side_n = extract_selection_side(selection, market)
    return f"{game_n}|{market_n}|{side_n}"


# ---------------------------------------------------------------------
# Odds helpers
# ---------------------------------------------------------------------

def american_to_implied_prob(odds: Any) -> float:
    odds = pd.to_numeric(pd.Series([odds]), errors="coerce").iloc[0]
    if pd.isna(odds) or odds == 0:
        return np.nan

    odds = float(odds)
    if odds > 0:
        return 100.0 / (odds + 100.0)
    return abs(odds) / (abs(odds) + 100.0)


def american_delta_for_bettor(bet_odds: Any, closing_odds: Any) -> float:
    """
    Positive means bettor beat the close.
    Example:
    -110 bet vs -125 close => positive
    +120 bet vs +105 close => positive
    """
    bet = pd.to_numeric(pd.Series([bet_odds]), errors="coerce").iloc[0]
    close = pd.to_numeric(pd.Series([closing_odds]), errors="coerce").iloc[0]
    if pd.isna(bet) or pd.isna(close):
        return np.nan

    bet = float(bet)
    close = float(close)

    # Convert to fair "bettor advantage" scale using implied probability
    bet_ip = american_to_implied_prob(bet)
    close_ip = american_to_implied_prob(close)
    if pd.isna(bet_ip) or pd.isna(close_ip):
        return np.nan

    # Positive if closing implied probability is higher than your bet implied probability
    return close_ip - bet_ip


# ---------------------------------------------------------------------
# CLV calculations
# ---------------------------------------------------------------------

def line_clv_points(
    market: Any,
    selection: Any,
    bet_line: Any,
    closing_line: Any,
) -> float:
    """
    Positive means bettor got the better number.
    Moneyline returns NaN because point-based CLV doesn't apply there.
    """
    mkt = normalize_text(market)
    bet_line = pd.to_numeric(pd.Series([bet_line]), errors="coerce").iloc[0]
    closing_line = pd.to_numeric(pd.Series([closing_line]), errors="coerce").iloc[0]

    if mkt not in {"spread", "total"}:
        return np.nan
    if pd.isna(bet_line) or pd.isna(closing_line):
        return np.nan

    bet_line = float(bet_line)
    closing_line = float(closing_line)
    side = extract_selection_side(selection, market)

    if mkt == "total":
        # Over wants a lower number; Under wants a higher number
        if side == "over":
            return closing_line - bet_line
        if side == "under":
            return bet_line - closing_line
        return np.nan

    if mkt == "spread":
        # Team -5.5 is better than -6.5 => closing -6.5 means +1.0 CLV
        # Team +5.5 is better than +4.5 => closing +4.5 means +1.0 CLV
        # Use sign of the selected team spread if available.
        if bet_line < 0:
            return bet_line - closing_line
        return closing_line - bet_line

    return np.nan


def compute_single_row_clv(row: pd.Series) -> Dict[str, Any]:
    bet_odds = row.get("bet_odds", row.get("odds", np.nan))
    closing_odds = row.get("closing_odds", np.nan)
    bet_line = row.get("bet_line_value", row.get("line", np.nan))
    closing_line = row.get("closing_line_value", np.nan)
    market = row.get("market", "")
    selection = row.get("selection", "")

    clv_points = line_clv_points(market, selection, bet_line, closing_line)
    clv_ip_delta = american_delta_for_bettor(bet_odds, closing_odds)

    # Human-readable odds delta. Positive = bettor beat close
    bet_num = pd.to_numeric(pd.Series([bet_odds]), errors="coerce").iloc[0]
    close_num = pd.to_numeric(pd.Series([closing_odds]), errors="coerce").iloc[0]
    if pd.isna(bet_num) or pd.isna(close_num):
        clv_odds_delta = np.nan
    else:
        clv_odds_delta = float(close_num) - float(bet_num)

    # Unified CLV score
    # Spread/total: points drive most of the signal, odds add secondary signal
    # Moneyline: implied probability delta drives the signal
    market_n = normalize_text(market)
    if market_n in {"spread", "total"}:
        points_component = 0.0 if pd.isna(clv_points) else clv_points * 100.0
        odds_component = 0.0 if pd.isna(clv_ip_delta) else clv_ip_delta * 100.0
        clv_score = points_component + odds_component
        clv_result = (
            "positive" if clv_score > 0.01 else
            "negative" if clv_score < -0.01 else
            "push"
        )
    else:
        clv_score = np.nan if pd.isna(clv_ip_delta) else clv_ip_delta * 100.0
        clv_result = (
            "positive" if (pd.notna(clv_score) and clv_score > 0.01) else
            "negative" if (pd.notna(clv_score) and clv_score < -0.01) else
            "push"
        )

    clv_hit = 1 if clv_result == "positive" else 0 if clv_result in {"negative", "push"} else np.nan

    return {
        "clv_points": clv_points,
        "clv_odds_delta": clv_odds_delta,
        "clv_implied_prob_delta": np.nan if pd.isna(clv_ip_delta) else clv_ip_delta * 100.0,
        "clv_score": clv_score,
        "clv_result": clv_result,
        "clv_hit": clv_hit,
    }


def compute_bet_clv(bet_log_df: Optional[pd.DataFrame]) -> pd.DataFrame:
    bet_log_df = ensure_clv_columns(bet_log_df)
    if len(bet_log_df) == 0:
        return bet_log_df

    out_rows = []
    for _, row in bet_log_df.iterrows():
        clv = compute_single_row_clv(row)
        row2 = row.copy()
        for k, v in clv.items():
            row2[k] = v
        out_rows.append(row2)

    return pd.DataFrame(out_rows)


# ---------------------------------------------------------------------
# Market snapshot logging
# ---------------------------------------------------------------------

SNAPSHOT_BASE_COLUMNS = [
    "snapshot_timestamp",
    "game",
    "market",
    "selection",
    "selection_side",
    "line",
    "odds",
    "book",
    "market_key",
]


def prepare_snapshot_df(live_df: Optional[pd.DataFrame]) -> pd.DataFrame:
    if live_df is None or len(live_df) == 0:
        return pd.DataFrame(columns=SNAPSHOT_BASE_COLUMNS)

    df = live_df.copy()

    for col in ["game", "market", "selection", "line", "odds", "book"]:
        if col not in df.columns:
            df[col] = np.nan

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    df["snapshot_timestamp"] = now_str
    df["selection_side"] = df.apply(
        lambda r: extract_selection_side(r.get("selection", ""), r.get("market", "")),
        axis=1,
    )
    df["line"] = pd.to_numeric(df["line"], errors="coerce")
    df["odds"] = pd.to_numeric(df["odds"], errors="coerce")
    df["market_key"] = df.apply(
        lambda r: build_market_key(r.get("game", ""), r.get("market", ""), r.get("selection", "")),
        axis=1,
    )

    keep_cols = SNAPSHOT_BASE_COLUMNS + [c for c in df.columns if c not in SNAPSHOT_BASE_COLUMNS]
    return df[keep_cols]


def append_market_snapshot(live_df: Optional[pd.DataFrame], snapshots_path: str) -> pd.DataFrame:
    snapshot_df = prepare_snapshot_df(live_df)
    if len(snapshot_df) == 0:
        return snapshot_df

    if os.path.exists(snapshots_path):
        try:
            old_df = pd.read_csv(snapshots_path)
            combined = pd.concat([old_df, snapshot_df], ignore_index=True)
        except Exception:
            combined = snapshot_df.copy()
    else:
        combined = snapshot_df.copy()

    combined.to_csv(snapshots_path, index=False)
    return snapshot_df


def load_snapshots(snapshots_path: str) -> pd.DataFrame:
    if not os.path.exists(snapshots_path):
        return pd.DataFrame(columns=SNAPSHOT_BASE_COLUMNS)
    try:
        df = pd.read_csv(snapshots_path)
    except Exception:
        return pd.DataFrame(columns=SNAPSHOT_BASE_COLUMNS)

    for col in ["snapshot_timestamp", "game", "market", "selection", "selection_side", "book", "market_key"]:
        if col not in df.columns:
            df[col] = np.nan

    df["snapshot_timestamp"] = pd.to_datetime(df["snapshot_timestamp"], errors="coerce")
    df["line"] = pd.to_numeric(df.get("line"), errors="coerce")
    df["odds"] = pd.to_numeric(df.get("odds"), errors="coerce")
    return df


# ---------------------------------------------------------------------
# Closing-line assignment
# ---------------------------------------------------------------------

def _match_snapshots_for_bet(bet_row: pd.Series, snapshots_df: pd.DataFrame) -> pd.DataFrame:
    key = build_market_key(
        bet_row.get("game", ""),
        bet_row.get("market", ""),
        bet_row.get("selection", ""),
    )
    subset = snapshots_df[snapshots_df["market_key"] == key].copy()

    bet_ts = parse_timestamp(bet_row.get("timestamp", bet_row.get("placed_at", None)))
    if pd.notna(bet_ts) and "snapshot_timestamp" in subset.columns:
        subset = subset[subset["snapshot_timestamp"] >= bet_ts]

    if len(subset) == 0:
        return subset.sort_values("snapshot_timestamp")

    # Prefer same book when possible
    bet_book = normalize_text(bet_row.get("book", ""))
    if bet_book:
        same_book = subset[subset["book"].fillna("").astype(str).str.lower().str.strip() == bet_book]
        if len(same_book) > 0:
            return same_book.sort_values("snapshot_timestamp")

    return subset.sort_values("snapshot_timestamp")


def update_bet_log_with_closing_lines(
    bet_log_df: Optional[pd.DataFrame],
    snapshots_path: str,
) -> pd.DataFrame:
    bet_log_df = ensure_clv_columns(bet_log_df)
    if len(bet_log_df) == 0:
        return bet_log_df

    snapshots_df = load_snapshots(snapshots_path)
    if len(snapshots_df) == 0:
        # Still populate market key and opening bet values
        bet_log_df["clv_market_key"] = bet_log_df.apply(
            lambda r: build_market_key(r.get("game", ""), r.get("market", ""), r.get("selection", "")),
            axis=1,
        )
        if "bet_odds" in bet_log_df.columns:
            missing_mask = bet_log_df["bet_odds"].isna() & ("odds" in bet_log_df.columns)
            bet_log_df.loc[missing_mask, "bet_odds"] = pd.to_numeric(
                bet_log_df.loc[missing_mask, "odds"], errors="coerce"
            )
        if "bet_line_value" in bet_log_df.columns:
            parsed_lines = bet_log_df.apply(
                lambda r: extract_numeric_line(r.get("selection", ""), r.get("line", np.nan)),
                axis=1,
            )
            missing_mask = bet_log_df["bet_line_value"].isna()
            bet_log_df.loc[missing_mask, "bet_line_value"] = parsed_lines[missing_mask]
        return bet_log_df

    updated_rows = []

    for _, row in bet_log_df.iterrows():
        row2 = row.copy()
        row2["clv_market_key"] = build_market_key(
            row.get("game", ""),
            row.get("market", ""),
            row.get("selection", ""),
        )

        if pd.isna(row2.get("bet_odds", np.nan)):
            row2["bet_odds"] = pd.to_numeric(pd.Series([row.get("odds", np.nan)]), errors="coerce").iloc[0]

        if pd.isna(row2.get("bet_line_value", np.nan)):
            row2["bet_line_value"] = extract_numeric_line(row.get("selection", ""), row.get("line", np.nan))

        matched = _match_snapshots_for_bet(row, snapshots_df)

        if len(matched) > 0:
            open_row = matched.iloc[0]
            close_row = matched.iloc[-1]

            row2["opening_odds"] = open_row.get("odds", np.nan)
            row2["closing_odds"] = close_row.get("odds", np.nan)
            row2["opening_line_value"] = open_row.get("line", np.nan)
            row2["closing_line_value"] = close_row.get("line", np.nan)
            row2["closing_timestamp"] = close_row.get("snapshot_timestamp", pd.NaT)

        updated_rows.append(row2)

    return pd.DataFrame(updated_rows)


# ---------------------------------------------------------------------
# Dashboard metrics
# ---------------------------------------------------------------------

def build_clv_dashboard_metrics(bet_log_df: Optional[pd.DataFrame]) -> Dict[str, Any]:
    bet_log_df = ensure_clv_columns(bet_log_df)
    if len(bet_log_df) == 0:
        return {
            "bets_with_clv": 0,
            "avg_clv_score": np.nan,
            "clv_hit_rate": np.nan,
            "avg_clv_points": np.nan,
            "avg_clv_ip_delta": np.nan,
            "positive_clv_bets": 0,
        }

    df = compute_bet_clv(bet_log_df)

    usable = df[df["clv_result"].notna()].copy()

    if len(usable) == 0:
        return {
            "bets_with_clv": 0,
            "avg_clv_score": np.nan,
            "clv_hit_rate": np.nan,
            "avg_clv_points": np.nan,
            "avg_clv_ip_delta": np.nan,
            "positive_clv_bets": 0,
        }

    return {
        "bets_with_clv": int(len(usable)),
        "avg_clv_score": float(pd.to_numeric(usable["clv_score"], errors="coerce").mean()),
        "clv_hit_rate": float(pd.to_numeric(usable["clv_hit"], errors="coerce").mean() * 100.0),
        "avg_clv_points": float(pd.to_numeric(usable["clv_points"], errors="coerce").mean()),
        "avg_clv_ip_delta": float(pd.to_numeric(usable["clv_implied_prob_delta"], errors="coerce").mean()),
        "positive_clv_bets": int((usable["clv_result"] == "positive").sum()),
    }


def build_clv_detail_table(bet_log_df: Optional[pd.DataFrame]) -> pd.DataFrame:
    bet_log_df = ensure_clv_columns(bet_log_df)
    if len(bet_log_df) == 0:
        return pd.DataFrame(
            columns=[
                "timestamp", "game", "market", "selection",
                "bet_odds", "closing_odds", "bet_line_value", "closing_line_value",
                "clv_points", "clv_implied_prob_delta", "clv_score", "clv_result"
            ]
        )

    df = compute_bet_clv(bet_log_df).copy()

    keep_cols = [
        c for c in [
            "timestamp",
            "game",
            "market",
            "selection",
            "book",
            "bet_odds",
            "closing_odds",
            "bet_line_value",
            "closing_line_value",
            "clv_points",
            "clv_implied_prob_delta",
            "clv_score",
            "clv_result",
            "result",
        ] if c in df.columns
    ]

    df = df[keep_cols].copy()
    if "timestamp" in df.columns:
        df = df.sort_values("timestamp", ascending=False)
    return df


# ---------------------------------------------------------------------
# Streamlit renderer
# ---------------------------------------------------------------------

def fmt_num(x: Any, digits: int = 2, suffix: str = "") -> str:
    x = pd.to_numeric(pd.Series([x]), errors="coerce").iloc[0]
    if pd.isna(x):
        return "—"
    return f"{float(x):.{digits}f}{suffix}"


def render_clv_streamlit_section(st, bet_log_df: Optional[pd.DataFrame]) -> None:
    """
    Usage:
        render_clv_streamlit_section(st, bet_log_df)
    """
    st.markdown("## 📉 Closing Line Value (CLV)")

    metrics = build_clv_dashboard_metrics(bet_log_df)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Bets w/ CLV", metrics["bets_with_clv"])
    c2.metric("CLV Hit Rate", fmt_num(metrics["clv_hit_rate"], 1, "%"))
    c3.metric("Avg CLV Score", fmt_num(metrics["avg_clv_score"], 2))
    c4.metric("Positive CLV Bets", metrics["positive_clv_bets"])

    c5, c6 = st.columns(2)
    c5.metric("Avg Line CLV", fmt_num(metrics["avg_clv_points"], 2))
    c6.metric("Avg Implied Prob Edge", fmt_num(metrics["avg_clv_ip_delta"], 2, "%"))

    detail_df = build_clv_detail_table(bet_log_df)
    st.dataframe(detail_df, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------
# Optional utility: update both CSVs in one call
# ---------------------------------------------------------------------

def run_v31_clv_pipeline(
    live_df: Optional[pd.DataFrame],
    bet_log_df: Optional[pd.DataFrame],
    snapshots_path: str = "market_snapshots.csv",
    save_bet_log_path: Optional[str] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Convenience wrapper.
    Returns:
        updated_bet_log_df, new_snapshot_df
    """
    new_snapshot_df = append_market_snapshot(live_df, snapshots_path)
    updated_bet_log_df = update_bet_log_with_closing_lines(
        bet_log_df=bet_log_df,
        snapshots_path=snapshots_path,
    )
    updated_bet_log_df = compute_bet_clv(updated_bet_log_df)

    if save_bet_log_path:
        updated_bet_log_df.to_csv(save_bet_log_path, index=False)

    return updated_bet_log_df, new_snapshot_df


# ---------------------------------------------------------------------
# Self-test demo
# ---------------------------------------------------------------------

if __name__ == "__main__":
    # Demo live rows
    live_rows = pd.DataFrame([
        {"game": "Nuggets vs Suns", "market": "moneyline", "selection": "Nuggets", "line": np.nan, "book": "DraftKings", "odds": -132},
        {"game": "Celtics vs Heat", "market": "spread", "selection": "Celtics -5.5", "line": -5.5, "book": "FanDuel", "odds": -110},
        {"game": "Celtics vs Heat", "market": "total", "selection": "Under 221.5", "line": 221.5, "book": "Caesars", "odds": -105},
    ])

    bet_log = pd.DataFrame([
        {"timestamp": "2026-03-22 21:37:11", "game": "Nuggets vs Suns", "market": "moneyline", "selection": "Nuggets", "line": np.nan, "book": "DraftKings", "odds": -132, "result": np.nan},
        {"timestamp": "2026-03-22 21:37:11", "game": "Celtics vs Heat", "market": "spread", "selection": "Celtics -5.5", "line": -5.5, "book": "FanDuel", "odds": -110, "result": np.nan},
        {"timestamp": "2026-03-22 21:37:11", "game": "Celtics vs Heat", "market": "total", "selection": "Under 221.5", "line": 221.5, "book": "Caesars", "odds": -105, "result": np.nan},
    ])

    path = "demo_market_snapshots.csv"

    append_market_snapshot(live_rows, path)

    # Simulate later close
    live_rows_2 = live_rows.copy()
    live_rows_2.loc[0, "odds"] = -145
    live_rows_2.loc[1, "line"] = -6.5
    live_rows_2.loc[1, "selection"] = "Celtics -6.5"
    live_rows_2.loc[2, "line"] = 219.5
    live_rows_2.loc[2, "selection"] = "Under 219.5"

    append_market_snapshot(live_rows_2, path)

    out = update_bet_log_with_closing_lines(bet_log, path)
    out = compute_bet_clv(out)

    print(out[[
        "game", "market", "selection", "bet_odds", "closing_odds",
        "bet_line_value", "closing_line_value", "clv_points",
        "clv_implied_prob_delta", "clv_score", "clv_result"
    ]])
