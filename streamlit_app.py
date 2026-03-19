
# ============================================================
# V13 — CORRELATION FILTER V2 (REAL WORKING VERSION)
# ============================================================
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(layout="wide")
st.title("Sports AI Betting Dashboard V13")

players = [
    ("Giannis Antetokounmpo","Bucks"),
    ("Tyrese Haliburton","Pacers"),
    ("LeBron James","Lakers"),
]

def sample_df():
    rows = []
    for p,t in players:
        for prop in ["pra","pa","points"]:
            rows.append({
                "player":p,
                "team":t,
                "prop_type":prop,
                "line":30 + np.random.randint(-3,3),
                "projection":35 + np.random.randint(-3,3),
                "odds":-110,
                "book":"DraftKings"
            })
    return pd.DataFrame(rows)

df = sample_df()

def calc(row):
    edge = row["projection"] - row["line"]
    hit = 0.5 + (edge/10)*0.5
    hit = max(0.40,min(0.66,hit))
    ev = (hit - 0.52)*100
    score = edge*10 + ev
    return pd.Series([edge,hit,ev,score])

df[["edge","hit","ev","score"]] = df.apply(calc,axis=1)

df["side"] = np.where(df["projection"]>df["line"],"Over","Under")

# CORRELATION FILTER V2
df["correlation_flag"] = ""
df["bet_size"] = 0.5

grouped = df.groupby("player")

for player, group in grouped:
    strong = group[group["score"] > 70]
    if len(strong) > 1:
        for i in strong.index:
            df.loc[i,"correlation_flag"] = "Strong overlap"
            df.loc[i,"bet_size"] = 0.25

df = df.sort_values("score",ascending=False)

for _,row in df.head(10).iterrows():
    st.write(f"{row['player']} | {row['side']} {row['line']} {row['prop_type']}")
    st.write(f"Projection {row['projection']} | Edge {row['edge']:.2f}")
    st.write(f"Hit {row['hit']*100:.1f}% | EV {row['ev']:.2f}% | Score {row['score']:.1f}")
    st.write(f"Bet Size {row['bet_size']}u | {row['correlation_flag']}")
    st.write("---")
