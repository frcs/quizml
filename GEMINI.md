# Gemini Agent Context

This document provides context and instructions for the Gemini agent working on the QuizML project.

## Project Overview
QuizML is a command-line tool for converting quiz questions (YAML/Markdown) into Blackboard tests (CSV) or LaTeX exam source files. The goal is to keep the core mechanism lean while allowing extensibility through templates.

## Operational Rules

### 1. Preflight Checks
Before submitting any changes, you **must** validate them by running the full test suite:
```bash
pytest .
```

### 2. Python Environment
**Do not** use the default `python` or `python3` commands. Use the specific MacPorts installation:
- Path: `/opt/local/bin/python3.9`

### 3. Documentation
- When modifying the CLI, update `docs/usage.md` with accurate arguments and descriptions.

### 4. Git Conventions
- **Main Branch:** `main`
- **Commit Messages:** Use the "Type: Subject" format.
  - Types: `Feat`, `Fix`, `Docs`, `Refactor`, `Chore`, `Test`, `Style`.
  - Example: `Feat: Adding --target-list as feature`

### 5. Comments Policy
- Write high-value comments only.
- Focus on *why*, not *what*.
- Do not address the user through code comments.

## Technical Context

### Jinja2 Configuration
Custom delimiters are used to avoid conflicts with LaTeX:
- **Block:** `<| ... |>`
- **Variable:** `<< ... >>`
- **Comment:** `<# ... #>`

### Project Structure
- `src/quizml/`: Core source code.
- `src/quizml/templates/`: Jinja2 templates (e.g., `blackboard.txt.j2`, `tcd-exam.tex.j2`).
- `tests/`: Unit tests.

### Dependencies
- **Internal:** `ruamel.yaml`, `rich`, `jinja2`, `docxtpl`, `latex2mathml`, `mistletoe`.
- **External:** Requires a LaTeX installation (TeXLive/MacTeX) with `gs`, `dvisvgm`, `dvipdfmx`.

## General Requirements
- If requirements are ambiguous, ask the user for clarification before assuming.
- Prefer modular architecture changes.