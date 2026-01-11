INSERT INTO asx_pipe_announcements (ticker, company_name, announcement_datetime, title, pdf_link, description, is_price_sensitive, downloaded_file_path)
VALUES (:ticker, :company_name, :announcement_datetime, :title, :pdf_link, :description, :is_price_sensitive, :downloaded_file_path)
ON CONFLICT (ticker, announcement_datetime, title) DO NOTHING;
