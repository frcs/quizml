"a few utility functions to deal with QuizMLYaml objects."


import os
import textwrap


def iter_nodes(data, key_filter=None):
    """
    Generator that yields all leaf nodes in the data structure.
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
    """
    Recursively applies fn to all leaf nodes in the data structure.
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


class MarkdownString(str):
    """
    A string subclass to tag values that should be treated as Markdown.
    """
    pass


# --- Schema Helpers ---

def apply_conditions(data, current_schema):
    """
    Applies conditional logic (if/then/else) from JSON schema.
    Handles root if/then/else and those inside allOf/anyOf/oneOf.
    Returns the specific sub-schema to apply, or the original if no condition matches.
    """
    # Helper to check a condition
    def check_condition(cond_schema):
        if "properties" in cond_schema:
            for prop, value in cond_schema["properties"].items():
                if "const" in value:
                    if data.get(prop) != value["const"]:
                        return False
        return True

    # Check root if/then/else
    if "if" in current_schema:
        if check_condition(current_schema["if"]):
            return current_schema.get("then", {})
        else:
            return current_schema.get("else", {})

    # Check combinators
    for key in ["allOf", "anyOf", "oneOf"]:
        if key in current_schema:
            for sub_schema in current_schema[key]:
                if "if" in sub_schema:
                    if check_condition(sub_schema["if"]):
                        return sub_schema.get("then", {})
    
    return current_schema


def is_format_markdown(schema_node):
    if not schema_node or not isinstance(schema_node, dict):
        return False
    if "$ref" in schema_node:
        # Note: simplistic ref resolution, assumes local definitions structure
        # In our specific case, we just need to detect the tag.
        if schema_node["$ref"] == "#/definitions/markdown":
            return True
        return False
    return schema_node.get("format") == "markdown"


# --- Coercion Logic ---

def coerce_value(value, schema):
    """
    Coerce a single value based on the schema type.
    """
    # Check Markdown
    if is_format_markdown(schema):
        if isinstance(value, str):
            return MarkdownString(value)
        return value

    types = schema.get("type", [])
    if isinstance(types, str):
        types = [types]

    if "boolean" in types:
        if isinstance(value, str):
            if value.lower() in ["true", "yes", "on"]:
                return True
            if value.lower() in ["false", "no", "off"]:
                return False
    
    if "integer" in types:
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                pass
    
    if "number" in types:
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                pass
                
    return value


def coerce_data(yaml_data, schema):
    """
    Traverses the yaml_data (specifically questions) and coerces types
    (int, float, bool, MarkdownString) based on the provided schema.
    """
    
    def coerce_recursive(data, current_schema):
        if not current_schema:
            return data

        if isinstance(data, dict):
            refined_schema = apply_conditions(data, current_schema)
            new_dict = {}
            properties = refined_schema.get("properties", {})
            for key, value in data.items():
                if key in properties:
                    new_dict[key] = coerce_recursive(value, properties[key])
                else:
                    new_dict[key] = value
            return new_dict

        elif isinstance(data, list):
            new_list = []
            items_schema = current_schema.get("items", {})
            for item in data:
                new_list.append(coerce_recursive(item, items_schema))
            return new_list
        
        else:
            return coerce_value(data, current_schema)

    if isinstance(yaml_data, dict) and "questions" in yaml_data and schema:
        yaml_data["questions"] = coerce_recursive(yaml_data["questions"], schema)
    
    return yaml_data


# --- Markdown Processing ---

def get_md_list_from_yaml(yaml_data, schema=None):
    """
    List all Markdown entries in the yaml file.
    Uses MarkdownString type for questions, and legacy logic for headers.
    """
    md_list = []

    def header_key_filter(key):
        non_md_keys = ["type"]
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


def transcode_md_in_yaml(yaml_data, md_dict, schema=None):
    """
    translate all strings in md_dict into their transcribed text
    """

    def transform_questions(node):
        if isinstance(node, MarkdownString) and node in md_dict:
            return md_dict[node]
        return node
    
    def transform_header(node):
        if isinstance(node, str) and node in md_dict:
            return md_dict[node]
        return node
        
    def header_key_filter(key):
        return not key.startswith("_")

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


def text_wrap(msg):
    try:
        w, _ = os.get_terminal_size(0)
    except OSError:
        w = 80  # Default width if terminal size can't be determined
    return textwrap.fill(msg, w - 5)


def msg_context_line(lines, lineo, charno=None, highlight=False):
    if lineo < 1 or lineo > len(lines):
        return ""
    if highlight:
        # Using simple formatting for now to avoid dependency on rich here
        # This can be enhanced later if needed.
        return f"❱ {lineo:>4} │  {lines[lineo - 1]}\n"
    else:
        return f"  {lineo:>4} │ {lines[lineo - 1]}\n"


def msg_context(lines, lineo, charno=None):
    msg = msg_context_line(lines, lineo - 1, charno, highlight=False)
    msg += msg_context_line(lines, lineo, charno, highlight=True)
    msg += msg_context_line(lines, lineo + 1, charno, highlight=False)
    return msg