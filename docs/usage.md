# Usage


```
Usage: bbquiz [-h] [-w] [--config CONFIGFILE] [--build] [--diff] [--zsh] [--fish] [-v] [--debug] [--verbose]
              [quiz.yaml] [otherfiles [otherfiles ...]]

Converts a questions in a YAML/markdown format into a Blackboard test or a LaTeX script

Positional Arguments:
  quiz.yaml            path to the quiz in a yaml format
  otherfiles           other yaml files

Optional Arguments:
  -h, --help           show this help message and exit
  -w, --watch          continuously compiles the document on file change
  --config CONFIGFILE  user config file. Default location is /Users/fpitie/Library/Application Support/bbquiz
  --build              compiles all targets and run all post-compilation commands
  --diff               compares questions from first yaml file to rest of files
  --zsh                A helper command used for exporting the command completion code in zsh
  --fish               A helper command used for exporting the command completion code in fish
  -v, --version        show program's version number and exit
  --debug              Print lots of debugging statements
  --verbose            set verbose on
```

Running BBQuiz on the simple example gives us:

```
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

```bash
latexmk -xelatex -pvc quiz1.tex
```

You can automate these additional compilations by setting the `--build` flag:

```bash
bbquiz --build quiz1.yaml
```

When editing a test, you can continuously watch for any file change and
recompile the target by setting the flag `-w`:

```bash
bbquiz -w quiz1.yaml
```

