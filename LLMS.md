# Language-model context

The shared guidance for coding agents is in [AGENTS.md](AGENTS.md). For
implementation details, see [ARCHITECTURE.md](ARCHITECTURE.md). User-facing
documentation is under [`docs/`](docs/README.md).

## Project at a glance

QuizML converts YAML and Markdown quizzes into outputs configured in
`quizml.cfg`, including Blackboard imports, HTML previews, LaTeX, PDFs, and
Word documents. Python 3.10 or newer is supported. The project uses `uv`,
`ruamel.yaml`, `jsonschema`, Mistletoe, Jinja2, and pytest.

Common commands:

```bash
uv run quizml quiz.yaml
uv run quizml compile quiz.yaml --target build
uv run quizml fmt quiz.yaml --check
uv run pytest
```
