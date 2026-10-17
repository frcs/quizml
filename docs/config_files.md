
## Configuration File Location  <!-- {docsify-ignore} -->

After reading the QuizML YAML file and converting the Markdown entries into
LaTeX or HTML, QuizML uses Jinja templates to render targets such as Blackboard
imports, HTML previews, and LaTeX documents.

The list of targets can be defined in the configuration file. The default config
file is called `quizml.cfg`.

QuizML searches these locations in order, walking up parent directories from the
quiz file's directory (and the current working directory):

1. `quizml.cfg` or `_quizml/quizml.cfg` (and legacy `quizml-templates/quizml.cfg`)
   in the quiz directory or any ancestor directory (stopping at the repository root).
2. `templates/quizml.cfg`, in the per-user QuizML configuration directory.
3. `quizml/templates/quizml.cfg`, among the installed package templates.

Any template or asset referenced by `quizml.cfg` is also searched in the
directory containing that `quizml.cfg` before falling back to user and package
templates, so you only need to place the files you customize in `_quizml/`.

You can also specify a config file directly via `--config CONFIGFILE` on the
command line or `_config: path/to/quizml.cfg` in a quiz YAML header, and declare
an optional version constraint (`quizml_version: ">=0.12,<0.13"`) in `quizml.cfg`.

The `--verbose` flag reports which config file is being used.
