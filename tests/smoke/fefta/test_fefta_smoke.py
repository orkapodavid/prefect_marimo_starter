"""
FEFTA Crawler Smoke Test
========================

Smoke test that verifies the FEFTA crawler works with live MOF website.
This test makes actual HTTP requests and parses the FEFTA Excel file.

Run with: pytest tests/smoke/fefta/test_fefta_smoke.py -v -s

Downloaded files are saved to: tests/outputs/fefta/
"""

import pytest
from datetime import date
from pathlib import Path

from src.services.fefta import (
    FeftaCrawler,
    FeftaSource,
    FeftaRecord,
)

# Output directory for downloaded files
OUTPUTS_DIR = Path(__file__).parent.parent.parent / "outputs" / "fefta"


class TestFeftaCrawlerSmoke:
    """
    Smoke tests for FEFTA Crawler using live MOF website.

    These tests verify:
    1. The MOF page is accessible and contains FEFTA links
    2. Excel file can be downloaded
    3. Records are correctly parsed with Japanese and English data

    Downloaded files are saved to: tests/outputs/fefta/
    """

    @pytest.fixture
    def crawler(self):
        """Create a FeftaCrawler with persistent output directory."""
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        with FeftaCrawler(output_dir=OUTPUTS_DIR) as c:
            yield c

    @pytest.mark.smoke
    def test_fetch_latest_source_from_mof(self, crawler):
        """
        Smoke test: Verify we can fetch the latest FEFTA source from MOF.

        Expected URL: https://www.mof.go.jp/english/policy/international_policy/fdi/Related_Guidance_and_Documents/index.html

        Assertions:
        - FeftaSource is returned
        - as_of_date is a valid date (not future)
        - file_url points to .xlsx file on mof.go.jp
        """
        source = crawler.fetch_latest_source()

        # Verify source structure
        assert isinstance(source, FeftaSource)
        assert source.as_of_raw.startswith("As of")
        assert isinstance(source.as_of_date, date)
        assert source.as_of_date <= date.today(), "As-of date should not be in the future"
        assert source.download_date == date.today()

        # Verify URL structure
        assert source.file_url.endswith(".xlsx")
        assert "mof.go.jp" in source.file_url
        assert source.saved_path is None  # Not downloaded yet

        print(f"\n✅ FEFTA Source Verification:")
        print(f"   As of: {source.as_of_date}")
        print(f"   Raw: {source.as_of_raw}")
        print(f"   URL: {source.file_url}")

    @pytest.mark.smoke
    def test_download_and_parse_excel(self, crawler):
        """
        Smoke test: Verify we can download and parse FEFTA Excel file.

        Assertions:
        - Excel file is downloaded successfully
        - At least 100 company records are parsed
        - Each record has valid securities_code (numeric string)
        - Each record has valid ISIN (12 chars, starts with JP)
        - Category values are 1-10
        """
        # Fetch source
        source = crawler.fetch_latest_source()

        # Download Excel
        source = crawler.download_excel(source)
        assert source.saved_path is not None

        saved_path = Path(source.saved_path)
        assert saved_path.exists()
        assert saved_path.suffix == ".xlsx"

        file_size = saved_path.stat().st_size
        assert file_size > 10000, f"File too small: {file_size} bytes"

        print(f"\n✅ Excel Download Verification:")
        print(f"   Path: {source.saved_path}")
        print(f"   Size: {file_size:,} bytes")

        # Parse records
        records, df = crawler.parse_records(source.saved_path)

        # Basic count check
        assert len(records) > 100, f"Expected >100 records, got {len(records)}"

        # Verify record structure
        for record in records[:10]:  # Check first 10 records
            assert isinstance(record, FeftaRecord)

            # Securities code: should be numeric, 4-5 digits
            assert record.securities_code.isdigit(), (
                f"Invalid securities_code: {record.securities_code}"
            )
            assert 4 <= len(record.securities_code) <= 5

            # ISIN: should be 12 chars, start with JP
            assert len(record.isin_code) == 12, f"Invalid ISIN length: {record.isin_code}"
            assert record.isin_code.startswith("JP"), (
                f"ISIN should start with JP: {record.isin_code}"
            )

            # Category: should be 1-10
            assert 1 <= record.category <= 10, f"Invalid category: {record.category}"

            # Company names should not be empty
            assert record.company_name_ja, "Japanese company name is empty"
            assert record.issue_or_company_name, "English company name is empty"

        print(f"\n✅ Record Parsing Verification:")
        print(f"   Total records: {len(records)}")
        print(f"   Sample records:")
        for r in records[:5]:
            print(
                f"     {r.securities_code} | {r.isin_code} | {r.company_name_ja[:20]}... | cat={r.category}"
            )

    @pytest.mark.smoke
    def test_full_crawl_workflow(self):
        """
        Smoke test: Complete end-to-end FEFTA crawl workflow.

        This is the main integration test that verifies the full workflow:
        fetch source -> download -> parse -> return records

        Downloaded files are saved to: tests/outputs/fefta/
        """
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        with FeftaCrawler(output_dir=OUTPUTS_DIR) as crawler:
            source, records = crawler.run()

            # Source verification
            assert isinstance(source, FeftaSource)
            assert source.saved_path is not None
            assert Path(source.saved_path).exists()

            # Records verification
            assert len(records) > 100

            # Category distribution check
            categories = {}
            for r in records:
                categories[r.category] = categories.get(r.category, 0) + 1

            print(f"\n✅ Full Crawl Workflow Verification:")
            print(f"   Total companies: {len(records)}")
            print(f"   As of: {source.as_of_date}")
            print(f"   Category distribution:")
            for cat in sorted(categories.keys()):
                print(f"     Category {cat}: {categories[cat]} companies")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
