# Quiz structure <!-- {docsify-ignore} -->

A QuizML file is a YAML document containing a list of questions. An optional
[header section](syntax_header.md) can hold metadata such as the quiz title,
course, or date. Separate the header from the question list with `---`. Question
text and answers use [Markdown and LaTeX equations](syntax_md.md).

Here is an example with a header and four questions:

```yaml
author: François Pitié
date: Semester 2 - 2020/2021
title: EEU44C08/EE5M08 Exam
examtime: 14:00--16:00
examdate: 23/04/2021
examyear: 2021
examvenue: online
examsemester: Semester 2
programmeyear: Senior Sophister
modulename: Image and Video Processing
modulecode: EEU44C08-1
examiner: Dr. F. Pitié
instructions: ""
materials: ""
additionalinformation: ""
_latexpreamble: |
  \newcommand{\R}{\mathbb{R}}

---

- # <Q1>
  type: mc
  marks: 5
  question: |
    If vector ${\bf w}$ is of dimension $3 \times 1$ and matrix ${\bf A}$ of
    dimension $5 \times 3$, then what is the dimension of $\left({\bf w}^{\top}{\bf
    A}^{\top}{\bf A}{\bf w}\right)^{\top}$?
  cols: 3
  choices:
    - o: $5 \times 5$
    - o: $3 \times 3$
    - o: $3 \times 1$
    - x: $1 \times 1$
    - o: $1 \times 5$
    - o: $1 \times 3$

- # <Q2>
  type: ma
  marks: 5
  question: |
    Consider the binary class dataset below (with 2 features $(x_1, x_2)\in\R^2$
    and 2 classes, cross and circle). Select all suitable classification
    techniques for this dataset.

    ![](figures/dataset-4.png){ width=30em }
  cols: 2
  choices:
    - x: Decision Tree
    - x: Logistic Regression
    - x: Random Forest
    - o: Least Squares

- # <Q3>
  type: matching
  marks: 2.5
  question: |
    Match the images to their corresponding PSD (the DC component is at the
    center of the PSD image).
  choices:
    - A: |
        ![](figures/psd-16-ori.png){width=30em}
      B: |
        ![](figures/psd-16-psd.png){width=30em}
    - A: |
        ![](figures/psd-13-ori.png){width=30em}
      B: |
        ![](figures/psd-13-psd.png){width=30em}

- # <Q4>
  type: essay
  marks: 10
  question: |
    Prove, in no more than a page, that the Riemann zeta function has its zeros
    only at the negative even integers and complex numbers with real part
    $\frac{1}{2}$.
  answer: |
    See handouts for a detailed answer.
```

QuizML uses its schema to validate question fields and coerce their values,
preventing YAML implicit-typing surprises. See
[Schema validation](schema_validation.md) for details.

## Reusing questions with `_include`

For larger exams or modular topic files, `- _include:` imports questions from
another YAML file:

```yaml
title: Midterm Exam
---
- type: essay
  marks: 5
  question: Introduce yourself and state your student ID.

# Include every question from a topic file
- _include: topics/calculus.yaml

# Cherry-pick specific questions by ID or 1-based index
- _include: banks/linear_algebra.yaml
  select: [eigenvalues-intro, 4]
```

Included paths are resolved relative to the file containing the `_include`
directive, and includes can be nested. Any figures referenced by an included
file are resolved relative to that file's directory automatically.

For randomized sampling (`count` and `seed` with `quizml sample`), duplicate
detection (`quizml diff`), and freezing exams (`quizml pin`), see
[Question banks](module_workflow.md).

## Formatting and question numbering (`quizml fmt`)

Run `quizml fmt exam.yaml -i` to format YAML in place and stamp `# <Q1>`
comments on each question and `_include` entry:

```yaml
- # <Q1>
  type: essay
  question: First question

- # <Q2>, <Q3>, <Q4>
  _include: bank.yaml

- # <Q5>
  type: essay
  question: Next question
```

This makes it easy to jump directly to a question number (such as `/<Q3>`) in
your text editor, even when questions come from included files.
