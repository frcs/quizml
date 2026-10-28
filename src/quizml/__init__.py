"""QuizML: modular toolkit for YAML/Markdown quizzes, transcoding, rendering, and builds."""

from quizml.build import BuildResult, TargetResult, compile_quiz
from quizml.markdown import (
    MarkdownOptions,
    MarkdownTranscoder,
    transcode,
    transcode_many,
    transcode_text,
)
from quizml.paths import FileLocator, find_path
from quizml.rendering import render, render_docx, render_qti, render_template
from quizml.yaml import (
    MarkdownString,
    QuizDocument,
    compare_quiz_files,
    format_yaml_text,
    grep_questions,
    load,
    loads,
    pin_yaml_text,
)

__all__ = [
    "BuildResult",
    "FileLocator",
    "MarkdownOptions",
    "MarkdownString",
    "MarkdownTranscoder",
    "QuizDocument",
    "TargetResult",
    "compare_quiz_files",
    "compile_quiz",
    "find_path",
    "format_yaml_text",
    "grep_questions",
    "load",
    "loads",
    "pin_yaml_text",
    "render",
    "render_docx",
    "render_qti",
    "render_template",
    "transcode",
    "transcode_many",
    "transcode_text",
]
