# General Remarks

The main idea is to have a core mechanism as tight as possible and let users
augment the system with their own templates and user-defined YAML structure.

# CLI/Install/UX

* propose shell completion helper functions for bash
* Latex install. I should really have a handy function to add Latex path at install
* Documentation. Python command to serve could be exposed? ... and at least have
  on github.io

# Backend

* Check ALL exceptions handling
* Check ctrl-c interrupt logic
* Schema seems to be quite slow
* move from `pdflatex` to `dvipdfmx`, this could save 1 `latex` call
* triple check MATHML, SVG and PNG backends...

# BBYAML

* Move away from not allowing unknown keys in Schema... [done]
* decide over the Figure and side-by-side with choices. 
    1. First option is to have a new key called `figure` that contains the code for
       the figure. Then we could also have another key, eg. `figure-split: 80%`
       that says how much of the width the figure takes.
		   * Pro: it is simple to implement
		   * Con: it breaks the `question` content accross two tags. Hence I'll
             need to re-implement things like `--diff`. 
    2. Second option is to have a new Markup Block keyword, eg. `:::figure` that
       signals that this is the Figure, or to have an automatic detection of the
       last figure in question. The problem then is I would need to parse the
       markup and then to expose this in a simple data structure for the
       templates. 
		   * Pro: it preserves the `question` tag. This means that things like
             `--diff`, etc. still make sense.
		   * Con: it is magic. might be prone to bugs. Also, we could consider
             that a `figure` key is semantic in a way. 
* Add a `shortname` or equiv key to summarise question as a one-liner.

# Templates

* use `question` keyword??? doesn't look very neat
* implement `matching` for latex/html-preview
* implement `sort` for latex/html-preview

# Road to v1.0

Overall, the idea of v1.0, is to have something that other people can use that
is not just me in TCD.

So, as far as I can see, I would need to consider the following points:
* sort/matching done
* robust error handling
* better feedback on compile error
* *probably* a JSON Schema implemented [in progress with 0.7]
* better Latex resource installer with `bbquiz --init-local` and `bbquiz --init-user`
