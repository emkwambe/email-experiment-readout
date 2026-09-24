import Link from "next/link";
import { getCuped, getDecision, getEffectsPrimary, getEffectsSecondary, getManifest, getTargeting } from "@/lib/data";
import { commitUrl, fmtFixed, fmtInt, fmtLevel, fmtP, fmtPct, fmtSignedDollars, fmtSignedPct, fmtSignedPp, shortSha } from "@/lib/format";
import { niceDomain } from "@/lib/scale";
import { IntervalChart, type Series } from "./results/interval-chart";
import { LineChart, type LineSeries } from "./line-chart";

const STATUS_STYLE: Record<string, string> = {
  send: "bg-pass-bg text-pass",
  "promising — test again": "bg-flag-bg text-ink",
  "do not send": "bg-fail-bg text-fail",
};

const dollars = (x: number) => (x === 0 ? "$0" : fmtSignedDollars(x).replace("+", ""));

/** Names the exported JSON fields an interpretive sentence rests on (review guard, correction log v1.0.1). */
function Sources({ fields }: { fields: string[] }) {
  return (
    <p className="text-xs text-muted">
      Sources:{" "}
      {fields.map((f, i) => (
        <span key={f}>
          {i > 0 && "; "}
          <code>{f}</code>
        </span>
      ))}
    </p>
  );
}

function Section({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-4">
      <h2 className="text-xl font-semibold tracking-tight">
        <span className="text-muted">{n}.</span> {title}
      </h2>
      {children}
    </section>
  );
}

export default function Home() {
  const m = getManifest();
  const decision = getDecision();
  const primary = getEffectsPrimary();
  const secondary = getEffectsSecondary();
  const targeting = getTargeting();
  const cuped = getCuped();
  const rec = decision.recommendation;
  const level = fmtLevel(decision.confidence_level);
  const emails = Object.keys(decision.emails);
  const targeted = targeting.policies.filter((p) => p.net_value_minus_best_blanket !== undefined);
  // A targeted policy whose paired difference is exactly zero on every resample assigns the same action as the blanket one.
  const isSame = (p: (typeof targeted)[number]) =>
    p.net_value_minus_best_blanket === 0 && p.net_value_minus_best_blanket_ci![0] === 0 && p.net_value_minus_best_blanket_ci![1] === 0;
  const identical = targeted.filter(isSame).map((p) => p.policy);
  const distinct = targeted.filter((p) => !isSame(p));
  const bestDistinct = distinct.length
    ? distinct.reduce((a, b) => (b.net_value_minus_best_blanket! > a.net_value_minus_best_blanket! ? b : a))
    : null;

  // 2. Why: the two primary contrasts.
  const why = primary.contrasts.filter((c) => c.holm_family);
  const whyScale = niceDomain(why.flatMap((c) => c.ci_analytic));
  const whySeries: Series[] = [{ key: "a", name: `${level} CI`, color: "var(--series-1)" }];

  // 4. When it stops paying: net revenue per customer vs cost, at the estimate and at the lower bound.
  const colors = ["var(--series-1)", "var(--series-2)"];
  const sens: LineSeries[] = emails.flatMap((e, i) => [
    { key: `${e}-est`, name: `${e}, point estimate`, color: colors[i], points: decision.sensitivity.map((r) => ({ x: r.cost, y: r[e].net_at_estimate })) },
    { key: `${e}-lo`, name: `${e}, ${level} lower bound`, color: colors[i], dashed: true, points: decision.sensitivity.map((r) => ({ x: r.cost, y: r[e].net_at_lower_bound })) },
  ]);
  const maxCost = decision.sensitivity[decision.sensitivity.length - 1].cost;
  const xScale = niceDomain([0, maxCost], 5);
  const yScale = niceDomain(sens.flatMap((s) => s.points.map((p) => p.y)));
  const markers = emails
    .map((e) => ({ e, x: decision.emails[e].break_even_cost_at_lower_bound }))
    .filter(({ x }) => x > 0 && x <= maxCost)
    .map(({ e, x }) => ({ x, label: `${e.replace(" E-Mail", "")} lower-bound break-even ${dollars(x)}` }));

  const visit = secondary.metrics.visit_rate;
  const conv = secondary.metrics.conversion_rate;
  const allRevenueUp = why.every((c) => c.ci_analytic[0] > 0);
  const qiniAtMostZero = Object.values(targeting.qini_holdout).every((q) => q.coefficient <= 0);
  const funnel = visit.contrasts.map((v, i) => ({ id: v.id, email: v.treatment, visit: v, purchase: conv.contrasts[i] }));
  const bothLifted = funnel.every((f) => f.visit.ci_newcombe[0] > 0 && f.purchase.ci_newcombe[0] > 0);
  const purchasesMore = funnel.every((f) => f.purchase.relative_lift.estimate > f.visit.relative_lift.estimate);
  const intervalsOverlap = funnel.some(
    (f) =>
      f.purchase.relative_lift.ci_low <= f.visit.relative_lift.ci_high &&
      f.visit.relative_lift.ci_low <= f.purchase.relative_lift.ci_high,
  );
  const visitors = secondary.purchase_rate_among_visitors;

  return (
    <div className="space-y-12">
      <header className="space-y-5">
        <span className="inline-flex items-center gap-2 rounded-full border border-pass/40 bg-pass-bg px-3 py-1 text-sm font-medium text-pass">
          <span aria-hidden className="h-2 w-2 rounded-full bg-pass" />
          Complete
        </span>
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Should the retailer send these emails again?</h1>
      </header>

      <Section n={1} title="Recommendation">
        <p className="rounded-lg border-2 border-accent/60 bg-accent/10 p-5 text-lg leading-relaxed">{rec.sentence}</p>
        <div className="flex flex-wrap gap-2 text-sm">
          {emails.map((e) => (
            <span key={e} className={`rounded px-2 py-1 font-medium ${STATUS_STYLE[decision.emails[e].status] ?? ""}`}>
              {e}: {decision.emails[e].status} at {dollars(decision.cost)} per email
            </span>
          ))}
        </div>
        <p className="text-sm text-muted">
          Pre-registered rule (Section 10): “send” if the lower bound of the {level} interval exceeds the cost per email;
          “promising — test again” if only the point estimate does. The cost per email is an assumption, not a property of
          the data, and revenue is not profit: see when it stops paying, below.
        </p>
      </Section>

      <Section n={2} title="Why">
        <p className="text-muted">
          {allRevenueUp
            ? "Both emails increased revenue per customer over the two weeks after the send, compared with customers who got no email: each interval lies above zero."
            : "Not every email's interval for incremental revenue per customer lies above zero; see each estimate below."}{" "}
          <Link href="/results" className="text-accent underline">All estimates →</Link>
        </p>
        <IntervalChart
          series={whySeries}
          legend={false}
          domain={whyScale.domain}
          ticks={whyScale.ticks}
          format={dollars}
          axisLabel="Incremental revenue per customer vs no email, dollars"
          rows={why.map((c) => ({
            id: c.id,
            label: c.treatment,
            aside: `Holm p = ${fmtP(c.p_holm!)}`,
            detail: `${fmtSignedDollars(c.estimate)} per customer (${level} CI ${fmtSignedDollars(c.ci_analytic[0])} to ${fmtSignedDollars(c.ci_analytic[1])})`,
            summary: `${c.treatment}: ${fmtSignedDollars(c.estimate)} per customer`,
            values: { a: { est: c.estimate, lo: c.ci_analytic[0], hi: c.ci_analytic[1] } },
          }))}
        />
        <Sources fields={["effects_primary.json: contrasts[H1, H2].estimate, .ci_analytic, .p_holm"]} />
      </Section>

      <Section n={3} title="Does targeting help?">
        <p>
          {targeting.winner.targeting_beat_blanket
            ? `Yes: ${targeting.winner.winner} beat sending to everyone on the holdout.`
            : "Not on this data. On a holdout of customers set aside before any model was trained, no targeted policy beat sending the best email to everyone."}{" "}
          <Link href="/targeting" className="text-accent underline">Targeting analysis →</Link>
        </p>
        <p className="text-sm text-muted">
          {identical.length > 0 && (
            <>
              The targeting rules chosen on the training split ({identical.join(", ")}) turned out to assign every customer
              the same action as {targeting.winner.best_blanket}.{" "}
            </>
          )}
          {bestDistinct && (
            <>
              The best targeted policy that did differ ({bestDistinct.policy}) came out{" "}
              {fmtSignedDollars(bestDistinct.net_value_minus_best_blanket!)} per customer against{" "}
              {targeting.winner.best_blanket} ({level} CI {fmtSignedDollars(bestDistinct.net_value_minus_best_blanket_ci![0])} to{" "}
              {fmtSignedDollars(bestDistinct.net_value_minus_best_blanket_ci![1])}).{" "}
            </>
          )}
          {qiniAtMostZero
            ? "The uplift models ranked customers no better than chance: holdout Qini"
            : "The uplift models' ranking gains were small: holdout Qini"}{" "}
          {Object.entries(targeting.qini_holdout)
            .map(([a, q]) => `${a} ${fmtSignedDollars(q.coefficient)}`)
            .join(", ")}{" "}
          per customer.
        </p>
        <p className="text-sm text-muted">
          On the {fmtInt(targeting.n_holdout)} holdout customers, sending everyone the {rec.emails_sent.join(" and ")} added{" "}
          {fmtSignedDollars(rec.holdout.incremental_revenue_vs_p0)} per customer ({level} CI{" "}
          {fmtSignedDollars(rec.holdout.incremental_revenue_vs_p0_ci[0])} to{" "}
          {fmtSignedDollars(rec.holdout.incremental_revenue_vs_p0_ci[1])}). That interval overlaps the full-experiment
          estimate above and is wider, because it uses only the holdout and a policy-value estimator. The holdout exists to
          compare targeting against blanket sending, not to re-confirm the email effect, which rests on the pre-registered
          full-sample test in section 2.
        </p>
        <Sources
          fields={[
            "targeting.json: winner, policies[].net_value_minus_best_blanket(_ci), qini_holdout[].coefficient",
            "decision.json: recommendation.holdout.incremental_revenue_vs_p0(_ci)",
          ]}
        />
      </Section>

      <Section n={4} title="When it stops paying">
        <p className="text-muted">
          Net revenue per customer at each assumed cost per email, from the full-experiment estimates. Solid lines use the
          point estimate; dashed lines use the lower bound of the {level} interval. Sending stops paying where a line
          crosses zero.
        </p>
        <div className="rounded-lg border border-line bg-surface p-4">
          <LineChart
            series={sens}
            xDomain={xScale.domain}
            yDomain={yScale.domain}
            xTicks={xScale.ticks}
            yTicks={yScale.ticks}
            xFormat="dollars"
            yFormat="dollars"
            xLabel="Cost per email"
            yLabel="Net revenue per customer"
            markers={markers}
          />
        </div>
        <ul className="num space-y-1 text-sm">
          {emails.map((e) => {
            const d = decision.emails[e];
            return (
              <li key={e}>
                <span className="font-medium">{e}</span>: breaks even at a cost of {dollars(d.break_even_cost_at_estimate)} per
                email at the point estimate, {dollars(d.break_even_cost_at_lower_bound)} at the lower bound.
              </li>
            );
          })}
        </ul>
        {rec.supplementary_margin_sentence && (
          <p className="rounded-lg border border-dashed border-line p-4 text-sm">
            {rec.supplementary_margin_sentence} <span className="text-muted">{decision.margin_view.note}</span>
          </p>
        )}
      </Section>

      <Section n={5} title="What we saw in the funnel">
        <p>
          {bothLifted
            ? "Both emails lifted visits and purchases: every interval lies above zero."
            : "Not every visit or purchase interval lies above zero; see the estimates below."}{" "}
          {purchasesMore &&
            (intervalsOverlap
              ? "For both emails the point estimate of the relative lift is larger for purchases than for visits, but the purchase intervals are wide and overlap the visit intervals, so that ordering is not statistically established."
              : "For both emails the relative lift is larger for purchases than for visits.")}
        </p>
        <ul className="num space-y-2 text-sm">
          {funnel.map((f) => (
            <li key={f.id}>
              <span className="font-medium">{f.email}</span>: visits {fmtSignedPp(f.visit.estimate)} ({level} CI{" "}
              {fmtSignedPp(f.visit.ci_newcombe[0])} to {fmtSignedPp(f.visit.ci_newcombe[1])}), a relative lift of{" "}
              {fmtSignedPct(f.visit.relative_lift.estimate)} ({fmtSignedPct(f.visit.relative_lift.ci_low)} to{" "}
              {fmtSignedPct(f.visit.relative_lift.ci_high)}); purchases {fmtSignedPp(f.purchase.estimate)} (
              {fmtSignedPp(f.purchase.ci_newcombe[0])} to {fmtSignedPp(f.purchase.ci_newcombe[1])}), a relative lift of{" "}
              {fmtSignedPct(f.purchase.relative_lift.estimate)} ({fmtSignedPct(f.purchase.relative_lift.ci_low)} to{" "}
              {fmtSignedPct(f.purchase.relative_lift.ci_high)}).
            </li>
          ))}
        </ul>
        <p className="text-sm text-muted">
          Descriptive only: among customers who visited, the share who bought was{" "}
          {Object.entries(visitors.arms)
            .map(([a, v]) => `${fmtPct(v.purchase_rate_among_visitors, 1)} (${a})`)
            .join(", ")}
          . {visitors.reason}
        </p>
        <p className="text-xs text-muted">{secondary.relative_lift_note}</p>
        <Sources
          fields={[
            "effects_secondary.json: metrics.visit_rate / conversion_rate .contrasts[].estimate, .ci_newcombe, .relative_lift",
            "effects_secondary.json: purchase_rate_among_visitors (descriptive_only)",
          ]}
        />
      </Section>

      <Section n={6} title="Limitations">
        <ul className="list-disc space-y-1 pl-5 text-sm">
          <li>Outcomes cover only the two weeks after the send; longer-term effects are unknown.</li>
          <li>One historical send, in 2008. Customers, channels and costs have changed since.</li>
          <li>No guardrail data: unsubscribes, complaints and long-term retention were not recorded.</li>
          <li>No margin data: revenue is not profit, and the cost per email is an assumption.</li>
          <li>
            Weak pre-period features: prior-year spend correlates with two-week spend at only r ={" "}
            {fmtFixed(cuped.correlation_spend_history.pooled, 3)}, which limits both variance reduction and targeting.
          </li>
        </ul>
        <Sources fields={["cuped.json: correlation_spend_history.pooled", "targeting.json: qini_holdout[].coefficient"]} />
      </Section>

      <Section n={7} title="How we know">
        <ul className="space-y-1 text-sm">
          <li>
            <Link href="/plan" className="text-accent underline">The pre-registered plan</Link>, committed before any data was
            loaded (
            <a className="font-mono text-accent underline" href={commitUrl(m.preregistration.commit_sha)}>
              {shortSha(m.preregistration.commit_sha)}
            </a>
            ).
          </li>
          <li><Link href="/checks" className="text-accent underline">Data-quality checks</Link>: integrity, sample ratio, balance.</li>
          <li><Link href="/results" className="text-accent underline">Effect estimates</Link>, every one with an interval.</li>
          <li>
            <Link href="/targeting" className="text-accent underline">Targeting analysis</Link>: {fmtInt(targeting.n_holdout)}{" "}
            holdout customers, evaluated once.
          </li>
          <li>
            <Link href="/how-its-built" className="text-accent underline">How it was built</Link> with Claude Code, including
            the correction log.
          </li>
        </ul>
      </Section>
    </div>
  );
}
