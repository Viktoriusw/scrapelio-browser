#!/usr/bin/env python3
"""
GenTab Engine - Motor de Pestañas Generativas para Scrapelio Browser

Inspirado en Google Disco GenTabs: extrae contexto de todas las pestañas abiertas,
lo envía a un LLM y genera aplicaciones web interactivas personalizadas.
"""

import json
import time
import hashlib
import requests
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from bs4 import BeautifulSoup

from PySide6.QtCore import QObject, Signal, QThread, QSettings

logger = logging.getLogger(__name__)


class GenTabStatus(Enum):
    PENDING = "pending"
    EXTRACTING = "extracting"
    GENERATING = "generating"
    READY = "ready"
    ERROR = "error"


@dataclass
class TabContext:
    """Contexto extraído de una pestaña individual."""
    index: int
    url: str
    title: str
    content: str
    content_length: int
    domain: str
    extracted_at: str = ""

    def __post_init__(self):
        if not self.extracted_at:
            self.extracted_at = datetime.now().isoformat()


@dataclass
class GenTabResult:
    """Resultado de una GenTab generada."""
    id: str
    title: str
    html: str
    prompt: str
    source_tabs: List[Dict[str, str]]
    created_at: str
    status: GenTabStatus = GenTabStatus.READY
    generation_time: float = 0.0
    model_used: str = ""
    token_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['status'] = self.status.value
        return result


class ContentExtractor:
    """Extrae y limpia contenido de páginas web."""

    MAX_CONTENT_PER_TAB = 4000
    MAX_TOTAL_CONTEXT = 24000

    @staticmethod
    def extract_from_html(html: str, url: str, title: str) -> str:
        try:
            soup = BeautifulSoup(html, 'lxml')
        except Exception:
            soup = BeautifulSoup(html, 'html.parser')

        for tag in soup(['script', 'style', 'nav', 'footer', 'aside',
                         'iframe', 'noscript', 'svg', 'form', 'input',
                         'button', 'select', 'textarea']):
            tag.decompose()

        headings = []
        for h in soup.find_all(['h1', 'h2', 'h3']):
            text = h.get_text(strip=True)
            if text:
                level = h.name
                headings.append(f"[{level.upper()}] {text}")

        links = []
        for a in soup.find_all('a', href=True):
            link_text = a.get_text(strip=True)
            if link_text and len(link_text) > 3:
                links.append(f"{link_text}: {a['href']}")

        images = []
        for img in soup.find_all('img', alt=True):
            alt = img.get('alt', '').strip()
            if alt and len(alt) > 3:
                images.append(alt)

        main_content = soup.find('main') or soup.find('article') or soup.find('body')
        text = main_content.get_text(separator='\n', strip=True) if main_content else ""

        lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 5]
        clean_text = '\n'.join(lines)

        sections = [f"TITLE: {title}", f"URL: {url}"]
        if headings:
            sections.append("STRUCTURE:\n" + '\n'.join(headings[:15]))
        sections.append(f"CONTENT:\n{clean_text[:ContentExtractor.MAX_CONTENT_PER_TAB]}")
        if images:
            sections.append("IMAGES: " + ', '.join(images[:10]))
        if links:
            sections.append("KEY LINKS:\n" + '\n'.join(links[:10]))

        return '\n\n'.join(sections)

    @staticmethod
    def get_domain(url: str) -> str:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc or url
        except Exception:
            return url


class GenTabWorker(QThread):
    """Worker thread para generar GenTabs sin bloquear la UI."""
    progress = Signal(str)
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, server_url: str, prompt: str, tab_contexts: List[TabContext],
                 temperature: float = 0.7, max_tokens: int = 4000):
        super().__init__()
        self.server_url = server_url
        self.prompt = prompt
        self.tab_contexts = tab_contexts
        self.temperature = temperature
        self.max_tokens = max_tokens

    def run(self):
        try:
            self.progress.emit("Construyendo contexto multi-tab...")
            context_text = self._build_context()
            self.progress.emit(f"Contexto preparado: {len(context_text)} caracteres de {len(self.tab_contexts)} pestañas")

            self.progress.emit("Enviando a IA para generar aplicación...")
            start_time = time.time()

            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(context_text)

            payload = {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stream": False
            }

            response = requests.post(
                f"{self.server_url}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=120
            )

            generation_time = time.time() - start_time

            if response.status_code != 200:
                self.error.emit(f"Error del servidor: {response.status_code}")
                return

            data = response.json()
            if "choices" not in data or not data["choices"]:
                self.error.emit("Respuesta vacía del servidor")
                return

            raw_content = data["choices"][0]["message"]["content"]
            html = self._extract_html(raw_content)

            if not html:
                self.error.emit("La IA no generó HTML válido")
                return

            html = self._inject_source_links(html)
            self.progress.emit("GenTab generada exitosamente")

            gen_id = hashlib.md5(
                f"{self.prompt}{time.time()}".encode()
            ).hexdigest()[:12]

            result = GenTabResult(
                id=gen_id,
                title=self._generate_title(raw_content),
                html=html,
                prompt=self.prompt,
                source_tabs=[{"url": tc.url, "title": tc.title, "domain": tc.domain}
                             for tc in self.tab_contexts],
                created_at=datetime.now().isoformat(),
                generation_time=round(generation_time, 2),
                model_used=data.get("model", "unknown"),
                token_count=data.get("usage", {}).get("total_tokens", 0)
            )

            self.finished.emit(result)

        except requests.exceptions.ConnectionError:
            self.error.emit("No se pudo conectar al servidor LLM. Verifica que LM Studio esté ejecutándose.")
        except requests.exceptions.Timeout:
            self.error.emit("Timeout: el servidor tardó demasiado en responder.")
        except Exception as e:
            self.error.emit(f"Error inesperado: {str(e)}")

    def _build_context(self) -> str:
        sections = []
        total = 0
        for tc in self.tab_contexts:
            if total >= ContentExtractor.MAX_TOTAL_CONTEXT:
                break
            chunk = tc.content[:ContentExtractor.MAX_CONTENT_PER_TAB]
            sections.append(f"=== TAB {tc.index + 1}: {tc.title} ===\n"
                            f"URL: {tc.url}\n"
                            f"Domain: {tc.domain}\n\n"
                            f"{chunk}")
            total += len(chunk)
        return '\n\n'.join(sections)

    def _build_system_prompt(self) -> str:
        return """You are GenTab, an AI that generates interactive web applications from browser tab data.

RULES:
1. Generate a COMPLETE, SINGLE HTML file with embedded CSS and JavaScript.
2. The app MUST be visually modern: use CSS Grid/Flexbox, gradients, shadows, rounded corners, smooth transitions.
3. Use a professional color palette. Default to dark theme with accent colors.
4. The app MUST be interactive: sorting, filtering, tabs, expandable sections, etc.
5. Include a header with the app title and a "Sources" section linking back to original URLs.
6. Every data point must reference its source tab.
7. Make it responsive and mobile-friendly.
8. Use modern CSS (variables, clamp(), container queries if needed).
9. Use vanilla JavaScript only (no external libraries).
10. Output ONLY the HTML. No explanations, no markdown fences.

VISUAL STYLE:
- Background: #0f0f23 with subtle gradient
- Cards: #1a1a3e with border-radius: 16px and box-shadow
- Accent: #6366f1 (indigo) with #818cf8 hover
- Text: #e2e8f0 main, #94a3b8 secondary
- Font: system-ui, -apple-system, sans-serif
- Smooth animations on hover and state changes
- Glass-morphism effects where appropriate"""

    def _build_user_prompt(self, context: str) -> str:
        source_list = '\n'.join(
            f"- Tab {tc.index + 1}: {tc.title} ({tc.url})"
            for tc in self.tab_contexts
        )
        return f"""USER REQUEST: {self.prompt}

OPEN TABS DATA:
{context}

SOURCE TABS (link back to these):
{source_list}

Generate a complete interactive HTML application that fulfills the user's request using the data from the open tabs.
Include a "Sources" footer that links to each original tab URL."""

    def _extract_html(self, raw: str) -> str:
        raw = raw.strip()

        for fence in ['```html', '```HTML']:
            if fence in raw:
                start = raw.index(fence) + len(fence)
                end = raw.rfind('```')
                if end > start:
                    raw = raw[start:end].strip()
                break

        if raw.startswith('```'):
            raw = raw[3:]
            if raw.endswith('```'):
                raw = raw[:-3]
            raw = raw.strip()

        if not raw.strip().startswith('<!DOCTYPE') and not raw.strip().startswith('<html'):
            if '<html' in raw:
                idx = raw.index('<html')
                raw = raw[idx:]
            elif '<body' in raw:
                raw = f"<!DOCTYPE html><html><head><meta charset='UTF-8'></head>{raw}</html>"

        if '<html' not in raw.lower() and '<body' not in raw.lower() and '<div' in raw.lower():
            raw = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GenTab</title></head>
<body>{raw}</body></html>"""

        return raw

    def _inject_source_links(self, html: str) -> str:
        badge_css = """
<style id="gentab-badge">
#gentab-badge-bar {
  position: fixed; bottom: 0; left: 0; right: 0;
  background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%);
  color: #c7d2fe; font-family: system-ui, sans-serif;
  padding: 6px 16px; display: flex; align-items: center;
  gap: 12px; font-size: 12px; z-index: 99999;
  border-top: 1px solid rgba(99,102,241,0.3);
  backdrop-filter: blur(10px);
}
#gentab-badge-bar .gentab-logo {
  background: linear-gradient(135deg, #6366f1, #818cf8);
  color: white; padding: 2px 8px; border-radius: 6px;
  font-weight: 700; font-size: 11px; letter-spacing: 0.5px;
}
#gentab-badge-bar a {
  color: #a5b4fc; text-decoration: none;
  padding: 2px 6px; border-radius: 4px;
  transition: all 0.2s;
}
#gentab-badge-bar a:hover {
  background: rgba(99,102,241,0.2); color: #e0e7ff;
}
body { padding-bottom: 36px !important; }
</style>
"""
        source_links = ' '.join(
            f'<a href="{tc.url}" target="_blank" title="{tc.title}">{tc.domain}</a>'
            for tc in self.tab_contexts
        )
        badge_html = f"""
<div id="gentab-badge-bar">
  <span class="gentab-logo">GenTab</span>
  <span>Fuentes:</span>
  {source_links}
  <span style="margin-left:auto;opacity:0.6;">Scrapelio Browser</span>
</div>
"""
        if '</head>' in html:
            html = html.replace('</head>', f'{badge_css}</head>')
        if '</body>' in html:
            html = html.replace('</body>', f'{badge_html}</body>')
        return html

    def _generate_title(self, raw: str) -> str:
        if '<title>' in raw and '</title>' in raw:
            start = raw.index('<title>') + 7
            end = raw.index('</title>')
            title = raw[start:end].strip()
            if title:
                return title

        words = self.prompt.split()
        return ' '.join(words[:6]).capitalize() + ('...' if len(words) > 6 else '')


class GenTabEngine(QObject):
    """Motor principal del sistema GenTabs."""

    gentab_started = Signal()
    gentab_progress = Signal(str)
    gentab_completed = Signal(object)
    gentab_error = Signal(str)
    context_extracted = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings("Scrapelio", "GenTabs")
        self.history: List[GenTabResult] = []
        self._worker: Optional[GenTabWorker] = None
        self._load_history()

    def extract_all_tabs_context(self, tab_manager) -> Tuple[List[TabContext], int]:
        """Extrae contexto de todas las pestañas abiertas. Retorna (contextos, pending_count)."""
        contexts: List[TabContext] = []
        pending = 0

        for i in range(tab_manager.tabs.count()):
            browser = tab_manager.tabs.widget(i)
            if not browser:
                continue

            url = browser.url().toString()
            if not url or url in ('about:blank', 'about:gentab'):
                continue

            title = ""
            if hasattr(browser, 'page') and browser.page():
                title = browser.page().title() or ""

            domain = ContentExtractor.get_domain(url)

            ctx = TabContext(
                index=i,
                url=url,
                title=title or f"Tab {i + 1}",
                content="",
                content_length=0,
                domain=domain
            )
            contexts.append(ctx)
            pending += 1

        return contexts, pending

    def extract_tab_html(self, browser, tab_context: TabContext, callback):
        """Extrae HTML de una pestaña individual de forma asíncrona."""
        def on_html(html):
            try:
                content = ContentExtractor.extract_from_html(
                    html, tab_context.url, tab_context.title
                )
                tab_context.content = content
                tab_context.content_length = len(content)
            except Exception as e:
                tab_context.content = f"[Error extracting: {e}]"
                tab_context.content_length = 0
            callback(tab_context)

        if hasattr(browser, 'page') and browser.page():
            browser.page().toHtml(on_html)
        else:
            tab_context.content = "[No page available]"
            callback(tab_context)

    def generate_gentab(self, server_url: str, prompt: str,
                        tab_contexts: List[TabContext],
                        temperature: float = 0.7,
                        max_tokens: int = 4000):
        """Inicia la generación de una GenTab en un hilo de trabajo."""
        if self._worker and self._worker.isRunning():
            self.gentab_error.emit("Ya hay una generación en curso.")
            return

        valid = [tc for tc in tab_contexts if tc.content and tc.content_length > 0]
        if not valid:
            self.gentab_error.emit("No hay contenido extraído de las pestañas.")
            return

        self._worker = GenTabWorker(server_url, prompt, valid, temperature, max_tokens)
        self._worker.progress.connect(self.gentab_progress.emit)
        self._worker.finished.connect(self._on_generation_complete)
        self._worker.error.connect(self.gentab_error.emit)

        self.gentab_started.emit()
        self._worker.start()

    def _on_generation_complete(self, result: GenTabResult):
        self.history.insert(0, result)
        if len(self.history) > 50:
            self.history = self.history[:50]
        self._save_history()
        self.gentab_completed.emit(result)

    def get_history(self) -> List[GenTabResult]:
        return self.history

    def clear_history(self):
        self.history.clear()
        self._save_history()

    def _save_history(self):
        try:
            data = []
            for r in self.history[:20]:
                entry = {
                    'id': r.id,
                    'title': r.title,
                    'prompt': r.prompt,
                    'source_tabs': r.source_tabs,
                    'created_at': r.created_at,
                    'generation_time': r.generation_time,
                    'model_used': r.model_used,
                }
                data.append(entry)
            self.settings.setValue("history", json.dumps(data))
        except Exception as e:
            logger.error(f"Error saving GenTab history: {e}")

    def _load_history(self):
        try:
            raw = self.settings.value("history", "[]")
            data = json.loads(raw) if isinstance(raw, str) else []
            self.history = []
            for entry in data:
                result = GenTabResult(
                    id=entry.get('id', ''),
                    title=entry.get('title', ''),
                    html='',
                    prompt=entry.get('prompt', ''),
                    source_tabs=entry.get('source_tabs', []),
                    created_at=entry.get('created_at', ''),
                    generation_time=entry.get('generation_time', 0),
                    model_used=entry.get('model_used', ''),
                )
                self.history.append(result)
        except Exception as e:
            logger.error(f"Error loading GenTab history: {e}")
            self.history = []
