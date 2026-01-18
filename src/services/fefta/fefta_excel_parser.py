"""
FEFTA Excel Parser
==================

Functions for parsing FEFTA Excel files from MOF.
Separated from the main crawler for better testability.
"""

import logging
from typing import List, Tuple

import pandas as pd

from .fefta_models import (
    FeftaRecord,
    FeftaExcelParseError,
)
from .fefta_constants import SHEET_NAME
from .fefta_helpers import (
    map_columns,
    normalize_circled_numeral,
    normalize_circled_numeral_optional,
)

# Configure logging
logger = logging.getLogger(__name__)


def parse_fefta_excel(saved_path: str) -> Tuple[List[FeftaRecord], pd.DataFrame]:
    """
    Parse the FEFTA Excel file and extract company records.

    Args:
        saved_path: Absolute path to the downloaded Excel file

    Returns:
        Tuple of (list of FeftaRecord, raw DataFrame)

    Raises:
        FeftaExcelParseError: If parsing fails

    Example:
        >>> records, df = parse_fefta_excel('/path/to/fefta.xlsx')
        >>> len(records)
        1500
    """
    logger.info(f"Parsing Excel file: {saved_path}")

    try:
        # Read the Excel file with specific sheet
        df = pd.read_excel(
            saved_path,
            sheet_name=SHEET_NAME,
            dtype=str,  # Read all as strings to preserve leading zeros
            engine="openpyxl",
        )
    except ValueError as e:
        if SHEET_NAME in str(e):
            raise FeftaExcelParseError(
                f"Sheet '{SHEET_NAME}' not found in Excel file. "
                f"Available sheets may have different names."
            )
        raise FeftaExcelParseError(f"Failed to read Excel file: {e}")
    except Exception as e:
        raise FeftaExcelParseError(f"Failed to read Excel file: {e}")

    # Map columns to our field names
    column_map = map_columns(df.columns.tolist())

    # Rename columns
    df_mapped = df.rename(columns=column_map)

    # Parse records, skipping empty/header rows
    records = []
    skipped_rows = 0
    for idx, row in df_mapped.iterrows():
        # Check if this is an empty or header row by looking at key fields
        securities_code = str(row.get("securities_code", "")).strip()
        isin_code = str(row.get("isin_code", "")).strip()

        # Skip rows where both securities_code and isin_code are empty/nan
        if not securities_code or securities_code == "nan" or not isin_code or isin_code == "nan":
            skipped_rows += 1
            logger.debug(f"Skipping row {idx}: empty securities_code or isin_code")
            continue

        try:
            record = _parse_row(row, idx)
            records.append(record)
        except FeftaExcelParseError as e:
            # Log warning and skip row if it can't be parsed
            # This handles edge cases like partial data rows
            logger.warning(f"Skipping row {idx}: {e}")
            skipped_rows += 1
            continue

    logger.info(f"Parsed {len(records)} records from Excel (skipped {skipped_rows} rows)")
    return records, df


def _parse_row(row: pd.Series, row_idx: int) -> FeftaRecord:
    """
    Parse a single row into a FeftaRecord.

    Args:
        row: Pandas Series representing the row
        row_idx: Row index for error messages

    Returns:
        FeftaRecord instance

    Raises:
        FeftaExcelParseError: If parsing fails
    """
    # Normalize circled numerals for category (required)
    category = normalize_circled_numeral(row.get("category", ""), row_idx, "category")

    # core_operator is optional - may be empty for non-core companies
    core_operator = normalize_circled_numeral_optional(
        row.get("core_operator", ""), row_idx, "core_operator"
    )

    return FeftaRecord(
        securities_code=str(row.get("securities_code", "")),
        isin_code=str(row.get("isin_code", "")),
        company_name_ja=str(row.get("company_name_ja", "")),
        issue_or_company_name=str(row.get("issue_or_company_name", "")),
        category=category,
        core_operator=core_operator,
    )
