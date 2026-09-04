"""QuizML target configuration loading and target resolution."""

import logging
import os
import pathlib
from string import Template

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from quizml.builder.dag import (
    get_required_target_names_set,
    sort_targets_topologically,
)
from quizml.exceptions import QuizMLConfigError
from quizml.filelocator import locate


def load_config(config_file: str | None = None, yaml_filename: str | None = None) -> dict:
    """Loads and parses the quizml.cfg YAML configuration."""
    if config_file:
        config_path = os.path.realpath(os.path.expanduser(config_file))
    else:
        try:
            config_path = locate.path("quizml.cfg")
        except FileNotFoundError as err:
            raise QuizMLConfigError("Could not find config file quizml.cfg") from err

    logging.info(f"using config file: {config_path}")

    try:
        with open(config_path, encoding="utf-8") as f:
            yaml = YAML(typ="safe")
            config = yaml.load(f)
    except YAMLError as err:
        s = f"Something went wrong while parsing the config file at:\n {config_path}\n\n {str(err)}"
        raise QuizMLConfigError(s) from err

    if yaml_filename:
        config["yaml_filename"] = yaml_filename

    return config


def resolve_targets(
    config: dict,
    yaml_data: dict,
    requested_targets: list[str] | str | None = None,
    yaml_filename: str | None = None,
) -> list[dict]:
    """Resolves target dictionaries from configuration:

    - Resolves dependencies topologically
    - Substitutes $inputbasename
    - Resolves absolute paths for templates and preambles
    - Reads content for preambles
    - Attaches _latexpreamble from document header
    """
    input_file = yaml_filename or config.get("yaml_filename", "quiz.yaml")
    basename, _ = os.path.splitext(input_file)

    subs = {"inputbasename": basename}
    filenames_to_resolve = ["template", "html_css", "html_pre", "latex_pre"]
    files_to_read_now = ["html_css", "html_pre", "latex_pre"]

    if isinstance(requested_targets, str):
        target_names = [requested_targets]
    elif requested_targets is not None:
        target_names = list(requested_targets)
    else:
        target_names = config.get("default_targets")

    required_target_names_set = get_required_target_names_set(
        target_names, config.get("targets", [])
    )

    if target_names:
        logging.info(f"requested target list: {target_names}")
        logging.info(f"required target list: {required_target_names_set}")

    ordered_targets = sort_targets_topologically(
        config.get("targets", []),
        required_target_names_set if required_target_names_set else None,
    )

    target_list = []
    for t in ordered_targets:
        target = {}

        for key, val in t.items():
            if isinstance(val, str):
                target[key] = Template(val).substitute(subs)
            else:
                target[key] = val

        for key in filenames_to_resolve:
            if key in target:
                target[key] = locate.path(target[key])
                logging.info(f"'{target.get('descr', '')}:{key}' expands as '{target[key]}'")

        for key in files_to_read_now:
            if key in target:
                file_path = target[key]
                target[key] = pathlib.Path(file_path).read_text(encoding="utf-8")

        target_list.append(target)

        if "fmt" in target:
            target["user_pre"] = yaml_data.get("header", {}).get("_latexpreamble", "")

    return target_list
