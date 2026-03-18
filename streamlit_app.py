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

st.subheader("Detected Opportunities")

for game in df["Game"].unique():
    game_df = df[df["Game"] == game]

    for i in range(len(game_df)):
        for j in range(i + 1, len(game_df)):
            bet1 = game_df.iloc[i]
            bet2 = game_df.iloc[j]

            # Spread middle check
            if bet1["Spread"] < 0 and bet2["Spread"] > 0:
                if bet2["Spread"] > abs(bet1["Spread"]):
                    middle_size = bet2["Spread"] - abs(bet1["Spread"])

                    st.success(f"{game} → Middle Found!")
                    st.write(f"{bet1['Book']}: {bet1['Team']} {bet1['Spread']}")
                    st.write(f"{bet2['Book']}: {bet2['Team']} +{bet2['Spread']}")
                    st.write(f"Middle Size: {middle_size:.1f} points")
                    st.write("---")
