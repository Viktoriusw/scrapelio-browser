#!/usr/bin/env python3
"""
AI Context Engine — Embeddings y cache vectorial para navegación aumentada.

Proporciona búsqueda semántica sobre el contenido de las pestañas abiertas
usando sentence-transformers (local) con ChromaDB como almacén vectorial
persistente.  Diseñado para degradar con gracia cuando no hay GPU o cuando
faltan dependencias pesadas.
"""

import hashlib
import logging
import re
import os
import time
from typing import Dict, List, Optional

import numpy as np
from PySide6.QtCore import QObject, QThread, Signal, QSettings

logger = logging.getLogger(__name__)

# ── Flags de disponibilidad ──────────────────────────────────────────────────

_SENTENCE_TRANSFORMERS_OK = False
_CHROMADB_OK = False

try:
    from sentence_transformers import SentenceTransformer
    _SENTENCE_TRANSFORMERS_OK = True
except ImportError:
    logger.warning("sentence-transformers no disponible; se usará fallback por keywords")

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    _CHROMADB_OK = True
except ImportError:
    logger.warning("chromadb no disponible; se usará almacén en memoria simple")


# ═════════════════════════════════════════════════════════════════════════════
# ContentChunker
# ═════════════════════════════════════════════════════════════════════════════

class ContentChunker:
    """Divide contenido de páginas en chunks óptimos para embeddings."""

    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50

    @classmethod
    def chunk_html(cls, html_text: str) -> List[str]:
        """Divide texto plano (ya limpio) en chunks con overlap.

        Args:
            html_text: Texto limpio extraído del HTML.

        Returns:
            Lista de strings de tamaño ≤ CHUNK_SIZE.
        """
        if not html_text or not html_text.strip():
            return []

        text = html_text.strip()
        chunks: List[str] = []
        start = 0
        while start < len(text):
            end = start + cls.CHUNK_SIZE
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk.strip())
            start += cls.CHUNK_SIZE - cls.CHUNK_OVERLAP
        return chunks

    @classmethod
    def chunk_by_headings(cls, html_text: str) -> List[str]:
        """Divide por encabezados (H1-H3) detectados como ``[H1]``, ``[H2]``, etc.

        Cada sección delimitada por un encabezado se devuelve como un chunk
        independiente.  Si una sección excede ``CHUNK_SIZE``, se subdivide
        con :meth:`chunk_html`.

        Args:
            html_text: Texto limpio con marcadores ``[H1]``, ``[H2]``, ``[H3]``.

        Returns:
            Lista de chunks.
        """
        if not html_text or not html_text.strip():
            return []

        heading_pattern = re.compile(r'\[H[1-3]\]')
        parts = heading_pattern.split(html_text)
        chunks: List[str] = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if len(part) <= cls.CHUNK_SIZE:
                chunks.append(part)
            else:
                chunks.extend(cls.chunk_html(part))
        return chunks


# ═════════════════════════════════════════════════════════════════════════════
# EmbeddingProvider
# ═════════════════════════════════════════════════════════════════════════════

class EmbeddingProvider:
    """Abstracción para generar embeddings locales con sentence-transformers.

    Usa ``all-MiniLM-L6-v2`` por defecto (rápido, 384 dims).
    Carga el modelo de forma perezosa para no bloquear el arranque.
    """

    DEFAULT_MODEL = "all-MiniLM-L6-v2"

    def __init__(self, model_name: Optional[str] = None):
        self._model_name = model_name or self.DEFAULT_MODEL
        self._model: Optional["SentenceTransformer"] = None
        self._available = _SENTENCE_TRANSFORMERS_OK

    @property
    def available(self) -> bool:
        return self._available

    def _ensure_model(self) -> None:
        """Lazy-load del modelo de embeddings."""
        if self._model is not None:
            return
        if not self._available:
            raise RuntimeError("sentence-transformers no está instalado")
        try:
            self._model = SentenceTransformer(self._model_name)
            logger.info("Modelo de embeddings '%s' cargado", self._model_name)
        except Exception as exc:
            self._available = False
            raise RuntimeError(f"No se pudo cargar el modelo: {exc}") from exc

    def encode(self, texts: List[str]) -> np.ndarray:
        """Codifica una lista de textos en vectores.

        Args:
            texts: Textos a codificar.

        Returns:
            ndarray de shape ``(len(texts), dim)``.
        """
        self._ensure_model()
        return self._model.encode(texts, show_progress_bar=False)  # type: ignore[union-attr]

    def encode_single(self, text: str) -> np.ndarray:
        """Codifica un solo texto.

        Args:
            text: Texto a codificar.

        Returns:
            ndarray de shape ``(dim,)``.
        """
        return self.encode([text])[0]


# ═════════════════════════════════════════════════════════════════════════════
# ContextVectorStore
# ═════════════════════════════════════════════════════════════════════════════

class ContextVectorStore:
    """Almacena embeddings del contenido de pestañas para búsqueda semántica.

    Usa ChromaDB en modo persistente cuando está disponible; de lo contrario
    mantiene un almacén en memoria con búsqueda brute-force por coseno.
    """

    COLLECTION_NAME = "scrapelio_tabs"

    def __init__(self, persist_dir: Optional[str] = None):
        self._persist_dir = persist_dir or os.path.join(
            os.path.expanduser("~"), ".scrapelio", "vector_store"
        )
        self._embedding_provider = EmbeddingProvider()
        self._use_chromadb = _CHROMADB_OK and self._embedding_provider.available
        self._collection = None
        self._client = None

        # Fallback en memoria
        self._mem_store: Dict[str, Dict] = {}

        if self._use_chromadb:
            self._init_chromadb()
        else:
            logger.info("Vector store en modo fallback (memoria)")

    def _init_chromadb(self) -> None:
        """Inicializa ChromaDB persistente."""
        try:
            os.makedirs(self._persist_dir, exist_ok=True)
            self._client = chromadb.Client(ChromaSettings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=self._persist_dir,
                anonymized_telemetry=False,
            ))
            self._collection = self._client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("ChromaDB inicializado en %s", self._persist_dir)
        except Exception as exc:
            logger.warning("ChromaDB no disponible, fallback a memoria: %s", exc)
            self._use_chromadb = False

    # ── API pública ──────────────────────────────────────────────────────────

    def add_tab_context(
        self,
        tab_id: str,
        url: str,
        title: str,
        content_chunks: List[str],
    ) -> None:
        """Indexa los chunks de una pestaña.

        Args:
            tab_id: Identificador único de la pestaña.
            url: URL de la pestaña.
            title: Título de la pestaña.
            content_chunks: Lista de fragmentos de texto.
        """
        if not content_chunks:
            return

        self.delete_tab(tab_id)

        if self._use_chromadb and self._collection is not None:
            try:
                ids = [f"{tab_id}_chunk_{i}" for i in range(len(content_chunks))]
                metadatas = [
                    {"tab_id": tab_id, "url": url, "title": title, "chunk_idx": i}
                    for i in range(len(content_chunks))
                ]
                self._collection.add(
                    documents=content_chunks,
                    ids=ids,
                    metadatas=metadatas,
                )
                return
            except Exception as exc:
                logger.warning("Error al indexar en ChromaDB: %s", exc)

        embeddings = None
        if self._embedding_provider.available:
            try:
                embeddings = self._embedding_provider.encode(content_chunks)
            except Exception:
                pass

        self._mem_store[tab_id] = {
            "url": url,
            "title": title,
            "chunks": content_chunks,
            "embeddings": embeddings,
        }

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Busca los chunks más relevantes para una query.

        Args:
            query: Texto de búsqueda.
            top_k: Número máximo de resultados.

        Returns:
            Lista de dicts con keys ``tab_id``, ``url``, ``title``,
            ``chunk``, ``score``.
        """
        if self._use_chromadb and self._collection is not None:
            try:
                results = self._collection.query(
                    query_texts=[query],
                    n_results=top_k,
                )
                output: List[Dict] = []
                if results and results["documents"]:
                    docs = results["documents"][0]
                    metas = results["metadatas"][0] if results["metadatas"] else [{}] * len(docs)
                    dists = results["distances"][0] if results.get("distances") else [0.0] * len(docs)
                    for doc, meta, dist in zip(docs, metas, dists):
                        output.append({
                            "tab_id": meta.get("tab_id", ""),
                            "url": meta.get("url", ""),
                            "title": meta.get("title", ""),
                            "chunk": doc,
                            "score": 1.0 - dist,
                        })
                return output
            except Exception as exc:
                logger.warning("Error en búsqueda ChromaDB: %s", exc)

        return self._search_memory(query, top_k)

    def _search_memory(self, query: str, top_k: int) -> List[Dict]:
        """Búsqueda fallback en memoria (coseno o keywords)."""
        query_emb = None
        if self._embedding_provider.available:
            try:
                query_emb = self._embedding_provider.encode_single(query)
            except Exception:
                pass

        results: List[Dict] = []
        for tab_id, data in self._mem_store.items():
            chunks = data["chunks"]
            embeddings = data.get("embeddings")

            for i, chunk in enumerate(chunks):
                if query_emb is not None and embeddings is not None:
                    chunk_emb = embeddings[i]
                    score = float(np.dot(query_emb, chunk_emb) / (
                        np.linalg.norm(query_emb) * np.linalg.norm(chunk_emb) + 1e-10
                    ))
                else:
                    score = self._keyword_score(query, chunk)

                results.append({
                    "tab_id": tab_id,
                    "url": data["url"],
                    "title": data["title"],
                    "chunk": chunk,
                    "score": score,
                })

        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:top_k]

    @staticmethod
    def _keyword_score(query: str, text: str) -> float:
        """Score simple basado en keywords cuando no hay embeddings."""
        query_words = set(query.lower().split())
        text_lower = text.lower()
        if not query_words:
            return 0.0
        matches = sum(1 for w in query_words if w in text_lower)
        return matches / len(query_words)

    def delete_tab(self, tab_id: str) -> None:
        """Elimina todos los chunks de una pestaña.

        Args:
            tab_id: Identificador de la pestaña a eliminar.
        """
        if self._use_chromadb and self._collection is not None:
            try:
                self._collection.delete(where={"tab_id": tab_id})
            except Exception as exc:
                logger.debug("Error al eliminar de ChromaDB: %s", exc)

        self._mem_store.pop(tab_id, None)

    def clear(self) -> None:
        """Elimina todo el contenido indexado."""
        if self._use_chromadb and self._client is not None:
            try:
                self._client.delete_collection(self.COLLECTION_NAME)
                self._collection = self._client.get_or_create_collection(
                    name=self.COLLECTION_NAME,
                    metadata={"hnsw:space": "cosine"},
                )
            except Exception as exc:
                logger.warning("Error al limpiar ChromaDB: %s", exc)

        self._mem_store.clear()

    @property
    def tab_count(self) -> int:
        """Número de pestañas indexadas."""
        if self._use_chromadb and self._collection is not None:
            try:
                count = self._collection.count()
                return count
            except Exception:
                pass
        return len(self._mem_store)


# ═════════════════════════════════════════════════════════════════════════════
# IndexWorker — indexación en segundo plano
# ═════════════════════════════════════════════════════════════════════════════

class IndexWorker(QThread):
    """Worker que indexa el contenido de una pestaña en segundo plano."""

    indexing_done = Signal(str)   # tab_id
    indexing_error = Signal(str)  # mensaje de error

    def __init__(
        self,
        store: ContextVectorStore,
        tab_id: str,
        url: str,
        title: str,
        html_content: str,
    ):
        super().__init__()
        self._store = store
        self._tab_id = tab_id
        self._url = url
        self._title = title
        self._html = html_content

    def run(self) -> None:
        try:
            from gentab_engine import ContentExtractor
            clean_text = ContentExtractor.extract_from_html(
                self._html, self._url, self._title,
            )
            chunks = ContentChunker.chunk_html(clean_text)
            if chunks:
                self._store.add_tab_context(
                    self._tab_id, self._url, self._title, chunks,
                )
            self.indexing_done.emit(self._tab_id)
        except Exception as exc:
            logger.error("Error indexando pestaña %s: %s", self._tab_id, exc)
            self.indexing_error.emit(str(exc))
