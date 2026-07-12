import type { Citation } from "@/lib/types";

function ChevronIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.2"
      className="shrink-0 transition-transform duration-200 group-open:rotate-180"
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="m6 9 6 6 6-6" />
    </svg>
  );
}

export default function CitationPanel({ citations }: { citations: Citation[] }) {
  if (citations.length === 0) return null;

  return (
    <details className="group mt-2 overflow-hidden rounded-lg border border-blue-200/70 bg-blue-50/60 text-sm dark:border-blue-500/20 dark:bg-blue-500/5">
      <summary className="flex cursor-pointer list-none items-center justify-between px-3 py-1.5 font-medium text-blue-900 marker:content-none dark:text-blue-300">
        <span>Sources ({citations.length})</span>
        <ChevronIcon />
      </summary>
      <ul className="space-y-2 px-3 pb-3">
        {citations.map((c, i) => (
          <li
            key={i}
            className="rounded-md border border-blue-100 bg-white p-2.5 dark:border-blue-500/10 dark:bg-slate-900/60"
          >
            <div className="flex items-center justify-between gap-2 font-mono text-xs text-blue-700 dark:text-blue-400">
              <span className="truncate">
                {c.source} — {c.section}
              </span>
              <span className="shrink-0 rounded bg-blue-100 px-1.5 py-0.5 text-[10px] text-blue-600 dark:bg-blue-500/15 dark:text-blue-300">
                {c.score.toFixed(2)}
              </span>
            </div>
            <p className="mt-1.5 leading-relaxed text-slate-700 dark:text-slate-300">{c.text}</p>
          </li>
        ))}
      </ul>
    </details>
  );
}
