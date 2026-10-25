# Quick start <!-- {docsify-ignore} -->

QuizML turns a YAML quiz into one or more configured outputs. You can write a
quiz with any text editor; Python 3.10 or newer is required to install and run
QuizML.

## 1. Install QuizML

```bash
python -m pip install quizml
```

## 2. Write a quiz

Save this as `quiz.yaml`:

```yaml
title: A short practice quiz
---
- type: mc
  marks: 1
  question: Which planet is known as the Red Planet?
  choices:
    - x: Mars
    - o: Venus
    - o: Jupiter

- type: tf
  marks: 1
  question: Earth orbits the Sun.
  answer: true
```

QuizML uses YAML for question fields and Markdown for question text. See
[Quiz structure](syntax_yaml.md) and [Question types](syntax_questions.md) for
more examples.

## 3. Compile and inspect

```bash
quizml compile quiz.yaml
```

QuizML writes the outputs selected by the current configuration beside the
input file. The bundled configuration includes Blackboard (`bb`), HTML preview
(`html-preview`), LaTeX (`latex`, `pdf`), Word (`docx`), QTI (`qti`, `qti21`),
and Moodle XML (`moodle`) targets. Select a particular target with `--target`:

```bash
quizml compile quiz.yaml --target html-preview
quizml compile quiz.yaml --target bb
```

Open the HTML output in a browser to review the questions. To see the targets
available in your configuration, run `quizml targets`.

Some targets use external tools. For example, building a PDF requires a LaTeX
compiler, and rendering equations as SVG or PNG requires LaTeX tools. Other
targets (such as QTI, Moodle XML, and Word) render equations directly as MathML
or Office Math without external tools. See [Targets](targets.md) for details.

## Next steps

- Learn the [quiz file structure](syntax_yaml.md), [question types](syntax_questions.md),
  and [Markdown features](syntax_md.md).
- Read [command-line usage](usage.md) to format files, sample question banks,
  or compile in watch mode.
- Customize outputs in [Project setup](configuration.md), [Targets](targets.md),
  and [Templates](writing_templates.md).
