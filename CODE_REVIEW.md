# QuizML Code Review: Current Status

*Updated: 2026-10-16 · Code revision: `5416b4a` (`main`) · Scope: remaining work after the P0/P1 and selected P2 changes.*

This file replaces the original review roadmap with the work that remains after the changes through `5416b4a`. The initial findings were based on `6ab38d7`; their recommendations should not be treated as open when marked complete below.

## Summary

The major P0 and P1 work is complete. QuizML now has explicit CLI subcommands, nonzero failure statuses and stderr diagnostics; the formatter supports stdout, in-place, check and diff modes; the confirmed tokenizer, image-width, target-config and equation-count bugs have fixes; and CI runs tests and Ruff. The docs browser has been removed in the current working tree.

The schema walker now supports the constructs needed by the project, including local `$ref`, `allOf`, conditionals, `anyOf`, `oneOf` and `patternProperties`. It intentionally does not implement all of JSON Schema; `not` remains out of scope. Question types and fields are constrained by the bundled schema.

The loader, renderer, Markdown parser, CLI state and equation cache handling have also been refactored to reduce cross-layer dependencies and process-wide state. The watch-mode, generated-path and cache-lifecycle findings are now addressed. Remaining work is mostly lower-priority correctness and maintenance: error-policy cleanup, header schema semantics and packaging hygiene.

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
- **C7/C9:** SVG-to-PDF conversions are stored in QuizML's shared cache. Relative output paths and build commands use the input YAML directory as their base.
- **C10:** equation and image conversion caches share one directory; `quizml cache clear` clears it, `quizml info` reports its path and size, and equation keys include relevant external renderer versions. Automatic age/size eviction is deferred in favor of explicit clearing unless cache growth proves problematic.
- **A5:** the curses docs browser is removed in the working tree. LiveReload remains instance-owned.
- **A7:** watch mode recursively observes the input file's parent directory, and LiveReload binds to loopback.

## Remaining work

### Medium priority

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

The original test gaps for the fixed tokenizer, widths, equation counts, CLI failures, config interpolation, watch paths and cache invalidation have been addressed. Add focused tests as work proceeds on cleanup with custom targets, header validation and the remaining external-tool error paths.

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

