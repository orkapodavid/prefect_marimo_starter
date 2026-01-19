"""
FEFTA Crawler Integration Tests
===============================

Integration tests for the FEFTA crawler.
These tests perform real HTTP requests to the MOF website.

Run with: pytest tests/unit/fefta/test_fefta_crawler.py -v
"""

import pytest
from datetime import date
from pathlib import Path

from src.services.fefta import (
    FeftaCrawler,
    FeftaSource,
    FeftaRecord,
)
from src.services.fefta.fefta_excel_parser import parse_fefta_excel


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
            records, df = parse_fefta_excel(source.saved_path)

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
