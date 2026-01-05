## Question Layout

You can control the layout of questions in QuizML to create more complex and visually appealing exams. This includes arranging questions in multiple columns and placing figures alongside the question text.

### Multiple Columns (`cols`)

The `cols` attribute allows you to arrange the content of a question, such as the choices in a multiple-choice question, into multiple columns. This is useful for saving space and for questions with many short options.

The `cols` attribute takes an integer value representing the number of columns.

**Example:**

```yaml
- type: mc
  statement: Which of the following are primary colors?
  cols: 3
  choices:
    - Red
    - Green
    - Blue
    - Yellow
    - Orange
    - Purple
```

This will render the choices in three columns.

### Figures (`figure`)

The `figure` attribute allows you to include a figure in a question. This can be a path to an image file or a LaTeX figure definition.

**Example with an image:**

```yaml
- type: tf
  statement: Is this the image of a bee?
  figure: figures/bee.jpg
  choices:
    - True
    - False
```

**Example with a LaTeX figure:**

```yaml
- type: tf
  statement: Is this the image of a bee?
  figure: |
    \begin{tikzpicture}
      ...
    \end{tikzpicture}
  choices:
    - True
    - False
```

### Side-by-Side Figure and Question (`figure-split`)

The `figure-split` attribute allows you to place a figure and the question text side-by-side. It takes a float value between 0 and 1, which represents the proportion of the total width that the figure will occupy. The remaining space will be used for the question text.

**Example:**

```yaml
- type: mc
  statement: What is shown in the figure?
  figure: figures/diagram.png
  figure-split: 0.4
  choices:
    - A diagram
    - A photo
    - A chart
    - A graph
```

In this example, the figure will occupy 40% of the width, and the question statement and choices will occupy the remaining 60%.

By combining these attributes, you can create a wide variety of question layouts to suit your needs.
