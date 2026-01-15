import re

from mistletoe.block_token import BlockToken
from mistletoe.span_token import SpanToken


class MathDisplay(BlockToken):
    pattern = re.compile(
        r"(\$\$|\\\[|\\begin\{(equation|split|alignat|multline|gather|align|flalign|)(\*?))"
    )

    envname = ""
    envstart = ""
    latex = ""
    repr_attributes = ["latex"]

    def __init__(self, lines):
        self.latex = "".join([line.lstrip() for line in lines]).strip()

    @classmethod
    def start(cls, line):
        match_obj = cls.pattern.match(line.strip())
        if not match_obj:
            return False
        cls.envname = match_obj.group(2)
        cls.envstar = match_obj.group(3)
        cls.envstart = match_obj.group(1)

        return True

    @classmethod
    def read(cls, lines):
        line_buffer = [next(lines)]
        for line in lines:
            line_buffer.append(line)
            stripped_line = line.lstrip()
            if cls.envstart == r"$$" and stripped_line.startswith(r"$$"):
                break
            elif cls.envstart == r"\[" and stripped_line.startswith(r"\]"):
                break
            elif cls.envname and stripped_line.startswith(
                r"\end{" + cls.envname + cls.envstar + "}"
            ):
                break

        return line_buffer

    @classmethod
    def check_interrupts_paragraph(cls, lines):
        return cls.start(lines.peek())

    @property
    def content(self):
        """Returns the code block content."""
        return self.latex


# no nesting
class Command(SpanToken):
    repr_attributes = ("cmdname", "cmd")
    parse_group = 2
    parse_inner = True
    pattern = re.compile(
        r"""
        \\([a-zA-Z]+?){\s*(.*?)\s*}""",
        re.MULTILINE | re.VERBOSE | re.DOTALL,
    )

    def __init__(self, match):
        self.cmdname = match.group(1)
        self.cmd = match.group(2)


# no nesting
class Environment(SpanToken):
    repr_attributes = ("envname", "cmd")
    parse_group = 2
    parse_inner = True
    pattern = re.compile(
        r"""
        \\begin{([a-zA-Z]+?)}{\s*(.*?)\s*}""",
        re.MULTILINE | re.VERBOSE | re.DOTALL,
    )

    def __init__(self, match):
        self.cmdname = match.group(1)
        self.cmd = match.group(2)


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
