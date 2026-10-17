
## Configuration File Location  <!-- {docsify-ignore} -->

After reading the QuizML YAML file and converting the Markdown entries into
LaTeX or HTML, QuizML uses Jinja templates to render targets such as Blackboard
imports, HTML previews, and LaTeX documents.

The list of targets can be defined in the configuration file. The default config
file is called `quizml.cfg`.

QuizML searches these locations in order:

1. `./quizml.cfg`, in the current directory.
2. `./quizml-templates/quizml.cfg`, in the current directory's template folder.
3. `templates/quizml.cfg`, in the per-user QuizML configuration directory.
4. `quizml/templates/quizml.cfg`, among the installed package templates.

The user configuration directory and installed package path depend on the
operating system and Python environment.

You can otherwise directly specify the path with the `--config CONFIGFILE` option.

The `--verbose` flag reports which config file is being used. This can help
confirm that you are editing the configuration QuizML loaded.



