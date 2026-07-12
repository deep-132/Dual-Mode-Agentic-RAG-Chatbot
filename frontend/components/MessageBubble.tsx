import type { ChatMessage } from "@/lib/types";
import ToolBadge from "./ToolBadge";
import CitationPanel from "./CitationPanel";
import SqlPanel from "./SqlPanel";
import { AssistantAvatar, UserAvatar } from "./Avatar";

export default function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex animate-fade-in-up gap-2.5 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      {isUser ? <UserAvatar /> : <AssistantAvatar />}

      <div className={`min-w-0 max-w-[80%] ${isUser ? "items-end" : "items-start"} flex flex-col`}>
        <div
          className={`rounded-2xl px-4 py-2.5 whitespace-pre-wrap break-words shadow-sm ${
            isUser
              ? "rounded-tr-sm bg-gradient-to-br from-indigo-600 to-indigo-500 text-white"
              : "rounded-tl-sm border border-slate-200 bg-white text-slate-800 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
          }`}
        >
          {message.content}
          {message.isStreaming && !message.content && (
            <span className="inline-flex items-center gap-1 py-1">
              <span className="h-1.5 w-1.5 animate-bounce-dot rounded-full bg-current [animation-delay:-0.3s]" />
              <span className="h-1.5 w-1.5 animate-bounce-dot rounded-full bg-current [animation-delay:-0.15s]" />
              <span className="h-1.5 w-1.5 animate-bounce-dot rounded-full bg-current" />
            </span>
          )}
          {message.isStreaming && message.content && (
            <span className="ml-0.5 inline-block w-1.5 animate-pulse text-indigo-400">▍</span>
          )}
          {message.error && (
            <span className="flex items-center gap-1.5 text-red-500 dark:text-red-400">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="9" />
                <path strokeLinecap="round" d="M12 8v5M12 16h.01" />
              </svg>
              {message.error}
            </span>
          )}
        </div>

        {!isUser && message.meta && (
          <div className="mt-1.5 w-full">
            <ToolBadge tools={message.meta.tools_used} />
            <CitationPanel citations={message.meta.citations} />
            <SqlPanel queries={message.meta.sql_queries} />
          </div>
        )}
      </div>
    </div>
  );
}
