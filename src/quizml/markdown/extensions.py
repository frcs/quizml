"""Custom Mistletoe block and span tokens for QuizML math and sized images."""

import re
from collections.abc import Iterable
from typing import Any, ClassVar

from mistletoe.block_token import BlockToken
from mistletoe.span_token import SpanToken


class MathDisplay(BlockToken):
    """Mistletoe block token matching display LaTeX equations.

    Supports ``$$...$$``, ``\\[...\\]``, and standard AMS math environments
    (``equation``, ``split``, ``alignat``, ``multline``, ``gather``, ``align``,
    ``flalign``, with or without ``*``).
    """

    pattern = re.compile(
        r"(\$\$|\\\[|\\begin\{(equation|split|alignat|multline|gather|"
        r"align|flalign)(\*?)\})"
    )

    latex: str = ""
    repr_attributes: ClassVar[list[str]] = ["latex"]

    def __init__(self, lines: Iterable[str]) -> None:
        self.latex = "".join([line.lstrip() for line in lines]).strip()

    @classmethod
    def start(cls, line: str) -> bool:
        """Return True if ``line`` starts a display math block."""
        return bool(cls.pattern.match(line.strip()))

    @classmethod
    def read(cls, lines: Any) -> list[str]:
        """Consume lines from the block tokenizer until the closing math delimiter."""
        first_line: str = next(lines)
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
            if close_pattern in stripped[match_obj.end() :]:
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
    def check_interrupts_paragraph(cls, lines: Any) -> bool:
        """Allow display math blocks to interrupt an open Markdown paragraph."""
        return cls.start(lines.peek())

    @property
    def content(self) -> str:
        """Return the raw LaTeX block content."""
        return self.latex


class ImageWithWidth(SpanToken):
    """Mistletoe span token matching ``![alt](src){width=...}`` syntax."""

    content: str = ""
    src: str = ""
    title: str = ""
    width: str = ""

    parse_group: ClassVar[int] = 1
    parse_inner: ClassVar[bool] = False
    pattern = re.compile(
        r"""
        !\[([^\]]*)\]\(([^\)]*)\)\{\s*width\s*=([^\}]*)\}
        """,
        re.MULTILINE | re.VERBOSE | re.DOTALL,
    )

    def __init__(self, match: re.Match[str]) -> None:
        self.title = match.group(1)
        self.src = match.group(2)
        self.width = match.group(3)


class MathInline(SpanToken):
    """Mistletoe span token matching inline ``$...$`` or ``\\(...\\)`` LaTeX math."""

    content: str = ""
    parse_group: ClassVar[int] = 1
    parse_inner: ClassVar[bool] = False
    pattern = re.compile(
        r"""
        (?:
          (?<![\\$])\$(?=[^\s$])(.+?)(?<=[^\s\\])\$(?![\d$])
          |
          \\\((.*?)(?<!\\)\\\)
        )
        """,
        re.MULTILINE | re.VERBOSE | re.DOTALL,
    )

    def __init__(self, match: re.Match[str]) -> None:
        self.content = match.group(0)
