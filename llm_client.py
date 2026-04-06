#!/usr/bin/env python3
"""
LLM Client - Abstracción unificada para proveedores LLM en Scrapelio Browser.

Proveedores soportados:
  - LM Studio  : servidor local OpenAI-compatible  (sin API key)
  - llmapi.ai  : gateway cloud gratuito/premium     (requiere API key)

API idéntica: LLMClient(config).chat(messages, max_tokens, temperature)
"""

import json
import logging
import requests
from dataclasses import dataclass, field
from typing import Iterator, List, Dict, Optional

from PySide6.QtCore import QSettings

logger = logging.getLogger(__name__)

# ─── Constantes ────────────────────────────────────────────────────────────────

PROVIDER_LOCAL = "local"          # LM Studio / Ollama / cualquier servidor local
PROVIDER_LLMAPI = "llmapi"        # llmapi.ai
PROVIDER_ANTHROPIC = "anthropic"  # API nativa de Anthropic

LLMAPI_BASE_URL = "https://api.llmapi.ai"
ANTHROPIC_BASE_URL = "https://api.anthropic.com"
ANTHROPIC_API_VERSION = "2023-06-01"

# Modelos de Anthropic disponibles para el usuario
ANTHROPIC_MODELS = [
    # Claude 4 — familia más reciente
    "claude-opus-4-5",
    "claude-sonnet-4-5",
    # Claude 3.7
    "claude-sonnet-3-7",
    # Claude 3.5
    "claude-sonnet-3-5",
    "claude-haiku-3-5",
    # Claude 3 — familia legacy
    "claude-opus-3",
    "claude-sonnet-3",
    "claude-haiku-3",
]

ANTHROPIC_DEFAULT_MODEL = "claude-sonnet-4-5"

# Modelos gratuitos disponibles en llmapi.ai (para mostrar en la UI)
LLMAPI_FREE_MODELS = [
    "zai/glm-4.5-flash",
    "gpt-4o-mini",
    "gemini-1.5-flash",
    "gemini-2.0-flash",
    "claude-haiku-4-5",
    "llama-3.3-70b-instruct",
    "mistral-small-latest",
    "deepseek-chat",
]


# ─── Configuración ──────────────────────────────────────────────────────────────

@dataclass
class LLMConfig:
    """Configuración de un proveedor LLM. Se serializa/deserializa con QSettings."""
    provider: str = PROVIDER_LOCAL
    local_url: str = "http://localhost:1234"
    llmapi_key: str = ""
    llmapi_model: str = "gpt-4o-mini"
    anthropic_key: str = ""
    anthropic_model: str = ANTHROPIC_DEFAULT_MODEL
    temperature: float = 0.7
    max_tokens: int = 4000

    # ── Persistencia ─────────────────────────────────────────────────────────

    def save(self, namespace: str = "LLMClient"):
        s = QSettings("Scrapelio", namespace)
        s.setValue("provider", self.provider)
        s.setValue("local_url", self.local_url)
        s.setValue("llmapi_key", self.llmapi_key)
        s.setValue("llmapi_model", self.llmapi_model)
        s.setValue("anthropic_key", self.anthropic_key)
        s.setValue("anthropic_model", self.anthropic_model)
        s.setValue("temperature", self.temperature)
        s.setValue("max_tokens", self.max_tokens)

    @classmethod
    def load(cls, namespace: str = "LLMClient") -> "LLMConfig":
        s = QSettings("Scrapelio", namespace)
        cfg = cls()
        cfg.provider = str(s.value("provider", PROVIDER_LOCAL))
        cfg.local_url = str(s.value("local_url", "http://localhost:1234"))
        cfg.llmapi_key = str(s.value("llmapi_key", ""))
        cfg.llmapi_model = str(s.value("llmapi_model", "gpt-4o-mini"))
        cfg.anthropic_key = str(s.value("anthropic_key", ""))
        cfg.anthropic_model = str(s.value("anthropic_model", ANTHROPIC_DEFAULT_MODEL))
        try:
            cfg.temperature = float(s.value("temperature", 0.7))
        except (TypeError, ValueError):
            cfg.temperature = 0.7
        try:
            cfg.max_tokens = int(s.value("max_tokens", 4000))
        except (TypeError, ValueError):
            cfg.max_tokens = 4000
        return cfg


# ─── Cliente ────────────────────────────────────────────────────────────────────

class LLMClient:
    """
    Cliente unificado. Expone:
      chat(messages, max_tokens?, temperature?) -> str   (contenido del mensaje)
      test() -> (ok: bool, info: str)
      list_models() -> [str]
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        # Session reutilizable para connection pooling (reduce latencia TCP)
        self._session = requests.Session()
        # Caché del modelo local detectado (evita llamadas GET repetidas)
        self._cached_model_id: Optional[str] = None

    # ── API pública ───────────────────────────────────────────────────────────

    def chat(
        self,
        messages: List[Dict],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Envía mensajes al LLM y devuelve el texto de la respuesta.
        Si max_tokens es None el servidor decide el límite (sin restricción desde el cliente).
        Lanza LLMError si algo falla.
        """
        temp = temperature if temperature is not None else self.config.temperature

        if self.config.provider == PROVIDER_ANTHROPIC:
            return self._chat_anthropic(messages, max_tokens, temp)
        if self.config.provider == PROVIDER_LLMAPI:
            return self._chat_llmapi(messages, max_tokens, temp)
        return self._chat_local(messages, max_tokens, temp)

    def chat_stream(
        self,
        messages: List[Dict],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Iterator[str]:
        """
        Genera la respuesta del LLM como un iterador de fragmentos de texto (SSE).
        Compatible con el formato OpenAI Server-Sent Events.
        """
        temp = temperature if temperature is not None else self.config.temperature

        if self.config.provider == PROVIDER_ANTHROPIC:
            yield from self._stream_anthropic(messages, max_tokens, temp)
            return

        payload: Dict = {
            "messages": messages,
            "temperature": temp,
            "stream": True,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        if self.config.provider == PROVIDER_LLMAPI:
            if not self.config.llmapi_key:
                raise LLMError("API key de llmapi.ai no configurada")
            url = f"{LLMAPI_BASE_URL}/v1/chat/completions"
            payload["model"] = self.config.llmapi_model
            headers = self.get_headers()
        else:
            url = f"{self.config.local_url.rstrip('/')}/v1/chat/completions"
            model_id = self._detect_local_model()
            if model_id:
                payload["model"] = model_id
            headers = self.get_headers()

        resp = self._session.post(url, json=payload, headers=headers,
                                  stream=True, timeout=180)
        if resp.status_code != 200:
            raise LLMError(f"HTTP {resp.status_code}: {resp.text[:200]}")

        for raw_line in resp.iter_lines():
            if not raw_line:
                continue
            line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
            if not line.startswith("data: "):
                continue
            data = line[6:].strip()
            if data == "[DONE]":
                break
            try:
                obj = json.loads(data)
                delta = obj["choices"][0]["delta"].get("content", "")
                if delta:
                    yield delta
            except (json.JSONDecodeError, KeyError, IndexError):
                continue

    def test(self) -> tuple:
        """Prueba la conexión. Devuelve (ok: bool, mensaje: str)."""
        try:
            if self.config.provider == PROVIDER_ANTHROPIC:
                return self._test_anthropic()
            if self.config.provider == PROVIDER_LLMAPI:
                return self._test_llmapi()
            return self._test_local()
        except Exception as e:
            return False, str(e)

    def list_models(self) -> List[str]:
        """Lista modelos disponibles (solo para el proveedor activo)."""
        try:
            if self.config.provider == PROVIDER_ANTHROPIC:
                return ANTHROPIC_MODELS
            if self.config.provider == PROVIDER_LLMAPI:
                return LLMAPI_FREE_MODELS
            return self._list_models_local()
        except Exception:
            return []

    def get_base_url(self) -> str:
        if self.config.provider == PROVIDER_ANTHROPIC:
            return ANTHROPIC_BASE_URL
        if self.config.provider == PROVIDER_LLMAPI:
            return LLMAPI_BASE_URL
        return self.config.local_url.rstrip("/")

    def get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.config.provider == PROVIDER_ANTHROPIC and self.config.anthropic_key:
            headers["x-api-key"] = self.config.anthropic_key
            headers["anthropic-version"] = ANTHROPIC_API_VERSION
        elif self.config.provider == PROVIDER_LLMAPI and self.config.llmapi_key:
            headers["Authorization"] = f"Bearer {self.config.llmapi_key}"
        return headers

    # ── Implementaciones locales ──────────────────────────────────────────────

    def _chat_local(self, messages, max_tokens, temperature) -> str:
        url = f"{self.config.local_url.rstrip('/')}/v1/chat/completions"
        model_id = self._detect_local_model()
        payload: Dict = {
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if model_id:
            payload["model"] = model_id

        resp = self._session.post(url, json=payload, headers=self.get_headers(), timeout=120)
        return self._parse_response(resp)

    def _test_local(self) -> tuple:
        url = f"{self.config.local_url.rstrip('/')}/v1/models"
        resp = self._session.get(url, timeout=8)
        if resp.status_code != 200:
            return False, f"HTTP {resp.status_code}"
        models = resp.json().get("data", [])
        if not models:
            return False, "Servidor responde pero sin modelos cargados"
        return True, f"Conectado — modelo: {models[0].get('id', '?')}"

    def _list_models_local(self) -> List[str]:
        url = f"{self.config.local_url.rstrip('/')}/v1/models"
        resp = self._session.get(url, timeout=8)
        if resp.status_code != 200:
            return []
        return [m.get("id", "") for m in resp.json().get("data", []) if m.get("id")]

    def _detect_local_model(self) -> str:
        """Devuelve el primer modelo disponible, usando caché para evitar GETs repetidos."""
        if self._cached_model_id is not None:
            return self._cached_model_id
        try:
            url = f"{self.config.local_url.rstrip('/')}/v1/models"
            resp = self._session.get(url, timeout=6)
            if resp.status_code == 200:
                models = resp.json().get("data", [])
                if models:
                    self._cached_model_id = models[0].get("id", "")
                    return self._cached_model_id
        except Exception:
            pass
        self._cached_model_id = ""
        return ""

    def detect_context_window(self) -> int:
        """Detecta ventana de contexto del modelo local; fallback seguro 4096."""
        if self.config.provider == PROVIDER_ANTHROPIC:
            return 200000  # Todos los modelos Claude tienen 200k ctx
        if self.config.provider == PROVIDER_LLMAPI:
            return 32000  # los modelos cloud tienen contexto amplio
        try:
            url = f"{self.config.local_url.rstrip('/')}/v1/models"
            resp = self._session.get(url, timeout=6)
            if resp.status_code != 200:
                return 4096
            models = resp.json().get("data", [])
            if not models:
                return 4096
            first = models[0] if isinstance(models[0], dict) else {}
            # Guardar el modelo en caché de paso
            if not self._cached_model_id and first.get("id"):
                self._cached_model_id = first["id"]
            for key in ("context_length", "n_ctx", "max_context_length", "num_ctx"):
                val = first.get(key)
                if isinstance(val, int) and val >= 1024:
                    return val
                if isinstance(val, str) and val.isdigit() and int(val) >= 1024:
                    return int(val)
        except Exception:
            pass
        return 4096

    # ── Implementaciones llmapi.ai ────────────────────────────────────────────

    def _chat_llmapi(self, messages, max_tokens, temperature) -> str:
        if not self.config.llmapi_key:
            raise LLMError("API key de llmapi.ai no configurada")
        url = f"{LLMAPI_BASE_URL}/v1/chat/completions"
        payload = {
            "model": self.config.llmapi_model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        resp = self._session.post(url, json=payload, headers=self.get_headers(), timeout=120)
        return self._parse_response(resp)

    def _test_llmapi(self) -> tuple:
        if not self.config.llmapi_key:
            return False, "API key vacía — introduce tu clave de llmapi.ai"
        resp = self._session.post(
            f"{LLMAPI_BASE_URL}/v1/chat/completions",
            json={
                "model": self.config.llmapi_model,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 10,
                "stream": False,
            },
            headers=self.get_headers(),
            timeout=20,
        )
        if resp.status_code == 200:
            return True, f"Conectado a llmapi.ai — modelo: {self.config.llmapi_model}"
        try:
            err = resp.json().get("error", {}).get("message", resp.text[:200])
        except Exception:
            err = resp.text[:200]
        return False, f"HTTP {resp.status_code}: {err}"

    # ── Implementaciones Anthropic ────────────────────────────────────────────

    def _build_anthropic_payload(
        self,
        messages: List[Dict],
        max_tokens: Optional[int],
        temperature: float,
        stream: bool = False,
    ) -> Dict:
        """
        Convierte el formato OpenAI de mensajes al formato nativo de Anthropic.
        - El mensaje system se extrae y va en el campo 'system' de top-level.
        - Los mensajes user/assistant van en 'messages'.
        """
        system_prompt = ""
        anthropic_messages = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                system_prompt = content
            elif role in ("user", "assistant"):
                anthropic_messages.append({"role": role, "content": content})

        payload: Dict = {
            "model": self.config.anthropic_model,
            "messages": anthropic_messages,
            "max_tokens": max_tokens if max_tokens is not None else self.config.max_tokens,
            "temperature": temperature,
            "stream": stream,
        }
        if system_prompt:
            payload["system"] = system_prompt

        return payload

    def _chat_anthropic(self, messages: List[Dict], max_tokens: Optional[int], temperature: float) -> str:
        """Llamada síncrona a la API de Anthropic."""
        if not self.config.anthropic_key:
            raise LLMError("API key de Anthropic no configurada")

        url = f"{ANTHROPIC_BASE_URL}/v1/messages"
        payload = self._build_anthropic_payload(messages, max_tokens, temperature, stream=False)

        resp = self._session.post(url, json=payload, headers=self.get_headers(), timeout=120)

        if resp.status_code != 200:
            detail = ""
            try:
                err = resp.json()
                detail = err.get("error", {}).get("message", resp.text[:400])
            except Exception:
                detail = resp.text[:400]
            raise LLMError(f"Anthropic API error {resp.status_code}: {detail}")

        data = resp.json()
        content_blocks = data.get("content", [])
        if not content_blocks:
            raise LLMError("Respuesta vacía de Anthropic")
        return "".join(block.get("text", "") for block in content_blocks if block.get("type") == "text")

    def _stream_anthropic(
        self,
        messages: List[Dict],
        max_tokens: Optional[int],
        temperature: float,
    ) -> Iterator[str]:
        """
        Streaming nativo SSE de Anthropic.
        Eventos relevantes:
          - content_block_delta → delta.type == "text_delta" → delta.text
          - message_stop        → fin de stream
        """
        if not self.config.anthropic_key:
            raise LLMError("API key de Anthropic no configurada")

        url = f"{ANTHROPIC_BASE_URL}/v1/messages"
        payload = self._build_anthropic_payload(messages, max_tokens, temperature, stream=True)

        resp = self._session.post(
            url, json=payload, headers=self.get_headers(),
            stream=True, timeout=180,
        )

        if resp.status_code != 200:
            detail = ""
            try:
                detail = resp.json().get("error", {}).get("message", resp.text[:200])
            except Exception:
                detail = resp.text[:200]
            raise LLMError(f"Anthropic stream error {resp.status_code}: {detail}")

        current_event = None
        for raw_line in resp.iter_lines():
            if not raw_line:
                continue
            line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line

            if line.startswith("event: "):
                current_event = line[7:].strip()
                continue

            if line.startswith("data: "):
                data_str = line[6:].strip()
                if data_str == "[DONE]" or current_event == "message_stop":
                    break
                if current_event != "content_block_delta":
                    continue
                try:
                    obj = json.loads(data_str)
                    delta = obj.get("delta", {})
                    if delta.get("type") == "text_delta":
                        text = delta.get("text", "")
                        if text:
                            yield text
                except (json.JSONDecodeError, KeyError):
                    continue

    def _test_anthropic(self) -> tuple:
        """Prueba la conexión con Anthropic enviando un mensaje mínimo."""
        if not self.config.anthropic_key:
            return False, "API key de Anthropic vacía — introduce tu clave sk-ant-..."
        try:
            url = f"{ANTHROPIC_BASE_URL}/v1/messages"
            payload = {
                "model": self.config.anthropic_model,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 10,
                "stream": False,
            }
            resp = self._session.post(
                url, json=payload, headers=self.get_headers(), timeout=20,
            )
            if resp.status_code == 200:
                return True, f"Conectado a Anthropic — modelo: {self.config.anthropic_model}"
            err = ""
            try:
                err = resp.json().get("error", {}).get("message", resp.text[:200])
            except Exception:
                err = resp.text[:200]
            return False, f"HTTP {resp.status_code}: {err}"
        except requests.exceptions.ConnectionError:
            return False, "Sin conexión a api.anthropic.com — verifica tu red"
        except requests.exceptions.Timeout:
            return False, "Timeout — la API de Anthropic no respondió en 20s"
        except Exception as e:
            return False, str(e)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_response(resp: requests.Response) -> str:
        if resp.status_code != 200:
            detail = ""
            try:
                detail = resp.json().get("error", {}).get("message", "")
            except Exception:
                detail = resp.text[:400]
            raise LLMError(f"Error del servidor: {resp.status_code}" + (f" — {detail}" if detail else ""))
        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            raise LLMError("Respuesta vacía del servidor")
        return choices[0]["message"]["content"]


class LLMError(Exception):
    """Error en la comunicación con el LLM."""
