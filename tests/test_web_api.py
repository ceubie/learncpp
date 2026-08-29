from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup

from study_app import create_app
from study_app.catalog import LessonRecord, lesson_content_hash, write_manifest


def _document(
    lesson_id: str,
    title: str,
    *,
    stale_link: str = "",
) -> str:
    return f"""<!doctype html>
    <html><head><title>{title}</title></head><body><main>
    <h1>{title}</h1>
    <div class="source">
      <a href="https://www.learncpp.com/cpp-tutorial/{lesson_id}/">source</a>
    </div>
    <nav class="lesson-navigation">
      <a class="nav-button" href="999-stale.html">Next</a>
    </nav>
    <div class="entry-content">
      <p>Body {stale_link}</p>
      <details class="local-quiz-answer">
        <summary></summary><div class="wpsolution">Answer</div>
      </details>
    </div>
    </main></body></html>"""


def _application(tmp_path: Path):
    course = tmp_path / "course"
    study = tmp_path / "study"
    course.mkdir()
    first_document = _document(
        "first",
        "0.1 — First",
        stale_link='<a href="777-removed.html#part">Removed</a>',
    )
    second_document = _document("second", "0.9 — Second")
    records = [
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
            content_hash=lesson_content_hash(first_document),
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
            content_hash=lesson_content_hash(second_document),
        ),
    ]
    (course / "001-first.html").write_text(first_document, encoding="utf-8")
    (course / "004-second.html").write_text(second_document, encoding="utf-8")
    (course / "index.html").write_text("index", encoding="utf-8")
    write_manifest(course / "manifest.json", records)
    app = create_app(
        {
            "TESTING": True,
            "COURSE_DIR": course,
            "STUDY_DATA_DIR": study,
        }
    )
    return app, study


def test_lesson_route_rewrites_navigation_and_repairs_quiz(
    tmp_path: Path,
) -> None:
    app, _ = _application(tmp_path)
    response = app.test_client().get("/course/001-first.html")
    soup = BeautifulSoup(response.get_data(as_text=True), "html.parser")

    assert response.status_code == 200
    assert soup.select_one("nav.lesson-navigation a:last-of-type")["href"] == (
        "/course/004-second.html"
    )
    assert soup.find("a", string="Removed")["href"] == (
        "https://www.learncpp.com/cpp-tutorial/removed/#part"
    )
    assert soup.select_one(".local-quiz-answer > summary").get_text(strip=True) == (
        "Show solution"
    )
    assert soup.select_one("#study-context") is not None


def test_page_routes_handle_redirects_and_unknown_lessons(tmp_path: Path) -> None:
    app, _ = _application(tmp_path)
    client = app.test_client()

    assert client.get("/course/index.html").status_code == 302
    assert client.get("/course/nope.html").status_code == 404
    assert client.get("/notes").status_code == 200
    assert client.get("/cards").status_code == 200
    assert client.get("/review").status_code == 200


def test_missing_manifest_renders_setup_instead_of_traceback(
    tmp_path: Path,
) -> None:
    app = create_app(
        {
            "TESTING": True,
            "COURSE_DIR": tmp_path / "missing-course",
            "STUDY_DATA_DIR": tmp_path / "study",
        }
    )

    response = app.test_client().get("/")

    assert response.status_code == 200
    assert "Generate the local course first" in response.get_data(as_text=True)
    assert app.test_client().get("/api/catalog").status_code == 503


def test_mutation_rejects_cross_origin_and_non_json_requests(
    tmp_path: Path,
) -> None:
    app, study = _application(tmp_path)
    client = app.test_client()
    path = "/api/lessons/first/progress"

    cross_origin = client.put(
        path,
        json={"completed": True},
        headers={
            "X-Study-Request": "1",
            "Origin": "https://attacker.example",
        },
    )
    non_json = client.put(
        path,
        data="completed=true",
        headers={"X-Study-Request": "1"},
    )

    assert cross_origin.status_code == 403
    assert non_json.status_code == 415
    assert not study.exists()


def test_note_conflict_returns_current_server_copy(tmp_path: Path) -> None:
    app, _ = _application(tmp_path)
    client = app.test_client()
    path = "/api/lessons/first/note"
    initial = client.get(path).get_json()
    first = client.put(
        path,
        json={"body": "first", "base_revision": initial["revision"]},
        headers={"X-Study-Request": "1"},
    )
    conflict = client.put(
        path,
        json={"body": "stale", "base_revision": initial["revision"]},
        headers={"X-Study-Request": "1"},
    )

    assert first.status_code == 200
    assert conflict.status_code == 409
    assert conflict.get_json()["current"]["body"] == "first"
