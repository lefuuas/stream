import sys
import os
import time
import psutil
import platform
import requests
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QSystemTrayIcon, QMenu,QInputDialog,QHBoxLayout,QStatusBar
)
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QPropertyAnimation, QRect, QTimer
import psutil
import win32gui  
import win32process  
import requests
from collections import defaultdict
from datetime import datetime

SERVER_URL = 'http://localhost:3000'
program_usage = defaultdict(lambda: {'usageTime': 0, 'windows': {}})
last_program_sent = None  # Variável global para armazenar o último programa enviado

class WorkerThread(QThread):
    error_signal = pyqtSignal(str)
    message_signal = pyqtSignal(str)
    command_signal = pyqtSignal(str)

    def __init__(self, token):
        super().__init__()
        self.token = token
        self.running = True

    def run(self):
        while self.running:
            try:
                info = self.get_machine_info()
                resources = self.get_resource_usage()
                self.update_machine(info, resources)
                self.execute_commands()
                self.check_for_messages()
                self.monitor_program_usage()
                time.sleep(5)
            except Exception as e:
                self.error_signal.emit(str(e))
                time.sleep(5)

    def stop(self):
        self.running = False

    def update_machine(self, info, resources):
        try:
            response = requests.post(f'{SERVER_URL}/update', json={
                'token': self.token,
                'info': info,
                'resources': resources,
            })
            if response.status_code != 200:
                raise Exception(f'Erro ao atualizar informações: {response.text}')
        except Exception as e:
            self.error_signal.emit(f"Erro ao enviar dados de máquina: {e}")

    def get_machine_info(self):
        arquitetura = platform.machine()
        so = platform.platform()
        cpus = psutil.cpu_count()
        armazenamento_total = round(psutil.disk_usage('/').total / (1024 ** 3), 1)
        armazenamento_free = round(psutil.disk_usage('/').free / (1024 ** 3), 1)
        memoria_total = round(psutil.virtual_memory().total / (1024 ** 3), 1)
        memoria_disponivel = round(psutil.virtual_memory().available / (1024 ** 3), 1)
        return {
            "arquitetura": arquitetura,
            "sistema_operacional": so,
            "cpus": cpus,
            "armazenamento_total": armazenamento_total,
            "armazenamento_livre": armazenamento_free,
            "memoria_total": memoria_total,
            "memoria_disponivel": memoria_disponivel
        }

    def get_resource_usage(self):
        uso_cpu = psutil.cpu_percent(interval=1)
        uso_memoria = psutil.virtual_memory().percent
        uso_hd = psutil.disk_usage('/').percent
        return {"uso_cpu": uso_cpu, "uso_memoria": uso_memoria, "uso_hd": uso_hd}

    def execute_commands(self):
        try:
            response = requests.get(f'{SERVER_URL}/get-command/{self.token}')
            if response.status_code == 200:
                command = response.text.strip()
                if command:
                    result = os.popen(command).read()
                    self.send_command_result(result)
        except Exception as e:
            self.error_signal.emit(f"Erro ao executar comandos: {e}")

    def send_command_result(self, result):
        try:
            response = requests.post(f'{SERVER_URL}/command-result', json={'token': self.token, 'result': result})
            if response.status_code != 200:
                self.error_signal.emit(f'Erro ao enviar resultado do comando: {response.text}')
            else:
                self.command_signal.emit(f"Comando executado com sucesso: {result[:100]}...")
        except Exception as e:
            self.error_signal.emit(f'Erro ao enviar resultado do comando: {e}')

    def check_for_messages(self):
        try:
            response = requests.get(f'{SERVER_URL}/get-message/{self.token}')
            if response.status_code == 200:
                message = response.text.strip()
                if message:
                    self.message_signal.emit(message)
        except Exception as e:
            self.error_signal.emit(f"Erro ao verificar mensagens: {e}")

    def monitor_program_usage(self):
        active_window_title = self.get_active_window_title()
        active_program = self.get_program_name_from_window()

        if active_program:
            # Define a chave única para o programa ativo e a janela
            key = f"{active_program} - {active_window_title}"

            # Atualiza o uso de tempo para o programa ativo
            program_usage[key]['usageTime'] = 5
            program_usage[key]['windows'][active_window_title] = program_usage[key]['usageTime']

            # Envia os dados do programa ativo
            self.send_program_usage_data(active_program, active_window_title)

    def get_active_window_title(self):
        window = win32gui.GetForegroundWindow()
        return win32gui.GetWindowText(window)

    def get_program_name_from_window(self):
        try:
            window = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(window)
            process_name = psutil.Process(pid).name()
            return process_name
        except Exception as e:
            return None

    def send_program_usage_data(self, active_program, active_window_title):
        try:
            # Formatar os dados para o programa ativo
            formatted_usage = {
                active_program: {
                    'windowTitle': active_window_title,
                    'usageTime': 5
                }
            }

            print(formatted_usage)  # Exibe os dados formatados para depuração

            # Enviar os dados para a API
            response = requests.post(f'{SERVER_URL}/report-usage', json={
                'token': self.token,
                'programUsage': formatted_usage
            })
            if response.status_code != 200:
                print(f"Erro ao enviar dados de uso: {response.text}")
        except Exception as e:
            print(f"Erro ao enviar dados de uso: {e}")

            
class MainWindow(QMainWindow):
    LOGIN_FILE = "login_data.txt"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Monitor de Máquina")
        self.setFixedSize(600, 400)
        self.setWindowIcon(QIcon("icon.png"))
        self.setStyleSheet(self.load_styles())

        self.token = None
        self.worker_thread = None
        self.correct_password = "sousa123"

        # Widget principal
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Layout principal
        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Tray icon
        self.tray_icon = QSystemTrayIcon(QIcon("icon.png"), self)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

        # Menu do tray
        self.tray_menu = QMenu()
        self.restore_action = self.tray_menu.addAction("Restaurar")
        self.restore_action.triggered.connect(self.request_password_and_restore)
        self.about_action = self.tray_menu.addAction("Sobre")
        self.about_action.triggered.connect(self.show_about)
        self.quit_action = self.tray_menu.addAction("Sair")
        self.quit_action.triggered.connect(self.quit_application)
        self.tray_icon.setContextMenu(self.tray_menu)

        # Exibir tray icon
        self.tray_icon.show()

        # Tela inicial
        if os.path.exists(self.LOGIN_FILE):
            with open(self.LOGIN_FILE, "r") as file:
                self.token = file.read().strip()
            if self.token:
                self.worker_thread = WorkerThread(self.token)
                self.worker_thread.start()
                self.setup_main_ui()
            else:
                self.setup_login_ui()
        else:
            self.setup_login_ui()

    def load_styles(self):
        return """
        QMainWindow {
            background-color: #282c34;
        }
        QLabel {
            color: #ffffff;
            font-size: 16px;
            font-weight: bold;
        }
        QLineEdit {
            background-color: #3c3f4a;
            color: #ffffff;
            border: 1px solid #5c5f6e;
            border-radius: 5px;
            padding: 8px;
            font-size: 14px;
        }
        QPushButton {
            background-color: #61afef;
            color: #ffffff;
            border: none;
            border-radius: 5px;
            padding: 10px;
            font-size: 14px;
            font-weight: bold;
           
        }
        QPushButton:hover {
            background-color: #4c92d0;
        }
        QPushButton:pressed {
            background-color: #3a78b0;
        }
        QMessageBox {
            background-color: #282c34;
        }
        QStatusBar {
            background-color: #21252b;
            color: #abb2bf;
        }
        """

    def setup_login_ui(self):
        self.layout.setAlignment(Qt.AlignCenter)
        self.clear_layout()

        title_label = QLabel("Login")
        title_label.setStyleSheet("font-size: 24px; color: #61afef;")
        title_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(title_label)

        self.login_input = QLineEdit()
        self.login_input.setPlaceholderText("Digite seu token")
        self.layout.addWidget(self.login_input)

        login_button = QPushButton("Entrar")
        login_button.clicked.connect(self.login)
        self.layout.addWidget(login_button)

    def clear_layout(self):
        for i in reversed(range(self.layout.count())):
            widget = self.layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

    def login(self):
        token = self.login_input.text().strip()
        if token:
            self.token = token
            self.worker_thread = WorkerThread(self.token)
            self.worker_thread.start()

            # Salvar token no arquivo
            with open(self.LOGIN_FILE, "w") as file:
                file.write(self.token)

            self.setup_main_ui()
        else:
            self.show_message("Erro", "Token inválido ou não fornecido!")

    def setup_main_ui(self):
        self.clear_layout()

        # Indicadores no topo
        self.status_label = QLabel(f"Status: Ativo  |  Token: {self.token}")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.status_label)

        # Indicadores visuais
        indicator_layout = QHBoxLayout()
        indicator_layout.addWidget(self.create_indicator("Conexão", "Ativo"))
        indicator_layout.addWidget(self.create_indicator("Token", self.token))
        self.layout.addLayout(indicator_layout)

        # Botões principais
        self.stop_button = QPushButton("Parar Monitoramento")
        self.stop_button.clicked.connect(self.stop_monitoring)
        self.layout.addWidget(self.stop_button)

        self.logout_button = QPushButton("Efetuar Logoff")
        self.logout_button.clicked.connect(self.logout)
        self.layout.addWidget(self.logout_button)

        # Mensagem no tray
        self.hide()
        self.tray_icon.showMessage(
            "Monitor de Máquina",
            "Monitoramento iniciado. O aplicativo está no tray.",
            QSystemTrayIcon.Information,
            2000
        )

    def create_indicator(self, label, value):
        layout = QVBoxLayout()
        label_widget = QLabel(label)
        value_widget = QLabel(value)
        label_widget.setStyleSheet("color: #abb2bf; font-size: 12px;")
        value_widget.setStyleSheet("color: #98c379; font-size: 14px; font-weight: bold;")
        layout.addWidget(label_widget)
        layout.addWidget(value_widget)
        return QWidget().setLayout(layout)

    def stop_monitoring(self):
        if self.worker_thread:
            self.worker_thread.stop()
            self.show_message("Status", "Monitoramento parado com sucesso.")

    def logout(self):
        if self.worker_thread:
            self.worker_thread.stop()
        if os.path.exists(self.LOGIN_FILE):
            os.remove(self.LOGIN_FILE)
        self.token = None
        self.setup_login_ui()
        self.show()

    def show_message(self, title, message):
        self.status_bar.showMessage(message, 5000)

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.request_password_and_restore()

    def request_password_and_restore(self):
        while True:
            password, ok = QInputDialog.getText(
                self, "Autenticação", "Digite a senha para restaurar:", QLineEdit.Password
            )
            if not ok:
                return
            if password == self.correct_password:
                self.show()
                break
            else:
                self.show_message("Erro", "Senha incorreta!")

    def show_about(self):
        QMessageBox.information(self, "Sobre", "Monitor de Máquina v1.0\nDesenvolvido por Sousa.")

    def quit_application(self):
        if self.worker_thread:
            self.worker_thread.stop()
            self.worker_thread.wait()
        QApplication.instance().quit()


if __name__ == '__main__':
    app = QApplication(sys.argv)

    login_file = "login_data.txt" 
    login_valido = False

    if os.path.exists(login_file):
        with open(login_file, "r") as file:
            token = file.read().strip()
            if token:  
                login_valido = True

    
    window = MainWindow()

    if login_valido:
        
        print("Login válido. Executando em segundo plano...")
        window.tray_icon.show()  
    else:
       
        window.show()

    sys.exit(app.exec_())