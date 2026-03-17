import streamlit as st
import pandas as pd

st.title("📊 Sports Betting Dashboard")

url = "https://raw.githubusercontent.com/Lou305Lou/lou305-sports-ai-bets/main/bet_log.csv"

df = pd.read_csv(url)

st.subheader("Raw Data")
st.dataframe(df)

spread_df = df[df["market"] == "spreads"].copy()
spread_df = spread_df[spread_df["point"].notnull()]

st.subheader("Spread Bets")
st.dataframe(spread_df)
