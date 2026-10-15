from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from quizml.exceptions import LatexCompilationError
from quizml.markdown.extensions import MathDisplay, MathInline
from quizml.markdown.html_renderer import build_eq_dict_PNG
from quizml.markdown.latextools import LatexRunner


# Helper functions to create correctly-structured mock tokens
def create_mock_inline(content):
    """Creates a MathInline token using a mock match object."""
    mock_match = MagicMock()
    # The real MathInline.__init__ uses match.group(0)
    mock_match.group.return_value = content
    return MathInline(mock_match)


def create_mock_display(content):
    """Creates a MathDisplay token using a list of lines."""
    # The real MathDisplay.__init__ takes a list of strings
    return MathDisplay([content])


def test_external_latex_tool_failure_is_typed_and_trimmed():
    process = MagicMock(
        returncode=1,
        stdout="routine output\n! fatal latex error\nerror details\n",
        stderr="",
    )
    with LatexRunner() as runner:
        with patch("quizml.markdown.latextools.subprocess.run", return_value=process):
            with pytest.raises(LatexCompilationError, match="! fatal latex error"):
                runner._run_checked(["fake-tool"], "fake-tool", runner.temp_dir)


@patch("quizml.markdown.html_renderer.save_to_cache")
@patch("quizml.markdown.html_renderer.get_from_cache")
@patch("quizml.markdown.html_renderer.embed_base64")
@patch("quizml.markdown.html_renderer.LatexRunner")
def test_build_eq_dict_png_success(
    MockLatexRunner, mock_embed_base64, mock_get_from_cache, mock_save_to_cache
):
    """
    Tests that build_eq_dict_PNG successfully generates an image dictionary
    by mocking the external pdflatex and gs commands.
    """
    # 0. Setup Cache Mock
    mock_get_from_cache.return_value = None

    # 1. Setup Mocks
    mock_latex_runner_instance = MockLatexRunner.return_value.__enter__.return_value
    mock_latex_runner_instance.run_pdflatex.return_value = (
        Path("/tmp/fake.pdf"),
        [0.5, 0.0],
    )
    mock_latex_runner_instance.run_gs_png.return_value = [
        Path("/tmp/img1.png"),
        Path("/tmp/img2.png"),
    ]

    mock_embed_base64.side_effect = [
        (100, 50, "data:image/png;base64,inline_fake_data"),
        (200, 80, "data:image/png;base64,display_fake_data"),
    ]

    # 2. Test Data
    # Use helper functions to create realistic token objects
    eq_list = [
        create_mock_inline(r"$E=mc^2$"),
        create_mock_display(r"$$\int_0^\infty x^2 dx$$"),
    ]
    opts = {}

    # 3. Call the function
    eq_dict = build_eq_dict_PNG(eq_list, opts)

    # 4. Assertions
    mock_latex_runner_instance.run_pdflatex.assert_called_once()
    latex_content = mock_latex_runner_instance.run_pdflatex.call_args[0][0]
    assert r"\setbox0=\hbox{$E=mc^2$}" in latex_content
    assert (
        r"\begin{standalone}$$\int_0^\infty x^2 dx$$\end{standalone}" in latex_content
    )

    mock_latex_runner_instance.run_gs_png.assert_called_once_with(Path("/tmp/fake.pdf"))

    assert mock_embed_base64.call_count == 2
    mock_embed_base64.assert_any_call(Path("/tmp/img1.png"))
    mock_embed_base64.assert_any_call(Path("/tmp/img2.png"))

    assert len(eq_dict) == 2

    # Robust assertions checking for key parts of the generated HTML
    inline_html = eq_dict["##Inline##" + r"$E=mc^2$"]
    assert "src='data:image/png;base64,inline_fake_data'" in inline_html
    assert "alt='\\(E=mc^2\\)'" in inline_html
    assert "width='50'" in inline_html
    assert "height='25'" in inline_html
    assert "style='vertical-align:-25.0px;'" in inline_html

    display_html = eq_dict["##Display##" + r"$$\int_0^\infty x^2 dx$$"]
    assert "src='data:image/png;base64,display_fake_data'" in display_html
    assert "alt='\\[\\int_0^\\infty x^2 dx\\]'" in display_html
    assert "width='100'" in display_html
    assert "height='40'" in display_html


@patch("quizml.markdown.html_renderer.get_from_cache")
@patch("quizml.markdown.html_renderer.LatexRunner")
def test_build_eq_dict_png_latex_error(MockLatexRunner, mock_get_from_cache):
    """
    Tests that build_eq_dict_PNG properly propagates a LatexCompilationError
    if the mocked pdflatex command fails.
    """
    # 0. Setup Cache Mock
    mock_get_from_cache.return_value = None

    # 1. Setup Mock
    mock_latex_runner_instance = MockLatexRunner.return_value.__enter__.return_value
    mock_latex_runner_instance.run_pdflatex.side_effect = LatexCompilationError(
        "LaTeX failed!"
    )

    # 2. Test Data
    eq_list = [create_mock_inline(r"$E=mc^2$")]
    opts = {}

    # 3. Call and Assert Exception
    with pytest.raises(LatexCompilationError, match="LaTeX failed!"):
        build_eq_dict_PNG(eq_list, opts)

    # 4. Assert that gs was not called
    mock_latex_runner_instance.run_gs_png.assert_not_called()


@patch("quizml.markdown.html_renderer.get_from_cache", return_value=None)
@patch("quizml.markdown.html_renderer.LatexRunner")
def test_build_eq_dict_png_count_mismatch(MockLatexRunner, mock_cache):
    mock_latex = MockLatexRunner.return_value.__enter__.return_value
    mock_latex.run_pdflatex.return_value = (Path("/tmp/fake.pdf"), [0.5])
    # 2 equations expected, but only 1 PNG returned
    mock_latex.run_gs_png.return_value = [Path("/tmp/img1.png")]

    eq_list = [create_mock_inline(r"$x$"), create_mock_inline(r"$y$")]
    with pytest.raises(
        LatexCompilationError,
        match="Mismatch between number of equations and compiled PNG",
    ):
        build_eq_dict_PNG(eq_list, {})


@patch("quizml.markdown.html_renderer.get_from_cache", return_value=None)
@patch("quizml.markdown.html_renderer.LatexRunner")
def test_build_eq_dict_svg_count_mismatch(MockLatexRunner, mock_cache):
    from quizml.markdown.html_renderer import build_eq_dict_SVG

    mock_latex = MockLatexRunner.return_value.__enter__.return_value
    mock_latex.run_latex_dvi.return_value = Path("/tmp/fake.dvi")
    # 2 equations expected, but only 1 SVG returned
    mock_latex.run_dvisvgm_svg.return_value = [Path("/tmp/img1.svg")]

    eq_list = [create_mock_inline(r"$x$"), create_mock_inline(r"$y$")]
    with pytest.raises(
        LatexCompilationError,
        match="Mismatch between number of equations and compiled SVG",
    ):
        build_eq_dict_SVG(eq_list, {})


def test_render_image_with_width():
    from quizml.exceptions import MarkdownAttributeError
    from quizml.markdown.extensions import ImageWithWidth
    from quizml.markdown.html_renderer import QuizMLYamlHTMLRenderer

    renderer = QuizMLYamlHTMLRenderer(eq_dict={})

    def make_token(width, title="Diagram", src="plot.png"):
        mock_match = MagicMock()
        mock_match.group.side_effect = lambda idx: {1: title, 2: src, 3: width}[idx]
        return ImageWithWidth(mock_match)

    with patch(
        "quizml.markdown.html_renderer.embed_base64",
        return_value=[200, 100, "data:image/png;base64,abc"],
    ):
        # 1. Centimeters (single digit and double digit)
        res_5cm = renderer.render_image_with_width(make_token("5cm"))
        assert 'style="width:5cm;"' in res_5cm
        assert 'src="data:image/png;base64,abc"' in res_5cm
        assert 'alt="Diagram"' in res_5cm

        res_10cm = renderer.render_image_with_width(make_token("10cm"))
        assert 'style="width:10cm;"' in res_10cm

        # 2. Percentage
        res_pct = renderer.render_image_with_width(make_token("50%"))
        assert 'style="width:50%;"' in res_pct

        # 3. LaTeX \linewidth
        res_lw = renderer.render_image_with_width(make_token(r"0.5\linewidth"))
        assert 'style="width:50%;"' in res_lw

        res_full_lw = renderer.render_image_with_width(make_token(r"\linewidth"))
        assert 'style="width:100%;"' in res_full_lw

        # 4. Pure digits (pixels)
        res_px = renderer.render_image_with_width(make_token("300"))
        assert 'style="width:300px;"' in res_px

        # 5. Invalid width raises MarkdownAttributeError
        with pytest.raises(MarkdownAttributeError, match="Sorry, bad width attr"):
            renderer.render_image_with_width(make_token("auto"))


def test_blackboard_html_postprocess_is_opt_in():
    from unittest.mock import patch

    from quizml.markdown.html_renderer import (
        QuizMLYamlHTMLRenderer,
        get_html_dict,
    )

    html_fragment = "<p>first line\nsecond line</p>"
    with patch.object(QuizMLYamlHTMLRenderer, "render", return_value=html_fragment):
        with patch(
            "quizml.markdown.html_renderer.inline_css",
            return_value=html_fragment,
        ) as inline_css:
            generic = get_html_dict({"md": object()}, {"fmt": "html"})["md"]
            assert generic == html_fragment
            inline_css.assert_not_called()

            blackboard = get_html_dict(
                {"md": object()},
                {"fmt": "html", "html_postprocess": "blackboard_html"},
            )["md"]
            assert "\n" not in blackboard
            inline_css.assert_called_once()
