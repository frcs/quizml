# Command-line usage

QuizML converts questions written in YAML and Markdown into Blackboard-compatible
HTML content, LaTeX documents, and other configured targets.

## Compile

Compile all configured targets (or read from stdin with `-`):

```bash
quizml compile quiz.yaml
quizml sample bank.yaml | quizml compile - --target bb --quiet
```

The shorthand `quizml quiz.yaml` is equivalent. Select targets or configured
target aliases with repeated `-t`/`--target` options, or watch for file changes
with `-w`/`--watch`:

```bash
quizml compile quiz.yaml --target build
quizml compile -w quiz.yaml
```

Compile options:

- `-t`, `--target TARGET`: compile a named target or configured alias; may be
  repeated.
- `-w`, `--watch`: compile again when the input or included files change.
- `--config CONFIGFILE`: use a specific QuizML config file.
- `--debug`, `--verbose`, `--quiet`: adjust diagnostic output.

## Other commands

```text
quizml diff [--check] FILE FILE [FILE ...]
quizml fmt [FILE|-] [-i | --check | --diff] [--wrap WIDTH]
quizml sample [FILE|-] [-o FILE|-] [--seed SEED] [--force]
quizml pin [FILE|-] [-o FILE] [-t TARGET] [--add-ids] [--freeze-includes] [--seed SEED] [-f]
quizml clean [PATH] [-r] [--dry-run] [--quiet] [--config CONFIGFILE]
quizml cache clear
quizml init [{local,user}] [--all] [--latex] [--html] [--bb] [--docx] [--schema] [-t FILE] [-f]
quizml docs [TOPIC] [--no-pager]
quizml info
quizml targets [--config CONFIGFILE]
quizml completion {bash,zsh,fish}
```

- `diff` lists questions from the first file that also appear in the other files
  (matching by question `id` or by stem and choice similarity). Use `--check`
  to exit with status `1` when duplicates are found.
- `fmt` reads a file or stdin and writes formatted YAML to stdout by default. Use
  `-i` to edit a file, `--check` for a non-writing check, or `--diff` to display
  the proposed changes. `--wrap WIDTH` opts into wrapping Markdown text.
- `sample` expands question-bank includes (`select`, `count`, `seed`),
  reading from a file or `-` (stdin) and writing a static YAML document to
  stdout (`-`) by default or to `--output FILE`. Include-level `seed` values
  make selections reproducible; `--seed` supplies a seed when an include does
  not specify one. Existing output files require `--force` to replace.
- `pin` stamps optional reproducibility metadata (`_quizml`, `_targets`, and
  non-default `_schema`) into a quiz YAML header in place (or to `-o FILE`),
  optionally generating deterministic question IDs (`--add-ids`) and expanding
  `_include` directives (`--freeze-includes`).
- `clean` removes configured target outputs and their declared sidecars.
  `-r`/`--recursive` scans subdirectories; `--dry-run` lists candidates without
  deleting them; `--quiet` suppresses per-file status messages; `--config`
  selects the config file used to resolve targets.
- `cache clear` removes cached equation renderings and SVG-to-PDF conversions.
  `info` reports the cache location and its current size.
- `init` creates `_quizml/quizml.cfg` by default (or initializes the user config
  directory when `user` is given). Pass `--latex`, `--html`, `--bb`, `--docx`,
  `--schema`, `-t FILE`, or `--all` to eject specific bundled templates into
  `_quizml/`, and `-f`/`--force` to overwrite existing files.
- `docs` displays a topic or the full guide. With no topic, behavior depends on
  whether output is a terminal; use `--no-pager` to disable the pager.
- `info` prints configuration paths and version information as JSON.
- `targets` lists the configured target names and descriptions.
- `completion` prints a shell completion script. Source the output using the
  instructions for your shell.

All commands accept `--help`; `quizml --help` lists commands and `quizml
COMMAND --help` lists that command's options. Use `--version` to print the
installed version.

## Migration from the flag-based CLI

The compile shorthand remains available. Other modes are now subcommands:

| Previous invocation | Current invocation |
|---|---|
| `quizml --diff a.yaml b.yaml` | `quizml diff a.yaml b.yaml` |
| `quizml --format quiz.yaml` | `quizml fmt quiz.yaml -i` |
| `quizml --cleanup [PATH]` | `quizml clean [PATH]` |
| `quizml --init-local` | `quizml init local` |
| `quizml --init-user` | `quizml init user` |
| `quizml --target-list` | `quizml targets` |
| `quizml --docs [TOPIC]` | `quizml docs [TOPIC]` |
| `quizml --info` | `quizml info` |
| `quizml --shell-completion zsh` | `quizml completion zsh` |

`fmt` now writes to stdout unless `-i` is supplied. Update scripts that used
`--format` to rewrite files by adding `-i`; scripts that need a read-only check
can use `--check`. To preserve the previous opt-in wrapping behavior while
editing a file, use `quizml fmt quiz.yaml -i --wrap 74`.
