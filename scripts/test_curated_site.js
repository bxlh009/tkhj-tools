const fs = require("fs");
const http = require("http");
const path = require("path");
const { chromium } = require("playwright");

const root = path.resolve(__dirname, "..", "site", "_site");
const screenshots = path.join("D:\\codex\\.codex", "tkhj-site-check");

function fileForUrl(rawUrl) {
  const pathname = decodeURIComponent(new URL(rawUrl, "http://127.0.0.1").pathname);
  let relative = pathname.replace(/^\/+/, "");
  if (!relative || relative.endsWith("/")) relative += "index.html";
  const target = path.resolve(root, relative);
  if (!target.startsWith(root)) return null;
  return target;
}

function contentType(filename) {
  const ext = path.extname(filename).toLowerCase();
  return {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".png": "image/png",
    ".json": "application/json; charset=utf-8",
  }[ext] || "application/octet-stream";
}

async function run() {
  fs.mkdirSync(screenshots, { recursive: true });
  const server = http.createServer((request, response) => {
    const filename = fileForUrl(request.url);
    if (!filename || !fs.existsSync(filename) || !fs.statSync(filename).isFile()) {
      response.writeHead(404);
      response.end("Not found");
      return;
    }
    response.writeHead(200, { "Content-Type": contentType(filename) });
    fs.createReadStream(filename).pipe(response);
  });

  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const port = server.address().port;
  const base = `http://127.0.0.1:${port}`;
  console.log(`Test server: ${base}`);
  const browser = await chromium.launch({
    headless: true,
    timeout: 15000,
    executablePath: "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  });
  console.log("Browser launched");
  const failures = [];

  async function checkViewport(name, viewport) {
    const context = await browser.newContext({ viewport });
    await context.route("**/*", async (route) => {
      const url = new URL(route.request().url());
      if (url.hostname === "127.0.0.1") await route.continue();
      else await route.fulfill({ status: 204, body: "" });
    });
    const page = await context.newPage();
    page.setDefaultNavigationTimeout(15000);
    const errors = [];
    page.on("console", (message) => {
      if (message.type() === "error") errors.push(message.text());
    });
    page.on("pageerror", (error) => errors.push(error.message));
    await page.goto(`${base}/`, { waitUntil: "domcontentloaded" });
    console.log(`${name}: homepage loaded`);

    const homeMetrics = await page.evaluate(() => ({
      overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
      cards: document.querySelectorAll(".guide-card").length,
      skipLink: Boolean(document.querySelector(".skip-link")),
      h1: document.querySelector("h1")?.textContent.trim(),
      learningNav: Boolean(document.querySelector("a[href='/learning/']")),
      aiNav: Boolean(document.querySelector("a[href='/ai/']")),
      logoLoaded: Boolean(
        document.querySelector(".brand-logo") &&
        document.querySelector(".brand-logo").complete &&
        document.querySelector(".brand-logo").naturalWidth > 0
      ),
      languageToggle: Boolean(document.querySelector("[data-language-toggle]")),
    }));
    if (homeMetrics.overflow) failures.push(`${name}: home page has horizontal overflow`);
    if (homeMetrics.cards < 5) failures.push(`${name}: expected at least 5 home cards, got ${homeMetrics.cards}`);
    if (!homeMetrics.skipLink) failures.push(`${name}: skip link missing`);
    if (!homeMetrics.learningNav || !homeMetrics.aiNav) {
      failures.push(`${name}: Learning or AI navigation missing`);
    }
    if (!homeMetrics.logoLoaded) failures.push(`${name}: brand logo is missing or failed to load`);
    if (!homeMetrics.languageToggle) failures.push(`${name}: language toggle is missing`);
    if (homeMetrics.h1 !== "Use evidence. Make a better next move.") {
      failures.push(`${name}: unexpected homepage H1`);
    }

    if (name === "desktop") {
      if (homeMetrics.languageToggle) {
        await page.locator("[data-language-toggle]").click();
        if ((await page.locator("html").getAttribute("lang")) !== "zh-CN") {
          failures.push("desktop: language toggle did not switch the page to Chinese");
        }
        if ((await page.locator(".nav-links a[href='/']").textContent()).trim() !== "首页") {
          failures.push("desktop: navigation was not translated to Chinese");
        }
        await page.reload({ waitUntil: "domcontentloaded" });
        if ((await page.locator("html").getAttribute("lang")) !== "zh-CN") {
          failures.push("desktop: language choice did not persist");
        }
      }
      await page.locator("[data-theme-toggle]").click();
      if ((await page.locator("html").getAttribute("data-theme")) !== "dark") {
        failures.push("desktop: theme toggle did not switch to dark");
      }
      await page.reload({ waitUntil: "domcontentloaded" });
      if ((await page.locator("html").getAttribute("data-theme")) !== "dark") {
        failures.push("desktop: theme choice did not persist");
      }
      await page.screenshot({ path: path.join(screenshots, "home-desktop.png"), fullPage: true });
    }

    await page.goto(`${base}/guides/ielts-true-false-not-given.html`, { waitUntil: "domcontentloaded" });
    console.log(`${name}: article loaded`);
    const articleMetrics = await page.evaluate(() => ({
      overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
      h2: document.querySelectorAll(".article-body > h2").length,
      byline: Boolean(document.querySelector(".byline a[href='/about.html#editorial-team']")),
      disclosure: Boolean(document.querySelector(".editorial-note")),
      sources: document.querySelectorAll(".source-notes a").length,
      toc: document.querySelectorAll(".article-toc a").length,
    }));
    if (articleMetrics.overflow) failures.push(`${name}: article has horizontal overflow`);
    if (articleMetrics.h2 < 3) failures.push(`${name}: article has fewer than 3 H2 sections`);
    if (!articleMetrics.byline) failures.push(`${name}: linked byline missing`);
    if (!articleMetrics.disclosure) failures.push(`${name}: editorial disclosure missing`);
    if (articleMetrics.sources < 2) failures.push(`${name}: source links missing`);
    if (articleMetrics.toc !== articleMetrics.h2) {
      failures.push(`${name}: ToC count ${articleMetrics.toc} differs from H2 count ${articleMetrics.h2}`);
    }
    await page.goto(`${base}/guides/ai-answer-verification-checklist.html`, { waitUntil: "domcontentloaded" });
    if (!(await page.locator("a.back-link[href='/ai/']").count())) {
      failures.push(`${name}: AI article does not link back to AI track`);
    }
    if (name === "mobile") {
      await page.screenshot({ path: path.join(screenshots, "article-mobile.png"), fullPage: true });
    }
    console.log(`${name}: checks complete`);
    if (errors.length) failures.push(`${name}: browser errors: ${errors.join(" | ")}`);
    await context.close();
  }

  try {
    await checkViewport("desktop", { width: 1440, height: 900 });
    await checkViewport("mobile", { width: 375, height: 812 });
  } finally {
    await browser.close();
    server.close();
  }

  if (failures.length) {
    console.error(`Curated site browser test: ${failures.length} failure(s)`);
    for (const failure of failures) console.error(`[FAIL] ${failure}`);
    process.exitCode = 1;
  } else {
    console.log(`Curated site browser test: PASS`);
    console.log(`Screenshots: ${screenshots}`);
  }
}

run().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
