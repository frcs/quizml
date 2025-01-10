## Header <!-- {docsify-ignore} -->

An optional header section can be declared at the start of the yaml file.  All
(key, val) pairs declared in this section will be sent to the template
renderer. For instance your LaTeX template might require information about the
exam date, venue, etc. The header must be the first item in the BBYaml file.

```yaml
- type: header
  descr: |
    A very long exam
    
    You are all going to suffer.
  venue: Maxwell Theatre
  date: 13/05/2024
```

Note that it is recommended for the key names should contain only uppercase and
lowercase alphabetical characters: a-z and A-Z, without any numeral or other
non-letter character.  This is because, in the LaTeX template, it is expected
that the keys will be copied accross as macros:

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

Note that if your key starts with the prefix `pre_`, as in `pre_latexpreamble`,
the key should not be turned into a macro by the LaTeX template.




