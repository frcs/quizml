# BBQuiz

Tool for converting a list of questions in yaml/markdown to a BlackBoard test or
to a Latex exam source file

Here is a minimal example of a `quiz.yaml` file. You write the questions in a YAML
file, using a Markdown syntax:

```yaml
- type: mc
  marks: 5           
  question: |
    If vector ${\bf w}$ is of dimension $3 \times 1$ and matrix ${\bf A}$ of
    dimension $5 \times 3$, then what is the dimension of $\left({\bf w}^{\top}{\bf
    A}^{\top}{\bf A}{\bf w}\right)^{\top}$?
  choices:
    - o:  $5\times 5$
    - o:  $3\times 3$
    - o:  $3\times 1$
    - x:  $1\times 1$

- type: tf
  marks: 5         
  question: |
    Is this the image of a tree?
    
    ![](figures/bee.jpg){ width=30em }
    
  answer: false
```

Then you can generate the BlackBoard exam, LaTeX, and HTML preview using the
following command in the terminal:

```
bbquiz quiz.yaml
```

and this is what the provided default HTML preview looks like:

<img src="docs/figures/html-screenshot.jpg" width="260" />

and this is what the BlackBoard output would look like:

<img src="docs/figures/bb-screenshot.jpg" width="500" />

and this is what the provided LaTeX template pdf output would look like:

<img src="docs/figures/pdf-screenshot.jpg" width="500" />


# Getting Started

This is a command line application. Assuming that you have python and pip
installed, you can simply install it with:

```bash
pip install .
```

You will also need a LaTeX installation with `gs` and `pdflatex`.


