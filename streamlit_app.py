import streamlit as st
import pandas as pd
import os

# Page title
st.title("Sports AI Betting Dashboard")

# Show files in current directory for debugging
st.write("Files in directory:", os.listdir())

# Exact file name shown in your repo
file_path = "Bet_log.csv"

# Load data safely
if os.path.exists(file_path):
    df = pd.read_csv(file_path)
    st.success("Data loaded successfully.")
else:
    st.error(f"File not found: {file_path}")
    st.stop()


def detect_opportunities(df):
    opportunities = []

    # Basic column check so the app fails gracefully if CSV format is off
    required_cols = ["game_id", "team", "odds", "market"]
    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        st.error(f"Missing required columns in CSV: {missing_cols}")
        st.write("Columns found in CSV:", list(df.columns))
        st.stop()

    # Add point column if missing, so middle logic does not crash
    if "point" not in df.columns:
        df["point"] = None

    for game in df["game_id"].dropna().unique():
        game_df = df[df["game_id"] == game]

        for i, row_a in game_df.iterrows():
            for j, row_b in game_df.iterrows():
                if i == j:
                    continue

                # ARBITRAGE CHECK
                if row_a["team"] != row_b["team"]:
                    try:
                        odds_a = float(row_a["odds"])
                        odds_b = float(row_b["odds"])

                        if odds_a > 1 and odds_b > 1:
                            prob = (1 / odds_a) + (1 / odds_b)

                            if prob < 1:
                                profit = round((1 - prob) * 100, 2)

                                if profit > 1:
                                    opportunities.append({
                                        "type": "Arbitrage",
                                        "game": game,
                                        "profit_%": profit,
                                        "bet_a": row_a["team"],
                                        "odds_a": odds_a,
                                        "bet_b": row_b["team"],
                                        "odds_b": odds_b,
                                    })
                    except:
                        pass

                # MIDDLE CHECK
                if (
                    row_a["team"] != row_b["team"]
                    and row_a["market"] == "spreads"
                    and row_b["market"] == "h2h"
                ):
                    spread = row_a["point"]

                    if pd.notna(spread):
                        try:
                            spread = float(spread)

                            if abs(spread) > 1.5:
                                opportunities.append({
                                    "type": "Middle",
                                    "game": game,
                                    "profit_%": None,
                                    "bet_a": row_a["team"],
                                    "odds_a": row_a["odds"],
                                    "bet_b": row_b["team"],
                                    "odds_b": row_b["odds"],
                                    "spread": spread,
                                })
                        except:
                            pass

    return pd.DataFrame(opportunities)


# Run detection
opps = detect_opportunities(df)

# Display results
if opps.empty:
    st.write("No strong opportunities right now.")
else:
    if "profit_%" in opps.columns:
        arb_rows = opps[opps["type"] == "Arbitrage"].copy()
        middle_rows = opps[opps["type"] == "Middle"].copy()

        if not arb_rows.empty:
            arb_rows = arb_rows.sort_values(by="profit_%", ascending=False)

        final_df = pd.concat([arb_rows, middle_rows], ignore_index=True)
        st.dataframe(final_df)
    else:
        st.dataframe(opps)
