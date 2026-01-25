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

# Check for required columns
required_columns = {"type", "name"}

missing_columns = required_columns - set(survey_df.columns)
if missing_columns:
    st.error(f"'survey' sheet is missing required columns: {', '.join(missing_columns)}")
    st.stop()

# Check for duplicate question names and output the row number if issue exist
dup_mask = (
    survey_df["name"].notna() &
    survey_df["name"].duplicated(keep=False)
)

if dup_mask.any():
    st.error("Duplicate question names found.")
    st.caption("Each question name must be unique in an XLSForm.")

    dup_df = survey_df.loc[dup_mask, ["name"]].copy()
    dup_df["excel_row"] = dup_df.index + 2
    dup_df = dup_df.sort_values(["name", "excel_row"])

    st.data_frame(
        dup_df[["excel_row", "name"]],
        use_container_width = True
    )
    st.stop()


# Check for invalid question names and output the row number if issue exists
invalid_name_mask = survey_df["name"].dropna().apply(
    lambda x: not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", str(x))
)

if invalid_name_mask.any():
    st.error(
        "Invalid question name found." 
        "Names must start with a letter and contain only letters, numbers, and underscores"
    )

    invalid_df = survey_df.loc[invalid_name_mask, ["name"]].copy()
    invalid_df["excel_row"] = invalid_df.index + 2

    st.dataframe(
        invalid_df[["excel_row", "name"]],
        user_container_width= True
    )
    st.stop()

# Check for select_one & select_multiple consistency
select_used = survey_df["type"].str.contains(
    r"select_(one|multiple)\b", regex = True, na = False
).any()

if select_used and "choices" not in xls.sheet_names:
    st.error("This form uses select_one / select_multiple but has no 'choices' sheet.")
    st.stop()

if "choices" in xls.sheet_names:
    choices_df = pd.read_excel(xls, sheet_name = "choices")

    if not {"list_name","name"}.issubset(choices_df.columns):
        st.error("'choices' sheet must contain 'list_name' and 'name' columns.")
        st.stop()

    defined_lists = set(choices_df["list_name"].dropna())

    used_lists = (
        survey_df["type"]
        .dropna()
        .str.extract(r"select_(?:one|multiple)\s+([^\s]+)")
        [0]
        .dropna()
    )

    missing_lists = set(used_lists) - defined_lists  #TODO: [Optional] Show row number where issue persists
    if missing_lists:
        st.error("Missing choice lists referenced in survey:")
        st.write(sorted(missing_lists))
        st.stop()

# Check for duplicate choices inside a list TODO: [Optional] Show row numbere where issue persists
if "choices" in xls.sheet_names:
    dup_mask = choices_df.duplicated(subset=["list_name", "name"], keep=False)
    dup_mask = dup_mask & choices_df["list_name"].notna() & choices_df["name"].notna()

    if dup_mask.any():
        st.error("Duplicate choice names found within the same list:")
        st.dataframe(choices_df.loc[dup_mask, ["list_name", "name"]])
        st.stop()

# Check for empty type or name cells
missing_type = survey_df["type"].isna()

if missing_type.any():
    st.error("Empty cells found in required column 'type'.")

    missing_type_df = survey_df.loc[missing_type, ["name"]].copy()
    missing_type_df["excel_row"] = missing_type_df.index + 2

    st.dataframe(
        missing_type_df[["excel_row", "name"]],
        user_container_width = True
    )
    st.stop()

# end_group / end_repeat rows may have empty name per XLSForm spec
end_types = {"end_group", "end_repeat"}
type_normalized = survey_df["type"].fillna("").astype(str).str.strip().str.lower()
rows_requiring_name = ~type_normalized.isin(end_types)
missing_name = survey_df["name"].isna() & rows_requiring_name # TODO: Show the row number where the issue persists
if missing_name.any():
    st.error("Empty cells found in required column 'name' (except 'end_group' / 'end_repeat' rows).")
    st.stop()


st.success("Basic XLSForm checks successful")