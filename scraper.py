from __future__ import annotations

import argparse
import re
import time
from dataclasses import replace
from html import escape
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import CppLexer

from study_app.catalog import (
    LessonRecord,
    apply_neighbors,
    discover_lesson_records,
    lesson_content_hash,
    validate_course_artifact,
    write_manifest,
)

BASE_URL = "https://www.learncpp.com/"
TUTORIAL_PATH = "/cpp-tutorial/"

USER_AGENT = "PersonalLearnCppReader/1.0"
DEFAULT_DELAY = 1.0


# =========================================================
# HTTP / ROBOTS
# =========================================================

def create_session() -> requests.Session:
    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
        }
    )

    return session


def load_robots(
    session: requests.Session,
) -> RobotFileParser | None:

    robots_url = urljoin(
        BASE_URL,
        "robots.txt",
    )

    parser = RobotFileParser()
    parser.set_url(robots_url)

    try:
        response = session.get(
            robots_url,
            timeout=30,
        )

        print(
            f"robots.txt status: "
            f"{response.status_code}"
        )

        if response.status_code == 404:
            return None

        response.raise_for_status()

        parser.parse(
            response.text.splitlines()
        )

        return parser

    except requests.RequestException as exc:
        print(
            "Warning: could not read "
            f"robots.txt: {exc}"
        )

        return None


def fetch_page(
    session: requests.Session,
    url: str,
    robots: RobotFileParser | None,
) -> str:

    if (
        robots is not None
        and not robots.can_fetch(
            USER_AGENT,
            url,
        )
    ):
        raise RuntimeError(
            "robots.txt does not permit "
            f"fetching: {url}"
        )

    response = session.get(
        url,
        timeout=30,
    )

    response.raise_for_status()

    return response.text


# =========================================================
# URL HELPERS
# =========================================================

def normalize_url(
    url: str,
) -> str:
    """
    Normalize a LearnCpp lesson URL for dictionary lookups.

    Removes query parameters and fragments and ensures
    the path ends in a slash.
    """

    parsed = urlparse(url)

    path = parsed.path

    if not path.endswith("/"):
        path += "/"

    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            path,
            "",
            "",
            "",
        )
    )


def is_lesson_url(
    url: str,
) -> bool:

    parsed = urlparse(url)

    host = parsed.netloc.lower()

    if host not in {
        "learncpp.com",
        "www.learncpp.com",
    }:
        return False

    return parsed.path.startswith(
        TUTORIAL_PATH
    )


def slug_from_url(
    url: str,
) -> str:

    path = urlparse(
        url
    ).path.rstrip("/")

    slug = path.split("/")[-1]

    slug = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "-",
        slug,
    )

    return slug.strip("-")


def lesson_filename(
    number: int,
    url: str,
) -> str:

    slug = slug_from_url(url)

    return (
        f"{number:03d}-"
        f"{slug}.html"
    )


# =========================================================
# LESSON DISCOVERY
# =========================================================

def discover_course(
    session: requests.Session,
    robots: RobotFileParser | None,
) -> list[LessonRecord]:

    print(
        "Reading LearnCpp "
        "table of contents..."
    )

    html = fetch_page(
        session,
        BASE_URL,
        robots,
    )

    return discover_lesson_records(
        html,
        base_url=BASE_URL,
    )


def discover_lessons(
    session: requests.Session,
    robots: RobotFileParser | None,
) -> list[str]:
    """Compatibility wrapper returning canonical lesson URLs."""

    return [
        lesson.source_url
        for lesson in discover_course(
            session,
            robots,
        )
    ]


def build_lesson_map(
    lessons: list[str],
) -> dict[str, str]:
    """
    Maps:

    https://www.learncpp.com/cpp-tutorial/comments/

    to:

    015-comments.html

    or whatever its discovered sequence number is.
    """

    lesson_map: dict[str, str] = {}

    for number, url in enumerate(
        lessons,
        start=1,
    ):
        lesson_map[
            normalize_url(url)
        ] = lesson_filename(
            number,
            url,
        )

    return lesson_map


# =========================================================
# SYNTAX HIGHLIGHTING
# =========================================================

def highlight_code_blocks(
    content,
) -> None:

    lexer = CppLexer()

    formatter = HtmlFormatter(
        nowrap=True,
        style="github-dark",
    )

    code_blocks = content.select(
        "pre.language-cpp code, "
        "pre code.language-cpp"
    )

    for code in code_blocks:

        source = code.get_text()

        highlighted = highlight(
            source,
            lexer,
            formatter,
        )

        highlighted_soup = (
            BeautifulSoup(
                highlighted,
                "html.parser",
            )
        )

        code.clear()

        for child in list(
            highlighted_soup.contents
        ):
            code.append(child)


# =========================================================
# QUIZZES
# =========================================================

def convert_quiz_sections(
    content,
) -> None:

    for solution in content.select(
        ".wpsolution"
    ):
        solution.attrs.pop(
            "style",
            None,
        )

        details = content.new_tag(
            "details"
        )

        details["class"] = [
            "local-quiz-answer"
        ]

        summary = content.new_tag(
            "summary"
        )

        summary.string = (
            "Show solution"
        )

        details.append(
            summary
        )

        solution.replace_with(
            details
        )

        details.append(
            solution
        )

    for hint in content.select(
        ".wphint"
    ):
        hint.attrs.pop(
            "style",
            None,
        )

        details = content.new_tag(
            "details"
        )

        details["class"] = [
            "local-quiz-hint"
        ]

        summary = content.new_tag(
            "summary"
        )

        summary.string = (
            "Show hint"
        )

        details.append(
            summary
        )

        hint.replace_with(
            details
        )

        details.append(
            hint
        )


def remove_dead_quiz_labels(
    content,
) -> None:

    for element in list(
        content.find_all(
            string=True
        )
    ):
        text = element.strip()

        if text in {
            "Show Solution",
            "Show solution",
            "Show Hint",
            "Show hint",
        }:
            parent = element.parent

            if (
                parent is not None
                and parent.name == "summary"
            ):
                continue

            if (
                parent is not None
                and parent.name == "p"
                and parent.get_text(
                    " ",
                    strip=True,
                ) == text
            ):
                parent.decompose()

            else:
                element.extract()


# =========================================================
# LINK REWRITING
# =========================================================

def rewrite_links(
    content,
    current_url: str,
    lesson_map: dict[str, str] | None,
) -> None:
    """
    Rewrite LearnCpp lesson links to local HTML files.

    External links remain normal web links.

    Same-page #anchor links remain unchanged.
    """

    for link in content.find_all(
        "a",
        href=True,
    ):

        href = link[
            "href"
        ].strip()

        if not href:
            continue

        # Same-page anchor.
        if href.startswith("#"):
            continue

        # Kill JavaScript-only links.
        if href.lower().startswith(
            "javascript:"
        ):
            link.unwrap()
            continue

        absolute_url = urljoin(
            current_url,
            href,
        )

        parsed = urlparse(
            absolute_url
        )

        fragment = parsed.fragment

        url_without_fragment = (
            urlunparse(
                (
                    parsed.scheme,
                    parsed.netloc,
                    parsed.path,
                    "",
                    parsed.query,
                    "",
                )
            )
        )

        # If this is a LearnCpp lesson and we've
        # discovered a local file for it, rewrite it.
        if (
            lesson_map is not None
            and is_lesson_url(
                url_without_fragment
            )
        ):
            normalized = normalize_url(
                url_without_fragment
            )

            local_filename = (
                lesson_map.get(
                    normalized
                )
            )

            if local_filename:

                if fragment:
                    local_filename += (
                        f"#{fragment}"
                    )

                link["href"] = (
                    local_filename
                )

                continue

        # Otherwise keep a normal absolute web URL.
        link["href"] = absolute_url


# =========================================================
# CLEAN ARTICLE
# =========================================================

def clean_content(
    content,
    url: str,
    lesson_map: dict[str, str] | None,
) -> None:

    selectors_to_remove = [
        "script",
        "style",
        "noscript",
        "iframe",
        "form",

        ".sharedaddy",
        ".entry-meta",
        ".entry-footer",
        ".post-navigation",
        ".prevnext",

        # Advertising / placeholders
        ".code-block",
        ".cf_monitor",

        "[id*='ezoic']",
        "[class*='ezoic']",
        "[data-ez-ph-id]",
    ]

    for selector in selectors_to_remove:

        for element in content.select(
            selector
        ):
            element.decompose()

    rewrite_links(
        content,
        current_url=url,
        lesson_map=lesson_map,
    )

    # Images can still load from LearnCpp when online.
    # The page itself and syntax highlighting remain local.
    for image in content.find_all(
        "img",
        src=True,
    ):
        image["src"] = urljoin(
            url,
            image["src"],
        )

    convert_quiz_sections(
        content
    )

    remove_dead_quiz_labels(
        content
    )

    highlight_code_blocks(
        content
    )


# =========================================================
# LOCAL NAVIGATION
# =========================================================

def build_navigation(
    previous_filename: str | None,
    next_filename: str | None,
) -> str:

    if previous_filename:
        previous_html = (
            f'<a class="nav-button" '
            f'href="{escape(previous_filename, quote=True)}">'
            f'← Previous'
            f'</a>'
        )
    else:
        previous_html = (
            '<span class="nav-button disabled">'
            '← Previous'
            '</span>'
        )

    if next_filename:
        next_html = (
            f'<a class="nav-button" '
            f'href="{escape(next_filename, quote=True)}">'
            f'Next →'
            f'</a>'
        )
    else:
        next_html = (
            '<span class="nav-button disabled">'
            'Next →'
            '</span>'
        )

    return f"""
<nav class="lesson-navigation">

    {previous_html}

    <a
        class="nav-button home-button"
        href="index.html"
    >
        Contents
    </a>

    {next_html}

</nav>
"""


# =========================================================
# LESSON HTML
# =========================================================

def extract_lesson(
    html: str,
    url: str,
    lesson_map: dict[str, str] | None = None,
    previous_filename: str | None = None,
    next_filename: str | None = None,
) -> tuple[str, str]:

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    title_element = (
        soup.select_one(
            "h1.entry-title"
        )
        or soup.select_one(
            "article h1"
        )
        or soup.select_one(
            "h1"
        )
    )

    if title_element is None:
        raise RuntimeError(
            "Could not find lesson title: "
            f"{url}"
        )

    title = title_element.get_text(
        " ",
        strip=True,
    )

    content = (
        soup.select_one(
            ".entry-content"
        )
        or soup.select_one(
            "article .entry-content"
        )
    )

    if content is None:
        raise RuntimeError(
            "Could not find lesson content: "
            f"{url}"
        )

    clean_content(
        content,
        url,
        lesson_map,
    )

    safe_title = escape(
        title
    )

    safe_url = escape(
        url,
        quote=True,
    )

    navigation = build_navigation(
        previous_filename,
        next_filename,
    )

    pygments_css = HtmlFormatter(
        style="github-dark"
    ).get_style_defs(
        "pre code"
    )

    document = f"""<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="utf-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1"
>

<title>{safe_title}</title>

<style>

    {pygments_css}

    :root {{
        color-scheme: light dark;
    }}

    * {{
        box-sizing: border-box;
    }}

    html {{
        scroll-behavior: smooth;
    }}

    body {{
        font-family:
            system-ui,
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            sans-serif;

        line-height: 1.7;

        margin: 0;
        padding: 0;

        background: #f3f4f6;
        color: #222;
    }}

    main {{
        max-width: 900px;

        margin: 40px auto;
        padding: 50px 65px;

        background: white;

        border-radius: 10px;

        box-shadow:
            0 2px 14px
            rgba(0, 0, 0, 0.08);
    }}

    h1 {{
        line-height: 1.25;

        margin-top: 0;
        margin-bottom: 8px;
    }}

    h2,
    h3,
    h4 {{
        line-height: 1.3;

        margin-top: 2rem;
    }}

    .source {{
        margin-bottom: 25px;

        font-size: 0.85rem;

        opacity: 0.65;

        overflow-wrap: anywhere;
    }}

    a {{
        color: #2367c9;
    }}

    p {{
        margin: 1em 0;
    }}

    ul,
    ol {{
        padding-left: 2rem;

        margin: 1rem 0;
    }}

    li {{
        margin: 0.35rem 0;
    }}


    /* =================================================
       LOCAL NAVIGATION
       ================================================= */

    .lesson-navigation {{
        display: grid;

        grid-template-columns:
            1fr
            auto
            1fr;

        gap: 12px;

        align-items: center;

        margin:
            25px
            0
            35px
            0;

        padding:
            14px
            0;

        border-top:
            1px solid
            rgba(128, 128, 128, 0.25);

        border-bottom:
            1px solid
            rgba(128, 128, 128, 0.25);
    }}

    .lesson-navigation
    .nav-button {{
        display: inline-block;

        padding:
            8px
            12px;

        border-radius: 6px;

        text-decoration: none;

        font-weight: 600;
    }}

    .lesson-navigation
    .nav-button:first-child {{
        justify-self: start;
    }}

    .lesson-navigation
    .nav-button:last-child {{
        justify-self: end;
    }}

    .home-button {{
        justify-self: center;
    }}

    .nav-button:hover {{
        background:
            rgba(
                128,
                128,
                128,
                0.12
            );
    }}

    .nav-button.disabled {{
        opacity: 0.3;

        cursor: default;
    }}


    /* =================================================
       LEARNCPP HEADINGS
       ================================================= */

    .cpp-section {{
        font-size: 1.35rem;
        font-weight: 700;

        line-height: 1.35;

        margin-top: 2.5rem;
        margin-bottom: 0.8rem;

        padding-top: 0.4rem;
    }}

    .cpp-topline {{
        border-top:
            1px solid
            rgba(128, 128, 128, 0.3);

        padding-top: 1.5rem;
    }}


    /* =================================================
       INLINE CODE
       ================================================= */

    code {{
        font-family:
            "Cascadia Code",
            "JetBrains Mono",
            Consolas,
            monospace;

        font-size: 0.95em;
    }}

    :not(pre) > code {{
        padding:
            2px
            5px;

        border-radius: 4px;

        background: #eeeeee;
    }}


    /* =================================================
       CODE BLOCKS
       ================================================= */

    pre {{
        overflow-x: auto;

        margin:
            1.4rem
            0;

        padding:
            18px
            20px;

        border-radius: 8px;

        background: #0d1117;
        color: #f0f0f0;

        line-height: 1.55;

        tab-size: 4;
    }}

    pre code {{
        font-size: 0.93rem;
    }}


    /* =================================================
       LEARNCPP CALLOUTS
       ================================================= */

    .cpp-note {{
        margin:
            1.5rem
            0;

        padding:
            0
            18px
            16px
            18px;

        border-left:
            5px solid #888;

        border-radius: 6px;

        background:
            rgba(
                128,
                128,
                128,
                0.08
            );
    }}

    .cpp-note-title {{
        margin:
            0
            -18px
            12px
            -18px;

        padding:
            10px
            18px;

        font-weight: 700;

        border-bottom:
            1px solid
            rgba(
                128,
                128,
                128,
                0.25
            );
    }}

    .cpp-lightpurplebackground {{
        border-left-color: #8957e5;
    }}

    .cpp-lightbluebackground {{
        border-left-color: #2f81f7;
    }}

    .cpp-lightgreenbackground {{
        border-left-color: #3fb950;
    }}

    .cpp-lightredbackground {{
        border-left-color: #f85149;
    }}

    .cpp-lightyellowbackground {{
        border-left-color: #d29922;
    }}


    /* =================================================
       QUIZZES
       ================================================= */

    .cpp-quiz-question {{
        font-size: 1.1rem;
        font-weight: 700;

        margin-top: 2rem;
    }}

    details {{
        margin:
            0.8rem
            0
            1.3rem
            0;

        padding:
            10px
            14px;

        border:
            1px solid
            rgba(
                128,
                128,
                128,
                0.35
            );

        border-radius: 6px;
    }}

    summary {{
        cursor: pointer;

        font-weight: 600;

        user-select: none;
    }}

    details[open] summary {{
        margin-bottom: 10px;
    }}

    .wpsolution,
    .wphint {{
        display: block !important;
    }}


    /* =================================================
       TABLES / IMAGES / QUOTES
       ================================================= */

    blockquote {{
        border-left:
            4px solid #888;

        margin-left: 0;

        padding-left: 18px;
    }}

    table {{
        width: 100%;

        border-collapse: collapse;

        margin: 1.5rem 0;
    }}

    th,
    td {{
        border:
            1px solid #ccc;

        padding:
            8px
            12px;

        text-align: left;
    }}

    img {{
        max-width: 100%;

        height: auto;
    }}


    /* =================================================
       MOBILE
       ================================================= */

    @media
    (max-width: 700px) {{

        main {{
            margin: 0;

            padding:
                25px
                20px;

            border-radius: 0;
        }}

        .lesson-navigation {{
            grid-template-columns:
                1fr
                1fr;

            gap: 8px;
        }}

        .home-button {{
            grid-column:
                1
                /
                -1;

            grid-row: 1;

            justify-self: center;
        }}

    }}


    /* =================================================
       DARK MODE
       ================================================= */

    @media
    (prefers-color-scheme: dark) {{

        body {{
            background: #111;

            color: #ddd;
        }}

        main {{
            background: #191919;

            box-shadow: none;
        }}

        a {{
            color: #78a9ff;
        }}

        :not(pre) > code {{
            background: #292929;
        }}

        th,
        td {{
            border-color: #444;
        }}

        .cpp-note {{
            background:
                rgba(
                    255,
                    255,
                    255,
                    0.04
                );
        }}

        details {{
            background:
                rgba(
                    255,
                    255,
                    255,
                    0.025
                );
        }}

    }}

</style>

</head>

<body>

<main>

<h1>{safe_title}</h1>

<div class="source">
    Original lesson:
    <a href="{safe_url}">
        {safe_url}
    </a>
</div>

{navigation}

{str(content)}

{navigation}

</main>

</body>

</html>
"""

    return title, document


# =========================================================
# FILE OUTPUT
# =========================================================

def save_lesson(
    document: str,
    url: str,
    output_directory: Path,
    index: int | None = None,
    overwrite: bool = False,
) -> Path:

    slug = slug_from_url(
        url
    )

    filename = (
        f"{slug}.html"
        if index is None
        else (
            f"{index:03d}-"
            f"{slug}.html"
        )
    )

    destination = (
        output_directory
        / filename
    )

    if (
        destination.exists()
        and not overwrite
    ):
        print(
            "Skipping existing: "
            f"{destination.name}"
        )

        return destination

    destination.write_text(
        document,
        encoding="utf-8",
    )

    return destination


# =========================================================
# SINGLE LESSON
# =========================================================

def scrape_one(
    session: requests.Session,
    robots: RobotFileParser | None,
    url: str,
    output_directory: Path,
    overwrite: bool,
) -> None:

    url = normalize_url(
        url
    )

    if not is_lesson_url(
        url
    ):
        raise ValueError(
            "URL does not appear to be "
            "a LearnCpp tutorial lesson."
        )

    print(
        f"Fetching {url}"
    )

    html = fetch_page(
        session,
        url,
        robots,
    )

    title, document = extract_lesson(
        html,
        url,
    )

    destination = save_lesson(
        document=document,
        url=url,
        output_directory=(
            output_directory
        ),
        overwrite=overwrite,
    )

    print(
        f"Saved: {title}"
    )

    print(
        f" -> {destination}"
    )


# =========================================================
# INDEX
# =========================================================

def build_index(
    entries: list[
        tuple[str, str]
    ],
) -> str:

    items = "\n".join(
        f"""
        <li>
            <a
                href="{escape(filename, quote=True)}"
            >
                {escape(title)}
            </a>
        </li>
        """
        for title, filename
        in entries
    )

    return f"""<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="utf-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1"
>

<title>LearnCpp Offline</title>

<style>

    :root {{
        color-scheme: light dark;
    }}

    body {{
        font-family:
            system-ui,
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            sans-serif;

        line-height: 1.6;

        margin: 0;

        background: #f3f4f6;
        color: #222;
    }}

    main {{
        max-width: 850px;

        margin: 40px auto;
        padding: 50px 65px;

        background: white;

        border-radius: 10px;

        box-shadow:
            0 2px 14px
            rgba(0, 0, 0, 0.08);
    }}

    h1 {{
        margin-top: 0;
    }}

    ol {{
        padding-left: 2rem;
    }}

    li {{
        margin: 0.65rem 0;
    }}

    a {{
        color: #2367c9;

        text-decoration: none;
    }}

    a:hover {{
        text-decoration: underline;
    }}

    @media
    (max-width: 700px) {{

        main {{
            margin: 0;

            padding:
                25px
                20px;

            border-radius: 0;
        }}

    }}

    @media
    (prefers-color-scheme: dark) {{

        body {{
            background: #111;

            color: #ddd;
        }}

        main {{
            background: #191919;

            box-shadow: none;
        }}

        a {{
            color: #78a9ff;
        }}

    }}

</style>

</head>

<body>

<main>

<h1>LearnCpp Offline</h1>

<p>
    Personal offline lesson index.
</p>

<ol>

{items}

</ol>

</main>

</body>

</html>
"""


def finalize_lesson_document(
    document: str,
    previous_filename: str | None,
    next_filename: str | None,
    available_filenames: set[str],
    discovered_by_id: dict[str, LessonRecord],
) -> str:
    """
    Finalize navigation and local links after successful downloads are known.

    This keeps one failed or removed lesson from leaving every neighboring page
    with a broken navigation target.
    """

    soup = BeautifulSoup(
        document,
        "html.parser",
    )

    navigation = build_navigation(
        previous_filename,
        next_filename,
    )

    for old_navigation in list(
        soup.select(
            "nav.lesson-navigation"
        )
    ):
        navigation_soup = BeautifulSoup(
            navigation,
            "html.parser",
        )
        new_navigation = (
            navigation_soup.select_one(
                "nav.lesson-navigation"
            )
        )
        if new_navigation is not None:
            old_navigation.replace_with(
                new_navigation
            )

    for details, label in (
        (
            soup.select(
                "details.local-quiz-answer"
            ),
            "Show solution",
        ),
        (
            soup.select(
                "details.local-quiz-hint"
            ),
            "Show hint",
        ),
    ):
        for quiz_section in details:
            summary = quiz_section.find(
                "summary",
                recursive=False,
            )
            if (
                summary is not None
                and not summary.get_text(
                    " ",
                    strip=True,
                )
            ):
                summary.string = label

    for link in soup.select(
        "a[href]"
    ):
        href = str(
            link.get(
                "href",
                "",
            )
        )
        parsed = urlparse(
            href
        )
        target_name = Path(
            parsed.path
        ).name

        if (
            not target_name.endswith(
                ".html"
            )
            or target_name == "index.html"
            or target_name
            in available_filenames
        ):
            continue

        match = re.fullmatch(
            r"\d{3}-(.+)\.html",
            target_name,
        )
        if match is None:
            continue

        missing_lesson = (
            discovered_by_id.get(
                match.group(1)
            )
        )
        if missing_lesson is None:
            continue

        replacement_href = (
            missing_lesson.source_url
        )
        if parsed.fragment:
            replacement_href += (
                f"#{parsed.fragment}"
            )
        link["href"] = replacement_href

    return str(
        soup
    )


def finalize_course_documents(
    output_directory: Path,
    successful_lessons: list[LessonRecord],
    discovered_lessons: list[LessonRecord],
) -> list[LessonRecord]:
    successful_lessons = apply_neighbors(
        successful_lessons
    )
    successful_by_id = {
        lesson.id: lesson
        for lesson in successful_lessons
    }
    discovered_by_id = {
        lesson.id: lesson
        for lesson in discovered_lessons
    }
    available_filenames = {
        lesson.filename
        for lesson in successful_lessons
    }
    finalized: list[LessonRecord] = []

    for lesson in successful_lessons:
        previous_lesson = (
            successful_by_id.get(
                lesson.previous_id
            )
            if lesson.previous_id
            else None
        )
        next_lesson = (
            successful_by_id.get(
                lesson.next_id
            )
            if lesson.next_id
            else None
        )
        path = (
            output_directory
            / lesson.filename
        )
        document = path.read_text(
            encoding="utf-8"
        )
        document = finalize_lesson_document(
            document=document,
            previous_filename=(
                previous_lesson.filename
                if previous_lesson
                else None
            ),
            next_filename=(
                next_lesson.filename
                if next_lesson
                else None
            ),
            available_filenames=(
                available_filenames
            ),
            discovered_by_id=(
                discovered_by_id
            ),
        )
        path.write_text(
            document,
            encoding="utf-8",
        )
        finalized.append(
            replace(
                lesson,
                content_hash=(
                    lesson_content_hash(
                        document
                    )
                ),
            )
        )

    return apply_neighbors(
        finalized
    )


# =========================================================
# FULL SITE
# =========================================================

def build_existing_manifest(
    session: requests.Session,
    robots: RobotFileParser | None,
    output_directory: Path,
) -> None:
    """Build metadata for an existing generated course without refetching it."""

    discovered_lessons = discover_course(
        session,
        robots,
    )
    generated_by_url: dict[
        str,
        tuple[
            Path,
            str,
            str,
        ],
    ] = {}

    for path in sorted(
        output_directory.glob(
            "*.html"
        )
    ):
        if path.name == "index.html":
            continue
        document = path.read_text(
            encoding="utf-8"
        )
        soup = BeautifulSoup(
            document,
            "html.parser",
        )
        source_link = soup.select_one(
            ".source a[href]"
        )
        if source_link is None:
            continue
        source_url = normalize_url(
            str(
                source_link.get(
                    "href",
                    "",
                )
            )
        )
        heading = soup.select_one(
            "main > h1"
        )
        title = (
            heading.get_text(
                " ",
                strip=True,
            )
            if heading
            else path.stem
        )
        generated_by_url[source_url] = (
            path,
            title,
            lesson_content_hash(
                document
            ),
        )

    available: list[LessonRecord] = []
    for discovered in discovered_lessons:
        generated = generated_by_url.get(
            normalize_url(
                discovered.source_url
            )
        )
        if generated is None:
            continue
        path, title, content_hash = generated
        available.append(
            replace(
                discovered,
                filename=path.name,
                title=title,
                content_hash=content_hash,
            )
        )

    if not available:
        raise RuntimeError(
            "No generated LearnCpp lessons were found "
            f"in {output_directory}."
        )

    manifest = write_manifest(
        output_directory
        / "manifest.json",
        available,
    )
    print(
        "Wrote manifest for "
        f"{len(manifest.lessons)} existing lessons."
    )


def scrape_all(
    session: requests.Session,
    robots: RobotFileParser | None,
    output_directory: Path,
    delay: float,
    overwrite: bool,
) -> None:

    discovered_lessons = discover_course(
        session,
        robots,
    )
    lessons = [
        lesson.source_url
        for lesson in discovered_lessons
    ]

    print(
        f"Found {len(lessons)} lessons."
    )

    print()

    # This mapping is what lets every page know
    # the LOCAL filename of every other lesson.
    lesson_map = build_lesson_map(
        lessons
    )

    successful_lessons: list[
        LessonRecord
    ] = []

    for number, discovered in enumerate(
        discovered_lessons,
        start=1,
    ):
        url = discovered.source_url

        print(
            f"[{number}/{len(discovered_lessons)}] "
            f"{url}"
        )

        filename = lesson_map[
            normalize_url(
                url
            )
        ]
        lesson = replace(
            discovered,
            order=number,
            filename=filename,
        )

        destination = (
            output_directory
            / filename
        )

        previous_filename = None
        next_filename = None

        if number > 1:

            previous_url = lessons[
                number - 2
            ]

            previous_filename = (
                lesson_map[
                    normalize_url(
                        previous_url
                    )
                ]
            )

        if number < len(
            lessons
        ):

            next_url = lessons[
                number
            ]

            next_filename = (
                lesson_map[
                    normalize_url(
                        next_url
                    )
                ]
            )

        try:

            if (
                destination.exists()
                and not overwrite
            ):
                print(
                    "    Already downloaded, "
                    "skipping."
                )

                existing_html = (
                    destination.read_text(
                        encoding="utf-8"
                    )
                )

                existing_soup = (
                    BeautifulSoup(
                        existing_html,
                        "html.parser",
                    )
                )

                existing_title = (
                    existing_soup.select_one(
                        "main > h1"
                    )
                )

                successful_lessons.append(
                    replace(
                        lesson,
                        title=(
                            existing_title.get_text(
                                " ",
                                strip=True,
                            )
                            if existing_title
                            else lesson.title
                        ),
                        content_hash=(
                            lesson_content_hash(
                                existing_html
                            )
                        ),
                    )
                )

                continue

            html = fetch_page(
                session,
                url,
                robots,
            )

            title, document = (
                extract_lesson(
                    html,
                    url,
                    lesson_map=(
                        lesson_map
                    ),
                    previous_filename=(
                        previous_filename
                    ),
                    next_filename=(
                        next_filename
                    ),
                )
            )

            destination.write_text(
                document,
                encoding="utf-8",
            )

            successful_lessons.append(
                replace(
                    lesson,
                    title=title,
                    content_hash=(
                        lesson_content_hash(
                            document
                        )
                    ),
                )
            )

            print(
                f"    Saved: {title}"
            )

        except Exception as exc:

            print(
                f"    ERROR: {exc}"
            )

        time.sleep(
            delay
        )

    if not successful_lessons:
        raise RuntimeError(
            "No lessons were available after scraping."
        )

    successful_lessons = (
        finalize_course_documents(
            output_directory=(
                output_directory
            ),
            successful_lessons=(
                successful_lessons
            ),
            discovered_lessons=(
                discovered_lessons
            ),
        )
    )

    index_entries = [
        (
            lesson.title,
            lesson.filename,
        )
        for lesson in successful_lessons
    ]
    index_document = build_index(
        index_entries
    )

    index_path = (
        output_directory
        / "index.html"
    )

    index_path.write_text(
        index_document,
        encoding="utf-8",
    )

    manifest = write_manifest(
        output_directory
        / "manifest.json",
        successful_lessons,
    )
    problems = validate_course_artifact(
        output_directory,
        manifest,
    )
    if problems:
        print()
        print(
            "Course validation failed:"
        )
        for problem in problems:
            print(
                f"    - {problem}"
            )
        raise RuntimeError(
            "Generated course contains "
            "invalid links or files."
        )

    print()

    print(
        "Done."
    )

    print(
        "Open this file:"
    )

    print(
        f"    {index_path}"
    )


# =========================================================
# CLI
# =========================================================

def main() -> None:

    parser = argparse.ArgumentParser(
        description=(
            "Save LearnCpp lessons "
            "as a clean local HTML site."
        )
    )

    group = (
        parser
        .add_mutually_exclusive_group(
            required=True
        )
    )

    group.add_argument(
        "--url",
        help=(
            "Download a single "
            "LearnCpp lesson."
        ),
    )

    group.add_argument(
        "--all",
        action="store_true",
        help=(
            "Download all lessons "
            "and build a local site."
        ),
    )

    group.add_argument(
        "--manifest-only",
        action="store_true",
        help=(
            "Build a manifest for existing "
            "generated lessons without refetching them."
        ),
    )

    parser.add_argument(
        "--output",
        default="course",
        help=(
            "Output directory "
            "(default: course)."
        ),
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY,
        help=(
            "Delay between requests "
            "(default: 1 second)."
        ),
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help=(
            "Overwrite existing lessons."
        ),
    )

    args = parser.parse_args()

    output_directory = Path(
        args.output
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    session = create_session()

    robots = load_robots(
        session
    )

    if args.manifest_only:
        build_existing_manifest(
            session=session,
            robots=robots,
            output_directory=(
                output_directory
            ),
        )
        return

    if args.url:

        scrape_one(
            session=session,
            robots=robots,
            url=args.url,
            output_directory=(
                output_directory
            ),
            overwrite=args.overwrite,
        )

        return

    delay = max(
        args.delay,
        1.0,
    )

    scrape_all(
        session=session,
        robots=robots,
        output_directory=(
            output_directory
        ),
        delay=delay,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()