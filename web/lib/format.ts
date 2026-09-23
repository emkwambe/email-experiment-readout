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

export const REPO_URL = "https://github.com/emkwambe/liftlab-email-experiment";
export const commitUrl = (sha: string) => `${REPO_URL}/commit/${sha}`;
export const treeUrl = (path: string) => `${REPO_URL}/tree/main/${path}`;
export const blobUrl = (path: string) => `${REPO_URL}/blob/main/${path}`;
