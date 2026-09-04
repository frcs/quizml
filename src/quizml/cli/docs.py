import re
import sys
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table


@dataclass
class DocItem:
    category: str
    title: str
    filename: str
    path: Path
    aliases: list[str]


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


def get_llms_file() -> Path | None:
    """Finds LLMS.md if present at repository root, package level, or in docs/."""
    base = Path(__file__).resolve().parent  # src/quizml/cli
    repo_llms = base.parent.parent.parent / "LLMS.md"
    if repo_llms.is_file():
        return repo_llms
    pkg_llms = base.parent / "LLMS.md"
    if pkg_llms.is_file():
        return pkg_llms
    prompt_template = base.parent / "docs" / "llm_prompt_template.md"
    if prompt_template.is_file():
        return prompt_template
    return None


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
                    aliases=[md_file.stem, md_file.stem.replace("_", "-")],
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
                stem = filepath.stem
                aliases = [stem, stem.replace("_", "-")]
                if stem.startswith("syntax_"):
                    aliases.append(stem.replace("syntax_", ""))
                elif stem.startswith("config_"):
                    aliases.append(stem.replace("config_", ""))

                items.append(
                    DocItem(
                        category=current_category,
                        title=title,
                        filename=filename,
                        path=filepath,
                        aliases=aliases,
                    )
                )
        else:
            match_cat = category_pattern.match(line_stripped)
            if match_cat:
                current_category = match_cat.group(1).strip()

    return items


def build_topic_map(doc_items: list[DocItem]) -> dict[str, DocItem]:
    """Creates a lookup dictionary mapping slugs and aliases to DocItem objects."""
    topic_map = {}
    for item in doc_items:
        topic_map[item.filename.lower()] = item
        topic_map[item.path.stem.lower()] = item
        for alias in item.aliases:
            topic_map[alias.lower()] = item
    return topic_map


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
        primary_slug = item.aliases[0] if item.aliases else item.path.stem
        cmd_str = f"quizml --docs {primary_slug}"
        table.add_row(cat, cmd_str, item.title, item.filename)

    console.print(table)
    console.print(
        "\n[dim]Tip: Run [bold green]quizml --docs all[/bold green] to display the complete guide, or pipe to an LLM / file.[/dim]\n"
    )


def handle_docs(topic: str | None = None) -> None:
    """CLI entry point for displaying documentation."""
    try:
        docs_dir = get_docs_dir()
    except FileNotFoundError as err:
        sys.stderr.write(f"Error: {err}\n")
        sys.exit(1)

    doc_items = parse_sidebar(docs_dir)
    topic_map = build_topic_map(doc_items)

    is_tty = sys.stdout.isatty()
    console = Console()

    query = (topic or "").strip().lower()

    if query in ("llm", "llms", "prompt"):
        llms_path = get_llms_file()
        if llms_path:
            content = llms_path.read_text(encoding="utf-8")
            if is_tty:
                console.print(Markdown(content))
            else:
                sys.stdout.write(content + "\n")
            return

    if query == "list":
        if is_tty:
            print_topics_table(doc_items, console)
        else:
            lines = ["QuizML Documentation Topics:\n"]
            for item in doc_items:
                primary_slug = item.aliases[0] if item.aliases else item.path.stem
                lines.append(f"- {primary_slug:<20} {item.title} ({item.filename})")
            sys.stdout.write("\n".join(lines) + "\n")
        return

    if (
        query == "all"
        or (not query and not is_tty)
        or (query == "overview" and not is_tty)
    ):
        full_doc = get_full_documentation(doc_items)
        if is_tty:
            with console.pager(styles=True):
                console.print(Markdown(full_doc))
        else:
            sys.stdout.write(full_doc + "\n")
        return

    if not query or query == "overview":
        readme_path = docs_dir / "README.md"
        if readme_path.is_file():
            content = readme_path.read_text(encoding="utf-8")
            console.print(Markdown(content))
            console.print("\n---\n")
        print_topics_table(doc_items, console)
        return

    matched_item = topic_map.get(query)
    if not matched_item:
        matches = [
            item
            for item in doc_items
            if query in item.path.stem.lower()
            or query in item.title.lower()
            or any(query in a for a in item.aliases)
        ]
        if len(matches) == 1:
            matched_item = matches[0]

    if matched_item:
        content = matched_item.path.read_text(encoding="utf-8")
        if is_tty:
            line_count = len(content.splitlines())
            terminal_height = console.size.height or 24
            if line_count > terminal_height:
                with console.pager(styles=True):
                    console.print(Markdown(content))
            else:
                console.print(Markdown(content))
        else:
            sys.stdout.write(content + "\n")
        return

    err_msg = f"Unknown documentation topic '{topic}'.\n\nAvailable topics:\n"
    available = sorted(list(dict.fromkeys(item.aliases[0] for item in doc_items)))
    err_msg += "  " + ", ".join(available) + "\n\n"
    err_msg += "Run 'quizml --docs list' to view all topics, or 'quizml --docs all' for full documentation.\n"

    sys.stderr.write(err_msg)
    sys.exit(1)
