import streamlit as st
import pandas as pd

st.title("Sports AI Betting Dashboard")

st.subheader("Quick Arbitrage Checker")

def american_to_decimal(odds):
    if odds > 0:
        return 1 + (odds / 100)
    else:
        return 1 + (100 / abs(odds))

def implied_prob(odds):
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)

odds_a = st.number_input("Odds A (e.g. -110)", value=-110)
odds_b = st.number_input("Odds B (e.g. +110)", value=110)

if st.button("Check Arbitrage"):
    prob_a = implied_prob(odds_a)
    prob_b = implied_prob(odds_b)

    total_prob = prob_a + prob_b

    st.write(f"Implied Probability A: {prob_a:.2f}")
    st.write(f"Implied Probability B: {prob_b:.2f}")
    st.write(f"Total: {total_prob:.2f}")

    if total_prob < 1:
        st.success("🔥 Arbitrage Opportunity Detected!")
        
        stake = 100
        dec_a = american_to_decimal(odds_a)
        dec_b = american_to_decimal(odds_b)

        stake_a = stake / dec_a
        stake_b = stake / dec_b

        st.write(f"Bet ${stake_a:.2f} on A")
        st.write(f"Bet ${stake_b:.2f} on B")
    else:
        st.error("No arbitrage opportunity.")
