## Test File Syntax <!-- {docsify-ignore} -->

QuizML takes in a YAML file. [YAML](https://en.wikipedia.org/wiki/YAML) is a
generic human-readable data-serialization language, typically used for
configuration files, and it is used here to define the questions' statements,
marks, type, answers, etc.

One motivation behind using YAML is that all text entries (e.g., question
statements, answers, etc.) can be written in
[Markdown](https://en.wikipedia.org/wiki/Markdown), and with a few extensions,
it is possible write LaTeX equations, and it will be very similar, in feel and
capabilities to LaTeX.

Below is an longer example of what an exam script would look like:

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
    - o:  $5 \times 5$
    - o:  $3 \times 3$
    - o:  $3 \times 1$
    - x:  $1 \times 1$
    - o:  $1 \times 5$
    - o:  $1 \times 3$

- # <Q2>
  type: ma
  marks: 5         
  question: |
    Consider the binary class dataset below (with 2 features $(x_1, x_2)\in\R^2$
    and 2 classes (cross and circle). Select all suitable classification
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

    Explain your choices.     
  choices:
    - A: |
        ![](figures/psd-16-ori.png){width=30em}
      B: |
        ![](figures/psd-16-psd.png){width=30em}
    - A: |
        ![](figures/psd-13-ori.png){width=30em}
      B: |
        ![](figures/psd-13-psd.png){width=30em}
    - A: |
        ![](figures/psd-01-ori.png){width=30em}
      B: |
        ![](figures/psd-01-psd.png){width=30em}
    - A: |
        ![](figures/psd-25-blur.png){width=30em}
      B: |
        ![](figures/psd-25-psd-blur.png){width=30em}

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


?> QuizML avoids some of the YAML oddities such as the [Norway
Problem](https://hitchdev.com/strictyaml/why/implicit-typing-removed) by
interpreting yaml fields according to the provided schema definition (see
[Schema Validation](schema_validation.md) for more information).


### Question Banking with `_include`

To organize large exams into modular topic files or reuse common question banks, QuizML supports the `- _include:` directive directly inside the questions list:

```yaml
title: Midterm Exam
---
# Inline question
- type: essay
  marks: 5
  question: Introduce yourself and state your student ID.
  answer: Model answer

# Include all questions from topic files
- _include: topics/calculus.yaml
- _include: topics/linear_algebra.yaml
```

#### Relative Paths & Nesting
- **Document-relative**: Included paths are resolved relative to the directory of the file referencing them.
- **Recursive**: Included files can themselves include further sub-files. Cycle detection automatically prevents circular inclusions.
- **Sub-file structure**: Included files can either be a standalone question list or contain their own header document; only questions are imported into the parent exam.

#### Figures & Image Paths in Included Files
When including a file from a different directory that contains images (e.g. `![](fig/diagram.png)`), QuizML automatically handles figure resolution:
- The included file's base directory is automatically registered as a figure search directory relative to the parent exam.
- Any `_figures_path` declared in the included file's own header (e.g. `custom_assets/`) is resolved relative to that sub-file and added to the parent exam's figure search paths.
- Both HTML Base64 embedding and LaTeX compilation (`\graphicspath`) resolve these assets seamlessly without altering question text or assuming magic subfolders.

#### Automatic Renumbering & Searchability (`quizml --format`)
When running `quizml --format`, QuizML renumbers questions and decorates includes with all the question numbers they introduce:
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
This preserves fast text-search workflows (`/<Q3>` in your text editor jumps directly to the include containing Q3).


