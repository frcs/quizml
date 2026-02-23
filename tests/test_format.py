
import pytest
from pathlib import Path
from quizml.cli.cli import main
import sys
import os

def test_format_renumbering(tmp_path, monkeypatch):
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text("""---
title: Test
---
- # <Q10>
  type: ma
  question: Q1
- # <Q5>
  type: ma
  question: Q2
""")
    
    monkeypatch.setattr(sys, "argv", ["quizml", "--format", str(yaml_file)])
    main()
    
    new_txt = yaml_file.read_text()
    assert "- # <Q1>" in new_txt
    assert "- # <Q2>" in new_txt
    assert "# <Q10>" not in new_txt
    assert "# <Q5>" not in new_txt

def test_format_idempotence(tmp_path, monkeypatch):
    yaml_file = tmp_path / "test_idem.yaml"
    yaml_file.write_text("""---
title: Test
---
- # <Q1>
  type: ma
""")
    
    monkeypatch.setattr(sys, "argv", ["quizml", "--format", str(yaml_file)])
    main()
    txt1 = yaml_file.read_text()
    main()
    txt2 = yaml_file.read_text()
    assert txt1 == txt2

def test_format_spurious_comments(tmp_path, monkeypatch):
    yaml_file = tmp_path / "test_spurious.yaml"
    # Messy numbering in different places
    yaml_file.write_text("""---
title: Test
# <Q0>
---
# <Q12>
- # <Q15>
  type: ma
  question: Q1 # <Q99>
""")
    
    monkeypatch.setattr(sys, "argv", ["quizml", "--format", str(yaml_file)])
    main()
    
    new_txt = yaml_file.read_text()
    # Should only have exactly one <Q1>
    assert new_txt.count("<Q") == 1
    assert "- # <Q1>" in new_txt
    assert "<Q0>" not in new_txt
    assert "<Q12>" not in new_txt
    assert "<Q15>" not in new_txt
    assert "<Q99>" not in new_txt

def test_format_no_space_numbering(tmp_path, monkeypatch):
    yaml_file = tmp_path / "test_nospace.yaml"
    yaml_file.write_text("""
- #<Q10>
  type: ma
""")
    monkeypatch.setattr(sys, "argv", ["quizml", "--format", str(yaml_file)])
    main()
    new_txt = yaml_file.read_text()
    assert "- # <Q1>" in new_txt
    assert "<Q10>" not in new_txt

def test_format_choices_literal_and_indent(tmp_path, monkeypatch):
    yaml_file = tmp_path / "test_choices.yaml"
    yaml_file.write_text("""
- type: mc
  choices:
    - o: Short string
    - x: Another one
""")
    monkeypatch.setattr(sys, "argv", ["quizml", "--format", str(yaml_file)])
    main()
    
    new_txt = yaml_file.read_text()
    # Check for literal block scalar indicator '|' followed by indented text
    assert "o: |\n      Short string" in new_txt
    # Check for zero indent of choices list items relative to 'choices' key
    # '  choices:' followed by '  - o:'
    assert "  choices:\n  - o:" in new_txt
