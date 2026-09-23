import os
from pathlib import Path
from typing import Any

from medibot.models import COLLECTION_ACCESS_ROLES, Collection

SUPPORTED_SUFFIXES = {".pdf", ".md"}
PDF_CHUNK_SIZE = 2000

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(variable, "1")


def section_title_for_chunk(chunk: Any) -> str:
    headings = heading_path_for_chunk(chunk)
    if headings:
        return headings[-1]
    return "Unknown"


def heading_path_for_chunk(chunk: Any) -> list[str]:
    headings = getattr(getattr(chunk, "meta", None), "headings", None)
    return [str(heading) for heading in headings or []]


def collection_for_directory(directory_name: str) -> Collection:
    try:
        return Collection(directory_name)
    except ValueError as error:
        raise ValueError(
            f"Unsupported document collection: {directory_name}"
        ) from error


def pdf_text_chunks(source_path: Path) -> list[str]:
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(str(source_path))
    chunks: list[str] = []
    try:
        for page in pdf:
            text_page = page.get_textpage()
            text = text_page.get_text_range().replace("\r", "").strip()
            text_page.close()
            page.close()
            if not text:
                continue
            chunks.extend(
                text[index : index + PDF_CHUNK_SIZE]
                for index in range(0, len(text), PDF_CHUNK_SIZE)
            )
    finally:
        pdf.close()
    return chunks


def load_documents(data_dir: Path, tokenizer_name: str) -> list[Any]:
    from docling.chunking import HierarchicalChunker
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.pipeline.simple_pipeline import SimplePipeline
    from langchain_core.documents import Document

    pdf_options = PdfPipelineOptions(do_ocr=False, force_backend_text=True)
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pdf_options,
                pipeline_cls=SimplePipeline,
            )
        }
    )
    chunker = HierarchicalChunker(always_emit_headings=False)
    documents: list[Document] = []

    for source_path in sorted(data_dir.rglob("*")):
        if (
            not source_path.is_file()
            or source_path.suffix.lower() not in SUPPORTED_SUFFIXES
        ):
            continue
        collection = collection_for_directory(source_path.parent.name)
        if source_path.suffix.lower() == ".pdf":
            for text in pdf_text_chunks(source_path):
                documents.append(
                    Document(
                        page_content=text,
                        metadata={
                            "source_document": source_path.name,
                            "section_title": "Unknown",
                            "headings": [],
                            "collection": collection.value,
                            "access_roles": [
                                role.value
                                for role in COLLECTION_ACCESS_ROLES[collection]
                            ],
                        },
                    )
                )
            continue
        result = converter.convert(source_path)
        for chunk in chunker.chunk(dl_doc=result.document):
            documents.append(
                Document(
                    page_content=chunker.contextualize(chunk=chunk),
                    metadata={
                        "source_document": source_path.name,
                        "section_title": section_title_for_chunk(chunk),
                        "headings": heading_path_for_chunk(chunk),
                        "collection": collection.value,
                        "access_roles": [
                            role.value for role in COLLECTION_ACCESS_ROLES[collection]
                        ],
                    },
                )
            )
    return documents


def collection_exists(settings: Any) -> bool:
    from qdrant_client import QdrantClient

    settings.qdrant_path.mkdir(parents=True, exist_ok=True)
    client = QdrantClient(path=str(settings.qdrant_path))
    try:
        return client.collection_exists(settings.qdrant_collection)
    finally:
        client.close()


def collection_has_documents(settings: Any) -> bool:
    from qdrant_client import QdrantClient

    settings.qdrant_path.mkdir(parents=True, exist_ok=True)
    client = QdrantClient(path=str(settings.qdrant_path))
    try:
        return client.collection_exists(settings.qdrant_collection) and (
            client.count(settings.qdrant_collection, exact=True).count > 0
        )
    finally:
        client.close()


def index_documents(
    documents: list[Any], settings: Any, force_rebuild: bool = False
) -> int:
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_qdrant import FastEmbedSparse, QdrantVectorStore, RetrievalMode
    from qdrant_client import QdrantClient

    settings.qdrant_path.mkdir(parents=True, exist_ok=True)
    client = QdrantClient(path=str(settings.qdrant_path))
    if client.collection_exists(settings.qdrant_collection):
        if (
            not force_rebuild
            and client.count(settings.qdrant_collection, exact=True).count > 0
        ):
            client.close()
            return 0
        client.delete_collection(settings.qdrant_collection)
    client.close()
    dense_embeddings = HuggingFaceEmbeddings(
        model_name=settings.embedding_model,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    sparse_embeddings = FastEmbedSparse(model_name="Qdrant/bm25", batch_size=32)
    vector_store = QdrantVectorStore.construct_instance(
        embedding=dense_embeddings,
        sparse_embedding=sparse_embeddings,
        collection_name=settings.qdrant_collection,
        retrieval_mode=RetrievalMode.HYBRID,
        client_options={"path": str(settings.qdrant_path)},
    )
    vector_store.add_documents(documents)
    return len(documents)
