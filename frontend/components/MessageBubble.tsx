import type { ChatMessage } from "@/lib/types";
import ToolBadge from "./ToolBadge";
import CitationPanel from "./CitationPanel";
import SqlPanel from "./SqlPanel";

export default function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[80%] ${isUser ? "order-2" : "order-1"}`}>
        <div
          className={`rounded-2xl px-4 py-2.5 whitespace-pre-wrap break-words ${
            isUser ? "bg-indigo-600 text-white" : "bg-white text-gray-900 border border-gray-200"
          }`}
        >
          {message.content}
          {message.isStreaming && <span className="ml-0.5 animate-pulse">▍</span>}
          {message.error && <span className="text-red-500">{message.error}</span>}
        </div>

        {!isUser && message.meta && (
          <div className="mt-1.5">
            <ToolBadge tools={message.meta.tools_used} />
            <CitationPanel citations={message.meta.citations} />
            <SqlPanel queries={message.meta.sql_queries} />
          </div>
        )}
      </div>
    </div>
  );
}
