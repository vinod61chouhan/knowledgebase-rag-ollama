from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from app.core.config import settings

async def rewrite(question: str):
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Rewrite as a concise standalone search query. Preserve meaning. Output only query."),
        ("human", "{question}")])
    llm = ChatOllama(model=settings.ollama_chat_model, base_url=settings.ollama_base_url, temperature=0)
    result = await (prompt | llm).ainvoke({"question": question})
    return str(result.content).strip() or question
