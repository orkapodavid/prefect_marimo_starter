/*
description: Upsert a document record
note: |
  Inserts a new document or updates an existing one based on doc_id.
  Uses T-SQL MERGE statement. pdf_url is preserved if the new value is NULL.
  Parameters: @doc_id, @stock_code, @company_name, @title, @description,
              @publish_datetime, @publish_date, @pdf_url, @tier,
              @pdf_downloaded, @processed_at, @created_by, @updated_by
version: 1.0.0
*/

/*__PARAMETERS__*/
-- Example parameters for manual execution (uncomment to run in SSMS):
-- DECLARE @doc_id VARCHAR(50) = 'sample_doc_id_123';
-- DECLARE @stock_code VARCHAR(10) = '1234';
-- DECLARE @company_name NVARCHAR(255) = N'Sample Company Ltd.';
-- DECLARE @title NVARCHAR(500) = N'Sample Document Title';
-- DECLARE @description NVARCHAR(MAX) = N'Sample description...';
-- DECLARE @publish_datetime DATETIME2 = '2026-01-15 10:30:00';
-- DECLARE @publish_date DATE = '2026-01-15';
-- DECLARE @pdf_url NVARCHAR(2048) = N'https://example.com/doc.pdf';
-- DECLARE @tier VARCHAR(20) = 'Prime';
-- DECLARE @pdf_downloaded BIT = 0;
-- DECLARE @processed_at DATETIME2 = GETUTCDATE();
-- DECLARE @created_by VARCHAR(20) = 'system';
-- DECLARE @updated_by VARCHAR(20) = 'system';

MERGE INTO [dealSourcing].[tblSearchDocuments] AS target
USING (SELECT @doc_id AS doc_id) AS source
ON target.doc_id = source.doc_id
WHEN MATCHED THEN
    UPDATE SET
        title = @title,
        description = @description,
        pdf_url = COALESCE(@pdf_url, target.pdf_url),
        tier = @tier,
        pdf_downloaded = @pdf_downloaded,
        processed_at = @processed_at,
        updated_time = GETUTCDATE(),
        updated_by = @updated_by
WHEN NOT MATCHED THEN
    INSERT (doc_id, stock_code, company_name, title, description,
            publish_datetime, publish_date, pdf_url, tier,
            pdf_downloaded, processed_at, created_by)
    VALUES (@doc_id, @stock_code, @company_name, @title, @description,
            @publish_datetime, @publish_date, @pdf_url, @tier,
            @pdf_downloaded, @processed_at, @created_by);
