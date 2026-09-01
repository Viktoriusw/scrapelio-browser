#!/usr/bin/env python3
"""AI Chat infrastructure for the AI Live IDE plugin.

Provee:
    - HF_CODE_MODELS:     catálogo curado de modelos HF para programación
    - AIChatMessage:      dataclass que representa un turno de la conversación
    - AIChatWorker:       QThread con streaming SSE contra HF Inference Router
    - CodeBlockParser:    extrae cambios de archivos de la respuesta del modelo
    - ProjectContextBuilder: empaqueta el proyecto en un prompt acotado
    - AIFileChange:       cambio propuesto sobre un archivo del proyecto

Filosofía similar a Cursor / Aider / GitHub Copilot Chat: la IA responde con
bloques de código *etiquetados con la ruta del archivo*, y el plugin los
aplica selectivamente sobre el árbol del proyecto.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

from PySide6.QtCore import QObject, QThread, Signal

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────
# Catálogo de modelos disponibles en HuggingFace Inference Router
# ────────────────────────────────────────────────────────────────────────────
# Cada entrada contiene:
#   slug       → identificador OpenAI-compatible que se envía al router
#   label      → texto bonito para el selector de la UI
#   family     → grupo lógico (Coder, Reasoning, Generalist)
#   ctx        → ventana de contexto aproximada en tokens
#   notes      → descripción corta visible como tooltip

HF_CODE_MODELS: List[dict] = [
    # ── Familia Qwen Coder (Alibaba) — top tier para código ──────────────
    {
        "slug": "Qwen/Qwen2.5-Coder-32B-Instruct",
        "label": "Qwen2.5-Coder 32B  (calidad alta)",
        "family": "Coder",
        "ctx": 32000,
        "notes": "Top-tier en código. Más lento pero genera proyectos completos.",
    },
    {
        "slug": "Qwen/Qwen2.5-Coder-7B-Instruct",
        "label": "Qwen2.5-Coder 7B  (rápido)",
        "family": "Coder",
        "ctx": 32000,
        "notes": "Equilibrado: rápido y muy competente en código.",
    },
    {
        "slug": "Qwen/Qwen2.5-Coder-3B-Instruct",
        "label": "Qwen2.5-Coder 3B  (turbo)",
        "family": "Coder",
        "ctx": 32000,
        "notes": "Ultra rápido. Bueno para edits puntuales.",
    },
    # ── Meta Llama ──────────────────────────────────────────────────────
    {
        "slug": "meta-llama/Llama-3.3-70B-Instruct",
        "label": "Llama 3.3 70B  (razonamiento)",
        "family": "Reasoning",
        "ctx": 32000,
        "notes": "Excelente razonamiento general. Más lento por tamaño.",
    },
    {
        "slug": "meta-llama/Llama-3.1-8B-Instruct",
        "label": "Llama 3.1 8B",
        "family": "Generalist",
        "ctx": 32000,
        "notes": "Generalista ligero.",
    },
    # ── Mistral ─────────────────────────────────────────────────────────
    {
        "slug": "mistralai/Mixtral-8x7B-Instruct-v0.1",
        "label": "Mixtral 8x7B",
        "family": "Generalist",
        "ctx": 32000,
        "notes": "MoE generalista. Buena relación coste/calidad.",
    },
    {
        "slug": "mistralai/Mistral-7B-Instruct-v0.3",
        "label": "Mistral 7B v0.3",
        "family": "Generalist",
        "ctx": 32000,
        "notes": "Pequeño y rápido para iteraciones.",
    },
    # ── DeepSeek ────────────────────────────────────────────────────────
    {
        "slug": "deepseek-ai/DeepSeek-V2.5",
        "label": "DeepSeek V2.5",
        "family": "Coder",
        "ctx": 32000,
        "notes": "Buen rendimiento en código y matemáticas.",
    },
    # ── Microsoft Phi ───────────────────────────────────────────────────
    {
        "slug": "microsoft/Phi-3.5-mini-instruct",
        "label": "Phi-3.5 mini",
        "family": "Generalist",
        "ctx": 32000,
        "notes": "Modelo pequeño optimizado para tareas instructivas.",
    },
    {
        "slug": "microsoft/Phi-4-mini-instruct",
        "label": "Phi-4 mini",
        "family": "Generalist",
        "ctx": 32000,
        "notes": "Última generación mini de Microsoft.",
    },
    # ── Google Gemma ────────────────────────────────────────────────────
    {
        "slug": "google/gemma-2-27b-it",
        "label": "Gemma 2 27B",
        "family": "Generalist",
        "ctx": 32000,
        "notes": "Generalista de Google. Buen balance.",
    },
    {
        "slug": "google/gemma-2-9b-it",
        "label": "Gemma 2 9B",
        "family": "Generalist",
        "ctx": 32000,
        "notes": "Versión ligera de Gemma 2.",
    },
]


HF_DEFAULT_MODEL_SLUG = "Qwen/Qwen2.5-Coder-7B-Instruct"

# Endpoint OpenAI-compatible del router serverless de HuggingFace
HF_ROUTER_URL = "https://router.huggingface.co/v1/chat/completions"

# Salida del chat: HF Router suele aceptar 4k–8k+ según modelo; 4k trunca
# sitios multi-archivo. Subir mejora comportamiento tipo Cursor.
HF_CHAT_MAX_TOKENS = 8192

# Límites de seguridad para evitar prompts gigantescos
MAX_CONTEXT_BYTES = 1_000_000        # ≈ 1 MB de texto enviado por proyecto
MAX_FILES = 200                       # nº máximo de archivos del proyecto
MAX_FILE_BYTES = 80_000              # tamaño máximo por archivo individual
MAX_HISTORY_MESSAGES = 30            # nº turnos en el historial conversacional

# Carpetas/archivos a ignorar al construir contexto de proyecto
DEFAULT_IGNORE_DIRS = {
    "__pycache__", ".git", ".hg", ".svn",
    "node_modules", "bower_components",
    ".venv", "venv", "env", ".env", "site-packages",
    "dist", "build", ".next", ".nuxt", ".cache",
    ".parcel-cache", ".vite", ".turbo",
    ".idea", ".vscode", ".gradle",
    "target", "coverage", "__snapshots__",
    ".mypy_cache", ".pytest_cache", ".tox",
}
DEFAULT_IGNORE_EXTENSIONS = {
    ".pyc", ".pyo", ".pyd",
    ".class", ".jar", ".war",
    ".exe", ".dll", ".so", ".dylib",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp", ".tiff",
    ".mp3", ".mp4", ".mov", ".avi", ".webm", ".wav", ".flac",
    ".zip", ".tar", ".gz", ".7z", ".rar",
    ".pdf", ".docx", ".xlsx", ".pptx",
    ".lock", ".log", ".bin", ".dat", ".db", ".sqlite",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
}


# ────────────────────────────────────────────────────────────────────────────
# Estructuras de datos
# ────────────────────────────────────────────────────────────────────────────

@dataclass
class AIChatMessage:
    """Representa un único mensaje de la conversación (estilo OpenAI)."""

    role: str               # "system" | "user" | "assistant"
    content: str

    def to_api_dict(self) -> dict:
        return {"role": self.role, "content": self.content}


@dataclass
class AIFileChange:
    """Una propuesta de la IA para crear o modificar un archivo."""

    path: str                # ruta relativa al proyecto (o absoluta)
    language: str            # "python", "javascript", etc.
    new_content: str         # contenido completo propuesto
    is_new: bool = False     # True si el archivo no existe todavía
    old_content: Optional[str] = None  # contenido actual si existe
    applied: bool = False    # marcado cuando se ha escrito a disco

    def absolute_path(self, project_root: Path) -> Path:
        p = Path(self.path)
        if p.is_absolute():
            return p
        return project_root / p


# ────────────────────────────────────────────────────────────────────────────
# AIChatWorker — streaming SSE contra HF Inference Router
# ────────────────────────────────────────────────────────────────────────────

class AIChatWorker(QThread):
    """Hilo que envía una conversación a Hugging Face y emite chunks."""

    chunk_received = Signal(str)         # delta del stream
    finished_ok = Signal(str)            # respuesta completa al terminar
    finished_error = Signal(str)         # mensaje de error
    started_request = Signal(str)        # debug: modelo + nº mensajes

    def __init__(
        self,
        api_token: str,
        model: str,
        messages: List[AIChatMessage],
        max_tokens: int = HF_CHAT_MAX_TOKENS,
        temperature: float = 0.2,
        timeout: int = 180,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._token = api_token
        self._model = model or HF_DEFAULT_MODEL_SLUG
        self._messages = list(messages)
        self._max_tokens = max_tokens
        self._temperature = max(0.01, float(temperature))  # HF no acepta 0
        self._timeout = timeout
        self._stop_requested = False

    def request_stop(self):
        self._stop_requested = True

    def run(self) -> None:
        try:
            import requests
        except ImportError:
            self.finished_error.emit("La librería 'requests' no está instalada.")
            return
        if not self._token:
            self.finished_error.emit(
                "Falta el token de Hugging Face. Configúralo en el panel "
                "de Chat IA del navegador (proveedor 'huggingface') o en "
                "la variable de entorno HUGGINGFACE_TOKEN."
            )
            return
        payload = {
            "model": self._model,
            "messages": [m.to_api_dict() for m in self._messages],
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
            "stream": True,
        }
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }

        self.started_request.emit(
            f"Modelo {self._model} · {len(self._messages)} mensajes"
        )

        full_response_parts: List[str] = []
        try:
            with requests.post(
                HF_ROUTER_URL,
                json=payload,
                headers=headers,
                stream=True,
                timeout=self._timeout,
            ) as resp:
                if resp.status_code != 200:
                    body = resp.text[:500].replace("\n", " ")
                    self.finished_error.emit(
                        f"HTTP {resp.status_code} desde Hugging Face: {body}"
                    )
                    return
                for raw in resp.iter_lines(decode_unicode=False):
                    if self._stop_requested:
                        break
                    if not raw:
                        continue
                    try:
                        line = raw.decode("utf-8")
                    except UnicodeDecodeError:
                        continue
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                        delta = (
                            obj.get("choices", [{}])[0]
                            .get("delta", {})
                            .get("content", "")
                        )
                        if delta:
                            full_response_parts.append(delta)
                            self.chunk_received.emit(delta)
                    except (json.JSONDecodeError, IndexError, AttributeError):
                        # Algunos servidores emiten líneas heartbeat sin JSON
                        continue
        except requests.exceptions.Timeout:
            self.finished_error.emit(
                f"Timeout — Hugging Face no respondió en {self._timeout}s."
            )
            return
        except requests.exceptions.ConnectionError as exc:
            self.finished_error.emit(f"Sin conexión a Hugging Face: {exc}")
            return
        except Exception as exc:  # noqa: BLE001
            self.finished_error.emit(f"Error en streaming: {exc}")
            return
        if self._stop_requested:
            self.finished_error.emit("Generación interrumpida por el usuario.")
            return
        self.finished_ok.emit("".join(full_response_parts))


# ────────────────────────────────────────────────────────────────────────────
# CodeBlockParser — extrae propuestas de cambios de la respuesta
# ────────────────────────────────────────────────────────────────────────────

class CodeBlockParser:
    """Parsea respuestas de IA y extrae bloques de código *con ruta de archivo*.

    Formatos soportados (en orden de preferencia):
        1)  ```language:path/to/file.ext
            <code>
            ```
        2)  ```language path/to/file.ext
            <code>
            ```
        3)  Línea previa al bloque indica la ruta:
            (línea) ### path/to/file.ext       o
            (línea) // File: path/to/file.ext  o
            (línea) # File: path/to/file.ext   o
            (línea) **path/to/file.ext**       o
            ```language
            <code>
            ```
    """

    _FENCE_RE = re.compile(
        r"```(?P<lang>[a-zA-Z0-9_+#\-]*)"   # lenguaje opcional
        r"[ \t]*"
        r"(?P<header>[^\n]*)\n"             # resto de la cabecera (puede tener path)
        r"(?P<body>.*?)"
        r"```",
        re.DOTALL,
    )

    # Rutas con extensión o ficheros típicos sin extensión (Dockerfile, Makefile…)
    _PATH_TOKEN = (
        r"(?P<path>(?:[A-Za-z0-9_./\\-]+(?:\.[A-Za-z0-9]+)?"
        r"|(?:[A-Za-z0-9_./\\-]+/)*[Dd]ockerfile"
        r"|(?:[A-Za-z0-9_./\\-]+/)*[Mm]akefile"
        r"|(?:[A-Za-z0-9_./\\-]+/)*[Gg]emfile"
        r"|(?:[A-Za-z0-9_./\\-]+/)*[Rr]akefile))\b"
    )

    _PATH_FROM_HEADER_RE = re.compile(
        r"(?:^|[\s,:;|])" + _PATH_TOKEN
    )

    _PREFIX_PATH_PATTERNS = [
        re.compile(
            r"^\s*#{1,6}\s+(?:File\s*[:=]\s*)?" + _PATH_TOKEN + r"\s*$"
        ),
        re.compile(
            r"^\s*(?://|#)\s*(?:File\s*[:=]\s*)?" + _PATH_TOKEN + r"\s*$"
        ),
        re.compile(r"^\s*\*\*" + _PATH_TOKEN + r"\*\*\s*$"),
        re.compile(r"^\s*`" + _PATH_TOKEN + r"`\s*$"),
        re.compile(
            r"^\s*File\s*[:=]\s*`?" + _PATH_TOKEN + r"`?\s*$",
            re.IGNORECASE,
        ),
        re.compile(
            r"^\s*Archivo\s*[:=]\s*`?" + _PATH_TOKEN + r"`?\s*$",
            re.IGNORECASE,
        ),
    ]

    @classmethod
    def extract_file_changes(cls, response: str) -> List[Tuple[str, str, str]]:
        """Devuelve [(path, language, content), ...] en orden de aparición."""
        if not response:
            return []
        results: List[Tuple[str, str, str]] = []

        # Construimos un mapa "posición → línea anterior no vacía" para detectar
        # rutas indicadas justo antes del fence.
        lines = response.split("\n")
        line_offsets: List[int] = []
        cursor = 0
        for ln in lines:
            line_offsets.append(cursor)
            cursor += len(ln) + 1  # +1 por el \n

        for m in cls._FENCE_RE.finditer(response):
            lang = (m.group("lang") or "").strip().lower()
            header = (m.group("header") or "").strip()
            body = m.group("body") or ""
            # Detectar ruta en la cabecera del fence
            path = cls._extract_path_from_header(lang, header)
            if not path:
                # Buscar en la línea inmediatamente anterior al fence
                fence_start = m.start()
                # Localizar índice de la línea de apertura
                line_idx = 0
                for i in range(len(line_offsets) - 1, -1, -1):
                    if line_offsets[i] <= fence_start:
                        line_idx = i
                        break
                # Mirar hasta 3 líneas hacia atrás (saltando vacías)
                for back in range(1, 4):
                    prev_idx = line_idx - back
                    if prev_idx < 0:
                        break
                    prev_line = lines[prev_idx].strip()
                    if not prev_line:
                        continue
                    path = cls._extract_path_from_prefix(prev_line)
                    if path:
                        break
                    # primera línea no vacía sin match → ya no es un encabezado
                    break
            if not path:
                continue  # bloque sin ruta — ignorar
            results.append((path, lang or cls._infer_lang_from_path(path), body.rstrip() + "\n"))
        return results

    @classmethod
    def _extract_path_from_header(cls, lang: str, header: str) -> str:
        """Detecta ruta dentro del propio fence header: ```py:src/main.py o ```py src/main.py"""
        if not header:
            return ""
        # Caso 1: el lang ya incluye ":path" tipo  ```python:foo/bar.py
        # (el regex separa lang del resto, así que aquí header empieza tras el lang).
        # Buscar en el header un token con extensión
        m = cls._PATH_FROM_HEADER_RE.search(header)
        if m:
            return m.group("path").strip(",:; |")
        # Caso especial: lang contiene ":path"
        if ":" in lang:
            _real_lang, _, p = lang.partition(":")
            if "." in p:
                return p.strip()
        return ""

    @classmethod
    def _extract_path_from_prefix(cls, text: str) -> str:
        for pat in cls._PREFIX_PATH_PATTERNS:
            m = pat.match(text)
            if m:
                return m.group("path").strip()
        return ""

    @staticmethod
    def _infer_lang_from_path(path: str) -> str:
        ext = Path(path).suffix.lower().lstrip(".")
        mapping = {
            "py": "python", "js": "javascript", "ts": "typescript",
            "jsx": "javascript", "tsx": "typescript",
            "html": "html", "htm": "html", "css": "css", "scss": "scss",
            "json": "json", "yml": "yaml", "yaml": "yaml",
            "md": "markdown", "sh": "shell", "bash": "shell",
            "go": "go", "rs": "rust", "java": "java",
            "c": "c", "cpp": "cpp", "cs": "csharp", "rb": "ruby",
            "php": "php", "kt": "kotlin", "swift": "swift", "sql": "sql",
        }
        return mapping.get(ext, "plaintext")


# ────────────────────────────────────────────────────────────────────────────
# ProjectContextBuilder — empaqueta el proyecto en un único bloque de texto
# ────────────────────────────────────────────────────────────────────────────

class ProjectContextBuilder:
    """Recorre el árbol del proyecto y construye un prompt acotado."""

    def __init__(
        self,
        project_root: Path,
        max_bytes: int = MAX_CONTEXT_BYTES,
        max_files: int = MAX_FILES,
        max_file_bytes: int = MAX_FILE_BYTES,
        ignore_dirs: Optional[set] = None,
        ignore_extensions: Optional[set] = None,
    ):
        self.project_root = Path(project_root)
        self.max_bytes = max_bytes
        self.max_files = max_files
        self.max_file_bytes = max_file_bytes
        self.ignore_dirs = ignore_dirs or DEFAULT_IGNORE_DIRS
        self.ignore_extensions = ignore_extensions or DEFAULT_IGNORE_EXTENSIONS

    def iter_files(self) -> Iterator[Path]:
        """Itera por todos los ficheros incluibles del proyecto."""
        root = self.project_root
        for base, dirs, files in os.walk(root):
            # filtrar carpetas in-place para no recurrir en ignoradas
            dirs[:] = [d for d in dirs if not self._is_ignored_dir(d)]
            for fname in files:
                p = Path(base) / fname
                if self._is_ignored_file(p):
                    continue
                yield p

    def _is_ignored_dir(self, name: str) -> bool:
        return name in self.ignore_dirs or name.startswith(".") and name not in {".env.example"}

    def _is_ignored_file(self, p: Path) -> bool:
        if p.suffix.lower() in self.ignore_extensions:
            return True
        try:
            if p.stat().st_size > self.max_file_bytes:
                return True
        except OSError:
            return True
        return False

    def build_summary_tree(self, limit: int = 200) -> str:
        """Devuelve una representación del árbol relativa al root."""
        lines: List[str] = []
        count = 0
        for f in sorted(self.iter_files()):
            try:
                rel = f.relative_to(self.project_root)
            except ValueError:
                continue
            lines.append(str(rel).replace(os.sep, "/"))
            count += 1
            if count >= limit:
                lines.append(f"… ({count}+ archivos)")
                break
        return "\n".join(lines)

    def build_context(
        self,
        focus_paths: Optional[List[Path]] = None,
    ) -> Tuple[str, dict]:
        """Construye el bloque de contexto.

        Args:
            focus_paths: lista opcional de ficheros a INCLUIR PRIORITARIAMENTE.

        Returns:
            (texto del contexto, dict con estadísticas {files, bytes, truncated}).
        """
        included: List[Tuple[Path, str]] = []
        total_bytes = 0
        truncated = False

        # 1) Recolectar focus paths primero
        already: set = set()
        if focus_paths:
            for p in focus_paths:
                if not p.exists() or not p.is_file():
                    continue
                txt = self._safe_read(p)
                if not txt:
                    continue
                if total_bytes + len(txt) > self.max_bytes:
                    truncated = True
                    break
                included.append((p, txt))
                already.add(p.resolve())
                total_bytes += len(txt)
                if len(included) >= self.max_files:
                    truncated = True
                    break
        # 2) Recolectar el resto del proyecto
        if not truncated:
            for p in sorted(self.iter_files()):
                if p.resolve() in already:
                    continue
                if len(included) >= self.max_files:
                    truncated = True
                    break
                txt = self._safe_read(p)
                if not txt:
                    continue
                if total_bytes + len(txt) > self.max_bytes:
                    truncated = True
                    break
                included.append((p, txt))
                total_bytes += len(txt)
        # 3) Renderizar
        tree = self.build_summary_tree()
        parts: List[str] = []
        parts.append("=== PROJECT TREE ===")
        parts.append(tree)
        parts.append("")
        parts.append("=== PROJECT FILES ===")
        for p, txt in included:
            try:
                rel = p.relative_to(self.project_root).as_posix()
            except ValueError:
                rel = str(p)
            parts.append(f"--- FILE: {rel} ---")
            parts.append(txt.rstrip())
            parts.append("")
        if truncated:
            parts.append("[NOTA: el contexto fue truncado por límites de tamaño.]")
        text = "\n".join(parts)
        stats = {
            "files": len(included),
            "bytes": total_bytes,
            "truncated": truncated,
        }
        return text, stats

    @staticmethod
    def _safe_read(p: Path) -> str:
        try:
            return p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            return ""


# ────────────────────────────────────────────────────────────────────────────
# Prompts de sistema
# ────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT_ASSISTANT = """You are an expert software engineering assistant integrated into Scrapelio Browser's AI Live IDE.

GOAL: help the user understand, debug, generate and refactor code in their project.

GUIDELINES:
- Respond in the user's language (Spanish/English/etc.) but emit code as is.
- Be concise. Prefer code over prose when the user asks for a change.
- When you propose changes to files, use this EXACT format (one block per file):

  ```<language>:<relative/path/to/file.ext>
  <full file content here — never use placeholders like "..." or "rest of code">
  ```

- Always provide the COMPLETE final content of each file you modify. Do not stop mid-file:
  finish every closing tag, brace, and string.
- If the user asks for multiple files or a small site, output ALL files in separate
  fenced blocks with distinct paths. Never reply with "the rest is analogous" or omit files.
- If a file already exists, output the full new version. Never use diff syntax only.
- If you need to create new files, use relative paths that fit the PROJECT TREE in context.
- For shell commands or installation steps, use a ```bash block (no file path required in the header).
- When discussing code without proposing changes, you may use unlabeled code blocks.
- Never invent file paths that are not in the project tree unless the user explicitly
  asked you to create new files.

QUALITY: write idiomatic, production-quality code with proper error handling,
typing where the language supports it, and clear naming.
"""


def build_system_prompt(extra_context: str = "") -> str:
    prompt = SYSTEM_PROMPT_ASSISTANT
    if extra_context:
        prompt += "\n\n=== ADDITIONAL CONTEXT ===\n" + extra_context
    return prompt
