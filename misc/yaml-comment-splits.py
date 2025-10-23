import strictyaml as styml
from strictyaml import YAML
from strictyaml.ruamel.comments import CommentedSeq
from strictyaml.ruamel.comments import CommentedMap
from strictyaml.ruamel.comments import Comment
from strictyaml.ruamel.tokens import CommentToken
from strictyaml.ruamel.error import CommentMark

from strictyaml.yamllocation import YAMLChunk

from strictyaml.ruamel.compat import ordereddict

import rich

yaml_txt = """
# something
# This should stay 1


# This should be with Q1

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
# out of question comment 4

- type: "MA"
  marks: 3.2
  # This should stay
  question: |
    Which of the following statements are correct? (mark all correct answers)
  cols: 1 # comment cols
  # weird 
  answers:
    - answer: foo is big
      correct: true
    - answer: foo is small
      correct: true
    - answer: foo is just right # comment 5
      correct: false

"""


yml = styml.load(yaml_txt, schema=styml.Any())
ryml = yml._chunk._ruamelparsed



def sensible_comment_breaks(data, carry):
    carry = None
    if isinstance(data, CommentedSeq):
        for a in len(data):
            carry = sensible_comment_breaks(a, carry)
           
            
    return carry
    



print(ryml.ca)
print(ryml[0].ca)
print(ryml[1].ca)



