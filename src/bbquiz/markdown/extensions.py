import re
import mistletoe
from mistletoe import Document, HTMLRenderer
from mistletoe.ast_renderer import ASTRenderer
from mistletoe.latex_token import Math
from mistletoe import span_token
from mistletoe.span_token import Image
from mistletoe.span_token import tokenize_inner
from mistletoe.span_token import SpanToken


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
        if match.group(3):
            self.content = match.group(3)
        else:
            self.content = match.group(4)


            
class MathDisplay(SpanToken):
    content = ''
    parse_group = 1
    parse_inner = False
#    precedence = 6    
    pattern = re.compile(r"""
	(?<!\\)    # negative look-behind to make sure start is not escaped 
	(?:        # start non-capture group for all possible match starts
	  # group 1, match dollar signs only 
	  # single or double dollar sign enforced by look-arounds
	  ((?<!\$)\${2}(?!\$))|
	  # group 2, match escaped bracket
	  (\\\[)|                 
	  # group 3, match begin equation
	  (\\begin\{equation\})
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
	  (.*)(?<!\\)
	  (?:
	    # if group 2 was start, escaped bracket is end
	    (?(2)\\\]|     
	    # else group 3 was start, match end equation
	    (?(3)\\end\{equation\})
            ))))
	""", re.MULTILINE | re.VERBOSE | re.DOTALL)
    def __init__(self, match):
        if match.group(4):
            self.content = match.group(4)
        else:
            self.content = match.group(5)
