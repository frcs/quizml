import json
from pathlib import Path

from quizml.utils import MarkdownString, coerce_data


def test_builtin_schema_conditions_refs_and_nested_coercion():
    schema_path = (
        Path(__file__).parents[1] / "src" / "quizml" / "templates" / "schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    document = {
        "questions": [
            {"type": "tf", "question": "Is this true?", "answer": "no"},
            {
                "type": "mfill",
                "question": "Fill the gaps",
                "answers": {"one": ["1", "2"]},
            },
        ]
    }

    result = coerce_data(document, schema)

    assert isinstance(result["questions"][0]["question"], MarkdownString)
    assert result["questions"][0]["answer"] is False
    assert result["questions"][1]["answers"] == {"one": ["1", "2"]}


def test_anyof_applies_every_matching_branch():
    schema = {
        "type": "array",
        "items": {
            "anyOf": [
                {"properties": {"enabled": {"type": "boolean"}}},
                {"properties": {"count": {"type": "integer"}}},
            ]
        },
    }

    result = coerce_data(
        {"questions": [{"enabled": "yes", "count": "3"}]}, schema
    )

    assert result["questions"] == [{"enabled": True, "count": 3}]


def test_allof_applies_every_matching_conditional_branch():
    schema = {
        "type": "array",
        "items": {
            "allOf": [
                {
                    "if": {"properties": {"kind": {"const": "example"}}},
                    "then": {"properties": {"enabled": {"type": "boolean"}}},
                },
                {
                    "if": {"properties": {"kind": {"const": "example"}}},
                    "then": {"properties": {"count": {"type": "integer"}}},
                },
            ]
        },
    }

    result = coerce_data(
        {"questions": [{"kind": "example", "enabled": "yes", "count": "3"}]},
        schema,
    )

    assert result["questions"] == [
        {"kind": "example", "enabled": True, "count": 3}
    ]


def test_oneof_applies_only_its_unique_matching_branch():
    schema = {
        "type": "array",
        "items": {
            "oneOf": [
                {
                    "properties": {
                        "kind": {"const": "count"},
                        "value": {"type": "integer"},
                    },
                    "required": ["kind", "value"],
                },
                {
                    "properties": {
                        "kind": {"const": "enabled"},
                        "value": {"type": "boolean"},
                    },
                    "required": ["kind", "value"],
                },
            ]
        },
    }

    result = coerce_data(
        {"questions": [{"kind": "enabled", "value": "off"}]}, schema
    )

    assert result["questions"] == [{"kind": "enabled", "value": False}]


def test_pattern_properties_apply_to_matching_keys():
    schema = {
        "type": "array",
        "items": {
            "properties": {"fixed": {"type": "integer"}},
            "patternProperties": {"^count_": {"type": "integer"}},
            "additionalProperties": {"type": "boolean"},
        },
    }

    result = coerce_data(
        {
            "questions": [
                {"fixed": "1", "count_items": "2", "other": "yes"}
            ]
        },
        schema,
    )

    assert result["questions"] == [
        {"fixed": 1, "count_items": 2, "other": True}
    ]
