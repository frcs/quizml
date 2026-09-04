#!/usr/bin/python

import argparse
import logging
import sys
from importlib.metadata import version

import appdirs
from rich import print
from rich.logging import RichHandler
from rich.traceback import install
from rich_argparse import RawDescriptionRichHelpFormatter, RichHelpFormatter

from ..exceptions import QuizMLError

install(show_locals=False)


def _load_cli_document(filename: str | None) -> tuple[dict, str]:
    """Loads a QuizML document from a file or stdin (auto-detecting JSON or YAML).

    Returns (doc, base_dir).
    """
    import json
    import os
    from pathlib import Path

    from quizml import quizmlyaml

    if filename and filename != "-":
        path = Path(filename).resolve()
        if not path.is_file():
            raise QuizMLError(f"File not found: {filename}")
        content = path.read_text(encoding="utf-8")
        base_dir = str(path.parent)
        basename = os.path.splitext(filename)[0]
    else:
        if sys.stdin.isatty():
            raise QuizMLError("A quiz YAML/JSON file or stdin pipe is required.")
        content = sys.stdin.read()
        base_dir = os.getcwd()
        basename = "quiz"

    from quizml.quizmlyaml.schema import load_schema

    schema = load_schema()

    content_trimmed = content.strip()
    if content_trimmed.startswith("{"):
        try:
            doc = json.loads(content_trimmed)
        except json.JSONDecodeError as err:
            raise QuizMLError(f"Invalid JSON input: {err}") from err
        if isinstance(doc, dict) and not doc.get("header", {}).get("_transcoded"):
            doc = quizmlyaml.coerce_data(doc, schema)
    else:
        doc, _ = quizmlyaml.loads(
            content, validate=True, schema=schema, base_dir=base_dir
        )

    if not isinstance(doc, dict):
        raise QuizMLError("Invalid document structure: expected a dictionary.")

    doc.setdefault("header", {})
    if "inputbasename" not in doc["header"]:
        doc["header"]["inputbasename"] = basename

    return doc, base_dir


def main():
    RichHelpFormatter.styles = {
        "argparse.args": "cyan",
        "argparse.groups": "yellow",
        "argparse.help": "grey50",
        "argparse.metavar": "dark_cyan",
        "argparse.prog": "default",
        "argparse.syntax": "bold",
        "argparse.text": "default",
        "argparse.pyproject": "green",
    }

    def formatter(prog):
        return RawDescriptionRichHelpFormatter(prog, max_help_position=52)

    parser = argparse.ArgumentParser(
        formatter_class=formatter,
        description="Converts a questions in a YAML/markdown format into"
        + " a Blackboard test or a LaTeX script",
    )

    parser.add_argument(
        "yaml_filename",
        nargs="?",
        metavar="quiz.yaml",
        type=str,
        help="path to the quiz in a yaml format",
    )

    parser.add_argument(
        "otherfiles",
        nargs="*",
        type=str,
        help="other yaml files (only used with diff command)",
    )

    parser.add_argument(
        "-w",
        "--watch",
        help="continuously compiles the document on file change",
        action="store_true",
    )

    default_config_dir = appdirs.user_config_dir(appname="quizml", appauthor="frcs")

    parser.add_argument(
        "-t",
        "--target",
        action="append",
        type=str,  # argparse.FileType('r'),
        help="target names (e.g. 'pdf', 'html-preview')",
    )

    parser.add_argument(
        "--target-list", help="list all targets in config file", action="store_true"
    )

    parser.add_argument(
        "--init-local",
        help="create a local directory 'quizml-templates' with all config files",
        action="store_true",
    )

    parser.add_argument(
        "--init-user",
        help="create the user app directory with all its config files",
        action="store_true",
    )

    parser.add_argument(
        "--config",
        metavar="CONFIGFILE",
        help=f"user config file. Default location is {default_config_dir}",
    )

    parser.add_argument(
        "--build",
        help="compiles all targets and run all post-compilation commands",
        action="store_true",
    )

    parser.add_argument(
        "--diff",
        help="compares questions from first yaml file to rest of files",
        action="store_true",
    )

    parser.add_argument(
        "--format",
        help="formats and renumbers questions in the yaml file",
        action="store_true",
    )

    parser.add_argument(
        "--ingest",
        help="parse and validate the quiz YAML, then print the coerced JSON intermediate representation (IR) to stdout",
        action="store_true",
    )

    parser.add_argument(
        "--transcode",
        metavar="FMT",
        help="transcode markdown fields to target format (e.g. 'html', 'latex') and print JSON IR to stdout",
    )

    parser.add_argument(
        "--render",
        metavar="TEMPLATE",
        help="render document using the specified Jinja2 or Word template and print output to stdout",
    )

    parser.add_argument(
        "-C",
        "--cleanup",
        help="deletes build artefacts from all yaml files in dir",
        action="store_true",
    )

    parser.add_argument(
        "--info", help="print configuration info and paths as json", action="store_true"
    )

    parser.add_argument(
        "--shell-completion",
        choices=["bash", "zsh", "fish"],
        help="print shell completion script for the specified shell",
    )

    parser.add_argument(
        "--no-pager",
        help="disable pager for documentation output",
        action="store_true",
    )

    parser.add_argument(
        "--docs",
        nargs="?",
        const="",
        metavar="TOPIC",
        help="display documentation topics or full guide (e.g. 'all', 'questions', 'targets'). TTY-aware.",
    )

    parser.add_argument("-v", "--version", action="version", version=version("quizml"))

    parser.add_argument(
        "--debug",
        help="Print lots of debugging statements",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.WARNING,
    )

    parser.add_argument(
        "--verbose",
        help="set verbose on",
        action="store_const",
        dest="loglevel",
        const=logging.INFO,
    )

    parser.add_argument("--quiet", help="turn off info statements", action="store_true")

    args = parser.parse_args()

    try:
        logging.basicConfig(
            force=True,
            level=args.loglevel,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
        )

        if args.target_list:
            import quizml.cli.ui

            quizml.cli.ui.print_target_list(args)
            return

        if args.info:
            import json

            import quizml.cli.filelocator

            try:
                config_file = quizml.cli.filelocator.locate.path("quizml.cfg")
            except FileNotFoundError:
                config_file = "not found"

            info = {
                "version": version("quizml"),
                "cwd": quizml.cli.filelocator.locate.cw_dir,
                "local_templates": quizml.cli.filelocator.locate.local_template_dir,
                "user_config_dir": quizml.cli.filelocator.locate.app_dir,
                "user_templates": quizml.cli.filelocator.locate.user_template_dir,
                "package_templates": quizml.cli.filelocator.locate.pkg_template_dir,
                "search_paths": quizml.cli.filelocator.locate.dirlist,
                "config_file": config_file,
            }
            sys.stdout.write(json.dumps(info, indent=4) + "\n")
            return

        if args.shell_completion:
            import quizml.cli.shellcompletion

            completion_func = getattr(quizml.cli.shellcompletion, args.shell_completion)
            sys.stdout.write(completion_func(parser) + "\n")
            return

        if args.docs is not None:
            import quizml.cli.docs

            quizml.cli.docs.handle_docs(args.docs, no_pager=args.no_pager)
            return

        if args.cleanup:
            from pathlib import Path

            import quizml.cli.cleanup

            if args.yaml_filename:
                target_path = Path(args.yaml_filename)
                if target_path.is_dir():
                    quizml.cli.cleanup.cleanup_yaml_files(
                        directory_path=str(target_path)
                    )
                else:
                    dir_path = (
                        target_path.parent if target_path.parent.name else Path(".")
                    )
                    quizml.cli.cleanup.cleanup_yaml_files(
                        directory_path=str(dir_path), target_stems={target_path.stem}
                    )
            else:
                quizml.cli.cleanup.cleanup_yaml_files()
            return

        if args.init_user:
            import quizml.cli.init

            quizml.cli.init.init_user()
            return

        if args.init_local:
            import quizml.cli.init

            quizml.cli.init.init_local()
            return

        if args.render:
            from quizml import renderer, transcoder
            from quizml.filelocator import locate

            template_arg = args.render
            try:
                template_path = locate.path(template_arg)
            except FileNotFoundError as err:
                raise QuizMLError(f"Template not found: {template_arg}") from err

            doc, base_dir = _load_cli_document(args.yaml_filename)

            # Auto-infer format if not already specified
            fmt = args.transcode
            if not fmt:
                tpl_lower = str(template_path).lower()
                if tpl_lower.endswith(".tex.j2") or tpl_lower.endswith(".tex"):
                    fmt = "latex"
                else:
                    fmt = "html"

            if doc.get("header", {}).get("_transcoded") != fmt:
                doc_transcoded = transcoder.transcode(
                    doc, target=fmt, base_dir=base_dir
                )
                doc_transcoded.setdefault("header", {})["_transcoded"] = fmt
            else:
                doc_transcoded = doc

            rendered = renderer.render(doc_transcoded, template_path)

            if isinstance(rendered, bytes):
                sys.stdout.buffer.write(rendered)
            else:
                sys.stdout.write(rendered)
            return

        if args.transcode:
            import json

            from quizml import transcoder

            doc, base_dir = _load_cli_document(args.yaml_filename)
            doc_transcoded = transcoder.transcode(
                doc, target=args.transcode, base_dir=base_dir
            )
            doc_transcoded.setdefault("header", {})["_transcoded"] = args.transcode
            sys.stdout.write(
                json.dumps(doc_transcoded, indent=2, ensure_ascii=False) + "\n"
            )
            return

        if args.ingest:
            import json

            doc, _ = _load_cli_document(args.yaml_filename)
            sys.stdout.write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
            return

        if not args.yaml_filename:
            parser.error("a yaml file is required")

        if args.diff:
            import quizml.cli.diff

            quizml.cli.diff.diff(args)
            return

        if args.format:
            import quizml.cli.format

            quizml.cli.format.format_yaml(args)
            return

        if args.otherfiles:
            parser.error("only one yaml file is required")

        import quizml.cli.compile

        if args.watch:
            quizml.cli.compile.compile(args)
            quizml.cli.compile.compile_on_change(args)
        else:
            quizml.cli.compile.compile(args)

    except QuizMLError as e:
        print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
