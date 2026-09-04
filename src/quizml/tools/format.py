"""QuizML document formatting and question renumbering."""

import io
import re
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import StreamMark
from ruamel.yaml.scalarstring import LiteralScalarString
from ruamel.yaml.tokens import CommentToken

from quizml.exceptions import QuizMLError
from quizml.quizmlyaml.includes import count_included_questions
from quizml.tools.wrap import wrap_markdown


def is_q_comment(token):
    """Checks if a comment token matches the <Q#> or <Q1>, <Q2> pattern."""
    if not isinstance(token, CommentToken):
        return False
    val = token.value.strip()
    return bool(re.match(r"^#[ \t]*<Q[0-9]+>(?:[ \t]*,[ \t]*<Q[0-9]+>)*$", val))


def is_blank_comment(token):
    """Checks if a comment token is just an empty line."""
    if not isinstance(token, CommentToken):
        return False
    return token.value.strip() == ""


def should_remove_comment(token):
    return is_q_comment(token) or is_blank_comment(token)


def clean_all_q_comments(data):
    """Recursively removes all <Q#> comments and blank lines from ruamel data."""
    if hasattr(data, "ca"):
        if data.ca.comment:
            for c_idx in range(len(data.ca.comment)):
                if isinstance(data.ca.comment[c_idx], list):
                    data.ca.comment[c_idx] = [
                        t
                        for t in data.ca.comment[c_idx]
                        if not should_remove_comment(t)
                    ]

        if hasattr(data.ca, "end") and data.ca.end:
            data.ca.end = [t for t in data.ca.end if not should_remove_comment(t)]

        if data.ca.items:
            for k in data.ca.items:
                comm_list_list = data.ca.items[k]
                if comm_list_list:
                    for c_idx in range(len(comm_list_list)):
                        if isinstance(comm_list_list[c_idx], list):
                            comm_list_list[c_idx] = [
                                t
                                for t in comm_list_list[c_idx]
                                if not should_remove_comment(t)
                            ]
                        elif should_remove_comment(comm_list_list[c_idx]):
                            comm_list_list[c_idx] = None

    if isinstance(data, dict):
        for v in data.values():
            clean_all_q_comments(v)
    elif isinstance(data, list):
        for item in data:
            clean_all_q_comments(item)


def wrap_text_fields(data):
    """Wraps text in markdown fields and choices to 74 columns."""
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, str):
                is_choice = k in ("x", "o", "A", "B") and len(v.strip()) > 0
                if "\n" in v or len(v) > 60 or is_choice:
                    if k.startswith("_"):
                        data[k] = LiteralScalarString(v.strip() + "\n")
                        continue
                    val = wrap_markdown(v.strip(), width=74)
                    if val:
                        data[k] = LiteralScalarString(val + "\n")
            elif isinstance(v, (dict, list)):
                wrap_text_fields(v)
    elif isinstance(data, list):
        for item in data:
            wrap_text_fields(item)


def format_yaml_string(yaml_text: str, base_dir: Path | str | None = None) -> str:
    """Formats QuizML YAML text:

    - Standardizes indentation (mapping=2, sequence=2, offset=0)
    - Wraps markdown text fields
    - Sequentially numbers question comments (# <Q1>, # <Q2>, ...)
    """
    if base_dir is None:
        base_dir = Path.cwd()
    else:
        base_dir = Path(base_dir).resolve()

    yaml = YAML()
    yaml.indent(mapping=2, sequence=2, offset=0)
    yaml.width = 80
    yaml.preserve_quotes = True

    try:
        docs = list(yaml.load_all(yaml_text))
    except Exception as err:
        raise QuizMLError(f"YAML parsing error: {err}") from err

    formatted_parts = []
    dummy_mark = StreamMark(None, 0, 0, 0)

    for data in docs:
        if data is None or (isinstance(data, str) and not data.strip()):
            continue

        clean_all_q_comments(data)
        wrap_text_fields(data)

        if isinstance(data, list):
            q_counter = 1
            for q_idx, item in enumerate(data):
                prefix = "\n" if q_idx > 0 else ""
                if isinstance(item, dict) and "_include" in item:
                    n_q = count_included_questions(item, base_dir=base_dir)
                    if n_q > 0:
                        q_tags = [f"<Q{q_counter + i}>" for i in range(n_q)]
                        new_comment = f"{prefix}# {', '.join(q_tags)}\n"
                        q_counter += n_q
                    else:
                        new_comment = None
                else:
                    new_comment = f"{prefix}# <Q{q_counter}>\n"
                    q_counter += 1

                if new_comment is not None:
                    if q_idx not in data.ca.items:
                        data.ca.items[q_idx] = [None, [], None, None]

                    if data.ca.items[q_idx][1] is None:
                        data.ca.items[q_idx][1] = []

                    data.ca.items[q_idx][1].append(
                        CommentToken(new_comment, dummy_mark, None, 0)
                    )

        buf = io.StringIO()
        yaml.dump(data, buf)
        formatted_parts.append(buf.getvalue().strip())

    actual_docs = [part for part in formatted_parts if part.strip()]
    res = ""
    if yaml_text.startswith("---"):
        res += "---\n"
    res += "---\n".join(doc + "\n" for doc in actual_docs)

    res = re.sub(
        r"^[ ]*(# <Q[0-9]+>(?:, <Q[0-9]+>)*)\n- ",
        r"- \1\n  ",
        res,
        flags=re.MULTILINE,
    )
    return res


def format_file(filepath: Path | str, in_place: bool = True) -> tuple[bool, str]:
    """Formats a QuizML YAML file on disk.

    Returns (has_changed, formatted_content).
    """
    yaml_path = Path(filepath).resolve()
    if not yaml_path.exists():
        raise QuizMLError(f"File not found: {yaml_path}")

    txt = yaml_path.read_text(encoding="utf-8")
    res = format_yaml_string(txt, base_dir=yaml_path.parent)

    has_changed = res != txt
    if in_place and has_changed:
        yaml_path.write_text(res, encoding="utf-8")

    return has_changed, res
