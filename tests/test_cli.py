
import pytest
from unittest.mock import patch, MagicMock
import sys
from quizml.cli.cli import main
from quizml.exceptions import QuizMLError

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
