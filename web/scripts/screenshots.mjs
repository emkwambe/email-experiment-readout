// Phone-width screenshots with device emulation (390x844, mobile, touch, DPR 2).
// Usage: SCREENSHOT_URL=http://localhost:3000 SCREENSHOT_OUT=<dir> npm run screenshots
// Fails if any page, or any scroll container on it, overflows horizontally at 390 px.
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const base = (process.env.SCREENSHOT_URL || "https://liftlab-email-experiment.vercel.app").replace(/\/$/, "");
const repoRoot = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const outDir = process.env.SCREENSHOT_OUT || join(repoRoot, "ai-workflow", "evidence", "sprint-2");
const pages = (process.env.SCREENSHOT_PAGES || "/,/plan,/checks,/how-its-built,/results").split(",");
const themes = ["light", "dark"];

mkdirSync(outDir, { recursive: true });
const browser = await chromium.launch();
let failures = 0;

for (const theme of themes) {
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 2,
    isMobile: true,
    hasTouch: true,
    colorScheme: theme,
  });
  const page = await context.newPage();
  for (const path of pages) {
    const res = await page.goto(base + path, { waitUntil: "networkidle" });
    const status = res?.status() ?? 0;
    const { scrollWidth, clientWidth, innerOverflow } = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
      // Scroll containers (e.g. table wrappers) whose content is wider than the box.
      innerOverflow: [...document.querySelectorAll(".overflow-x-auto")].filter((el) => el.scrollWidth > el.clientWidth + 1)
        .length,
    }));
    const name = `${path === "/" ? "home" : path.slice(1)}-390-${theme}.png`;
    await page.screenshot({ path: join(outDir, name), fullPage: true });
    const ok = status === 200 && scrollWidth <= clientWidth && innerOverflow === 0;
    if (!ok) failures++;
    console.log(
      `${ok ? "PASS" : "FAIL"}  ${path} [${theme}] status ${status}, scrollWidth ${scrollWidth} / clientWidth ${clientWidth}, clipped scroll boxes ${innerOverflow} -> ${name}`,
    );
  }
  await context.close();
}

await browser.close();
process.exit(failures ? 1 : 0);
