# Question Types Syntax <!-- {docsify-ignore} -->

QuizML supports the question types listed below. Fields and accepted values are
validated by the [bundled schema](schema_validation.md).

## Common question fields

Every question requires `type` and `question` (except `part`, where `question`
is optional) and accepts these optional fields:

- `marks`: Point value for the question (defaults to `2.5`, or `4` for `essay`).
- `id`: Stable string identifier used for [cherry-picking (`select`), duplicate checking (`diff`), and pinning (`pin`)](module_workflow.md).
- `title`: Short question title used in LMS exports (QTI, Moodle) and previews.
- `feedback`: General Markdown feedback shown to students after submission.
- `comments`: Internal Markdown notes or grading rubrics (excluded from student views).
- `figure`, `figure-split`, `cols`: Optional [layout controls](question_layout.md).

### Essay

The student writes an open-ended response. The optional `answer` field provides
an indicative solution or grading guide.

```yaml
- type: essay
  marks: 14
  question: |
    Explain the difference between L1 and L2 regularization.
  answer: |
    L1 adds the sum of absolute weights (promoting sparsity); L2 adds the sum
    of squared weights.
```

### True/False

```yaml
- type: tf
  marks: 4
  question: |
    Earth orbits the Sun.
  answer: true
```

### Multiple Choice

Only one choice is correct. Mark the correct choice with `- x:` and incorrect
choices with `- o:`.

```yaml
- type: mc
  marks: 4
  question: |
    Which planet is known as the Red Planet?
  choices:
    - x: Mars
    - o: Venus
    - o: Jupiter
    - o: Saturn
```

### Multiple Answers

Same syntax as Multiple Choice, except that any number of choices can be marked
correct (`- x:`).

```yaml
- type: ma
  marks: 4
  question: |
    Select all prime numbers.
  choices:
    - x: 2
    - x: 3
    - o: 4
    - x: 5
```

### Matching

The student maps each prompt `A` to its corresponding match `B`.

```yaml
- type: matching
  marks: 5
  question: |
    Match the following trees to their typical height.
  choices:
    - A: Japanese Maple (Acer palmatum)
      B: 15–25 feet
    - A: Flowering Dogwood (Cornus florida)
      B: 30–40 feet
    - A: Coast Redwood (Sequoia sempervirens)
      B: 200–350+ feet
    - A: American Beech (Fagus grandifolia)
      B: 60–80 feet
```

### Fill in the Blank (`fill`)

Used for a single blank. The `answers` field lists acceptable correct strings.

```yaml
- type: fill
  marks: 5
  question: |
    The color of the sky on a clear day is _____.
  answers:
    - blue
    - Blue
    - cyan
```

### Fill in Multiple Blanks (`mfill`)

Maps placeholder variables (written in brackets `[ ]` in the question text) to
lists of acceptable answers.

```yaml
- type: mfill
  marks: 5
  question: |
    Roses are [color1] and violets are [color2].
  answers:
    color1:
      - red
      - Red
    color2:
      - blue
      - Blue
```

### Calculated Numeric (`num`)

Numeric answer with an optional `tolerance`.

```yaml
- type: num
  marks: 5
  question: |
    What is the value of $\pi$ to two decimal places?
  answer: 3.14
  tolerance: 0.01
```

### Ordering

The student ranks the items in `choices` into the correct sequence.

!> Blackboard Classic accepts Ordering rows, but Blackboard Ultra does not
support Ordering questions via text import (use `qti21` for Blackboard Ultra).

```yaml
- type: ordering
  marks: 5
  question: |
    Rank the following planets from closest to farthest from the Sun.
  choices:
    - Mercury
    - Venus
    - Earth
    - Mars
```

## Bundled template support

The table below summarizes which question types are supported by each bundled
target template:

| Type | Name | Blackboard (`bb`) | LaTeX / PDF | HTML preview | QTI (`qti`, `qti21`) | Moodle (`moodle`) | Word (`docx`) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `essay` | [Essay](#essay) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `tf` | [True/False](#true-false) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `mc` | [Multiple Choice](#multiple-choice) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `ma` | [Multiple Answers](#multiple-answers) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `matching` | [Matching](#matching) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `ordering` | [Ordering](#ordering) | ✅ (1) | ✅ | ✅ | ✅ | ✅ | ❌ |
| `fill` | [Fill in the Blank](#fill-in-the-blank-fill) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `mfill` | [Fill in Multiple Blanks](#fill-in-multiple-blanks-mfill) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `num` | [Calculated Numeric](#calculated-numeric-num) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

*(1) Blackboard Ultra does not support Ordering questions in tab-delimited text imports.*
