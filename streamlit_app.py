import streamlit as st

st.title("Sports AI Betting Dashboard")

tab1, tab2 = st.tabs(["Arbitrage Checker", "Spread Middle Checker"])

# ---------- Arbitrage Checker ----------
with tab1:
    st.subheader("Quick Arbitrage Checker")

    def american_to_decimal(odds):
        odds = float(odds)
        if odds > 0:
            return 1 + (odds / 100)
        return 1 + (100 / abs(odds))

    def implied_prob(odds):
        odds = float(odds)
        if odds > 0:
            return 100 / (odds + 100)
        return abs(odds) / (abs(odds) + 100)

    odds_a = st.number_input("Odds A", value=110, step=1, key="arb_a")
    odds_b = st.number_input("Odds B", value=-105, step=1, key="arb_b")

    if st.button("Check Arbitrage"):
        prob_a = implied_prob(odds_a)
        prob_b = implied_prob(odds_b)
        total_prob = prob_a + prob_b

        st.write(f"Implied Probability A: {prob_a:.4f}")
        st.write(f"Implied Probability B: {prob_b:.4f}")
        st.write(f"Total Probability: {total_prob:.4f}")

        if total_prob < 1:
            st.success("Arbitrage Opportunity Detected!")

            bankroll = 100
            dec_a = american_to_decimal(odds_a)
            dec_b = american_to_decimal(odds_b)

            stake_a = bankroll * prob_a / total_prob
            stake_b = bankroll * prob_b / total_prob

            payout_a = stake_a * dec_a
            payout_b = stake_b * dec_b
            guaranteed_profit = min(payout_a, payout_b) - bankroll

            st.write(f"Bet ${stake_a:.2f} on A")
            st.write(f"Bet ${stake_b:.2f} on B")
            st.write(f"Guaranteed Profit: ${guaranteed_profit:.2f}")
        else:
            st.error("No arbitrage opportunity.")

# ---------- Spread Middle Checker ----------
with tab2:
    st.subheader("Spread Middle Checker")

    team_a = st.text_input("Team A", "Lakers")
    spread_a = st.number_input("Book A Spread", value=-4.5, step=0.5)
    odds_spread_a = st.number_input("Book A Odds", value=-110, step=1, key="mid_a")

    team_b = st.text_input("Team B", "Heat")
    spread_b = st.number_input("Book B Spread", value=5.5, step=0.5)
    odds_spread_b = st.number_input("Book B Odds", value=-110, step=1, key="mid_b")

    if st.button("Check Middle"):
        st.write(f"Book A: {team_a} {spread_a} @ {odds_spread_a}")
        st.write(f"Book B: {team_b} {spread_b} @ {odds_spread_b}")

        middle_gap = spread_b - abs(spread_a)

        if spread_a < 0 and spread_b > 0 and spread_b > abs(spread_a):
            st.success("Possible spread middle detected!")
            st.write(f"Middle window size: {middle_gap:.1f} points")

            low_end = abs(spread_a) + 0.5
            high_end = spread_b - 0.5

            if high_end >= low_end:
                st.write(f"Possible middle scores land between {low_end:.1f} and {high_end:.1f} points.")
            else:
                st.write("Very small middle window.")
        else:
            st.error("No spread middle detected.")
