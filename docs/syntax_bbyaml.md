## Test File Syntax <!-- {docsify-ignore} -->

BBQuiz takes in a YAML file. [YAML](https://en.wikipedia.org/wiki/YAML) is a
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

- type: header
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
  pre_latexpreamble: |
    \newcommand{\R}{\mathbb{R}}

- type: mc
  marks: 5           
  question: |
    If vector ${\bf w}$ is of dimension $3 \times 1$ and matrix ${\bf A}$ of
    dimension $5 \times 3$, then what is the dimension of $\left({\bf w}^{\top}{\bf
    A}^{\top}{\bf A}{\bf w}\right)^{\top}$?

  answers:
    - answer:  ${\tt 5}\times {\tt 5}$
      correct: false
    - answer:  ${\tt 3}\times {\tt 3}$
      correct: false
    - answer:  ${\tt 3}\times {\tt 1}$
      correct: false
    - answer:  ${\tt 1}\times {\tt 1}$
      correct: true
    - answer:  ${\tt 1}\times {\tt 5}$
      correct: false
    - answer:  ${\tt 1}\times {\tt 3}$
      correct: false

- type: ma
  marks: 5         
  question: |
    Consider the binary class dataset below (with 2 features $(x_1, x_2)\in\R^2$
    and 2 classes (cross and circle). Select all suitable classification
    techniques for this dataset.

    ![](figures/dataset-4.png){ width=30em }
    
  answers:
    - answer: Decision Tree
      correct: true
    - answer: Logistic Regression
      correct: true
    - answer: Random Forest
      correct: true
    - answer: Least Squares
      correct: false

- type: matching
  marks: 2.5
  question: |
    Match the images to their corresponding PSD (the DC component is at the
    center of the PSD image).

    Explain your choices.     
  answers:
    - answer: |
        ![](figures/psd-16-ori.png){width=30em}
      correct: |
        ![](figures/psd-16-psd.png){width=30em}
    - answer: |
        ![](figures/psd-13-ori.png){width=30em}
      correct: |
        ![](figures/psd-13-psd.png){width=30em}
    - answer: |
        ![](figures/psd-01-ori.png){width=30em}
      correct: |
        ![](figures/psd-01-psd.png){width=30em}
    - answer: |
        ![](figures/psd-25-blur.png){width=30em}
      correct: |
        ![](figures/psd-25-psd-blur.png){width=30em}

- type: essay
  marks: 10
  question: |
    Prove, in no more than a page, that the Riemann zeta function has its zeros
    only at the negative even integers and complex numbers with real part
    $\frac{1}{2}$.
  answer: |
    See handouts for a detailed answer.
        
```


?> BBQuiz uses a particular flavour of YAML called
[StrictYAML](https://github.com/crdoconnor/strictyaml). This is a type-safe YAML
parser that parses and validates a restricted subset of the YAML
specification. StrictYAML avoids some of the YAML oddities such as the [Norway
Problem](https://hitchdev.com/strictyaml/why/implicit-typing-removed).




