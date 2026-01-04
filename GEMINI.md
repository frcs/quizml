## Building and running

Before submitting any changes, it is crucial to validate them by running the
full preflight check. 
To run the full suite of checks, execute the following command:

```bash
pytest .
```

## Updating the Docs

Makse sure to update docs/usage.md with the accurate CLI arguments and descriptions
obtained from the help command.

## Python version

Do not use the default `python` or `python3` when invoking python as I use
macports, specifically /opt/local/bin/python3.9

## Git Repo

The main branch for this project is called "main"

## Comments policy

Only write high-value comments if at all. Avoid talking to the user through
comments.

## General requirements

- If there is something you do not understand or is ambiguous, seek confirmation
  or clarification from the user before making changes based on assumptions.

## External Dependencies

It is assumed that a latex installation exists, along with tools like gs,
dvisvgm, dvipdfmx, dvipng, etc.


## Philosophy

The core objective is to keep the central mechanism as lean as possible,
allowing users to extend the system through custom templates and user-defined
YAML structures.

When possible, use a modular architecture.

## Git 

The commit messages have been standardised to the "Type: Subject" format.  The
  types include Feat, Fix, Docs, Refactor, Chore, Test, Style.
  
For example:
- Feat: Adding --target-list as feature
- Docs: Using docsify.js
- Fix: Fix loader and sets default schema
- Refactor: Rename project structure to quizml

## Jinja Templates

the delimiters are as follows:
* comment start string : `<#`
* comment end string   : `#>`
* block start string   : `<|`
* block end string     : `|>`
* variable start string: `<<`
* variable end string  : `>>`


