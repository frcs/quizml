## Question Types Syntax <!-- {docsify-ignore} -->

QuizML provided templates currently supports 5 types of questions but only
`Essay`, `True/False`, `Multiple Choice` and `Multiple Answers` are currently
implemented across all templates.

### Essay

The student is expected to write down a few sentences. The `answer` field
provides an indicative answer that can be used as guideline for marking.

```yaml
- type: essay
  marks: 14
  question: |
    my question statement in Mardown
  answer: |
    a suggestion for how to answer that essay question   
```

### True/False

```yaml
- type: tf
  marks: 4
  question: |
    question statement goes here...
  answer: true
```

### Multiple Choice

In multiple choice questions, only one answer/statement is correct. The correct
statements are indicated with `- x:` and the incorrectd ones with `- o:`.

```yaml
- type: mc
  marks: 4
  question: |
    question statement goes here...
  choices:
    - x:  text for answer 1
    - o:  text for answer 2
    - o:  text for answer 3
    - o:  text for answer 4
```

### Multiple Answers

This is the same as for multiple choices, except that more than one answer can
be true (potentially zero or all statements can be correct).

```yaml
- type: ma
  marks: 4
  question: |
    question statement goes here...
  choices:
    - x:  text for answer 1
    - x:  text for answer 2
    - o:  text for answer 3
    - x:  text for answer 4
```
### Matching

In Matching questions, the student is asked to map each statement (`A`) with its
corresponding match (`B`). For n statements, there are factorial n
possibilities. The (`A`,`B`) statements are shuffled when generating the exam
(see how to set the random seed here).

```yaml
- type: matching
  marks: 5
  question: |
    Match the following trees to their typical height.
  choices:
    - A: Japanese Maple (Acer palmatum)
      B: 15-25 feet
    - A: Flowering Dogwood (Cornus florida)
      B: 30–40 feet
    - A: Coast Redwood (Sequoia sempervirens)
      B: 200–350+ feet
    - A: American Beech (Fagus grandifolia)
      B: 60–80 feet
```

(only implemented for BlackBoard and HTML preview)

### Ordering

In Ordering questions, the student is asked to rank each statement (`answer`) in
correct order. The statements need to be entered in correct order. Shuffling
occurs when generating the exam (see how to set the random seed here). 

```yaml
- type: ordering
  marks: 5
  question: |
    Order the following trees in **increasing** order of height.  
  choices:
    - Japanese Maple (Acer palmatum)
    - Flowering Dogwood (Cornus florida)
    - American Beech (Fagus grandifolia)
    - Coast Redwood (Sequoia sempervirens)
```

(only implemented for BlackBoard)
