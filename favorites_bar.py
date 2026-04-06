#!/usr/bin/env python3
"""
Favorites Bar - Complete implementation similar to Firefox/Chrome
"""

from PySide6.QtWidgets import (QToolBar, QMenu, QDialog, QVBoxLayout,
                               QHBoxLayout, QLabel, QLineEdit, QComboBox,
                               QPushButton, QMessageBox, QCheckBox, QWidget,
                               QToolButton)
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QIcon, QPixmap, QAction
import sqlite3
import os
from urllib.parse import urlparse
import urllib.request
import logging

logger = logging.getLogger(__name__)

def get_favicon_icon(url, favicon_cache=None):
    """
    Utility function to get favicon from a URL
    Returns a QIcon for general use
    """
    if favicon_cache is None:
        favicon_cache = {}
    
    try:
        if url in favicon_cache:
            return favicon_cache[url]
        
        parsed_url = urlparse(url)
        favicon_url = f"{parsed_url.scheme}://{parsed_url.netloc}/favicon.ico"
        
        # Do not download favicons during initialization to avoid blocking
        # TODO: Implement asynchronous favicon download in the future
        
        # Default favicon
        try:
            default_icon = QIcon("icons/bookmark.svg")
            if default_icon.isNull():
                # Create a simple icon if no file exists
                pixmap = QPixmap(16, 16)
                pixmap.fill()
                default_icon = QIcon(pixmap)
        except:
            # Last resort: empty icon
            pixmap = QPixmap(16, 16)
            pixmap.fill()
            default_icon = QIcon(pixmap)
            
        favicon_cache[url] = default_icon
        return default_icon
        
    except Exception as e:
        logger.error(f"Error getting favicon for URL %s: %s", url, e)
        return QIcon("icons/bookmark.svg")

def get_favicon_pixmap(url, favicon_cache=None):
    """
    Utility function to get favicon as QPixmap
    For compatibility with code that needs QPixmap
    """
    icon = get_favicon_icon(url, favicon_cache)
    return icon.pixmap(16, 16)

class FavoriteDialog(QDialog):
    """Dialog for adding/editing favorites in the bar"""
    
    def __init__(self, parent=None, title="", url="", category="", show_in_bar=True):
        super().__init__(parent)
        self.setWindowTitle("Add to Favorites")
        self.setModal(True)
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Title
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("Title:"))
        self.title_edit = QLineEdit(title)
        title_layout.addWidget(self.title_edit)
        layout.addLayout(title_layout)
        
        # URL
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("URL:"))
        self.url_edit = QLineEdit(url)
        url_layout.addWidget(self.url_edit)
        layout.addLayout(url_layout)
        
        # Category
        category_layout = QHBoxLayout()
        category_layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.load_categories()
        if category:
            index = self.category_combo.findText(category)
            if index >= 0:
                self.category_combo.setCurrentIndex(index)
        category_layout.addWidget(self.category_combo)
        layout.addLayout(category_layout)
        
        # Show in favorites bar
        self.show_in_bar_check = QCheckBox("Show in favorites bar")
        self.show_in_bar_check.setChecked(show_in_bar)
        layout.addWidget(self.show_in_bar_check)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
    
    def load_categories(self):
        """Loads available categories"""
        try:
            conn = sqlite3.connect('bookmarks.db')
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM categories ORDER BY name")
            categories = cursor.fetchall()
            
            self.category_combo.addItem("No category")
            for category in categories:
                self.category_combo.addItem(category[0])
            
            conn.close()
        except Exception as e:
            logger.error("Error loading favorite categories from bookmarks.db: %s", e)
    
    def get_values(self):
        """Gets values from the dialog"""
        return {
            'title': self.title_edit.text(),
            'url': self.url_edit.text(),
            'category': self.category_combo.currentText(),
            'show_in_bar': self.show_in_bar_check.isChecked()
        }

class FavoritesBar(QToolBar):
    """Favorites bar with complete functionality"""
    
    favorite_clicked = Signal(str)  # Signal when a favorite is clicked
    
    def __init__(self, parent=None):
        super().__init__("Favorites", parent)
        self.setWindowTitle("Favorites Bar")
        self.setVisible(False)  # Initially hidden
        
        # Configure the bar
        self.setMovable(True)
        self.setFloatable(True)
        self.setIconSize(QPixmap(16, 16).size())
        # Sin restricción de altura máxima: la barra se ajusta a su contenido.
        # Los botones de carpeta (QToolButton añadidos con addWidget) tienen
        # su propio stylesheet con padding generoso.
        self.setStyleSheet("""
            QToolBar {
                spacing: 2px;
                padding: 2px 6px;
                border: none;
            }
            QToolBar::separator {
                width: 1px;
                background: rgba(128,128,128,0.35);
                margin: 4px 3px;
            }
            QToolButton {
                min-width: 24px;
                padding: 4px 6px;
                margin: 0px;
                border: none;
                border-radius: 4px;
            }
            QToolButton:hover {
                background-color: rgba(255, 255, 255, 0.12);
            }
        """)
        
        # Favicon cache
        self.favicon_cache = {}
        
        # Load favorites
        self.load_favorites()
    
    def load_favorites(self):
        """Loads favorites from the database"""
        try:
            conn = sqlite3.connect('bookmarks.db')
            cursor = conn.cursor()
            
            # Get favorites marked for the bar
            cursor.execute("""
                SELECT title, url, category, notes, tags 
                FROM bookmarks 
                WHERE notes LIKE '%[barra]%' 
                   OR tags LIKE '%[barra]%' 
                   OR category LIKE '%Barra%' 
                   OR tags LIKE '%barra%' 
                   OR notes LIKE '%barra%'
                   OR category = 'Barra de Favoritos'
                ORDER BY title
            """)
            
            favorites = cursor.fetchall()
            conn.close()
            
            # Clear current bar
            self.clear()
            
            # Add favorites to the bar
            for favorite in favorites:
                title, url, category, notes, tags = favorite
                self.add_favorite_to_bar(title, url)
            
            # Add button to add current page
            self.add_add_favorite_action()
            
        except Exception as e:
            logger.error("Error loading favorites for favorites bar: %s", e)
    
    def add_favorite_to_bar(self, title, url):
        """Adds a favorite to the bar"""
        try:
            # Get favicon
            icon = self.get_favicon(url)
            
            # Create action
            action = QAction(icon, title, self)
            action.setToolTip(f"{title}\n{url}")
            action.setData(url)
            action.triggered.connect(lambda: self.favorite_clicked.emit(url))
            
            # Add context menu
            action.setMenu(self.create_favorite_menu(title, url))
            
            # Add to bar
            self.addAction(action)
            
        except Exception as e:
            logger.error("Error adding favorite '%s' (%s) to bar: %s", title, url, e)
    
    def create_favorite_menu(self, title, url):
        """Creates the context menu for a favorite"""
        menu = QMenu()
        
        # Open
        open_action = menu.addAction("Open")
        open_action.triggered.connect(lambda: self.favorite_clicked.emit(url))
        
        # Open in new tab
        open_new_tab_action = menu.addAction("Open in new tab")
        open_new_tab_action.triggered.connect(lambda: self.open_in_new_tab(url))
        
        menu.addSeparator()
        
        # Edit
        edit_action = menu.addAction("Edit")
        edit_action.triggered.connect(lambda: self.edit_favorite(title, url))
        
        # Remove from bar
        remove_action = menu.addAction("Remove from favorites bar")
        remove_action.triggered.connect(lambda: self.remove_from_bar(title, url))
        
        menu.addSeparator()
        
        # Delete
        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(lambda: self.delete_favorite(title, url))
        
        return menu
    
    def add_add_favorite_action(self):
        """Adds the button to add the current page"""
        add_action = QAction("⭐", self)
        add_action.setToolTip("Add current page to favorites")
        add_action.triggered.connect(self.add_current_page)
        self.addAction(add_action)
    
    def add_current_page(self):
        """Adds the current page to favorites"""
        try:
            # Get the current page from the browser
            main_window = self.window()
            if hasattr(main_window, 'tab_manager'):
                current_tab = main_window.tab_manager.tabs.currentWidget()
                if current_tab:
                    url = current_tab.url().toString()
                    title = current_tab.page().title()
                    
                    # Show dialog
                    dialog = FavoriteDialog(self, title, url)
                    if dialog.exec():
                        values = dialog.get_values()
                        self.save_favorite(values)
                        
        except Exception as e:
            logger.error("Error adding current page to favorites: %s", e)
    
    def save_favorite(self, values):
        """Saves a favorite to the database"""
        try:
            conn = sqlite3.connect('bookmarks.db')
            cursor = conn.cursor()
            
            # Prepare notes and tags based on whether it's shown in the bar
            notes = "[barra]" if values['show_in_bar'] else ""
            tags = "barra" if values['show_in_bar'] else ""
            
            # Insert into database
            cursor.execute("""
                INSERT INTO bookmarks (title, url, category, notes, tags) 
                VALUES (?, ?, ?, ?, ?)
            """, (values['title'], values['url'], values['category'], notes, tags))
            
            conn.commit()
            conn.close()
            
            # Reload the bar
            self.load_favorites()
            
            QMessageBox.information(self, "Success", "Favorite saved successfully")
            
        except Exception as e:
            logger.error("Error saving favorite to bookmarks.db: %s", e)
            QMessageBox.critical(self, "Error", f"Error saving favorite: {e}")
    
    def edit_favorite(self, title, url):
        """Edits an existing favorite"""
        try:
            conn = sqlite3.connect('bookmarks.db')
            cursor = conn.cursor()
            
            # Get current data
            cursor.execute("""
                SELECT title, url, category, notes, tags 
                FROM bookmarks 
                WHERE url = ?
            """, (url,))
            
            result = cursor.fetchone()
            if result:
                current_title, current_url, current_category, current_notes, current_tags = result
                show_in_bar = "[barra]" in current_notes or "barra" in current_tags
                
                # Show edit dialog
                dialog = FavoriteDialog(self, current_title, current_url, current_category, show_in_bar)
                if dialog.exec():
                    values = dialog.get_values()
                    self.update_favorite(url, values)
            
            conn.close()
            
        except Exception as e:
            logger.error("Error editing favorite '%s' (%s): %s", title, url, e)
            QMessageBox.critical(self, "Error", f"Error editing favorite: {e}")
    
    def update_favorite(self, old_url, values):
        """Updates an existing favorite"""
        try:
            conn = sqlite3.connect('bookmarks.db')
            cursor = conn.cursor()
            
            # Prepare notes and tags
            notes = "[barra]" if values['show_in_bar'] else ""
            tags = "barra" if values['show_in_bar'] else ""
            
            # Update in database
            cursor.execute("""
                UPDATE bookmarks 
                SET title = ?, url = ?, category = ?, notes = ?, tags = ?
                WHERE url = ?
            """, (values['title'], values['url'], values['category'], notes, tags, old_url))
            
            conn.commit()
            conn.close()
            
            # Reload the bar
            self.load_favorites()
            
            QMessageBox.information(self, "Success", "Favorite updated successfully")
            
        except Exception as e:
            logger.error("Error updating favorite %s -> %s: %s", old_url, values.get('url'), e)
            QMessageBox.critical(self, "Error", f"Error updating favorite: {e}")
    
    def remove_from_bar(self, title, url):
        """Removes a favorite from the bar (but does not delete it)"""
        try:
            conn = sqlite3.connect('bookmarks.db')
            cursor = conn.cursor()
            
            # Update to remove from bar
            cursor.execute("""
                UPDATE bookmarks 
                SET notes = REPLACE(notes, '[barra]', ''), 
                    tags = REPLACE(tags, 'barra', '')
                WHERE url = ?
            """, (url,))
            
            conn.commit()
            conn.close()
            
            # Reload the bar
            self.load_favorites()
            
            QMessageBox.information(self, "Success", "Favorite removed from bar")
            
        except Exception as e:
            logger.error("Error removing favorite '%s' (%s) from bar: %s", title, url, e)
            QMessageBox.critical(self, "Error", f"Error removing favorite from bar: {e}")
    
    def delete_favorite(self, title, url):
        """Completely deletes a favorite"""
        reply = QMessageBox.question(
            self, "Confirm deletion", 
            f"Are you sure you want to delete '{title}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                conn = sqlite3.connect('bookmarks.db')
                cursor = conn.cursor()
                
                cursor.execute("DELETE FROM bookmarks WHERE url = ?", (url,))
                
                conn.commit()
                conn.close()
                
                # Reload the bar
                self.load_favorites()
                
                QMessageBox.information(self, "Success", "Favorite deleted successfully")
                
            except Exception as e:
                logger.error("Error deleting favorite '%s' (%s): %s", title, url, e)
                QMessageBox.critical(self, "Error", f"Error deleting favorite: {e}")
    
    def open_in_new_tab(self, url):
        """Opens a favorite in a new tab"""
        try:
            main_window = self.window()
            if hasattr(main_window, 'tab_manager'):
                main_window.tab_manager.add_new_tab(url)
        except Exception as e:
            logger.error("Error opening favorite in new tab (%s): %s", url, e)
    
    def get_favicon(self, url):
        """Gets the favicon for a URL"""
        return get_favicon_icon(url, self.favicon_cache)
    
    def refresh_favorites(self):
        """Updates the favorites bar"""
        self.load_favorites()

    # ─── Integración con el sistema de carpetas ───────────────────────────────

    def load_with_folders(self, folders_manager) -> None:
        """
        Recarga la barra mostrando primero las carpetas como botones con
        submenú desplegable y después los marcadores sueltos de la raíz.

        Debe llamarse cuando el sistema de carpetas está disponible, en lugar
        de (o además de) load_favorites().

        Args:
            folders_manager: Instancia de FoldersManager.
        """
        try:
            self.clear()

            hierarchy = folders_manager.get_hierarchy()

            # Subcarpetas de la raíz → botón con submenú
            for sub in hierarchy.get("children_folders", []):
                self._add_folder_button(sub)

            # Marcadores directamente en la raíz
            for bm in hierarchy.get("children_bookmarks", []):
                self.add_favorite_to_bar(bm["title"], bm["url"])

            # Separador + botón de añadir
            self.addSeparator()
            self.add_add_favorite_action()

        except Exception as e:
            logger.error("Error cargando barra de favoritos con carpetas: %s", e)
            # Fallback al sistema anterior
            self.load_favorites()

    _FOLDER_MENU_STYLE = """
        QMenu {
            background-color: #1e1e2e;
            color: #cdd6f4;
            border: 1px solid #313244;
            border-radius: 6px;
            padding: 4px;
            font-size: 13px;
        }
        QMenu::item {
            padding: 5px 20px 5px 10px;
            border-radius: 4px;
        }
        QMenu::item:selected {
            background-color: #45475a;
        }
        QMenu::separator {
            height: 1px;
            background-color: #313244;
            margin: 4px 8px;
        }
    """

    def _add_folder_button(self, folder_node: dict) -> None:
        """
        Añade un QToolButton a la barra que despliega un submenú con los
        contenidos de la carpeta al hacer clic (sin flecha desplegable).
        """
        try:
            _menu_style = self._FOLDER_MENU_STYLE

            submenu = QMenu(folder_node["name"], self)
            submenu.setStyleSheet(_menu_style)
            self._build_folder_submenu(submenu, folder_node)

            btn = QToolButton(self)
            label = folder_node["name"].upper()
            btn.setText(label)
            btn.setToolTip(folder_node["name"])
            btn.setMenu(submenu)
            # InstantPopup: click directo → menú, sin flecha lateral
            btn.setPopupMode(QToolButton.InstantPopup)

            btn.setStyleSheet("""
                QToolButton {
                    background: transparent;
                    border: none;
                    padding: 4px 10px;
                    font-size: 12px;
                    font-weight: 700;
                    letter-spacing: 0.8px;
                    border-radius: 4px;
                }
                QToolButton:hover {
                    background-color: rgba(255,255,255,0.12);
                }
                QToolButton:pressed {
                    background-color: rgba(255,255,255,0.20);
                }
                QToolButton::menu-indicator {
                    width: 0px;
                    height: 0px;
                    image: none;
                }
            """)

            # Forzar ancho suficiente para el texto completo.
            # sizeHint() no es fiable antes de mostrar el widget, así que
            # calculamos directamente con QFontMetrics.
            from PySide6.QtGui import QFontMetrics
            fm = QFontMetrics(btn.font())
            text_px = fm.horizontalAdvance(label)
            btn.setMinimumWidth(text_px + 24)   # padding izq+der = 2×10 + 4 extra

            self.addWidget(btn)

        except Exception as e:
            logger.error("Error añadiendo botón de carpeta '%s': %s", folder_node.get("name"), e)

    def _build_folder_submenu(self, menu: QMenu, folder_node: dict) -> None:
        """
        Rellena *menu* de forma recursiva con las subcarpetas y marcadores
        de *folder_node*.
        """
        # Subcarpetas → submenús anidados
        for sub in folder_node.get("children_folders", []):
            submenu = menu.addMenu(f"📁 {sub['name']}")
            submenu.setStyleSheet(self._FOLDER_MENU_STYLE)
            self._build_folder_submenu(submenu, sub)

        # Marcadores de esta carpeta
        bms = folder_node.get("children_bookmarks", [])
        if folder_node.get("children_folders") and bms:
            menu.addSeparator()

        for bm in bms:
            url = bm["url"]
            title = bm["title"]
            icon = self.get_favicon(url)
            action = menu.addAction(icon, title)
            action.setToolTip(f"{title}\n{url}")
            action.triggered.connect(lambda _checked=False, u=url: self.favorite_clicked.emit(u))