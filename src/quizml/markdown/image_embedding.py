import base64
import os
import re
import struct
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path

from PIL import Image

from ..exceptions import MarkdownImageError


def embed_pdf(pdf_filename):
    """returns a base64 string of a PDF file. The PDF is first converted to
    a PNG file using ghostscript (gs).
    """

    pdf_abspath = os.path.abspath(pdf_filename)
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
        except (subprocess.CalledProcessError, FileNotFoundError) as err:
            raise MarkdownImageError(
                f"failed to convert PDF {pdf_filename} to PNG using ghostscript: {err}"
            ) from err

        return embed_base64(png_path)


def embed_base64(pathname):
    """returns a base64 string of an image file."""

    path = Path(pathname)
    suffix = path.suffix.lower()

    if suffix == ".svg":
        ext = "svg+xml"
    elif suffix == ".png":
        ext = "png"
    elif suffix == ".jpeg" or suffix == ".jpg":
        ext = "jpeg"
    elif suffix == ".pdf":
        return embed_pdf(pathname)
    else:
        raise MarkdownImageError(
            f"unsupported image format '{suffix}'. Supported formats: .png, .svg, .jpg, .jpeg, .pdf"
        )

    try:
        data = path.read_bytes()
    except FileNotFoundError as err:
        raise MarkdownImageError(f"cannot read image {pathname}") from err

    if ext == "svg+xml":
        [w, h] = get_SVG_info(data.decode("utf-8", errors="replace"))
    else:
        im = Image.open(BytesIO(data))
        w, h = im.size

    data64 = f"data:image/{ext};base64,{base64.b64encode(data).decode('ascii')}"

    return (w, h, data64)


def get_PNG_info(data):
    """
    get width and height from an image

    Parameters
    ----------
    data : image
        input image
    """

    w, h = struct.unpack(">LL", data[16:24])
    width = int(w)
    height = int(h)
    return width, height


def convert_css_values_to_pixels(value):
    """converts CSS lengths such as 12in into pixels
        https://www.w3.org/TR/css3-values/#cm

    cm	centimeters	1cm = 96px/2.54
    mm	millimeters	1mm = 1/10th of 1cm
    Q	quarter-millimeters	1Q = 1/40th of 1cm
    in	inches	1in = 2.54cm = 96px
    pc	picas	1pc = 1/6th of 1in
    pt	points	1pt = 1/72nd of 1in
    px	pixels	1px = 1/96th of 1in
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


def get_SVG_info(data):
    """
    get width and height from an SVG

    Parameters
    ----------
    data : str
        SVG XML content
    """
    svg_match = re.search(r"<svg\b([^>]*)>", data, re.IGNORECASE | re.DOTALL)
    if not svg_match:
        raise MarkdownImageError("can't read SVG dimensions: no <svg> tag found")

    attrs = svg_match.group(1)
    w_match = re.search(r'\bwidth\s*=\s*["\']([^"\']+)["\']', attrs, re.IGNORECASE)
    h_match = re.search(r'\bheight\s*=\s*["\']([^"\']+)["\']', attrs, re.IGNORECASE)
    vb_match = re.search(r'\bviewBox\s*=\s*["\']([^"\']+)["\']', attrs, re.IGNORECASE)

    vb_w, vb_h = None, None
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
        raise MarkdownImageError("can't read SVG dimensions: missing height and viewBox")

    return round(w), round(h)
