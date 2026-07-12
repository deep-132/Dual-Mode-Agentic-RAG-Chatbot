export default function SqlPanel({ queries }: { queries: string[] }) {
  if (queries.length === 0) return null;

  return (
    <details className="mt-2 rounded-md border border-emerald-200 bg-emerald-50 text-sm">
      <summary className="cursor-pointer px-3 py-1.5 font-medium text-emerald-900">
        Generated SQL ({queries.length})
      </summary>
      <ul className="space-y-2 px-3 pb-3">
        {queries.map((q, i) => (
          <li key={i}>
            <pre className="overflow-x-auto rounded bg-gray-900 p-2 text-xs text-emerald-300">
              <code>{q}</code>
            </pre>
          </li>
        ))}
      </ul>
    </details>
  );
}
