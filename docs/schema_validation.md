## Custom Schema Validation

QuizML uses a powerful schema validation system to ensure that your quiz files
are structured correctly. This not only catches errors but also provides a
robust and predictable way of interpreting your data, avoiding common YAML
pitfalls.

This system is built upon the `jsonschema` library (see
[here](https://json-schema.org/)), and you can leverage it to create your own
custom question types or modify existing ones.

### The "Norway Problem": A Common YAML Pitfall

One of the most well-known issues with YAML is its aggressive implicit
typing. For example, if you have a field for a country code:

```yaml
- type: mc
  question: What is the country code for Norway?
  choices:
    - o: SW
    - o: DK
    - x: NO
```

A standard YAML parser will see `NO` and automatically convert it to the boolean
value `False`. This is often not the desired behavior and can lead to silent
bugs. This is known as the "Norway Problem".

### The QuizML Solution: Schema-Driven Parsing

QuizML solves this problem with a two-stage loading process that prioritises
your declared intent over YAML's guesswork.

#### Stage 1: Load Everything as Strings

First, QuizML reads your YAML file but deliberately ignores all of YAML's
automatic typing. Every scalar value—be it `NO`, `true`, `5`, or `3.14`—is
initially loaded as a plain string.

#### Stage 2: Coerce Types Based on the Schema

Next, QuizML uses a JSON schema file (by default, the `schema.json` file in your
default templates/config directory) to intelligently convert those strings into
the correct data types. The schema acts as the single source of truth for what
each field should be.

Let's revisit the "Norway problem" example. The default `schema.json` specifies
that multiple-choice answers (`o` and `x`) should be strings:

```json
// from schema.json, for "mc" type questions
"choices": {
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "x": { "type": "string" },
      "o": { "type": "string" }
    }
  }
}
```

Because the schema for `x` is `"type": "string"`, QuizML ensures that the value
`"NO"` remains a string.

However, for a true/false question type, the schema specifies the answer should
be a boolean:

```json
// from schema.json, for "tf" type questions
"answer": { "type": ["boolean", "string"] }
```

In this case, if your YAML is `answer: no`, it will be correctly coerced into
the boolean `False`. This approach gives you full control and predictability.

### Using a Custom Schema

You can extend QuizML by providing your own schema. This is useful for:
- Defining entirely new question types.
- Adding custom fields to existing types.
- Changing the data types of existing fields.

You can specify a path to your custom schema in your `quizml.cfg` file:

```yaml
schema_path: my_custom_schema.json
```

When you compile with `quizml`, it will use your new schema for validation.

For example, if you wanted to create a new question type `geolocation` that
requires numeric latitude and longitude, you could add this to your custom
schema's `allOf` array:

```json
{
  "if": { "properties": { "type": { "const": "geolocation" } } },
  "then": {
    "properties": {
      "type": { "type": "string" },
      "marks": { "type": ["number", "string"], "default": "2.5" },        
      "question": { "type": "string" },
      "latitude": { "type": "number" },
      "longitude": { "type": "number" }
    },
    "required": ["question", "latitude", "longitude"]
  }
}
```

With this schema, QuizML will now recognize the `geolocation` type and ensure
that `latitude` and `longitude` are treated as numbers.
