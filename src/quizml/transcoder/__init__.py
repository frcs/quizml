"""QuizML Markdown Transcoder module.

Extracts Markdown strings from QuizML documents, parses them with Mistletoe AST,
and renders target-specific representations (HTML with MathML/base64 images, LaTeX with PDF conversions).
"""

from quizml.transcoder.nodes import (
    get_md_list_from_yaml,
    iter_nodes,
    map_nodes,
    transcode_md_in_yaml,
)
from quizml.transcoder.tokens import ImageWithWidth, MathDisplay, MathInline
from quizml.transcoder.transcoder import MarkdownTranscoder


def transcode(
    doc: dict,
    target: str | dict = "html",
    schema: dict | None = None,
    base_dir: str | None = None,
) -> dict:
    """Convenience function to transcode a QuizML document dict to a target format.

    :param doc: The QuizML document dict (as returned by `quizmlyaml.load`).
    :param target: Either format name ("html", "latex", "pdf", "bb") or a target dict with "fmt".
    :param schema: Optional JSON schema.
    :param base_dir: Optional base directory for resolving relative image paths.
    :return: A copy of doc where markdown fields are transcoded.
    """
    if isinstance(target, str):
        target_name = target.lower()
        if target_name in ("latex", "pdf", "tex"):
            opts = {"fmt": "latex"}
        elif target_name in ("html", "bb", "blackboard"):
            opts = {"fmt": "html"}
        else:
            opts = {"fmt": target_name}
    else:
        opts = target

    transcoder = MarkdownTranscoder(doc, schema=schema, base_dir=base_dir)
    return transcoder.transcode_target(opts)


__all__ = [
    "transcode",
    "MarkdownTranscoder",
    "get_md_list_from_yaml",
    "transcode_md_in_yaml",
    "iter_nodes",
    "map_nodes",
    "MathInline",
    "MathDisplay",
    "ImageWithWidth",
]
