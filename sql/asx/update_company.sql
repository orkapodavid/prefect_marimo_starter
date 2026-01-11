UPDATE asx_companies
SET company_name = :company_name,
    industry = :industry,
    last_updated = CURRENT_TIMESTAMP
WHERE ticker = :ticker;
