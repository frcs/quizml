import hashlib
import struct
import re


def get_hash(txt):
    """
    returns a hash from a string

    Parameters
    ----------
    txt : str
        string to be hashed
    """

    return hashlib.md5(txt.encode('utf-8')).hexdigest()
 
def md_combine_list(md_list):
    """
    Collate all Markdown entries into a single Markdown document.

    Parameters
    ----------
    md_list : list  
        list of markdown entries
    """
    
    txt = ""
    for md_entry in md_list:
        txt = txt + "\n\n# " + get_hash(md_entry) + "\n\n" + md_entry
    return txt

def append_unique(alist, blist):
    """
    append all elements of blist to alist that are not already in alist.

    Parameters
    ----------
    alist : list
        input list
    blist : list
        list to be added
    """

    for b in blist:
        if b not in alist:
            alist.append(b)
    return alist

# def get_PNG_info(data):
#     """
#     get width and height from an image

#     Parameters
#     ----------
#     data : image
#         input image
#     """

#     w, h = struct.unpack('>LL', data[16:24])
#     width = int(w)
#     height = int(h)
#     return width, height


# def get_image_info(data):
#     from PIL import Image

#     # Load an image
#     image = Image.open('path/to/your/image.jpg')

#     # Get the size of the image
#     width, height = image.size


# def convert_css_values_to_pixels(value):

#     """ converts CSS lengths such as 12in into pixels
#         https://www.w3.org/TR/css3-values/#cm
    
#     cm	centimeters	1cm = 96px/2.54
#     mm	millimeters	1mm = 1/10th of 1cm
#     Q	quarter-millimeters	1Q = 1/40th of 1cm
#     in	inches	1in = 2.54cm = 96px
#     pc	picas	1pc = 1/6th of 1in
#     pt	points	1pt = 1/72nd of 1in
#     px	pixels	1px = 1/96th of 1in
#     """
    
#     regex = r"(\d*\.?\d*)\s*([a-zA-Z]*)"
#     m = re.search(regex, value, re.MULTILINE)
#     if m:
#         val = float(m.group(1))
#         unit = m.group(2)
#     else:
#         raise MarkdownImageError("Sorry, bad size value when reading CSS dimensions")

#     if unit == 'pt':
#         val = val * 1.333
#     elif unit == 'em':
#         val = val * 16
#     elif unit == 'in':
#         val = val * 96
#     elif unit == 'cm':
#         val = val * 96/2.54
#     elif unit == 'mm':
#         val = val * 9.6/2.54
#     elif unit == 'pc':
#         val = val * 96/6.0
#     elif unit == 'Q':
#         val = val * 9.6/2.54/4

#     return val
    

# def get_SVG_info(data):
#     """
#     get width and height from an SVG 

#     Parameters
#     ----------
#     data : image
#         input image
#     """
#     pattern = r"<svg.*width\s*=[\"\'](.*?)[\"\'].*height\s*=\s*[\"\'](.*?)[\"\'].*>"
#     m = re.search(pattern, data, re.MULTILINE)
    
#     if m:        
#         w = convert_css_values_to_pixels(m.group(1))       
#         h = convert_css_values_to_pixels(m.group(2))
#     else:
#         raise MarkdownImageError("can't read SVG dimensions")

    
#     width = w
#     height = h
#     return width, height


