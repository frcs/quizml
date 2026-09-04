"""Tree traversal and node transformation utilities for QuizML documents."""

from quizml.quizmlyaml.validator import MarkdownString


def iter_nodes(data, key_filter=None):
    """Generator that yields all leaf nodes in the data structure.

    Recurses into lists and dicts.

    :param data: The structure to traverse (list, dict, or value).
    :param key_filter: Optional function(key) -> bool.
                       If True (or None), recurses into the dict value.
                       If False, skips the key (value is ignored).
    """
    if isinstance(data, list):
        for item in data:
            yield from iter_nodes(item, key_filter)
    elif isinstance(data, dict):
        for k, v in data.items():
            if key_filter and not key_filter(k):
                continue
            yield from iter_nodes(v, key_filter)
    else:
        yield data


def map_nodes(data, fn, key_filter=None):
    """Recursively applies fn to all leaf nodes in the data structure.

    Returns a new structure with transformed values.

    :param data: The structure to traverse.
    :param fn: Function(node) -> new_node. Applied to leaves.
    :param key_filter: Optional function(key) -> bool.
                       If True (or None), recurses into the dict value.
                       If False, preserves the value as-is without recursion/transformation.
    """
    if isinstance(data, list):
        return [map_nodes(item, fn, key_filter) for item in data]
    elif isinstance(data, dict):
        new_dict = type(data)()
        for k, v in data.items():
            if key_filter and not key_filter(k):
                new_dict[k] = v
            else:
                new_dict[k] = map_nodes(v, fn, key_filter)
        return new_dict
    else:
        return fn(data)


def get_md_list_from_yaml(yaml_data):
    """List all Markdown entries in the yaml document.

    Uses MarkdownString type for questions, and non-underscore string keys for headers.
    """
    md_list = []

    def header_key_filter(key):
        non_md_keys = ["type", "inputbasename"]
        return (key not in non_md_keys) and not key.startswith("_")

    if isinstance(yaml_data, dict) and ("header" in yaml_data or "questions" in yaml_data):
        if "header" in yaml_data:
            for node in iter_nodes(yaml_data["header"], header_key_filter):
                if isinstance(node, str):
                    md_list.append(str(node))

        if "questions" in yaml_data:
            for node in iter_nodes(yaml_data["questions"]):
                if isinstance(node, MarkdownString):
                    md_list.append(str(node))
    else:
        # Fallback
        for node in iter_nodes(yaml_data, header_key_filter):
            if isinstance(node, str):
                md_list.append(str(node))

    return md_list


def transcode_md_in_yaml(yaml_data, md_dict):
    """Translates all strings in md_dict into their transcoded text."""

    def transform_questions(node):
        if isinstance(node, MarkdownString) and node in md_dict:
            return md_dict[node]
        return node

    def transform_header(node):
        if isinstance(node, str) and node in md_dict:
            return md_dict[node]
        return node

    def header_key_filter(key):
        return key != "inputbasename" and not key.startswith("_")

    if isinstance(yaml_data, dict) and ("header" in yaml_data or "questions" in yaml_data):
        new_doc = {}
        for k, v in yaml_data.items():
            if k == "header":
                new_doc[k] = map_nodes(v, transform_header, header_key_filter)
            elif k == "questions":
                new_doc[k] = map_nodes(v, transform_questions)
            else:
                new_doc[k] = v
        return new_doc
    else:
        return map_nodes(yaml_data, transform_header, header_key_filter)
