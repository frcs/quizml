import os

from quizml.quizmlyaml import load


def test_yaml_syntax():
    
    pkg_dirname = os.path.dirname(__file__)
    yaml_file = os.path.join(pkg_dirname, "fixtures", "test-basic-syntax.yaml")
    
    yamldata = [{"type": "essay",
                     "marks": 4.0,
                     "question": "answer this question",
                     "answer": "some very long answer",
                     },
                    {"type": "ma",
                     "marks": 2.5,
                     "question": "some multiple answer question",
                     "choices": [{"x": "A"},
                                 {"o": "B"},
                                 {"x": "C"},
                                 {"o": "D"}
                                 ],
                     "cols": 1},
                    {"type": "mc",
                     "marks": 2.5,
                     "question": "some multiple choice question",
                     "choices": [{"o": "A"},
                                 {"o": "B"},
                                 {"x": "C"},
                                 {"o": "D"}
                                 ],
                     "cols": 1},
                    {"type": "matching",
                     "marks": 2.5,
                     "question": "some matching question",
                     "choices": [{"A": "1", "B": "2"},
                                 {"A": "3", "B": "4"}
                                 ],
                     },
                    {"type": "ordering",
                     "marks": 2.5,
                     "question": "some ordering question",
                     "choices": ["A", "B", "C", "D"],
                     "cols": 1},
                    ]  
    yamldoc, _ = load(yaml_file)

    # Helper to strip strings recursively
    def strip_strings(data):
        if isinstance(data, dict):
            return {k: strip_strings(v) for k, v in data.items()}
        if isinstance(data, list):
            return [strip_strings(v) for v in data]
        if isinstance(data, str):
            return data.strip()
        return data

    assert strip_strings(yamldoc['questions']) == yamldata


def test_horizontal_rule_in_markdown_question():
    from quizml.quizmlyaml import loads

    quiz_yaml = """title: Math Quiz
---
- type: tf
  marks: 2.5
  question: |
    Section above divider
    ---
    Section below divider
  answer: true
"""
    doc, _ = loads(quiz_yaml, validate=False)
    assert doc["header"]["title"] == "Math Quiz"
    assert len(doc["questions"]) == 1
    q_text = doc["questions"][0]["question"]
    assert "Section above divider" in q_text
    assert "---" in q_text
    assert "Section below divider" in q_text


def test_unicode_yaml_loading(tmp_path):
    f = tmp_path / "unicode.yaml"
    content = """title: Math Quiz with Unicode € é à ü 數學 🚀
---
- type: tf
  marks: 2.5
  question: 'Is $e^{i\\pi} + 1 = 0$ vérité? €100'
  answer: true
"""
    f.write_text(content, encoding="utf-8")
    doc, _ = load(str(f), validate=False)
    assert "€" in doc["header"]["title"]
    assert "數學" in doc["header"]["title"]
    assert "vérité" in doc["questions"][0]["question"]
