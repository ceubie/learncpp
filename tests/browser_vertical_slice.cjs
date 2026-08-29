const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawn } = require("node:child_process");
const { chromium } = require("playwright");

const projectRoot = path.resolve(__dirname, "..");
const port = 8123;
const baseUrl = `http://127.0.0.1:${port}`;
const edgePath =
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const studyDirectory = fs.mkdtempSync(
    path.join(os.tmpdir(), "learncpp-study-vertical-"),
);
const screenshotPath = path.join(
    os.tmpdir(),
    "learncpp-study-vertical-slice.png",
);
const narrowScreenshotPath = path.join(
    os.tmpdir(),
    "learncpp-study-dashboard-narrow.png",
);
const pythonScript = [
    "from pathlib import Path",
    "from study_app import create_app",
    `app = create_app({"STUDY_DATA_DIR": Path(r"${studyDirectory}")})`,
    `app.run(host="127.0.0.1", port=${port}, debug=False)`,
].join("; ");

let server;
let browser;

function assert(condition, message) {
    if (!condition) {
        throw new Error(message);
    }
}

function startServer() {
    server = spawn("python", ["-c", pythonScript], {
        cwd: projectRoot,
        stdio: ["ignore", "pipe", "pipe"],
        windowsHide: true,
    });
    server.stdout.on("data", (chunk) => process.stdout.write(chunk));
    server.stderr.on("data", (chunk) => process.stderr.write(chunk));
}

async function stopServer() {
    if (!server || server.exitCode !== null) {
        return;
    }
    server.kill();
    await new Promise((resolve) => {
        const timeout = setTimeout(resolve, 3000);
        server.once("exit", () => {
            clearTimeout(timeout);
            resolve();
        });
    });
}

async function waitForServer() {
    for (let attempt = 0; attempt < 80; attempt += 1) {
        try {
            const response = await fetch(`${baseUrl}/api/health`);
            if (response.ok) {
                return;
            }
        } catch {
            // The server is still starting.
        }
        await new Promise((resolve) => setTimeout(resolve, 100));
    }
    throw new Error("Flask did not start in time.");
}

async function waitForCondition(predicate, message) {
    for (let attempt = 0; attempt < 80; attempt += 1) {
        if (predicate()) {
            return;
        }
        await new Promise((resolve) => setTimeout(resolve, 50));
    }
    throw new Error(message);
}

async function run() {
    startServer();
    await waitForServer();
    browser = await chromium.launch({
        executablePath: edgePath,
        headless: true,
    });
    const page = await browser.newPage({ viewport: { width: 1440, height: 960 } });
    const pageErrors = [];
    page.on("pageerror", (error) => pageErrors.push(error.message));
    await page.route("**/*", (route) => {
        const requestUrl = new URL(route.request().url());
        if (requestUrl.origin === baseUrl) {
            route.continue();
        } else {
            route.abort("internetdisconnected");
        }
    });

    await page.goto(
        `${baseUrl}/course/001-introduction-to-these-tutorials.html`,
        { waitUntil: "domcontentloaded" },
    );
    await page.getByRole("button", { name: "Study", exact: true }).click();
    const note = page.locator(".study-note-editor");
    await note.waitFor();
    await page.waitForFunction(
        () => document.querySelector(".study-save-status")?.textContent === "Saved",
    );
    const noteText = "## Browser checkpoint\n\nExplain the lesson in my own words.";
    await note.fill(noteText);
    await page.waitForFunction(
        () => document.querySelector(".study-save-status")?.textContent === "Saved",
    );
    await page.reload({ waitUntil: "domcontentloaded" });
    await page.getByRole("button", { name: "Study", exact: true }).click();
    await page.waitForFunction(
        (expected) => document.querySelector(".study-note-editor")?.value === expected,
        noteText,
    );

    await page.locator(".entry-content p").first().evaluate((paragraph) => {
        const textNode = [...paragraph.childNodes].find(
            (node) => node.nodeType === Node.TEXT_NODE && node.textContent.trim(),
        );
        const target = textNode || paragraph.firstChild;
        const range = document.createRange();
        range.selectNodeContents(target);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
        paragraph.dispatchEvent(new MouseEvent("mouseup", { bubbles: true }));
    });
    const createFromSelection = page.getByRole("button", { name: "Create card" });
    await createFromSelection.waitFor({ state: "visible" });
    await createFromSelection.click();
    await page.locator('.study-card-form textarea[name="front"]').fill(
        "What should I remember from this selected passage?",
    );
    const selectedBack = await page
        .locator('.study-card-form textarea[name="back"]')
        .inputValue();
    assert(selectedBack.trim().length > 0, "Selected text did not populate the card back.");
    await page.locator('.study-card-form input[name="tags"]').fill("checkpoint, browser");
    await page
        .locator(".study-card-form")
        .getByRole("button", { name: "Save card" })
        .click();
    await page.waitForFunction(
        () => document.querySelector(".study-lesson-card-list .study-mini-card"),
    );

    await page.getByRole("button", { name: "Mark lesson complete" }).click();
    await page.waitForFunction(
        () =>
            document
                .querySelector(".study-complete-button")
                ?.getAttribute("aria-pressed") === "true",
    );

    const cardFiles = fs.readdirSync(path.join(studyDirectory, "cards"));
    assert(cardFiles.length === 1, "Expected exactly one card file.");
    const cardId = path.basename(cardFiles[0], ".json");

    await page.goto(
        `${baseUrl}/review?scope=lesson&lesson_id=introduction-to-these-tutorials`,
        { waitUntil: "domcontentloaded" },
    );
    await page.locator("#study-review-front").waitFor({ state: "visible" });
    await page.getByRole("button", { name: /Show answer/ }).click();
    await page.getByRole("button", { name: /Again/ }).click();
    const markerPath = path.join(studyDirectory, "reviews", `${cardId}.json`);
    await waitForCondition(
        () => fs.existsSync(markerPath),
        "Again did not create the review marker.",
    );

    await stopServer();
    startServer();
    await waitForServer();

    await page.goto(
        `${baseUrl}/course/001-introduction-to-these-tutorials.html`,
        { waitUntil: "domcontentloaded" },
    );
    await page.getByRole("button", { name: "Study", exact: true }).click();
    await page.waitForFunction(
        (expected) => document.querySelector(".study-note-editor")?.value === expected,
        noteText,
    );
    assert(
        (await page.locator(".study-complete-button").getAttribute("aria-pressed")) ===
            "true",
        "Completion did not survive restart.",
    );
    await page.getByRole("tab", { name: /Cards/ }).click();
    await page.locator(".study-mini-card").waitFor();
    await page.screenshot({ path: screenshotPath, fullPage: true });

    await page.goto(`${baseUrl}/review?scope=again`, {
        waitUntil: "domcontentloaded",
    });
    await page.locator("#study-review-front").waitFor({ state: "visible" });
    await page.keyboard.press("Space");
    await page.keyboard.press("2");
    await page.waitForFunction(
        () => document.querySelector("#study-review-empty h2")?.textContent ===
            "Review complete",
    );
    await waitForCondition(
        () => !fs.existsSync(markerPath),
        "Got it did not remove the review marker.",
    );

    await page.goto(`${baseUrl}/`, { waitUntil: "domcontentloaded" });
    await page.waitForFunction(
        () => document.querySelector("#study-completed-summary")?.textContent.startsWith("1 /"),
    );
    assert(
        (await page.locator("#study-continue").getAttribute("href")).includes(
            "002-introduction-to-programming-languages.html",
        ),
        "Continue did not advance from the completed lesson.",
    );
    await page.locator("#study-course-search").fill("Introduction to these tutorials");
    const visibleLessonCount = await page.locator(".study-lesson-row:visible").count();
    assert(
        visibleLessonCount === 1,
        `Course search left ${visibleLessonCount} lessons visible instead of one.`,
    );

    await page.goto(`${baseUrl}/notes`, { waitUntil: "domcontentloaded" });
    await page.locator(".study-note-card").waitFor();
    assert(
        (await page.locator(".study-note-card pre").textContent()).includes(
            "Browser checkpoint",
        ),
        "All Notes did not include the saved note.",
    );

    await page.goto(`${baseUrl}/cards`, { waitUntil: "domcontentloaded" });
    await page.locator(".study-global-card").waitFor();
    await page.getByRole("button", { name: "Edit" }).click();
    const updatedFront = "What did the browser checkpoint prove?";
    await page.locator('.study-global-card-editor textarea[name="front"]').fill(
        updatedFront,
    );
    await page.getByRole("button", { name: "Save changes" }).click();
    await page.waitForFunction(
        (expected) => document.querySelector(".study-global-card h2")?.textContent === expected,
        updatedFront,
    );

    await page.goto(`${baseUrl}/review?scope=all`, {
        waitUntil: "domcontentloaded",
    });
    await page.waitForFunction(
        (expected) => document.querySelector("#study-review-front")?.textContent === expected,
        updatedFront,
    );
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(`${baseUrl}/`, { waitUntil: "domcontentloaded" });
    await page.waitForFunction(
        () => document.querySelector("#study-completed-summary")?.textContent.startsWith("1 /"),
    );
    await page.screenshot({ path: narrowScreenshotPath, fullPage: true });

    assert(pageErrors.length === 0, `Browser errors: ${pageErrors.join("; ")}`);

    console.log("VERTICAL_SLICE_OK");
    console.log(`screenshot=${screenshotPath}`);
    console.log(`narrow_screenshot=${narrowScreenshotPath}`);
}

run()
    .catch((error) => {
        console.error(error);
        process.exitCode = 1;
    })
    .finally(async () => {
        if (browser) {
            await browser.close();
        }
        await stopServer();
        fs.rmSync(studyDirectory, { recursive: true, force: true });
    });
