from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import Any

from app.modules.llm_chat.domain.exceptions import ChatRuntimeUnavailable
from app.modules.llm_chat.domain.rag_index import EmbeddingFingerprintSpec


class FastEmbedEmbeddingClient:
    def __init__(
        self,
        *,
        model_name: str,
        dimension: int = 384,
        cache_dir: str | None = None,
        model: Any | None = None,
        model_revision: str = "registry-default",
        pooling_strategy: str = "mean",
        normalization: bool = True,
        document_prefix: str = "",
        query_prefix: str = "",
    ) -> None:
        self.model_name = model_name
        self.dimension = dimension
        self.model_revision = model_revision
        self.pooling_strategy = pooling_strategy
        self.normalization = normalization
        self.document_prefix = document_prefix
        self.query_prefix = query_prefix
        if model is None:
            from fastembed import TextEmbedding

            model = TextEmbedding(model_name=model_name, cache_dir=cache_dir)
        self._model = model

    @classmethod
    def fingerprint_spec(
        cls,
        *,
        model_name: str,
        dimension: int,
        model_revision: str = "registry-default",
        pooling_strategy: str = "mean",
        normalization: bool = True,
        document_prefix: str = "",
        query_prefix: str = "",
    ) -> EmbeddingFingerprintSpec:
        try:
            library_version = version("fastembed")
        except PackageNotFoundError:
            # This path is useful for dry-run/tests outside the backend image. A
            # real ingestion cannot construct the model without the dependency.
            library_version = "not-installed"
        return EmbeddingFingerprintSpec(
            provider="fastembed",
            model=model_name,
            model_revision=model_revision,
            library_name="fastembed",
            library_version=library_version,
            pooling_strategy=pooling_strategy,
            vector_dimension=dimension,
            normalization=normalization,
            document_prefix=document_prefix,
            query_prefix=query_prefix,
        )

    def index_fingerprint_spec(self) -> EmbeddingFingerprintSpec:
        return self.fingerprint_spec(
            model_name=self.model_name,
            dimension=self.dimension,
            model_revision=self.model_revision,
            pooling_strategy=self.pooling_strategy,
            normalization=self.normalization,
            document_prefix=self.document_prefix,
            query_prefix=self.query_prefix,
        )

    def embed_query(self, text: str) -> list[float]:
        try:
            vector = next(iter(self._model.query_embed([f"{self.query_prefix}{text}"])))
        except Exception as exc:
            raise ChatRuntimeUnavailable("Query embedding failed") from exc
        converted = [float(value) for value in vector]
        if len(converted) != self.dimension:
            raise ChatRuntimeUnavailable("Query embedding dimension mismatch")
        return converted

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        try:
            vectors = [
                [float(value) for value in vector]
                for vector in self._model.passage_embed(
                    [f"{self.document_prefix}{text}" for text in texts]
                )
            ]
        except Exception as exc:
            raise ChatRuntimeUnavailable("Document embedding failed") from exc
        if len(vectors) != len(texts) or any(
            len(vector) != self.dimension for vector in vectors
        ):
            raise ChatRuntimeUnavailable("Document embedding dimension mismatch")
        return vectors
