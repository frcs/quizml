
import pytest
import os
from quizml.loader import load
from quizml.exceptions import QuizMLYamlSyntaxError

def test_incorrect_01():
    pkg_dirname = os.path.dirname(__file__)
    yaml_file = os.path.join(pkg_dirname, "fixtures", "test-incorrect-01.yaml")
    
    with pytest.raises(QuizMLYamlSyntaxError) as excinfo:
        load(yaml_file)
    
    # Check that the error message indicates a problem
    # The actual message depends on the schema and jsonschema version,
    # but it should mention the error.
    assert "YAML parsing error" in str(excinfo.value) or "Schema validation error" in str(excinfo.value)

def test_incorrect_02():
    pkg_dirname = os.path.dirname(__file__)
    yaml_file = os.path.join(pkg_dirname, "fixtures", "test-incorrect-02.yaml")
    
    with pytest.raises(QuizMLYamlSyntaxError) as excinfo:
        load(yaml_file)
        
    assert "YAML parsing error" in str(excinfo.value) or "Schema validation error" in str(excinfo.value)

def test_missing_file():
    with pytest.raises(QuizMLYamlSyntaxError) as excinfo:
        load("non_existent_file.yaml")
    assert "Yaml file not found" in str(excinfo.value)
