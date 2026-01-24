import io
from typing import Optional

import re
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

#----- Basic Validation: -----
st.subheader("Basic XLSForm Validation")
 
try:
    xls = pd.ExcelFile(io.BytesIO(file_bytes))
except Exception as exc:
    st.error(f"Not a valid Excel file: {exc}")
    st.stop()

# Check for required sheets
required_sheets = {"survey"}

missing_sheets = required_sheets - set(xls.sheet_names)

if missing_sheets:
    st.error(f"Missing required sheets: {', '.join(missing_sheets)}")
    st.stop()

survey_df = pd.read_excel(xls, sheet_name="survey")

# Check for required columns
required_columns = {"type", "name"}

missing_columns = required_columns - set(survey_df.columns)
if missing_columns:
    st.error(f"'survey' sheet is missing required columns: {', '.join(missing_columns)}")
    st.stop()

# Check for duplicate question names
duplicates = survey_df["name"][survey_df["name"].duplicated()].dropna()
if not duplicates.empty:
    st.error(f"Duplicate question names found:")
    st.write(sorted(duplicates.unique()))
    st.stop()

# Check for invalid question names
invalid_name_mask = survey_df["name"].dropna().apply(
    lambda x: not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", str(x))
)

if invalid_name_mask.any():
    st.error(f"Invalid question names (must start with a letter and contain only letters, numbers, and underscores): ")
    st.dataframe(survey_df.loc[invalid_name_mask, ["name"]])
    st.stop()

# Check for select_one & select_multiple consistency
if "choices" in xls.sheet_names:
    choices_df = pd.read_excel(xls, sheet_name = "choices")

    if not {"list_name","name"}.issubset(choices_df.columns):
        st.error("'choices' sheet must contain 'list_name' and 'name' columns.")
        st.stop()

    defined_lists = set(choices_df["list_name"].dropna())

    used_lists = (
        survey_df["type"]
        .dropna()
        .str.extract(r"select_(?:one|multiple)\s+(.+)")
        [0]
        .dropna()
    )

    missing_lists = set(used_lists) - defined_lists
    if missing_lists:
        st.error("Missing choice lists referenced in survey:")
        st.write(sorted(missing_lists))
        st.stop()

st.success("Basic XLSForm checks successful")