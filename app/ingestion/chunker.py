from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.config import settings

def split_pages(pages: list[dict], filename: str) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""])
    documents = [Document(page_content=p["text"], metadata={"page": p["page"], "filename": filename})
                 for p in pages if p["text"].strip()]
    return splitter.split_documents(documents)
