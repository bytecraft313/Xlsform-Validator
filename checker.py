import io
from typing import Optional

import pandas as pd
import streamlit as st


st.title("XLSForm Checker")
st.write("Step 1: upload your XLSForm as an Excel file (.xls or .xlsx).")

uploaded_file = st.file_uploader(
    "Upload XLSForm (.xls or .xlsx)",
    type=["xls", "xlsx"]
)

file_bytes: Optional[bytes] = None
file_label: str = ""

if uploaded_file:
    file_bytes = uploaded_file.getvalue()
    file_label = uploaded_file.name

if not file_bytes:
    st.info("Please upload an Excel XLSForm to continue.")
    st.stop()

st.success(f"Loaded input: {file_label} ({len(file_bytes):,} bytes)")

try:
    survey_df = pd.read_excel(
        io.BytesIO(file_bytes),
        sheet_name="survey"
    )
except Exception as exc:
    st.error(f"Unable to read the 'survey' sheet from this file: {exc}")
    st.stop()

if "name" not in survey_df.columns:
    st.error("The 'survey' sheet must contain a 'name' column.")
    st.stop()

st.success(
    "Looks like a valid XLSForm structure "
    "(found 'survey' sheet and 'name' column)."
)

# 1. Basic Validation:
st.subheader("Basic XLSForm Validation")
 
try:
    xls = pd.ExcelFile(io.BytesIO(file_bytes))
except Exception as exc:
    st.error(f"Not a valid Excel file: {exc}")
    st.stop()

# Check for required sheets
required_sheets = ["survey", "choices", "settings"]
missing_sheets = required_sheets - set(xls.sheet_names)

if missing_sheets:
    st.error(f"Missing required sheets: {', '.join(missing_sheets)}")
    st.stop()

survey_df = pd.read_excel(xls, sheet_name="survey")

# Check for required columns
required_columns = ["name", "type", "label", "required"]
missing_columns = required_columns - set(survey_df.columns)
if missing_columns:
    st.error(f"'survey' sheet is missing required columns: {', '.join(missing_columns)}")
    st.stop()

# Check for duplicate question names

    