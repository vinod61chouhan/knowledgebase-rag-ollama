from functools import lru_cache
from langchain_ollama import OllamaEmbeddings
from app.core.config import settings

@lru_cache
def get_embeddings():
    return OllamaEmbeddings(model=settings.ollama_embed_model, base_url=settings.ollama_base_url)

async def embed_documents(texts: list[str]):
    return await get_embeddings().aembed_documents(texts)

async def embed_query(text: str):
    return await get_embeddings().aembed_query(text)
