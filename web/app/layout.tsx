import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import { getManifest } from "@/lib/data";
import { commitUrl, shortSha } from "@/lib/format";
import { ThemeToggle, themeInitScript } from "./theme-toggle";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "LiftLab",
  description: "A pre-registered analysis of a randomized email experiment.",
};

const NAV = [
  { href: "/plan", label: "Plan" },
  { href: "/checks", label: "Checks" },
  { href: "/how-its-built", label: "How it's built" },
];

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const { manifest } = getManifest();
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className={`${geistSans.variable} ${geistMono.variable} font-sans antialiased`}>
        <header className="border-b border-line">
          <div className="mx-auto flex max-w-4xl flex-wrap items-center justify-between gap-x-4 gap-y-2 px-4 py-4 sm:px-6">
            <Link href="/" className="font-semibold tracking-tight">
              LiftLab
            </Link>
            <nav className="flex flex-wrap items-center gap-x-3 gap-y-2 text-sm sm:gap-x-4">
              {NAV.map((n) => (
                <Link key={n.href} href={n.href} className="text-muted hover:text-ink">
                  {n.label}
                </Link>
              ))}
              <ThemeToggle />
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-4xl px-4 py-10 sm:px-6">{children}</main>
        <footer className="border-t border-line">
          <div className="mx-auto max-w-4xl px-4 py-6 text-xs text-muted sm:px-6">
            Data exported by <code>{manifest.script}</code> at commit{" "}
            <a className="underline" href={commitUrl(manifest.commit_sha)}>
              {shortSha(manifest.commit_sha)}
            </a>{" "}
            on {manifest.generated_utc}. Dataset SHA-256{" "}
            <code className="break-all">{manifest.dataset_sha256}</code>.
          </div>
        </footer>
      </body>
    </html>
  );
}
