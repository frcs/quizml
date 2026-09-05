# Python API & Pipelines  <!-- {docsify-ignore} -->

QuizML provides a clean, modular Python API alongside its command-line interface. Each stage of the document lifecycle—parsing, markdown transcoding, template rendering, and file building—is cleanly decoupled and can be used independently in Python scripts, custom web services, or Unix shell pipelines.

---

## High-Level Python API

The root package `quizml` exposes the primary pipeline functions:

```python
import quizml

# 1. Ingest: Parse YAML into structured Python dictionaries
doc = quizml.load_quiz("exam.yaml")

# 2. Transcode: Convert Markdown questions and choices to LaTeX or HTML
doc_latex = quizml.transcode(doc, fmt="latex")

# 3. Render: Populate a Jinja2 or Word (.docx) template
tex_output = quizml.render(doc_latex, "tcd-exam.tex.j2")

with open("exam.tex", "w", encoding="utf-8") as f:
    f.write(tex_output)
```

### Core Functions

#### `quizml.load_quiz(file_or_stream, schema=None)`
Parses a QuizML YAML file or input stream into validated Python data structures (header dictionary and questions list).

* **Arguments:**
  * `file_or_stream` (`str | Path | TextIO`): Path to a YAML file or an open text stream.
  * `schema` (`dict | None`, optional): Custom JSON Schema dictionary for question validation.
* **Returns:**
  * `dict`: Document dictionary containing `header` and `questions`.

#### `quizml.transcode(doc, fmt="latex", preamble_file=None, css_file=None)`
Transforms Markdown text within question statements, choices, and explanations into target-specific markup.

* **Arguments:**
  * `doc` (`dict`): The document dictionary containing `header` and `questions`.
  * `fmt` (`str`): Target markup format. Supported formats:
    * `"latex"`: Converts Markdown formatting and math to LaTeX macros.
    * `"html"`: Converts Markdown to HTML with default math handling.
    * `"html-svg"`: Renders LaTeX equations as embedded SVG graphics.
    * `"html-mathml"`: Converts LaTeX equations to native MathML elements.
    * `"html-math-hybrid"`: Uses MathML for inline math and PNG images for display equations (optimal for LMS editors like Blackboard Ultra).
  * `preamble_file` (`str | Path | None`, optional): Path to LaTeX preamble for equation rendering.
  * `css_file` (`str | Path | None`, optional): Path to CSS file for inline HTML styling.
* **Returns:**
  * `dict`: A deep copy of the document with all markdown fields transcoded. Automatically adds `_transcoded: <fmt>` to the document header to ensure idempotency.

#### `quizml.render(doc, template_path, extra_context=None)`
Renders a transcoded document using a Jinja2 template or Word (`.docx`) template.

* **Arguments:**
  * `doc` (`dict`): Document dictionary (will automatically run `quizml.transcode()` if not already transcoded).
  * `template_path` (`str | Path`): Path or filename of the template. Automatically searches working directory, local `quizml-templates/`, user config directory, and packaged templates.
  * `extra_context` (`dict | None`, optional): Additional template variables passed to Jinja2 or docxtpl.
* **Returns:**
  * `str`: Rendered text string for text/Jinja2 templates (e.g. `.tex.j2`, `.html.j2`, `.txt.j2`).
  * `bytes`: Rendered binary byte buffer for Word templates (`.docx`).

#### `quizml.build_targets(quiz_path, targets=None, build=False, locator=None)`
Executes the multi-target compilation workflow configured in `quizml.cfg`.

* **Arguments:**
  * `quiz_path` (`str | Path`): Path to the input YAML file.
  * `targets` (`list[str] | None`, optional): Specific target names to build (e.g. `["pdf", "bb"]`). Defaults to all targets.
  * `build` (`bool`): When `True`, executes post-compilation shell commands (such as running `latexmk` to generate PDF).
* **Returns:**
  * `dict`: Build status summary and rendered target file paths.

---

## Subpackages Architecture

QuizML is organized into 6 focused, decoupled subpackages:

| Package | Responsibility |
| :--- | :--- |
| `quizml.quizmlyaml` | YAML loading, custom tag parsing, question formatting, and JSON Schema validation. |
| `quizml.transcoder` | Markdown AST parsing, math rendering (LaTeX, SVG, MathML), and figure path resolution. |
| `quizml.renderer` | Jinja2 template rendering (with custom `<\| \|>` delimiters) and Word document (`docxtpl`) templating. |
| `quizml.builder` | Multi-target compilation orchestration, topological dependency resolution, and post-build task execution. |
| `quizml.tools` | File locator (`FileLocator`), equation cache, and image conversion utilities. |
| `quizml.cli` | Argument parsing, interactive Rich terminal UI, diff, and docs viewer. |

---

## Unix Pipeline Composability

QuizML is fully composable with standard Unix pipes. Every stage can output or consume JSON intermediate representations (IR) across standard input (`stdin`) and standard output (`stdout`).

### 1. Ingest Stage (`--ingest`)
Reads raw YAML from a file or `stdin`, validates the schema, coerces data types, and prints the document structure as JSON:

```bash
quizml exam.yaml --ingest > exam.ir.json
# Or reading from stdin:
cat exam.yaml | quizml --ingest > exam.ir.json
```

### 2. Transcode Stage (`--transcode <FMT>`)
Reads either raw YAML or ingested JSON IR from a file or `stdin`, transcodes markdown fields to `<FMT>` (`latex`, `html`, `html-svg`, `html-mathml`, `html-math-hybrid`), and outputs the transcoded JSON IR:

```bash
quizml exam.yaml --transcode latex > exam.latex.json
# Or in a pipe:
cat exam.yaml | quizml --ingest | quizml --transcode latex > exam.latex.json
```

### 3. Render Stage (`--render <TEMPLATE>`)
Reads either raw YAML or transcoded JSON IR from a file or `stdin`, renders the template, and writes the output text to `stdout`:

```bash
# Direct one-step render:
quizml exam.yaml --render tcd-exam.tex.j2 > exam.tex

# Composed 3-stage pipe:
cat exam.yaml | quizml --ingest | quizml --transcode latex | quizml --render tcd-exam.tex.j2 > exam.tex
```

### Integrating with External Tools

Because QuizML emits clean JSON IR, you can easily inspect and modify tests with `jq` or external scripts:

```bash
# Count questions by type
quizml exam.yaml --ingest | jq '.questions | group_by(.type) | map({type: .[0].type, count: length})'

# Extract all questions worth more than 5 marks
quizml exam.yaml --ingest | jq '[.questions[] | select(.marks > 5)]'
```
