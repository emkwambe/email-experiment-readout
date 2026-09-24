import { readFileSync } from "node:fs";
import { join } from "node:path";

export type Manifest = {
  commit_sha: string;
  working_tree_dirty: boolean;
  dataset_sha256: string;
  generated_utc: string;
  script: string;
  seed: number;
  stage: string;
};

export type Gate = { passed: boolean; violations: number };

export type Integrity = {
  manifest: Manifest;
  passed: boolean;
  row_count: number;
  expected_row_count: number;
  column_count: number;
  gates: Record<string, Gate>;
  documented_levels: Record<string, string[]>;
};

export type Srm = {
  manifest: Manifest;
  observed: Record<string, number>;
  expected: Record<string, number>;
  total: number;
  df: number;
  chi_square: number;
  p_value: number;
  halt_threshold: number;
  halt: boolean;
};

export type BalanceRow = {
  arm: string;
  control: string;
  covariate: string;
  type: "binary" | "continuous";
  smd: number;
  abs_smd: number;
  flag: boolean;
};

export type Balance = {
  manifest: Manifest;
  flag_threshold: number;
  method: string;
  n_covariates: number;
  n_flagged: number;
  max_abs_smd: number;
  rows: BalanceRow[];
};

export type ProportionMde = {
  basis: string;
  contrast: string;
  n_treatment: number;
  n_control: number;
  metric: string;
  assumed_baseline_rate: number;
  mde_absolute: number;
  mde_relative: number;
};

export type RevenueMde = {
  basis: string;
  contrast: string;
  n_treatment: number;
  n_control: number;
  metric: string;
  assumed_sd_dollars: number;
  mde_dollars: number;
};

export type Power = {
  manifest: Manifest;
  basis: string;
  label: string;
  alpha_per_test: number;
  sides: number;
  power: number;
  method: string;
  proportions: ProportionMde[];
  revenue_per_customer: RevenueMde[];
};

export type ManifestFile = {
  manifest: Manifest;
  preregistration: { commit_sha: string; committed_utc: string; file: string };
  files: { file: string; sha256: string }[];
  summary: {
    integrity_passed: boolean;
    srm_p_value: number;
    srm_halt: boolean;
    balance_n_flagged: number;
    halted: boolean;
  };
};

function read<T>(name: string): T {
  return JSON.parse(readFileSync(join(process.cwd(), "public", "data", name), "utf-8")) as T;
}

export const getIntegrity = () => read<Integrity>("integrity.json");
export const getSrm = () => read<Srm>("srm.json");
export const getBalance = () => read<Balance>("balance.json");
export const getPower = () => read<Power>("power.json");
export const getManifest = () => read<ManifestFile>("manifest.json");

export function getPlanMarkdown(): string {
  return readFileSync(join(process.cwd(), "content", "analysis-plan.md"), "utf-8");
}

// ---------- Sprint 2 (analysis-plan Sections 6-8) ----------

export type Interval = [number, number];

export type ArmMean = { n: number; mean: number; se: number; ci_low: number; ci_high: number };

export type Agreement = {
  sign_analytic: string;
  sign_bootstrap: string;
  sign_agrees: boolean;
  width_ratio: number;
  width_ratio_bounds: Interval;
  width_ok: boolean;
  passed: boolean;
};

export type PrimaryContrast = {
  id: string;
  treatment: string;
  comparison: string;
  metric: string;
  estimate: number;
  se: number;
  welch_t: number;
  welch_df: number;
  p_value: number;
  ci_analytic: Interval;
  ci_bootstrap: Interval;
  agreement: Agreement;
  relative_lift: { estimate: number; se: number; ci_low: number; ci_high: number };
  holm_family: boolean;
  p_holm: number | null;
  reject_holm: boolean | null;
};

export type EffectsPrimary = {
  manifest: Manifest;
  metric: string;
  definition: string;
  confidence_level: number;
  alpha_familywise: number;
  holm_family: string[];
  bootstrap: { resamples: number; seed: number; arm_order: string[]; method: string };
  arms: Record<string, ArmMean>;
  contrasts: PrimaryContrast[];
  all_agreement_passed: boolean;
};

export type RateArm = { n: number; events: number; rate: number; ci_low: number; ci_high: number };

export type RateContrast = {
  id: string;
  treatment: string;
  comparison: string;
  estimate: number;
  ci_newcombe: Interval;
  z: number;
  p_value: number;
  p_holm: number;
  reject_holm: boolean;
};

export type EffectsSecondary = {
  manifest: Manifest;
  confidence_level: number;
  alpha_familywise: number;
  holm: string;
  interval: string;
  test: string;
  metrics: Record<string, { arms: Record<string, RateArm>; contrasts: RateContrast[] }>;
  spend_among_converters: {
    descriptive_only: boolean;
    reason: string;
    arms: Record<string, { n_converters: number; mean_spend_among_converters: number }>;
  };
};

export type CupedEstimate = { primary: boolean; estimate: number; se: number; p_value: number; ci: Interval };

export type Cuped = {
  manifest: Manifest;
  covariate: string;
  confidence_level: number;
  correlation_spend_history: { pooled: number; by_arm: Record<string, number> };
  theta: number;
  theta_definition: string;
  history_pooled_mean: number;
  primary_estimate: string;
  interval: string;
  variance_by_arm: Record<string, { var_unadjusted: number; var_adjusted: number; variance_reduction: number }>;
  contrasts: {
    id: string;
    treatment: string;
    comparison: string;
    unadjusted: CupedEstimate;
    adjusted: CupedEstimate;
    se_ratio_adjusted_to_unadjusted: number;
    sign_agrees: boolean;
  }[];
  all_signs_agree: boolean;
};

export type SegmentEffect = {
  segment: string;
  n_email: number;
  n_control: number;
  estimate: number;
  se: number;
  ci_low: number;
  ci_high: number;
};

export type HeterogeneityTest = {
  arm: string;
  comparison: string;
  dimension: string;
  reference_level: string;
  coefficients: string[];
  interaction_test: { chi2: number; df: number; p_value: number; p_holm: number; reject_holm: boolean };
  segments: SegmentEffect[];
};

export type Heterogeneity = {
  manifest: Manifest;
  metric: string;
  model: string;
  covariance: string;
  confidence_level: number;
  interaction_test: string;
  segment_effect: string;
  holm: string;
  alpha_familywise: number;
  dimensions: { id: string; label: string }[];
  n_tests: number;
  n_reject_holm: number;
  tests: HeterogeneityTest[];
};

export const getEffectsPrimary = () => read<EffectsPrimary>("effects_primary.json");
export const getEffectsSecondary = () => read<EffectsSecondary>("effects_secondary.json");
export const getCuped = () => read<Cuped>("cuped.json");
export const getHeterogeneity = () => read<Heterogeneity>("heterogeneity.json");
