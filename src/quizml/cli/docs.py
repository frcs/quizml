import curses
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
                stem = filepath.stem.lower()
                aliases = [stem, stem.replace("_", "-")]
                if stem == "readme":
                    aliases.extend(
                        [
                            "overview",
                            "getting-started",
                            "getting_started",
                            "getting started",
                            "readme",
                        ]
                    )
                for part in stem.split("_"):
                    if part and part not in aliases:
                        aliases.append(part)
                if stem.startswith("syntax_"):
                    aliases.append(stem.replace("syntax_", ""))
                elif stem.startswith("config_"):
                    aliases.append(stem.replace("config_", ""))
                elif stem.startswith("writing_"):
                    aliases.append(stem.replace("writing_", ""))

                title_clean = title.lower().strip()
                if title_clean:
                    aliases.append(title_clean)
                    slug_base = re.sub(r"[^\w\s-]", " ", title_clean)
                    slug_parts = slug_base.split()
                    if slug_parts:
                        aliases.append("-".join(slug_parts))
                        aliases.append("_".join(slug_parts))

                items.append(
                    DocItem(
                        category=current_category,
                        title=title,
                        filename=filename,
                        path=filepath,
                        aliases=list(dict.fromkeys(aliases)),
                    )
                )
        else:
            match_cat = category_pattern.match(line_stripped)
            if match_cat:
                current_category = match_cat.group(1).strip()

    return items


def build_topic_map(doc_items: list[DocItem]) -> dict[str, DocItem]:
    """Creates a lookup dictionary mapping slugs, titles, and aliases to DocItem objects."""
    topic_map = {}
    for item in doc_items:
        topic_map[item.filename.lower()] = item
        topic_map[item.path.stem.lower()] = item
        topic_map[item.title.lower()] = item
        for alias in item.aliases:
            topic_map[alias.lower()] = item
    return topic_map


def get_all_topics(docs_dir: Path | None = None) -> list[str]:
    """Returns a deduplicated list of all recognized topic slugs and aliases."""
    if docs_dir is None:
        try:
            docs_dir = get_docs_dir()
        except FileNotFoundError:
            return ["all", "list", "overview", "quickstart", "usage"]

    doc_items = parse_sidebar(docs_dir)
    builtins = ["all", "list", "overview"]
    topics = list(builtins)
    for item in doc_items:
        for a in item.aliases:
            low = a.lower()
            if low not in topics:
                topics.append(low)
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
        primary_slug = item.aliases[0] if item.aliases else item.path.stem
        cmd_str = f"quizml --docs {primary_slug}"
        table.add_row(cat, cmd_str, item.title, item.filename)

    console.print(table)
    console.print(
        "\n[dim]Tip: Run [bold green]quizml --docs all[/bold green] to display the complete guide, or pipe to an LLM / file.[/dim]\n"
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
        if less_path:
            pager_cmd = f"{less_path} -R"
        else:
            pager_cmd = shutil.which("more")

    if not pager_cmd or pager_cmd == "cat":
        console.print(renderable)
        return

    try:
        proc = subprocess.Popen(
            pager_cmd,
            shell=True,
            stdin=subprocess.PIPE,
            text=True,
            env=env,
        )
        proc.communicate(input=rendered_text)
    except (OSError, KeyboardInterrupt):
        pass


def run_interactive_browser(
    doc_items: list[DocItem], docs_dir: Path, console: Console
) -> None:
    """Launches a full-screen interactive topic browser using curses."""
    entries: list[dict] = []

    # 1. Doc items
    for item in doc_items:
        entries.append(
            {
                "category": item.category,
                "title": item.title,
                "path": item.path,
            }
        )

    # 3. Full Guide
    entries.append(
        {
            "category": "Reference",
            "title": "Complete Documentation Guide (All)",
            "path": None,
        }
    )

    def _menu(stdscr) -> None:
        curses.curs_set(0)
        stdscr.keypad(True)
        try:
            curses.use_default_colors()
        except curses.error:
            pass

        has_color = curses.has_colors()
        if has_color:
            try:
                curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)  # Selected
                curses.init_pair(2, curses.COLOR_CYAN, -1)  # Category
                curses.init_pair(3, curses.COLOR_WHITE, -1)  # Normal
                curses.init_pair(4, curses.COLOR_YELLOW, -1)  # Header help
            except curses.error:
                pass

        selected = 0
        top_line = 0

        while True:
            stdscr.clear()
            h, w = stdscr.getmaxyx()
            if h < 6 or w < 20:
                stdscr.addstr(0, 0, "Window too small")
                stdscr.refresh()
                key = stdscr.getch()
                if key in (ord("q"), ord("Q"), 27):
                    break
                continue

            # Header
            title = "QuizML Documentation Browser"
            stdscr.addstr(
                0, max(0, (w - len(title)) // 2), title[: w - 1], curses.A_BOLD
            )
            help_line = "↑/↓, j/k: Navigate | Enter: Read | q: Quit"
            attr_help = curses.color_pair(4) if has_color else curses.A_DIM
            stdscr.addstr(
                1, max(0, (w - len(help_line)) // 2), help_line[: w - 1], attr_help
            )

            try:
                stdscr.hline(2, 0, curses.ACS_HLINE, w)
            except curses.error:
                pass

            available_rows = h - 4
            if selected < top_line:
                top_line = selected
            elif selected >= top_line + available_rows:
                top_line = selected - available_rows + 1

            for i in range(top_line, min(len(entries), top_line + available_rows)):
                row = 3 + (i - top_line)
                entry = entries[i]
                is_sel = i == selected

                prefix = " ▸ " if is_sel else "   "
                cat_tag = f"[{entry['category']}] "
                text = f"{prefix}{cat_tag}{entry['title']}"
                text = text[: w - 1].ljust(w - 1)

                if is_sel:
                    attr = (
                        curses.color_pair(1) | curses.A_BOLD
                        if has_color
                        else curses.A_REVERSE
                    )
                else:
                    attr = curses.color_pair(3) if has_color else curses.A_NORMAL

                try:
                    stdscr.addstr(row, 0, text, attr)
                except curses.error:
                    pass

            # Footer
            footer = f" Topic {selected + 1} of {len(entries)} "
            try:
                stdscr.addstr(h - 1, 0, footer[: w - 1], curses.A_DIM)
            except curses.error:
                pass

            stdscr.refresh()

            key = stdscr.getch()

            if key in (curses.KEY_UP, ord("k"), ord("K")):
                selected = (selected - 1) % len(entries)
            elif key in (curses.KEY_DOWN, ord("j"), ord("J")):
                selected = (selected + 1) % len(entries)
            elif key == curses.KEY_PPAGE:
                selected = max(0, selected - available_rows)
            elif key == curses.KEY_NPAGE:
                selected = min(len(entries) - 1, selected + available_rows)
            elif key in (curses.KEY_HOME, ord("g")):
                selected = 0
            elif key in (curses.KEY_END, ord("G")):
                selected = len(entries) - 1
            elif key in (ord("q"), ord("Q"), 27):
                break
            elif key in (curses.KEY_ENTER, 10, 13):
                target_entry = entries[selected]
                if target_entry["path"] is not None:
                    content = target_entry["path"].read_text(encoding="utf-8")
                else:
                    content = get_full_documentation(doc_items)

                curses.def_prog_mode()
                curses.endwin()
                try:
                    page_content(Markdown(content), console)
                finally:
                    curses.reset_prog_mode()
                    stdscr.clear()
                    stdscr.refresh()

    try:
        curses.wrapper(_menu)
    except curses.error:
        # Fallback if curses fails to initialize
        readme_path = docs_dir / "README.md"
        if readme_path.is_file():
            console.print(Markdown(readme_path.read_text(encoding="utf-8")))
            console.print("\n---\n")
        print_topics_table(doc_items, console)


def handle_docs(topic: str | None = None, no_pager: bool = False) -> None:
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
        # No topic provided (e.g. `quizml --docs`)
        if not is_tty:
            full_doc = get_full_documentation(doc_items)
            sys.stdout.write(full_doc + "\n")
            return

        if no_pager or not sys.stdin.isatty():
            readme_path = docs_dir / "README.md"
            if readme_path.is_file():
                console.print(Markdown(readme_path.read_text(encoding="utf-8")))
                console.print("\n---\n")
            print_topics_table(doc_items, console)
            return

        run_interactive_browser(doc_items, docs_dir, console)
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
        if not is_tty:
            sys.stdout.write(content + "\n")
        elif no_pager:
            console.print(Markdown(content))
        else:
            page_content(Markdown(content), console)
        return

    err_msg = f"Unknown documentation topic '{topic}'.\n\nAvailable topics:\n"
    available = sorted(list(dict.fromkeys(item.aliases[0] for item in doc_items)))
    err_msg += "  " + ", ".join(available) + "\n\n"
    err_msg += "Run 'quizml --docs list' to view all topics, or 'quizml --docs all' for full documentation.\n"

    sys.stderr.write(err_msg)
    sys.exit(1)
