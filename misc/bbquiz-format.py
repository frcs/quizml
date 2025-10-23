# python3.8 bbquiz-format.py test-01.yaml | bat -l yaml



# import strictyaml as styml
import rich


import sys
from pathlib import Path
import re
from ruamel.yaml import YAML
from ruamel.yaml.tokens import CommentToken
from ruamel.yaml.error import CommentMark
import textwrap

def wrap80(value):
    return value;   

def format_questions(data, indent=0):
    output = ""
    if isinstance(data, dict):
        first = True
        for key, value in data.items():
            if not first:
                output += '  ' * indent
            first = False
            if isinstance(value, str) and '\n' in value:
                output += f"{key}: |\n"
                content = value.rstrip()
                if not key.startswith(('pre_', '_')):
                    lines = content.split('\n')
                    wrapped_lines = []
                    for line in lines:
                        if '\\' in line:
                            wrapped_lines.append(line)
                        else:
                            wrapped_lines.extend(textwrap.wrap(line, width=80))
                    content = '\n'.join(wrapped_lines)
                for line in content.split('\n'):
                    output += '  ' * (indent + 1) + line + '\n'
            elif isinstance(value, str):
                output += f"{key}: {value}\n"
            elif isinstance(value, int):
                output += f"{key}: {str(value)}\n"
            elif isinstance(value, float):
                output += f"{key}: {str(value)}\n"
            else:
                output += f"{key}: \n{format_questions(value, indent)}"
                
    elif isinstance(data, list):
        for item in data:
            output += '  ' * indent + "- "
            output += format_questions(item, indent + 1)
    else:
        print(str(data))
        output += str(data)
        
    return output


 
def format_yaml_file(filepath):
    yaml_txt = Path(filepath).read_text()

    # Remove spurious Q tags
    # yaml_txt = re.sub(r'# <Q\d+>', '', yaml_txt)

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=2, offset=0)
    data = list(yaml.load_all(yaml_txt))

    if not data:
        return

    header = None
    if len(data) > 1:
        header = data[0]
        questions = data[1]
    else:
        questions = data[0]

    print(questions.ca)
    print(questions)
        
    for i, question in enumerate(questions):
        
        if not hasattr(question, 'ca'):
            continue

        print(question.ca)
        
        if question.ca.comment is None:
            question.ca.comment = [None, []]
        
        if question.ca.comment[1]:
            print("AAAAA\nAAAAA")
            
            question.ca.comment[1] = [c for c in question.ca.comment[1] if not re.match(r'\s*# <Q\d+>', c.value)]

        question.ca.comment[1].insert(0, CommentToken(f'\n# <Q{i+1}>\n', CommentMark(0), None))


    yaml.dump(questions, sys.stdout)
    return
        
    from io import StringIO
    string_stream = StringIO()
    if header:
        yaml.dump(header, string_stream)
        string_stream.write('---\n')
    
    output = string_stream.getvalue()
    output += format_questions(questions)

    # Limit consecutive newlines
    output = re.sub(r'\n{3,}', '\n\n', output)

    print(output)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        format_yaml_file(sys.argv[1])
