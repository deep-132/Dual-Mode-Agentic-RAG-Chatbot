import type { ToolName } from "@/lib/types";

const LABELS: Record<ToolName, { label: string; className: string }> = {
  search_documents: { label: "📄 Document RAG", className: "bg-blue-100 text-blue-800" },
  query_orders: { label: "🗄️ SQL Query", className: "bg-emerald-100 text-emerald-800" },
};

export default function ToolBadge({ tools }: { tools: ToolName[] }) {
  if (tools.length === 0) {
    return (
      <span className="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-600">
        No tool used
      </span>
    );
  }

  return (
    <div className="flex gap-1.5 flex-wrap">
      {tools.map((tool) => (
        <span
          key={tool}
          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${LABELS[tool].className}`}
        >
          {LABELS[tool].label}
        </span>
      ))}
    </div>
  );
}
