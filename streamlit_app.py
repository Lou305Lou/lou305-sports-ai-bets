import streamlit as st
import pandas as pd

st.title("Sports AI Betting Dashboard")

# Sample data (we’ll replace with real API next)
data = {
    "Game": ["Lakers vs Heat", "Celtics vs Bulls"],
    "Book": ["DraftKings", "FanDuel"],
    "Team": ["Lakers", "Celtics"],
    "Spread": [-4.5, -3.5],
    "Odds": [-110, -105]
}

df = pd.DataFrame(data)

st.subheader("Current Odds")
st.dataframe(df)
