from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.db.database import connect, disconnect, init_db, pool
from app.core.logging import configure_logging
from app.api.routes import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    await connect()
    await init_db()
    try:
        yield
    finally:
        await disconnect()

app = FastAPI(title="KnowledgeBase AI - Local Ollama RAG", lifespan=lifespan)
app.include_router(router)

@app.get("/health")
async def health():
    async with pool().acquire() as conn:
        await conn.fetchval("SELECT 1")
    return {"status": "ok", "database": "connected"}
