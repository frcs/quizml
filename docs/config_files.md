
## Configuration File Location  <!-- {docsify-ignore} -->

After reading the QuizML YAML file and converting the markdown entries into LaTeX or
HTML, QuizML uses jinja2 templates to render the various targets (BlackBoard
compatible quiz, HTML preview or LaTeX).

The list of targets can be defined in the configuration file. The default config
file is called `quizml.cfg`.

QuizML will first try to read this file in 
1. the local directory from which QuizML is called 
2. the local templates subdirectory
3. the default application config dir 
4. the install package templates dir

For instance, on my mac, it will be:
1. `./quizml.cfg`
2. `quizml-templates/quizml.cfg`
3. `~/Library/Application\ Support/quizml/quizml.cfg`
4. `~/Library/Python/3.9/lib/python/site-packages/quizml/templates/quizml.cfg`

You can otherwise directly specify the path with the `--config CONFIGFILE` option.

The `--verbose` flag will report which config file is actually being used. This
can be useful for making sure that the correct config file is being edited.



