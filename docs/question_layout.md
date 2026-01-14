## Question Layout

You can control the layout of questions in QuizML to create more compact exams. This includes arranging questions in multiple columns and placing figures alongside the question text.

!> Only the Latex template (`tcd-eleceng-latex`) fully implements these
features. Other templates will silently ignore layout indications.

### Multiple Columns (`cols`)

The `cols` attribute allows you to arrange the choices of a question, such as in
a multiple-choice question or multiple-answer questions, into multiple
columns. This is useful for saving space and for questions with many short
options.

The `cols` attribute takes an integer value representing the number of columns.

**Example:**

```yaml
- type: mc
  question: Which of the following are primary colors?
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

The `figure` attribute allows you to include a figure in a question. Alone this
does not do much, the idea is to use it in conjonction with `figure-split`.

**Example with an image:**

```yaml
- type: mc
  question: Is this the image of a bee?
  figure: figures/bee.jpg
  choices:
    - True
    - False
```

**Example with a Code Listing:**

```yaml
- type: tf
  question: Is this the code of a sort function?
  figure: |
    ```python
    def sort_list(items):
        return sorted(items)
    ```
  answer: True
```

### Side-by-Side Figure and Question (`figure-split`)

The `figure-split` attribute allows you to place a figure and the question text
side-by-side. It takes a float value between 0 and 1, which represents the
proportion of the total width that the figure will occupy. The remaining space
will be used for the question text.

**Example:**

```yaml
- type: mc
  question: What is shown in the figure?
  figure: ![](figures/diagram.png)
  figure-split: 0.6
  choices:
    - A diagram
    - A photo
    - A chart
    - A graph
```

In this example, the figure will occupy 60% of the width, and the question
 choices will occupy the remaining 40%.

By combining these attributes, you can create a wide variety of question layouts
to suit your needs.
