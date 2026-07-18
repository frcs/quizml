# QuizML Test Creation Guide

QuizML is a YAML-based format for writing exams and quizzes. It uses a combination of YAML structure, Markdown formatting, and LaTeX extensions. When writing QuizML tests, follow these rules and structures.

## 1. Overall Structure
A QuizML file consists of an optional header section and a list of questions, separated by `---`.

```yaml
author: "Author Name"
date: "Date"
_latexpreamble: |
  \newcommand{\R}{\mathbb{R}}
---
- type: tf
  marks: 1
  question: |
    Is this a question?
  answer: true
```
- **Header Keys**: Should use only `a-z` and `A-Z` (no numbers or symbols). Values are interpreted as Markdown unless the key starts with an underscore `_` (e.g., `_latexpreamble`).
- **Questions**: Must be defined as a YAML list (`-`) under the `---` separator.

## 2. Formatting (Markdown & LaTeX)
- Use standard Markdown (`**bold**`, `*italic*`, lists, `![](image.png){width=30em}`).
- Inline LaTeX uses `$`, `\(` or `\)`. Display math uses `$$`, `\[`, `\]`, or environments like `\begin{align*}...\end{align*}` (display math blocks must be on their own line).

## 3. Question Types

### Essay (`essay`)
Student writes an open-ended response.
```yaml
- type: essay
  marks: 10
  question: |
    Write a short essay on AI.
  answer: |
    Indicative answer for marking.
```

### True/False (`tf`)
```yaml
- type: tf
  marks: 2
  question: |
    The earth is flat.
  answer: false
```

### Multiple Choice (`mc`)
Only one correct statement (`- x:` for correct, `- o:` for incorrect).
```yaml
- type: mc
  marks: 4
  question: |
    What is the capital of France?
  choices:
    - x: Paris
    - o: London
    - o: Berlin
```

### Multiple Answers (`ma`)
Multiple correct statements allowed.
```yaml
- type: ma
  marks: 4
  question: |
    Select all prime numbers.
  choices:
    - x: 2
    - x: 3
    - o: 4
```

### Matching (`matching`)
Match statement `A` with corresponding `B`.
```yaml
- type: matching
  marks: 5
  question: |
    Match the country to its capital.
  choices:
    - A: France
      B: Paris
    - A: Japan
      B: Tokyo
```

### Fill in the Blank (`fill`)
Single blank space indicated by `____`.
```yaml
- type: fill
  marks: 5
  question: |
    The color of the sky is _____.
  answers:
    - blue
    - Blue
```

### Fill in Multiple Blanks (`mfill`)
Multiple variables defined in brackets `[ ]`.
```yaml
- type: mfill
  marks: 5
  question: |
    Roses are [c1] and violets are [c2].
  answers:
    c1:
      - red
      - Red
    c2:
      - blue
      - Blue
```

### Calculated Numeric (`num`)
Numeric answers with a tolerance.
```yaml
- type: num
  marks: 5
  question: |
    Value of $\pi$ (2 decimal places)?
  answer: 3.14
  tolerance: 0.01
```

### Ordering (`ordering`)
Rank statements in the correct order.
```yaml
- type: ordering
  marks: 5
  question: |
    Rank these planets closest to farthest from the sun.
  choices:
    - Mercury
    - Venus
    - Earth
```
