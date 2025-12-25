
## Installation 

This is a command line application written in Python. Assuming that you have
python and pip installed, you can simply install it with:

```shell-session
$ pip install .
```

## LaTeX

You will need a LaTeX installation with `gs` and `pdflatex` (e.g., [MacTeX](https://www.tug.org/mactex/) or `texlive`).

For handling **SVG images** in LaTeX output:
* QuizML will automatically look for a `.pdf`, `.png`, or `.jpg` version of the image in the same directory.
* If only an `.svg` is present, it will attempt to convert it to PDF using `rsvg-convert` or `inkscape`.
* Therefore, installing `librsvg` (which provides `rsvg-convert`) or `inkscape` is recommended but **optional** if you provide fallback images (e.g., `.png`).


## Configuration File and Templates

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
This will copy a `quizml.cfg` to the current directory and copy all templates to
`quizml-templates/`. You can then copy the relevant files to the correct directory.

Alternatively you can make a user-level install with:

```shell-session
$ quizml --init-user
```

In this case `quizml.cfg` and the rest of the files will be moved to XXX







