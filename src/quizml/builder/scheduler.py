"""Headless build scheduler and target executor."""

import pathlib
import shlex
import subprocess
from dataclasses import dataclass

from quizml import renderer
from quizml.exceptions import (
    Jinja2SyntaxError,
    LatexEqError,
    MarkdownError,
    QuizMLError,
)
from quizml.transcoder import MarkdownTranscoder


@dataclass
class TargetResult:
    """Result of compiling or building a single QuizML target."""

    name: str
    descr: str
    out: str
    descr_cmd: str
    success: bool
    error_message: str | None = None
    is_build_cmd: bool = False


def compile_cmd_target(target: dict) -> tuple[bool, str | None]:
    """Executes external command line script for post-compilation build targets."""
    command = shlex.split(target["build_cmd"])
    try:
        subprocess.check_output(command, stderr=subprocess.STDOUT)
        return True, None
    except subprocess.CalledProcessError as e:
        err_out = e.output.decode("utf-8", errors="replace") if e.output else str(e)
        return False, err_out
    except FileNotFoundError:
        return False, f"Command not found: {command[0]}"


def compile_render_target(
    target: dict,
    transcoder: MarkdownTranscoder,
    extra_context: dict | None = None,
) -> tuple[bool, str | None]:
    """Transcodes and renders a template target to disk."""
    try:
        yaml_transcoded = transcoder.transcode_target(target)
        rendered_doc = renderer.render(
            yaml_transcoded, target["template"], extra_context
        )

        out_path = pathlib.Path(target["out"])
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(rendered_doc, bytes):
            out_path.write_bytes(rendered_doc)
        else:
            out_path.write_text(rendered_doc, encoding="utf-8")

        return True, None

    except (LatexEqError, MarkdownError, FileNotFoundError, Jinja2SyntaxError, QuizMLError) as err:
        return False, str(err)
    except Exception as err:
        return False, f"Unexpected error: {err}"


def execute_targets(
    target_list: list[dict],
    transcoder: MarkdownTranscoder,
    build: bool = False,
    is_targeted: bool = False,
    extra_context: dict | None = None,
) -> list[TargetResult]:
    """Iterates through resolved targets, checking dependencies and executing them in order."""
    results: list[TargetResult] = []
    success_map: dict[str, bool] = {}

    for target in target_list:
        is_build_cmd = "build_cmd" in target
        name = target.get("name", "")
        descr = target.get("descr", name)
        out = target.get("out", "")
        descr_cmd = target.get("descr_cmd", descr)

        # Skip build target if neither --build nor specific target was requested
        if is_build_cmd and not (build or is_targeted):
            continue

        # Check dependencies
        dep = target.get("dep")
        if dep:
            dep_names = dep if isinstance(dep, list) else [dep]
            dep_failed = any(not success_map.get(d, False) for d in dep_names)
            if dep_failed:
                result = TargetResult(
                    name=name,
                    descr=descr,
                    out=out,
                    descr_cmd=descr_cmd,
                    success=False,
                    error_message=f"Dependency failed: {dep}",
                    is_build_cmd=is_build_cmd,
                )
                results.append(result)
                success_map[name] = False
                break

        if is_build_cmd:
            success, err_msg = compile_cmd_target(target)
        elif "template" in target:
            success, err_msg = compile_render_target(target, transcoder, extra_context)
        else:
            success, err_msg = False, "Unknown target type (no template or build_cmd)"

        success_map[name] = success
        result = TargetResult(
            name=name,
            descr=descr,
            out=out,
            descr_cmd=descr_cmd,
            success=success,
            error_message=err_msg,
            is_build_cmd=is_build_cmd,
        )
        results.append(result)

        if not success:
            break

    return results
