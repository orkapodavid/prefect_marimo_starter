# SQL Schema Guidelines

This document outlines the standard guidelines for writing SQL table schemas, based on the `dealSourcing` patterns.

## 1. Naming Conventions

*   **Schema Name**: Must be `[dealSourcing]`.
    *   Example: `[dealSourcing]`
*   **Table Name**: Use **PascalCase** prefixed with `tbl`.
    *   Example: `[tblAsxAnnouncement]`
*   **Column Names**: Use **snake_case**.
    *   Example: `ticker`, `announcement_date`, `is_price_sensitive`
*   **Quoting**: Always use brackets `[]` for identifiers to ensure safety and reserved word compatibility.

## 2. Standard Columns (Audit)

Every table **MUST** include the following identity and audit columns:

| Column Name | Data Type | Nullable | Default / Notes |
| :--- | :--- | :--- | :--- |
| `id` | `INT` | NO | `IDENTITY(1,1)` Primary Key |
| `created_time` | `DATETIME2` | NO | Default to current time (e.g., UTC or business timezone) |
| `created_by` | `VARCHAR(20)` | NO | System or User ID creating the record |
| `updated_time` | `DATETIME2` | YES | Timestamp of last update |
| `updated_by` | `VARCHAR(20)` | YES | System or User ID modifying the record |

*Note: The sample used `Created_Time` (PascalCase), but `snake_case` is recommended for consistency with other columns.*

## 3. Data Types

*   **Strings**:
    *   `NVARCHAR(n)` or `NVARCHAR(MAX)` for text that may contain Unicode/special characters.
    *   `VARCHAR(n)` for fixed standard codes (e.g., Tickers, ISINs).
*   **Dates**:
    *   `DATE` for calendar dates.
    *   `TIME(0)` for time without sub-second precision.
    *   `DATETIME2` for high-precision timestamps.
*   **Booleans**:
    *   `BIT` (0 or 1).

## 4. Constraints

**Always** explicitly name your constraints to ensure they are easy to reference and manage.

*   **Format**: `[ConstraintType]_[TableName]_[ColumnName(s)]`
    *   **Primary Key**: `CONSTRAINT [PK_tblAsxAnnouncement] PRIMARY KEY`
    *   **Default**: `CONSTRAINT [DF_tblAsxAnnouncement_announcement_type] DEFAULT (...)`
    *   **Check**: `CONSTRAINT [CK_tblAsxAnnouncement_matched_keywords_isjson] CHECK (...)`
    *   **Unique**: `CONSTRAINT [UQ_tblAsxAnnouncement_ticker_date_hash] UNIQUE (...)`

## 5. Idempotency

Ensure scripts can be re-run without error. Use object existence checks before creation.

```sql
IF OBJECT_ID(N'[dealSourcing].[tblTableName]', N'U') IS NULL
BEGIN
    CREATE TABLE ...
END
```

## 6. Advanced Patterns

### Computed Hash Columns for Uniqueness
When creating a unique constraint on long text columns (like URLs), create a persisted computed column with a hash of the text.

```sql
-- Column Definition
pdf_url NVARCHAR(2048) NOT NULL,
pdf_url_hash AS CONVERT(BINARY(32), HASHBYTES('SHA2_256', UPPER(RTRIM(pdf_url)))) PERSISTED,

-- Unique Constraint using the Hash
CONSTRAINT [UQ_tblAsxAnnouncement_Hash] UNIQUE (pdf_url_hash)
```

### JSON Validation
If storing JSON data in text columns, enforce validity with a generic check constraint.

```sql
CONSTRAINT [CK_tblAsxAnnouncement_JsonCol_IsJson]
    CHECK (JsonCol IS NULL OR ISJSON(JsonCol) = 1)
```

## Sample Template

```sql
IF OBJECT_ID(N'[dealSourcing].[tblExample]', N'U') IS NULL
BEGIN
CREATE TABLE [dealSourcing].[tblExample] (
    -- Identity
    id INT IDENTITY(1,1) NOT NULL
        CONSTRAINT [PK_tblExample] PRIMARY KEY,

    -- Data Columns
    name NVARCHAR(100) NOT NULL,
    metadata NVARCHAR(MAX) NULL,

    -- Audit Columns
    created_time DATETIME2 NOT NULL
        CONSTRAINT [DF_tblExample_created_time] DEFAULT (GETUTCDATE()),
    created_by VARCHAR(20) NOT NULL,
    updated_time DATETIME2 NULL,
    updated_by VARCHAR(20) NULL,

    -- Constraints
    CONSTRAINT [CK_tblExample_metadata_isjson]
        CHECK (metadata IS NULL OR ISJSON(metadata) = 1)
);
END
GO
```
