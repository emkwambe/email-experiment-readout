import type { Metadata } from "next";
import { blobUrl, treeUrl } from "@/lib/format";

export const metadata: Metadata = { title: "How it's built · LiftLab" };

const STEPS = [
  {
    title: "Plan in chat",
    body: "The business question, hypotheses, metrics, gates and decision rule were worked out in conversation with Claude, then written into a pre-registered analysis plan and committed before any data loader existed. Each sprint's scope is written out in full as a sprint file.",
  },
  {
    title: "Execute in Claude Code",
    body: "Claude Code works through the sprint file step by step inside the repository, following binding project rules: no hand-typed numbers, no outcomes compared across groups until the plan allows it, a manifest on every export, and one command that regenerates every published number for a stage. It stops and reports when a step fails instead of working around it.",
  },
  {
    title: "Verify with tests",
    body: "A result isn't done until a test asserts it against an independent computation: effect sizes recomputed in DuckDB SQL from the raw file, Welch tests against scipy and statsmodels, the Newcombe interval against its published worked example, bootstrap and analytic intervals checked for agreement, plus the data-quality gates. A guard test allows outcomes by email group only in the pre-registered estimate files and fails on any targeting output before Sprint 3.",
  },
];

export default function HowItsBuiltPage() {
  return (
    <div className="space-y-10">
      <header className="space-y-3">
        <h1 className="text-3xl font-semibold tracking-tight">How it&apos;s built</h1>
        <p className="max-w-2xl text-muted">
          This project is also a record of how an AI coding agent was used to do analysis work that can be checked. The
          process matters as much as the result, so it is published alongside the code.
        </p>
      </header>

      <ol className="grid gap-4 sm:grid-cols-3">
        {STEPS.map((s, i) => (
          <li key={s.title} className="rounded-lg border border-line bg-surface p-5">
            <div className="text-sm font-medium text-accent">Step {i + 1}</div>
            <h2 className="mt-1 font-semibold">{s.title}</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted">{s.body}</p>
          </li>
        ))}
      </ol>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold tracking-tight">The correction log</h2>
        <p className="max-w-2xl text-muted">
          Every time Claude (in chat or in Claude Code) produced something wrong that a test, a check or a human review
          caught, the error is recorded with how it was caught, the fix, and the guard added to prevent it happening
          again. Each entry lands in the same commit as its fix.
        </p>
        <ul className="space-y-2">
          <li>
            <a className="text-accent underline" href={blobUrl("ai-workflow/correction-log.md")}>
              Read the correction log
            </a>
          </li>
          <li>
            <a className="text-accent underline" href={treeUrl("ai-workflow")}>
              Browse ai-workflow/: sprint prompts and verification evidence
            </a>
          </li>
          <li>
            <a className="text-accent underline" href={blobUrl("CLAUDE.md")}>
              CLAUDE.md: the project rules Claude Code works under
            </a>
          </li>
        </ul>
      </section>
    </div>
  );
}
