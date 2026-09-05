# QuizML Architecture Report

## 1. High-Level Overview

QuizML is a pipeline-driven tool that transforms structured quiz data (YAML/Markdown) into various output formats (LaTeX, Blackboard CSV, HTML). It prioritizes a **lean core** with extensibility provided through **Jinja2 templates** and **user-defined schemas**.

### Core Pipeline
1.  **Ingest:** Load YAML, normalize types, and validate against a JSON schema.
2.  **Transcode:** Convert embedded Markdown/LaTeX strings into target-specific formats (HTML or LaTeX) using a specialized transcoding engine.
3.  **Render:** Apply the transformed data to Jinja2 templates (or Docx templates) to generate final artifacts.
4.  **Build:** Execute external build commands (e.g., `latexmk`) if required.

## 2. Design Philosophy

QuizML is built around five core architectural principles:

### 2.1 Pure Declarative Compiler (Deterministic & Auditable)
* **What you write is what gets compiled.** QuizML is a deterministic compiler, not a runtime code-execution sandbox.
* **Zero Hidden State:** Document compilation does not execute arbitrary code or introduce dynamic/probabilistic behavior (like random question sampling) during builds.
* **Auditability & Version Control:** An exam document (`quiz.yaml`) represents an immutable, reviewable pedagogical artifact that can be diffed (`quizml diff`), signed off by external examiners, and tracked in Git. If randomized question variants are needed, they are generated beforehand as static, reviewable YAML files.

### 2.2 Document-Centric Authoring (Cohesive vs. Fragmented)
* **Exam as a Unified Assessment:** Instead of forcing one file per question (which creates file sprawl and bookkeeping friction), an entire exam lives cohesively in a single human-readable YAML document.
* **Modular Question Banking via Static Inclusion (`_include:`):** When modular topic banks or shared repositories are desired, `- _include:` acts as a clean, transparent 1-to-1 composition mechanism without nesting or hidden logic.

### 2.3 Lean Core + Transparent Template Extensibility
QuizML does only three core things:
1. **Ingest & Validate:** Type-safe YAML ingestion with schema validation (solving YAML gotchas like the "Norway problem").
2. **Transcode:** Uniformly translates Markdown formatting, LaTeX equations, and embedded figures into target-specific assets.
3. **Render:** Applies data to user-editable Jinja2 templates (using LaTeX-safe delimiters `<| ... |>`, `<< ... >>`) or Word templates.

Institutional layouts, grading guidelines, and university templates remain completely decoupled from the compiler engine and can be customized with `quizml --init-local`.

### 2.4 Human & AI Ergonomics
* **Natural Authoring Syntax:** Intuitive inline markers like `- x:` (correct) and `- o:` (distractor) eliminate error-prone binary bitstrings or detached answer lists.
* **AI & LLM Synergy:** Compact, standard YAML fits cleanly in single prompts and produces near-zero syntax hallucinations when prompting AI assistants to draft or refine question sets.

### 2.5 Unix Philosophy: Composability over Monoliths
* QuizML focuses strictly on **exam document compilation and multi-target rendering** (LaTeX, Blackboard, Word, HTML).
* Peripheral tasks (e.g. generating randomized question batches, pulling grades, or archiving) are left to simple scripts, CLI utilities (`quizml format`, `quizml diff`), or standard Unix tools.

---

## 3. Component Analysis

### 3.1 Data Ingestion (`quizml.quizmlyaml`)
*   **Package:** `src/quizml/quizmlyaml/`
*   **The "Norway Problem" Solution (`parser.py`):**
    *   Uses a custom `ruamel.yaml` constructor (`StringConstructor`) to load *all* scalar values as strings initially. This prevents `country: NO` from becoming `country: False`.
*   **Modular Ingestion (`includes.py`):**
    *   Recursively resolves `- _include: file.yaml` directives cleanly into a flattened list of questions.
    *   Tracks visited paths to prevent circular dependency cycles.
    *   Propagates figure directory paths relative to the root quiz directory.
*   **Validation & Coercion (`validator.py`):**
    *   Uses `jsonschema` with a custom validator stack (`DefaultFillingValidator`).
    *   **Coercion:** Attempts to convert strings to `boolean`, `integer`, or `number` *only* if the schema explicitly allows those types for a specific field.
    *   **Defaults:** Automatically populates missing fields with default values defined in the schema.

### 3.2 Markdown Transcoder (`quizml.transcoder`)
*   **Package:** `src/quizml/transcoder/`
*   **Concept (`transcoder.py`):**
    *   Extracts all Markdown strings from the loaded YAML.
    *   Parses each unique Markdown block into an isolated Mistletoe AST Document.
    *   Renders to HTML or LaTeX dictionaries and caches results.
*   **Custom Tokens (`tokens.py`):**
    *   `MathDisplay`: Handles `$$...$$`, `\[...\]`, `\begin{equation}`.
    *   `MathInline`: Handles `$ ... $`, `\( ... \)`.
    *   `ImageWithWidth`: Handles `![alt](src){width=...}`.
*   **HTML Rendering (`html.py`):**
    *   Converts LaTeX math to images (PNG/SVG) using external tools (`pdflatex`, `gs`, `dvisvgm`) or MathML using `latex2mathml` with recursive macro expansion.
    *   Embeds images as Base64 strings for self-contained HTML.
*   **LaTeX Rendering (`latex.py`):**
    *   Converts `ImageWithWidth` tokens to `\includegraphics`.
    *   Auto-converts SVG images to PDF (using `rsvg-convert` or `inkscape`) for compatibility with `pdflatex`.
*   **Images & Tools (`images.py`, `latextools.py`, `nodes.py`):**
    *   Path resolution across figure search paths, dimensions calculation, and equation compilation.

### 3.3 Template Renderer (`quizml.renderer`)
*   **Package:** `src/quizml/renderer/`
*   **Jinja2 Engine (`jinja.py`):**
    *   Configured with custom delimiters to avoid clashes with LaTeX syntax:
        *   Block: `<| ... |>`
        *   Variable: `<< ... >>`
        *   Comment: `<# ... #>`
    *   Context includes `header`, `questions` (with transcoded Markdown), and `math` module.
*   **Docx Support (`docx.py`):**
    *   Delegates to `docxtpl` for rendering Word documents (`.docx`).
    *   Bypasses the standard Jinja text engine to work directly with Word's XML structure.

### 3.4 Build Engine (`quizml.builder`)
*   **Package:** `src/quizml/builder/`
*   **DAG Dependency Resolution (`dag.py`):**
    *   Uses Python's `graphlib.TopologicalSorter` to ensure prerequisite targets compile before dependents.
*   **Config Resolution (`config.py`):**
    *   Loads `quizml.cfg`, substitutes `$inputbasename`, resolves relative template paths, reads preambles.
*   **Headless Scheduler (`scheduler.py`):**
    *   Compiles targets and executes external build tools (`pdflatex`, `latexmk`), returning structured `TargetResult` objects without terminal UI dependencies.

### 3.5 Companion Tools (`quizml.tools`)
*   **Package:** `src/quizml/tools/`
*   **Pure Functional Utilities:**
    *   `format.py`: Indentation formatting and automatic question comment numbering (`# <Q1>`, `# <Q2>`).
    *   `diff.py`: Similarity matching across quiz exams and duplicate detection.
    *   `cleanup.py`: Build artifact detection and cleanup.

### 3.6 CLI & Terminal Presentation (`quizml.cli`)
*   **Package:** `src/quizml/cli/`
*   **Entry Point (`cli.py`):**
    *   Uses `rich_argparse` and `rich` tables/panels for terminal output.
    *   Supports `--watch` with LiveReload server (`livereload.py`).
    *   Exports JSON Intermediate Representation via `--ingest`.
    *   Exposes pipeline stages directly for Unix composability: `--transcode <fmt>` and `--render <template>`.

---

## 4. Data Flow Diagram

```mermaid
graph TD
    User[User / Python API] -->|quizml quiz.yaml / compile_quiz| Builder[Builder Engine (quizml.builder)]
    Builder -->|Load & Validate| YAML[Ingestion Engine (quizml.quizmlyaml)]
    
    YAML -->|StringConstructor| ruamel[ruamel.yaml]
    YAML -->|Includes| IncludeRes[_resolve_includes]
    YAML -->|Schema & Defaults| Validator[DefaultFillingValidator]
    Validator -->|Coerced QuizMLDoc| DocIR[QuizML Document IR]

    DocIR -->|Transcode| Transcoder[Transcoder (quizml.transcoder)]
    Transcoder -->|Mistletoe AST| ASTTokens[Math & Image Tokens]
    ASTTokens -->|LaTeX / HTML| RenderTargetData[Transcoded Doc]

    RenderTargetData -->|Render| Renderer[Renderer (quizml.renderer)]
    Renderer -->|Jinja2| TextFiles[Text Output (tex, csv, html)]
    Renderer -->|DocxTpl| WordFiles[Word Output (docx)]
    
    Builder -->|Post-Build Cmds| ExternalBuild[Build Tools (latexmk)]
    ExternalBuild --> FinalArtifacts[Final Output (pdf)]
```

## 5. Key Functions Reference

| Component | Function | Description |
| :--- | :--- | :--- |
| **Ingestion** | `quizmlyaml.load(path, validate=True)` | Ingests, resolves `_include`, validates, and coerces QuizML document. |
| **Ingestion** | `quizmlyaml.loads(text, validate=True)` | Parses QuizML text from a string into document dict. |
| **Transcoder** | `transcoder.transcode(doc, target)` | Transcodes Markdown fields in document to HTML or LaTeX. |
| **Renderer** | `renderer.render(doc, template)` | Renders document through Jinja2 or Word template. |
| **Builder** | `builder.compile_quiz(yaml_file, targets=...)` | Compiles targets via TopologicalSorter DAG scheduler. |
| **Tools** | `tools.format_file(path, in_place=True)` | Formats YAML indentation and renumbers question comments. |
| **Tools** | `tools.cleanup_build(dir_path)` | Scans and deletes generated targets and LaTeX artifacts. |
| **Tools** | `tools.compare_quiz_files(ref, others)` | Detects duplicated/similar questions across exams. |

