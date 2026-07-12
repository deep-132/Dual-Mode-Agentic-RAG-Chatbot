"use client";

import { useRef, useState } from "react";
import type { ChatMessage } from "@/lib/types";
import { streamChat } from "@/lib/api";
import MessageBubble from "./MessageBubble";

const SUGGESTIONS = [
  "What is the refund window?",
  "How many orders are pending right now?",
  "Our policy allows 30-day returns — did order ORD-1044 qualify?",
  "What is your policy on remote work?",
];

export default function ChatWindow() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

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
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        {messages.length === 0 && (
          <div className="mx-auto max-w-md text-center text-gray-500 mt-8">
            <p className="mb-4">Ask about policies, orders, or both. Try:</p>
            <div className="flex flex-col gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => handleSend(s)}
                  className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-left text-sm hover:border-indigo-300 hover:bg-indigo-50"
                >
                  {s}
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

      <div className="border-t border-gray-200 bg-white p-3">
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
        >
          <input
            className="flex-1 rounded-full border border-gray-300 px-4 py-2 focus:border-indigo-400 focus:outline-none"
            placeholder="Ask a question..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isSending}
          />
          <button
            type="submit"
            disabled={isSending || !input.trim()}
            className="rounded-full bg-indigo-600 px-5 py-2 font-medium text-white disabled:opacity-40"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
