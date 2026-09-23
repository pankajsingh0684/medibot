# MediBot

MediBot is a role-aware healthcare assistant with a FastAPI backend and a Next.js/React client. The client is intentionally thin: authentication, RBAC, retrieval, SQL access, and model calls belong to the API.

## Current implementation

- Typed role and collection access mappings
- JWT token creation and validation
- Argon2 password hashing
- Login, health, collections, and protected chat endpoints
- Read-only SQL statement validator for `claims` and `maintenance_tickets`
- Docling/HybridChunker ingestion path with required chunk metadata
- Dense and sparse Qdrant indexing with role metadata filters
- Cross-encoder reranking and grounded Groq document answers
- Initial Next.js/React login and chat interface

Authorized analytics questions execute read-only queries against the confirmed SQLite tables. Document answers require one indexing run and a configured Groq API key.

## Backend setup

Requires Python 3.12 and UV.

```powershell
uv sync
Copy-Item .env.example .env
uv run pytest
uv run ruff check .
uv run python scripts/ingest_documents.py
uv run uvicorn medibot.main:app --reload
```

Set a real `JWT_SECRET_KEY` and `GROQ_API_KEY` in `.env` before using model-backed features. The default demo password is development-only and should be replaced.

## Frontend setup

Requires Node.js and npm.

```powershell
cd frontend
Copy-Item .env.example .env.local
npm install
npm run dev
```

The local API runs at `http://localhost:8000` and the Next.js client at `http://localhost:3000`.

## Data and Qdrant sequencing

The supplied documents and SQLite database are preserved as source data. Local embedded Qdrant must be opened by ingestion and the API sequentially, never concurrently. Production deployments should use Qdrant Server or Qdrant Cloud.