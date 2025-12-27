import sys
from pathlib import Path
import os
import pytest

from quizml.loader import load
from quizml.markdown.markdown import MarkdownTranscoder

def test_markdown_transcoding_html():
    pkg_dirname = os.path.dirname(__file__)
    yaml_file = os.path.join(pkg_dirname, "fixtures", "test-markdown.yaml")
    
    yamldoc = load(yaml_file, validate=False)
    transcoder = MarkdownTranscoder(yamldoc)
    
    # Test HTML conversion
    html_md_dict = transcoder.get_dict(opts={'fmt': 'html'})
    
    # Check if we have expected keys (the original markdown strings)
    # The keys in the dictionary are the original markdown strings prepended with "##Markdown##"
    # We need to find the keys corresponding to the question and choices.
    
    question_md = yamldoc['questions'][0]['question']
    key = question_md
    assert key in html_md_dict
    
    html_output = html_md_dict[key]
    
    # Check for HTML tags
    assert "<em>question</em>" in html_output # *question* -> <em>question</em>
    
    # Check for equation placeholders (converts to images or specific spans)
    # The exact format depends on the implementation, but we expect *something* different than raw latex
    # Based on existing code, it likely produces <img> tags for equations in HTML mode if configured, 
    # or keeps them as MathJax/Katex if not.
    # Looking at the code, it uses mistletoe. 
    
    # Let's check choices
    choice_0_md = yamldoc['questions'][0]['choices'][0]['x']
    key_c0 = choice_0_md
    assert key_c0 in html_md_dict
    assert "<img" in html_md_dict[key_c0] # Should convert ![pic] to <img ...>

def test_markdown_transcoding_latex():
    pkg_dirname = os.path.dirname(__file__)
    yaml_file = os.path.join(pkg_dirname, "fixtures", "test-markdown.yaml")
    
    yamldoc = load(yaml_file, validate=False)
    transcoder = MarkdownTranscoder(yamldoc)
    
    # Test LaTeX conversion
    latex_md_dict = transcoder.get_dict(opts={'fmt': 'latex'})
    
    question_md = yamldoc['questions'][0]['question']
    key = question_md
    assert key in latex_md_dict
    
    latex_output = latex_md_dict[key]
    
    # Check for LaTeX specific formatting
    assert r"\textit{question}" in latex_output # *question* -> \textit{question}
    
    # Check choices
    choice_0_md = yamldoc['questions'][0]['choices'][0]['x']
    key_c0 = choice_0_md
    assert key_c0 in latex_md_dict
    assert r"\includegraphics" in latex_md_dict[key_c0] # ![pic] -> \includegraphics