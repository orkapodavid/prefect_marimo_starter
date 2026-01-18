-- =============================================================================
-- FEFTA Schema with Temporal Tables (SQL Server 2016+)
-- =============================================================================
-- NOTE: Temporal tables require a different creation pattern.
-- If you have an existing table, you need to drop it first or use ALTER.
-- This script assumes a fresh install.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Table: tblFeftaSource
-- -----------------------------------------------------------------------------
IF OBJECT_ID(N'[dealSourcing].[tblFeftaSource]', N'U') IS NULL
BEGIN
CREATE TABLE [dealSourcing].[tblFeftaSource] (
    -- Identity
    id INT IDENTITY(1,1) NOT NULL
        CONSTRAINT [PK_tblFeftaSource] PRIMARY KEY,

    -- Data Columns
    as_of_raw NVARCHAR(255) NOT NULL,
    as_of_date DATE NOT NULL,
    download_date DATE NOT NULL,
    file_url NVARCHAR(2048) NOT NULL,
    file_url_hash AS CONVERT(BINARY(32), HASHBYTES('SHA2_256', UPPER(RTRIM(file_url)))) PERSISTED,
    saved_path NVARCHAR(MAX) NULL,

    -- Audit Columns
    created_time DATETIME2 NOT NULL
        CONSTRAINT [DF_tblFeftaSource_created_time] DEFAULT (GETUTCDATE()),
    created_by VARCHAR(20) NOT NULL,
    updated_time DATETIME2 NULL,
    updated_by VARCHAR(20) NULL,

    -- Constraints
    CONSTRAINT [UQ_tblFeftaSource_file_url_hash] UNIQUE (file_url_hash)
);
END
GO

-- -----------------------------------------------------------------------------
-- Table: tblFeftaListedCompany (Temporal / System-Versioned)
-- -----------------------------------------------------------------------------
-- Drop existing table if it exists and is NOT temporal (for fresh setup)
-- If table already exists as temporal, this will be skipped.
IF OBJECT_ID(N'[dealSourcing].[tblFeftaListedCompany]', N'U') IS NULL
BEGIN
CREATE TABLE [dealSourcing].[tblFeftaListedCompany] (
    -- Identity
    id INT IDENTITY(1,1) NOT NULL
        CONSTRAINT [PK_tblFeftaListedCompany] PRIMARY KEY NONCLUSTERED,

    -- Data Columns
    securities_code NVARCHAR(50) NOT NULL,
    isin_code NVARCHAR(50) NOT NULL,
    company_name_ja NVARCHAR(500) NOT NULL,
    issue_or_company_name NVARCHAR(500) NOT NULL,
    category INT NOT NULL,
    core_operator INT NULL,

    -- Audit Columns
    created_time DATETIME2 NOT NULL
        CONSTRAINT [DF_tblFeftaListedCompany_created_time] DEFAULT (GETUTCDATE()),
    created_by VARCHAR(20) NOT NULL,
    updated_time DATETIME2 NULL,
    updated_by VARCHAR(20) NULL,

    -- Temporal Columns (System-Generated)
    SysStartTime DATETIME2 GENERATED ALWAYS AS ROW START HIDDEN NOT NULL,
    SysEndTime DATETIME2 GENERATED ALWAYS AS ROW END HIDDEN NOT NULL,
    PERIOD FOR SYSTEM_TIME (SysStartTime, SysEndTime),

    -- Constraints
    CONSTRAINT [UQ_tblFeftaListedCompany_securities_code] UNIQUE (securities_code)
)
WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = [dealSourcing].[tblFeftaListedCompanyHistory]));
END
GO
