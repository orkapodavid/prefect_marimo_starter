SELECT ticker, company_name, industry, last_updated
FROM asx_companies
WHERE ticker = :ticker;
