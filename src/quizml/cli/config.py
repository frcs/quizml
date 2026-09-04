"""CLI adapter for configuration loading and target list resolution."""

from quizml.builder.config import load_config, resolve_targets
from quizml.builder.dag import (
    get_required_target_names_set,
    sort_targets_topologically,
)


def get_config(args):
    """Returns the config dictionary from the config file, setting yaml_filename."""
    return load_config(
        config_file=getattr(args, "config", None),
        yaml_filename=getattr(args, "yaml_filename", None),
    )


def get_target_list(args, config, yaml_data):
    """Resolves target dictionaries from configuration according to CLI arguments."""
    requested = getattr(args, "target", None)
    yaml_file = getattr(args, "yaml_filename", None)
    return resolve_targets(
        config, yaml_data, requested_targets=requested, yaml_filename=yaml_file
    )


__all__ = [
    "get_config",
    "get_target_list",
    "get_required_target_names_set",
    "sort_targets_topologically",
]
