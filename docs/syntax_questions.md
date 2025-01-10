## Question Types Syntax <!-- {docsify-ignore} -->

BBQuiz currently supports 5 types of questions.

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

### Multiple Choice

In multiple choice questions, only one answer/statement is correct.

```yaml
- type: mc
  marks: 4
  question: |
    question statement goes here...
  answers:
    - answer:  text for answer 1
      correct: true
    - answer:  text for answer 2
      correct: false
    - answer:  text for answer 3
      correct: false
    - answer:  text for answer 4
      correct: false
```

### Multiple Answers

This is the same as for multiple choices, except that more than one answer can
be true (potentially zero or all statements can be correct).

```yaml
- type: ma
  marks: 4
  question: |
    question statement goes here...
  answers:
    - answer:  text for answer 1
      correct: true
    - answer:  text for answer 2
      correct: false
    - answer:  text for answer 3
      correct: true
    - answer:  text for answer 4
      correct: false
```
### Matching

In Matching questions, the student is asked to map each statement (`answer`)
with its corresponding match (`correct`). For n statements, there are factorial
n possibilities. The (`answer`,`correct`) statements are shuffled when
generating the exam (see how to set the random seed here).

```yaml
- type: matching
  marks: 5
  question: |
    question statement goes here...
      
  answers:
    - answer: text 1
      correct: text for correct match for text 1
    - answer: text 2
      correct: text for correct match for text 2
    - answer: text 3
      correct: text for correct match for text 3
    - answer: text 4
      correct: text for correct match for text 4 
```

### Ordering

In Ordering questions, the student is asked to rank each statement (`answer`) in
correct order. The statements need to be entered in correct order. Shuffling
occurs when generating the exam (see how to set the random seed here). 

```yaml
- type: ordering
  marks: 5
  question: |
    Order the following trees in **decreasing** order of height.
  
  answers:
    - answer: tree 1
    - answer: tree 2
    - answer: tree 3
```

