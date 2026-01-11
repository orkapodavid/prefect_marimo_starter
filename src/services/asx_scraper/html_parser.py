"""
HTML parser for ASX announcement pages and company lists.
"""

import re
import logging
import csv
from io import StringIO
from typing import List
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from .models import Company, Announcement

logger = logging.getLogger(__name__)


# Constants
BASE_URL = "https://www.asx.com.au"


class HtmlParser:
    """Parser for ASX HTML content."""
    
    @staticmethod
    def parse_company_list_csv(csv_content: str) -> List[Company]:
        """
        Parse ASX company list from CSV content.
        
        Args:
            csv_content: CSV content as string
            
        Returns:
            List of Company models
        """
        companies = []
        
        try:
            # Skip first 3 header rows
            lines = csv_content.split('\n')
            data_lines = '\n'.join(lines[3:])
            
            reader = csv.reader(StringIO(data_lines))
            
            for row in reader:
                if len(row) >= 2:
                    name = row[0].strip()
                    ticker = row[1].strip()
                    if ticker and len(ticker) >= 2:
                        companies.append(Company(
                            company_name=name,
                            ticker=ticker
                        ))
            
            logger.info(f"Parsed {len(companies)} companies from CSV")
            return companies
        except Exception as e:
            logger.error(f"Error parsing company list CSV: {e}")
            return []
    
    @staticmethod
    def parse_today_announcements(html_content: str) -> List[Announcement]:
        """
        Parse today's announcements from ASX HTML page.
        
        Args:
            html_content: HTML content as string
            
        Returns:
            List of Announcement models
        """
        announcements = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            rows = soup.find_all('tr')
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 4:
                    code = cells[0].get_text(strip=True)
                    date_text = cells[1].get_text(strip=True)
                    price_sens = cells[2].get_text(strip=True)
                    headline_cell = cells[3]
                    
                    link = headline_cell.find('a')
                    if link:
                        headline_raw = link.get_text(strip=True)
                        # Clean headline
                        headline = re.sub(r'\d+\s*pages?.*$', '', headline_raw, flags=re.IGNORECASE).strip()
                        headline = re.sub(r'\d+(\.\d+)?\s*[KMG]B$', '', headline, flags=re.IGNORECASE).strip()
                        headline = re.sub(r'\s+', ' ', headline).strip()
                        
                        pdf_href = link.get('href', '')
                        pdf_url = urljoin(BASE_URL, pdf_href) if pdf_href else ''
                        
                        # Parse date
                        date_match = re.search(r'(\d{2}/\d{2}/\d{4})', date_text)
                        time_match = re.search(r'(\d{1,2}:\d{2}\s*(?:am|pm|AM|PM))', date_text)
                        
                        if date_match:
                            date_str = date_match.group(1)
                            time_str = time_match.group(1) if time_match else ''
                            datetime_str = f"{date_str} {time_str}".strip()
                        else:
                            datetime_str = date_text
                        
                        announcements.append(Announcement(
                            ticker=code,
                            datetime=datetime_str,
                            headline=headline,
                            pdf_url=pdf_url,
                            price_sensitive=bool(price_sens.strip())
                        ))
            
            logger.info(f"Parsed {len(announcements)} announcements from today's page")
            return announcements
        except Exception as e:
            logger.error(f"Error parsing today's announcements: {e}")
            return []
    
    @staticmethod
    def parse_ticker_announcements(html_content: str, ticker: str) -> List[Announcement]:
        """
        Parse announcements for a specific ticker from ASX search results.
        
        Args:
            html_content: HTML content as string
            ticker: Ticker code for validation
            
        Returns:
            List of Announcement models
        """
        announcements = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for announcement table
            table = soup.find("table", summary="Most recent company announcements")
            if not table or not table.find("tbody"):
                logger.debug(f"No announcements table found for {ticker}")
                return []
            
            rows = table.find("tbody").find_all("tr")
            
            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 3:
                    continue
                
                # Date/Time
                date_time_str = cols[0].get_text(strip=True)
                # Price Sensitive
                price_sensitive = bool(cols[1].find("img"))
                
                # Headline / Link
                headline_link = cols[2].find("a")
                if not headline_link:
                    continue
                
                headline = headline_link.get_text(strip=True)
                headline = re.sub(r'\s+', ' ', headline).strip()
                headline = re.sub(r'\d+\s*pages?.*$', '', headline, flags=re.IGNORECASE).strip()
                headline = re.sub(r'\d+(\.\d+)?\s*[KMG]B$', '', headline, flags=re.IGNORECASE).strip()
                
                pdf_url = urljoin(BASE_URL, headline_link["href"]) if headline_link.get("href") else ""
                
                announcements.append(Announcement(
                    ticker=ticker.upper(),
                    datetime=date_time_str,
                    price_sensitive=price_sensitive,
                    headline=headline,
                    pdf_url=pdf_url
                ))
            
            logger.info(f"Parsed {len(announcements)} announcements for ticker {ticker}")
            return announcements
        except Exception as e:
            logger.error(f"Error parsing announcements for {ticker}: {e}")
            return []
