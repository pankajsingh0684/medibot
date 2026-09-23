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

### Required environment values

Before starting the app, create a real `.env` file from `.env.example` and set the required secrets and defaults.

```env
GROQ_API_KEY=your_groq_key_here
GROQ_MODEL=openai/gpt-oss-20b
QDRANT_PATH=qdrant_data
QDRANT_COLLECTION=medibot_documents
DATABASE_PATH=data/db/mediassist.db
JWT_SECRET_KEY=replace-with-a-long-random-secret
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
FRONTEND_ORIGIN=http://localhost:3000
DEMO_PASSWORD=change-this-demo-password
```

Important:

- `GROQ_API_KEY` is required for document-answer generation and must be set to a valid key from Groq.
- `JWT_SECRET_KEY` must be a long random secret for signing JWTs.
- `DEMO_PASSWORD` is the shared password for the development demo accounts below.
- The demo password is for local development only and should be changed in production or replaced with real authentication.

### Demo users

The app includes a small built-in demo set that all use the same `DEMO_PASSWORD` value:

| Username | Role |
| --- | --- |
| `dr.mehta` | doctor |
| `nurse.priya` | nurse |
| `billing.ravi` | billing_executive |
| `tech.anand` | technician |
| `admin.sys` | admin |

Example login flow:

```json
{
  "username": "dr.mehta",
  "password": "your-demo-password"
}
```

These users are intended for local testing and demonstration only.

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