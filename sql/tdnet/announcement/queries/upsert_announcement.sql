/*
description: Upsert a generic TDnet announcement
note: |
  Inserts a new announcement or updates an existing one if it matches the unique composite key
  (stock_code, publish_datetime, title, language).
  Updates fields like notes, pdf_url, etc.
version: 1.0.0
*/

/*__PARAMETERS__*/
-- DECLARE @publish_datetime DATETIME2 = '2026-01-15T16:30:00';
-- DECLARE @publish_date DATE = '2026-01-15';
-- DECLARE @stock_code VARCHAR(10) = '40620';
-- DECLARE @company_name NVARCHAR(255) = 'IBIDEN CO.,LTD.';
-- DECLARE @title NVARCHAR(500) = 'Notice Concerning Tender Offer';
-- DECLARE @pdf_url NVARCHAR(2048) = 'https://www.release.tdnet.info/inbs/ek/140120260115534185.pdf';
-- DECLARE @has_xbrl BIT = 0;
-- DECLARE @notes NVARCHAR(50) = '';
-- DECLARE @language VARCHAR(20) = 'english';
-- DECLARE @sector NVARCHAR(100) = 'Electric Appliances';
-- DECLARE @listed_exchange NVARCHAR(50) = NULL;
-- DECLARE @xbrl_url NVARCHAR(2048) = NULL;
-- DECLARE @created_by VARCHAR(20) = 'system';

MERGE [dealSourcing].[tblTdnetAnnouncement] AS target
USING (SELECT 
    @stock_code AS stock_code, 
    @publish_datetime AS publish_datetime, 
    @title AS title, 
    @language AS language
) AS source
ON (
    target.stock_code = source.stock_code 
    AND target.publish_datetime = source.publish_datetime 
    AND target.title = source.title
    AND target.language = source.language
)
WHEN MATCHED THEN
    UPDATE SET
        company_name = @company_name,
        publish_date = @publish_date,
        pdf_url = @pdf_url,
        has_xbrl = @has_xbrl,
        notes = @notes,
        sector = @sector,
        listed_exchange = @listed_exchange,
        xbrl_url = @xbrl_url,
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
        @publish_datetime,
        @publish_date,
        @stock_code,
        @company_name,
        @title,
        @pdf_url,
        @has_xbrl,
        @notes,
        @language,
        @sector,
        @listed_exchange,
        @xbrl_url,
        GETUTCDATE(),
        @created_by
    );
