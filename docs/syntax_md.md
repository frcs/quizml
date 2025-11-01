
## Markdown Syntax <!-- {docsify-ignore} -->

All yaml entries, including the question statements and answers, will be
interpreted as Markdown (expect if key is prefixed with `_` as discussed in 
[header section](header)).

### Basic Markdown Syntax 

Text Tags can be found here:

https://commonmark.org/help/

````markdown
In this question we can use __bold__, *italic*.

images can be inserted this way: 

![](figures/bee.jpg)

You can defined lists this way:

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

BBQuiz implements the following Markdown extensions for integrating LaTeX
equations and images.

#### Images

We can set the image size as an attribute:

```
![](figures/bee.jpg){width=30em}

```

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





