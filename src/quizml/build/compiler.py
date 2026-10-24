"""Headless build pipeline and target compiler for QuizML."""

import logging
import pathlib
import shlex
import subprocess
from dataclasses import dataclass, field
from typing import Literal

from quizml import rendering
from quizml.build.config import (
    check_quizml_version,
    load_config,
    resolve_targets,
)
from quizml.exceptions import QuizMLBuildError, QuizMLConfigError
from quizml.markdown import MarkdownTranscoder
from quizml.paths import FileLocator
from quizml.yaml import load
from quizml.yaml.parser import peek_yaml_header


@dataclass
class TargetResult:
    """Structured result for a single compiled target."""

    name: str
    status: Literal["succeeded", "failed", "skipped"]
    output_path: str | None = None
    description: str = ""
    descr_cmd: str = ""
    error: str | None = None


@dataclass
class BuildResult:
    """Structured result of compiling a QuizML quiz."""

    targets: list[TargetResult] = field(default_factory=list)
    document: dict | None = None
    config: dict | None = None

    @property
    def ok(self) -> bool:
        return all(t.status != "failed" for t in self.targets)


def compile_cmd_target(target, cwd=None, tex_search_dirs=None):
    """Execute command line scripts of the post-compilation targets."""
    from quizml.markdown.latextools import build_tex_env

    command = shlex.split(target["build_cmd"])
    run_kwargs = {"check": True, "capture_output": True, "text": True, "cwd": cwd}
    if tex_search_dirs:
        run_kwargs["env"] = build_tex_env(tex_search_dirs)

    try:
        subprocess.run(command, **run_kwargs)
    except subprocess.CalledProcessError as err:
        output = err.stderr or err.stdout or ""
        details = (
            "\n".join(output.splitlines()[-40:])
            or "No diagnostic output was produced."
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
    """Compile one template target."""
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
    rendered_doc = rendering.render(
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


def compile_quiz(
    yaml_filename,
    *,
    config_path=None,
    targets=None,
    extra_context=None,
    on_stats=None,
    warn_fn=None,
) -> BuildResult:
    """Headless compiler for a QuizML file."""
    config = load_config(
        config_path, yaml_filename=yaml_filename, warn_fn=warn_fn
    )

    if yaml_filename == "-":
        input_dir = pathlib.Path.cwd().resolve()
    else:
        input_dir = pathlib.Path(yaml_filename).expanduser().resolve().parent
    base_dir = str(input_dir)

    locator = FileLocator(base_dir=base_dir, config_dir=config.get("_config_dir"))
    header_peek = peek_yaml_header(yaml_filename)
    header_schema = (
        header_peek.get("_schema") if isinstance(header_peek, dict) else None
    )
    schema_ref = (
        header_schema.strip()
        if isinstance(header_schema, str) and header_schema.strip()
        else config.get("schema_path", "schema.json")
    )
    try:
        schema_path = locator.path(schema_ref)
    except FileNotFoundError as err:
        raise QuizMLConfigError(
            f"Schema file {schema_ref} not found; check the config file."
        ) from err

    yaml_data = load(
        yaml_filename,
        validate=True,
        schema_path=schema_path,
        schema_extensions=config.get("schema_extensions"),
    )

    if yaml_data.get("header", {}).get("_quizml"):
        check_quizml_version(
            yaml_data["header"]["_quizml"], str(yaml_filename), warn_fn=warn_fn
        )

    logging.debug(yaml_data)

    transcoder = MarkdownTranscoder(yaml_data, base_dir=base_dir)
    config_texinputs = config.get("texinputs", [])
    tex_search_dirs = [
        base_dir,
        *config_texinputs,
        *transcoder.search_dirs,
        *locator.dirlist,
    ]

    if on_stats is not None:
        on_stats(yaml_data, config)

    try:
        target_list = resolve_targets(
            config, yaml_data, target_names=targets
        )
    except FileNotFoundError as err:
        raise QuizMLConfigError(str(err)) from err

    for target in target_list:
        target.setdefault("tex_search_dirs", tex_search_dirs)
        if target.get("out") and target["out"] != "-":
            target["out"] = str(resolve_output_path(target["out"], input_dir))

    results: list[TargetResult] = []
    success_list: dict[str, bool] = {}
    explicit_targets = bool(
        targets or yaml_data.get("header", {}).get("_targets")
    )

    for target in target_list:
        if ("build_cmd" in target) and not explicit_targets:
            continue

        success = False
        if ("build_cmd" in target) and explicit_targets:
            deps = target.get("dep")
            if not deps:
                dep_ok = True
            elif isinstance(deps, list):
                dep_ok = all(success_list.get(d, False) for d in deps)
            else:
                dep_ok = success_list.get(deps, False)

            if dep_ok:
                success = compile_cmd_target(
                    target, cwd=input_dir, tex_search_dirs=tex_search_dirs
                )
            else:
                success = False
        elif "template" in target:
            success = compile_target(
                target,
                transcoder,
                extra_context,
                template_search_dirs=locator.dirlist,
            )

        target_name = target.get("name", "<unnamed>")
        target_descr = target.get("descr", target_name)
        target_out = target.get("out", "")
        target_descr_cmd = target.get("descr_cmd", target_out)

        success_list[target_name] = success
        results.append(
            TargetResult(
                name=target_name,
                status="succeeded" if success else "failed",
                output_path=target_out,
                description=target_descr,
                descr_cmd=target_descr_cmd,
            )
        )

        if not success:
            break

    return BuildResult(targets=results, document=yaml_data, config=config)
