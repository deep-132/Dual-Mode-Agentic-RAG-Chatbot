import ChatWindow from "@/components/ChatWindow";

export default function Home() {
  return (
    <main className="mx-auto flex h-screen max-w-3xl flex-col py-6">
      <header className="mb-4 px-4">
        <h1 className="text-xl font-semibold text-gray-900">Northwind Gadgets Support Agent</h1>
        <p className="text-sm text-gray-500">
          Dual-mode agent: policy questions via document RAG, order/data questions via text-to-SQL.
        </p>
      </header>
      <div className="flex-1 overflow-hidden rounded-xl border border-gray-200 bg-gray-50 shadow-sm">
        <ChatWindow />
      </div>
    </main>
  );
}
