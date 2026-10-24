"""CLI adapter for configuration loading and target resolution."""

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
from quizml.yaml.parser import peek_yaml_header


def get_config(args):
    """Return the parsed config dictionary for CLI args."""
    return load_config(
        getattr(args, "config", None),
        yaml_filename=getattr(args, "yaml_filename", None),
    )


def get_target_list(args, config, yaml_data):
    """Resolve target templates for CLI args."""
    return resolve_targets(
        config,
        yaml_data,
        target_names=getattr(args, "target", None),
    )


__all__ = [
    "_parse_version_tuple",
    "_validate_targets_list",
    "build_target_substitutions",
    "check_quizml_version",
    "expand_target_aliases",
    "get_config",
    "get_required_target_names_set",
    "get_target_list",
    "load_config",
    "peek_yaml_header",
    "resolve_targets",
    "sort_targets_topologically",
]
