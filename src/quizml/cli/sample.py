"""Materialize question-bank includes into a static, editable QuizML file."""

import copy
import os
import random
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedSeq
from ruamel.yaml.error import YAMLError
from ruamel.yaml.tokens import CommentToken

from ..exceptions import QuizMLError


def _sample_questions(questions, count, seed):
    indices = random.Random(str(seed)).sample(range(len(questions)), count)
    selected = CommentedSeq()
    for source_index in indices:
        selected.append(questions[source_index])
        comment = getattr(questions, "ca", None)
        if comment and source_index in comment.items:
            selected.ca.items[len(selected) - 1] = copy.deepcopy(
                comment.items[source_index]
            )
    return selected


def _read_yaml(path):
    yaml = YAML()
    try:
        text = path.read_text(encoding="utf-8")
        docs = [doc for doc in yaml.load_all(text) if doc is not None]
    except OSError as err:
        raise QuizMLError(f"Could not read YAML file {path}: {err}") from err
    except YAMLError as err:
        raise QuizMLError(f"YAML parsing error in {path}: {err}") from err
    if len(docs) > 2:
        raise QuizMLError(f"YAML file {path} cannot have more than 2 documents")
    if not docs:
        return yaml, [], None
    if len(docs) == 1:
        if isinstance(docs[0], list):
            return yaml, docs, 0
        return yaml, [docs[0], []], 1
    if not isinstance(docs[1], list):
        raise QuizMLError(f"Questions in {path} must be a YAML list")
    return yaml, docs, 1


def _figure_paths(header, base_dir):
    if not isinstance(header, dict):
        return []
    paths = header.get("_figures_path", [])
    if isinstance(paths, str):
        paths = [paths]
    if not isinstance(paths, list):
        return []
    result = []
    for path in paths:
        path = Path(str(path)).expanduser()
        result.append(
            path.resolve() if path.is_absolute() else (base_dir / path).resolve()
        )
    return result


def _comment_tokens(data):
    ca = getattr(data, "ca", None)
    if ca is None:
        return []
    tokens = []

    def collect(value):
        if isinstance(value, CommentToken):
            tokens.append(copy.deepcopy(value))
        elif isinstance(value, dict):
            for item in value.values():
                collect(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                collect(item)

    collect(ca.comment)
    collect(ca.end)
    collect(ca.items)
    return tokens


def _expand(questions, base_dir, *, inherited_seed, stack, figure_dirs):
    expanded = CommentedSeq()

    def append_items(items, comments=None):
        start = len(expanded)
        expanded.extend(items)
        if comments:
            for offset, comment in enumerate(comments):
                if offset >= len(items) or comment is None:
                    continue
                target_index = start + offset
                existing = expanded.ca.items.get(target_index)
                if existing is None:
                    expanded.ca.items[target_index] = copy.deepcopy(comment)
                else:
                    for slot, value in enumerate(comment):
                        if value is None:
                            continue
                        if existing[slot] is None:
                            existing[slot] = copy.deepcopy(value)
                        elif isinstance(existing[slot], list):
                            values = value if isinstance(value, list) else [value]
                            existing[slot].extend(copy.deepcopy(values))
                        else:
                            existing[slot] = [existing[slot], copy.deepcopy(value)]

    for index, question in enumerate(questions):
        source_comments = getattr(questions, "ca", None)
        question_comments = (
            source_comments.items.get(index) if source_comments is not None else None
        )
        if not isinstance(question, dict) or "_include" not in question:
            append_items([question], [question_comments])
            continue

        include_path = (base_dir / str(question["_include"])).expanduser().resolve()
        if include_path in stack:
            chain = " -> ".join(str(path) for path in (*stack, include_path))
            raise QuizMLError(f"Circular include detected: {chain}")
        try:
            _, bank_docs, q_index = _read_yaml(include_path)
        except QuizMLError as err:
            raise QuizMLError(f"In include {question['_include']!s}: {err}") from err
        bank_questions = bank_docs[q_index] if q_index is not None else []
        figure_dirs.add(include_path.parent.resolve())
        if q_index == 1:
            figure_dirs.update(_figure_paths(bank_docs[0], include_path.parent))
        bank_questions = _expand(
            bank_questions,
            include_path.parent,
            inherited_seed=inherited_seed,
            stack=(*stack, include_path),
            figure_dirs=figure_dirs,
        )

        if "count" in question:
            try:
                count = int(question["count"])
            except (TypeError, ValueError) as err:
                raise QuizMLError("Include 'count' must be an integer") from err
            if count < 0:
                raise QuizMLError("Include 'count' cannot be negative")
            seed = question.get("seed", inherited_seed)
            if seed is None:
                raise QuizMLError(
                    "Sampled includes require a 'seed' or a command-line --seed"
                )
            if count < len(bank_questions):
                bank_questions = _sample_questions(bank_questions, count, seed)
        elif "seed" in question:
            raise QuizMLError("Include 'seed' requires a 'count'")

        comments = [bank_questions.ca.items.get(i) for i in range(len(bank_questions))]
        directive_comments = _comment_tokens(question)
        if comments and directive_comments:
            if comments[0] is None:
                comments[0] = [None, directive_comments, None, None]
            else:
                before = comments[0][1]
                comments[0][1] = (
                    directive_comments
                    if before is None
                    else [*directive_comments, *before]
                )
        if comments and question_comments:
            if comments[0] is None:
                comments[0] = question_comments
            else:
                for slot, value in enumerate(question_comments):
                    if value is not None:
                        current = comments[0][slot]
                        comments[0][slot] = (
                            copy.deepcopy(value)
                            if current is None
                            else [current, copy.deepcopy(value)]
                        )
        append_items(bank_questions, comments)

    if getattr(questions, "ca", None):
        expanded.ca.comment = copy.deepcopy(questions.ca.comment)
        expanded.ca.end = copy.deepcopy(questions.ca.end)
    return expanded


def run_sample(args):
    source = Path(args.file).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    if source == output:
        raise QuizMLError("Sample output must be different from the meta YAML input")
    if output.exists() and not args.force:
        raise QuizMLError(
            f"Output already exists: {output}. Use --force to replace it."
        )

    yaml, docs, q_index = _read_yaml(source)
    if q_index is None:
        raise QuizMLError(f"No questions found in {source}")
    figure_dirs = set(_figure_paths(docs[0], source.parent) if q_index == 1 else [])
    docs[q_index] = _expand(
        docs[q_index],
        source.parent,
        inherited_seed=args.seed,
        stack=(source,),
        figure_dirs=figure_dirs,
    )
    if figure_dirs and q_index == 1:
        docs[0]["_figures_path"] = sorted(
            os.path.relpath(path, output.parent) for path in figure_dirs
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as stream:
        yaml.dump_all(docs, stream)
    return True
