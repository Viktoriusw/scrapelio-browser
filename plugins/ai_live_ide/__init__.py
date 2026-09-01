#!/usr/bin/env python3
"""AI Live IDE — paquete del plugin premium estrella de Scrapelio Browser.

Este `__init__.py` proporciona la metadata estática y reexporta las funciones
del entry point (`plugin.py`) para que el resto del navegador pueda hacer:

    from plugins.ai_live_ide import get_panel_class, initialize_plugin

al igual que con los demás plugins (`scraping`, `seo_analyzer`, etc.).
"""

__version__ = "1.0.0"
__author__ = "Scrapelio Team"
__description__ = (
    "IDE en vivo con asistente IA basado en Hugging Face Qwen2.5-Coder, "
    "editor Monaco embebido y live preview HTML/CSS/JS."
)

PLUGIN_INFO = {
    "id": "ai_live_ide",
    "name": "AI Live IDE",
    "version": __version__,
    "author": __author__,
    "description": __description__,
    "category": "developer_tools",
    "dependencies": ["requests"],
    "compatibility": ">=1.0.0",
    "premium": True,
    "icon": "🧠",
}


def get_plugin_info() -> dict:
    """Metadata sintética (usada por algunos verificadores)."""
    return dict(PLUGIN_INFO)


def initialize_plugin() -> bool:
    """Delegación al entry point real del plugin."""
    try:
        from . import plugin as _plugin
        return _plugin.initialize_plugin()
    except ImportError as exc:
        print(f"[WARNING] AI Live IDE plugin no disponible: {exc}")
        return False


__all__ = ["PLUGIN_INFO", "get_plugin_info", "initialize_plugin"]
