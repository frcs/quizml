# QuizML Code Review: Current Status

*Updated: 2026-10-15 · Code revision: `694d7ea` (`main`) · Scope: remaining work after the P0/P1 and selected P2 changes.*

This file replaces the original review roadmap with the work that remains after the changes through `d630a26`. The initial findings were based on `6ab38d7`; their recommendations should not be treated as open when marked complete below.

## Summary

The major P0 and P1 work is complete. QuizML now has explicit CLI subcommands, nonzero failure statuses and stderr diagnostics; the formatter supports stdout, in-place, check and diff modes; the confirmed tokenizer, image-width, target-config and equation-count bugs have fixes; and CI runs tests and Ruff. The docs browser has been removed in the current working tree.

The schema walker now supports the constructs needed by the project, including local `$ref`, `allOf`, conditionals, `anyOf`, `oneOf` and `patternProperties`. It intentionally does not implement all of JSON Schema; `not` remains out of scope. Question types and fields are constrained by the bundled schema.

The loader, renderer, Markdown parser, CLI state and equation cache handling have also been refactored to reduce cross-layer dependencies and process-wide state. Remaining work is mostly lower-priority correctness and maintenance: watch-mode coverage, a few path and side-effect issues, cache lifecycle, some error-policy cleanup, and header schema semantics.

## Completed

### P0: CLI contract and correctness

- **A1/A2:** failures return nonzero status; diagnostics go to stderr.
- **B1 agreed mitigation:** formatting is opt-in and supports stdout, `-i`, `--check` and `--diff`; wrapping has guards for common Markdown structures. A fully AST-preserving Markdown formatter was not part of the agreed scope.
- **B2/B3:** inline math tokenization and HTML image width handling were fixed, with regression coverage.
- **B5/B6:** list-valued target dependencies and literal/unexpanded `$` values are handled.
- **B7:** equation/image and depth counts are checked before pairing.
- **F1/F3:** pager tests are isolated from the caller's `PAGER`; CI runs pytest and Ruff.
- **G:** the Python minimum is now 3.10; unused/deprecated dependencies identified in the review were removed or replaced.

### P1: CLI, config and template architecture

- **A3/A4:** subcommands replaced the flag-mode dispatch; `fmt` is a filter with stdout, in-place, check and diff modes. The `quizml FILE` shorthand remains.
- **C3/C4:** Markdown format, math backend and HTML post-processing are separate validated settings. The Blackboard transform is selected with `markdown.html_postprocess: blackboard_html`. Legacy `fmt` configuration remains supported and retains its historical HTML transform behavior during migration.
- **C5:** templates use a Jinja `FileSystemLoader`, support composition, and use `StrictUndefined`.
- **B4:** included YAML validation errors retain source information.
- **E1:** question types are enumerated and unknown question fields are rejected; supported `patternProperties` are respected.

### P2: scoped modularity work

- **C1:** schema-guided coercion was generalized to the agreed subset. `anyOf` and `oneOf` are implemented; `not` is intentionally unsupported. This is not a claim of full JSON Schema support.
- **C2/C6:** shared include parsing and path lookup were introduced; the loader no longer imports CLI lookup; renderer and asset paths are passed explicitly; Markdown token registration and CLI/live-reload state are scoped; equation cache handling is shared.
- **C8 partial:** loaded documents now have top-level `header`, `questions` and `paths`; `_figures_path` is moved out of `header`. The loader still injects `inputbasename` into `header`.
- **A5:** the curses docs browser is removed in the working tree. LiveReload remains instance-owned; its watch-mode and bind-address issues are tracked separately under A7.

## Remaining work

### Medium priority

#### A7 — Make watch mode observe its actual inputs

`compile_on_change` watches `.` non-recursively and only reacts to changes to the original YAML path. It misses input files in another directory and changes to included YAML, figures, templates, config and schema. The LiveReload server binds to `("", 0)`, exposing it on all interfaces; port zero already lets the OS choose an available port.

**Next step:** watch the paths used by a compile, including included files, or at minimum watch the input's parent directory recursively. Bind the server to `127.0.0.1` while retaining OS-assigned port selection.

#### C7/C9 — Keep generated files and build outputs predictable

LaTeX image handling can create converted PDFs beside source SVGs during transcoding. Output paths and build commands also still depend on the current working directory in ways that can put generated PDFs somewhere other than the source document's directory.

**Next step:** decide whether generated conversions belong in a build/cache directory, then define one documented base-directory rule for output paths and build commands. Avoid writing generated artifacts beside user assets as a side effect of Markdown conversion.

#### C10 — Define a cache lifecycle

Equation cache entries persist without an age/size policy. `clear_cache()` exists but is not exposed through the CLI, and cache keys do not account for external tool versions.

**Next step:** decide whether a cache-clearing command and bounded retention are useful. Include relevant tool/version settings in cache keys if output may change across tool versions.

#### D/B8 — Finish the error-handling audit

The main CLI error path and include provenance are improved, but the review found remaining cleanup such as redundant `raise e` statements in equation renderers and a deprecated `LatexEqError` type. Continue checking subprocess and template failures for useful typed errors and avoid obscuring programming errors as user-input errors.

**Next step:** remove no-op exception handling, consolidate or retire deprecated exception types, and check that external-tool failures carry concise diagnostics without raw tracebacks.

#### E2–E4 — Decide header and YAML scalar semantics

- The header is not validated against a schema.
- Some schema defaults are still strings and rely on coercion.
- YAML `null` is loaded as string-like input by `StringConstructor`; whether a schema-approved `null` should become Python `None` is not defined.

**Next step:** decide which header fields should be validated, whether defaults should use native JSON types, and whether `null` is supported for any fields. Keep the scope aligned with actual template/config use.

### Lower priority

#### A6 — Make build-target selection explicit

Requesting any target currently enables build commands in the selected dependency set. Consider requiring `--build` or explicitly selecting the build target instead of enabling build commands as a side effect of `-t`.

#### A8 — Derive cleanup candidates from target configuration

Cleanup still has knowledge of output suffixes separate from the target `out:` configuration. Derive cleanup candidates from configured outputs so custom targets can be cleaned safely.

#### C11 — Make sampled includes reproducible on demand

Sampling remains nondeterministic when an include has `count:` without `seed:`. Decide whether to require a seed, derive one, or report the generated seed so rebuilds can be repeated.

#### F2 — Add tests around remaining high-risk paths

The original test gaps for the fixed tokenizer, widths, equation counts, CLI failures and config interpolation have been addressed. Add focused tests as work proceeds on watch mode, cache invalidation, cleanup with custom targets, header validation and the remaining external-tool error paths.

#### G — Finish packaging and documentation hygiene

- Template paths are still assembled from `__file__`; consider `importlib.resources` for package data.
- `src/quizml/docs` is still a symlink to the repository docs; verify sdist/wheel behavior on supported platforms.
- `ARCHITECTURE.md` still describes the removed “Shadow Document” approach and needs a refresh.
- Remaining identifier/UI typos and low-value dead code can be cleaned up opportunistically.
- The bundled config's `version: 0.9` is not currently checked; either validate it or remove the misleading version field.

## Deferred or explicitly out of scope

- Full JSON Schema implementation, especially `not`; add a construct only when a real schema requires it.
- Replacing the formatter with a complete Markdown AST rewriter; the current agreed mitigation makes wrapping opt-in and protects common structures.
- Removing LiveReload entirely. The curses docs browser was the disproportionate UI and has been removed; LiveReload remains useful, with its concrete issues tracked under A7.

