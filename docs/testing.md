# Testing

## Directory Structure

Tests are organized into the following directories:

*   `tests/unit`: Unit tests for individual components. These should be fast and not require external dependencies.
*   `tests/integration`: Integration tests that may involve multiple components or external systems (e.g., databases, APIs).
*   `tests/notebooks`: Interactive Marimo notebooks used for manual verification and exploration.

## Running Tests

### Unit and Integration Tests

We use `pytest` to run unit and integration tests.

To run all tests:
```bash
pytest
```

To run only unit tests:
```bash
pytest tests/unit
```

To run only integration tests:
```bash
pytest tests/integration
```

### Notebook Tests

Notebook tests are interactive Marimo notebooks. You can run them to manually verify functionality.

To run a notebook test interactively:
```bash
marimo edit tests/notebooks/<notebook_name>.py
```

For example:
```bash
marimo edit tests/notebooks/test_mssql_service.py
```

## Adding New Tests

*   **Unit Tests:** Add new unit tests to `tests/unit/`. Use the `test_` prefix for files and functions.
*   **Integration Tests:** Add new integration tests to `tests/integration/`. Use the `test_` prefix.
*   **Notebook Tests:** Add new interactive notebooks to `tests/notebooks/`.
