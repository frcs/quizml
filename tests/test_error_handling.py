import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest
from jinja2 import TemplateError

from quizml.build import compile_cmd_target
from quizml.exceptions import (
    DvisvgmNotFoundError,
    GhostscriptNotFoundError,
    Jinja2SyntaxError,
    LatexCompilationError,
    LatexNotFoundError,
    LatexToolError,
    QuizMLBuildError,
    TemplateRenderError,
)
from quizml.markdown.latextools import LatexRunner, _communicate
from quizml.rendering import docx as docx_renderer


def test_latex_launch_permission_error_is_typed():
    with LatexRunner() as runner:
        with (
            patch(
                "quizml.markdown.latextools.subprocess.run",
                side_effect=PermissionError("permission denied"),
            ),
            pytest.raises(LatexToolError, match="Could not start fake-tool"),
        ):
            runner._run_checked(["fake-tool"], "fake-tool", runner.temp_dir)


def test_latex_communication_error_is_typed():
    process = MagicMock()
    process.communicate.side_effect = OSError("pipe failed")

    with pytest.raises(LatexToolError, match="Could not collect output from fake-tool"):
        _communicate(process, "fake-tool")


def test_latex_failure_output_is_limited_to_last_40_lines():
    process = subprocess.CompletedProcess(
        ["fake-tool"], 1, "\n".join(f"line {i}" for i in range(60)), ""
    )
    with LatexRunner() as runner:
        with (
            patch("quizml.markdown.latextools.subprocess.run", return_value=process),
            pytest.raises(LatexCompilationError) as exc_info,
        ):
            runner._run_checked(["fake-tool"], "fake-tool", runner.temp_dir)

    assert "line 0" not in str(exc_info.value)
    assert "line 59" in str(exc_info.value)


def test_build_failure_output_is_limited_to_last_40_lines():
    output = "\n".join(f"line {i}" for i in range(60))
    failure = subprocess.CalledProcessError(1, ["fake-tool"], stderr=output)
    with (
        patch("quizml.build.compiler.subprocess.run", side_effect=failure),
        pytest.raises(QuizMLBuildError) as exc_info,
    ):
        compile_cmd_target({"build_cmd": "fake-tool"})

    assert "line 0" not in str(exc_info.value)
    assert "line 59" in str(exc_info.value)


def test_docx_template_errors_use_template_error_type(monkeypatch):
    class BrokenDocxTemplate:
        def __init__(self, filename):
            pass

        def render(self, context):
            raise TemplateError("template failed")

    monkeypatch.setitem(
        sys.modules,
        "docxtpl",
        type("DocxTplModule", (), {"DocxTemplate": BrokenDocxTemplate}),
    )

    with pytest.raises(TemplateRenderError, match="DOCX template.*template failed"):
        docx_renderer.render({}, "template.docx")


def test_latex_compilation_errors_are_latex_tool_errors():
    assert issubclass(LatexCompilationError, LatexToolError)
    assert issubclass(Jinja2SyntaxError, TemplateRenderError)


@pytest.mark.parametrize(
    "method, args, expected_error",
    [
        ("run_pdflatex", ("content",), LatexNotFoundError),
        ("run_latex_dvi", ("content",), LatexNotFoundError),
        ("run_gs_png", ("input.pdf",), GhostscriptNotFoundError),
        ("run_dvisvgm_svg", ("input.dvi",), DvisvgmNotFoundError),
    ],
)
def test_missing_latex_tools_raise_tool_specific_errors(
    monkeypatch, method, args, expected_error
):
    monkeypatch.setattr("quizml.markdown.latextools.shutil.which", lambda _: None)

    with LatexRunner() as runner:
        with pytest.raises(expected_error):
            getattr(runner, method)(*args)


@pytest.mark.parametrize(
    "method, args",
    [
        ("run_pdflatex", ("content",)),
        ("run_latex_dvi", ("content",)),
    ],
)
def test_latex_tool_launch_permission_errors_are_typed(monkeypatch, method, args):
    monkeypatch.setattr("quizml.markdown.latextools.shutil.which", lambda _: "/tool")
    monkeypatch.setattr(
        "quizml.markdown.latextools.subprocess.Popen",
        MagicMock(side_effect=PermissionError("permission denied")),
    )

    with LatexRunner() as runner:
        with pytest.raises(LatexToolError, match="Could not start"):
            getattr(runner, method)(*args)


@pytest.mark.parametrize(
    "method, args",
    [
        ("run_pdflatex", ("content",)),
        ("run_latex_dvi", ("content",)),
    ],
)
def test_latex_tool_nonzero_exit_is_reported(monkeypatch, method, args):
    monkeypatch.setattr("quizml.markdown.latextools.shutil.which", lambda _: "/tool")
    process = MagicMock(
        returncode=1, communicate=lambda: ("routine output\n! tool failed", "")
    )
    monkeypatch.setattr(
        "quizml.markdown.latextools.subprocess.Popen", lambda *_, **__: process
    )

    with LatexRunner() as runner:
        with pytest.raises(LatexCompilationError, match="! tool failed"):
            getattr(runner, method)(*args)


def test_pdflatex_invalid_depth_output_is_reported(monkeypatch):
    monkeypatch.setattr("quizml.markdown.latextools.shutil.which", lambda _: "/tool")
    process = MagicMock(returncode=0, communicate=lambda: ("::: not-a-number", ""))
    monkeypatch.setattr(
        "quizml.markdown.latextools.subprocess.Popen", lambda *_, **__: process
    )

    with LatexRunner() as runner:
        with pytest.raises(LatexCompilationError, match="invalid equation depth data"):
            runner.run_pdflatex("content")
