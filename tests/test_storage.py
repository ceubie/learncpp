from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from study_app.catalog import CourseManifest, LessonRecord, apply_neighbors
from study_app.storage import (
    StudyConflictError,
    StudyNotFoundError,
    StudyStorage,
    StudyValidationError,
)


def _manifest() -> CourseManifest:
    lessons = [
        LessonRecord(
            id="first",
            source_url="https://www.learncpp.com/cpp-tutorial/first/",
            title="0.1 — First",
            chapter_id="chapter-0",
            chapter_label="Chapter 0",
            chapter_title="Start",
            lesson_label="0.1",
            order=1,
            filename="001-first.html",
            kind="lesson",
            content_hash="hash-one",
        ),
        LessonRecord(
            id="second",
            source_url="https://www.learncpp.com/cpp-tutorial/second/",
            title="0.9 — Second",
            chapter_id="chapter-0",
            chapter_label="Chapter 0",
            chapter_title="Start",
            lesson_label="0.9",
            order=2,
            filename="004-second.html",
            kind="lesson",
            content_hash="hash-two",
        ),
    ]
    return CourseManifest(lessons=tuple(apply_neighbors(lessons)))


def test_note_revision_prevents_lost_updates(tmp_path: Path) -> None:
    storage = StudyStorage(tmp_path, _manifest())
    initial = storage.get_note("first")
    saved = storage.put_note("first", "first edit", initial["revision"])

    with pytest.raises(StudyConflictError) as conflict:
        storage.put_note("first", "stale edit", initial["revision"])

    assert saved["body"] == "first edit"
    assert conflict.value.current["body"] == "first edit"
    assert not list(tmp_path.rglob("*.tmp"))


def test_blank_note_removes_the_file(tmp_path: Path) -> None:
    storage = StudyStorage(tmp_path, _manifest())
    initial = storage.get_note("first")
    saved = storage.put_note("first", "temporary", initial["revision"])

    cleared = storage.put_note("first", "  ", saved["revision"])

    assert cleared["body"] == ""
    assert not (tmp_path / "notes" / "first.md").exists()


def test_card_crud_filters_and_deterministic_json(tmp_path: Path) -> None:
    storage = StudyStorage(tmp_path, _manifest())
    first = storage.create_card(
        {
            "lesson_id": "first",
            "front": "Question?",
            "back": "Answer",
            "tags": ["Basics", "basics", " active recall "],
            "source_text": "Source",
        }
    )
    storage.create_card(
        {
            "lesson_id": "second",
            "front": "Other?",
            "back": "Other answer",
            "tags": ["other"],
        }
    )

    assert first["tags"] == ["basics", "active-recall"]
    assert [card["id"] for card in storage.list_cards(tag="basics")] == [
        first["id"]
    ]
    assert len(storage.list_cards(chapter_id="chapter-0")) == 2
    assert [card["id"] for card in storage.list_cards(query="recall")] == [
        first["id"]
    ]

    updated = storage.update_card(
        first["id"],
        {"front": "Updated?", "tags": ["updated"]},
    )
    assert updated["front"] == "Updated?"
    assert updated["tags"] == ["updated"]

    card_path = tmp_path / "cards" / f"{first['id']}.json"
    parsed = json.loads(card_path.read_text(encoding="utf-8"))
    expected = json.dumps(parsed, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    assert card_path.read_text(encoding="utf-8") == expected
    assert not list(tmp_path.rglob("*.tmp"))


def test_progress_hash_and_review_marker_semantics(tmp_path: Path) -> None:
    manifest = _manifest()
    storage = StudyStorage(tmp_path, manifest)
    card = storage.create_card(
        {
            "lesson_id": "first",
            "front": "Question?",
            "back": "Answer",
        }
    )

    assert storage.set_progress("first", True)["completed"] is True
    assert storage.mark_again(card["id"])["needs_review"] is True
    marker = tmp_path / "reviews" / f"{card['id']}.json"
    assert marker.is_file()

    changed_first = replace(manifest.lessons[0], content_hash="changed")
    changed_manifest = CourseManifest(
        lessons=tuple(apply_neighbors([changed_first, manifest.lessons[1]]))
    )
    restarted = StudyStorage(tmp_path, changed_manifest)
    assert restarted.get_progress("first")["content_updated"] is True
    assert restarted.list_cards(needs_review=True)[0]["id"] == card["id"]

    restarted.mark_got_it(card["id"])
    assert not marker.exists()
    restarted.set_progress("first", False)
    assert not (tmp_path / "progress" / "first.json").exists()


def test_deleting_card_removes_its_review_marker(tmp_path: Path) -> None:
    storage = StudyStorage(tmp_path, _manifest())
    card = storage.create_card(
        {
            "lesson_id": "first",
            "front": "Question?",
            "back": "Answer",
        }
    )
    storage.mark_again(card["id"])

    storage.delete_card(card["id"])

    assert not (tmp_path / "cards" / f"{card['id']}.json").exists()
    assert not (tmp_path / "reviews" / f"{card['id']}.json").exists()
    with pytest.raises(StudyNotFoundError):
        storage.get_card(card["id"])


@pytest.mark.parametrize("unsafe_id", ["../first", "FIRST", "first/second", ""])
def test_unsafe_lesson_ids_never_become_paths(
    tmp_path: Path,
    unsafe_id: str,
) -> None:
    storage = StudyStorage(tmp_path, _manifest())

    with pytest.raises((StudyValidationError, StudyNotFoundError)):
        storage.get_note(unsafe_id)

    assert list(tmp_path.iterdir()) == []
