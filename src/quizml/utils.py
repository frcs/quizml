"""a few utility functions to deal with QuizMLYaml objects.



"""

def filter_yaml(yaml_data, f):
    """
    apply a function to all values in QuizMLYaml obj

    Parameters
    ----------
    yaml_data : list
        yaml file content, as decoded by quizmlyaml.load
    """

    if isinstance(yaml_data, list):
        return [filter_yaml(a,f) for a in yaml_data]
    elif isinstance(yaml_data, dict):
        new_dict = type(yaml_data)()
        for k, v in yaml_data.items():
            new_dict[k] = filter_yaml(v, f)
        return new_dict
    else:
        return f(yaml_data)


def get_md_list_from_yaml(yaml_data, md_list=[]):
    """
    List all Markdown entries in the yaml file.

    Parameters
    ----------
    yaml_data : yaml datastruct, eg. list of dicts
        yaml file content, as decoded by quizmlyaml.load
    md_list : list
        output list of markdown entries
    """
        
    non_md_keys = ['type']
    
    if isinstance(yaml_data, list):
        for item in yaml_data:
            md_list = get_md_list_from_yaml(item, md_list)
    elif isinstance(yaml_data, dict):
        for key, val in yaml_data.items():
            if (key not in non_md_keys) and not key.startswith("_"):
                md_list = get_md_list_from_yaml(val, md_list)
    elif (isinstance(yaml_data, str)):
        md_list.append(str(yaml_data))
        
    return md_list



def transcode_md_in_yaml(yaml_data, md_dict):
    """
    translate all strings in md_dict into their transcribed text

    Parameters
    ----------
    yaml_data : list
        yaml file content, as decoded by quizmlyaml.load
    md_dict : dictionary 
        markdown entries with their transcriptions
    """

    non_md_keys = ['type']
    
    if isinstance(yaml_data, list):
        out_data = [transcode_md_in_yaml(item, md_dict)
               for item in yaml_data]
    elif isinstance(yaml_data, dict):
        out_data = {}
        for key, val in yaml_data.items():
            if (key not in non_md_keys) and not key.startswith("pre_"):
                out_data[key] = transcode_md_in_yaml(val, md_dict)
            else:
                out_data[key] = val
    elif isinstance(yaml_data, str) and (yaml_data in md_dict):
        out_data = md_dict[yaml_data]
    else:
        out_data = yaml_data

    return out_data


import os
import textwrap

def text_wrap(msg):
    try:
        w, _ = os.get_terminal_size(0)
    except OSError:
        w = 80  # Default width if terminal size can't be determined
    return textwrap.fill(msg, w - 5)

def msg_context_line(lines, lineo, charno=None, highlight=False):
    if (lineo < 1 or lineo > len(lines)):
        return ""
    if highlight:
        # Using simple formatting for now to avoid dependency on rich here
        # This can be enhanced later if needed.
        return f"❱ {lineo:>4} │  {lines[lineo-1]}\n"
    else:
        return f"  {lineo:>4} │ {lines[lineo-1]}\n"

def msg_context(lines, lineo, charno=None):
    msg = msg_context_line(lines, lineo - 1, charno, highlight=False)
    msg += msg_context_line(lines, lineo, charno, highlight=True)
    msg += msg_context_line(lines, lineo + 1, charno, highlight=False)
    return msg



