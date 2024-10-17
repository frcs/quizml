"""a few utility functions to deal with BBYaml objects.



"""


def filter_yaml(yaml_data, f):
    """
    apply a function to all values in BByaml obj

    Parameters
    ----------
    yaml_data : list
        yaml file content, as decoded by bbyaml.load
    """

    if isinstance(yaml_data, list):
        return [filter_yaml(a,f) for a in yaml_data]
    elif isinstance(yaml_data, dict):
        return dict(zip(
            yaml_data.keys(),
            [filter_yaml(a, f) for a in yaml_data.values()]))
    else:
        return f(yaml_data)

def get_header_questions(yaml_data):
    """
    returns a header dict and a list containing all the questions

    Parameters
    ----------
    yaml_data : list
        yaml file content, as decoded by bbyaml.load
    """

    header = None
    questions = []
    for entry in yaml_data:
        if entry['type'] == 'header':
            header = entry
        else:
            questions.append(entry)
    return (header, questions)



def get_md_list_from_yaml(yaml_data, md_list=[]):
    """
    List all Markdown entries in the yaml file.

    Parameters
    ----------
    yaml_data : yaml datastruct, eg. list of dicts
        yaml file content, as decoded by bbyaml.load
    md_list : list
        output list of markdown entries
    """
        
    non_md_keys = ['type']
    
    if isinstance(yaml_data, list):
        for item in yaml_data:
            md_list = get_md_list_from_yaml(item, md_list)
    elif isinstance(yaml_data, dict):
        for key, val in yaml_data.items():
            if (key not in non_md_keys) and not key.startswith("pre_"):
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
        yaml file content, as decoded by bbyaml.load
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



