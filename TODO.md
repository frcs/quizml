# Philosophy

The core objective is to keep the central mechanism as lean as possible, allowing users to extend the system through custom templates and user-defined YAML structures.

# CLI / Install / UX

* Improve the LaTeX installation process; consider a more robust method for adding the LaTeX path during setup.

# Backend

* Perform a comprehensive audit of **exception handling**.
* Further validate the **Schema** mechanism.
* Consider switching from `pdflatex` to `dvipdfmx` to eliminate one possible redundant `latex` call.
* Re-evaluate **MathML, SVG, and PNG** backends.

# Yaml

* [x] **Finalise implementation for Figures and side-by-side choices** (Implemented Option 1: `figure` and `figure-split` keys)

* Consider adding a `shortname` (or equivalent) key to provide a one-line summary of each question.

# Templates

* Evaluate the use of a `part` keyword.
* Implement `matching` type for LaTeX/HTML previews.
* Implement `sort` type for LaTeX/HTML previews.

# Road to v1.0

The goal for v1.0 is to deliver a user-friendly experience for external
adopters. So, the following points probably need to be addressed:

* Implement `sort` and `matching`
* Ensure robust error handling.
* Provide clearer feedback on compilation errors.
* Complete **JSON Schema** implementation (In progress since v0.7).
* Improve the LaTeX resource installer.

