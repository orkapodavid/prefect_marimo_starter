# .codex/skills/marimo.md

## Marimo Skill

### Core Concepts

**Reactive notebooks**: Cells auto-run when dependencies change.

**Pure Python storage**: Notebooks are `.py` files, Git-friendly.

**Three execution modes**:
- `marimo edit notebook.py` - Interactive development
- `marimo run notebook.py` - Read-only app
- `python notebook.py` - Script execution

### App Structure

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

### Key Patterns

**@app.function decorator**: Export functions for external use
```python
@app.function
def exported_function(x: int) -> int:
    return x * 2
```

**Mode detection**:
```python
if mo.app_meta().mode == "edit":
    # Interactive widgets
    pass
elif mo.app_meta().mode == "script":
    # Production execution
    pass
```

**UI Elements**:
```python
mo.ui.slider(min, max, value=default)
mo.ui.text(value="", label="")
mo.ui.dropdown(options=["a", "b", "c"])
mo.ui.run_button(label="Run")
mo.ui.table(df)  # Interactive dataframe
```

**Layout**:
```python
mo.vstack([widget1, widget2])
mo.hstack([left, right])
mo.tabs({"Tab 1": content1, "Tab 2": content2})
```

### CLI Reference

| Command | Purpose |
|---------|---------|
| `marimo edit notebook.py` | Edit notebook |
| `marimo run notebook.py` | Run as app |
| `marimo check notebook.py` | Lint/validate |
| `marimo convert file.ipynb` | Convert from Jupyter |
| `marimo export html notebook.py` | Export to HTML |

### PEP 723 Inline Dependencies

```python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "pandas>=2.0.0",
#     "altair>=5.0.0",
# ]
# ///
```

### Key Documentation Links

- Reactivity: https://docs.marimo.io/guides/reactivity/
- UI Elements: https://docs.marimo.io/api/inputs/
- Scripts: https://docs.marimo.io/guides/scripts/
- Apps: https://docs.marimo.io/guides/apps/
