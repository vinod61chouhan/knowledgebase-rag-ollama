import asyncio
import json
from uuid import UUID
from app.db.database import pool
from app.ingestion.extractors import extract
from app.ingestion.chunker import split_pages
from app.ingestion.embeddings import embed_documents
from app.core.config import settings
from app.core.logging import logger

async def ingest(document_id: str, version: int):
    async with pool().acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM documents WHERE id=$1", UUID(document_id))
    if not row or row["version"] != version:
        return
    # CPU/blocking document parsing runs off the event loop.
    pages = await asyncio.to_thread(extract, row["file_path"])
    docs = split_pages(pages, row["filename"])
    vectors = await embed_documents([d.page_content for d in docs]) if docs else []
    if any(len(v) != settings.embed_dimensions for v in vectors):
        raise ValueError("Embedding dimension mismatch: check Ollama model and database schema")
    async with pool().acquire() as conn:
        async with conn.transaction():
            current = await conn.fetchrow("SELECT version FROM documents WHERE id=$1 FOR UPDATE", UUID(document_id))
            if not current or current["version"] != version:
                return  # A newer version won the race; never publish stale chunks.
            await conn.execute("DELETE FROM chunks WHERE document_id=$1", UUID(document_id))
            for index, (doc, vector) in enumerate(zip(docs, vectors)):
                literal = "[" + ",".join(str(float(x)) for x in vector) + "]"
                await conn.execute("""INSERT INTO chunks(document_id,tenant_id,owner_id,chunk_index,
                    content,page_number,metadata,embedding)
                    VALUES($1,$2,$3,$4,$5,$6,$7::jsonb,$8::vector)""",
                    UUID(document_id), row["tenant_id"], row["owner_id"], index,
                    doc.page_content, doc.metadata.get("page"), json.dumps(doc.metadata), literal)
            await conn.execute("UPDATE documents SET status='ready',error=NULL,updated_at=now() WHERE id=$1", UUID(document_id))
    logger.info("ingested", document_id=document_id, version=version, chunks=len(docs))
