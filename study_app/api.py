from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from flask import Blueprint, Response, abort, current_app, jsonify, request

from .catalog import CourseManifest
from .storage import (
    StudyConflictError,
    StudyNotFoundError,
    StudyStorage,
    StudyStorageError,
    StudyValidationError,
)

api_blueprint = Blueprint("api", __name__)
MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _manifest() -> CourseManifest | None:
    value = current_app.extensions.get("course_manifest")
    return value if isinstance(value, CourseManifest) else None


def _storage() -> StudyStorage:
    value = current_app.extensions.get("study_storage")
    if not isinstance(value, StudyStorage):
        abort(503, description="Study storage is unavailable without a course.")
    return value


def _payload() -> dict[str, Any]:
    value = request.get_json(silent=True)
    if not isinstance(value, dict):
        raise StudyValidationError("Request body must be a JSON object.")
    return value


def _request_host() -> str:
    parsed = urlparse(f"//{request.host}")
    return (parsed.hostname or "").lower()


@api_blueprint.before_request
def protect_mutations() -> Response | None:
    if request.method not in MUTATING_METHODS:
        return None
    if _request_host() not in LOOPBACK_HOSTS:
        return jsonify(error="Mutation requests must use a loopback host."), 403
    if request.headers.get("X-Study-Request") != "1":
        return jsonify(error="Missing study request header."), 403
    if not request.is_json:
        return jsonify(error="Mutation requests must contain JSON."), 415

    origin = request.headers.get("Origin")
    if origin:
        origin_host = (urlparse(origin).hostname or "").lower()
        if origin_host != _request_host():
            return jsonify(error="Cross-origin mutations are not allowed."), 403
    fetch_site = request.headers.get("Sec-Fetch-Site")
    if fetch_site and fetch_site not in {"same-origin", "none"}:
        return jsonify(error="Cross-site mutations are not allowed."), 403
    return None


@api_blueprint.errorhandler(StudyValidationError)
def handle_validation_error(exc: StudyValidationError) -> tuple[Response, int]:
    return jsonify(error=str(exc)), 400


@api_blueprint.errorhandler(StudyNotFoundError)
def handle_not_found_error(exc: StudyNotFoundError) -> tuple[Response, int]:
    return jsonify(error=str(exc)), 404


@api_blueprint.errorhandler(StudyConflictError)
def handle_conflict_error(exc: StudyConflictError) -> tuple[Response, int]:
    return jsonify(error=str(exc), current=exc.current), 409


@api_blueprint.errorhandler(StudyStorageError)
def handle_storage_error(exc: StudyStorageError) -> tuple[Response, int]:
    current_app.logger.exception("Study storage failure")
    return jsonify(error=str(exc)), 500


@api_blueprint.get("/catalog")
def catalog() -> Response:
    manifest = _manifest()
    if manifest is None:
        return (
            jsonify(
                error=current_app.extensions.get("course_manifest_error")
                or "Course manifest is unavailable."
            ),
            503,
        )
    return jsonify(manifest.to_dict())


@api_blueprint.get("/dashboard")
def dashboard() -> Response:
    storage = _storage()
    summary = storage.dashboard_summary()
    summary["orphans"] = storage.orphaned_files()
    return jsonify(summary)


@api_blueprint.get("/notes")
def notes() -> Response:
    return jsonify(notes=_storage().list_notes())


@api_blueprint.get("/lessons/<lesson_id>/note")
def get_note(lesson_id: str) -> Response:
    return jsonify(_storage().get_note(lesson_id))


@api_blueprint.put("/lessons/<lesson_id>/note")
def put_note(lesson_id: str) -> Response:
    value = _payload()
    body = value.get("body")
    base_revision = value.get("base_revision")
    if not isinstance(body, str) or not isinstance(base_revision, str):
        raise StudyValidationError("body and base_revision must be strings.")
    return jsonify(_storage().put_note(lesson_id, body, base_revision))


@api_blueprint.get("/lessons/<lesson_id>/progress")
def get_progress(lesson_id: str) -> Response:
    return jsonify(_storage().get_progress(lesson_id))


@api_blueprint.put("/lessons/<lesson_id>/progress")
def put_progress(lesson_id: str) -> Response:
    value = _payload()
    return jsonify(
        _storage().set_progress(
            lesson_id,
            value.get("completed"),
        )
    )


@api_blueprint.get("/cards")
def list_cards() -> Response:
    needs_review_value = request.args.get("needs_review")
    needs_review = None
    if needs_review_value is not None:
        normalized = needs_review_value.lower()
        if normalized not in {"true", "false"}:
            raise StudyValidationError("needs_review must be true or false.")
        needs_review = normalized == "true"
    return jsonify(
        cards=_storage().list_cards(
            lesson_id=request.args.get("lesson_id"),
            chapter_id=request.args.get("chapter_id"),
            tag=request.args.get("tag"),
            needs_review=needs_review,
            query=request.args.get("q", ""),
        )
    )


@api_blueprint.post("/cards")
def create_card() -> tuple[Response, int]:
    card = _storage().create_card(_payload())
    return jsonify(card), 201


@api_blueprint.get("/cards/<card_id>")
def get_card(card_id: str) -> Response:
    return jsonify(_storage().get_card(card_id))


@api_blueprint.patch("/cards/<card_id>")
def update_card(card_id: str) -> Response:
    return jsonify(_storage().update_card(card_id, _payload()))


@api_blueprint.delete("/cards/<card_id>")
def delete_card(card_id: str) -> Response:
    _storage().delete_card(card_id)
    return Response(status=204)


@api_blueprint.put("/reviews/<card_id>")
def mark_again(card_id: str) -> Response:
    return jsonify(_storage().mark_again(card_id))


@api_blueprint.delete("/reviews/<card_id>")
def mark_got_it(card_id: str) -> Response:
    return jsonify(_storage().mark_got_it(card_id))


@api_blueprint.get("/health")
def health() -> Response:
    return jsonify(
        status="ok",
        course_ready=_manifest() is not None,
    )
