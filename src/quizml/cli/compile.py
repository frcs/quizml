import logging
import os
import pathlib
import shlex
import subprocess
import threading
from time import sleep

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

import quizml.markdown.markdown as md
from quizml import renderer

# Imported from refactored modules
from quizml.cli.config import get_config, get_target_list
from quizml.cli.errorhandler import err_console
from quizml.cli.filelocator import FileLocator
from quizml.cli.livereload import LiveReloadServer
from quizml.cli.ui import (
    add_hyperlinks,
    print_quiet_ouputs,
    print_stats_table,
    print_table_ouputs,
)
from quizml.exceptions import (
    QuizMLBuildError,
    QuizMLConfigError,
)
from quizml.loader import load


def compile_cmd_target(target, cwd=None):
    """execute command line scripts of the post compilation targets."""
    command = shlex.split(target["build_cmd"])

    try:
        subprocess.run(command, check=True, capture_output=True, text=True, cwd=cwd)
    except subprocess.CalledProcessError as err:
        output = err.stderr or err.stdout or ""
        details = (
            "\n".join(output.splitlines()[-40:]) or "No diagnostic output was produced."
        )
        raise QuizMLBuildError(
            f"Build command failed ({err.returncode}):\n{details}"
        ) from err
    except FileNotFoundError as err:
        raise QuizMLBuildError(f"Build command not found: {command[0]}") from err
    except OSError as err:
        detail = err.strerror or str(err)
        raise QuizMLBuildError(
            f"Could not start build command '{command[0]}': {detail}"
        ) from err
    return True


def resolve_output_path(output, base_dir):
    """Resolve a target output relative to its source document directory."""
    path = pathlib.Path(output).expanduser()
    if not path.is_absolute():
        path = pathlib.Path(base_dir) / path
    return path.resolve()


def compile_target(target, transcoder, extra_context=None, template_search_dirs=None):
    """compiles one target"""
    import sys

    yaml_transcoded = transcoder.transcode_target(target)
    merged_extra = {"target": target}
    if isinstance(target.get("context"), dict):
        merged_extra.update(target["context"])
    if extra_context:
        merged_extra.update(extra_context)
    render_kwargs = {"template_search_dirs": template_search_dirs}
    if target.get("jinja_filters"):
        render_kwargs["jinja_filters"] = target["jinja_filters"]
    rendered_doc = renderer.render(
        yaml_transcoded,
        target["template"],
        merged_extra,
        **render_kwargs,
    )

    try:
        if target["out"] == "-":
            if isinstance(rendered_doc, bytes):
                sys.stdout.buffer.write(rendered_doc)
                sys.stdout.buffer.flush()
            else:
                sys.stdout.write(rendered_doc)
                sys.stdout.flush()
        else:
            pathlib.Path(target["out"]).parent.mkdir(parents=True, exist_ok=True)
            if isinstance(rendered_doc, bytes):
                pathlib.Path(target["out"]).write_bytes(rendered_doc)
            else:
                pathlib.Path(target["out"]).write_text(rendered_doc, encoding="utf-8")
    except OSError as err:
        raise QuizMLBuildError(
            f"Could not write output {target['out']}: {err}"
        ) from err
    return True


def compile(args, live_reload=None):
    """compiles the targets of a yaml file"""
    if args.watch and args.yaml_filename == "-":
        raise QuizMLConfigError("--watch cannot be used when reading from stdin (-).")

    # read config file
    config = get_config(args)

    if args.yaml_filename == "-":
        input_dir = pathlib.Path.cwd().resolve()
    else:
        input_dir = pathlib.Path(args.yaml_filename).expanduser().resolve().parent
    base_dir = str(input_dir)

    # load Schema file
    locator = FileLocator(base_dir=base_dir, config_dir=config.get("_config_dir"))
    schema_ref = config.get("schema_path", "schema.json")
    try:
        schema_path = locator.path(schema_ref)
    except FileNotFoundError as err:
        raise QuizMLConfigError(
            f"Schema file {schema_ref} not found; check the config file."
        ) from err

    # load QuizMLYaml file
    yaml_data, schema = load(args.yaml_filename, validate=True, schema_path=schema_path)

    logging.debug(yaml_data)

    # load all markdown entries into a list
    # and build dictionaries of their HTML and LaTeX translations
    transcoder = md.MarkdownTranscoder(yaml_data, schema, base_dir=base_dir)

    # diplay stats about the questions
    if not args.quiet:
        print_stats_table(yaml_data, config)

    # get target list from config file
    try:
        target_list = get_target_list(args, config, yaml_data)
    except FileNotFoundError as err:
        raise QuizMLConfigError(str(err)) from err

    for target in target_list:
        if target.get("out") and target["out"] != "-":
            target["out"] = str(resolve_output_path(target["out"], input_dir))

    # Prepare LiveReload if watching
    extra_context = {}
    if args.watch:
        if live_reload is None:
            live_reload = LiveReloadServer()
        port = live_reload.start()
        if port:
            extra_context["livereload_port"] = port

    # sets up list of the output for each build
    targets_output = []
    targets_quiet_output = []
    success_list = {}
    all_success = True

    for _i, target in enumerate(target_list):
        # Build-command targets run only when included in explicit target
        # selection, directly or through an alias such as "build".
        if ("build_cmd" in target) and not args.target:
            continue

        success = False

        # a build target (eg. compile pdf of generated latex) a build
        # target only requires the execution of an external command,
        # ie. no python code required
        #
        if ("build_cmd" in target) and args.target:
            # need to check if there is a dependency,
            # and if this dependency compiled successfully
            deps = target.get("dep")
            if not deps:
                dep_ok = True
            elif isinstance(deps, list):
                dep_ok = all(success_list.get(d, False) for d in deps)
            else:
                dep_ok = success_list.get(deps, False)

            if dep_ok:
                success = compile_cmd_target(target, cwd=input_dir)
            else:
                success = False

        # a template task that needs to be rendered
        elif "template" in target:
            success = compile_target(
                target, transcoder, extra_context, template_search_dirs=locator.dirlist
            )

        target_name = target.get("name", "<unnamed>")
        target_descr = target.get("descr", target_name)
        target_out = target.get("out", "")
        target_descr_cmd = target.get("descr_cmd", target_out)

        success_list[target_name] = success

        targets_output.append(
            [
                target_descr,
                add_hyperlinks(target_descr_cmd, target_out),
                "" if success else "[FAIL]",
            ]
        )

        targets_quiet_output.append(
            [add_hyperlinks(target_out, target_out), "" if success else "[FAIL]"]
        )

        if not success:
            all_success = False
            break

    # Update timestamp for LiveReload clients
    if live_reload is not None:
        live_reload.update_timestamp()

    # display stats about the outputs
    if args.quiet:
        print_quiet_ouputs(targets_quiet_output)
    else:
        print_table_ouputs(targets_output)

    return all_success


def compile_on_change(args, live_reload=None):
    """compiles the targets if input QuizMLYaml file has changed on disk"""

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
            # Support for editors that use atomic saves (write to tmp -> rename)
            if not event.is_directory and _should_trigger(event.dest_path):
                rebuild_event.set()

    observer = Observer()
    observer.schedule(
        Handler(), str(pathlib.Path(full_yaml_path).parent), recursive=True
    )
    observer.start()

    try:
        while True:
            # Wait for the event, checking every 0.5s to allow KeyboardInterrupt
            if rebuild_event.wait(timeout=0.5):
                rebuild_event.clear()

                # Debounce: wait a brief moment for file operations to settle
                sleep(0.1)
                # Clear any events that occurred during the sleep
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
