import hashlib
import random

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Sports Betting AI Dashboard V31.6.3",
    layout="wide"
)

# =========================================================
# SESSION STATE
# =========================================================
if "is_mobile" not in st.session_state:
    st.session_state["is_mobile"] = True

if "bet_log" not in st.session_state:
    st.session_state["bet_log"] = []

if "auto_logged_ids" not in st.session_state:
    st.session_state["auto_logged_ids"] = set()

if "nav_choice" not in st.session_state:
    st.session_state["nav_choice"] = "Top Plays"

st.sidebar.toggle("📱 Mobile Mode", key="is_mobile")


def is_mobile():
    return st.session_state.get("is_mobile", True)


# =========================================================
# ENGINE SETTINGS
# =========================================================
MIN_ACTIVE_EDGE = 1.25
ACTIVE_EDGE_PROMOTION = 1.50
MAX_TOTAL_UNITS = 3.50
MAX_ACTIVE_PLAYS = 3
DEFAULT_ODDS_RANGE = (-200, 150)


# =========================================================
# HELPERS
# =========================================================
def american_to_int(odds_str):
    try:
        return int(str(odds_str).replace("+", "").strip())
    except Exception:
        return None


def in_allowed_odds_range(odds_str, min_odds=-200, max_odds=150):
    odds_val = american_to_int(odds_str)
    if odds_val is None:
        return False
    return min_odds <= odds_val <= max_odds


def confidence_fill_and_color(confidence: str):
    c = str(confidence).strip().lower()
    if c == "elite":
        return "92%", "#10b981"
    if c == "high":
        return "78%", "#22c55e"
    return "56%", "#f59e0b"


def tier_colors(tier: str):
    t = str(tier).upper()
    if t == "A":
        return "#d1fae5", "#065f46"
    if t == "B":
        return "#dbeafe", "#1d4ed8"
    return "#fef3c7", "#92400e"


def build_play_id(row_dict):
    raw = "|".join(
        [
            str(row_dict.get("game", "")),
            str(row_dict.get("market", "")),
            str(row_dict.get("selection", "")),
            str(row_dict.get("odds", "")),
        ]
    )
    return hashlib.md5(raw.encode()).hexdigest()


# =========================================================
# DYNAMIC ENGINE
# =========================================================
def generate_ai_plays():
    base_rows = [
        {"game": "Warriors vs Lakers", "market": "moneyline", "selection": "Lakers"},
        {"game": "Warriors vs Lakers", "market": "moneyline", "selection": "Warriors"},
        {"game": "Warriors vs Lakers", "market": "total", "selection": "Over 229.5"},
        {"game": "Warriors vs Lakers", "market": "total", "selection": "Under 229.5"},
        {"game": "Celtics vs Heat", "market": "spread", "selection": "Celtics -4.5"},
        {"game": "Celtics vs Heat", "market": "total", "selection": "Under 221.5"},
        {"game": "Nuggets vs Suns", "market": "moneyline", "selection": "Nuggets"},
        {"game": "Nuggets vs Suns", "market": "spread", "selection": "Suns +4.5"},
        {"game": "Rangers vs Bruins", "market": "moneyline", "selection": "Bruins"},
        {"game": "Mavericks vs Clippers", "market": "spread", "selection": "Clippers -3.5"},
    ]

    odds_pool = ["-132", "-118", "-110", "-105", "-102", "+100", "+110", "+120", "+135"]
    consensus_pool = ["Strong", "Fair", "Thin"]
    confidence_pool = ["Medium", "High", "Elite"]

    rows = []
    random.seed(31)

    for item in base_rows:
        edge = round(random.uniform(0.80, 5.20), 2)
        score = round(random.uniform(80.0, 99.5), 1)
        confidence = random.choices(confidence_pool, weights=[3, 5, 2], k=1)[0]
        books_seen = random.randint(1, 4)
        odds = random.choice(odds_pool)
        consensus = random.choices(consensus_pool, weights=[3, 5, 2], k=1)[0]
        price_edge = round(random.uniform(0.40, 2.60), 2)

        if edge < MIN_ACTIVE_EDGE:
            continue

        if not in_allowed_odds_range(odds, DEFAULT_ODDS_RANGE[0], DEFAULT_ODDS_RANGE[1]):
            continue

        if score >= 94:
            tier = "A"
        elif score >= 86:
            tier = "B"
        else:
            tier = "C"

        status = "Active" if edge >= ACTIVE_EDGE_PROMOTION else "Watch"

        if confidence == "Elite" and status != "Active":
            confidence = "High"

        base_units = round(min(max(edge / 4.0, 0.05), 1.00), 2)
        if consensus == "Thin":
            base_units = round(max(base_units - 0.10, 0.05), 2)
        if books_seen == 1:
            base_units = round(max(base_units - 0.10, 0.05), 2)

        ai_tags = ["AI generated", "model consensus", "value detected"]
        if consensus == "Strong":
            ai_tags.append("strong market agreement")
        elif consensus == "Thin":
            ai_tags.append("thin market")
        else:
            ai_tags.append("usable consensus")

        if price_edge >= 1.5:
            ai_tags.append("best price edge")

        if books_seen <= 1:
            ai_tags.append("watch for confirmation")

        row = {
            "game": item["game"],
            "market": item["market"],
            "selection": item["selection"],
            "odds": odds,
            "edge": edge,
            "score": score,
            "units": base_units,
            "tier": tier,
            "status": status,
            "confidence": confidence,
            "books_seen": books_seen,
            "best_price": "Yes" if price_edge >= 1.25 else "No",
            "consensus": consensus,
            "price_edge": price_edge,
            "ai_tags": ai_tags,
        }
        row["play_id"] = build_play_id(row)
        rows.append(row)

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    df["rank_score"] = (
        df["score"] * 0.45
        + df["edge"] * 8.5
        + df["price_edge"] * 5.0
        + df["books_seen"] * 1.5
        + df["confidence"].map({"Medium": 1.0, "High": 2.0, "Elite": 3.0}).fillna(1.0)
    )

    df = df.sort_values(["status", "rank_score"], ascending=[True, False]).reset_index(drop=True)

    active_df = df[df["status"] == "Active"].copy().sort_values("rank_score", ascending=False)
    watch_df = df[df["status"] == "Watch"].copy().sort_values("rank_score", ascending=False)

    active_rows = []
    total_units = 0.0

    for _, row in active_df.iterrows():
        if len(active_rows) >= MAX_ACTIVE_PLAYS:
            row2 = row.copy()
            row2["status"] = "Watch"
            watch_df = pd.concat([watch_df, pd.DataFrame([row2])], ignore_index=True)
            continue

        proposed_units = float(row["units"])
        if total_units + proposed_units > MAX_TOTAL_UNITS:
            row2 = row.copy()
            row2["status"] = "Watch"
            watch_df = pd.concat([watch_df, pd.DataFrame([row2])], ignore_index=True)
            continue

        active_rows.append(row)
        total_units += proposed_units

    active_final = pd.DataFrame(active_rows) if active_rows else pd.DataFrame(columns=df.columns)
    combined = pd.concat([active_final, watch_df], ignore_index=True)

    if "rank_score" in combined.columns:
        combined = combined.sort_values(
            ["status", "rank_score"], ascending=[True, False]
        ).reset_index(drop=True)

    return combined


# =========================================================
# AUTO-LOG ACTIVE PLAYS
# =========================================================
def auto_log_active_plays(df):
    if df.empty:
        return 0

    count_added = 0
    active_df = df[df["status"] == "Active"].copy()

    for _, row in active_df.iterrows():
        play_id = row["play_id"]
        if play_id in st.session_state["auto_logged_ids"]:
            continue

        log_row = {
            "play_id": play_id,
            "game": row["game"],
            "market": row["market"],
            "selection": row["selection"],
            "odds": row["odds"],
            "edge": row["edge"],
            "score": row["score"],
            "units": row["units"],
            "confidence": row["confidence"],
            "tier": row["tier"],
            "status": row["status"],
        }

        st.session_state["bet_log"].append(log_row)
        st.session_state["auto_logged_ids"].add(play_id)
        count_added += 1

    return count_added


# =========================================================
# MOBILE NAV
# =========================================================
def render_horizontal_nav():
    labels = ["Top Plays", "Watchlist", "AI Slip", "Bet Log"]
    icons = {
        "Top Plays": "🎯",
        "Watchlist": "👀",
        "AI Slip": "🧠",
        "Bet Log": "🧾",
    }

    selected = st.session_state.get("nav_choice", "Top Plays")

    html_parts = ['<div class="nav-scroll-wrap">']
    for label in labels:
        active = label == selected
        klass = "nav-pill active" if active else "nav-pill"
        html_parts.append(
            f"""
            <button onclick="selectNav('{label}')" class="{klass}">
                <span class="nav-emoji">{icons[label]}</span>
                <span>{label}</span>
            </button>
            """
        )
    html_parts.append("</div>")
    pills_html = "".join(html_parts)

    nav_value = components.html(
        f"""
        <html>
        <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <style>
        body {{
            margin: 0;
            background: transparent;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }}
        .nav-scroll-wrap {{
            display: flex;
            gap: 10px;
            overflow-x: auto;
            white-space: nowrap;
            padding: 2px 0 6px 0;
            scrollbar-width: none;
        }}
        .nav-scroll-wrap::-webkit-scrollbar {{
            display: none;
        }}
        .nav-pill {{
            display: inline-flex;
            align-items: center;
            gap: 7px;
            padding: 9px 14px;
            border-radius: 999px;
            border: 1px solid #d7dce6;
            background: #ffffff;
            color: #111827;
            font-size: 14px;
            font-weight: 750;
            box-sizing: border-box;
            box-shadow: 0 1px 0 rgba(17, 24, 39, 0.03);
            cursor: pointer;
        }}
        .nav-pill.active {{
            background: #0f172a;
            color: #ffffff;
            border-color: #0f172a;
            box-shadow: 0 4px 14px rgba(15, 23, 42, 0.18);
        }}
        .nav-emoji {{
            font-size: 14px;
            line-height: 1;
        }}
        </style>
        </head>
        <body>
            {pills_html}
            <script>
                function selectNav(value) {{
                    const message = {{
                        isStreamlitMessage: true,
                        type: "streamlit:setComponentValue",
                        value: value
                    }};
                    window.parent.postMessage(message, "*");
                }}
            </script>
        </body>
        </html>
        """,
        height=56,
    )

    if nav_value in labels:
        st.session_state["nav_choice"] = nav_value

    return st.session_state["nav_choice"]


# =========================================================
# ELITE MOBILE CARD RENDERING
# =========================================================
def render_play_card(row: pd.Series, show_best_badge: bool = False):
    badge_bg, badge_fg = tier_colors(row["tier"])
    status_bg = "#f59e0b" if str(row["status"]) == "Active" else "#64748b"
    status_fg = "#111827" if str(row["status"]) == "Active" else "#f8fafc"
    best_display = "inline-flex" if show_best_badge else "none"

    fill_width, fill_color = confidence_fill_and_color(row["confidence"])
    edge_color = "#4ade80" if float(row["edge"]) >= 2 else "#fbbf24"

    visible_tags = list(row["ai_tags"])[:3]
    tags_html = ""
    for tag in visible_tags:
        tags_html += f"""
        <span style="
            background:#1e2638;
            color:#d8e0ec;
            border:1px solid #2a3448;
            border-radius:999px;
            padding:3px 7px;
            font-size:10px;
            line-height:1;
            display:inline-block;
            margin-right:5px;
            margin-bottom:4px;
            white-space:nowrap;
        ">{tag}</span>
        """

    title_size = "21px" if is_mobile() else "26px"
    subtitle_size = "12px" if is_mobile() else "14px"
    metric_label_size = "10px" if is_mobile() else "11px"
    metric_value_size = "14px" if is_mobile() else "16px"
    card_padding = "12px" if is_mobile() else "15px"
    card_height = 265 if is_mobile() else 320

    html = f"""
    <html>
    <head>
      <meta name="viewport" content="width=device-width, initial-scale=1" />
    </head>
    <body style="margin:0; background:transparent; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
        <div style="
            background:linear-gradient(180deg, #151b29 0%, #0e1422 100%);
            border:1px solid #243047;
            border-radius:22px;
            padding:{card_padding};
            color:#ffffff;
            box-sizing:border-box;
        ">
            <div style="display:flex; flex-wrap:wrap; gap:6px; margin-bottom:7px;">
                <span style="
                    background:{badge_bg};
                    color:{badge_fg};
                    padding:5px 9px;
                    border-radius:999px;
                    font-size:10px;
                    font-weight:800;
                    line-height:1;
                    display:inline-block;
                ">Tier {row["tier"]}</span>

                <span style="
                    background:{status_bg};
                    color:{status_fg};
                    padding:5px 9px;
                    border-radius:999px;
                    font-size:10px;
                    font-weight:800;
                    line-height:1;
                    display:inline-block;
                ">{row["status"]}</span>

                <span style="
                    background:#efe2ff;
                    color:#6b21a8;
                    padding:4px 8px;
                    border-radius:999px;
                    font-size:9px;
                    font-weight:800;
                    line-height:1;
                    display:{best_display};
                    align-items:center;
                ">🏆 Best Bet</span>
            </div>

            <div style="
                font-size:{title_size};
                line-height:1.0;
                font-weight:800;
                margin:0 0 5px 0;
                letter-spacing:-0.03em;
                color:#ffffff;
            ">{row["selection"]}</div>

            <div style="
                color:#d4dbe8;
                font-size:{subtitle_size};
                margin-bottom:8px;
            ">{row["game"]} • {str(row["market"]).title()}</div>

            <div style="
                display:grid;
                grid-template-columns:1fr 1fr;
                gap:6px 12px;
                margin-bottom:6px;
            ">
                <div>
                    <div style="color:#91a0b7; font-size:{metric_label_size}; margin-bottom:1px;">Odds</div>
                    <div style="color:#f8fafc; font-size:{metric_value_size}; font-weight:700;">{row["odds"]}</div>
                </div>
                <div>
                    <div style="color:#91a0b7; font-size:{metric_label_size}; margin-bottom:1px;">AI Score</div>
                    <div style="color:#60a5fa; font-size:{metric_value_size}; font-weight:700;">{row["score"]}</div>
                </div>

                <div>
                    <div style="color:#91a0b7; font-size:{metric_label_size}; margin-bottom:1px;">Edge</div>
                    <div style="color:{edge_color}; font-size:{metric_value_size}; font-weight:700;">{row["edge"]:.2f}%</div>
                </div>
                <div>
                    <div style="color:#91a0b7; font-size:{metric_label_size}; margin-bottom:1px;">Units</div>
                    <div style="color:#f8fafc; font-size:{metric_value_size}; font-weight:700;">{row["units"]:.2f}u</div>
                </div>

                <div>
                    <div style="color:#91a0b7; font-size:{metric_label_size}; margin-bottom:1px;">Consensus</div>
                    <div style="color:#f8fafc; font-size:{metric_value_size}; font-weight:700;">{row["consensus"]}</div>
                </div>
                <div>
                    <div style="color:#91a0b7; font-size:{metric_label_size}; margin-bottom:1px;">Books</div>
                    <div style="color:#f8fafc; font-size:{metric_value_size}; font-weight:700;">{row["books_seen"]}</div>
                </div>

                <div>
                    <div style="color:#91a0b7; font-size:{metric_label_size}; margin-bottom:1px;">Best Price</div>
                    <div style="color:#f8fafc; font-size:{metric_value_size}; font-weight:700;">{row["best_price"]}</div>
                </div>
                <div>
                    <div style="color:#91a0b7; font-size:{metric_label_size}; margin-bottom:1px;">Price Edge</div>
                    <div style="color:#f8fafc; font-size:{metric_value_size}; font-weight:700;">{row["price_edge"]:.2f}%</div>
                </div>
            </div>

            <div style="height:1px; background:#283550; margin:6px 0 7px 0;"></div>

            <div>
                <div style="color:#91a0b7; font-size:{metric_label_size}; margin-bottom:4px;">Confidence • {row["confidence"]}</div>
                <div style="width:100%; height:5px; background:#24324b; border-radius:999px; overflow:hidden;">
                    <div style="width:{fill_width}; height:5px; background:{fill_color}; border-radius:999px;"></div>
                </div>
            </div>

            <div style="height:7px;"></div>

            <div style="overflow:hidden; max-height:22px;">
                {tags_html}
            </div>
        </div>
    </body>
    </html>
    """

    components.html(html, height=card_height, scrolling=False)


def render_table_desktop(dataframe: pd.DataFrame):
    cols = [
        "tier", "status", "game", "market", "selection", "odds", "edge",
        "score", "units", "confidence", "books_seen", "best_price",
        "consensus", "price_edge"
    ]
    out = dataframe[cols].copy()
    st.dataframe(out, use_container_width=True, hide_index=True)


def render_mobile_or_table(dataframe: pd.DataFrame, best_first: bool = False):
    if dataframe.empty:
        st.info("No plays available.")
        return

    if is_mobile():
        for idx, (_, row) in enumerate(dataframe.iterrows()):
            render_play_card(row, show_best_badge=(best_first and idx == 0))
    else:
        render_table_desktop(dataframe)


# =========================================================
# DATA BUILD
# =========================================================
df = generate_ai_plays()
auto_logged_count = auto_log_active_plays(df)

active_df = df[df["status"] == "Active"].copy().reset_index(drop=True)
watch_df = df[df["status"] == "Watch"].copy().reset_index(drop=True)

best_row = None
if not active_df.empty:
    best_row = active_df.sort_values(["score", "edge"], ascending=False).iloc[0]

avg_active_edge = active_df["edge"].mean() if not active_df.empty else 0.0
best_score = best_row["score"] if best_row is not None else "—"
total_units = active_df["units"].sum() if not active_df.empty else 0.0


# =========================================================
# PAGE STYLES
# =========================================================
st.markdown(
    """
<style>
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
.stApp {
    background-color: #f6f7fb;
}
.block-container {
    max-width: 880px;
    padding-top: 0.85rem;
    padding-bottom: 1.8rem;
}
h1, h2, h3 {
    letter-spacing: -0.02em;
    color: #202533;
}
.metric-panel {
    background: #ffffff;
    border: 1px solid #e7ebf2;
    border-radius: 18px;
    padding: 10px 12px;
    margin-bottom: 10px;
}
.metric-panel-title {
    color: #1f2937;
    font-weight: 800;
    font-size: 0.94rem;
    margin-bottom: 6px;
}
.metric-mini-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px 12px;
}
.metric-mini-label {
    font-size: 0.75rem;
    color: #6b7280;
}
.metric-mini-value {
    font-size: 0.98rem;
    font-weight: 800;
    color: #111827;
}
.nav-wrap {
    background: #ffffff;
    border: 1px solid #e6eaf2;
    border-radius: 18px;
    padding: 10px 12px 7px 12px;
    margin-bottom: 12px;
}
.section-title {
    font-size: 0.98rem;
    font-weight: 800;
    margin-bottom: 0.25rem;
    color: #1e2430;
}
.slip-card {
    background: linear-gradient(180deg, #151b29 0%, #0e1422 100%);
    border: 1px solid #243047;
    border-radius: 22px;
    padding: 13px;
    margin-bottom: 10px;
    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.14);
}
.slip-kicker {
    color: #fbbf24;
    font-size: 0.82rem;
    font-weight: 800;
    margin-bottom: 5px;
}
.slip-title {
    color: #ffffff;
    font-size: 1.35rem;
    font-weight: 800;
    margin-bottom: 5px;
    letter-spacing: -0.03em;
}
.slip-meta {
    color: #d6deea;
    font-size: 0.86rem;
    margin-bottom: 3px;
}
.bet-form-wrap {
    background: #ffffff;
    border: 1px solid #e7ebf2;
    border-radius: 20px;
    padding: 14px;
    margin-bottom: 14px;
}
.notice-box {
    background: #ecfdf5;
    border: 1px solid #a7f3d0;
    color: #065f46;
    border-radius: 16px;
    padding: 10px 12px;
    margin-bottom: 10px;
    font-weight: 700;
}
.small-muted {
    color: #6b7280;
    font-size: 0.84rem;
}
</style>
""",
    unsafe_allow_html=True,
)

# =========================================================
# HEADER
# =========================================================
st.title("🔥 Sports Betting AI Dashboard V31.6.3")
st.caption("Elite Mobile Finish • Dynamic Play Generation • Auto Bet Log")

if auto_logged_count > 0:
    st.markdown(
        f'<div class="notice-box">Auto-logged {auto_logged_count} new active play(s).</div>',
        unsafe_allow_html=True,
    )

# =========================================================
# SNAPSHOT
# =========================================================
st.markdown('<div class="metric-panel">', unsafe_allow_html=True)
st.markdown('<div class="metric-panel-title">Market Snapshot</div>', unsafe_allow_html=True)
st.markdown(
    f"""
    <div class="metric-mini-grid">
        <div>
            <div class="metric-mini-label">Active Plays</div>
            <div class="metric-mini-value">{len(active_df)}</div>
        </div>
        <div>
            <div class="metric-mini-label">Watchlist</div>
            <div class="metric-mini-value">{len(watch_df)}</div>
        </div>
        <div>
            <div class="metric-mini-label">Best Score</div>
            <div class="metric-mini-value">{best_score}</div>
        </div>
        <div>
            <div class="metric-mini-label">Avg Active Edge</div>
            <div class="metric-mini-value">{avg_active_edge:.2f}%</div>
        </div>
        <div>
            <div class="metric-mini-label">Total Active Units</div>
            <div class="metric-mini-value">{total_units:.2f}u</div>
        </div>
        <div>
            <div class="metric-mini-label">Odds Filter</div>
            <div class="metric-mini-value">{DEFAULT_ODDS_RANGE[0]} to +{DEFAULT_ODDS_RANGE[1]}</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# NAVIGATION
# =========================================================
st.markdown('<div class="nav-wrap">', unsafe_allow_html=True)
st.markdown('<div class="section-title">🚀 Navigation</div>', unsafe_allow_html=True)

if is_mobile():
    nav = render_horizontal_nav()
else:
    nav = st.radio(
        "Navigation",
        ["Top Plays", "Watchlist", "AI Slip", "Bet Log"],
        horizontal=True,
        label_visibility="collapsed",
        key="nav_choice_desktop",
    )
    st.session_state["nav_choice"] = nav

st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# TOP PLAYS
# =========================================================
if nav == "Top Plays":
    st.header("🎯 Top Plays")
    st.caption("Qualified by dynamic engine thresholds and active-play risk caps.")
    top_df = active_df.sort_values(["score", "edge"], ascending=False).reset_index(drop=True)
    render_mobile_or_table(top_df, best_first=True)

# =========================================================
# WATCHLIST
# =========================================================
elif nav == "Watchlist":
    st.header("👀 Watchlist")
    st.caption("Near-qualified or lower-priority plays still worth monitoring.")
    wl_df = watch_df.sort_values(["score", "edge"], ascending=False).reset_index(drop=True)
    render_mobile_or_table(wl_df, best_first=False)

# =========================================================
# AI SLIP
# =========================================================
elif nav == "AI Slip":
    st.header("🧠 AI Slip")

    if best_row is not None:
        slip_type = "Single best bet"
        risk_level = "Low" if float(best_row["units"]) <= 0.50 else "Moderate"

        st.markdown(
            f"""
            <div class="slip-card">
                <div class="slip-kicker">🔥 AI Recommended Slip</div>
                <div class="slip-title">{best_row["selection"]}</div>
                <div class="slip-meta">{best_row["game"]} • {str(best_row["market"]).title()}</div>
                <div class="slip-meta"><strong>Projected Odds:</strong> {best_row["odds"]}</div>
                <div class="slip-meta"><strong>Confidence:</strong> {best_row["confidence"]}</div>
                <div class="slip-meta"><strong>Type:</strong> {slip_type}</div>
                <div class="slip-meta"><strong>Risk Level:</strong> {risk_level}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_play_card(best_row, show_best_badge=True)
    else:
        st.info("No active AI slip available.")

# =========================================================
# BET LOG
# =========================================================
elif nav == "Bet Log":
    st.header("🧾 Bet Log")
    st.caption("Auto-logged active plays plus any future manual entries.")

    if len(st.session_state["bet_log"]) == 0:
        st.info("No bets logged yet.")
    else:
        log_df = pd.DataFrame(st.session_state["bet_log"]).copy()
        log_cols = [
            "game", "market", "selection", "odds", "edge",
            "score", "units", "confidence", "tier", "status"
        ]
        log_df = log_df[log_cols]
        st.dataframe(log_df, use_container_width=True, hide_index=True)

    st.markdown('<div class="bet-form-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="small-muted">Manual bet entry</div>', unsafe_allow_html=True)

    with st.form("bet_log_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            game = st.text_input("Game")
            market = st.selectbox("Market", ["moneyline", "spread", "total", "prop"])
            units = st.number_input("Units", min_value=0.0, max_value=10.0, value=0.50, step=0.05)

        with col2:
            selection = st.text_input("Selection")
            odds = st.text_input("Odds", value="")
            confidence = st.selectbox("Confidence", ["Medium", "High", "Elite"])

        submitted = st.form_submit_button("Save Bet")

        if submitted:
            manual_row = {
                "play_id": build_play_id({
                    "game": game,
                    "market": market,
                    "selection": selection,
                    "odds": odds,
                }),
                "game": game or "N/A",
                "market": market,
                "selection": selection or "N/A",
                "odds": odds or "N/A",
                "edge": None,
                "score": None,
                "units": units,
                "confidence": confidence,
                "tier": "Manual",
                "status": "Manual",
            }
            st.session_state["bet_log"].append(manual_row)
            st.success("Manual bet saved.")

    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# ADAPTIVE SETTINGS
# =========================================================
with st.expander("⚙️ Adaptive Settings", expanded=False):
    c1, c2 = st.columns(2)

    with c1:
        st.write(f"**Min Active Edge:** {MIN_ACTIVE_EDGE:.2f}%")
        st.write(f"**Active Promotion Edge:** {ACTIVE_EDGE_PROMOTION:.2f}%")
        st.write(f"**Max Active Plays:** {MAX_ACTIVE_PLAYS}")

    with c2:
        st.write(f"**Max Total Units:** {MAX_TOTAL_UNITS:.1f}u")
        st.write(f"**Odds Filter:** {DEFAULT_ODDS_RANGE[0]} to +{DEFAULT_ODDS_RANGE[1]}")
        st.write("**CLV Priority:** Delayed until more free books/APIs are added")
