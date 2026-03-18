import streamlit as st
import pandas as pd

st.title("Sports AI Betting Dashboard")
st.subheader("Auto Opportunity Scanner")

data = [
    {"Game": "Lakers vs Heat", "Team": "Lakers", "Spread": -4.5, "Odds": -110, "Book": "DK"},
    {"Game": "Lakers vs Heat", "Team": "Heat", "Spread": 5.5, "Odds": -110, "Book": "FD"},
    {"Game": "Celtics vs Bulls", "Team": "Celtics", "Spread": -3.5, "Odds": -105, "Book": "MGM"},
    {"Game": "Celtics vs Bulls", "Team": "Bulls", "Spread": 4.5, "Odds": -110, "Book": "Caesars"},
]

df = pd.DataFrame(data)
st.dataframe(df)

def find_middle_opportunities(df):
    results = []

    for game in df["Game"].unique():
        game_df = df[df["Game"] == game].reset_index(drop=True)

        for i in range(len(game_df)):
            for j in range(i + 1, len(game_df)):
                bet1 = game_df.iloc[i]
                bet2 = game_df.iloc[j]

                if bet1["Spread"] < 0 and bet2["Spread"] > 0:
                    if bet2["Spread"] > abs(bet1["Spread"]):
                        middle_size = bet2["Spread"] - abs(bet1["Spread"])
                        results.append({
                            "Game": game,
                            "Book A": bet1["Book"],
                            "Bet A": f"{bet1['Team']} {bet1['Spread']}",
                            "Odds A": bet1["Odds"],
                            "Book B": bet2["Book"],
                            "Bet B": f"{bet2['Team']} +{bet2['Spread']}",
                            "Odds B": bet2["Odds"],
                            "Middle Size": middle_size
                        })

                if bet2["Spread"] < 0 and bet1["Spread"] > 0:
                    if bet1["Spread"] > abs(bet2["Spread"]):
                        middle_size = bet1["Spread"] - abs(bet2["Spread"])
                        results.append({
                            "Game": game,
                            "Book A": bet2["Book"],
                            "Bet A": f"{bet2['Team']} {bet2['Spread']}",
                            "Odds A": bet2["Odds"],
                            "Book B": bet1["Book"],
                            "Bet B": f"{bet1['Team']} +{bet1['Spread']}",
                            "Odds B": bet1["Odds"],
                            "Middle Size": middle_size
                        })

    return pd.DataFrame(results)

st.subheader("Detected Middle Opportunities")

middle_df = find_middle_opportunities(df)

if not middle_df.empty:
    st.dataframe(middle_df)
else:
    st.info("No middle opportunities found.")
