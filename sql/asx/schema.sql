-- Schema for ASX Scraper Data
-- Compatible with PostgreSQL

-- Table for storing the master list of ASX companies
CREATE TABLE IF NOT EXISTS asx_companies (
    ticker VARCHAR(10) PRIMARY KEY,
    company_name VARCHAR(255),
    industry VARCHAR(255),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for general ASX announcements (from asx_announcement_scraper_enhanced.py)
CREATE TABLE IF NOT EXISTS asx_announcements (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    announcement_date DATE,
    announcement_time TIME,
    is_price_sensitive BOOLEAN,
    headline TEXT,
    number_of_pages INT,
    file_size VARCHAR(50),
    pdf_url TEXT,
    downloaded_file_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_announcement UNIQUE (ticker, announcement_date, announcement_time, headline)
);

-- Table for PIPE (Private Investment in Public Equity) specific announcements (from asx_pipe_scraper.py)
CREATE TABLE IF NOT EXISTS asx_pipe_announcements (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    company_name VARCHAR(255),
    announcement_datetime TIMESTAMP,
    title TEXT,
    pdf_link TEXT,
    description TEXT,
    is_price_sensitive BOOLEAN,
    downloaded_file_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_pipe_announcement UNIQUE (ticker, announcement_datetime, title)
);

-- Table for Appendix 5B and Cash Flow Reports (from asx_appendix5b_scraper.py)
CREATE TABLE IF NOT EXISTS asx_appendix_5b_reports (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    report_date DATE,
    headline TEXT,
    pdf_link TEXT,
    total_available_funding DECIMAL(20, 2), -- Section 8.6
    estimated_quarters_funding DECIMAL(10, 2), -- Section 8.7
    matched_keywords TEXT, -- JSON or comma-separated string
    extraction_warnings TEXT,
    downloaded_file_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_appendix_report UNIQUE (ticker, report_date, headline)
);

-- Indexes for faster searching
CREATE INDEX idx_announcements_ticker ON asx_announcements(ticker);
CREATE INDEX idx_announcements_date ON asx_announcements(announcement_date);

CREATE INDEX idx_pipe_ticker ON asx_pipe_announcements(ticker);
CREATE INDEX idx_pipe_datetime ON asx_pipe_announcements(announcement_datetime);

CREATE INDEX idx_appendix_ticker ON asx_appendix_5b_reports(ticker);
CREATE INDEX idx_appendix_date ON asx_appendix_5b_reports(report_date);
