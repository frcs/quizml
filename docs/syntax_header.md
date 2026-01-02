## The Header Section<!-- {docsify-ignore} -->

An optional header section can be declared at the start of the yaml file. All
(key, val) pairs declared in this section will be sent to the template
renderer. For instance your LaTeX template might require information about the
exam date, venue, etc. The header must be declared at the start of the file and
must be separated from the rest of the questions with a line starting with
`---`.

```yaml
descr: |
  A very long exam
  
  You are all going to suffer.

venue: Maxwell Theatre
date: 13/05/2024
---
- type: "tf"
  question: is the Earth flat?
  answer: true
```

!> Note that it is recommended for the key names to only contain uppercase and
lowercase alphabetical characters: a-z and A-Z, without any numeral or other
non-letter character.  This is because the LaTeX template copies the keys
accross as TeX macros:

```tex
\def\descr{
    A very long exam
    
    You are all going to suffer.
}
\def\venue{Maxwell Theatre}
\def\date{13/05/2024}
```

Hence, as each key will be turned into a LaTeX macro, it must also follow LaTeX
syntax macro naming rules.

!> All keys' values will be interpreted as Markdown. 

!> If your key starts with the prefix `_` (eg. `_latexpreamble`), the
value will not be interprated as markdown and it will not be turned into a macro
by the LaTeX template. 


