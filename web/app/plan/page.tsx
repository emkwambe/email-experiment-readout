import type { Metadata } from "next";
import ReactMarkdown from "react-markdown";
import remarkBreaks from "remark-breaks";
import remarkGfm from "remark-gfm";
import { getManifest, getPlanMarkdown } from "@/lib/data";
import { blobUrl, commitUrl, shortSha } from "@/lib/format";

export const metadata: Metadata = { title: "Analysis plan · LiftLab" };

export default function PlanPage() {
  const { preregistration } = getManifest();
  return (
    <div className="space-y-6">
      <p className="rounded-lg border border-line bg-surface p-4 text-sm text-muted">
        Rendered from{" "}
        <a className="text-accent underline" href={blobUrl(preregistration.file)}>
          {preregistration.file}
        </a>
        . First committed in{" "}
        <a className="font-mono text-accent underline" href={commitUrl(preregistration.commit_sha)}>
          {shortSha(preregistration.commit_sha)}
        </a>{" "}
        ({preregistration.committed_utc}). The body is locked; changes appear only under Deviations.
      </p>
      <article className="prose prose-neutral max-w-none dark:prose-invert prose-headings:tracking-tight prose-a:text-accent">
        <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>{getPlanMarkdown()}</ReactMarkdown>
      </article>
    </div>
  );
}
