# LearnCpp Study Companion

Before using this, please make a donation to [LearnCpp.com](https://www.learncpp.com/about/#Support).

I created this because I could not focus on the course with the advertisements on the website. The ads 
help them pay for hosting the site. Scraping the content and making a donation is a fair trade. 

This is a private, local study app for a generated copy of
[LearnCpp.com](https://www.learncpp.com/). The generated course is disposable;
your Markdown notes, flashcards, progress, and review markers are ordinary files
under `study_data/` that can be synchronized with Git.

## Offline scope

The application is **offline-capable**, not fully offline. After an initial
scrape, lesson text, code, local navigation, notes, cards, progress, and review
work without a network connection. Lesson images and external links may still
require network access.

## Setup on Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python scraper.py --all
python app.py
```

Open <http://127.0.0.1:8000>. The server deliberately binds only to the local
machine.

If `course/` already contains lessons from an older scraper run, generate only
the new catalog metadata:

```powershell
python scraper.py --manifest-only
```

Use `python scraper.py --all --overwrite` when you intentionally want to
refresh every lesson. A full scrape now validates its manifest, navigation, and
local lesson links before reporting success.

## Study workflow

1. Open a lesson and use **Study** to edit its Markdown note.
2. Select lesson text and choose **Create card**. Write the question yourself.
3. Explicitly mark the lesson complete.
4. Review cards with Space to reveal, `1` for **Again**, and `2` for
   **Got it**.

The dashboard groups the real LearnCpp chapter/appendix structure, derives
**Continue** from explicit completions, and marks a completed lesson as updated
if its scraped content hash changes. Review can be scoped to one lesson, one
chapter, every card, or only cards marked **Again**.

Only intentional study actions change tracked files. Opening a lesson does not
record a timestamp or dirty the working tree.

## Data layout

```text
study_data/
├── notes/<lesson-id>.md
├── cards/<uuid>.json
├── progress/<lesson-id>.json
└── reviews/<card-id>.json
```

A review marker existing means that card needs review. **Got it** removes the
marker. There is no database or aggregate mutable index.

Notes use content-hash revisions. If two tabs or machines edit the same lesson
note from an outdated copy, the API returns a conflict instead of silently
overwriting the newer text. Card IDs are random and each card has its own file,
so independently created cards normally merge cleanly.

## Development checks

```powershell
python -m ruff check .
python -m pytest
```

## Generated content and Git history

`course/` is generated and ignored by Git. This repository's existing remote
history already contains an older generated copy, so `.gitignore` alone cannot
remove it. The safe migration is to create a fresh private repository after the
implementation is verified, push a new history that excludes `course/`, verify
the new remote, and only then retire the old repository. Do not force-push the
existing `main` branch.

The optional `python sync.py` helper stages only `study_data/`, creates a study
commit when needed, rebases from the private remote, and pushes. It refuses to
operate when unrelated changes are staged, when conflicts are unresolved, or
when the current branch has no upstream:

```powershell
python sync.py
python sync.py --message "Study chapter 4"
```

It never resolves conflicts automatically. If a rebase stops, resolve or abort
that rebase before running the helper again.
