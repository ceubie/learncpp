from __future__ import annotations

from pathlib import Path

from study_app import create_app
from study_app.catalog import LessonRecord, lesson_content_hash, write_manifest

MUTATION_HEADERS = {"X-Study-Request": "1"}


def _build_course(course_directory: Path) -> LessonRecord:
    course_directory.mkdir()
    document = """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>0.1 — Intro</title></head>
<body>
<main>
<h1>0.1 — Intro</h1>
<div class="source">
  <a href="https://www.learncpp.com/cpp-tutorial/intro/">source</a>
</div>
<nav class="lesson-navigation"><a href="index.html">Contents</a></nav>
<div class="entry-content"><p>Every program has a main function.</p></div>
</main>
</body>
</html>
"""
    lesson = LessonRecord(
        id="intro",
        source_url="https://www.learncpp.com/cpp-tutorial/intro/",
        title="0.1 — Intro",
        chapter_id="chapter-0",
        chapter_label="Chapter 0",
        chapter_title="Getting started",
        lesson_label="0.1",
        order=1,
        filename="001-intro.html",
        kind="lesson",
        content_hash=lesson_content_hash(document),
    )
    (course_directory / lesson.filename).write_text(document, encoding="utf-8")
    (course_directory / "index.html").write_text("index", encoding="utf-8")
    write_manifest(course_directory / "manifest.json", [lesson])
    return lesson


def _app(course_directory: Path, study_directory: Path):
    return create_app(
        {
            "TESTING": True,
            "COURSE_DIR": course_directory,
            "STUDY_DATA_DIR": study_directory,
        }
    )


def test_vertical_slice_survives_restart(tmp_path: Path) -> None:
    course_directory = tmp_path / "course"
    study_directory = tmp_path / "study_data"
    lesson = _build_course(course_directory)
    client = _app(course_directory, study_directory).test_client()

    lesson_response = client.get(f"/course/{lesson.filename}")
    assert lesson_response.status_code == 200
    assert b"study-context" in lesson_response.data

    note = client.get(f"/api/lessons/{lesson.id}/note").get_json()
    note_response = client.put(
        f"/api/lessons/{lesson.id}/note",
        json={
            "body": "## Recall\n\nEvery program starts in `main()`.",
            "base_revision": note["revision"],
        },
        headers=MUTATION_HEADERS,
    )
    assert note_response.status_code == 200
    assert (study_directory / "notes" / "intro.md").is_file()

    card_response = client.post(
        "/api/cards",
        json={
            "lesson_id": lesson.id,
            "front": "Where does a C++ program begin?",
            "back": "In `main()`.",
            "tags": ["functions", "fundamentals"],
            "source_text": "Every program has a main function.",
            "source_prefix": "",
            "source_suffix": "",
        },
        headers=MUTATION_HEADERS,
    )
    assert card_response.status_code == 201
    card = card_response.get_json()
    card_path = study_directory / "cards" / f"{card['id']}.json"
    assert card_path.is_file()

    progress_response = client.put(
        f"/api/lessons/{lesson.id}/progress",
        json={"completed": True},
        headers=MUTATION_HEADERS,
    )
    assert progress_response.get_json()["completed"] is True
    assert (study_directory / "progress" / "intro.json").is_file()

    again_response = client.put(
        f"/api/reviews/{card['id']}",
        json={},
        headers=MUTATION_HEADERS,
    )
    assert again_response.get_json()["needs_review"] is True
    marker_path = study_directory / "reviews" / f"{card['id']}.json"
    assert marker_path.is_file()

    restarted_client = _app(course_directory, study_directory).test_client()
    restarted_note = restarted_client.get(
        f"/api/lessons/{lesson.id}/note"
    ).get_json()
    assert "`main()`" in restarted_note["body"]
    assert restarted_client.get(f"/api/cards/{card['id']}").get_json()[
        "needs_review"
    ] is True
    assert restarted_client.get(
        f"/api/lessons/{lesson.id}/progress"
    ).get_json()["completed"] is True
    review_queue = restarted_client.get(
        "/api/cards?needs_review=true"
    ).get_json()["cards"]
    assert [item["id"] for item in review_queue] == [card["id"]]

    got_it_response = restarted_client.delete(
        f"/api/reviews/{card['id']}",
        json={},
        headers=MUTATION_HEADERS,
    )
    assert got_it_response.get_json()["needs_review"] is False
    assert not marker_path.exists()

    tracked_files = {
        str(path.relative_to(study_directory))
        for path in study_directory.rglob("*")
        if path.is_file()
    }
    assert tracked_files == {
        str(Path("cards") / f"{card['id']}.json"),
        str(Path("notes") / "intro.md"),
        str(Path("progress") / "intro.json"),
    }


def test_mutations_require_study_header(tmp_path: Path) -> None:
    course_directory = tmp_path / "course"
    study_directory = tmp_path / "study_data"
    lesson = _build_course(course_directory)
    client = _app(course_directory, study_directory).test_client()

    response = client.put(
        f"/api/lessons/{lesson.id}/progress",
        json={"completed": True},
    )

    assert response.status_code == 403
    assert not study_directory.exists()
