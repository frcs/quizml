# Markdown and equations <!-- {docsify-ignore} -->

Question text, choices, answers, feedback, and ordinary header values use
Markdown. QuizML converts these fields according to each target's
`markdown` configuration. Underscore-prefixed header keys are reserved for
QuizML controls or raw template values and are not transcoded as Markdown.

## Markdown formatting

QuizML supports CommonMark syntax, including emphasis, links, lists, inline
code, fenced code blocks, tables, and images:

```markdown
Use **bold**, *italic*, or `inline code`.

1. First step
2. Second step

![](figures/bee.jpg){width=30em}
```

Images use standard Markdown syntax with an optional `{width=...}` attribute.
Paths are resolved relative to the quiz file (or the included file where the
question is defined) and any directories listed in `_figures_path`.

Supported image formats depend on the output target:
- **HTML, QTI, Moodle, and Word**: PNG, JPEG, and SVG (embedded as Base64 data URIs in HTML, packaged into the ZIP archive in QTI, or inserted as OpenXML drawings in Word).
- **LaTeX / PDF**: PDF, PNG, and JPEG. When a question references an `.svg` image, QuizML automatically uses a matching `.pdf`/`.png`/`.jpg` sibling if present, or converts the SVG using a configured `svg_converter` tool.

## Equations

Use `$...$` or `\(...\)` for inline math and `$$...$$`, `\[...\]`, or a LaTeX
math environment for display math. Place display math delimiters or environment
boundaries on their own lines:

```markdown
The energy is $E = mc^2$.

$$
E = mc^2
$$

\begin{align*}
2x - 5y &= 8 \\
3x + 9y &= -12
\end{align*}
```

Custom LaTeX macros (`\newcommand`, `\DeclareMathOperator`, etc.) defined in the
target's `html_pre` file (`math-preamble.tex` by default) or in the quiz
header's `_latexpreamble` are available across all equation backends—including
pure-Python MathML and Word Office Math (`OMML`) as well as LaTeX/SVG/PNG
renders.

See [Targets](targets.md) for configuring `markdown.format` and `markdown.math`.
