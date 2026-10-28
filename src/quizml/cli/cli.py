import argparse
import logging
import sys
from importlib.metadata import version

from rich.logging import RichHandler
from rich.traceback import install
from rich_argparse import RawDescriptionRichHelpFormatter, RichHelpFormatter

from ..exceptions import QuizMLConfigError, QuizMLError
from .errorhandler import err_console

COMMANDS = {
    "compile",
    "diff",
    "fmt",
    "grep",
    "search",
    "sample",
    "pin",
    "clean",
    "init",
    "docs",
    "info",
    "targets",
    "completion",
    "cache",
}


def _add_common_options(parser, *, include_config=True):
    if include_config:
        parser.add_argument(
            "--config", metavar="CONFIGFILE", help="use this QuizML config file"
        )
    parser.add_argument(
        "--debug",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        help="show debug diagnostics",
    )
    parser.add_argument(
        "--verbose",
        action="store_const",
        dest="loglevel",
        const=logging.INFO,
        help="show informational diagnostics",
    )
    parser.add_argument(
        "--quiet", action="store_true", help="suppress informational output"
    )


def build_parser():
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
        prog="quizml",
        formatter_class=formatter,
        description="Convert YAML/Markdown questions to Blackboard or LaTeX output.",
    )
    parser.add_argument("-v", "--version", action="version", version=version("quizml"))
    subparsers = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    compile_parser = subparsers.add_parser(
        "compile", help="compile a quiz", formatter_class=formatter
    )
    _add_common_options(compile_parser)
    compile_parser.add_argument(
        "yaml_filename", metavar="FILE", help="QuizML YAML input"
    )
    compile_parser.add_argument(
        "-t",
        "--target",
        action="append",
        metavar="TARGET",
        help="target to compile; repeatable",
    )
    compile_parser.add_argument(
        "-w", "--watch", action="store_true", help="watch for changes"
    )

    diff_parser = subparsers.add_parser(
        "diff", help="compare questions across quiz files", formatter_class=formatter
    )
    _add_common_options(diff_parser, include_config=False)
    diff_parser.add_argument(
        "--check",
        action="store_true",
        help="exit nonzero if duplicate questions are found",
    )
    diff_parser.add_argument("files", nargs="+", metavar="FILE")

    grep_parser = subparsers.add_parser(
        "grep",
        aliases=["search"],
        help="search questions across quiz files",
        formatter_class=formatter,
    )
    _add_common_options(grep_parser, include_config=False)
    grep_parser.add_argument(
        "pattern", metavar="PATTERN", help="search string or regular expression"
    )
    grep_parser.add_argument(
        "paths",
        nargs="*",
        default=None,
        metavar="PATH",
        help="files or directories to search (default: current directory)",
    )
    grep_parser.add_argument(
        "-i",
        "--ignore-case",
        action="store_true",
        help="ignore case distinctions in pattern",
    )
    grep_parser.add_argument(
        "-F",
        "--fixed-strings",
        action="store_true",
        help="interpret pattern as fixed strings, not regular expressions",
    )
    grep_parser.add_argument(
        "-v",
        "--invert-match",
        action="store_true",
        help="select non-matching questions",
    )
    grep_parser.add_argument(
        "--field",
        metavar="FIELD",
        help="search only within a specific question field (e.g. question, figure, choices)",
    )
    grep_parser.add_argument(
        "-t",
        "--type",
        metavar="TYPE",
        help="filter by question type (e.g. mc, ma, tf)",
    )
    grep_parser.add_argument(
        "-u",
        "--unique",
        action="store_true",
        help="deduplicate identical or similar questions across files",
    )
    grep_parser.add_argument(
        "-l",
        "--files-with-matches",
        action="store_true",
        help="print only filenames of matching files",
    )
    grep_parser.add_argument(
        "-c",
        "--count",
        action="store_true",
        help="print count of matching questions",
    )
    grep_parser.add_argument(
        "--table",
        "--summary",
        action="store_true",
        dest="summary",
        help="display matching questions in a summary table",
    )
    grep_parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="write matching YAML questions to a file instead of stdout",
    )
    grep_parser.add_argument(
        "--no-provenance",
        action="store_true",
        help="omit provenance comments (# file: <Q#>) from YAML output",
    )
    grep_parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        default=True,
        help="recursively search subdirectories (default: True)",
    )
    grep_parser.add_argument(
        "--no-recursive",
        action="store_false",
        dest="recursive",
        help="do not search subdirectories",
    )
    grep_parser.add_argument(
        "--wrap",
        type=int,
        metavar="WIDTH",
        help="wrap Markdown fields at WIDTH characters in YAML output",
    )

    fmt_parser = subparsers.add_parser(
        "fmt", help="format YAML", formatter_class=formatter
    )
    fmt_parser.add_argument(
        "file",
        nargs="?",
        default="-",
        metavar="FILE",
        help="input file, or - for stdin",
    )

    sample_parser = subparsers.add_parser(
        "sample",
        help="expand and sample question-bank includes",
        formatter_class=formatter,
    )
    sample_parser.add_argument(
        "file",
        nargs="?",
        default="-",
        metavar="FILE",
        help="meta YAML input, or - for stdin",
    )
    sample_parser.add_argument(
        "-o",
        "--output",
        default="-",
        metavar="FILE",
        help="write static YAML here, or - for stdout (default)",
    )
    sample_parser.add_argument(
        "--seed",
        help="seed for sampled includes without their own seed",
    )
    sample_parser.add_argument(
        "--force", action="store_true", help="replace an existing output file"
    )

    pin_parser = subparsers.add_parser(
        "pin",
        help="stamp version/target metadata, generate question IDs, or freeze includes",
        formatter_class=formatter,
    )
    _add_common_options(pin_parser)
    pin_parser.add_argument(
        "file",
        nargs="?",
        default="-",
        metavar="FILE",
        help="input YAML file (updated in place by default), or - for stdin",
    )
    pin_parser.add_argument(
        "-o",
        "--output",
        default=None,
        metavar="FILE",
        help="write pinned YAML to this file instead of updating in place",
    )
    pin_parser.add_argument(
        "-t",
        "--target",
        action="append",
        metavar="TARGET",
        help="target to record in _targets; repeatable",
    )
    pin_parser.add_argument(
        "--add-ids",
        action="store_true",
        help="generate deterministic IDs for questions missing an id field",
    )
    pin_parser.add_argument(
        "--freeze-includes",
        action="store_true",
        help="expand _include directives in place",
    )
    pin_parser.add_argument(
        "--seed",
        help="seed for sampled includes when --freeze-includes is used",
    )
    pin_parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="overwrite existing header metadata or output file",
    )

    fmt_modes = fmt_parser.add_mutually_exclusive_group()
    fmt_modes.add_argument(
        "-i",
        "--in-place",
        action="store_true",
        help="write changes back to the input file",
    )
    fmt_modes.add_argument(
        "--check",
        action="store_true",
        help="exit nonzero if formatting would change the input",
    )
    fmt_modes.add_argument(
        "--diff", action="store_true", help="show the proposed changes"
    )
    fmt_parser.add_argument(
        "--wrap",
        type=int,
        metavar="WIDTH",
        help="wrap Markdown fields at WIDTH characters",
    )

    clean_parser = subparsers.add_parser(
        "clean", help="remove generated build artifacts", formatter_class=formatter
    )
    clean_parser.add_argument(
        "path", nargs="?", default=".", help="directory or YAML file"
    )
    clean_parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="recursively scan subdirectories for quiz YAML files",
    )
    clean_parser.add_argument(
        "--dry-run", action="store_true", help="list without deleting"
    )
    clean_parser.add_argument(
        "--config", metavar="CONFIGFILE", help="use a specific QuizML config file"
    )
    clean_parser.add_argument(
        "--quiet", action="store_true", help="suppress informational output"
    )

    cache_parser = subparsers.add_parser(
        "cache", help="manage cached equation and image conversions"
    )
    cache_subparsers = cache_parser.add_subparsers(dest="cache_command", required=True)
    cache_subparsers.add_parser("clear", help="remove all cached renderings")

    init_parser = subparsers.add_parser(
        "init",
        help="initialize QuizML configuration and templates",
        formatter_class=formatter,
    )
    init_parser.add_argument(
        "scope",
        nargs="?",
        default="local",
        choices=("local", "user"),
        help="where to initialize (default: local _quizml/)",
    )
    init_parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        dest="all_files",
        help="copy all bundled templates, assets, and schema.json",
    )
    init_parser.add_argument(
        "--latex",
        action="store_true",
        help="copy LaTeX exam templates and math preamble",
    )
    init_parser.add_argument(
        "--html",
        action="store_true",
        help="copy HTML preview template, CSS, and math preamble",
    )
    init_parser.add_argument(
        "--bb",
        action="store_true",
        help="copy Blackboard template, CSS, and math preamble",
    )
    init_parser.add_argument(
        "--docx",
        action="store_true",
        help="copy Word (docxtpl) reference template",
    )
    init_parser.add_argument(
        "--schema",
        action="store_true",
        help="copy schema.json for custom validation rules",
    )
    init_parser.add_argument(
        "-t",
        "--template",
        action="append",
        dest="templates",
        metavar="FILE",
        help="copy a specific bundled template file; repeatable",
    )
    init_parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="overwrite existing files in the destination directory",
    )

    docs_parser = subparsers.add_parser(
        "docs", help="display documentation", formatter_class=formatter
    )
    docs_parser.add_argument("topic", nargs="?", default="", help="topic name or all")
    docs_parser.add_argument(
        "--no-pager", action="store_true", help="write directly to stdout"
    )

    subparsers.add_parser("info", help="print configuration paths as JSON")

    targets_parser = subparsers.add_parser(
        "targets", help="list configured targets", formatter_class=formatter
    )
    _add_common_options(targets_parser)

    completion_parser = subparsers.add_parser(
        "completion", help="print a shell completion script"
    )
    completion_parser.add_argument("shell", choices=("bash", "zsh", "fish"))
    return parser


def _normalize_argv(argv):
    """Treat a leading file or compile option as the historical compile shorthand."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        return argv
    if argv[0] not in COMMANDS and argv[0] not in ("-h", "--help", "-v", "--version"):
        argv.insert(0, "compile")
    return argv


def _dispatch(args, parser):
    if args.command == "compile":
        import quizml.cli.compile

        if args.watch:
            from quizml.cli.livereload import LiveReloadServer

            live_reload = LiveReloadServer()
            try:
                if not quizml.cli.compile.compile(args, live_reload=live_reload):
                    return False
                quizml.cli.compile.compile_on_change(args, live_reload=live_reload)
                return True
            finally:
                live_reload.stop()
        return quizml.cli.compile.compile(args)

    if args.command == "diff":
        import quizml.cli.diff

        args.yaml_filename, *args.otherfiles = args.files
        return quizml.cli.diff.diff(args)

    if args.command in ("grep", "search"):
        from quizml.cli.grep import run_grep

        return run_grep(args)

    if args.command == "fmt":
        import quizml.cli.format

        return quizml.cli.format.run_format(args)

    if args.command == "sample":
        from quizml.cli.sample import run_sample

        return run_sample(args)

    if args.command == "pin":
        from quizml.cli.pin import run_pin

        return run_pin(args)

    if args.command == "clean":
        from pathlib import Path
        from types import SimpleNamespace

        from quizml.cli.cleanup import cleanup_yaml_files
        from quizml.cli.config import get_config

        path = Path(args.path)
        yaml_for_cfg = (
            None
            if (path.is_dir() or (not path.exists() and not path.suffix))
            else str(path)
        )
        config = get_config(
            SimpleNamespace(config=args.config, yaml_filename=yaml_for_cfg)
        )
        targets = config.get("targets")
        if not isinstance(targets, list):
            raise QuizMLConfigError("The config file must define a list of targets.")

        extra_clean = (
            {"recursive": True} if getattr(args, "recursive", False) else {}
        )
        if path.is_dir() or (not path.exists() and not path.suffix):
            result = cleanup_yaml_files(
                str(path),
                dry_run=args.dry_run,
                targets=targets,
                quiet=args.quiet,
                **extra_clean,
            )
        else:
            result = cleanup_yaml_files(
                str(path.parent or Path(".")),
                dry_run=args.dry_run,
                target_stems={path.stem},
                targets=targets,
                quiet=args.quiet,
            )
        return result is not None

    if args.command == "cache":
        from ..cache import CACHE_DIR, clear_cache

        try:
            size = clear_cache()
        except OSError as err:
            raise QuizMLConfigError(
                f"Could not clear QuizML cache at {CACHE_DIR}: {err}"
            ) from err
        err_console.print(f"Cleared {size} bytes from QuizML cache at {CACHE_DIR}")
        return True

    if args.command == "init":
        from quizml.cli import init

        init_kwargs = {
            k: v
            for k, v in {
                "all_files": getattr(args, "all_files", False),
                "latex": getattr(args, "latex", False),
                "html": getattr(args, "html", False),
                "bb": getattr(args, "bb", False),
                "docx": getattr(args, "docx", False),
                "schema": getattr(args, "schema", False),
                "templates": getattr(args, "templates", None),
                "force": getattr(args, "force", False),
            }.items()
            if v
        }
        fn = init.init_local if args.scope == "local" else init.init_user
        return fn(**init_kwargs)

    if args.command == "docs":
        from quizml.cli.docs import handle_docs

        handle_docs(args.topic, no_pager=args.no_pager)
        return True

    if args.command == "info":
        import json

        from quizml.paths import FileLocator

        from ..cache import CACHE_DIR, get_cache_size

        locator = FileLocator()

        try:
            config_file = locator.path("quizml.cfg")
        except FileNotFoundError:
            config_file = "not found"
        info = {
            "version": version("quizml"),
            "cwd": locator.cw_dir,
            "local_templates": locator.local_template_dir,
            "user_config_dir": locator.app_dir,
            "user_templates": locator.user_template_dir,
            "package_templates": locator.pkg_template_dir,
            "search_paths": locator.dirlist,
            "config_file": config_file,
            "cache_dir": CACHE_DIR,
            "cache_size_bytes": get_cache_size(),
        }
        sys.stdout.write(json.dumps(info, indent=4) + "\n")
        return True

    if args.command == "targets":
        from quizml.cli.ui import print_target_list

        args.yaml_filename = None
        return print_target_list(args)

    if args.command == "completion":
        from quizml.cli import shellcompletion

        sys.stdout.write(getattr(shellcompletion, args.shell)() + "\n")
        return True

    parser.error(f"unknown command: {args.command}")


def main(argv=None):
    from .errorhandler import print_error

    install(show_locals=False, console=err_console)
    parser = build_parser()
    args = parser.parse_args(_normalize_argv(argv))
    if not hasattr(args, "config"):
        args.config = None
    if not hasattr(args, "loglevel") or args.loglevel is None:
        args.loglevel = logging.WARNING
    if not hasattr(args, "quiet"):
        args.quiet = False

    logging.basicConfig(
        force=True,
        level=args.loglevel,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(console=err_console, rich_tracebacks=True, show_path=False)
        ],
    )

    try:
        if not _dispatch(args, parser):
            sys.exit(1)
    except QuizMLError as err:
        print_error(err)
        sys.exit(1)
    except BrokenPipeError:
        try:
            sys.stdout.close()
        except OSError:
            pass
        sys.exit(0)
    except KeyboardInterrupt:
        err_console.print("[bold red]Interrupted[/bold red]")
        sys.exit(130)


if __name__ == "__main__":
    main()
