
import base64
from PIL import Image
from io import BytesIO
from pathlib import Path
import re

from subprocess import call
import tempfile
import subprocess
import os

from ..exceptions import MarkdownImageError


def embed_pdf(pdf_filename):
    """returns a base64 string of a PDF file. The PDF is first converted to
    a PNG file using ghostscript (gs).
    """

    pdf_abspath = os.path.abspath(pdf_filename)
    tmpdir = tempfile.mkdtemp()
    olddir = os.getcwd()
    os.chdir(tmpdir)
    
    call(["gs",
          "-dBATCH", '-q', "-dNOPAUSE",
          "-sDEVICE=pngalpha",
          "-r250",
          "-dTextAlphaBits=4",
          "-dGraphicsAlphaBits=4",
          "-sOutputFile=pngfile.png",
          pdf_abspath])

    # converting into base64 strings
    [w, h, data64] = embed_base64("pngfile.png")
    os.chdir(olddir)
    return (w, h, data64)



def embed_base64(pathname):
    """returns a base64 string of an image file.
    """

    path = Path(pathname)
    suffix = path.suffix.lower()

    if suffix=='.svg':
        ext = 'svg+xml'
    elif suffix=='.png':
        ext = 'png'
    elif suffix=='.jpeg' or suffix=='.jpg':
        ext = 'jpeg'
    elif suffix=='.pdf':
        return embed_pdf(pathname)
    else:
        raise MarkdownImageError(
            "image formats other than png and svg are not supported")
            
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        raise MarkdownImageError(f"cannot read image {pathname}")
          
    if ext=='svg+xml':
        [w, h] = get_SVG_info(data.decode())
    else:
        im = Image.open(BytesIO(data))
        w, h = im.size
                        
    data64 = (
        f"data:image/{ext};base64,"
        f"{base64.b64encode(data).decode('ascii')}")
    
    return (w, h, data64)


def get_PNG_info(data):
    """
    get width and height from an image

    Parameters
    ----------
    data : image
        input image
    """

    w, h = struct.unpack('>LL', data[16:24])
    width = int(w)
    height = int(h)
    return width, height


def get_image_info(data):
    from PIL import Image

    # Load an image
    image = Image.open('path/to/your/image.jpg')

    # Get the size of the image
    width, height = image.size


def convert_css_values_to_pixels(value):

    """ converts CSS lengths such as 12in into pixels
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

    if unit == 'pt':
        val = val * 1.333
    elif unit == 'em':
        val = val * 16
    elif unit == 'in':
        val = val * 96
    elif unit == 'cm':
        val = val * 96/2.54
    elif unit == 'mm':
        val = val * 9.6/2.54
    elif unit == 'pc':
        val = val * 96/6.0
    elif unit == 'Q':
        val = val * 9.6/2.54/4

    return val
    

def get_SVG_info(data):
    """
    get width and height from an SVG 

    Parameters
    ----------
    data : image
        input image
    """
    pattern = r"<svg.*width\s*=[\"\'](.*?)[\"\'].*height\s*=\s*[\"\'](.*?)[\"\'].*>"
    m = re.search(pattern, data, re.MULTILINE)
    
    if not m:
        raise MarkdownImageError("can't read SVG dimensions")
        
    w = convert_css_values_to_pixels(m.group(1))       
    h = convert_css_values_to_pixels(m.group(2))

    return w, h


