## Writing Your Own Targets  <!-- {docsify-ignore} -->


### Target Definition in the Configuration File

The configuration file defines the list of all the targets. For instance, the
BlackBoard csv quiz file can be defined as the following target:

```yaml
  - out       : ${inputbasename}.txt    
    descr     : BlackBoard CSV          
    descr_cmd : ${inputbasename}.txt    
    fmt       : html                    
    html_pre  : html-latex-preamble.tex 
    html_css  : html-inline-style.css   
    template  : bb.jinja  
```


As for the config file directory, any resource file or template file is defined
as a relative path, the template is searched in:
1. the local directory from which BBQuiz is called 
2. the default application config dir 
3. the install package templates dir


### Target Configuration


#### `name`

unique name of that target.

#### `out`

template of the output filename. In the example above, `${inputbasename}` refers
to the basename of the quiz. 

E.g., in the example above,

`bbquiz test-01.yaml` will produce a file called `test-01.txt`

 
#### `descr`
 
Description for the target. 

#### `descr_cmd` 

This is the command to use (here we have no suggestion, so just print output
path)

#### `fmt` 
This can be set to `latex` or `html`. It is the format that markdown gets
converted to.

#### `html_pre`

latex preamble for generating the equations in the markdown to html conversion.

#### `html_css` 

CSS file used for inline styling the HTML render.

e.g. it can be used to style code, tables, line separation, etc.

#### `template` 

filename/path for the jinja template used
