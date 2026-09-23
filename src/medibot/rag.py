import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from medibot.config import Settings
from medibot.models import ChatResponse, Collection, Role, Source, TokenData
from medibot.sql import SQLValidationError, validate_read_only_sql

SQL_ROLES = {Role.BILLING_EXECUTIVE, Role.ADMIN}
DOCUMENT_CANDIDATE_COUNT = 10
DOCUMENT_RESULT_COUNT = 3


@dataclass(frozen=True)
class SQLAnswer:
    query: str
    rows: list[dict[str, object]]


def is_sql_question(question: str) -> bool:
    terms = {
        "claim",
        "claims",
        "ticket",
        "tickets",
        "maintenance",
        "approved",
        "insurer",
    }
    return bool(terms.intersection(question.lower().split()))


def build_sql_question(question: str) -> str:
    lowered = question.lower()
    if "ticket" in lowered or "maintenance" in lowered:
        return (
            "SELECT status, COUNT(*) AS ticket_count "
            "FROM maintenance_tickets GROUP BY status"
        )
    if "insurer" in lowered:
        return (
            "SELECT insurer, COUNT(*) AS claim_count, "
            "SUM(claimed_amount) AS total_claimed FROM claims GROUP BY insurer"
        )
    if "approved" in lowered:
        return (
            "SELECT status, COUNT(*) AS claim_count, "
            "SUM(approved_amount) AS total_approved FROM claims GROUP BY status"
        )
    return (
        "SELECT status, COUNT(*) AS claim_count, "
        "SUM(claimed_amount) AS total_claimed FROM claims GROUP BY status"
    )


def execute_sql_question(question: str, role: Role, database_path: Path) -> SQLAnswer:
    if role not in SQL_ROLES:
        raise PermissionError(
            "SQL analytics requires billing executive or admin access."
        )
    query = validate_read_only_sql(build_sql_question(question))
    with sqlite3.connect(f"file:{database_path}?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        rows = [dict(row) for row in connection.execute(query).fetchall()]
    return SQLAnswer(query=query, rows=rows)


def format_sql_answer(result: SQLAnswer) -> str:
    if not result.rows:
        return "No matching records were found."
    lines = [
        " | ".join(f"{key}: {value}" for key, value in row.items())
        for row in result.rows
    ]
    return "\n".join(lines)


def build_role_filter(role: Role) -> Any:
    from qdrant_client import models

    return models.Filter(
        must=[
            models.FieldCondition(
                key="metadata.access_roles",
                match=models.MatchValue(value=role.value),
            )
        ]
    )


def create_vector_store(settings: Settings) -> Any:
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_qdrant import FastEmbedSparse, QdrantVectorStore, RetrievalMode
    from qdrant_client import QdrantClient

    settings.qdrant_path.mkdir(parents=True, exist_ok=True)
    client = QdrantClient(path=str(settings.qdrant_path))
    if not client.collection_exists(settings.qdrant_collection):
        client.close()
        raise RuntimeError(
            f"Qdrant collection '{settings.qdrant_collection}' is missing. "
            "Run document ingestion before asking document questions."
        )
    dense_embeddings = HuggingFaceEmbeddings(
        model_name=settings.embedding_model,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    sparse_embeddings = FastEmbedSparse(model_name="Qdrant/bm25", batch_size=32)
    return QdrantVectorStore(
        client=client,
        collection_name=settings.qdrant_collection,
        embedding=dense_embeddings,
        sparse_embedding=sparse_embeddings,
        retrieval_mode=RetrievalMode.HYBRID,
    )


def retrieve_documents(question: str, role: Role, settings: Settings) -> list[Any]:
    vector_store = create_vector_store(settings)
    return vector_store.similarity_search(
        question,
        k=DOCUMENT_CANDIDATE_COUNT,
        filter=build_role_filter(role),
    )


def rerank_documents(
    question: str, documents: list[Any], settings: Settings
) -> list[Any]:
    from sentence_transformers import CrossEncoder

    if not documents:
        return []
    reranker = CrossEncoder(settings.reranker_model)
    scores = reranker.predict(
        [(question, document.page_content) for document in documents]
    )
    ranked = sorted(
        zip(scores, documents, strict=True),
        key=lambda item: float(item[0]),
        reverse=True,
    )
    return [document for _, document in ranked[:DOCUMENT_RESULT_COUNT]]


def generate_document_answer(
    question: str, documents: list[Any], settings: Settings
) -> str:
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is required for document answers.")
    from langchain_groq import ChatGroq

    context_parts = []
    for document in documents:
        headings = document.metadata.get("headings", [])
        heading_path = " > ".join(headings) or document.metadata.get(
            "section_title", "Unknown"
        )
        context_parts.append(
            f"Source: {document.metadata.get('source_document', 'Unknown')}\n"
            f"Heading path: {heading_path}\n"
            f"{document.page_content}"
        )
    context = "\n\n".join(context_parts)
    prompt = (
        "You are MediBot, an internal healthcare knowledge assistant.\n"
        "Answer only using the supplied context. If the answer is not present, "
        "say that the information is not available. Never invent facts.\n"
        "Return a well-structured Markdown answer. Preserve the relevant "
        "Heading path from the context by using Markdown headings or a "
        "clearly labeled section heading. Do not omit useful parent or child "
        "headings. Use Markdown tables when the context contains tabular data.\n\n"
        f"Context:\n{context}\n\nQuestion: {question}"
    )
    response = ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0,
    ).invoke(prompt)
    answer = str(response.content)
    heading_paths = []
    for document in documents:
        path = " / ".join(document.metadata.get("headings", []))
        if path and path not in heading_paths:
            heading_paths.append(path)
    if not heading_paths:
        return answer
    sections = "\n".join(f"- {path}" for path in heading_paths)
    return f"## Referenced sections\n\n{sections}\n\n{answer}"


def document_sources(documents: list[Any]) -> list[Source]:
    return [
        Source(
            source_document=document.metadata["source_document"],
            section_title=document.metadata["section_title"],
            collection=Collection(document.metadata["collection"]),
            headings=document.metadata.get("headings", []),
        )
        for document in documents
    ]


def answer_question(question: str, user: TokenData, settings: Settings) -> ChatResponse:
    if is_sql_question(question):
        try:
            result = execute_sql_question(question, user.role, settings.database_path)
        except PermissionError:
            raise
        except (OSError, sqlite3.Error, SQLValidationError) as error:
            raise RuntimeError(
                "Unable to execute the authorized analytics query."
            ) from error
        return ChatResponse(answer=format_sql_answer(result))

    candidates = retrieve_documents(question, user.role, settings)
    documents = rerank_documents(question, candidates, settings)
    if not documents:
        return ChatResponse(
            answer="The information is not available in your authorized documents.",
            sources=[],
        )
    return ChatResponse(
        answer=generate_document_answer(question, documents, settings),
        sources=document_sources(documents),
    )
