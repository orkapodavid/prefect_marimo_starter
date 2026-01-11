INSERT INTO asx_companies (ticker, company_name, industry)
VALUES (:ticker, :company_name, :industry)
ON CONFLICT (ticker) DO UPDATE
SET company_name = EXCLUDED.company_name,
    industry = EXCLUDED.industry,
    last_updated = CURRENT_TIMESTAMP;
