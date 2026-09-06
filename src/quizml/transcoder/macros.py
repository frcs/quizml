"""LaTeX macro expansion module for QuizML.

Parses custom LaTeX preambles containing \\newcommand, \\renewcommand,
\\providecommand, \\DeclareMathOperator, and \\def, expanding them recursively
into standard LaTeX for engines like latex2mathml.
"""

import re


def extract_braced(text: str, pos: int) -> tuple[str | None, int]:
    """Finds matching {...} starting from pos, handling nested braces."""
    while pos < len(text) and text[pos].isspace():
        pos += 1
    if pos >= len(text) or text[pos] != "{":
        return None, pos
    depth = 0
    start = pos + 1
    for i in range(pos, len(text)):
        if text[i] == "{" and (i == 0 or text[i - 1] != "\\"):
            depth += 1
        elif text[i] == "}" and (i == 0 or text[i - 1] != "\\"):
            depth -= 1
            if depth == 0:
                return text[start:i], i + 1
    return None, pos


class LatexMacroExpander:
    """Lightweight in-memory expander for LaTeX math macros."""

    def __init__(self, preamble: str = ""):
        self.macros: dict[str, tuple[int, str]] = {}
        if preamble:
            self.parse_preamble(preamble)

    def parse_preamble(self, preamble: str):
        """Extracts macro definitions from a LaTeX preamble string."""
        # Strip comments
        lines = [re.sub(r"(?<!\\)%.*$", "", l) for l in preamble.splitlines()]
        text = "\n".join(lines)
        pos = 0
        while pos < len(text):
            m_cmd = re.search(
                r"\\(?:re|provide)?newcommand\*?\s*\{?\\([a-zA-Z]+)\}?", text[pos:]
            )
            m_op = re.search(
                r"\\DeclareMathOperator(\*?)\s*\{?\\([a-zA-Z]+)\}?", text[pos:]
            )
            m_def = re.search(r"\\def\s*\\([a-zA-Z]+)", text[pos:])

            candidates = []
            if m_cmd:
                candidates.append((m_cmd.start(), "cmd", m_cmd))
            if m_op:
                candidates.append((m_op.start(), "op", m_op))
            if m_def:
                candidates.append((m_def.start(), "def", m_def))

            if not candidates:
                break

            candidates.sort(key=lambda x: x[0])
            rel_start, kind, match = candidates[0]
            curr_pos = pos + rel_start + len(match.group(0))

            if kind in ("cmd", "def"):
                name = match.group(1)
                m_args = (
                    re.match(r"\s*\[(\d+)\]", text[curr_pos:])
                    if kind == "cmd"
                    else None
                )
                nargs = int(m_args.group(1)) if m_args else 0
                curr_pos += len(m_args.group(0)) if m_args else 0
                body, next_pos = extract_braced(text, curr_pos)
                if body is not None:
                    self.macros[name] = (nargs, body)
                    pos = next_pos
                else:
                    pos = curr_pos + 1
            elif kind == "op":
                star, name = match.group(1), match.group(2)
                body, next_pos = extract_braced(text, curr_pos)
                if body is not None:
                    op_tag = r"\operatorname*" if star else r"\operatorname"
                    self.macros[name] = (0, f"{op_tag}{{{body}}}")
                    pos = next_pos
                else:
                    pos = curr_pos + 1

    def expand(self, expr: str, max_depth: int = 20) -> str:
        """Recursively expands macros within a LaTeX expression."""
        cur = expr
        for _ in range(max_depth):
            changed = False
            for name, (nargs, body) in self.macros.items():
                pattern = re.compile(r"\\" + name + r"(?![a-zA-Z])")
                pos = 0
                new_parts = []
                while True:
                    m = pattern.search(cur, pos)
                    if not m:
                        new_parts.append(cur[pos:])
                        break
                    new_parts.append(cur[pos : m.start()])
                    after_pos = m.end()

                    if nargs == 0:
                        new_parts.append(body)
                        pos = after_pos
                        changed = True
                    else:
                        args, arg_pos, valid = [], after_pos, True
                        for _ in range(nargs):
                            arg_val, arg_pos = extract_braced(cur, arg_pos)
                            if arg_val is None:
                                valid = False
                                break
                            args.append(arg_val)
                        if valid:
                            sub_body = body
                            for idx, val in enumerate(args, 1):
                                sub_body = sub_body.replace(f"#{idx}", val)
                            new_parts.append(sub_body)
                            pos = arg_pos
                            changed = True
                        else:
                            new_parts.append(m.group(0))
                            pos = after_pos
                cur = "".join(new_parts)
            if not changed:
                break
        return cur


def preprocess_latex_for_mathml(latex_str: str) -> str:
    """Normalizes LaTeX expressions for compatibility with latex2mathml.

    Handles:
    1. Splitting math ($...$) embedded inside \\text{...}.
    2. Mapping alignment environments (alignat, align, flalign, gather, multline, split)
       into \\begin{matrix}...\\end{matrix} which latex2mathml converts to <mtable>.
    3. Cleaning redundant or trailing ampersands (&) inside matrix rows.
    """
    if not latex_str:
        return ""

    # 1. Expand/split nested math inside \text{...} using extract_braced to handle nested braces like \mathbf{A}
    pos = 0
    while True:
        m = re.search(r"\\text\s*\{", latex_str[pos:])
        if not m:
            break
        text_start = pos + m.start()
        brace_pos = text_start + len(m.group(0)) - 1
        body, next_pos = extract_braced(latex_str, brace_pos)
        if body is None:
            pos = brace_pos + 1
            continue

        if "$" in body:
            parts = re.split(r"\$([^\$]+)\$", body)
            out = []
            for i, p in enumerate(parts):
                if i % 2 == 0:
                    if p:
                        out.append(rf"\text{{{p}}}")
                else:
                    if p:
                        out.append(f" {p} ")
            replacement = "".join(out)
            latex_str = latex_str[:text_start] + replacement + latex_str[next_pos:]
            pos = text_start + len(replacement)
        else:
            pos = next_pos

    # 2. Convert align, alignat, flalign, gather, multline, split environments to matrix
    latex_str = re.sub(r"\\begin\{(?:alignat\*?)\}\s*\{[^}]*\}", r"\\begin{matrix}", latex_str)
    latex_str = re.sub(r"\\begin\{(?:align\*?|flalign\*?|gather\*?|multline\*?|split\*?)\}", r"\\begin{matrix}", latex_str)
    latex_str = re.sub(r"\\end\{(?:alignat\*?|align\*?|flalign\*?|gather\*?|multline\*?|split\*?)\}", r"\\end{matrix}", latex_str)

    # 3. If matrix environment is present, clean alignment ampersands
    if r"\begin{matrix}" in latex_str:
        # Collapse multiple & to single &
        latex_str = re.sub(r"&+", "&", latex_str)
        # Strip leading & at start of row (after \begin{matrix} or after \\)
        latex_str = re.sub(r"(\\begin\{matrix\}\s*|\\\\\s*)&", r"\1", latex_str)
        # Strip trailing & before \\ or \end{matrix}
        latex_str = re.sub(r"&\s*(\\\\|\\end\{matrix\})", r"\1", latex_str)

    return latex_str
