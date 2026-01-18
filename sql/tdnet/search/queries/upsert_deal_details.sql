/*
description: Upsert deal details for a document
note: |
  Inserts new deal details or updates existing ones based on doc_id.
  Uses T-SQL MERGE statement.
  Parameters: @doc_id, @investor, @deal_size, @deal_size_currency, @share_price,
              @share_count, @deal_date, @deal_structure, @raw_text_snippet,
              @created_by, @updated_by
version: 1.0.0
*/

/*__PARAMETERS__*/
-- Example parameters for manual execution (uncomment to run in SSMS):
-- DECLARE @doc_id VARCHAR(50) = 'sample_doc_id_123';
-- DECLARE @investor NVARCHAR(MAX) = N'Sample Investor';
-- DECLARE @deal_size VARCHAR(100) = '100M';
-- DECLARE @deal_size_currency VARCHAR(50) = 'JPY';
-- DECLARE @share_price VARCHAR(100) = '1500';
-- DECLARE @share_count VARCHAR(100) = '1000000';
-- DECLARE @deal_date VARCHAR(100) = '2026-01-15';
-- DECLARE @deal_structure VARCHAR(50) = 'Placement';
-- DECLARE @raw_text_snippet NVARCHAR(MAX) = N'Sample text snippet...';
-- DECLARE @created_by VARCHAR(20) = 'system';
-- DECLARE @updated_by VARCHAR(20) = 'system';

MERGE INTO [dealSourcing].[tblSearchDealDetails] AS target
USING (SELECT @doc_id AS doc_id) AS source
ON target.doc_id = source.doc_id
WHEN MATCHED THEN
    UPDATE SET
        investor = @investor,
        deal_size = @deal_size,
        deal_size_currency = @deal_size_currency,
        share_price = @share_price,
        share_count = @share_count,
        deal_date = @deal_date,
        deal_structure = @deal_structure,
        raw_text_snippet = @raw_text_snippet,
        updated_time = GETUTCDATE(),
        updated_by = @updated_by
WHEN NOT MATCHED THEN
    INSERT (doc_id, investor, deal_size, deal_size_currency, share_price,
            share_count, deal_date, deal_structure, raw_text_snippet, created_by)
    VALUES (@doc_id, @investor, @deal_size, @deal_size_currency, @share_price,
            @share_count, @deal_date, @deal_structure, @raw_text_snippet, @created_by);
