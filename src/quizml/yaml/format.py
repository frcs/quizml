"""QuizML YAML formatting, <Q#> comment renumbering, and Markdown text wrapping."""

import io
import re
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import StreamMark, YAMLError
from ruamel.yaml.scalarstring import LiteralScalarString
from ruamel.yaml.tokens import CommentToken

from quizml.exceptions import QuizMLError
from quizml.yaml.includes import count_included_questions

_BLOCK_PATTERNS: tuple[str, ...] = (
    r"(?sm)^[ \t]*(?:`{3,}|~{3,}).*?^[ \t]*(?:`{3,}|~{3,})",
    r"(?sm)\$\$.*?\$\$",
    r"(?sm)\\\[.*?\\\]",
    r"(?sm)\\begin\{.*?\}.*?\\end\{.*?\}",
)

_INLINE_PATTERNS: tuple[str, ...] = (
    r"(?s)`+.*?`+",
    r"(?s)\$.*?\$",
    r"(?s)\\\(.*?\\\)",
    r"(?s)!?\[.*?\]\(.*?\)(?:\{[^{}]*\})?",
)


def _split_markdown_paragraphs(temp_text: str) -> list[str]:
    """Split text with ``__BLOCK_N__`` placeholders into logical paragraphs."""
    paragraphs: list[str] = []
    current_p: list[str] = []

    for line in temp_text.split("\n"):
        if re.match(r"^[ \t]*__BLOCK_\d+__[ \t]*$", line):
            if current_p:
                paragraphs.append("\n".join(current_p))
                current_p = []
            paragraphs.append(line)
        elif not line.strip():
            if current_p:
                paragraphs.append("\n".join(current_p))
                current_p = []
        elif re.match(r"^[ \t]*(?:[-*+]|\d+\.)[ \t]+", line):
            if current_p:
                paragraphs.append("\n".join(current_p))
                current_p = []
            current_p.append(line)
        else:
            current_p.append(line)

    if current_p:
        paragraphs.append("\n".join(current_p))
    return paragraphs


def _wrap_hard_break_segment(
    segment: str,
    width: int,
    subsequent_indent: str,
    inlines: dict[str, str],
) -> str:
    """Wrap words in one hard-break segment while measuring unmasked inline lengths."""
    words = re.split(r"[ \t\n]+", segment.strip())
    wrapped_lines: list[str] = []
    current_line: list[str] = []
    current_len = 0

    for w in words:
        if not w:
            continue

        # Measure the true visual length of the word after restoring inline tokens.
        real_w = w
        for k, v in inlines.items():
            real_w = real_w.replace(k, v)
        w_len = len(real_w)

        if not current_line:
            current_line.append(w)
            current_len = w_len
        elif current_len + 1 + w_len <= width:
            current_line.append(w)
            current_len += 1 + w_len
        elif re.match(r"^([-+*>#]|\d+[.)])$", w):
            # Never wrap a bare list/blockquote/heading marker onto the start
            # of a new line, as Markdown parsers would treat it as a new block.
            current_line.append(w)
            current_len += 1 + w_len
        else:
            wrapped_lines.append(" ".join(current_line))
            current_line = [w]
            current_len = len(subsequent_indent) + w_len

    if current_line:
        wrapped_lines.append(" ".join(current_line))

    for i in range(1, len(wrapped_lines)):
        wrapped_lines[i] = subsequent_indent + wrapped_lines[i]

    return "\n".join(wrapped_lines)


def wrap_markdown(text: str, width: int = 80) -> str:
    """Wrap Markdown paragraphs to ``width`` while preserving math, code, and tables."""
    blocks: dict[str, str] = {}
    inlines: dict[str, str] = {}
    block_counter = 0
    inline_counter = 0

    def repl_block(m: re.Match[str]) -> str:
        nonlocal block_counter
        key = f"__BLOCK_{block_counter}__"
        blocks[key] = m.group(0)
        block_counter += 1
        return key

    def repl_inline(m: re.Match[str]) -> str:
        nonlocal inline_counter
        key = f"__INLINE_{inline_counter}__"
        inlines[key] = m.group(0)
        inline_counter += 1
        return key

    # 1. Mask fenced code blocks and display math equations.
    temp_text = text
    for pat in _BLOCK_PATTERNS:
        temp_text = re.sub(pat, repl_block, temp_text)

    # 2. Split into logical paragraphs and wrap each non-block, non-table paragraph.
    wrapped_paragraphs: list[str] = []
    for p in _split_markdown_paragraphs(temp_text):
        if not p.strip():
            continue
        if re.match(r"^[ \t]*__BLOCK_\d+__[ \t]*$", p):
            wrapped_paragraphs.append(p)
            continue
        if "\n|" in p or p.lstrip().startswith("|"):
            wrapped_paragraphs.append(p)
            continue

        first_line = p.split("\n", maxsplit=1)[0]
        match_list = re.match(r"^([ \t]*(?:[-*+]|\d+\.)[ \t]+)", first_line)
        if match_list:
            subsequent_indent = " " * len(match_list.group(1))
        else:
            match_indent = re.match(r"^([ \t]+)", first_line)
            subsequent_indent = match_indent.group(1) if match_indent else ""

        p_temp = p
        for pat in _INLINE_PATTERNS:
            p_temp = re.sub(pat, repl_inline, p_temp)

        wrapped_segments = [
            _wrap_hard_break_segment(seg, width, subsequent_indent, inlines)
            for seg in p_temp.split("  \n")
        ]
        wrapped_paragraphs.append("  \n".join(wrapped_segments))

    # 3. Restore masked inline spans and block elements.
    final_text = "\n\n".join(wrapped_paragraphs)
    for k, v in inlines.items():
        final_text = final_text.replace(k, v)
    for k, v in blocks.items():
        final_text = final_text.replace(k, v)
    return final_text


def is_q_comment(token: Any) -> bool:
    """Return True if ``token`` is a ``# <Q#>`` or ``# <Q1>, <Q2>`` comment token."""
    if not isinstance(token, CommentToken):
        return False
    val = token.value.strip()
    return bool(re.match(r"^#[ \t]*<Q[0-9]+>(?:[ \t]*,[ \t]*<Q[0-9]+>)*$", val))


def is_blank_comment(token: Any) -> bool:
    """Return True if ``token`` is a comment token containing only whitespace."""
    if not isinstance(token, CommentToken):
        return False
    return token.value.strip() == ""


def clean_all_q_comments(data: Any, *, strip_blank_lines: bool = True) -> None:
    """Recursively remove ``<Q#>`` comments and optional blank lines from ``data``."""

    def _drop(token: Any) -> bool:
        if is_q_comment(token):
            return True
        return strip_blank_lines and is_blank_comment(token)

    if hasattr(data, "ca"):
        if data.ca.comment:
            for c_idx in range(len(data.ca.comment)):
                if isinstance(data.ca.comment[c_idx], list):
                    data.ca.comment[c_idx] = [
                        t for t in data.ca.comment[c_idx] if not _drop(t)
                    ]

        if hasattr(data.ca, "end") and data.ca.end:
            data.ca.end = [t for t in data.ca.end if not _drop(t)]

        if data.ca.items:
            for k in data.ca.items:
                comm_list_list = data.ca.items[k]
                if comm_list_list:
                    for c_idx in range(len(comm_list_list)):
                        if isinstance(comm_list_list[c_idx], list):
                            comm_list_list[c_idx] = [
                                t for t in comm_list_list[c_idx] if not _drop(t)
                            ]
                        elif _drop(comm_list_list[c_idx]):
                            comm_list_list[c_idx] = None

    if isinstance(data, dict):
        for v in data.values():
            clean_all_q_comments(v, strip_blank_lines=strip_blank_lines)
    elif isinstance(data, list):
        for item in data:
            clean_all_q_comments(item, strip_blank_lines=strip_blank_lines)


def wrap_text_fields(data: Any, wrap_width: int | None = None) -> None:
    """Convert multiline, long, or choice strings into YAML literal block scalars."""
    if isinstance(data, dict):
        for k, v in data.items():
            if k == "_include":
                continue
            if isinstance(v, str):
                is_choice = (
                    isinstance(k, str)
                    and k in ("x", "o", "A", "B")
                    and len(v.strip()) > 0
                )
                if "\n" in v or len(v) > 60 or is_choice:
                    if isinstance(k, str) and k.startswith("_"):
                        data[k] = LiteralScalarString(v.strip() + "\n")
                        continue
                    val = (
                        wrap_markdown(v.strip(), width=wrap_width)
                        if wrap_width is not None
                        else v.strip()
                    )
                    if val:
                        data[k] = LiteralScalarString(val + "\n")
            elif isinstance(v, (dict, list)):
                wrap_text_fields(v, wrap_width=wrap_width)
    elif isinstance(data, list):
        for item in data:
            wrap_text_fields(item, wrap_width=wrap_width)


def _inject_question_number_comments(data: list[Any], base_dir: Path) -> None:
    """Attach sequential ``# <Q#>`` pre-item comments to each question in ``data``."""
    dummy_mark = StreamMark(None, 0, 0, 0)
    q_counter = 1
    for q_idx, item in enumerate(data):
        prefix = "\n" if q_idx > 0 else ""
        if isinstance(item, dict) and "_include" in item:
            n_q = count_included_questions(item, base_dir=base_dir)
            if n_q > 0:
                q_tags = [f"<Q{q_counter + i}>" for i in range(n_q)]
                new_comment: str | None = f"{prefix}# {', '.join(q_tags)}\n"
                q_counter += n_q
            else:
                new_comment = None
        else:
            new_comment = f"{prefix}# <Q{q_counter}>\n"
            q_counter += 1

        if new_comment is not None:
            # In ruamel.yaml, data.ca.items[q_idx] is a 4-slot list:
            # [pre_key, pre_item, post_key, post_item].
            if q_idx not in data.ca.items:
                data.ca.items[q_idx] = [None, [], None, None]
            if data.ca.items[q_idx][1] is None:
                data.ca.items[q_idx][1] = []
            data.ca.items[q_idx][1].append(
                CommentToken(new_comment, dummy_mark, None, 0)
            )


def format_yaml_text(
    txt: str,
    *,
    base_dir: Path = Path("."),
    filename: str = "<stdin>",
    wrap_width: int | None = None,
) -> str:
    """Format QuizML YAML text with standard indentation, blocks, and ``<Q#>`` tags."""
    yaml = YAML()
    yaml.indent(mapping=2, sequence=2, offset=0)
    yaml.width = 4096
    yaml.preserve_quotes = True

    try:
        docs = list(yaml.load_all(txt))
    except YAMLError as err:
        raise QuizMLError(f"YAML parsing error in {filename}: {err}") from err

    formatted_parts: list[str] = []
    for data in docs:
        if data is None or (isinstance(data, str) and not data.strip()):
            continue

        clean_all_q_comments(data, strip_blank_lines=isinstance(data, list))
        wrap_text_fields(data, wrap_width=wrap_width)

        if isinstance(data, list):
            _inject_question_number_comments(data, base_dir=base_dir)

        buf = io.StringIO()
        yaml.dump(data, buf)
        formatted_parts.append(buf.getvalue().strip())

    actual_docs = [part for part in formatted_parts if part.strip()]
    res = "---\n" if txt.startswith("---") else ""
    res += "---\n".join(doc + "\n" for doc in actual_docs)

    # Move top-level question comments inline onto the sequence dash:
    #   # <Q1>
    #   - type: mc
    # becomes:
    #   - # <Q1>
    #     type: mc
    return re.sub(
        r"^(# <Q[0-9]+>(?:, <Q[0-9]+>)*)\n- ",
        r"- \1\n  ",
        res,
        flags=re.MULTILINE,
    )
