"""Pure quiz metadata pinning, deterministic question ID generation, and include freezing."""

import hashlib
import importlib.metadata
import io
import os
import re
from pathlib import Path

from ruamel.yaml.comments import CommentedMap

from quizml.yaml.format import format_yaml_text
from quizml.yaml.includes import expand_roundtrip_includes
from quizml.yaml.parser import extract_figure_paths, parse_roundtrip_yaml_text


def parse_version_tuple(version_str):
    base = re.split(r"(?:\.dev|\+|a|b|rc|-)", str(version_str).strip(), maxsplit=1)[0]
    parts = [int(p) for p in re.findall(r"\d+", base)]
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3]), len(re.findall(r"\d+", base))


def default_version_constraint():
    try:
        ver_str = importlib.metadata.version("quizml")
    except importlib.metadata.PackageNotFoundError:
        return ">=0.1"
    (major, minor, _patch), _ = parse_version_tuple(ver_str)
    if major == 0:
        return f">={major}.{minor},<{major}.{minor + 1}"
    return f">={major}.{minor},<{major + 1}.0"


def generate_question_id(question_map, index, used_ids):
    source_text = str(
        question_map.get("title") or question_map.get("question") or ""
    ).strip()
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


def pin_yaml_text(
    raw_text: str,
    *,
    base_dir: Path = Path("."),
    source_label: str = "<stdin>",
    out_dir: Path | None = None,
    force: bool = False,
    default_targets=None,
    schema_path: str | None = None,
    freeze_includes: bool = False,
    seed=None,
    add_ids: bool = False,
    initial_stack: tuple[Path, ...] = (),
) -> str:
    """Stamp header metadata (_quizml, _targets, _schema), optionally freeze includes and generate question IDs."""
    yaml, docs, q_index = parse_roundtrip_yaml_text(raw_text, source_label)
    if len(docs) == 1:
        header = CommentedMap()
        docs = [header, docs[0]]
        q_index = 1
    else:
        header = docs[0]

    if force or "_quizml" not in header:
        header["_quizml"] = default_version_constraint()

    if default_targets and (force or "_targets" not in header):
        if isinstance(default_targets, str):
            header["_targets"] = [default_targets]
        else:
            header["_targets"] = list(default_targets)

    if (
        schema_path
        and schema_path != "schema.json"
        and (force or "_schema" not in header)
    ):
        header["_schema"] = str(schema_path)

    if freeze_includes:
        figure_dirs = list(extract_figure_paths(header, base_dir))
        docs[q_index] = expand_roundtrip_includes(
            docs[q_index],
            base_dir,
            inherited_seed=seed,
            stack=initial_stack,
            figure_dirs=figure_dirs,
        )
        if figure_dirs:
            target_out_dir = out_dir or base_dir
            header["_figures_path"] = list(
                dict.fromkeys(os.path.relpath(p, target_out_dir) for p in figure_dirs)
            )

    if add_ids:
        used_ids = {
            str(q["id"]).strip()
            for q in docs[q_index]
            if isinstance(q, dict) and q.get("id")
        }
        for idx, q in enumerate(docs[q_index], start=1):
            if not isinstance(q, dict) or "_include" in q:
                continue
            if not q.get("id"):
                new_id = generate_question_id(q, idx, used_ids)
                if hasattr(q, "insert"):
                    q.insert(0, "id", new_id)
                else:
                    q["id"] = new_id

    buf = io.StringIO()
    yaml.dump_all(docs, buf)
    return format_yaml_text(buf.getvalue(), base_dir=base_dir, filename=source_label)
