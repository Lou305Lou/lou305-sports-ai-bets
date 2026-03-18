import streamlit as st
import pandas as pd
import os

st.title("Sports AI Betting Dashboard")

file_path = "Bet_log.csv"

if os.path.exists(file_path):
    df = pd.read_csv(file_path)
    st.success("Data loaded successfully.")
else:
    st.error(f"File not found: {file_path}")
    st.stop()


def prepare_data(df):
    df = df.copy()

    required_cols = [
        "date",
        "home_team",
        "away_team",
        "bet_type",
        "pick",
        "bookmaker",
        "odds",
        "line",
    ]

    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        st.error(f"Missing required columns in CSV: {missing_cols}")
        st.stop()

    df["game_id"] = (
        df["date"].astype(str)
        + " | "
        + df["home_team"].astype(str)
        + " vs "
        + df["away_team"].astype(str)
    )

    df["team"] = df["pick"].astype(str)
    df["market"] = df["bet_type"].astype(str).str.lower().str.strip()
    df["point"] = pd.to_numeric(df["line"], errors="coerce")
    df["odds"] = pd.to_numeric(df["odds"], errors="coerce")

    return df


def american_to_decimal(odds):
    if pd.isna(odds):
        return None

    try:
        odds = float(odds)
    except:
        return None

    if odds > 0:
        return (odds / 100) + 1
    elif odds < 0:
        return (100 / abs(odds)) + 1
    return None


def detect_opportunities(df):
    opportunities = []

    for game in df["game_id"].dropna().unique():
        game_df = df[df["game_id"] == game].copy()

        for i, row_a in game_df.iterrows():
            for j, row_b in game_df.iterrows():
                if i == j:
                    continue

                dec_a = american_to_decimal(row_a["odds"])
                dec_b = american_to_decimal(row_b["odds"])

                # Arbitrage
                if (
                    row_a["team"] != row_b["team"]
                    and dec_a is not None
                    and dec_b is not None
                    and dec_a > 1
                    and dec_b > 1
                ):
                    prob = (1 / dec_a) + (1 / dec_b)

                    if prob < 1:
                        profit = round((1 - prob) * 100, 2)

                        if profit > 1:
                            opportunities.append({
                                "type": "Arbitrage",
                                "game": game,
                                "profit_%": profit,
                                "bet_a": row_a["team"],
                                "book_a": row_a["bookmaker"],
                                "odds_a": row_a["odds"],
                                "bet_b": row_b["team"],
                                "book_b": row_b["bookmaker"],
                                "odds_b": row_b["odds"],
                            })

                # Middle
                if (
                    row_a["team"] != row_b["team"]
                    and row_a["market"] == "spread"
                    and row_b["market"] in ["moneyline", "h2h", "ml"]
                ):
                    spread = row_a["point"]

                    if pd.notna(spread) and abs(spread) > 1.5:
                        opportunities.append({
                            "type": "Middle",
                            "game": game,
                            "bet_a": row_a["team"],
                            "book_a": row_a["bookmaker"],
                            "odds_a": row_a["odds"],
                            "bet_b": row_b["team"],
                            "book_b": row_b["bookmaker"],
                            "odds_b": row_b["odds"],
                            "spread": spread,
                        })

    return pd.DataFrame(opportunities)


clean_df = prepare_data(df)
opps = detect_opportunities(clean_df)

st.subheader("Detected Opportunities")

if opps.empty:
    st.warning("No strong opportunities found in this CSV.")
else:
    if "profit_%" in opps.columns:
        arb_rows = opps[opps["type"] == "Arbitrage"].copy()
        middle_rows = opps[opps["type"] == "Middle"].copy()

        if not arb_rows.empty:
            arb_rows = arb_rows.sort_values(by="profit_%", ascending=False)

        final_df = pd.concat([arb_rows, middle_rows], ignore_index=True)
    else:
        final_df = opps.copy()

    st.dataframe(final_df)
