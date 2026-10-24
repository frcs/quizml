"""CLI adapter for quiz compilation and watch mode."""

import os
import pathlib
import threading
from time import sleep

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from quizml.build.compiler import (
    compile_cmd_target,
    compile_quiz,
    compile_target,
    resolve_output_path,
)
from quizml.cli.errorhandler import err_console
from quizml.cli.livereload import LiveReloadServer
from quizml.cli.ui import (
    add_hyperlinks,
    print_quiet_ouputs,
    print_stats_table,
    print_table_ouputs,
)
from quizml.exceptions import QuizMLConfigError


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


def compile_on_change(args, live_reload=None):
    """Re-compile targets if input QuizML YAML or template files change on disk."""
    waitingtxt = "\n...waiting for a file change to re-compile the document...\n "
    err_console.print(waitingtxt)

    full_yaml_path = os.path.abspath(args.yaml_filename)
    rebuild_event = threading.Event()
    watched_exts = {".yaml", ".yml", ".j2", ".cfg", ".json", ".css", ".tex"}

    def _should_trigger(path):
        abs_path = os.path.abspath(path)
        if abs_path == full_yaml_path:
            return True
        return pathlib.Path(abs_path).suffix.lower() in watched_exts

    class Handler(FileSystemEventHandler):
        def on_modified(self, event):
            if not event.is_directory and _should_trigger(event.src_path):
                rebuild_event.set()

        def on_moved(self, event):
            if not event.is_directory and _should_trigger(event.dest_path):
                rebuild_event.set()

    observer = Observer()
    observer.schedule(
        Handler(), str(pathlib.Path(full_yaml_path).parent), recursive=True
    )
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
                compile(args, live_reload=live_reload)
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
