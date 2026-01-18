-- Upsert Deal Details
INSERT INTO tblSearchDealDetails (
    doc_id, investor, deal_size, deal_size_currency, 
    share_price, share_count, deal_date, deal_structure, 
    raw_text_snippet
)
VALUES (
    :doc_id, :investor, :deal_size, :deal_size_currency,
    :share_price, :share_count, :deal_date, :deal_structure,
    :raw_text_snippet
)
ON CONFLICT (doc_id) DO UPDATE SET
    investor = EXCLUDED.investor,
    deal_size = EXCLUDED.deal_size,
    deal_size_currency = EXCLUDED.deal_size_currency,
    share_price = EXCLUDED.share_price,
    share_count = EXCLUDED.share_count,
    deal_date = EXCLUDED.deal_date,
    deal_structure = EXCLUDED.deal_structure,
    raw_text_snippet = EXCLUDED.raw_text_snippet;
