# Philosophy

The core objective is to keep the central mechanism as lean as possible,
allowing users to extend the system through custom templates and user-defined
YAML structures.

# Git Conventions

### 1. Atomic Commits
Every commit should represent a single logical change or concern. Do not bundle multiple unrelated refactorings, features, or fixes into one commit. Each commit must leave the test suite (`uv run pytest`) passing.

### 2. Commit Message Format
Commit messages follow the "Type: Subject" format.
Types include: `Feat`, `Fix`, `Docs`, `Refactor`, `Chore`, `Test`, `Style`, `Perf`.

For non-trivial changes, structure the commit body to explain the architectural rationale:

```text
Type: Short imperative summary (under 50 chars)

Problem:
Explain the limitation, architectural flaw, or bug that existed.
Why was the current code problematic?

Solution:
Explain the chosen design and how it solves the problem.
Why was this approach chosen over alternatives?

Impact:
Explain the benefits, guarantees, and verification.
```

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
