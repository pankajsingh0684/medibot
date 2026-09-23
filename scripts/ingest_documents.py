import argparse
from pathlib import Path

from medibot.config import get_settings
from medibot.ingestion import (
    collection_has_documents,
    index_documents,
    load_documents,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare MediBot source documents.")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Recreate the collection and refresh document metadata.",
    )
    args = parser.parse_args()
    settings = get_settings()
    if collection_has_documents(settings) and not args.rebuild:
        print(
            f"Collection {settings.qdrant_collection} already exists; "
            "skipping document ingestion."
        )
        return
    documents = load_documents(args.data_dir, settings.embedding_model)
    count = index_documents(documents, settings, force_rebuild=args.rebuild)
    print(f"Indexed {count} chunks in collection {settings.qdrant_collection}.")


if __name__ == "__main__":
    main()
