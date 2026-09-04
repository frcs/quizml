
import sys
from unittest.mock import patch

import pytest

from quizml.cli.cli import main


@patch('quizml.cli.ui.print_target_list')
def test_target_list(mock_print_target_list):
    with patch.object(sys, 'argv', ['quizml', '--target-list']):
        main()
    mock_print_target_list.assert_called_once()

@patch('quizml.cli.cleanup.cleanup_yaml_files')
def test_cleanup(mock_cleanup):
    with patch.object(sys, 'argv', ['quizml', '--cleanup']):
        main()
    mock_cleanup.assert_called_once()


def test_cleanup_safety(tmp_path):
    from quizml.cli.cleanup import cleanup_yaml_files

    # Create exam yaml
    exam_yaml = tmp_path / "exam.yaml"
    exam_yaml.write_text("title: Test\n---\n[]")

    # Target outputs and artifacts that SHOULD be cleaned up
    targets_to_clean = [
        tmp_path / "exam.txt",
        tmp_path / "exam.html",
        tmp_path / "exam.tex",
        tmp_path / "exam.solutions.tex",
        tmp_path / "exam.pdf",
        tmp_path / "exam.solutions.pdf",
        tmp_path / "exam.aux",
        tmp_path / "exam.solutions.aux",
        tmp_path / "exam.log",
        tmp_path / "exam.synctex.gz",
        tmp_path / "exam.docx",
    ]
    for p in targets_to_clean:
        p.write_text("generated artifact")

    # Non-target files that MUST NOT be cleaned up
    safe_files = [
        tmp_path / "exam.py",
        tmp_path / "exam.md",
        tmp_path / "exam.png",
        tmp_path / "other_notes.txt",
        exam_yaml,
    ]
    for p in safe_files:
        if not p.exists():
            p.write_text("precious authored file")

    deleted_count = cleanup_yaml_files(str(tmp_path))

    # Verify all targets/artifacts were deleted
    assert deleted_count == len(targets_to_clean)
    for p in targets_to_clean:
        assert not p.exists(), f"Expected {p.name} to be deleted"

    # Verify all safe files are untouched
    for p in safe_files:
        assert p.exists(), f"Expected {p.name} to be preserved"


def test_cleanup_specific_target_stem(tmp_path):
    from quizml.cli.cleanup import cleanup_yaml_files

    # Create two exams and their artifacts
    (tmp_path / "exam1.html").write_text("artifact")
    (tmp_path / "exam2.html").write_text("artifact")

    # Only clean exam1
    deleted_count = cleanup_yaml_files(str(tmp_path), target_stems={"exam1"})

    assert deleted_count == 1
    assert not (tmp_path / "exam1.html").exists()
    assert (tmp_path / "exam2.html").exists()


@patch('quizml.cli.init.init_local')
def test_init_local(mock_init_local):
    with patch.object(sys, 'argv', ['quizml', '--init-local']):
        main()
    mock_init_local.assert_called_once()

@patch('quizml.cli.init.init_user')
def test_init_user(mock_init_user):
    with patch.object(sys, 'argv', ['quizml', '--init-user']):
        main()
    mock_init_user.assert_called_once()

@patch('sys.stdout.write')
def test_shell_completion(mock_write):
    with patch.object(sys, 'argv', ['quizml', '--shell-completion', 'bash']):
        main()
    mock_write.assert_called()

def test_missing_yaml_file(capsys):
    with patch.object(sys, 'argv', ['quizml']):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 2 # argparse error code

@patch('quizml.cli.compile.compile')
def test_compile_default(mock_compile):
    with patch.object(sys, 'argv', ['quizml', 'test.yaml']):
        main()
    mock_compile.assert_called_once()

@patch('quizml.cli.diff.diff')
def test_diff_command(mock_diff):
    with patch.object(sys, 'argv', ['quizml', '--diff', 'test1.yaml', 'test2.yaml']):
        main()
    mock_diff.assert_called_once()


def test_diff_execution(tmp_path, capsys):
    f1 = tmp_path / "quiz1.yaml"
    f2 = tmp_path / "quiz2.yaml"
    content = """
- type: tf
  marks: 2.5
  question: Is this a test question?
  answer: true
"""
    f1.write_text(content)
    f2.write_text(content)

    with patch.object(sys, 'argv', ['quizml', '--diff', str(f1), str(f2)]):
        main()

    captured = capsys.readouterr()
    assert "Is this a test question?" in captured.out
    assert "tf" in captured.out

def test_version(capsys):
    with patch.object(sys, 'argv', ['quizml', '--version']):
        with pytest.raises(SystemExit):
            main()
    # verify output contains version? argparse usually prints to stdout/stderr

def test_info_command(capsys):
    import json
    with patch.object(sys, 'argv', ['quizml', '--info']):
        try:
            main()
        except SystemExit:
            pass 
        
    captured = capsys.readouterr()
    output = captured.out
    
    # Check if output is valid JSON
    data = json.loads(output)
    
    expected_keys = [
        "version",
        "cwd",
        "local_templates",
        "user_config_dir",
        "user_templates",
        "package_templates",
        "search_paths",
        "config_file"
    ]
    
    for key in expected_keys:
        assert key in data
