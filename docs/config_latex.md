## Setting up your local LaTeX <!-- {docsify-ignore} -->


To be able to compile the LaTeX targets, you might need to make sure to have the
required LaTeX assets `.sty` `.cls` and other images. If we don't, trying to
compile the LaTeX target will give out an error message like this one:

```
! LaTeX Error: File `exams.cls' not found.
```

### Using the local TEXMF tree

You can add these resources to your local TEXMF tree so that LaTeX can see
them. To know where your local tree is, you can run this command in the
terminal:

```shell-session
$ kpsewhich -var-value=TEXMFHOME
```

In my case it says that my local TEXMF tree is located at
`~/Library/texmf/`. You can create a dedicated directory for your templates,
e.g., 

```shell-session
$ mkdir -p  ~/Library/texmf/tex/latex/quizml/
```

I can then copy the required assets to that location.

```shell-session
$ cp -r my-latex-assets/* ~/Library/texmf/tex/latex/quizml/
```

and then update LaTeX:
```shell-session
$ texhash ~/Library/texmf/tex/latex/quizml/
```

At that point you should be able to compile your LaTeX targets from anywhere.


### Using the Environment Variables

Alternatively, you can just set up the `TEXINPUTS` environment variable before
using pdflatex. For instance, if you have set up a local copy of the templates
using `quizml --init-local` and copied your LaTeX resouces there, you can
compile your LaTeX output with something like:


```shell-session
$ set TEXINPUTS=quizml-templates: latexmk -xelatex -pvc exam.tex
```






