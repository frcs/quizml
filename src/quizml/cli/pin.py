import hashlib
import importlib.metadata
import io
import os
import re
import sys
from pathlib import Path
from types import SimpleNamespace

from ruamel.yaml.comments import CommentedMap

from ..exceptions import QuizMLConfigError, QuizMLError
from .config import _parse_version_tuple, get_config
from .errorhandler import err_console
from .format import format_yaml_text
from .sample import _expand, _figure_paths, _parse_yaml_text


def _default_version_constraint():
    try:
        ver_str = importlib.metadata.version("quizml")
    except importlib.metadata.PackageNotFoundError:
        return ">=0.1"
    (major, minor, _patch), _ = _parse_version_tuple(ver_str)
    if major == 0:
        return f">={major}.{minor},<{major}.{minor + 1}"
    return f">={major}.{minor},<{major + 1}.0"


def _generate_question_id(question_map, index, used_ids):
    source_text = str(
        question_map.get("title") or question_map.get("question") or ""
    ).strip()
    # Strip basic LaTeX commands and non-alphanumeric tokens for a readable slug
    cleaned = re.sub(r"\\[a-zA-Z]+", " ", source_text)
    words = re.findall(r"[a-z0-9]+", cleaned.lower())
    slug = "-".join(words[:3]) if words else f"q{index}"
    slug = slug[:28].strip("-") or f"q{index}"

    digest_input = f"{question_map.get('type', '')}:{question_map.get('question', '')}"
    short_hash = hashlib.sha1(digest_input.encode("utf-8")).hexdigest()[:4]
    candidate = f"{slug}-{short_hash}"
    suffix = 2
    while candidate in used_ids:
        candidate = f"{slug}-{short_hash}-{suffix}"
        suffix += 1
    used_ids.add(candidate)
    return candidate


def run_pin(args):
    source = args.file
    if source == "-":
        raw_text = sys.stdin.read()
        source_label = "<stdin>"
        base_dir = Path.cwd().resolve()
        yaml_for_cfg = None
    else:
        source_path = Path(source).expanduser()
        if not source_path.is_file():
            raise QuizMLConfigError(f"File not found: {source_path}")
        source_path = source_path.resolve()
        raw_text = source_path.read_text(encoding="utf-8")
        source_label = str(source_path)
        base_dir = source_path.parent
        yaml_for_cfg = str(source_path)

    output = getattr(args, "output", None)
    if output is None:
        output = "-" if source == "-" else str(source_path)

    if (
        output != "-"
        and source != "-"
        and Path(output).expanduser().resolve() != source_path
        and Path(output).expanduser().exists()
        and not getattr(args, "force", False)
    ):
        raise QuizMLConfigError(
            f"Refusing to overwrite existing file {output} (use --force)."
        )

    config = get_config(
        SimpleNamespace(
            config=getattr(args, "config", None),
            yaml_filename=yaml_for_cfg,
        )
    )

    yaml, docs, q_index = _parse_yaml_text(raw_text, source_label)
    if len(docs) == 1:
        header = CommentedMap()
        docs = [header, docs[0]]
        q_index = 1
    else:
        header = docs[0]

    force = getattr(args, "force", False)
    if force or "_quizml" not in header:
        header["_quizml"] = _default_version_constraint()

    cli_targets = getattr(args, "target", None)
    default_targets = cli_targets or config.get("default_targets")
    if default_targets and (force or "_targets" not in header):
        if isinstance(default_targets, str):
            header["_targets"] = [default_targets]
        else:
            header["_targets"] = list(default_targets)

    schema_path = config.get("schema_path")
    if (
        schema_path
        and schema_path != "schema.json"
        and (force or "_schema" not in header)
    ):
        header["_schema"] = str(schema_path)

    if getattr(args, "freeze_includes", False):
        figure_dirs = list(_figure_paths(header, base_dir))
        docs[q_index] = _expand(
            docs[q_index],
            base_dir,
            inherited_seed=getattr(args, "seed", None),
            stack=(source_path,) if source != "-" else (),
            figure_dirs=figure_dirs,
        )
        if figure_dirs:
            out_dir = (
                base_dir
                if output == "-"
                else Path(output).expanduser().resolve().parent
            )
            header["_figures_path"] = list(
                dict.fromkeys(os.path.relpath(p, out_dir) for p in figure_dirs)
            )

    if getattr(args, "add_ids", False):
        used_ids = {
            str(q["id"]).strip()
            for q in docs[q_index]
            if isinstance(q, dict) and q.get("id")
        }
        for idx, q in enumerate(docs[q_index], start=1):
            if not isinstance(q, dict) or "_include" in q:
                continue
            if not q.get("id"):
                new_id = _generate_question_id(q, idx, used_ids)
                if hasattr(q, "insert"):
                    q.insert(0, "id", new_id)
                else:
                    q["id"] = new_id

    buf = io.StringIO()
    yaml.dump_all(docs, buf)
    formatted = format_yaml_text(
        buf.getvalue(), base_dir=base_dir, filename=source_label
    )

    if output == "-":
        sys.stdout.write(formatted)
    else:
        out_path = Path(output).expanduser()
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(formatted, encoding="utf-8")
        except OSError as err:
            raise QuizMLError(f"Could not write {out_path}: {err}") from err
        if not getattr(args, "quiet", False):
            err_console.print(f"Pinned metadata in {out_path}")
    return True
