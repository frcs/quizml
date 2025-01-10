## Setting up your local LaTeX <!-- {docsify-ignore} -->

To be able to compile the LaTeX targets, you will need to have the required
LaTeX assets `.sty` `.cls` and other images.

The best way is to copy these templates in the local TEXMF tree so that LaTeX
can see them. To know where your local tree is, you can run this command in the
terminal:

```bash
kpsewhich -var-value=TEXMFHOME
```

In my case it says that my local TEXMF tree is located at
`~/Library/texmf/`. You can create a dedicated directory for your templates,
e.g., 

```bash
mkdir -p  ~/Library/texmf/tex/latex/bbquiz-templates/
```

I can then copy the required templates to that location:

```bash
unzip bbquiz-latex-templates.zip ~/Library/texmf/tex/latex/bbquiz-templates/
```

and then update LaTeX:
```bash
texhash ~/Library/texmf/tex/latex/bbquiz-templates/
```

At that point you should be able to compile your LaTeX targets from anywhere.


Alternatively,
```bash
set TEXINPUTS=/path/to/package/a/c/b/c/d
```

