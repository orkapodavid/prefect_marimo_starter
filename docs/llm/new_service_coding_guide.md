# New Service Coding Guide

This guide outlines the standard procedure for adding new backend services to the project. We follow a modular, service-oriented structure to ensure scalability and maintainability.

## Directory Structure

All services should be located in `src/services/`.
Each service gets its own dedicated directory.

**Pattern:**
`src/services/<service_name>/<service_name>_service.py`

**Example:**
If you are creating a service for "Exchange Email", the structure should be:
```
src/
└── services/
    └── exchange_email/
        ├── __init__.py
        └── exchange_email_service.py
```

## Implementation Rules

1.  **Dedicated Directory**: Never place a new service directly in `src/` or `src/shared_utils/`. Always create a new directory in `src/services/`.
2.  **Naming Convention**:
    *   Directory: `snake_case` name of the domain (e.g., `google_sheets`, `salesforce_crm`).
    *   File: `<domain>_service.py` (e.g., `google_sheets_service.py`).
    *   Class: `PascalCase` name ending in `Service` (e.g., `GoogleSheetsService`).
3.  **Dependencies**: If the service requires new libraries, add them to `pyproject.toml` immediately.

## Testing

For every service, create a corresponding Marimo notebook for interactive testing.

**Location**: `notebooks/src/services/<domain>/test_<domain>_service.py`
This mirrors the source path `src/services/<domain>/...`.

**Contents**:
*   Import the service.
*   Load env vars.
*   Provide UI controls (inputs).
*   Execute service methods and display results.

## Example Workflow

1.  **Plan**: Identify the domain (e.g., `pdf_generator`).
2.  **Create Structure**:
    ```bash
    mkdir -p src/services/pdf_generator
    touch src/services/pdf_generator/__init__.py
    ```
3.  **Implement**: Write `src/services/pdf_generator/pdf_generator_service.py`.
4.  **Test**: Create `notebooks/src/services/pdf_generator/test_pdf_generator_service.py`.
