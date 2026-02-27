# QuizML Project Context for LLMs

## Project Overview
QuizML is a command-line tool designed to convert quiz questions written in YAML/Markdown into various formats, specifically for Blackboard tests (CSV), LaTeX exam source files, HTML, and Word documents. It allows for the generation of multiple render targets from a single source of truth.

## Core Philosophy
- **Lean Mechanism:** Keep the central logic minimal.
- **Extensibility:** Allow users to extend functionality through custom templates and user-defined YAML structures.
- **Modularity:** Prefer a modular architecture.

## Technical Stack
- **Language:** Python (>=3.11).
- **Package Manager:** `uv` (mandatory for all environment and dependency management).
- **Configuration/Input:** YAML (via `ruamel.yaml`), Markdown (via `mistletoe`).
- **Templating:** Jinja2 (custom delimiters, see below).
- **CLI:** `rich` for formatted output.
- **Document Processing:** `docxtpl` for Word docs, `latex2mathml` for math conversion.
- **Testing:** `pytest`.

## Python Workflow (uv)
Do NOT use `python` or `pip` directly.
- **Run tests:** `uv run pytest`
- **Run tool:** `uv run quizml quiz1.yaml`
- **Add dependency:** `uv add <package>`
- **Remove dependency:** `uv remove <package>`

## Project Structure
- `src/quizml/`: Core package source code.
    - `cli/`: Command-line interface logic using `argparse` and `rich`.
    - `markdown/`: Custom Markdown extensions and renderers (HTML, LaTeX).
    - `templates/`: Jinja2 templates for output formats (Blackboard, LaTeX, HTML, etc.).
    - `loader.py`: Handles loading and parsing of YAML files.
    - `renderer.py`: Orchestrates the rendering process using Jinja2.
- `docs/`: Project documentation (served via GitHub Pages using Docsify).
- `examples/`: Example quiz files (`quiz1.yaml`) and figures.
- `tests/`: Unit and integration tests.

## Key Conventions

### Question Types
Supported types: `essay`, `tf` (True/False), `mc` (Multiple Choice), `ma` (Multiple Answers), `matching`, `ordering` (Note: removed in Blackboard Ultra), `fill` (Fill in the Blank), `mfill` (Fill in Multiple Blanks), `num` (Calculated Numeric).

### Jinja2 Templates
Custom delimiters are used to avoid conflicts with LaTeX:
- **Block:** `<| ... |>`
- **Variable:** `<< ... >>`
- **Comment:** `<# ... #>`

### Git Strategy & Commit Messages
- **Strategy:** GitHub Flow. Use feature branches and PRs. Stable code resides on `main`.
- **Versioning:** Semantic Versioning (SemVer) with Git tags (e.g., `v0.10.0`).
- **Format:** `Type: Subject` (e.g., `Feat: Adding --target-list as feature`)
- **Types:** `Feat`, `Fix`, `Docs`, `Refactor`, `Chore`, `Test`, `Style`.

### Testing
Always run the full suite with `uv run pytest` before submitting changes.

### External Dependencies
Assumes the presence of a LaTeX installation (TeXLive/MacTeX) with tools like `gs`, `dvisvgm`, `dvipdfmx`, etc. for certain targets.

## Usage
Basic command:
```bash
uv run quizml quiz1.yaml
```
Common features:
- `--format`: Formats and renumbers questions in the YAML file.
- `-w`, `--watch`: Continuously compiles on file change.
- `--build`: Compiles all targets and runs post-compilation commands.
