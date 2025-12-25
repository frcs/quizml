<a name="0.9"></a>

# [0.9]() (2025-12-25)

* **Fix:** Improved image path resolution for LaTeX. It now prioritizes existing PDF, PNG, or JPG files before attempting SVG conversion. This makes external tools like `rsvg-convert` or `inkscape` optional if compatible image formats are present.
* **Fix:** Correctly exposed `main` entry point, fixing `python -m quizml` usage.
* **Refactor:** Improved YAML loading and type alignment in tests/templates.
* **Docs:** Added `GEMINI.md` and `run_test.py` for development.

<a name="0.8"></a>

# [0.8]() (2025-12-16)

Rename from `bbquiz` to `quizml`


<a name="0.7"></a>

# [0.7]() (2025-12-11)

Migration from strictyaml to ruamel. Also, we now have with user-definable
schema using jsonschema.

* more consistent and better consistency with error reporting
* slightly better testing
* more CLI arguments, with `-t` 


<a name="0.6"></a>

# [0.6]() (2025-02-08)

new MCQ syntax with `-x:` and `-o:` style.

<a name="0.5"></a>

# [0.5]() (2025-01-10)

first release


