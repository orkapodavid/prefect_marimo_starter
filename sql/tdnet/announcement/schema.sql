/*
description: Schema for TDnet Company Announcements
note: |
  Creates the main table for storing TDnet announcements (English and Japanese).
  Uses [dealSourcing] schema.
  Run this script in SSMS or Azure Data Studio.
version: 1.0.0
*/

-- =============================================================================
-- Table: tblTdnetAnnouncement
-- =============================================================================
IF OBJECT_ID(N'[dealSourcing].[tblTdnetAnnouncement]', N'U') IS NULL
BEGIN
CREATE TABLE [dealSourcing].[tblTdnetAnnouncement] (
    id INT IDENTITY(1,1) NOT NULL
        CONSTRAINT [PK_tblTdnetAnnouncement] PRIMARY KEY,

    -- Core Data
    publish_datetime DATETIME2 NOT NULL,
    publish_date DATE NOT NULL,
    stock_code VARCHAR(10) NOT NULL,
    company_name NVARCHAR(255) NOT NULL,
    title NVARCHAR(500) NOT NULL,
    pdf_url NVARCHAR(2048) NULL,
    has_xbrl BIT NOT NULL
        CONSTRAINT [DF_tblTdnetAnnouncement_has_xbrl] DEFAULT (0),
    notes NVARCHAR(50) NULL,
    language VARCHAR(20) NOT NULL,
    sector NVARCHAR(100) NULL,
    listed_exchange NVARCHAR(50) NULL,
    xbrl_url NVARCHAR(2048) NULL,

    -- Computed Hash for Uniqueness (stock_code + publish_datetime + title + language)
    -- Using CONVERT(VARCHAR, publish_datetime, 126) for ISO8601 format in hash
    announcement_hash AS CONVERT(BINARY(32), HASHBYTES('SHA2_256', 
        UPPER(CONCAT(
            stock_code, '|', 
            CONVERT(VARCHAR(30), publish_datetime, 126), '|',
            title, '|',
            language
        ))
    )) PERSISTED,

    -- Audit Columns
    created_time DATETIME2 NOT NULL
        CONSTRAINT [DF_tblTdnetAnnouncement_created_time] DEFAULT (GETUTCDATE()),
    created_by VARCHAR(20) NOT NULL,
    updated_time DATETIME2 NULL,
    updated_by VARCHAR(20) NULL,

    -- Constraints
    CONSTRAINT [UQ_tblTdnetAnnouncement_announcement_hash] UNIQUE (announcement_hash)
);
END
GO

-- Indexes for common search patterns
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_tblTdnetAnnouncement_publish_date' AND object_id = OBJECT_ID('[dealSourcing].[tblTdnetAnnouncement]'))
BEGIN
    CREATE INDEX [IX_tblTdnetAnnouncement_publish_date] ON [dealSourcing].[tblTdnetAnnouncement](publish_date);
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_tblTdnetAnnouncement_stock_code' AND object_id = OBJECT_ID('[dealSourcing].[tblTdnetAnnouncement]'))
BEGIN
    CREATE INDEX [IX_tblTdnetAnnouncement_stock_code] ON [dealSourcing].[tblTdnetAnnouncement](stock_code);
END
GO
