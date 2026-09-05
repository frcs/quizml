import pytest
from quizml.transcoder.macros import LatexMacroExpander, extract_braced


def test_extract_braced():
    text = "  {abc {def} ghi} remaining"
    val, pos = extract_braced(text, 0)
    assert val == "abc {def} ghi"
    assert text[pos:] == " remaining"

    # Escaped braces
    text2 = r"  {abc \{def\} ghi} rest"
    val2, pos2 = extract_braced(text2, 0)
    assert val2 == r"abc \{def\} ghi"

    # Unclosed brace
    text3 = "{unclosed"
    val3, pos3 = extract_braced(text3, 0)
    assert val3 is None


def test_parameterless_macros():
    preamble = r"""
    \usepackage{amsmath}
    % A comment
    \newcommand{\R}{\mathbb{R}}
    \newcommand\bx{\mathbf{x}}
    \def\E{\mathbb{E}}
    """
    expander = LatexMacroExpander(preamble)
    assert expander.expand(r"\bx \in \R^d") == r"\mathbf{x} \in \mathbb{R}^d"
    assert expander.expand(r"\E[X]") == r"\mathbb{E}[X]"
    # Ensure substring macro names do not falsely match (e.g. \bx vs \bxyz)
    assert expander.expand(r"\bxyz") == r"\bxyz"


def test_parameterized_macros():
    preamble = r"""
    \newcommand{\norm}[1]{\left\|#1\right\|}
    \newcommand{\inner}[2]{\langle #1, #2 \rangle}
    \newcommand{\tuple}[3]{(#1, #2, #3)}
    """
    expander = LatexMacroExpander(preamble)
    assert expander.expand(r"\norm{x}") == r"\left\|x\right\|"
    assert expander.expand(r"\inner{u}{v}") == r"\langle u, v \rangle"
    assert expander.expand(r"\tuple{a}{b}{c}") == r"(a, b, c)"


def test_nested_macro_expansion():
    preamble = r"""
    \newcommand{\R}{\mathbb{R}}
    \newcommand{\bx}{\mathbf{x}}
    \newcommand{\norm}[1]{\left\|#1\right\|}
    """
    expander = LatexMacroExpander(preamble)
    # Nested expansion: \norm{\bx} should expand \norm and then expand \bx
    assert expander.expand(r"\norm{\bx} \in \R") == r"\left\|\mathbf{x}\right\| \in \mathbb{R}"


def test_declare_math_operator():
    preamble = r"""
    \DeclareMathOperator{\argmin}{arg\,min}
    \DeclareMathOperator*{\argmax}{arg\,max}
    """
    expander = LatexMacroExpander(preamble)
    assert expander.expand(r"\argmin_x f(x)") == r"\operatorname{arg\,min}_x f(x)"
    assert expander.expand(r"\argmax_x f(x)") == r"\operatorname*{arg\,max}_x f(x)"


def test_circular_macro_safety():
    preamble = r"""
    \newcommand{\foo}{\bar}
    \newcommand{\bar}{\foo}
    """
    expander = LatexMacroExpander(preamble)
    # Should terminate safely without infinite loop
    result = expander.expand(r"\foo", max_depth=5)
    assert result in (r"\bar", r"\foo")
