import type { Metadata } from "next";
import { getBalance, getIntegrity, getPower, getSrm } from "@/lib/data";
import { fmtDollars, fmtFixed, fmtInt, fmtPct, fmtPp, fmtSigned } from "@/lib/format";
import { METRIC_NAMES, SOURCE_SPELLING_FIXES, displayCovariate, displayGate, isRelabelled } from "@/lib/labels";

export const metadata: Metadata = { title: "Data-quality checks · Email Experiment Readout" };

function Status({ ok, okText = "Pass", badText = "Fail" }: { ok: boolean; okText?: string; badText?: string }) {
  return (
    <span
      className={`inline-block rounded px-2 py-0.5 text-xs font-semibold ${ok ? "bg-pass-bg text-pass" : "bg-fail-bg text-fail"}`}
    >
      {ok ? okText : badText}
    </span>
  );
}

function Section({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} className="space-y-4">
      <h2 className="text-xl font-semibold tracking-tight">{title}</h2>
      {children}
    </section>
  );
}

const th = "px-2 py-2 text-left font-medium text-muted sm:px-3";
const td = "px-2 py-2 sm:px-3";
const tableWrap = "overflow-x-auto rounded-lg border border-line bg-surface";

export default function ChecksPage() {
  const integrity = getIntegrity();
  const srm = getSrm();
  const balance = getBalance();
  const power = getPower();
  const arms = Object.keys(srm.observed);
  const contrasts = [...new Set(balance.rows.map((r) => r.arm))];
  const covariates = [...new Set(balance.rows.map((r) => r.covariate))];
  const smdOf = (arm: string, cov: string) => balance.rows.find((r) => r.arm === arm && r.covariate === cov)!;
  const relabelled = Object.entries(SOURCE_SPELLING_FIXES);
  const powerContrasts = [...new Set(power.revenue_per_customer.map((r) => r.contrast))];
  const powerControl = power.revenue_per_customer[0].contrast.split(" vs ")[1];
  const metrics = [...new Set(power.proportions.map((r) => r.metric))];

  return (
    <div className="space-y-12">
      <header className="space-y-3">
        <h1 className="text-3xl font-semibold tracking-tight">Data-quality checks</h1>
        <p className="max-w-2xl text-muted">
          These gates come from Section 5 of the analysis plan and run before any outcome is compared across groups. A
          failed integrity gate or a sample-ratio p-value below {srm.halt_threshold} halts the analysis.
        </p>
      </header>

      <Section id="integrity" title="1. Integrity">
        <p className="text-muted">
          <Status ok={integrity.passed} okText="All gates pass" badText="A gate failed" /> ·{" "}
          <span className="num">{fmtInt(integrity.row_count)}</span> rows (documented:{" "}
          <span className="num">{fmtInt(integrity.expected_row_count)}</span>),{" "}
          <span className="num">{integrity.column_count}</span> columns.
        </p>
        <div className={tableWrap}>
          <table className="w-full text-sm">
            <thead className="border-b border-line">
              <tr>
                <th className={th}>Gate</th>
                <th className={`${th} text-right`}>Violations</th>
                <th className={`${th} text-right`}>Result</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(integrity.gates).map(([key, g]) => (
                <tr key={key} className="border-b border-line last:border-0">
                  <td className={td}>{displayGate(key)}</td>
                  <td className={`${td} num text-right`}>{fmtInt(g.violations)}</td>
                  <td className={`${td} text-right`}>
                    <Status ok={g.passed} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section id="srm" title="2. Sample ratio mismatch">
        <p className="text-muted">
          <Status ok={!srm.halt} okText="No mismatch" badText="Halt" /> · Chi-square test of group sizes against an
          equal split: χ²(<span className="num">{srm.df}</span>) = <span className="num">{fmtFixed(srm.chi_square, 3)}</span>,
          p = <span className="num">{fmtFixed(srm.p_value, 3)}</span>. Halt threshold p &lt; {srm.halt_threshold}.
        </p>
        <div className={tableWrap}>
          <table className="w-full text-sm">
            <thead className="border-b border-line">
              <tr>
                <th className={th}>Group</th>
                <th className={`${th} text-right`}>Observed</th>
                <th className={`${th} text-right`}>Expected</th>
                <th className={`${th} text-right`}>Share</th>
              </tr>
            </thead>
            <tbody>
              {arms.map((a) => (
                <tr key={a} className="border-b border-line last:border-0">
                  <td className={`${td} whitespace-nowrap`}>{a}</td>
                  <td className={`${td} num text-right`}>{fmtInt(srm.observed[a])}</td>
                  <td className={`${td} num text-right`}>{fmtFixed(srm.expected[a], 1)}</td>
                  <td className={`${td} num text-right`}>{fmtPct(srm.observed[a] / srm.total, 2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section id="balance" title="3. Covariate balance">
        <p className="text-muted">
          Standardized mean difference (SMD) of each pre-period covariate, each email group vs {balance.rows[0].control}.
          Rows with |SMD| &gt; {balance.flag_threshold} are flagged and highlighted.{" "}
          <span className="num">{balance.n_flagged}</span> of <span className="num">{balance.rows.length}</span>{" "}
          comparisons flagged; largest |SMD| = <span className="num">{fmtFixed(balance.max_abs_smd, 4)}</span>.
        </p>
        <div className={tableWrap}>
          <table className="w-full text-sm">
            <thead className="border-b border-line">
              <tr>
                <th className={th}>Covariate</th>
                {contrasts.map((c) => (
                  <th key={c} className={`${th} whitespace-nowrap text-right`}>
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {covariates.map((cov) => {
                const flagged = contrasts.some((c) => smdOf(c, cov).flag);
                return (
                  <tr key={cov} className={`border-b border-line last:border-0 ${flagged ? "bg-flag-bg" : ""}`}>
                    <td className={td}>
                      {displayCovariate(cov)}
                      {isRelabelled(cov) && <sup className="text-muted">*</sup>}
                    </td>
                    {contrasts.map((c) => {
                      const r = smdOf(c, cov);
                      return (
                        <td key={c} className={`${td} num text-right ${r.flag ? "font-semibold text-fail" : ""}`}>
                          {fmtSigned(r.smd, 4)}
                          {r.flag && " ⚑"}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-muted">
          {relabelled.map(([raw, shown]) => (
            <span key={raw}>
              * Shown as “{shown}”. The source file spells this level “{raw}”; analysis code and data exports keep the
              source spelling (see Deviations in the analysis plan).{" "}
            </span>
          ))}
          Method: {balance.method}.
        </p>
        <p className="text-xs text-muted">
          Note: prior-year spend (<code>history</code>) and the prior-year spend band (<code>history_segment</code>) overlap by
          construction, because the band is derived from the dollar amount. Both are listed because the plan names both as
          pre-period covariates, but they are not independent balance checks.
        </p>
      </Section>

      <Section id="power" title="4. Planning power (minimum detectable effects)">
        <div className="rounded-lg border border-accent/40 bg-accent/10 p-4 text-sm">
          <strong>{power.label}</strong> Baseline rates and standard
          deviations below are assumptions, not measurements; only the group sizes come from the data. Two-sided α ={" "}
          {power.alpha_per_test} per test, power = {fmtPct(power.power, 0)}.
        </div>
        {metrics.map((metric) => (
          <div key={metric} className="space-y-2">
            <h3 className="font-medium">
              {METRIC_NAMES[metric] ?? metric}{" "}
              <span className="text-sm font-normal text-muted">· MDE vs {powerControl}</span>
            </h3>
            <div className={tableWrap}>
              <table className="w-full text-sm">
                <thead className="border-b border-line">
                  <tr>
                    <th className={th}>Assumed baseline</th>
                    {powerContrasts.map((c) => (
                      <th key={c} className={`${th} whitespace-nowrap text-right`}>
                        {c.split(" vs ")[0]}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[...new Set(power.proportions.filter((r) => r.metric === metric).map((r) => r.assumed_baseline_rate))].map(
                    (p) => (
                      <tr key={p} className="border-b border-line last:border-0">
                        <td className={`${td} num`}>{fmtPct(p, 1)}</td>
                        {powerContrasts.map((c) => {
                          const r = power.proportions.find(
                            (x) => x.metric === metric && x.contrast === c && x.assumed_baseline_rate === p,
                          )!;
                          return (
                            <td key={c} className={`${td} num text-right`}>
                              <span className="whitespace-nowrap">{fmtPp(r.mde_absolute)}</span>
                              <span className="block text-xs text-muted">{fmtPct(r.mde_relative, 0)} relative</span>
                            </td>
                          );
                        })}
                      </tr>
                    ),
                  )}
                </tbody>
              </table>
            </div>
          </div>
        ))}
        <div className="space-y-2">
          <h3 className="font-medium">
            {METRIC_NAMES.revenue_per_customer}{" "}
            <span className="text-sm font-normal text-muted">· MDE per customer vs {powerControl}</span>
          </h3>
          <div className={tableWrap}>
            <table className="w-full text-sm">
              <thead className="border-b border-line">
                <tr>
                  <th className={th}>Assumed SD of spend</th>
                  {powerContrasts.map((c) => (
                    <th key={c} className={`${th} whitespace-nowrap text-right`}>
                      {c.split(" vs ")[0]}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[...new Set(power.revenue_per_customer.map((r) => r.assumed_sd_dollars))].map((sd) => (
                  <tr key={sd} className="border-b border-line last:border-0">
                    <td className={`${td} num`}>{fmtDollars(sd, 0)}</td>
                    {powerContrasts.map((c) => {
                      const r = power.revenue_per_customer.find((x) => x.contrast === c && x.assumed_sd_dollars === sd)!;
                      return (
                        <td key={c} className={`${td} num text-right`}>
                          {fmtDollars(r.mde_dollars)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <p className="text-xs text-muted">
          Method: {power.method}. These are normal-approximation planning values; exact small-sample power, the skew of
          spend and multiple-testing adjustments beyond the per-test α are not modelled.
        </p>
      </Section>
    </div>
  );
}
