/*
description: Upsert a company record
note: |
  Inserts a new company or updates an existing one based on stock_code.
  Uses T-SQL MERGE statement.
  Parameters: @stock_code, @company_name, @created_by, @updated_by
version: 1.0.0
*/

/*__PARAMETERS__*/
-- Example parameters for manual execution (uncomment to run in SSMS):
-- DECLARE @stock_code VARCHAR(10) = '1234';
-- DECLARE @company_name NVARCHAR(255) = N'Sample Company Ltd.';
-- DECLARE @created_by VARCHAR(20) = 'system';
-- DECLARE @updated_by VARCHAR(20) = 'system';

MERGE INTO [dealSourcing].[tblSearchCompanies] AS target
USING (SELECT @stock_code AS stock_code, @company_name AS company_name) AS source
ON target.stock_code = source.stock_code
WHEN MATCHED THEN
    UPDATE SET
        company_name = source.company_name,
        updated_time = GETUTCDATE(),
        updated_by = @updated_by
WHEN NOT MATCHED THEN
    INSERT (stock_code, company_name, created_by)
    VALUES (source.stock_code, source.company_name, @created_by);
