
import io
from typing import Optional

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Sports AI Dashboard", layout="wide")


# ---------- Helpers ----------
EXPECTED_COLS = [
    "sport", "league", "market", "book", "odds", "point", "player",
    "team", "opponent", "game", "event", "result", "projection",
    "edge", "hit_pct", "ev_edge", "score", "is_starter"
]


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip().lower().replace(" ", "_") for c in out.columns]
    return out


def ensure_session_defaults():
    if "active_df" not in st.session_state:
        st.session_state.active_df = None
    if "active_source" not in st.session_state:
        st.session_state.active_source = "None"


def sample_nba_props_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "sport": "NBA",
                "league": "NBA",
                "market": "Points Over",
                "book": "DraftKings",
                "odds": -115,
                "point": 27.5,
                "player": "Stephen Curry",
                "team": "GSW",
                "opponent": "LAL",
                "game": "GSW @ LAL",
                "projection": 32.2,
                "edge": 4.7,
                "hit_pct": 66.7,
                "ev_edge": 12.7,
                "score": 70.9,
                "is_starter": True,
            },
            {
                "sport": "NBA",
                "league": "NBA",
                "market": "PRA Over",
                "book": "FanDuel",
                "odds": -110,
                "point": 38.5,
                "player": "LeBron James",
                "team": "LAL",
                "opponent": "GSW",
                "game": "GSW @ LAL",
                "projection": 43.8,
                "edge": 5.3,
                "hit_pct": 64.8,
                "ev_edge": 12.2,
                "score": 67.7,
                "is_starter": True,
            },
            {
                "sport": "NBA",
                "league": "NBA",
                "market": "Assists Over",
                "book": "BetMGM",
                "odds": 105,
                "point": 8.5,
                "player": "Tyrese Haliburton",
                "team": "IND",
                "opponent": "MIL",
                "game": "MIL @ IND",
                "projection": 10.1,
                "edge": 1.6,
                "hit_pct": 58.3,
                "ev_edge": 7.9,
                "score": 61.4,
                "is_starter": True,
            },
            {
                "sport": "NBA",
                "league": "NBA",
                "market": "Rebounds Over",
                "book": "Caesars",
                "odds": -125,
                "point": 11.5,
                "player": "Anthony Davis",
                "team": "LAL",
                "opponent": "GSW",
                "game": "GSW @ LAL",
                "projection": 13.2,
                "edge": 1.7,
                "hit_pct": 59.4,
                "ev_edge": 6.8,
                "score": 60.2,
                "is_starter": True,
            },
        ]
    )


def try_read_uploaded_file(uploaded_file) -> tuple[Optional[pd.DataFrame], Optional[str]]:
    if uploaded_file is None:
        return None, "No file uploaded."

    filename = (uploaded_file.name or "").lower()

    try:
        file_bytes = uploaded_file.getvalue()
        if not file_bytes:
            return None, "The uploaded file appears to be empty."

        if filename.endswith(".csv"):
            attempts = [
                {"encoding": "utf-8", "sep": ","},
                {"encoding": "utf-8-sig", "sep": ","},
                {"encoding": "latin1", "sep": ","},
                {"encoding": "utf-8", "sep": ";"},
                {"encoding": "latin1", "sep": ";"},
            ]
            last_error = None
            for attempt in attempts:
                try:
                    return pd.read_csv(io.BytesIO(file_bytes), **attempt), None
                except Exception as e:
                    last_error = e
            return None, f"CSV read failed after multiple attempts: {last_error}"

        if filename.endswith(".xlsx") or filename.endswith(".xls"):
            return pd.read_excel(io.BytesIO(file_bytes)), None

        return None, "Unsupported file type. Please upload a .csv, .xlsx, or .xls file."

    except Exception as e:
        return None, f"Unexpected upload error: {e}"


def parse_pasted_csv(text: str) -> tuple[Optional[pd.DataFrame], Optional[str]]:
    if not text or not text.strip():
        return None, "Paste box is empty."

    attempts = [
        {"sep": ","},
        {"sep": ";"},
        {"sep": None, "engine": "python"},
    ]
    last_error = None

    for attempt in attempts:
        try:
            df = pd.read_csv(io.StringIO(text.strip()), **attempt)
            return df, None
        except Exception as e:
            last_error = e

    return None, f"Could not parse pasted CSV text: {last_error}"


def inspect_dataframe(df: pd.DataFrame) -> dict:
    normalized = normalize_columns(df)
    normalized_cols = list(normalized.columns)
    matched = [c for c in EXPECTED_COLS if c in normalized_cols]
    return {
        "rows": int(len(df)),
        "cols": int(len(df.columns)),
        "normalized_columns": normalized_cols,
        "matched_expected_columns": matched,
        "missing_expected_columns": [c for c in EXPECTED_COLS if c not in normalized_cols],
        "duplicate_columns": normalized.columns[normalized.columns.duplicated()].tolist(),
        "blank_rows": int(df.isna().all(axis=1).sum()) if len(df) else 0,
    }


def convert_numeric_columns(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    return out


def prepare_props_df(df: pd.DataFrame) -> pd.DataFrame:
    out = normalize_columns(df)
    out = convert_numeric_columns(out, ["odds", "point", "projection", "edge", "hit_pct", "ev_edge", "score"])

    if "sport" in out.columns:
        out = out[out["sport"].astype(str).str.upper().str.contains("NBA", na=False)].copy()
    elif "league" in out.columns:
        out = out[out["league"].astype(str).str.upper().str.contains("NBA", na=False)].copy()

    return out


def display_data_summary(df: pd.DataFrame):
    report = inspect_dataframe(df)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows", report["rows"])
    c2.metric("Columns", report["cols"])
    c3.metric("Blank rows", report["blank_rows"])
    c4.metric("Expected cols found", len(report["matched_expected_columns"]))

    st.subheader("Preview")
    st.dataframe(df.head(50), use_container_width=True)

    st.subheader("Column Check")
    left, right = st.columns(2)
    with left:
        st.write("Detected columns")
        st.code("\n".join(report["normalized_columns"]) or "No columns")
    with right:
        st.write("Sports-AI style columns found")
        st.code(", ".join(report["matched_expected_columns"]) if report["matched_expected_columns"] else "None detected")

    if report["duplicate_columns"]:
        st.warning(f"Duplicate columns found after normalization: {report['duplicate_columns']}")

    with st.expander("Debug details", expanded=False):
        st.json(
            {
                "shape": list(df.shape),
                "dtypes": {k: str(v) for k, v in df.dtypes.astype(str).to_dict().items()},
                "missing_expected_columns": report["missing_expected_columns"],
            }
        )


# ---------- App ----------
ensure_session_defaults()

st.title("Sports AI Dashboard")
st.caption("Mobile-proof base app with upload, paste-in CSV, sample data, and an NBA props tab.")

tab1, tab2, tab3 = st.tabs(["Dashboard", "Data Input", "NBA Props"])

with tab1:
    st.subheader("Overview")
    st.write(
        "Use the Data Input tab to load data three ways: upload a file, paste CSV text directly, "
        "or load sample data. The app keeps the most recently loaded dataset active across tabs."
    )

    source = st.session_state.active_source
    active_df = st.session_state.active_df

    info_col1, info_col2 = st.columns(2)
    with info_col1:
        st.info(f"Active data source: {source}")
    with info_col2:
        if active_df is not None:
            st.success(f"Active rows: {len(active_df):,}")
        else:
            st.warning("No active dataset loaded yet.")

    st.markdown(
        '''
        **Mobile-proof options**

        - Upload a CSV or Excel file
        - Paste CSV text directly from Notes, Sheets, or email
        - Load built-in NBA sample data
        '''
    )

with tab2:
    st.subheader("Load Your Data")

    action_col1, action_col2 = st.columns(2)

    with action_col1:
        if st.button("Load Sample NBA Data", use_container_width=True):
            st.session_state.active_df = sample_nba_props_df()
            st.session_state.active_source = "Built-in sample data"
            st.success("Sample NBA data loaded.")

    with action_col2:
        if st.button("Clear Active Data", use_container_width=True):
            st.session_state.active_df = None
            st.session_state.active_source = "None"
            st.warning("Active data cleared.")

    st.divider()
    st.markdown("### Option 1 — Upload a file")
    uploaded_file = st.file_uploader(
        "Choose a CSV or Excel file",
        type=["csv", "xlsx", "xls"],
        help="If mobile upload is unreliable, use the paste option below instead.",
    )

    if uploaded_file is not None:
        st.write("File detected:", uploaded_file.name)
        st.write("File size:", f"{uploaded_file.size:,} bytes")
        with st.spinner("Reading file..."):
            df_upload, upload_error = try_read_uploaded_file(uploaded_file)

        if upload_error:
            st.error(upload_error)
        elif df_upload is not None:
            st.session_state.active_df = df_upload
            st.session_state.active_source = f"Uploaded file: {uploaded_file.name}"
            st.success("Uploaded file loaded successfully.")

    st.divider()
    st.markdown("### Option 2 — Paste CSV text directly")
    st.caption("This is the most reliable option on iPhone if file upload is inconsistent.")
    default_text = '''player,market,odds,point,sport,league,book,projection,edge,hit_pct,ev_edge,score,is_starter,team,opponent,game
Stephen Curry,Points Over,-115,27.5,NBA,NBA,DraftKings,32.2,4.7,66.7,12.7,70.9,True,GSW,LAL,GSW @ LAL
LeBron James,PRA Over,-110,38.5,NBA,NBA,FanDuel,43.8,5.3,64.8,12.2,67.7,True,LAL,GSW,GSW @ LAL'''
    pasted_csv = st.text_area("Paste CSV data here", value="", height=220, placeholder=default_text)

    paste_btn_col1, paste_btn_col2 = st.columns(2)
    with paste_btn_col1:
        if st.button("Load Pasted CSV", use_container_width=True):
            df_paste, paste_error = parse_pasted_csv(pasted_csv)
            if paste_error:
                st.error(paste_error)
            elif df_paste is not None:
                st.session_state.active_df = df_paste
                st.session_state.active_source = "Pasted CSV text"
                st.success("Pasted CSV loaded successfully.")

    with paste_btn_col2:
        st.download_button(
            "Download sample CSV",
            data=sample_nba_props_df().to_csv(index=False).encode("utf-8"),
            file_name="sample_nba_props.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.divider()
    st.markdown("### Active Dataset Preview")

    if st.session_state.active_df is None:
        st.info("No active data loaded yet. Use one of the options above.")
    else:
        st.write("Current source:", st.session_state.active_source)
        display_data_summary(st.session_state.active_df)

        normalized_df = normalize_columns(st.session_state.active_df)
        st.subheader("Normalized Copy")
        st.dataframe(normalized_df.head(20), use_container_width=True)
        st.download_button(
            "Download normalized active CSV",
            data=normalized_df.to_csv(index=False).encode("utf-8"),
            file_name="normalized_active_data.csv",
            mime="text/csv",
        )

with tab3:
    st.subheader("NBA Props")

    if st.session_state.active_df is None:
        st.info("Load data first in the Data Input tab, or use the built-in sample data.")
    else:
        props_df = prepare_props_df(st.session_state.active_df)

        if props_df.empty:
            st.warning("No NBA rows were found in the active dataset.")
        else:
            st.caption("Filters below update the displayed props table.")
            f1, f2, f3 = st.columns(3)

            with f1:
                odds_min, odds_max = st.slider(
                    "Odds range",
                    min_value=-300,
                    max_value=200,
                    value=(-300, 200),
                )

            with f2:
                if "market" in props_df.columns:
                    market_options = sorted([m for m in props_df["market"].dropna().astype(str).unique().tolist()])
                    selected_markets = st.multiselect("Markets", market_options, default=market_options[: min(5, len(market_options))])
                else:
                    selected_markets = []

            with f3:
                starters_only = False
                if "is_starter" in props_df.columns:
                    starters_only = st.toggle("Starters only", value=False)
                min_score = st.number_input("Minimum score", min_value=0.0, max_value=100.0, value=0.0, step=1.0)

            filtered = props_df.copy()

            if "odds" in filtered.columns:
                filtered = filtered[filtered["odds"].between(odds_min, odds_max, inclusive="both")]

            if selected_markets and "market" in filtered.columns:
                filtered = filtered[filtered["market"].astype(str).isin(selected_markets)]

            if starters_only and "is_starter" in filtered.columns:
                starter_vals = filtered["is_starter"].astype(str).str.lower()
                filtered = filtered[starter_vals.isin(["true", "1", "yes"])]

            if "score" in filtered.columns:
                filtered = filtered[filtered["score"].fillna(0) >= min_score]

            sort_col = "score" if "score" in filtered.columns else ("edge" if "edge" in filtered.columns else None)
            if sort_col:
                filtered = filtered.sort_values(sort_col, ascending=False)

            metric_col1, metric_col2, metric_col3 = st.columns(3)
            metric_col1.metric("Filtered props", len(filtered))
            metric_col2.metric("Books", filtered["book"].nunique() if "book" in filtered.columns else 0)
            metric_col3.metric("Players", filtered["player"].nunique() if "player" in filtered.columns else 0)

            display_cols = [
                c for c in [
                    "player", "market", "book", "odds", "point", "projection",
                    "edge", "hit_pct", "ev_edge", "score", "team", "opponent",
                    "game", "is_starter"
                ] if c in filtered.columns
            ]

            st.dataframe(filtered[display_cols], use_container_width=True)

            if not filtered.empty:
                st.download_button(
                    "Download filtered props CSV",
                    data=filtered.to_csv(index=False).encode("utf-8"),
                    file_name="filtered_nba_props.csv",
                    mime="text/csv",
                )

st.success("App ready. Use Data Input to load data, then review results in NBA Props.")
