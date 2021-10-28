import re
import mistletoe
from mistletoe import Document
from mistletoe.html_renderer import HTMLRenderer
from mistletoe.ast_renderer import ASTRenderer
from mistletoe.latex_token import Math
from mistletoe import span_token
from mistletoe.span_token import Image
from mistletoe.span_token import tokenize_inner
from mistletoe.span_token import SpanToken
from mistletoe.block_token import BlockToken
from mistletoe.block_token import ThematicBreak

   

class MathDisplay(BlockToken):
    pattern = re.compile(r"(\$\$|\\\[|\\begin\{(equation|split|alignat|multline|gather|align|flalign|)(\*?))")
    
    envname = ''
    envstart = ''
    latex = ''
    repr_attributes = ['latex']
    
    def __init__(self, lines):
        self.latex = ''.join([line.lstrip() for line in lines]).strip()
        
    @classmethod
    def start(cls, line):
        match_obj = cls.pattern.match(line.strip())
        if not match_obj:
            return False
        cls.envname = match_obj.group(2)
        cls.envstar = match_obj.group(3)
        cls.envstart = match_obj.group(1)
                
        return True

    @classmethod
    def read(cls, lines):
        line_buffer = [next(lines)]
        for line in lines:
            line_buffer.append(line)
            l = line.lstrip()
            if (cls.envstart == r'$$' and l.startswith(r'$$')):
                break               
            elif (cls.envstart == r'\[' and l.startswith(r'\]')):
                break               
            elif (cls.envname and l.startswith(r'\end{' + cls.envname + cls.envstar + '}')):
                break
        
        return line_buffer

    @classmethod
    def check_interrupts_paragraph(cls, lines):
        return cls.start(lines.peek())
    
    @property
    def content(self):
        """Returns the code block content."""
        return self.latex

    # def __repr__(self):
    #     output = "<{}.{}".format(
    #         self.__class__.__module__,
    #         self.__class__.__name__
    #     )
    #     output += " content=" + _short_repr(self.content)

    #     return output
    
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


            
# class MathDisplay(SpanToken):
#     content = ''
#     env = ''
#     parse_group = 1
#     parse_inner = False
# #    precedence =     
#     pattern = re.compile(r"""
#     (?<!\\)      # negative look-behind to make sure start is not escaped 
#     (?:          # start non-capture group for all possible match starts
#     ((?<!\$)\${2}(?!\$))| # group 1, match dollar signs only 
#     (\\\[)|               # group 2, \[
#     (\\begin\{(equation|split|alignat|multline|gather|align|flalign|)(\*?)\}) # group 3, all amsmath
#     )
#     (?(1)(.*?)(?<!\\)(?<!\$)\1(?!\$)|
#     (?(2)(.*?)(?<!\\)\\\]|
#     (?(3)(.*?)(?<!\\)\\end\{\4\5\}
#     )))
#     """, re.MULTILINE | re.VERBOSE | re.DOTALL)

#     # pattern = re.compile(r"(?<!\\)(?:((?<!\$)\${2}(?!\$))|(\\\[)|(\\begin\{(equation|split|alignat|multline|gather|align|flalign|)(\*?)\}))(?(1)(.*?)(?<!\\)(?<!\$)\1(?!\$)|(?(2)(.*?)(?<!\\)\\\]|(?(3)(.*?)(?<!\\)\\end\{\4\5\})))\n\n", re.MULTILINE | re.DOTALL)

    
# # pattern = re.compile(r"""
# # 	(?<!\\)    # negative look-behind to make sure start is not escaped 
# # 	(?:        # start non-capture group for all possible match starts
# # 	  # group 1, match dollar signs only 
# # 	  # single or double dollar sign enforced by look-arounds
# # 	  ((?<!\$)\${2}(?!\$))|
# # 	  # group 2, match escaped bracket
# # 	  (\\\[)|                 
# # 	  # group 3, match begin equation
# # 	  (\\begin\{equation\})
# # 	)
# # 	# if group 1 was start
# # 	(?(1)
# # 	  # non greedy match everything in between
# # 	  # group 1 matches do not support recursion
# # 	  (.*?)(?<!\\)
# # 	  # match ending double or single dollar signs
# # 	  (?<!\$)\1(?!\$)|  
# # 	# else
# # 	(?:
# # 	  # greedily and recursively match everything in between
# # 	  # groups 2, 3 and 4 support recursion
# # 	  (.*)(?<!\\)
# # 	  (?:
# # 	    # if group 2 was start, escaped bracket is end
# # 	    (?(2)\\\]|     
# # 	    # else group 3 was start, match end equation
# # 	    (?(3)\\end\{equation\})
# #             ))))
# # 	""", re.MULTILINE | re.VERBOSE | re.DOTALL)
#     def __init__(self, match):

#         self.content = match.group(0)
        
        
#         # # if match.group()
#         # if match.group(6):
#         #     self.content = match.group(0)
#         #     self.env = 'equation*'            
#         # if match.group(7):
#         #     self.content = match.group(7)
#         #     self.env = 'equation*'
#         # else:
#         #     self.content = match.group(0)
#         #     print(self.content)
#         #     self.env = match.group(4) + match.group(5)
            


