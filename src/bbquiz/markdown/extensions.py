import re
import mistletoe
from mistletoe import Document, HTMLRenderer
from mistletoe.ast_renderer import ASTRenderer
from mistletoe.latex_token import Math
from mistletoe import span_token
from mistletoe.span_token import Image
from mistletoe.span_token import tokenize_inner
from mistletoe.span_token import SpanToken
from mistletoe.block_token import BlockToken

# # no nesting        
# class Environment(BlockToken):
#     repr_attributes = ("env")

#     pattern = re.compile(r"\\begin{(.*?)}")
#     envname = ''

#     def __init__(self, lines):
#         content = ''.join([line.lstrip() for line in lines]).strip()
#         print("--")
#         print(content)
#         print("--")

#         super().__init__(content, span_token.tokenize_inner)
        
#     @classmethod
#     def start(cls, line):
#         print("here:'" + line.strip() + '\'')
#         print(cls.pattern)
#         match_obj = cls.pattern.match(line.strip())
#         print(match_obj)
#         if not match_obj:
#             return False
#         print("+++")
#         cls.envname = match_obj.group(1)        
#         return True

#     @classmethod
#     def read(cls, lines):
#         next(lines)
#         line_buffer = []
#         for line in lines:
#             if (line.startswith(r'\end{' + cls.envname + '}')):
#                 break
#             line_buffer.append(line)
#         return line_buffer

#     @property
#     def content(self):
#         """Returns the code block content."""
#         return self.children[0].content

# no nesting        
class Command(SpanToken):
    repr_attributes = ("cmdname", "cmd")
    parse_group = 2
    parse_inner = True
    pattern = re.compile(r"""
	\\([a-zA-Z]+?){\s*(.*?)\s*}""", re.MULTILINE | re.VERBOSE | re.DOTALL)
    def __init__(self, match):
        self.cmdname = match.group(1)
        self.cmd = match.group(2)

# no nesting        
class Environment(SpanToken):
    repr_attributes = ("envname", "cmd")
    parse_group = 2
    parse_inner = True
    pattern = re.compile(r"""
	\\begin{([a-zA-Z]+?)}{\s*(.*?)\s*}""", re.MULTILINE | re.VERBOSE | re.DOTALL)
    def __init__(self, match):
        self.cmdname = match.group(1)
        self.cmd = match.group(2)
        
class ImageWithWidth(SpanToken):
    content = ''
    src = ''
    title = ''
    width = ''

    parse_group = 1
    parse_inner = False
#    precedence = 6    
    pattern = re.compile(r"""
	!\[([^\]]*)\]\(([^\)]*)\)\{\s*width\s*=([^\}]*)\}
	""", re.MULTILINE | re.VERBOSE | re.DOTALL)
    def __init__(self, match):
        self.title = match.group(1)
        self.src = match.group(2)
        self.width = match.group(3)


class MathInline(SpanToken):
    content = ''
    parse_group = 1
    parse_inner = False
#    precedence = 6    
    pattern = re.compile(r"""
	(?<!\\)    # negative look-behind to make sure start is not escaped 
	(?:        # start non-capture group for all possible match starts
	  # group 1, match dollar signs only 
	  # single or double dollar sign enforced by look-arounds
	  ((?<!\$)\${1}(?!\$))|
	  # group 2, match escaped parenthesis
	  (\\\()
	)
	# if group 1 was start
	(?(1)
	  # non greedy match everything in between
	  # group 1 matches do not support recursion
	  (.*?)(?<!\\)
	  # match ending double or single dollar signs
	  (?<!\$)\1(?!\$)|  
	# else
	(?:
	  # greedily and recursively match everything in between
	  # groups 2, 3 and 4 support recursion
	  (.*)(?<!\\)\\\)
	))
	""", re.MULTILINE | re.VERBOSE | re.DOTALL)
    def __init__(self, match):
        self.content = match.group(0)        
        # if match.group(3):
        #     self.content = match.group(3)
        # else:
        #     self.content = match.group(4)


            
class MathDisplay(SpanToken):
    content = ''
    env = ''
    parse_group = 1
    parse_inner = False
#    precedence = 6    
    pattern = re.compile(r"""
    (?<!\\)      # negative look-behind to make sure start is not escaped 
    (?:          # start non-capture group for all possible match starts
    ((?<!\$)\${2}(?!\$))| # group 1, match dollar signs only 
    (\\\[)|               # group 2, \[
    (\\begin\{(equation|split|alignat|multline|gather|align|flalign|)(\*?)\}) # group 3, all amsmath
    )
    (?(1)(.*?)(?<!\\)(?<!\$)\1(?!\$)|
    (?(2)(.*?)(?<!\\)\\\]|
    (?(3)(.*?)(?<!\\)\\end\{\4\5\}
    )))
    """, re.MULTILINE | re.VERBOSE | re.DOTALL)
        
# pattern = re.compile(r"""
# 	(?<!\\)    # negative look-behind to make sure start is not escaped 
# 	(?:        # start non-capture group for all possible match starts
# 	  # group 1, match dollar signs only 
# 	  # single or double dollar sign enforced by look-arounds
# 	  ((?<!\$)\${2}(?!\$))|
# 	  # group 2, match escaped bracket
# 	  (\\\[)|                 
# 	  # group 3, match begin equation
# 	  (\\begin\{equation\})
# 	)
# 	# if group 1 was start
# 	(?(1)
# 	  # non greedy match everything in between
# 	  # group 1 matches do not support recursion
# 	  (.*?)(?<!\\)
# 	  # match ending double or single dollar signs
# 	  (?<!\$)\1(?!\$)|  
# 	# else
# 	(?:
# 	  # greedily and recursively match everything in between
# 	  # groups 2, 3 and 4 support recursion
# 	  (.*)(?<!\\)
# 	  (?:
# 	    # if group 2 was start, escaped bracket is end
# 	    (?(2)\\\]|     
# 	    # else group 3 was start, match end equation
# 	    (?(3)\\end\{equation\})
#             ))))
# 	""", re.MULTILINE | re.VERBOSE | re.DOTALL)
    def __init__(self, match):

        self.content = match.group(0)
        
        # # if match.group()
        # if match.group(6):
        #     self.content = match.group(0)
        #     self.env = 'equation*'            
        # if match.group(7):
        #     self.content = match.group(7)
        #     self.env = 'equation*'
        # else:
        #     self.content = match.group(0)
        #     print(self.content)
        #     self.env = match.group(4) + match.group(5)
            


