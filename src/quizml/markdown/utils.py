import hashlib


def get_hash(txt):
    """
    returns a hash from a string

    Parameters
    ----------
    txt : str
        string to be hashed
    """

    return hashlib.md5(txt.encode("utf-8")).hexdigest()


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
