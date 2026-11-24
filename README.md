# KnowledgeBase AI — LangChain + Ollama + uv + local PostgreSQL

**No Docker. No OpenAI API key. No Redis required.** The exact requested `app/` module structure is preserved.

## Prerequisites (Windows)

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/).
2. Install [Ollama](https://ollama.com/download) and run `ollama pull qwen2.5:7b` and `ollama pull nomic-embed-text`.
3. Install PostgreSQL locally, plus the **matching pgvector extension** for your PostgreSQL major version. On Windows, follow pgvector's Windows build/install instructions if no compatible package is available. In psql as a privileged role:
   ```sql
   CREATE DATABASE knowledgebase;
   ```
   Connect to that database, then:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
4. For scanned PDFs install [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) and ensure `tesseract.exe` is on PATH, or set `OCR_ENABLED=false`.

## Setup

```powershell
cd knowledgebase-rag
Copy-Item .env.example .env
# Edit DATABASE_URL and API_KEY in .env
uv sync
```

To run Ollama locally, launch its Windows application; verify with `ollama list`.

**Terminal 1 — API:**

```powershell
uv run uvicorn app.main:app --reload
```

**Terminal 2 — ingestion worker:**

```powershell
uv run python -m app.workers.tasks
```

**Terminal 3 — tests:**

```powershell
uv run pytest -q
```

Open http://127.0.0.1:8000/docs and use **Authorize** only if your own Swagger customization provides it; otherwise add headers to requests manually. All `/api/v1/*` routes require:

- `X-API-Key: change-this-local-dev-key` (change in `.env`)
- `X-Tenant-ID: demo`
- `X-User-ID: alice`

Example using PowerShell's `curl.exe`:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/documents -H "X-API-Key: change-this-local-dev-key" -H "X-Tenant-ID: demo" -H "X-User-ID: alice" -F "file=@sample.pdf"
```

Copy the returned `document_id`. Poll status:

```powershell
curl.exe "http://127.0.0.1:8000/api/v1/documents/YOUR_DOCUMENT_ID" -H "X-API-Key: change-this-local-dev-key" -H "X-Tenant-ID: demo" -H "X-User-ID: alice"
```

Once status is `ready`, ask:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/ask -H "Content-Type: application/json" -H "X-API-Key: change-this-local-dev-key" -H "X-Tenant-ID: demo" -H "X-User-ID: alice" -d '{"question":"Summarize the document","top_k":5}'
```

On Windows PowerShell, escaping JSON in curl can be awkward; use `Invoke-RestMethod` or Swagger's Try it out as alternatives.

## Architecture

```text
app/
  main.py
  api/routes.py,schemas.py
  core/config.py,logging.py
  db/database.py
  ingestion/extractors.py,chunker.py,embeddings.py,pipeline.py
  retrieval/vector.py,keyword.py,hybrid.py,reranker.py
  services/rag.py,generator.py,query_rewriter.py
  evaluation/metrics.py,dataset.json
  workers/celery_app.py,tasks.py
```

### Ingestion flow

Upload → PostgreSQL job → worker → PyMuPDF / DOCX / TXT → optional Tesseract OCR → LangChain recursive splitting → Ollama embeddings → pgvector → ready status.

### Question flow

Question → optional Ollama rewriting → pgvector similarity + tenant-scoped BM25 → RRF → optional cross-encoder → Ollama answer → citations.

### Configuration and caveats

- `REWRITE_ENABLED=true` enables LLM query rewriting.
- `RERANK_ENABLED=true` enables cross-encoder reranking; first use downloads a model.
- `nomic-embed-text` returns 768 dimensions. Do not switch embedding models without a database migration and full reindex.
- The first Ollama request may take time while the model loads.
- Uploaded files live on local disk; PostgreSQL stores paths and chunk embeddings.
- Updates are versioned and published atomically; the previous ready chunks are hidden while a replacement is processing. Deletion cascades to chunks and jobs, but local file cleanup is not yet automated.
- BM25 is a real rank-bm25 implementation, but currently loads all authorized chunks into memory per query; use a persistent keyword index for large collections.
- `/evaluate` computes document-level Recall@K and MRR. Edit `app/evaluation/dataset.json` with real uploaded UUIDs. Human-rated answer correctness/faithfulness is not implemented.
- This project uses an API key plus **caller-supplied** tenant/user headers. This is a development-only access-control demonstration, **not secure multi-tenant authentication**. Use server-derived identities (OIDC/JWT), TLS, authorization checks, quotas and auditing before exposing it publicly.
- The PostgreSQL job queue is durable for queued jobs, but a process killed while a job is `running` leaves it stuck until manually reset. Add leases, retries, dead-letter handling and startup recovery for production.
- For robust document parsing, add file signature validation, antivirus scanning, OCR resource limits, table-specific tests, and per-document observability.
- Database schema is initialized at startup for learning. Production deployments should use migrations (Alembic) and backups.

## API endpoints

- `GET /health`
- `POST /api/v1/documents` (multipart upload)
- `GET /api/v1/documents/{id}`
- `PUT /api/v1/documents/{id}` (replace document)
- `DELETE /api/v1/documents/{id}`
- `POST /api/v1/search` (inspect retrieval)
- `POST /api/v1/ask` (RAG answer)
- `POST /api/v1/evaluate` (retrieval metrics)

## Tests

`uv run pytest -q` checks chunking, BM25 ranking, RRF and retrieval metrics. End-to-end tests need a running PostgreSQL instance, pgvector and Ollama.
