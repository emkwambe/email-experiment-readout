import type { Metadata } from "next";
import { getSplit, getTargeting, getTimeline, getTraining } from "@/lib/data";
import { commitUrl, fmtInt, fmtPct, fmtSignedDollars, shortSha } from "@/lib/format";
import { SOURCE_SPELLING_FIXES, displaySegment } from "@/lib/labels";
import { niceDomain } from "@/lib/scale";
import { LineChart } from "../line-chart";
import { IntervalChart, type Series } from "../results/interval-chart";

export const metadata: Metadata = { title: "Targeting · LiftLab" };

const POLICY_LABEL: Record<string, string> = {
  P0: "Send nothing",
  P1: "Everyone gets the Mens E-Mail",
  P2: "Everyone gets the Womens E-Mail",
  P3: "Segment rule chosen by cross-validation",
  P4a: "Mens E-Mail to the top k% by predicted uplift",
  P4b: "Womens E-Mail to the top k% by predicted uplift",
  P5: "Each customer gets the email with the highest predicted net uplift",
};

const DIMENSION_LABEL: Record<string, string> = {
  prior_merchandise: "Prior merchandise purchase",
  newbie: "New customer",
  channel: "Purchase channel",
  zip_code: "Zip code class",
};

const dollars = (x: number) => (x === 0 ? "$0" : fmtSignedDollars(x).replace("+", ""));

function Section({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} className="space-y-4">
      <h2 className="text-xl font-semibold tracking-tight">{title}</h2>
      {children}
    </section>
  );
}

export default function TargetingPage() {
  const t = getTargeting();
  const training = getTraining();
  const split = getSplit();
  const timeline = getTimeline().timeline;
  const evaluation = timeline.find((e) => e.event === "holdout_evaluation");
  const seal = timeline.find((e) => e.event === "holdout_seal");
  const ciLevel = t.bootstrap.interval.replace("percentile ", "");
  const k = { "Mens E-Mail": t.selected.p4a_k, "Womens E-Mail": t.selected.p4b_k } as Record<string, number>;
  const label = (p: string) =>
    p === "P4a" || p === "P4b" ? `${POLICY_LABEL[p]} (k = ${k[p === "P4a" ? "Mens E-Mail" : "Womens E-Mail"]}%, chosen on training)` : POLICY_LABEL[p];

  // Policy comparison: net value vs sending nothing, with paired CIs.
  const series: Series[] = [{ key: "nv", name: `Net value vs P0, ${ciLevel} CI`, color: "var(--series-1)" }];
  const scale = niceDomain(t.policies.flatMap((p) => p.net_value_vs_p0_ci), 4);
  const kScale = niceDomain(Object.values(t.net_value_by_k).flatMap((c) => c.flatMap((r) => r.net_value_vs_p0_ci)));

  return (
    <div className="space-y-12">
      <header className="space-y-4">
        <h1 className="text-3xl font-semibold tracking-tight">Does targeting beat sending to everyone?</h1>
        <p className="max-w-2xl text-muted">
          Seven policies, each fixed before the holdout was opened, compared on {fmtInt(t.n_holdout)} customers who were
          set aside before any model was trained. Net value = revenue per customer minus an assumed{" "}
          {dollars(t.cost)} per email sent.
        </p>
        <div role="note" className="rounded-lg border-2 border-accent/60 bg-accent/10 p-4 text-sm">
          <strong>The holdout was evaluated once</strong>
          {evaluation && (
            <>
              , in commit{" "}
              <a className="font-mono text-accent underline" href={commitUrl(evaluation.sha)}>{evaluation.short_sha}</a> (
              {evaluation.date_utc})
            </>
          )}
          , by code at{" "}
          <a className="font-mono text-accent underline" href={commitUrl(t.evaluated_at_code_commit_sha)}>
            {shortSha(t.evaluated_at_code_commit_sha)}
          </a>
          . Its customer list was sealed
          {seal && (
            <>
              {" "}in{" "}
              <a className="font-mono text-accent underline" href={commitUrl(seal.sha)}>{seal.short_sha}</a>
            </>
          )}{" "}
          before training (hash <code className="break-all">{split.holdout_index_sha256.slice(0, 16)}…</code>).
        </div>
      </header>

      <Section id="policies" title="1. Policy comparison on the holdout">
        <p className="text-muted">
          Winner: <strong className="text-ink">{t.winner.winner}</strong>. {t.winner.reason} A targeted policy could replace
          the best blanket policy ({t.winner.best_blanket}) only if the paired {ciLevel} interval of their difference lay
          entirely above zero.
        </p>
        <IntervalChart
          series={series}
          legend={false}
          domain={scale.domain}
          ticks={scale.ticks}
          format={dollars}
          axisLabel="Net revenue per customer vs sending nothing (P0), dollars"
          rows={t.policies.map((p) => ({
            id: p.policy,
            label: (
              <>
                {p.policy}
                {p.policy === t.winner.winner && <span className="ml-2 rounded bg-pass-bg px-1.5 text-xs text-pass">winner</span>}
                <span className="block text-xs font-normal text-muted">{label(p.policy)}</span>
              </>
            ),
            aside: `sends to ${fmtPct(p.share_sent, 0)}`,
            detail: (
              <>
                Net {fmtSignedDollars(p.net_value_vs_p0)} ({fmtSignedDollars(p.net_value_vs_p0_ci[0])} to{" "}
                {fmtSignedDollars(p.net_value_vs_p0_ci[1])}) · revenue {fmtSignedDollars(p.incremental_revenue_vs_p0)} (
                {fmtSignedDollars(p.incremental_revenue_vs_p0_ci[0])} to {fmtSignedDollars(p.incremental_revenue_vs_p0_ci[1])})
                {p.net_value_minus_best_blanket !== undefined && (
                  <>
                    <br />
                    {p.net_value_minus_best_blanket === 0 &&
                    p.net_value_minus_best_blanket_ci![0] === 0 &&
                    p.net_value_minus_best_blanket_ci![1] === 0 ? (
                      <>Assigns every customer the same action as {t.winner.best_blanket}.</>
                    ) : (
                      <>
                        vs {t.winner.best_blanket}: {fmtSignedDollars(p.net_value_minus_best_blanket)} (
                        {fmtSignedDollars(p.net_value_minus_best_blanket_ci![0])} to{" "}
                        {fmtSignedDollars(p.net_value_minus_best_blanket_ci![1])})
                      </>
                    )}
                  </>
                )}
              </>
            ),
            summary: `${p.policy}: net ${fmtSignedDollars(p.net_value_vs_p0)} vs sending nothing`,
            values: { nv: { est: p.net_value_vs_p0, lo: p.net_value_vs_p0_ci[0], hi: p.net_value_vs_p0_ci[1] } },
          }))}
        />
        <p className="text-xs text-muted">
          Estimator: {t.estimator}; {fmtInt(t.bootstrap.resamples)} paired bootstrap resamples. Robustness check (
          {t.robustness_estimator}):{" "}
          {t.hajek_sign_flags.length === 0
            ? "agrees in sign with the primary estimator for every policy."
            : `disagrees in sign for ${t.hajek_sign_flags.join(", ")}.`}
        </p>
      </Section>

      <Section id="qini" title="2. Can the models rank customers by uplift?">
        <p className="text-muted">
          A Qini curve shows cumulative incremental revenue when customers are targeted in order of predicted uplift. A
          model that ranks well bows above the straight line of random targeting; the coefficient is the area between them,
          per customer.
        </p>
        <div className="grid gap-4 lg:grid-cols-2">
          {Object.entries(t.qini_holdout).map(([arm, q]) => {
            const ys = niceDomain([...q.q, 0]);
            const last = q.q[q.q.length - 1];
            return (
              <div key={arm} className="space-y-2 rounded-lg border border-line bg-surface p-4">
                <div className="text-sm">
                  <span className="font-medium">{arm}</span>{" "}
                  <span className="num text-muted">
                    · holdout Qini {fmtSignedDollars(q.coefficient)} per customer · training (out-of-fold){" "}
                    {fmtSignedDollars(training.oof_qini[arm].coefficient)}
                  </span>
                </div>
                <LineChart
                  series={[
                    { key: "model", name: "Model ranking", color: "var(--series-1)", points: q.phi.map((x, i) => ({ x, y: q.q[i] })) },
                    { key: "random", name: "Random targeting", color: "var(--zero)", dashed: true, points: q.phi.map((x) => ({ x, y: x * last })) },
                  ]}
                  xDomain={[0, 1]}
                  yDomain={ys.domain}
                  xTicks={[0, 0.25, 0.5, 0.75, 1]}
                  yTicks={ys.ticks}
                  xFormat="percent"
                  yFormat="dollars0"
                  xLabel="Share of customers targeted"
                  yLabel="Cumulative incremental revenue"
                  height={200}
                />
              </div>
            );
          })}
        </div>
        <p className="text-xs text-muted">{training.oof_note}</p>
      </Section>

      <Section id="k" title="3. Net value by targeting depth (descriptive)">
        <p className="text-muted">
          k was chosen on the training split (Mens {t.selected.p4a_k}%, Womens {t.selected.p4b_k}%). These holdout curves are
          shown for context only; picking k from them would reuse the holdout.
        </p>
        <div className="grid gap-4 lg:grid-cols-2">
          {Object.entries(t.net_value_by_k).map(([arm, curve]) => (
            <div key={arm} className="space-y-2">
              <div className="text-sm font-medium">{arm} to the top k%</div>
              <IntervalChart
                series={series}
                legend={false}
                domain={kScale.domain}
                ticks={kScale.ticks}
                format={dollars}
                axisLabel="Net revenue per customer vs P0, dollars"
                rows={curve.map((r) => ({
                  id: String(r.k),
                  label: `k = ${r.k}%${r.k === k[arm] ? " (chosen)" : ""}`,
                  aside: fmtSignedDollars(r.net_value_vs_p0),
                  summary: `k ${r.k}%: ${fmtSignedDollars(r.net_value_vs_p0)}`,
                  values: { nv: { est: r.net_value_vs_p0, lo: r.net_value_vs_p0_ci[0], hi: r.net_value_vs_p0_ci[1] } },
                }))}
              />
            </div>
          ))}
        </div>
      </Section>

      <Section id="p3" title="4. The segment rule (P3), chosen by cross-validation">
        <p className="text-muted">
          One candidate rule per pre-specified dimension, each giving every segment the action with the highest training net
          revenue; the candidate with the best 5-fold cross-validated net value on the training split was selected, with no
          human choice.
        </p>
        <ul className="num space-y-1 text-sm">
          {training.selection.p3_candidates.map((c) => (
            <li key={c.dimension}>
              {DIMENSION_LABEL[c.dimension] ?? c.dimension}: CV net value {fmtSignedDollars(c.cv_net_value_mean)} per customer
              {c.dimension === training.selection.p3_selected_dimension && (
                <span className="ml-2 rounded bg-pass-bg px-1.5 text-xs text-pass">selected</span>
              )}
            </li>
          ))}
        </ul>
        {training.selection.p3_candidates.filter(
          (c) => c.cv_net_value_mean === Math.max(...training.selection.p3_candidates.map((x) => x.cv_net_value_mean)),
        ).length > 1 && (
          <p className="text-xs text-muted">
            The top candidates tied exactly because their rules made identical assignments; the pre-registered tie-break
            (dimension order) selected the first.
          </p>
        )}
        <p className="text-sm">
          Selected rule ({DIMENSION_LABEL[t.selected.p3_dimension] ?? t.selected.p3_dimension}):{" "}
          {Object.entries(t.selected.p3_rule)
            .map(([seg, action]) => `${displaySegment(t.selected.p3_dimension, seg)} → ${action}`)
            .join("; ")}
          .
        </p>
        {t.selected.p3_dimension === "zip_code" &&
          Object.entries(SOURCE_SPELLING_FIXES).map(([raw, shown]) => (
            <p key={raw} className="text-xs text-muted">
              “{shown}” is spelled “{raw}” in the source file; exports keep the source spelling.
            </p>
          ))}
        <p className="text-xs text-muted">
          Training split: {fmtInt(training.n_train)} customers. Hyperparameters chosen by 5-fold CV:{" "}
          {Object.entries(training.tuning)
            .map(([arm, v]) => `${arm} depth ${v.chosen.max_depth}, rate ${v.chosen.learning_rate}, ${v.chosen.max_iter} trees, leaf ${v.chosen.min_samples_leaf}`)
            .join("; ")}
          . Uplift-assignment policy on training (out-of-fold):{" "}
          {Object.entries(training.p5_training_oof_action_share)
            .map(([a, s]) => `${a} ${fmtPct(s, 1)}`)
            .join(", ")}
          .
        </p>
      </Section>
    </div>
  );
}
