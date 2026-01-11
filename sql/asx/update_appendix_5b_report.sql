UPDATE asx_appendix_5b_reports
SET total_available_funding = :total_available_funding,
    estimated_quarters_funding = :estimated_quarters_funding,
    matched_keywords = :matched_keywords,
    extraction_warnings = :extraction_warnings,
    downloaded_file_path = :downloaded_file_path
WHERE id = :id;
