## Writing Your Own Targets  <!-- {docsify-ignore} -->


### Target Definition in the Configuration File

The configuration file defines the list of all the targets. For instance, the
BlackBoard csv quiz file can be defined as the following target:

```yaml
- name      : bb
  out       : ${inputbasename}.txt
  descr     : Blackboard test
  descr_cmd : ${inputbasename}.txt
  markdown:
    format: html
    math: svg
    html_postprocess: blackboard_html
  html_pre  : math-preamble.tex
  html_css  : markdown-html.css
  template  : blackboard.txt.j2
```


As for the config file directory, any resource file or template file is defined
as a relative path, the template is searched in:
1. the local directory from which QuizML is called 
2. the local templates subdirectory
3. the default application config dir 
4. the install package templates dir


### Target Configuration


#### `name`

unique identifier for that target.

#### `out`

template of the output filename. In the example above, `${inputbasename}` refers
to the basename of the quiz. 

E.g., in the example above,

`quizml test-01.yaml` will produce a file called `test-01.txt`

Output paths that are relative are resolved from the directory containing the
input YAML file. Absolute output paths are used as given. Post-build commands
run with that same input directory as their working directory. `${inputbasename}`
and `${inputstem}` expand to the input filename without its directory or
extension; `${inputdir}` expands to the absolute input directory. In addition,
any top-level scalar field from the quiz YAML header (such as `${code}` or
`${title}`) can be interpolated in `out`, `build_cmd`, and `descr_cmd` (with
path separators sanitized to `_`). This keeps outputs and build commands beside
the source YAML even when QuizML is launched from another directory.

#### `context` / `vars`

Optional mapping of extra variables passed to the target's Jinja2 template
context (both `context` and `vars` are accepted as aliases, with `context`
taking precedence if both are specified).

#### `dep`

Name of a target (or list of target names) that this target depends on. QuizML
resolves dependencies recursively and guarantees they are compiled before their
dependents in topological order. For example, `pdf-solutions` depends on
`latex-solutions`, which in turn depends on `latex`.

#### `clean_extensions`

Optional list of file suffixes for additional artifacts produced by this
target, such as LaTeX's `.aux` and `.log` files. `quizml clean` always considers
the target's configured `out`; for each suffix listed here, it also considers a
file with that suffix and the same output stem. Suffixes must start with a dot
and cannot include path separators or glob patterns.

 
#### `descr`
 
Description for the target. 

#### `descr_cmd` 

Suggestion for the command to use after the quizml build.

In the example above, there is no post-build require, so we simply output the
path of the generated rendered BlackBoard test.


#### `markdown`

This mapping controls how Markdown fields are transcoded before they are passed
to the target's Jinja template.

##### `markdown.format`

Choose the output representation: `html`, `latex`, or `markdown` (which keeps
authored Markdown strings untouched for downstream static-site generators or
Pandoc/Quarto pipelines).

##### `markdown.math`

For HTML output, choose how LaTeX equations are rendered: `png` (the default),
`svg`, `mathml`, or `passthrough` (which emits HTML `<span class="math inline">\( ... \)</span>`
and `<div class="math display">\[ ... \]</div>` delimiters for client-side
MathJax or KaTeX rendering without invoking external LaTeX tools). The LaTeX and
raw Markdown output formats do not use this setting.

##### `markdown.html_postprocess`

Set this to `blackboard_html` when the target needs Blackboard-specific HTML
preparation, or to a custom `module:function` callable path. `blackboard_html`
inlines CSS and removes line breaks and tabs from rendered HTML fragments before
the template consumes them. It does not select or imply an output file format;
the target may write any format supported by its template.

The postprocessor is opt-in. Generic HTML targets receive the rendered HTML
without Blackboard-specific changes. Existing templates can keep using fields
such as `q.question` because post-processing happens before Jinja rendering.


In the example above Blackboard needs HTML fragments with equation SVGs, so
`markdown.format` is `html`, `markdown.math` is `svg`, and the HTML postprocessor
is enabled.

Older configuration files may still use `fmt`. QuizML maps `latex` to LaTeX,
`html` to HTML with PNG equations, `html-svg` to HTML with SVG equations, and
`html-mathml` to HTML with MathML equations. Move these values to the `markdown`
mapping when updating your config. Add `html_postprocess: blackboard_html` only
for targets that need the Blackboard-specific treatment. While an old `fmt`
setting remains, QuizML preserves its historical HTML post-processing behavior;
new `markdown` mappings only post-process HTML when explicitly configured.

#### `html_pre`

Path to latex preamble file used when generating the equations in the markdown
to html conversion. 

In the example above we use quizml's default which is `math-preamble.tex`.

#### `html_css` 

Path to the CSS file used for inline styling the HTML render. E.g. it can be
used to style code, tables, line separation, etc.

In the example above we default to quizml's default which is
`markdown-html.css`.

!> Note that the new version of BlackBoard tests strip out any CSS information.

#### `template` 

filename/path for the jinja template used
