# Usage


This document explains how to use the `bbquiz` command-line tool, which converts questions in a YAML/markdown format into a Blackboard test or a LaTeX script.


### TL;DR

* Compile all targets
```bash
bbquiz quiz.yaml
```

* Re-compile all targets every time `quiz.yaml` changes:

```bash
bbquiz -w quiz.yaml
```

* Compile all targets and also run post-build commands, eg. run LaTeX on the
  rendered `quiz.tex` to produce `quiz.pdf`:

```bash
bbquiz --build quiz.yaml
```


### Syntax


```bash
Usage: bbquiz [-h] [-w] [--config CONFIGFILE] [--build] [--diff] [--zsh]
[--fish] [-v] [--debug] [--verbose] [quiz.yaml] [otherfiles [otherfiles ...]]

```

### Positional Arguments

* `quiz.yaml`: The primary input file containing the quiz questions in YAML format.
* `otherfiles`: (Optional) Additional YAML files to compare questions against the primary `quiz.yaml` file.

### Optional Arguments

* `-h`, `--help`: Show this help message and exit.
* `-w`, `--watch`: Continuously compiles the document on file change.
* `--config CONFIGFILE`: Sets path to config file. See the [Configuration
  section](config_files) for default config files locations and [how to edit the
  config file](targets)

* `--build`: Compiles all targets and run all post-compilation commands.
* `--diff`: Compares questions from the first YAML file to the rest of the files.
* `--zsh`: A helper command used for exporting the command completion code in zsh.
* `--fish`: A helper command used for exporting the command completion code in fish.
* `-v`, `--version`: Show program's version number and exit.
* `--debug`: Print lots of debugging statements.
* `--verbose`: Set verbose on.


### Examples

* Running BBQuiz on the simple example:

```shell-session
$ bbquiz quiz1.yaml

..  pdflatex compilation

  Q  Type  Marks  #    Exp  Question Statement
 ────────────────────────────────────────────────────────────────────────
  1   mc     5.0  4    1.2  If vector ${\bf w}$ is of dimension $3
                            \times 1$ and matrix ${\bf A}$ of […]
  2   mc     5.0  2    2.5  Is this the image of a tree? […]
 ────────────────────────────────────────────────────────────────────────
  2   --    10.0  -  37.5%

╭──────────────────────────── Target Ouputs ─────────────────────────────╮
│                                                                        │
│   BlackBoard CSV   quiz1.txt                                           │
│   html preview     quiz1.html                                          │
│   latex            latexmk -xelatex -pvc quiz1.tex                     │
│   Latex solutions  latexmk -xelatex -pvc quiz1.solutions.tex           │
│                                                                        │
╰────────────────────────────────────────────────────────────────────────╯
```

The command returns a table that summarises some statistics about this
exam. Namely, it lists all the questions, their types, their marks, the number
of possible options per question, the expected mark if it is answered randomly.

The rendered target outputs are shown at the end. It will also indicate how to
further compile the output if it is required. For instance, to compile the
generated LaTeX into a pdf, you can do it with:

```shell-session
$ latexmk -xelatex -pvc quiz1.tex
```


* Running post-build scripts:

You can automate these additional compilations by setting the `--build` flag:

```shell-session
$ bbquiz --build quiz1.yaml
```

* Continuously compiling on file change:

When editing a test, you can continuously watch for any file change and
recompile the target by setting the flag `-w`:

```shell-session
$ bbquiz -w quiz1.yaml
```

