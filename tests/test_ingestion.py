from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from medibot.ingestion import (
    collection_exists,
    collection_for_directory,
    collection_has_documents,
    heading_path_for_chunk,
    index_documents,
    pdf_text_chunks,
    section_title_for_chunk,
)


def test_section_title_uses_last_heading() -> None:
    chunk = SimpleNamespace(meta=SimpleNamespace(headings=["Clinical", "Protocols"]))

    assert section_title_for_chunk(chunk) == "Protocols"


def test_heading_path_preserves_hierarchy() -> None:
    chunk = SimpleNamespace(meta=SimpleNamespace(headings=["Clinical", "Protocols"]))

    assert heading_path_for_chunk(chunk) == ["Clinical", "Protocols"]


def test_section_title_falls_back_when_missing() -> None:
    assert (
        section_title_for_chunk(SimpleNamespace(meta=SimpleNamespace(headings=[])))
        == "Unknown"
    )


def test_collection_directory_must_be_known() -> None:
    assert collection_for_directory("billing").value == "billing"
    with pytest.raises(ValueError):
        collection_for_directory("unknown")


def test_pdf_text_chunks_extracts_text() -> None:
    chunks = pdf_text_chunks(Path("data/general/leave_policy.pdf"))

    assert chunks
    assert "Leave & Attendance Policy" in chunks[0]


def test_collection_exists_checks_configured_qdrant_collection(tmp_path) -> None:
    settings = SimpleNamespace(
        qdrant_path=tmp_path,
        qdrant_collection="medibot_documents",
        embedding_model="test-model",
    )
    client = MagicMock()
    client.collection_exists.return_value = True

    with patch("qdrant_client.QdrantClient", return_value=client):
        assert collection_exists(settings) is True

    client.collection_exists.assert_called_once_with("medibot_documents")
    client.close.assert_called_once_with()


def test_collection_has_documents_requires_non_empty_collection(tmp_path) -> None:
    settings = SimpleNamespace(
        qdrant_path=tmp_path,
        qdrant_collection="medibot_documents",
    )
    client = MagicMock()
    client.collection_exists.return_value = True
    client.count.return_value.count = 0

    with patch("qdrant_client.QdrantClient", return_value=client):
        assert collection_has_documents(settings) is False

    client.count.assert_called_once_with("medibot_documents", exact=True)
    client.close.assert_called_once_with()


def test_index_documents_does_not_replace_existing_collection(tmp_path) -> None:
    settings = SimpleNamespace(
        qdrant_path=tmp_path,
        qdrant_collection="medibot_documents",
    )
    client = MagicMock()
    client.collection_exists.return_value = True
    client.count.return_value.count = 1

    with patch("qdrant_client.QdrantClient", return_value=client):
        assert index_documents([], settings) == 0

    client.delete_collection.assert_not_called()
    client.close.assert_called_once_with()


def test_index_documents_can_rebuild_existing_collection(tmp_path) -> None:
    settings = SimpleNamespace(
        qdrant_path=tmp_path,
        qdrant_collection="medibot_documents",
        embedding_model="test-model",
    )
    client = MagicMock()
    client.collection_exists.return_value = True
    client.count.return_value.count = 1

    vector_store = MagicMock()
    with (
        patch("qdrant_client.QdrantClient", return_value=client),
        patch("langchain_huggingface.HuggingFaceEmbeddings"),
        patch("langchain_qdrant.FastEmbedSparse"),
        patch(
            "langchain_qdrant.QdrantVectorStore.construct_instance",
            return_value=vector_store,
        ),
    ):
        assert index_documents(["document"], settings, force_rebuild=True) == 1

    client.delete_collection.assert_called_once_with("medibot_documents")
