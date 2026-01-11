SELECT id, ticker, announcement_date, announcement_time, is_price_sensitive, headline, number_of_pages, file_size, pdf_url, downloaded_file_path, created_at
FROM asx_announcements
WHERE id = :id;
