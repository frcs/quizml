# QuizML Project Context for LLMs

## Project Overview
QuizML is a command-line tool designed to convert quiz questions written in YAML/Markdown into various formats, specifically for Blackboard tests (CSV) and LaTeX exam source files. It allows for the generation of multiple render targets from a single source of truth.

## Core Philosophy
- **Lean Mechanism:** Keep the central logic minimal.
- **Extensibility:** Allow users to extend functionality through custom templates and user-defined YAML structures.
- **Modularity:** Prefer a modular architecture.

## Technical Stack
- **Language:** Python (>=3.8, specific dev preference for 3.9 via macports).
- **Configuration/Input:** YAML (via `ruamel.yaml`), Markdown (via `mistletoe`).
- **Templating:** Jinja2 (custom delimiters, see below).
- **CLI:** `rich` for formatted output.
- **Document Processing:** `docxtpl` for Word docs, `latex2mathml` for math conversion.
- **Testing:** `pytest`.

## Project Structure
- `src/quizml/`: Core package source code.
    - `cli/`: Command-line interface logic using `argparse` and `rich`.
    - `markdown/`: Custom Markdown extensions and renderers (HTML, LaTeX).
    - `templates/`: Jinja2 templates for output formats (Blackboard, LaTeX, HTML, etc.).
    - `loader.py`: Handles loading and parsing of YAML files.
    - `renderer.py`: Orchestrates the rendering process using Jinja2.
- `docs/`: Project documentation (served via GitHub Pages).
- `examples/`: Example quiz files (`quiz1.yaml`) and figures.
- `tests/`: Unit and integration tests.

## Key Conventions

### Jinja2 Templates
Custom delimiters are used to avoid conflicts with LaTeX:
- **Block:** `<| ... |>`
- **Variable:** `<< ... >>`
- **Comment:** `<# ... #>`

### Git Commit Messages
Format: `Type: Subject`
Types:
- `Feat`: New features
- `Fix`: Bug fixes
- `Docs`: Documentation changes
- `Refactor`: Code refactoring
- `Chore`: Maintenance tasks
- `Test`: Adding or updating tests
- `Style`: Formatting changes

### Testing
Run the full suite before submitting changes:
```bash
pytest .
```

### External Dependencies
The system assumes the presence of a LaTeX installation (TeXLive/MacTeX) with tools like `gs`, `dvisvgm`, `dvipdfmx`, etc.

## Usage
Basic command:
```bash
quizml quiz1.yaml
```
This generates:
- Blackboard CSV
- HTML preview
- LaTeX source (and compiles it if configured)
