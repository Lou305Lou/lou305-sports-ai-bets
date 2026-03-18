import streamlit as st

st.title("Sports AI Betting Dashboard")
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

odds_a = st.number_input("Odds A (e.g. +110)", value=110, step=1)
odds_b = st.number_input("Odds B (e.g. -105)", value=-105, step=1)

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
