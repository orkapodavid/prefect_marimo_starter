-- Upsert Company
INSERT INTO tblSearchCompanies (stock_code, company_name, updated_at)
VALUES (:stock_code, :company_name, CURRENT_TIMESTAMP)
ON CONFLICT (stock_code) DO UPDATE SET
    company_name = EXCLUDED.company_name,
    updated_at = CURRENT_TIMESTAMP;
