from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
import logging

from exchangelib import Account, Configuration, Credentials, Message, FileAttachment, DELEGATE

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExchangeEmailService:
    def __init__(self, username: str, password: str, ews_url: str):
        """
        Initialize the Exchange service with credentials and EWS URL.
        """
        self.username = username
        self.password = password
        self.ews_url = ews_url
        
        # Configure credentials and server
        self.credentials = Credentials(username=self.username, password=self.password)
        self.config = Configuration(server=None, credentials=self.credentials)
        self.config.service_endpoint = self.ews_url # Manually set EWS URL to avoid autodiscover
        
        try:
            self.account = Account(
                primary_smtp_address=self.username,
                config=self.config,
                autodiscover=False,
                access_type=DELEGATE
            )
            logger.info(f"Successfully connected to Exchange as {self.username}")
        except Exception as e:
            logger.error(f"Failed to connect to Exchange: {e}")
            raise

    def get_emails(
        self, 
        start_time: datetime, 
        subject_filter: Optional[str] = None, 
        sender_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch emails from the Inbox based on start_time and optional filters.
        """
        logger.info(f"Fetching emails from {start_time}")
        
        # Base query: emails received after start_time
        qs = self.account.inbox.filter(datetime_received__gt=start_time)
        
        if subject_filter:
            qs = qs.filter(subject__icontains=subject_filter)
            
        if sender_filter:
            # Note: Filtering by sender might require specific field access depending on Exchange version
            # Using 'sender__icontains' usually works for name/email
            qs = qs.filter(sender__icontains=sender_filter)
            
        # Order by newest first
        qs = qs.order_by('-datetime_received')
        
        results = []
        for item in qs:
            email_data = {
                'subject': item.subject,
                'sender': str(item.sender),
                'datetime_received': item.datetime_received,
                'body_text': item.text_body,
                'attachments': []
            }
            
            for attachment in item.attachments:
                if isinstance(attachment, FileAttachment):
                    email_data['attachments'].append({
                        'filename': attachment.name,
                        'content_bytes': attachment.content
                    })
            
            results.append(email_data)
            
        logger.info(f"Found {len(results)} emails")
        return results

    def send_email(
        self, 
        to_recipients: List[str], 
        subject: str, 
        body: str, 
        cc_recipients: Optional[List[str]] = None,
        attachments: Optional[List[Any]] = None
    ):
        """
        Send an email with optional attachments.
        attachments can be a list of file paths (str) or tuples (filename, content_bytes).
        """
        if cc_recipients is None:
            cc_recipients = []
            
        m = Message(
            account=self.account,
            subject=subject,
            body=body,
            to_recipients=to_recipients,
            cc_recipients=cc_recipients
        )
        
        if attachments:
            for att in attachments:
                if isinstance(att, str):
                    # It's a file path
                    with open(att, 'rb') as f:
                        file_content = f.read()
                    filename = att.split('/')[-1]
                    file_att = FileAttachment(name=filename, content=file_content)
                    m.attach(file_att)
                elif isinstance(att, tuple) and len(att) == 2:
                    # It's (filename, content_bytes)
                    filename, content = att
                    file_att = FileAttachment(name=filename, content=content)
                    m.attach(file_att)
                    
        m.send()
        logger.info(f"Email sent to {to_recipients}")
