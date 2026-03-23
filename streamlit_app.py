import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Sports Betting AI Dashboard V31.5.2",
    layout="wide"
)

# =========================================================
# SESSION STATE / MOBILE MODE
# =========================================================
if "is_mobile" not in st.session_state:
    st.session_state["is_mobile"] = True

st.sidebar.toggle("📱 Mobile Mode", key="is_mobile")


def is_mobile():
    return st.session_state.get("is_mobile", True)


# =========================================================
# SAMPLE DATA
# Replace this later with your real engine output
# =========================================================
data = [
    {
        "game": "Warriors vs Lakers",
        "market": "moneyline",
        "selection": "Lakers",
        "odds": "+110",
        "edge": 1.58,
        "score": 92.0,
        "units": 0.43,
        "tier": "B",
        "status": "Active",
        "confidence": "High",
        "books_seen": 2,
        "best_price": "Yes",
        "consensus": "Fair",
        "price_edge": 1.89,
        "ai_tags": ["best price", "market disagreement", "correlation adjusted"],
    },
    {
        "game": "Warriors vs Lakers",
        "market": "total",
        "selection": "Over 229.5",
        "odds": "-102",
        "edge": 1.60,
        "score": 88.3,
        "units": 0.51,
        "tier": "B",
        "status": "Active",
        "confidence": "High",
        "books_seen": 2,
        "best_price": "Yes",
        "consensus": "Fair",
        "price_edge": 1.66,
        "ai_tags": ["best available price", "usable consensus", "strong total signal"],
    },
    {
        "game": "Warriors vs Lakers",
        "market": "moneyline",
        "selection": "Warriors",
        "odds": "-110",
        "edge": 1.82,
        "score": 89.8,
        "units": 0.05,
        "tier": "B",
        "status": "Watch",
        "confidence": "High",
        "books_seen": 2,
        "best_price": "No",
        "consensus": "Fair",
        "price_edge": 1.75,
        "ai_tags": ["watch only", "market disagreement", "favorite side risk"],
    },
    {
        "game": "Nuggets vs Suns",
        "market": "moneyline",
        "selection": "Nuggets",
        "odds": "-132",
        "edge": 4.60,
        "score": 100.0,
        "units": 0.05,
        "tier": "C",
        "status": "Watch",
        "confidence": "Medium",
        "books_seen": 1,
        "best_price": "Yes",
        "consensus": "Thin",
        "price_edge": 2.29,
        "ai_tags": ["thin market", "watch for confirmation", "high raw edge"],
    },
]

df = pd.DataFrame(data)

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
    padding-top: 1.2rem;
    padding-bottom: 3rem;
}

h1, h2, h3 {
    letter-spacing: -0.02em;
    color: #202533;
}

.metric-panel {
    background: #ffffff;
    border: 1px solid #e7ebf2;
    border-radius: 18px;
    padding: 14px 16px;
    margin-bottom: 14px;
}

.metric-panel-title {
    color: #1f2937;
    font-weight: 800;
    font-size: 1rem;
    margin-bottom: 10px;
}

.metric-mini-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px 16px;
}

.metric-mini-label {
    font-size: 0.82rem;
    color: #6b7280;
}

.metric-mini-value {
    font-size: 1.2rem;
    font-weight: 800;
    color: #111827;
}

.nav-wrap {
    background: #ffffff;
    border: 1px solid #e6eaf2;
    border-radius: 18px;
    padding: 14px 16px 8px 16px;
    margin-bottom: 18px;
}

.section-title {
    font-size: 1.15rem;
    font-weight: 800;
    margin-bottom: 0.5rem;
    color: #1e2430;
}

.slip-card {
    background: linear-gradient(180deg, #171d2a 0%, #101624 100%);
    border: 1px solid #273043;
    border-radius: 24px;
    padding: 18px;
    margin-bottom: 14px;
    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.14);
}

.slip-kicker {
    color: #fbbf24;
    font-size: 0.95rem;
    font-weight: 800;
    margin-bottom: 8px;
}

.slip-title {
    color: #ffffff;
    font-size: 1.95rem;
    font-weight: 800;
    margin-bottom: 8px;
    letter-spacing: -0.03em;
}

.slip-meta {
    color: #d6deea;
    font-size: 1rem;
    margin-bottom: 6px;
}

.bet-form-wrap {
    background: #ffffff;
    border: 1px solid #e7ebf2;
    border-radius: 20px;
    padding: 14px;
    margin-bottom: 14px;
}
</style>
""",
    unsafe_allow_html=True,
)

# =========================================================
# HELPERS
# =========================================================
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


def render_play_card(row: pd.Series, show_best_badge: bool = False):
    badge_bg, badge_fg = tier_colors(row["tier"])
    status_bg = "#f59e0b" if str(row["status"]) == "Active" else "#64748b"
    status_fg = "#111827" if str(row["status"]) == "Active" else "#f8fafc"
    best_width = "inline-block" if show_best_badge else "none"

    fill_width, fill_color = confidence_fill_and_color(row["confidence"])

    tags_html = ""
    for tag in row["ai_tags"]:
        tags_html += f"""
        <span style="
            background:#202838;
            color:#d8e0ec;
            border:1px solid #2d3748;
            border-radius:999px;
            padding:6px 10px;
            font-size:12px;
            line-height:1;
            display:inline-block;
            margin-right:8px;
            margin-bottom:8px;
        ">{tag}</span>
        """

    edge_color = "#4ade80" if float(row["edge"]) >= 2 else "#fbbf24"

    html = f"""
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    </head>
    <body style="margin:0; background:transparent; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
        <div style="
            background:linear-gradient(180deg, #171d2a 0%, #101624 100%);
            border:1px solid #273043;
            border-radius:22px;
            padding:16px;
            color:#ffffff;
            box-sizing:border-box;
        ">
            <div style="display:flex; flex-wrap:wrap; gap:8px; margin-bottom:12px;">
                <span style="
                    background:{badge_bg};
                    color:{badge_fg};
                    padding:7px 12px;
                    border-radius:999px;
                    font-size:12px;
                    font-weight:800;
                    line-height:1;
                    display:inline-block;
                ">Tier {row["tier"]}</span>

                <span style="
                    background:{status_bg};
                    color:{status_fg};
                    padding:7px 12px;
                    border-radius:999px;
                    font-size:12px;
                    font-weight:800;
                    line-height:1;
                    display:inline-block;
                ">{row["status"]}</span>

                <span style="
                    background:#ead8ff;
                    color:#6b21a8;
                    padding:7px 12px;
                    border-radius:999px;
                    font-size:12px;
                    font-weight:800;
                    line-height:1;
                    display:{best_width};
                ">🏆 Best Bet</span>
            </div>

            <div style="
                font-size:30px;
                line-height:1.05;
                font-weight:800;
                margin:0 0 8px 0;
                letter-spacing:-0.03em;
                color:#ffffff;
            ">{row["selection"]}</div>

            <div style="
                color:#d4dbe8;
                font-size:16px;
                margin-bottom:14px;
            ">{row["game"]} • {str(row["market"]).title()}</div>

            <div style="
                display:grid;
                grid-template-columns:1fr 1fr;
                gap:12px 16px;
                margin-bottom:12px;
            ">
                <div>
                    <div style="color:#91a0b7; font-size:12px; margin-bottom:2px;">Odds</div>
                    <div style="color:#f8fafc; font-size:17px; font-weight:700;">{row["odds"]}</div>
                </div>
                <div>
                    <div style="color:#91a0b7; font-size:12px; margin-bottom:2px;">AI Score</div>
                    <div style="color:#60a5fa; font-size:17px; font-weight:700;">{row["score"]}</div>
                </div>

                <div>
                    <div style="color:#91a0b7; font-size:12px; margin-bottom:2px;">Edge</div>
                    <div style="color:{edge_color}; font-size:17px; font-weight:700;">{row["edge"]:.2f}%</div>
                </div>
                <div>
                    <div style="color:#91a0b7; font-size:12px; margin-bottom:2px;">Units</div>
                    <div style="color:#f8fafc; font-size:17px; font-weight:700;">{row["units"]:.2f}u</div>
                </div>

                <div>
                    <div style="color:#91a0b7; font-size:12px; margin-bottom:2px;">Consensus</div>
                    <div style="color:#f8fafc; font-size:17px; font-weight:700;">{row["consensus"]}</div>
                </div>
                <div>
                    <div style="color:#91a0b7; font-size:12px; margin-bottom:2px;">Books Seen</div>
                    <div style="color:#f8fafc; font-size:17px; font-weight:700;">{row["books_seen"]}</div>
                </div>

                <div>
                    <div style="color:#91a0b7; font-size:12px; margin-bottom:2px;">Best Price</div>
                    <div style="color:#f8fafc; font-size:17px; font-weight:700;">{row["best_price"]}</div>
                </div>
                <div>
                    <div style="color:#91a0b7; font-size:12px; margin-bottom:2px;">Price Edge</div>
                    <div style="color:#f8fafc; font-size:17px; font-weight:700;">{row["price_edge"]:.2f}%</div>
                </div>
            </div>

            <div style="height:1px; background:#2a3448; margin:10px 0 12px 0;"></div>

            <div style="margin-top:2px;">
                <div style="color:#91a0b7; font-size:12px; margin-bottom:6px;">Confidence • {row["confidence"]}</div>
                <div style="width:100%; height:8px; background:#263041; border-radius:999px; overflow:hidden;">
                    <div style="width:{fill_width}; height:8px; background:{fill_color}; border-radius:999px;"></div>
                </div>
            </div>

            <div style="height:12px;"></div>

            <div>
                {tags_html}
            </div>
        </div>
    </body>
    </html>
    """

    components.html(html, height=355, scrolling=False)


def render_table_desktop(dataframe: pd.DataFrame):
    display_cols = [
        "tier",
        "status",
        "game",
        "market",
        "selection",
        "odds",
        "edge",
        "score",
        "units",
        "confidence",
        "books_seen",
        "best_price",
        "consensus",
        "price_edge",
    ]
    out = dataframe[display_cols].copy()
    st.dataframe(out, use_container_width=True, hide_index=True)


def render_mobile_or_table(dataframe: pd.DataFrame, best_first: bool = False):
    if len(dataframe) == 0:
        st.info("No plays available.")
        return

    if is_mobile():
        for idx, (_, row) in enumerate(dataframe.iterrows()):
            render_play_card(row, show_best_badge=(best_first and idx == 0))
    else:
        render_table_desktop(dataframe)


# =========================================================
# DATA SPLITS
# =========================================================
active_df = df[df["status"] == "Active"].copy().reset_index(drop=True)
watch_df = df[df["status"] == "Watch"].copy().reset_index(drop=True)

best_row = None
if len(active_df) > 0:
    best_row = active_df.sort_values(["score", "edge"], ascending=False).iloc[0]

avg_active_edge = active_df["edge"].mean() if len(active_df) > 0 else 0.0
best_score = best_row["score"] if best_row is not None else "—"

# =========================================================
# HEADER
# =========================================================
st.title("🔥 Sports Betting AI Dashboard V31.5.2")
st.caption("DraftKings + Action Network + AI UI")

# =========================================================
# MARKET SNAPSHOT
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

nav = st.radio(
    "Navigation",
    ["Top Plays", "Watchlist", "AI Slip", "Bet Log"],
    horizontal=True,
    label_visibility="collapsed",
)

st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# TOP PLAYS
# =========================================================
if nav == "Top Plays":
    st.header("🎯 Top Plays")
    top_df = active_df.sort_values(["score", "edge"], ascending=False).reset_index(drop=True)
    render_mobile_or_table(top_df, best_first=True)

# =========================================================
# WATCHLIST
# =========================================================
elif nav == "Watchlist":
    st.header("👀 Watchlist")
    wl_df = watch_df.sort_values(["score", "edge"], ascending=False).reset_index(drop=True)
    render_mobile_or_table(wl_df, best_first=False)

# =========================================================
# AI SLIP
# =========================================================
elif nav == "AI Slip":
    st.header("🎯 AI Bet Slip")

    if best_row is not None:
        st.markdown(
            f"""
            <div class="slip-card">
                <div class="slip-kicker">🔥 AI Recommended Slip</div>
                <div class="slip-title">{best_row["selection"]}</div>
                <div class="slip-meta">{best_row["game"]} • {str(best_row["market"]).title()}</div>
                <div class="slip-meta"><strong>Projected Odds:</strong> {best_row["odds"]}</div>
                <div class="slip-meta"><strong>Confidence:</strong> Elite</div>
                <div class="slip-meta"><strong>Type:</strong> Single best bet</div>
                <div class="slip-meta"><strong>Risk Level:</strong> Low</div>
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

    st.markdown('<div class="bet-form-wrap">', unsafe_allow_html=True)
    st.caption("Quick manual save for active or external bets.")

    with st.form("bet_log_form", clear_on_submit=False):
        col1, col2 = st.columns(2)

        with col1:
            game = st.text_input("Game")
            market = st.selectbox("Market", ["moneyline", "spread", "total", "prop"])
            units = st.number_input("Units", min_value=0.0, max_value=10.0, value=0.50, step=0.05)

        with col2:
            selection = st.text_input("Selection")
            odds = st.text_input("Odds", value="")
            book = st.text_input("Book", value="")

        submitted = st.form_submit_button("Save Bet", use_container_width=False)

        if submitted:
            st.success(
                f"Saved bet: {selection or 'N/A'} • {game or 'N/A'} • {market} • {units:.2f}u"
            )

    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# ADAPTIVE SETTINGS
# =========================================================
with st.expander("⚙️ Adaptive Settings", expanded=False):
    c1, c2 = st.columns(2)

    with c1:
        st.write("**Min Edge:** 1.25%")
        st.write("**Max Plays:** 3")
        st.write("**Elite Only Mode:** Off")

    with c2:
        st.write("**Max Units:** 3.5u")
        st.write("**Adaptive State:** Neutral")
        st.write("**Skip Weak Games:** On")
