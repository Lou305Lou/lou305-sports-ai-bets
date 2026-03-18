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

                        if profit > 1:  # FILTER (only good arbs)
                            opportunities.append({
                                "type": "Arbitrage",
                                "game": game,
                                "profit_%": profit,
                                "bet_a": row_a["team"],
                                "odds_a": row_a["odds"],
                                "bet_b": row_b["team"],
                                "odds_b": row_b["odds"],
                            })

                # MIDDLE CHECK (spread + ML combo)
                if row_a["team"] != row_b["team"]:
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
