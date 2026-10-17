import logging
import os
import pathlib
from graphlib import CycleError, TopologicalSorter
from string import Template

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from quizml.cli.filelocator import FileLocator
from quizml.exceptions import QuizMLConfigError


def _validate_targets_list(config):
    targets = config.get("targets")
    if not isinstance(targets, list) or not all(isinstance(t, dict) for t in targets):
        raise QuizMLConfigError(
            "Config file must define 'targets' as a list of target mappings."
        )
    return targets


def get_config(args):
    """
    returns the yaml data of the config file
    """
    yaml_filename = getattr(args, "yaml_filename", None)
    base_dir = (
        str(pathlib.Path(yaml_filename).expanduser().resolve().parent)
        if yaml_filename and yaml_filename != "-"
        else None
    )

    if getattr(args, "config", None):
        config_file = os.path.realpath(os.path.expanduser(args.config))
    else:
        try:
            config_file = FileLocator(base_dir=base_dir).path("quizml.cfg")
        except FileNotFoundError as err:
            raise QuizMLConfigError("Could not find config file quizml.cfg") from err

    logging.info(f"using config file:{config_file}")

    try:
        with open(config_file, encoding="utf-8") as f:
            yaml = YAML(typ="safe")
            config = yaml.load(f)
    except YAMLError as err:
        s = f"Something went wrong while parsing the config file at:\n {config_file}\n\n {str(err)}"
        raise QuizMLConfigError(s) from err
    except OSError as err:
        raise QuizMLConfigError(
            f"Could not read config file {config_file}: {err}"
        ) from err

    if not isinstance(config, dict):
        raise QuizMLConfigError(
            f"Config file {config_file} must contain a YAML mapping at its root."
        )

    _validate_targets_list(config)
    config["yaml_filename"] = yaml_filename

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


def expand_target_aliases(names, targets, aliases):
    """Expand selected aliases to configured target names."""
    if not names:
        return names
    if not isinstance(aliases, dict):
        raise QuizMLConfigError("The 'aliases' config setting must be a mapping.")

    target_names = {target.get("name") for target in targets if target.get("name")}
    collisions = target_names.intersection(aliases)
    if collisions:
        names = ", ".join(sorted(collisions))
        raise QuizMLConfigError(f"Target aliases conflict with target names: {names}.")
    expanded = []
    active = []

    def expand(name):
        if name in aliases:
            if name in active:
                cycle = " -> ".join([*active, name])
                raise QuizMLConfigError(f"Circular target alias detected: {cycle}")
            value = aliases[name]
            if isinstance(value, str):
                members = [value]
            elif isinstance(value, list) and all(
                isinstance(item, str) for item in value
            ):
                members = value
            else:
                raise QuizMLConfigError(
                    f"Target alias '{name}' must be a target name or a list of target names."
                )
            active.append(name)
            for member in members:
                expand(member)
            active.pop()
        elif name in target_names:
            expanded.append(name)
        else:
            raise QuizMLConfigError(f"Unknown target or target alias '{name}'.")

    for name in names if isinstance(names, list) else [names]:
        expand(name)
    return list(dict.fromkeys(expanded))


def sort_targets_topologically(targets, required_names=None):
    """
    Sorts target configs topologically according to their 'dep' attribute.
    Guarantees dependencies are compiled before dependents.
    """
    all_target_names = {t.get("name") for t in targets if t.get("name")}
    for target in targets:
        name = target.get("name", "<unnamed>")
        dep = target.get("dep")
        if not dep:
            continue
        dependencies = dep if isinstance(dep, list) else [dep]
        for dependency in dependencies:
            if dependency not in all_target_names:
                raise QuizMLConfigError(
                    f"Target '{name}' depends on unknown target '{dependency}'."
                )

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
        raise QuizMLConfigError(
            f"Circular dependency detected among targets: {err}"
        ) from err

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
    _validate_targets_list(config)

    if config["yaml_filename"] == "-":
        inputdir = str(pathlib.Path.cwd().resolve())
        inputstem = "stdin"
    else:
        input_path = pathlib.Path(config["yaml_filename"]).expanduser().resolve()
        inputstem = input_path.stem
        inputdir = str(input_path.parent)

    subs = {}
    header_data = (
        yaml_data.get("header", {}) if isinstance(yaml_data, dict) else {}
    )
    if isinstance(header_data, dict):
        for k, v in header_data.items():
            if isinstance(v, (str, int, float, bool)):
                subs[str(k)] = str(v)
    subs.update(
        {
            "inputbasename": inputstem,
            "inputstem": inputstem,
            "inputdir": inputdir,
        }
    )
    filenames_to_resolve = ["template", "html_css", "html_pre", "latex_pre"]
    files_to_read_now = ["html_css", "html_pre", "latex_pre"]
    locator = FileLocator(base_dir=inputdir)

    # if CLI provided specific list of required target names
    # we compile a list of all the required target names
    target_names = args.target
    if not target_names:
        target_names = config.get("default_targets")
    target_names = expand_target_aliases(
        target_names, config["targets"], config.get("aliases", {})
    )

    required_target_names_set = get_required_target_names_set(
        target_names, config["targets"]
    )

    if target_names:
        logging.info(f"requested target list:{target_names}")
        logging.info(f"required target list:{required_target_names_set}")

    ordered_targets = sort_targets_topologically(
        config["targets"],
        required_target_names_set if required_target_names_set else None,
    )

    target_list = []

    for t in ordered_targets:
        target = {}

        # resolves $inputbasename, $inputstem, $inputdir, and scalar header vars safely
        for key, val in t.items():
            if isinstance(val, str):
                target[key] = Template(val).safe_substitute(subs)
            elif isinstance(val, list):
                target[key] = [
                    Template(v).safe_substitute(subs) if isinstance(v, str) else v
                    for v in val
                ]
            else:
                target[key] = val

        target.setdefault("name", "<unnamed>")
        target.setdefault("descr", target["name"])
        target.setdefault("out", "")
        target.setdefault("descr_cmd", target["out"])

        markdown = t.get("markdown")
        if markdown is not None:
            if not isinstance(markdown, dict):
                raise QuizMLConfigError(
                    f"Target '{target['name']}' markdown setting must be a mapping."
                )
            unknown_settings = set(markdown) - {
                "format",
                "math",
                "html_postprocess",
                "png_dpi",
                "png_scale",
                "svg_scale",
                "svg_converter",
            }
            if unknown_settings:
                unknown = ", ".join(sorted(unknown_settings))
                raise QuizMLConfigError(
                    f"Unknown Markdown setting(s) for target '{target['name']}': {unknown}."
                )
            output_format = markdown.get("format", "html")
            math_backend = markdown.get("math", "png")
            postprocess = markdown.get("html_postprocess")
            valid_postprocess = (
                postprocess is None
                or postprocess == "blackboard_html"
                or callable(postprocess)
                or (isinstance(postprocess, str) and ":" in postprocess)
            )
            if not valid_postprocess:
                raise QuizMLConfigError(
                    f"Unknown HTML postprocessor '{postprocess}' in target '{target['name']}'."
                )
            if output_format == "latex":
                if postprocess is not None:
                    raise QuizMLConfigError(
                        "markdown.html_postprocess can only be used with markdown.format: html."
                    )
                target["fmt"] = "latex"
            elif output_format in ("markdown", "none"):
                if postprocess is not None:
                    raise QuizMLConfigError(
                        "markdown.html_postprocess can only be used with markdown.format: html."
                    )
                target["fmt"] = "markdown"
            elif output_format == "html":
                backend_fmt = {
                    "png": "html",
                    "svg": "html-svg",
                    "mathml": "html-mathml",
                    "passthrough": "html-passthrough",
                    "mathjax": "html-passthrough",
                    "katex": "html-passthrough",
                    "none": "html-passthrough",
                }.get(math_backend)
                if backend_fmt is None:
                    raise QuizMLConfigError(
                        f"Unknown Markdown math backend '{math_backend}' in target '{target['name']}'."
                    )
                target["fmt"] = backend_fmt
            else:
                raise QuizMLConfigError(
                    f"Unknown Markdown format '{output_format}' in target '{target['name']}'."
                )
            target["html_postprocess"] = postprocess
            for opt_key in ("png_dpi", "png_scale", "svg_scale", "svg_converter"):
                if opt_key in markdown:
                    target[opt_key] = markdown[opt_key]
        elif "fmt" in t:
            # Translate existing configuration values while users migrate.
            legacy_fmt = t["fmt"]
            if legacy_fmt not in ("latex", "html", "html-svg", "html-mathml"):
                raise QuizMLConfigError(f"Unknown legacy fmt value '{legacy_fmt}'.")
            target["fmt"] = legacy_fmt
            # Legacy HTML formats historically applied the Blackboard-oriented
            # transformations to every HTML target.
            target["html_postprocess"] = (
                "blackboard_html" if legacy_fmt.startswith("html") else None
            )

        merged_tools = {}
        global_tools = config.get("tools")
        if global_tools is not None:
            if not isinstance(global_tools, dict):
                raise QuizMLConfigError("Top-level 'tools' setting must be a mapping.")
            merged_tools.update(global_tools)
        target_tools = t.get("tools")
        if target_tools is not None:
            if not isinstance(target_tools, dict):
                raise QuizMLConfigError(
                    f"Target '{target['name']}' tools setting must be a mapping."
                )
            merged_tools.update(target_tools)
        if merged_tools:
            target["tools"] = merged_tools

        merged_context = {}
        for ctx_key in ("vars", "context"):
            global_ctx = config.get(ctx_key)
            if global_ctx is not None:
                if not isinstance(global_ctx, dict):
                    raise QuizMLConfigError(
                        f"Top-level '{ctx_key}' setting must be a mapping."
                    )
                merged_context.update(global_ctx)
        for ctx_key in ("vars", "context"):
            target_ctx = t.get(ctx_key)
            if target_ctx is not None:
                if not isinstance(target_ctx, dict):
                    raise QuizMLConfigError(
                        f"Target '{target['name']}' {ctx_key} setting must be a mapping."
                    )
                merged_context.update(target_ctx)
        if merged_context:
            target["context"] = merged_context

        merged_filters = {}
        global_filters = config.get("jinja_filters")
        if global_filters is not None:
            if not isinstance(global_filters, dict):
                raise QuizMLConfigError(
                    "Top-level 'jinja_filters' setting must be a mapping."
                )
            merged_filters.update(global_filters)
        target_filters = t.get("jinja_filters")
        if target_filters is not None:
            if not isinstance(target_filters, dict):
                raise QuizMLConfigError(
                    f"Target '{target['name']}' jinja_filters setting must be a mapping."
                )
            merged_filters.update(target_filters)
        if merged_filters:
            target["jinja_filters"] = merged_filters

        # resolves relative path for all files
        for key in filenames_to_resolve:
            if key in target:
                target[key] = locator.path(target[key])
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
