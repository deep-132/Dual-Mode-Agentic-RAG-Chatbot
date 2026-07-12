import type { Citation } from "@/lib/types";

export default function CitationPanel({ citations }: { citations: Citation[] }) {
  if (citations.length === 0) return null;

  return (
    <details className="mt-2 rounded-md border border-blue-200 bg-blue-50 text-sm">
      <summary className="cursor-pointer px-3 py-1.5 font-medium text-blue-900">
        Sources ({citations.length})
      </summary>
      <ul className="space-y-2 px-3 pb-3">
        {citations.map((c, i) => (
          <li key={i} className="rounded bg-white p-2 border border-blue-100">
            <div className="font-mono text-xs text-blue-700">
              {c.source} — {c.section}{" "}
              <span className="text-gray-400">(score {c.score.toFixed(2)})</span>
            </div>
            <p className="mt-1 text-gray-700">{c.text}</p>
          </li>
        ))}
      </ul>
    </details>
  );
}
