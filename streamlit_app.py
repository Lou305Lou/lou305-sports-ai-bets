import hashlib
import random
from itertools import combinations

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Sports Betting AI Dashboard V31.9.1", layout="wide")

# =========================================================
# SESSION STATE
# =========================================================
if "is_mobile" not in st.session_state:
    st.session_state["is_mobile"] = True
if "bet_log" not in st.session_state:
    st.session_state["bet_log"] = []
if "auto_logged_ids" not in st.session_state:
    st.session_state["auto_logged_ids"] = set()
if "nav_choice" not in st.session_state:
    st.session_state["nav_choice"] = "Top Plays"
if "manual_results" not in st.session_state:
    st.session_state["manual_results"] = {}

st.sidebar.toggle("📱 Mobile Mode", key="is_mobile")


def is_mobile() -> bool:
    return st.session_state.get("is_mobile", True)


# =========================================================
# ENGINE SETTINGS
# =========================================================
MIN_ACTIVE_EDGE = 1.25
ACTIVE_EDGE_PROMOTION = 1.50
MAX_TOTAL_UNITS = 3.50
MAX_ACTIVE_PLAYS = 3
DEFAULT_ODDS_RANGE = (-200, 150)

QUALITY_ACTIVE_PRIMARY = 0.58
QUALITY_ACTIVE_SECONDARY = 0.64
QUALITY_FLOOR_FALLBACK = 0.54

MIN_PARLAY_LEGS = 2
MAX_PARLAY_LEGS = 3
MIN_PARLAY_ODDS = 200

SHARP_PARLAY_MIN_TRUE_CONF = 60.0
SHARP_PARLAY_MAX_PENALTY = 0.18
FALLBACK_PARLAY_MAX_PENALTY = 0.36

TEST_MODE = "Paper Test"
SINGLE_UNIT_MIN = 0.40
SINGLE_UNIT_MAX = 1.25
PARLAY_UNIT_SHARP = 0.60
PARLAY_UNIT_FALLBACK_2 = 0.35
PARLAY_UNIT_FALLBACK_3 = 0.20
TEST_DAILY_UNIT_CAP = 3.50
