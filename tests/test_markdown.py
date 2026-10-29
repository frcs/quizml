import os
import shutil

import pytest
from mistletoe import block_token, span_token

from quizml.markdown.markdown import MarkdownTranscoder
from quizml.yaml import MarkdownString, load


@pytest.fixture(autouse=True)
def reset_mistletoe_tokens():
    block_token.reset_tokens()
    span_token.reset_tokens()


def test_markdown_transcoding_html():
    pkg_dirname = os.path.dirname(__file__)
    yaml_file = os.path.join(pkg_dirname, "fixtures", "test-markdown.yaml")

    yamldoc = load(yaml_file, validate=True)
    transcoder = MarkdownTranscoder(yamldoc)

    # Test HTML conversion with passthrough math (portable, no external latex requirement)
    html_md_dict = transcoder.get_dict(
        opts={"markdown": {"format": "html", "math": "passthrough"}}
    )

    # Check if we have expected keys (the original markdown strings)
    # The keys in the dictionary are the original markdown strings prepended with "##Markdown##"
    # We need to find the keys corresponding to the question and choices.

    question_md = yamldoc["questions"][0]["question"]
    key = question_md
    assert key in html_md_dict

    html_output = html_md_dict[key]

    # Check for HTML tags
    assert "<em>question</em>" in html_output  # *question* -> <em>question</em>

    # Check choices
    choice_0_md = yamldoc["questions"][0]["choices"][0]["x"]
    key_c0 = choice_0_md
    assert key_c0 in html_md_dict
    assert "<img" in html_md_dict[key_c0]  # Should convert ![pic] to <img ...>


@pytest.mark.skipif(not shutil.which("pdflatex"), reason="pdflatex not found in PATH")
def test_markdown_transcoding_html_math_png():
    """Verify HTML equation transcoding via pdflatex when external tools are available."""
    pkg_dirname = os.path.dirname(__file__)
    yaml_file = os.path.join(pkg_dirname, "fixtures", "test-markdown.yaml")

    yamldoc = load(yaml_file, validate=True)
    transcoder = MarkdownTranscoder(yamldoc)

    html_md_dict = transcoder.get_dict(
        opts={"markdown": {"format": "html", "math": "png"}}
    )
    question_md = yamldoc["questions"][0]["question"]
    assert question_md in html_md_dict
    assert "<em>question</em>" in html_md_dict[question_md]


def test_markdown_transcoding_latex():
    pkg_dirname = os.path.dirname(__file__)
    yaml_file = os.path.join(pkg_dirname, "fixtures", "test-markdown.yaml")

    yamldoc = load(yaml_file, validate=True)
    transcoder = MarkdownTranscoder(yamldoc)

    # Test LaTeX conversion
    latex_md_dict = transcoder.get_dict(opts={"markdown": {"format": "latex"}})

    question_md = yamldoc["questions"][0]["question"]
    key = question_md
    assert key in latex_md_dict

    latex_output = latex_md_dict[key]

    # Check for LaTeX specific formatting
    assert r"\textit{question}" in latex_output  # *question* -> \textit{question}

    # Check choices
    choice_0_md = yamldoc["questions"][0]["choices"][0]["x"]
    key_c0 = choice_0_md
    assert key_c0 in latex_md_dict
    assert r"\includegraphics" in latex_md_dict[key_c0]  # ![pic] -> \includegraphics


def test_markdown_transcoding_latex_inline_code_nested():
    """Verify inline code nested in bold or italics renders with \\texttt and no \\verb."""
    q_text = MarkdownString(
        "**Submodule `F` (Shared Encoder) [1.5 marks]:**\n\n*See `module_b`.*"
    )
    yamldoc = {
        "header": {},
        "questions": [
            {
                "type": "essay",
                "question": q_text,
            }
        ],
    }
    transcoder = MarkdownTranscoder(yamldoc)
    latex_dict = transcoder.get_dict(opts={"markdown": {"format": "latex"}})
    rendered = latex_dict[q_text]

    assert r"\textbf{Submodule \texttt{F} (Shared Encoder) [1.5 marks]:}" in rendered
    assert r"\textit{See \texttt{module\_b}.}" in rendered
    assert r"\verb" not in rendered


def test_markdown_transcoding_latex_inline_code_special_chars():
    """Verify inline code with special LaTeX characters is properly escaped inside \\texttt."""
    q_text = MarkdownString(
        "Use `func(a_b, &c, 50%, $10, #id, {key}, x^2, ~home, \\path, <T>, a|b)`."
    )
    yamldoc = {
        "header": {},
        "questions": [
            {
                "type": "essay",
                "question": q_text,
            }
        ],
    }
    transcoder = MarkdownTranscoder(yamldoc)
    latex_dict = transcoder.get_dict(opts={"markdown": {"format": "latex"}})
    rendered = latex_dict[q_text]

    expected_code = (
        r"\texttt{func(a\_b, \&c, 50\%, \$10, \#id, \{key\}, x\textasciicircum{}2, "
        r"\textasciitilde{}home, \textbackslash{}path, \textless{}T\textgreater{}, a\textbar{}b)}"
    )
    assert expected_code in rendered
    assert r"\verb" not in rendered


def test_markdown_transcoding_with_headings():
    """Verify that markdown containing headings does not break document splitting."""
    q1_text = MarkdownString(
        "# Important Concept\n\nPlease read carefully.\n\n## Subpart A\n\nWhat is $x$?"
    )
    q2_text = MarkdownString(
        "Question 2 statement.\n\n# Another Heading\n\nFinal text."
    )
    yamldoc = {
        "header": {},
        "questions": [
            {
                "type": "mc",
                "question": q1_text,
                "choices": [
                    {"x": MarkdownString("First choice")},
                    {"o": MarkdownString("Second choice")},
                ],
            },
            {
                "type": "mc",
                "question": q2_text,
                "choices": [{"x": MarkdownString("Yes")}, {"o": MarkdownString("No")}],
            },
        ],
    }

    transcoder = MarkdownTranscoder(yamldoc)

    # Test HTML: ensure headings and text after headings are fully preserved
    html_dict = transcoder.get_dict(
        opts={"markdown": {"format": "html", "math": "passthrough"}}
    )
    assert q1_text in html_dict
    assert q2_text in html_dict
    assert "Important Concept" in html_dict[q1_text]
    assert "Subpart A" in html_dict[q1_text]
    assert "What is" in html_dict[q1_text]
    assert "Another Heading" in html_dict[q2_text]
    assert "Final text." in html_dict[q2_text]

    # Test LaTeX: ensure section tags and subsequent text are not truncated
    latex_dict = transcoder.get_dict(opts={"fmt": "latex"})
    assert q1_text in latex_dict
    assert q2_text in latex_dict
    assert r"\section{Important Concept}" in latex_dict[q1_text]
    assert r"\subsection{Subpart A}" in latex_dict[q1_text]
    assert "What is $x$?" in latex_dict[q1_text]
    assert r"\section{Another Heading}" in latex_dict[q2_text]
    assert "Final text." in latex_dict[q2_text]


def test_markdown_transcoder_with_figures_path(tmp_path):
    from PIL import Image

    shared_figures = tmp_path / "figures-quiz"
    shared_figures.mkdir()
    quizzes_dir = tmp_path / "quizzes"
    quizzes_dir.mkdir()

    # Create dummy image
    im = Image.new("RGB", (10, 10), color="purple")
    im.save(str(shared_figures / "plot.png"))

    question_text = MarkdownString("Here is a plot:\n![](plot.png)")
    yamldoc = {
        "header": {"_figures_path": "../figures-quiz"},
        "questions": [
            {
                "type": "tf",
                "question": question_text,
                "answer": True,
            }
        ],
    }

    transcoder = MarkdownTranscoder(yamldoc, base_dir=str(quizzes_dir))

    # HTML transcoding: verifies image is located in _figures_path and embedded
    html_dict = transcoder.get_dict(opts={"fmt": "html"})
    assert question_text in html_dict
    assert "data:image/png;base64," in html_dict[question_text]

    # LaTeX transcoding: verifies image name is preserved for \graphicspath
    latex_dict = transcoder.get_dict(opts={"fmt": "latex"})
    assert question_text in latex_dict
    assert r"\includegraphics{plot.png}" in latex_dict[question_text]


def test_inputbasename_with_underscore_not_escaped():
    yamldoc = {
        "header": {"inputbasename": "quizzes/mda_01_final"},
        "questions": [],
    }
    transcoder = MarkdownTranscoder(yamldoc)
    transcoded = transcoder.transcode_target({"markdown": {"format": "latex"}})
    assert transcoded["header"]["inputbasename"] == "quizzes/mda_01_final"


def test_latex_template_graphicspath():
    import os

    from quizml import rendering as renderer

    template_path = os.path.join(
        os.path.dirname(__file__), "../src/quizml/templates/tcd-exam.tex.j2"
    )

    # 1. Single string path
    doc_single = {
        "header": {"title": "Test", "_figures_path": "../figures-quiz"},
        "questions": [],
    }
    rendered_single = renderer.render(doc_single, template_path)
    assert r"\graphicspath{" in rendered_single
    assert "{../figures-quiz/}" in rendered_single

    # 2. List of paths
    doc_list = {
        "header": {"title": "Test", "_figures_path": ["figures", "../shared-figures"]},
        "questions": [],
    }
    rendered_list = renderer.render(doc_list, template_path)
    assert r"\graphicspath{" in rendered_list
    assert "{figures/}" in rendered_list
    assert "{../shared-figures/}" in rendered_list


def test_math_inline_tokenizer():
    import mistletoe as mt

    from quizml.markdown import extensions as mte
    from quizml.markdown.markdown import _parse_markdown_documents

    original_block_tokens = list(mt.block_token._token_types)
    original_span_tokens = list(mt.span_token._token_types)

    def get_inline_math(text):
        doc = _parse_markdown_documents([text])[text]
        p = doc.children[0]
        return [t.content for t in p.children if isinstance(t, mte.MathInline)]

    # 1. Non-greedy \(...\) does not merge equations
    tokens = get_inline_math(r"Let \(a\) and \(b\) be reals.")
    assert tokens == [r"\(a\)", r"\(b\)"]

    assert mt.block_token._token_types == original_block_tokens
    assert mt.span_token._token_types == original_span_tokens

    # 2. Currency with digits does not trigger math
    assert get_inline_math("It costs $5 and $10 today.") == []

    # 3. Valid inline dollar math matches separately
    assert get_inline_math("Here is $x$ and $y^2$.") == ["$x$", "$y^2$"]

    # 4. Single character variable
    assert get_inline_math("What about single char $a$?") == ["$a$"]

    # 5. Escaped dollar signs do not trigger math
    assert get_inline_math(r"Escaped \$5 and \$10") == []


def test_latex_svg_conversion_does_not_mutate_ast_for_html(tmp_path, monkeypatch):
    svg_file = tmp_path / "diagram.svg"
    svg_file.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"></svg>',
        encoding="utf-8",
    )

    def fake_resolve(src, base_dir=None, search_dirs=None):
        pdf_path = tmp_path / "cached.pdf"
        pdf_path.write_bytes(b"%PDF-1.4")
        return str(pdf_path)

    monkeypatch.setattr(
        "quizml.markdown.latex_renderer.resolve_image_path",
        fake_resolve,
    )

    q_text = MarkdownString(f"![]({svg_file.name})")
    yamldoc = {
        "header": {},
        "questions": [
            {
                "type": "essay",
                "question": q_text,
                "answer": MarkdownString("**Bold** model answer"),
            }
        ],
    }

    transcoder = MarkdownTranscoder(yamldoc, base_dir=str(tmp_path))
    latex_doc = transcoder.transcode_target({"markdown": {"format": "latex"}})
    assert "cached.pdf" in latex_doc["questions"][0]["question"]
    assert r"\textbf{Bold}" in latex_doc["questions"][0]["answer"]

    html_doc = transcoder.transcode_target(
        {"markdown": {"format": "html", "math": "svg"}}
    )
    assert "data:image/svg+xml;base64," in html_doc["questions"][0]["question"]
    assert "<strong>Bold</strong>" in html_doc["questions"][0]["answer"]


def test_html_renderer_separates_inline_and_display_equation_keys():
    from quizml.markdown.html_renderer import _equation_key, get_eq_list_from_doc
    from quizml.markdown.markdown import _parse_markdown_documents

    docs = _parse_markdown_documents([r"Inline $x+y$ and display:", "$$x+y$$"])
    inline_eq = get_eq_list_from_doc(docs[r"Inline $x+y$ and display:"])[0]
    display_eq = get_eq_list_from_doc(docs["$$x+y$$"])[0]
    assert _equation_key(inline_eq).startswith("##Inline##")
    assert _equation_key(display_eq).startswith("##Display##")
    assert _equation_key(inline_eq) != _equation_key(display_eq)


def test_templates_handle_optional_essay_answer_and_part_ordering(tmp_path):
    from quizml import rendering as renderer

    yaml_path = tmp_path / "exam.yaml"
    yaml_path.write_text(
        """
title: Template Test
---
- type: part
  title: Section A
  question: Answer all questions in this section.
- type: essay
  marks: 5
  question: Explain gravity.
- type: ordering
  marks: 3
  question: Order these steps.
  choices:
    - First step
    - Second step
""",
        encoding="utf-8",
    )

    yamldoc = load(str(yaml_path), validate=True)
    assert yamldoc["header"]["inputbasename"] == "exam"

    transcoder = MarkdownTranscoder(yamldoc, base_dir=str(tmp_path))
    tex_doc = transcoder.transcode_target({"markdown": {"format": "latex"}})
    tex_template = os.path.join(
        os.path.dirname(__file__), "../src/quizml/templates/tcd-exam.tex.j2"
    )
    rendered_tex = renderer.render(tex_doc, tex_template)
    assert r"\item[{\bf Q.1}]" in rendered_tex
    assert r"\item[{\bf Q.2}]" in rendered_tex
    assert r"\item[{\bf Q.3}]" not in rendered_tex
    assert r"\section*{Section A}" in rendered_tex
    assert "First step" in rendered_tex

    bb_doc = transcoder.transcode_target(
        {
            "markdown": {
                "format": "html",
                "math": "svg",
                "html_postprocess": "blackboard_html",
            }
        }
    )
    bb_template = os.path.join(
        os.path.dirname(__file__), "../src/quizml/templates/blackboard.txt.j2"
    )
    rendered_bb = renderer.render(bb_doc, bb_template)
    assert "ESS\t<p>Explain gravity.</p>\t" in rendered_bb
