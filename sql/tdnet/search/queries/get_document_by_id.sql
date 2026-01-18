-- Get Document by ID with Deal Details
SELECT 
    d.*, 
    dd.investor, dd.deal_size, dd.deal_size_currency, 
    dd.share_price, dd.share_count, dd.deal_date, dd.deal_structure
FROM tblSearchDocuments d
LEFT JOIN tblSearchDealDetails dd ON d.doc_id = dd.doc_id
WHERE d.doc_id = :doc_id;
