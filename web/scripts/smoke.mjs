// Smoke test for the deployed readout. Usage: SMOKE_URL=https://... npm run smoke
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const DEFAULT_URL = "https://liftlab-email-experiment.vercel.app";
const base = (process.env.SMOKE_URL || DEFAULT_URL).replace(/\/$/, "");
const dataSourceDoc = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "docs", "data-source.md");

const results = [];
const check = (name, ok, detail = "") => {
  results.push(ok);
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? `  (${detail})` : ""}`);
};

async function get(path) {
  const res = await fetch(base + path, { redirect: "follow" });
  return res;
}

console.log(`Smoke test against ${base}`);

for (const path of ["/", "/plan", "/checks", "/how-its-built"]) {
  try {
    const res = await get(path);
    check(`GET ${path} returns 200`, res.status === 200, `status ${res.status}`);
  } catch (e) {
    check(`GET ${path} returns 200`, false, String(e));
  }
}

try {
  const res = await get("/data/manifest.json");
  const manifest = await res.json();
  const deployed = manifest?.manifest?.dataset_sha256;
  const documented = readFileSync(dataSourceDoc, "utf-8").match(/\| SHA-256 \| `([0-9a-f]{64})` \|/)?.[1];
  check("manifest.json loads", res.status === 200 && typeof deployed === "string", `status ${res.status}`);
  check(
    "manifest dataset SHA-256 matches docs/data-source.md",
    Boolean(documented) && deployed === documented,
    `deployed ${deployed?.slice(0, 12)}…, documented ${documented?.slice(0, 12)}…`,
  );
} catch (e) {
  check("manifest.json loads", false, String(e));
}

try {
  const res = await get("/data/srm.json");
  const srm = await res.json();
  const p = srm?.p_value;
  check("srm.json has a numeric p-value", typeof p === "number" && Number.isFinite(p), `p_value ${p}`);
} catch (e) {
  check("srm.json has a numeric p-value", false, String(e));
}

const failed = results.filter((ok) => !ok).length;
console.log(`${results.length - failed}/${results.length} checks passed`);
process.exit(failed ? 1 : 0);
