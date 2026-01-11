INSERT INTO asx_announcements (ticker, announcement_date, announcement_time, is_price_sensitive, headline, number_of_pages, file_size, pdf_url, downloaded_file_path)
VALUES (:ticker, :announcement_date, :announcement_time, :is_price_sensitive, :headline, :number_of_pages, :file_size, :pdf_url, :downloaded_file_path)
ON CONFLICT (ticker, announcement_date, announcement_time, headline) DO NOTHING;
