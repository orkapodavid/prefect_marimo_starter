/*
description: Upsert a FEFTA listed company record
note: |
  Inserts a new FEFTA listed company record or updates an existing one if it matches the securities_code.
version: 1.0.0
*/

/*__PARAMETERS__*/
-- DECLARE @securities_code NVARCHAR(50) = '1234';
-- DECLARE @isin_code NVARCHAR(50) = 'JP1234567890';
-- DECLARE @company_name_ja NVARCHAR(MAX) = 'テスト株式会社';
-- DECLARE @issue_or_company_name NVARCHAR(MAX) = 'Test Inc.';
-- DECLARE @category INT = 1;
-- DECLARE @core_operator INT = 1;
-- DECLARE @created_by VARCHAR(20) = 'system';

MERGE [dealSourcing].[tblFeftaListedCompany] AS target
USING (SELECT 
    @securities_code AS securities_code
) AS source
ON (
    target.securities_code = source.securities_code
)
WHEN MATCHED THEN
    UPDATE SET
        isin_code = @isin_code,
        company_name_ja = @company_name_ja,
        issue_or_company_name = @issue_or_company_name,
        category = @category,
        core_operator = @core_operator,
        updated_time = GETUTCDATE(),
        updated_by = @created_by
WHEN NOT MATCHED THEN
    INSERT (
        securities_code,
        isin_code,
        company_name_ja,
        issue_or_company_name,
        category,
        core_operator,
        created_time,
        created_by
    )
    VALUES (
        @securities_code,
        @isin_code,
        @company_name_ja,
        @issue_or_company_name,
        @category,
        @core_operator,
        GETUTCDATE(),
        @created_by
    );
