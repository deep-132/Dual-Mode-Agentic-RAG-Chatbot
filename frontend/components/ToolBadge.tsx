import type { ToolName } from "@/lib/types";

function DocIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M14 3v5h5" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 3h8l5 5v13a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z" />
      <path strokeLinecap="round" d="M9 13h6M9 17h6" />
    </svg>
  );
}

function SqlIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
      <ellipse cx="12" cy="6" rx="7" ry="3" />
      <path strokeLinecap="round" d="M5 6v12c0 1.66 3.13 3 7 3s7-1.34 7-3V6" />
      <path strokeLinecap="round" d="M5 12c0 1.66 3.13 3 7 3s7-1.34 7-3" />
    </svg>
  );
}

const CONFIG: Record<ToolName, { label: string; icon: () => JSX.Element; className: string }> = {
  search_documents: {
    label: "Document RAG",
    icon: DocIcon,
    className:
      "bg-blue-50 text-blue-700 ring-1 ring-inset ring-blue-200 dark:bg-blue-500/10 dark:text-blue-300 dark:ring-blue-500/30",
  },
  query_orders: {
    label: "SQL Query",
    icon: SqlIcon,
    className:
      "bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-300 dark:ring-emerald-500/30",
  },
};

export default function ToolBadge({ tools }: { tools: ToolName[] }) {
  if (tools.length === 0) {
    return (
      <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-500 ring-1 ring-inset ring-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:ring-slate-700">
        No tool used
      </span>
    );
  }

  return (
    <div className="flex flex-wrap gap-1.5">
      {tools.map((tool) => {
        const { label, icon: Icon, className } = CONFIG[tool];
        return (
          <span
            key={tool}
            className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${className}`}
          >
            <Icon />
            {label}
          </span>
        );
      })}
    </div>
  );
}
