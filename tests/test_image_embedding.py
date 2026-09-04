import os
from pathlib import Path

import pytest

from quizml.exceptions import MarkdownImageError
from quizml.markdown.image_embedding import (
    embed_base64,
    embed_pdf,
    get_SVG_info,
)


def test_embed_base64_jpeg():
    fixtures_dir = Path(__file__).parent / "fixtures" / "figures"
    img_path = fixtures_dir / "dogcat.jpg"
    w, h, data64 = embed_base64(str(img_path))
    assert w > 0
    assert h > 0
    assert data64.startswith("data:image/jpeg;base64,")


def test_embed_base64_svg(tmp_path):
    # 1. Standard width and height
    svg1 = tmp_path / "std.svg"
    svg1.write_text('<svg width="200" height="100"><rect width="200" height="100"/></svg>')
    w, h, data = embed_base64(str(svg1))
    assert w == 200
    assert h == 100
    assert data.startswith("data:image/svg+xml;base64,")

    # 2. Inverted attributes (height before width)
    svg2 = tmp_path / "inverted.svg"
    svg2.write_text('<svg height="80" width="160"><rect width="160" height="80"/></svg>')
    w, h, data = embed_base64(str(svg2))
    assert w == 160
    assert h == 80

    # 3. ViewBox only (no width/height)
    svg3 = tmp_path / "viewbox.svg"
    svg3.write_text('<svg viewBox="0 0 300 150"><circle cx="150" cy="75" r="50"/></svg>')
    w, h, data = embed_base64(str(svg3))
    assert w == 300
    assert h == 150


def test_embed_pdf_preserves_cwd_and_cleans_up():
    demo_pdf = Path(__file__).parent.parent / "demo" / "test" / "figures" / "fig-1.pdf"
    if not demo_pdf.exists():
        pytest.skip("fig-1.pdf not found in demo folder")

    cwd_before = os.getcwd()
    w, h, data64 = embed_pdf(str(demo_pdf))
    cwd_after = os.getcwd()

    assert cwd_before == cwd_after, "embed_pdf must not modify process working directory"
    assert w > 0
    assert h > 0
    assert data64.startswith("data:image/png;base64,")


def test_embed_base64_errors(tmp_path):
    # Non-existent file
    with pytest.raises(MarkdownImageError, match="cannot read image"):
        embed_base64("non_existent_image.png")

    # Unsupported format
    bmp_file = tmp_path / "test.bmp"
    bmp_file.write_bytes(b"BMfakebmp")
    with pytest.raises(MarkdownImageError, match="unsupported image format"):
        embed_base64(str(bmp_file))

    # Invalid SVG without dimensions or viewBox
    bad_svg = tmp_path / "bad.svg"
    bad_svg.write_text("<svg><path d='M0 0'/></svg>")
    with pytest.raises(MarkdownImageError, match="missing width and viewBox"):
        get_SVG_info(bad_svg.read_text())


def test_embed_base64_with_base_dir(tmp_path):
    sub_dir = tmp_path / "nested"
    sub_dir.mkdir()
    img_file = sub_dir / "diagram.png"
    
    # Create a simple 10x10 PNG
    from PIL import Image
    im = Image.new("RGB", (10, 10), color="blue")
    im.save(str(img_file))

    # Passing relative path with base_dir resolves successfully
    w, h, data64 = embed_base64("diagram.png", base_dir=str(sub_dir))
    assert w == 10
    assert h == 10
    assert data64.startswith("data:image/png;base64,")


def test_embed_base64_with_search_dirs(tmp_path):
    shared_dir = tmp_path / "figures-quiz"
    shared_dir.mkdir()
    quiz_dir = tmp_path / "quizzes"
    quiz_dir.mkdir()

    from PIL import Image
    im = Image.new("RGB", (15, 20), color="red")
    im.save(str(shared_dir / "quiz-plot.png"))

    # Asset found via search_dirs without specifying directory in pathname
    w, h, data64 = embed_base64(
        "quiz-plot.png", base_dir=str(quiz_dir), search_dirs=[str(shared_dir)]
    )
    assert w == 15
    assert h == 20
    assert data64.startswith("data:image/png;base64,")


def test_resolve_image_path_with_search_dirs(tmp_path):
    from quizml.markdown.latex_renderer import resolve_image_path
    from PIL import Image

    shared_dir = tmp_path / "figures-quiz"
    shared_dir.mkdir()
    quiz_dir = tmp_path / "quizzes"
    quiz_dir.mkdir()

    im = Image.new("RGB", (10, 10), color="green")
    im.save(str(shared_dir / "regression.png"))

    # When found in search_dirs, resolve_image_path retains filename for \graphicspath
    resolved = resolve_image_path(
        "regression.png", base_dir=str(quiz_dir), search_dirs=[str(shared_dir)]
    )
    assert resolved == "regression.png"

