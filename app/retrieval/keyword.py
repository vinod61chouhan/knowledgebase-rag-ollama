import re
from rank_bm25 import BM25Okapi
from app.db.database import pool

def tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())

def bm25_rank(question: str, rows: list[dict], limit: int) -> list[dict]:
    if not rows:
        return []
    tokens = [tokenize(r["content"]) for r in rows]
    if not any(tokens):
        return []
    model = BM25Okapi(tokens)
    scores = model.get_scores(tokenize(question))
    return [dict(rows[i], score=float(scores[i])) for i in sorted(range(len(rows)),
        key=lambda i: scores[i], reverse=True)[:limit] if scores[i] > 0]

async def search_keyword(question: str, tenant: str, owner: str, limit: int, document_id=None):
    # Tenant-scoped corpus; simple baseline, not suitable for millions of chunks.
    async with pool().acquire() as conn:
        rows = await conn.fetch("""SELECT c.id,c.document_id,d.filename,c.page_number,c.content
            FROM chunks c JOIN documents d ON d.id=c.document_id
            WHERE c.tenant_id=$1 AND c.owner_id=$2 AND d.status='ready'
              AND ($3::uuid IS NULL OR c.document_id=$3::uuid)""", tenant, owner, document_id)
    return bm25_rank(question, [dict(r) for r in rows], limit)
