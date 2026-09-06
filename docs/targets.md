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

 
#### `descr`
 
Description for the target. 

#### `descr_cmd` 

Suggestion for the command to use after the quizml build.

In the example above, there is no post-build require, so we simply output the
path of the generated rendered BlackBoard test.


#### `fmt` 
This can be set to `latex`, `html`, `html-svg`, `html-mathml`, or `html-math-hybrid`. It is the format
that markdown gets converted to.


In the example above BlackBoard format requires HTML code. You have then the
choice between `html`, `html-svg`, `html-mathml`, and `html-math-hybrid`, depending on whether you
wish to convert LaTeX equations into PNG images, SVG graphics, MathML tags, or a hybrid
(MathML for inline math to prevent broken lines, and PNG for crisp display equations).
We recommend using `html-mathml` for Blackboard Ultra QTI 2.1 imports.

!> Note that `html-svg` is best suited for the new version of BlackBoard.

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
 
filename/path for the jinja template used.

---

### Standalone Rendering without Target Configuration

You do not need to configure targets in `quizml.cfg` to render a template. You can render any Jinja2 template or Word (`.docx`) template on demand using the CLI:

```bash
quizml exam.yaml --render tcd-exam.tex.j2 > exam.tex
```

Or programmatically in Python:

```python
import quizml

doc = quizml.load_quiz("exam.yaml")
doc_latex = quizml.transcode(doc, fmt="latex")
output_tex = quizml.render(doc_latex, "tcd-exam.tex.j2")
```

When rendering directly, QuizML automatically searches for the template in the current directory, the local `quizml-templates/` directory, the user configuration directory, and package-provided templates.

---

### LMS and QTI Targets

QuizML supports multiple LMS export formats:

* **Blackboard Text (`bb`):** Produces a tab-delimited `.txt` file suitable for uploading directly into tests on Blackboard Learn and Blackboard Ultra via the `(+)` $\to$ *Upload questions from file* menu.
* **Moodle XML (`moodle`):** Produces a self-contained `.xml` file conforming to the native **Moodle XML format**. Verified for importing directly into Moodle courses via the *Question bank* $\to$ *Import* $\to$ *Moodle XML format* menu. Supports all QuizML question types, embedded MathML equations, and base64 images.
* **IMS QTI 2.1 (`qti21`):** Produces a `.qti21.zip` package conforming to IMS QTI 2.1 specifications (containing `imsmanifest.xml`, `assessment.xml`, and individual `items/item_N.xml` files). Verified for **Blackboard Ultra's Question Bank** importer (*Manage banks* $\to$ `(+)` $\to$ *Import from QTI 2.1 package*).
* **IMS QTI 1.2 (`qti` / `qti12`):** Produces a `.qti.zip` package (containing `quiz.xml`, `imsmanifest.xml`, `assessment_meta.xml`) designed for **Canvas** quiz imports and classic LMS platforms. *(Note: QTI 1.2 export structure is generated per specification but has not yet been verified in a live Canvas/LMS environment).*

---

### Microsoft Word Targets

QuizML supports generating official Microsoft Word (`.docx`) examination papers:

* **TCD Word Exam Paper (`docx`):** Produces an official `.docx` file (`${inputbasename}.docx`) based on the Trinity College Dublin examination paper template. Preserves the institutional crest, typography (Calibri 12pt, 1.5 line spacing), cover page metadata layout (Faculty, School, Department, Degree Programme, Year level, Semester, Academic Year, Examiners, Instructions, Rubric notice, Materials permitted), running header with module code, dynamic running footers (`Page X of Y` and copyright), right-aligned marks (`[X marks]`), and the official centered `[oOo]` closing marker.
* **TCD Word Exam Paper Solutions (`docx-solutions`):** Produces a `.solutions.docx` file (`${inputbasename}.solutions.docx`) with answers and solutions highlighted: correct choices marked with `[X]` (bold), numerical answers with tolerances, acceptable fill-in answers, and essay model answers.


