"use client";

import { useEffect, useRef, useState } from "react";
import type { ChatMessage } from "@/lib/types";
import { streamChat } from "@/lib/api";
import MessageBubble from "./MessageBubble";

interface Suggestion {
  text: string;
  kind: "doc" | "sql" | "mixed";
}

const SUGGESTIONS: Suggestion[] = [
  { text: "What is the refund window?", kind: "doc" },
  { text: "How many orders are pending right now?", kind: "sql" },
  { text: "Our policy allows 30-day returns — did order ORD-1044 qualify?", kind: "mixed" },
  { text: "What is your policy on remote work?", kind: "doc" },
];

const KIND_STYLES: Record<Suggestion["kind"], { label: string; className: string }> = {
  doc: { label: "RAG", className: "bg-blue-50 text-blue-600 dark:bg-blue-500/10 dark:text-blue-300" },
  sql: { label: "SQL", className: "bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-300" },
  mixed: { label: "BOTH", className: "bg-violet-50 text-violet-600 dark:bg-violet-500/10 dark:text-violet-300" },
};

export default function ChatWindow() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
  }, [input]);

  async function handleSend(overrideText?: string) {
    const text = (overrideText ?? input).trim();
    if (!text || isSending) return;

    const history = messages;
    const userMessage: ChatMessage = { role: "user", content: text };
    const assistantMessage: ChatMessage = { role: "assistant", content: "", isStreaming: true };

    setMessages([...history, userMessage, assistantMessage]);
    setInput("");
    setIsSending(true);

    const updateAssistant = (patch: Partial<ChatMessage>) => {
      setMessages((prev) => {
        const next = [...prev];
        const last = next[next.length - 1];
        next[next.length - 1] = { ...last, ...patch };
        return next;
      });
    };

    try {
      await streamChat(text, history, {
        onMeta: (meta) => updateAssistant({ meta }),
        onToken: (token) =>
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            next[next.length - 1] = { ...last, content: last.content + token };
            return next;
          }),
        onError: (message) => updateAssistant({ error: message, isStreaming: false }),
        onDone: () => updateAssistant({ isStreaming: false }),
      });
    } catch (err) {
      updateAssistant({ error: "Connection failed.", isStreaming: false });
    } finally {
      setIsSending(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        {messages.length === 0 && (
          <div className="mx-auto mt-6 max-w-md text-center">
            <p className="mb-4 text-sm text-slate-500 dark:text-slate-400">
              Ask about policies, orders, or both. Try one of these:
            </p>
            <div className="flex flex-col gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s.text}
                  onClick={() => handleSend(s.text)}
                  className="group flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-left text-sm text-slate-700 shadow-sm transition hover:-translate-y-0.5 hover:border-indigo-300 hover:shadow-md dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-200 dark:hover:border-indigo-500/40"
                >
                  <span>{s.text}</span>
                  <span
                    className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold tracking-wide ${KIND_STYLES[s.kind].className}`}
                  >
                    {KIND_STYLES[s.kind].label}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <MessageBubble key={i} message={m} />
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-900">
        <form
          className="flex items-end gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
        >
          <textarea
            ref={textareaRef}
            rows={1}
            className="max-h-[120px] flex-1 resize-none rounded-2xl border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100 dark:placeholder:text-slate-500 dark:focus:ring-indigo-500/20"
            placeholder="Ask a question..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            disabled={isSending}
          />
          <button
            type="submit"
            aria-label="Send message"
            disabled={isSending || !input.trim()}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-indigo-600"
          >
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="m3 12 18-8-8 18-2-8-8-2Z" />
            </svg>
          </button>
        </form>
      </div>
    </div>
  );
}
