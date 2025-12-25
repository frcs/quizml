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
- type: mc
  marks: 5           
  question: |
    If vector ${\bf w}$ is of dimension $3 \times 1$ and matrix ${\bf A}$ of
    dimension $5 \times 3$, then what is the dimension of $\left({\bf w}^{\top}{\bf
    A}^{\top}{\bf A}{\bf w}\right)^{\top}$?
  choices:
    - o:  $5 \times 5$
    - o:  $3 \times 3$
    - o:  $3 \times 1$
    - x:  $1 \times 1$
    - o:  $1 \times 5$
    - o:  $1 \times 3$

- type: ma
  marks: 5         
  question: |
    Consider the binary class dataset below (with 2 features $(x_1, x_2)\in\R^2$
    and 2 classes (cross and circle). Select all suitable classification
    techniques for this dataset.

    ![](figures/dataset-4.png){ width=30em }    
  choices:
    - x: Decision Tree
    - x: Logistic Regression
    - x: Random Forest
    - o: Least Squares

- type: matching
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

- type: essay
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
assuming that all key values in the YAML file are strings. 




