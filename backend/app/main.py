"""FastAPI application entrypoint.

All expensive, stateful objects (embedding model, FAISS index, SQLite file,
Azure client) are built once in the lifespan handler and stashed on
`app.state` -- request handlers only ever read them, never rebuild them.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agent.orchestrator import AgentOrchestrator
from app.agent.tools import ToolExecutor
from app.api.chat import router as chat_router
from app.config import get_settings
from app.llm.azure_client import AzureChatClient
from app.rag.retriever import DocumentRetriever
from app.sql.db import SCHEMA_DESCRIPTION, OrdersRepository, build_orders_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    logger.info("Building orders SQLite database from %s", settings.orders_csv_path)
    orders_db_path = settings.index_dir / "orders.db"
    build_orders_db(settings.orders_csv_path, orders_db_path)
    orders_repo = OrdersRepository(orders_db_path, row_limit=settings.sql_row_limit)

    logger.info("Loading document retriever (embedding model: %s)", settings.embedding_model_name)
    retriever = DocumentRetriever(settings.index_dir, settings.documents_dir, settings.embedding_model_name)
    retriever.load()

    tool_executor = ToolExecutor(retriever, orders_repo, settings)
    llm_client = AzureChatClient(settings)
    app.state.orchestrator = AgentOrchestrator(
        llm=llm_client,
        tool_executor=tool_executor,
        settings=settings,
        schema_description=SCHEMA_DESCRIPTION,
    )
    logger.info("Startup complete")
    yield


app = FastAPI(title="Northwind Gadgets Support Agent", lifespan=lifespan)

_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
