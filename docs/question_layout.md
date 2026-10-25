# Question Layout <!-- {docsify-ignore} -->

Question layout fields make exams more compact by arranging choices in columns
or placing a figure beside a question.

!> The bundled LaTeX (`tcd-exam.tex.j2`), HTML preview (`preview.html.j2`), and
Word (`tcd-exam.docx`) templates support layout fields (`cols` in LaTeX, HTML,
and Word; `figure` and `figure-split` in LaTeX and HTML). LMS import formats
(Blackboard, QTI, Moodle) ignore page-layout hints.

## Multiple columns (`cols`)

The `cols` attribute arranges the choices of a Multiple Choice (`mc`), Multiple
Answers (`ma`), or Ordering (`ordering`) question into multiple columns—useful
when choices are short expressions or numbers.

```yaml
- type: ma
  question: Which of the following are primary colors?
  cols: 3
  choices:
    - x: Red
    - x: Green
    - x: Blue
    - o: Yellow
    - o: Orange
    - o: Purple
```

## Figures (`figure`) and side-by-side split (`figure-split`)

The `figure` attribute attaches a dedicated figure block (an image, table, or
code listing) to a question. Combine `figure` with `figure-split` (a number
between `0` and `1` giving the fraction of the width allocated to the figure) to
place the figure alongside the question stem and choices:

```yaml
- type: mc
  question: What is shown in the figure?
  figure: "![](figures/diagram.png)"
  figure-split: 0.6
  choices:
    - x: A diagram
    - o: A photo
    - o: A chart
    - o: A graph
```

Here the figure occupies 60% of the width and the question text and choices
occupy the remaining 40%.

A `figure` block can contain any Markdown, including a fenced code listing:

```yaml
- type: tf
  question: Does this function sort the list in ascending order?
  figure: |
    ```python
    def sort_list(items):
        return sorted(items)
    ```
  figure-split: 0.5
  answer: true
```
