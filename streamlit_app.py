import io
from typing import Optional

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Sports AI Upload Debugger", layout="wide")


# ---------- Helpers ----------
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip().lower().replace(" ", "_") for c in out.columns]
    return out


def try_read_uploaded_file(uploaded_file) -> tuple[Optional[pd.DataFrame], Optional[str]]:
    """Safely read CSV or Excel upload and return (df, error_message)."""
    if uploaded_file is None:
        return None, "No file uploaded."

    filename = (uploaded_file.name or "").lower()

    try:
        file_bytes = uploaded_file.getvalue()
        if not file_bytes:
            return None, "The uploaded file appears to be empty."

        if filename.endswith(".csv"):
            # Try common CSV encodings / separators
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


REQUIRED_HINT_COLUMNS = [
    "sport", "league", "market", "book", "odds", "point", "player",
    "team", "opponent", "game", "event", "result"
]


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


# ---------- UI ----------
st.title("Sports AI Upload Debugger")
st.caption("Use this to confirm your file is uploading, loading, and being read correctly.")

with st.expander("What should happen after upload", expanded=False):
    st.write(
        "A valid file should load in a few seconds, show a success message, display row/column counts, "
        "preview the data, and list detected columns."
    )

uploaded_file = st.file_uploader(
    "Upload your bets/data file",
    type=["csv", "xlsx", "xls"],
    help="Supported formats: CSV and Excel"
)

if uploaded_file is None:
    st.info("Waiting for upload...")
    st.stop()

st.write("File detected:", uploaded_file.name)
st.write("File size:", f"{uploaded_file.size:,} bytes")

with st.spinner("Reading file..."):
    df, error_message = try_read_uploaded_file(uploaded_file)

if error_message:
    st.error(error_message)
    st.stop()

if df is None:
    st.error("The file did not load, but no detailed error was returned.")
    st.stop()

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

# Optional normalization for downstream use
st.subheader("Normalized Copy for Downstream Logic")
normalized_df = normalize_columns(df)
st.dataframe(normalized_df.head(20), use_container_width=True)

csv_data = normalized_df.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download normalized CSV",
    data=csv_data,
    file_name="normalized_uploaded_data.csv",
    mime="text/csv"
)

st.success("Upload test complete. If you can see the preview above, the uploader is working.")
