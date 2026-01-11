"""
PDF handler for downloading and extracting text from ASX PDFs.
Includes Section 8 data extraction for Appendix 5B reports.
"""

import re
import logging
from pathlib import Path
from typing import Optional
import fitz  # PyMuPDF
import pdfplumber

from .models import Section8Data

logger = logging.getLogger(__name__)


class PdfHandler:
    """Handler for PDF operations."""
    
    def __init__(self, pdf_dir: Path):
        """
        Initialize PDF handler.
        
        Args:
            pdf_dir: Directory to save downloaded PDFs
        """
        self.pdf_dir = Path(pdf_dir)
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract text from PDF using PyMuPDF (primary) and pdfplumber (fallback).
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted text content
        """
        text = ""
        
        # Try PyMuPDF first (faster)
        try:
            doc = fitz.open(pdf_path)
            for page in doc:
                text += page.get_text()
            doc.close()
            if text.strip():
                logger.debug(f"Successfully extracted text using PyMuPDF from {pdf_path}")
                return text
        except Exception as e:
            logger.debug(f"PyMuPDF extraction failed for {pdf_path}: {e}")
        
        # Fallback to pdfplumber
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            if text.strip():
                logger.debug(f"Successfully extracted text using pdfplumber from {pdf_path}")
                return text
        except Exception as e:
            logger.error(f"pdfplumber extraction also failed for {pdf_path}: {e}")
        
        return text
    
    def extract_section8_data(self, text: str) -> Section8Data:
        """
        Extract Section 8 data from text content.
        
        Args:
            text: Extracted PDF text
            
        Returns:
            Section8Data model with extracted values
        """
        data = Section8Data(section_8_found=False)
        
        # Look for Section 8 header
        section8_patterns = [
            r'8\.?\s*\n?\s*Estimated\s+cash\s+available\s+for\s+future\s+operating\s+activities',
            r'Estimated\s+cash\s+available\s+for\s+future\s+operating',
        ]
        
        section8_match = None
        for pattern in section8_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                section8_match = match
                break
        
        if not section8_match:
            return data
        
        data.section_8_found = True
        start_pos = section8_match.start()
        end_pos = min(start_pos + 3000, len(text))
        section_text = text[start_pos:end_pos]
        data.raw_section_8_text = section_text[:1000]  # Store first 1000 chars
        
        # Extract item 8.6 (total available funding)
        patterns_8_6 = [
            r'8\.6\s*\n\s*Total\s+available\s+funding[^\n]*\n\s*(\-?\d[\d,\.]*)',
            r'8\.6\s*\n[^\n]+\n\s*(\-?\d[\d,\.]*)',
            r'8\.6\s+Total\s+available\s+funding[^\d]*(\-?\d[\d,\.]*)',
            r'8\.6[^\d]*?(\-?\d[\d,\.]+)(?:\s|$)',
        ]
        
        for pattern in patterns_8_6:
            match = re.search(pattern, section_text, re.IGNORECASE)
            if match:
                value = match.group(1).strip().replace(',', '')
                try:
                    data.item_8_6_total_available_funding = float(value)
                    logger.debug(f"Extracted 8.6 value: {data.item_8_6_total_available_funding}")
                    break
                except ValueError:
                    continue
        
        # Extract item 8.7 (estimated quarters)
        patterns_8_7 = [
            r'8\.7\s*\n\s*Estimated\s+quarters[^\n]*\n[^\n]*\n\s*(\d+\.?\d*|N/?A)',
            r'8\.7\s*\n[^\n]+\n[^\n]+\n\s*(\d+\.?\d*|N/?A)',
            r'8\.7\s*\n[^\n]+\n\s*(\d+\.?\d*|N/?A)',
            r'8\.7\s+Estimated\s+quarters[^\d]*?(\d+\.?\d*|N/?A)',
            r'8\.7[^\d]*?(\d+\.?\d*|N/?A)',
        ]
        
        for pattern in patterns_8_7:
            match = re.search(pattern, section_text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if value.upper() in ['N/A', 'NA']:
                    data.item_8_7_estimated_quarters = 'N/A'
                    logger.debug(f"Extracted 8.7 value: N/A")
                    break
                try:
                    data.item_8_7_estimated_quarters = float(value)
                    logger.debug(f"Extracted 8.7 value: {data.item_8_7_estimated_quarters}")
                    break
                except ValueError:
                    continue
        
        return data
    
    def extract_section8_with_tables(self, pdf_path: str) -> Section8Data:
        """
        Extract Section 8 data using table parsing (fallback method).
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Section8Data model with extracted values
        """
        data = Section8Data(section_8_found=False)
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        if not table:
                            continue
                        
                        table_text = str(table).lower()
                        if 'estimated cash available' in table_text or '8.6' in table_text or '8.7' in table_text:
                            data.section_8_found = True
                            
                            for row in table:
                                if not row:
                                    continue
                                row_text = ' '.join([str(cell) if cell else '' for cell in row]).lower()
                                
                                # Look for 8.6
                                if '8.6' in row_text or 'total available funding' in row_text:
                                    for cell in row:
                                        if cell:
                                            cell_str = str(cell).strip()
                                            num_match = re.search(r'(\(?\-?\d[\d,\.]*\)?)', cell_str)
                                            if num_match and data.item_8_6_total_available_funding is None:
                                                value = num_match.group(1).replace(',', '')
                                                if value.startswith('(') and value.endswith(')'):
                                                    value = '-' + value[1:-1]
                                                try:
                                                    data.item_8_6_total_available_funding = float(value)
                                                    logger.debug(f"Extracted 8.6 from table: {data.item_8_6_total_available_funding}")
                                                except ValueError:
                                                    pass
                                
                                # Look for 8.7
                                if '8.7' in row_text or 'estimated quarters' in row_text:
                                    for cell in row:
                                        if cell:
                                            cell_str = str(cell).strip().upper()
                                            if cell_str in ['N/A', 'NA']:
                                                data.item_8_7_estimated_quarters = 'N/A'
                                                logger.debug(f"Extracted 8.7 from table: N/A")
                                            else:
                                                num_match = re.search(r'(\d+\.?\d*)', cell_str)
                                                if num_match and data.item_8_7_estimated_quarters is None:
                                                    try:
                                                        data.item_8_7_estimated_quarters = float(num_match.group(1))
                                                        logger.debug(f"Extracted 8.7 from table: {data.item_8_7_estimated_quarters}")
                                                    except ValueError:
                                                        pass
        except Exception as e:
            logger.error(f"Error extracting Section 8 with tables from {pdf_path}: {e}")
        
        return data
    
    def extract_section8_combined(self, pdf_path: str) -> Section8Data:
        """
        Extract Section 8 data using both text and table methods.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Section8Data model with best extracted values
        """
        # Try text extraction first
        text = self.extract_text_from_pdf(pdf_path)
        data = self.extract_section8_data(text)
        
        # If incomplete, try table extraction
        if not data.section_8_found or \
           data.item_8_6_total_available_funding is None or \
           data.item_8_7_estimated_quarters is None:
            table_data = self.extract_section8_with_tables(pdf_path)
            
            # Merge results (table data takes precedence if text extraction failed)
            if table_data.section_8_found:
                data.section_8_found = True
            if table_data.item_8_6_total_available_funding is not None:
                data.item_8_6_total_available_funding = table_data.item_8_6_total_available_funding
            if table_data.item_8_7_estimated_quarters is not None:
                data.item_8_7_estimated_quarters = table_data.item_8_7_estimated_quarters
        
        return data
