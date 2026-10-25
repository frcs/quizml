# The Header Section <!-- {docsify-ignore} -->

An optional header section can appear at the start of a quiz file. Its
key-value pairs are passed to templates as `header` metadata. Separate the
header from the question list with a line containing `---`.

The bundled schema checks the types of commonly used header fields. Additional
custom header keys are allowed without modifying the schema. Plain YAML `null`
values are loaded as `None`; quote `"null"` when the literal text is intended.

```yaml
title: Final Examination
venue: Maxwell Theatre
date: 13/05/2024
descr: |
  Attempt all questions. Show all intermediate steps.
---
- type: tf
  question: Is the Earth an oblate spheroid?
  answer: true
```

Ordinary header values are transcoded as Markdown for the active target. Keys
starting with `_` are reserved for QuizML controls or raw template values and
are not transcoded as Markdown.

## Template-specific header keys

The bundled LaTeX exam template (`tcd-exam.tex.j2`) converts ordinary header
keys into TeX macro definitions (`\def\info<key>{...}`), so use letters only
(`a-z`, `A-Z`) for header key names when compiling with that template:

```tex
\def\infotitle{Final Examination}
\def\infovenue{Maxwell Theatre}
\def\infodate{13/05/2024}
```

## Built-in control keys

All header keys are optional, but the following `_`-prefixed keys have special
meaning to QuizML:

- `_targets`: Target name or list of target names (e.g. `[pdf, html-preview]` or `bb`)
  to build for this file when `-t`/`--target` is not passed on the CLI.
- `_quizml`: Version constraint (e.g. `">=0.12,<0.13"` or `"~=0.12"`). QuizML
  prints a warning if the running version does not satisfy the constraint.
- `_schema`: Path to a custom JSON or YAML schema file for validating this quiz.
- `_config`: Path to a custom `quizml.cfg` file for compiling this quiz.
- `_figures_path`: Additional directory or list of directories searched for
  figures and LaTeX inputs.
- `_latexpreamble`: Raw LaTeX preamble declarations (such as `\newcommand`
  macros) injected into equation and document builds.

Run `quizml pin exam.yaml` to stamp `_quizml` and `_targets` automatically.
