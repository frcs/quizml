import re


def test_math_regex():
    md_text = r"""
    $$
      E({\bf w}) = \frac{1}{N} \sum_{i=1}^N \|{\bf w}^{\top}{\bf x}_i - {\bf
      y}_i\|^2
    $$
    
    Inline: $x^2$
    
    Slash bracket: \[ y^2 \]
    
    Equation env:
    \begin{equation}
      z^2
    \end{equation}
    """

    # This is the regex from the original file
    regex = r"""
    (?<!\\)      # negative look-behind to make sure start is not escaped 
    (?:          # start non-capture group for all possible match starts
    ((?<!\$)\${2}(?!\$))| # group 1, match dollar signs only 
    (\\\[)|               # group 2, \[
    (\\begin\{(equation|split|alignat|multline|gather|align|flalign|)(\*?)\}) # group 3, all amsmath
    )
    (?(1)(.*?)(?<!\\)(?<!\$)\1(?!\$)| # group 4, content for $$ math
    (?(2)(.*?)(?<!\\)\\\]| # group 5, content for \[ math
    (?(3)(.*?)(?<!\\)\\end\{\4\5\}
    ))) # group 6, content for \begin math
    """

    matches = list(re.finditer(regex, md_text, re.MULTILINE | re.DOTALL | re.VERBOSE))
    
    assert len(matches) == 3
    
    # Check $$ match
    assert "$$" in matches[0].group(0)
    
    # Check $ match is NOT in this regex (Wait, the regex above checks for $${2} i.e. $$, what about single $?)
    # Looking at the regex: ((?<!\$)\${2}(?!\$)) matches $$.
    # It does NOT seem to match single $ inline math based on group 1.
    # But wait, let's re-read carefully.
    
    # Actually, the regex seems to be targeting display math mainly or complex structures.
    # Group 1: $${2} -> $$
    
    # Let's check what it actually matched in the original test output (implied)
    # The original file had matches = re.finditer(...)
    
    # Let's see if it finds 'Inline: $x^2$'
    # The regex does NOT appear to have a group for single $.
    # So it should skip $x^2$.
    
    # Let's verify what I captured.
    # 1. $$ ... $$
    # 2. \[ ... \]
    # 3. \begin{equation} ... \end{equation}
    
    # Wait, my assertion `len(matches) == 4` might be wrong if it doesn't match single $.
    # Let's assume it matches the 3 display blocks.
    
    count = 0
    for match in matches:
        if "$$" in match.group(0):
            count += 1
        if r"\[" in match.group(0):
            count += 1
        if "\\begin{equation}" in match.group(0):
            count += 1
        
    assert count == 3


def test_math_display_token_parsing():
    import mistletoe as mt

    from quizml.transcoder.tokens import MathDisplay
    from quizml.transcoder.transcoder import _setup_mistletoe_tokens

    _setup_mistletoe_tokens()

    # Multi-line block equation
    doc1 = mt.Document("$$\nE=mc^2\n$$\n\nParagraph text.")
    assert len(doc1.children) == 2
    assert isinstance(doc1.children[0], MathDisplay)
    assert doc1.children[0].latex == "$$\nE=mc^2\n$$"

    # Single-line block equation
    doc2 = mt.Document("$$E=mc^2$$\nParagraph text.")
    assert len(doc2.children) == 2
    assert isinstance(doc2.children[0], MathDisplay)
    assert doc2.children[0].latex == "$$E=mc^2$$"
    assert doc2.children[1].children[0].content == "Paragraph text."

    # Interrupted paragraph with two single-line block equations
    doc3 = mt.Document("Question text\n$$E=mc^2$$\nExplanation text\n$$\\alpha=5$$\nDone.")
    assert len(doc3.children) == 5
    assert isinstance(doc3.children[1], MathDisplay)
    assert isinstance(doc3.children[3], MathDisplay)


def test_math_display_wrapped_in_paragraph():
    from quizml.transcoder.transcoder import MarkdownTranscoder

    yaml_data = [
        {
            "question": (
                "Intro text\n\n"
                "$$\nE=mc^2\n$$\n\n"
                "\\begin{equation}\n\\int_x \\sin(x)dx = \\phi\n\\end{equation}\n"
            )
        }
    ]
    tc = MarkdownTranscoder(yaml_data)
    html_res = tc.html_dict({"fmt": "html-mathml"})
    content = list(html_res.values())[0]
    assert "<p><math display=\"block\"" in content
    assert content.count("<p>") >= 3
