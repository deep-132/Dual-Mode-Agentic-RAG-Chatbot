# Northwind Gadgets — Dual-Mode Agentic RAG + Text-to-SQL Support Chatbot

A single conversational agent that answers questions about a fictional e-commerce
company, **Northwind Gadgets**, by deciding per-question whether to retrieve from
its policy documents (vector RAG), query its structured orders data (text-to-SQL),
or both — with citations and generated SQL always shown in the UI.

Built for an EMB technical assessment. This document covers architecture, the
reasoning behind each technical choice, how routing works, and known limitations.

---

## 1. Live Demo / Repo

- Live URL: https://dual-mode-agentic-rag-chatbot-psi.vercel.app/
- Backend API: https://northwind-support-backend.onrender.com (Render free tier — may cold-start after idling, see §9)
- GitHub repo: https://github.com/deep-132/Dual-Mode-Agentic-RAG-Chatbot

---

## 2. Architecture

```
                      ┌─────────────────────────┐
                      │   Next.js Frontend       │
                      │   (chat UI, SSE client)  │
                      └───────────┬─────────────┘
                                  │ POST /api/chat (stream)
                                  ▼
                      ┌─────────────────────────┐
                      │       FastAPI            │
                      │   app/api/chat.py         │
                      └───────────┬─────────────┘
                                  ▼
                      ┌─────────────────────────┐
                      │   AgentOrchestrator       │
                      │   app/agent/orchestrator  │
                      │                           │
                      │  Phase 1 (non-streaming): │
                      │   Azure OpenAI + tools    │
                      │   decides & calls tools   │
                      │   in a loop               │
                      │                           │
                      │  Phase 2 (streaming):     │
                      │   Azure OpenAI composes   │
                      │   final answer, streamed  │
                      │   token-by-token          │
                      └──────┬─────────────┬──────┘
                             │             │
                 tool: search_documents   tool: query_orders
                             │             │
                             ▼             ▼
                 ┌────────────────────┐  ┌───────────────────────┐
                 │ DocumentRetriever   │  │ OrdersRepository       │
                 │ FAISS + MiniLM      │  │ SQLite (read-only)     │
                 │ (5 policy docs,     │  │ (orders.csv, ~200 rows)│
                 │  chunked by section)│  │ + SQL safety guard     │
                 └────────────────────┘  └───────────────────────┘
```

Both tools are exposed to the LLM as OpenAI-style function-calling tools.
The LLM — not a hand-written if/else router — decides which tool(s) to call,
based on tool descriptions and the user's question. See §4 for why.

---

## 3. Component choices and reasoning

| Layer | Choice | Why |
|---|---|---|
| LLM | Azure OpenAI (`gpt-4o` by default, configurable deployment name) | Organization already has an Azure OpenAI subscription/API key; Azure OpenAI's Chat Completions API supports function calling and streaming identically to OpenAI's, so the same client code works against either. |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2`, run locally | The assignment allows "any provider" for the *LLM*, but says nothing about embeddings needing to come from the same provider. Running embeddings locally means: no second API key/quota to provision, zero marginal cost per query, deterministic output (useful for a graded fixed dataset), and the model runs fully inside the Docker image — nothing about the vector-search half of this system depends on network access. The trade-off is a heavier Docker image (~90MB model weights) and lower embedding quality than e.g. `text-embedding-3-large` — acceptable here because the corpus is 5 short policy documents, not a large heterogeneous corpus. |
| Vector store | FAISS (`IndexFlatIP`, cosine via normalized vectors) | The corpus is ~20 short chunks total. An exact flat index is simplest, fastest to reason about, and has zero infra to run (no pgvector/Pinecone/Supabase service to provision and keep alive just to serve a live-URL grading demo). FAISS is explicitly listed as an acceptable choice in the brief. For a larger/production corpus I'd reach for pgvector (keeps vectors next to relational data, one fewer moving part operationally) — see Limitations. |
| Structured data | SQLite, built from `orders.csv` at container-build/startup time, queried through **generated SQL** (never embedded) | The brief explicitly requires text-to-SQL, not RAG-over-rows. SQLite needs no server process, ships as a single file, and is trivial to rebuild deterministically from the fixed CSV — appropriate for ~200 rows. |
| SQL safety | Two independent layers: (1) static validation — single statement, `SELECT`-only, table whitelist, forbidden-keyword check, forced `LIMIT`; (2) `PRAGMA query_only = ON` on every connection, i.e. **engine-level** read-only enforcement | Static SQL validation by regex/parsing can never be proven complete against a sufficiently adversarial LLM output. Layer (2) doesn't need to be — SQLite itself refuses any write regardless of what slipped past layer (1). This is the single design decision I'd most want to walk through in an interview (see `backend/app/sql/guard.py` and `backend/app/sql/db.py`). |
| Backend | FastAPI, Server-Sent Events for streaming | Native `async`, first-class typing via Pydantic, and `StreamingResponse` makes token-level SSE straightforward without a websocket. |
| Frontend | Next.js 16 (App Router) + Tailwind, hand-rolled SSE client via `fetch` | `EventSource` can't send a POST body or custom headers, and this request needs both (message + conversation history) — a manual `fetch` + `ReadableStream` reader consumes the same `event:`/`data:` framing with full control over the request. |
| Packaging | Multi-stage Dockerfiles for both services + `docker-compose.yml` | Reproducible builds; FAISS index is **prebuilt at image-build time** (not on first request) so a bad document fails CI/build, not a user's first query, and cold starts are fast. |

---

## 4. How routing works

Routing is **not** a keyword classifier or a separate "router LLM call" — it's
native LLM tool-calling, the same pattern used by "agentic RAG": the model is
given two tool definitions and decides, per turn, which to invoke (see
`backend/app/agent/tools.py` for the exact schemas and
`backend/app/agent/orchestrator.py` for the loop).

**Two-phase turn:**

1. **Phase 1 — decide & gather (non-streaming, temperature 0).** The model is
   sent the user's question with both tools available and `tool_choice="auto"`.
   It may:
   - call `search_documents` (policy questions),
   - call `query_orders` (data questions),
   - call **both**, optionally sequentially — e.g. for *"Our policy allows
     30-day returns; did order ORD-1044 qualify?"* the model typically calls
     `search_documents("return window")` and `query_orders("SELECT * FROM
     orders WHERE order_id = 'ORD-1044'")`, then reasons over both results, or
   - call **neither**, if the question is out of scope.

   This repeats (tool results are appended to the conversation and fed back)
   up to `MAX_TOOL_ITERATIONS` (default 4), so the model can use one tool's
   result to decide it needs the other. The loop ends when the model stops
   requesting tools.

2. **Phase 2 — compose & stream (streaming, temperature 0).** With all tool
   results now in context, one final call generates the user-facing answer,
   streamed token-by-token over SSE. A `meta` SSE event is emitted *before*
   this phase starts, carrying which tool(s) were used, the citations
   retrieved, and the SQL executed — so the UI can render the tool badge and
   citation/SQL panel immediately, without waiting for the prose to finish.

**Why split into two phases instead of one streaming call with tools?**
Streaming is only valuable for content the user reads as it arrives. Tool-call
arguments are JSON the user never sees; there's nothing to gain from streaming
phase 1, and doing so would mean incrementally parsing partial JSON argument
deltas for no UX benefit. Splitting also makes phase 1 independently unit-testable
against a scripted fake LLM client with zero network calls (see
`backend/tests/test_routing.py`) — the hardest-to-get-right part of this system
(does it call the right tool(s), does it stop, does it respect the iteration cap)
is tested without needing a live Azure deployment.

**Grounding / anti-hallucination**, enforced entirely via the system prompt
(`orchestrator.py::SYSTEM_PROMPT_TEMPLATE`):
- Never state a policy fact that wasn't actually returned by `search_documents`
  in that conversation.
- Never state a data fact, or invent a column/table, that wasn't actually
  returned by `query_orders`.
- If a lookup returns zero rows (e.g. a non-existent order ID), say so — never
  assume the row exists.
- If neither tool can answer the question, respond with the exact fallback
  string `"I don't have that information."` rather than answering from the
  model's general knowledge.
- The graded "current date" (2026-06-15) is injected into the system prompt so
  relative-date questions ("last month", "this year") resolve deterministically.

---

## 5. Repository layout

```
backend/
  app/
    agent/         orchestrator (routing loop) + tool schemas/executors
    api/            FastAPI routes (chat SSE endpoint)
    llm/            Azure OpenAI client wrapper
    rag/            document chunking, FAISS index build, retriever
    sql/            CSV → SQLite loader, SQL safety guard
    config.py       typed settings (env-driven)
    schemas.py      shared Pydantic models
    main.py          app + startup wiring
  data/             documents/*.md, orders.csv (the fixed dataset)
  scripts/          build_index.py (prebuild FAISS at image build time)
  tests/            pytest — SQL guard, ingest chunking, routing loop
  Dockerfile
frontend/
  app/               Next.js App Router pages
  components/       ChatWindow, MessageBubble, ToolBadge, CitationPanel, SqlPanel
  lib/              types.ts, api.ts (hand-rolled SSE client)
  Dockerfile
docker-compose.yml
.env.example
```

---

## 6. Running locally

### Docker (recommended)
```bash
cp .env.example .env   # fill in AZURE_OPENAI_* values
docker compose up --build
# frontend: http://localhost:3000
# backend:  http://localhost:8000/health
```

### Without Docker
```bash
# Backend
cd backend
python -m venv .venv && source .venv/Scripts/activate   # or .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
python -m scripts.build_index   # prebuild FAISS index (one-time)
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

### Tests
```bash
cd backend
pytest -v
```

---

## 7. Sample questions to try

| Question | Expected path |
|---|---|
| "What is the refund window?" | `search_documents` only, cites `returns_policy.md` |
| "How many orders are currently pending?" | `query_orders` only |
| "What was total revenue last month?" | `query_orders` only (uses fixed current date 2026-06-15 → May 2026) |
| "Our policy allows 30-day returns — did order ORD-1044 qualify?" | both tools |
| "Does Northwind Gadgets offer a pet insurance plan?" | neither tool; fallback message |

---

## 8. Deployment

This is Docker-first and platform-agnostic — any host that runs
`docker compose` or two separate Docker containers works. The live demo above
is deployed as:

- **Backend** → [Render](https://render.com), a Docker Web Service built from
  `backend/Dockerfile` (Root Directory: `backend`, Dockerfile Path: `Dockerfile`
  — Render resolves the Dockerfile path relative to Root Directory, not the
  repo root). `AZURE_OPENAI_*` and `ALLOWED_ORIGINS` are set as environment
  variables in the Render dashboard (injected at container runtime only, never
  into the `docker build` step — see `require_azure_credentials` in
  `app/config.py` for why credential validation is deliberately deferred to
  first use rather than done at Settings-construction time). Render's free
  tier cold-starts after idling (~30-60s first request) — see §9.
- **Frontend** → [Vercel](https://vercel.com), native Next.js build (Root
  Directory: `frontend`; the `frontend/Dockerfile` is unused here, kept for the
  `docker compose` / self-hosted path below). `NEXT_PUBLIC_API_URL` is set as a
  build-time environment variable pointing at the Render backend URL above,
  since Next.js inlines `NEXT_PUBLIC_*` vars into the client bundle at build
  time, not runtime.
- A plain VM (AWS/GCP/Azure) or a single Render/Fly.io host works identically
  via `docker compose up -d` behind any reverse proxy/TLS terminator, using
  both Dockerfiles instead of splitting across two platforms.

---

## 9. Known limitations

- **Single shared SQLite file, no connection pooling.** Fine for ~200 rows and
  demo-level concurrency; a real production system would use Postgres and a
  connection pool.
- **Local embedding model quality.** `all-MiniLM-L6-v2` is small and general-purpose;
  a larger domain-tuned or API-based embedding model would improve recall on a
  larger/messier document corpus. Chosen deliberately here to avoid a second
  API dependency (see §3).
- **No conversation persistence.** History lives in frontend React state only;
  refreshing the page loses it. Adding a session store (Redis/Postgres) would be
  the next step for multi-session/multi-device use.
- **No streaming during tool-selection.** By design (§4) — phase 1 (embedding
  search + SQL execution + the routing LLM call) produces no user-facing
  tokens. The frontend shows an animated "thinking" indicator during this gap
  so it doesn't look frozen, but there's no way to show partial progress
  (e.g. "searching documents..." vs "querying orders...") without the backend
  emitting intermediate SSE events, which isn't implemented.
- **Tool-iteration cap (4) is a blunt backstop**, not a smart budget — if a
  future mixed question genuinely needs more than 4 tool round-trips, it will
  be cut off. Never observed in testing against the provided dataset.
- **No rate limiting / auth on the API.** Out of scope for the assignment but
  required before any real deployment beyond a graded demo.
- **SQL guard is static-analysis-based**, not a full SQL parser — see §3 for why
  the engine-level `query_only` pragma is the real backstop rather than the
  regex checks.
- **Dataset has two out-of-sequence order IDs** (`ORD-1207`, `ORD-1233`) in the
  provided `orders.csv`, kept exactly as supplied since it's the fixed grading
  dataset. The agent handles them the same as any other order — no special-casing.
