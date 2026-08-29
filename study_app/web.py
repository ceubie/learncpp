from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    redirect,
    render_template,
    url_for,
)

from .catalog import CourseManifest, LessonRecord

web_blueprint = Blueprint("web", __name__)


def _manifest() -> CourseManifest | None:
    value = current_app.extensions.get("course_manifest")
    return value if isinstance(value, CourseManifest) else None


def _chapter_groups(
    manifest: CourseManifest,
) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    for lesson in manifest.lessons:
        group = by_id.get(lesson.chapter_id)
        if group is None:
            group = {
                "id": lesson.chapter_id,
                "label": lesson.chapter_label,
                "title": lesson.chapter_title,
                "lessons": [],
            }
            by_id[lesson.chapter_id] = group
            groups.append(group)
        group["lessons"].append(lesson)
    return groups


def _json_for_html(value: Any) -> str:
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )


def _rewrite_course_markup(
    document: str,
    lesson: LessonRecord,
    manifest: CourseManifest,
) -> str:
    soup = BeautifulSoup(document, "html.parser")
    by_id = manifest.by_id
    previous_lesson = by_id.get(lesson.previous_id or "")
    next_lesson = by_id.get(lesson.next_id or "")

    for navigation in soup.select("nav.lesson-navigation"):
        navigation.clear()
        if previous_lesson is None:
            previous = soup.new_tag("span", attrs={"class": "nav-button disabled"})
            previous.string = "← Previous"
        else:
            previous = soup.new_tag(
                "a",
                href=url_for("web.lesson", filename=previous_lesson.filename),
                attrs={"class": "nav-button"},
            )
            previous.string = "← Previous"
        contents = soup.new_tag(
            "a",
            href=url_for("web.dashboard"),
            attrs={"class": "nav-button home-button"},
        )
        contents.string = "Contents"
        if next_lesson is None:
            next_link = soup.new_tag(
                "span",
                attrs={"class": "nav-button disabled"},
            )
            next_link.string = "Next →"
        else:
            next_link = soup.new_tag(
                "a",
                href=url_for("web.lesson", filename=next_lesson.filename),
                attrs={"class": "nav-button"},
            )
            next_link.string = "Next →"
        navigation.extend([previous, contents, next_link])

    for link in soup.select("a[href]"):
        href = str(link.get("href", ""))
        parsed = urlparse(href)
        if parsed.scheme or parsed.netloc or parsed.path == "index.html":
            continue
        match = re.fullmatch(r"\d{3}-(.+)\.html", Path(parsed.path).name)
        if match is None:
            continue
        target_id = match.group(1)
        target = by_id.get(target_id)
        if target is not None:
            replacement = url_for("web.lesson", filename=target.filename)
        else:
            replacement = (
                "https://www.learncpp.com/cpp-tutorial/"
                f"{target_id}/"
            )
        if parsed.fragment:
            replacement += f"#{parsed.fragment}"
        link["href"] = replacement

    for selector, label in (
        ("details.local-quiz-answer", "Show solution"),
        ("details.local-quiz-hint", "Show hint"),
    ):
        for details in soup.select(selector):
            summary = details.find("summary", recursive=False)
            if summary is not None and not summary.get_text(" ", strip=True):
                summary.string = label
    return str(soup)


def _decorate_lesson(
    document: str,
    lesson: LessonRecord,
    manifest: CourseManifest,
) -> str:
    document = _rewrite_course_markup(document, lesson, manifest)
    stylesheet_url = url_for("static", filename="study.css")
    script_url = url_for("static", filename="study.js")
    context = {
        "page": "lesson",
        "lesson": lesson.to_dict(),
        "routes": {
            "home": url_for("web.dashboard"),
            "review": url_for("web.review"),
            "notes": url_for("web.notes"),
            "cards": url_for("web.cards"),
            "api": url_for("api.catalog"),
        },
    }
    head_addition = (
        f'<link rel="stylesheet" href="{stylesheet_url}" data-study-asset>'
        '<meta name="learncpp-study" content="enabled">'
    )
    body_addition = (
        '<script id="study-context" type="application/json">'
        f"{_json_for_html(context)}"
        "</script>"
        f'<script src="{script_url}" defer data-study-asset></script>'
    )
    if "</head>" not in document.lower() or "</body>" not in document.lower():
        raise ValueError("Generated lesson is missing head or body markup.")

    head_index = document.lower().rfind("</head>")
    document = document[:head_index] + head_addition + document[head_index:]
    body_index = document.lower().rfind("</body>")
    return document[:body_index] + body_addition + document[body_index:]


@web_blueprint.get("/")
def dashboard() -> str:
    manifest = _manifest()
    if manifest is None:
        return render_template(
            "setup.html",
            error=current_app.extensions.get("course_manifest_error"),
        )
    return render_template(
        "dashboard.html",
        chapters=_chapter_groups(manifest),
        lesson_count=len(manifest.lessons),
    )


@web_blueprint.get("/course/")
@web_blueprint.get("/course/index.html")
def course_index() -> Response:
    return redirect(url_for("web.dashboard"))


@web_blueprint.get("/course/<path:filename>")
def lesson(filename: str) -> Response:
    manifest = _manifest()
    if manifest is None:
        abort(503)
    lesson_record = manifest.by_filename.get(filename)
    if lesson_record is None:
        abort(404)

    course_directory = Path(current_app.config["COURSE_DIR"]).resolve()
    lesson_path = (course_directory / lesson_record.filename).resolve()
    try:
        lesson_path.relative_to(course_directory)
    except ValueError:
        abort(404)
    if not lesson_path.is_file():
        abort(404)

    try:
        document = lesson_path.read_text(encoding="utf-8")
        document = _decorate_lesson(document, lesson_record, manifest)
    except (OSError, UnicodeError, ValueError):
        current_app.logger.exception("Could not render %s", lesson_record.filename)
        abort(500)

    response = Response(document, content_type="text/html; charset=utf-8")
    response.headers["Cache-Control"] = "no-cache"
    return response


@web_blueprint.get("/notes")
def notes() -> str:
    return render_template("notes.html")


@web_blueprint.get("/cards")
def cards() -> str:
    return render_template("cards.html")


@web_blueprint.get("/review")
def review() -> str:
    return render_template("review.html")
