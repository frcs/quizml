# QuizML vs R/exams<!-- {docsify-ignore} -->

Both **QuizML** and **R/exams** (`exams` package in R) are tools designed to solve the same fundamental academic problem: authoring quizzes and exams once and compiling them into multiple output formats (paper LaTeX exams, LMS quizzes, and HTML previews).

However, they embody fundamentally different design philosophies and workflows. This page outlines the key differences, QuizML's design rationale, and when to use each tool.

---

## At a Glance: Feature Comparison

| Dimension | QuizML | R/exams |
| :--- | :--- | :--- |
| **Authoring Paradigm** | **Single-file exam** (`quiz.yaml`) | **One file per question** (`.Rmd` / `.Rnw` exercise bank) |
| **Execution Model** | **Pure Declarative Compiler** (Safe, deterministic) | **Programmatic Sandbox** (Executes arbitrary R code) |
| **Question Syntax** | Clean, human-readable YAML (`- o:` / `- x:`) | Multi-section Markdown/LaTeX (`Question`, `Answerlist`, `exsolution: 1010`) |
| **Tech Stack** | Python (lean `uv` / `pip` workflow) | R, CRAN packages, Pandoc, LaTeX, ImageMagick |
| **Compilation Speed** | Instant (<0.2s for 30 questions) | Moderate (runs R processes & knitr rendering per question) |
| **Developer Ergonomics** | Built-in CLI: `--watch`, `--format`, `--diff`, `--docs` | Driven via R interactive console or Rscript pipelines |
| **LMS Exports** | Blackboard (CSV/Tab), LaTeX, HTML, Word docx | Blackboard, Moodle, Canvas (QTI), OpenOlat, ILIAS |
| **AI / LLM Friendly** | **Exceptional** (compact YAML fits in a single prompt) | Moderate (LLMs often hallucinate binary bitstrings and knitr chunks) |

---

## 1. Single-File Authoring vs. Exercise File Sprawl

### The R/exams Approach
In R/exams, **every single question is an isolated file** (`question1.Rmd`, `question2.Rmd`). To create an exam of 30 questions, you must maintain 30 separate files in a directory and write an R script that lists them:
```r
exams2pdf(c("derivative.Rmd", "matrix_mult.Rmd", "hypothesis_test.Rmd"))
```
While this is useful for massive departmental question banks, it introduces significant friction for daily teaching:
- Authoring, balancing marks, and reviewing an exam requires juggling dozens of open tabs in your text editor.
- Calculating total marks or adjusting difficulty across questions requires cross-file bookkeeping.

### The QuizML Approach
QuizML treats the **entire exam as a single coherent document** (`quiz.yaml`):
- All questions, header metadata, mark allocations, and layout instructions live in one place.
- You can review the entire exam sequentially in seconds.
- QuizML provides `--format` to automatically format YAML indentation and sequentially renumber question comments (`<Q1>`, `<Q2>`).
- For question banking, QuizML supports the `_include` directive: you can still modularize questions into separate topic files and splice them into an exam when desired.

---

## 2. Declarative Compiler vs. Code Execution Sandbox

### Why QuizML Avoids Running Code
R/exams' hallmark feature is **dynamic parametric randomization**: every question can embed arbitrary R code chunks to generate random numbers, compute statistical models, and render dynamic plots.

However, executing user code inside a compiler introduces major drawbacks:
1. **Security Risks**: Running arbitrary code during compilation creates serious vulnerabilities if sharing templates across teams.
2. **Environment Brittleness**: Code chunks depend on specific package versions and R environments, leading to "works on my machine" failures years later.
3. **Debugging Overhead**: If an embedded R chunk produces an error or infinite loop, diagnosing it through multiple layers of knitr and LaTeX is painful.

### The QuizML Philosophy: Clean Separation
QuizML is designed as a **fast, deterministic compiler**:
- QuizML compiles pure declarative data structures into output templates. It does not run user code.
- If you need 50 randomized versions of a question, the recommended approach is **external parametrization**: write a 10-line Python script or Jupyter notebook to generate `quiz1.yaml`, `quiz2.yaml`, etc.
- This keeps QuizML lightweight, deterministic, and instant to run.

---

## 3. Authoring Ergonomics: YAML vs. Binary Bitstrings

Compare authoring a multiple-choice question in both tools:

### QuizML
```yaml
- type: mc
  marks: 5
  question: |
    Which of the following is a primary color?
  choices:
    - o: Green
    - x: Blue
    - o: Orange
```
*Why it works*:
- `- o:` represents an incorrect choice (distractor).
- `- x:` represents the correct choice.
- No need to count indices or configure separate solution blocks.

### R/exams
```markdown
Question
========
Which of the following is a primary color?

Answerlist
----------
* Green
* Blue
* Orange

Meta-information
================
exname: Primary Colors
extype: schoice
exsolution: 010
```
*The friction*:
- Correctness is separated from choices and encoded as a binary bitstring (`exsolution: 010`). If choices are reordered, the bitstring must be manually recalculated.
- Strict header separators (`========`, `----------`) must be memorized.

---

## 4. Seamless Synergy with AI & LLMs

One of QuizML's greatest modern advantages is how effortlessly it integrates with Large Language Models (LLMs) like Claude, ChatGPT, and Gemini:

- **Single-Prompt Generation**: Because a complete QuizML quiz is valid YAML, you can ask an LLM: *"Generate a 10-question QuizML YAML quiz on linear algebra"*, and it will generate the entire exam in a single response with valid syntax.
- **Zero Hallucination on Bitstrings**: LLMs frequently make off-by-one errors when generating R/exams' binary `exsolution: 1000` tags, especially when shuffling answers. QuizML's inline `- x:` and `- o:` choices prevent these errors entirely.

---

## 5. Template Transparency (Jinja2)

QuizML uses standard **Jinja2** templates with custom delimiters (`<| ... |>`, `<< ... >>`) to prevent conflicts with LaTeX and Markdown.

- If you want to change university logos, adapt margins, or alter LaTeX exam headers, run:
  ```bash
  quizml --init-local
  ```
- All templates (`tcd-exam.tex.j2`, `blackboard.txt.j2`, `html-preview.html.j2`) are copied into your local `quizml-templates/` directory as plain text files you can edit with standard Jinja2.
- R/exams templates, by comparison, are deeply intertwined with R internals, XML generators, and complex Pandoc filters.

---

## Summary: When to Use Which?

### Choose QuizML if:
- You want to author and manage an entire exam in a **single, human-readable file**.
- You value **instant compilation**, live-reload preview in your browser (`-w`), and a modern CLI.
- You use Python or prefer not having to install R and its dependencies.
- You want to author quizzes using **LLMs / AI assistants**.
- You want straightforward template customization with Jinja2.

### Choose R/exams if:
- You are deeply invested in the **R statistical ecosystem**.
- Your assessment relies fundamentally on **in-situ parametric code execution** (e.g. generating unique random datasets and `ggplot2` charts inside each student's exam sheet).
- You manage a department-wide pool with hundreds of standalone `.Rmd` exercise files.
