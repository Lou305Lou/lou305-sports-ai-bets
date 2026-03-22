
import io
import json
import math
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

APP_TITLE = "Sports AI Betting Dashboard — V22"
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
BET_LOG_PATH = DATA_DIR / "bet_log.csv"
SETTINGS_PATH = DATA_DIR / "settings_v22.json"


# -----------------------------
# Helpers: persistence
# -----------------------------
def load_settings():
    default = {
        "bankroll": 1000.0,
        "base_unit_pct": 1.0,
        "kelly_fraction": 0.35,
        "max_single_bet_pct": 2.5,
        "max_game_exposure_pct": 6.0,
        "max_book_exposure_pct": 15.0,
        "odds_min": -200,
        "odds_max": 150,
        "min_consensus": 3,
        "min_ev_edge": 2.0,
        "min_hit_rate": 53.0,
        "target_parlay_odds": 200,
    }
    if SETTINGS_PATH.exists():
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            default.update(saved)
        except Exception:
            pass
    return default


def save_settings(settings):
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)


def load_bet_log():
    if BET_LOG_PATH.exists():
        try:
            df = pd.read_csv(BET_LOG_PATH)
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
            return df
        except Exception:
            pass
    cols = [
        "timestamp", "bet_id", "sport", "league", "game", "market", "bet_name", "side",
        "book", "odds", "line", "projection", "model_prob", "implied_prob", "edge",
        "ev_edge", "score", "consensus", "recommended_units", "result", "pnl", "clv_close",
        "clv_delta", "status"
    ]
    return pd.DataFrame(columns=cols)


def save_bet_log(df):
    df.to_csv(BET_LOG_PATH, index=False)


# -----------------------------
# Odds math
# -----------------------------
def american_to_decimal(odds):
    try:
        odds = float(odds)
        if odds > 0:
            return 1 + odds / 100
        return 1 + 100 / abs(odds)
    except Exception:
        return np.nan


def implied_prob_from_american(odds):
    try:
        odds = float(odds)
        if odds > 0:
            return 100 / (odds + 100)
        return abs(odds) / (abs(odds) + 100)
    except Exception:
        return np.nan


def decimal_to_american(decimal_odds):
    try:
        d = float(decimal_odds)
        if d >= 2:
            return int(round((d - 1) * 100))
        return int(round(-100 / (d - 1)))
    except Exception:
        return np.nan


def expected_value_pct(model_prob, odds):
    try:
        p = float(model_prob)
        dec = american_to_decimal(odds)
        return ((p * dec) - 1.0) * 100
    except Exception:
        return np.nan


def kelly_units(bankroll, base_unit_pct, win_prob, odds, kelly_fraction=0.35, max_single_bet_pct=2.5):
    try:
        bankroll = float(bankroll)
        base_unit_pct = float(base_unit_pct) / 100.0
        max_single_bet_pct = float(max_single_bet_pct) / 100.0
        p = float(win_prob)
        dec = american_to_decimal(odds)
        b = dec - 1
        q = 1 - p
        kelly = max(((b * p) - q) / b, 0)
        stake_pct = min(kelly * float(kelly_fraction), max_single_bet_pct)
        unit_size = bankroll * base_unit_pct
        units = (bankroll * stake_pct) / unit_size if unit_size > 0 else 0
        return max(round(units, 2), 0.0)
    except Exception:
        return 0.0


# -----------------------------
# Data standardization
# -----------------------------
CANONICAL_COLS = {
    "sport": ["sport"],
    "league": ["league"],
    "game": ["game", "matchup", "event", "event_name"],
    "market": ["market", "bet_type"],
    "bet_name": ["bet_name", "selection", "player", "team", "name", "prop_name"],
    "side": ["side", "pick", "direction"],
    "book": ["book", "sportsbook"],
    "odds": ["odds", "price", "american_odds"],
    "line": ["line", "point", "total", "spread"],
    "projection": ["projection", "proj", "model_projection"],
    "model_prob": ["model_prob", "win_prob", "hit_rate", "probability"],
    "start_time": ["start_time", "commence_time", "game_time"],
    "close_odds": ["close_odds", "closing_odds"],
}


def find_matching_col(df, options):
    lower_map = {c.lower().strip(): c for c in df.columns}
    for opt in options:
        if opt in lower_map:
            return lower_map[opt]
    return None


def standardize_input_df(df):
    out = pd.DataFrame()
    for canonical, options in CANONICAL_COLS.items():
        src = find_matching_col(df, options)
        if src:
            out[canonical] = df[src]
        else:
            out[canonical] = np.nan

    if out["side"].isna().all():
        out["side"] = out["bet_name"]

    if out["sport"].isna().all():
        out["sport"] = "Unknown"
    if out["league"].isna().all():
        out["league"] = "Unknown"
    if out["market"].isna().all():
        out["market"] = "Unknown"
    if out["book"].isna().all():
        out["book"] = "Unknown"
    if out["game"].isna().all():
        out["game"] = "Unknown Game"

    out["odds"] = pd.to_numeric(out["odds"], errors="coerce")
    out["line"] = pd.to_numeric(out["line"], errors="coerce")
    out["projection"] = pd.to_numeric(out["projection"], errors="coerce")
    out["model_prob"] = pd.to_numeric(out["model_prob"], errors="coerce")

    # Detect hit rate percentages entered as 58.2 instead of 0.582
    out.loc[out["model_prob"] > 1, "model_prob"] = out.loc[out["model_prob"] > 1, "model_prob"] / 100.0

    out["implied_prob"] = out["odds"].apply(implied_prob_from_american)

    # Projection-based probability fallback
    needs_prob = out["model_prob"].isna()
    fallback_edge = (out["projection"] - out["line"]).abs()
    out.loc[needs_prob, "model_prob"] = (0.50 + np.clip(fallback_edge[needs_prob] * 0.03, 0, 0.2)).fillna(0.50)

    out["edge"] = ((out["model_prob"] - out["implied_prob"]) * 100).round(2)
    out["ev_edge"] = out.apply(lambda r: expected_value_pct(r["model_prob"], r["odds"]), axis=1).round(2)

    if "start_time" in out.columns:
        out["start_time"] = pd.to_datetime(out["start_time"], errors="coerce")

    out["close_odds"] = pd.to_numeric(out["close_odds"], errors="coerce")
    return out


# -----------------------------
# V22 scoring engine
# -----------------------------
def build_v22_scores(df):
    x = df.copy()

    x["hit_rate_pct"] = x["model_prob"] * 100
    x["abs_edge"] = x["edge"].clip(lower=0)
    x["abs_ev"] = x["ev_edge"].clip(lower=0)

    # Model 1: probability model
    x["m1"] = np.select(
        [x["hit_rate_pct"] >= 60, x["hit_rate_pct"] >= 57, x["hit_rate_pct"] >= 54],
        [1, 1, 1],
        default=0
    )

    # Model 2: edge model
    x["m2"] = np.select(
        [x["abs_edge"] >= 7, x["abs_edge"] >= 4, x["abs_edge"] >= 2],
        [1, 1, 1],
        default=0
    )

    # Model 3: EV model
    x["m3"] = np.select(
        [x["abs_ev"] >= 10, x["abs_ev"] >= 6, x["abs_ev"] >= 2],
        [1, 1, 1],
        default=0
    )

    # Model 4: price discipline model
    x["m4"] = ((x["odds"] >= -200) & (x["odds"] <= 150)).astype(int)

    # Model 5: CLV proxy / market sharpness model
    x["price_quality"] = np.select(
        [x["book"].astype(str).str.contains("pinnacle|circa|betcris", case=False, na=False),
         x["book"].astype(str).str.contains("draftkings|fanduel|caesars|betmgm", case=False, na=False)],
        [1.0, 0.75],
        default=0.50
    )
    x["m5"] = ((x["price_quality"] >= 0.75) & (x["abs_edge"] >= 1.5)).astype(int)

    x["consensus"] = x[["m1", "m2", "m3", "m4", "m5"]].sum(axis=1)

    # Weighted score
    x["score"] = (
        x["hit_rate_pct"] * 0.34 +
        x["abs_edge"] * 3.2 +
        x["abs_ev"] * 1.9 +
        x["consensus"] * 6.0 +
        x["price_quality"] * 6.0
    ).round(1)

    x["confidence_tier"] = np.select(
        [x["consensus"] >= 5, x["consensus"] == 4, x["consensus"] == 3],
        ["A", "B", "C"],
        default="D"
    )
    return x


def add_recommended_units(df, settings):
    x = df.copy()
    x["recommended_units"] = x.apply(
        lambda r: kelly_units(
            bankroll=settings["bankroll"],
            base_unit_pct=settings["base_unit_pct"],
            win_prob=r["model_prob"],
            odds=r["odds"],
            kelly_fraction=settings["kelly_fraction"],
            max_single_bet_pct=settings["max_single_bet_pct"],
        ),
        axis=1
    )
    return x


def enforce_guardrails(df, settings):
    x = df.copy()
    x["allowed"] = True
    bankroll = settings["bankroll"]
    unit_dollars = bankroll * (settings["base_unit_pct"] / 100.0)
    x["stake_dollars"] = x["recommended_units"] * unit_dollars

    max_game = bankroll * (settings["max_game_exposure_pct"] / 100.0)
    max_book = bankroll * (settings["max_book_exposure_pct"] / 100.0)

    game_running = {}
    book_running = {}

    allowed_flags = []
    reasons = []
    for _, row in x.sort_values(["score", "ev_edge"], ascending=False).iterrows():
        g = str(row["game"])
        b = str(row["book"])
        stake = float(row["stake_dollars"])

        game_total = game_running.get(g, 0.0) + stake
        book_total = book_running.get(b, 0.0) + stake

        ok = True
        why = []
        if game_total > max_game:
            ok = False
            why.append("game exposure cap")
        if book_total > max_book:
            ok = False
            why.append("book exposure cap")

        if ok:
            game_running[g] = game_total
            book_running[b] = book_total

        allowed_flags.append(ok)
        reasons.append(", ".join(why) if why else "")

    x["allowed"] = allowed_flags
    x["blocked_reason"] = reasons
    return x


def filter_qualified(df, settings):
    x = df.copy()
    return x[
        (x["odds"] >= settings["odds_min"]) &
        (x["odds"] <= settings["odds_max"]) &
        (x["consensus"] >= settings["min_consensus"]) &
        (x["ev_edge"] >= settings["min_ev_edge"]) &
        (x["hit_rate_pct"] >= settings["min_hit_rate"]) &
        (x["allowed"])
    ].copy()


def build_parlay_candidates(df, min_decimal_target=3.0, max_legs=4):
    if df.empty:
        return pd.DataFrame()

    pool = df.sort_values(["score", "ev_edge"], ascending=False).head(12).copy()
    records = []

    rows = pool.to_dict("records")
    for leg_count in range(2, max_legs + 1):
        # lightweight combination builder
        import itertools
        for combo in itertools.combinations(rows, leg_count):
            games = [str(r["game"]) for r in combo]
            if len(set(games)) != len(games):
                continue  # avoid same-game parlays by default

            decs = [american_to_decimal(r["odds"]) for r in combo]
            probs = [float(r["model_prob"]) for r in combo]
            parlay_decimal = np.prod(decs)
            if parlay_decimal < min_decimal_target:
                continue

            naive_prob = np.prod(probs)
            ev_pct = (naive_prob * parlay_decimal - 1) * 100
            avg_score = np.mean([float(r["score"]) for r in combo])

            records.append({
                "legs": leg_count,
                "bets": " | ".join([f'{r["bet_name"]} ({int(r["odds"])})' for r in combo]),
                "games": " | ".join(games),
                "parlay_odds": decimal_to_american(parlay_decimal),
                "parlay_decimal": round(parlay_decimal, 2),
                "naive_hit_rate_pct": round(naive_prob * 100, 2),
                "ev_edge": round(ev_pct, 2),
                "avg_score": round(avg_score, 1),
            })

    if not records:
        return pd.DataFrame()

    parlays = pd.DataFrame(records).sort_values(
        ["ev_edge", "avg_score", "naive_hit_rate_pct"],
        ascending=False
    )
    return parlays.head(15)


def grade_bet_pnl(odds, units, result):
    if pd.isna(odds) or pd.isna(units):
        return np.nan
    odds = float(odds)
    units = float(units)
    result = str(result).strip().lower()
    if result == "win":
        if odds > 0:
            return round(units * (odds / 100), 2)
        return round(units * (100 / abs(odds)), 2)
    if result == "loss":
        return round(-units, 2)
    if result == "push":
        return 0.0
    return np.nan


def add_clv_metrics(log_df):
    df = log_df.copy()
    if "clv_close" not in df.columns:
        df["clv_close"] = np.nan
    df["clv_delta"] = np.where(
        df["clv_close"].notna() & df["odds"].notna(),
        df["clv_close"] - df["odds"],
        np.nan
    )
    return df


# -----------------------------
# UI
# -----------------------------
st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title(APP_TITLE)
st.caption("V22 adds smarter portfolio guardrails, cleaner consensus scoring, CLV tracking, auto-save logging, and AI parlay lab.")

settings = load_settings()
bet_log = load_bet_log()

with st.sidebar:
    st.header("V22 Controls")
    settings["bankroll"] = st.number_input("Bankroll ($)", min_value=50.0, value=float(settings["bankroll"]), step=50.0)
    settings["base_unit_pct"] = st.slider("Base unit (% bankroll)", 0.25, 5.0, float(settings["base_unit_pct"]), 0.25)
    settings["kelly_fraction"] = st.slider("Kelly fraction", 0.05, 1.0, float(settings["kelly_fraction"]), 0.05)
    settings["max_single_bet_pct"] = st.slider("Max single bet (% bankroll)", 0.25, 5.0, float(settings["max_single_bet_pct"]), 0.25)
    settings["max_game_exposure_pct"] = st.slider("Max game exposure (% bankroll)", 1.0, 15.0, float(settings["max_game_exposure_pct"]), 0.5)
    settings["max_book_exposure_pct"] = st.slider("Max book exposure (% bankroll)", 2.0, 25.0, float(settings["max_book_exposure_pct"]), 0.5)
    settings["odds_min"] = st.number_input("Min odds", value=int(settings["odds_min"]), step=5)
    settings["odds_max"] = st.number_input("Max odds", value=int(settings["odds_max"]), step=5)
    settings["min_consensus"] = st.slider("Minimum consensus", 1, 5, int(settings["min_consensus"]))
    settings["min_ev_edge"] = st.slider("Minimum EV edge (%)", 0.0, 20.0, float(settings["min_ev_edge"]), 0.5)
    settings["min_hit_rate"] = st.slider("Minimum hit rate (%)", 50.0, 80.0, float(settings["min_hit_rate"]), 0.5)
    settings["target_parlay_odds"] = st.number_input("Target parlay odds (American)", value=int(settings["target_parlay_odds"]), step=10)

    if st.button("Save V22 Settings"):
        save_settings(settings)
        st.success("Settings saved.")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "AI Board", "Portfolio Optimizer", "Parlay Lab", "Bet Tracker", "Import / Export"
])

with tab1:
    st.subheader("Upload market sheet")
    up = st.file_uploader("Upload CSV", type=["csv"], key="v22_csv")

    if up is not None:
        raw = pd.read_csv(up)
        df = standardize_input_df(raw)
        df = build_v22_scores(df)
        df = add_recommended_units(df, settings)
        df = enforce_guardrails(df, settings)

        sports = ["All"] + sorted(df["sport"].dropna().astype(str).unique().tolist())
        markets = ["All"] + sorted(df["market"].dropna().astype(str).unique().tolist())
        books = ["All"] + sorted(df["book"].dropna().astype(str).unique().tolist())

        c1, c2, c3 = st.columns(3)
        selected_sport = c1.selectbox("Sport", sports)
        selected_market = c2.selectbox("Market", markets)
        selected_book = c3.selectbox("Book", books)

        filtered = df.copy()
        if selected_sport != "All":
            filtered = filtered[filtered["sport"].astype(str) == selected_sport]
        if selected_market != "All":
            filtered = filtered[filtered["market"].astype(str) == selected_market]
        if selected_book != "All":
            filtered = filtered[filtered["book"].astype(str) == selected_book]

        qualified = filter_qualified(filtered, settings).sort_values(["score", "ev_edge"], ascending=False)

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Uploaded Bets", len(df))
        k2.metric("Qualified Bets", len(qualified))
        k3.metric("Avg Qualified Score", round(qualified["score"].mean(), 1) if len(qualified) else 0)
        k4.metric("Avg Qualified EV", f'{round(qualified["ev_edge"].mean(), 2) if len(qualified) else 0}%')

        display_cols = [
            "sport", "league", "game", "market", "bet_name", "book", "odds", "line",
            "projection", "hit_rate_pct", "implied_prob", "edge", "ev_edge", "consensus",
            "score", "confidence_tier", "recommended_units"
        ]
        st.dataframe(qualified[display_cols], use_container_width=True, height=500)

        if len(qualified):
            st.markdown("**Auto-save qualified bets to tracker**")
            if st.button("Save qualified bets"):
                to_save = qualified.copy()
                to_save["timestamp"] = pd.Timestamp.now()
                to_save["bet_id"] = (
                    to_save["game"].astype(str) + "|" +
                    to_save["market"].astype(str) + "|" +
                    to_save["bet_name"].astype(str) + "|" +
                    to_save["book"].astype(str) + "|" +
                    to_save["odds"].astype(str)
                )
                to_save["result"] = to_save.get("result", np.nan)
                to_save["pnl"] = to_save.get("pnl", np.nan)
                to_save["status"] = "open"

                existing = load_bet_log()
                combined = pd.concat([existing, to_save[existing.columns.intersection(to_save.columns).tolist() + [c for c in to_save.columns if c not in existing.columns]]], ignore_index=True)
                if "bet_id" in combined.columns:
                    combined = combined.drop_duplicates(subset=["bet_id"], keep="last")
                save_bet_log(combined)
                st.success(f"Saved {len(to_save)} bets to bet log.")
    else:
        st.info("Upload a CSV with odds, market, game, and model columns to activate V22 AI Board.")

with tab2:
    st.subheader("Portfolio Optimizer")
    log = add_clv_metrics(load_bet_log())
    open_bets = log[log["status"].fillna("open").astype(str).str.lower().eq("open")].copy() if len(log) else pd.DataFrame()

    if len(open_bets):
        bankroll = settings["bankroll"]
        unit_dollars = bankroll * (settings["base_unit_pct"] / 100.0)
        open_bets["stake_dollars"] = pd.to_numeric(open_bets["recommended_units"], errors="coerce").fillna(0) * unit_dollars

        by_game = open_bets.groupby("game", dropna=False)["stake_dollars"].sum().reset_index().sort_values("stake_dollars", ascending=False)
        by_book = open_bets.groupby("book", dropna=False)["stake_dollars"].sum().reset_index().sort_values("stake_dollars", ascending=False)
        by_market = open_bets.groupby("market", dropna=False)["stake_dollars"].sum().reset_index().sort_values("stake_dollars", ascending=False)

        c1, c2, c3 = st.columns(3)
        c1.metric("Open Bets", len(open_bets))
        c2.metric("Open Exposure ($)", round(open_bets["stake_dollars"].sum(), 2))
        c3.metric("Open Exposure (% bankroll)", round(open_bets["stake_dollars"].sum() / bankroll * 100, 2) if bankroll > 0 else 0)

        d1, d2, d3 = st.columns(3)
        with d1:
            st.markdown("**Exposure by Game**")
            st.dataframe(by_game, use_container_width=True, height=280)
        with d2:
            st.markdown("**Exposure by Book**")
            st.dataframe(by_book, use_container_width=True, height=280)
        with d3:
            st.markdown("**Exposure by Market**")
            st.dataframe(by_market, use_container_width=True, height=280)
    else:
        st.info("No open bets in log yet.")

with tab3:
    st.subheader("AI Parlay Lab")
    log = load_bet_log()
    open_bets = log[log["status"].fillna("open").astype(str).str.lower().eq("open")].copy() if len(log) else pd.DataFrame()
    if len(open_bets):
        target_decimal = american_to_decimal(settings["target_parlay_odds"])
        parlays = build_parlay_candidates(open_bets, min_decimal_target=target_decimal, max_legs=4)
        if len(parlays):
            st.dataframe(parlays, use_container_width=True, height=420)
        else:
            st.info("No parlay combinations currently meet the target odds and separation rules.")
    else:
        st.info("Save some qualified bets first to build AI parlays.")

with tab4:
    st.subheader("Bet Tracker + CLV")
    log = add_clv_metrics(load_bet_log())

    if len(log):
        editable_cols = [
            "timestamp", "bet_id", "sport", "league", "game", "market", "bet_name", "book",
            "odds", "recommended_units", "status", "result", "clv_close"
        ]
        for col in editable_cols:
            if col not in log.columns:
                log[col] = np.nan

        editor = st.data_editor(
            log[editable_cols],
            use_container_width=True,
            num_rows="dynamic",
            hide_index=True,
            column_config={
                "status": st.column_config.SelectboxColumn("status", options=["open", "settled"]),
                "result": st.column_config.SelectboxColumn("result", options=["", "win", "loss", "push"]),
            },
            key="bet_log_editor"
        )

        if st.button("Update tracker"):
            editor["pnl"] = editor.apply(
                lambda r: grade_bet_pnl(r["odds"], r["recommended_units"], r["result"]),
                axis=1
            )
            editor["status"] = np.where(editor["result"].fillna("").astype(str).str.len() > 0, "settled", editor["status"])
            editor["clv_delta"] = np.where(
                pd.to_numeric(editor["clv_close"], errors="coerce").notna() &
                pd.to_numeric(editor["odds"], errors="coerce").notna(),
                pd.to_numeric(editor["clv_close"], errors="coerce") - pd.to_numeric(editor["odds"], errors="coerce"),
                np.nan
            )
            save_bet_log(editor)
            st.success("Bet tracker updated.")

        settled = log[log["result"].fillna("").astype(str).str.len() > 0].copy()
        if len(settled):
            c1, c2, c3, c4 = st.columns(4)
            wins = (settled["result"].astype(str).str.lower() == "win").sum()
            losses = (settled["result"].astype(str).str.lower() == "loss").sum()
            pushes = (settled["result"].astype(str).str.lower() == "push").sum()
            pnl = pd.to_numeric(settled.get("pnl", 0), errors="coerce").fillna(0).sum()
            c1.metric("Wins", int(wins))
            c2.metric("Losses", int(losses))
            c3.metric("Pushes", int(pushes))
            c4.metric("Net Units", round(pnl, 2))

            clv_series = pd.to_numeric(settled.get("clv_delta"), errors="coerce")
            st.metric("Average CLV Delta", round(clv_series.dropna().mean(), 2) if clv_series.notna().any() else 0.0)
    else:
        st.info("Bet tracker is empty.")

with tab5:
    st.subheader("Import / Export")
    log = load_bet_log()
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("**Download current bet log**")
        if len(log):
            csv_bytes = log.to_csv(index=False).encode("utf-8")
            st.download_button("Download bet_log.csv", csv_bytes, file_name="bet_log.csv", mime="text/csv")
        else:
            st.info("No bet log data available yet.")

    with c2:
        st.markdown("**Replace bet log from CSV**")
        replacement = st.file_uploader("Upload replacement bet_log.csv", type=["csv"], key="replace_log")
        if replacement is not None:
            new_log = pd.read_csv(replacement)
            if st.button("Replace current bet log"):
                save_bet_log(new_log)
                st.success("Bet log replaced.")

st.markdown("---")
st.caption("Tip: For best results, upload a CSV that includes game, market, bet_name, odds, book, line, projection, and model_prob.")
