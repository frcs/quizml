import io
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from quizml.exceptions import QuizMLConfigError


@dataclass
class DocItem:
    category: str
    title: str
    filename: str
    path: Path


def _normalize_topic(topic: str) -> str:
    """Make filename and title spellings comparable for topic lookup."""
    return " ".join(topic.lower().replace("_", " ").replace("-", " ").split())


def _primary_topic(item: DocItem) -> str:
    """Return the topic name shown in lists and shell completion."""
    return "overview" if item.path.stem.lower() == "readme" else item.path.stem.lower()


def _topic_names(item: DocItem) -> set[str]:
    names = {
        _normalize_topic(item.filename),
        _normalize_topic(item.path.stem),
        _normalize_topic(item.title),
    }
    if item.path.stem.lower() == "readme":
        names.add("overview")
    return names


def get_docs_dir() -> Path:
    """Finds the QuizML documentation directory.

    Checks package-level docs directory first, then repository root docs directory.
    """
    base = Path(__file__).resolve().parent  # src/quizml/cli
    # 1. Packaged docs (inside quizml package: src/quizml/docs)
    pkg_docs = base.parent / "docs"
    if pkg_docs.is_dir():
        return pkg_docs

    # 2. Repository root docs (dev mode: root/docs)
    repo_docs = base.parent.parent.parent / "docs"
    if repo_docs.is_dir():
        return repo_docs

    raise FileNotFoundError("Could not locate QuizML documentation directory.")


def parse_sidebar(docs_dir: Path) -> list[DocItem]:
    """Parses docs/_sidebar.md to extract reading order, categories, and titles."""
    sidebar_file = docs_dir / "_sidebar.md"
    if not sidebar_file.is_file():
        items = []
        for md_file in sorted(docs_dir.glob("*.md")):
            if md_file.name.startswith("_"):
                continue
            stem = md_file.stem.replace("_", " ").title()
            items.append(
                DocItem(
                    category="Documentation",
                    title=stem,
                    filename=md_file.name,
                    path=md_file,
                )
            )
        return items

    lines = sidebar_file.read_text(encoding="utf-8").splitlines()
    items = []
    current_category = "General"

    link_pattern = re.compile(r"\[(?:\*\*)?(.*?)(?:\*\*)?\]\((.*?\.md)\)")
    category_pattern = re.compile(r"^-\s+([^[].*)$")

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped or line_stripped.startswith("<!--"):
            continue

        match_link = link_pattern.search(line_stripped)
        if match_link:
            title = match_link.group(1).strip()
            filename = match_link.group(2).strip()
            filepath = docs_dir / filename
            if filepath.is_file():
                items.append(
                    DocItem(
                        category=current_category,
                        title=title,
                        filename=filename,
                        path=filepath,
                    )
                )
        else:
            match_cat = category_pattern.match(line_stripped)
            if match_cat:
                current_category = match_cat.group(1).strip()

    return items


def get_completion_topics(docs_dir: Path | None = None) -> list[str]:
    """Return one canonical topic per page in sidebar order, plus built-ins."""
    if docs_dir is None:
        try:
            docs_dir = get_docs_dir()
        except FileNotFoundError:
            return ["all", "list", "overview", "quickstart", "usage"]

    topics = ["all", "list"]
    for item in parse_sidebar(docs_dir):
        topic = _primary_topic(item)
        if topic not in topics:
            topics.append(topic)
    return topics


def get_full_documentation(doc_items: list[DocItem]) -> str:
    """Concatenates all documentation sections into a single markdown stream."""
    docs = []
    seen_paths = set()

    for item in doc_items:
        if item.path in seen_paths:
            continue
        seen_paths.add(item.path)
        content = item.path.read_text(encoding="utf-8").strip()
        docs.append(
            f"<!-- Section: {item.category} / {item.title} ({item.filename}) -->\n\n{content}"
        )

    return "\n\n---\n\n".join(docs)


def print_topics_table(doc_items: list[DocItem], console: Console) -> None:
    """Displays a clean table of available documentation topics."""
    table = Table(
        title="QuizML Documentation Topics", show_header=True, header_style="bold cyan"
    )
    table.add_column("Category", style="dim", no_wrap=True)
    table.add_column("Topic / Command", style="bold")
    table.add_column("Description / Title")
    table.add_column("File", style="grey50")

    last_category = None
    for item in doc_items:
        cat = item.category if item.category != last_category else ""
        last_category = item.category
        primary_slug = _primary_topic(item)
        cmd_str = f"quizml docs {primary_slug}"
        table.add_row(cat, cmd_str, item.title, item.filename)

    console.print(table)
    console.print(
        "\n[dim]Tip: Run [bold green]quizml docs all[/bold green] to display the complete guide, or pipe to an LLM / file.[/dim]\n"
    )


def page_content(renderable, console: Console | None = None) -> None:
    """Renders Rich content with ANSI styling and pages it via less -RF (or $PAGER)."""
    if console is None:
        console = Console()

    width = console.size.width or 80
    buf = io.StringIO()
    buf_console = Console(
        file=buf,
        force_terminal=True,
        color_system=console.color_system or "truecolor",
        width=width,
    )
    buf_console.print(renderable)
    rendered_text = buf.getvalue()

    pager_cmd = os.environ.get("PAGER")
    env = os.environ.copy()
    if "LESS" not in env:
        env["LESS"] = "-R"

    if not pager_cmd:
        less_path = shutil.which("less")
        pager_cmd = f"{less_path} -R" if less_path else shutil.which("more")

    if not pager_cmd or pager_cmd == "cat":
        console.print(renderable)
        return

    try:
        import shlex

        proc = subprocess.Popen(
            shlex.split(pager_cmd),
            stdin=subprocess.PIPE,
            text=True,
            env=env,
        )
        proc.communicate(input=rendered_text)
    except (OSError, KeyboardInterrupt):
        pass


def handle_docs(topic: str | None = None, no_pager: bool = False) -> None:
    """CLI entry point for displaying documentation."""
    try:
        docs_dir = get_docs_dir()
    except FileNotFoundError as err:
        raise QuizMLConfigError(str(err)) from err

    doc_items = parse_sidebar(docs_dir)
    is_tty = sys.stdout.isatty()
    console = Console()

    query = _normalize_topic(topic or "")

    if query == "list":
        if is_tty:
            print_topics_table(doc_items, console)
        else:
            lines = ["QuizML Documentation Topics:\n"]
            for item in doc_items:
                primary_slug = _primary_topic(item)
                lines.append(f"- {primary_slug:<20} {item.title} ({item.filename})")
            sys.stdout.write("\n".join(lines) + "\n")
        return

    if query == "all":
        full_doc = get_full_documentation(doc_items)
        if not is_tty:
            sys.stdout.write(full_doc + "\n")
        elif no_pager:
            console.print(Markdown(full_doc))
        else:
            page_content(Markdown(full_doc), console)
        return

    if not query:
        # No topic provided (e.g. `quizml docs`)
        if not is_tty:
            full_doc = get_full_documentation(doc_items)
            sys.stdout.write(full_doc + "\n")
            return

        readme_path = docs_dir / "README.md"
        if readme_path.is_file():
            console.print(Markdown(readme_path.read_text(encoding="utf-8")))
            console.print("\n---\n")
        print_topics_table(doc_items, console)
        return

    exact_matches = [item for item in doc_items if query in _topic_names(item)]
    matches = exact_matches or [
        item for item in doc_items if any(query in name for name in _topic_names(item))
    ]
    matched_item = matches[0] if len(matches) == 1 else None

    if matched_item:
        content = matched_item.path.read_text(encoding="utf-8")
        if not is_tty:
            sys.stdout.write(content + "\n")
        elif no_pager:
            console.print(Markdown(content))
        else:
            page_content(Markdown(content), console)
        return

    err_msg = f"Unknown documentation topic '{topic}'.\n\nAvailable topics:\n"
    available = [_primary_topic(item) for item in doc_items]
    err_msg += "  " + ", ".join(available) + "\n\n"
    err_msg += "Run 'quizml docs list' to view all topics, or 'quizml docs all' for full documentation.\n"

    raise QuizMLConfigError(err_msg)
