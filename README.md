# QuizML

QuizML converts quizzes written in YAML and Markdown into configurable outputs
such as Blackboard imports, HTML previews, Word documents, QTI packages, Moodle
XML, and LaTeX sources or PDFs.

[Read the documentation](https://frcs.github.io/quizml) or start with the
[quick start](https://frcs.github.io/quizml/#/quickstart).

Install QuizML with Python 3.10 or newer:

```bash
python -m pip install quizml
```

Save a quiz as `quiz.yaml`:

```yaml
- type: mc
  marks: 5
  question: Which planet is known as the Red Planet?
  choices:
    - x: Mars
    - o: Venus
    - o: Jupiter

- type: tf
  marks: 5
  question: Is this statement true?
  answer: false
```

Compile the quiz using its configured targets:

```bash
quizml compile quiz.yaml
```

Choose an individual target with `--target`, for example
`quizml compile quiz.yaml --target html-preview`. Available targets depend on
your configuration. Some outputs, such as PDFs or equation images, require
external rendering tools; see the [target guide](https://frcs.github.io/quizml/#/targets)
if you need them.

The animation below shows examples of rendered QuizML outputs.

<img src="docs/figures/demo-output-carousel.gif" width="100%" alt="Examples of QuizML output formats" />

## Documentation

- [Quick start](https://frcs.github.io/quizml/#/quickstart)
- [Quiz structure](https://frcs.github.io/quizml/#/syntax_yaml)
- [Command-line usage](https://frcs.github.io/quizml/#/usage)
- [Project setup](https://frcs.github.io/quizml/#/configuration)
