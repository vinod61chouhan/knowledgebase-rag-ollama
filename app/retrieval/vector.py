from app.db.database import pool
from app.ingestion.embeddings import embed_query

async def search_vector(question: str, tenant: str, owner: str, limit: int, document_id=None):
    vector = await embed_query(question)
    literal = "[" + ",".join(str(float(x)) for x in vector) + "]"
    async with pool().acquire() as conn:
        rows = await conn.fetch("""SELECT c.id,c.document_id,d.filename,c.page_number,c.content,
            1-(c.embedding <=> $1::vector) AS score FROM chunks c
            JOIN documents d ON d.id=c.document_id
            WHERE c.tenant_id=$2 AND c.owner_id=$3 AND d.status='ready'
              AND ($5::uuid IS NULL OR c.document_id=$5::uuid)
            ORDER BY c.embedding <=> $1::vector LIMIT $4""",
            literal, tenant, owner, limit, document_id)
    return [dict(r) for r in rows]
