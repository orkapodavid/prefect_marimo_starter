UPDATE asx_pipe_announcements
SET company_name = :company_name,
    title = :title,
    pdf_link = :pdf_link,
    description = :description,
    is_price_sensitive = :is_price_sensitive,
    downloaded_file_path = :downloaded_file_path
WHERE id = :id;
