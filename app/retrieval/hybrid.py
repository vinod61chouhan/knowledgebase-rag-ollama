import asyncio
from app.retrieval.vector import search_vector
from app.retrieval.keyword import search_keyword

def fuse(lists: list[list[dict]], k: int = 60):
    merged = {}
    for results in lists:
        for rank, item in enumerate(results, 1):
            key = item["id"]
            if key not in merged:
                merged[key] = dict(item, rrf_score=0.0)
            merged[key]["rrf_score"] += 1 / (k + rank)
    return sorted(merged.values(), key=lambda r: r["rrf_score"], reverse=True)

async def search_hybrid(question: str, tenant: str, owner: str, limit: int, document_id=None):
    vec, keyword = await asyncio.gather(
        search_vector(question, tenant, owner, limit, document_id),
        search_keyword(question, tenant, owner, limit, document_id))
    return fuse([vec, keyword])
