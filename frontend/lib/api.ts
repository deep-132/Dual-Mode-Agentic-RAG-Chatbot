import type { ChatMeta, ChatMessage } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface StreamCallbacks {
  onMeta: (meta: ChatMeta) => void;
  onToken: (text: string) => void;
  onError: (message: string) => void;
  onDone: () => void;
}

/**
 * Parses the backend's SSE stream by hand rather than using EventSource,
 * because EventSource can't send a POST body (we need to send the message +
 * history) or custom headers. `fetch` + a manual reader gives full control
 * over the request while still consuming the same `event: ... \n data: ...`
 * framing on the response.
 */
export async function streamChat(
  message: string,
  history: ChatMessage[],
  callbacks: StreamCallbacks,
  signal?: AbortSignal
): Promise<void> {
  const response = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      history: history.map((m) => ({ role: m.role, content: m.content })),
    }),
    signal,
  });

  if (!response.ok || !response.body) {
    callbacks.onError(`Request failed (${response.status})`);
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";

    for (const rawEvent of events) {
      const lines = rawEvent.split("\n");
      const eventLine = lines.find((l) => l.startsWith("event: "));
      const dataLine = lines.find((l) => l.startsWith("data: "));
      if (!eventLine || !dataLine) continue;

      const eventType = eventLine.slice("event: ".length).trim();
      const data = JSON.parse(dataLine.slice("data: ".length));

      if (eventType === "meta") callbacks.onMeta(data as ChatMeta);
      else if (eventType === "token") callbacks.onToken(data.text as string);
      else if (eventType === "error") callbacks.onError(data.message as string);
      else if (eventType === "done") callbacks.onDone();
    }
  }
}
