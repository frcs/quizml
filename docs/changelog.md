## Changelog 

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
