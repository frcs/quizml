## Usage


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

* Export an IMS QTI 1.2 ZIP package (Canvas, Blackboard Ultra/Learn, Moodle, Brightspace):

```bash
quizml -t qti quiz.yaml
```



### Syntax


```bash
Usage: quizml [-h] [-w] [-t TARGET] [--target-list] [--init-local] [--init-user]
              [--config CONFIGFILE] [--build] [--diff] [--format] [--ingest]
              [--transcode FMT] [--render TEMPLATE] [-C] [--info]
              [--shell-completion {bash,zsh,fish}] [--no-pager] [--docs [TOPIC]] [-v]
              [--debug] [--verbose] [--quiet]
              [quiz.yaml] [otherfiles ...]
```

Converts a questions in a YAML/markdown format into a Blackboard test or a LaTeX script

### Positional Arguments

* `quiz.yaml`: path to the quiz in a yaml format (or `-` / omit to read from stdin)
* `otherfiles`: other yaml files (only used with diff command)

### Optional Arguments

* `-h`, `--help`: show this help message and exit
* `-w`, `--watch`: continuously compiles the document on file change
* `-t`, `--target TARGET`: target names (e.g. 'pdf', 'html-preview', 'qti', 'qti21')
* `--target-list`: list all targets in config file
* `--init-local`: create a local directory 'quizml-templates' with all config files
* `--init-user`: create the user app directory with all its config files
* `--config CONFIGFILE`: user config file. Default location is
  `/Users/fpitie/Library/Application Support/quizml`
* `--build`: compiles all targets and run all post-compilation commands
* `--diff`: compares questions from first yaml file to rest of files
* `--format`: formats and renumbers questions in the yaml file
* `--ingest`: parse and validate the quiz YAML, then print the coerced JSON intermediate representation (IR) to stdout
* `--transcode FMT`: transcode markdown fields to target format (e.g. 'html', 'latex') and print JSON IR to stdout
* `--render TEMPLATE`: render document using the specified Jinja2 or Word template and print output to stdout
* `-C`, `--cleanup`: deletes build artefacts from yaml files in directory (or matching the specified YAML file)
* `--info`: print configuration info and paths as json
* `--shell-completion {bash,zsh,fish}`: print shell completion script for the specified shell
* `--no-pager`: disable pager for documentation output
* `--docs [TOPIC]`: display documentation topic (e.g. 'quickstart', 'questions', 'targets') or full guide ('all'). TTY-aware: renders in full-screen pager, launches interactive topic browser if run with no topic in an interactive terminal, or outputs plain markdown when piped.
* `-v`, `--version`: show program's version number and exit
* `--debug`: Print lots of debugging statements
* `--verbose`: set verbose on
* `--quiet`: turn off info statements

### Unix Pipeline Composability

QuizML supports both all-in-one execution and modular Unix pipe composition:

* **Direct Template Render:**
  ```bash
  quizml exam.yaml --render tcd-exam.tex.j2 > exam.tex
  ```

* **Inspect Transcoded IR as JSON:**
  ```bash
  quizml exam.yaml --transcode latex > exam.latex.json
  quizml exam.yaml --transcode html > exam.html.json
  ```

* **Full 3-Stage Unix Pipe:**
  ```bash
  cat exam.yaml | quizml --ingest | quizml --transcode latex | quizml --render tcd-exam.tex.j2 > exam.tex
  ```


### Examples

* Running QuizML on the simple example:

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

* Formatting and renumbering questions:

You can format the YAML file and renumber the questions with the `--format` flag.
This will update the `<Q#>` comments in front of each question sequentially.

```shell-session
$ quizml --format quiz1.yaml
```

### Running as a Module

You can also run QuizML directly as a Python module, which is useful for development or if the `quizml` executable is not in your path:

```bash
python3 -m quizml quiz.yaml
```

