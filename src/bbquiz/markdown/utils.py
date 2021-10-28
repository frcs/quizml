import hashlib
import struct

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

def get_image_info(data):
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


