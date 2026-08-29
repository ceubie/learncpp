from __future__ import annotations

import hashlib
import json
import re
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .catalog import CourseManifest, LessonRecord

SCHEMA_VERSION = 1
LESSON_ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]{0,199}")
CARD_ID_PATTERN = re.compile(r"[0-9a-f]{32}")
MAX_NOTE_LENGTH = 500_000
MAX_FRONT_LENGTH = 5_000
MAX_BACK_LENGTH = 20_000
MAX_SOURCE_LENGTH = 20_000
MAX_CONTEXT_LENGTH = 500
MAX_TAGS = 20
MAX_TAG_LENGTH = 40


class StudyStorageError(RuntimeError):
    """Base class for study-data failures."""


class StudyValidationError(StudyStorageError):
    """Raised when a requested study-data change is invalid."""


class StudyNotFoundError(StudyStorageError):
    """Raised when a requested study object does not exist."""


class StudyConflictError(StudyStorageError):
    """Raised when optimistic concurrency detects a stale edit."""

    def __init__(self, message: str, current: dict[str, Any]) -> None:
        super().__init__(message)
        self.current = current


def _revision(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _normalize_line_endings(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


class StudyStorage:
    def __init__(self, root: Path, manifest: CourseManifest) -> None:
        self.root = root
        self.manifest = manifest
        self.lessons = manifest.by_id
        self._lock = threading.RLock()

    @property
    def notes_directory(self) -> Path:
        return self.root / "notes"

    @property
    def cards_directory(self) -> Path:
        return self.root / "cards"

    @property
    def progress_directory(self) -> Path:
        return self.root / "progress"

    @property
    def reviews_directory(self) -> Path:
        return self.root / "reviews"

    def _lesson(self, lesson_id: str) -> LessonRecord:
        if not LESSON_ID_PATTERN.fullmatch(lesson_id):
            raise StudyValidationError("Invalid lesson ID.")
        lesson = self.lessons.get(lesson_id)
        if lesson is None:
            raise StudyNotFoundError("Lesson not found.")
        return lesson

    def _card_id(self, card_id: str) -> str:
        normalized = card_id.lower()
        if not CARD_ID_PATTERN.fullmatch(normalized):
            raise StudyValidationError("Invalid card ID.")
        return normalized

    def _atomic_write_text(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            temporary.write_text(content, encoding="utf-8", newline="\n")
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)

    def _atomic_write_json(self, path: Path, value: dict[str, Any]) -> None:
        content = json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        self._atomic_write_text(path, content + "\n")

    def _read_json(self, path: Path) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise
        except (json.JSONDecodeError, OSError, UnicodeError) as exc:
            raise StudyStorageError(f"Could not read {path.name}.") from exc
        if not isinstance(value, dict):
            raise StudyStorageError(f"{path.name} must contain a JSON object.")
        return value

    def get_note(self, lesson_id: str) -> dict[str, Any]:
        lesson = self._lesson(lesson_id)
        path = self.notes_directory / f"{lesson.id}.md"
        try:
            body = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            body = ""
        except (OSError, UnicodeError) as exc:
            raise StudyStorageError(f"Could not read note for {lesson.id}.") from exc
        return {
            "lesson_id": lesson.id,
            "body": body,
            "revision": _revision(body),
        }

    def put_note(
        self,
        lesson_id: str,
        body: str,
        base_revision: str,
    ) -> dict[str, Any]:
        lesson = self._lesson(lesson_id)
        if not isinstance(body, str):
            raise StudyValidationError("Note body must be text.")
        body = _normalize_line_endings(body)
        if len(body) > MAX_NOTE_LENGTH:
            raise StudyValidationError("Note is too long.")

        with self._lock:
            current = self.get_note(lesson.id)
            if base_revision != current["revision"]:
                raise StudyConflictError(
                    "The note changed since it was loaded.",
                    current=current,
                )
            path = self.notes_directory / f"{lesson.id}.md"
            if body.strip():
                self._atomic_write_text(path, body)
            else:
                path.unlink(missing_ok=True)
                body = ""
            return {
                "lesson_id": lesson.id,
                "body": body,
                "revision": _revision(body),
            }

    def list_notes(self) -> list[dict[str, Any]]:
        if not self.notes_directory.is_dir():
            return []
        notes: list[dict[str, Any]] = []
        for lesson in self.manifest.lessons:
            path = self.notes_directory / f"{lesson.id}.md"
            if not path.is_file():
                continue
            try:
                body = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                raise StudyStorageError(f"Could not read {path.name}.") from exc
            notes.append(
                {
                    "lesson_id": lesson.id,
                    "lesson_title": lesson.title,
                    "lesson_label": lesson.lesson_label,
                    "chapter_id": lesson.chapter_id,
                    "body": body,
                    "revision": _revision(body),
                    "lesson_url": f"/course/{lesson.filename}",
                }
            )
        return notes

    def _normalize_tags(self, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise StudyValidationError("Tags must be a list.")
        if len(value) > MAX_TAGS:
            raise StudyValidationError(f"Cards may have at most {MAX_TAGS} tags.")
        tags: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise StudyValidationError("Every tag must be text.")
            tag = re.sub(r"\s+", "-", item.strip().lower())
            if not tag:
                continue
            if len(tag) > MAX_TAG_LENGTH:
                raise StudyValidationError("A card tag is too long.")
            if tag not in tags:
                tags.append(tag)
        return tags

    def _card_text(
        self,
        value: Any,
        *,
        field: str,
        maximum: int,
        required: bool = False,
    ) -> str:
        if value is None and not required:
            return ""
        if not isinstance(value, str):
            raise StudyValidationError(f"{field} must be text.")
        normalized = _normalize_line_endings(value).strip()
        if required and not normalized:
            raise StudyValidationError(f"{field} is required.")
        if len(normalized) > maximum:
            raise StudyValidationError(f"{field} is too long.")
        return normalized

    def create_card(self, value: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise StudyValidationError("Card must be a JSON object.")
        lesson = self._lesson(str(value.get("lesson_id", "")))
        timestamp = _now()
        card = {
            "schema_version": SCHEMA_VERSION,
            "id": uuid.uuid4().hex,
            "lesson_id": lesson.id,
            "source_url": lesson.source_url,
            "front": self._card_text(
                value.get("front"),
                field="Front",
                maximum=MAX_FRONT_LENGTH,
                required=True,
            ),
            "back": self._card_text(
                value.get("back"),
                field="Back",
                maximum=MAX_BACK_LENGTH,
                required=True,
            ),
            "tags": self._normalize_tags(value.get("tags")),
            "source_text": self._card_text(
                value.get("source_text"),
                field="Source text",
                maximum=MAX_SOURCE_LENGTH,
            ),
            "source_prefix": self._card_text(
                value.get("source_prefix"),
                field="Source prefix",
                maximum=MAX_CONTEXT_LENGTH,
            ),
            "source_suffix": self._card_text(
                value.get("source_suffix"),
                field="Source suffix",
                maximum=MAX_CONTEXT_LENGTH,
            ),
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        with self._lock:
            self._atomic_write_json(
                self.cards_directory / f"{card['id']}.json",
                card,
            )
        return self._enrich_card(card)

    def _read_card(self, card_id: str) -> dict[str, Any]:
        card_id = self._card_id(card_id)
        path = self.cards_directory / f"{card_id}.json"
        try:
            card = self._read_json(path)
        except FileNotFoundError as exc:
            raise StudyNotFoundError("Card not found.") from exc
        if card.get("id") != card_id:
            raise StudyStorageError(f"Card ID mismatch in {path.name}.")
        lesson_id = card.get("lesson_id")
        if not isinstance(lesson_id, str) or lesson_id not in self.lessons:
            raise StudyStorageError(f"Card {card_id} references an unknown lesson.")
        return card

    def _enrich_card(self, card: dict[str, Any]) -> dict[str, Any]:
        lesson = self.lessons[str(card["lesson_id"])]
        enriched = dict(card)
        enriched.update(
            {
                "lesson_title": lesson.title,
                "lesson_label": lesson.lesson_label,
                "chapter_id": lesson.chapter_id,
                "chapter_label": lesson.chapter_label,
                "lesson_url": f"/course/{lesson.filename}",
                "needs_review": self.needs_review(str(card["id"])),
            }
        )
        return enriched

    def get_card(self, card_id: str) -> dict[str, Any]:
        return self._enrich_card(self._read_card(card_id))

    def list_cards(
        self,
        *,
        lesson_id: str | None = None,
        chapter_id: str | None = None,
        tag: str | None = None,
        needs_review: bool | None = None,
        query: str = "",
    ) -> list[dict[str, Any]]:
        if lesson_id is not None:
            self._lesson(lesson_id)
        if not self.cards_directory.is_dir():
            return []

        normalized_query = query.strip().casefold()
        cards: list[dict[str, Any]] = []
        for path in self.cards_directory.glob("*.json"):
            if not CARD_ID_PATTERN.fullmatch(path.stem):
                continue
            card = self._enrich_card(self._read_card(path.stem))
            if lesson_id is not None and card["lesson_id"] != lesson_id:
                continue
            if chapter_id is not None and card["chapter_id"] != chapter_id:
                continue
            if tag is not None and tag.strip().lower() not in card["tags"]:
                continue
            if needs_review is not None and card["needs_review"] is not needs_review:
                continue
            if normalized_query:
                haystack = " ".join(
                    [
                        str(card["front"]),
                        str(card["back"]),
                        str(card["lesson_title"]),
                        " ".join(str(tag) for tag in card["tags"]),
                    ]
                ).casefold()
                if normalized_query not in haystack:
                    continue
            cards.append(card)
        cards.sort(key=lambda card: (str(card["created_at"]), str(card["id"])))
        return cards

    def update_card(
        self,
        card_id: str,
        value: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise StudyValidationError("Card update must be a JSON object.")
        with self._lock:
            card = self._read_card(card_id)
            for key, maximum, required in (
                ("front", MAX_FRONT_LENGTH, True),
                ("back", MAX_BACK_LENGTH, True),
                ("source_text", MAX_SOURCE_LENGTH, False),
                ("source_prefix", MAX_CONTEXT_LENGTH, False),
                ("source_suffix", MAX_CONTEXT_LENGTH, False),
            ):
                if key in value:
                    card[key] = self._card_text(
                        value[key],
                        field=key.replace("_", " ").title(),
                        maximum=maximum,
                        required=required,
                    )
            if "tags" in value:
                card["tags"] = self._normalize_tags(value["tags"])
            card["updated_at"] = _now()
            self._atomic_write_json(
                self.cards_directory / f"{card['id']}.json",
                card,
            )
        return self._enrich_card(card)

    def delete_card(self, card_id: str) -> None:
        card_id = self._card_id(card_id)
        path = self.cards_directory / f"{card_id}.json"
        with self._lock:
            if not path.is_file():
                raise StudyNotFoundError("Card not found.")
            path.unlink()
            (self.reviews_directory / f"{card_id}.json").unlink(missing_ok=True)

    def get_progress(self, lesson_id: str) -> dict[str, Any]:
        lesson = self._lesson(lesson_id)
        path = self.progress_directory / f"{lesson.id}.json"
        if not path.is_file():
            return {
                "lesson_id": lesson.id,
                "completed": False,
                "completed_content_hash": None,
                "content_updated": False,
            }
        value = self._read_json(path)
        completed_hash = value.get("completed_content_hash")
        return {
            "lesson_id": lesson.id,
            "completed": True,
            "completed_content_hash": completed_hash,
            "content_updated": bool(
                completed_hash
                and lesson.content_hash
                and completed_hash != lesson.content_hash
            ),
        }

    def set_progress(self, lesson_id: str, completed: bool) -> dict[str, Any]:
        lesson = self._lesson(lesson_id)
        if not isinstance(completed, bool):
            raise StudyValidationError("completed must be a boolean.")
        path = self.progress_directory / f"{lesson.id}.json"
        with self._lock:
            if completed:
                self._atomic_write_json(
                    path,
                    {
                        "schema_version": SCHEMA_VERSION,
                        "lesson_id": lesson.id,
                        "source_url": lesson.source_url,
                        "completed": True,
                        "completed_content_hash": lesson.content_hash,
                    },
                )
            else:
                path.unlink(missing_ok=True)
        return self.get_progress(lesson.id)

    def list_progress(self) -> list[dict[str, Any]]:
        return [
            progress
            for lesson in self.manifest.lessons
            if (progress := self.get_progress(lesson.id))["completed"]
        ]

    def needs_review(self, card_id: str) -> bool:
        card_id = self._card_id(card_id)
        return (self.reviews_directory / f"{card_id}.json").is_file()

    def mark_again(self, card_id: str) -> dict[str, Any]:
        card = self._read_card(card_id)
        marker = {
            "schema_version": SCHEMA_VERSION,
            "card_id": card["id"],
        }
        with self._lock:
            self._atomic_write_json(
                self.reviews_directory / f"{card['id']}.json",
                marker,
            )
        return {"card_id": card["id"], "needs_review": True}

    def mark_got_it(self, card_id: str) -> dict[str, Any]:
        card = self._read_card(card_id)
        with self._lock:
            (self.reviews_directory / f"{card['id']}.json").unlink(missing_ok=True)
        return {"card_id": card["id"], "needs_review": False}

    def dashboard_summary(self) -> dict[str, Any]:
        progress = self.list_progress()
        completed_ids = {item["lesson_id"] for item in progress}
        cards = self.list_cards()
        again_count = sum(bool(card["needs_review"]) for card in cards)
        continue_lesson = self.manifest.lessons[0]
        completed_orders = [
            lesson.order
            for lesson in self.manifest.lessons
            if lesson.id in completed_ids
        ]
        if completed_orders:
            furthest = max(completed_orders)
            remaining = [
                lesson
                for lesson in self.manifest.lessons
                if lesson.order > furthest and lesson.id not in completed_ids
            ]
            if remaining:
                continue_lesson = remaining[0]
            else:
                earlier = [
                    lesson
                    for lesson in self.manifest.lessons
                    if lesson.id not in completed_ids
                ]
                if earlier:
                    continue_lesson = earlier[0]

        return {
            "completed": progress,
            "completed_count": len(completed_ids),
            "lesson_count": len(self.manifest.lessons),
            "course_complete": len(completed_ids) == len(self.manifest.lessons),
            "card_count": len(cards),
            "again_count": again_count,
            "continue_lesson_id": continue_lesson.id,
            "continue_url": f"/course/{continue_lesson.filename}",
        }

    def orphaned_files(self) -> list[str]:
        orphans: list[str] = []
        for directory in (self.notes_directory, self.progress_directory):
            if not directory.is_dir():
                continue
            for path in directory.iterdir():
                if path.is_file() and path.stem not in self.lessons:
                    orphans.append(str(path.relative_to(self.root)))
        if self.reviews_directory.is_dir():
            for path in self.reviews_directory.glob("*.json"):
                if not (self.cards_directory / path.name).is_file():
                    orphans.append(str(path.relative_to(self.root)))
        return sorted(orphans)
