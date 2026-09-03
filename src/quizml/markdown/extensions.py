import re

from mistletoe.block_token import BlockToken
from mistletoe.span_token import SpanToken


class MathDisplay(BlockToken):
    pattern = re.compile(
        r"(\$\$|\\\[|\\begin\{(equation|split|alignat|multline|gather|align|flalign|)(\*?)\})"
    )

    latex = ""
    repr_attributes = ["latex"]

    def __init__(self, lines):
        self.latex = "".join([line.lstrip() for line in lines]).strip()

    @classmethod
    def start(cls, line):
        return bool(cls.pattern.match(line.strip()))

    @classmethod
    def read(cls, lines):
        first_line = next(lines)
        stripped = first_line.strip()
        match_obj = cls.pattern.match(stripped)
        if not match_obj:
            return [first_line]

        envstart = match_obj.group(1)
        envname = match_obj.group(2)
        envstar = match_obj.group(3)

        if envstart == "$$":
            if "$$" in stripped[2:]:
                return [first_line]
            close_pattern = "$$"
        elif envstart == r"\[":
            if r"\]" in stripped[2:]:
                return [first_line]
            close_pattern = r"\]"
        elif envname:
            close_pattern = r"\end{" + envname + envstar + "}"
            if close_pattern in stripped[match_obj.end():]:
                return [first_line]
        else:
            return [first_line]

        line_buffer = [first_line]
        for line in lines:
            line_buffer.append(line)
            if close_pattern in line.lstrip():
                break
        return line_buffer

    @classmethod
    def check_interrupts_paragraph(cls, lines):
        return cls.start(lines.peek())

    @property
    def content(self):
        """Returns the code block content."""
        return self.latex


class ImageWithWidth(SpanToken):
    content = ""
    src = ""
    title = ""
    width = ""

    parse_group = 1
    parse_inner = False
    #    precedence = 6
    pattern = re.compile(
        r"""
        !\[([^\]]*)\]\(([^\)]*)\)\{\s*width\s*=([^\}]*)\}
        """,
        re.MULTILINE | re.VERBOSE | re.DOTALL,
    )

    def __init__(self, match):
        self.title = match.group(1)
        self.src = match.group(2)
        self.width = match.group(3)


class MathInline(SpanToken):
    content = ""
    parse_group = 1
    parse_inner = False
    #    precedence = 6
    pattern = re.compile(
        r"""
        (?<!\\)    # negative look-behind to make sure start is not escaped 
        (?:        # start non-capture group for all possible match starts
          # group 1, match dollar signs only 
          # single or double dollar sign enforced by look-arounds
          ((?<!\$)\${1}(?!\$))|
          # group 2, match escaped parenthesis
          (\\\()
        )
        # if group 1 was start
        (?(1)
          # non greedy match everything in between
          # group 1 matches do not support recursion
          (.*?)(?<!\\)
          # match ending double or single dollar signs
          (?<!\$)\1(?!\$)|  
        # else
        (?:
          # greedily and recursively match everything in between
          # groups 2, 3 and 4 support recursion
          (.*)(?<!\\)\\\)
        ))
        """,
        re.MULTILINE | re.VERBOSE | re.DOTALL,
    )

    def __init__(self, match):
        self.content = match.group(0)
