## Configuration File and Target Templates

After reading the QuizMLYaml file and converting the markdown entries into LaTeX or
HTML, QuizML uses jinja2 templates to render the various targets (BlackBoard
compatible quiz, HTML preview or LaTeX).



### Defining Your Own Targets

The configuration file defines the list of all the targets. For instance, the
BlackBoard csv quiz file can be defined as the following target:

```yaml
  - out       : ${inputbasename}.txt     # template for outputfilename.
                                         # ${inputbasename} refers to the basename of the quiz
                                         # (eg. mcq-01.yaml => mcq-01)
    descr     : BlackBoard CSV           # description for the target. 
    descr_cmd : ${inputbasename}.txt     # command to use (here we have no suggestion, so just print output path)
    fmt       : html                     # latex or html: format that markdown gets converted to
    html_pre  : html-latex-preamble.tex  # latex preamble for generating the equations in the markdown > html conversion
    html_css  : html-inline-style.css    # CSS used for inline styling the HTML render.
                                         # e.g. it can be used to stye <code></code>, tables, line separation, etc.
    template  : bb.jinja                 # filename for the jinja template used
```

### Default Targets

You can specify a subset of targets to be compiled by default when no `--target` option is provided.

```yaml
default_targets:
  - html-preview
  - latex
```

If `default_targets` is not defined, all targets are compiled by default.

As for the config file directory, any resource file or template file is defined
as a relative path, the template is searched in:
1. the local directory from which QuizML is called 
2. the default application config dir 
3. the install package templates dir


### Writing Your Own Rendering Templates

Templates are rendered with Jinja2. The [Jinja2 Template Designer
Documentation](https://jinja.palletsprojects.com/en/3.1.x/templates/) provides
complete information about how to write jinja2 templates.

The default templates used in QuizML can be found in the `templates`
directory. (Again, use `--verbose` to know which template is actually being
used)

Note that to be compatible with both LaTeX and HTML, we use the following
delimiters:
* `<| ... |>`  for Statements
* `<< ... >>`  for Expressions
* `<# ... #>`  for Comments

## Setting up your local LaTeX

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
mkdir -p  ~/Library/texmf/tex/latex/quizml-templates/
```

I can then copy the required templates to that location:

```bash
unzip quizml-latex-templates.zip ~/Library/texmf/tex/latex/quizml-templates/
```

and then update LaTeX:
```bash
texhash ~/Library/texmf/tex/latex/quizml-templates/
```

At that point you should be able to compile your LaTeX targets from anywhere.


Alternatively,
```bash
set TEXINPUTS=/path/to/package/a/c/b/c/d
```
