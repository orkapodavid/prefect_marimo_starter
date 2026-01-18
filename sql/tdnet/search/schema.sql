/*
description: Schema for TDnet Search Service
note: |
  Creates tables for companies, documents, deal details, and scrape sessions.
  All tables use the [dealSourcing] schema and follow T-SQL conventions.
  Run this script in SSMS or Azure Data Studio.
version: 1.0.0
*/

-- =============================================================================
-- Table: tblSearchCompanies
-- =============================================================================
IF OBJECT_ID(N'[dealSourcing].[tblSearchCompanies]', N'U') IS NULL
BEGIN
CREATE TABLE [dealSourcing].[tblSearchCompanies] (
    id INT IDENTITY(1,1) NOT NULL
        CONSTRAINT [PK_tblSearchCompanies] PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL
        CONSTRAINT [UQ_tblSearchCompanies_stock_code] UNIQUE,
    company_name NVARCHAR(255) NOT NULL,

    -- Audit Columns
    created_time DATETIME2 NOT NULL
        CONSTRAINT [DF_tblSearchCompanies_created_time] DEFAULT (GETUTCDATE()),
    created_by VARCHAR(20) NOT NULL,
    updated_time DATETIME2 NULL,
    updated_by VARCHAR(20) NULL
);
END
GO

-- =============================================================================
-- Table: tblSearchDocuments
-- =============================================================================
IF OBJECT_ID(N'[dealSourcing].[tblSearchDocuments]', N'U') IS NULL
BEGIN
CREATE TABLE [dealSourcing].[tblSearchDocuments] (
    id INT IDENTITY(1,1) NOT NULL
        CONSTRAINT [PK_tblSearchDocuments] PRIMARY KEY,
    doc_id VARCHAR(50) NOT NULL
        CONSTRAINT [UQ_tblSearchDocuments_doc_id] UNIQUE,
    stock_code VARCHAR(10) NOT NULL,
    company_name NVARCHAR(255) NOT NULL,
    title NVARCHAR(500) NOT NULL,
    description NVARCHAR(MAX) NULL,
    publish_datetime DATETIME2 NOT NULL,
    publish_date DATE NOT NULL,
    pdf_url NVARCHAR(2048) NULL,
    tier VARCHAR(20) NULL,
    pdf_downloaded BIT NOT NULL
        CONSTRAINT [DF_tblSearchDocuments_pdf_downloaded] DEFAULT (0),
    processed_at DATETIME2 NULL,

    -- Audit Columns
    created_time DATETIME2 NOT NULL
        CONSTRAINT [DF_tblSearchDocuments_created_time] DEFAULT (GETUTCDATE()),
    created_by VARCHAR(20) NOT NULL,
    updated_time DATETIME2 NULL,
    updated_by VARCHAR(20) NULL
);
END
GO

-- Index for faster range queries
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_tblSearchDocuments_publish_date' AND object_id = OBJECT_ID('[dealSourcing].[tblSearchDocuments]'))
BEGIN
    CREATE INDEX [IX_tblSearchDocuments_publish_date] ON [dealSourcing].[tblSearchDocuments](publish_date);
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_tblSearchDocuments_stock_code' AND object_id = OBJECT_ID('[dealSourcing].[tblSearchDocuments]'))
BEGIN
    CREATE INDEX [IX_tblSearchDocuments_stock_code] ON [dealSourcing].[tblSearchDocuments](stock_code);
END
GO

-- =============================================================================
-- Table: tblSearchDealDetails
-- =============================================================================
IF OBJECT_ID(N'[dealSourcing].[tblSearchDealDetails]', N'U') IS NULL
BEGIN
CREATE TABLE [dealSourcing].[tblSearchDealDetails] (
    id INT IDENTITY(1,1) NOT NULL
        CONSTRAINT [PK_tblSearchDealDetails] PRIMARY KEY,
    doc_id VARCHAR(50) NOT NULL
        CONSTRAINT [UQ_tblSearchDealDetails_doc_id] UNIQUE,
    investor NVARCHAR(MAX) NULL,
    deal_size VARCHAR(100) NULL,
    deal_size_currency VARCHAR(50) NULL,
    share_price VARCHAR(100) NULL,
    share_count VARCHAR(100) NULL,
    deal_date VARCHAR(100) NULL,
    deal_structure VARCHAR(50) NULL,
    raw_text_snippet NVARCHAR(MAX) NULL,

    -- Audit Columns
    created_time DATETIME2 NOT NULL
        CONSTRAINT [DF_tblSearchDealDetails_created_time] DEFAULT (GETUTCDATE()),
    created_by VARCHAR(20) NOT NULL,
    updated_time DATETIME2 NULL,
    updated_by VARCHAR(20) NULL
);
END
GO

-- =============================================================================
-- Table: tblSearchScrapeSessions
-- =============================================================================
IF OBJECT_ID(N'[dealSourcing].[tblSearchScrapeSessions]', N'U') IS NULL
BEGIN
CREATE TABLE [dealSourcing].[tblSearchScrapeSessions] (
    id INT IDENTITY(1,1) NOT NULL
        CONSTRAINT [PK_tblSearchScrapeSessions] PRIMARY KEY,
    session_id VARCHAR(50) NOT NULL
        CONSTRAINT [UQ_tblSearchScrapeSessions_session_id] UNIQUE,
    scrape_date DATETIME2 NOT NULL
        CONSTRAINT [DF_tblSearchScrapeSessions_scrape_date] DEFAULT (GETUTCDATE()),
    search_terms NVARCHAR(MAX) NULL,
    entries_found INT NULL,
    new_entries INT NULL,

    -- Audit Columns
    created_time DATETIME2 NOT NULL
        CONSTRAINT [DF_tblSearchScrapeSessions_created_time] DEFAULT (GETUTCDATE()),
    created_by VARCHAR(20) NOT NULL,
    updated_time DATETIME2 NULL,
    updated_by VARCHAR(20) NULL,

    -- Constraints
    CONSTRAINT [CK_tblSearchScrapeSessions_search_terms_isjson]
        CHECK (search_terms IS NULL OR ISJSON(search_terms) = 1)
);
END
GO
