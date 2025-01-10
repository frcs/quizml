
## Configuration File Location  <!-- {docsify-ignore} -->

After reading the BBYaml file and converting the markdown entries into LaTeX or
HTML, BBQuiz uses jinja2 templates to render the various targets (BlackBoard
compatible quiz, HTML preview or LaTeX).

The list of targets can be defined in the configuration file. The default config
file is called `bbquiz.cfg`.

BBQuiz will first try to read this file in 
1. the local directory from which BBQuiz is called 
2. the default application config dir 
3. the install package templates dir

For instance, on my mac, it will be:
1. `./bbquiz.cfg`
2. `~/Library/Application\ Support/bbquiz/bbquiz.cfg`
3. `~/Library/Python/3.9/lib/python/site-packages/bbquiz/templates/bbquiz.cfg`

You can otherwise directly specify the path with the `--config CONFIGFILE` option.

The `--verbose` flag will report which config file is actually being used. This
can be useful for making sure that the correct config file is being edited.



