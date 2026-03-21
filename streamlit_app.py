import io
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Sports AI Dashboard V8 Core", layout="wide")

# ---------- SESSION ----------
if "active_df" not in st.session_state:
    st.session_state.active_df = None
if "active_source" not in st.session_state:
    st.session_state.active_source = "None"

# ---------- HELPERS ----------
def normalize_columns(df):
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    return df

def american_to_decimal(odds):
    odds = float(odds)
    return 1 + (odds/100 if odds > 0 else 100/abs(odds))

def implied_prob(odds):
    odds = float(odds)
    return 100/(odds+100) if odds > 0 else abs(odds)/(abs(odds)+100)

def calc_ev(hit_pct, odds):
    p = hit_pct/100
    dec = american_to_decimal(odds)
    return ((p*dec)-1)*100

def clean_bool(x):
    return str(x).lower() in ["true","1","yes"]

# ---------- SAMPLE DATA ----------
def sample_data():
    return pd.DataFrame([
        ["Stephen Curry","Points Over",-115,27.5,"NBA","NBA","DK",32.2,4.7,66.7,84,True],
        ["Stephen Curry","Points Over",-108,27.0,"NBA","NBA","Caesars",32.2,5.2,66.7,86,True],
        ["LeBron James","PRA Over",-110,38.5,"NBA","NBA","FD",43.8,5.3,64.8,80,True],
        ["Anthony Davis","Rebounds Over",-125,11.5,"NBA","NBA","CZ",13.2,1.7,59.4,62,True],
    ], columns=["player","market","odds","point","sport","league","book","projection","edge","hit_pct","score","is_starter"])

# ---------- ENGINE ----------
def build_engine(df):
    df = normalize_columns(df)

    for col in ["odds","point","projection","edge","hit_pct","score"]:
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "ev_edge" not in df:
        df["ev_edge"] = df.apply(lambda r: calc_ev(r["hit_pct"], r["odds"]) if pd.notna(r["hit_pct"]) else 0, axis=1)

    if "score" not in df:
        df["score"] = 50 + df["edge"]*5 + df["ev_edge"]*0.5

    df["tier"] = np.select(
        [df["score"]>=80, df["score"]>=68, df["score"]>=58],
        ["🟢 Tier 1","🟡 Tier 2","⚪ Tier 3"],
        default="🔴 Pass"
    )

    df["units"] = np.select(
        [df["score"]>=80, df["score"]>=68, df["score"]>=58],
        [1,0.5,0.25],
        default=0
    )

    return df

# ---------- UI ----------
st.title("Sports AI Dashboard V8")

tabs = st.tabs(["Dashboard","Data Input","NBA Props"])

# ---------- DASHBOARD ----------
with tabs[0]:
    st.write("Active Source:", st.session_state.active_source)

    if st.session_state.active_df is not None:
        df = build_engine(st.session_state.active_df)

        st.subheader("Top Plays")

        best = df.sort_values("score", ascending=False).head(5)

        for _, r in best.iterrows():
            st.write(
                f"{r.player} — {r.market} | Odds {r.odds} | Score {round(r.score,1)} | {r.tier} | {r.units}u"
            )

        st.dataframe(df)

# ---------- DATA INPUT ----------
with tabs[1]:
    if st.button("Load Sample Data"):
        st.session_state.active_df = sample_data()
        st.session_state.active_source = "Sample"

    st.subheader("Paste CSV")

    txt = st.text_area("Paste here")

    if st.button("Load Pasted Data"):
        try:
            df = pd.read_csv(io.StringIO(txt))
            st.session_state.active_df = df
            st.session_state.active_source = "Pasted"
            st.success("Loaded")
        except Exception as e:
            st.error(e)

# ---------- NBA PROPS ----------
with tabs[2]:
    if st.session_state.active_df is None:
        st.info("Load data first")
    else:
        df = build_engine(st.session_state.active_df)

        min_score = st.slider("Min Score",0,100,60)

        df = df[df["score"]>=min_score]

        st.dataframe(df)

        st.download_button(
            "Download",
            df.to_csv(index=False),
            "props.csv"
        )

st.success("V8 Ready")
