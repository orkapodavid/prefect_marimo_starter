/*
description: Get documents within a date range
note: |
  Retrieves all documents where publish_date is within the specified range (inclusive).
  Parameters: @start_date DATE, @end_date DATE
version: 1.0.0
*/

/*__PARAMETERS__*/
-- Example parameters for manual execution (uncomment to run in SSMS):
-- DECLARE @start_date DATE = '2026-01-01';
-- DECLARE @end_date DATE = '2026-01-31';

SELECT
    id,
    doc_id,
    stock_code,
    company_name,
    title,
    description,
    publish_datetime,
    publish_date,
    pdf_url,
    tier,
    pdf_downloaded,
    processed_at,
    created_time,
    created_by,
    updated_time,
    updated_by
FROM [dealSourcing].[tblSearchDocuments] WITH (NOLOCK)
WHERE publish_date BETWEEN @start_date AND @end_date
ORDER BY publish_datetime DESC;
