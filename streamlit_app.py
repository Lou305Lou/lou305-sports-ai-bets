import streamlit as st

st.title("Minimal Upload Test")

uploaded_file = st.file_uploader("Upload a file", type=["csv", "xlsx", "xls"])

st.write("uploaded_file is None:", uploaded_file is None)

if uploaded_file is not None:
    st.success(f"Detected: {uploaded_file.name}")
