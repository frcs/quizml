# Development

QuizML aims to keep its core conversion pipeline small and let users adapt
schemas, targets, and templates to their needs.

## Project checks

Use `uv` to run the application and manage dependencies:

```bash
uv run quizml quiz.yaml
uv run pytest
uv run ruff check .
```

When changing behavior, update the relevant documentation. Add tests when the
task calls for test coverage, and follow its instructions about which checks to
run. Report the checks you performed.

## Git conventions

- Keep commits focused on one logical change.
- Use `Type: Subject` commit messages. Common types are `Feat`, `Fix`, `Docs`,
  `Refactor`, `Chore`, `Test`, `Style`, and `Perf`.
- For substantial changes, describe the problem, solution, and impact in the
  commit body.
- Commit and push only when requested.

## Releases

Versions are generated from Git tags with `setuptools_scm`. To prepare a
release:

1. Move the relevant entries from `[Unreleased]` in `docs/changelog.md` into a
   dated version section.
2. Commit the changelog update.
3. Tag the release, for example `git tag v0.12.0`.
4. Push the commit and tag. The publish workflow builds the package and
   publishes it to PyPI using Trusted Publishing.
