# Agent guide

This file contains shared project guidance for all coding agents.

## Project

QuizML converts quizzes written in YAML and Markdown into configured outputs
such as Blackboard imports, HTML previews, LaTeX sources, PDFs, and Word
documents. Keep the core focused and let users customize outputs through
`quizml.cfg`, schemas, and templates.

Useful references:

- [Architecture](ARCHITECTURE.md) describes the code and data flow.
- [Development guide](DEVELOPMENT.md) covers project conventions and releases.
- [Command-line usage](docs/usage.md) documents the CLI.
- [Configuration guide](docs/configuration.md) explains target configuration.

## Working in the repository

- Inspect the relevant code and current Git changes before editing. Preserve
  unrelated user changes.
- Prefer small changes that fit the existing architecture. Keep comments
  focused on why a non-obvious choice is needed.
- When changing the CLI or configuration, update the related documentation.
- Resolve routine implementation choices from the code and documentation. Ask
  only when a missing decision blocks meaningful progress.
- Follow the active task's instructions about tests and other checks. Report
  exactly what you ran.
- Do not commit or push unless the user asks, and always present changes and
  the proposed commit message for approval first.
- Keep Git commits atomic and focused on a single logical concern.
- Write detailed, self-contained multi-line Git commit messages that explain
  the problem or root cause, the motivation/impact, and the specific technical
  solution. Never rely on external or temporary files to explain the context of
  a commit.
- Record codebase reviews, multi-stage implementation plans, rejected
  alternatives, and session notes in `.devlog/` (`reviews/`, `plans/`,
  `decisions/`, and `journal.md`), which is git-ignored in the main repository
  and tracked as its own private Git repository. Distill lasting architectural
  invariants into [ARCHITECTURE.md](ARCHITECTURE.md).

## Python workflow

The package supports Python 3.10 and newer. Use `uv` for the project
environment and dependencies:

```bash
uv run quizml quiz.yaml
uv run pytest
uv run ruff check .
uv add <package>
uv remove <package>
```

## Technical notes

- Templates use Jinja2 delimiters that avoid common LaTeX syntax:
  - Blocks: `<| ... |>`
  - Expressions: `<< ... >>`
  - Comments: `<# ... #>`
- The bundled schema controls question types, field validation, and type
  coercion. Custom schemas can extend question data.
- LaTeX, Ghostscript, `dvisvgm`, and other external renderers are needed only
  for output paths that use them.
