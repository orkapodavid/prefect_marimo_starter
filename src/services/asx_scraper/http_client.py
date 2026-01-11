"""
HTTP client for ASX scraper with retry logic and terms acceptance handling.
"""

import time
import logging
from typing import Optional
from urllib.parse import urljoin, urlparse, parse_qs
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# Constants
BASE_URL = "https://www.asx.com.au"
ANNOUNCEMENT_BASE_URL = "https://www.asx.com.au/asx/v2/statistics/displayAnnouncement.do"

DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
}


class HttpClient:
    """HTTP client with retry logic and ASX-specific handling."""
    
    def __init__(self, delay: float = 0.5, retries: int = 3, backoff_factor: float = 0.3, timeout: int = 30):
        """
        Initialize HTTP client.
        
        Args:
            delay: Delay between requests in seconds
            retries: Number of retry attempts
            backoff_factor: Exponential backoff multiplier
            timeout: Request timeout in seconds
        """
        self.delay = delay
        self.timeout = timeout
        self.session = self._create_session(retries, backoff_factor)
        self.session.headers.update(DEFAULT_HEADERS)
        self.terms_accepted = False
        self._last_request_time = 0
        
    def _create_session(self, retries: int, backoff_factor: float) -> requests.Session:
        """Create a requests session with retry logic."""
        session = requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=(500, 502, 504),
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session
    
    def _apply_delay(self):
        """Apply rate limiting delay between requests."""
        if self.delay > 0:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.delay:
                time.sleep(self.delay - elapsed)
        self._last_request_time = time.time()
    
    def get(self, url: str, params: Optional[dict] = None, allow_redirects: bool = True) -> requests.Response:
        """
        Perform GET request with rate limiting.
        
        Args:
            url: Target URL
            params: Query parameters
            allow_redirects: Whether to follow redirects
            
        Returns:
            Response object
        """
        self._apply_delay()
        try:
            response = self.session.get(url, params=params, timeout=self.timeout, allow_redirects=allow_redirects)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP GET error for {url}: {e}")
            raise
    
    def post(self, url: str, data: Optional[dict] = None, allow_redirects: bool = True) -> requests.Response:
        """
        Perform POST request with rate limiting.
        
        Args:
            url: Target URL
            data: Form data
            allow_redirects: Whether to follow redirects
            
        Returns:
            Response object
        """
        self._apply_delay()
        try:
            response = self.session.post(url, data=data, timeout=self.timeout, allow_redirects=allow_redirects)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP POST error for {url}: {e}")
            raise
    
    def accept_terms_and_get_pdf_url(self, initial_url: str) -> Optional[str]:
        """
        Navigate through ASX terms agreement page if present.
        
        Args:
            initial_url: Initial URL that may redirect to terms page
            
        Returns:
            Direct PDF URL or None if failed
        """
        try:
            response = self.get(initial_url, allow_redirects=True)
            
            # Check if already got PDF
            if 'announcements.asx.com.au' in response.url and response.url.endswith('.pdf'):
                return response.url
            
            # Check if we got terms agreement page
            if 'Access to this site' in response.text or 'agree' in response.text.lower():
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for hidden pdfURL input
                pdf_url_input = soup.find('input', {'name': 'pdfURL'})
                if pdf_url_input and pdf_url_input.get('value'):
                    return pdf_url_input.get('value')
                
                # Try form submission
                form = soup.find('form')
                if form:
                    action_url = form.get('action', '')
                    action_url = urljoin(initial_url, action_url) if action_url else initial_url
                    
                    form_data = {}
                    for input_tag in form.find_all('input'):
                        name = input_tag.get('name')
                        value = input_tag.get('value', '')
                        input_type = input_tag.get('type', '')
                        if name:
                            if input_type == 'submit' and 'agree' in value.lower():
                                form_data[name] = value
                            elif input_type != 'submit':
                                form_data[name] = value
                    
                    if not form_data:
                        form_data = {'agree': 'true'}
                    
                    response = self.post(action_url, data=form_data, allow_redirects=True)
                    if 'announcements.asx.com.au' in response.url and response.url.endswith('.pdf'):
                        self.terms_accepted = True
                        return response.url
                    if response.headers.get('Content-Type', '').startswith('application/pdf'):
                        return response.url
            
            # Try direct PDF URL construction from idsId parameter
            parsed = urlparse(initial_url)
            params = parse_qs(parsed.query)
            ids_id = params.get('idsId', [None])[0]
            
            if ids_id:
                direct_url = f"{ANNOUNCEMENT_BASE_URL}?display=pdf&idsId={ids_id}"
                response = self.get(direct_url, allow_redirects=True)
                if 'announcements.asx.com.au' in response.url:
                    return response.url
            
            return None
        except Exception as e:
            logger.error(f"Error accepting terms for {initial_url}: {e}")
            return None
    
    def download_file(self, url: str, output_path: str) -> bool:
        """
        Download file from URL to local path.
        
        Args:
            url: File URL
            output_path: Local path to save file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Try to get actual PDF URL if this is a display URL
            actual_url = self.accept_terms_and_get_pdf_url(url)
            if not actual_url:
                logger.warning(f"Could not get actual PDF URL, trying direct download")
                response = self.get(url, allow_redirects=True)
            else:
                response = self.get(actual_url)
            
            # Verify it's a PDF
            content_type = response.headers.get('Content-Type', '')
            if 'pdf' not in content_type.lower() and not response.content[:4] == b'%PDF':
                logger.error(f"Downloaded content is not a PDF: {content_type}")
                return False
            
            # Write to file
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            return True
        except Exception as e:
            logger.error(f"Error downloading file from {url}: {e}")
            return False
