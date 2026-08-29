from __future__ import annotations

from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from scraper import (
    convert_quiz_sections,
    finalize_lesson_document,
    remove_dead_quiz_labels,
)
from study_app.catalog import (
    CatalogError,
    CourseManifest,
    LessonRecord,
    discover_lesson_records,
    lesson_content_hash,
    read_manifest,
    validate_course_artifact,
    write_manifest,
)


def _homepage(*, duplicate_slug: bool = False) -> str:
    second_url = (
        "https://learncpp.com/cpp-tutorial/first/"
        if duplicate_slug
        else "https://www.learncpp.com/cpp-tutorial/summary/"
    )
    return f"""
    <div class="lessontable">
      <div class="lessontable-header">
        <div class="lessontable-header-chapter">Chapter&nbsp;0</div>
        <div class="lessontable-header-title">Getting Started</div>
      </div>
      <div class="lessontable-row">
        <div class="lessontable-row-number">0.1</div>
        <div class="lessontable-row-title">
          <a href="/cpp-tutorial/first/">First lesson</a>
        </div>
      </div>
      <div class="lessontable-row">
        <div class="lessontable-row-number">0.x</div>
        <div class="lessontable-row-title">
          <a href="{second_url}">Chapter summary and quiz</a>
        </div>
      </div>
    </div>
    <div class="lessontable">
      <div class="lessontable-header">
        <div class="lessontable-header-chapter">Chapter O</div>
        <div class="lessontable-header-title">Optional Bits</div>
      </div>
      <div class="lessontable-row">
        <div class="lessontable-row-number">O.7</div>
        <div class="lessontable-row-title">
          <a href="/cpp-tutorial/bits/">Bits</a>
        </div>
      </div>
    </div>
    """


def _document(title: str, body: str, extra: str = "") -> str:
    return f"""<!doctype html>
    <html><head><title>{title}</title></head><body><main>
    <h1>{title}</h1>
    <div class="source">
      <a href="https://www.learncpp.com/cpp-tutorial/first/">source</a>
    </div>
    <nav class="lesson-navigation"><a href="index.html">Contents</a></nav>
    <div class="entry-content">{body}{extra}</div>
    </main></body></html>"""


def _record(document: str) -> LessonRecord:
    return LessonRecord(
        id="first",
        source_url="https://www.learncpp.com/cpp-tutorial/first/",
        title="0.1 — First",
        chapter_id="chapter-0",
        chapter_label="Chapter 0",
        chapter_title="Getting Started",
        lesson_label="0.1",
        order=1,
        filename="001-first.html",
        kind="lesson",
        content_hash=lesson_content_hash(document),
    )


def test_structured_discovery_preserves_chapters_and_noncontiguous_labels() -> None:
    lessons = discover_lesson_records(_homepage())

    assert [lesson.id for lesson in lessons] == ["first", "summary", "bits"]
    assert lessons[0].chapter_id == "chapter-0"
    assert lessons[1].kind == "summary_quiz"
    assert lessons[2].chapter_id == "chapter-o"
    assert lessons[2].lesson_label == "O.7"
    assert lessons[1].previous_id == "first"
    assert lessons[1].next_id == "bits"


def test_discovery_rejects_duplicate_file_safe_ids() -> None:
    with pytest.raises(CatalogError, match="Duplicate lesson ID"):
        discover_lesson_records(_homepage(duplicate_slug=True))


def test_manifest_round_trip_and_artifact_validation(tmp_path: Path) -> None:
    document = _document("0.1 — First", "<p>Hello</p>")
    record = _record(document)
    (tmp_path / record.filename).write_text(document, encoding="utf-8")
    (tmp_path / "index.html").write_text("index", encoding="utf-8")

    written = write_manifest(tmp_path / "manifest.json", [record])
    loaded = read_manifest(tmp_path / "manifest.json")

    assert loaded == written
    assert validate_course_artifact(tmp_path, loaded) == []


def test_artifact_validation_reports_missing_and_broken_files(tmp_path: Path) -> None:
    document = _document(
        "0.1 — First",
        '<a href="999-missing.html">Missing</a>',
    )
    record = _record(document)
    (tmp_path / record.filename).write_text(document, encoding="utf-8")
    manifest = CourseManifest(lessons=(record,))

    problems = validate_course_artifact(tmp_path, manifest)

    assert any("Broken link" in problem for problem in problems)


def test_generated_quiz_summary_survives_dead_label_cleanup() -> None:
    soup = BeautifulSoup(
        '<div><p>Show solution</p><div class="wpsolution">Answer</div></div>',
        "html.parser",
    )

    convert_quiz_sections(soup)
    remove_dead_quiz_labels(soup)

    summary = soup.select_one("details.local-quiz-answer > summary")
    assert summary is not None
    assert summary.get_text(strip=True) == "Show solution"
    assert soup.find("p", string="Show solution") is None


def test_finalization_repairs_quiz_labels_and_missing_lesson_links() -> None:
    document = _document(
        "0.1 — First",
        (
            '<a href="002-missing-lesson.html#topic">Next topic</a>'
            '<details class="local-quiz-answer"><summary></summary>'
            '<div class="wpsolution">Answer</div></details>'
        ),
    )
    missing = LessonRecord(
        id="missing-lesson",
        source_url="https://www.learncpp.com/cpp-tutorial/missing-lesson/",
        title="Missing",
        chapter_id="chapter-0",
        chapter_label="Chapter 0",
        chapter_title="Getting Started",
        lesson_label="0.2",
        order=2,
        filename="002-missing-lesson.html",
        kind="lesson",
    )

    finalized = finalize_lesson_document(
        document=document,
        previous_filename=None,
        next_filename=None,
        available_filenames={"001-first.html"},
        discovered_by_id={"missing-lesson": missing},
    )
    soup = BeautifulSoup(finalized, "html.parser")

    assert soup.select_one(".local-quiz-answer > summary").get_text(strip=True) == (
        "Show solution"
    )
    assert soup.find("a", string="Next topic")["href"] == (
        "https://www.learncpp.com/cpp-tutorial/missing-lesson/#topic"
    )
