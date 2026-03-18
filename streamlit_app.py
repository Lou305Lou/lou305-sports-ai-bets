import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Sports AI Betting Dashboard", layout="wide")

st.title("Sports AI Betting Dashboard")
st.caption("Manual live odds scanner with sportsbook selection, arbitrage, middles, bet sizing, and sharp filters")

API_KEY = st.secrets.get("ODDS_API_KEY", "")

SPORT_OPTIONS = {
    "NBA": "basketball_nba",
    "NHL": "icehockey_nhl",
    "NFL": "americanfootball_nfl",
    "MLB": "baseball_mlb",
    "NCAAF": "americanfootball_ncaaf",
}

if not API_KEY:
    st.error("Missing ODDS_API_KEY in Streamlit secrets.")
    st.stop()


def american_to_decimal(odds):
    if odds is None:
        return None
    try:
        odds = float(odds)
    except Exception:
        return None

    if odds > 0:
        return (odds / 100.0) + 1.0
    if odds < 0:
        return (100.0 / abs(odds)) + 1.0
    return None


def implied_prob_from_american(odds):
    dec = american_to_decimal(odds)
    if dec is None or dec <= 1:
        return None
    return 1 / dec


def calculate_arb_stakes(odds_a, odds_b, bankroll):
    dec_a = american_to_decimal(odds_a)
    dec_b = american_to_decimal(odds_b)

    if dec_a is None or dec_b is None or bankroll <= 0:
        return None, None, None, None

    inv_a = 1 / dec_a
    inv_b = 1 / dec_b
    total_inv = inv_a + inv_b

    if total_inv >= 1:
        return None, None, None, None

    stake_a = bankroll * (inv_a / total_inv)
    stake_b = bankroll * (inv_b / total_inv)
