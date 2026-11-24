import asyncpg
from contextlib import asynccontextmanager
from app.core.config import settings

_pool = None

async def connect():
    global _pool
    _pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=10)

async def disconnect():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None

def pool():
    if _pool is None:
        raise RuntimeError("Database not connected")
    return _pool

async def init_db():
    # Model dimension is set at first initialization; changing it requires reindexing/migration.
    if settings.embed_dimensions != 768:
        raise RuntimeError("Starter schema uses vector(768); migrate schema before changing EMBED_DIMENSIONS")
    sql = """
    CREATE EXTENSION IF NOT EXISTS vector;
    CREATE TABLE IF NOT EXISTS documents (
      id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, owner_id TEXT NOT NULL,
      filename TEXT NOT NULL, sha256 TEXT NOT NULL, file_path TEXT NOT NULL,
      version INTEGER NOT NULL DEFAULT 1,
      status TEXT NOT NULL DEFAULT 'queued', error TEXT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    CREATE INDEX IF NOT EXISTS documents_tenant_owner ON documents(tenant_id,owner_id);
    CREATE TABLE IF NOT EXISTS chunks (
      id BIGSERIAL PRIMARY KEY, document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
      tenant_id TEXT NOT NULL, owner_id TEXT NOT NULL,
      chunk_index INTEGER NOT NULL, content TEXT NOT NULL,
      page_number INTEGER, metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
      embedding vector(768) NOT NULL,
      UNIQUE(document_id,chunk_index)
    );
    CREATE INDEX IF NOT EXISTS chunks_scope ON chunks(tenant_id,owner_id);
    CREATE INDEX IF NOT EXISTS chunks_vector ON chunks USING hnsw(embedding vector_cosine_ops);
    CREATE TABLE IF NOT EXISTS ingestion_jobs (
      id BIGSERIAL PRIMARY KEY, document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
      version INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'queued',
      attempts INTEGER NOT NULL DEFAULT 0, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), error TEXT
    );
    CREATE INDEX IF NOT EXISTS jobs_queue ON ingestion_jobs(status,id);
    """
    async with pool().acquire() as conn:
        await conn.execute(sql)

@asynccontextmanager
async def lifespan_db():
    await connect()
    try:
        await init_db()
        yield
    finally:
        await disconnect()
