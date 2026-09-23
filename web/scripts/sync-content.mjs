// Copies the locked analysis plan from docs/ into web/content/ before every build, so /plan
// renders the committed document rather than a hand-maintained duplicate. On Vercel only web/
// is uploaded, so the copy made by the last local build is used there; a Python test asserts
// the copy is byte-identical to docs/analysis-plan.md.
import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const webRoot = join(dirname(fileURLToPath(import.meta.url)), "..");
const source = join(webRoot, "..", "docs", "analysis-plan.md");
const target = join(webRoot, "content", "analysis-plan.md");

if (existsSync(source)) {
  mkdirSync(dirname(target), { recursive: true });
  copyFileSync(source, target);
  console.log(`sync-content: copied ${source} -> ${target}`);
} else if (existsSync(target)) {
  console.log("sync-content: docs/ not present (remote build); using committed web/content copy");
} else {
  console.error("sync-content: neither docs/analysis-plan.md nor web/content/analysis-plan.md exists");
  process.exit(1);
}
