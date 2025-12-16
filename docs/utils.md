# Utils

## Diff

The `--diff` flag allows you to check whether some questions can be found in
other tests. For instance:

```bash
quizml --diff exam-2024.yaml exam-2023.yaml exam-2022.yaml ...
```

This will list all the questions in `exam-2024.yaml` that can be found in older
exams. Duplicate files will be ignored.

On my setup, I have all yaml files into a single directory (e.g.,
`exam-2023.yaml`, `midterm-2021.yaml`, `tutorial-02.yaml`), so I would call it
like this:

```bash
quizml --diff exam-2024.yaml exam-*.yaml midterm-*.yaml tutorial-*.yaml
```


