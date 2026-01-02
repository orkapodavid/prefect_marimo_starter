# Design: Fix Non-Compliant Skill Setup in .codex Directory

## Objective

Restructure three skills (`marimo`, `prefect`, and `prefect-marimo`) in the `.codex/skills/` directory to comply with the standard skill structure defined in `skill-development/SKILL.md`. The current files exist as flat markdown files instead of proper skill directories with YAML frontmatter.

## Problem Analysis

### Current State (Non-Compliant)

```
.codex/skills/
├── marimo.md                    ❌ Flat file, no SKILL.md, no frontmatter
├── prefect.md                   ❌ Flat file, no SKILL.md, no frontmatter
├── prefect-marimo.md            ❌ Flat file, no SKILL.md, no frontmatter
├── prefect-cli/                 ✅ Proper structure
│   └── SKILL.md
├── skill-development/           ✅ Proper structure
│   ├── SKILL.md
│   └── references/
└── uv-package-manager/          ✅ Proper structure
    └── SKILL.md
```

### Required Standard Structure

According to `skill-development/SKILL.md`, each skill must:

1. **Live in a subdirectory**: `skills/skill-name/`
2. **Contain SKILL.md file** with:
   - YAML frontmatter (name + description)
   - Markdown body in imperative/infinitive form
3. **Use third-person trigger descriptions**: "This skill should be used when the user asks to..."
4. **Include specific trigger phrases**: Concrete user queries that should activate the skill
5. **Keep SKILL.md lean**: 1,500-2,000 words ideal, <5k max
6. **Use progressive disclosure**: Move detailed content to `references/` subdirectory

### Violations Identified

| File | Issues |
|------|--------|
| `marimo.md` | No directory structure, no YAML frontmatter, no trigger description |
| `prefect.md` | No directory structure, no YAML frontmatter, no trigger description |
| `prefect-marimo.md` | No directory structure, no YAML frontmatter, no trigger description |

## Design Solution

### Target Structure

Transform the flat markdown files into proper skill directories:

```
.codex/skills/
├── marimo/
│   ├── SKILL.md
│   └── references/
│       └── api-reference.md
├── prefect/
│   ├── SKILL.md
│   └── references/
│       └── api-reference.md
└── prefect-marimo/
    ├── SKILL.md
    └── references/
        └── patterns.md
```

### Skill Directory Specifications

#### 1. Marimo Skill

**Purpose**: Provide guidance for working with Marimo reactive notebooks in Python

**Structure**:
```
marimo/
├── SKILL.md
└── references/
    └── api-reference.md
```

**SKILL.md Contents**:

| Section | Content | Word Target |
|---------|---------|-------------|
| Frontmatter | Name: "Marimo", Description with triggers | N/A |
| Core Concepts | Reactive notebooks, pure Python storage, execution modes | 300 words |
| App Structure | Basic notebook template pattern | 200 words |
| Key Patterns | @app.function, mode detection, UI elements, layout | 500 words |
| CLI Reference | Quick reference table | 100 words |
| Additional Resources | Pointer to references/api-reference.md | 50 words |

**Frontmatter Specification**:
- **name**: "Marimo"
- **description**: "This skill should be used when the user asks to 'create a marimo notebook', 'edit marimo app', 'convert Jupyter to marimo', 'add marimo widgets', 'use marimo UI elements', or mentions marimo reactive notebooks, mode detection, or marimo export functionality."
- **version**: "0.1.0"

**references/api-reference.md**:
- Detailed UI element documentation
- PEP 723 inline dependencies
- Advanced layout patterns
- Export options (HTML, WASM, etc.)
- Full documentation links

#### 2. Prefect Skill

**Purpose**: Provide guidance for working with Prefect 3.x orchestration framework

**Structure**:
```
prefect/
├── SKILL.md
└── references/
    └── api-reference.md
```

**SKILL.md Contents**:

| Section | Content | Word Target |
|---------|---------|-------------|
| Frontmatter | Name: "Prefect", Description with triggers | N/A |
| Core Concepts | Flows, tasks, basic patterns | 300 words |
| Deployment Patterns | prefect.yaml structure essentials | 200 words |
| Work Pools | Overview of pool types | 150 words |
| Blocks | Secret and configuration loading | 150 words |
| CLI Reference | Quick reference table | 100 words |
| Additional Resources | Pointer to references/api-reference.md | 50 words |

**Frontmatter Specification**:
- **name**: "Prefect"
- **description**: "This skill should be used when the user asks to 'create a prefect flow', 'add prefect task', 'deploy prefect workflow', 'configure prefect.yaml', 'set up work pool', 'use prefect blocks', or mentions Prefect orchestration, flow scheduling, or task retries."
- **version**: "0.1.0"

**references/api-reference.md**:
- Detailed task configuration options
- Advanced deployment patterns
- Work pool type specifications
- Block types and usage patterns
- Full documentation links

#### 3. Prefect-Marimo Skill

**Purpose**: Provide guidance for unified Prefect + Marimo notebook architecture

**Structure**:
```
prefect-marimo/
├── SKILL.md
└── references/
    └── patterns.md
```

**SKILL.md Contents**:

| Section | Content | Word Target |
|---------|---------|-------------|
| Frontmatter | Name: "Prefect-Marimo", Description with triggers | N/A |
| Architecture Overview | Unified notebook concept | 200 words |
| Core Pattern | Template with decorator stacking | 400 words |
| Deployment | prefect.yaml pointing to notebooks | 150 words |
| Key Rules | Critical rules (1-5) | 150 words |
| Additional Resources | Pointer to references/patterns.md | 50 words |

**Frontmatter Specification**:
- **name**: "Prefect-Marimo"
- **description**: "This skill should be used when the user asks to 'create a prefect marimo notebook', 'combine prefect with marimo', 'deploy marimo as prefect flow', 'stack decorators', 'use mode-conditional execution', or mentions unified Prefect-Marimo architecture, @app.function with @flow/@task decorators."
- **version**: "0.1.0"

**references/patterns.md**:
- Complete notebook template
- Advanced decorator stacking patterns
- Mode-conditional execution examples
- Common pitfalls and anti-patterns
- Integration with project structure (notebooks/ directory)

### Content Migration Strategy

#### From marimo.md → marimo/

| Source Section | Destination | Rationale |
|----------------|-------------|-----------|
| Core Concepts | SKILL.md | Essential understanding |
| App Structure (basic) | SKILL.md | Core pattern |
| Key Patterns (overview) | SKILL.md | Quick reference |
| CLI Reference | SKILL.md | Frequently needed |
| Detailed UI Elements | references/api-reference.md | Detailed content |
| PEP 723 Dependencies | references/api-reference.md | Implementation detail |
| Documentation Links | references/api-reference.md | Reference material |

#### From prefect.md → prefect/

| Source Section | Destination | Rationale |
|----------------|-------------|-----------|
| Core Concepts | SKILL.md | Essential understanding |
| Deployment Patterns (basic) | SKILL.md | Core pattern |
| Work Pools (overview) | SKILL.md | Quick reference |
| Blocks (basic) | SKILL.md | Common usage |
| CLI Reference | SKILL.md | Frequently needed |
| Advanced task configs | references/api-reference.md | Detailed content |
| Advanced deployment patterns | references/api-reference.md | Implementation detail |
| Documentation Links | references/api-reference.md | Reference material |

#### From prefect-marimo.md → prefect-marimo/

| Source Section | Destination | Rationale |
|----------------|-------------|-----------|
| Architecture | SKILL.md | Essential understanding |
| Core Pattern | SKILL.md | Core pattern |
| Deployment | SKILL.md | Critical integration |
| Key Rules | SKILL.md | Must-know constraints |
| Complete template | references/patterns.md | Detailed example |
| Anti-patterns | references/patterns.md | Troubleshooting |

### Writing Style Requirements

All SKILL.md content must follow these rules:

1. **Imperative/Infinitive Form**: Use verb-first instructions
   - ✅ "Create a flow by defining the function"
   - ❌ "You should create a flow by defining the function"

2. **Third-Person in Description**: Frontmatter uses third person
   - ✅ "This skill should be used when the user asks to..."
   - ❌ "Use this skill when you want to..."

3. **Objective, Instructional Language**: Focus on what to do
   - ✅ "Define the flow decorator with parameters"
   - ❌ "You can define the flow decorator"

4. **Specific Trigger Phrases**: Include concrete user queries in description
   - ✅ "'create a marimo notebook', 'add widgets', 'convert Jupyter'"
   - ❌ "working with notebooks"

### File Operations

#### Phase 1: Create New Skill Directories

1. Create directory structure for each skill:
   - `mkdir .codex/skills/marimo/`
   - `mkdir .codex/skills/marimo/references/`
   - `mkdir .codex/skills/prefect/`
   - `mkdir .codex/skills/prefect/references/`
   - `mkdir .codex/skills/prefect-marimo/`
   - `mkdir .codex/skills/prefect-marimo/references/`

#### Phase 2: Create SKILL.md Files

2. Create compliant SKILL.md for each skill:
   - `marimo/SKILL.md` with YAML frontmatter + lean body (800-1000 words)
   - `prefect/SKILL.md` with YAML frontmatter + lean body (800-1000 words)
   - `prefect-marimo/SKILL.md` with YAML frontmatter + lean body (800-1000 words)

#### Phase 3: Create Reference Files

3. Create references/ files with detailed content:
   - `marimo/references/api-reference.md`
   - `prefect/references/api-reference.md`
   - `prefect-marimo/references/patterns.md`

#### Phase 4: Remove Old Files

4. Delete non-compliant flat files:
   - Remove `.codex/skills/marimo.md`
   - Remove `.codex/skills/prefect.md`
   - Remove `.codex/skills/prefect-marimo.md`

### Content Distribution Guidelines

#### SKILL.md Body (Keep Lean)

**Include**:
- Core concepts overview
- Essential procedures
- Quick reference tables
- Pointers to references/
- Most common use cases

**Target**: 800-1,000 words for these skills (they are focused and technical)

#### references/ Files

**Include**:
- Detailed API documentation
- Complete code templates
- Advanced patterns
- Troubleshooting guides
- External documentation links

**Target**: Unlimited (2,000-3,000 words typical)

## Progressive Disclosure Benefits

### Before (Current)

- All content loaded when skill triggers
- No distinction between essential and detailed information
- No discovery mechanism for Claude to load skills

### After (Compliant)

1. **Metadata Level** (Always in context): Name + description (~100 words)
   - Claude can determine if skill is relevant without loading content

2. **SKILL.md Level** (Loaded when triggered): Core essentials (~800-1000 words)
   - Provides enough information for common tasks
   - Points to references for details

3. **References Level** (Loaded as needed): Detailed content (2,000-3,000 words)
   - Claude loads only when needed for complex tasks
   - Doesn't bloat context for simple queries

## Validation Criteria

### Structure Validation

- [ ] Each skill exists as subdirectory in `.codex/skills/`
- [ ] Each subdirectory contains `SKILL.md` file
- [ ] Referenced `references/` directories exist
- [ ] Referenced files exist in `references/`

### SKILL.md Validation

- [ ] YAML frontmatter present with `---` delimiters
- [ ] Frontmatter contains `name` field
- [ ] Frontmatter contains `description` field
- [ ] Frontmatter contains `version` field
- [ ] Description uses third-person format
- [ ] Description includes specific trigger phrases
- [ ] Body uses imperative/infinitive form (not second person)
- [ ] Body is focused and lean (800-1,000 words for these skills)
- [ ] Body references supporting files clearly

### Content Quality Validation

- [ ] Core concepts are clear and concise
- [ ] Essential patterns are included in SKILL.md
- [ ] Detailed content moved to references/
- [ ] No duplication between SKILL.md and references/
- [ ] External links preserved in references/

### Progressive Disclosure Validation

- [ ] SKILL.md provides actionable guidance for common tasks
- [ ] References contain detailed information for complex tasks
- [ ] Clear pointers from SKILL.md to references/
- [ ] Information hierarchy is logical

## Implementation Notes

### Consistency with Existing Skills

The three compliant skills in the repository serve as templates:

1. **prefect-cli/**: Demonstrates lean SKILL.md with clear triggers
2. **skill-development/**: Shows proper use of references/ subdirectory
3. **uv-package-manager/**: Example of comprehensive single-file skill

The new structure should match the patterns used in these existing skills.

### Integration with Project

These skills are project-specific and should reference:
- Project structure (`notebooks/`, `src/`, etc.)
- AGENTS.md conventions
- Project-specific patterns (decorator stacking, mode-conditional execution)

### No Code in Design

This design document contains:
- Natural language descriptions
- Structured tables
- Directory structure diagrams
- File operation specifications

Implementation will create actual SKILL.md files with YAML frontmatter and markdown content following these specifications.

## Success Criteria

### Functional Success

1. Claude Code can discover all three skills via auto-discovery
2. Skills trigger on appropriate user queries (as defined in descriptions)
3. SKILL.md provides sufficient guidance for common tasks
4. References files load when Claude needs detailed information

### Structural Success

1. All skills follow standard directory structure
2. All SKILL.md files have valid YAML frontmatter
3. All content uses correct writing style (imperative form)
4. Progressive disclosure is properly implemented

### Quality Success

1. No information loss from original flat files
2. Content is appropriately distributed (lean SKILL.md, detailed references/)
3. Trigger descriptions are specific and actionable
4. Skills integrate with project patterns (AGENTS.md, notebooks/, etc.)

## Risk Mitigation

### Risk: Information Loss

**Mitigation**: Carefully map all content from flat files to new structure. Verify completeness before deleting old files.

### Risk: Incorrect Trigger Phrases

**Mitigation**: Base trigger phrases on actual user queries and project patterns documented in AGENTS.md.

### Risk: Content Distribution Unclear

**Mitigation**: Use word count targets and content type guidelines to determine SKILL.md vs references/ placement.

### Risk: Writing Style Inconsistency

**Mitigation**: Review all content against writing style checklist before finalizing. Use existing compliant skills as examples.
