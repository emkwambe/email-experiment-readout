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
