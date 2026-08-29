from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup

BASE_URL = "https://www.learncpp.com/"
TUTORIAL_PATH = "/cpp-tutorial/"
MANIFEST_SCHEMA_VERSION = 1


class CatalogError(ValueError):
    """Raised when course metadata is missing or internally inconsistent."""


@dataclass(frozen=True, slots=True)
class LessonRecord:
    id: str
    source_url: str
    title: str
    chapter_id: str
    chapter_label: str
    chapter_title: str
    lesson_label: str
    order: int
    filename: str
    kind: str
    previous_id: str | None = None
    next_id: str | None = None
    content_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_url": self.source_url,
            "title": self.title,
            "chapter_id": self.chapter_id,
            "chapter_label": self.chapter_label,
            "chapter_title": self.chapter_title,
            "lesson_label": self.lesson_label,
            "order": self.order,
            "filename": self.filename,
            "kind": self.kind,
            "previous_id": self.previous_id,
            "next_id": self.next_id,
            "content_hash": self.content_hash,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> LessonRecord:
        try:
            return cls(
                id=str(value["id"]),
                source_url=str(value["source_url"]),
                title=str(value["title"]),
                chapter_id=str(value["chapter_id"]),
                chapter_label=str(value["chapter_label"]),
                chapter_title=str(value["chapter_title"]),
                lesson_label=str(value["lesson_label"]),
                order=int(value["order"]),
                filename=str(value["filename"]),
                kind=str(value["kind"]),
                previous_id=(
                    str(value["previous_id"])
                    if value.get("previous_id") is not None
                    else None
                ),
                next_id=(
                    str(value["next_id"])
                    if value.get("next_id") is not None
                    else None
                ),
                content_hash=str(value.get("content_hash", "")),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise CatalogError("Manifest contains an invalid lesson record.") from exc


@dataclass(frozen=True, slots=True)
class CourseManifest:
    lessons: tuple[LessonRecord, ...]
    schema_version: int = MANIFEST_SCHEMA_VERSION
    source_url: str = BASE_URL

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "source_url": self.source_url,
            "lessons": [lesson.to_dict() for lesson in self.lessons],
        }

    @property
    def by_id(self) -> dict[str, LessonRecord]:
        return {lesson.id: lesson for lesson in self.lessons}

    @property
    def by_filename(self) -> dict[str, LessonRecord]:
        return {lesson.filename: lesson for lesson in self.lessons}


def normalize_source_url(url: str) -> str:
    parsed = urlparse(urljoin(BASE_URL, url))
    path = parsed.path
    if not path.endswith("/"):
        path += "/"
    return urlunparse((parsed.scheme, parsed.netloc.lower(), path, "", "", ""))


def is_lesson_url(url: str) -> bool:
    parsed = urlparse(normalize_source_url(url))
    return (
        parsed.netloc in {"learncpp.com", "www.learncpp.com"}
        and parsed.path.startswith(TUTORIAL_PATH)
        and parsed.path != TUTORIAL_PATH
    )


def lesson_id_from_url(url: str) -> str:
    path = urlparse(normalize_source_url(url)).path.rstrip("/")
    raw_slug = path.rsplit("/", maxsplit=1)[-1]
    lesson_id = re.sub(r"[^a-zA-Z0-9_-]+", "-", raw_slug).strip("-").lower()
    if not lesson_id:
        raise CatalogError(f"Could not derive a lesson ID from {url!r}.")
    return lesson_id


def lesson_filename(order: int, lesson_id: str) -> str:
    return f"{order:03d}-{lesson_id}.html"


def _clean_visible_text(value: str) -> str:
    value = value.replace("\xa0", " ").replace("\ufffd", " ")
    return " ".join(value.split())


def _chapter_metadata(table: Any, position: int) -> tuple[str, str, str]:
    label_element = table.select_one(".lessontable-header-chapter")
    title_element = table.select_one(".lessontable-header-title")
    raw_label = _clean_visible_text(
        label_element.get_text(" ", strip=True) if label_element else ""
    )
    chapter_title = _clean_visible_text(
        title_element.get_text(" ", strip=True) if title_element else ""
    )
    match = re.search(r"\b(chapter|appendix)\s*([a-z0-9]+)\b", raw_label, re.I)
    if match:
        kind = match.group(1).lower()
        token = match.group(2).upper()
        chapter_id = f"{kind}-{token.lower()}"
        chapter_label = f"{kind.title()} {token}"
    else:
        chapter_id = f"section-{position}"
        chapter_label = raw_label or f"Section {position}"
    return chapter_id, chapter_label, chapter_title


def discover_lesson_records(
    homepage_html: str,
    *,
    base_url: str = BASE_URL,
) -> list[LessonRecord]:
    soup = BeautifulSoup(homepage_html, "html.parser")
    tables = soup.select(".lessontable")
    if not tables:
        raise CatalogError("The LearnCpp table of contents was not found.")

    lessons: list[LessonRecord] = []
    seen_urls: set[str] = set()
    seen_ids: set[str] = set()

    for chapter_position, table in enumerate(tables, start=1):
        chapter_id, chapter_label, chapter_title = _chapter_metadata(
            table, chapter_position
        )
        for row in table.select(".lessontable-row"):
            link = row.select_one(".lessontable-row-title a[href]")
            if link is None:
                continue
            source_url = normalize_source_url(urljoin(base_url, link["href"]))
            if not is_lesson_url(source_url) or source_url in seen_urls:
                continue

            lesson_id = lesson_id_from_url(source_url)
            if lesson_id in seen_ids:
                raise CatalogError(f"Duplicate lesson ID discovered: {lesson_id}")

            label_element = row.select_one(".lessontable-row-number")
            lesson_label = _clean_visible_text(
                label_element.get_text(" ", strip=True) if label_element else ""
            )
            link_title = _clean_visible_text(link.get_text(" ", strip=True))
            title = (
                f"{lesson_label} — {link_title}" if lesson_label else link_title
            )
            kind = (
                "summary_quiz"
                if lesson_label.lower().endswith((".x", ".y"))
                or "summary-and-quiz" in lesson_id
                else "lesson"
            )
            order = len(lessons) + 1
            lessons.append(
                LessonRecord(
                    id=lesson_id,
                    source_url=source_url,
                    title=title,
                    chapter_id=chapter_id,
                    chapter_label=chapter_label,
                    chapter_title=chapter_title,
                    lesson_label=lesson_label,
                    order=order,
                    filename=lesson_filename(order, lesson_id),
                    kind=kind,
                )
            )
            seen_urls.add(source_url)
            seen_ids.add(lesson_id)

    if not lessons:
        raise CatalogError("No LearnCpp lessons were discovered.")
    return apply_neighbors(lessons)


def apply_neighbors(lessons: list[LessonRecord]) -> list[LessonRecord]:
    return [
        replace(
            lesson,
            previous_id=lessons[index - 1].id if index > 0 else None,
            next_id=lessons[index + 1].id if index + 1 < len(lessons) else None,
            order=index + 1,
        )
        for index, lesson in enumerate(lessons)
    ]


def hash_content_html(content_html: str) -> str:
    normalized = re.sub(r"\s+", " ", content_html).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def lesson_content_hash(document: str) -> str:
    soup = BeautifulSoup(document, "html.parser")
    content = soup.select_one(".entry-content")
    if content is None:
        raise CatalogError("Generated lesson has no .entry-content element.")
    return hash_content_html(str(content))


def read_manifest(path: Path) -> CourseManifest:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except (json.JSONDecodeError, OSError) as exc:
        raise CatalogError(f"Could not read course manifest at {path}.") from exc

    if not isinstance(raw, dict):
        raise CatalogError("Course manifest must be a JSON object.")
    if raw.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise CatalogError("Unsupported course manifest schema version.")
    lesson_values = raw.get("lessons")
    if not isinstance(lesson_values, list):
        raise CatalogError("Course manifest lessons must be a list.")

    manifest = CourseManifest(
        schema_version=MANIFEST_SCHEMA_VERSION,
        source_url=str(raw.get("source_url", BASE_URL)),
        lessons=tuple(LessonRecord.from_dict(value) for value in lesson_values),
    )
    validate_manifest(manifest)
    return manifest


def write_manifest(path: Path, lessons: list[LessonRecord]) -> CourseManifest:
    manifest = CourseManifest(lessons=tuple(apply_neighbors(lessons)))
    validate_manifest(manifest)
    path.write_text(
        json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def validate_manifest(manifest: CourseManifest) -> None:
    if not manifest.lessons:
        raise CatalogError("Course manifest has no lessons.")

    ids: set[str] = set()
    filenames: set[str] = set()
    for index, lesson in enumerate(manifest.lessons):
        if lesson.id in ids:
            raise CatalogError(f"Duplicate lesson ID in manifest: {lesson.id}")
        if lesson.filename in filenames:
            raise CatalogError(
                f"Duplicate lesson filename in manifest: {lesson.filename}"
            )
        if lesson.id != lesson_id_from_url(lesson.source_url):
            raise CatalogError(f"Lesson ID does not match source URL: {lesson.id}")
        if Path(lesson.filename).name != lesson.filename:
            raise CatalogError(f"Unsafe lesson filename: {lesson.filename}")
        if lesson.order != index + 1:
            raise CatalogError(f"Invalid lesson order for {lesson.id}.")
        expected_previous = manifest.lessons[index - 1].id if index > 0 else None
        expected_next = (
            manifest.lessons[index + 1].id
            if index + 1 < len(manifest.lessons)
            else None
        )
        if (
            lesson.previous_id != expected_previous
            or lesson.next_id != expected_next
        ):
            raise CatalogError(f"Invalid lesson neighbors for {lesson.id}.")
        if lesson.kind not in {"lesson", "summary_quiz"}:
            raise CatalogError(f"Invalid lesson kind for {lesson.id}.")
        ids.add(lesson.id)
        filenames.add(lesson.filename)


def validate_course_artifact(
    course_directory: Path,
    manifest: CourseManifest,
) -> list[str]:
    problems: list[str] = []
    course_root = course_directory.resolve()

    for lesson in manifest.lessons:
        lesson_path = course_directory / lesson.filename
        if not lesson_path.is_file():
            problems.append(f"Missing lesson file: {lesson.filename}")
            continue

        try:
            document = lesson_path.read_text(encoding="utf-8")
            actual_hash = lesson_content_hash(document)
        except (CatalogError, OSError, UnicodeError) as exc:
            problems.append(f"Unreadable lesson {lesson.filename}: {exc}")
            continue
        if lesson.content_hash and actual_hash != lesson.content_hash:
            problems.append(f"Content hash mismatch: {lesson.filename}")

        soup = BeautifulSoup(document, "html.parser")
        for link in soup.select("a[href]"):
            href = str(link.get("href", "")).strip()
            parsed = urlparse(href)
            if (
                not parsed.path
                or parsed.scheme
                or parsed.netloc
                or parsed.path.startswith("/")
                or not parsed.path.endswith(".html")
            ):
                continue
            target = (lesson_path.parent / unquote(parsed.path)).resolve()
            try:
                target.relative_to(course_root)
            except ValueError:
                problems.append(f"Unsafe link in {lesson.filename}: {href}")
                continue
            if not target.is_file():
                problems.append(f"Broken link in {lesson.filename}: {href}")

    return problems
