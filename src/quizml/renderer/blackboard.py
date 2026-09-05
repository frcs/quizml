"""Blackboard CSV export sanitization and helpers.

Blackboard Ultra's question importer strips style blocks, CSS classes,
and complex table formatting. This module sanitizes question HTML to ensure
tables display properly with native borders and no unescaped tabs or newlines.
"""

import copy
import warnings
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning


def sanitize_blackboard_html(html_str: str) -> str:
    """Sanitizes HTML content for Blackboard CSV export.

    - Decomposes <style> tags.
    - Unwraps <div> wrappers.
    - Sanitizes <table> by unwrapping thead/tbody/tfoot and adding border="1".
    - Strips tabs and newlines to preserve CSV format integrity.
    """
    if not html_str:
        return ""

    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
    soup = BeautifulSoup(str(html_str), "html.parser")

    # 1. Strip style tags
    for s in soup.find_all("style"):
        s.decompose()

    # 2. Unwrap div tags
    for div in soup.find_all("div"):
        div.unwrap()

    # 3. Clean tables for Blackboard compatibility
    for table in soup.find_all("table"):
        for container in table.find_all(["thead", "tbody", "tfoot"]):
            container.unwrap()
        table.attrs = {"border": "1", "style": "border-collapse: collapse;"}
        for tr in table.find_all("tr"):
            tr.attrs = {}
        for cell in table.find_all(["th", "td"]):
            cell.attrs = {}

    # 4. Handle code blocks (newlines to <br>)
    for code in soup.find_all("code"):
        if "\n" in code.text:
            code.replace_with(
                BeautifulSoup(str(code).replace("\n", "<br/>"), "html.parser")
            )

    cleaned = str(soup).replace("\n", " ").replace("\t", " ")
    return " ".join(cleaned.split())


def process_questions_for_blackboard(questions: list) -> list:
    """Processes questions, choices, and answers for Blackboard CSV export."""
    processed = []
    for q in questions:
        item_q = copy.deepcopy(q) if isinstance(q, dict) else dict(q)
        if "question" in item_q and item_q["question"]:
            item_q["question"] = sanitize_blackboard_html(item_q["question"])
        if "answer" in item_q and isinstance(item_q["answer"], str) and item_q["answer"]:
            item_q["answer"] = sanitize_blackboard_html(item_q["answer"])

        if "choices" in item_q and isinstance(item_q["choices"], list):
            new_choices = []
            for c in item_q["choices"]:
                if isinstance(c, dict):
                    c_dict = dict(c)
                    for k in ["x", "o", "text", "A", "B"]:
                        if k in c_dict and isinstance(c_dict[k], str):
                            c_dict[k] = sanitize_blackboard_html(c_dict[k])
                    new_choices.append(c_dict)
                elif isinstance(c, str):
                    new_choices.append(sanitize_blackboard_html(c))
                else:
                    new_choices.append(c)
            item_q["choices"] = new_choices

        if "answers" in item_q:
            if isinstance(item_q["answers"], list):
                item_q["answers"] = [
                    sanitize_blackboard_html(a) if isinstance(a, str) else a
                    for a in item_q["answers"]
                ]
            elif isinstance(item_q["answers"], dict):
                item_q["answers"] = {
                    sanitize_blackboard_html(k): [
                        sanitize_blackboard_html(v) if isinstance(v, str) else v
                        for v in vals
                    ]
                    for k, vals in item_q["answers"].items()
                }

        processed.append(item_q)
    return processed
