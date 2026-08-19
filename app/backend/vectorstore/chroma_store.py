"""ChromaDB wrapper — adapted from Healthcare.ipynb Week 3
(TracedClinicalVectorStore + add_documents_with_tracing/search_with_tracing,
cells 48-52). Embedding generation is injected via a callable rather than
reaching for a module-global OpenAI client, so this class has no LLM
dependency of its own.
"""
from collections.abc import Callable
from typing import Any

import chromadb

EmbedFn = Callable[[str], list[float]]


class ChromaStore:
    """Persistent ChromaDB client with cosine HNSW collections and naive
    word-based chunking (500 words / 50 overlap, matching Week 3)."""

    def __init__(self, persist_directory: str):
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collections: dict[str, chromadb.Collection] = {}

    def get_or_create_collection(self, name: str) -> chromadb.Collection:
        if name not in self.collections:
            self.collections[name] = self.client.get_or_create_collection(
                name=name, metadata={"hnsw:space": "cosine"}
            )
        return self.collections[name]

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
        words = text.split()
        if not words:
            return [text]
        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)
        return chunks if chunks else [text]

    def add_document(self, collection_name: str, *, doc_id: str, text: str,
                      metadata: dict[str, Any], embed_fn: EmbedFn) -> int:
        """Chunks `text`, embeds each chunk via `embed_fn`, and upserts into
        the collection. Returns the number of chunks added."""
        collection = self.get_or_create_collection(collection_name)
        chunks = self.chunk_text(text)
        if not chunks or not text.strip():
            return 0

        ids, embeddings, documents, metadatas = [], [], [], []
        for i, chunk in enumerate(chunks):
            ids.append(f"{doc_id}_chunk_{i}")
            embeddings.append(embed_fn(chunk))
            documents.append(chunk)
            metadatas.append({**metadata, "chunk_index": i})

        collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
        return len(ids)

    def query(self, collection_name: str, *, query_text: str, embed_fn: EmbedFn,
              n_results: int = 5, where: dict[str, Any] | None = None) -> dict[str, Any]:
        collection = self.get_or_create_collection(collection_name)
        query_embedding = embed_fn(query_text)
        return collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
