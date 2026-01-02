# QuizML   <!-- {docsify-ignore} -->

> QuizML is a command line tool for converting a list of questions in
> yaml/markdown to a BlackBoard test or to a Latex exam source file.

Questions are written in a YAML file, using a Markdown syntax. Here is a minimal
`quiz.yaml` example:

```yaml
- type: mc
  marks: 5           
  question: |
    If vector ${\bf w}$ is of dimension $3 \times 1$ and matrix ${\bf A}$ of
    dimension $5 \times 3$, then what is the dimension of $\left({\bf
    w}^{\top}{\bf A}^{\top}{\bf A}{\bf w}\right)^{\top}$?
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

Then you can generate multiple render targets, including BlackBoard test, LaTeX,
and an HTML preview. 

```shell-session
$ quizml quiz1.yaml

  Q  Type  Marks  #  Exp  Question Statement
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1   mc     5.0  4  1.2  If vector ${\bf w}$ is of dimension $3 \times 1$ ...
  2   tf     5.0  2  2.5  Is this the image of a tree?

  Total: 10.0 (with random expected mark at 37.5%)

╭──────────────────────────────── Target Ouputs ────────────────────────────────╮
│                                                                               │
│   BlackBoard CSV   quiz1.txt                                                  │
│   html preview     quiz1.html                                                 │
│   latex            latexmk -xelatex -pvc quiz1.tex                            │
│   Latex solutions  latexmk -xelatex -pvc quiz1.solutions.tex                  │
│                                                                               │
╰───────────────────────────────────────────────────────────────────────────────╯
```

and this is what the rendered outputs look like:

<img src="figures/demo-output-carousel.gif" width="800px" />



