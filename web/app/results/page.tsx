import type { Metadata } from "next";
import { getCuped, getEffectsPrimary, getEffectsSecondary, getHeterogeneity } from "@/lib/data";
import {
  fmtDollars,
  fmtFixed,
  fmtInt,
  fmtLevel,
  fmtP,
  fmtPct,
  fmtSignedDollars,
  fmtSignedPct,
  fmtSignedPp,
} from "@/lib/format";
import { SOURCE_SPELLING_FIXES, displaySegment } from "@/lib/labels";
import { niceDomain } from "@/lib/scale";
import { IntervalChart, type Series } from "./interval-chart";

export const metadata: Metadata = { title: "Results · Email Experiment Readout" };

const METRIC_LABEL: Record<string, string> = { visit_rate: "Visit rate", conversion_rate: "Conversion rate" };

/** Tick formatter with enough decimals to show every tick exactly (e.g. $0.25, never "$0.3"). */
function dollarAxis(ticks: number[]): (x: number) => string {
  const decimals = Math.max(0, ...ticks.map((t) => (Number.isInteger(t) ? 0 : (String(t).split(".")[1] ?? "").length)));
  const d = decimals === 0 ? 0 : Math.max(2, decimals);
  return (x) => (x === 0 ? "$0" : `${x < 0 ? "−" : ""}$${fmtFixed(Math.abs(x), d)}`);
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
const td = "px-2 py-2 align-top sm:px-3";
const tableWrap = "overflow-x-auto rounded-lg border border-line bg-surface";

export default function ResultsPage() {
  const primary = getEffectsPrimary();
  const secondary = getEffectsSecondary();
  const cuped = getCuped();
  const het = getHeterogeneity();
  const level = fmtLevel(primary.confidence_level);
  const arms = Object.keys(primary.arms);

  // Primary chart: analytic vs bootstrap intervals, one shared axis.
  const primarySeries: Series[] = [
    { key: "analytic", name: `Welch analytic ${level} CI`, color: "var(--series-1)" },
    { key: "bootstrap", name: `Bootstrap percentile ${level} CI (${fmtInt(primary.bootstrap.resamples)} resamples)`, color: "var(--series-2)", dashed: true },
  ];
  const primaryScale = niceDomain(primary.contrasts.flatMap((c) => [...c.ci_analytic, ...c.ci_bootstrap]));

  // CUPED chart: unadjusted (primary) vs adjusted.
  const cupedSeries: Series[] = [
    { key: "unadjusted", name: `Unadjusted (primary), ${level} CI`, color: "var(--series-1)" },
    { key: "adjusted", name: `CUPED-adjusted, ${level} CI`, color: "var(--series-2)", dashed: true },
  ];
  const cupedScale = niceDomain(cuped.contrasts.flatMap((c) => [...c.unadjusted.ci, ...c.adjusted.ci]));
  const maxReduction = Math.max(...Object.values(cuped.variance_by_arm).map((v) => v.variance_reduction));

  // Heterogeneity: one shared axis across all eight panels so segments are comparable.
  const segSeries: Series[] = [{ key: "effect", name: `Segment effect, ${level} CI`, color: "var(--series-1)" }];
  const segScale = niceDomain(het.tests.flatMap((t) => t.segments.flatMap((s) => [s.ci_low, s.ci_high])), 6);
  const relabelled = Object.entries(SOURCE_SPELLING_FIXES);

  return (
    <div className="space-y-12">
      <header className="space-y-4">
        <h1 className="text-3xl font-semibold tracking-tight">Effect estimates</h1>
        <p className="max-w-2xl text-muted">
          Every estimate specified in Sections 6–8 of the pre-registered analysis plan, with its interval. Results are
          reported whether or not they are statistically significant.
        </p>
        <div role="note" className="rounded-lg border-2 border-accent/60 bg-accent/10 p-4 font-medium">
          Estimates only. The cost-based decision rule and targeting analysis are applied in Sprint 3.
        </div>
      </header>

      <Section id="primary" title="1. Revenue per customer (primary)">
        <p className="text-muted">
          {primary.definition}. H1 and H2 form the Holm family at family-wise α = {primary.alpha_familywise}; H3 is
          tested the same way but outside the family.
        </p>
        <div className="grid gap-3 sm:grid-cols-3">
          {arms.map((a) => {
            const m = primary.arms[a];
            return (
              <div key={a} className="rounded-lg border border-line bg-surface p-3">
                <div className="text-sm text-muted">{a}</div>
                <div className="text-lg font-semibold">{fmtDollars(m.mean)}</div>
                <div className="num text-xs text-muted">
                  {level} CI {fmtDollars(m.ci_low)} to {fmtDollars(m.ci_high)} · n = {fmtInt(m.n)}
                </div>
              </div>
            );
          })}
        </div>
        <IntervalChart
          series={primarySeries}
          domain={primaryScale.domain}
          ticks={primaryScale.ticks}
          format={dollarAxis(primaryScale.ticks)}
          axisLabel="Difference in revenue per customer (treatment − comparison), dollars"
          rows={primary.contrasts.map((c) => ({
            id: c.id,
            label: `${c.id} · ${c.treatment} vs ${c.comparison}`,
            aside: c.holm_family ? `Holm p = ${fmtP(c.p_holm!)}` : `p = ${fmtP(c.p_value)} (outside Holm family)`,
            detail: (
              <>
                {fmtSignedDollars(c.estimate)} per customer · analytic {fmtSignedDollars(c.ci_analytic[0])} to{" "}
                {fmtSignedDollars(c.ci_analytic[1])} · bootstrap {fmtSignedDollars(c.ci_bootstrap[0])} to{" "}
                {fmtSignedDollars(c.ci_bootstrap[1])}
                <br />
                Relative lift (secondary): {fmtSignedPct(c.relative_lift.estimate)} ({level} CI{" "}
                {fmtSignedPct(c.relative_lift.ci_low)} to {fmtSignedPct(c.relative_lift.ci_high)})
              </>
            ),
            summary: `${c.id}, ${c.treatment} vs ${c.comparison}: ${fmtSignedDollars(c.estimate)} per customer; analytic CI ${fmtSignedDollars(c.ci_analytic[0])} to ${fmtSignedDollars(c.ci_analytic[1])}; bootstrap CI ${fmtSignedDollars(c.ci_bootstrap[0])} to ${fmtSignedDollars(c.ci_bootstrap[1])}`,
            values: {
              analytic: { est: c.estimate, lo: c.ci_analytic[0], hi: c.ci_analytic[1] },
              bootstrap: { est: c.estimate, lo: c.ci_bootstrap[0], hi: c.ci_bootstrap[1] },
            },
          }))}
        />
        {primary.contrasts
          .filter((c) => !c.holm_family)
          .map((c) => (
            <p key={c.id} className="text-sm text-muted">
              For {c.id}, the dollar difference and the relative lift are different estimands: the relative-lift interval
              is wider because it also carries the uncertainty in the comparison group&apos;s ({c.comparison}) mean.
            </p>
          ))}
        <div className={tableWrap}>
          <table className="w-full text-sm">
            <caption className="px-3 pt-3 text-left text-xs text-muted">
              Test statistics and the pre-registered agreement check (bootstrap width ÷ analytic width must lie in{" "}
              {fmtFixed(primary.contrasts[0].agreement.width_ratio_bounds[0], 2)}–
              {fmtFixed(primary.contrasts[0].agreement.width_ratio_bounds[1], 2)}, same sign pattern).
            </caption>
            <thead className="border-b border-line">
              <tr>
                <th className={th}></th>
                <th className={`${th} text-right`}>Welch t (df)</th>
                <th className={`${th} text-right`}>p</th>
                <th className={`${th} text-right`}>Width ratio</th>
                <th className={`${th} text-right`}>Agree</th>
              </tr>
            </thead>
            <tbody>
              {primary.contrasts.map((c) => (
                <tr key={c.id} className="border-b border-line last:border-0">
                  <td className={`${td} font-medium`}>{c.id}</td>
                  <td className={`${td} num text-right`}>
                    {fmtFixed(c.welch_t, 2)} <span className="text-muted">({fmtInt(Math.round(c.welch_df))})</span>
                  </td>
                  <td className={`${td} num text-right`}>{fmtP(c.p_value)}</td>
                  <td className={`${td} num text-right`}>{fmtFixed(c.agreement.width_ratio, 3)}</td>
                  <td className={`${td} text-right`}>{c.agreement.passed ? "Yes" : "No"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section id="secondary" title="2. Visit and conversion rates (secondary)">
        <p className="text-muted">
          Difference in proportions with the {secondary.interval.split(";")[0]} ({level}); {secondary.test}. Holm
          correction {secondary.holm}.
        </p>
        {Object.entries(secondary.metrics).map(([metric, block]) => (
          <div key={metric} className="space-y-2">
            <h3 className="font-medium">{METRIC_LABEL[metric] ?? metric}</h3>
            <p className="num text-xs text-muted">
              {arms.map((a, i) => (
                <span key={a}>
                  {i > 0 && " · "}
                  {a}: {fmtPct(block.arms[a].rate, 2)} ({fmtPct(block.arms[a].ci_low, 2)}–{fmtPct(block.arms[a].ci_high, 2)})
                </span>
              ))}
            </p>
            <div className={tableWrap}>
              <table className="w-full text-sm">
                <thead className="border-b border-line">
                  <tr>
                    <th className={th}>Contrast</th>
                    <th className={`${th} text-right`}>Difference ({level} CI)</th>
                    <th className={`${th} text-right`}>Holm p</th>
                  </tr>
                </thead>
                <tbody>
                  {block.contrasts.map((c) => (
                    <tr key={c.id} className="border-b border-line last:border-0">
                      <td className={td}>
                        <span className="font-medium">{c.id}</span>
                        <span className="block text-xs text-muted">
                          {c.treatment} vs {c.comparison}
                        </span>
                      </td>
                      <td className={`${td} num text-right`}>
                        {fmtSignedPp(c.estimate)}
                        <span className="block whitespace-nowrap text-xs text-muted">
                          {fmtSignedPp(c.ci_newcombe[0])} to {fmtSignedPp(c.ci_newcombe[1])}
                        </span>
                      </td>
                      <td className={`${td} num text-right`}>
                        <span className="whitespace-nowrap">{fmtP(c.p_holm)}</span>
                        <span className="block whitespace-nowrap text-xs text-muted">raw {fmtP(c.p_value)}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}
        <div className="space-y-2 rounded-lg border border-dashed border-line p-4">
          <h3 className="font-medium">
            Spend among converters <span className="text-sm font-normal text-muted">· descriptive only</span>
          </h3>
          <p className="text-xs text-muted">{secondary.spend_among_converters.reason}</p>
          <ul className="num space-y-1 text-sm">
            {arms.map((a) => {
              const v = secondary.spend_among_converters.arms[a];
              return (
                <li key={a}>
                  {a}: {fmtDollars(v.mean_spend_among_converters)} mean spend across {fmtInt(v.n_converters)} converters
                </li>
              );
            })}
          </ul>
        </div>
      </Section>

      <Section id="cuped" title="3. Variance reduction with CUPED (secondary estimate)">
        <p className="text-muted">
          Revenue per customer adjusted for prior-year spend (<code>{cuped.covariate}</code>), θ ={" "}
          <span className="num">{cuped.theta.toPrecision(3)}</span> estimated on pooled data. The unadjusted estimate
          remains the primary result. The adjustment reduced within-arm variance by at most{" "}
          <span className="num">{fmtPct(maxReduction, 3)}</span>.
        </p>
        <p className="text-sm">
          CUPED produced negligible variance reduction because prior-year spend is only weakly correlated with two-week
          spend: pooled correlation r = <span className="num">{fmtFixed(cuped.correlation_spend_history.pooled, 3)}</span>.
        </p>
        <p className="num text-xs text-muted">
          Variance reduction by arm:{" "}
          {arms.map((a, i) => (
            <span key={a}>
              {i > 0 && " · "}
              {a} {fmtPct(cuped.variance_by_arm[a].variance_reduction, 3)}
            </span>
          ))}
        </p>
        <IntervalChart
          series={cupedSeries}
          domain={cupedScale.domain}
          ticks={cupedScale.ticks}
          format={dollarAxis(cupedScale.ticks)}
          axisLabel="Difference in revenue per customer vs No E-Mail, dollars"
          rows={cuped.contrasts.map((c) => ({
            id: c.id,
            label: `${c.id} · ${c.treatment} vs ${c.comparison}`,
            aside: `SE ratio ${fmtFixed(c.se_ratio_adjusted_to_unadjusted, 4)}`,
            detail: (
              <>
                Unadjusted {fmtSignedDollars(c.unadjusted.estimate)} ({fmtSignedDollars(c.unadjusted.ci[0])} to{" "}
                {fmtSignedDollars(c.unadjusted.ci[1])}) · adjusted {fmtSignedDollars(c.adjusted.estimate)} (
                {fmtSignedDollars(c.adjusted.ci[0])} to {fmtSignedDollars(c.adjusted.ci[1])}) · signs{" "}
                {c.sign_agrees ? "agree" : "disagree"}
              </>
            ),
            summary: `${c.id}: unadjusted ${fmtSignedDollars(c.unadjusted.estimate)}, adjusted ${fmtSignedDollars(c.adjusted.estimate)}`,
            values: {
              unadjusted: { est: c.unadjusted.estimate, lo: c.unadjusted.ci[0], hi: c.unadjusted.ci[1] },
              adjusted: { est: c.adjusted.estimate, lo: c.adjusted.ci[0], hi: c.adjusted.ci[1] },
            },
          }))}
        />
      </Section>

      <Section id="heterogeneity" title="4. Effects by customer segment (heterogeneity)">
        <p className="text-muted">
          Pre-specified dimensions only. For each email and dimension, a joint Wald test asks whether the effect differs
          across segments; Holm correction across all {het.n_tests} tests. {het.n_reject_holm} of {het.n_tests} tests
          reject at family-wise α = {het.alpha_familywise}. Segment estimates are shown with {level} CIs whether or not
          the test rejects, in a fixed order, and are not ranked. All panels share one axis.
        </p>
        {het.dimensions.map((d) => (
          <div key={d.id} className="space-y-3">
            <h3 className="font-medium">{d.label}</h3>
            <div className="grid gap-4 lg:grid-cols-2">
              {het.tests
                .filter((t) => t.dimension === d.id)
                .map((t) => (
                  <div key={t.arm} className="space-y-2">
                    <div className="text-sm">
                      <span className="font-medium">{t.arm}</span> <span className="text-muted">vs {t.comparison}</span>
                      <div className="num text-xs text-muted">
                        Wald χ²({t.interaction_test.df}) = {fmtFixed(t.interaction_test.chi2, 2)}, p ={" "}
                        {fmtP(t.interaction_test.p_value)}, Holm p = {fmtP(t.interaction_test.p_holm)}
                      </div>
                    </div>
                    <IntervalChart
                      series={segSeries}
                      legend={false}
                      domain={segScale.domain}
                      ticks={segScale.ticks}
                      format={dollarAxis(segScale.ticks)}
                      axisLabel="Effect on revenue per customer, dollars"
                      rows={t.segments.map((s) => ({
                        id: s.segment,
                        label: (
                          <>
                            {displaySegment(t.dimension, s.segment)}
                            {s.segment in SOURCE_SPELLING_FIXES && <sup className="text-muted">*</sup>}
                          </>
                        ),
                        aside: `n = ${fmtInt(s.n_email)} / ${fmtInt(s.n_control)}`,
                        detail: `${fmtSignedDollars(s.estimate)} (${fmtSignedDollars(s.ci_low)} to ${fmtSignedDollars(s.ci_high)})`,
                        summary: `${displaySegment(t.dimension, s.segment)}: ${fmtSignedDollars(s.estimate)} per customer, CI ${fmtSignedDollars(s.ci_low)} to ${fmtSignedDollars(s.ci_high)}; n = ${fmtInt(s.n_email)} emailed, ${fmtInt(s.n_control)} control`,
                        values: { effect: { est: s.estimate, lo: s.ci_low, hi: s.ci_high } },
                      }))}
                    />
                  </div>
                ))}
            </div>
            {d.id === "zip_code" &&
              relabelled.map(([raw, shown]) => (
                <p key={raw} className="text-xs text-muted">
                  * Shown as “{shown}”. The source file spells this level “{raw}”; analysis code and data exports keep
                  the source spelling (see Deviations in the analysis plan).
                </p>
              ))}
          </div>
        ))}
        <p className="text-xs text-muted">
          n = emailed / control customers in the segment. Model: {het.model}; {het.covariance} standard errors;{" "}
          {het.segment_effect}.
        </p>
      </Section>
    </div>
  );
}
