## Writing Your Own Rendering Templates <!-- {docsify-ignore} -->

Templates are rendered with Jinja2. The [Jinja2 Template Designer
Documentation](https://jinja.palletsprojects.com/en/3.1.x/templates/) provides
complete information about how to write jinja2 templates.

The default templates used in QuizML can be found in the `templates`
directory. 

?> Because they are multiple possible locations for the templates, it can
sometimes be confusing to know which file is being edited. Use `--verbose` to
know which template is actually being used.


### Minimal Example

A template can contain variables and expressions, which get replaced when the
template is rendered.

Here is a minimal example of template for LaTeX, where we make a enumeration of
all questions 


```
\begin{enumerate}
<| for q in questions +|>
\item[{\bf Q.<<loop.index>>}] <<q.question>>
<| endfor |>
\end{enumerate}
```

The output would look like something like this:

```
\begin{enumerate}
\item[{\bf Q1}] This is statement for question 1
\item[{\bf Q2}] This is statement for question 2
\item[{\bf Q3}] This is statement for question 3
\end{enumerate}
```


### Jinja Delimiters

Note that to be compatible with both LaTeX and HTML, we use the following
delimiters:
* `<| ... |>`  for Statements
* `<< ... >>`  for Expressions
* `<# ... #>`  for Comments


### Questions Information

The questions can be accessed with `questions`. The variable is a list of
dictionary, and has the same structure as per the yaml syntax specified in .

For instance, this code would generate an HTML list of the types of questions:

```
<ol>
<| for q in questions +|>
<li> 
<| if q.type == 'essay' |>
Short Essay
<|- elif q.type == 'mc'  -|>
Multiple Choice
<|- elif q.type == 'ma'  -|>
Multiple Answers
<|- else -|>
Other type
<|- endif |>
</li>
</ol>
```


### Header Information

The header information is stored in `header`.

For instance, this is how we can save the header keys/vales for keys that do not
start with `_` as LaTeX macros:


```
<# passing the header variables to template  #>
<# we do not include 'type' and 'pre_' keys  #>
<| if header                                               -|>
<|   for key, value in header.items()                      -|>
<|     if (key != 'type') and (not key.startswith('_'))     |>
\def \info<<key>> {<<value>>}
<|     endif                                                |>
<|-  endfor                                                 |>
<|-endif                                                    |>
```
