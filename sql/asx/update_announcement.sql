UPDATE asx_announcements
SET is_price_sensitive = :is_price_sensitive,
    headline = :headline,
    number_of_pages = :number_of_pages,
    file_size = :file_size,
    pdf_url = :pdf_url,
    downloaded_file_path = :downloaded_file_path
WHERE id = :id;
