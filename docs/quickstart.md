## Quick Start

### Installation 

This is a command line application written in Python. Assuming that you have
python and pip installed, you can simply install it with:

```shell-session
$ pip install quizml
```

### LaTeX

You will need a LaTeX installation with `gs` and `pdflatex` (e.g.,
[MacTeX](https://www.tug.org/mactex/) or `texlive`). 

You might also want to install `librsvg` to automatically convert `.svg` files
to `.pdf`.


### Configuration File and Templates

Out-of-the-box, QuizML comes with a number of template targets:

* BlackBoard test
* LaTeX exam 
* HTML preview

If you only care about the BlackBoard tests and/or the HTML preview, then QuizML
should just work fine as it is.

If you want to use the LaTeX exam target, chances are that you'll want to adapt
the template to your liking, e.g. at the very least changing the University
name, etc.

To do this, you'll need to edit the config file and the templates that are
provided.

More details are given in the [configuration section](configuration) about how
to specify template targets and in the [LaTeX setup section](config_latex).

To get you started,

```shell-session
$ quizml --init-local
```
This will copy a default `quizml.cfg` and all the provided templates to a newly
created 
`quizml-templates/` sub-directory. 

Alternatively you can make a user-level install with:

```shell-session
$ quizml --init-user
```

In this case `quizml.cfg` and the rest of the files will be moved to the default
user configuration directory (eg. `~/Library/Application\ Support/quizml/` on my
mac).






