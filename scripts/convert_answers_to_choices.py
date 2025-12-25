
import strictyaml as styml
import rich

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

import sys
from pathlib import Path
import re

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

# ryml.indent(mapping=4, sequence=6, offset=3)

# b = ryml.indent(mapping=4, sequence=6, offset=3)
# ryml.dump(d, sys.stdout)


# print(ryml.indent(mapping=4, sequence=6, offset=3))

from strictyaml import YAML
from strictyaml.ruamel.comments import CommentedSeq
from strictyaml.ruamel.comments import CommentedMap
from strictyaml.ruamel.comments import Comment
from strictyaml.ruamel.tokens import CommentToken
from strictyaml.ruamel.error import CommentMark

from strictyaml.yamllocation import YAMLChunk

from strictyaml.ruamel.compat import ordereddict

# def fil(data):
#     print(type(data._value))
#     if isinstance(data._value, CommentedSeq):
#         print("YEAH")
#         seq = CommentedSeq() #data._value
#         for a in data._value:
#             seq.extend(a)
#         new_data = YAML(YAMLChunk(seq))
# #        print(new_data)
# #        print(data)

#     else:
#         new_data = data
#     return new_data

# from collections import OrderedDict

# def sensible_comment_breaks(data, carry):
#     if isinstance(data, CommentedSeq):
#         for a in len(data):
#             carry = sensible_comment_breaks(a, carry)
           
#     elif isinstance(data, CommentedMap):
            
#     return follow
    

# e = yml.as_marked_up()
# e_ = e[0];
# answers = e[0]['answers']
# del e_['answers']
# e_['choices'] = answers
# e[0] = e_

# print("------")
# print(YAML(e).as_yaml())


# def swapkey(e, oldkey, newkey):
#     e['newkey'] = e['oldkey']
#     del e['oldkey']
#     return e

import textwrap

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
            
        
# ryml = yml.as_marked_up()

# wrap80(ryml)


# print(styml.YAML(ryml).as_yaml())


# txt = """

# Something is great in the whole wide word with a lot of
# equations. Something is great in the whole wide word with a lot of
# equations. Something is great in the whole wide word with a lot of
# equations. Something is great in the whole wide word with a lot of
# equations.

# $$
# S(t) = \int_t S(t)^2 dt
# $$

# """

# print(textwrap.fill(
#     txt, width=50,
#     expand_tabs=True,
#     replace_whitespace=False,
#     fix_sentence_endings=False,
#     break_long_words=True,
#     drop_whitespace=False,
#     break_on_hyphens=True,
#     tabsize=2))

# exit()


#print(ryml)

header = None

for i, q in enumerate(ryml):
    if (q['type'] == 'ma' or q['type'] == 'mc') and ('answers' in q):
        choices = q['answers']        
        for j, a in enumerate(choices):
            cor = 'x' if a['correct'].lower()=="true" else "o"
            a.ca.items[cor] = [None, None, None, None]
            for k in range(4):
                if 'correct' in a.ca.items:
                    if a.ca.items[cor][k] is None:
                        a.ca.items[cor][k] = a.ca.items['correct'][k]
                if 'answer' in a.ca.items:
                    if a.ca.items[cor][k] is None:
                        a.ca.items[cor][k] = a.ca.items['answer'][k]
            a[cor] = a['answer']

            del a['answer']
            del a['correct']
            if 'answer' in a.ca.items:
                del a.ca.items['answer']
            if 'correct' in a.ca.items:
                del a.ca.items['correct']
            choices[j] = a
        del ryml[i]['answers']            
        ryml[i]['choices'] = choices
        if 'answers' in ryml[i].ca.items:
            ryml[i].ca.items['choices'] = ryml[i].ca.items['answers']
            del ryml[i].ca.items['answers']

    if q['type'] == 'matching' and 'answers' in q:
        choices = q['answers']        
        for j, a in enumerate(choices):
            cor = a['correct']
            ans = a['answer']
            a['A'] = ans
            a['B'] = cor
            del a['answer']
            del a['correct']
            if 'answer' in a.ca.items:
                a.ca.items['A'] = a.ca.items['answer']
                del a.ca.items['answer']
            if 'correct' in a.ca.items:
                a.ca.items['B'] = a.ca.items['correct']
                del a.ca.items['correct']

        del ryml[i]['answers']            
        ryml[i]['choices'] = choices
        if 'answers' in ryml[i].ca.items:
            ryml[i].ca.items['choices'] = ryml[i].ca.items['answers']
            del ryml[i].ca.items['answers']
           
                
    if q['type'] == 'header':
        header = q
        header_index = i # should really be 0
        #        print(ryml.ca)

        if header.ca.comment is None:
            header.ca.comment = [None, []]

        if ryml.ca.comment:
            header.ca.comment[1] = ryml.ca.comment[1]
            ryml.ca.comment[1] = []
                       
        # if 'type' in header.ca.items:            
        #     print(header.ca.items)
        #     #            header.ca.items['type'] = ryml[i].ca.items['answers']
        #     del ryml[i].ca.items['answers']

        del header['type']


# print(yaml_txt)
# print("======================================")   
        
# if header:
#     del ryml[header_index]    
#     print(styml.YAML(header).as_yaml())  
#     print("---")

# ryml.ca.comment = [None, [CommentToken('\n\n\n# <Q1>\n', CommentMark(0), None)]]

print(ryml.ca)

for i, a in enumerate(ryml):
    if a.ca.comment is None:
        a.ca.comment = [None, [CommentToken(f'\n\n\n# <Q{i+1}>\n', CommentMark(0), None)]]
#    else:
#        print("xxx")

outtext = str(styml.YAML(ryml).as_yaml())
import re
outtext = re.sub(r'(\s*\n){4,}', '\n\n\n', outtext)
outtext = outtext.strip()

print(outtext)

# new_yaml_txt = str(YAML(ryml).as_yaml())

# new_yml = styml.load(new_yaml_txt, schema=styml.Any())


# print(new_yml.as_yaml())
# print(new_yml.data)

# a = yml[0]['answers'][0]
# a._value.insert(key='papa-true', value="something", pos=100)
# yml[0]['answers'][0] = a

# print(yml.as_yaml())

# seq = {"key": "something"}
# new_data = YAML(seq)
# print(new_data.as_yaml())

# from collections import OrderedDict
#from strictyaml.ruamel.compat import ordereddict

# print(yml[0])

# for i, e in enumerate(yml):
#     if 'answers' in e:   
#         new_e = ordereddict();
#         # print("----")
#         for k, v in e.items():
#             k_ = k;
#             # if (k._value == "answers"):
#             #     k_  = styml.as_document("choices")
#             #     print(k_)
#             new_e[k_] = v;      
#             # print(new_e)

#         # print(new_e)
#         # print(e)
#         print(type(e))
#         print(type(new_e))
            
#         yml[i] = new_e # styml.as_document(new_e)
            
#            print(t)
#             for key, value in e.items():
#                 OrderedDict(('choices' if k == 'answers' else k, v) for k, v in e.items())

#                 if key == 'answers':
#                     print(e)
#                     for a in e['answers']:
#                         print(a)
#                         if a['correct'] == 'true':
#                             n = {'true' : a['answer'].as_yaml()}
#                         else:
#                             n = {'false' : a['answer'].as_yaml()}
                    
#                         print(styml.as_document(n).as_yaml())                        
# #                        print(a.as_yaml()) 
#                         print("-------")
# #                        print(a.as_yaml())
# #                        
# print("here")
# print(yml.as_yaml())
                    
# #    else:
#  #       print(e.lines())
        
#print(yml.as_yaml())


 
