# QuizML vs R/exams <!-- {docsify-ignore} -->

QuizML and [R/exams](https://www.r-exams.org/) both compile assessments into
multiple LMS and print formats, but they are built around different authoring
models and ecosystems.

## QuizML

- Questions are authored together in a single YAML file or organized into
  topic-level YAML question banks via `_include`.
- Question text uses CommonMark Markdown and LaTeX equations.
- Compilation is purely declarative and deterministic; randomized question-bank
  sampling is materialized explicitly into static YAML files with
  `quizml sample`.
- Configured in Python (`quizml.cfg` + Jinja2 / `docxtpl` templates), exporting
  Blackboard text, QTI 1.2 & 2.1, Moodle XML, HTML previews, Word (`.docx`),
  and LaTeX / PDF exams.

## R/exams

- Each exercise is authored in its own R Markdown (`.Rmd`) or R/LaTeX (`.Rnw`)
  file and assembled by an R script.
- Exercises can execute embedded R code during rendering to generate
  parameterized numbers, plots, and solutions dynamically.
- Tightly integrated with the R statistical computing ecosystem.

Choose QuizML if you prefer a declarative single-file YAML/Markdown workflow and
Jinja/Word templates; choose R/exams if you want programmatic R code execution
inside individual exercises.
