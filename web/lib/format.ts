const int = new Intl.NumberFormat("en-US");

export const fmtInt = (n: number) => int.format(n);

export const fmtFixed = (n: number, digits: number) =>
  n.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });

export const fmtPct = (x: number, digits = 1) => `${fmtFixed(x * 100, digits)}%`;

/** Percentage points for an absolute difference in proportions. */
export const fmtPp = (x: number, digits = 2) => `${fmtFixed(x * 100, digits)} pp`;

export const fmtDollars = (x: number, digits = 2) => `$${fmtFixed(x, digits)}`;

export const fmtSigned = (x: number, digits: number) => `${x < 0 ? "−" : "+"}${fmtFixed(Math.abs(x), digits)}`;

export const shortSha = (sha: string, n = 7) => sha.slice(0, n);

export const REPO_URL = "https://github.com/emkwambe/email-experiment-readout";
export const commitUrl = (sha: string) => `${REPO_URL}/commit/${sha}`;
export const treeUrl = (path: string) => `${REPO_URL}/tree/main/${path}`;
export const blobUrl = (path: string) => `${REPO_URL}/blob/main/${path}`;

const SUPERSCRIPT: Record<string, string> = {
  "-": "⁻", "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
};

/** p-values: three decimals down to 0.001, then scientific (e.g. 2.3 × 10⁻⁷). */
export function fmtP(p: number): string {
  if (p >= 0.001) return fmtFixed(p, 3);
  const [mantissa, exponent] = p.toExponential(1).split("e");
  const exp = String(Number(exponent)).split("").map((c) => SUPERSCRIPT[c] ?? c).join("");
  return `${mantissa} × 10${exp}`;
}

export const fmtSignedDollars = (x: number, digits = 2) =>
  `${x < 0 ? "−" : "+"}$${fmtFixed(Math.abs(x), digits)}`;

export const fmtSignedPct = (x: number, digits = 0) => `${x < 0 ? "−" : "+"}${fmtFixed(Math.abs(x) * 100, digits)}%`;

export const fmtSignedPp = (x: number, digits = 2) => `${x < 0 ? "−" : "+"}${fmtFixed(Math.abs(x) * 100, digits)} pp`;

export const fmtLevel = (level: number) => `${fmtFixed(level * 100, 0)}%`;
