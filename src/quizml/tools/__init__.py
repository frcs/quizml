"""QuizML Companion Tools module.

Provides pure-functional utilities for formatting/renumbering QuizML documents,
cleaning up build artifacts, and detecting duplicate questions across exams.
"""

from quizml.tools.cleanup import cleanup_build, find_cleanup_files
from quizml.tools.diff import compare_quiz_files, questions_are_similar
from quizml.tools.format import format_file, format_yaml_string

__all__ = [
    "format_file",
    "format_yaml_string",
    "cleanup_build",
    "find_cleanup_files",
    "compare_quiz_files",
    "questions_are_similar",
]
