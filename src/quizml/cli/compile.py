import logging
import os
import pathlib
import shlex
import subprocess
import threading
from time import sleep

from rich import print
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

import quizml.cli.filelocator as filelocator
import quizml.markdown.markdown as md
from quizml import renderer

# Imported from refactored modules
from quizml.cli.config import get_config, get_target_list
from quizml.cli.errorhandler import err_console
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


def compile_cmd_target(target):
    """execute command line scripts of the post compilation targets."""
    command = shlex.split(target["build_cmd"])

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as err:
        details = err.stderr or err.stdout or str(err)
        raise QuizMLBuildError(
            f"Build command failed ({err.returncode}): {details.strip()}"
        ) from err
    except FileNotFoundError as err:
        raise QuizMLBuildError(f"Build command not found: {command[0]}") from err
    return True


def compile_target(target, transcoder, extra_context=None):
    """compiles one target"""

    yaml_transcoded = transcoder.transcode_target(target)
    rendered_doc = renderer.render(yaml_transcoded, target["template"], extra_context)

    try:
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

    # read config file
    config = get_config(args)

    # load Schema file
    try:
        schema_path = filelocator.locate.path(config["schema_path"])
    except FileNotFoundError as err:
        raise QuizMLConfigError(
            f"Schema file {config['schema_path']} not found; check the config file."
        ) from err

    # load QuizMLYaml file
    yaml_data, schema = load(args.yaml_filename, validate=True, schema_path=schema_path)

    logging.debug(yaml_data)

    # load all markdown entries into a list
    # and build dictionaries of their HTML and LaTeX translations
    base_dir = os.path.dirname(os.path.abspath(args.yaml_filename))
    transcoder = md.MarkdownTranscoder(yaml_data, schema, base_dir=base_dir)

    # diplay stats about the questions
    if not args.quiet:
        print_stats_table(yaml_data, config)

    # get target list from config file
    try:
        target_list = get_target_list(args, config, yaml_data)
    except FileNotFoundError as err:
        raise QuizMLConfigError(str(err)) from err

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
        # skipping build target if build option is not on
        if ("build_cmd" in target) and not (args.build or args.target):
            continue

        success = False

        # a build target (eg. compile pdf of generated latex) a build
        # target only requires the execution of an external command,
        # ie. no python code required
        #
        if ("build_cmd" in target) and (args.build or args.target):
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
                success = compile_cmd_target(target)
            else:
                success = False

        # a template task that needs to be rendered
        elif "template" in target:
            success = compile_target(target, transcoder, extra_context)

        success_list[target["name"]] = success

        targets_output.append(
            [
                target["descr"],
                add_hyperlinks(target["descr_cmd"], target["out"]),
                "" if success else "[FAIL]",
            ]
        )

        targets_quiet_output.append(
            [add_hyperlinks(target["out"], target["out"]), "" if success else "[FAIL]"]
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

    class Handler(FileSystemEventHandler):
        def on_modified(self, event):
            if os.path.abspath(event.src_path) == full_yaml_path:
                rebuild_event.set()

        def on_moved(self, event):
            # Support for editors that use atomic saves (write to tmp -> rename)
            if os.path.abspath(event.dest_path) == full_yaml_path:
                rebuild_event.set()

    observer = Observer()
    observer.schedule(Handler(), ".")  # watch the local directory
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

                print("[bold yellow]Change detected, re-compiling...[/bold yellow]")
                compile(args, live_reload=live_reload)
                print(waitingtxt)

    except KeyboardInterrupt:
        print("[bold red]Stopping watch mode...[/bold red]")
        observer.stop()

    observer.join()
