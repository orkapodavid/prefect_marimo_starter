/*
description: Get a document by ID with its associated deal details
note: |
  Retrieves a single document and LEFT JOINs deal details.
  Parameter: @doc_id VARCHAR(50)
version: 1.0.0
*/

/*__PARAMETERS__*/
-- Example parameters for manual execution (uncomment to run in SSMS):
-- DECLARE @doc_id VARCHAR(50) = 'sample_doc_id_123';

SELECT
    d.id,
    d.doc_id,
    d.stock_code,
    d.company_name,
    d.title,
    d.description,
    d.publish_datetime,
    d.publish_date,
    d.pdf_url,
    d.tier,
    d.pdf_downloaded,
    d.processed_at,
    d.created_time,
    d.created_by,
    d.updated_time,
    d.updated_by,
    dd.investor,
    dd.deal_size,
    dd.deal_size_currency,
    dd.share_price,
    dd.share_count,
    dd.deal_date,
    dd.deal_structure
FROM [dealSourcing].[tblSearchDocuments] d WITH (NOLOCK)
LEFT JOIN [dealSourcing].[tblSearchDealDetails] dd WITH (NOLOCK) ON d.doc_id = dd.doc_id
WHERE d.doc_id = @doc_id;
