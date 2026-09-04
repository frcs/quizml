# Changelog

## [Unreleased]

<a name="0.12.0"></a>

### [0.12.0]() (2026-09-03)

**Refactors:**
*   Replaced shadow document concatenation with a discrete AST parsing pipeline in `MarkdownTranscoder`, fixing heading truncation in question statements.
*   Made `MathDisplay` stateless, removing mutable class-level parsing variables.
*   Implemented document-relative asset resolution, enabling exams with relative figures to compile accurately from any directory.
*   Implemented topological sorting (`graphlib.TopologicalSorter`) for target dependencies, ensuring dependencies always build before dependents and detecting circular dependencies.
*   Made `FileLocator` dynamic and context-aware, preventing stale CWD paths and providing informative missing-file errors.
*   Cached configured `jinja2.Environment` in `renderer.py` to eliminate redundant environment re-creations.
*   Removed obsolete code (~400 lines), dead functions (`_parse_yaml_fragment`, `print_doc`), and unused schema parameters.
*   Deduplicated template initialization logic in `quizml.cli.init`.

**Fixes:**
*   Fixed single-line `MathDisplay` block equations (`$$E=mc^2$$`) greedily consuming subsequent paragraphs.
*   Restricted `quizml --cleanup` strictly to known targets and LaTeX build artifacts, and enabled targeted cleanup for specific YAML files or directories.
*   Fixed tuple unpacking on `load()` in the `quizml --diff` CLI command.
*   Prevented process CWD mutation and tempdir leaks in `embed_pdf`.
*   Supported `viewBox`-only SVG dimensions and SVGs with `height` before `width`.
*   Replaced regex document splitting with native `yaml.load_all()` in loader and formatter, allowing Markdown horizontal rules (`---`) in question bodies.
*   Enforced explicit `encoding="utf-8"` across all file reading and writing operations for reliable cross-platform execution on Windows.
*   Resolved all codebase lint and style warnings and transitioned tests to `tmp_path` fixtures.


<a name="0.11.0"></a>

### [0.11.0]() (2026-07-18)

**Features:**
*   Implemented 80-column text wrapping for paragraph lines in `quizml --format`.

**Refactors:**
*   Converted versioning to use `setuptools_scm` for dynamic version strings.
*   Automated PyPI publishing via GitHub Actions.


<a name="0.10.0"></a>

### [0.10.0]() (2026-01-16)

This release marks a major milestone for `quizml`, with a wide range of improvements across features, stability, and developer experience.

**Features:**
*   Implemented side-by-side figure layout using 'figure-split'.
*   Added `--info` command to output configuration details as JSON.
*   Allowed defining default targets in configuration.
*   Added support for Jinja templates in Word documents (docxtpl).
*   Implemented fuzzy matching in diff.
*   Implemented persistent equation caching to speed up compilation.
*   Added built-in LiveReload server for auto-refreshing HTML previews.
*   Implemented schema-guided type coercion in YAML loader.

**Fixes:**
*   Improved side figure implementation for MA/MC in the HTML preview.
*   Improved side figure implementation for MA/MC in tcd-eleceng-latex template.
*   Refined LaTeX template and restored OMR glyph spacing.
*   Ensured logging configuration is applied correctly.
*   Improved watch mode and Ctrl-C handling.
*   Improved image path resolution for LaTeX with format fallback.

**Refactors:**
*   Replaced `pyyaml` with `ruamel.yaml` for consistency.
*   Added Ruff for linting and fixed all Ruff errors.
*   Renamed template assets for clarity and consistency.
*   Removed redundant `--print-package-templates-path` argument.
*   Split `compile.py`.
*   Lazy loaded CLI subcommands to improve startup time.
*   Template logic and renderer improvements.
*   Improved YAML loading and aligned types in tests/templates.
*   Changed codebase structure.

**Docs:**
*   Updated documentation, including adding a page on custom schema validation and question layout.
*   Updated `usage.md` with latest CLI arguments.
*   Updated README.md.
*   Updated style CSS and docs text.
*   Added Jinja syntax highlighting to the documentation.

<a name="0.9"></a>

### [0.9]() (2025-12-25)

* **Fix:** Improved image path resolution for LaTeX. It now prioritizes existing PDF, PNG, or JPG files before attempting SVG conversion. This makes external tools like `rsvg-convert` or `inkscape` optional if compatible image formats are present.
* **Fix:** Correctly exposed `main` entry point, fixing `python -m quizml` usage.
* **Refactor:** Improved YAML loading and type alignment in tests/templates.

<a name="0.8"></a>

### [0.8]() (2025-12-16)

Rename from `bbquiz` to `quizml`


<a name="0.7"></a>

### [0.7]() (2025-12-11)

Migration from strictyaml to ruamel. Also, we now have with user-definable
schema using jsonschema.

* more consistent and better consistency with error reporting
* slightly better testing
* more CLI arguments, with `-t` 


<a name="0.6"></a>

### [0.6]() (2025-02-08)

new MCQ syntax with `-x:` and `-o:` style.

<a name="0.5"></a>

### [0.5]() (2025-01-10)

first release
