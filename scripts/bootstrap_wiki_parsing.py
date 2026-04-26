from __future__ import annotations

from collections import Counter
from pathlib import Path
from types import ModuleType
import re


def parse_note_snippets(api: ModuleType, note_lines: list[str]) -> list[str]:
    snippets: list[str] = []
    for line in note_lines:
        stripped = line.strip()
        if not stripped:
            continue
        if any(pattern.fullmatch(stripped) for pattern in api.BOILERPLATE_PATTERNS):
            continue
        if stripped.startswith("### "):
            continue
        normalized = re.sub(r"^[-*+]\s+", "", stripped)
        normalized = re.sub(r"^\d+\.\s+", "", normalized)
        cleaned = api.strip_markdown(normalized).strip()
        if cleaned and cleaned not in snippets:
            snippets.append(cleaned)
    return snippets


def parse_source_line(api: ModuleType, line: str, retained_evidence: str = "") -> object | None:
    match = api.SOURCE_LINE_RE.match(line.strip())
    if not match:
        return None
    label = match.group("label")
    suffix = match.group("suffix").strip()
    status = "local_only"
    if suffix == "— [⚠️ fetch failed]":
        status = "fetch_failed"
    elif suffix == "— [⚠️ non-HTML resource]":
        status = "non_html"
    elif suffix == "— [⚠️ dead link]":
        status = "http_dead"
    return api.SourceRecord(
        label=label,
        path=match.group("path"),
        status=status,
        raw_content="",
        cleaned_text=retained_evidence,
        fetched_summary=None,
        detected_url=label if label.startswith(("http://", "https://")) else None,
        source_kind="chat" if match.group("path").startswith("../sources/chat/") else "capture",
        title=label,
        external_url=label if label.startswith(("http://", "https://")) else None,
    )


def extract_connection_slugs(api: ModuleType, connection_lines: list[str]) -> list[str]:
    slugs: list[str] = []
    for line in connection_lines:
        match = api.CONNECTION_SLUG_RE.search(line)
        if not match:
            continue
        slug = match.group("slug")
        if slug not in slugs:
            slugs.append(slug)
    return slugs


def parse_page_file(api: ModuleType, path: Path, page_type: str | None = None) -> object:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = text.splitlines()
    slug = path.stem
    title = lines[0][2:].strip() if lines and lines[0].startswith("# ") else api.page_title(slug)
    sections: dict[str, list[str]] = {
        "summary": [],
        "notes": [],
        "connections": [],
        "sources": [],
        "open_questions": [],
    }
    current = "summary"
    for line in lines[1:]:
        if line == "## Notes":
            current = "notes"
            continue
        if line == "## Open Questions":
            current = "open_questions"
            continue
        if line == "## Connections":
            current = "connections"
            continue
        if line == "## Sources":
            current = "sources"
            continue
        sections[current].append(line)

    retained_evidence = "\n".join(parse_note_snippets(api, [line for line in sections["notes"] if line.strip()]))
    sources: dict[str, object] = {}
    for line in sections["sources"]:
        source = parse_source_line(api, line, retained_evidence)
        if source is not None:
            sources[source.path] = source

    connection_slugs = extract_connection_slugs(api, [line for line in sections["connections"] if line.strip()])
    summary_lines = [line for line in sections["summary"] if line.strip()]
    note_lines = [line for line in sections["notes"] if line.strip()]
    open_question_lines = [line for line in sections["open_questions"] if line.strip()]
    inferred_shape = api.PAGE_SHAPE_TOPIC if (not note_lines and not sources and connection_slugs) else api.PAGE_SHAPE_ATOMIC

    return api.ParsedWikiPage(
        slug=slug,
        title=title,
        page_type=page_type or api.classify_page(slug, title, "title"),
        shape=inferred_shape,
        summary_lines=summary_lines,
        note_lines=note_lines,
        open_question_lines=open_question_lines,
        connection_slugs=connection_slugs,
        sources=sources,
    )


def parsed_page_to_page(api: ModuleType, parsed: object) -> object:
    page = api.Page(
        slug=parsed.slug,
        title=parsed.title or api.page_title(parsed.slug),
        page_type=parsed.page_type,
        summary_hint=parsed.title,
        shape=parsed.shape,
    )
    page.notes = parse_note_snippets(api, parsed.note_lines)
    if parsed.note_lines:
        page.rendered_notes_markdown = "\n".join(parsed.note_lines).strip()
    page.open_questions = parse_note_snippets(api, parsed.open_question_lines)
    for source_path, source in parsed.sources.items():
        page.sources[source_path] = source
    for other in parsed.connection_slugs:
        page.connections[other] += 1
    return page


def load_existing_page_types(api: ModuleType, index_path: Path) -> dict[str, str]:
    if not index_path.exists():
        return {}
    page_types: dict[str, str] = {}
    current_section: str | None = None
    for line in index_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            current_section = section if section in api.INDEX_SECTION_ORDER else None
            continue
        if current_section is None:
            continue
        match = re.match(r"^- \[\[(?P<slug>[^\]]+)\]\] — ", line)
        if match:
            page_types[match.group("slug")] = current_section
    return page_types


def load_page_types(api: ModuleType) -> dict[str, str]:
    catalog_path = api.WIKI_ROOT / api.CATALOG_PATH
    if catalog_path.exists():
        return load_existing_page_types(api, catalog_path)
    return load_existing_page_types(api, api.WIKI_ROOT / "index.md")


def load_existing_wiki_pages(api: ModuleType) -> dict[str, object]:
    page_types = load_page_types(api)
    parsed_pages: dict[str, object] = {}
    if not api.WIKI_ROOT.exists():
        return parsed_pages
    for path in sorted(api.WIKI_ROOT.glob("*.md")):
        if path.stem in {"index", "log", Path(api.CATALOG_PATH).stem}:
            continue
        parsed = parse_page_file(api, path, page_type=page_types.get(path.stem))
        parsed_pages[parsed.slug] = parsed
    return parsed_pages
