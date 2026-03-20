
# Minimal but working V22 full file
import math
from datetime import datetime
from io import BytesIO
from itertools import combinations

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Sports AI Betting Dashboard DEV MODE V22", page_icon="🏀", layout="wide")
st.title("🏀 Sports AI Betting Dashboard — DEV MODE V22")
st.caption("PORTFOLIO ENGINE V4 (GAME SCRIPT INTELLIGENCE)")

SPORTS = ["NBA"]
BOOKS = ["DraftKings", "FanDuel", "BetMGM"]

NBA_PLAYERS = [
    ("Giannis Antetokounmpo", "Bucks"),
    ("Tyrese Haliburton", "Pacers"),
    ("LeBron James", "Lakers"),
    ("Jayson Tatum", "Celtics"),
    ("Stephen Curry", "Warriors"),
]

TEAM_OPPONENT = {
    "Bucks": "Heat",
    "Pacers": "Cavaliers",
    "Lakers": "Warriors",
    "Celtics": "Knicks",
    "Warriors": "Lakers",
}

PLAYER_PROFILE = {
    "Giannis Antetokounmpo": {"points": 1.12, "pra": 1.10, "pa": 1.00},
    "Tyrese Haliburton": {"points": 0.98, "pra": 1.08, "pa": 1.06},
    "LeBron James": {"points": 1.02, "pra": 1.07, "pa": 1.08},
    "Jayson Tatum": {"points": 1.08, "pra": 1.02, "pa": 0.99},
    "Stephen Curry": {"points": 1.11, "pra": 1.02, "pa": 0.97},
}
TEAM_MATCHUP = {
    "Bucks": {"pace": 1.02, "matchup": 1.00},
    "Pacers": {"pace": 1.06, "matchup": 1.07},
    "Lakers": {"pace": 1.01, "matchup": 1.02},
    "Celtics": {"pace": 1.03, "matchup": 1.01},
    "Warriors": {"pace": 1.04, "matchup": 1.05},
}
PLAYER_VARIANCE = {"Giannis Antetokounmpo":1.10,"Tyrese Haliburton":1.08,"LeBron James":1.04,"Jayson Tatum":1.00,"Stephen Curry":1.12}
OPPONENT_PROP_DEFENSE = {
    "Heat": {"points":0.95,"pra":0.97,"pa":0.96},
    "Cavaliers": {"points":0.96,"pra":0.96,"pa":0.95},
    "Warriors": {"points":1.03,"pra":1.03,"pa":1.04},
    "Knicks": {"points":0.97,"pra":0.97,"pa":0.96},
    "Lakers": {"points":1.04,"pra":1.03,"pa":1.03},
}
TRACKER_COLUMNS = [
    "bet_id","added_at","sport","player","opponent","book","game_segment","prop_type","side","line","odds",
    "projection","edge","hit_probability","ev_edge","edge_score","play_tier","steam_flag","bet_timing",
    "bet_size_units","bet_size_label","result","profit_units","actual_stat","grade_source","notes"
]

def safe_float(x):
    try:
        return float(x)
    except Exception:
        return np.nan

def implied_prob_american(odds):
    odds = safe_float(odds)
    return 100 / (odds + 100) if odds > 0 else abs(odds) / (abs(odds) + 100)

def american_to_decimal(odds):
    odds = safe_float(odds)
    return 1 + (odds / 100.0) if odds > 0 else 1 + (100.0 / abs(odds))

def tier_badge(tier):
    return {"Tier 1": "🟢 Tier 1", "Tier 2": "🟡 Tier 2", "Tier 3": "⚪ Tier 3"}.get(tier, tier)

def edge_bucket(score):
    if score >= 86: return "🟢 A"
    if score >= 76: return "🟢 B"
    if score >= 66: return "🟡 C"
    return "🔴 Pass"

def current_ts_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def init_tracker_state():
    if "bet_tracker_df" not in st.session_state:
        st.session_state["bet_tracker_df"] = pd.DataFrame(columns=TRACKER_COLUMNS)

def make_sample_props_df():
    rows = []
    base_lines = {"points":27.5,"pra":38.5,"pa":31.5}
    for player, team in NBA_PLAYERS:
        opp = TEAM_OPPONENT[team]
        for prop in ["points","pra","pa"]:
            for i, book in enumerate(BOOKS):
                line = base_lines[prop] + (-0.5 + i*0.5)
                odds = [-115, -105, 100][i]
                rows.append({
                    "sport":"NBA","player":player,"team":team,"opponent":f"{team} vs {opp}",
                    "prop_type":prop,"line":line,"odds":odds,"game_segment":"full_game","book":book
                })
    return pd.DataFrame(rows)

def matchup_modifier(team, prop_type):
    opp = TEAM_OPPONENT[team]
    return OPPONENT_PROP_DEFENSE.get(opp, {}).get(prop_type, 1.0)

def apply_auto_projections(df, dev_strength):
    out = df.copy()
    projections = []
    matchup_notes = []
    variance_notes = []
    for _, r in out.iterrows():
        profile = PLAYER_PROFILE.get(r["player"], {}).get(r["prop_type"], 1.0)
        pace = TEAM_MATCHUP.get(r["team"], {}).get("pace", 1.0)
        matchup = TEAM_MATCHUP.get(r["team"], {}).get("matchup", 1.0)
        mm = matchup_modifier(r["team"], r["prop_type"])
        var = PLAYER_VARIANCE.get(r["player"], 1.0)
        seed = ((sum(ord(c) for c in f'{r["player"]}{r["prop_type"]}{r["team"]}') % 15) - 7) / 100.0
        projection = r["line"] * profile * pace * matchup * mm * (1 + seed * var * dev_strength)
        cap = {"points":5.2,"pra":5.8,"pa":5.0}[r["prop_type"]]
        projection = min(max(projection, r["line"]-cap), r["line"]+cap)
        projections.append(projection)
        matchup_notes.append("Strong matchup" if mm >= 1.03 else ("Tough matchup" if mm <= 0.97 else "Neutral matchup"))
        variance_notes.append("High-upside profile" if var >= 1.08 else "Neutral variance")
    out["projection"] = projections
    out["matchup_note"] = matchup_notes
    out["variance_note"] = variance_notes
    return out

def calibrated_hit_probability(row):
    sigma = {"points":6.5,"pra":8.4,"pa":7.0}[row["prop_type"]]
    z = (row["projection"] - row["line"]) / sigma
    raw = 0.5 * (1 + math.erf(z / math.sqrt(2)))
    return max(0.35, min(0.70, 0.50 + (raw - 0.50) * 0.58))

def curved_ev_edge(prob, implied_prob, edge_abs, matchup_note):
    raw_gap = (prob - implied_prob) * 100.0
    matchup_factor = {"Strong matchup":1.06,"Neutral matchup":1.0,"Tough matchup":0.94}[matchup_note]
    shaped = raw_gap * (1 + min(0.30, edge_abs / 20.0)) * matchup_factor
    return round(13.8 * math.tanh(shaped / 11.2), 2)

def compute_prop_scores(df):
    out = df.copy()
    out["proj_edge"] = out["projection"] - out["line"]
    out["recommended_side"] = np.where(out["projection"] > out["line"], "Over", "Under")
    out["hit_probability"] = out.apply(calibrated_hit_probability, axis=1)
    out["book_implied_prob"] = out["odds"].apply(implied_prob_american)
    out["expected_value_edge"] = out.apply(lambda r: curved_ev_edge(r["hit_probability"], r["book_implied_prob"], abs(r["proj_edge"]), r["matchup_note"]), axis=1)
    out["edge_score"] = (
        np.clip(out["proj_edge"].abs() * 7.3, 0, 31) +
        np.clip((out["hit_probability"] - 0.50) * 125, 0, 24) +
        np.clip(out["expected_value_edge"] * 1.50, -6, 20)
    ).round(1)
    out["bet_grade"] = out["edge_score"].apply(edge_bucket)
    out["play_tier"] = np.where((out["edge_score"] >= 81) & (out["hit_probability"] >= 0.61), "Tier 1",
                         np.where((out["edge_score"] >= 68) & (out["hit_probability"] >= 0.57), "Tier 2", "Tier 3"))
    return out

def apply_line_shopping(df):
    rows = []
    for _, g in df.groupby(["player","prop_type","recommended_side"], dropna=False):
        side = g["recommended_side"].iloc[0]
        ordered = g.sort_values(["line","odds","edge_score"], ascending=[side=="Over", False, False])
        rows.append(ordered.iloc[0])
    return pd.DataFrame(rows).reset_index(drop=True)

def overlap_strength(prop_a, prop_b):
    pair = {prop_a, prop_b}
    if prop_a == prop_b: return "strong"
    if pair in [{"pra","pa"},{"points","pra"},{"points","pa"}]: return "medium"
    return "weak"

def apply_correlation_filter(df):
    out = df.copy()
    out["correlation_flag"] = ""
    out["correlation_penalty"] = 0.0
    out["correlation_rank_note"] = "Top play or no issue"
    for player, g in out.groupby("player"):
        g = g.sort_values(["edge_score","expected_value_edge"], ascending=[False,False])
        if len(g) <= 1: 
            continue
        anchor_idx = g.index[0]
        out.loc[anchor_idx, "correlation_rank_note"] = "Top same-player prop kept at full size"
        anchor_prop = g.iloc[0]["prop_type"]
        for idx in g.index[1:]:
            strength = overlap_strength(anchor_prop, out.loc[idx, "prop_type"])
            if strength == "strong":
                out.loc[idx, "correlation_flag"] = "⚠️ Strong overlap"
                out.loc[idx, "correlation_penalty"] = 0.25
                out.loc[idx, "correlation_rank_note"] = "Heavy reduction"
            elif strength == "medium":
                out.loc[idx, "correlation_flag"] = "⚠️ Medium overlap"
                out.loc[idx, "correlation_penalty"] = 0.15
                out.loc[idx, "correlation_rank_note"] = "Light reduction"
    return out

def kelly_fraction_from_row(row):
    p = row["hit_probability"]
    dec = american_to_decimal(row["odds"])
    b = dec - 1
    q = 1 - p
    return max(0.0, (b * p - q) / b)

def apply_bet_sizing(df):
    out = df.copy()
    out["kelly_fraction"] = out.apply(kelly_fraction_from_row, axis=1)
    units = []
    labels = []
    for _, r in out.iterrows():
        u = 0.75 if r["play_tier"] == "Tier 1" else (0.50 if r["play_tier"] == "Tier 2" else 0.25)
        if r["expected_value_edge"] >= 7.5 and r["edge_score"] >= 77:
            u += 0.25
        u -= r["correlation_penalty"]
        kelly_cap = min(1.0, max(0.25, round((r["kelly_fraction"] * 0.35) / 0.01) * 0.25))
        u = min(u, kelly_cap)
        u = max(0.0, min(1.0, round(u * 20) / 20))
        units.append(u)
        labels.append("0.75u Strong" if u >= 0.75 else ("0.5u Standard" if u >= 0.50 else ("0.35u Reduced" if u >= 0.35 else "0.25u Small")))
    out["bet_size_units"] = units
    out["bet_size_label"] = labels
    return out

def portfolio_risk_penalty_v4(sub):
    pen = 0.0
    players = sub["player"].value_counts()
    games = sub["opponent"].value_counts()
    for _, count in players.items():
        if count > 1:
            pen += 1000
    rows = list(sub.itertuples(index=False))
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            same_game = rows[i].opponent == rows[j].opponent
            if same_game:
                pen += 3
                if rows[i].recommended_side == rows[j].recommended_side:
                    pen += 8
                else:
                    pen -= 2
            if rows[i].player == rows[j].player:
                pen += 1000
    for _, count in games.items():
        if count == 2:
            pen += 5
        elif count >= 3:
            pen += 20 + (count - 3) * 10
    return pen

def portfolio_bonus_v4(sub, total_unit_cap):
    bonus = 0.0
    units = sub["bet_size_units"].sum()
    bonus += min(5.5, (units / max(0.25, total_unit_cap)) * 3.2)
    bonus += sub["player"].nunique() * 2.0
    bonus += sub["opponent"].nunique() * 1.5
    bonus += sub["matchup_note"].map({"Strong matchup":1.5,"Neutral matchup":0.4,"Tough matchup":-1.5}).sum()
    return bonus

def portfolio_value_v4(sub, total_unit_cap):
    base = sub["edge_score"].sum() * 0.74 + sub["expected_value_edge"].sum() * 1.9 + (sub["hit_probability"].sum() * 100) * 0.08
    return base + portfolio_bonus_v4(sub, total_unit_cap) - portfolio_risk_penalty_v4(sub)

def build_portfolio_v4(df, max_same_game=2, total_unit_cap=2.5, max_plays=4):
    out = df.copy()
    out["portfolio_selected"] = False
    out["portfolio_units"] = 0.0
    out["portfolio_note"] = "Not selected"
    out["portfolio_rank"] = np.nan

    candidates = out.sort_values(["edge_score","expected_value_edge","hit_probability","bet_size_units"], ascending=[False,False,False,False]).head(10)
    idxs = list(candidates.index)
    best_combo = []
    best_value = -1e9

    for r in range(1, min(max_plays, len(idxs)) + 1):
        for combo in combinations(idxs, r):
            sub = candidates.loc[list(combo)].copy()
            if sub["bet_size_units"].sum() > total_unit_cap + 1e-9:
                continue
            if sub["player"].value_counts().max() > 1:
                continue
            if sub["opponent"].value_counts().max() > max_same_game:
                continue
            val = portfolio_value_v4(sub, total_unit_cap)
            if val > best_value:
                best_value = val
                best_combo = list(combo)

    if best_combo:
        selected = out.loc[best_combo].sort_values(["edge_score","expected_value_edge"], ascending=[False,False]).copy()
        selected["portfolio_selected"] = True
        selected["portfolio_rank"] = range(1, len(selected)+1)
        selected["portfolio_units"] = selected["bet_size_units"]
        selected["portfolio_note"] = "Selected"

        total_units = selected["portfolio_units"].sum()
        if len(selected) >= 3 and total_units < total_unit_cap - 0.20:
            top_idx = selected.index[0]
            selected.loc[top_idx, "portfolio_units"] = min(0.85, round((selected.loc[top_idx, "portfolio_units"] + 0.10) * 20) / 20)
            selected.loc[top_idx, "portfolio_note"] = "Selected | top-up"

        out.loc[selected.index, ["portfolio_selected","portfolio_units","portfolio_note","portfolio_rank"]] = selected[["portfolio_selected","portfolio_units","portfolio_note","portfolio_rank"]]

    for idx, row in out.iterrows():
        if out.loc[idx, "portfolio_selected"]:
            continue
        note = "Blocked"
        if row["player"] in list(out.loc[out["portfolio_selected"], "player"]):
            note = "Blocked: player already used"
        elif list(out.loc[out["portfolio_selected"], "opponent"]).count(row["opponent"]) >= max_same_game:
            note = "Blocked: game concentration"
        out.loc[idx, "portfolio_note"] = note

    out["portfolio_label"] = np.where(out["portfolio_selected"], out["portfolio_units"].map(lambda x: f"{x:.2f}u"), "—")
    return out

def render_top_play_card(row, rank_num):
    st.markdown(f'''
<div style="padding:14px;border:1px solid #333;border-radius:12px;margin-bottom:10px;">
  <div style="font-size:18px;font-weight:700;">#{rank_num} {row["player"]} — {row["recommended_side"]} {row["line"]} {row["prop_type"]}</div>
  <div style="margin-top:4px;">{row["opponent"]} • {str(row["game_segment"]).upper()} • {row["book"]}</div>
  <div style="margin-top:8px;"><b>Projection:</b> {row["projection"]:.2f} | <b>Edge:</b> {row["proj_edge"]:.2f} | <b>Odds:</b> {int(row["odds"])} | <b>Hit %:</b> {row["hit_probability"]*100:.1f}% | <b>EV Edge:</b> {row["expected_value_edge"]:.2f}% | <b>Score:</b> {row["edge_score"]:.1f} ({row["bet_grade"]})</div>
  <div style="margin-top:8px;"><b>Tier:</b> {tier_badge(row["play_tier"])} | <b>Model Size:</b> {row["bet_size_units"]:.2f}u | <b>Portfolio Size:</b> {row["portfolio_label"]}</div>
  <div style="margin-top:8px;"><b>Matchup:</b> {row["matchup_note"]} | <b>Variance:</b> {row["variance_note"]} | <b>Portfolio:</b> {row["portfolio_note"]}</div>
</div>
''', unsafe_allow_html=True)

def tracker_add_bet(row):
    init_tracker_state()
    tracker = st.session_state["bet_tracker_df"].copy()
    bet_id = f'BET-{datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]}'
    units = safe_float(row.get("portfolio_units", row.get("bet_size_units", 0.25)))
    new_row = {
        "bet_id": bet_id, "added_at": current_ts_str(), "sport": row["sport"], "player": row["player"],
        "opponent": row["opponent"], "book": row["book"], "game_segment": row["game_segment"],
        "prop_type": row["prop_type"], "side": row["recommended_side"], "line": safe_float(row["line"]),
        "odds": safe_float(row["odds"]), "projection": safe_float(row["projection"]), "edge": safe_float(row["proj_edge"]),
        "hit_probability": safe_float(row["hit_probability"]), "ev_edge": safe_float(row["expected_value_edge"]),
        "edge_score": safe_float(row["edge_score"]), "play_tier": row["play_tier"], "steam_flag": row.get("steam_flag","➖ Stable"),
        "bet_timing": row.get("bet_timing","Okay now"), "bet_size_units": units, "bet_size_label": f"{units:.2f}u Portfolio",
        "result": "Open", "profit_units": np.nan, "actual_stat": np.nan, "grade_source": "", "notes": row.get("portfolio_note",""),
    }
    st.session_state["bet_tracker_df"] = pd.concat([pd.DataFrame([new_row]), tracker], ignore_index=True)

def tracker_summary(df):
    if df.empty:
        return {"bets":0,"open":0,"win_rate":0.0,"units":0.0,"roi":0.0}
    graded = df[df["result"].isin(["Win","Loss","Push"])].copy()
    wins = int((graded["result"] == "Win").sum())
    losses = int((graded["result"] == "Loss").sum())
    risked = graded["bet_size_units"].fillna(0).sum()
    units = graded["profit_units"].fillna(0).sum()
    return {"bets":len(df),"open":int((df["result"]=="Open").sum()),"win_rate":(wins/max(1,wins+losses))*100,"units":units,"roi":(units/max(1e-9,risked))*100 if risked>0 else 0.0}

# build app
init_tracker_state()
st.sidebar.header("DEV MODE V22")
sport_name = st.sidebar.selectbox("Sport", SPORTS, index=0)
dev_strength = st.sidebar.slider("Auto projection aggressiveness", 0.50, 1.50, 1.00, 0.05)
st.sidebar.markdown("### Game Script Rules")
max_same_game = st.sidebar.slider("Max plays per game", 1, 3, 2, 1)
total_unit_cap = st.sidebar.slider("Total unit cap", 1.0, 4.0, 2.5, 0.25)
max_plays = st.sidebar.slider("Max total plays", 2, 5, 4, 1)

props_df = make_sample_props_df()
props_df = props_df[props_df["sport"] == sport_name].copy()
props_df = apply_auto_projections(props_df, dev_strength)
props_df = compute_prop_scores(props_df)
props_df = apply_line_shopping(props_df)
props_df["steam_flag"] = "➖ Stable"
props_df["bet_timing"] = "Okay now"
props_df = apply_correlation_filter(props_df)
props_df = apply_bet_sizing(props_df)
props_df = build_portfolio_v4(props_df, max_same_game=max_same_game, total_unit_cap=total_unit_cap, max_plays=max_plays)

props_shop = props_df.sort_values(["portfolio_selected","portfolio_units","edge_score"], ascending=[False,False,False]).reset_index(drop=True)

tab_home, tab_best, tab_portfolio, tab_tracker, tab_templates = st.tabs(["Home","Best Bets","Portfolio","Bet Tracker","Templates"])

with tab_home:
    selected_mask = props_shop["portfolio_selected"] == True
    st.subheader("Portfolio Engine V4 audit")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Selected", int(selected_mask.sum()))
    c2.metric("Portfolio Units", f"{props_shop.loc[selected_mask,'portfolio_units'].sum():.2f}")
    c3.metric("Unique Players", int(props_shop.loc[selected_mask,'player'].nunique()) if selected_mask.any() else 0)
    c4.metric("Games Used", int(props_shop.loc[selected_mask,'opponent'].nunique()) if selected_mask.any() else 0)
    st.dataframe(props_shop[["player","prop_type","recommended_side","edge_score","expected_value_edge","bet_size_units","portfolio_units","portfolio_selected","portfolio_note","matchup_note"]].head(12), use_container_width=True)
    st.info("V4 adds game-script intelligence: same-game same-direction combos are penalized heavily, while opposite-direction same-game combos get a diversification credit.")

with tab_best:
    st.subheader("Best Bets")
    for idx, (_, row) in enumerate(props_shop.head(15).iterrows(), start=1):
        render_top_play_card(row, idx)

with tab_portfolio:
    st.subheader("Portfolio Card")
    selected = props_shop[props_shop["portfolio_selected"] == True].copy()
    blocked = props_shop[props_shop["portfolio_selected"] == False].copy()
    if selected.empty:
        st.warning("No plays selected.")
    else:
        st.markdown("### Selected plays")
        st.dataframe(selected[["portfolio_rank","player","prop_type","recommended_side","line","odds","projection","edge_score","play_tier","bet_size_units","portfolio_units","matchup_note","portfolio_note"]], use_container_width=True)
        options = [f'{r.player} | {r.recommended_side} {r.line} {r.prop_type} | {r.portfolio_units:.2f}u' for _, r in selected.iterrows()]
        lookup = {options[i]: selected.iloc[i] for i in range(len(options))}
        chosen = st.selectbox("Add selected portfolio play to tracker", options)
        if st.button("Add portfolio play to tracker"):
            tracker_add_bet(lookup[chosen])
            st.success("Portfolio play added to tracker")
    if not blocked.empty:
        st.markdown("### Blocked plays")
        st.dataframe(blocked[["player","prop_type","recommended_side","line","bet_size_units","portfolio_note"]], use_container_width=True)

with tab_tracker:
    st.subheader("Bet Tracker")
    tracker_df = st.session_state["bet_tracker_df"].copy()
    stats = tracker_summary(tracker_df)
    a,b,c,d,e = st.columns(5)
    a.metric("Total Bets", stats["bets"])
    b.metric("Open", stats["open"])
    c.metric("Win %", f'{stats["win_rate"]:.1f}%')
    d.metric("Units", f'{stats["units"]:.2f}')
    e.metric("ROI %", f'{stats["roi"]:.1f}%')
    if tracker_df.empty:
        st.info("No tracked bets yet.")
    else:
        st.dataframe(tracker_df, use_container_width=True)
        st.download_button("Download bet tracker CSV", tracker_df.to_csv(index=False).encode("utf-8"), "bet_tracker_v22.csv", "text/csv")

with tab_templates:
    st.subheader("Templates")
    st.markdown("### Auto-grade template")
    st.dataframe(sample_auto_grade_template(), use_container_width=True)
    st.markdown("### Bet log import template")
    st.dataframe(sample_bet_log_import_template(), use_container_width=True)
