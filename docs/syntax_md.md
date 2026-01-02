
## Markdown Syntax <!-- {docsify-ignore} -->

All yaml entries, including the question statements and answers, will be
interpreted as Markdown (except if key is prefixed with `_` as discussed in 
[header section](header)).

### Basic Markdown Syntax 

Text Tags can be found here:

https://commonmark.org/help/

````markdown
In this question we can use __bold__, *italic*.

images can be inserted this way: 

![](figures/bee.jpg)

You can define lists this way:

* List
* List
* List

or like this: 

1. One
2. Two
3. Three

Code can be included inline `like this` or as a block:

```c
void main(int argc, char* argv[])
{
    return 0;
}
```
````



### Markdown Extensions

QuizML implements the following Markdown extensions for integrating LaTeX
equations and images.

#### Images

Images can be included using standard Markdown syntax. We can also set the image size as an attribute:

```
![](figures/bee.jpg){width=30em}
```

**Supported Formats:**
* **HTML:** Supports all standard web formats (JPG, PNG, SVG, GIF, etc.).
* **LaTeX:** Supports PDF, PNG, and JPG.

**Automatic Fallback for LaTeX:**
If you use an `.svg` image in your Markdown, QuizML attempts to handle it gracefully for LaTeX output:
1.  It first checks if a `.pdf`, `.png`, or `.jpg` version of the same image exists (e.g., `figures/bee.png`).
2.  If found, it uses that file instead.
3.  If not found, and if tools like `rsvg-convert` or `inkscape` are installed, it attempts to convert the `.svg` to `.pdf` automatically.

This means you can use SVG for high-quality web previews while keeping a PNG copy for LaTeX compatibility without needing extra tools.

#### LaTeX

You can use inline LaTeX expressions using both `$`, and `\(`, `\)`
delimiters and also display equations with `$$` but also `\[`, but also the
following environments `equation`, `split` `alignat` `multline` `gather` `align`
`flalign`:


```
this can be done inline with $sin(x)$, \(t\) or as a display equation:

$$
	E(w) = \int_x \sin(x^2w) dx
$$

\begin{align*} 
2x - 5y &=  8 \\ 
3x + 9y &=  -12
\end{align*}
```

Note that for display equations, these must treated as blocks, with delimiters
(eg. `\begin{align*}` and `\end{align*}`) being alone on their line. For
instance, this wouldn't work:

```
We can't have this inline \begin{equation} A = B + C \end{equation} 
```
Instead you will need to do this:

```
We can have this:
\begin{equation} 
A = B + C 
\end{equation} 
```





