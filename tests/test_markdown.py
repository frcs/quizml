import os

import pytest
from mistletoe import block_token, span_token

from quizml.loader import load
from quizml.markdown.markdown import MarkdownTranscoder
from quizml.utils import MarkdownString


@pytest.fixture(autouse=True)
def reset_mistletoe_tokens():
    block_token.reset_tokens()
    span_token.reset_tokens()


def test_markdown_transcoding_html():
    pkg_dirname = os.path.dirname(__file__)
    yaml_file = os.path.join(pkg_dirname, "fixtures", "test-markdown.yaml")
    
    yamldoc, schema = load(yaml_file, validate=True)
    transcoder = MarkdownTranscoder(yamldoc, schema)
    
    # Test HTML conversion
    html_md_dict = transcoder.get_dict(opts={'fmt': 'html'})
    
    # Check if we have expected keys (the original markdown strings)
    # The keys in the dictionary are the original markdown strings prepended with "##Markdown##"
    # We need to find the keys corresponding to the question and choices.
    
    question_md = yamldoc['questions'][0]['question']
    key = question_md
    assert key in html_md_dict
    
    html_output = html_md_dict[key]
    
    # Check for HTML tags
    assert "<em>question</em>" in html_output # *question* -> <em>question</em>
    
    # Check for equation placeholders (converts to images or specific spans)
    # The exact format depends on the implementation, but we expect *something* different than raw latex
    # Based on existing code, it likely produces <img> tags for equations in HTML mode if configured, 
    # or keeps them as MathJax/Katex if not.
    # Looking at the code, it uses mistletoe. 
    
    # Let's check choices
    choice_0_md = yamldoc['questions'][0]['choices'][0]['x']
    key_c0 = choice_0_md
    assert key_c0 in html_md_dict
    assert "<img" in html_md_dict[key_c0] # Should convert ![pic] to <img ...>

def test_markdown_transcoding_latex():
    pkg_dirname = os.path.dirname(__file__)
    yaml_file = os.path.join(pkg_dirname, "fixtures", "test-markdown.yaml")
    
    yamldoc, schema = load(yaml_file, validate=True)
    transcoder = MarkdownTranscoder(yamldoc, schema)
    
    # Test LaTeX conversion
    latex_md_dict = transcoder.get_dict(opts={'fmt': 'latex'})
    
    question_md = yamldoc['questions'][0]['question']
    key = question_md
    assert key in latex_md_dict
    
    latex_output = latex_md_dict[key]
    
    # Check for LaTeX specific formatting
    assert r"\textit{question}" in latex_output # *question* -> \textit{question}
    
    # Check choices
    choice_0_md = yamldoc['questions'][0]['choices'][0]['x']
    key_c0 = choice_0_md
    assert key_c0 in latex_md_dict
    assert r"\includegraphics" in latex_md_dict[key_c0] # ![pic] -> \includegraphics


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
                "choices": [{"x": MarkdownString("First choice")}, {"o": MarkdownString("Second choice")}],
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
    html_dict = transcoder.get_dict(opts={"fmt": "html"})
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
    transcoded = transcoder.transcode_target({"fmt": "latex"})
    assert transcoded["header"]["inputbasename"] == "quizzes/mda_01_final"


def test_latex_template_graphicspath():
    import os

    from quizml import renderer

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