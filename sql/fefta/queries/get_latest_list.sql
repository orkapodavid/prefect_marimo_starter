/*
description: Get the latest list of FEFTA listed companies
note: |
  Retrieves the current state of all companies in the FEFTA list.
  Since the table is system-versioned, querying the main table automatically
  returns the current valid records. The updated_time column reflects
  the latest change timestamp for each record.
version: 1.0.0
*/

/*__PARAMETERS__*/
-- No parameters required

SELECT
    id,
    securities_code,
    isin_code,
    company_name_ja,
    issue_or_company_name,
    category,
    core_operator,
    created_time,
    created_by,
    updated_time,
    updated_by
FROM [dealSourcing].[tblFeftaListedCompany] WITH (NOLOCK)
ORDER BY securities_code;
