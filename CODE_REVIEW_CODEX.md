# QuizML Code Review

**Reviewed:** 2026-10-17  
**Revision:** `9c975dc` (`Fix package docs and config metadata`)  
**Scope:** Fresh review of the current repository state, covering CLI commands, YAML loading and sampling, target selection and builds, cleanup, Markdown rendering, caching, documentation, packaging, and the related project documentation.

## Summary

The codebase has a clear separation between loading, transcoding, rendering, and CLI orchestration. Target aliases/dependencies, explicit sampling, and output cleanup are documented and largely align with the implementation. I found two actionable issues, both in configuration handling. No source-code changes were made as part of this review.

## Findings

### 1. [P2] Missing target dependencies are silently omitted

**Location:** [`src/quizml/cli/config.py:131-139`](src/quizml/cli/config.py)

When constructing the dependency graph, dependencies are filtered to names that already exist in `target_by_name`. A misspelled or removed dependency therefore disappears from the graph instead of producing a configuration error. For example, if target `pdf` declares `dep: latexx`, selecting `pdf` leaves only `pdf` in the ordered target list. A render target may then run without its required output. A build-command target instead reaches the dependency-success check and fails without explaining that the dependency name is invalid.

Validate every declared dependency against all configured target names before filtering to the selected targets, and report the target and unknown dependency in a `QuizMLConfigError`. Add coverage for both a missing dependency in a selected target and one reached through an alias.

### 2. [P2] Valid YAML with an invalid config shape causes an unhandled exception

**Location:** [`src/quizml/cli/config.py:29-37`](src/quizml/cli/config.py)

The YAML parser errors are translated into `QuizMLConfigError`, but the parsed value is assumed to be a mapping. A config containing a valid YAML scalar, list, or `null` reaches `config["yaml_filename"] = ...` and raises `TypeError` instead. The CLI catches `QuizMLError`, not `TypeError`, so users see a traceback rather than a configuration diagnostic. File-open errors such as permission failures also bypass this conversion.

Check that the parsed config is a mapping before adding runtime fields, and translate config-file read errors into `QuizMLConfigError` with the config path. Include cases for `null`, a list, and an unreadable file in config-loading coverage.

## Follow-up

Both findings were addressed after the static review: dependency names are now checked against the full configured target set, and config reads/root values produce `QuizMLConfigError` diagnostics. Regression coverage was added for direct and aliased target selection, non-mapping YAML roots, and config read failures.

- `uv run pytest`: **170 passed, 1 skipped**.
- `uv run ruff check .`: **passed**.

## Review notes

- I inspected the current CLI and supporting modules, target and schema configuration, templates, tests, and user documentation.
- The review itself was static; the follow-up fixes were verified with the checks above.
- The requested prior review files were removed. `CODE_REVIEW.md` is a tracked deletion; `CODE_REVIEW.md.bak` was also removed. This review is saved separately in `CODE_REVIEW_CODEX.md`.
