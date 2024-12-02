import sys
import os
import time
import psutil
import platform
import requests
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QLabel, QLineEdit, QPushButton, QWidget, QMessageBox, QGraphicsOpacityEffect
)
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QPropertyAnimation, QRect, QTimer
import time
import psutil
from datetime import datetime
from collections import defaultdict
from win10toast import ToastNotifier
import psutil
import time
import win32gui  # Para capturar a janela ativa no Windows
import win32process  # Para obter o processo da janela ativa
from collections import defaultdict

SERVER_URL = 'http://localhost:3000'

# Thread para execução em segundo plano
class WorkerThread(QThread):
    error_signal = pyqtSignal(str)
    message_signal = pyqtSignal(str)

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
                self.check_for_messages()  # Verifica se há novas mensagens
                self.send_usage_data()
                time.sleep(5)
            except Exception as e:
                self.error_signal.emit(str(e))
                time.sleep(5)

    def stop(self):
        self.running = False

    def update_machine(self, info, resources):
        response = requests.post(f'{SERVER_URL}/update', json={
            'token': self.token,
            'info': info,
            'resources': resources,
        })
        if response.status_code != 200:
            raise Exception(f'Erro ao atualizar informações: {response.text}')

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
        response = requests.get(f'{SERVER_URL}/get-command/{self.token}')
        if response.status_code == 200:
            command = response.text.strip()
            if command:
                # Executa o comando recebido
                result = os.popen(command).read()
                self.send_command_result(result)

    def send_command_result(self, result):
        response = requests.post(f'{SERVER_URL}/command-result', json={'token': self.token, 'result': result})
        if response.status_code != 200:
            raise Exception(f'Erro ao enviar resultado do comando: {response.text}')
    
    def check_for_messages(self):
       
        response = requests.get(f'{SERVER_URL}/get-message/{self.token}')
        if response.status_code == 200:
            message = response.text.strip()
            if message:
                print(message)
                self.message_signal.emit(message)



    """"FUNÇOES PARA CAPTURA DE PROGRAMAS ATIVOS"""

    def get_active_window_title(self):
        """Captura o título da janela ativa."""
        window = win32gui.GetForegroundWindow()
        return win32gui.GetWindowText(window)

    def get_program_name_from_window(self):
        """Captura o programa associado à janela ativa."""
        try:
            
            window = win32gui.GetForegroundWindow()
        
            _, pid = win32process.GetWindowThreadProcessId(window)
            
            process_name = psutil.Process(pid).name()
            return process_name
        except Exception as e:
            print(f"Erro ao capturar programa ativo: {e}")
            return None
        
    def send_usage_data(self):
        active_window_title = self.get_active_window_title()
        active_program = self.get_program_name_from_window()
    
        if active_program:
            self.send_usage_data(self.token, active_program, active_window_title, 5)

    def send_usage_data_api(token, program_name, window_title, usage_time, self):
        url = 'http://localhost:3000/report-usage'
        data = {
            'token': token,
            'programName': program_name,
            'windowTitle': window_title,
            'usageTime': usage_time
        }
        
        try:
            response = requests.post(url, json=data)
            if response.status_code == 200:
                print('Dados de uso registrados com sucesso.')
            else:
                print(f'Erro ao registrar dados de uso: {response.status_code}')
        except Exception as e:
            print(f'Erro ao enviar dados de uso: {e}')


# Classe principal com interface estilizada
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QLabel, QLineEdit, QPushButton, QWidget, QMessageBox
)
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import Qt

import sys
import requests

SERVER_URL = 'http://localhost:3000'

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Monitor de Máquina")
        self.setFixedSize(400, 300)
        self.setWindowIcon(QIcon("icon.png"))
        self.setStyleSheet(self.load_styles())

        self.token = None

        # Widget principal
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Layout principal
        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        # Tela de login inicial
        self.setup_login_ui()

    def load_styles(self):
        """Carrega o estilo CSS para personalizar a interface."""
        return """
        QMainWindow {
            background-color: #1e1e2f;
        }
        QLabel {
            color: #ffffff;
            font-size: 16px;
            font-weight: bold;
        }
        QLineEdit {
            background-color: #2e2e3e;
            color: #ffffff;
            border: 1px solid #4e4e6e;
            border-radius: 5px;
            padding: 8px;
            font-size: 14px;
        }
        QPushButton {
            background-color: #4e4e6e;
            color: #ffffff;
            border: none;
            border-radius: 5px;
            padding: 10px;
            font-size: 14px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #3e3e5e;
        }
        QPushButton:pressed {
            background-color: #5e5e8e;
        }
        QMessageBox {
            background-color: #1e1e2f;
        }
        """

    def setup_login_ui(self):
        self.layout.setAlignment(Qt.AlignCenter)
        self.clear_layout()

        title_label = QLabel("Login")
        title_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(title_label)

        self.login_input = QLineEdit()
        self.login_input.setPlaceholderText("Digite seu login")
        self.layout.addWidget(self.login_input)

        self.senha_input = QLineEdit()
        self.senha_input.setPlaceholderText("Digite sua senha")
        self.senha_input.setEchoMode(QLineEdit.Password)
        self.layout.addWidget(self.senha_input)

        login_button = QPushButton("Entrar")
        login_button.clicked.connect(self.login)
        self.layout.addWidget(login_button)

    def setup_main_ui(self):
        self.layout.setAlignment(Qt.AlignTop)
        self.clear_layout()

        title_label = QLabel("Monitor de Recursos")
        title_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(title_label)

        self.status_label = QLabel("Status: Conectado")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.status_label)

        logout_button = QPushButton("Logout")
        logout_button.clicked.connect(self.logout)
        self.layout.addWidget(logout_button)

    def clear_layout(self):
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def login(self):
        login = self.login_input.text().strip()
        senha = self.senha_input.text().strip()

        if not login or not senha:
            QMessageBox.warning(self, "Erro", "Por favor, preencha todos os campos.")
            return

        response = requests.post(f'{SERVER_URL}/login', json={'login': login, 'senha': senha})
        if response.status_code == 200:
            self.token = response.text
            QMessageBox.information(self, "Login", "Login realizado com sucesso!")
            self.setup_main_ui()
        else:
            # QMessageBox.critical(self, "Erro", f"Falha ao fazer login: {response.text}")
            print(response.text)

    def logout(self):
        self.token = None
        QMessageBox.information(self, "Logout", "Logout realizado com sucesso!")
        self.setup_login_ui()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
