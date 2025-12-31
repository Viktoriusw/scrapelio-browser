from datetime import datetime

from PySide6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QLabel



class HistoryManager:

    def __init__(self):

        self.history = []



    def record_history(self, url):

        self.history.append({"url": url.toString(), "timestamp": datetime.now()})



    def show_history(self, tab_manager):

        dialog = QDialog()

        dialog.setWindowTitle("History")

        dialog.resize(600, 400)



        layout = QVBoxLayout()

        label = QLabel("History:")

        layout.addWidget(label)



        history_list = QListWidget()

        for entry in self.history:

            history_list.addItem(f"{entry['url']} - {entry['timestamp']}")

        history_list.itemClicked.connect(lambda item: tab_manager.add_new_tab(item.text().split(' - ')[0]))

        layout.addWidget(history_list)



        dialog.setLayout(layout)

        dialog.exec_()
    
    def clear_history(self):
        """Limpiar todo el historial de navegación"""
        self.history.clear()
        print("[HistoryManager] Historial limpiado")

