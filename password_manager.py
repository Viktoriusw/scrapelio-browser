from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 

                              QLabel, QLineEdit, QListWidget, QListWidgetItem,

                              QDialog, QMessageBox, QInputDialog, QCheckBox,

                              QSpinBox, QComboBox, QGroupBox, QApplication,

                              QTableWidget, QTableWidgetItem, QHeaderView,

                              QDialogButtonBox)

from PySide6.QtCore import Qt, QSettings, Signal, QUrl, QObject, Slot

from PySide6.QtGui import QIcon, QIntValidator

from PySide6.QtWebEngineCore import QWebEngineScript

from PySide6.QtWebEngineWidgets import QWebEngineView

from PySide6.QtWebChannel import QWebChannel

import json

import base64

from cryptography.fernet import Fernet

from cryptography.hazmat.primitives import hashes

from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

import os

import sqlite3

from datetime import datetime

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



class PasswordBridge(QObject):

    def __init__(self, parent):

        super().__init__()

        self.parent = parent



    @Slot(str, str, str)

    def saveCredentials(self, url, username, password):

        self.parent.show_password_dialog(url, username, password)



class PasswordManager(QWidget):

    password_saved = Signal(str, str)  # url, username

    password_updated = Signal(str, str)  # url, username

    password_deleted = Signal(str)  # url



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

        self._webchannels = {}



    def init_ui(self):

        """Initializes the user interface"""

        layout = QVBoxLayout(self)

        

        # Use global theme (no hardcoded styles)

        # Colors are now inherited from the theme in ui.py

        

        # Search bar

        search_layout = QHBoxLayout()

        self.search_input = QLineEdit()

        self.search_input.setPlaceholderText("Search passwords...")

        self.search_input.setFixedHeight(32)  # Consistent height

        if hasattr(self.search_input, "setClearButtonEnabled"):

            self.search_input.setClearButtonEnabled(True)

        self.search_input.textChanged.connect(self.filter_passwords)

        search_layout.addWidget(self.search_input)

        layout.addLayout(search_layout)

        

        # Password list

        self.passwords_list = QListWidget()

        self.passwords_list.setToolTip("Double-click to view password details")

        # Remove hardcoded styles to inherit global theme

        layout.addWidget(self.passwords_list)

        

        # Action buttons

        buttons_layout = QHBoxLayout()

        

        self.add_button = QPushButton("Add")

        self.add_button.clicked.connect(self.add_password)

        buttons_layout.addWidget(self.add_button)

        

        self.view_button = QPushButton("View")

        self.view_button.clicked.connect(lambda: self.view_password_details(self.passwords_list.currentItem()) if self.passwords_list.currentItem() else None)

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



    def add_password(self):

        """Adds a new password"""

        try:

            dialog = QDialog(self)

            dialog.setWindowTitle("Add Password")

            layout = QVBoxLayout(dialog)

            

            # Fields

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

            

            # Fields

            url_input = QLineEdit(url)

            layout.addWidget(QLabel("URL:"))

            layout.addWidget(url_input)

            

            username_input = QLineEdit(username)

            layout.addWidget(QLabel("Username:"))

            layout.addWidget(username_input)

            

            # Password field with show/hide toggle

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

                cursor.execute(

                    "UPDATE passwords SET url = ?, username = ?, password = ?, notes = ?, updated_at = CURRENT_TIMESTAMP WHERE url = ? AND username = ?",

                    (url_input.text(), username_input.text(), password_input.text(), notes_input.text(), url, username)

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

            

            # Display fields (read-only)

            layout.addWidget(QLabel(f"<b>URL:</b> {url}"))

            layout.addWidget(QLabel(f"<b>Username:</b> {username}"))

            

            # Password field with show/hide toggle

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

            

            # Close button

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



    def show_generator(self):

        """Shows the password generator"""

        try:

            dialog = QDialog(self)

            dialog.setWindowTitle("Password Generator")

            # Remove hardcoded styles to inherit global theme

            layout = QVBoxLayout(dialog)

            

            # Generation options

            options_group = QGroupBox("Options")

            options_layout = QVBoxLayout()

            

            length_layout = QHBoxLayout()

            length_layout.addWidget(QLabel("Length:"))

            length_input = QLineEdit()

            length_input.setPlaceholderText("Enter length (8-10,000,000)")

            length_input.setValidator(QIntValidator(8, 10_000_000))

            length_input.setText("16")  # Default value

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

            

            # Generated password

            result_group = QGroupBox("Result")

            result_layout = QVBoxLayout()

            

            password_input = QLineEdit()

            password_input.setReadOnly(True)

            result_layout.addWidget(password_input)

            

            stats_label = QLabel()

            result_layout.addWidget(stats_label)

            

            result_group.setLayout(result_layout)

            layout.addWidget(result_group)

            

            # Buttons

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

            

            # Generate first password

            generate()

            

            dialog.exec()

            

        except Exception as e:

            print(f"Error showing generator: {str(e)}")



    def setup_encryption(self):

        try:

            # Generate or load encryption key

            if not self.settings.contains("encryption_key"):

                key = Fernet.generate_key()

                self.settings.setValue("encryption_key", key.decode())

            self.fernet = Fernet(self.settings.value("encryption_key").encode())

        except Exception as e:

            print(f"Error setting up encryption: {str(e)}")



    def save_password(self, url, username, password):

        try:

            # Encrypt the password

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

            return True

        except Exception as e:

            print(f"Error saving password: {str(e)}")

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

                # Decrypt the password

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

                except:

                    continue

            return passwords

        except Exception as e:

            print(f"Error getting all passwords: {str(e)}")

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



    def show_password_dialog(self, url, username, password):

        try:

            dialog = QDialog(self.parent)

            dialog.setWindowTitle("Save Password")

            layout = QVBoxLayout()

            

            # Display information

            layout.addWidget(QLabel(f"Save password for {url}?"))

            layout.addWidget(QLabel(f"Username: {username}"))

            

            # Buttons

            buttons = QDialogButtonBox(

                QDialogButtonBox.Save | QDialogButtonBox.Cancel

            )

            buttons.accepted.connect(lambda: self.save_password(url, username, password))

            buttons.accepted.connect(dialog.accept)

            buttons.rejected.connect(dialog.reject)

            layout.addWidget(buttons)

            

            dialog.setLayout(layout)

            dialog.exec()

        except Exception as e:

            print(f"Error showing password dialog: {str(e)}")



    def show_passwords_dialog(self):

        try:

            dialog = QDialog(self.parent)

            dialog.setWindowTitle("Saved Passwords")

            dialog.setMinimumSize(600, 400)

            

            layout = QVBoxLayout()

            

            # Password table

            table = QTableWidget()

            table.setColumnCount(3)

            table.setHorizontalHeaderLabels(["URL", "Username", "Password"])

            table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

            

            # Populate table

            passwords = self.get_all_passwords()

            table.setRowCount(len(passwords))

            for i, pwd in enumerate(passwords):

                table.setItem(i, 0, QTableWidgetItem(pwd['url']))

                table.setItem(i, 1, QTableWidgetItem(pwd['username']))

                table.setItem(i, 2, QTableWidgetItem(pwd['password']))

            

            layout.addWidget(table)

            

            # Buttons

            buttons = QDialogButtonBox(QDialogButtonBox.Close)

            buttons.rejected.connect(dialog.reject)

            layout.addWidget(buttons)

            

            dialog.setLayout(layout)

            dialog.exec()

        except Exception as e:

            print(f"Error showing passwords dialog: {str(e)}")



    def closeEvent(self, event):

        """Handles widget closing"""

        try:

            if hasattr(self, 'conn'):

                self.conn.close()

        except Exception as e:

            print(f"Error closing connection: {str(e)}")

        finally:

            super().closeEvent(event)



    def setup_browser(self, browser):

        try:

            if browser and hasattr(browser, 'page'):

                # QWebChannel and bridge

                page = browser.page()

                channel = QWebChannel(page)

                bridge = PasswordBridge(self)

                channel.registerObject('passwordBridge', bridge)

                page.setWebChannel(channel)

                self._webchannels[id(page)] = (channel, bridge)



                # QWebChannel script

                qwebchannel_script = '''

                (function() {

                    function QWebChannel(transport, initCallback) {

                        if (typeof transport !== "object" || typeof transport.send !== "function") {

                            console.error("The QWebChannel expects a transport object with a send function and onmessage callback property.");

                            return;

                        }



                        var channel = this;

                        channel.transport = transport;

                        transport.onmessage = function(message) {

                            var data = JSON.parse(message.data);

                            channel.handleMessage(data);

                        }

                        channel.execCallbacks = {};

                        channel.execId = 0;

                        channel.exec = function(data, callback) {

                            if (!callback) {

                                callback = function() {};

                            }

                            channel.execId++;

                            channel.execCallbacks[channel.execId] = callback;

                            data.id = channel.execId;

                            channel.transport.send(JSON.stringify(data));

                        };

                        channel.execWithPromise = function(data) {

                            return new Promise(function(resolve, reject) {

                                channel.exec(data, function(response) {

                                    if (response.error) {

                                        reject(response.error);

                                    } else {

                                        resolve(response.data);

                                    }

                                });

                            });

                        };

                        channel.handleMessage = function(message) {

                            var callback = channel.execCallbacks[message.id];

                            if (callback) {

                                callback(message.data);

                                delete channel.execCallbacks[message.id];

                            }

                        };

                        channel.registerObjects = function(objects) {

                            channel.objects = objects;

                        };

                        channel.registerObject = function(name, object) {

                            if (!channel.objects) {

                                channel.objects = {};

                            }

                            channel.objects[name] = object;

                        };

                        channel.destroy = function() {

                            if (channel.transport) {

                                channel.transport.onmessage = undefined;

                            }

                            for (var i in channel.execCallbacks) {

                                channel.execCallbacks[i]({error: "Channel destroyed"});

                            }

                        };

                        channel.exec({type: "init"}, function(data) {

                            for (var i in data) {

                                var object = new QObject(this, i, data[i], function(name, data) {

                                    channel.exec({type: "invokeMethod", object: name, method: data.method, args: data.args});

                                });

                                channel.objects[i] = object;

                            }

                            if (initCallback) {

                                initCallback(channel);

                            }

                        });

                    }



                    function QObject(webChannel, name, data, callback) {

                        function QObject() {}

                        QObject.prototype = {

                            _id: name,

                            _webChannel: webChannel,

                            _data: data,

                            _callback: callback,

                            _signals: {},

                            _propertyUpdateVersion: {},

                            _methodReturnValues: {},

                            _invokableProperties: data.invokableProperties,

                            _invokableMethods: data.invokableMethods,

                            _propertyUpdateVersionTimeout: 0,

                            _notifyAboutNewProperties: false,

                            _signalEmitted: signalEmitted,

                            _invokeMethod: invokeMethod,

                            _connectNotify: connectNotify,

                            _disconnectNotify: disconnectNotify

                        };

                        return new QObject();

                    }



                    function signalEmitted(signalName, signalData) {

                        var signal = this._signals[signalName];

                        if (signal) {

                            signal.emit(signalData);

                        }

                    }



                    function invokeMethod(methodName, args) {

                        return this._callback(this._id, {method: methodName, args: args});

                    }



                    function connectNotify(signalName, callback) {

                        if (!this._signals[signalName]) {

                            this._signals[signalName] = new Signal();

                        }

                        this._signals[signalName].connect(callback);

                    }



                    function disconnectNotify(signalName, callback) {

                        if (this._signals[signalName]) {

                            this._signals[signalName].disconnect(callback);

                        }

                    }



                    function Signal() {

                        this.connect = function(callback) {

                            if (typeof callback !== "function") {

                                console.error("Signal.connect: Cannot connect to non-function");

                                return;

                            }

                            this.callbacks.push(callback);

                        };

                        this.disconnect = function(callback) {

                            var index = this.callbacks.indexOf(callback);

                            if (index !== -1) {

                                this.callbacks.splice(index, 1);

                            }

                        };

                        this.emit = function(data) {

                            for (var i = 0; i < this.callbacks.length; ++i) {

                                this.callbacks[i](data);

                            }

                        };

                        this.callbacks = [];

                    }



                    window.QWebChannel = QWebChannel;

                })();

                '''



                # Form detection script

                form_script = '''

                (function() {

                    // Function to set up the bridge

                    function setupBridge() {

                        try {

                            if (typeof qt === 'undefined' || !qt.webChannelTransport) {

                                console.error('QWebChannel not available');

                                return;

                            }

                            

                            new QWebChannel(qt.webChannelTransport, function(channel) {

                                window.passwordBridge = channel.objects.passwordBridge;

                                setupFormHandlers();

                            });

                        } catch (e) {

                            console.error('Error setting up bridge:', e);

                        }

                    }



                    // Function to find form fields

                    function findFormFields(form) {

                        var fields = { username: null, password: null };

                        

                        // Search for username field

                        var usernameInputs = form.querySelectorAll('input[type="text"], input[type="email"], input[name*="user"], input[name*="email"], input[id*="user"], input[id*="email"]');

                        for (var i = 0; i < usernameInputs.length; i++) {

                            var input = usernameInputs[i];

                            var name = (input.name || '').toLowerCase();

                            var id = (input.id || '').toLowerCase();

                            var placeholder = (input.placeholder || '').toLowerCase();

                            if (name.includes('user') || name.includes('email') || id.includes('user') || id.includes('email') || placeholder.includes('user') || placeholder.includes('email')) {

                                fields.username = input;

                                break;

                            }

                        }

                        

                        // Search for password field

                        var passwordInputs = form.querySelectorAll('input[type="password"], input[name*="pass"], input[id*="pass"]');

                        if (passwordInputs.length > 0) {

                            fields.password = passwordInputs[0];

                        }

                        

                        return fields;

                    }



                    // Function to set up a form

                    function setupForm(form) {

                        var isLoginForm = false;

                        var formHtml = form.outerHTML.toLowerCase();

                        var formAction = (form.action || '').toLowerCase();

                        var formId = (form.id || '').toLowerCase();

                        var formClass = (form.className || '').toLowerCase();

                        

                        if (formHtml.includes('login') || formHtml.includes('signin') || 

                            formHtml.includes('register') || formHtml.includes('signup') || 

                            formAction.includes('login') || formAction.includes('signin') || 

                            formAction.includes('register') || formAction.includes('signup') || 

                            formId.includes('login') || formId.includes('signin') || 

                            formId.includes('register') || formId.includes('signup') || 

                            formClass.includes('login') || formClass.includes('signin') || 

                            formClass.includes('register') || formClass.includes('signup')) {

                            isLoginForm = true;

                        }

                        

                        var fields = findFormFields(form);

                        if (isLoginForm || (fields.username && fields.password)) {

                            form.removeEventListener('submit', form._submitHandler);

                            form._submitHandler = function(e) {

                                setTimeout(function() {

                                    var fields = findFormFields(form);

                                    if (fields.username && fields.username.value && 

                                        fields.password && fields.password.value) {

                                        if (window.passwordBridge && window.passwordBridge.saveCredentials) {

                                            window.passwordBridge.saveCredentials(

                                                window.location.href,

                                                fields.username.value,

                                                fields.password.value

                                            );

                                        }

                                    }

                                }, 100);

                            };

                            form.addEventListener('submit', form._submitHandler);

                        }

                    }



                    // Function to set up all handlers

                    function setupFormHandlers() {

                        // Set up existing forms

                        document.querySelectorAll('form').forEach(setupForm);



                        // Observe DOM for new forms

                        var observer = new MutationObserver(function(mutations) {

                            mutations.forEach(function(mutation) {

                                if (mutation.addedNodes) {

                                    mutation.addedNodes.forEach(function(node) {

                                        if (node.nodeName === 'FORM') {

                                            setupForm(node);

                                        }

                                    });

                                }

                            });

                        });

                        observer.observe(document.body, { childList: true, subtree: true });



                        // Observe input field changes

                        document.addEventListener('input', function(e) {

                            if (e.target.tagName === 'INPUT') {

                                var form = e.target.form;

                                if (form) {

                                    setupForm(form);

                                }

                            }

                        });

                    }



                    // Wait for the document to be ready

                    if (document.readyState === 'loading') {

                        document.addEventListener('DOMContentLoaded', setupBridge);

                    } else {

                        setupBridge();

                    }

                })();

                '''

                

                # Create and configure scripts

                qwebchannel_script_obj = QWebEngineScript()

                qwebchannel_script_obj.setSourceCode(qwebchannel_script)

                qwebchannel_script_obj.setInjectionPoint(QWebEngineScript.DocumentCreation)

                qwebchannel_script_obj.setWorldId(QWebEngineScript.MainWorld)

                qwebchannel_script_obj.setRunsOnSubFrames(True)



                form_script_obj = QWebEngineScript()

                form_script_obj.setSourceCode(form_script)

                form_script_obj.setInjectionPoint(QWebEngineScript.DocumentCreation)

                form_script_obj.setWorldId(QWebEngineScript.MainWorld)

                form_script_obj.setRunsOnSubFrames(True)

                

                # Ensure scripts run after the page is loaded

                def insert_scripts(ok):

                    if ok:

                        page.scripts().insert(qwebchannel_script_obj)

                        page.scripts().insert(form_script_obj)

                

                page.loadFinished.connect(insert_scripts)

                

                print("Password manager configured correctly")

        except Exception as e:

            print(f"Error setting up browser: {str(e)}") 