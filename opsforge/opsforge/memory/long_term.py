"""Long-term memory: plain markdown files the agents read and write.

Layout under memory_dir:
  incidents/<slug>.md   one file per resolved incident (symptom, cause, fix)
  lessons.md            short, durable rules learned from past runs
  services/<name>.md    per-service notes (owners, quirks, dependencies)

Files are the source of truth; the vector index is derived from them.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path


def slugify(text: str, limit: int = 60) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:limit] or "untitled"


class LongTermMemory:
    def __init__(self, root: Path):
        self.root = Path(root)
        for sub in ("incidents", "services"):
            (self.root / sub).mkdir(parents=True, exist_ok=True)
        self.lessons_path = self.root / "lessons.md"
        if not self.lessons_path.exists():
            self.lessons_path.write_text("# Lessons\n\n")

    # --- incidents -------------------------------------------------------
    def save_incident(self, title: str, symptom: str, root_cause: str, fix: str, tags: list[str] | None = None) -> Path:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = self.root / "incidents" / f"{stamp}-{slugify(title)}.md"
        tags_line = ", ".join(tags or [])
        path.write_text(
            f"# {title}\n\n"
            f"- date: {stamp}\n"
            f"- tags: {tags_line}\n\n"
            f"## Symptom\n{symptom}\n\n"
            f"## Root cause\n{root_cause}\n\n"
            f"## Fix\n{fix}\n"
        )
        return path

    def list_incidents(self) -> list[Path]:
        return sorted((self.root / "incidents").glob("*.md"))

    # --- lessons ---------------------------------------------------------
    def add_lesson(self, lesson: str) -> None:
        lesson = lesson.strip().lstrip("- ").strip()
        if not lesson or lesson in self.lessons_path.read_text():
            return  # dedupe
        with self.lessons_path.open("a") as f:
            f.write(f"- {lesson}\n")

    def lessons(self, limit: int = 20) -> list[str]:
        lines = [l[2:].strip() for l in self.lessons_path.read_text().splitlines() if l.startswith("- ")]
        return lines[-limit:]

    # --- services --------------------------------------------------------
    def service_note(self, name: str) -> str:
        p = self.root / "services" / f"{slugify(name)}.md"
        return p.read_text() if p.exists() else ""

    def write_service_note(self, name: str, body: str) -> Path:
        p = self.root / "services" / f"{slugify(name)}.md"
        p.write_text(body)
        return p

    # --- bulk ------------------------------------------------------------
    def all_documents(self) -> list[tuple[str, str]]:
        """(doc_id, text) for everything that should be searchable."""
        docs: list[tuple[str, str]] = []
        for p in self.list_incidents():
            docs.append((f"incident:{p.stem}", p.read_text()))
        for p in sorted((self.root / "services").glob("*.md")):
            docs.append((f"service:{p.stem}", p.read_text()))
        return docs
