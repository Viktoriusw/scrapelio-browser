#!/usr/bin/env python3
"""
Modern Widgets - Widgets modernos para la UI

Extraído de modern_styles.py, conservando solo los widgets que se usan
en ui.py (ExpandableUrlBar principalmente)
"""

from PySide6.QtWidgets import (QLineEdit, QPushButton, QGraphicsOpacityEffect)
from PySide6.QtCore import Signal, QPropertyAnimation, Qt, QSize
from PySide6.QtGui import QIcon


class CircularButton(QPushButton):
    """Botón circular estilo Chrome con animaciones"""

    def __init__(self, icon_path=None, parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 36)
        self.setCursor(Qt.PointingHandCursor)

        if icon_path:
            self.setIcon(QIcon(icon_path))
            self.setIconSize(QSize(20, 20))

        # Efecto de opacidad para animaciones
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)

    def animate_click(self):
        """Animación al hacer click"""
        self.animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.animation.setDuration(150)
        self.animation.setStartValue(1.0)
        self.animation.setKeyValueAt(0.5, 0.7)
        self.animation.setEndValue(1.0)
        self.animation.start()


class ExpandableUrlBar(QLineEdit):
    """Barra de URL expandible tipo Chrome - VERSION RESPONSIVE"""

    focused = Signal()
    unfocused = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Buscar o escribir URL...")

        # ✅ CRÍTICO: Anchos más conservadores para evitar overflow
        # Ya NO establecemos anchos fijos aquí - se manejarán desde ui.py
        # self.default_width = 600
        # self.expanded_width = 800
        # self.setMinimumWidth(self.default_width)
        # self.setMaximumWidth(self.expanded_width)

        # ⚠️ DESACTIVADO: Animación de expansión que causaba problemas
        # self.expand_animation = QPropertyAnimation(self, b"minimumWidth")
        # self.expand_animation.setDuration(200)

        # NUEVO: Sin expansión automática para evitar problemas de layout
        self.expansion_enabled = False

    def focusInEvent(self, event):
        """Recibir foco SIN expandir (para evitar problemas de layout)"""
        super().focusInEvent(event)

        # ✅ Ya NO se expande al hacer clic - comportamiento estable
        # if self.expansion_enabled:
        #     self.expand_animation.stop()
        #     self.expand_animation.setStartValue(self.width())
        #     self.expand_animation.setEndValue(self.expanded_width)
        #     self.expand_animation.start()

        self.focused.emit()

    def focusOutEvent(self, event):
        """Perder foco SIN contraer"""
        super().focusOutEvent(event)

        # ✅ Ya NO se contrae al perder foco
        # if self.expansion_enabled:
        #     self.expand_animation.stop()
        #     self.expand_animation.setStartValue(self.width())
        #     self.expand_animation.setEndValue(self.default_width)
        #     self.expand_animation.start()

        self.unfocused.emit()

