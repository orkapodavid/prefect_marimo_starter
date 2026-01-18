/*
description: Find all changes since the last update for FEFTA listed companies
note: |
  This query compares the current data with the most recent historical version
  for each securities_code to identify what changed in the latest update.
  Returns rows where category or core_operator differ from the previous version.
version: 1.0.0
*/

/*__PARAMETERS__*/
-- No parameters required. This query finds all changes from the latest update.

-- Get current data
WITH CurrentData AS (
    SELECT 
        id,
        securities_code,
        isin_code,
        company_name_ja,
        issue_or_company_name,
        category,
        core_operator,
        SysStartTime,
        updated_time
    FROM [dealSourcing].[tblFeftaListedCompany]
),
-- Get the previous version of each row (before the latest update)
PreviousData AS (
    SELECT 
        h.securities_code,
        h.category AS prev_category,
        h.core_operator AS prev_core_operator,
        h.SysEndTime,
        ROW_NUMBER() OVER (PARTITION BY h.securities_code ORDER BY h.SysEndTime DESC) AS rn
    FROM [dealSourcing].[tblFeftaListedCompanyHistory] h
)
SELECT 
    c.securities_code,
    c.isin_code,
    c.company_name_ja,
    c.issue_or_company_name,
    p.prev_category,
    c.category AS new_category,
    p.prev_core_operator,
    c.core_operator AS new_core_operator,
    CASE 
        WHEN p.prev_category <> c.category THEN 'CATEGORY_CHANGED'
        WHEN ISNULL(p.prev_core_operator, -999) <> ISNULL(c.core_operator, -999) THEN 'CORE_OPERATOR_CHANGED'
        ELSE 'BOTH_CHANGED'
    END AS change_type,
    c.updated_time AS change_time
FROM CurrentData c
INNER JOIN PreviousData p 
    ON c.securities_code = p.securities_code AND p.rn = 1
WHERE 
    p.prev_category <> c.category
    OR ISNULL(p.prev_core_operator, -999) <> ISNULL(c.core_operator, -999)
ORDER BY c.securities_code;
