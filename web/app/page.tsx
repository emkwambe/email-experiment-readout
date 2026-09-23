import Link from "next/link";
import { getIntegrity, getManifest, getSrm } from "@/lib/data";
import { commitUrl, fmtInt, shortSha } from "@/lib/format";

const PAGES = [
  { href: "/plan", title: "The analysis plan", body: "Hypotheses, metrics, tests and the decision rule, fixed before any results were seen." },
  { href: "/checks", title: "Data-quality checks", body: "Integrity gates, sample-ratio check, covariate balance and planning power." },
  { href: "/how-its-built", title: "How it's built", body: "How Claude Code was used, and how its work was verified." },
];

export default function Home() {
  const m = getManifest();
  const integrity = getIntegrity();
  const armCount = Object.keys(getSrm().observed).length;
  const gatesOk = !m.summary.halted;
  return (
    <div className="space-y-10">
      <section className="space-y-5">
        <span className="inline-flex items-center gap-2 rounded-full border border-accent/40 bg-accent/10 px-3 py-1 text-sm font-medium text-accent">
          <span aria-hidden className="h-2 w-2 rounded-full bg-accent" />
          Pre-registered · outcomes locked
        </span>
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Did the emails make money, and for whom?</h1>
        <p className="max-w-2xl text-lg leading-relaxed text-muted">
          A retailer randomly split {fmtInt(integrity.row_count)} recent customers into {armCount} groups: one got an email
          featuring men&apos;s merchandise, one got an email featuring women&apos;s merchandise, and one got nothing. The
          question is whether either email generated incremental revenue, which one, and which customers the team should
          send each email to next time, given that every send has a cost.
        </p>
        <p className="max-w-2xl text-muted">
          The analysis plan was committed before any data was loaded:{" "}
          <a className="font-mono text-accent underline" href={commitUrl(m.preregistration.commit_sha)}>
            {shortSha(m.preregistration.commit_sha)}
          </a>{" "}
          ({m.preregistration.committed_utc}). No results by email group have been computed yet.
        </p>
      </section>

      <section
        className={`rounded-lg border p-5 ${gatesOk ? "border-pass/40 bg-pass-bg" : "border-fail/40 bg-fail-bg"}`}
      >
        <h2 className="font-semibold">{gatesOk ? "Data-quality gates passed" : "Analysis halted by a data-quality gate"}</h2>
        <p className="mt-1 text-sm text-muted">
          Integrity {m.summary.integrity_passed ? "passed" : "failed"} · Sample-ratio check{" "}
          {m.summary.srm_halt ? "halted" : "passed"} · {m.summary.balance_n_flagged} covariates flagged for imbalance.{" "}
          <Link href="/checks" className="text-accent underline">
            See the checks
          </Link>
        </p>
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        {PAGES.map((p) => (
          <Link key={p.href} href={p.href} className="rounded-lg border border-line bg-surface p-5 hover:border-accent">
            <h3 className="font-semibold">{p.title}</h3>
            <p className="mt-2 text-sm text-muted">{p.body}</p>
          </Link>
        ))}
      </section>
    </div>
  );
}
