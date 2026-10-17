# QuizML Code Review Status

*Updated: 2026-10-17 · Code revision: `311e993` (`main`) · Scope: remaining work after the P0/P1 and selected P2 changes.*

This file tracks remaining work after the changes through `311e993`. The initial findings were based on `6ab38d7`; recommendations marked complete below are closed.

## Summary

The major P0 and P1 work is complete. QuizML now has explicit CLI subcommands, nonzero failure statuses and stderr diagnostics; the formatter supports stdout, in-place, check and diff modes; the confirmed tokenizer, image-width, target-config and equation-count bugs have fixes; CI runs tests and Ruff; and the curses docs browser has been removed.

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
- **D/B8:** redundant equation re-raises now add renderer context, the deprecated `LatexEqError` type has been removed, subprocess launch/build failures are typed with concise bounded diagnostics, and Jinja/DOCX render failures use template-specific errors.
- **A5:** the curses docs browser is removed. LiveReload remains instance-owned.
- **A7:** watch mode recursively observes the input file's parent directory, and LiveReload binds to loopback.
- **A6:** target aliases can group configured outputs and build commands; the bundled `build` alias selects HTML, Blackboard, LaTeX, and PDF outputs. The ambiguous `--build` option was removed.
- **A8:** cleanup derives exact outputs from target `out` values and additional sidecar suffixes from per-target `clean_extensions`; `quizml clean --config` selects the configuration.
- **C11:** moved random question sampling into `quizml sample`, which materializes seeded selections as static YAML. Compilation remains deterministic.
- **F2:** added focused coverage for header schema validation and external LaTeX tool failures, including missing executables, launch failures, nonzero exits, and invalid equation-depth output.

## Remaining work

### Medium priority

#### E2–E4 — Header and YAML scalar semantics

- The bundled schema validates commonly used header fields and `_figures_path`; additional header keys remain allowed for template-specific metadata.
- Plain YAML `null` becomes Python `None`, while quoted `"null"` remains a string. Known string fields reject null; unknown extension fields may contain it.
- Question schema defaults remain unchanged; their string defaults are coerced according to the declared schema type.

### Lower priority

#### G — Finish packaging and documentation hygiene

- Template paths are still assembled from `__file__`; consider `importlib.resources` for package data.
- `src/quizml/docs` is still a symlink to the repository docs; verify sdist/wheel behavior on supported platforms.
- Remaining identifier/UI typos and low-value dead code can be cleaned up opportunistically.
- The bundled config's `version: 0.9` is not currently checked; either validate it or remove the misleading version field.

## Deferred or explicitly out of scope

- Full JSON Schema implementation, especially `not`; add a construct only when a real schema requires it.
- Replacing the formatter with a complete Markdown AST rewriter; the current agreed mitigation makes wrapping opt-in and protects common structures.
- Removing LiveReload entirely. The curses docs browser was the disproportionate UI and has been removed; LiveReload remains useful, with its concrete issues tracked under A7.

