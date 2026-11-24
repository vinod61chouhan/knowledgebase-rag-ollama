from app.core.config import settings
from app.retrieval.hybrid import search_hybrid
from app.retrieval.reranker import rerank
from app.services.query_rewriter import rewrite
from app.services.generator import generate

async def retrieve(question: str, tenant: str, owner: str, top_k: int, document_id=None):
    query = await rewrite(question) if settings.rewrite_enabled else question
    candidates = await search_hybrid(query, tenant, owner, max(top_k, settings.candidates), document_id)
    selected = await rerank(question, candidates, top_k) if settings.rerank_enabled else candidates[:top_k]
    return query, selected

async def ask(question: str, tenant: str, owner: str, top_k: int, document_id=None):
    query, rows = await retrieve(question, tenant, owner, top_k, document_id)
    answer = await generate(question, rows)
    return {"answer": answer, "rewritten_query": query,
            "citations": [{"source": i, "document_id": str(r["document_id"]),
                "chunk_id": r["id"], "filename": r["filename"], "page": r["page_number"]}
                for i, r in enumerate(rows, 1)]}
