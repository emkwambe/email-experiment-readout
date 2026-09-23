// Presentation-layer labels. Analysis code and JSON exports keep raw source values; this is the
// only place a raw value is relabelled for display (analysis-plan Deviations, 2026-09-23).

export const SOURCE_SPELLING_FIXES: Record<string, string> = {
  Surburban: "Suburban",
};

export function displayLevel(raw: string): string {
  return SOURCE_SPELLING_FIXES[raw] ?? raw;
}

const COVARIATE_NAMES: Record<string, string> = {
  recency: "Months since last purchase",
  history: "Prior-year spend ($)",
  mens: "Bought men's merchandise",
  womens: "Bought women's merchandise",
  newbie: "New customer",
  history_segment: "Prior-year spend band",
  zip_code: "Zip code class",
  channel: "Purchase channel",
};

export function displayCovariate(raw: string): string {
  const [column, level] = raw.split("=");
  const name = COVARIATE_NAMES[column] ?? column;
  return level === undefined ? name : `${name}: ${displayLevel(level)}`;
}

export function isRelabelled(raw: string): boolean {
  const level = raw.split("=")[1];
  return level !== undefined && level in SOURCE_SPELLING_FIXES;
}

const GATE_NAMES: Record<string, string> = {
  row_count_is_64000: "Row count equals the documented population size",
  no_nulls: "No missing values in any column",
  spend_nonnegative: "Spend is never negative",
  spend_positive_implies_conversion: "Positive spend implies a conversion",
  conversion_implies_visit: "A conversion implies a visit",
};

export function displayGate(key: string): string {
  if (key in GATE_NAMES) return GATE_NAMES[key];
  const column = key.replace(/^documented_levels_/, "");
  return `${column}: only documented levels`;
}

export const METRIC_NAMES: Record<string, string> = {
  conversion_rate: "Conversion rate",
  visit_rate: "Visit rate",
  revenue_per_customer: "Revenue per customer",
};
