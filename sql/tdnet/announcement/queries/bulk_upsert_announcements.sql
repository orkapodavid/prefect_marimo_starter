/*
description: Bulk upsert TDnet announcements from JSON
note: |
  Accepts a JSON array of announcement objects and upserts them.
  Matches on (stock_code, publish_datetime, title, language).
  
  JSON format per row:
  {
    "publish_datetime": "ISO8601",
    "publish_date": "YYYY-MM-DD",
    "stock_code": "...",
    "company_name": "...",
    "title": "...",
    "pdf_url": "...",
    "has_xbrl": bool,
    "notes": "...",
    "language": "...",
    "sector": "...",
    "listed_exchange": "...",
    "xbrl_url": "..."
  }
version: 1.0.0
*/

/*__PARAMETERS__*/
-- DECLARE @json_data NVARCHAR(MAX) = '[{"stock_code": "40620", "company_name": "TEST", "title": "TEST", "publish_datetime": "2026-01-15T16:30:00", "publish_date": "2026-01-15", "language": "english"}]';
-- DECLARE @created_by VARCHAR(20) = 'system';

MERGE [dealSourcing].[tblTdnetAnnouncement] AS target
USING (
    SELECT *
    FROM OPENJSON(@json_data)
    WITH (
        publish_datetime DATETIME2 '$.publish_datetime',
        publish_date DATE '$.publish_date',
        stock_code VARCHAR(10) '$.stock_code',
        company_name NVARCHAR(255) '$.company_name',
        title NVARCHAR(500) '$.title',
        pdf_url NVARCHAR(2048) '$.pdf_url',
        has_xbrl BIT '$.has_xbrl',
        notes NVARCHAR(50) '$.notes',
        language VARCHAR(20) '$.language',
        sector NVARCHAR(100) '$.sector',
        listed_exchange NVARCHAR(50) '$.listed_exchange',
        xbrl_url NVARCHAR(2048) '$.xbrl_url'
    )
) AS source
ON (
    target.stock_code = source.stock_code 
    AND target.publish_datetime = source.publish_datetime 
    AND target.title = source.title
    AND target.language = source.language
)
WHEN MATCHED THEN
    UPDATE SET
        company_name = source.company_name,
        publish_date = source.publish_date,
        pdf_url = source.pdf_url,
        has_xbrl = source.has_xbrl,
        notes = source.notes,
        sector = source.sector,
        listed_exchange = source.listed_exchange,
        xbrl_url = source.xbrl_url,
        updated_time = GETUTCDATE(),
        updated_by = @created_by
WHEN NOT MATCHED THEN
    INSERT (
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
        created_by
    )
    VALUES (
        source.publish_datetime,
        source.publish_date,
        source.stock_code,
        source.company_name,
        source.title,
        source.pdf_url,
        source.has_xbrl,
        source.notes,
        source.language,
        source.sector,
        source.listed_exchange,
        source.xbrl_url,
        GETUTCDATE(),
        @created_by
    );
