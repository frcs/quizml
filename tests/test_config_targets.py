import pytest
from unittest.mock import MagicMock, patch
import os
from quizml.cli.config import get_target_list

@pytest.fixture
def mock_dependencies():
    with patch('quizml.cli.config.filelocator.locate.path') as mock_path, \
         patch('pathlib.Path.read_text') as mock_read:
        mock_path.side_effect = lambda x: f"/abs/{x}"
        mock_read.return_value = "content"
        yield

def test_get_target_list_defaults(mock_dependencies):
    args = MagicMock()
    args.target = None
    args.yaml_filename = "test.yaml"
    
    config = {
        'yaml_filename': 'test.yaml',
        'default_targets': ['t1'],
        'targets': [
            {'name': 't1', 'template': 't1.jinja', 'descr': 'Target 1'},
            {'name': 't2', 'template': 't2.jinja', 'descr': 'Target 2'}
        ]
    }
    
    yaml_data = {'header': {}}
    
    targets = get_target_list(args, config, yaml_data)
    assert len(targets) == 1
    assert targets[0]['name'] == 't1'

def test_get_target_list_cli_override(mock_dependencies):
    args = MagicMock()
    args.target = ['t2']
    args.yaml_filename = "test.yaml"
    
    config = {
        'yaml_filename': 'test.yaml',
        'default_targets': ['t1'],
        'targets': [
            {'name': 't1', 'template': 't1.jinja', 'descr': 'Target 1'},
            {'name': 't2', 'template': 't2.jinja', 'descr': 'Target 2'}
        ]
    }
    
    yaml_data = {'header': {}}
    
    targets = get_target_list(args, config, yaml_data)
    assert len(targets) == 1
    assert targets[0]['name'] == 't2'

def test_get_target_list_no_defaults(mock_dependencies):
    args = MagicMock()
    args.target = None
    args.yaml_filename = "test.yaml"
    
    config = {
        'yaml_filename': 'test.yaml',
        'targets': [
            {'name': 't1', 'template': 't1.jinja', 'descr': 'Target 1'},
            {'name': 't2', 'template': 't2.jinja', 'descr': 'Target 2'}
        ]
    }
    
    yaml_data = {'header': {}}
    
    targets = get_target_list(args, config, yaml_data)
    assert len(targets) == 2
    names = sorted([t['name'] for t in targets])
    assert names == ['t1', 't2']

def test_get_target_list_defaults_with_dependencies(mock_dependencies):
    args = MagicMock()
    args.target = None
    args.yaml_filename = "test.yaml"
    
    # t1 depends on t2. If t1 is default, t2 should also be included (if logic permits, or just t1 is selected but deps are handled elsewhere? 
    # get_required_target_names_set handles dependencies recursively.
    
    config = {
        'yaml_filename': 'test.yaml',
        'default_targets': ['t1'],
        'targets': [
            {'name': 't1', 'template': 't1.jinja', 'descr': 'Target 1', 'dep': 't2'},
            {'name': 't2', 'template': 't2.jinja', 'descr': 'Target 2'}
        ]
    }
    
    yaml_data = {'header': {}}
    
    targets = get_target_list(args, config, yaml_data)
    # logic: get_required_target_names_set(['t1']) -> {'t1', 't2'}
    # So both should be returned.
    
    assert len(targets) == 2
    names = sorted([t['name'] for t in targets])
    assert names == ['t1', 't2']
