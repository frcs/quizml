# Managing a Module Across Academic Years

This guide describes recommended repository layouts and workflows for lecturers managing weekly Blackboard MCQs, midterms, final exams, and question banks over multiple academic years.

## Recommended Repository Layout

Place your module-wide QuizML configuration and custom templates in a root `_quizml/` directory. QuizML automatically walks up parent directories from the quiz file being compiled to discover `_quizml/` (as well as `quizml.cfg`), so you can compile any quiz from the repository root or from inside a subfolder:

```text
EE401-Deep-Learning/
├── pyproject.toml              # Optional: pins quizml via `uv`
├── uv.lock
├── _quizml/                    # Module-wide config & custom templates
│   ├── quizml.cfg
│   ├── uni-exam.tex.j2         # Custom LaTeX exam template
│   └── uni-logo.pdf            # Found automatically via TEXINPUTS
├── bank/                       # Shared topic question banks
│   ├── 01-linear-models.yaml
│   ├── 02-cnn.yaml
│   └── figs/
├── 2024-2025/
│   ├── bbq/
│   │   └── week01.yaml
│   └── exams/
│       └── final.yaml          # Frozen & pinned archival exam
└── 2025-2026/
    ├── _quizml/                # Optional year-specific override
    ├── bbq/
    │   └── week01.yaml
    └── exams/
        ├── midterm.yaml
        └── final.yaml
```

## Tiered Initialization (`quizml init`)

Instead of copying every bundled file into your repository, `quizml init` creates only what you want to customize and inherits everything else from the installed QuizML package:

```bash
# Minimal setup: creates only _quizml/quizml.cfg
quizml init

# Eject only the LaTeX exam templates and math preamble for university branding
quizml init --latex

# Eject the HTML preview or Blackboard templates
quizml init --html
quizml init --bb

# Eject a specific file or everything
quizml init -t tcd-exam.tex.j2
quizml init --all
```

Existing files in `_quizml/` are never overwritten unless you pass `--force` (`-f`).

## Question IDs, Titles, and Cherry-Picking (`select`)

Give questions in your `bank/*.yaml` files an optional `id` and `title`:

```yaml
- id: cnn-receptive-field
  title: CNN Receptive Field
  type: num
  marks: 5
  question: |
    Consider two $3 \times 3$ convolutional layers with stride 1...
  answer: 5
```

You can then cherry-pick specific questions into a midterm or final exam by `id` (or 1-based index) using `select`:

```yaml
title: Final Examination 2025/26
_targets: [pdf, preview]
---
- _include: ../../bank/02-cnn.yaml
  select:
    - cnn-receptive-field
    - cnn-parameter-count
```

For randomized weekly quizzes, use `count` and `seed` with `quizml sample`:

```bash
quizml sample 2025-2026/bbq/week01.meta.yaml -o 2025-2026/bbq/week01.yaml
```

## Checking for Reused Questions Across Years (`quizml diff`)

Before finalizing an exam paper, check whether any questions overlap with previous years' papers:

```bash
quizml diff 2025-2026/exams/final.yaml 2024-2025/exams/final.yaml 2023-2024/exams/final.yaml
```

`quizml diff` matches questions that share the same `id`, or that have the same question type and $\ge 90\%$ stem similarity with overlapping choices (catching reused MCQs even when a distractor was tweaked). Pass `--check` in CI scripts to exit non-zero if duplicates are detected.

## Archiving and Pinning Past Exams (`quizml pin`)

All header metadata (`_targets`, `_quizml`, `_schema`, `_config`) is completely optional while drafting. Once an exam paper is finalized and sent to the Examinations Office, freeze and stamp it with `quizml pin`:

```bash
quizml pin 2025-2026/exams/final.yaml --add-ids --freeze-includes -t pdf
```

This command:
1. Stamps `_quizml` (e.g. `">=0.12,<0.13"`) and `_targets` into the YAML header so future builds warn if the installed QuizML version is incompatible.
2. Expands `_include` directives in place (`--freeze-includes`) so later edits to `bank/*.yaml` cannot retroactively alter a past exam paper.
3. Generates deterministic `id` slugs (`--add-ids`) for any question that does not yet have an `id`.

If your university changes its exam paper layout in a new academic year, either place the updated template in `2026-2027/_quizml/` or version the template filename in your root `_quizml/quizml.cfg` (`uni-exam-2026.tex.j2`) so older exams remain reproducible.
