## Setting up your local LaTeX <!-- {docsify-ignore} -->


To be able to compile the LaTeX targets, you will need to have the required
LaTeX assets `.sty` `.cls` and other images. If we don't, trying to compile the
LaTeX target will give out an error message like this one:

```
! LaTeX Error: File `tcdexams.cls' not found.
```

### Using the local TEXMF tree


The best way is to copy the templates in the local TEXMF tree so that LaTeX
can see them. To know where your local tree is, you can run this command in the
terminal:

```shell-session
$ kpsewhich -var-value=TEXMFHOME
```

In my case it says that my local TEXMF tree is located at
`~/Library/texmf/`. You can create a dedicated directory for your templates,
e.g., 

```shell-session
$ mkdir -p  ~/Library/texmf/tex/latex/quizml-templates/
```

I can then copy the required templates to that location:

```shell-session
$ cp -r XXXX ~/Library/texmf/tex/latex/quizml-templates/
```

and then update LaTeX:
```shell-session
$ texhash ~/Library/texmf/tex/latex/quizml-templates/
```

At that point you should be able to compile your LaTeX targets from anywhere.


### Using the Environment Variables

Alternatively, you can just set up the `TEXINPUTS` environment variable before
using pdflatex. 


```shell-session
$ set TEXINPUTS=/path/to/package/a/c/b/c/d
```






