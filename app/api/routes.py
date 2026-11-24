from pathlib import Path
from uuid import uuid4, UUID
import hashlib
import os
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from app.core.config import settings
from app.db.database import pool
from app.api.schemas import QueryRequest, EvaluationRequest
from app.services.rag import ask, retrieve

router = APIRouter(prefix="/api/v1")

async def identity(x_api_key: str = Header(default=""), x_tenant_id: str = Header(default=""),
                   x_user_id: str = Header(default="")):
    # DEMO ONLY: caller-supplied identity is not real authentication.
    if x_api_key != settings.api_key or not x_tenant_id.strip() or not x_user_id.strip():
        raise HTTPException(401, "Invalid API key or missing identity headers")
    return x_tenant_id.strip(), x_user_id.strip()

@router.post("/documents", status_code=202)
async def upload(file: UploadFile = File(...), scope=Depends(identity)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".txt", ".md", ".docx"}:
        raise HTTPException(415, "Supported: PDF, DOCX, TXT, MD")
    contents = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(contents) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "File too large")
    document_id = uuid4()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    path = settings.upload_dir / f"{document_id}{suffix}"
    path.write_bytes(contents)
    tenant, owner = scope
    try:
        async with pool().acquire() as conn:
            async with conn.transaction():
                await conn.execute("""INSERT INTO documents
                    (id,tenant_id,owner_id,filename,sha256,file_path)
                    VALUES($1,$2,$3,$4,$5,$6)""", document_id, tenant, owner,
                    Path(file.filename or "document").name, hashlib.sha256(contents).hexdigest(), str(path))
                await conn.execute("INSERT INTO ingestion_jobs(document_id,version) VALUES($1,1)", document_id)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return {"document_id": str(document_id), "status": "queued"}

@router.get("/documents/{document_id}")
async def status(document_id: UUID, scope=Depends(identity)):
    async with pool().acquire() as conn:
        row = await conn.fetchrow("""SELECT id,filename,version,status,error,created_at,updated_at
            FROM documents WHERE id=$1 AND tenant_id=$2 AND owner_id=$3""", document_id, *scope)
    if not row:
        raise HTTPException(404, "Document not found")
    return dict(row)

@router.put("/documents/{document_id}", status_code=202)
async def replace(document_id: UUID, file: UploadFile = File(...), scope=Depends(identity)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".docx", ".txt", ".md"}:
        raise HTTPException(415, "Unsupported file type")
    contents = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(contents) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "File too large")
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    new_path = settings.upload_dir / f"{document_id}-{uuid4()}{suffix}"
    new_path.write_bytes(contents)
    try:
        async with pool().acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow("""UPDATE documents SET filename=$4,sha256=$5,file_path=$6,
                    version=version+1,status='queued',updated_at=now()
                    WHERE id=$1 AND tenant_id=$2 AND owner_id=$3 RETURNING version""",
                    document_id, *scope, Path(file.filename or "document").name,
                    hashlib.sha256(contents).hexdigest(), str(new_path))
                if not row:
                    raise HTTPException(404, "Document not found")
                await conn.execute("INSERT INTO ingestion_jobs(document_id,version) VALUES($1,$2)",
                                   document_id, row["version"])
    except Exception:
        new_path.unlink(missing_ok=True)
        raise
    return {"document_id": str(document_id), "version": row["version"], "status": "queued"}

@router.delete("/documents/{document_id}", status_code=204)
async def delete(document_id: UUID, scope=Depends(identity)):
    async with pool().acquire() as conn:
        result = await conn.execute("DELETE FROM documents WHERE id=$1 AND tenant_id=$2 AND owner_id=$3",
                                    document_id, *scope)
    if result == "DELETE 0":
        raise HTTPException(404, "Document not found")

@router.post("/search")
async def search(request: QueryRequest, scope=Depends(identity)):
    query, rows = await retrieve(request.question, *scope, request.top_k, request.document_id)
    return {"rewritten_query": query, "results": [{"chunk_id": r["id"],
        "document_id": str(r["document_id"]), "filename": r["filename"],
        "page": r["page_number"], "content": r["content"], "score": r.get("rrf_score")}
        for r in rows]}

@router.post("/ask")
async def ask_route(request: QueryRequest, scope=Depends(identity)):
    return await ask(request.question, *scope, request.top_k, request.document_id)

@router.post("/evaluate")
async def evaluate(request: EvaluationRequest, scope=Depends(identity)):
    from app.evaluation.metrics import evaluate_dataset
    return await evaluate_dataset(*scope, request.top_k)
