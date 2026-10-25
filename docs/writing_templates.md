# Customize templates <!-- {docsify-ignore} -->

QuizML renders text outputs with Jinja2, Word documents with `docxtpl`, and QTI
packages from directory templates. To customize a bundled template, copy it into
`_quizml/` using `quizml init` (see [Project setup](configuration.md)).

Run `quizml compile --verbose quiz.yaml` to verify which template file is
selected during a build.

## Jinja text templates

To avoid conflicts with LaTeX braces and percent signs, QuizML's Jinja2
environment uses custom delimiters:

- `<| ... |>` for statements and control flow
- `<< ... >>` for expressions
- `<# ... #>` for comments

A minimal template loops over `questions` and reads metadata from `header`:

```jinja
<| for q in questions |>
Question << loop.index >> (<< q.marks >> marks):
<< q.question >>
<| endfor |>
```

All Markdown fields in `header` and `questions` are already transcoded according
to the target's `markdown` settings before they reach the template.

### Template inheritance

Templates can `extends`, `include`, and `import` other templates resolved
through QuizML's template search paths. Give an extending template a different
filename from its parent so it does not resolve to itself.

The bundled `tcd-exam.tex.j2` template defines overridable blocks (`preamble`,
`document_start`, `solution_key`, `question_list`, and `document_end`):

```jinja
<| extends "tcd-exam.tex.j2" |>

<| block preamble |>
<< super() >>
\newcommand{\myexamcommand}{...}
<| endblock |>
```

### Strict undefined variables

QuizML uses strict undefined-variable checking so typos in template expressions
fail immediately rather than rendering as empty strings. Guard optional fields
with `is defined` or the `default` filter:

```jinja
<< q.comments | default('') >>
```

See the [Jinja template documentation](https://jinja.palletsprojects.com/en/3.1.x/templates/)
for the full template language reference, and [Targets](targets.md) for passing
extra `context` variables or custom `jinja_filters`.
