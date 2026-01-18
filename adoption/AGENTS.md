# AI Agents Documentation

This document serves as a guide for AI agents working on this repository.

## Repository Structure

The project follows a standard `src`-layout:

```
research/
├── src/
│   └── market_intelligence/    # Application source code
├── tests/                      # Test suite
├── docs/                       # Documentation
├── sql/                        # SQL queries and schema
└── pyproject.toml              # Project configuration
```

## Development Guidelines

### 1. Code Style
- Follow PEP 8 conventions.
- Use `snake_case` for file names, function names, and variable names.
- Use `PascalCase` for class names.
- Ensure all new files have a docstring explaining their purpose.

### 2. Testing
- Place all tests in the `tests/` directory.
- Use `pytest` for running tests.
- Ensure tests are independent and do not leave artifacts (files) behind.
- Use `unittest.mock` to mock external API calls (TDnet, EDINET, etc.).

### 3. Dependency Management
- Use `uv` for dependency management.
- Run `uv sync` to install dependencies.
- Add new dependencies via `pyproject.toml` and run `uv sync`.

### 4. File Operations
- **DO NOT** hardcode paths. Use `os.path` or `pathlib`.
- Output generated files (CSVs, PDFs) to an ignored `output/` directory or a temporary directory during tests.

## Key Modules

- **`market_intelligence.tdnet_scraper`**: Scrapes third-party allotment deals from TDnet Search.
- **`market_intelligence.tdnet_announcement_scraper`**: Official TDnet announcement scraper.
- **`market_intelligence.edinet_backfill`**: Backfills missing PDF links using EDINET data.

## Common Tasks

- **Running Tests**: `uv run pytest`
- **Running Scraper**: `uv run python -m market_intelligence.tdnet_scraper --period today`
