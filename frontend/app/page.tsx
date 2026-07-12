import ChatWindow from "@/components/ChatWindow";
import ThemeToggle from "@/components/ThemeToggle";

export default function Home() {
  return (
    <main className="mx-auto flex h-screen max-w-3xl flex-col p-4 sm:p-6">
      <header className="mb-4 flex items-start justify-between gap-4 px-1">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-md shadow-indigo-500/20">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="4" y="8" width="16" height="12" rx="2" />
              <path strokeLinecap="round" d="M12 8V4M9 4h6" />
              <circle cx="9" cy="14" r="1.2" fill="currentColor" stroke="none" />
              <circle cx="15" cy="14" r="1.2" fill="currentColor" stroke="none" />
            </svg>
          </div>
          <div>
            <h1 className="text-lg font-semibold leading-tight text-slate-900 dark:text-slate-50">
              Northwind Gadgets Support Agent
            </h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Policy questions via document RAG · order/data questions via text-to-SQL
            </p>
          </div>
        </div>
        <ThemeToggle />
      </header>

      <div className="flex-1 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <ChatWindow />
      </div>

      <p className="mt-3 text-center text-xs text-slate-400 dark:text-slate-600">
        Fictional demo data · current date treated as 15 June 2026
      </p>
    </main>
  );
}
