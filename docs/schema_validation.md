# Schema validation <!-- {docsify-ignore} -->

QuizML validates every quiz against a [JSON Schema](https://json-schema.org/)
and uses the schema to coerce values into predictable Python types. Questions in
included files are validated at their point of definition so error messages
report the exact file and line number.

## Schema-driven type coercion

Standard YAML parsers implicitly convert unquoted scalars like `NO`, `on`, or
`3.10` into booleans or floats. QuizML avoids these pitfalls with a two-step
loading pipeline:

1. Every YAML scalar is initially parsed as a plain string.
2. Each string is coerced into its target type (`string`, `number`, `integer`,
   `boolean`, or `markdown`) according to the active JSON Schema.

For example, in a multiple-choice question where choices have `"type": "string"`,
an unquoted choice `- x: NO` remains the string `"NO"` instead of becoming
`False`. In a True/False question where `answer` has `"type": "boolean"`,
`answer: no` or `answer: false` is coerced to the boolean `False`.

The bundled schema rejects unknown question types and undeclared question
fields (`additionalProperties: false`), catching typos such as `mcq` or
`anwser` early.

## Extending the schema in `quizml.cfg` (`schema_extensions`)

To add custom metadata fields to questions or headers—or to define a new
question type—declare `schema_extensions` directly in `_quizml/quizml.cfg`
without copying the full schema file:

```yaml
schema_extensions:
  header_properties:
    semester:
      type: string
  question_properties:
    topic:
      type: string
    difficulty:
      type: integer
  question_types:
    code_review:
      properties:
        language:
          type: string
        snippet:
          type: string
          format: markdown
      required: [question, language, snippet]
```

Fields declared with `format: markdown` are automatically transcoded to HTML,
LaTeX, or Word OpenXML alongside built-in Markdown fields.

## Using a standalone schema file

If you need full control over the JSON Schema, copy the bundled `schema.json`
into `_quizml/` with `quizml init --schema` (see
[Project setup](configuration.md)), or point `schema_path:` in `quizml.cfg` (or
`_schema:` in a quiz header) to a custom `.json` or `.yaml` schema file:

```yaml
schema_path: my_custom_schema.json
```
