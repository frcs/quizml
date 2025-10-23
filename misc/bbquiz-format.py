
import strictyaml as styml
import rich

import sys
from pathlib import Path
import re

from strictyaml import YAML
from strictyaml.ruamel.comments import CommentedSeq
from strictyaml.ruamel.comments import CommentedMap
from strictyaml.ruamel.comments import Comment
from strictyaml.ruamel.tokens import CommentToken
from strictyaml.ruamel.error import CommentMark

from strictyaml.yamllocation import YAMLChunk

from strictyaml.ruamel.compat import ordereddict

import textwrap


yaml_txt = """
# something
# This should stay 1

# This should stay 2
- type: "MC"
  marks: 3.2
  # This should stay 2
  question: |
    Which of the following statements are correct? (mark all correct answers)
  cols: 1
  answers: # comment 0
    - answer: |       # comment 1a
        foo is big                # comment 1b
      correct: true               # comment 2
    - answer: foo is small        # comment 3
      correct: true
    - answer: foo is just right   # comment 4
      correct: false 

# out of question comment 1
# out of question comment 2
# out of question comment 3

- type: "MA"
  marks: 3.2
  # This should stay
  question: |
    Which of the following statements are correct? (mark all correct answers)
  cols: 1
  answers:
    - answer: foo is big
      correct: true
    - answer: foo is small
      correct: true
    - answer: foo is just right # comment 5
      correct: false

"""



yaml_txt = Path(sys.argv[1]).read_text()

yamldoc_pattern = re.compile(r"^---\s*$", re.MULTILINE) 
yamldocs = yamldoc_pattern.split(yaml_txt)    
yamldocs = list(filter(None, yamldocs))

if len(yamldocs) == 0:
    exit()    
elif len(yamldocs) == 1:
    yaml_txt = yamldocs[0]
    
else:
    print(yamldocs[0])
    yaml_txt = yamldocs[1]


yml = styml.load(yaml_txt, schema=styml.Any())

ryml = yml._chunk._ruamelparsed


def wrap80(data):
    if isinstance(data, CommentedSeq):
        for a in data:
            a = wrap80(a)
    elif isinstance(data, CommentedMap):
        for key, val in data.items():
            data[key] = wrap80(val)
    elif isinstance(data, str):
        data = textwrap.fill(data, width=50)
    else:
        print(type(data))
    return data


# if header:
#     del ryml[header_index]    
#     print(styml.YAML(header).as_yaml())  
#     print("---")

# ryml.ca.comment = [None, [CommentToken('\n\n\n# <Q1>\n', CommentMark(0), None)]]

print(ryml.ca)
print(ryml.items)

for i, a in enumerate(ryml):
    print(a)
    print(a.ca)
    if a.ca.comment is None:
        a.ca.comment = [None, [CommentToken(f'\n\n\n# <Q{i+1}>\n', CommentMark(0), None)]]
    else:
        print("XXXXXXXXXXXXXXXXXXXX")

outtext = str(styml.YAML(ryml).as_yaml())
import re
outtext = re.sub(r'(\s*\n){4,}', '\n\n\n', outtext)
outtext = outtext.strip()

#print(outtext)
