"""
FEFTA Crawler Smoke Tests
=========================

Smoke tests to verify the FEFTA crawler functionality.
These tests perform real HTTP requests to the MOF website.

Run with: pytest tests/unit/fefta/test_crawler.py -v
"""

import pytest
from datetime import date
from pathlib import Path

from src.services.fefta import (
    FeftaCrawler,
    FeftaSource,
    FeftaRecord,
    FeftaCrawlerError,
    FeftaLinkNotFoundError,
    FeftaDateParseError,
    FeftaExcelParseError,
)


# =============================================================================
# Test Configuration
# =============================================================================


@pytest.fixture
def crawler():
    """Create a FeftaCrawler instance for testing."""
    with FeftaCrawler() as c:
        yield c


@pytest.fixture
def output_dir(tmp_path):
    """Create a temporary output directory."""
    return tmp_path / "fefta_output"


# =============================================================================
# Unit Tests - Date Parsing
# =============================================================================


class TestDateParsing:
    """Test the 'As of' date parsing functionality."""

    def test_parse_as_of_date_standard_format(self, crawler):
        """Test parsing standard date format: 'As of 15 July, 2025'."""
        link_text = 'the "List of classifications..." FEFTA (As of 15 July, 2025)(Excel:296KB)'
        as_of_raw, as_of_date = crawler._parse_as_of_date(link_text)

        assert as_of_raw == "As of 15 July, 2025"
        assert as_of_date == date(2025, 7, 15)

    def test_parse_as_of_date_without_comma(self, crawler):
        """Test parsing date without comma: 'As of 15 July 2025'."""
        link_text = "FEFTA (As of 1 January 2026)(Excel:100KB)"
        as_of_raw, as_of_date = crawler._parse_as_of_date(link_text)

        assert as_of_date == date(2026, 1, 1)

    def test_parse_as_of_date_abbreviated_month(self, crawler):
        """Test parsing abbreviated month names."""
        link_text = "FEFTA document (As of 5 Jan, 2025)"
        as_of_raw, as_of_date = crawler._parse_as_of_date(link_text)

        assert as_of_date == date(2025, 1, 5)

    def test_parse_as_of_date_invalid_raises_error(self, crawler):
        """Test that invalid date format raises FeftaDateParseError."""
        link_text = "FEFTA document without date"

        with pytest.raises(FeftaDateParseError):
            crawler._parse_as_of_date(link_text)

    def test_parse_as_of_date_invalid_month_raises_error(self, crawler):
        """Test that unknown month name raises FeftaDateParseError."""
        link_text = "FEFTA (As of 15 Smarch, 2025)"

        with pytest.raises(FeftaDateParseError):
            crawler._parse_as_of_date(link_text)


# =============================================================================
# Unit Tests - Circled Numeral Normalization
# =============================================================================


class TestCircledNumeralNormalization:
    """Test the circled numeral to integer conversion."""

    @pytest.mark.parametrize(
        "circled,expected",
        [
            ("①", 1),
            ("②", 2),
            ("③", 3),
            ("④", 4),
            ("⑤", 5),
            ("⑥", 6),
            ("⑦", 7),
            ("⑧", 8),
            ("⑨", 9),
            ("⑩", 10),
        ],
    )
    def test_circled_numerals(self, crawler, circled, expected):
        """Test all circled numerals map correctly."""
        result = crawler._normalize_circled_numeral(circled, 0, "test")
        assert result == expected

    @pytest.mark.parametrize("plain_digit", ["1", "5", "10", "3.0"])
    def test_plain_digits(self, crawler, plain_digit):
        """Test plain digit strings are converted correctly."""
        result = crawler._normalize_circled_numeral(plain_digit, 0, "test")
        assert isinstance(result, int)
        assert 1 <= result <= 10

    def test_empty_value_raises_error(self, crawler):
        """Test empty value raises FeftaExcelParseError."""
        with pytest.raises(FeftaExcelParseError):
            crawler._normalize_circled_numeral("", 0, "category")

    def test_out_of_range_raises_error(self, crawler):
        """Test out-of-range value raises FeftaExcelParseError."""
        with pytest.raises(FeftaExcelParseError):
            crawler._normalize_circled_numeral("15", 0, "category")

    def test_invalid_value_raises_error(self, crawler):
        """Test invalid value raises FeftaExcelParseError."""
        with pytest.raises(FeftaExcelParseError):
            crawler._normalize_circled_numeral("abc", 0, "category")


# =============================================================================
# Integration Tests - Live HTTP Requests
# =============================================================================


class TestFeftaCrawlerIntegration:
    """
    Integration tests that make real HTTP requests to MOF website.

    These tests verify the full crawler functionality works with the
    live website.
    """

    @pytest.mark.integration
    def test_fetch_latest_source(self, crawler):
        """Test fetching the latest FEFTA source metadata."""
        source = crawler.fetch_latest_source()

        # Verify FeftaSource fields
        assert isinstance(source, FeftaSource)
        assert source.as_of_raw.startswith("As of")
        assert isinstance(source.as_of_date, date)
        assert source.download_date == date.today()
        assert source.file_url.endswith(".xlsx")
        assert "mof.go.jp" in source.file_url
        assert source.saved_path is None  # Not downloaded yet

        print(f"\nFound source: {source.as_of_raw}")
        print(f"URL: {source.file_url}")

    @pytest.mark.integration
    def test_download_excel(self, output_dir):
        """Test downloading the Excel file."""
        with FeftaCrawler(output_dir=output_dir) as crawler:
            source = crawler.fetch_latest_source()
            source = crawler.download_excel(source)

            # Verify file was saved
            assert source.saved_path is not None
            saved_path = Path(source.saved_path)
            assert saved_path.exists()
            assert saved_path.suffix == ".xlsx"

            # Verify filename has date prefix
            today_prefix = date.today().strftime("%Y_%m_%d")
            assert today_prefix in saved_path.name

            print(f"\nSaved to: {source.saved_path}")
            print(f"File size: {saved_path.stat().st_size} bytes")

    @pytest.mark.integration
    def test_parse_records(self, output_dir):
        """Test parsing records from downloaded Excel."""
        with FeftaCrawler(output_dir=output_dir) as crawler:
            source = crawler.fetch_latest_source()
            source = crawler.download_excel(source)
            records, df = crawler.parse_records(source.saved_path)

            # Verify records
            assert len(records) > 0
            assert all(isinstance(r, FeftaRecord) for r in records)

            # Check first record structure
            first = records[0]
            assert first.securities_code  # Not empty
            assert first.isin_code  # Not empty
            assert first.company_name_ja  # Japanese name present
            assert 1 <= first.category <= 10
            # core_operator is optional - may be None for non-core companies
            assert first.core_operator is None or 1 <= first.core_operator <= 10

            print(f"\nParsed {len(records)} records")
            print(f"DataFrame shape: {df.shape}")
            print(f"\nFirst record:")
            print(f"  Securities Code: {first.securities_code}")
            print(f"  ISIN: {first.isin_code}")
            print(f"  Company (JP): {first.company_name_ja}")
            print(f"  Company (EN): {first.issue_or_company_name}")
            print(f"  Category: {first.category}")
            print(f"  Core Operator: {first.core_operator}")

    @pytest.mark.integration
    def test_full_run(self, output_dir):
        """Test the complete end-to-end workflow."""
        with FeftaCrawler(output_dir=output_dir) as crawler:
            source, records = crawler.run()

            # Verify source
            assert isinstance(source, FeftaSource)
            assert source.saved_path is not None
            assert Path(source.saved_path).exists()

            # Verify records
            assert len(records) > 0
            assert all(isinstance(r, FeftaRecord) for r in records)

            print(f"\n=== FEFTA Crawler Full Run ===")
            print(f"As of: {source.as_of_date}")
            print(f"Downloaded: {source.download_date}")
            print(f"File URL: {source.file_url}")
            print(f"Saved to: {source.saved_path}")
            print(f"Total records: {len(records)}")

            # Show sample records
            print(f"\nSample records:")
            for i, record in enumerate(records[:3]):
                print(
                    f"  {i + 1}. {record.securities_code} - "
                    f"{record.company_name_ja[:20]}... "
                    f"(cat: {record.category}, core: {record.core_operator})"
                )


# =============================================================================
# Smoke Test - Quick Verification
# =============================================================================


class TestSmokeTest:
    """
    Quick smoke test to verify basic functionality.

    Run this test to quickly check if the crawler is working:
        pytest tests/unit/fefta/test_crawler.py::TestSmokeTest -v
    """

    @pytest.mark.integration
    def test_smoke_crawl_fefta(self, tmp_path):
        """
        Smoke test: Verify the crawler can fetch, download, and parse
        FEFTA data from the MOF website.
        """
        output_dir = tmp_path / "fefta"

        print("\n" + "=" * 60)
        print("FEFTA CRAWLER SMOKE TEST")
        print("=" * 60)

        with FeftaCrawler(output_dir=output_dir) as crawler:
            # Step 1: Fetch source metadata
            print("\n[1/3] Fetching source metadata from MOF...")
            source = crawler.fetch_latest_source()
            print(f"  ✓ Found FEFTA Excel link")
            print(f"  ✓ As of: {source.as_of_date}")
            print(f"  ✓ URL: {source.file_url[:60]}...")

            # Step 2: Download Excel
            print("\n[2/3] Downloading Excel file...")
            source = crawler.download_excel(source)
            file_size = Path(source.saved_path).stat().st_size
            print(f"  ✓ Saved to: {source.saved_path}")
            print(f"  ✓ Size: {file_size:,} bytes")

            # Step 3: Parse records
            print("\n[3/3] Parsing Excel records...")
            records, df = crawler.parse_records(source.saved_path)
            print(f"  ✓ Parsed {len(records)} company records")
            print(f"  ✓ DataFrame shape: {df.shape}")

            # Summary
            print("\n" + "-" * 60)
            print("SMOKE TEST PASSED ✓")
            print("-" * 60)
            print(f"Total Companies: {len(records)}")
            print(f"Data As Of: {source.as_of_date}")
            print(f"Downloaded: {source.download_date}")

            # Assertions
            assert len(records) > 100, "Expected at least 100 company records"
            assert source.saved_path is not None
            assert Path(source.saved_path).exists()

            # Sample output
            print("\nSample Records:")
            for r in records[:5]:
                print(
                    f"  {r.securities_code} | {r.isin_code} | "
                    f"{r.company_name_ja[:15]}... | "
                    f"cat={r.category} core={r.core_operator}"
                )
