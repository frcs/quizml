# Command-line usage <!-- {docsify-ignore} -->

Use `quizml compile` to turn a YAML quiz into the outputs configured for your
project. Run `quizml --help` or `quizml COMMAND --help` for the options available
in your installed version.

## Compile

Compile configured targets (or read from stdin with `-`):

```bash
quizml compile quiz.yaml
quizml sample bank.yaml | quizml compile - --target bb --quiet
```

The shorthand `quizml quiz.yaml` is also supported. Select targets or configured
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
quizml grep PATTERN [PATH ...] [-i] [-F] [-v] [--field FIELD] [-t TYPE] [-u] [-l] [-c] [--table] [-o FILE]
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

- `grep` (or `search`): searches questions across quiz YAML files or standard input
  for a regular expression or fixed string (`-F`), outputting complete matching
  questions in valid QuizML YAML with provenance comments (`# file: <Q#>`). Use
  `-e`/`--regexp` to specify patterns explicitly, `-i` for case-insensitivity,
  `-u`/`--unique` to deduplicate identical or similar questions across exams,
  `--field` to restrict search to specific fields (such as `figure` or `question`),
  `-t`/`--type` to filter question types (the pattern may be omitted or `*` to
  match all questions of that type), `-l` to print only filenames with matches,
  `-c` for counts, and `--table`/`--summary` for a Rich table view.
- `diff`: lists questions from the first file that also appear in the other files
  (matching by question `id` or by stem and choice similarity). Use `--check`
  to exit with status `1` when duplicates are found.
- `fmt`: reads a file or stdin and writes formatted YAML to stdout by default,
  updating `# <Q1>` question number comments. Use `-i` to edit a file in place,
  `--check` for a non-writing check, `--diff` to display proposed changes, and
  `--wrap WIDTH` to wrap Markdown text lines.
- `sample`: expands question-bank includes (`select`, `count`, `seed`),
  reading from a file or `-` (stdin) and writing a static YAML document to
  stdout (`-`) by default or to `--output FILE`. Include-level `seed` values
  make selections reproducible; `--seed` supplies a fallback seed when an
  include does not specify one. Existing output files require `--force` to
  replace.
- `pin`: stamps reproducibility metadata (`_quizml`, `_targets`, and
  non-default `_schema`) into a quiz YAML header in place (or to `-o FILE`),
  optionally generating deterministic question IDs (`--add-ids`) and expanding
  `_include` directives (`--freeze-includes`).
- `clean`: removes configured target outputs and their declared sidecars.
  `-r`/`--recursive` scans subdirectories; `--dry-run` lists candidates without
  deleting them; `--quiet` suppresses per-file status messages; `--config`
  selects the config file used to resolve targets.
- `cache clear`: removes cached equation renderings and SVG-to-PDF conversions.
  `info` reports the cache location and its current size.
- `init`: initializes a project configuration in `_quizml/quizml.cfg` (or the
  user config directory when `user` is given) and optionally copies bundled
  templates. See [Project setup](configuration.md) for details.
- `docs`: displays a documentation topic or the full guide (`quizml docs list`
  lists topics). When piped to another command or file (e.g.
  `quizml docs syntax_questions | pbcopy`), it outputs clean Markdown—useful
  for providing accurate QuizML syntax context to an LLM.
- `info`: prints configuration paths and version information as JSON.
- `targets`: lists the configured target names and descriptions.
- `completion`: prints a shell completion script for `bash`, `zsh`, or `fish`.

## Migration from the flag-based CLI

The `quizml quiz.yaml` compile shorthand remains supported. Other modes are
subcommands:

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
