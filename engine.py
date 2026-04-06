#!/usr/bin/env python3
"""
engine.py

Unified engine for:
- Fetching odds from The Odds API (Starter plan)
- Storing all markets (moneyline, spreads, totals, player props) as separate cards
- Filtering cards by odds band (-300 to +150)
- Sending eligible cards to Qwen 3.6 Plus (via OpenRouter) for selection and optional parlays

Secrets expected (Streamlit or environment):
- ODDS_API_KEY        = The Odds API key
- OPENROUTER_API_KEY  = OpenRouter key for Qwen 3.6 Plus
- SPORTDATA_API_KEY   = SportsDataIO key (reserved for future deeper stats use)

This file is designed to be:
- Drop-in
- Safe
- Streamlit-friendly
"""

import os
import sys
import argparse
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional

import requests

# -----------------------------
# Config
# -----------------------------
DB_FILE = "bet_log.db"
TABLE_NAME = "cards"

ODDS_ENV = "ODDS_API_KEY"
OPENROUTER_ENV = "OPENROUTER_API_KEY"
SPORTDATA_ENV = "SPORTDATA_API_KEY"  # not used yet, reserved

# The Odds API base URL (v4)
ODDS_API_BASE = "https://api.the-odds-api.com/v4"

# Sports keys for The Odds API
ODDS_SPORT_KEYS = {
    "NBA": "basketball_nba",
    "MLB": "baseball_mlb",
    "NHL": "ice_hockey_nhl",
}

# Markets we want from The Odds API
ODDS_MARKETS = "h2h,spreads,totals,player_props"
ODDS_REGIONS = "us"
ODDS_FORMAT = "american"

# Qwen / OpenRouter config
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
QWEN_MODEL = "qwen/qwen3.6-plus:free"

# Odds band for eligible cards
MIN_ODDS = -300
MAX_ODDS = 150


# -----------------------------
# Database initialization
# -----------------------------
def init_db() -> None:
    """Create the cards table if it does not exist."""
    conn = sqlite3.connect(DB_FILE)
    try:
        cur = conn.cursor()
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sport TEXT NOT NULL,
                league TEXT,
                event_id TEXT NOT NULL,
                event_time TEXT,
                market_type TEXT NOT NULL,   -- moneyline, spread, total, player_prop
                selection TEXT NOT NULL,     -- team or player + side
                line REAL,                   -- spread/total/prop line if numeric
                odds INTEGER NOT NULL,       -- American odds
                bookmaker TEXT NOT NULL,
                source TEXT NOT NULL,        -- 'the-odds-api'
                created_at TEXT NOT NULL,
                UNIQUE(sport, league, event_id, market_type, selection, line, odds, bookmaker, source)
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


# -----------------------------
# Helpers for secrets
# -----------------------------
def get_odds_key() -> str:
    key = os.getenv(ODDS_ENV)
    if not key:
        raise RuntimeError(
            f"{ODDS_ENV} is not set. Add it to Streamlit secrets or environment."
        )
    return key


def get_openrouter_key() -> str:
    key = os.getenv(OPENROUTER_ENV)
    if not key:
        raise RuntimeError(
            f"{OPENROUTER_ENV} is not set. Add it to Streamlit secrets or environment."
        )
    return key


# -----------------------------
# Fetch from The Odds API
# -----------------------------
def fetch_odds_for_sport(sport_label: str) -> List[Dict[str, Any]]:
    """
    Fetch odds for a given sport from The Odds API.

    sport_label: "NBA", "MLB", "NHL"
    """
    api_key = get_odds_key()
    sport_key = ODDS_SPORT_KEYS.get(sport_label)
    if not sport_key:
        print(f"[{sport_label}] No Odds API sport key configured.")
        return []

    url = f"{ODDS_API_BASE}/sports/{sport_key}/odds"
    params = {
        "apiKey": api_key,
        "regions": ODDS_REGIONS,
        "markets": ODDS_MARKETS,
        "oddsFormat": ODDS_FORMAT,
    }

    try:
        resp = requests.get(url, params=params, timeout=20)
    except Exception as e:
        print(f"[{sport_label}] Error calling The Odds API: {e}")
        return []

    if resp.status_code != 200:
        print(f"[{sport_label}] Non-200 from The Odds API: {resp.status_code} - {resp.text[:200]}")
        return []

    try:
        data = resp.json()
    except Exception as e:
        print(f"[{sport_label}] Failed to parse JSON from The Odds API: {e}")
        return []

    if not isinstance(data, list):
        print(f"[{sport_label}] Expected list from The Odds API, got {type(data)}")
        return []

    return data


# -----------------------------
# Normalize Odds API data to cards
# -----------------------------
def normalize_odds_to_cards(sport_label: str, raw_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert The Odds API events into normalized cards.

    Each card:
        - sport: "NBA", "MLB", "NHL"
        - league: sport_key from The Odds API
        - event_id: event["id"]
        - event_time: event["commence_time"]
        - market_type: "moneyline", "spread", "total", "player_prop"
        - selection: team or player + side
        - line: numeric line if available (spread/total/prop)
        - odds: American odds (int)
        - bookmaker: bookmaker["key"]
        - source: "the-odds-api"
    """
    cards: List[Dict[str, Any]] = []

    for event in raw_events:
        event_id = event.get("id")
        league = event.get("sport_key")
        event_time = event.get("commence_time")

        bookmakers = event.get("bookmakers") or []
        for book in bookmakers:
            bookmaker_key = book.get("key") or "unknown"
            markets = book.get("markets") or []

            for market in markets:
                market_key = market.get("key")  # "h2h", "spreads", "totals", "player_props"
                outcomes = market.get("outcomes") or []

                for outcome in outcomes:
                    name = outcome.get("name")  # team or player or "Over"/"Under"
                    price = outcome.get("price")
                    point = outcome.get("point")

                    if price is None:
                        continue
                    try:
                        odds = int(price)
                    except Exception:
                        continue

                    if market_key == "h2h":
                        market_type = "moneyline"
                        selection = name
                        line_val = None
                    elif market_key == "spreads":
                        market_type = "spread"
                        selection = name
                        line_val = float(point) if point is not None else None
                    elif market_key == "totals":
                        market_type = "total"
                        selection = name  # "Over" or "Under"
                        line_val = float(point) if point is not None else None
                    elif market_key == "player_props":
                        market_type = "player_prop"
                        selection = name
                        line_val = float(point) if point is not None else None
                    else:
                        continue

                    card = {
                        "sport": sport_label,
                        "league": league,
                        "event_id": event_id,
                        "event_time": event_time,
                        "market_type": market_type,
                        "selection": selection,
                        "line": line_val,
                        "odds": odds,
                        "bookmaker": bookmaker_key,
                        "source": "the-odds-api",
                    }
                    cards.append(card)

    return cards


# -----------------------------
# Save cards with dedupe
# -----------------------------
def save_cards(cards: List[Dict[str, Any]]) -> int:
    """
    Save normalized cards into the cards table.

    Uses INSERT OR IGNORE with UNIQUE constraint to dedupe.
    Returns number of NEW rows inserted.
    """
    if not cards:
        return 0

    conn = sqlite3.connect(DB_FILE)
    try:
        cur = conn.cursor()
        inserted = 0
        now = datetime.utcnow().isoformat()

        for c in cards:
            cur.execute(
                f"""
                INSERT OR IGNORE INTO {TABLE_NAME} (
                    sport, league, event_id, event_time,
                    market_type, selection, line, odds,
                    bookmaker, source, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    c.get("sport"),
                    c.get("league"),
                    c.get("event_id"),
                    c.get("event_time"),
                    c.get("market_type"),
                    c.get("selection"),
                    c.get("line"),
                    c.get("odds"),
                    c.get("bookmaker"),
                    c.get("source"),
                    now,
                ),
            )
            if cur.rowcount > 0:
                inserted += 1

        conn.commit()
        return inserted
    finally:
        conn.close()


# -----------------------------
# Unified multi-sport refresh
# -----------------------------
def refresh_all_sports() -> None:
    """
    Refresh NBA, MLB, and NHL odds from The Odds API,
    normalize to cards, and save with dedupe.
    """
    sports = ["NBA", "MLB", "NHL"]

    for sport in sports:
        raw_events = fetch_odds_for_sport(sport)
        cards = normalize_odds_to_cards(sport, raw_events)
        inserted = save_cards(cards)

        print(
            f"[{sport}] Events: {len(raw_events)} | Cards: {len(cards)} | New saved: {inserted}"
        )


# -----------------------------
# Card filtering for AI
# -----------------------------
def get_eligible_cards(
    min_odds: int = MIN_ODDS,
    max_odds: int = MAX_ODDS,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """
    Get cards that fall within the desired odds band and are
    candidates for AI selection.

    - Odds between min_odds and max_odds (inclusive)
    - All markets: moneyline, spread, total, player_prop
    - Most recent first
    """
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT *
            FROM {TABLE_NAME}
            WHERE odds >= ? AND odds <= ?
            ORDER BY created_at DESC
            LIMIT ?;
            """,
            (min_odds, max_odds, limit),
        )
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# -----------------------------
# Qwen / OpenRouter analysis
# -----------------------------
def analyze_cards_with_qwen(
    min_odds: int = MIN_ODDS,
    max_odds: int = MAX_ODDS,
    limit: int = 200,
) -> Optional[Dict[str, Any]]:
    """
    Send eligible cards to Qwen 3.6 Plus via OpenRouter and get structured JSON back.

    Expected response format (example):

    {
      "strong_cards": [
        {
          "id": 123,
          "reason": "Line is off vs market consensus...",
          "confidence": 0.82
        },
        ...
      ],
      "parlay_suggestions": [
        {
          "card_ids": [123, 145],
          "estimated_odds": 275,
          "reason": "Correlated edges on same team..."
        }
      ],
      "engine_state": "collecting|probation|active|trusted",
      "notes": "Short CLV / strategy notes..."
    }
    """
    cards = get_eligible_cards(min_odds=min_odds, max_odds=max_odds, limit=limit)
    if not cards:
        print("No eligible cards found in the desired odds band.")
        return None

    api_key = get_openrouter_key()

    payload_cards = [
        {
            "id": c["id"],
            "sport": c["sport"],
            "league": c["league"],
            "market_type": c["market_type"],
            "selection": c["selection"],
            "line": c["line"],
            "odds": c["odds"],
            "bookmaker": c["bookmaker"],
            "event_time": c["event_time"],
        }
        for c in cards
    ]

    system_prompt = (
        "You are a sports betting selection engine.\n"
        "You receive a list of candidate betting cards, each representing a single bet:\n"
        "- sport, league, market_type (moneyline, spread, total, player_prop)\n"
        "- selection (team or player + side)\n"
        "- line (spread/total/prop line if numeric)\n"
        "- odds (American odds, between -300 and +150)\n"
        "- bookmaker, event_time\n\n"
        "Your job:\n"
        "1) Identify the strongest individual cards (highest probability of winning / best edge).\n"
        "2) Optionally propose parlays using only these cards, with reasonable combined odds.\n"
        "3) Use proven concepts like:\n"
        "   - market consensus vs outlier prices\n"
        "   - implied probability from odds\n"
        "   - avoiding extremely volatile or low-information spots\n"
        "4) Be conservative: only mark a card as strong if you have a clear edge rationale.\n\n"
        "Engine state guideline:\n"
        "- 'collecting' if fewer than ~3 strong cards\n"
        "- 'probation' around 3–4\n"
        "- 'active' around 5–8\n"
        "- 'trusted' if you consistently find many strong edges\n\n"
        "Respond with STRICT JSON only, no prose, with keys:\n"
        "- strong_cards: array of {id, reason, confidence}\n"
        "- parlay_suggestions: array of {card_ids, estimated_odds, reason}\n"
        "- engine_state: 'collecting' | 'probation' | 'active' | 'trusted'\n"
        "- notes: short string with CLV/strategy notes\n"
    )

    user_prompt = {
        "eligible_cards": payload_cards
    }

    body = {
        "model": QWEN_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": str(user_prompt)},
        ],
        "response_format": {"type": "json_object"},
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(OPENROUTER_URL, json=body, headers=headers, timeout=60)
    except Exception as e:
        print(f"Error calling Qwen/OpenRouter: {e}")
        return None

    if resp.status_code != 200:
        print(f"Qwen/OpenRouter non-200: {resp.status_code} - {resp.text[:200]}")
        return None

    try:
        data = resp.json()
    except Exception as e:
        print(f"Failed to parse Qwen response JSON: {e}")
        return None

    try:
        content = data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Unexpected Qwen response shape: {e}")
        return None

    if isinstance(content, dict):
        return content

    try:
        import json
        return json.loads(content)
    except Exception:
        print("Qwen returned non-JSON content.")
        return None


# -----------------------------
# CLI entry point (optional)
# -----------------------------
def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Multi-sport odds refresh + Qwen selection engine."
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Refresh odds from The Odds API and store cards.",
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Run Qwen analysis on eligible cards.",
    )
    parser.add_argument(
        "--min-odds",
        type=int,
        default=MIN_ODDS,
        help="Minimum American odds for eligible cards (default: -300).",
    )
    parser.add_argument(
        "--max-odds",
        type=int,
        default=MAX_ODDS,
        help="Maximum American odds for eligible cards (default: +150).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Max number of eligible cards to send to Qwen (default: 200).",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    init_db()

    if args.refresh:
        print("Refreshing odds and saving cards...")
        refresh_all_sports()

    if args.analyze:
        print("Running Qwen analysis on eligible cards...")
        result = analyze_cards_with_qwen(
            min_odds=args.min_odds,
            max_odds=args.max_odds,
            limit=args.limit,
        )
        if result is not None:
            import json
            print(json.dumps(result, indent=2))
        else:
            print("No analysis result.")

    if not args.refresh and not args.analyze:
        print("Nothing to do. Use --refresh and/or --analyze.")

