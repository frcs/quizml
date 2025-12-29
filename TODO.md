# Philosophy

The core objective is to keep the central mechanism as lean as possible, allowing users to extend the system through custom templates and user-defined YAML structures.

# CLI / Install / UX

* Implement shell completion helper functions for Bash.
* Improve the LaTeX installation process; consider a more robust method for adding the LaTeX path during setup.

# Backend

* Perform a comprehensive audit of **exception handling**.
* Review and refine **Ctrl+C (SIGINT) interrupt logic**. (probably sorted now)
* Further validate the **Schema**.
* Consider switching from `pdflatex` to `dvipdfmx` to eliminate one redundant `latex` call.
* Re-evaluate **MathML, SVG, and PNG** backends.

# QuizMLYaml

* **Finalise implementation for Figures and side-by-side choices:**
1. **Option 1: Dedicated `figure` key.** Include a `figure` key for the code and a `figure-split` key (e.g., `80%`) to define the width ratio.
* **Pro:** Simple to implement.
* **Con:** Splits question content across multiple tags, which would require refactoring features like `--diff`.


2. **Option 2: Markup Block keyword.** Use a custom block (e.g., `:::figure`) or auto-detect the final figure in a question.
* **Pro:** Preserves the integrity of the `question` tag, keeping `--diff` and other utilities functional.
* **Con:** Relies on "magic" detection which may be bug-prone. However, a dedicated `figure` key might be more semantically clear.



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

