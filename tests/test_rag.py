from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from medibot.models import Role
from medibot.rag import (
    create_vector_store,
    execute_sql_question,
    is_sql_question,
)

DATABASE_PATH = Path("data/db/mediassist.db")


def test_sql_question_detection() -> None:
    assert is_sql_question("Show the latest claims by insurer")
    assert is_sql_question("How many maintenance tickets are open?")
    assert not is_sql_question("What is the infection control procedure?")


def test_billing_role_can_query_claims() -> None:
    result = execute_sql_question(
        "Show claims by status", Role.BILLING_EXECUTIVE, DATABASE_PATH
    )

    assert result.rows
    assert "FROM claims" in result.query


def test_nurse_cannot_query_claims() -> None:
    with pytest.raises(PermissionError):
        execute_sql_question("Show claims by status", Role.NURSE, DATABASE_PATH)


def test_create_vector_store_requires_ingested_collection(tmp_path) -> None:
    settings = SimpleNamespace(
        qdrant_path=tmp_path,
        qdrant_collection="medibot_documents",
    )
    client = MagicMock()
    client.collection_exists.return_value = False

    with patch("qdrant_client.QdrantClient", return_value=client):
        with pytest.raises(RuntimeError, match="Run document ingestion"):
            create_vector_store(settings)

    client.close.assert_called_once_with()
