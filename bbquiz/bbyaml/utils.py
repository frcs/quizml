

def get_header_questions(yaml_data):
    header = None
    questions = []
    for entry in yaml_data:
        if entry['type'] == 'header':
            header = entry
            break
        else:
            questions.append(entry)
    return (header, questions)


def get_solutions(yaml_data):
    solutions = []
    for entry in yaml_data:
        if entry['type'] == 'essay':
            solutions.append({'type': 'essay'})
        if entry['type'] == 'ma':
            s = []
            for a in entry['answers']:
                s.append(a['correct'])
            solutions.append({'type': 'ma', 'solutions': s})
        if entry['type'] == 'matching':
            s = []
            for a in entry['answers']:
                s.append(a['correct'])
            solutions.append({'type': 'ma', 'solutions': s})
        if entry['type'] == 'ordering':
            s = []
            for a in entry['answers']:
                s.append(a['correct'])
            solutions.append({'type': 'ordering', 'solutions': s})

    return solutions


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
    # if md_list is None:
    #     md_list = []
        
    non_md_keys = ['type']

    if isinstance(yaml_data, list):
        for item in yaml_data:
            md_list = get_md_list_from_yaml(item, md_list)
    elif isinstance(yaml_data, dict):
        for key, val in yaml_data.items():
            if key not in non_md_keys:
                md_list = get_md_list_from_yaml(val, md_list)
    elif (isinstance(yaml_data, str) or
          isinstance(yaml_data, int) or
          isinstance(yaml_data, float) or
          isinstance(yaml_data, complex)):
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
    
    if isinstance(yaml_data, list):
        out_data = [transcode_md_in_yaml(item, md_dict)
               for item in yaml_data]
    elif isinstance(yaml_data, dict):
        out_data = {}
        for key, val in yaml_data.items():
            out_data[key] = transcode_md_in_yaml(val, md_dict)
    elif isinstance(yaml_data, str) and (yaml_data in md_dict):
        out_data = md_dict[yaml_data]
    else:
        out_data = yaml_data

    return out_data
