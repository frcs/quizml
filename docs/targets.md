## Writing Your Own Targets  <!-- {docsify-ignore} -->


### Target Definition in the Configuration File

The configuration file defines the list of all the targets. For instance, the
BlackBoard csv quiz file can be defined as the following target:

```yaml
- name      : bb
  out       : ${inputbasename}.txt    
  descr     : BlackBoard CSV          
  descr_cmd : ${inputbasename}.txt    
  fmt       : html-svg                    
  html_pre  : html-latex-preamble.tex 
  html_css  : html-inline-style.css   
  template  : bb.jinja  
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

 
#### `descr`
 
Description for the target. 

#### `descr_cmd` 

Suggestion for the command to use after the quizml build.

In the example above, there is no post-build require, so we simply output the
path of the generated rendered BlackBoard test.


#### `fmt` 
This can be set to `latex`, `html`, `html-svg`, `html-mathml`. It is the format
that markdown gets converted to.


In the example above BlackBoard format requires HTML code. You have then the
choice between `html`, `html-svg` and `html-mathml`, depending on whether you
wish to convert LaTeX equations into PNG images, SVG graphics, or MathML tags.
We recommend using `html-svg` for BlackBoard.

!> Note that `html-svg` is best suited for the new version of BlackBoard.

#### `html_pre`

Path to latex preamble file used when generating the equations in the markdown
to html conversion. 

In the example above we use quizml's default which is `html-latex-preamble.tex`.

#### `html_css` 

Path to the CSS file used for inline styling the HTML render. E.g. it can be
used to style code, tables, line separation, etc.

In the example above we default to quizml's default which is
`html-inline-style.css`.

!> Note that the new version of BlackBoard tests strip out any CSS information.

#### `template` 

filename/path for the jinja template used
