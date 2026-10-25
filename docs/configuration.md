# Project setup <!-- {docsify-ignore} -->

QuizML uses `quizml.cfg` to define output targets and shared project settings.
Out of the box, QuizML uses its bundled configuration and templates; create a
project config only when you want to customize targets, templates, or schema
rules.

## Initialize a project (`quizml init`)

Run `quizml init` in your project root to create `_quizml/quizml.cfg`:

```bash
# Create _quizml/quizml.cfg (inherits bundled templates by default)
quizml init

# Copy specific bundled templates into _quizml/ for customization
quizml init --latex
quizml init --html
quizml init --bb
quizml init --docx
quizml init --schema

# Copy an individual template file or all bundled assets
quizml init -t tcd-exam.tex.j2
quizml init --all
```

To initialize a per-user configuration shared across projects, run
`quizml init user`. Existing files are never overwritten unless you pass
`--force` (`-f`).

## How QuizML finds configuration and assets

When compiling a quiz, QuizML searches for `quizml.cfg` in the following order:

1. An explicit path passed via `--config FILE` on the CLI or `_config:` in the
   quiz YAML header.
2. `_quizml/quizml.cfg` or `quizml.cfg` in the quiz file's directory or any
   ancestor directory up to the repository root (as well as from the current
   working directory).
3. The user configuration directory (reported by `quizml info`).
4. The bundled package defaults.

Any relative template, CSS, preamble, or schema path referenced by `quizml.cfg`
is searched in `_quizml/` and the directory containing the active `quizml.cfg`
before falling back to user and package defaults. Run
`quizml compile --verbose quiz.yaml` to inspect the exact config and template
paths resolved for a build.

## Default targets and aliases

In `quizml.cfg`, `default_targets` controls which targets are built when
`quizml compile` is run without `--target`. If `default_targets` is omitted,
QuizML compiles all render targets and skips targets with a `build_cmd` (such
as `pdf`) unless they are requested explicitly.

Use `aliases` to group targets into named workflows selectable with `--target`:

```yaml
default_targets:
  - html-preview
  - bb

aliases:
  build:
    - bb
    - html-preview
    - pdf
    - pdf-solutions
```

Running `quizml compile quiz.yaml --target build` compiles all listed targets
and their dependencies in topological order.

## Project-level settings

Beyond `targets`, `default_targets`, and `aliases`, `quizml.cfg` supports
several top-level settings:

```yaml
# Custom schema file or inline schema extensions
schema_path: schema.json
schema_extensions:
  question_properties:
    topic: { type: string }

# Extra directories searched by LaTeX (prepended to TEXINPUTS)
texinputs:
  - shared
  - ../exam-assets

# Custom Jinja2 filters (name: module:callable)
jinja_filters:
  slugify: urllib.parse:quote_plus

# Override external binary names or paths
tools:
  pdflatex: xelatex
  gs: gs
  dvisvgm: dvisvgm
```

### LaTeX asset paths (`texinputs`)

When compiling LaTeX targets or rendering SVG/PNG equations, TeX searches for
custom `.cls`, `.sty`, and image files in:
1. The quiz directory and any included question-bank figure directories.
2. Discovered `_quizml/` project directories.
3. Directories listed under `texinputs` in `quizml.cfg` (resolved relative to
   the directory containing `quizml.cfg`).
4. Your system's standard `TEXMF` trees.

See [Targets](targets.md), [Templates](writing_templates.md), and
[Schema validation](schema_validation.md) for details on customizing individual
outputs.
