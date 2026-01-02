# Marimo API Reference

This document provides detailed information about Marimo's UI elements, PEP 723 dependencies, advanced patterns, and export functionality.

## UI Elements Reference

### Input Widgets

**Text Input**:
```python
text = mo.ui.text(
    value="",           # Default value
    label="Enter text", # Label displayed above
    placeholder="...",  # Placeholder text
    max_length=100,     # Maximum character length
    disabled=False      # Whether input is disabled
)
```

**Number Input**:
```python
number = mo.ui.number(
    start=0,           # Minimum value
    stop=100,          # Maximum value
    value=50,          # Default value
    step=1,            # Increment step
    label="Number"     # Label displayed above
)
```

**Slider**:
```python
slider = mo.ui.slider(
    start=0,           # Minimum value
    stop=100,          # Maximum value
    value=50,          # Default value
    step=1,            # Increment step
    label="Adjust",    # Label displayed above
    show_value=True    # Show current value
)
```

**Range Slider**:
```python
range_slider = mo.ui.range_slider(
    start=0,
    stop=100,
    value=(25, 75),    # Tuple for range
    step=1
)
```

**Checkbox**:
```python
checkbox = mo.ui.checkbox(
    value=False,       # Default checked state
    label="Enable feature"
)
```

**Switch**:
```python
switch = mo.ui.switch(
    value=False,
    label="Toggle"
)
```

**Dropdown**:
```python
dropdown = mo.ui.dropdown(
    options=["option1", "option2", "option3"],
    value="option1",   # Default selection
    label="Choose"
)

# With custom labels
dropdown = mo.ui.dropdown(
    options={
        "opt1": "Display Label 1",
        "opt2": "Display Label 2"
    }
)
```

**Radio Buttons**:
```python
radio = mo.ui.radio(
    options=["A", "B", "C"],
    value="A",
    label="Select one"
)
```

**Multiselect**:
```python
multiselect = mo.ui.multiselect(
    options=["tag1", "tag2", "tag3"],
    value=["tag1"],    # Default selections
    label="Select multiple"
)
```

**Date Picker**:
```python
date = mo.ui.date(
    value="2024-01-01",
    label="Pick date"
)
```

**File Upload**:
```python
file = mo.ui.file(
    filetypes=[".csv", ".json"],  # Allowed file types
    multiple=False,               # Allow multiple files
    label="Upload file"
)

# Access uploaded file
if file.value:
    content = file.contents()  # File contents as bytes
    name = file.name()         # File name
```

**Button**:
```python
button = mo.ui.button(
    value=0,           # Counter increments on click
    label="Click me",
    on_click=lambda: print("Clicked!")
)
```

**Run Button**:
```python
run_btn = mo.ui.run_button(
    label="Execute"
)

# Check if button was clicked
if run_btn.value:
    # Execute code
    pass
```

### Data Display Widgets

**Table**:
```python
table = mo.ui.table(
    df,                # Pandas or Polars DataFrame
    selection="multi", # "single", "multi", or None
    page_size=10,      # Rows per page
    show_column_summaries=True
)

# Get selected rows
selected = table.value
```

**DataFrame**:
```python
# Display non-interactive DataFrame
mo.ui.dataframe(df)
```

**Altair Chart**:
```python
import altair as alt

chart = alt.Chart(df).mark_bar().encode(
    x='category',
    y='value'
)

mo.ui.altair_chart(chart)
```

**Plotly Chart**:
```python
import plotly.express as px

fig = px.scatter(df, x='x', y='y')
mo.ui.plotly(fig)
```

### Layout Components

**Vertical Stack**:
```python
mo.vstack([
    widget1,
    widget2,
    widget3
], align="start")  # "start", "center", "end", "stretch"
```

**Horizontal Stack**:
```python
mo.hstack([
    left_widget,
    right_widget
], justify="space-between")  # "start", "center", "end", "space-between", "space-around"
```

**Tabs**:
```python
mo.tabs({
    "Tab 1": content1,
    "Tab 2": content2,
    "Tab 3": content3
})
```

**Accordion**:
```python
mo.accordion({
    "Section 1": content1,
    "Section 2": content2
})
```

**Callout**:
```python
mo.callout(
    content,
    kind="info"  # "info", "warn", "danger", "success", "neutral"
)
```

**Markdown**:
```python
mo.md("""
# Header
**Bold text** and *italic text*

```python
code_block()
```
""")
```

## PEP 723 Inline Dependencies

Marimo notebooks support PEP 723 inline script metadata for dependency management:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "pandas>=2.0.0",
#     "polars>=1.0.0",
#     "altair>=5.0.0",
#     "plotly>=5.0.0",
#     "requests>=2.31.0",
# ]
# ///

import marimo
# ... rest of notebook
```

**Key Points**:
- Must be at the very top of the file
- Uses TOML format within comments
- Automatically recognized by tools like `uv` and `pip`
- Enables reproducible notebook execution

## Advanced Patterns

### State Management

```python
# Create stateful value
state = mo.state(initial_value=0)

# Update state
def increment():
    state.value += 1

button = mo.ui.button(
    label="Increment",
    on_click=increment
)
```

### Dynamic UI

```python
@app.cell
def _(mo):
    selection = mo.ui.dropdown(options=["chart", "table"])
    return (selection,)

@app.cell
def _(mo, selection):
    if selection.value == "chart":
        display = mo.ui.altair_chart(create_chart())
    else:
        display = mo.ui.table(create_table())
    display
    return
```

### Form Groups

```python
form = mo.ui.form({
    "name": mo.ui.text(label="Name"),
    "age": mo.ui.number(start=0, stop=120, label="Age"),
    "email": mo.ui.text(label="Email")
})

# Access form values
if form.value:
    name = form.value["name"]
    age = form.value["age"]
```

### Batch Updates

```python
# Create multiple widgets
sliders = mo.ui.array([
    mo.ui.slider(0, 100) for _ in range(5)
])

# Access values
values = [s.value for s in sliders.elements]
```

## Export Options

### Export to HTML

```bash
marimo export html notebook.py -o output.html
```

**Options**:
- `--no-include-code` - Exclude code cells from output
- `--watch` - Watch for changes and rebuild

### Export to Script

```bash
marimo export script notebook.py -o script.py
```

Converts interactive notebook to pure Python script.

### Export to WASM

```bash
marimo export html notebook.py --mode wasm -o output.html
```

Creates standalone HTML with WebAssembly Python runtime (runs offline in browser).

### Export to Markdown

```bash
marimo export md notebook.py -o output.md
```

## Documentation Links

- **Official Docs**: https://docs.marimo.io/
- **Reactivity Guide**: https://docs.marimo.io/guides/reactivity/
- **UI Elements**: https://docs.marimo.io/api/inputs/
- **Layouts**: https://docs.marimo.io/api/layouts/
- **Scripts Guide**: https://docs.marimo.io/guides/scripts/
- **Apps Guide**: https://docs.marimo.io/guides/apps/
- **GitHub**: https://github.com/marimo-team/marimo
- **Discord Community**: https://discord.gg/JE7nhX6mD8
