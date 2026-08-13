from __future__ import annotations

from typing import Protocol

from app.modules.llm_chat.domain.entities import KnowledgeChunk


class DocumentEmbeddingClient(Protocol):
    model_name: str
    dimension: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...


class IngestionVectorStore(Protocol):
    def ids_for_document(self, source_path: str) -> set[str]: ...

    def upsert(
        self, chunks: list[KnowledgeChunk], embeddings: list[list[float]]
    ) -> None: ...

    def delete(self, ids: set[str]) -> None: ...
    def document_paths(self) -> set[str]: ...
    def delete_document(self, source_path: str) -> int: ...
    def count(self) -> int: ...
