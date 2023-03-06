from mistletoe import Document, HTMLRenderer


mdtext = """
In this paper we consider the case where $\frac{1}{2}\int_x \cos(x) dx = \phi$

This is an intersting problem, \textit{with}:

* massive issues
* something cool
* an equation with somelike:
\[
Badiblablabadibla
\]

"""


with HTMLRenderer() as renderer:     # or: `with HTMLRenderer(AnotherToken1, AnotherToken2) as renderer:`
    doc = Document(mdtext * 1000)           # parse the lines into AST
    rendered = renderer.render(doc)  # render the AST
   
    print(doc)


        
