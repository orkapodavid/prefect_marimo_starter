SELECT id, ticker, report_date, headline, pdf_link, total_available_funding, estimated_quarters_funding, matched_keywords, extraction_warnings, downloaded_file_path, created_at
FROM asx_appendix_5b_reports
WHERE id = :id;
