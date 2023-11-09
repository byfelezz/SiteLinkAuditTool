import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLineEdit, QVBoxLayout, QWidget, QLabel, QTextEdit
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QIcon
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from requests.exceptions import RequestException

# Worker Thread
class Worker(QThread):
    signal = pyqtSignal(str)  # Signal to emit the status

    def __init__(self, url):
        super(Worker, self).__init__()
        self.url = url

    def run(self):
        links = self.find_links(self.url)
        if links:
            self.check_links(links)

    def find_links(self, url):
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            links = soup.find_all("a")
            return links
        except RequestException as e:
            self.signal.emit(f"Error: {url} - {e}")
            return []

    def check_links(self, links):
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_url = {executor.submit(self.fetch_status, link.get('href')): link for link in links}
            for future in future_to_url:
                url = future_to_url[future].get('href')
                try:
                    status = future.result()
                    self.signal.emit(f"{url} - Status: {status}")
                except RequestException as e:
                    self.signal.emit(f"Error: {url} - {e}")

    def fetch_status(self, url):
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return response.status_code
        except RequestException as e:
            raise

# Main Window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('SiteLinkAuditTool')
        script_dir = os.path.dirname(os.path.realpath(__file__))
        icon_path = os.path.join(script_dir, 'byfelez.png')
        self.setWindowIcon(QIcon(icon_path))

        layout = QVBoxLayout()

        self.url_input = QLineEdit(self)
        self.url_input.setPlaceholderText('Please enter a URL...')
        layout.addWidget(self.url_input)

        self.check_button = QPushButton('Check Links', self)
        self.check_button.clicked.connect(self.on_check)
        layout.addWidget(self.check_button)

        self.result_area = QTextEdit(self)
        self.result_area.setReadOnly(True)
        layout.addWidget(self.result_area)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def on_check(self):
        url = self.url_input.text()
        self.check_button.setEnabled(False)
        self.result_area.clear()

        self.worker = Worker(url)
        self.worker.signal.connect(self.on_finished)
        self.worker.start()

    def on_finished(self, message):
        self.result_area.append(message)
        self.check_button.setEnabled(True)

# PyQt5 Application Initialization
app = QApplication(sys.argv)
main_window = MainWindow()
main_window.show()
sys.exit(app.exec_())