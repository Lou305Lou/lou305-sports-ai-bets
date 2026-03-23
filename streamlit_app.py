import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(layout="wide")

# -----------------------------
# MOBILE DETECTION
# -----------------------------
def is_mobile():
    try:
        return st.session_state.get("is_mobile", True)
    except:
        return True

# Toggle (for testing)
st.sidebar.toggle("📱 Mobile Mode", key="is_mobile", value=True)

# -----------------------------
# STYLES
# -----------------------------
st.markdown("""
<style>
.card {
    border-radius: 12px;
    padding: 12px;
    margin-bottom: 10px;
    background-color: #111;
    border: 1px solid #222;
}
.badge {
    padding: 4px 8px;
    border-radius: 8px;
    font-size: 12px;
    margin-right: 6px;
}
.tier-b {background:#2a4365;}
.tier-c {background:#444;}
.best {background:#6b46c1;}
.active {background:#975a16;}
.watch {background:#2d3748;}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# NAV BAR
# -----------------------------
st.markdown("### 🚀 Navigation")
nav = st.radio(
    "",
    ["Top Plays", "Watchlist", "AI Slip", "Bet Log"],
    horizontal=True
)

# -----------------------------
# SAMPLE DATA (Replace w/ your df)
# -----------------------------
data = [
    {"game":"Warriors vs Lakers","market":"moneyline","selection":"Lakers","odds":110,"edge":1.58,"score":92,"units":0.43,"tier":"B","status":"Active"},
    {"game":"Warriors vs Lakers","market":"total","selection":"Over 229.5","odds":-102,"edge":1.60,"score":88,"units":0.51,"tier":"B","status":"Active"},
    {"game":"Warriors vs Lakers","market":"moneyline","selection":"Warriors","odds":-110,"edge":1.82,"score":89,"units":0.05,"tier":"B","status":"Watch"},
    {"game":"Nuggets vs Suns","market":"moneyline","selection":"Nuggets","odds":-132,"edge":4.60,"score":100,"units":0.05,"tier":"C","status":"Watch"},
]

df = pd.DataFrame(data)

# -----------------------------
# CARD RENDER
# -----------------------------
def render_card(row):
    tier_class = "tier-b" if row["tier"] == "B" else "tier-c"
    status_class = "active" if row["status"] == "Active" else "watch"

    st.markdown(f"""
    <div class="card">
        <div>
            <span class="badge {tier_class}">Tier {row['tier']}</span>
            <span class="badge {status_class}">{row['status']}</span>
        </div>
        <h4>{row['selection']}</h4>
        <p>{row['game']}</p>
        <p>Odds: {row['odds']} | Edge: {row['edge']}% | Score: {row['score']}</p>
        <p>Units: {row['units']}u</p>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------
# SMART TABLE
# -----------------------------
def smart_display(df):
    if is_mobile():
        for _, row in df.iterrows():
            render_card(row)
    else:
        st.dataframe(df, use_container_width=True)

# -----------------------------
# TOP PLAYS
# -----------------------------
if nav == "Top Plays":
    st.markdown("## 🎯 Top Plays")

    top_df = df[df["status"] == "Active"]
    smart_display(top_df)

# -----------------------------
# WATCHLIST
# -----------------------------
if nav == "Watchlist":
    st.markdown("## 👀 Watchlist")

    watch_df = df[df["status"] == "Watch"]
    smart_display(watch_df)

# -----------------------------
# AI BET SLIP (STICKY STYLE)
# -----------------------------
if nav == "AI Slip":
    st.markdown("## 🎯 AI Bet Slip")

    best = df[df["status"] == "Active"].iloc[0]

    st.markdown(f"""
    <div class="card">
        <h3>🔥 Best Bet</h3>
        <h4>{best['selection']}</h4>
        <p>{best['game']}</p>
        <p>Odds: {best['odds']}</p>
        <p>Confidence: Elite</p>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------
# BET LOG
# -----------------------------
if nav == "Bet Log":
    st.markdown("## 🧾 Bet Log")

    with st.form("log"):
        game = st.text_input("Game")
        selection = st.text_input("Selection")
        units = st.number_input("Units", 0.0, 5.0, 0.5)

        submitted = st.form_submit_button("Save Bet")

        if submitted:
            st.success("Bet saved (mock)")

# -----------------------------
# ADAPTIVE (CLEANED)
# -----------------------------
with st.expander("⚙️ Adaptive Settings"):
    st.write("Min Edge: 1.25%")
    st.write("Max Plays: 3")
    st.write("Max Units: 3.5u")
