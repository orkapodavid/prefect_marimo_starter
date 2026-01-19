"""
FEFTA Excel Parser Unit Tests
==============================

Unit tests for the FEFTA Excel parser using a sample Excel file.

Run with: pytest tests/unit/fefta/test_fefta_excel_parser.py -v
"""

import pytest
from pathlib import Path

from src.services.fefta.fefta_excel_parser import parse_fefta_excel
from src.services.fefta.fefta_models import FeftaRecord, FeftaExcelParseError


# =============================================================================
# Test Configuration
# =============================================================================


SAMPLE_EXCEL_PATH = Path(__file__).parent.parent.parent / "inputs" / "fefta" / "fefta_sample.xlsx"


@pytest.fixture
def sample_excel_path():
    """Return path to the sample FEFTA Excel file."""
    assert SAMPLE_EXCEL_PATH.exists(), f"Sample file not found: {SAMPLE_EXCEL_PATH}"
    return str(SAMPLE_EXCEL_PATH)


# =============================================================================
# Tests for parse_fefta_excel
# =============================================================================


class TestParseFeftaExcel:
    """Tests for the main parse_fefta_excel function."""

    def test_parse_returns_records_and_dataframe(self, sample_excel_path):
        """Test that parsing returns a tuple of records and DataFrame."""
        records, df = parse_fefta_excel(sample_excel_path)

        assert isinstance(records, list)
        assert len(records) > 0
        assert all(isinstance(r, FeftaRecord) for r in records)

        # DataFrame should have columns
        assert df is not None
        assert len(df.columns) > 0

    def test_parsed_records_have_valid_securities_code(self, sample_excel_path):
        """Test that all parsed records have valid securities codes."""
        records, _ = parse_fefta_excel(sample_excel_path)

        for record in records:
            assert record.securities_code, "securities_code should not be empty"
            # Securities codes can be alphanumeric (e.g., "130A")
            assert record.securities_code.isalnum(), (
                f"Invalid securities_code: {record.securities_code}"
            )
            assert 4 <= len(record.securities_code) <= 5, (
                f"Unexpected length: {record.securities_code}"
            )

    def test_parsed_records_have_valid_isin_code(self, sample_excel_path):
        """Test that all parsed records have valid ISIN codes."""
        records, _ = parse_fefta_excel(sample_excel_path)

        for record in records:
            assert record.isin_code, "isin_code should not be empty"
            assert len(record.isin_code) == 12, f"ISIN should be 12 chars: {record.isin_code}"
            assert record.isin_code.startswith("JP"), (
                f"ISIN should start with JP: {record.isin_code}"
            )

    def test_parsed_records_have_valid_category(self, sample_excel_path):
        """Test that all parsed records have valid category values (1-10)."""
        records, _ = parse_fefta_excel(sample_excel_path)

        for record in records:
            assert 1 <= record.category <= 10, f"Category out of range: {record.category}"

    def test_parsed_records_have_company_names(self, sample_excel_path):
        """Test that all parsed records have company names."""
        records, _ = parse_fefta_excel(sample_excel_path)

        for record in records:
            assert record.company_name_ja, "Japanese company name should not be empty"
            assert record.issue_or_company_name, "English company name should not be empty"

    def test_core_operator_is_optional(self, sample_excel_path):
        """Test that core_operator can be None or a valid value (1-10)."""
        records, _ = parse_fefta_excel(sample_excel_path)

        for record in records:
            if record.core_operator is not None:
                assert 1 <= record.core_operator <= 10, (
                    f"core_operator out of range: {record.core_operator}"
                )

    def test_nonexistent_file_raises_error(self):
        """Test that parsing a nonexistent file raises FeftaExcelParseError."""
        with pytest.raises(FeftaExcelParseError):
            parse_fefta_excel("/nonexistent/path/to/file.xlsx")

    def test_invalid_file_raises_error(self, tmp_path):
        """Test that parsing an invalid file raises FeftaExcelParseError."""
        invalid_file = tmp_path / "invalid.xlsx"
        invalid_file.write_text("not an excel file")

        with pytest.raises(FeftaExcelParseError):
            parse_fefta_excel(str(invalid_file))


# =============================================================================
# Tests for record count and data integrity
# =============================================================================


class TestDataIntegrity:
    """Tests for data integrity of parsed records."""

    def test_minimum_record_count(self, sample_excel_path):
        """Test that the sample file contains a reasonable number of records."""
        records, _ = parse_fefta_excel(sample_excel_path)

        # Sample file should have at least a few records for testing
        assert len(records) >= 1, "Expected at least 1 record in sample file"

    def test_no_duplicate_isin_codes(self, sample_excel_path):
        """Test that there are no duplicate ISIN codes in the parsed records."""
        records, _ = parse_fefta_excel(sample_excel_path)

        isin_codes = [r.isin_code for r in records]
        unique_codes = set(isin_codes)

        assert len(isin_codes) == len(unique_codes), "Found duplicate ISIN codes"

    def test_dataframe_row_count_matches_or_exceeds_records(self, sample_excel_path):
        """Test that DataFrame has at least as many rows as records (may have header/empty rows)."""
        records, df = parse_fefta_excel(sample_excel_path)

        # DataFrame may have more rows due to headers/empty rows that get skipped
        assert len(df) >= len(records), "DataFrame should have at least as many rows as records"


# =============================================================================
# Specific Row Tests - Fail Fast on Format Changes
# =============================================================================


class TestSpecificRecords:
    """
    Tests for specific records in the sample file.

    These tests verify exact values for known records to detect
    Excel format changes early. If these fail, the Excel format
    has likely changed and the parser needs updating.
    """

    @pytest.fixture
    def parsed_records(self, sample_excel_path):
        """Parse records once for all tests in this class."""
        records, _ = parse_fefta_excel(sample_excel_path)
        return {r.securities_code: r for r in records}

    def test_first_record_kyokuyo(self, parsed_records):
        """Test first record: 株式会社極洋 (KYOKUYO CO.,LTD.)"""
        record = parsed_records.get("1301")
        assert record is not None, "Record 1301 not found"

        assert record.securities_code == "1301"
        assert record.isin_code == "JP3257200000"
        assert "極洋" in record.company_name_ja
        assert "KYOKUYO" in record.issue_or_company_name.upper()
        assert record.category == 1
        assert record.core_operator is None

    def test_record_with_core_operator_inpex(self, parsed_records):
        """Test record with core_operator: 株式会社ＩＮＰＥＸ (INPEX)"""
        record = parsed_records.get("1605")
        assert record is not None, "Record 1605 not found"

        assert record.securities_code == "1605"
        assert record.isin_code == "JP3294460005"
        assert "ＩＮＰＥＸ" in record.company_name_ja or "INPEX" in record.company_name_ja
        assert record.category == 3
        assert record.core_operator == 4, "INPEX should have core_operator=4"

    def test_record_with_core_operator_rakuten(self, parsed_records):
        """Test record with core_operator: 楽天グループ株式会社 (Rakuten)"""
        record = parsed_records.get("4755")
        assert record is not None, "Record 4755 not found"

        assert record.securities_code == "4755"
        assert record.isin_code == "JP3967200001"
        assert "楽天" in record.company_name_ja
        assert record.category == 3
        assert record.core_operator == 4, "Rakuten should have core_operator=4"

    def test_alphanumeric_securities_code_130a(self, parsed_records):
        """Test alphanumeric securities code: 130A"""
        record = parsed_records.get("130A")
        assert record is not None, "Record 130A not found"

        assert record.securities_code == "130A"
        assert record.isin_code == "JP3155340007"
        assert record.category in [1, 2, 3]  # Valid category range
        # core_operator may or may not be set

    def test_category_1_record(self, parsed_records):
        """Test a Category 1 record exists and is valid."""
        # 1301 is category 1
        record = parsed_records.get("1301")
        assert record is not None
        assert record.category == 1

    def test_category_2_record(self, parsed_records):
        """Test a Category 2 record: 株式会社ニッスイ -> Actually category 3, use different one."""
        # 1333 is category 2
        record = parsed_records.get("1333")
        assert record is not None
        assert record.category == 2
        assert "マルハニチロ" in record.company_name_ja

    def test_category_3_record(self, parsed_records):
        """Test a Category 3 record: 株式会社ニッスイ (Nissui Corporation)"""
        record = parsed_records.get("1332")
        assert record is not None
        assert record.category == 3
        assert "ニッスイ" in record.company_name_ja


class TestExpectedCounts:
    """
    Tests for expected record counts and distributions.

    These tests verify the sample file has expected characteristics
    to detect if the file was truncated or corrupted.
    """

    def test_expected_total_record_count(self, sample_excel_path):
        """Test that the sample file has approximately the expected number of records."""
        records, _ = parse_fefta_excel(sample_excel_path)

        # Based on sample file: 4041 records
        # Allow some variation for minor updates
        assert len(records) >= 4000, f"Expected at least 4000 records, got {len(records)}"
        assert len(records) <= 5000, f"Expected at most 5000 records, got {len(records)}"

    def test_category_distribution(self, sample_excel_path):
        """Test that all three categories are represented."""
        records, _ = parse_fefta_excel(sample_excel_path)

        from collections import Counter

        cat_dist = Counter(r.category for r in records)

        # All three categories should have significant counts
        assert cat_dist[1] >= 1000, f"Category 1 count too low: {cat_dist[1]}"
        assert cat_dist[2] >= 500, f"Category 2 count too low: {cat_dist[2]}"
        assert cat_dist[3] >= 500, f"Category 3 count too low: {cat_dist[3]}"

    def test_core_operator_records_exist(self, sample_excel_path):
        """Test that some records have core_operator set."""
        records, _ = parse_fefta_excel(sample_excel_path)

        core_records = [r for r in records if r.core_operator is not None]

        # Based on sample: 46 records with core_operator
        assert len(core_records) >= 40, (
            f"Expected at least 40 core_operator records, got {len(core_records)}"
        )

    def test_alphanumeric_codes_exist(self, sample_excel_path):
        """Test that alphanumeric securities codes exist (e.g., 130A)."""
        records, _ = parse_fefta_excel(sample_excel_path)

        alpha_codes = [r for r in records if not r.securities_code.isdigit()]

        # Based on sample: 170 alphanumeric codes
        assert len(alpha_codes) >= 100, (
            f"Expected at least 100 alphanumeric codes, got {len(alpha_codes)}"
        )
