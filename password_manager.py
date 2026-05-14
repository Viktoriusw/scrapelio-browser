from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLabel, QLineEdit, QListWidget, QListWidgetItem,
                              QDialog, QMessageBox, QInputDialog, QCheckBox,
                              QSpinBox, QComboBox, QGroupBox, QApplication,
                              QTableWidget, QTableWidgetItem, QHeaderView,
                              QDialogButtonBox, QFrame, QGraphicsOpacityEffect)
from PySide6.QtCore import (Qt, QSettings, Signal, QUrl, QObject, Slot,
                            QTimer, QPropertyAnimation, QEasingCurve)
from PySide6.QtGui import QIcon, QIntValidator
from PySide6.QtWebEngineWidgets import QWebEngineView
import json
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import os
import sqlite3
from datetime import datetime
from urllib.parse import urlparse

# Importar password_generator con fallback
try:
    from password_generator import PasswordGenerator
except ImportError:
    # Fallback simple si no existe password_generator
    class PasswordGenerator:
        def generate_password(self, length=16, **kwargs):
            import random
            import string
            chars = string.ascii_letters + string.digits + "!@#$%^&*"
            password = ''.join(random.choice(chars) for _ in range(length))
            return {
                "password": password,
                "time": "0.1s",
                "cpu_usage": "1%",
                "ram_usage": "1MB"
            }


def _normalize_origin(url_str: str) -> str:
    """Normalize a URL to its origin (scheme://host[:port])."""
    try:
        parsed = urlparse(url_str)
        scheme = parsed.scheme or "https"
        host = parsed.hostname or ""
        port = parsed.port
        if port and port not in (80, 443):
            return f"{scheme}://{host}:{port}"
        return f"{scheme}://{host}"
    except Exception:
        return url_str


# ---------------------------------------------------------------------------
# PasswordSaveBanner — non-intrusive banner (replaces blocking QDialog)
# ---------------------------------------------------------------------------

class PasswordSaveBanner(QFrame):
    """Non-intrusive banner shown below the nav bar when credentials are detected.

    Signals:
        accepted – user clicked Save / Update
        dismissed – user clicked "Not now" or banner auto-dismissed
    """

    accepted = Signal()
    dismissed = Signal()

    def __init__(self, url: str, username: str, password: str,
                 is_update: bool = False, parent=None):
        super().__init__(parent)
        self.url = url
        self.username = username
        self.password = password
        self.is_update = is_update
        self.setObjectName("passwordSaveBanner")
        self.setFrameShape(QFrame.NoFrame)
        self.setFixedHeight(48)
        self._build_ui()
        self._apply_style()
        # Auto-dismiss after 15 seconds
        self._auto_timer = QTimer(self)
        self._auto_timer.setSingleShot(True)
        self._auto_timer.setInterval(15000)
        self._auto_timer.timeout.connect(self._on_dismiss)
        self._auto_timer.start()
    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(8)

        # Icon
        icon_label = QLabel("🔑")
        icon_label.setFixedWidth(24)
        layout.addWidget(icon_label)

        # Text
        action = "Update" if self.is_update else "Save"
        origin = _normalize_origin(self.url)
        text = f"{action} password for <b>{self.username}</b> on {origin}?"
        self._text_label = QLabel(text)
        self._text_label.setTextFormat(Qt.RichText)
        layout.addWidget(self._text_label, 1)

        # Save / Update button
        action_label = "Update" if self.is_update else "Save"
        self._save_btn = QPushButton(action_label)
        self._save_btn.setFixedHeight(30)
        self._save_btn.setCursor(Qt.PointingHandCursor)
        self._save_btn.clicked.connect(self._on_accept)
        layout.addWidget(self._save_btn)

        # Dismiss button
        self._dismiss_btn = QPushButton("Not now")
        self._dismiss_btn.setFixedHeight(30)
        self._dismiss_btn.setCursor(Qt.PointingHandCursor)
        self._dismiss_btn.clicked.connect(self._on_dismiss)
        layout.addWidget(self._dismiss_btn)
    def _apply_style(self):
        self.setStyleSheet("""
            QFrame#passwordSaveBanner {
                background-color: rgba(30, 80, 160, 0.92);
                border-bottom: 1px solid rgba(100, 160, 255, 0.4);
            }
            QFrame#passwordSaveBanner QLabel {
                color: #f0f0f0;
                font-size: 13px;
            }
            QFrame#passwordSaveBanner QPushButton {
                background-color: rgba(255, 255, 255, 0.15);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.25);
                border-radius: 4px;
                padding: 2px 14px;
                font-size: 12px;
            }
            QFrame#passwordSaveBanner QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.28);
            }
        """)
    def _on_accept(self):
        self._auto_timer.stop()
        self.accepted.emit()
        self._animate_out()
    def _on_dismiss(self):
        self._auto_timer.stop()
        self.dismissed.emit()
        self._animate_out()
    def _animate_out(self):
        """Slide up + fade out, then delete."""
        try:
            anim = QPropertyAnimation(self, b"maximumHeight", self)
            anim.setDuration(200)
            anim.setStartValue(self.height())
            anim.setEndValue(0)
            anim.setEasingCurve(QEasingCurve.InQuad)
            anim.finished.connect(self.deleteLater)
            anim.start()
        except Exception:
            self.deleteLater()


# ---------------------------------------------------------------------------
# JS capture script — stored as constant, injected via runJavaScript()
# No QWebChannel dependency. Stores captured creds in window.__scrapelioLastCred
# ---------------------------------------------------------------------------

_CAPTURE_JS = r'''
(function() {
    if (window.__scrapelioPasswordCapture) return;
    window.__scrapelioPasswordCapture = true;
    window.__scrapelioLastCred = null;

    function isUsernameField(input) {
        if (!input || input.type === 'hidden') return false;
        var type = (input.type || '').toLowerCase();
        if (type === 'password' || type === 'submit' || type === 'button' ||
            type === 'checkbox' || type === 'radio' || type === 'file') return false;
        if (type === 'email') return true;
        var attrs = [
            (input.name || ''), (input.id || ''),
            (input.placeholder || ''), (input.autocomplete || ''),
            (input.getAttribute('aria-label') || '')
        ].join(' ').toLowerCase();
        var positives = ['user', 'email', 'login', 'account', 'nick',
                         'identifier', 'phone', 'mobile', 'correo',
                         'usuario', 'nombre'];
        for (var i = 0; i < positives.length; i++) {
            if (attrs.indexOf(positives[i]) !== -1) return true;
        }
        var ac = (input.autocomplete || '').toLowerCase();
        if (ac === 'username' || ac === 'email') return true;
        return false;
    }

    function findFormFields(root) {
        var fields = { username: null, password: null };
        var inputs = root.querySelectorAll('input');
        var passwordInputs = [];
        for (var i = 0; i < inputs.length; i++) {
            var inp = inputs[i];
            if ((inp.type || '').toLowerCase() === 'password') {
                passwordInputs.push(inp);
            }
        }
        if (passwordInputs.length === 0) return fields;
        fields.password = passwordInputs[0];
        var allInputs = Array.prototype.slice.call(inputs);
        var pwIndex = allInputs.indexOf(fields.password);
        for (var j = pwIndex - 1; j >= 0; j--) {
            if (isUsernameField(allInputs[j])) {
                fields.username = allInputs[j];
                break;
            }
        }
        if (!fields.username) {
            for (var k = 0; k < allInputs.length; k++) {
                if (isUsernameField(allInputs[k])) {
                    fields.username = allInputs[k];
                    break;
                }
            }
        }
        return fields;
    }

    function getOrigin() {
        return window.location.protocol + '//' + window.location.host;
    }

    function storeCred(user, pass) {
        window.__scrapelioLastCred = JSON.stringify({
            origin: getOrigin(),
            username: user,
            password: pass
        });
    }

    // Capture form submit (CAPTURE phase)
    document.addEventListener('submit', function(e) {
        try {
            var form = e.target;
            if (!form || form.tagName !== 'FORM') return;
            var fields = findFormFields(form);
            if (!fields.username || !fields.password) return;
            var user = fields.username.value;
            var pass = fields.password.value;
            if (user && pass) storeCred(user, pass);
        } catch (ex) {}
    }, true);

    // Capture click on submit buttons (for formless logins)
    document.addEventListener('click', function(e) {
        try {
            var btn = e.target;
            if (!btn) return;
            var el = btn.closest('button[type="submit"], input[type="submit"], button:not([type])');
            if (!el) return;
            var form = el.closest('form');
            var container = form || el.closest('div, section, main') || document.body;
            var fields = findFormFields(container);
            if (fields.username && fields.password &&
                fields.username.value && fields.password.value) {
                storeCred(fields.username.value, fields.password.value);
            }
        } catch (ex) {}
    }, true);
})();
'''

_READ_CRED_JS = 'window.__scrapelioLastCred || null'


# ---------------------------------------------------------------------------
# PasswordManager — main widget + DB + encryption + browser integration
# ---------------------------------------------------------------------------

class PasswordManager(QWidget):
    password_saved = Signal(str, str)   # url, username
    password_updated = Signal(str, str) # url, username
    password_deleted = Signal(str)      # url

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.password_generator = PasswordGenerator()
        self.settings = QSettings("Scrapelio", "Passwords")
        self.db_path = "passwords.db"
        self.init_ui()
        self.init_database()
        self.load_passwords()
        self.setup_encryption()
        self._browser_connections = {}   # browser_id → list of (signal, slot)
        self._dismissed_origins = set()  # origins dismissed this session
        self._active_banner = None       # current PasswordSaveBanner
    # -----------------------------------------------------------------
    # UI
    # -----------------------------------------------------------------

    def init_ui(self):
        """Initializes the user interface"""
        layout = QVBoxLayout(self)

        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search passwords...")
        self.search_input.setFixedHeight(32)
        if hasattr(self.search_input, "setClearButtonEnabled"):
            self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self.filter_passwords)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # Password list
        self.passwords_list = QListWidget()
        self.passwords_list.setToolTip("Double-click to view password details")
        layout.addWidget(self.passwords_list)

        # Action buttons
        buttons_layout = QHBoxLayout()

        self.add_button = QPushButton("Add")
        self.add_button.clicked.connect(self.add_password)
        buttons_layout.addWidget(self.add_button)

        self.view_button = QPushButton("View")
        self.view_button.clicked.connect(
            lambda: self.view_password_details(self.passwords_list.currentItem())
            if self.passwords_list.currentItem() else None
        )
        buttons_layout.addWidget(self.view_button)

        self.edit_button = QPushButton("Edit")
        self.edit_button.clicked.connect(self.edit_password)
        buttons_layout.addWidget(self.edit_button)

        self.remove_button = QPushButton("Remove")
        self.remove_button.clicked.connect(self.remove_password)
        buttons_layout.addWidget(self.remove_button)

        self.generate_button = QPushButton("Generate")
        self.generate_button.clicked.connect(self.show_generator)
        buttons_layout.addWidget(self.generate_button)

        layout.addLayout(buttons_layout)
        self.setLayout(layout)
    # -----------------------------------------------------------------
    # Database
    # -----------------------------------------------------------------

    def init_database(self):
        """Initializes the password database"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS passwords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    username TEXT NOT NULL,
                    password TEXT NOT NULL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            self.conn.commit()
        except Exception as e:
            print(f"Error initializing database: {str(e)}")
    def load_passwords(self):
        """Loads saved passwords"""
        try:
            self.passwords_list.clear()
            cursor = self.conn.cursor()
            cursor.execute("SELECT url, username, notes FROM passwords ORDER BY url")
            for row in cursor.fetchall():
                item = QListWidgetItem(f"{row[0]} - {row[1]}")
                if row[2]:
                    item.setToolTip(row[2])
                self.passwords_list.addItem(item)
            # Connect double-click to view password details
            self.passwords_list.itemDoubleClicked.connect(self.view_password_details)
        except Exception as e:
            print(f"Error loading passwords: {str(e)}")
    def filter_passwords(self):
        """Filters passwords based on search text"""
        search_text = self.search_input.text().lower()
        for i in range(self.passwords_list.count()):
            item = self.passwords_list.item(i)
            item.setHidden(search_text not in item.text().lower())
    # -----------------------------------------------------------------
    # CRUD operations (manual UI dialogs)
    # -----------------------------------------------------------------

    def add_password(self):
        """Adds a new password"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("Add Password")
            layout = QVBoxLayout(dialog)

            url_input = QLineEdit()
            layout.addWidget(QLabel("URL:"))
            layout.addWidget(url_input)

            username_input = QLineEdit()
            layout.addWidget(QLabel("Username:"))
            layout.addWidget(username_input)

            # Password field with show/hide toggle
            password_layout = QHBoxLayout()
            password_input = QLineEdit()
            password_input.setEchoMode(QLineEdit.Password)
            password_layout.addWidget(password_input)

            show_password_btn = QPushButton("👁️")
            show_password_btn.setFixedSize(32, 32)
            show_password_btn.setCheckable(True)
            show_password_btn.toggled.connect(
                lambda checked: password_input.setEchoMode(
                    QLineEdit.Normal if checked else QLineEdit.Password
                )
            )
            password_layout.addWidget(show_password_btn)

            layout.addWidget(QLabel("Password:"))
            layout.addLayout(password_layout)

            notes_input = QLineEdit()
            layout.addWidget(QLabel("Notes:"))
            layout.addWidget(notes_input)

            # Buttons
            buttons_layout = QHBoxLayout()
            save_button = QPushButton("Save")
            save_button.clicked.connect(dialog.accept)
            cancel_button = QPushButton("Cancel")
            cancel_button.clicked.connect(dialog.reject)
            buttons_layout.addWidget(save_button)
            buttons_layout.addWidget(cancel_button)
            layout.addLayout(buttons_layout)

            if dialog.exec():
                cursor = self.conn.cursor()
                cursor.execute(
                    "INSERT INTO passwords (url, username, password, notes) VALUES (?, ?, ?, ?)",
                    (url_input.text(), username_input.text(), password_input.text(), notes_input.text())
                )
                self.conn.commit()
                self.load_passwords()
                self.password_saved.emit(url_input.text(), username_input.text())
        except Exception as e:
            print(f"Error adding password: {str(e)}")
    def edit_password(self):
        """Edits an existing password"""
        try:
            current_item = self.passwords_list.currentItem()
            if not current_item:
                return
            url, username = current_item.text().split(" - ")

            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT password, notes FROM passwords WHERE url = ? AND username = ?",
                (url, username)
            )
            row = cursor.fetchone()
            if not row:
                return
            dialog = QDialog(self)
            dialog.setWindowTitle("Edit Password")
            layout = QVBoxLayout(dialog)

            url_input = QLineEdit(url)
            layout.addWidget(QLabel("URL:"))
            layout.addWidget(url_input)

            username_input = QLineEdit(username)
            layout.addWidget(QLabel("Username:"))
            layout.addWidget(username_input)

            password_layout = QHBoxLayout()
            password_input = QLineEdit(row[0])
            password_input.setEchoMode(QLineEdit.Password)
            password_layout.addWidget(password_input)

            show_password_btn = QPushButton("👁️")
            show_password_btn.setFixedSize(32, 32)
            show_password_btn.setCheckable(True)
            show_password_btn.toggled.connect(
                lambda checked: password_input.setEchoMode(
                    QLineEdit.Normal if checked else QLineEdit.Password
                )
            )
            password_layout.addWidget(show_password_btn)

            layout.addWidget(QLabel("Password:"))
            layout.addLayout(password_layout)

            notes_input = QLineEdit(row[1] if row[1] else "")
            layout.addWidget(QLabel("Notes:"))
            layout.addWidget(notes_input)

            buttons_layout = QHBoxLayout()
            save_button = QPushButton("Save")
            save_button.clicked.connect(dialog.accept)
            cancel_button = QPushButton("Cancel")
            cancel_button.clicked.connect(dialog.reject)
            buttons_layout.addWidget(save_button)
            buttons_layout.addWidget(cancel_button)
            layout.addLayout(buttons_layout)

            if dialog.exec():
                cursor.execute(
                    "UPDATE passwords SET url = ?, username = ?, password = ?, notes = ?, "
                    "updated_at = CURRENT_TIMESTAMP WHERE url = ? AND username = ?",
                    (url_input.text(), username_input.text(), password_input.text(),
                     notes_input.text(), url, username)
                )
                self.conn.commit()
                self.load_passwords()
                self.password_updated.emit(url_input.text(), username_input.text())
        except Exception as e:
            print(f"Error editing password: {str(e)}")
    def view_password_details(self, item):
        """View password details with show/hide toggle"""
        try:
            url, username = item.text().split(" - ")

            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT password, notes FROM passwords WHERE url = ? AND username = ?",
                (url, username)
            )
            row = cursor.fetchone()
            if not row:
                return
            dialog = QDialog(self)
            dialog.setWindowTitle("Password Details")
            layout = QVBoxLayout(dialog)

            layout.addWidget(QLabel(f"<b>URL:</b> {url}"))
            layout.addWidget(QLabel(f"<b>Username:</b> {username}"))

            password_layout = QHBoxLayout()
            password_input = QLineEdit(row[0])
            password_input.setEchoMode(QLineEdit.Password)
            password_input.setReadOnly(True)
            password_layout.addWidget(password_input)

            show_password_btn = QPushButton("👁️")
            show_password_btn.setFixedSize(32, 32)
            show_password_btn.setCheckable(True)
            show_password_btn.toggled.connect(
                lambda checked: password_input.setEchoMode(
                    QLineEdit.Normal if checked else QLineEdit.Password
                )
            )
            password_layout.addWidget(show_password_btn)

            copy_password_btn = QPushButton("📋")
            copy_password_btn.setFixedSize(32, 32)
            copy_password_btn.setToolTip("Copy password to clipboard")
            copy_password_btn.clicked.connect(
                lambda: QApplication.clipboard().setText(row[0])
            )
            password_layout.addWidget(copy_password_btn)

            layout.addWidget(QLabel("<b>Password:</b>"))
            layout.addLayout(password_layout)

            if row[1]:
                layout.addWidget(QLabel(f"<b>Notes:</b> {row[1]}"))
            close_button = QPushButton("Close")
            close_button.clicked.connect(dialog.accept)
            layout.addWidget(close_button)

            dialog.exec()
        except Exception as e:
            print(f"Error viewing password details: {str(e)}")
    def remove_password(self):
        """Removes a password"""
        try:
            current_item = self.passwords_list.currentItem()
            if not current_item:
                return
            url, username = current_item.text().split(" - ")

            reply = QMessageBox.question(
                self,
                "Confirm removal",
                f"Are you sure you want to remove the password for {url}?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                cursor = self.conn.cursor()
                cursor.execute(
                    "DELETE FROM passwords WHERE url = ? AND username = ?",
                    (url, username)
                )
                self.conn.commit()
                self.load_passwords()
                self.password_deleted.emit(url)
        except Exception as e:
            print(f"Error removing password: {str(e)}")
    # -----------------------------------------------------------------
    # Password generator dialog
    # -----------------------------------------------------------------

    def show_generator(self):
        """Shows the password generator"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("Password Generator")
            layout = QVBoxLayout(dialog)

            options_group = QGroupBox("Options")
            options_layout = QVBoxLayout()

            length_layout = QHBoxLayout()
            length_layout.addWidget(QLabel("Length:"))
            length_input = QLineEdit()
            length_input.setPlaceholderText("Enter length (8-10,000,000)")
            length_input.setValidator(QIntValidator(8, 10_000_000))
            length_input.setText("16")
            length_layout.addWidget(length_input)
            options_layout.addLayout(length_layout)

            numbers_check = QCheckBox("Include numbers")
            numbers_check.setChecked(True)
            options_layout.addWidget(numbers_check)

            uppercase_check = QCheckBox("Include uppercase")
            uppercase_check.setChecked(True)
            options_layout.addWidget(uppercase_check)

            lowercase_check = QCheckBox("Include lowercase")
            lowercase_check.setChecked(True)
            options_layout.addWidget(lowercase_check)

            special_check = QCheckBox("Include special characters")
            special_check.setChecked(True)
            options_layout.addWidget(special_check)

            options_group.setLayout(options_layout)
            layout.addWidget(options_group)

            result_group = QGroupBox("Result")
            result_layout = QVBoxLayout()

            password_input = QLineEdit()
            password_input.setReadOnly(True)
            result_layout.addWidget(password_input)

            stats_label = QLabel()
            result_layout.addWidget(stats_label)

            result_group.setLayout(result_layout)
            layout.addWidget(result_group)

            buttons_layout = QHBoxLayout()

            generate_button = QPushButton("Generate")
            def generate():
                try:
                    length = int(length_input.text())
                    if length < 8 or length > 10_000_000:
                        raise ValueError("Length must be between 8 and 10,000,000 characters")
                    result = self.password_generator.generate_password(
                        length=length,
                        include_numbers=numbers_check.isChecked(),
                        include_uppercase=uppercase_check.isChecked(),
                        include_lowercase=lowercase_check.isChecked(),
                        include_special=special_check.isChecked()
                    )
                    password_input.setText(result["password"])
                    stats_label.setText(
                        f"Time: {result['time']}\n"
                        f"CPU: {result['cpu_usage']}\n"
                        f"RAM: {result['ram_usage']}"
                    )
                except Exception as e:
                    QMessageBox.critical(dialog, "Error", str(e))
            generate_button.clicked.connect(generate)
            buttons_layout.addWidget(generate_button)

            copy_button = QPushButton("Copy")
            copy_button.clicked.connect(lambda: QApplication.clipboard().setText(password_input.text()))
            buttons_layout.addWidget(copy_button)

            close_button = QPushButton("Close")
            close_button.clicked.connect(dialog.accept)
            buttons_layout.addWidget(close_button)

            layout.addLayout(buttons_layout)
            generate()
            dialog.exec()
        except Exception as e:
            print(f"Error showing generator: {str(e)}")
    # -----------------------------------------------------------------
    # Encryption
    # -----------------------------------------------------------------

    def setup_encryption(self):
        try:
            if not self.settings.contains("encryption_key"):
                key = Fernet.generate_key()
                self.settings.setValue("encryption_key", key.decode())
            self.fernet = Fernet(self.settings.value("encryption_key").encode())
        except Exception as e:
            print(f"Error setting up encryption: {str(e)}")
    # -----------------------------------------------------------------
    # Encrypted CRUD (used by browser integration / autofill)
    # -----------------------------------------------------------------

    def save_password(self, url, username, password):
        """Save or insert a credential (encrypts password)."""
        try:
            encrypted_password = self.fernet.encrypt(password.encode())
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO passwords (url, username, password)
                VALUES (?, ?, ?)
            ''', (url, username, encrypted_password.decode()))
            conn.commit()
            conn.close()
            print(f"Password saved for {url}")
            self.load_passwords()
            return True
        except Exception as e:
            print(f"Error saving password: {str(e)}")
            return False
    def update_password(self, origin, username, new_password):
        """Update only the password for an existing credential."""
        try:
            encrypted_password = self.fernet.encrypt(new_password.encode())
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE passwords SET password = ?, updated_at = CURRENT_TIMESTAMP
                WHERE url = ? AND username = ?
            ''', (encrypted_password.decode(), origin, username))
            conn.commit()
            conn.close()
            print(f"Password updated for {origin} / {username}")
            self.load_passwords()
            return True
        except Exception as e:
            print(f"Error updating password: {str(e)}")
            return False
    def get_password(self, url, username):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT password FROM passwords
                WHERE url = ? AND username = ?
            ''', (url, username))
            result = cursor.fetchone()
            conn.close()
            if result:
                decrypted_password = self.fernet.decrypt(result[0].encode())
                return decrypted_password.decode()
            return None
        except Exception as e:
            print(f"Error getting password: {str(e)}")
            return None
    def get_all_passwords(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT url, username, password FROM passwords')
            results = cursor.fetchall()
            conn.close()
            passwords = []
            for url, username, encrypted_password in results:
                try:
                    decrypted_password = self.fernet.decrypt(encrypted_password.encode())
                    passwords.append({
                        'url': url,
                        'username': username,
                        'password': decrypted_password.decode()
                    })
                except Exception:
                    continue
            return passwords
        except Exception as e:
            print(f"Error getting all passwords: {str(e)}")
            return []
    def get_credentials_for_origin(self, origin: str) -> list:
        """Return list of {username, password} dicts for a given origin."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                'SELECT username, password FROM passwords WHERE url = ?',
                (origin,)
            )
            results = cursor.fetchall()
            conn.close()
            creds = []
            for username, encrypted_password in results:
                try:
                    decrypted = self.fernet.decrypt(encrypted_password.encode()).decode()
                    creds.append({"username": username, "password": decrypted})
                except Exception:
                    continue
            return creds
        except Exception as e:
            print(f"Error getting credentials for origin: {str(e)}")
            return []
    def delete_password(self, url, username):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM passwords
                WHERE url = ? AND username = ?
            ''', (url, username))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting password: {str(e)}")
            return False
    # -----------------------------------------------------------------
    # Phase C: Credential comparison logic
    # -----------------------------------------------------------------

    def compare_credentials(self, origin: str, username: str, password: str):
        """Compare incoming credentials against stored ones.

        Returns:
            tuple: (action, stored_password)
            action is one of:
                "new"    – no credential stored for this origin+username
                "same"   – identical credential already stored
                "update" – same origin+username but different password
        """
        stored_pw = self.get_password(origin, username)
        if stored_pw is None:
            return ("new", None)
        if stored_pw == password:
            return ("same", stored_pw)
        return ("update", stored_pw)
    # -----------------------------------------------------------------
    # Phase B: Banner-based credential handling (non-blocking)
    # -----------------------------------------------------------------

    def _on_credentials_captured(self, origin: str, username: str, password: str):
        """Central handler called when JS detects a form submission."""
        try:
            if not username or not password:
                return
            # Skip if this origin was dismissed this session
            if origin in self._dismissed_origins:
                return
            action, _stored = self.compare_credentials(origin, username, password)

            if action == "same":
                # Credentials unchanged, do nothing
                return
            # Show banner
            self._show_save_banner(origin, username, password, is_update=(action == "update"))
        except Exception as e:
            print(f"Error handling captured credentials: {str(e)}")
    def _show_save_banner(self, origin: str, username: str, password: str, is_update: bool):
        """Show (or replace) the non-intrusive save banner."""
        try:
            # Remove existing banner if any
            if self._active_banner is not None:
                try:
                    self._active_banner.deleteLater()
                except RuntimeError:
                    pass
                self._active_banner = None
            # Find the main window to insert the banner
            main_win = self._find_main_window()
            if main_win is None:
                # Fallback: just save directly
                self.save_password(origin, username, password)
                return
            banner = PasswordSaveBanner(origin, username, password,
                                        is_update=is_update, parent=None)
            self._active_banner = banner

            # Connect signals
            def on_accepted():
                if is_update:
                    self.update_password(origin, username, password)
                    self.password_updated.emit(origin, username)
                else:
                    self.save_password(origin, username, password)
                    self.password_saved.emit(origin, username)
                self._active_banner = None
            def on_dismissed():
                self._dismissed_origins.add(origin)
                self._active_banner = None
            banner.accepted.connect(on_accepted)
            banner.dismissed.connect(on_dismissed)

            # Insert banner into main_layout below nav_bar
            self._insert_banner_in_layout(main_win, banner)
        except Exception as e:
            print(f"Error showing save banner: {str(e)}")
    def _find_main_window(self):
        """Walk the parent chain to find the QMainWindow."""
        widget = self.parent
        while widget is not None:
            if hasattr(widget, 'centralWidget'):
                return widget
            widget = getattr(widget, 'parent', None)
            if callable(widget):
                widget = widget()
        return None
    def _insert_banner_in_layout(self, main_win, banner):
        """Insert the banner below the nav bar in the main layout."""
        try:
            central = main_win.centralWidget()
            if central is None:
                banner.setParent(main_win)
                banner.show()
                return
            layout = central.layout()
            if layout is None:
                banner.setParent(main_win)
                banner.show()
                return
            # Insert at index 1 (after nav_bar at index 0, before find_bar)
            # But find_bar may be at index 1, so insert at 1 to push it down
            layout.insertWidget(1, banner)
            banner.show()
        except Exception as e:
            print(f"Error inserting banner: {str(e)}")
            banner.setParent(main_win)
            banner.show()
    # -----------------------------------------------------------------
    # Legacy show_password_dialog — redirects to banner
    # -----------------------------------------------------------------

    def show_password_dialog(self, url, username, password):
        """Legacy entry point — now uses the non-intrusive banner."""
        origin = _normalize_origin(url)
        self._on_credentials_captured(origin, username, password)
    def show_passwords_dialog(self):
        try:
            dialog = QDialog(self.parent)
            dialog.setWindowTitle("Saved Passwords")
            dialog.setMinimumSize(600, 400)

            layout = QVBoxLayout()

            table = QTableWidget()
            table.setColumnCount(3)
            table.setHorizontalHeaderLabels(["URL", "Username", "Password"])
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

            passwords = self.get_all_passwords()
            table.setRowCount(len(passwords))
            for i, pwd in enumerate(passwords):
                table.setItem(i, 0, QTableWidgetItem(pwd['url']))
                table.setItem(i, 1, QTableWidgetItem(pwd['username']))
                table.setItem(i, 2, QTableWidgetItem(pwd['password']))
            layout.addWidget(table)

            buttons = QDialogButtonBox(QDialogButtonBox.Close)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)

            dialog.setLayout(layout)
            dialog.exec()
        except Exception as e:
            print(f"Error showing passwords dialog: {str(e)}")
    # -----------------------------------------------------------------
    # Cleanup
    # -----------------------------------------------------------------

    def closeEvent(self, event):
        try:
            if hasattr(self, 'conn'):
                self.conn.close()
        except Exception as e:
            print(f"Error closing connection: {str(e)}")
        finally:
            super().closeEvent(event)
    def cleanup_browser(self, browser):
        """Disconnect signals when a tab is closed."""
        try:
            browser_id = id(browser)
            if browser_id in self._browser_connections:
                for signal, slot in self._browser_connections.pop(browser_id):
                    try:
                        signal.disconnect(slot)
                    except (RuntimeError, TypeError):
                        pass
                print(f"[PasswordManager] Cleaned up browser {browser_id}")
        except Exception as e:
            print(f"Error cleaning up browser: {str(e)}")
    # -----------------------------------------------------------------
    # Browser integration — NO QWebChannel, uses runJavaScript + signals
    # -----------------------------------------------------------------

    def setup_browser(self, browser):
        """Connect signals and prepare credential capture for this browser."""
        try:
            if not browser or not hasattr(browser, 'page'):
                return
            browser_id = id(browser)
            if browser_id in self._browser_connections:
                return  # already set up
            connections = []

            # On page load finished → inject capture JS + attempt autofill
            def on_load_finished(ok, b=browser):
                if ok:
                    self._inject_capture_script(b)
                    self._attempt_autofill(b)
            browser.loadFinished.connect(on_load_finished)
            connections.append((browser.loadFinished, on_load_finished))

            # On URL change → check for captured credentials from previous page
            def on_url_changed(url, b=browser):
                self._check_captured_credentials(b)
            browser.urlChanged.connect(on_url_changed)
            connections.append((browser.urlChanged, on_url_changed))

            self._browser_connections[browser_id] = connections
            print(f"[PasswordManager] Browser configured (browser {browser_id})")
        except Exception as e:
            print(f"Error setting up browser: {str(e)}")
    def _inject_capture_script(self, browser):
        """Inject the credential capture JS into the current page."""
        try:
            browser.page().runJavaScript(_CAPTURE_JS)
        except Exception as e:
            print(f"[PasswordManager] Error injecting capture script: {e}")
    def _check_captured_credentials(self, browser):
        """Read captured credentials from JS and process them."""
        try:
            def handle_result(result):
                if result is None:
                    return
                try:
                    if isinstance(result, str):
                        data = json.loads(result)
                    else:
                        return
                    origin = data.get("origin", "")
                    username = data.get("username", "")
                    password = data.get("password", "")
                    if origin and username and password:
                        print(f"[PasswordManager] Credentials captured for {origin} / {username}")
                        self._on_credentials_captured(origin, username, password)
                except (json.JSONDecodeError, AttributeError):
                    pass
            browser.page().runJavaScript(_READ_CRED_JS, handle_result)
        except Exception as e:
            print(f"[PasswordManager] Error checking credentials: {e}")
    def _attempt_autofill(self, browser):
        """Inject stored credentials into login forms on the current page."""
        try:
            current_url = browser.url().toString()
            origin = _normalize_origin(current_url)
            creds = self.get_credentials_for_origin(origin)
            if not creds:
                return
            # Build autofill JS
            creds_json = json.dumps(creds)
            autofill_js = '''
            (function() {
                var creds = ''' + creds_json + ''';
                if (!creds || creds.length === 0) return;

                function isUsernameField(input) {
                    if (!input || input.type === 'hidden') return false;
                    var type = (input.type || '').toLowerCase();
                    if (type === 'password' || type === 'submit' || type === 'button' ||
                        type === 'checkbox' || type === 'radio' || type === 'file') return false;
                    if (type === 'email') return true;
                    var attrs = [(input.name||''), (input.id||''),
                                 (input.placeholder||''), (input.autocomplete||''),
                                 (input.getAttribute('aria-label')||'')].join(' ').toLowerCase();
                    var positives = ['user','email','login','account','nick','identifier',
                                     'phone','mobile','correo','usuario','nombre'];
                    for (var i = 0; i < positives.length; i++) {
                        if (attrs.indexOf(positives[i]) !== -1) return true;
                    }
                    return false;
                }

                function findFields() {
                    var inputs = document.querySelectorAll('input');
                    var pwField = null, userField = null;
                    for (var i = 0; i < inputs.length; i++) {
                        if ((inputs[i].type||'').toLowerCase() === 'password') {
                            pwField = inputs[i]; break;
                        }
                    }
                    if (!pwField) return null;
                    var allInputs = Array.prototype.slice.call(inputs);
                    var pwIdx = allInputs.indexOf(pwField);
                    for (var j = pwIdx - 1; j >= 0; j--) {
                        if (isUsernameField(allInputs[j])) { userField = allInputs[j]; break; }
                    }
                    if (!userField) {
                        for (var k = 0; k < allInputs.length; k++) {
                            if (isUsernameField(allInputs[k])) { userField = allInputs[k]; break; }
                        }
                    }
                    return { username: userField, password: pwField };
                }

                function setVal(el, value) {
                    try {
                        var s = Object.getOwnPropertyDescriptor(
                            window.HTMLInputElement.prototype, 'value').set;
                        s.call(el, value);
                        el.dispatchEvent(new Event('input', {bubbles:true}));
                        el.dispatchEvent(new Event('change', {bubbles:true}));
                    } catch(e) { el.value = value; }
                }

                function fill(fields, cred) {
                    if (fields.username && cred.username) setVal(fields.username, cred.username);
                    if (fields.password && cred.password) setVal(fields.password, cred.password);
                }

                var fields = findFields();
                if (!fields || !fields.password) return;
                if (fields.password.value) return; // already filled

                fill(fields, creds[0]);
            })();
            '''
            browser.page().runJavaScript(autofill_js)
            print(f"[PasswordManager] Autofill injected for {origin}")
        except Exception as e:
            print(f"[PasswordManager] Error in autofill: {e}")
