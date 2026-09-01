#!/usr/bin/env python3
"""AI Live IDE — Entry point del plugin para UnifiedPluginManager.

Este módulo es el que `UnifiedPluginManager.load_plugin()` carga
dinámicamente. Expone:

    - get_plugin_info()       → dict con metadata
    - initialize_plugin()     → bool indicando si el plugin está disponible
    - get_panel_class()       → clase QWidget del panel (UnifiedPluginManager
                                lo prefiere para plugins modernos)
    - get_ai_live_ide_panel() → alias de get_panel_class (compatibilidad con
                                la convención `get_<plugin>_panel`)
    - shutdown()              → libera recursos al desactivar el plugin
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

plugin_dir = Path(__file__).parent
if str(plugin_dir) not in sys.path:
    sys.path.insert(0, str(plugin_dir))

PLUGIN_ID = "ai_live_ide"
PLUGIN_NAME = "AI Live IDE"
PLUGIN_VERSION = "1.0.0"
PLUGIN_AUTHOR = "Scrapelio Team"
PLUGIN_DESCRIPTION = (
    "IDE en vivo con asistente IA: Monaco Editor + Live Preview "
    "+ Hugging Face Qwen2.5-Coder. Plugin premium estrella de Scrapelio."
)

AI_LIVE_IDE_AVAILABLE = False
AILiveIDEPanel = None  # type: ignore[assignment]

try:
    from ai_live_ide_panel import AILiveIDEPanel as _AILiveIDEPanel  # noqa: E402

    AILiveIDEPanel = _AILiveIDEPanel
    AI_LIVE_IDE_AVAILABLE = True
    print("[OK] AI Live IDE plugin cargado")
except Exception as exc:  # noqa: BLE001
    AI_LIVE_IDE_AVAILABLE = False
    print(f"[WARNING] AI Live IDE plugin no disponible: {exc}")
    import traceback as _tb
    _tb.print_exc()


def get_plugin_info() -> dict:
    """Devuelve la metadata del plugin."""
    return {
        "id": PLUGIN_ID,
        "name": PLUGIN_NAME,
        "version": PLUGIN_VERSION,
        "author": PLUGIN_AUTHOR,
        "description": PLUGIN_DESCRIPTION,
        "category": "developer_tools",
        "premium": True,
        "available": AI_LIVE_IDE_AVAILABLE,
        "dependencies": ["requests"],
        "compatibility": ">=1.0.0",
        "features": [
            "Editor Monaco profesional",
            "Live Preview HTML/CSS/JS",
            "Asistente IA con Hugging Face Qwen2.5-Coder",
            "Auto-reload con QFileSystemWatcher",
        ],
    }


def initialize_plugin() -> bool:
    """Hook llamado por UnifiedPluginManager al cargar el plugin."""
    if AI_LIVE_IDE_AVAILABLE:
        print("[OK] AI Live IDE plugin inicializado")
        return True
    print("[WARNING] AI Live IDE plugin no inicializado (módulo no disponible)")
    return False


def get_panel_class():
    """Devuelve la clase del panel (la convención que usa pentesting_tool)."""
    return AILiveIDEPanel


def get_ai_live_ide_panel():
    """Alias siguiendo la convención `get_<plugin>_panel` (scraping, seo…)."""
    return AILiveIDEPanel


def shutdown() -> bool:
    """Hook de limpieza. UnifiedPluginManager.unload_plugin() lo llamará."""
    print("[OK] AI Live IDE plugin shutdown")
    return True


__all__ = [
    "PLUGIN_ID",
    "PLUGIN_NAME",
    "PLUGIN_VERSION",
    "AI_LIVE_IDE_AVAILABLE",
    "AILiveIDEPanel",
    "get_plugin_info",
    "initialize_plugin",
    "get_panel_class",
    "get_ai_live_ide_panel",
    "shutdown",
]
