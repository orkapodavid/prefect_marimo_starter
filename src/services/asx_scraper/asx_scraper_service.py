"""
ASX Scraper Service - Main orchestrator for scraping ASX announcements.
Combines PIPE, general announcements, and Appendix 5B functionality.
"""

import os
import re
import logging
import random
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import pandas as pd
import json

from .http_client import HttpClient
from .html_parser import HtmlParser
from .pdf_handler import PdfHandler
from .filters import AnnouncementFilters
from .models import Company, Announcement, ScrapeResult, ScrapeSummary, Section8Data

logger = logging.getLogger(__name__)


# Constants
COMPANIES_CSV_URL = "https://www.asx.com.au/asx/research/ASXListedCompanies.csv"
TODAY_ANNOUNCEMENTS_URL = "https://www.asx.com.au/asx/v2/statistics/todayAnns.do"
SEARCH_URL = "https://www.asx.com.au/asx/v2/statistics/announcements.do"

PERIOD_MAPPINGS = {
    "today": "T",
    "previous": "P",
    "week": "W",
    "month": "M3",
    "3months": "M3",
    "6months": "M6",
    "all": "A"
}


class AsxScraperService:
    """Main service for scraping ASX announcements."""
    
    def __init__(self, output_dir: str = "outputs", delay: float = 0.5, database_service=None):
        """
        Initialize ASX scraper service.
        
        Args:
            output_dir: Base directory for outputs
            delay: Delay between requests in seconds
            database_service: Optional database service for persistence
        """
        self.output_dir = Path(output_dir)
        self.delay = delay
        self.database_service = database_service
        
        # Create output directories
        self.pdf_dir = self.output_dir / "pdfs"
        self.json_dir = self.output_dir / "json"
        self.csv_dir = self.output_dir / "csv"
        
        for dir_path in [self.pdf_dir, self.json_dir, self.csv_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.http_client = HttpClient(delay=delay)
        self.html_parser = HtmlParser()
        self.pdf_handler = PdfHandler(pdf_dir=self.pdf_dir)
        self.filters = AnnouncementFilters()
        
        logger.info(f"Initialized AsxScraperService with output_dir={output_dir}, database={'enabled' if database_service else 'disabled'}")
    
    # ========================================================================
    # Company Operations
    # ========================================================================
    
    def get_listed_companies(self) -> List[Company]:
        """
        Fetch list of all ASX listed companies.
        
        Returns:
            List of Company models
        """
        logger.info("Fetching ASX listed companies...")
        try:
            response = self.http_client.get(COMPANIES_CSV_URL)
            companies = self.html_parser.parse_company_list_csv(response.text)
            logger.info(f"Retrieved {len(companies)} listed companies")
            return companies
        except Exception as e:
            logger.error(f"Error fetching company list: {e}")
            return []
    
    # ========================================================================
    # Announcement Operations
    # ========================================================================
    
    def get_announcements_for_ticker(self, ticker: str, period: str = "M6") -> List[Announcement]:
        """
        Get announcements for a specific ticker.
        
        Args:
            ticker: ASX ticker code
            period: Time period (T, W, M3, M6, A)
            
        Returns:
            List of Announcement models
        """
        logger.info(f"Fetching announcements for {ticker} (period={period})")
        
        params = {
            "by": "asxCode",
            "timeframe": "D",
            "period": period,
            "asxCode": ticker.upper()
        }
        
        try:
            response = self.http_client.get(SEARCH_URL, params=params)
            announcements = self.html_parser.parse_ticker_announcements(response.text, ticker)
            logger.info(f"Found {len(announcements)} announcements for {ticker}")
            return announcements
        except Exception as e:
            logger.error(f"Error fetching announcements for {ticker}: {e}")
            return []
    
    def get_today_announcements(self) -> List[Announcement]:
        """
        Get all announcements from today.
        
        Returns:
            List of Announcement models
        """
        logger.info("Fetching today's announcements...")
        try:
            response = self.http_client.get(TODAY_ANNOUNCEMENTS_URL)
            announcements = self.html_parser.parse_today_announcements(response.text)
            logger.info(f"Found {len(announcements)} announcements today")
            return announcements
        except Exception as e:
            logger.error(f"Error fetching today's announcements: {e}")
            return []
    
    # ========================================================================
    # PDF Operations
    # ========================================================================
    
    def download_pdf(self, url: str, ticker: str, headline: str) -> Optional[Path]:
        """
        Download PDF from URL.
        
        Args:
            url: PDF URL
            ticker: Company ticker
            headline: Announcement headline (for filename)
            
        Returns:
            Path to downloaded PDF or None if failed
        """
        filename = self.filters.sanitize_filename(f"{ticker}_{headline}.pdf")
        output_path = self.pdf_dir / filename
        
        logger.info(f"Downloading PDF: {filename}")
        success = self.http_client.download_file(url, str(output_path))
        
        if success:
            return output_path
        return None
    
    # ========================================================================
    # High-Level Workflows
    # ========================================================================
    
    def scrape_target_announcements(
        self,
        tickers: List[str],
        period: str = "M6",
        download_pdfs: bool = False,
        save_to_db: bool = False
    ) -> pd.DataFrame:
        """
        Scrape announcements for specific tickers.
        
        Args:
            tickers: List of ticker codes
            period: Time period (today, week, month, 3months, 6months, all)
            download_pdfs: Whether to download PDF files
            save_to_db: Whether to save to database
            
        Returns:
            DataFrame with announcement data
        """
        logger.info(f"Starting target scrape for tickers: {tickers}, period={period}")
        
        period_code = PERIOD_MAPPINGS.get(period.lower(), "M6")
        all_announcements = []
        
        for ticker in tickers:
            announcements = self.get_announcements_for_ticker(ticker, period_code)
            
            for ann in announcements:
                ann_dict = ann.model_dump()
                
                # Download PDF if requested
                if download_pdfs:
                    pdf_path = self.download_pdf(ann.pdf_url, ann.ticker, ann.headline)
                    ann_dict['downloaded_file_path'] = str(pdf_path) if pdf_path else None
                else:
                    ann_dict['downloaded_file_path'] = None
                
                # Save to database if requested and available
                if save_to_db and self.database_service:
                    self._save_announcement_to_db(ann_dict, 'announcement')
                
                all_announcements.append(ann_dict)
        
        df = pd.DataFrame(all_announcements)
        logger.info(f"Scraped {len(df)} total announcements from {len(tickers)} tickers")
        
        return df
    
    def scrape_pipe_announcements(
        self,
        period: str = "M6",
        download_pdfs: bool = False,
        save_to_db: bool = False,
        sample_size: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Scan all ASX companies for PIPE/placement announcements.
        
        Args:
            period: Time period to scan
            download_pdfs: Whether to download PDFs
            save_to_db: Whether to save to database
            sample_size: If provided, only scan this many companies (for testing)
            
        Returns:
            DataFrame with PIPE announcements
        """
        logger.info(f"Starting PIPE scan (period={period}, sample_size={sample_size})")
        
        # Get company list
        companies = self.get_listed_companies()
        if not companies:
            logger.error("No companies found, aborting scan")
            return pd.DataFrame()
        
        # Sample if requested
        if sample_size and sample_size < len(companies):
            random.seed(42)
            companies = random.sample(companies, sample_size)
            logger.info(f"Sample mode: scanning {len(companies)} companies")
        
        period_code = PERIOD_MAPPINGS.get(period.lower(), "M6")
        pipe_announcements = []
        total = len(companies)
        
        for idx, company in enumerate(companies):
            if idx % 10 == 0:
                logger.info(f"Progress: {idx}/{total} ({idx/total*100:.1f}%)")
            
            announcements = self.get_announcements_for_ticker(company.ticker, period_code)
            
            for ann in announcements:
                # Check if matches PIPE keywords
                if self.filters.is_pipe_announcement(ann.headline):
                    matched_keywords = self.filters.get_matched_pipe_keywords(ann.headline)
                    
                    ann_dict = ann.model_dump()
                    ann_dict['company_name'] = company.company_name
                    ann_dict['matched_keywords'] = matched_keywords
                    
                    logger.info(f"FOUND PIPE: {company.ticker} - {ann.headline}")
                    
                    # Download PDF if requested
                    if download_pdfs:
                        pdf_path = self.download_pdf(ann.pdf_url, ann.ticker, ann.headline)
                        ann_dict['downloaded_file_path'] = str(pdf_path) if pdf_path else None
                    else:
                        ann_dict['downloaded_file_path'] = None
                    
                    # Save to database if requested
                    if save_to_db and self.database_service:
                        self._save_announcement_to_db(ann_dict, 'pipe')
                    
                    pipe_announcements.append(ann_dict)
        
        df = pd.DataFrame(pipe_announcements)
        logger.info(f"Found {len(df)} PIPE announcements from {total} companies")
        
        return df
    
    def scrape_appendix5b_reports(
        self,
        download_pdfs: bool = True,
        save_to_db: bool = False
    ) -> ScrapeSummary:
        """
        Scrape today's Appendix 5B and cash flow reports.
        
        Args:
            download_pdfs: Whether to download PDFs (required for extraction)
            save_to_db: Whether to save to database
            
        Returns:
            ScrapeSummary with extraction results
        """
        logger.info("Starting Appendix 5B scrape")
        
        # Get today's announcements
        announcements = self.get_today_announcements()
        
        # Filter for Appendix 5B keywords
        matching_announcements = []
        for ann in announcements:
            if self.filters.is_appendix5b_announcement(ann.headline):
                matched_keywords = self.filters.get_matched_appendix5b_keywords(ann.headline)
                ann_dict = ann.model_dump()
                ann_dict['matched_keywords'] = matched_keywords
                matching_announcements.append(ann_dict)
        
        logger.info(f"Found {len(matching_announcements)} Appendix 5B announcements")
        
        # Process each announcement
        results = []
        warnings_count = 0
        
        for ann_dict in matching_announcements:
            result = self._process_appendix5b_announcement(ann_dict, download_pdfs)
            results.append(result)
            
            if result.warning:
                warnings_count += 1
            
            # Save to database if requested
            if save_to_db and self.database_service:
                self._save_appendix5b_to_db(result)
            
            # Save individual JSON
            self._save_result_json(result)
        
        # Create summary
        summary = ScrapeSummary(
            scrape_datetime=datetime.now().isoformat(),
            total_announcements_found=len(results),
            successful_extractions=sum(1 for r in results if r.extraction_success),
            warnings_count=warnings_count,
            results=results
        )
        
        logger.info(f"Appendix 5B scrape complete: {summary.successful_extractions}/{summary.total_announcements_found} successful extractions")
        
        return summary
    
    # ========================================================================
    # Private Helper Methods
    # ========================================================================
    
    def _process_appendix5b_announcement(self, ann_dict: dict, download_pdf: bool) -> ScrapeResult:
        """Process a single Appendix 5B announcement."""
        # Parse date
        date_match = re.search(r'(\d{2})/(\d{2})/(\d{4})', ann_dict['datetime'])
        if date_match:
            day, month, year = date_match.groups()
            date_formatted = f"{year}_{month}_{day}"
        else:
            date_formatted = datetime.now().strftime('%Y_%m_%d')
        
        result = ScrapeResult(
            date=date_formatted,
            stock_code=ann_dict['ticker'],
            headline=ann_dict['headline'],
            pdf_link=ann_dict['pdf_url'],
            matched_keywords=ann_dict.get('matched_keywords', [])
        )
        
        if not download_pdf:
            result.warning = 'PDF download skipped'
            return result
        
        # Download PDF
        pdf_path = self.download_pdf(ann_dict['pdf_url'], ann_dict['ticker'], ann_dict['headline'])
        if not pdf_path:
            result.warning = 'Failed to download PDF'
            return result
        
        result.pdf_downloaded = True
        result.pdf_filename = pdf_path.name
        
        # Extract Section 8 data
        section8_data = self.pdf_handler.extract_section8_combined(str(pdf_path))
        result.section_8_data = section8_data
        
        if section8_data.section_8_found:
            result.extraction_success = True
            if section8_data.item_8_6_total_available_funding is None or \
               section8_data.item_8_7_estimated_quarters is None:
                result.warning = 'Section 8 found but some values could not be extracted'
        else:
            result.warning = 'Section 8 not found in PDF'
        
        return result
    
    def _save_result_json(self, result: ScrapeResult) -> Path:
        """Save individual result to JSON."""
        filename = f"{result.date}-{result.stock_code}.json"
        filepath = self.json_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(result.model_dump_json(indent=2))
        
        return filepath
    
    def _save_announcement_to_db(self, ann_dict: dict, table_type: str):
        """Save announcement to database."""
        if not self.database_service:
            return
        
        try:
            if table_type == 'announcement':
                params = self._prepare_announcement_params(ann_dict)
                sql_file = Path(__file__).parent.parent.parent / "asx" / "sql" / "create_announcement.sql"
            elif table_type == 'pipe':
                params = self._prepare_pipe_params(ann_dict)
                sql_file = Path(__file__).parent.parent.parent / "asx" / "sql" / "create_pipe_announcement.sql"
            else:
                logger.error(f"Unknown table type: {table_type}")
                return
            
            if not sql_file.exists():
                logger.error(f"SQL file not found: {sql_file}")
                return
            
            self.database_service.execute_query_from_file(str(sql_file), params=params)
            logger.debug(f"Saved {table_type} announcement to database: {ann_dict.get('ticker')}")
        except Exception as e:
            logger.warning(f"Failed to save {table_type} to database: {e}")
    
    def _save_appendix5b_to_db(self, result: ScrapeResult):
        """Save Appendix 5B result to database."""
        if not self.database_service:
            return
        
        try:
            params = self._prepare_appendix5b_params(result)
            sql_file = Path(__file__).parent.parent.parent / "asx" / "sql" / "create_appendix_5b_report.sql"
            
            if not sql_file.exists():
                logger.error(f"SQL file not found: {sql_file}")
                return
            
            self.database_service.execute_query_from_file(str(sql_file), params=params)
            logger.debug(f"Saved Appendix 5B report to database: {result.stock_code}")
        except Exception as e:
            logger.warning(f"Failed to save Appendix 5B to database: {e}")
    
    def _prepare_announcement_params(self, ann_dict: dict) -> dict:
        """Prepare parameters for announcement SQL insert."""
        date_str, time_str = self.filters.parse_datetime_to_parts(ann_dict.get('datetime', ''))
        
        return {
            'ticker': ann_dict.get('ticker'),
            'announcement_date': date_str,
            'announcement_time': time_str,
            'is_price_sensitive': ann_dict.get('price_sensitive', False),
            'headline': ann_dict.get('headline'),
            'number_of_pages': ann_dict.get('number_of_pages'),
            'file_size': ann_dict.get('file_size'),
            'pdf_url': ann_dict.get('pdf_url'),
            'downloaded_file_path': ann_dict.get('downloaded_file_path')
        }
    
    def _prepare_pipe_params(self, ann_dict: dict) -> dict:
        """Prepare parameters for PIPE announcement SQL insert."""
        # Convert datetime to timestamp format
        datetime_str = ann_dict.get('datetime', '')
        date_str, time_str = self.filters.parse_datetime_to_parts(datetime_str)
        
        # Combine date and time for timestamp
        if date_str and time_str:
            announcement_datetime = f"{date_str} {time_str}"
        else:
            announcement_datetime = None
        
        # Convert matched_keywords list to comma-separated string
        matched_keywords = ann_dict.get('matched_keywords', [])
        description = ', '.join(matched_keywords) if matched_keywords else None
        
        return {
            'ticker': ann_dict.get('ticker'),
            'company_name': ann_dict.get('company_name'),
            'announcement_datetime': announcement_datetime,
            'title': ann_dict.get('headline'),
            'pdf_link': ann_dict.get('pdf_url'),
            'description': description,
            'is_price_sensitive': ann_dict.get('price_sensitive', False),
            'downloaded_file_path': ann_dict.get('downloaded_file_path')
        }
    
    def _prepare_appendix5b_params(self, result: ScrapeResult) -> dict:
        """Prepare parameters for Appendix 5B SQL insert."""
        # Convert date format from YYYY_MM_DD to YYYY-MM-DD
        date_parts = result.date.split('_')
        if len(date_parts) == 3:
            report_date = f"{date_parts[0]}-{date_parts[1]}-{date_parts[2]}"
        else:
            report_date = None
        
        # Convert matched_keywords list to JSON string
        import json
        matched_keywords_str = json.dumps(result.matched_keywords) if result.matched_keywords else None
        
        # Get Section 8 values
        total_funding = result.section_8_data.item_8_6_total_available_funding
        estimated_quarters = result.section_8_data.item_8_7_estimated_quarters
        
        # Convert estimated_quarters to proper type
        if isinstance(estimated_quarters, str):
            estimated_quarters_value = None  # Store N/A as NULL or handle separately
        else:
            estimated_quarters_value = estimated_quarters
        
        return {
            'ticker': result.stock_code,
            'report_date': report_date,
            'headline': result.headline,
            'pdf_link': result.pdf_link,
            'total_available_funding': total_funding,
            'estimated_quarters_funding': estimated_quarters_value,
            'matched_keywords': matched_keywords_str,
            'extraction_warnings': result.warning,
            'downloaded_file_path': str(self.pdf_dir / result.pdf_filename) if result.pdf_filename else None
        }
