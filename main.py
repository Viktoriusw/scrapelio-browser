import sys


import socket


import traceback


from threading import Thread, Event


from PySide6.QtWidgets import QApplication


# Import MainWindow from ui module file (not ui package)
import os
# Ensure we import from ui.py file, not ui/ directory
sys.path.insert(0, os.path.dirname(__file__))
import importlib.util
spec = importlib.util.spec_from_file_location("ui_module", os.path.join(os.path.dirname(__file__), "ui.py"))
ui_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ui_module)
MainWindow = ui_module.MainWindow





# Global exception handling before any initialization


def exception_handler(type, value, tb):


    print("Uncaught global exception:")


    print("".join(traceback.format_exception(type, value, tb)))





sys.excepthook = exception_handler





class BookmarkListener(Thread):


    def __init__(self, navigation_manager):


        super().__init__()


        self.navigation_manager = navigation_manager


        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)


        self.server_socket.bind(("localhost", 65432))


        self.server_socket.settimeout(1)  # Timeout to allow checking the exit flag


        self.server_socket.listen(1)


        self._stop_event = Event()  # Event to control thread stopping


        self.daemon = True  # Daemon thread to terminate with main program





    def run(self):


        while not self._stop_event.is_set():


            try:


                client_socket, _ = self.server_socket.accept()


                with client_socket:


                    url = client_socket.recv(1024).decode("utf-8").strip()


                    if url:


                        print(f"URL received: {url}")


                        try:


                            self.navigation_manager.navigate_to_url(url)


                        except Exception as e:


                            print(f"Error handling URL: {e}")


            except socket.timeout:


                continue  # Normal timeout to check stop_event


            except Exception as e:


                if not self._stop_event.is_set():


                    print(f"Error in BookmarkListener: {e}")


                    traceback.print_exc()





    def stop(self):


        """Safely stops the thread"""


        self._stop_event.set()


        try:


            # Temporary connection to unblock accept()


            temp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


            temp_socket.connect(("localhost", 65432))


            temp_socket.close()


        except Exception:


            pass


        if self.is_alive():


            self.join(timeout=2)


        try:


            self.server_socket.close()


        except Exception:


            pass





def main():


    app = QApplication(sys.argv)
    
    # Configurar nombre de la aplicación para QStandardPaths
    app.setApplicationName("Scrapelio")
    app.setOrganizationName("Scrapelio")


    window = MainWindow()


    # Start socket listener for URLs after verifying navigation_manager exists


    bookmark_listener = None


    if hasattr(window, 'navigation_manager') and window.navigation_manager:


        bookmark_listener = BookmarkListener(window.navigation_manager)


        bookmark_listener.start()


    else:


        print("Warning: Navigation manager not available, socket listener disabled")


    window.show()


    try:


        exit_code = app.exec()


    except Exception as e:


        print(f"Application error: {e}")


        traceback.print_exc()


        exit_code = 1


    finally:


        if bookmark_listener:


            bookmark_listener.stop()


    sys.exit(exit_code)





if __name__ == "__main__":


    main()