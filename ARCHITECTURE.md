# QuizML Architecture Report

## 1. High-Level Overview

QuizML is a pipeline-driven tool that transforms structured quiz data (YAML/Markdown) into various output formats (LaTeX, Blackboard CSV, HTML). It prioritizes a **lean core** with extensibility provided through **Jinja2 templates** and **user-defined schemas**.

### Core Pipeline
1.  **Ingest:** Load YAML, normalize types, and validate against a JSON schema.
2.  **Transcode:** Convert embedded Markdown/LaTeX strings into target-specific formats (HTML or LaTeX) using a specialized transcoding engine.
3.  **Render:** Apply the transformed data to Jinja2 templates (or Docx templates) to generate final artifacts.
4.  **Build:** Execute external build commands (e.g., `latexmk`) if required.

---

## 2. Component Analysis

### 2.1 CLI & Configuration
*   **Entry Point:** `src/quizml/cli/cli.py`
    *   Uses `rich_argparse` for a polished CLI experience.
    *   Main dispatch logic for commands: `compile`, `diff`, `init`, `cleanup`.
*   **File Resolution:** `src/quizml/cli/filelocator.py`
    *   Implements a cascading search strategy for configs and templates:
        1.  Current Working Directory
        2.  `./quizml-templates/` (Local override)
        3.  User Config Directory (OS-specific, e.g., `~/.config/quizml`)
        4.  Package `templates/` directory (Fallback)
*   **Configuration:** `src/quizml/cli/config.py`
    *   Loads `quizml.cfg`.
    *   Resolves target dependencies (e.g., ensuring a `.tex` file is generated before trying to compile it to PDF).
    *   Substitutes variables like `${inputbasename}` in file paths.

### 2.2 Data Ingestion (Loader)
*   **Module:** `src/quizml/loader.py`
*   **The "Norway Problem" Solution:**
    *   Uses a custom `ruamel.yaml` constructor (`StringConstructor`) to load *all* scalar values as strings initially. This prevents `country: NO` from becoming `country: False`.
*   **Validation & Coercion:**
    *   Uses `jsonschema` with a custom validator stack (`DefaultFillingValidator`).
    *   **Coercion:** It attempts to convert strings to `boolean`, `integer`, or `number` *only* if the schema explicitly allows those types for a specific field.
    *   **Defaults:** Automatically populates missing fields with default values defined in the schema.

### 2.3 Markdown Transcoding Engine
*   **Module:** `src/quizml/markdown/markdown.py`
*   **Concept:** Instead of rendering Markdown fields one by one, the `MarkdownTranscoder`:
    1.  Extracts all Markdown strings from the loaded YAML.
    2.  Concatenates them into a single "Shadow Document" (separated by headers).
    3.  Parses this document once using `mistletoe`.
    4.  Splits the rendered output back into a dictionary (keyed by content hash) and caches it.
*   **Custom Tokens (`src/quizml/markdown/extensions.py`):**
    *   `MathDisplay`: Handles `$$...$$`, `\[...\]`, `\begin{equation}`.
    *   `MathInline`: Handles `$ ... $`, `\( ... \)`.
    *   `ImageWithWidth`: Handles `![alt](src){width=...}`.
*   **HTML Rendering (`src/quizml/markdown/html_renderer.py`):**
    *   Converts LaTeX math to images (PNG/SVG) or MathML using external tools (`pdflatex`, `gs`, `dvisvgm`, `make4ht`).
    *   Embeds images as Base64 strings for self-contained HTML.
*   **LaTeX Rendering (`src/quizml/markdown/latex_renderer.py`):**
    *   Converts `ImageWithWidth` tokens to `\includegraphics`.
    *   Auto-converts SVG images to PDF (using `rsvg-convert` or `inkscape`) for compatibility with `pdflatex`.

### 2.4 Template Rendering
*   **Module:** `src/quizml/renderer.py`
*   **Jinja2 Engine:**
    *   Configured with custom delimiters to avoid clashes with LaTeX syntax:
        *   Block: `<| ... |>`
        *   Variable: `<< ... >>`
        *   Comment: `<# ... #>`
    *   Context includes `header`, `questions` (with transcoded Markdown), and `math` module.
*   **Docx Support:** `src/quizml/docx_renderer.py`
    *   Delegates to `docxtpl` for rendering Word documents (`.docx`).
    *   Bypasses the standard Jinja text engine to work directly with Word's XML structure.

---

## 3. Data Flow Diagram

```mermaid
graph TD
    User[User] -->|quizml file.yaml| CLI[CLI Entry (cli.py)]
    CLI -->|Load Config| Config[Config Loader (config.py)]
    CLI -->|Load Data| Loader[Data Loader (loader.py)]
    
    Loader -->|Raw Strings| YAML[ruamel.yaml]
    YAML -->|Schema Validation| Validator[JSON Schema Validator]
    Validator -->|Coerced Data| DataStruct[Internal Data Structure]

    DataStruct -->|Extract MD| Transcoder[Markdown Transcoder (markdown.py)]
    Transcoder -->|Render HTML/LaTeX| Mistletoe[Mistletoe Parser]
    Mistletoe -->|Images/Math| ExternalTools[External Tools (latex, gs)]
    Mistletoe -->|Rendered Content| TranscodedData[Transcoded Data]

    CLI -->|Compile Targets| Renderer[Template Renderer (renderer.py)]
    TranscodedData --> Renderer
    Renderer -->|Jinja2| TextFiles[Text Output (tex, csv, html)]
    Renderer -->|DocxTpl| WordFiles[Word Output (docx)]
    
    CLI -->|Build Cmd| Build[External Build (latexmk)]
    Build --> Final[Final Artifacts (pdf)]
```

## 4. Key Functions Reference

| Component | Function | Description |
| :--- | :--- | :--- |
| **Loader** | `loader.load(path, validate=True)` | Main entry to load, validate, and coerce YAML data. |
| **Loader** | `loader.DefaultFillingValidator` | Custom class combining defaults filling and type coercion. |
| **Markdown** | `markdown.MarkdownTranscoder.transcode_target(target)` | Pre-renders all Markdown fields for a specific target format. |
| **HTML** | `html_renderer.build_eq_dict_SVG(eq_list, opts)` | Compiles LaTeX equations to SVG for HTML embedding. |
| **LaTeX** | `latex_renderer.resolve_image_path(src)` | Handles SVG->PDF conversion for LaTeX compatibility. |
| **Renderer** | `renderer.render(data, template)` | Selects between Jinja2 (text) and DocxTpl (Word) rendering. |
| **CLI** | `compile.compile(args)` | Orchestrates the entire loading, transcoding, rendering, and building process. |
