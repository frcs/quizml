## The Header Section<!-- {docsify-ignore} -->

An optional header section can be declared at the start of the yaml file. All
(key, val) pairs declared in this section will be sent to the template
renderer. For instance your LaTeX template might require information about the
exam date, venue, etc. The header must be declared at the start of the file and
must be separated from the rest of the questions with a line starting with
`---`.

The bundled schema checks the types of commonly used header fields and
`_figures_path`. Other header keys are allowed, so templates can use
project-specific metadata without extending the schema. Plain YAML `null`
values are loaded as `None`; quote `"null"` when the literal text is intended.

```yaml
descr: |
  A very long exam
  
  You are all going to suffer.

venue: Maxwell Theatre
date: 13/05/2024
---
- type: "tf"
  question: is the Earth flat?
  answer: true
```

!> Note that it is recommended for the key names to only contain uppercase and
lowercase alphabetical characters: a-z and A-Z, without any numeral or other
non-letter character.  This is because the LaTeX template copies the keys
accross as TeX macros:

```tex
\def\infodescr{
    A very long exam
    
    You are all going to suffer.
}
\def\infovenue{Maxwell Theatre}
\def\infodate{13/05/2024}
```

Hence, as each key will be turned into a LaTeX macro, it must also follow LaTeX
syntax macro naming rules.

!> All keys' values will be interpreted as Markdown. 

!> If your key starts with the prefix `_` (eg. `_latexpreamble`), the
value will not be interpreted as markdown and it will not be turned into a macro
by the LaTeX template.

### Built-in Control Keys (Optional)

All header keys are optional, but the following `_`-prefixed keys have special
meaning when present:

- `_targets`: Target name or list of target names (e.g. `[pdf, preview]` or `bb`)
  to build for this file when `-t`/`--target` is not passed on the CLI.
- `_quizml`: Version constraint (e.g. `">=0.12,<0.13"` or `"~=0.12"`). QuizML
  prints a warning if the running version does not satisfy the constraint.
- `_schema`: Path to a custom JSON or YAML schema file for validating this quiz.
- `_config`: Path to a custom `quizml.cfg` file for compiling this quiz.
- `_figures_path`: Additional directory or list of directories searched for
  figures and LaTeX inputs.
- `_latexpreamble`: Raw LaTeX preamble declarations injected into equation and
  document builds.

Run `quizml pin exam.yaml` to stamp `_quizml` and `_targets` automatically.
