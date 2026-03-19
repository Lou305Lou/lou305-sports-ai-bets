
import math
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st


# =========================================================
# PAGE SETUP
# =========================================================
st.set_page_config(
    page_title="Sports AI Betting Dashboard V3",
    page_icon="🏀",
    layout="wide",
)

st.title("🏀 Sports AI Betting Dashboard V3")
st.caption("Live-Ready Structure • Arbitrage • Middles • NBA Props Hub • 1Q Focus • Line Shopping")


# =========================================================
# HELPERS
# =========================================================
def normalize_text(x):
    if pd.isna(x):
        return ""
    return str(x).strip().lower().strip()


def safe_float(x):
    try:
        if pd.isna(x):
            return np.nan
        return float(x)
    except Exception:
        return np.nan


def american_to_decimal(odds):
    try:
        odds = float(odds)
        if odds > 0:
            return 1 + (odds / 100)
        return 1 + (100 / abs(odds))
    except Exception:
        return np.nan


def implied_prob_american(odds):
    try:
        odds = float(odds)
        if odds > 0:
            return 100 / (odds + 100)
        return abs(odds) / (abs(odds) + 100)
    except Exception:
        return np.nan


def prob_to_american(prob):
    try:
        prob = float(prob)
        if prob <= 0 or prob >= 1:
            return np.nan
        if prob >= 0.5:
            return int(round(-(prob / (1 - prob)) * 100))
        return int(round(((1 - prob) / prob) * 100))
    except Exception:
        return np.nan


def clean_market_name(x):
    x = normalize_text(x)
    mapping = {
        "ml": "moneyline",
        "moneyline": "moneyline",
        "spread": "spreads",
        "spreads": "spreads",
        "total": "totals",
        "totals": "totals",
    }
    return mapping.get(x, x)


def add_missing_cols(df, cols_with_defaults):
    for col, default in cols_with_defaults.items():
        if col not in df.columns:
            df[col] = default
    return df


def edge_bucket(score):
    if score >= 84:
        return "🟢 A"
    if score >= 74:
        return "🟢 B"
    if score >= 64:
        return "🟡 C"
    return "🔴 Pass"


def confidence_warning_label(row):
    warnings = []

    minutes = safe_float(row.get("minutes_projection"))
    is_starter = safe_float(row.get("is_starter"))
    recent_avg = safe_float(row.get("recent_avg"))
    projection = safe_float(row.get("projection"))
    line = safe_float(row.get("line"))
    segment = normalize_text(row.get("game_segment"))
    starter_status = normalize_text(row.get("starter_status", ""))
    starter_confirmed = safe_float(row.get("starter_confirmed"))

    if not pd.isna(minutes):
        if segment == "1q":
            if minutes < 8:
                warnings.append("Low 1Q minutes")
        else:
            if minutes < 26:
                warnings.append("Low minutes")

    if not pd.isna(is_starter) and is_starter < 1:
        warnings.append("Bench player")

    if starter_status not in ["confirmed", "expected", "probable", "starting"]:
        if pd.isna(starter_confirmed) or starter_confirmed < 1:
            warnings.append("Starter not confirmed")

    if not pd.isna(recent_avg) and not pd.isna(line):
        if abs(recent_avg - line) < 0.5:
            warnings.append("Thin recent edge")

    if not pd.isna(projection) and not pd.isna(line):
        if abs(projection - line) < 0.4:
            warnings.append("Thin model edge")

    if not warnings:
        return "Clear"

    return " | ".join(warnings)


def confidence_status(row):
    msg = confidence_warning_label(row)
    if msg == "Clear":
        return "✅ Clear"
    if "Bench player" in msg or "Starter not confirmed" in msg:
        return "⚠️ Caution"
    return "🟡 Watch"


# =========================================================
# SAMPLE DATA
# =========================================================
def sample_odds_data():
    rows = [
        ["NBA", "Heat", "Celtics", "BetMGM", "moneyline", np.nan, np.nan, "Heat", +145],
        ["NBA", "Heat", "Celtics", "DraftKings", "moneyline", np.nan, np.nan, "Celtics", -135],
        ["NBA", "Heat", "Celtics", "FanDuel", "spreads", -4.5, np.nan, "Celtics", -110],
        ["NBA", "Heat", "Celtics", "Caesars", "spreads", +6.5, np.nan, "Heat", -110],
        ["NBA", "Lakers", "Suns", "BookA", "moneyline", np.nan, np.nan, "Lakers", +140],
        ["NBA", "Lakers", "Suns", "BookB", "spreads", -2.5, np.nan, "Suns", -110],
        ["NHL", "Panthers", "Rangers", "Book1", "moneyline", np.nan, np.nan, "Panthers", +125],
        ["NHL", "Panthers", "Rangers", "Book2", "moneyline", np.nan, np.nan, "Rangers", +130],
        ["NBA", "Knicks", "Bulls", "BetA", "totals", np.nan, 221.5, "Over", -105],
        ["NBA", "Knicks", "Bulls", "BetB", "totals", np.nan, 223.5, "Under", -105],
    ]
    return pd.DataFrame(rows, columns=[
        "sport", "team_a", "team_b", "book", "market", "point", "total", "selection", "odds"
    ])


def sample_props_data():
    rows = [
        ["NBA", "Jalen Brunson", "Knicks", "Celtics", 1, "confirmed", 1, "points", 27.5, 31.2, 36, 32.1, 5, 1.07, 1.03, -115, "full_game", "DraftKings"],
        ["NBA", "Jalen Brunson", "Knicks", "Celtics", 1, "confirmed", 1, "points", 28.5, 31.2, 36, 32.1, 5, 1.07, 1.03, +100, "full_game", "FanDuel"],
        ["NBA", "Jayson Tatum", "Celtics", "Knicks", 1, "confirmed", 1, "rebounds", 8.5, 9.7, 37, 10.2, 5, 1.04, 1.02, -105, "full_game", "BetMGM"],
        ["NBA", "Jayson Tatum", "Celtics", "Knicks", 1, "confirmed", 1, "rebounds", 9.5, 9.7, 37, 10.2, 5, 1.04, 1.02, +120, "full_game", "Caesars"],
        ["NBA", "Bam Adebayo", "Heat", "Bucks", 1, "expected", 1, "rebounds", 9.5, 11.1, 35, 11.0, 5, 1.06, 1.04, +110, "full_game", "DraftKings"],
        ["NBA", "Tyrese Haliburton", "Pacers", "Cavs", 1, "expected", 1, "assists", 10.5, 11.8, 35, 12.1, 5, 1.05, 1.03, +125, "full_game", "FanDuel"],
        ["NBA", "Stephen Curry", "Warriors", "Lakers", 1, "confirmed", 1, "3pt_made", 1.5, 2.2, 10, 2.4, 5, 1.03, 1.01, -120, "1q", "DraftKings"],
        ["NBA", "Stephen Curry", "Warriors", "Lakers", 1, "confirmed", 1, "3pt_made", 2.5, 2.2, 10, 2.4, 5, 1.03, 1.01, +155, "1q", "FanDuel"],
        ["NBA", "LeBron James", "Lakers", "Warriors", 1, "confirmed", 1, "points", 6.5, 7.8, 10, 8.4, 5, 1.04, 1.02, -110, "1q", "BetMGM"],
        ["NBA", "Bench Example", "TeamX", "TeamY", 0, "bench", 0, "points", 8.5, 10.2, 22, 9.0, 5, 1.02, 1.00, +150, "full_game", "BookX"],
        ["NBA", "Questionable Starter", "TeamQ", "TeamZ", 1, "unknown", 0, "assists", 7.5, 8.1, 27, 8.2, 5, 1.01, 1.00, +110, "full_game", "BookY"],
    ]
    return pd.DataFrame(rows, columns=[
        "sport", "player", "team", "opponent", "is_starter", "starter_status", "starter_confirmed",
        "prop_type", "line", "projection", "minutes_projection", "recent_avg", "last_5_games",
        "pace_factor", "matchup_factor", "odds", "game_segment", "book"
    ])


# =========================================================
# DATA LOADERS
# =========================================================
def load_odds_data(uploaded_file):
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
        except Exception:
            df = pd.read_excel(uploaded_file)
    else:
        df = sample_odds_data()

    df.columns = [c.strip().lower() for c in df.columns]
    df = add_missing_cols(df, {
        "sport": "NBA",
        "team_a": "",
        "team_b": "",
        "book": "",
        "market": "",
        "point": np.nan,
        "total": np.nan,
        "selection": "",
        "odds": np.nan,
    })

    df["market"] = df["market"].apply(clean_market_name)
    df["selection"] = df["selection"].fillna("").astype(str)
    df["odds"] = pd.to_numeric(df["odds"], errors="coerce")
    df["point"] = pd.to_numeric(df["point"], errors="coerce")
    df["total"] = pd.to_numeric(df["total"], errors="coerce")
    df["dec_odds"] = df["odds"].apply(american_to_decimal)
    df["imp_prob"] = df["odds"].apply(implied_prob_american)
    return df


def load_props_data(uploaded_file):
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
        except Exception:
            df = pd.read_excel(uploaded_file)
    else:
        df = sample_props_data()

    df.columns = [c.strip().lower() for c in df.columns]
    df = add_missing_cols(df, {
        "sport": "NBA",
        "player": "",
        "team": "",
        "opponent": "",
        "is_starter": 1,
        "starter_status": "unknown",
        "starter_confirmed": 0,
        "prop_type": "points",
        "line": np.nan,
        "projection": np.nan,
        "minutes_projection": np.nan,
        "recent_avg": np.nan,
        "last_5_games": 5,
        "pace_factor": 1.00,
        "matchup_factor": 1.00,
        "odds": np.nan,
        "game_segment": "full_game",
        "book": "Unknown",
    })

    numeric_cols = [
        "is_starter", "starter_confirmed", "line", "projection", "minutes_projection",
        "recent_avg", "last_5_games", "pace_factor", "matchup_factor", "odds"
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["player", "team", "opponent", "starter_status", "book"]:
        df[col] = df[col].fillna("").astype(str)

    df["prop_type"] = df["prop_type"].apply(normalize_text)
    df["game_segment"] = df["game_segment"].apply(normalize_text)
    df["starter_status"] = df["starter_status"].apply(normalize_text)
    return df


# =========================================================
# ARBITRAGE / MIDDLES
# =========================================================
def find_moneyline_arbs(df):
    ml = df[df["market"] == "moneyline"].copy()
    results = []

    if ml.empty:
        return pd.DataFrame()

    for keys, group in ml.groupby(["sport", "team_a", "team_b"], dropna=False):
        selections = group["selection"].dropna().unique()
        if len(selections) < 2:
            continue

        best_rows = []
        for selection in selections:
            sub = group[group["selection"] == selection].copy()
            if sub.empty:
                continue
            best_rows.append(sub.loc[sub["dec_odds"].idxmax()])

        if len(best_rows) != 2:
            continue

        r1, r2 = best_rows
        inv_sum = (1 / r1["dec_odds"]) + (1 / r2["dec_odds"])

        if inv_sum < 1:
            results.append({
                "sport": keys[0],
                "matchup": f"{keys[1]} vs {keys[2]}",
                "side_1": r1["selection"],
                "book_1": r1["book"],
                "odds_1": int(r1["odds"]),
                "side_2": r2["selection"],
                "book_2": r2["book"],
                "odds_2": int(r2["odds"]),
                "arb_profit_pct": round((1 - inv_sum) * 100, 2),
            })

    if not results:
        return pd.DataFrame()
    return pd.DataFrame(results).sort_values("arb_profit_pct", ascending=False)


def find_spread_middles(df):
    spreads = df[df["market"] == "spreads"].copy()
    results = []

    if spreads.empty:
        return pd.DataFrame()

    for keys, group in spreads.groupby(["sport", "team_a", "team_b"], dropna=False):
        rows = group.dropna(subset=["point"]).copy()
        if len(rows) < 2:
            continue

        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                r1 = rows.iloc[i]
                r2 = rows.iloc[j]
                p1 = safe_float(r1["point"])
                p2 = safe_float(r2["point"])

                if pd.isna(p1) or pd.isna(p2):
                    continue

                if p1 < 0 and p2 > 0 and abs(p1) < abs(p2):
                    width = p2 - abs(p1)
                    if width > 0:
                        results.append({
                            "sport": keys[0],
                            "matchup": f"{keys[1]} vs {keys[2]}",
                            "bet_1": f"{r1['selection']} {p1} ({r1['book']} {int(r1['odds'])})",
                            "bet_2": f"{r2['selection']} +{p2} ({r2['book']} {int(r2['odds'])})",
                            "middle_window_points": round(width, 2),
                            "middle_type": "Spread vs Spread",
                        })

                elif p2 < 0 and p1 > 0 and abs(p2) < abs(p1):
                    width = p1 - abs(p2)
                    if width > 0:
                        results.append({
                            "sport": keys[0],
                            "matchup": f"{keys[1]} vs {keys[2]}",
                            "bet_1": f"{r2['selection']} {p2} ({r2['book']} {int(r2['odds'])})",
                            "bet_2": f"{r1['selection']} +{p1} ({r1['book']} {int(r1['odds'])})",
                            "middle_window_points": round(width, 2),
                            "middle_type": "Spread vs Spread",
                        })

    if not results:
        return pd.DataFrame()
    return pd.DataFrame(results).sort_values("middle_window_points", ascending=False).drop_duplicates()


def find_moneyline_spread_middles(df):
    ml = df[df["market"] == "moneyline"].copy()
    spreads = df[df["market"] == "spreads"].copy()
    results = []

    if ml.empty or spreads.empty:
        return pd.DataFrame()

    for keys, group_ml in ml.groupby(["sport", "team_a", "team_b"], dropna=False):
        group_sp = spreads[
            (spreads["sport"] == keys[0]) &
            (spreads["team_a"] == keys[1]) &
            (spreads["team_b"] == keys[2])
        ].copy()

        if group_sp.empty:
            continue

        for _, ml_row in group_ml.iterrows():
            for _, sp_row in group_sp.iterrows():
                ml_sel = normalize_text(ml_row["selection"])
                sp_sel = normalize_text(sp_row["selection"])
                point = safe_float(sp_row["point"])

                if pd.isna(point):
                    continue

                if ml_sel != sp_sel and point > 0:
                    results.append({
                        "sport": keys[0],
                        "matchup": f"{keys[1]} vs {keys[2]}",
                        "bet_1": f"{ml_row['selection']} ML ({ml_row['book']} {int(ml_row['odds'])})",
                        "bet_2": f"{sp_row['selection']} +{point} ({sp_row['book']} {int(sp_row['odds'])})",
                        "middle_window_points": round(max(point - 1, 0), 2),
                        "middle_type": "Moneyline vs Spread",
                        "notes": "Middle hits if ML side wins by fewer than the spread points.",
                    })

    if not results:
        return pd.DataFrame()
    return pd.DataFrame(results).sort_values("middle_window_points", ascending=False).drop_duplicates()


# =========================================================
# PROP ENGINE
# =========================================================
def hit_probability_from_edge(row):
    prop_type = normalize_text(row.get("prop_type", "points"))
    line = safe_float(row.get("line"))
    proj = safe_float(row.get("projection"))
    minutes = safe_float(row.get("minutes_projection"))
    recent_avg = safe_float(row.get("recent_avg"))
    segment = normalize_text(row.get("game_segment", "full_game"))

    if pd.isna(line) or pd.isna(proj):
        return np.nan

    sigma_map_full = {
        "points": 6.5,
        "rebounds": 3.0,
        "assists": 3.2,
        "3pt_made": 1.6,
        "threes": 1.6,
        "pra": 8.4,
        "pa": 7.0,
        "pr": 6.8,
        "ra": 5.2,
        "steals": 1.2,
        "blocks": 1.2,
    }

    sigma_map_1q = {
        "points": 2.6,
        "rebounds": 1.4,
        "assists": 1.5,
        "3pt_made": 0.9,
        "threes": 0.9,
        "pra": 3.0,
        "pa": 2.7,
        "pr": 2.5,
        "ra": 2.1,
        "steals": 0.6,
        "blocks": 0.5,
    }

    sigma_map = sigma_map_1q if segment == "1q" else sigma_map_full
    sigma = sigma_map.get(prop_type, 5.5 if segment != "1q" else 2.3)

    if not pd.isna(minutes):
        if segment == "1q":
            if minutes < 8:
                sigma *= 1.10
            elif minutes >= 11:
                sigma *= 0.96
        else:
            if minutes < 24:
                sigma *= 1.18
            elif minutes < 30:
                sigma *= 1.08
            elif minutes >= 36:
                sigma *= 0.95

    if not pd.isna(recent_avg):
        if abs(recent_avg - proj) <= 1:
            sigma *= 0.97
        elif abs(recent_avg - proj) >= 4:
            sigma *= 1.05

    z = (proj - line) / sigma if sigma > 0 else 0
    prob_over = 0.5 * (1 + math.erf(z / math.sqrt(2)))
    prob_over = max(0.01, min(0.99, prob_over))
    return prob_over


def compute_prop_scores(df):
    df = df.copy()

    df["proj_edge"] = df["projection"] - df["line"]
    df["proj_edge_abs"] = df["proj_edge"].abs()
    df["recommended_side"] = np.where(df["projection"] > df["line"], "Over", "Under")
    df["hit_prob_over"] = df.apply(hit_probability_from_edge, axis=1)
    df["hit_prob_under"] = 1 - df["hit_prob_over"]
    df["hit_probability"] = np.where(df["recommended_side"] == "Over", df["hit_prob_over"], df["hit_prob_under"])
    df["book_implied_prob"] = df["odds"].apply(implied_prob_american)
    df["model_fair_odds"] = df["hit_probability"].apply(prob_to_american)
    df["expected_value_edge"] = ((df["hit_probability"] - df["book_implied_prob"]) * 100).round(2)

    minutes_score = np.where(
        df["game_segment"] == "1q",
        np.clip((df["minutes_projection"] / 12) * 16, 0, 16),
        np.clip((df["minutes_projection"] / 36) * 18, 0, 18)
    )
    edge_score_component = np.clip(df["proj_edge_abs"] * 6, 0, 24)
    recent_gap = (df["recent_avg"] - df["line"]).abs()
    recent_score = np.clip(recent_gap * 2.2, 0, 14)
    starter_score = np.where(df["is_starter"] >= 1, 10, 0)
    confirmed_bonus = np.where(df["starter_confirmed"] >= 1, 6, 0)
    pace_score = np.clip((df["pace_factor"] - 1.0) * 100, -4, 10)
    matchup_score = np.clip((df["matchup_factor"] - 1.0) * 100, -4, 12)

    price_score = np.select(
        [
            (df["odds"] >= -125) & (df["odds"] <= 140),
            (df["odds"] >= -150) & (df["odds"] < -125),
            (df["odds"] > 140) & (df["odds"] <= 200),
        ],
        [10, 7, 8],
        default=4
    )

    probability_score = np.clip((df["hit_probability"] - 0.50) * 100, 0, 14)
    ev_score = np.clip(df["expected_value_edge"], 0, 10)

    caution_penalty = np.select(
        [
            df["starter_confirmed"] < 1,
            df["minutes_projection"] < np.where(df["game_segment"] == "1q", 8, 26),
        ],
        [6, 4],
        default=0
    )

    df["edge_score"] = (
        minutes_score
        + edge_score_component
        + recent_score
        + starter_score
        + confirmed_bonus
        + pace_score
        + matchup_score
        + price_score
        + probability_score
        + ev_score
        - caution_penalty
    ).round(1)

    df["edge_score"] = np.clip(df["edge_score"], 0, 100)
    df["bet_grade"] = df["edge_score"].apply(edge_bucket)
    df["confidence_warning"] = df.apply(confidence_warning_label, axis=1)
    df["confidence_status"] = df.apply(confidence_status, axis=1)
    return df


def best_line_shop(df):
    if df.empty:
        return df.copy()

    rows = []
    group_cols = ["player", "team", "opponent", "prop_type", "game_segment", "recommended_side"]

    for _, group in df.groupby(group_cols, dropna=False):
        group = group.copy()
        side = group["recommended_side"].iloc[0]

        if side == "Over":
            group = group.sort_values(
                ["line", "odds", "edge_score", "expected_value_edge"],
                ascending=[True, False, False, False]
            )
        else:
            group = group.sort_values(
                ["line", "odds", "edge_score", "expected_value_edge"],
                ascending=[False, False, False, False]
            )
        rows.append(group.iloc[0])

    return pd.DataFrame(rows).reset_index(drop=True).sort_values(
        ["edge_score", "expected_value_edge", "hit_probability"],
        ascending=[False, False, False]
    )


def player_prop_line_compare(df, player_name, prop_type, segment):
    comp = df.copy()
    comp = comp[
        (comp["player"] == player_name) &
        (comp["prop_type"] == prop_type) &
        (comp["game_segment"] == segment)
    ].copy()

    if comp.empty:
        return comp

    comp = comp.sort_values(["line", "odds"], ascending=[True, False])
    return comp


def filter_props_base(df, sport="All", prop_type="All", segment="All", starters_only=True,
                      confirmed_only=False, min_odds=-300, max_odds=200, min_edge=60,
                      min_hit_prob=54, min_ev=0, book="All"):
    out = df.copy()

    if sport != "All":
        out = out[out["sport"] == sport]
    if prop_type != "All":
        out = out[out["prop_type"] == prop_type]
    if segment != "All":
        out = out[out["game_segment"] == segment]
    if starters_only:
        out = out[out["is_starter"] >= 1]
    if confirmed_only:
        out = out[out["starter_confirmed"] >= 1]
    if book != "All":
        out = out[out["book"] == book]

    out = out[(out["odds"] >= min_odds) & (out["odds"] <= max_odds)]
    out = out[out["edge_score"] >= min_edge]
    out = out[(out["hit_probability"] * 100) >= min_hit_prob]
    out = out[out["expected_value_edge"] >= min_ev]

    return out.sort_values(
        ["edge_score", "expected_value_edge", "hit_probability", "proj_edge_abs"],
        ascending=[False, False, False, False]
    )


def render_top_play_card(row, rank_num):
    st.markdown(
        f"""
<div style="padding:14px;border:1px solid #333;border-radius:12px;margin-bottom:10px;">
  <div style="font-size:18px;font-weight:700;">#{rank_num} {row['player']} — {row['recommended_side']} {row['line']} {row['prop_type']}</div>
  <div style="margin-top:4px;">{row['team']} vs {row['opponent']} • {str(row['game_segment']).upper()} • {row['book']}</div>
  <div style="margin-top:8px;">
    <b>Projection:</b> {row['projection']:.2f} |
    <b>Edge:</b> {row['proj_edge']:.2f} |
    <b>Odds:</b> {int(row['odds']) if not pd.isna(row['odds']) else 'N/A'} |
    <b>Hit %:</b> {row['hit_probability']*100:.1f}% |
    <b>EV Edge:</b> {row['expected_value_edge']:.2f}% |
    <b>Score:</b> {row['edge_score']:.1f} ({row['bet_grade']})
  </div>
  <div style="margin-top:8px;">
    <b>Confidence:</b> {row['confidence_status']} |
    <b>Notes:</b> {row['confidence_warning']}
  </div>
</div>
""",
        unsafe_allow_html=True
    )


def format_props_table(df):
    out = df.copy()
    if out.empty:
        return out

    out["hit_probability"] = (out["hit_probability"] * 100).round(1)
    out["book_implied_prob"] = (out["book_implied_prob"] * 100).round(1)
    return out


def prop_summary_metrics(df):
    if df.empty:
        return {"count": 0, "a_grade": 0, "avg_edge": 0.0, "avg_hit": 0.0}
    return {
        "count": len(df),
        "a_grade": int((df["edge_score"] >= 84).sum()),
        "avg_edge": round(df["edge_score"].mean(), 1),
        "avg_hit": round(df["hit_probability"].mean() * 100, 1),
    }


# =========================================================
# LOAD DATA
# =========================================================
st.sidebar.header("Upload Files")

odds_file = st.sidebar.file_uploader(
    "Upload odds file (CSV/XLSX)",
    type=["csv", "xlsx"],
    help="Columns: sport, team_a, team_b, book, market, point, total, selection, odds"
)

props_file = st.sidebar.file_uploader(
    "Upload props file (CSV/XLSX)",
    type=["csv", "xlsx"],
    help="Columns: sport, player, team, opponent, is_starter, starter_status, starter_confirmed, prop_type, line, projection, minutes_projection, recent_avg, pace_factor, matchup_factor, odds, game_segment, book"
)

odds_df = load_odds_data(odds_file)
props_df = load_props_data(props_file)
props_scored = compute_prop_scores(props_df)
props_shop = best_line_shop(props_scored)


# =========================================================
# TABS
# =========================================================
tab_home, tab_arb, tab_mid, tab_props = st.tabs([
    "Home",
    "Arbitrage",
    "Middles",
    "NBA Props Hub",
])


# =========================================================
# HOME
# =========================================================
with tab_home:
    st.subheader("Dashboard Summary")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Odds Rows", len(odds_df))
    c2.metric("Props Rows", len(props_df))
    c3.metric("Sportsbooks", max(odds_df["book"].nunique(), props_df["book"].nunique()))
    c4.metric("Updated", datetime.now().strftime("%Y-%m-%d %H:%M"))

    st.markdown("### V3 live-ready structure")
    st.write("• Moneyline arbitrage scanner")
    st.write("• Spread vs spread middle scanner")
    st.write("• Moneyline vs spread middle scanner")
    st.write("• NBA Props Hub")
    st.write("• Separate ranking sections for points, rebounds, assists, and 3s")
    st.write("• 1Q-only ranking section")
    st.write("• Best-line shop logic")
    st.write("• Same-player sportsbook comparison table")
    st.write("• Confidence warnings for low minutes / unconfirmed starters")

    with st.expander("Sample odds format"):
        st.dataframe(sample_odds_data(), use_container_width=True)

    with st.expander("Sample props format"):
        st.dataframe(sample_props_data(), use_container_width=True)


# =========================================================
# ARBITRAGE
# =========================================================
with tab_arb:
    st.subheader("Moneyline Arbitrage Scanner")

    sport_options = ["All"] + sorted(odds_df["sport"].dropna().astype(str).unique().tolist())
    selected_sport = st.selectbox("Sport", sport_options, key="arb_sport")

    arb_base = odds_df.copy()
    if selected_sport != "All":
        arb_base = arb_base[arb_base["sport"] == selected_sport]

    arb_results = find_moneyline_arbs(arb_base)

    if arb_results.empty:
        st.warning("No moneyline arbitrage opportunities detected.")
    else:
        st.success(f"Found {len(arb_results)} arbitrage opportunity(s).")
        st.dataframe(arb_results, use_container_width=True)


# =========================================================
# MIDDLES
# =========================================================
with tab_mid:
    st.subheader("Middle Detection")

    selected_mid_sport = st.selectbox("Sport ", sport_options, key="mid_sport")

    mid_base = odds_df.copy()
    if selected_mid_sport != "All":
        mid_base = mid_base[mid_base["sport"] == selected_mid_sport]

    spread_mids = find_spread_middles(mid_base)
    ml_spread_mids = find_moneyline_spread_middles(mid_base)

    left, right = st.columns(2)

    with left:
        st.markdown("### Spread vs Spread")
        if spread_mids.empty:
            st.info("No spread-vs-spread middles found.")
        else:
            st.dataframe(spread_mids, use_container_width=True)

    with right:
        st.markdown("### Moneyline vs Spread")
        if ml_spread_mids.empty:
            st.info("No moneyline-vs-spread middles found.")
        else:
            st.dataframe(ml_spread_mids, use_container_width=True)


# =========================================================
# NBA PROPS HUB
# =========================================================
with tab_props:
    st.subheader("NBA Props Hub V3")

    sport_options_props = ["All"] + sorted(props_shop["sport"].dropna().astype(str).unique().tolist())
    prop_types = ["All"] + sorted(props_shop["prop_type"].dropna().astype(str).unique().tolist())
    segments = ["All"] + sorted(props_shop["game_segment"].dropna().astype(str).unique().tolist())
    books = ["All"] + sorted(props_scored["book"].dropna().astype(str).unique().tolist())

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        selected_prop_sport = st.selectbox("Sport", sport_options_props, key="props_sport")
    with c2:
        selected_segment = st.selectbox("Game Segment", segments, key="props_segment")
    with c3:
        starters_only = st.checkbox("Starters Only", value=True)
    with c4:
        confirmed_only = st.checkbox("Confirmed Starters Only", value=False)

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        min_odds = st.slider("Min Odds", min_value=-300, max_value=200, value=-300, step=5)
    with c6:
        max_odds = st.slider("Max Odds", min_value=-300, max_value=200, value=200, step=5)
    with c7:
        min_edge = st.slider("Min Edge Score", min_value=0, max_value=100, value=60, step=5)
    with c8:
        selected_book = st.selectbox("Book", books, key="props_book")

    c9, c10, c11 = st.columns(3)
    with c9:
        min_hit_prob = st.slider("Min Hit %", min_value=50, max_value=95, value=54, step=1)
    with c10:
        min_ev_edge = st.slider("Min EV Edge %", min_value=-10, max_value=25, value=0, step=1)
    with c11:
        show_best_line_only = st.checkbox("Best Line Shop Only", value=True)

    props_base_source = props_shop.copy() if show_best_line_only else props_scored.copy()

    props_base = filter_props_base(
        props_base_source,
        sport=selected_prop_sport,
        prop_type="All",
        segment=selected_segment,
        starters_only=starters_only,
        confirmed_only=confirmed_only,
        min_odds=min_odds,
        max_odds=max_odds,
        min_edge=min_edge,
        min_hit_prob=min_hit_prob,
        min_ev=min_ev_edge,
        book=selected_book,
    )

    metrics = prop_summary_metrics(props_base)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Props Found", metrics["count"])
    m2.metric("A-Grade Plays", metrics["a_grade"])
    m3.metric("Avg Edge Score", metrics["avg_edge"])
    m4.metric("Avg Hit %", f"{metrics['avg_hit']}%")

    st.markdown("### Top Plays")
    if props_base.empty:
        st.warning("No props match the current filters.")
    else:
        for idx, (_, row) in enumerate(props_base.head(10).iterrows(), start=1):
            render_top_play_card(row, idx)

    # Separate live-ready sections
    section_map = [
        ("Points", "points"),
        ("Rebounds", "rebounds"),
        ("Assists", "assists"),
        ("3PT Made", "3pt_made"),
    ]

    table_cols = [
        "player", "team", "opponent", "book", "game_segment", "recommended_side",
        "line", "projection", "proj_edge", "minutes_projection", "recent_avg",
        "odds", "hit_probability", "model_fair_odds", "book_implied_prob",
        "expected_value_edge", "edge_score", "bet_grade", "confidence_status", "confidence_warning"
    ]

    for section_title, prop_key in section_map:
        st.markdown(f"### {section_title}")
        section_df = props_base[props_base["prop_type"] == prop_key].copy()
        if section_df.empty:
            st.info(f"No {section_title.lower()} plays under current filters.")
        else:
            st.dataframe(format_props_table(section_df[table_cols]), use_container_width=True)

    # 1Q ranking section
    st.markdown("### 1Q-Only Rankings")
    one_q = props_base[props_base["game_segment"] == "1q"].copy()
    if one_q.empty:
        st.info("No 1Q plays under current filters.")
    else:
        one_q = one_q.sort_values(
            ["edge_score", "hit_probability", "expected_value_edge"],
            ascending=[False, False, False]
        )
        st.dataframe(format_props_table(one_q[table_cols]), use_container_width=True)

    # Main props table
    st.markdown("### Full Props Table")
    if props_base.empty:
        st.info("No props to show.")
    else:
        st.dataframe(format_props_table(props_base[table_cols]), use_container_width=True)

    # Sportsbook comparison for same prop
    st.markdown("### Sportsbook Comparison")
    comp_candidates = props_scored.copy()
    if selected_prop_sport != "All":
        comp_candidates = comp_candidates[comp_candidates["sport"] == selected_prop_sport]
    if starters_only:
        comp_candidates = comp_candidates[comp_candidates["is_starter"] >= 1]

    player_options = [""] + sorted(comp_candidates["player"].dropna().astype(str).unique().tolist())
    selected_player = st.selectbox("Player to compare", player_options, key="compare_player")

    comp_prop_options = [""] + sorted(
        comp_candidates[comp_candidates["player"] == selected_player]["prop_type"].dropna().astype(str).unique().tolist()
    ) if selected_player else [""]

    selected_compare_prop = st.selectbox("Prop type to compare", comp_prop_options, key="compare_prop")

    comp_segment_options = [""] + sorted(
        comp_candidates[
            (comp_candidates["player"] == selected_player) &
            (comp_candidates["prop_type"] == selected_compare_prop)
        ]["game_segment"].dropna().astype(str).unique().tolist()
    ) if selected_player and selected_compare_prop else [""]

    selected_compare_segment = st.selectbox("Segment to compare", comp_segment_options, key="compare_segment")

    if selected_player and selected_compare_prop and selected_compare_segment:
        comp_df = player_prop_line_compare(props_scored, selected_player, selected_compare_prop, selected_compare_segment)
        if comp_df.empty:
            st.info("No sportsbook comparison rows found.")
        else:
            comp_display_cols = [
                "player", "team", "opponent", "book", "game_segment", "prop_type",
                "recommended_side", "line", "projection", "odds", "hit_probability",
                "model_fair_odds", "expected_value_edge", "edge_score", "confidence_status"
            ]
            st.dataframe(format_props_table(comp_df[comp_display_cols]), use_container_width=True)

    with st.expander("V3 Notes"):
        st.write("This version is organized so it is easier to plug in live feeds later.")
        st.write("Starter confirmation is still file-driven unless you connect a live source yourself.")
        st.write("Hit probability and fair odds remain model estimates, not true market-simulation outputs.")


st.markdown("---")
st.caption("V3 full clean build — copy-paste ready for Streamlit Cloud.")
