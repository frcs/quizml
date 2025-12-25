# Usage


This document explains how to use the `quizml` command-line tool, which converts questions in a YAML/markdown format into a Blackboard test or a LaTeX script.


### TL;DR

* Compile all targets
```bash
quizml quiz.yaml
```

* Re-compile all targets every time `quiz.yaml` changes:

```bash
quizml -w quiz.yaml
```

* Compile all targets and also run post-build commands, eg. including running LaTeX on the
  rendered `quiz.tex` to produce `quiz.pdf`:

```bash
quizml --build quiz.yaml
```

* Compile just one target, eg. the BlackBoard quiz:

```bash
quizml -t bb quiz.yaml
```


### Syntax


```bash
Usage: quizml [-h] [-w] [-t TARGET] [--target-list] [--init-local] [--init-user] [--config CONFIGFILE] [--build] [--diff] [-C]
              [--print-package-templates-path] [--shell-completion {bash,zsh,fish}] [-v] [--debug] [--verbose] [--quiet]
              [quiz.yaml] [otherfiles ...]
```

### Positional Arguments

* `quiz.yaml`: The primary input file containing the quiz questions in YAML format.
* `otherfiles`: (Optional) Additional YAML files to compare questions against the primary `quiz.yaml` file (only used with `--diff` command).

### Optional Arguments

* `-h`, `--help`: Show this help message and exit.
* `-w`, `--watch`: Continuously compiles the document on file change.
* `-t`, `--target TARGET`: Specific target names to compile (e.g. 'pdf', 'html-preview'). Can be specified multiple times.
* `--target-list`: List all targets defined in the configuration file.
* `--init-local`: Create a local directory 'quizml-templates' with all configuration files.
* `--init-user`: Create the user application directory with all its configuration files.
* `--config CONFIGFILE`: Sets path to a specific config file.
* `--build`: Compiles all targets and runs all post-compilation commands.
* `--diff`: Compares questions from the first YAML file to the rest of the files.
* `-C`, `--cleanup`: Deletes build artefacts from all YAML files in the current directory.
* `--print-package-templates-path`: Print the path for QuizML's package templates directory.
* `--shell-completion {bash,zsh,fish}`: Print shell completion script for the specified shell.
* `-v`, `--version`: Show program's version number and exit.
* `--debug`: Print lots of debugging statements.
* `--verbose`: Set verbose mode on.
* `--quiet`: Turn off informational statements.


### Examples

* Running QuizML on the simple example:

```shell-session
$ quizml quiz1.yaml

     Q  Type  Marks  #  Exp  Question Statement
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     1   mc     5.0  4  1.2  If vector ${\bf w}$ is of dimension $3 \times 1$ and matrix ${\bf A}$ of...
     2   tf     5.0  2  2.5  Is this the image of a tree?

    Total: 10.0 (with random expected mark at 37.5%)

╭────────────────────────────────────── Target Ouputs ──────────────────────────────────────╮
│                                                                                           │
│   BlackBoard CSV   quiz1.txt                                                              │
│   html preview     quiz1.html                                                             │
│   latex            latexmk -xelatex -pvc quiz1.tex                                        │
│   Latex solutions  latexmk -xelatex -pvc quiz1.solutions.tex                               │
│                                                                                           │
╰───────────────────────────────────────────────────────────────────────────────────────────╯
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
$ quizml --build quiz1.yaml
```

* Continuously compiling on file change:

When editing a test, you can continuously watch for any file change and
recompile the target by setting the flag `-w`:

```shell-session
$ quizml -w quiz1.yaml
```

### Running as a Module

You can also run QuizML directly as a Python module, which is useful for development or if the `quizml` executable is not in your path:

```bash
python3 -m quizml quiz.yaml
```

