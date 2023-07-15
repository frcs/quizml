# BBQuiz

Tool for converting a list of questions in yaml/markdown to a BlackBoard test or to a Latex exam source file


Here is a quick example. You write the questions in a YAML file, using a
Markdown syntax:

```yaml
- type: ma
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

- type: mc
  marks: 5         
  question: |
    Is this the image of a tree?
    
    ![](figures/tree.png){ width=30em }
    
  answers:
    - answer: "yes"
      correct: false
    - answer: "false"
      correct: true     
```







```
Usage: bbquiz [-h] [-w] [--config CONFIGFILE] [--latextemplate TEMPLATEFILE] [--htmltemplate TEMPLATEFILE] [--zsh] [quiz.yaml]

```




# Installation

```bash
pip install .
```

# Usage


```
Usage: bbquiz [-h] [-w] [--config CONFIGFILE] [--latextemplate TEMPLATEFILE] [--htmltemplate TEMPLATEFILE] [--zsh] [quiz.yaml]

Converts a questions in a YAML/markdown format into a Blackboard test or a Latex script

Positional Arguments:
  quiz.yaml                     path to the quiz in a yaml format

Optional Arguments:
  -h, --help                    show this help message and exit
  -w, --watch                   continuously compiles the document on file change
  --config CONFIGFILE           path to user config file
  --latextemplate TEMPLATEFILE  Latex jinja2 template
  --htmltemplate TEMPLATEFILE   HTML jinja2 template
  --zsh                         A helper command used for exporting the command completion code in zsh
```


# BBYaml Syntax

BBQuiz takes in a YAML file. [YAML](https://en.wikipedia.org/wiki/YAML) is a
generic human-readable data-serialization language, typically used for
configuration files, and it is used here to define the questions' statements,
marks, type, answers, etc.

What is nice with YAML is that all text entries can be written in
[Markdown](https://en.wikipedia.org/wiki/Markdown). This means that question
statements, answers, etc. can be written in Markdown, and using a few basic
Markdown extensions, we can also use LaTex equations and tables.

Below is an example of what an exam script would look like:

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

  desc: |
    This is a BlackBoard exam. 

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

- type: mc
  marks: 5         
  question: |
    Consider the binary class dataset below (with 2 features $(x_1, x_2)$ and
    2 classes (cross and circle). What is the most suitable
    classification technique for this dataset? (choose only one)

    ![](figures/dataset-4.png){ width=30em }
    
  answers:
    - answer: Decision Tree
      correct: false
    - answer: Logistic Regression
      correct: true
    - answer: Random Forest
      correct: false
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
      
```

and this is what the HTML preview looks like:


and this is what the BlackBoard output would look like:



and this is what the pdf output would look like:



## Question Types Syntax

At the moment BBQuiz supports 5 types of questions.

### Essay

The student is execpted to write down a few sentences. The `answer` field
provides an indicative answer that can be used as guideline for marking.

```yaml
- type: essay
  marks: 14
  question: |
    my question statement in Mardown
  answer: |
    an suggestion for how to answer that essay question   
```

### Multiple Choice

In multiple choice questions, only one answer/statement should be selected.

```yaml
- type: mc
  marks: 4
  question: |
    question statement goes here...
  answers:
    - answer:  text for answer 1
      correct: true
    - answer:  text for answer 2
      correct: false
    - answer:  text for answer 3
      correct: false
    - answer:  text for answer 4
      correct: false
```

### Multiple Answers

This is the same as for multiple choices, except that more than one answer can
be true (potentially zero or all statements can be correct).

```yaml
- type: ma
  marks: 4
  question: |
    question statement goes here...
  answers:
    - answer:  text for answer 1
      correct: true
    - answer:  text for answer 2
      correct: false
    - answer:  text for answer 3
      correct: true
    - answer:  text for answer 4
      correct: false
```
### Matching

In Matching questions, the student is asked to map each statement (`answer`)
with its corresponding match (`correct`). For n statements, there are factorial
n possibilities. The pairs of (`answer`,`correct`) statements are shuffled when
generating the exam  (see how to set the random seed).

```yaml
- type: matching
  marks: 5
  question: |
    question statement goes here...
      
  answers:
    - answer: text 1
      correct: text for correct match for text 1
    - answer: text 2
      correct: text for correct match for text 2
    - answer: text 3
      correct: text for correct match for text 3
    - answer: text 4
      correct: text for correct match for text 4 
```

### Ordering

In Ordering questions, the student is asked to rank each statement (`answer`) in
correct order. The statements need to be entered in correct order. Shuffling
occurs when generating the exam (see how to set the random seed). 

```yaml
- type: ordering
  marks: 5
  question: |
    Order the following trees in **decreasing** order of height.
  
  answers:
    - answer: tree 1
    - answer: tree 2
    - answer: tree 3
```

### Header

It is optional to use a header. All (key, val) pairs will be sent to the
template renderer. For instance your LaTex template might require information
about the exam date, venue, etc. The header must be the first item in the BBYaml
file.

```yaml
- type: header
  key1: val1
  key2: val2
  key3: val3
  key4: val4
```

### Random Generator

You can set a random seed generator by assigning the key `srand` (eg. `srand:
42`) in the header.


## Quick Guide to Markdown


Here is what a typical question would look like:

```
    Consider the following system below:
    ![](figures/diagram1.svg){ width=30em }
    compute the output $Y(z)$ for $X(z) = 1 + z^4 + z^{13} + z^{18}$.
```

## Text Tags

https://commonmark.org/help/



# Configuration File and Target Templates

After reading the BBYaml file and converting the markdown entries into LaTex or
HTML, BBQuiz uses jinja2 templates to render the various targets (BlackBoard
quiz, HTML preview, LaTex). 


## Configuration Files Location

The default config file is called `bbquiz.cfg`. 

BBQuiz will first try to read this file in 
1. the local directory from which BBQuiz is called 
2. the default application config dir 
3. the install package templates dir

For instance, on my mac, it will be:
1. `./bbquiz.cfg`
2. `~/Library/Application\ Support/bbquiz/bbquiz.cfg`
3. `~/Library/Python/3.9/lib/python/site-packages/bbquiz/templates/bbquiz.cfg`

You can otherwise directly specify the path with the `--config CONFIGFILE` option.


## Defining Your Own Targets


The list of targets can be defined in the configuration file. For instance, the
BlackBoard csv quiz file can be defined as the following target:
```yaml
- out      : ${inputbasename}.txt  # template for output filename.
                                   #    ${inputbasename} refers to the basename of the quiz
                                   #    (eg. mcq-01.yaml => mcq-01)
  descr    : BlackBoard CSV        # description for the target. 
  descr_cmd: ${inputbasename}.txt  # command to use (here we have no suggestion, so just print output path)
  fmt      : html                  # latex or html: format that markdown gets converted to
  template : bb.jinja              # filename for the jinja template used
```

As for the config file directory, if the templates are defined as a relative
path, the template is searched in:
1. the local directory from which BBQuiz is called 
2. the default application config dir 
3. the install package templates dir


## Writing Your Own Templates

Templates are rendered with Jinja2. The [Jinja2 Template Designer
Documentation](https://jinja.palletsprojects.com/en/3.1.x/templates/) provides
complete information about how to write jinja2 templates.

The default templates used in BBQuiz can be found in the `templates` directory.

Note that to be compatible with both LaTex and HTML, we use following delimiters:
* `<| ... |>`  for Statements
* `<< ... >>`  for Expressions
* `<# ... #>`  for Comments





# Requirements

LaTex installation with `gs` and `pdflatex`.

