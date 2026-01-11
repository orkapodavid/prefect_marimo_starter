INSERT INTO asx_appendix_5b_reports (ticker, report_date, headline, pdf_link, total_available_funding, estimated_quarters_funding, matched_keywords, extraction_warnings, downloaded_file_path)
VALUES (:ticker, :report_date, :headline, :pdf_link, :total_available_funding, :estimated_quarters_funding, :matched_keywords, :extraction_warnings, :downloaded_file_path)
ON CONFLICT (ticker, report_date, headline) DO NOTHING;
