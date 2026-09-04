import logging
import os
import pathlib
from graphlib import CycleError, TopologicalSorter
from string import Template

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

import quizml.cli.filelocator as filelocator
from quizml.exceptions import QuizMLConfigError


def get_config(args):
    """
    returns the yaml data of the config file
    """

    if args.config:
        config_file = os.path.realpath(os.path.expanduser(args.config))
    else:
        try:
            config_file = filelocator.locate.path("quizml.cfg")
        except FileNotFoundError as err:
            raise QuizMLConfigError("Could not find config file quizml.cfg") from err

    logging.info(f"using config file:{config_file}")

    try:
        with open(config_file, encoding="utf-8") as f:
            yaml = YAML(typ='safe')
            config = yaml.load(f)
    except YAMLError as err:
        s = f"Something went wrong while parsing the config file at:\n {config_file}\n\n {str(err)}"
        raise QuizMLConfigError(s) from err

    config["yaml_filename"] = args.yaml_filename

    return config


def get_required_target_names_set(name, targets):
    """resolves the set of the names of the required targets"""
    if not name:
        return set()

    if isinstance(name, list):
        pending = list(name)
    else:
        pending = [name]

    dep_map = {}
    for target in targets:
        t_name = target.get("name", "")
        if t_name and "dep" in target:
            deps = target["dep"]
            dep_map[t_name] = deps if isinstance(deps, list) else [deps]

    required_set = set(pending)
    visited = set()

    while pending:
        curr = pending.pop()
        if curr in visited:
            continue
        visited.add(curr)
        for dep in dep_map.get(curr, []):
            required_set.add(dep)
            pending.append(dep)

    return required_set


def sort_targets_topologically(targets, required_names=None):
    """
    Sorts target configs topologically according to their 'dep' attribute.
    Guarantees dependencies are compiled before dependents.
    """
    target_by_name = {}
    for t in targets:
        name = t.get("name")
        if name:
            if required_names is None or name in required_names:
                target_by_name[name] = t

    graph = {}
    for name, t in target_by_name.items():
        dep = t.get("dep")
        if not dep:
            graph[name] = set()
        elif isinstance(dep, list):
            graph[name] = {d for d in dep if d in target_by_name}
        else:
            graph[name] = {dep} if dep in target_by_name else set()

    try:
        ts = TopologicalSorter(graph)
        sorted_names = list(ts.static_order())
    except CycleError as err:
        raise QuizMLConfigError(f"Circular dependency detected among targets: {err}") from err

    ordered = [target_by_name[n] for n in sorted_names if n in target_by_name]

    # Preserve any anonymous targets without a name
    for t in targets:
        if "name" not in t and required_names is None:
            ordered.append(t)

    return ordered


def get_target_list(args, config, yaml_data):
    """
    gets the list of target templates from config['targets'] and
      * resolves dependencies topologically
      * resolves the absolute path of each template
      * also resolves $inputbasename
    """

    (basename, _) = os.path.splitext(config["yaml_filename"])

    subs = {"inputbasename": basename}
    filenames_to_resolve = ["template", "html_css", "html_pre", "latex_pre"]
    files_to_read_now = ["html_css", "html_pre", "latex_pre"]

    # if CLI provided specific list of required target names
    # we compile a list of all the required target names
    target_names = args.target
    if not target_names:
        target_names = config.get("default_targets")

    required_target_names_set = get_required_target_names_set(
        target_names, config["targets"]
    )

    if target_names:
        logging.info(f"requested target list:{target_names}")
        logging.info(f"required target list:{required_target_names_set}")

    ordered_targets = sort_targets_topologically(
        config["targets"], required_target_names_set if required_target_names_set else None
    )

    target_list = []

    for t in ordered_targets:
        target = {}

        # resolves $inputbasename
        for key, val in t.items():
            target[key] = Template(val).substitute(subs)

        # resolves relative path for all files
        for key in filenames_to_resolve:
            if key in target:
                target[key] = filelocator.locate.path(t[key])
                logging.info(f"'{target['descr']}:{key}' expands as '{target[key]}'")

        # replaces values with actual file content for some keys
        for key in files_to_read_now:
            if key in target:
                file_path = target[key]
                contents = pathlib.Path(file_path).read_text(encoding="utf-8")
                target[key] = contents

        # add target to list
        target_list.append(target)

        # add preamble key if defined in the QuizMLYaml header
        if "fmt" in target:
            target["user_pre"] = yaml_data["header"].get("_latexpreamble", "")

    return target_list
