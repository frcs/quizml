"""CLI adapter for quiz compilation and watch mode."""

import os
import pathlib
import threading
from time import sleep

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from quizml.build.cleanup import get_cleanup_candidates
from quizml.build.compiler import (
    compile_cmd_target,
    compile_quiz,
    compile_target,
    resolve_output_path,
)
from quizml.build.config import load_config
from quizml.cli.errorhandler import err_console, print_error
from quizml.cli.livereload import LiveReloadServer
from quizml.cli.ui import (
    add_hyperlinks,
    print_quiet_ouputs,
    print_stats_table,
    print_table_ouputs,
)
from quizml.exceptions import QuizMLConfigError, QuizMLError


def compile(args, live_reload=None):
    """Compile the targets of a YAML file and print terminal summaries."""
    if args.watch and args.yaml_filename == "-":
        raise QuizMLConfigError("--watch cannot be used when reading from stdin (-).")

    extra_context = {}
    if args.watch:
        if live_reload is None:
            live_reload = LiveReloadServer()
        port = live_reload.start()
        if port:
            extra_context["livereload_port"] = port

    build_result = compile_quiz(
        args.yaml_filename,
        config_path=getattr(args, "config", None),
        targets=getattr(args, "target", None),
        extra_context=extra_context,
        on_stats=None if args.quiet else print_stats_table,
    )

    if live_reload is not None:
        live_reload.update_timestamp()

    targets_output = []
    targets_quiet_output = []
    for res in build_result.targets:
        ok = res.status == "succeeded"
        out = res.output_path or ""
        targets_output.append(
            [
                res.description,
                add_hyperlinks(res.descr_cmd, out),
                "" if ok else "[FAIL]",
            ]
        )
        targets_quiet_output.append(
            [add_hyperlinks(out, out), "" if ok else "[FAIL]"]
        )

    if args.quiet:
        print_quiet_ouputs(targets_quiet_output)
    else:
        print_table_ouputs(targets_output)

    return build_result.ok


def _collect_ignored_paths(yaml_filename, config_path=None):
    """Collect absolute string paths of all target outputs and sidecars to ignore in watch mode."""
    if not yaml_filename or yaml_filename == "-":
        return set()
    full_path = pathlib.Path(os.path.abspath(yaml_filename))
    ignored = set()
    try:
        config = load_config(config_path, yaml_filename=str(full_path))
        for p in get_cleanup_candidates(
            str(full_path), config.get("targets", [])
        ):
            ignored.add(str(p))
            ignored.add(str(p.resolve()))
    except Exception:
        pass
    return ignored


def compile_on_change(args, live_reload=None):
    """Re-compile targets if input QuizML YAML or template files change on disk."""
    waitingtxt = "\n...waiting for a file change to re-compile the document...\n "
    err_console.print(waitingtxt)

    full_yaml_path = os.path.abspath(args.yaml_filename)
    full_yaml_resolved = str(pathlib.Path(full_yaml_path).resolve())
    watch_dir = pathlib.Path(full_yaml_path).parent
    rebuild_event = threading.Event()
    watched_exts = {".yaml", ".yml", ".j2", ".cfg", ".json", ".css", ".tex"}
    ignored_paths = _collect_ignored_paths(
        args.yaml_filename, getattr(args, "config", None)
    )

    def _should_trigger(path):
        abs_path = os.path.abspath(path)
        resolved_path = str(pathlib.Path(abs_path).resolve())
        if abs_path in ignored_paths or resolved_path in ignored_paths:
            return False
        p = pathlib.Path(abs_path)
        try:
            rel_parts = p.relative_to(watch_dir).parts
            if any(part.startswith(".") for part in rel_parts):
                return False
        except ValueError:
            if p.name.startswith("."):
                return False
        if abs_path == full_yaml_path or resolved_path == full_yaml_resolved:
            return True
        return p.suffix.lower() in watched_exts

    class Handler(FileSystemEventHandler):
        def on_modified(self, event):
            if not event.is_directory and _should_trigger(event.src_path):
                rebuild_event.set()

        def on_moved(self, event):
            if not event.is_directory and _should_trigger(event.dest_path):
                rebuild_event.set()

    observer = Observer()
    observer.schedule(Handler(), str(watch_dir), recursive=True)
    observer.start()

    try:
        while True:
            if rebuild_event.wait(timeout=0.5):
                rebuild_event.clear()
                sleep(0.1)
                rebuild_event.clear()

                err_console.print(
                    "[bold yellow]Change detected, re-compiling...[/bold yellow]"
                )
                try:
                    compile(args, live_reload=live_reload)
                    ignored_paths.update(
                        _collect_ignored_paths(
                            args.yaml_filename, getattr(args, "config", None)
                        )
                    )
                except QuizMLError as err:
                    print_error(err)
                err_console.print(waitingtxt)

    except KeyboardInterrupt:
        err_console.print("[bold red]Stopping watch mode...[/bold red]")
        observer.stop()

    observer.join()


__all__ = [
    "compile",
    "compile_cmd_target",
    "compile_on_change",
    "compile_target",
    "resolve_output_path",
]
