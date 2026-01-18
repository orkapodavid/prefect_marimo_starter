/*
description: Get TDnet announcements within a date range
note: |
  Returns announcements where publish_date is within the specified range (inclusive).
  Optionally filter by language if provided (pass NULL for all).
version: 1.0.0
*/

/*__PARAMETERS__*/
-- DECLARE @date_from DATE = '2026-01-01';
-- DECLARE @date_to DATE = '2026-01-31';
-- DECLARE @language VARCHAR(20) = NULL; -- 'english', 'japanese', or NULL

SELECT
    id,
    publish_datetime,
    publish_date,
    stock_code,
    company_name,
    title,
    pdf_url,
    has_xbrl,
    notes,
    language,
    sector,
    listed_exchange,
    xbrl_url,
    created_time,
    updated_time
FROM [dealSourcing].[tblTdnetAnnouncement] WITH (NOLOCK)
WHERE publish_date >= @date_from
  AND publish_date <= @date_to
  AND (@language IS NULL OR language = @language)
ORDER BY publish_datetime DESC;
