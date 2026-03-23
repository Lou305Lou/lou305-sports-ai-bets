import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Sports Betting AI Dashboard V31.5",
    layout="wide"
)

# =========================================================
# MOBILE TOGGLE
# =========================================================
if "is_mobile" not in st.session_state:
    st.session_state.is_mobile = True

st.sidebar.toggle("📱 Mobile Mode", key="is_mobile", value=st.session_state.is_mobile)


def is_mobile():
    return st.session_state.get("is_mobile", True)


# =========================================================
# SAMPLE DATA
# Replace this block with your real engine output later
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
# STYLES
# =========================================================
st.markdown(
    """
<style>
:root {
    --bg: #f5f7fb;
    --card: #151922;
    --card-2: #1b2130;
    --line: #2a3142;
    --text: #f8fafc;
    --muted: #b6c0cf;
    --soft: #8f9bb0;
    --green: #22c55e;
    --yellow: #f59e0b;
    --red: #ef4444;
    --blue: #3b82f6;
    --purple: #8b5cf6;
}

html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.block-container {
    padding-top: 1.25rem;
    padding-bottom: 3rem;
    max-width: 880px;
}

h1, h2, h3 {
    letter-spacing: -0.02em;
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

.dk-card {
    background: linear-gradient(180deg, #171c26 0%, #121722 100%);
    border: 1px solid #242c3a;
    border-radius: 22px;
    padding: 16px 16px 14px 16px;
    margin-bottom: 14px;
    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.12);
}

.dk-toprow {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-bottom: 10px;
}

.dk-badge {
    display: inline-block;
    padding: 6px 11px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
    line-height: 1;
}

.badge-tier-a { background: #d1fae5; color: #065f46; }
.badge-tier-b { background: #dbeafe; color: #1d4ed8; }
.badge-tier-c { background: #fef3c7; color: #92400e; }

.badge-active { background: #f59e0b; color: #111827; }
.badge-watch  { background: #475569; color: #f8fafc; }
.badge-best   { background: #e9d5ff; color: #6b21a8; }

.dk-title {
    color: #ffffff;
    font-size: 2rem;
    line-height: 1.05;
    font-weight: 800;
    margin: 0 0 6px 0;
    letter-spacing: -0.03em;
}

.dk-subtitle {
    color: #c8d1df;
    font-size: 1rem;
    margin-bottom: 14px;
}

.dk-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px 16px;
    margin-bottom: 12px;
}

.dk-metric-label {
    color: #90a0b7;
    font-size: 0.82rem;
    margin-bottom: 2px;
}

.dk-metric-value {
    color: #f8fafc;
    font-size: 1.08rem;
    font-weight: 700;
    line-height: 1.15;
}

.dk-metric-value.green { color: #4ade80; }
.dk-metric-value.yellow { color: #fbbf24; }
.dk-metric-value.blue { color: #60a5fa; }

.dk-divider {
    height: 1px;
    background: #263041;
    margin: 10px 0 12px 0;
}

.ai-tag-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.ai-tag {
    background: #202838;
    color: #d8e0ec;
    border: 1px solid #2d3748;
    border-radius: 999px;
    padding: 6px 10px;
    font-size: 12px;
    line-height: 1;
}

.conf-wrap {
    margin-top: 2px;
}

.conf-track {
    width: 100%;
    height: 8px;
    border-radius: 999px;
    background: #263041;
    overflow: hidden;
    margin-top: 6px;
}

.conf-fill-high {
    height: 100%;
    width: 78%;
    background: linear-gradient(90deg, #22c55e 0%, #84cc16 100%);
}
.conf-fill-medium {
    height: 100%;
    width: 56%;
    background: linear-gradient(90deg, #f59e0b 0%, #fbbf24 100%);
}
.conf-fill-elite {
    height: 100%;
    width: 92%;
    background: linear-gradient(90deg, #22c55e 0%, #10b981 100%);
}

.slip-card {
    background: linear-gradient(180deg, #171c26 0%, #121722 100%);
    border: 1px solid #242c3a;
    border-radius: 24px;
    padding: 18px;
    margin-bottom: 14px;
    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.12);
}

.slip-title {
    color: white;
    font-size: 1.95rem;
    font-weight: 800;
    margin-bottom: 8px;
    letter-spacing: -0.03em;
}

.slip-kicker {
    color: #fbbf24;
    font-size: 0.95rem;
    font-weight: 800;
    margin-bottom: 8px;
}

.slip-meta {
    color: #d6deea;
    font-size: 1rem;
    margin-bottom: 6px;
}

.metric-panel {
    background: white;
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
    font-size: 0.8rem;
    color: #6b7280;
}

.metric-mini-value {
    font-size: 1.2rem;
    font-weight: 800;
    color: #111827;
}

.bet-form-wrap {
    background: white;
    border: 1px solid #e7ebf2;
    border-radius: 20px;
    padding: 14px;
}

.small-note {
    color: #6b7280;
    font-size: 0.88rem;
    margin-top: -3px;
    margin-bottom: 10px;
}

@media (max-width: 768px) {
    .dk-title {
        font-size: 1.75rem;
    }
    .dk-grid {
        grid-template-columns: 1fr 1fr;
    }
}
</style>
""",
    unsafe_allow_html=True,
)

# =========================================================
# HELPERS
# =========================================================
def confidence_class(confidence: str) -> str:
    c = str(confidence).strip().lower()
    if c == "elite":
        return "conf-fill-elite"
    if c == "high":
        return "conf-fill-high"
    return "conf-fill-medium"


def render_play_card(row: pd.Series, show_best_badge: bool = False):
    tier = str(row["tier"]).upper()
    status = str(row["status"]).strip()
    tier_class = {
        "A": "badge-tier-a",
        "B": "badge-tier-b",
        "C": "badge-tier-c",
    }.get(tier, "badge-tier-c")
    status_class = "badge-active" if status == "Active" else "badge-watch"

    best_badge_html = '<span class="dk-badge badge-best">🏆 Best Bet</span>' if show_best_badge else ""
    conf_class = confidence_class(row["confidence"])

    tags = "".join([f'<span class="ai-tag">{tag}</span>' for tag in row["ai_tags"]])

    edge_class = "green" if float(row["edge"]) >= 2 else "yellow"
    score_class = "blue"

    st.markdown(
        f"""
        <div class="dk-card">
            <div class="dk-toprow">
                <span class="dk-badge {tier_class}">Tier {tier}</span>
                <span class="dk-badge {status_class}">{status}</span>
                {best_badge_html}
            </div>

            <div class="dk-title">{row["selection"]}</div>
            <div class="dk-subtitle">{row["game"]} • {str(row["market"]).title()}</div>

            <div class="dk-grid">
                <div>
                    <div class="dk-metric-label">Odds</div>
                    <div class="dk-metric-value">{row["odds"]}</div>
                </div>
                <div>
                    <div class="dk-metric-label">AI Score</div>
                    <div class="dk-metric-value {score_class}">{row["score"]}</div>
                </div>

                <div>
                    <div class="dk-metric-label">Edge</div>
                    <div class="dk-metric-value {edge_class}">{row["edge"]:.2f}%</div>
                </div>
                <div>
                    <div class="dk-metric-label">Units</div>
                    <div class="dk-metric-value">{row["units"]:.2f}u</div>
                </div>

                <div>
                    <div class="dk-metric-label">Consensus</div>
                    <div class="dk-metric-value">{row["consensus"]}</div>
                </div>
                <div>
                    <div class="dk-metric-label">Books Seen</div>
                    <div class="dk-metric-value">{row["books_seen"]}</div>
                </div>

                <div>
                    <div class="dk-metric-label">Best Price</div>
                    <div class="dk-metric-value">{row["best_price"]}</div>
                </div>
                <div>
                    <div class="dk-metric-label">Price Edge</div>
                    <div class="dk-metric-value">{row["price_edge"]:.2f}%</div>
                </div>
            </div>

            <div class="dk-divider"></div>

            <div class="conf-wrap">
                <div class="dk-metric-label">Confidence • {row["confidence"]}</div>
                <div class="conf-track">
                    <div class="{conf_class}"></div>
                </div>
            </div>

            <div style="height:10px;"></div>

            <div class="ai-tag-row">
                {tags}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
    ]
    out = dataframe[display_cols].copy()
    st.dataframe(out, use_container_width=True, hide_index=True)


def render_mobile_or_table(dataframe: pd.DataFrame, best_first: bool = False):
    if is_mobile():
        if len(dataframe) == 0:
            st.info("No plays available.")
            return
        for idx, (_, row) in enumerate(dataframe.iterrows()):
            render_play_card(row, show_best_badge=(best_first and idx == 0))
    else:
        render_table_desktop(dataframe)


# =========================================================
# HEADER METRICS
# =========================================================
active_df = df[df["status"] == "Active"].copy()
watch_df = df[df["status"] == "Watch"].copy()

best_row = active_df.sort_values(["score", "edge"], ascending=False).iloc[0] if len(active_df) else None

st.title("🔥 Sports Betting AI Dashboard V31.5")
st.caption("DraftKings + Action Network + AI UI")

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
            <div class="metric-mini-value">{best_row["score"] if best_row is not None else "—"}</div>
        </div>
        <div>
            <div class="metric-mini-label">Avg Active Edge</div>
            <div class="metric-mini-value">{active_df["edge"].mean():.2f}%</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# NAV
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
