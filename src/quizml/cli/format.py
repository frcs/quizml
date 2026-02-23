
import re
import io
from pathlib import Path
from ruamel.yaml import YAML
from ruamel.yaml.tokens import CommentToken
from ruamel.yaml.error import StreamMark
from ruamel.yaml.scalarstring import LiteralScalarString
from ..exceptions import QuizMLError

def is_q_comment(token):
    """Checks if a comment token matches the <Q#> pattern."""
    if not isinstance(token, CommentToken):
        return False
    # Matches "# <Q12>" or "#<Q12>" with any amount of whitespace
    val = token.value.strip()
    return bool(re.match(r"^#[ \t]*<Q[0-9]+>$", val))

def clean_all_q_comments(data):
    """Recursively removes all <Q#> comments from a ruamel.yaml data structure."""
    if hasattr(data, 'ca'):
        # 1. Clean object-level comments (pre/post)
        if data.ca.comment:
            for c_idx in range(len(data.ca.comment)):
                if isinstance(data.ca.comment[c_idx], list):
                    data.ca.comment[c_idx] = [t for t in data.ca.comment[c_idx] if not is_q_comment(t)]
        
        # 2. Clean end comments
        if hasattr(data.ca, 'end') and data.ca.end:
            data.ca.end = [t for t in data.ca.end if not is_q_comment(t)]
            
        # 3. Clean item-level comments
        if data.ca.items:
            for k in data.ca.items:
                comm_list_list = data.ca.items[k]
                if comm_list_list:
                    for c_idx in range(len(comm_list_list)):
                        if isinstance(comm_list_list[c_idx], list):
                            comm_list_list[c_idx] = [t for t in comm_list_list[c_idx] if not is_q_comment(t)]
                        elif is_q_comment(comm_list_list[c_idx]):
                            comm_list_list[c_idx] = None

    # Recursive step and choices literal conversion
    if isinstance(data, dict):
        for k, v in data.items():
            # Special rule: convert all choices values to long strings (literal scalars)
            if k == 'choices' and isinstance(v, list):
                for choice_item in v:
                    if isinstance(choice_item, dict):
                        for ck in choice_item:
                            val = str(choice_item[ck]).strip()
                            if val:
                                choice_item[ck] = LiteralScalarString(val + "\n")
            clean_all_q_comments(v)
    elif isinstance(data, list):
        for item in data:
            clean_all_q_comments(item)

def format_yaml(args):
    yaml_path = Path(args.yaml_filename)
    if not yaml_path.exists():
        raise QuizMLError(f"File not found: {yaml_path}")
    
    txt = yaml_path.read_text()
    
    # Split documents by ---
    yamldoc_pattern = re.compile(r"^---\s*$", re.MULTILINE)
    parts = yamldoc_pattern.split(txt)
    
    yaml = YAML()
    yaml.indent(mapping=2, sequence=2, offset=0)
    yaml.width = 80
    yaml.preserve_quotes = True
    
    formatted_parts = []
    dummy_mark = StreamMark(None, 0, 0, 0)
    
    for part in parts:
        if not part.strip():
            formatted_parts.append("")
            continue
            
        data = yaml.load(part)
        
        # Aggressive cleaning and choices literal conversion
        clean_all_q_comments(data)

        # Renumber questions if this part is a list
        if isinstance(data, list):
            for q_idx, item in enumerate(data):
                q_num = q_idx + 1
                new_comment = f"# <Q{q_num}>\n"
                
                if q_idx not in data.ca.items:
                    data.ca.items[q_idx] = [None, [], None, None]
                
                if data.ca.items[q_idx][1] is None:
                    data.ca.items[q_idx][1] = []
                
                # Append so it stays right before the hyphen line
                data.ca.items[q_idx][1].append(CommentToken(new_comment, dummy_mark, None, 0))
        
        buf = io.StringIO()
        yaml.dump(data, buf)
        formatted_parts.append(buf.getvalue().strip())

    # Re-join documents
    actual_docs = [part for part in formatted_parts if part.strip()]
    res = ""
    if txt.startswith("---"):
        res += "---\n"
    res += "---\n".join(doc + "\n" for doc in actual_docs)

    # Convert to "- # <Q#>" convention
    res = re.sub(r"^[ ]*(# <Q[0-9]+>)\n- ", r"- \1\n  ", res, flags=re.MULTILINE)
    
    if res != txt:
        yaml_path.write_text(res)
        print(f"Formatted and renumbered {yaml_path}")
    else:
        print(f"No changes made to {yaml_path}")
