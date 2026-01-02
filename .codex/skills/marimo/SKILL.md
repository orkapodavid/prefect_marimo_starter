---
name: Marimo
description: This skill should be used when the user asks to "create a marimo notebook", "edit marimo app", "convert Jupyter to marimo", "add marimo widgets", "use marimo UI elements", or mentions marimo reactive notebooks, mode detection, or marimo export functionality.
version: 0.1.0
---

# Marimo

Marimo is a reactive notebook framework for Python that stores notebooks as pure Python files, making them Git-friendly and executable as scripts or interactive apps.

## Core Concepts

**Reactive Notebooks**: Marimo notebooks automatically re-run cells when their dependencies change, creating a reactive dataflow graph. This eliminates stale outputs and ensures consistency.

**Pure Python Storage**: Notebooks are stored as `.py` files with a specific structure, making them version-control friendly and executable in multiple modes.

**Three Execution Modes**:
- `marimo edit notebook.py` - Interactive development with live editing
- `marimo run notebook.py` - Read-only app mode for dashboards
- `python notebook.py` - Script execution for CLI or automation

## App Structure

Every marimo notebook follows this basic structure:

```python
import marimo

__generated_with = "0.18.4"
app = marimo.App(width="medium")

# Shared imports for @app.function exports
with app.setup:
    import pandas as pd

@app.cell
def _():
    import marimo as mo
    return (mo,)

@app.cell
def _(mo):
    slider = mo.ui.slider(1, 100, value=50)
    slider
    return (slider,)

@app.cell
def _(slider):
    result = slider.value * 2
    result
    return

if __name__ == "__main__":
    app.run()
```

**Key Structure Elements**:
- `app = marimo.App()` - Creates the app instance
- `with app.setup:` - Shared imports for exported functions
- `@app.cell` - Defines reactive cells
- `@app.function` - Exports functions for external use

## Key Patterns

### Exporting Functions

Use `@app.function` decorator to export functions for use outside the notebook:

```python
@app.function
def exported_function(x: int) -> int:
    return x * 2
```

### Mode Detection

Detect the execution mode to conditionally run code:

```python
if mo.app_meta().mode == "edit":
    # Interactive widgets, charts, debugging
    pass
elif mo.app_meta().mode == "script":
    # Production execution
    pass
```

### UI Elements

Create interactive widgets with `mo.ui`:

```python
slider = mo.ui.slider(min, max, value=default)
text_input = mo.ui.text(value="", label="")
dropdown = mo.ui.dropdown(options=["a", "b", "c"])
run_button = mo.ui.run_button(label="Run")
table = mo.ui.table(df)  # Interactive dataframe
```

### Layout Components

Organize UI elements with layout functions:

```python
mo.vstack([widget1, widget2])  # Vertical stack
mo.hstack([left, right])       # Horizontal stack
mo.tabs({"Tab 1": content1, "Tab 2": content2})  # Tabbed interface
```

## CLI Reference

| Command | Purpose |
|---------|---------|
| `marimo edit notebook.py` | Edit notebook interactively |
| `marimo run notebook.py` | Run as read-only app |
| `marimo check notebook.py` | Lint and validate notebook |
| `marimo convert file.ipynb` | Convert from Jupyter |
| `marimo export html notebook.py` | Export to HTML |

## Additional Resources

### Reference Files

For detailed API documentation and advanced patterns, consult:
- **`references/api-reference.md`** - Detailed UI elements, PEP 723 dependencies, export options, and full documentation links
