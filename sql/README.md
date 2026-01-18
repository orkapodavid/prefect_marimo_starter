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

## 7. CRUD SQL File Guidelines

When writing SQL files for CRUD operations (e.g., in `sql/queries/`), adhere to the following structure and patterns.

### Metadata Header

Every SQL file **MUST** start with a YAML-formatted metadata block in a multi-line comment.

```sql
/*
description: [Short description of the query's purpose]
note: |
  [Detailed notes, usage instructions, or warnings]
  [Mention parameter replacements if any]
version: 1.0.0
*/
```

### Parameters Section

Define parameters using a stylized comment block. Provide commented-out `DECLARE` statements for easy manual testing in SSMS/Azure Data Studio.

```sql
/*__PARAMETERS__*/
-- Example parameters for manual execution (uncomment to run in SSMS):
-- DECLARE @date_from DATE = '2026-01-01';
-- DECLARE @date_to DATE = '2026-01-31';
```

### Query Structure

1.  **Explicit Columns**: **NEVER** use `SELECT *`. List all required columns explicitly.
2.  **Schema qualification**: Always use the fully qualified table name (e.g., `[dealSourcing].[tblAsxAnnouncement]`).
3.  **NoLock**: Use `WITH (NOLOCK)` for all read-only queries to prevent blocking, unless strict consistency is required.
4.  **Filtering**: Use standard SQL parameters (e.g., `@date_from`) in the `WHERE` clause.

### Example Template

```sql
/*
description: Query announcements within a date range
note: |
  Returns all announcements strictly between the provided dates.
version: 1.0.0
*/

/*__PARAMETERS__*/
-- DECLARE @date_from DATE = '2024-01-01';
-- DECLARE @date_to DATE = '2024-01-31';

SELECT
  id,
  ticker,
  announcement_date,
  title,
  pdf_url,
  created_time
FROM [dealSourcing].[tblAsxAnnouncement] WITH (NOLOCK)
WHERE announcement_date >= @date_from
  AND announcement_date <= @date_to
ORDER BY announcement_date DESC;
```
