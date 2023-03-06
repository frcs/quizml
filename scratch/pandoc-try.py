import pandoc

text = """
In this paper we consider the case where $\\frac{1}{2}\\int_x \\cos(x) dx = \\phi$

This is an intersting problem, \\textit{with}:

* massive issues
* something cool
* an equation with somelike:
\\[
Badiblablabadibla
\\]

An an image below:
![](test.png){width=30em}


"""

# for i in range(100):
doc = pandoc.read(text * 1000)

print(doc)

