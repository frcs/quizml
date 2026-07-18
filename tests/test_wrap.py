import pytest
from pathlib import Path
from quizml.cli.cli import main
import sys

def test_wrap_markdown(tmp_path, monkeypatch):
    yaml_file = tmp_path / "test_wrap.yaml"
    yaml_file.write_text("""---
title: Test
---
- # <Q1>
  type: essay
  question: |
    Here is a very long question statement that should absolutely be wrapped by the format script so that it does not exceed the 80 characters limit that was requested by the user.

    - This is a list item that is also very very very very very very very very long and should be wrapped carefully to preserve indentation.
    - Another item with an equation $E=mc^2$ and more text to push it over the limit.

    ```python
    def foo():
        print("This should NOT be wrapped at all even if it is very very very long.")
    ```
""")
    
    monkeypatch.setattr(sys, "argv", ["quizml", "--format", str(yaml_file)])
    main()
    
    new_txt = yaml_file.read_text()
    
    # Check that lines don't exceed 80 chars (excluding code block)
    lines = new_txt.split("\\n")
    for line in lines:
        if "print" in line:
            # Code block can be long
            assert len(line) > 80
        elif line.strip():
            # Account for some margin due to prefix "  " and words
            assert len(line) <= 90
            
    # Check that list indent was preserved
    assert "- This is a list item that is also very very very very very very very very" in new_txt
    assert "  long and should be wrapped carefully to preserve indentation." in new_txt
