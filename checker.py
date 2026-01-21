import io
import re
from typing import Optional, Tuple

import pandas as pd
import requests
import streamlit as st


def parse_google_sheet_id(url: str) -> Optional[str]:
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
    return m.group(1) if m else None


def download_google_sheet_as_xlsx(url: str, timeout_s: int = 30) -> Tuple[Optional[bytes], Optional[str]]:
    sheet_id = parse_google_sheet_id(url)
    if not sheet_id:
        return None, "Could not detect a Google Sheets file id from the link."

    export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
    try:
        resp = requests.get(export_url, timeout=timeout_s)
    except requests.RequestException as exc:
        return None, f"Network error while downloading the sheet: {exc}"

    if resp.status_code != 200:
        return (
            None,
            f"Download failed (HTTP {resp.status_code}). If this is a private sheet, "
            "make it accessible or download/upload the file instead.",
        )

    return resp.content, None


st.title("XLSForm Checker")
st.write("Step 1: provide your XLSForm via **upload** or **Google Sheets link**.")

source = st.radio(
    "Choose input source",
    options=["Upload Excel file", "Google Sheets link"],
    horizontal=True,
)

file_bytes: Optional[bytes] = None
file_label: str = ""

if source == "Upload Excel file":
    uploaded_file = st.file_uploader("Upload XLSForm (.xls or .xlsx)", type=["xls", "xlsx"])
    if uploaded_file:
        file_bytes = uploaded_file.getvalue()
        file_label = uploaded_file.name
else:
    sheet_url = st.text_input(
        "Paste Google Sheets link",
        placeholder="https://docs.google.com/spreadsheets/d/<id>/edit#gid=0",
        help="We will download the sheet as .xlsx (publicly accessible sheets work best).",
    )
    load_clicked = st.button("Load sheet")
    if load_clicked:
        if not sheet_url.strip():
            st.error("Please paste a Google Sheets link.")
        else:
            with st.spinner("Downloading Google Sheet as .xlsx..."):
                data, err = download_google_sheet_as_xlsx(sheet_url.strip())
            if err:
                st.error(err)
            else:
                file_bytes = data
                file_label = "google-sheet.xlsx"

if not file_bytes:
    st.info("Provide an XLSForm (upload or link) to continue.")
    st.stop()

st.success(f"Loaded input: {file_label} ({len(file_bytes):,} bytes)")

# Minimal sanity check: can we read the survey sheet and name column?
try:
    survey_df = pd.read_excel(io.BytesIO(file_bytes), sheet_name="survey")
except Exception as exc:
    st.error(f"Unable to read the 'survey' sheet from this file: {exc}")
    st.stop()

if "name" not in survey_df.columns:
    st.error("The 'survey' sheet must contain a 'name' column.")
    st.stop()

st.success("Looks like a valid XLSForm structure (found 'survey' sheet and 'name' column).")
