export type ToolName = "search_documents" | "query_orders";

export interface Citation {
  source: string;
  section: string;
  text: string;
  score: number;
}

export interface ChatMeta {
  tools_used: ToolName[];
  citations: Citation[];
  sql_queries: string[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  meta?: ChatMeta;
  isStreaming?: boolean;
  error?: string;
}
