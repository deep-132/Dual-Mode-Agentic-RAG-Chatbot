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

export default function SqlPanel({ queries }: { queries: string[] }) {
  if (queries.length === 0) return null;

  return (
    <details className="group mt-2 overflow-hidden rounded-lg border border-emerald-200/70 bg-emerald-50/60 text-sm dark:border-emerald-500/20 dark:bg-emerald-500/5">
      <summary className="flex cursor-pointer list-none items-center justify-between px-3 py-1.5 font-medium text-emerald-900 marker:content-none dark:text-emerald-300">
        <span>Generated SQL ({queries.length})</span>
        <ChevronIcon />
      </summary>
      <ul className="space-y-2 px-3 pb-3">
        {queries.map((q, i) => (
          <li key={i}>
            <pre className="overflow-x-auto rounded-md bg-slate-900 p-2.5 text-xs leading-relaxed text-emerald-300 ring-1 ring-inset ring-white/5">
              <code>{q}</code>
            </pre>
          </li>
        ))}
      </ul>
    </details>
  );
}
