"""Configuration loading, version checks, variable interpolation, and target resolution."""

import importlib.metadata
import logging
import os
import pathlib
import re
import warnings
from string import Template

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from quizml.build.dag import (
    expand_target_aliases,
    get_required_target_names_set,
    sort_targets_topologically,
)
from quizml.exceptions import QuizMLConfigError
from quizml.markdown.options import normalize_markdown_options
from quizml.paths import FileLocator
from quizml.yaml.parser import peek_yaml_header
from quizml.yaml.pin import parse_version_tuple

_parse_version_tuple = parse_version_tuple


def check_quizml_version(specifier, source_label="config", *, warn_fn=None):
    """Validate current quizml version against a comma-separated constraint string."""
    if not specifier or not str(specifier).strip():
        return True
    try:
        current_str = importlib.metadata.version("quizml")
    except importlib.metadata.PackageNotFoundError:
        return True

    cur_tuple, _ = _parse_version_tuple(current_str)
    clauses = [c.strip() for c in str(specifier).split(",") if c.strip()]
    satisfied = True

    for clause in clauses:
        m = re.match(r"^(>=|<=|==|!=|~=| equals |>|<)?\s*(.+)$", clause)
        if not m:
            continue
        op = (m.group(1) or "==").strip()
        target_str = m.group(2).strip()
        req_tuple, n_parts = _parse_version_tuple(target_str)

        if op == ">=":
            ok = cur_tuple >= req_tuple
        elif op == "<=":
            ok = cur_tuple <= req_tuple
        elif op == ">":
            ok = cur_tuple > req_tuple
        elif op == "<":
            ok = cur_tuple < req_tuple
        elif op == "!=":
            ok = cur_tuple[:n_parts] != req_tuple[:n_parts]
        elif op == "~=":
            upper = (
                (req_tuple[0] + 1, 0, 0)
                if n_parts <= 2
                else (req_tuple[0], req_tuple[1] + 1, 0)
            )
            ok = req_tuple <= cur_tuple < upper
        else:
            ok = cur_tuple[: max(1, n_parts)] == req_tuple[: max(1, n_parts)]

        if not ok:
            satisfied = False
            break

    if not satisfied:
        if warn_fn is not None:
            warn_fn(
                f"[yellow]Warning:[/yellow] {source_label} expects quizml "
                f"'{specifier}', but running quizml {current_str}."
            )
        else:
            warnings.warn(
                f"{source_label} expects quizml '{specifier}', "
                f"but running quizml {current_str}.",
                UserWarning,
                stacklevel=2,
            )
    return satisfied


def _validate_targets_list(config):
    targets = config.get("targets")
    if not isinstance(targets, list) or not all(isinstance(t, dict) for t in targets):
        raise QuizMLConfigError(
            "Config file must define 'targets' as a list of target mappings."
        )
    return targets


def build_target_substitutions(yaml_filename=None, header_data=None):
    """Build substitution dictionary for `${inputdir}`, `${inputstem}`, `${inputbasename}`, and header scalars."""
    if not yaml_filename or yaml_filename == "-":
        inputdir = str(pathlib.Path.cwd().resolve())
        inputstem = "stdin"
    else:
        input_path = pathlib.Path(yaml_filename).expanduser().resolve()
        inputstem = input_path.stem
        inputdir = str(input_path.parent)

    subs = {}
    if isinstance(header_data, dict):
        for k, v in header_data.items():
            if isinstance(v, (str, int, float, bool)):
                subs[str(k)] = re.sub(r"[/\\]+", "_", str(v)).strip()
    subs.update(
        {
            "inputbasename": inputstem,
            "inputstem": inputstem,
            "inputdir": inputdir,
        }
    )
    return subs, inputdir, inputstem


def _load_bundled_default_config():
    """Load the package's bundled `templates/quizml.cfg` as a baseline dictionary."""
    pkg_cfg = (
        pathlib.Path(__file__).resolve().parent.parent / "templates" / "quizml.cfg"
    )
    if not pkg_cfg.is_file():
        return {}
    with pkg_cfg.open(encoding="utf-8") as f:
        data = YAML(typ="safe").load(f)
    return data if isinstance(data, dict) else {}


def _merge_with_bundled_defaults(config, config_file):
    """Inherit bundled targets, aliases, and defaults when omitted in a project config."""
    pkg_cfg = (
        pathlib.Path(__file__).resolve().parent.parent / "templates" / "quizml.cfg"
    )
    try:
        if os.path.realpath(config_file) == os.path.realpath(pkg_cfg):
            return config
    except OSError:
        pass

    defaults = _load_bundled_default_config()
    if not defaults:
        return config

    for key in ("schema_path", "stats_template"):
        if key not in config and key in defaults:
            config[key] = defaults[key]

    user_aliases = config.get("aliases")
    user_alias_names = (
        set(user_aliases.keys()) if isinstance(user_aliases, dict) else set()
    )

    default_targets = defaults.get("targets")
    if isinstance(default_targets, list):
        if "targets" not in config:
            config["targets"] = [
                dict(t) for t in default_targets if isinstance(t, dict)
            ]
        elif (
            isinstance(config.get("targets"), list)
            and config["targets"]
            and all(isinstance(t, dict) for t in config["targets"])
        ):
            by_name = {
                t["name"]: t
                for t in default_targets
                if isinstance(t, dict) and "name" in t
            }
            user_targets = config["targets"]
            if "default_targets" not in config:
                user_render_names = [
                    t["name"]
                    for t in user_targets
                    if t.get("name") and "build_cmd" not in t
                ]
                if user_render_names:
                    config["default_targets"] = user_render_names

            merged_targets = []
            seen_names = set()
            for t in user_targets:
                t_name = t.get("name")
                if t_name:
                    seen_names.add(t_name)
                if t_name in by_name:
                    merged_targets.append({**by_name[t_name], **t})
                else:
                    merged_targets.append(t)
            for dt in default_targets:
                if (
                    isinstance(dt, dict)
                    and dt.get("name") not in seen_names
                    and dt.get("name") not in user_alias_names
                ):
                    merged_targets.append(dict(dt))
            config["targets"] = merged_targets

    target_names = {
        t["name"]
        for t in config.get("targets", [])
        if isinstance(t, dict) and t.get("name")
    }

    default_aliases = defaults.get("aliases")
    if isinstance(default_aliases, dict):
        inherited_aliases = {
            k: v
            for k, v in default_aliases.items()
            if k in user_alias_names or k not in target_names
        }
        if user_aliases is None:
            config["aliases"] = inherited_aliases
        elif isinstance(user_aliases, dict):
            config["aliases"] = {**inherited_aliases, **user_aliases}

    return config


def load_config(config_path=None, *, yaml_filename=None, warn_fn=None):
    """Load and validate a `quizml.cfg` configuration file."""
    base_dir = (
        str(pathlib.Path(yaml_filename).expanduser().resolve().parent)
        if yaml_filename and yaml_filename != "-"
        else None
    )

    if config_path:
        config_file = os.path.realpath(os.path.expanduser(str(config_path)))
    else:
        header_peek = peek_yaml_header(yaml_filename)
        header_cfg = (
            header_peek.get("_config") if isinstance(header_peek, dict) else None
        )
        cfg_ref = (
            header_cfg.strip()
            if isinstance(header_cfg, str) and header_cfg.strip()
            else "quizml.cfg"
        )
        try:
            config_file = FileLocator(base_dir=base_dir).path(cfg_ref)
        except FileNotFoundError as err:
            raise QuizMLConfigError(f"Could not find config file {cfg_ref}") from err

    logging.info(f"using config file:{config_file}")

    try:
        with open(config_file, encoding="utf-8") as f:
            yaml = YAML(typ="safe")
            config = yaml.load(f)
    except YAMLError as err:
        s = f"Something went wrong while parsing the config file at:\n {config_file}\n\n {err!s}"
        raise QuizMLConfigError(s) from err
    except OSError as err:
        raise QuizMLConfigError(
            f"Could not read config file {config_file}: {err}"
        ) from err

    if not isinstance(config, dict):
        raise QuizMLConfigError(
            f"Config file {config_file} must contain a YAML mapping at its root."
        )

    config = _merge_with_bundled_defaults(config, config_file)
    _validate_targets_list(config)
    config["yaml_filename"] = yaml_filename
    config_dir = os.path.dirname(os.path.abspath(config_file))
    config["_config_dir"] = config_dir

    raw_texinputs = config.get("texinputs", [])
    if isinstance(raw_texinputs, (str, bytes)):
        raw_texinputs = [raw_texinputs]
    elif not isinstance(raw_texinputs, list):
        raw_texinputs = []

    resolved_texinputs = []
    for item in raw_texinputs:
        if item:
            item_str = str(item).strip()
            if item_str:
                if os.path.isabs(item_str):
                    resolved_texinputs.append(os.path.abspath(item_str))
                else:
                    resolved_texinputs.append(
                        os.path.abspath(os.path.join(config_dir, item_str))
                    )
    config["texinputs"] = resolved_texinputs

    if config.get("quizml_version"):
        check_quizml_version(config["quizml_version"], config_file, warn_fn=warn_fn)

    return config


def resolve_targets(config, yaml_data, *, target_names=None):
    """Resolve and topologically order target templates from `config['targets']`."""
    _validate_targets_list(config)

    header_data = yaml_data.get("header", {}) if isinstance(yaml_data, dict) else {}
    subs, inputdir, _ = build_target_substitutions(
        config.get("yaml_filename"), header_data
    )

    filenames_to_resolve = ["template", "html_css", "html_pre", "latex_pre"]
    files_to_read_now = ["html_css", "html_pre", "latex_pre"]
    locator = FileLocator(base_dir=inputdir, config_dir=config.get("_config_dir"))

    if not target_names:
        header_targets = (
            header_data.get("_targets") if isinstance(header_data, dict) else None
        )
        if header_targets:
            target_names = (
                [header_targets]
                if isinstance(header_targets, str)
                else list(header_targets)
            )
        else:
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

        if "markdown" in t or "fmt" in t:
            normalized = normalize_markdown_options(
                target, target_name=target["name"], config_error=True
            )
            target.update(normalized)

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

        for key in filenames_to_resolve:
            if key in target:
                target[key] = locator.path(target[key])
                logging.info(f"'{target['descr']}:{key}' expands as '{target[key]}'")

        for key in files_to_read_now:
            if key in target:
                file_path = target[key]
                try:
                    contents = pathlib.Path(file_path).read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError) as err:
                    raise QuizMLConfigError(
                        f"Could not read '{key}' file '{file_path}' for target '{target['name']}': {err}"
                    ) from err
                target[key] = contents

        target_list.append(target)

        if "fmt" in target:
            target["user_pre"] = yaml_data["header"].get("_latexpreamble", "")

    return target_list
