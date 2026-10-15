import difflib
import io
import re
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import StreamMark
from ruamel.yaml.scalarstring import LiteralScalarString
from ruamel.yaml.tokens import CommentToken

from ..exceptions import QuizMLError
from ..loader import count_included_questions


def is_q_comment(token):
    """Checks if a comment token matches the <Q#> or <Q1>, <Q2> pattern."""
    if not isinstance(token, CommentToken):
        return False
    # Matches "# <Q12>" or list like "# <Q10>, <Q11>, <Q12>" with any whitespace
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
    """Recursively removes all <Q#> comments and blank lines from a ruamel.yaml data structure."""
    if hasattr(data, "ca"):
        # 1. Clean object-level comments (pre/post)
        if data.ca.comment:
            for c_idx in range(len(data.ca.comment)):
                if isinstance(data.ca.comment[c_idx], list):
                    data.ca.comment[c_idx] = [
                        t
                        for t in data.ca.comment[c_idx]
                        if not should_remove_comment(t)
                    ]

        # 2. Clean end comments
        if hasattr(data.ca, "end") and data.ca.end:
            data.ca.end = [t for t in data.ca.end if not should_remove_comment(t)]

        # 3. Clean item-level comments
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

    # Recursive step
    if isinstance(data, dict):
        for v in data.values():
            clean_all_q_comments(v)
    elif isinstance(data, list):
        for item in data:
            clean_all_q_comments(item)


def wrap_text_fields(data, wrap_width=None):
    from .wrap import wrap_markdown

    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, str):
                # Always format choices values or long strings as Literal Blocks
                is_choice = k in ("x", "o", "A", "B") and len(v.strip()) > 0
                if "\n" in v or len(v) > 60 or is_choice:
                    # Skip header keys starting with _
                    if k.startswith("_"):
                        data[k] = LiteralScalarString(v.strip() + "\n")
                        continue
                    if wrap_width is not None:
                        val = wrap_markdown(v.strip(), width=wrap_width)
                    else:
                        val = v.strip()
                    if val:
                        data[k] = LiteralScalarString(val + "\n")
            elif isinstance(v, (dict, list)):
                wrap_text_fields(v, wrap_width=wrap_width)
    elif isinstance(data, list):
        for item in data:
            wrap_text_fields(item, wrap_width=wrap_width)


def format_yaml_text(txt, *, base_dir=Path("."), filename="<stdin>", wrap_width=None):
    yaml = YAML()
    yaml.indent(mapping=2, sequence=2, offset=0)
    yaml.width = 80
    yaml.preserve_quotes = True

    try:
        docs = list(yaml.load_all(txt))
    except Exception as err:
        raise QuizMLError(f"YAML parsing error in {filename}: {err}") from err

    formatted_parts = []
    dummy_mark = StreamMark(None, 0, 0, 0)

    for data in docs:
        if data is None or (isinstance(data, str) and not data.strip()):
            continue

        # Aggressive cleaning and text wrapping (if requested)
        clean_all_q_comments(data)
        wrap_text_fields(data, wrap_width=wrap_width)

        # Renumber questions if this part is a list
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

                    # Append so it stays right before the hyphen line
                    data.ca.items[q_idx][1].append(
                        CommentToken(new_comment, dummy_mark, None, 0)
                    )

        buf = io.StringIO()
        yaml.dump(data, buf)
        formatted_parts.append(buf.getvalue().strip())

    # Re-join documents
    actual_docs = [part for part in formatted_parts if part.strip()]
    res = ""
    if txt.startswith("---"):
        res += "---\n"
    res += "---\n".join(doc + "\n" for doc in actual_docs)

    # Convert to "- # <Q#>" convention
    res = re.sub(
        r"^[ ]*(# <Q[0-9]+>(?:, <Q[0-9]+>)*)\n- ",
        r"- \1\n  ",
        res,
        flags=re.MULTILINE,
    )

    return res


def run_format(args):
    import sys

    from .errorhandler import err_console

    source_name = args.file
    if source_name == "-":
        original = sys.stdin.read()
        base_dir = Path.cwd()
        filename = "<stdin>"
    else:
        path = Path(source_name)
        if not path.is_file():
            raise QuizMLError(f"File not found: {path}")
        original = path.read_text(encoding="utf-8")
        base_dir = path.parent
        filename = str(path)

    formatted = format_yaml_text(
        original,
        base_dir=base_dir,
        filename=filename,
        wrap_width=args.wrap,
    )
    changed = formatted != original

    if args.check:
        return not changed
    if args.diff:
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            formatted.splitlines(keepends=True),
            fromfile=filename,
            tofile=f"{filename} (formatted)",
        )
        sys.stdout.writelines(diff)
        return True
    if args.in_place:
        if source_name == "-":
            raise QuizMLError("--in-place requires a file path")
        if changed:
            Path(source_name).write_text(formatted, encoding="utf-8")
            err_console.print(f"Formatted and renumbered {source_name}")
        else:
            err_console.print(f"No changes needed in {source_name}")
        return True

    sys.stdout.write(formatted)
    return True
