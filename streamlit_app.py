import io
from typing import Optional

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Sports AI Dashboard", layout="wide")


# ------------------------------
# Helpers
# ------------------------------
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip().lower().replace(" ", "_") for c in out.columns]
    return out


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
            try:
                return pd.read_excel(io.BytesIO(file_bytes)), None
            except Exception as e:
                return None, f"Excel read failed: {e}"

        return None, "Unsupported file type. Please upload a .csv, .xlsx, or .xls file."

    except Exception as e:
        return None, f"Unexpected upload error: {e}"


def coerce_numeric(series: pd.Series) -> pd.Series:
    if series is None:
        return series
    cleaned = (
        series.astype(str)
        .str.replace("%", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    return pd.to_numeric(cleaned, errors="coerce")


def american_to_implied_prob(odds: float) -> Optional[float]:
    try:
        odds = float(odds)
    except Exception:
        return None
    if odds == 0:
        return None
    if odds > 0:
        return 100 / (odds + 100)
    return abs(odds) / (abs(odds) + 100)


def expected_value(prob: float, odds: float) -> Optional[float]:
    try:
        prob = float(prob)
        odds = float(odds)
    except Exception:
        return None

    if prob <= 0 or prob >= 1:
        return None

    if odds > 0:
        profit = odds / 100
    else:
        profit = 100 / abs(odds)

    return prob * profit - (1 - prob)


REQUIRED_HINT_COLUMNS = [
    "sport", "league", "market", "book", "odds", "point", "player",
    "team", "opponent", "game", "event", "result"
]


PROP_CANDIDATE_MAP = {
    "player": ["player", "player_name", "name"],
    "market": ["market", "bet_type", "stat_type", "prop_type"],
    "line": ["point", "line", "prop_line"],
    "odds": ["odds", "price", "american_odds"],
    "projection": ["projection", "proj", "model_projection"],
    "hit_rate": ["hit_rate", "hit_%", "win_prob", "probability", "model_prob"],
    "book": ["book", "sportsbook"],
    "team": ["team"],
    "opponent": ["opponent", "opp"],
    "game": ["game", "matchup", "event"],
}


def find_column(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    for col in candidates:
        if col in df.columns:
            return col
    return None



def inspect_dataframe(df: pd.DataFrame) -> dict:
    cols = [str(c) for c in df.columns]
    normalized = normalize_columns(df)
    normalized_cols = list(normalized.columns)
    matched = [c for c in REQUIRED_HINT_COLUMNS if c in normalized_cols]

    return {
        "rows": int(len(df)),
        "cols": int(len(df.columns)),
        "original_columns": cols,
        "normalized_columns": normalized_cols,
        "matched_expected_columns": matched,
        "missing_expected_columns": [c for c in REQUIRED_HINT_COLUMNS if c not in normalized_cols],
        "duplicate_columns": normalized.columns[normalized.columns.duplicated()].tolist(),
        "null_rows": int(df.isna().all(axis=1).sum()) if len(df) else 0,
    }



def build_nba_props_view(df: pd.DataFrame, odds_min: int, odds_max: int, starters_only: bool) -> pd.DataFrame:
    data = normalize_columns(df)

    sport_col = find_column(data, ["sport", "league"])
    if sport_col:
        sport_mask = data[sport_col].astype(str).str.upper().str.contains("NBA", na=False)
        data = data[sport_mask].copy()

    player_col = find_column(data, PROP_CANDIDATE_MAP["player"])
    market_col = find_column(data, PROP_CANDIDATE_MAP["market"])
    line_col = find_column(data, PROP_CANDIDATE_MAP["line"])
    odds_col = find_column(data, PROP_CANDIDATE_MAP["odds"])
    projection_col = find_column(data, PROP_CANDIDATE_MAP["projection"])
    hit_rate_col = find_column(data, PROP_CANDIDATE_MAP["hit_rate"])
    book_col = find_column(data, PROP_CANDIDATE_MAP["book"])
    team_col = find_column(data, PROP_CANDIDATE_MAP["team"])
    opponent_col = find_column(data, PROP_CANDIDATE_MAP["opponent"])
    game_col = find_column(data, PROP_CANDIDATE_MAP["game"])

    if odds_col is None:
        return pd.DataFrame()

    data["_odds_num"] = coerce_numeric(data[odds_col])
    data = data[data["_odds_num"].between(odds_min, odds_max, inclusive="both")].copy()

    if starters_only and "is_starter" in data.columns:
        starter_mask = data["is_starter"].astype(str).str.lower().isin(["true", "1", "yes", "y"])
        data = data[starter_mask].copy()

    if projection_col and line_col:
        data["_line_num"] = coerce_numeric(data[line_col])
        data["_proj_num"] = coerce_numeric(data[projection_col])
        data["edge"] = data["_proj_num"] - data["_line_num"]
    else:
        data["edge"] = pd.NA

    if hit_rate_col:
        hit_raw = coerce_numeric(data[hit_rate_col])
        data["hit_rate"] = hit_raw.where(hit_raw <= 1, hit_raw / 100)
    else:
        data["hit_rate"] = data["_odds_num"].apply(american_to_implied_prob)

    data["implied_prob"] = data["_odds_num"].apply(american_to_implied_prob)
    data["ev"] = [
        expected_value(p, o) if pd.notna(p) and pd.notna(o) else None
        for p, o in zip(data["hit_rate"], data["_odds_num"])
    ]

    display = pd.DataFrame()
    display["Player"] = data[player_col] if player_col else ""
    display["Market"] = data[market_col] if market_col else ""
    display["Line"] = data[line_col] if line_col else ""
    display["Odds"] = data[odds_col] if odds_col else ""
    display["Projection"] = data[projection_col] if projection_col else ""
    display["Edge"] = data["edge"]
    display["Hit %"] = data["hit_rate"]
    display["EV"] = data["ev"]
    display["Book"] = data[book_col] if book_col else ""
    display["Team"] = data[team_col] if team_col else ""
    display["Opponent"] = data[opponent_col] if opponent_col else ""
    display["Game"] = data[game_col] if game_col else ""

    if "Hit %" in display.columns:
        display["Hit %"] = (display["Hit %"] * 100).round(1)
    if "EV" in display.columns:
        display["EV"] = (display["EV"] * 100).round(2)
    if "Edge" in display.columns:
        display["Edge"] = pd.to_numeric(display["Edge"], errors="coerce").round(2)

    sort_cols = [c for c in ["EV", "Edge", "Hit %"] if c in display.columns]
    if sort_cols:
        display = display.sort_values(by=sort_cols, ascending=False, na_position="last")

    return display.reset_index(drop=True)


# ------------------------------
# App
# ------------------------------
st.title("Sports AI Dashboard")
st.caption("Full downloadable base app with safer upload handling and an NBA props tab.")

main_tab, upload_tab, props_tab = st.tabs(["Dashboard", "Upload Debug", "NBA Props"])

with main_tab:
    st.subheader("Overview")
    st.write(
        "This is a stable base version built for mobile-friendly use. Upload a CSV or Excel file in the "
        "Upload Debug tab, then review detected data and NBA props in the NBA Props tab."
    )
    st.info(
        "This file is a clean replacement base. It does not include all custom V7/V8 logic from your earlier app, "
        "but it gives you a working foundation with safer uploads and props filtering."
    )

with upload_tab:
    st.subheader("Upload your bets/data file")

    uploaded_file = st.file_uploader(
        "Choose a CSV or Excel file",
        type=["csv", "xlsx", "xls"],
        help="Supported formats: CSV, XLSX, XLS"
    )

    if uploaded_file is None:
        st.info("Waiting for upload...")
    else:
        st.write("File detected:", uploaded_file.name)
        st.write("File size:", f"{uploaded_file.size:,} bytes")

        with st.spinner("Reading file..."):
            df, error_message = try_read_uploaded_file(uploaded_file)

        if error_message:
            st.error(error_message)
        elif df is None:
            st.error("The file did not load, but no detailed error was returned.")
        else:
            st.session_state["uploaded_df"] = df.copy()
            st.session_state["uploaded_name"] = uploaded_file.name

            if len(df) == 0:
                st.warning("The file loaded, but it has 0 rows.")
            else:
                st.success("File loaded successfully.")

            report = inspect_dataframe(df)
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Rows", report["rows"])
            col2.metric("Columns", report["cols"])
            col3.metric("Blank rows", report["null_rows"])
            col4.metric("Expected cols found", len(report["matched_expected_columns"]))

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
                st.json({
                    "filename": uploaded_file.name,
                    "shape": list(df.shape),
                    "dtypes": {k: str(v) for k, v in df.dtypes.astype(str).to_dict().items()},
                    "missing_expected_columns": report["missing_expected_columns"],
                })

            normalized_df = normalize_columns(df)
            csv_data = normalized_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download normalized CSV",
                data=csv_data,
                file_name="normalized_uploaded_data.csv",
                mime="text/csv"
            )

with props_tab:
    st.subheader("NBA Player Props")
    st.caption("Starter base version with odds filter and optional starters-only mode.")

    source_df = st.session_state.get("uploaded_df")
    if source_df is None:
        st.warning("Upload a file first in the Upload Debug tab.")
    else:
        c1, c2, c3 = st.columns(3)
        with c1:
            odds_min = st.number_input("Minimum odds", min_value=-1000, max_value=2000, value=-300, step=5)
        with c2:
            odds_max = st.number_input("Maximum odds", min_value=-1000, max_value=2000, value=200, step=5)
        with c3:
            starters_only = st.checkbox("Starters only", value=False)

        props_df = build_nba_props_view(source_df, odds_min=odds_min, odds_max=odds_max, starters_only=starters_only)

        if props_df.empty:
            st.info(
                "No NBA props matched the current filters, or your uploaded file does not yet include the columns "
                "needed for the props view."
            )
            st.write("Helpful columns for this tab: player, market, point/line, odds, projection, hit_rate, team, opponent, game.")
        else:
            st.success(f"Found {len(props_df)} prop rows.")
            st.dataframe(props_df, use_container_width=True)

            export_csv = props_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download NBA props view",
                data=export_csv,
                file_name="nba_props_view.csv",
                mime="text/csv"
            )
