# Philosophy

The core objective is to keep the central mechanism as lean as possible,
allowing users to extend the system through custom templates and user-defined
YAML structures.

# Git 

The commit messages have been standardised to the "Type: Subject" format.  The
  types include Feat, Fix, Docs, Refactor, Chore, Test, Style.
  
For example:
- Feat: Adding --target-list as feature
- Docs: Using docsify.js
- Fix: Fix loader and sets default schema
- Refactor: Rename project structure to quizml

# Releasing

QuizML uses `setuptools_scm` to automatically generate version numbers from Git tags, and GitHub Actions to automatically publish releases to PyPI. 

To release a new version (e.g., `v0.11.0`):

1. **Update the Changelog:** 
   Move the items from the `[Unreleased]` section of `docs/changelog.md` into a new release block matching the standard format (e.g., `<a name="0.11.0"></a>` and `### [0.11.0]() (YYYY-MM-DD)`).
2. **Commit the Changelog:**
   ```bash
   git commit -am "Docs: Update Changelog for v0.11.0"
   ```
3. **Tag the Release:**
   Tag the commit with the exact version number, prefixed with `v`:
   ```bash
   git tag v0.11.0
   ```
4. **Push the Release:**
   Push the commit and the tag to the repository:
   ```bash
   git push && git push origin v0.11.0
   ```

Upon pushing the tag, the `.github/workflows/publish.yml` GitHub Action will trigger. It will check out the code, use `uv build` to construct the wheel, and upload it to PyPI using PyPI Trusted Publishing.
