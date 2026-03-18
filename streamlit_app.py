import streamlit as st
import pandas as pd

st.title("Sports AI Betting Dashboard")

st.subheader("Sample Odds Board")

data = {
    "Game": ["Lakers vs Heat", "Lakers vs Heat", "Celtics vs Bulls", "Celtics vs Bulls"],
    "Book": ["DraftKings", "FanDuel", "BetMGM", "Caesars"],
    "Bet Type": ["Spread", "Spread", "Moneyline", "Moneyline"],
    "Selection": ["Lakers -4.5", "Heat +5.5", "Celtics", "Bulls"],
    "Odds": [-110, -110, -125, +135]
}

df = pd.DataFrame(data)
st.dataframe(df)

st.subheader("Quick Bet Checker")

book_a = st.text_input("Book A Bet", "Lakers -4.5")
odds_a = st.number_input("Book A Odds", value=-110)

book_b = st.text_input("Book B Bet", "Heat +5.5")
odds_b = st.number_input("Book B Odds", value=-110)

if st.button("Check Opportunity"):
    st.write("Book A:", book_a, "@", odds_a)
    st.write("Book B:", book_b, "@", odds_b)

    if "Lakers -4.5" in book_a and "Heat +5.5" in book_b:
        st.success("Possible middle detected.")
    else:
        st.info("No middle detected from this simple check.")
