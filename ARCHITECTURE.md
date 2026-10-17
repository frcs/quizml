# Architecture

QuizML turns a YAML quiz into one or more configured outputs. The CLI loads the
configuration and quiz, prepares Markdown for each selected target, renders its
template, and optionally runs configured build commands.

```mermaid
flowchart LR
    CLI[CLI] --> Config[Configuration and target selection]
    CLI --> Loader[YAML loader]
    Config --> Targets[Selected targets and dependencies]
    Loader --> Data[Header, questions, and paths]
    Data --> Markdown[Markdown transcoder]
    Targets --> Markdown
    Markdown --> Renderer[Template renderer]
    Renderer --> Output[Rendered files]
    Targets --> Build[Optional build commands]
    Output --> Build
    Build --> Artifact[Built artifacts, such as PDFs]
```

## Main components

| Component | Responsibility |
| --- | --- |
| `quizml.cli.cli` | Defines the command line and dispatches subcommands. |
| `quizml.cli.config` | Loads `quizml.cfg`, expands target aliases and dependencies, and resolves target settings. |
| `quizml.cli.filelocator` | Finds configuration, schema, template, and supporting files across local, user, and package paths. |
| `quizml.loader` | Reads YAML documents, resolves question includes, validates data against a JSON Schema, and coerces values according to that schema. |
| `quizml.markdown.markdown` | Parses Markdown fields and converts them for the selected HTML or LaTeX target. |
| `quizml.markdown.html_renderer` | Produces HTML math and embeds or references generated equation images. |
| `quizml.markdown.latex_renderer` | Prepares Markdown content and images for LaTeX output. |
| `quizml.renderer` | Renders text templates with Jinja2 or Word templates with `docxtpl`. |
| `quizml.cli.compile` | Coordinates loading, target rendering, output writing, optional build commands, and watch mode. |
| `quizml.cli.pin` | Stamps optional `_quizml`, `_targets`, and `_schema` header metadata, generates question `id`s, and freezes includes. |

## Data flow

1. The CLI loads `quizml.cfg` (or `_config` from the quiz header) and resolves
   selected targets (`--target`, header `_targets`, or `default_targets`). A
   target can be selected by name or through an alias; its dependencies are
   included and ordered before it.
2. The loader reads the quiz's optional header and question list, expands
   document-relative includes (supporting `select` by question `id` or 1-based
   index), and validates the resulting data against the configured schema (with
   any inline `schema_extensions` from `quizml.cfg` merged in). The loaded
   document has top-level `header`, `questions`, and `paths` values.
3. For each target, the Markdown transcoder parses Markdown fields and converts
   them to the configured representation (`html`, `latex`, or raw `markdown`).
   HTML targets can choose `png`, `svg`, `mathml`, or `passthrough` (client-side
   MathJax/KaTeX) equation output, with configurable DPI/scaling and optional
   custom HTML postprocessors; LaTeX targets receive LaTeX-formatted content.
4. The renderer supplies the document, paths, target metadata, and any custom
   `context`/`vars` variables or `jinja_filters` to a Jinja or Word (`docxtpl`)
   template. Text templates use `<| ... |>` for blocks, `<< ... >>` for
   expressions, and `<# ... #>` for comments. Undefined Jinja variables are
   errors.
5. Targets with `build_cmd` run external commands after their dependencies
   succeed. The bundled `build` alias selects the standard exports and PDF
   targets.

## Design notes

- YAML scalar values are initially preserved as strings, avoiding implicit
  conversions such as `NO` to `false`. Schema types control coercion across both
  `header` and `questions`; plain YAML `null` remains `None`.
- Markdown documents are parsed individually into isolated ASTs that are never
  mutated in-place during target rendering. QuizML's custom math and
  image-width tokens are registered only while parsing, to avoid leaking parser
  state to other users of Mistletoe.
- Templates, configs, schemas, and assets are found through `FileLocator`, which
  walks up parent directories from `base_dir` and `cwd` (stopping at `.git` or
  `pyproject.toml` repo boundaries) looking for `_quizml/` (and legacy
  `quizml-templates/`), then checks the resolved config's directory, the user
  config directory, and the packaged defaults. This allows `quizml init` to
  eject only `_quizml/quizml.cfg` by default while inheriting unmodified
  templates and schemas from the package.
- Both `LatexRunner` and `compile_cmd_target` prepend the quiz directory,
  included figure directories, and `FileLocator` search directories to
  `TEXINPUTS` so custom `.cls`/`.sty` files, logos, and `\input{...}` assets
  inside `_quizml/` are found automatically by LaTeX compilers.
- Relative output paths, template lookups, and build commands are anchored to
  the input quiz's directory (or current working directory when reading from
  `stdin`). Target `out`, `build_cmd`, and `descr_cmd` strings support
  `${inputdir}`, `${inputbasename}`, `${inputstem}`, and sanitized scalar header
  variables (`${<header_key>}`).
- Equation and SVG-to-PDF conversions use QuizML's shared cache, keyed on
  content, preamble/converter settings, DPI/scale, and external tool versions.
  Run `quizml cache clear` to remove cached conversions.
- CLI subcommands keep `stdout` strictly reserved for data payloads (`fmt`,
  `sample`, `pin -o -`, `compile -o -`, and tab-separated `targets`/`diff`
  output when piped) and route all human diagnostics, banners, and errors to
  `stderr`.

