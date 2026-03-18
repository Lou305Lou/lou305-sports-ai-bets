import streamlit as st
import pandas as pd
import os

# Title
st.title("Sports AI Betting Dashboard")

# Debug: show available files (optional but helpful)
st.write("Files in directory:", os.listdir())

# File path (UPDATED to match your folder)
file_path = "Sports-ai-bets/bet_log.csv"

# Load data safely
if os.path.exists(file_path):
    df = pd.read_csv(file_path)
    st.success("Data loaded successfully.")
else:
    st.error(f"File not found: {file_path}")
    st.stop()

# Detection function
def detect_opportunities(df):
    opportunities = []

    for game in df["game_id"].unique():
        game_df = df[df["game_id"] == game]

        for i, row_a in game_df.iterrows():
            for j, row_b in game_df.iterrows():

                if i == j:
                    continue

                # ARBITRAGE CHECK
                if row_a["team"] != row_b["team"]:
                    prob = (1 / row_a["odds"]) + (1 / row_b["odds"])

                    if prob < 1:
                        profit = round((1 - prob) * 100, 2)

                        if profit > 1:
                            opportunities.append({
                                "type": "Arbitrage",
                                "game": game,
                                "profit_%": profit,
                                "bet_a": row_a["team"],
                                "odds_a": row_a["odds"],
                                "bet_b": row_b["team"],
                                "odds_b": row_b["odds"],
                            })

                # MIDDLE CHECK
                if row_a["market"] == "spreads" and row_b["market"] == "h2h":
                    spread = row_a["point"]

                    if spread and abs(spread) > 1.5:
                        opportunities.append({
                            "type": "Middle",
                            "game": game,
                            "spread_side": row_a["team"],
                            "spread": spread,
                            "ml_side": row_b["team"],
                            "ml_odds": row_b["odds"],
                        })

    return pd.DataFrame(opportunities)

# Run detection
opps = detect_opportunities(df)

# Display results
if opps.empty:
    st.write("No strong opportunities right now.")
else:
    st.dataframe(opps)
