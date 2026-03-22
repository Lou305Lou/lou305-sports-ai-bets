
import io
import os
import math
import json
from datetime import datetime, date
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st


# =========================
# CONFIG
# =========================
APP_TITLE = "Sports AI Betting Dashboard — V16"
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

BET_LOG_PATH = DATA_DIR / "bet_log.csv"
SETTINGS_PATH = DATA_DIR / "settings.json"
MODEL_MEMORY_PATH = DATA_DIR / "model_memory.csv"


# =========================
# PAGE SETUP
# =========================
st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title(APP_TITLE)
st.caption("All-market betting AI + auto-save + tracking + CLV + consensus parlays + self-learning foundation")


# =========================
# HELPERS
# =========================
def safe_read_csv(path: Path, columns=None):
    try:
        if path.exists():
            return pd.read_csv(path)
    except Exception:
        pass
    return pd.DataFrame(columns=columns if columns is not None else [])


def safe_to_numeric(series, default=np.nan):
    try:
        return pd.to_numeric(series, errors="coerce")
    except Exception:
        return pd.Series([default] * len(series))


def american_to_decimal(odds):
    try:
        odds = float(odds)
        if odds > 0:
            return 1 + odds / 100.0
        return 1 + 100.0 / abs(odds)
    except Exception:
        return np.nan


def american_implied_prob(odds):
    try:
        odds = float(odds)
        if odds > 0:
            return 100.0 / (odds + 100.0)
        return abs(odds) / (abs(odds) + 100.0)
    except Exception:
        return np.nan


def kelly_fraction(p, odds_american):
    try:
        p = float(p)
        dec = american_to_decimal(odds_american)
        if np.isnan(dec) or dec <= 1:
            return 0.0
        b = dec - 1
        q = 1 - p
        k = (b * p - q) / b
        return max(0.0, k)
    except Exception:
        return 0.0


def normalize_text(x):
    try:
        return str(x).strip()
    except Exception:
        return ""


def ensure_columns(df: pd.DataFrame, required_cols):
    out = df.copy()
    for c in required_cols:
        if c not in out.columns:
            out[c] = np.nan
    return out


def letter_grade(score):
    try:
        s = float(score)
    except Exception:
        return "D"
    if s >= 85:
        return "A"
    if s >= 75:
        return "B"
    if s >= 65:
        return "C"
    return "D"


def tier_label(score):
    try:
        s = float(score)
    except Exception:
        return "Tier 4"
    if s >= 85:
        return "Tier 1"
    if s >= 75:
        return "Tier 2"
    if s >= 65:
        return "Tier 3"
    return "Tier 4"


def score_to_emoji(score):
    try:
        s = float(score)
    except Exception:
        return "⚪"
    if s >= 85:
        return "🟢"
    if s >= 75:
        return "🟡"
    if s >= 65:
        return "🟠"
    return "⚪"


def pct(x):
    try:
        return f"{100 * float(x):.1f}%"
    except Exception:
        return "—"


def plus_money_range_ok(odds, min_odds=-200, max_odds=150):
    try:
        odds = float(odds)
        return min_odds <= odds <= max_odds
    except Exception:
        return False


def compute_ev(prob, odds):
    try:
        dec = american_to_decimal(odds)
        if np.isnan(dec):
            return np.nan
        return prob * (dec - 1) - (1 - prob)
    except Exception:
        return np.nan


def load_settings():
    defaults = {
        "bankroll": 1000.0,
        "kelly_multiplier": 0.35,
        "max_unit": 2.0,
        "base_unit_pct": 0.01,
        "min_consensus": 3,
        "min_parlay_legs": 2,
        "max_parlay_legs": 4,
        "default_odds_min": -200,
        "default_odds_max": 150,
    }
    try:
        if SETTINGS_PATH.exists():
            with open(SETTINGS_PATH, "r") as f:
                saved = json.load(f)
            defaults.update(saved)
    except Exception:
        pass
    return defaults


def save_settings(settings):
    try:
        with open(SETTINGS_PATH, "w") as f:
            json.dump(settings, f, indent=2)
    except Exception:
        pass


def load_model_memory():
    cols = [
        "date",
        "market",
        "sport",
        "book",
        "bet_type",
        "selection",
        "odds",
        "model_prob",
        "closing_odds",
        "result",
        "units",
        "profit_units",
    ]
    return safe_read_csv(MODEL_MEMORY_PATH, cols)


def save_model_memory(df):
    try:
        df.to_csv(MODEL_MEMORY_PATH, index=False)
    except Exception:
        pass


def load_bet_log():
    cols = [
        "bet_id",
        "date_added",
        "sport",
        "event",
        "market",
        "bet_type",
        "selection",
        "book",
        "odds",
        "closing_odds",
        "projection",
        "line",
        "edge",
        "model_prob",
        "implied_prob",
        "ev",
        "score",
        "consensus",
        "tier",
        "recommended_units",
        "result",
        "profit_units",
        "notes",
    ]
    return safe_read_csv(BET_LOG_PATH, cols)


def save_bet_log(df):
    try:
        df.to_csv(BET_LOG_PATH, index=False)
    except Exception:
        pass


def build_bet_id(row):
    parts = [
        normalize_text(row.get("sport", "")),
        normalize_text(row.get("event", "")),
        normalize_text(row.get("market", "")),
        normalize_text(row.get("bet_type", "")),
        normalize_text(row.get("selection", "")),
        normalize_text(row.get("book", "")),
        normalize_text(row.get("line", "")),
        normalize_text(row.get("odds", "")),
    ]
    return "|".join(parts)


def clean_input_df(df: pd.DataFrame):
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]

    rename_map = {
        "game": "event",
        "matchup": "event",
        "player": "selection",
        "name": "selection",
        "sportsbook": "book",
        "price": "odds",
        "probability": "model_prob",
        "hit_rate": "model_prob",
        "confidence": "score",
        "market_type": "market",
        "pick_type": "bet_type",
        "proj": "projection",
        "team": "selection",
        "side": "selection",
        "points": "line",
        "prop_line": "line",
    }
    df = df.rename(columns={c: rename_map[c] for c in df.columns if c in rename_map})

    required = [
        "sport", "event", "market", "bet_type", "selection", "book",
        "odds", "projection", "line", "edge", "model_prob", "score", "consensus"
    ]
    df = ensure_columns(df, required)

    numeric_cols = ["odds", "projection", "line", "edge", "model_prob", "score", "consensus"]
    for c in numeric_cols:
        df[c] = safe_to_numeric(df[c])

    if df["model_prob"].dropna().max() > 1.5:
        df["model_prob"] = df["model_prob"] / 100.0

    df["implied_prob"] = df["odds"].apply(american_implied_prob)
    if df["edge"].isna().all() and ("projection" in df.columns and "line" in df.columns):
        df["edge"] = df["projection"] - df["line"]

    if df["score"].isna().all():
        comp = (
            df["model_prob"].fillna(0) * 55
            + (df["edge"].fillna(0).clip(lower=0) * 4)
            + (df["consensus"].fillna(0) * 6)
            + (df["odds"].apply(lambda x: 10 if plus_money_range_ok(x, -200, 150) else 0).fillna(0))
        )
        df["score"] = comp.clip(0, 99)

    if df["consensus"].isna().all():
        df["consensus"] = np.where(df["score"] >= 85, 5, np.where(df["score"] >= 75, 4, np.where(df["score"] >= 65, 3, 2)))

    df["ev"] = df.apply(lambda r: compute_ev(r.get("model_prob", np.nan), r.get("odds", np.nan)), axis=1)
    df["tier"] = df["score"].apply(tier_label)
    df["grade"] = df["score"].apply(letter_grade)
    df["bet_id"] = df.apply(build_bet_id, axis=1)

    df["date_added"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return df


def recommend_units(row, bankroll, kelly_multiplier=0.35, base_unit_pct=0.01, max_unit=2.0, memory_df=None):
    p = row.get("model_prob", np.nan)
    odds = row.get("odds", np.nan)
    score = row.get("score", 0)
    consensus = row.get("consensus", 0)

    k = kelly_fraction(p, odds)
    units = k * kelly_multiplier * (bankroll * base_unit_pct)

    if score >= 85:
        units *= 1.25
    elif score >= 75:
        units *= 1.10
    elif score < 65:
        units *= 0.70

    if consensus >= 5:
        units *= 1.15
    elif consensus <= 2:
        units *= 0.80

    # self-learning adjustment
    adj = 1.0
    if memory_df is not None and len(memory_df) > 0:
        m = memory_df.copy()
        market = normalize_text(row.get("market", "")).lower()
        sport = normalize_text(row.get("sport", "")).lower()
        seg = m[
            m["market"].astype(str).str.lower().eq(market) &
            m["sport"].astype(str).str.lower().eq(sport) &
            m["result"].notna()
        ]
        if len(seg) >= 15:
            roi = seg["profit_units"].sum() / max(seg["units"].sum(), 1e-9)
            if roi > 0.08:
                adj = 1.10
            elif roi < -0.08:
                adj = 0.85
    units *= adj

    units = max(0.1, min(max_unit, units))
    return round(units, 2)


def format_pick_card(row):
    grade = row.get("grade", "D")
    emoji = score_to_emoji(row.get("score", 0))
    return f"""#{int(row.name)+1} {normalize_text(row.get("selection", ""))} — {normalize_text(row.get("bet_type", ""))}
{normalize_text(row.get("event", ""))} • {normalize_text(row.get("market", ""))} • {normalize_text(row.get("book", ""))}
Projection: {row.get("projection", np.nan):.2f} | Edge: {row.get("edge", np.nan):.2f} | Odds: {int(row.get("odds", 0)) if pd.notna(row.get("odds")) else "—"} | Hit %: {pct(row.get("model_prob", np.nan))} | EV Edge: {pct(row.get("ev", np.nan))} | Score: {row.get("score", np.nan):.1f} ({emoji} {grade})
Tier: {row.get("tier", "Tier 4")} | Units: {row.get("recommended_units", np.nan):.2f}u | Consensus: {int(row.get("consensus", 0))}/5"""


def add_recommended_units(df, settings, memory_df):
    df = df.copy()
    df["recommended_units"] = df.apply(
        lambda r: recommend_units(
            r,
            bankroll=settings["bankroll"],
            kelly_multiplier=settings["kelly_multiplier"],
            base_unit_pct=settings["base_unit_pct"],
            max_unit=settings["max_unit"],
            memory_df=memory_df,
        ),
        axis=1,
    )
    return df


def qualify_plays(df, settings):
    if len(df) == 0:
        return df.copy()
    out = df.copy()
    out = out[
        (out["consensus"] >= settings["min_consensus"]) &
        (out["score"] >= 65) &
        (out["odds"] >= settings["default_odds_min"]) &
        (out["odds"] <= settings["default_odds_max"])
    ].copy()
    out = out.sort_values(["score", "ev", "model_prob"], ascending=[False, False, False])
    return out


def market_buckets(df):
    labels = []
    for m in df.get("market", pd.Series(dtype=str)).astype(str).str.lower():
        if "player" in m or "prop" in m:
            labels.append("Player Props")
        elif "spread" in m:
            labels.append("Spreads")
        elif "total" in m:
            labels.append("Totals")
        elif "moneyline" in m or "mainline" in m or "ml" == m:
            labels.append("Moneylines")
        else:
            labels.append("Other")
    out = df.copy()
    out["market_bucket"] = labels
    return out


def build_consensus_parlays(df, min_legs=2, max_legs=4, min_parlay_odds=200):
    if len(df) == 0:
        return pd.DataFrame()

    df = df.copy().head(12)
    rows = []

    for leg_count in range(min_legs, max_legs + 1):
        combos = list(__import__("itertools").combinations(df.index.tolist(), leg_count))
        for combo in combos:
            legs = df.loc[list(combo)].copy()

            # Avoid same event duplicates when possible
            if legs["event"].nunique() < len(legs):
                continue

            dec_odds = legs["odds"].apply(american_to_decimal)
            if dec_odds.isna().any():
                continue

            parlay_dec = dec_odds.prod()
            parlay_american = int(round((parlay_dec - 1) * 100)) if parlay_dec >= 2 else int(round(-100 / (parlay_dec - 1)))
            if parlay_american < min_parlay_odds:
                continue

            joint_prob = legs["model_prob"].clip(lower=0.01, upper=0.99).prod()
            implied = american_implied_prob(parlay_american)
            ev = compute_ev(joint_prob, parlay_american)
            score = (
                legs["score"].mean() * 0.55
                + (legs["consensus"].mean() / 5.0) * 20
                + min(15, max(0, (joint_prob - implied) * 100))
            )

            rows.append({
                "legs": len(legs),
                "parlay_odds": parlay_american,
                "joint_prob": joint_prob,
                "implied_prob": implied,
                "ev": ev,
                "score": round(score, 1),
                "summary": " + ".join(legs["selection"].astype(str) + " " + legs["bet_type"].astype(str)),
                "events": " | ".join(legs["event"].astype(str)),
            })

    out = pd.DataFrame(rows)
    if len(out) == 0:
        return out
    out = out.sort_values(["score", "ev", "joint_prob"], ascending=[False, False, False]).drop_duplicates(subset=["summary"])
    return out.head(10)


def append_new_bets_to_log(candidates_df, bet_log_df):
    if len(candidates_df) == 0:
        return bet_log_df.copy(), 0

    base = bet_log_df.copy()
    if "bet_id" not in base.columns:
        base["bet_id"] = ""

    new_rows = candidates_df.copy()
    new_rows["bet_id"] = new_rows.apply(build_bet_id, axis=1)

    existing = set(base["bet_id"].astype(str).tolist())
    to_add = new_rows[~new_rows["bet_id"].astype(str).isin(existing)].copy()

    if len(to_add) == 0:
        return base, 0

    keep_cols = [
        "bet_id", "date_added", "sport", "event", "market", "bet_type", "selection", "book", "odds",
        "closing_odds", "projection", "line", "edge", "model_prob", "implied_prob", "ev", "score",
        "consensus", "tier", "recommended_units", "result", "profit_units", "notes"
    ]
    to_add = ensure_columns(to_add, keep_cols)
    updated = pd.concat([base, to_add[keep_cols]], ignore_index=True)
    return updated, len(to_add)


def calculate_profit_units(result, odds, units):
    try:
        odds = float(odds)
        units = float(units)
        result = str(result).strip().lower()
        if result == "win":
            if odds > 0:
                return units * odds / 100.0
            return units * 100.0 / abs(odds)
        if result == "loss":
            return -units
        if result in {"push", "void"}:
            return 0.0
    except Exception:
        pass
    return np.nan


def update_bet_outcomes(log_df):
    out = log_df.copy()
    out["profit_units"] = out.apply(
        lambda r: calculate_profit_units(r.get("result", np.nan), r.get("odds", np.nan), r.get("recommended_units", np.nan)),
        axis=1,
    )
    return out


def clv_value(odds, closing_odds):
    try:
        open_ip = american_implied_prob(odds)
        close_ip = american_implied_prob(closing_odds)
        return close_ip - open_ip
    except Exception:
        return np.nan


def summary_metrics(log_df):
    settled = log_df[log_df["result"].astype(str).str.lower().isin(["win", "loss", "push", "void"])].copy()
    pending = log_df[~log_df.index.isin(settled.index)].copy()

    total_bets = len(log_df)
    settled_count = len(settled)
    wins = (settled["result"].astype(str).str.lower() == "win").sum()
    losses = (settled["result"].astype(str).str.lower() == "loss").sum()
    pushes = (settled["result"].astype(str).str.lower().isin(["push", "void"])).sum()
    units = settled["profit_units"].fillna(0).sum()
    stake = settled["recommended_units"].fillna(0).sum()
    roi = units / stake if stake else 0.0

    clv_df = settled.dropna(subset=["closing_odds"]).copy()
    if len(clv_df) > 0:
        clv_df["clv"] = clv_df.apply(lambda r: clv_value(r.get("odds", np.nan), r.get("closing_odds", np.nan)), axis=1)
        avg_clv = clv_df["clv"].mean()
    else:
        avg_clv = np.nan

    return {
        "total_bets": total_bets,
        "settled": settled_count,
        "pending": len(pending),
        "wins": int(wins),
        "losses": int(losses),
        "pushes": int(pushes),
        "profit_units": units,
        "roi": roi,
        "avg_clv": avg_clv,
    }


def export_download(df, filename, label):
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(label, csv, file_name=filename, mime="text/csv")


# =========================
# SIDEBAR
# =========================
settings = load_settings()
memory_df = load_model_memory()
bet_log = update_bet_outcomes(load_bet_log())

with st.sidebar:
    st.header("V16 Controls")

    settings["bankroll"] = st.number_input("Bankroll", min_value=100.0, value=float(settings["bankroll"]), step=50.0)
    settings["kelly_multiplier"] = st.slider("Kelly Multiplier", 0.05, 1.00, float(settings["kelly_multiplier"]), 0.05)
    settings["base_unit_pct"] = st.slider("Base Unit % of Bankroll", 0.0025, 0.05, float(settings["base_unit_pct"]), 0.0025)
    settings["max_unit"] = st.slider("Max Units Per Bet", 0.5, 5.0, float(settings["max_unit"]), 0.25)
    settings["min_consensus"] = st.selectbox("Minimum AI Consensus", [2, 3, 4, 5], index=[2, 3, 4, 5].index(int(settings["min_consensus"])))
    settings["default_odds_min"] = st.number_input("Minimum Odds", value=int(settings["default_odds_min"]), step=5)
    settings["default_odds_max"] = st.number_input("Maximum Odds", value=int(settings["default_odds_max"]), step=5)
    settings["min_parlay_legs"] = st.selectbox("Min Parlay Legs", [2, 3], index=0 if int(settings["min_parlay_legs"]) == 2 else 1)
    settings["max_parlay_legs"] = st.selectbox("Max Parlay Legs", [3, 4, 5], index=[3, 4, 5].index(int(settings["max_parlay_legs"])))
    if st.button("Save Settings"):
        save_settings(settings)
        st.success("Settings saved.")

    st.divider()
    st.markdown("**Auto-Save Status**")
    st.write("Bet log:", "Ready")
    st.write("Model memory:", "Ready")


# =========================
# INPUT AREA
# =========================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Upload + AI Board",
    "Best Bets",
    "Consensus Parlays",
    "Bet Tracker + CLV",
    "Self-Learning Engine",
])

with tab1:
    st.subheader("Upload Market Data")
    st.write("Upload a CSV containing your betting candidates. Flexible columns are supported.")
    uploaded = st.file_uploader("Upload CSV", type=["csv"])

    sample_cols = [
        "sport", "event", "market", "bet_type", "selection", "book",
        "odds", "projection", "line", "edge", "model_prob", "score", "consensus"
    ]
    sample_df = pd.DataFrame([
        ["NBA", "Warriors vs Lakers", "player props", "Over 27.5 points", "Stephen Curry", "DraftKings", -115, 31.8, 27.5, 4.3, 0.66, 82, 5],
        ["NBA", "Warriors vs Lakers", "totals", "Over 234.5", "Game Total", "FanDuel", -110, 239.2, 234.5, 4.7, 0.58, 74, 4],
        ["NBA", "Heat vs Celtics", "spreads", "Celtics -6.5", "Boston Celtics", "BetMGM", -108, -8.1, -6.5, 1.6, 0.57, 71, 4],
        ["NHL", "Rangers vs Leafs", "moneyline", "Moneyline", "Rangers", "Caesars", 118, np.nan, np.nan, np.nan, 0.49, 67, 3],
    ], columns=sample_cols)

    with st.expander("See sample input format"):
        st.dataframe(sample_df, use_container_width=True)
        export_download(sample_df, "v16_sample_input.csv", "Download sample CSV")

    input_df = pd.DataFrame()

    if uploaded is not None:
        try:
            raw = pd.read_csv(uploaded)
            input_df = clean_input_df(raw)
            input_df = add_recommended_units(input_df, settings, memory_df)
            input_df = market_buckets(input_df)
            st.success(f"Loaded {len(input_df)} rows.")
        except Exception as e:
            st.error(f"Could not read CSV: {e}")

    if len(input_df) > 0:
        c1, c2, c3 = st.columns(3)
        with c1:
            sports = ["All"] + sorted([x for x in input_df["sport"].dropna().astype(str).unique().tolist()])
            sport_filter = st.selectbox("Sport", sports)
        with c2:
            mkts = ["All"] + sorted([x for x in input_df["market_bucket"].dropna().astype(str).unique().tolist()])
            market_filter = st.selectbox("Market Bucket", mkts)
        with c3:
            books = ["All"] + sorted([x for x in input_df["book"].dropna().astype(str).unique().tolist()])
            book_filter = st.selectbox("Book", books)

        filtered = input_df.copy()
        if sport_filter != "All":
            filtered = filtered[filtered["sport"].astype(str) == sport_filter]
        if market_filter != "All":
            filtered = filtered[filtered["market_bucket"].astype(str) == market_filter]
        if book_filter != "All":
            filtered = filtered[filtered["book"].astype(str) == book_filter]

        st.subheader("AI Board")
        st.dataframe(
            filtered[
                ["sport", "event", "market_bucket", "selection", "bet_type", "book", "odds", "projection", "line", "edge", "model_prob", "ev", "score", "consensus", "recommended_units"]
            ].sort_values(["score", "ev"], ascending=[False, False]),
            use_container_width=True,
        )

        if st.button("Auto-Save Qualified Bets To Tracker"):
            qualified = qualify_plays(filtered, settings)
            updated_log, added = append_new_bets_to_log(qualified, bet_log)
            save_bet_log(updated_log)
            st.success(f"Auto-saved {added} new bets.")
            st.rerun()


with tab2:
    st.subheader("Best Bets")
    if uploaded is None:
        st.info("Upload a CSV in the first tab to generate the V16 board.")
    else:
        qualified = qualify_plays(input_df, settings)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Qualified Bets", len(qualified))
        c2.metric("Avg Score", f"{qualified['score'].mean():.1f}" if len(qualified) else "—")
        c3.metric("Avg EV", pct(qualified["ev"].mean()) if len(qualified) else "—")
        c4.metric("Avg Hit Rate", pct(qualified["model_prob"].mean()) if len(qualified) else "—")

        if len(qualified) == 0:
            st.warning("No plays met the V16 filters. Try loosening consensus or odds range.")
        else:
            st.dataframe(
                qualified[
                    ["sport", "event", "market_bucket", "selection", "bet_type", "book", "odds", "edge", "model_prob", "ev", "score", "consensus", "tier", "recommended_units"]
                ],
                use_container_width=True,
            )

            st.subheader("Top Pick Cards")
            top_cards = qualified.head(10).reset_index(drop=True)
            for i, row in top_cards.iterrows():
                st.code(format_pick_card(row))


with tab3:
    st.subheader("Consensus Parlays")
    if uploaded is None:
        st.info("Upload a CSV in the first tab to generate parlays.")
    else:
        qualified = qualify_plays(input_df, settings)
        parlays = build_consensus_parlays(
            qualified,
            min_legs=int(settings["min_parlay_legs"]),
            max_legs=int(settings["max_parlay_legs"]),
            min_parlay_odds=200,
        )
        if len(parlays) == 0:
            st.warning("No qualifying parlays found.")
        else:
            st.dataframe(parlays, use_container_width=True)
            export_download(parlays, "v16_consensus_parlays.csv", "Download parlays CSV")


with tab4:
    st.subheader("Bet Tracker + CLV")
    bet_log = update_bet_outcomes(load_bet_log())
    metrics = summary_metrics(bet_log)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Bets", metrics["total_bets"])
    c2.metric("Record", f'{metrics["wins"]}-{metrics["losses"]}-{metrics["pushes"]}')
    c3.metric("Profit (u)", f'{metrics["profit_units"]:.2f}')
    c4.metric("ROI", f'{metrics["roi"]*100:.1f}%')

    c5, c6 = st.columns(2)
    c5.metric("Pending", metrics["pending"])
    c6.metric("Avg CLV", f'{metrics["avg_clv"]*100:.2f}%' if pd.notna(metrics["avg_clv"]) else "—")

    if len(bet_log) == 0:
        st.info("No tracked bets yet. Use Auto-Save in the first tab.")
    else:
        editable = bet_log.copy()
        editable = ensure_columns(editable, ["closing_odds", "result", "notes"])
        edited = st.data_editor(
            editable,
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "result": st.column_config.SelectboxColumn("result", options=["", "win", "loss", "push", "void"]),
            },
            key="bet_log_editor",
        )

        if st.button("Save Tracker Changes"):
            edited = update_bet_outcomes(edited)
            save_bet_log(edited)

            # push settled bets to memory
            settled = edited[edited["result"].astype(str).str.lower().isin(["win", "loss", "push", "void"])].copy()
            mem = load_model_memory()

            if len(settled) > 0:
                mem_add = settled[[
                    "market", "sport", "book", "bet_type", "selection", "odds", "model_prob",
                    "closing_odds", "result", "recommended_units", "profit_units"
                ]].copy()
                mem_add = mem_add.rename(columns={"recommended_units": "units"})
                mem_add["date"] = datetime.now().strftime("%Y-%m-%d")
                mem = pd.concat([mem, mem_add], ignore_index=True)
                mem = mem.drop_duplicates(subset=["date", "market", "sport", "selection", "odds", "result"], keep="last")
                save_model_memory(mem)

            st.success("Tracker and model memory updated.")
            st.rerun()

        export_download(bet_log, "v16_bet_log.csv", "Download bet log CSV")


with tab5:
    st.subheader("Self-Learning Engine Foundation")
    memory_df = load_model_memory()

    if len(memory_df) == 0:
        st.info("No settled history yet. Once tracked bets are graded, V16 will start adapting unit sizing by market and sport.")
    else:
        memory_df = ensure_columns(memory_df, ["units", "profit_units", "result", "sport", "market"])
        settled = memory_df[memory_df["result"].astype(str).str.lower().isin(["win", "loss", "push", "void"])].copy()

        overall_roi = settled["profit_units"].fillna(0).sum() / max(settled["units"].fillna(0).sum(), 1e-9)
        win_rate = (settled["result"].astype(str).str.lower() == "win").mean() if len(settled) else 0.0

        c1, c2, c3 = st.columns(3)
        c1.metric("Settled Samples", len(settled))
        c2.metric("Win Rate", f"{win_rate*100:.1f}%")
        c3.metric("ROI", f"{overall_roi*100:.1f}%")

        sport_market = (
            settled.groupby(["sport", "market"], dropna=False)
            .agg(
                bets=("selection", "count"),
                units=("units", "sum"),
                profit_units=("profit_units", "sum"),
            )
            .reset_index()
        )
        sport_market["roi"] = sport_market["profit_units"] / sport_market["units"].replace(0, np.nan)
        sport_market["unit_adjustment_signal"] = np.where(
            sport_market["roi"] > 0.08, "Increase slightly",
            np.where(sport_market["roi"] < -0.08, "Reduce slightly", "Hold steady")
        )

        st.dataframe(sport_market.sort_values(["roi", "bets"], ascending=[False, False]), use_container_width=True)

        st.markdown("**How V16 learns**")
        st.write(
            "V16 adjusts recommended units by sport + market when there is enough settled history. "
            "Strong positive ROI slightly increases sizing, while negative ROI reduces exposure."
        )

        export_download(memory_df, "v16_model_memory.csv", "Download model memory CSV")
