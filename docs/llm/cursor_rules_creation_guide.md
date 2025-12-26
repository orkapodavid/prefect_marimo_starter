# Guide: Creating Cursor IDE Rule Files

This guide explains how to generate well-structured `.mdc` (Markdown Components) rule files that provide persistent context and guidelines to Cursor's AI assistant.

## Rule File System

### File Format Structure

Every `.mdc` rule file must follow this structure:

```markdown
---
description: Brief description of what this rule does (required)
globs: pattern/to/match/**/*.ts (optional, gitignore-style patterns)
alwaysApply: false (optional, default: false)
---

# Rule Title

Main rule content written in clear, actionable markdown.
Use specific instructions, examples, and constraints.
```

### Critical Requirements

1. **Location**: All project rules MUST be in `.cursor/rules/` directory.
   ```
   PROJECT_ROOT/
   ├── .cursor/
   │   └── rules/
   │       ├── code-style.mdc
   │       ├── testing.mdc
   │       └── component-patterns.mdc
   ```

2. **Naming Convention**: Use kebab-case with `.mdc` extension.
   - ✅ `python-best-practices.mdc`
   - ✅ `react-component-rules.mdc`
   - ❌ `PythonRules.mdc`
   - ❌ `react_rules.md`

3. **YAML Frontmatter Fields**:
   - `description`: (Required) Short, clear description of the rule's purpose.
   - `globs`: (Optional) File pattern matching (e.g., `**/*.py`, `src/components/**/*`).
   - `alwaysApply`: (Optional) Set to `true` for rules that should always be included.

### Rule Types and Scopes

1. **Global Rules (User Rules)**
   - Location: Cursor Settings → Rules → User Rules
   - Format: Plain text (MDC format NOT supported)
   - Scope: Apply to all projects across all workspaces

2. **Project Rules (Recommended)**
   - Location: `.cursor/rules/*.mdc`
   - Format: MDC with YAML frontmatter
   - Scope: Specific to the current project
   - Use for: Project-specific conventions, tech stack guidelines

3. **Path-Specific Rules**
   - Use `globs` field to target specific files/directories (e.g., `globs: **/*.test.ts`)
   - Auto-attached when matching files are referenced

### Best Practices

1. **Be Specific and Actionable**
   ```markdown
   ❌ "Write good code"
   ✅ "Use type hints for all function parameters and return types"
   ```

2. **Keep Rules Concise**
   - Limit to under 500 lines.
   - One focused purpose per rule file.
   - Break complex standards into multiple focused rules.

3. **Include Examples** (Do's and Don'ts)
   ```markdown
   ## Example
   ```python
   # ✅ Correct
   def fetch_data(id: str) -> dict: ...
   
   # ❌ Avoid
   def fetch_data(id): ...
   ```
   ```

4. **Use Clear Structure**
   - Headers for organization
   - Lists for multiple requirements
   - Code blocks for examples

### Template: Comprehensive .mdc Rule File

```markdown
---
description: TypeScript coding standards for React components
globs: src/components/**/*.tsx
alwaysApply: false
---

# React Component Standards

## Component Structure

- Always use functional components with hooks
- Export components as named exports, not default

## Type Safety

- Define explicit types for all props using `interface`
- Avoid `any` type - use `unknown` if type is truly unknown

## Example

```typescript
// ✅ Correct Pattern
interface ButtonProps {
  label: string;
  onClick: () => void;
}

export function Button({ label, onClick }: ButtonProps) {
  return <button onClick={onClick}>{label}</button>;
}
```
```

## Creating New Rules

When creating a new Cursor rule file:
1. Identify the rule's purpose and scope.
2. Choose appropriate glob patterns (if any).
3. Structure content with clear headers and examples.
4. Include both positive (DO) and negative (DON'T) guidance.
5. Keep language concise and directive.
6. Save as `.mdc` in `.cursor/rules/`.
