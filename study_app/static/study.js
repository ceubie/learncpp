(() => {
    "use strict";

    const MUTATION_HEADERS = {
        "Content-Type": "application/json",
        "X-Study-Request": "1",
    };

    class ApiError extends Error {
        constructor(message, status, payload) {
            super(message);
            this.name = "ApiError";
            this.status = status;
            this.payload = payload;
        }
    }

    async function apiRequest(path, options = {}) {
        const requestOptions = {
            method: options.method || "GET",
            headers: {},
        };
        if (Object.prototype.hasOwnProperty.call(options, "body")) {
            requestOptions.headers = MUTATION_HEADERS;
            requestOptions.body = JSON.stringify(options.body);
        }
        const response = await fetch(path, requestOptions);
        const payload =
            response.status === 204 ? null : await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new ApiError(
                payload && payload.error ? payload.error : `Request failed (${response.status})`,
                response.status,
                payload,
            );
        }
        return payload;
    }

    function showToast(message, tone = "default") {
        const toast = document.querySelector("#study-toast");
        if (!toast) {
            return;
        }
        toast.textContent = message;
        toast.dataset.tone = tone;
        toast.hidden = false;
        window.clearTimeout(showToast.timeout);
        showToast.timeout = window.setTimeout(() => {
            toast.hidden = true;
        }, 3200);
    }

    function repairQuizSummaries() {
        document.querySelectorAll("details.local-quiz-answer").forEach((details) => {
            const summary = details.querySelector(":scope > summary");
            if (summary && !summary.textContent.trim()) {
                summary.textContent = "Show solution";
            }
        });
        document.querySelectorAll("details.local-quiz-hint").forEach((details) => {
            const summary = details.querySelector(":scope > summary");
            if (summary && !summary.textContent.trim()) {
                summary.textContent = "Show hint";
            }
        });
    }

    function parseLessonContext() {
        const element = document.querySelector("#study-context");
        if (!element) {
            return null;
        }
        try {
            return JSON.parse(element.textContent);
        } catch (error) {
            console.error("Invalid study context", error);
            return null;
        }
    }

    function focusWithoutScroll(element) {
        element.focus({ preventScroll: true });
    }

    function initializeLesson(context) {
        const lesson = context.lesson;
        const lessonId = encodeURIComponent(lesson.id);
        const state = {
            noteRevision: "",
            noteBody: "",
            saveTimer: null,
            saving: false,
            selectedSource: null,
            cards: [],
            editingCardId: null,
        };

        const root = document.createElement("div");
        root.className = "study-lesson-tools";
        root.innerHTML = `
            <button
                class="study-launcher"
                type="button"
                aria-expanded="false"
                aria-controls="study-panel"
            >
                <span aria-hidden="true">✦</span>
                Study
            </button>
            <aside
                id="study-panel"
                class="study-panel"
                aria-label="Study tools"
                aria-hidden="true"
            >
                <header class="study-panel-header">
                    <div>
                        <span>Study tools</span>
                        <strong></strong>
                    </div>
                    <button class="study-icon-button" type="button" data-action="close" aria-label="Close study tools">×</button>
                </header>
                <div class="study-panel-progress">
                    <button class="study-complete-button" type="button" aria-pressed="false">
                        <span class="study-complete-check" aria-hidden="true"></span>
                        <span data-complete-label>Mark lesson complete</span>
                    </button>
                    <span class="study-content-updated" hidden>Lesson changed since completion</span>
                </div>
                <div class="study-tabs" role="tablist" aria-label="Study tools">
                    <button type="button" role="tab" aria-selected="true" aria-controls="study-notes-panel" id="study-notes-tab">Notes</button>
                    <button type="button" role="tab" aria-selected="false" aria-controls="study-cards-panel" id="study-cards-tab">Cards <span data-card-count>0</span></button>
                </div>
                <section id="study-notes-panel" class="study-tab-panel" role="tabpanel" aria-labelledby="study-notes-tab">
                    <label class="study-field">
                        <span class="study-field-label">Markdown note</span>
                        <textarea class="study-note-editor" placeholder="Explain the idea in your own words…" spellcheck="true"></textarea>
                    </label>
                    <div class="study-save-row">
                        <span class="study-save-status" role="status">Loading…</span>
                        <button class="study-text-button" type="button" data-action="reload-note" hidden>Reload saved note</button>
                    </div>
                </section>
                <section id="study-cards-panel" class="study-tab-panel" role="tabpanel" aria-labelledby="study-cards-tab" hidden>
                    <form class="study-card-form">
                        <div class="study-card-form-heading">
                            <strong data-card-form-title>Create a flashcard</strong>
                            <button class="study-text-button" type="button" data-action="clear-card">Clear</button>
                        </div>
                        <label class="study-field">
                            <span class="study-field-label">Front</span>
                            <textarea name="front" rows="3" placeholder="Write a question that makes you recall the idea" required></textarea>
                        </label>
                        <label class="study-field">
                            <span class="study-field-label">Back</span>
                            <textarea name="back" rows="4" placeholder="Answer in the fewest useful words" required></textarea>
                        </label>
                        <label class="study-field">
                            <span class="study-field-label">Tags</span>
                            <input name="tags" type="text" placeholder="functions, fundamentals">
                        </label>
                        <blockquote class="study-source-preview" hidden></blockquote>
                        <button class="study-primary-button study-full-button" type="submit" data-card-submit>Save card</button>
                    </form>
                    <div class="study-card-list-heading">
                        <strong>This lesson’s cards</strong>
                        <a href="${context.routes.review}?scope=lesson&amp;lesson_id=${encodeURIComponent(lesson.id)}">Review lesson</a>
                    </div>
                    <label class="study-field study-card-filter">
                        <span class="study-visually-hidden">Filter this lesson’s cards</span>
                        <input type="search" data-card-filter placeholder="Filter questions, answers, or tags">
                    </label>
                    <div class="study-lesson-card-list">
                        <p class="study-loading">Loading cards…</p>
                    </div>
                </section>
            </aside>
            <button class="study-selection-action" type="button" hidden>Create card</button>
        `;
        document.body.append(root);

        const launcher = root.querySelector(".study-launcher");
        const panel = root.querySelector(".study-panel");
        const closeButton = root.querySelector('[data-action="close"]');
        const title = root.querySelector(".study-panel-header strong");
        const tabButtons = [...root.querySelectorAll('[role="tab"]')];
        const noteEditor = root.querySelector(".study-note-editor");
        const noteStatus = root.querySelector(".study-save-status");
        const reloadNoteButton = root.querySelector('[data-action="reload-note"]');
        const completeButton = root.querySelector(".study-complete-button");
        const completeLabel = root.querySelector("[data-complete-label]");
        const updatedLabel = root.querySelector(".study-content-updated");
        const cardForm = root.querySelector(".study-card-form");
        const cardList = root.querySelector(".study-lesson-card-list");
        const cardCount = root.querySelector("[data-card-count]");
        const sourcePreview = root.querySelector(".study-source-preview");
        const cardFormTitle = root.querySelector("[data-card-form-title]");
        const cardSubmit = root.querySelector("[data-card-submit]");
        const cardFilter = root.querySelector("[data-card-filter]");
        const selectionAction = root.querySelector(".study-selection-action");
        const article = document.querySelector(".entry-content");
        const lessonFooter = document.createElement("section");
        lessonFooter.className = "study-lesson-checkpoint";
        lessonFooter.innerHTML = `
            <div>
                <span>Finished this lesson?</span>
                <strong>Mark it complete when you can explain the key idea.</strong>
            </div>
            <button class="study-secondary-button" type="button" data-footer-complete>
                Mark complete
            </button>
        `;
        const bottomNavigation = [...document.querySelectorAll("nav.lesson-navigation")].at(-1);
        if (bottomNavigation) {
            bottomNavigation.before(lessonFooter);
        } else {
            document.querySelector("main")?.append(lessonFooter);
        }
        const footerCompleteButton = lessonFooter.querySelector("[data-footer-complete]");

        title.textContent = lesson.title;

        function setPanel(open) {
            panel.setAttribute("aria-hidden", String(!open));
            launcher.setAttribute("aria-expanded", String(open));
            document.body.classList.toggle("study-panel-open", open);
            if (open) {
                focusWithoutScroll(panel.querySelector('[role="tab"][aria-selected="true"]'));
            } else {
                focusWithoutScroll(launcher);
            }
        }

        function activateTab(button, remember = true) {
            tabButtons.forEach((candidate) => {
                const selected = candidate === button;
                candidate.setAttribute("aria-selected", String(selected));
                candidate.tabIndex = selected ? 0 : -1;
                const controlled = document.querySelector(`#${candidate.getAttribute("aria-controls")}`);
                if (controlled) {
                    controlled.hidden = !selected;
                }
            });
            if (remember) {
                window.localStorage.setItem("learncpp-study-tab", button.id);
            }
        }

        launcher.addEventListener("click", () => {
            setPanel(panel.getAttribute("aria-hidden") === "true");
        });
        closeButton.addEventListener("click", () => setPanel(false));
        tabButtons.forEach((button) => {
            button.addEventListener("click", () => activateTab(button));
            button.addEventListener("keydown", (event) => {
                if (!["ArrowLeft", "ArrowRight"].includes(event.key)) {
                    return;
                }
                event.preventDefault();
                const direction = event.key === "ArrowRight" ? 1 : -1;
                const current = tabButtons.indexOf(button);
                const next = tabButtons[(current + direction + tabButtons.length) % tabButtons.length];
                activateTab(next);
                focusWithoutScroll(next);
            });
        });
        const preferredTabId = window.localStorage.getItem("learncpp-study-tab");
        const preferredTab = tabButtons.find((button) => button.id === preferredTabId);
        if (preferredTab) {
            activateTab(preferredTab, false);
        }
        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && panel.getAttribute("aria-hidden") === "false") {
                setPanel(false);
            }
        });

        async function loadNote() {
            noteStatus.textContent = "Loading…";
            reloadNoteButton.hidden = true;
            try {
                const note = await apiRequest(`/api/lessons/${lessonId}/note`);
                state.noteRevision = note.revision;
                state.noteBody = note.body;
                noteEditor.value = note.body;
                noteStatus.textContent = "Saved";
            } catch (error) {
                noteStatus.textContent = error.message;
            }
        }

        async function saveNote() {
            window.clearTimeout(state.saveTimer);
            if (state.saving || noteEditor.value === state.noteBody) {
                return;
            }
            state.saving = true;
            const sentBody = noteEditor.value;
            noteStatus.textContent = "Saving…";
            try {
                const note = await apiRequest(`/api/lessons/${lessonId}/note`, {
                    method: "PUT",
                    body: {
                        body: sentBody,
                        base_revision: state.noteRevision,
                    },
                });
                state.noteRevision = note.revision;
                state.noteBody = note.body;
                noteStatus.textContent = "Saved";
                if (noteEditor.value !== sentBody) {
                    scheduleNoteSave();
                }
            } catch (error) {
                if (error.status === 409) {
                    noteStatus.textContent = "Conflict — saved note changed";
                    reloadNoteButton.hidden = false;
                } else {
                    noteStatus.textContent = `Save failed — ${error.message}`;
                }
            } finally {
                state.saving = false;
            }
        }

        function scheduleNoteSave() {
            window.clearTimeout(state.saveTimer);
            noteStatus.textContent = "Editing…";
            state.saveTimer = window.setTimeout(saveNote, 750);
        }

        noteEditor.addEventListener("input", scheduleNoteSave);
        noteEditor.addEventListener("blur", saveNote);
        reloadNoteButton.addEventListener("click", loadNote);

        function applyProgress(progress) {
            completeButton.setAttribute("aria-pressed", String(progress.completed));
            completeLabel.textContent = progress.completed
                ? "Lesson complete"
                : "Mark lesson complete";
            footerCompleteButton.textContent = progress.completed
                ? "Completed ✓"
                : "Mark complete";
            footerCompleteButton.dataset.completed = String(progress.completed);
            updatedLabel.hidden = !progress.content_updated;
        }

        async function loadProgress() {
            try {
                applyProgress(
                    await apiRequest(`/api/lessons/${lessonId}/progress`),
                );
            } catch (error) {
                showToast(error.message, "error");
            }
        }

        async function toggleProgress() {
            const nextCompleted = completeButton.getAttribute("aria-pressed") !== "true";
            completeButton.disabled = true;
            footerCompleteButton.disabled = true;
            try {
                const progress = await apiRequest(`/api/lessons/${lessonId}/progress`, {
                    method: "PUT",
                    body: { completed: nextCompleted },
                });
                applyProgress(progress);
                showToast(progress.completed ? "Lesson marked complete" : "Completion cleared");
            } catch (error) {
                showToast(error.message, "error");
            } finally {
                completeButton.disabled = false;
                footerCompleteButton.disabled = false;
            }
        }

        completeButton.addEventListener("click", toggleProgress);
        footerCompleteButton.addEventListener("click", toggleProgress);

        function resetCardForm() {
            cardForm.reset();
            state.selectedSource = null;
            state.editingCardId = null;
            sourcePreview.hidden = true;
            sourcePreview.textContent = "";
            cardFormTitle.textContent = "Create a flashcard";
            cardSubmit.textContent = "Save card";
        }

        function editCard(card) {
            state.editingCardId = card.id;
            state.selectedSource = {
                text: card.source_text,
                prefix: card.source_prefix,
                suffix: card.source_suffix,
            };
            cardForm.elements.front.value = card.front;
            cardForm.elements.back.value = card.back;
            cardForm.elements.tags.value = card.tags.join(", ");
            sourcePreview.textContent = card.source_text;
            sourcePreview.hidden = !card.source_text;
            cardFormTitle.textContent = "Edit flashcard";
            cardSubmit.textContent = "Save changes";
            cardForm.scrollIntoView({ behavior: "smooth", block: "start" });
            focusWithoutScroll(cardForm.elements.front);
        }

        function renderCards() {
            cardCount.textContent = String(state.cards.length);
            const query = cardFilter.value.trim().toLowerCase();
            const cards = state.cards.filter((card) => {
                if (!query) {
                    return true;
                }
                return [card.front, card.back, ...card.tags]
                    .join(" ")
                    .toLowerCase()
                    .includes(query);
            });
            cardList.replaceChildren();
            if (!cards.length) {
                const empty = document.createElement("p");
                empty.className = "study-empty-copy";
                empty.textContent = state.cards.length
                    ? "No cards match that filter."
                    : "No cards for this lesson yet.";
                cardList.append(empty);
                return;
            }
            cards.forEach((card) => {
                const item = document.createElement("article");
                item.className = "study-mini-card";
                const front = document.createElement("strong");
                front.textContent = card.front;
                const back = document.createElement("p");
                back.textContent = card.back;
                const footer = document.createElement("div");
                const tags = document.createElement("span");
                tags.textContent = card.tags.map((tag) => `#${tag}`).join(" ");
                const actions = document.createElement("span");
                actions.className = "study-mini-card-actions";
                const edit = document.createElement("button");
                edit.type = "button";
                edit.className = "study-text-button";
                edit.textContent = "Edit";
                edit.addEventListener("click", () => editCard(card));
                const remove = document.createElement("button");
                remove.type = "button";
                remove.className = "study-text-button";
                remove.textContent = "Delete";
                remove.addEventListener("click", async () => {
                    if (!window.confirm("Delete this flashcard?")) {
                        return;
                    }
                    try {
                        await apiRequest(`/api/cards/${encodeURIComponent(card.id)}`, {
                            method: "DELETE",
                            body: {},
                        });
                        await loadCards();
                        showToast("Card deleted");
                    } catch (error) {
                        showToast(error.message, "error");
                    }
                });
                actions.append(edit, remove);
                footer.append(tags, actions);
                item.append(front, back);
                if (card.source_text) {
                    const source = document.createElement("details");
                    source.className = "study-mini-card-source";
                    const summary = document.createElement("summary");
                    summary.textContent = "Source selection";
                    const quote = document.createElement("blockquote");
                    quote.textContent = card.source_text;
                    source.append(summary, quote);
                    item.append(source);
                }
                if (card.needs_review) {
                    item.dataset.needsReview = "true";
                }
                item.append(footer);
                cardList.append(item);
            });
        }

        async function loadCards() {
            try {
                const payload = await apiRequest(`/api/cards?lesson_id=${lessonId}`);
                state.cards = payload.cards;
                renderCards();
            } catch (error) {
                cardList.textContent = error.message;
            }
        }

        root.querySelector('[data-action="clear-card"]').addEventListener("click", resetCardForm);
        cardFilter.addEventListener("input", renderCards);
        cardForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            const formData = new FormData(cardForm);
            const source = state.selectedSource || {};
            const editing = state.editingCardId;
            cardSubmit.disabled = true;
            try {
                await apiRequest(
                    editing ? `/api/cards/${encodeURIComponent(editing)}` : "/api/cards",
                    {
                        method: editing ? "PATCH" : "POST",
                        body: {
                            ...(editing ? {} : { lesson_id: lesson.id }),
                            front: formData.get("front"),
                            back: formData.get("back"),
                            tags: String(formData.get("tags") || "")
                                .split(",")
                                .map((tag) => tag.trim())
                                .filter(Boolean),
                            source_text: source.text || "",
                            source_prefix: source.prefix || "",
                            source_suffix: source.suffix || "",
                        },
                    },
                );
                resetCardForm();
                await loadCards();
                showToast(editing ? "Flashcard updated" : "Flashcard saved");
            } catch (error) {
                showToast(error.message, "error");
            } finally {
                cardSubmit.disabled = false;
            }
        });

        function captureSelection() {
            if (!article) {
                return null;
            }
            const selection = window.getSelection();
            if (!selection || selection.isCollapsed || !selection.rangeCount) {
                return null;
            }
            const range = selection.getRangeAt(0);
            const ancestor =
                range.commonAncestorContainer.nodeType === Node.ELEMENT_NODE
                    ? range.commonAncestorContainer
                    : range.commonAncestorContainer.parentElement;
            if (!ancestor || !article.contains(ancestor)) {
                return null;
            }
            const text = selection.toString().trim().slice(0, 20_000);
            if (!text) {
                return null;
            }
            const before = range.cloneRange();
            before.selectNodeContents(article);
            before.setEnd(range.startContainer, range.startOffset);
            const after = range.cloneRange();
            after.selectNodeContents(article);
            after.setStart(range.endContainer, range.endOffset);
            return {
                text,
                prefix: before.toString().slice(-500).trim(),
                suffix: after.toString().slice(0, 500).trim(),
                rect: range.getBoundingClientRect(),
            };
        }

        function updateSelectionAction() {
            window.setTimeout(() => {
                const source = captureSelection();
                if (!source || !source.rect.width) {
                    selectionAction.hidden = true;
                    return;
                }
                state.selectedSource = source;
                selectionAction.hidden = false;
                selectionAction.style.left = `${Math.max(
                    12,
                    Math.min(window.innerWidth - 120, source.rect.left + source.rect.width / 2 - 50),
                )}px`;
                selectionAction.style.top = `${Math.max(12, source.rect.top - 44)}px`;
            });
        }

        if (article) {
            article.addEventListener("mouseup", updateSelectionAction);
            article.addEventListener("keyup", updateSelectionAction);
        }
        document.addEventListener("pointerdown", (event) => {
            if (event.target !== selectionAction && !article?.contains(event.target)) {
                selectionAction.hidden = true;
            }
        });
        selectionAction.addEventListener("click", () => {
            const source = state.selectedSource;
            if (!source) {
                return;
            }
            setPanel(true);
            activateTab(root.querySelector("#study-cards-tab"));
            cardForm.elements.back.value = source.text;
            sourcePreview.textContent = source.text;
            sourcePreview.hidden = false;
            selectionAction.hidden = true;
            focusWithoutScroll(cardForm.elements.front);
        });

        loadNote();
        loadProgress();
        loadCards();
    }

    function initializeDashboard() {
        const chapterList = document.querySelector("#study-chapter-list");
        const search = document.querySelector("#study-course-search");
        const noResults = document.querySelector("#study-no-course-results");
        const chapterButtons = [
            ...document.querySelectorAll(".study-chapter-heading"),
        ];

        chapterButtons.forEach((button) => {
            button.addEventListener("click", () => {
                const expanded = button.getAttribute("aria-expanded") === "true";
                button.setAttribute("aria-expanded", String(!expanded));
                document.querySelector(`#${button.getAttribute("aria-controls")}`).hidden =
                    expanded;
            });
        });

        function filterCourse() {
            const query = search.value.trim().toLowerCase();
            let visibleChapters = 0;
            document.querySelectorAll(".study-chapter").forEach((chapter) => {
                const chapterMatches = chapter.dataset.search.includes(query);
                let visibleLessons = 0;
                chapter.querySelectorAll(".study-lesson-row").forEach((row) => {
                    const visible =
                        !query || chapterMatches || row.dataset.search.includes(query);
                    row.hidden = !visible;
                    visibleLessons += visible ? 1 : 0;
                });
                chapter.hidden = visibleLessons === 0;
                visibleChapters += visibleLessons ? 1 : 0;
                const button = chapter.querySelector(".study-chapter-heading");
                const lessons = chapter.querySelector(".study-lesson-list");
                if (query && visibleLessons) {
                    button.setAttribute("aria-expanded", "true");
                    lessons.hidden = false;
                } else if (!query) {
                    lessons.hidden = button.getAttribute("aria-expanded") !== "true";
                }
            });
            noResults.hidden = visibleChapters > 0;
        }

        search.addEventListener("input", filterCourse);

        apiRequest("/api/dashboard")
            .then((summary) => {
                const completed = new Map(
                    summary.completed.map((progress) => [
                        progress.lesson_id,
                        progress,
                    ]),
                );
                document.querySelectorAll(".study-lesson-row").forEach((row) => {
                    const progress = completed.get(row.dataset.lessonId);
                    row.dataset.completed = String(Boolean(progress));
                    const updated = row.querySelector(".study-updated-badge");
                    if (updated) {
                        updated.hidden = !progress?.content_updated;
                    }
                });
                document.querySelectorAll(".study-chapter").forEach((chapter) => {
                    const rows = [...chapter.querySelectorAll(".study-lesson-row")];
                    const count = rows.filter(
                        (row) => row.dataset.completed === "true",
                    ).length;
                    chapter.querySelector("[data-chapter-progress]").textContent =
                        `${count} / ${rows.length}`;
                });

                const percent = summary.lesson_count
                    ? Math.round((summary.completed_count / summary.lesson_count) * 100)
                    : 0;
                document.querySelector("#study-completed-summary").textContent =
                    `${summary.completed_count} / ${summary.lesson_count}`;
                document.querySelector("#study-progress-percent").textContent =
                    `${percent}% complete`;
                document.querySelector("#study-progress-fill").style.width = `${percent}%`;
                document.querySelector("#study-again-count").textContent =
                    String(summary.again_count);
                const continueLink = document.querySelector("#study-continue");
                continueLink.href = summary.course_complete
                    ? "/review?scope=all"
                    : summary.continue_url;
                continueLink.textContent = summary.course_complete
                    ? "Review your cards"
                    : summary.completed_count
                      ? "Continue learning"
                      : "Start learning";
                if (summary.orphans.length) {
                    showToast(
                        `${summary.orphans.length} orphaned study file(s) need attention`,
                        "error",
                    );
                }
            })
            .catch((error) => {
                chapterList.setAttribute("aria-busy", "false");
                showToast(error.message, "error");
            });
    }

    function initializeNotesPage() {
        const list = document.querySelector("#study-notes-list");
        const search = document.querySelector("#study-notes-search");
        let notes = [];

        function render() {
            const query = search.value.trim().toLowerCase();
            const visible = notes.filter((note) =>
                [note.lesson_title, note.lesson_label, note.body]
                    .join(" ")
                    .toLowerCase()
                    .includes(query),
            );
            list.replaceChildren();
            if (!visible.length) {
                const empty = document.createElement("p");
                empty.className = "study-empty-copy";
                empty.textContent = notes.length
                    ? "No notes match that search."
                    : "No notes yet. Open a lesson and write what matters.";
                list.append(empty);
                return;
            }
            visible.forEach((note) => {
                const article = document.createElement("article");
                article.className = "study-note-card";
                const heading = document.createElement("div");
                const label = document.createElement("span");
                label.className = "study-eyebrow";
                label.textContent = note.lesson_label;
                const title = document.createElement("h2");
                const link = document.createElement("a");
                link.href = note.lesson_url;
                link.textContent = note.lesson_title.split("—").at(-1).trim();
                title.append(link);
                heading.append(label, title);
                const body = document.createElement("pre");
                body.textContent = note.body;
                const open = document.createElement("a");
                open.className = "study-text-link";
                open.href = note.lesson_url;
                open.textContent = "Open lesson to edit →";
                article.append(heading, body, open);
                list.append(article);
            });
        }

        search.addEventListener("input", render);
        apiRequest("/api/notes")
            .then((payload) => {
                notes = payload.notes;
                render();
            })
            .catch((error) => {
                list.textContent = error.message;
            });
    }

    function initializeCardsPage() {
        const list = document.querySelector("#study-cards-list");
        const search = document.querySelector("#study-cards-search");
        const againOnly = document.querySelector("#study-cards-again-only");
        let cards = [];

        async function removeCard(card) {
            if (!window.confirm("Delete this flashcard?")) {
                return;
            }
            try {
                await apiRequest(`/api/cards/${encodeURIComponent(card.id)}`, {
                    method: "DELETE",
                    body: {},
                });
                cards = cards.filter((candidate) => candidate.id !== card.id);
                render();
                showToast("Card deleted");
            } catch (error) {
                showToast(error.message, "error");
            }
        }

        async function toggleAgain(card) {
            try {
                const result = await apiRequest(
                    `/api/reviews/${encodeURIComponent(card.id)}`,
                    {
                        method: card.needs_review ? "DELETE" : "PUT",
                        body: {},
                    },
                );
                card.needs_review = result.needs_review;
                render();
                showToast(result.needs_review ? "Marked for review" : "Review marker cleared");
            } catch (error) {
                showToast(error.message, "error");
            }
        }

        function editCard(article, card) {
            article.replaceChildren();
            const form = document.createElement("form");
            form.className = "study-global-card-editor";
            form.innerHTML = `
                <label class="study-field">
                    <span class="study-field-label">Front</span>
                    <textarea name="front" rows="3" required></textarea>
                </label>
                <label class="study-field">
                    <span class="study-field-label">Back</span>
                    <textarea name="back" rows="4" required></textarea>
                </label>
                <label class="study-field">
                    <span class="study-field-label">Tags</span>
                    <input name="tags" type="text">
                </label>
                <div class="study-global-card-actions">
                    <button class="study-primary-button" type="submit">Save changes</button>
                    <button class="study-secondary-button" type="button">Cancel</button>
                </div>
            `;
            form.elements.front.value = card.front;
            form.elements.back.value = card.back;
            form.elements.tags.value = card.tags.join(", ");
            form.querySelector('button[type="button"]').addEventListener("click", render);
            form.addEventListener("submit", async (event) => {
                event.preventDefault();
                const submit = form.querySelector('button[type="submit"]');
                submit.disabled = true;
                try {
                    const updated = await apiRequest(
                        `/api/cards/${encodeURIComponent(card.id)}`,
                        {
                            method: "PATCH",
                            body: {
                                front: form.elements.front.value,
                                back: form.elements.back.value,
                                tags: form.elements.tags.value
                                    .split(",")
                                    .map((tag) => tag.trim())
                                    .filter(Boolean),
                            },
                        },
                    );
                    cards = cards.map((candidate) =>
                        candidate.id === updated.id ? updated : candidate,
                    );
                    render();
                    showToast("Flashcard updated");
                } catch (error) {
                    showToast(error.message, "error");
                    submit.disabled = false;
                }
            });
            article.append(form);
            focusWithoutScroll(form.elements.front);
        }

        function cardArticle(card) {
            const article = document.createElement("article");
            article.className = "study-global-card";
            article.dataset.needsReview = String(card.needs_review);
            const meta = document.createElement("div");
            meta.className = "study-global-card-meta";
            const lesson = document.createElement("a");
            lesson.href = card.lesson_url;
            lesson.textContent = card.lesson_title;
            meta.append(lesson);
            if (card.needs_review) {
                const badge = document.createElement("span");
                badge.textContent = "Again";
                meta.append(badge);
            }
            const front = document.createElement("h2");
            front.textContent = card.front;
            const back = document.createElement("p");
            back.textContent = card.back;
            const tags = document.createElement("div");
            tags.className = "study-tag-list";
            card.tags.forEach((tag) => {
                const element = document.createElement("span");
                element.textContent = tag;
                tags.append(element);
            });
            article.append(meta, front, back, tags);
            if (card.source_text) {
                const source = document.createElement("details");
                source.className = "study-global-card-source";
                const summary = document.createElement("summary");
                summary.textContent = "Source selection";
                const quote = document.createElement("blockquote");
                quote.textContent = card.source_text;
                source.append(summary, quote);
                article.append(source);
            }
            const actions = document.createElement("div");
            actions.className = "study-global-card-actions";
            const open = document.createElement("a");
            open.className = "study-secondary-button";
            open.href = card.lesson_url;
            open.textContent = "Open lesson";
            const review = document.createElement("button");
            review.className = "study-secondary-button";
            review.type = "button";
            review.textContent = card.needs_review ? "Clear Again" : "Mark Again";
            review.addEventListener("click", () => toggleAgain(card));
            const edit = document.createElement("button");
            edit.className = "study-text-button";
            edit.type = "button";
            edit.textContent = "Edit";
            edit.addEventListener("click", () => editCard(article, card));
            const remove = document.createElement("button");
            remove.className = "study-text-button";
            remove.type = "button";
            remove.textContent = "Delete";
            remove.addEventListener("click", () => removeCard(card));
            actions.append(open, review, edit, remove);
            article.append(actions);
            return article;
        }

        function render() {
            const query = search.value.trim().toLowerCase();
            const visible = cards.filter((card) => {
                if (againOnly.checked && !card.needs_review) {
                    return false;
                }
                return (
                    !query ||
                    [card.front, card.back, card.lesson_title, ...card.tags]
                        .join(" ")
                        .toLowerCase()
                        .includes(query)
                );
            });
            list.replaceChildren();
            if (!visible.length) {
                const empty = document.createElement("p");
                empty.className = "study-empty-copy";
                empty.textContent = cards.length
                    ? "No cards match those filters."
                    : "No flashcards yet. Select text in a lesson to create one.";
                list.append(empty);
                return;
            }
            visible.forEach((card) => list.append(cardArticle(card)));

            const requestedCard = new URLSearchParams(window.location.search).get("edit");
            if (requestedCard) {
                const index = visible.findIndex((card) => card.id === requestedCard);
                const article = list.children[index];
                if (index >= 0 && article) {
                    editCard(article, visible[index]);
                    window.history.replaceState(null, "", "/cards");
                }
            }
        }

        search.addEventListener("input", render);
        againOnly.addEventListener("change", render);
        apiRequest("/api/cards")
            .then((payload) => {
                cards = payload.cards;
                render();
            })
            .catch((error) => {
                list.textContent = error.message;
            });
    }

    function shuffle(values) {
        const result = [...values];
        for (let index = result.length - 1; index > 0; index -= 1) {
            const target = Math.floor(Math.random() * (index + 1));
            [result[index], result[target]] = [result[target], result[index]];
        }
        return result;
    }

    async function initializeReview() {
        const scope = document.querySelector("#study-review-scope");
        const targetField = document.querySelector("#study-review-target-field");
        const targetLabel = document.querySelector("#study-review-target-label");
        const target = document.querySelector("#study-review-target");
        const start = document.querySelector("#study-review-start");
        const empty = document.querySelector("#study-review-empty");
        const session = document.querySelector("#study-review-session");
        const position = document.querySelector("#study-review-position");
        const lessonName = document.querySelector("#study-review-lesson");
        const front = document.querySelector("#study-review-front");
        const back = document.querySelector("#study-review-back");
        const reveal = document.querySelector("#study-review-reveal");
        const grades = document.querySelector("#study-review-grades");
        const again = document.querySelector("#study-review-again");
        const gotIt = document.querySelector("#study-review-got-it");
        const previous = document.querySelector("#study-review-previous");
        const next = document.querySelector("#study-review-next");
        const source = document.querySelector("#study-review-source");
        const edit = document.querySelector("#study-review-edit");
        const contextLinks = document.querySelector("#study-review-context-links");
        const state = {
            catalog: null,
            queue: [],
            index: 0,
            revealed: false,
        };

        function updateTargets() {
            const needsTarget = ["chapter", "lesson"].includes(scope.value);
            targetField.hidden = !needsTarget;
            target.replaceChildren();
            if (!needsTarget || !state.catalog) {
                return;
            }
            if (scope.value === "lesson") {
                targetLabel.textContent = "Lesson";
                state.catalog.lessons.forEach((lesson) => {
                    const option = document.createElement("option");
                    option.value = lesson.id;
                    option.textContent = lesson.title;
                    target.append(option);
                });
                return;
            }
            targetLabel.textContent = "Chapter";
            const seen = new Set();
            state.catalog.lessons.forEach((lesson) => {
                if (seen.has(lesson.chapter_id)) {
                    return;
                }
                seen.add(lesson.chapter_id);
                const option = document.createElement("option");
                option.value = lesson.chapter_id;
                option.textContent = `${lesson.chapter_label} — ${lesson.chapter_title}`;
                target.append(option);
            });
        }

        function currentCard() {
            return state.queue[state.index] || null;
        }

        function setRevealed(value) {
            state.revealed = value;
            back.hidden = !value;
            reveal.hidden = value;
            grades.hidden = !value;
            contextLinks.hidden = !value;
        }

        function renderCard() {
            const card = currentCard();
            if (!card) {
                session.hidden = true;
                empty.hidden = false;
                return;
            }
            empty.hidden = true;
            session.hidden = false;
            position.textContent = `${state.index + 1} / ${state.queue.length}`;
            lessonName.textContent = card.lesson_title;
            front.textContent = card.front;
            back.textContent = card.back;
            source.href = card.lesson_url;
            edit.href = `/cards?edit=${encodeURIComponent(card.id)}`;
            previous.disabled = state.index === 0;
            next.disabled = state.index === state.queue.length - 1;
            setRevealed(false);
        }

        async function buildQueue() {
            start.disabled = true;
            try {
                const parameters = new URLSearchParams();
                if (scope.value === "again") {
                    parameters.set("needs_review", "true");
                } else if (scope.value === "lesson") {
                    parameters.set("lesson_id", target.value);
                } else if (scope.value === "chapter") {
                    parameters.set("chapter_id", target.value);
                }
                const payload = await apiRequest(`/api/cards?${parameters}`);
                state.queue = shuffle(payload.cards);
                state.index = 0;
                renderCard();
            } catch (error) {
                showToast(error.message, "error");
            } finally {
                start.disabled = false;
            }
        }

        async function grade(needsReview) {
            const card = currentCard();
            if (!card || !state.revealed) {
                return;
            }
            try {
                await apiRequest(`/api/reviews/${encodeURIComponent(card.id)}`, {
                    method: needsReview ? "PUT" : "DELETE",
                    body: {},
                });
                card.needs_review = needsReview;
                if (state.index + 1 < state.queue.length) {
                    state.index += 1;
                    renderCard();
                } else {
                    session.hidden = true;
                    empty.hidden = false;
                    empty.querySelector("h2").textContent = "Review complete";
                    empty.querySelector("p").textContent =
                        "Build another queue whenever you are ready.";
                }
            } catch (error) {
                showToast(error.message, "error");
            }
        }

        scope.addEventListener("change", updateTargets);
        start.addEventListener("click", buildQueue);
        reveal.addEventListener("click", () => setRevealed(true));
        again.addEventListener("click", () => grade(true));
        gotIt.addEventListener("click", () => grade(false));
        previous.addEventListener("click", () => {
            if (state.index > 0) {
                state.index -= 1;
                renderCard();
            }
        });
        next.addEventListener("click", () => {
            if (state.index + 1 < state.queue.length) {
                state.index += 1;
                renderCard();
            }
        });
        document.addEventListener("keydown", (event) => {
            if (["INPUT", "TEXTAREA", "SELECT"].includes(event.target.tagName)) {
                return;
            }
            if (session.hidden) {
                return;
            }
            if (event.code === "Space") {
                event.preventDefault();
                setRevealed(true);
            } else if (event.key === "1") {
                grade(true);
            } else if (event.key === "2") {
                grade(false);
            } else if (event.key === "ArrowLeft" && state.index > 0) {
                state.index -= 1;
                renderCard();
            } else if (
                event.key === "ArrowRight" &&
                state.index + 1 < state.queue.length
            ) {
                state.index += 1;
                renderCard();
            }
        });

        try {
            state.catalog = await apiRequest("/api/catalog");
            const parameters = new URLSearchParams(window.location.search);
            const requestedScope = parameters.get("scope");
            if (["again", "all", "chapter", "lesson"].includes(requestedScope)) {
                scope.value = requestedScope;
            }
            updateTargets();
            const lessonId = parameters.get("lesson_id");
            const chapterId = parameters.get("chapter_id");
            if (lessonId && scope.value === "lesson") {
                target.value = lessonId;
            }
            if (chapterId && scope.value === "chapter") {
                target.value = chapterId;
            }
            await buildQueue();
        } catch (error) {
            showToast(error.message, "error");
        }
    }

    repairQuizSummaries();
    const lessonContext = parseLessonContext();
    if (lessonContext && lessonContext.page === "lesson") {
        initializeLesson(lessonContext);
    }
    if (document.body.dataset.page === "dashboard") {
        initializeDashboard();
    } else if (document.body.dataset.page === "notes") {
        initializeNotesPage();
    } else if (document.body.dataset.page === "cards") {
        initializeCardsPage();
    } else if (document.body.dataset.page === "review") {
        initializeReview();
    }
})();
