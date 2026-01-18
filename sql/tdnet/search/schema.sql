-- Schema for TDnet Search Service
-- Table names prefixed with 'tbl' and use camel case

-- Table for storing company information
CREATE TABLE IF NOT EXISTS tblSearchCompanies (
    stock_code VARCHAR(10) PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for storing the main document metadata
CREATE TABLE IF NOT EXISTS tblSearchDocuments (
    doc_id VARCHAR(50) PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    publish_datetime TIMESTAMP NOT NULL,
    publish_date DATE NOT NULL,
    pdf_url TEXT,
    tier VARCHAR(20),
    pdf_downloaded BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (stock_code) REFERENCES tblSearchCompanies(stock_code)
);

-- Table for storing extracted deal details (One-to-One with documents)
CREATE TABLE IF NOT EXISTS tblSearchDealDetails (
    id SERIAL PRIMARY KEY, -- or INTEGER PRIMARY KEY AUTOINCREMENT for SQLite
    doc_id VARCHAR(50) NOT NULL UNIQUE,
    investor TEXT,
    deal_size VARCHAR(100),
    deal_size_currency VARCHAR(50),
    share_price VARCHAR(100),
    share_count VARCHAR(100),
    deal_date VARCHAR(100),
    deal_structure VARCHAR(50),
    raw_text_snippet TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doc_id) REFERENCES tblSearchDocuments(doc_id) ON DELETE CASCADE
);

-- Index for faster range queries
CREATE INDEX IF NOT EXISTS idxTblSearchDocumentsPublishDate ON tblSearchDocuments(publish_date);
CREATE INDEX IF NOT EXISTS idxTblSearchDocumentsStockCode ON tblSearchDocuments(stock_code);

-- Table for tracking scrape sessions/metadata (optional but good for audit)
CREATE TABLE IF NOT EXISTS tblSearchScrapeSessions (
    session_id VARCHAR(50) PRIMARY KEY,
    scrape_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    search_terms TEXT, -- JSON string or similar
    entries_found INTEGER,
    new_entries INTEGER
);

