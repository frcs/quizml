# Output targets <!-- {docsify-ignore} -->

Targets are defined under the `targets:` list in `quizml.cfg`. Each target
describes one output artifact: its output filename, Markdown conversion
options, template, and optional post-processing command.

## Bundled targets

Run `quizml targets` to list the targets available in your active configuration.
The bundled `quizml.cfg` provides:

| Target | Output | Description |
| :--- | :--- | :--- |
| `bb` | `${inputbasename}.txt` | Blackboard tab-delimited import file |
| `html-preview` | `${inputbasename}.html` | Standalone HTML preview with embedded assets |
| `latex` | `${inputbasename}.tex` | LaTeX exam source (`tcd-exam.tex.j2`) |
| `latex-solutions` | `${inputbasename}.solutions.tex` | LaTeX exam source with solutions |
| `pdf` | `${inputbasename}.pdf` | Compiled PDF exam (via `latexmk -xelatex`) |
| `pdf-solutions` | `${inputbasename}.solutions.pdf` | Compiled PDF exam with solutions |
| `docx` | `${inputbasename}.docx` | Word exam paper (`tcd-exam.docx`) |
| `docx-solutions` | `${inputbasename}.solutions.docx` | Word exam paper with solutions |
| `qti` / `qti12` | `${inputbasename}.qti.zip` | IMS QTI 1.2 package (Canvas, Brightspace) |
| `qti21` | `${inputbasename}.qti21.zip` | IMS QTI 2.1 package (Blackboard Ultra) |
| `moodle` | `${inputbasename}.xml` | Moodle XML question bank |

## Target definition example

```yaml
targets:
  - name: bb
    descr: Blackboard test
    out: ${inputbasename}.txt
    descr_cmd: ${inputbasename}.txt
    markdown:
      format: html
      math: svg
      html_postprocess: blackboard_html
    html_pre: math-preamble.tex
    html_css: markdown-html.css
    template: blackboard.txt.j2
```

## Target fields

### `name` and `descr`

`name` is the unique identifier passed to `--target`. `descr` is the short
human-readable description shown by `quizml targets`.

### `out` and `descr_cmd`

`out` is the output filename template. Relative output paths are resolved from
the directory containing the input YAML file. Available variables:
- `${inputbasename}` / `${inputstem}`: Input filename without directory or extension.
- `${inputdir}`: Absolute path to the input YAML file's directory.
- Any top-level scalar field from the quiz YAML header (e.g. `${modulecode}` or
  `${title}`), with path separators sanitized to `_`.

`descr_cmd` is the suggested command or output path displayed in the build
summary table after compilation.

### `template`

Path or name of the template used to render the target, resolved through
QuizML's [configuration search paths](configuration.md):
- **Jinja2 text templates** (`.j2`, `.tex`, `.html`, `.xml`, `.txt`): Rendered
  with QuizML's LaTeX-friendly Jinja2 delimiters (see [Templates](writing_templates.md)).
- **Word templates** (`.docx`): Rendered into a `.docx` file via `docxtpl` with
  native Word OpenXML (`w:p`) paragraphs and Office Math (`m:oMath`) equations.
- **QTI package directories** (`qti12`, `qti21`): Packaged into an IMS Content
  Package `.zip` archive with bundled media files and `imsmanifest.xml`.

### `markdown`

Controls how Markdown fields in the header and questions are transcoded before
rendering:

- **`markdown.format`**:
  - `html`: Standard HTML fragments.
  - `latex`: LaTeX markup.
  - `docx`: Word OpenXML (`RichText` / subdocument XML) for `.docx` templates.
  - `markdown`: Keeps raw Markdown strings untouched (useful for downstream
    Pandoc or Quarto pipelines).
- **`markdown.math`** (used when `markdown.format` is `html`):
  - `svg`: Renders equations to inline SVGs using `dvisvgm` (requires LaTeX).
  - `png`: Renders equations to Base64 PNGs using `pdflatex` + Ghostscript (`gs`).
  - `mathml`: Converts LaTeX equations to MathML in pure Python (no external
    LaTeX installation required; used by `qti`, `qti21`, and `moodle`).
  - `passthrough`: Emits `<span class="math inline">\(...\)</span>` and
    `<div class="math display">\[...\]</div>` for client-side MathJax or KaTeX.
- **`markdown.html_postprocess`**:
  - Set to `blackboard_html` (to inline CSS and strip newlines/tabs for
    Blackboard text imports) or a custom `module:function` callable.
- **Additional options**: `svg_scale` (default `1.2`), `png_dpi` (default `250`),
  `png_scale` (default `0.5`), and `svg_converter` (command template for
  converting `.svg` figures to `.pdf` in LaTeX targets).

### `html_pre` and `html_css`

- `html_pre`: LaTeX preamble file supplying macros for equation rendering
  (defaults to `math-preamble.tex`).
- `html_css`: CSS stylesheet used for HTML rendering and `blackboard_html`
  inlining (defaults to `markdown-html.css`).

### `context` (or `vars`)

Optional mapping of extra variables merged into the template context for this
target (for example, `context: { solutions: true }` on `docx-solutions`).

### `dep`, `build_cmd`, and `clean_extensions`

- `dep`: Target name (or list of target names) that must be built before this
  target. Dependencies are resolved recursively in topological order.
- `build_cmd`: Shell command executed from the input YAML file's directory after
  template rendering (or after dependencies complete, for build-only targets
  like `pdf`).
- `clean_extensions`: List of dot-prefixed file suffixes (such as `[.aux, .log, .fls]`)
  that `quizml clean` should remove alongside the target's `out` file.
