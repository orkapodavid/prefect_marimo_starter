SELECT id, ticker, company_name, announcement_datetime, title, pdf_link, description, is_price_sensitive, downloaded_file_path, created_at
FROM asx_pipe_announcements
WHERE id = :id;
