from __future__ import annotations

from pathlib import Path
from typing import Any

from flask import Flask, Response

from .api import api_blueprint
from .catalog import CatalogError, read_manifest
from .storage import StudyStorage
from .web import web_blueprint


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    project_root = Path(__file__).resolve().parent.parent
    app = Flask(__name__)
    app.config.from_mapping(
        COURSE_DIR=project_root / "course",
        STUDY_DATA_DIR=project_root / "study_data",
        MAX_CONTENT_LENGTH=1_000_000,
        TRUSTED_HOSTS=["127.0.0.1", "localhost", "::1"],
    )
    if test_config:
        app.config.update(test_config)

    app.config["COURSE_DIR"] = Path(app.config["COURSE_DIR"])
    app.config["STUDY_DATA_DIR"] = Path(app.config["STUDY_DATA_DIR"])

    manifest_path = app.config["COURSE_DIR"] / "manifest.json"
    manifest = None
    manifest_error = None
    try:
        manifest = read_manifest(manifest_path)
    except FileNotFoundError:
        manifest_error = (
            "The generated course manifest is missing. "
            "Run: python scraper.py --all"
        )
    except CatalogError as exc:
        manifest_error = str(exc)

    app.extensions["course_manifest"] = manifest
    app.extensions["course_manifest_error"] = manifest_error
    app.extensions["study_storage"] = (
        StudyStorage(
            app.config["STUDY_DATA_DIR"],
            manifest,
        )
        if manifest is not None
        else None
    )
    app.register_blueprint(web_blueprint)
    app.register_blueprint(api_blueprint, url_prefix="/api")

    @app.after_request
    def add_security_headers(response: Response) -> Response:
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        return response

    return app


__all__ = ["create_app"]
