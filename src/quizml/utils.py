"a few utility functions to deal with QuizMLYaml objects."


import os
import textwrap


def walk_yaml(yaml_data, fn, *args, **kwargs):
    """
    recursively apply a function to all values in QuizMLYaml obj

    Parameters
    ----------
    yaml_data : list
        yaml file content, as decoded by quizmlyaml.load
    fn: function to apply
    """

    if isinstance(yaml_data, list):
        return [walk_yaml(a, fn, *args, **kwargs) for a in yaml_data]
    elif isinstance(yaml_data, dict):
        new_dict = type(yaml_data)()
        for k, v in yaml_data.items():
            new_dict[k] = walk_yaml(v, fn, *args, **kwargs)
        return new_dict
    else:
        return fn(yaml_data, *args, **kwargs)


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

    def collect_questions(node):
        if isinstance(node, list):
            for item in node:
                collect_questions(item)
        elif isinstance(node, dict):
            for val in node.values():
                collect_questions(val)
        elif isinstance(node, MarkdownString):
            md_list.append(str(node))

    def collect_header(node):
        non_md_keys = ["type"]
        if isinstance(node, list):
            for item in node:
                collect_header(item)
        elif isinstance(node, dict):
            for key, val in node.items():
                if (key not in non_md_keys) and not key.startswith("_"):
                    collect_header(val)
        elif isinstance(node, str):
            md_list.append(str(node))

    if isinstance(yaml_data, dict) and ("header" in yaml_data or "questions" in yaml_data):
        if "header" in yaml_data:
            collect_header(yaml_data["header"])
        
        if "questions" in yaml_data:
            collect_questions(yaml_data["questions"])
    else:
        # Fallback
        collect_header(yaml_data)

    return md_list


def transcode_md_in_yaml(yaml_data, md_dict, schema=None):
    """
    translate all strings in md_dict into their transcribed text
    """

    def transcode_questions(node):
        if isinstance(node, list):
            return [transcode_questions(item) for item in node]
        elif isinstance(node, dict):
            new_dict = {}
            for key, val in node.items():
                new_dict[key] = transcode_questions(val)
            return new_dict
        elif isinstance(node, MarkdownString) and (node in md_dict):
            return md_dict[node]
        else:
            return node

    def transcode_header(node):
        if isinstance(node, list):
            return [transcode_header(item) for item in node]
        elif isinstance(node, dict):
            new_dict = {}
            for key, val in node.items():
                if key.startswith("_"):
                    new_dict[key] = val              
                else:
                    new_dict[key] = transcode_header(val)
            return new_dict
        elif isinstance(node, str) and (node in md_dict):
            return md_dict[node]
        else:
            return node

    if isinstance(yaml_data, dict) and ("header" in yaml_data or "questions" in yaml_data):
        new_doc = {}
        for k, v in yaml_data.items():
            if k == "header":
                new_doc[k] = transcode_header(v)
            elif k == "questions":
                new_doc[k] = transcode_questions(v)
            else:
                new_doc[k] = v
        return new_doc
    else:
        return transcode_header(yaml_data)


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