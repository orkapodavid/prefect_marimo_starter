/*
description: Upsert a FEFTA source record
note: |
  Inserts a new FEFTA source record or updates an existing one if it matches the file_url.
  Matches on file_url_hash for efficiency if possible, or just file_url.
  Since we compute hash in schema, we can match on original url in MERGE source but schema uses hash for Unique.
  MERGE ON file_url should be fine.
version: 1.0.0
*/

/*__PARAMETERS__*/
-- DECLARE @as_of_raw NVARCHAR(255) = 'As of 15 July, 2025';
-- DECLARE @as_of_date DATE = '2025-07-15';
-- DECLARE @download_date DATE = '2026-01-18';
-- DECLARE @file_url NVARCHAR(2048) = 'https://www.mof.go.jp/english/policy/international_policy/fdi/list.xlsx';
-- DECLARE @saved_path NVARCHAR(MAX) = 'data/fefta/list.xlsx';
-- DECLARE @created_by VARCHAR(20) = 'system';

MERGE [dealSourcing].[tblFeftaSource] AS target
USING (SELECT 
    @file_url AS file_url
) AS source
ON (
    target.file_url = source.file_url
)
WHEN MATCHED THEN
    UPDATE SET
        as_of_raw = @as_of_raw,
        as_of_date = @as_of_date,
        download_date = @download_date,
        saved_path = @saved_path,
        updated_time = GETUTCDATE(),
        updated_by = @created_by
WHEN NOT MATCHED THEN
    INSERT (
        as_of_raw,
        as_of_date,
        download_date,
        file_url,
        saved_path,
        created_time,
        created_by
    )
    VALUES (
        @as_of_raw,
        @as_of_date,
        @download_date,
        @file_url,
        @saved_path,
        GETUTCDATE(),
        @created_by
    );
