import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest
from jinja2 import TemplateError

from quizml import docx_renderer
from quizml.cli.compile import compile_cmd_target
from quizml.exceptions import (
    Jinja2SyntaxError,
    LatexCompilationError,
    LatexToolError,
    QuizMLBuildError,
    TemplateRenderError,
)
from quizml.markdown.latextools import LatexRunner, _communicate


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
        patch("quizml.cli.compile.subprocess.run", side_effect=failure),
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
