"""Headless build pipeline, target resolution, and DAG package for QuizML."""

from quizml.build.cleanup import find_quiz_files, get_cleanup_candidates
from quizml.build.compiler import (
    BuildResult,
    TargetResult,
    compile_cmd_target,
    compile_quiz,
    compile_target,
    resolve_output_path,
)
from quizml.build.config import (
    _parse_version_tuple,
    _validate_targets_list,
    build_target_substitutions,
    check_quizml_version,
    load_config,
    resolve_targets,
)
from quizml.build.dag import (
    expand_target_aliases,
    get_required_target_names_set,
    sort_targets_topologically,
)

__all__ = [
    "BuildResult",
    "TargetResult",
    "_parse_version_tuple",
    "_validate_targets_list",
    "build_target_substitutions",
    "check_quizml_version",
    "compile_cmd_target",
    "compile_quiz",
    "compile_target",
    "expand_target_aliases",
    "find_quiz_files",
    "get_cleanup_candidates",
    "get_required_target_names_set",
    "load_config",
    "resolve_output_path",
    "resolve_targets",
    "sort_targets_topologically",
]
