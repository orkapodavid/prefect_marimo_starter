-- Upsert Document
INSERT INTO tblSearchDocuments (
    doc_id, stock_code, company_name, title, description, 
    publish_datetime, publish_date, pdf_url, tier, 
    pdf_downloaded, processed_at, updated_at
)
VALUES (
    :doc_id, :stock_code, :company_name, :title, :description,
    :publish_datetime, :publish_date, :pdf_url, :tier,
    :pdf_downloaded, :processed_at, CURRENT_TIMESTAMP
)
ON CONFLICT (doc_id) DO UPDATE SET
    title = EXCLUDED.title,
    description = EXCLUDED.description,
    pdf_url = COALESCE(EXCLUDED.pdf_url, tblSearchDocuments.pdf_url), -- Don't overwrite with null if we have one
    tier = EXCLUDED.tier,
    pdf_downloaded = EXCLUDED.pdf_downloaded,
    processed_at = EXCLUDED.processed_at,
    updated_at = CURRENT_TIMESTAMP;
