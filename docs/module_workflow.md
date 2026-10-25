# Question banks <!-- {docsify-ignore} -->

This guide shows how to organize reusable question banks, sample or cherry-pick
questions across quizzes, check for duplicates across academic years, and freeze
finalized exams.

## Example repository layout

You can place module-wide configuration and custom templates in a root
`_quizml/` directory (created with `quizml init`; see
[Project setup](configuration.md)). Because QuizML walks up parent directories
from the quiz file being compiled to discover `_quizml/quizml.cfg`, you can
compile any quiz from the repository root or from inside a subfolder:

```text
EE401-Deep-Learning/
├── _quizml/                    # Module-wide config & custom templates
│   ├── quizml.cfg
│   ├── uni-exam.tex.j2
│   └── uni-logo.pdf
├── bank/                       # Shared topic question banks
│   ├── 01-linear-models.yaml
│   ├── 02-cnn.yaml
│   └── figs/
├── 2024-2025/
│   └── exams/
│       └── final.yaml          # Frozen & pinned archival exam
└── 2025-2026/
    ├── bbq/
    │   └── week01.yaml
    └── exams/
        ├── midterm.yaml
        └── final.yaml
```

## Question IDs and cherry-picking (`select`)

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

You can then cherry-pick specific questions into an exam by `id` (or 1-based
question index) using `select`:

```yaml
title: Final Examination 2025/26
_targets: [pdf, html-preview]
---
- _include: ../../bank/02-cnn.yaml
  select:
    - cnn-receptive-field
    - cnn-parameter-count
```

## Random sampling (`quizml sample`)

An `_include` with `count` describes a random sample from a question bank:

```yaml
title: Week 1 Practice Quiz
---
- _include: ../../bank/01-linear-models.yaml
  count: 5
  seed: 42
```

To keep compilation deterministic, `quizml compile` does not perform random
selection on the fly. Instead, materialize the sample into a static YAML file
with `quizml sample` and compile the generated file:

```bash
quizml sample week01.meta.yaml -o week01.yaml
quizml compile week01.yaml --target bb
```

Each sampled include uses its `seed` in the YAML (or a fallback passed via
`quizml sample --seed`).

## Checking for reused questions (`quizml diff`)

Before finalizing an exam paper, check whether any questions overlap with
previous years' papers:

```bash
quizml diff 2025-2026/exams/final.yaml 2024-2025/exams/final.yaml 2023-2024/exams/final.yaml
```

`quizml diff` flags questions from the first file that appear in any of the
comparison files, matching either by identical `id` or by question type and
$\ge 90\%$ stem similarity with overlapping choices. Pass `--check` in CI
scripts to exit with status `1` if duplicates are found.

## Archiving and pinning past exams (`quizml pin`)

Once an exam paper is finalized, freeze and stamp it with `quizml pin`:

```bash
quizml pin 2025-2026/exams/final.yaml --add-ids --freeze-includes -t pdf
```

This command:
1. Stamps `_quizml` (e.g. `">=0.12,<0.13"`) and `_targets` into the YAML header
   so future builds warn if the installed QuizML version is incompatible.
2. Expands `_include` directives in place (`--freeze-includes`) so later edits
   to `bank/*.yaml` cannot retroactively alter a past exam paper.
3. Generates deterministic `id` slugs (`--add-ids`) for any question that does
   not yet have an `id`.
