"""Base64 image embedding, PDF-to-PNG rasterization, and CSS/SVG dimension helpers."""

import base64
import os
import re
import subprocess
import tempfile
from collections.abc import Sequence
from io import BytesIO
from pathlib import Path

from PIL import Image

from ..exceptions import MarkdownImageError
from ..paths import find_path


def _resolve_asset_path(
    pathname: str | Path,
    base_dir: str | Path | None = None,
    search_dirs: Sequence[str | Path] | None = None,
) -> Path:
    """Resolve ``pathname`` against ``search_dirs`` and ``base_dir`` when relative."""
    path = Path(pathname)
    if not path.is_absolute():
        dirs: list[str | Path] = []
        if search_dirs:
            dirs.extend(search_dirs)
        if base_dir:
            dirs.append(base_dir)
        found = find_path(str(pathname), dirs)
        if found:
            path = found[0]
    return path


def embed_pdf(
    pdf_filename: str | Path,
    base_dir: str | Path | None = None,
    search_dirs: Sequence[str | Path] | None = None,
) -> tuple[int, int, str]:
    """Rasterize a PDF image into a PNG via Ghostscript and return its base64 tuple."""
    resolved = _resolve_asset_path(
        pdf_filename, base_dir=base_dir, search_dirs=search_dirs
    )
    pdf_abspath = os.path.abspath(str(resolved))
    if not os.path.exists(pdf_abspath):
        raise MarkdownImageError(f"cannot read image {pdf_filename}")

    with tempfile.TemporaryDirectory(prefix="quizml_pdf_") as tmpdir:
        png_path = os.path.join(tmpdir, "pngfile.png")
        try:
            subprocess.check_call(
                [
                    "gs",
                    "-dBATCH",
                    "-q",
                    "-dNOPAUSE",
                    "-sDEVICE=pngalpha",
                    "-r250",
                    "-dTextAlphaBits=4",
                    "-dGraphicsAlphaBits=4",
                    f"-sOutputFile={png_path}",
                    pdf_abspath,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except (subprocess.CalledProcessError, OSError) as err:
            if isinstance(err, subprocess.CalledProcessError):
                detail = f"Ghostscript exited with status {err.returncode}"
            else:
                detail = err.strerror or str(err)
            raise MarkdownImageError(
                f"failed to convert PDF {pdf_filename} to PNG "
                f"using ghostscript: {detail}"
            ) from err

        return embed_base64(png_path)


def embed_base64(
    pathname: str | Path,
    base_dir: str | Path | None = None,
    search_dirs: Sequence[str | Path] | None = None,
) -> tuple[int, int, str]:
    """Read an image file and return ``(width_px, height_px, data_uri)``."""
    path = _resolve_asset_path(pathname, base_dir=base_dir, search_dirs=search_dirs)
    suffix = path.suffix.lower()

    if suffix == ".svg":
        ext = "svg+xml"
    elif suffix == ".png":
        ext = "png"
    elif suffix in (".jpeg", ".jpg"):
        ext = "jpeg"
    elif suffix == ".pdf":
        return embed_pdf(str(path), base_dir=base_dir, search_dirs=search_dirs)
    else:
        raise MarkdownImageError(
            f"unsupported image format '{suffix}'. "
            "Supported formats: .png, .svg, .jpg, .jpeg, .pdf"
        )

    try:
        data = path.read_bytes()
    except FileNotFoundError as err:
        raise MarkdownImageError(f"cannot read image {pathname}") from err

    if ext == "svg+xml":
        w, h = get_SVG_info(data.decode("utf-8", errors="replace"))
    else:
        im = Image.open(BytesIO(data))
        w, h = im.size

    data64 = f"data:image/{ext};base64,{base64.b64encode(data).decode('ascii')}"
    return (w, h, data64)


def convert_css_values_to_pixels(value: str) -> float:
    """Convert a CSS length string (e.g. ``12in``, ``5cm``, ``72pt``) into pixels.

    Follows W3C CSS Values and Units (96px = 1in = 2.54cm = 72pt = 6pc).
    """
    regex = r"(\d*\.?\d*)\s*([a-zA-Z]*)"
    m = re.search(regex, value, re.MULTILINE)
    if m:
        val = float(m.group(1))
        unit = m.group(2)
    else:
        raise MarkdownImageError("Sorry, bad size value when reading CSS dimensions")

    if unit == "pt":
        val = val * 1.333
    elif unit == "em":
        val = val * 16
    elif unit == "in":
        val = val * 96
    elif unit == "cm":
        val = val * 96 / 2.54
    elif unit == "mm":
        val = val * 9.6 / 2.54
    elif unit == "pc":
        val = val * 96 / 6.0
    elif unit == "Q":
        val = val * 9.6 / 2.54 / 4

    return val


def get_SVG_info(data: str) -> tuple[int, int]:
    """Extract ``(width_px, height_px)`` from an SVG XML string."""
    svg_match = re.search(r"<svg\b([^>]*)>", data, re.IGNORECASE | re.DOTALL)
    if not svg_match:
        raise MarkdownImageError("can't read SVG dimensions: no <svg> tag found")

    attrs = svg_match.group(1)
    w_match = re.search(r'\bwidth\s*=\s*["\']([^"\']+)["\']', attrs, re.IGNORECASE)
    h_match = re.search(r'\bheight\s*=\s*["\']([^"\']+)["\']', attrs, re.IGNORECASE)
    vb_match = re.search(r'\bviewBox\s*=\s*["\']([^"\']+)["\']', attrs, re.IGNORECASE)

    vb_w: float | None = None
    vb_h: float | None = None
    if vb_match:
        parts = vb_match.group(1).replace(",", " ").split()
        if len(parts) == 4:
            try:
                vb_w = float(parts[2])
                vb_h = float(parts[3])
            except ValueError:
                pass

    if w_match:
        w = convert_css_values_to_pixels(w_match.group(1))
    elif vb_w is not None:
        w = vb_w
    else:
        raise MarkdownImageError("can't read SVG dimensions: missing width and viewBox")

    if h_match:
        h = convert_css_values_to_pixels(h_match.group(1))
    elif vb_h is not None:
        h = vb_h
    else:
        raise MarkdownImageError(
            "can't read SVG dimensions: missing height and viewBox"
        )

    return round(w), round(h)
