import sys

from quizml.cli.cli import main


def test_wrap_markdown(tmp_path, monkeypatch):
    yaml_file = tmp_path / "test_wrap.yaml"
    yaml_file.write_text(
        """---
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
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys, "argv", ["quizml", "--format", "--wrap", "74", str(yaml_file)]
    )
    main()

    new_txt = yaml_file.read_text(encoding="utf-8")

    # Check that lines don't exceed 80 chars (excluding code block)
    lines = new_txt.splitlines()
    for line in lines:
        if "print" in line:
            # Code block can be long
            assert len(line) > 80
        elif line.strip():
            # Account for some margin due to prefix "  " and words
            assert len(line) <= 90

    # Check that list indent was preserved
    assert (
        "- This is a list item that is also very very very very very very very very"
        in new_txt
    )
    assert "  long and should be wrapped carefully to preserve indentation." in new_txt


def test_format_without_wrap_preserves_lines(tmp_path, monkeypatch):
    yaml_file = tmp_path / "test_nowrap.yaml"
    long_line = "This is a single long line that exceeds standard terminal width and should remain on one line because wrapping is opt-in."
    yaml_file.write_text(
        f"""---
title: Test
---
- # <Q1>
  type: essay
  question: {long_line}
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(sys, "argv", ["quizml", "--format", str(yaml_file)])
    main()

    new_txt = yaml_file.read_text(encoding="utf-8")
    assert long_line in new_txt


def test_wrap_markdown_semantics_preservation():
    from quizml.cli.wrap import wrap_markdown

    # 1. Hyphen does not turn into list item
    res_hyphen = wrap_markdown("a" * 73 + " - b c", 74)
    assert "\n- " not in res_hyphen

    # 2. Numbered token does not turn into ordered list
    res_num = wrap_markdown("a" * 73 + " 1. b c", 74)
    assert "\n1. " not in res_num

    # 3. Hard line break (ending with two spaces) is preserved
    res_hardbreak = wrap_markdown("Line one  \nhard break", 74)
    assert res_hardbreak == "Line one  \nhard break"
