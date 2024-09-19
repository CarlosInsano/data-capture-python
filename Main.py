import sqlite3
import re
import threading
import cv2
import numpy as np
import pyautogui
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
import tkinter as tk
from tkinter import ttk
import pytesseract
import time


# Configurar o caminho do executável do Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Exemplo para Windows

# Função para aplicar tratamento de imagem
def process_image(image):
    # Converter para escala de cinza
    image = ImageOps.grayscale(image)
    # Ajustar contraste
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.5)
    # Aplicar filtro de nitidez
    image = image.filter(ImageFilter.SHARPEN)
    return image

# Função para converter imagem PIL em texto usando pytesseract
def image_to_text(image):
    text = pytesseract.image_to_string(image)
    return text

# Função para extrair dados do texto
def extract_data(text):
    # Substituir quebras de linha e múltiplos espaços por um único espaço
    text = re.sub(r'\s+', ' ', text).strip()
    # Lista de palavras-chave com variações possíveis
    categories = [
        'ESTRANGEIROS',
        'INSTITUCIONAIS',
        'PESSOA FISICA'
    ]
    # Criar uma expressão regular para capturar essas palavras-chave e valores
    category_pattern = '|'.join(re.escape(cat) for cat in categories)
    pattern = re.compile(rf'(?P<Category>{category_pattern})\s*[-—_–]*\s*R\$[\s]*(?P<Value>[\d\.,]+)', re.IGNORECASE)
    # Encontrar todas as correspondências no texto
    matches = pattern.findall(text) 
    # Inicializar uma lista vazia para armazenar os dados extraídos
    data = []
    
    # Iterar sobre todas as correspondências encontradas
    for match in matches:
        # Desempacotar a correspondência em duas variáveis: category e value
        category, value = match
        # Remover espaços desnecessários da categoria
        category = category.strip()
        # Limpar e converter o valor
        #print('valor antes do replace',value)
        value = value.replace('R$', '').replace('.', '').replace(',', '').strip()
        #print('valor depois do replace',value)
        # Tentar converter o valor para float
        try:
            value = float(value)
            # Adicionar uma tupla (category, value) à lista de dados
            data.append((category.strip(), value))
        except ValueError:
            continue
    # Retornar a lista de dados extraídos
    return data
    

# Função para procurar a imagem e definir a região de captura
def find_image_and_set_region(image_path, confidence=0.7):
    try:
        location = pyautogui.locateOnScreen('print.png', confidence=0.7)
        if location is not None:
            x, y, width, height = location
            print(f"Imagem encontrada na posição: {location}")
            return (x, y, width, height)
        else:
            print("Imagem não encontrada")
            return None
    except Exception as e:
        print(f"Erro ao procurar imagem: {e}")
        return None

# Função para esperar até que a imagem seja encontrada
def wait_for_image(image_path, confidence=0.7, wait_time=10):
    start_time = time.time()
    while True:
        screen_region = find_image_and_set_region(image_path, confidence)
        if screen_region is not None:
            return screen_region
        elapsed_time = time.time() - start_time
        if elapsed_time > wait_time:
            print(f"Tempo de espera de {wait_time} segundos expirado. Imagem não encontrada.")
            return None
        print(f"Imagem não encontrada. Aguardando {wait_time - elapsed_time:.2f} segundos restantes...")
        time.sleep(0.5)

# Função para capturar e processar a tela em tempo real
def capture_and_process_screen(image_path):
    # Esperar até que a imagem seja encontrada
    screen_region = wait_for_image(image_path)
    if screen_region is None:
        print("Não foi possível definir a região de captura.")
        return

    try:
        # Configuração da captura de vídeo
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = cv2.VideoWriter('output.avi', fourcc, 20.0, (screen_region[2], screen_region[3]))

        # Converter valores para inteiros nativos
        screen_region = tuple(int(value) for value in screen_region)

        while True:
            try:
                # Captura da tela
                img = pyautogui.screenshot(region=screen_region)
                frame = np.array(img)

                # Convertendo para formato OpenCV (RGB)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Convertendo para PIL para processamento
                pil_image = Image.fromarray(frame)

                # Processar imagem
                processed_image = process_image(pil_image)

                # Converter imagem processada em texto
                text = image_to_text(processed_image)
                print(f'''texto extraido da imagem:
                {text}''')
                # Extrair dados do texto
                data = extract_data(text)
                print (data)

                # Verificar se a função extraiu algum dado e, em caso afirmativo, exibir os dados em tempo real
                if data:
                    # Formatar os dados extraídos como uma string, onde cada linha tem o formato 'categoria: R$ valor'
                    data_str = '\n'.join([f'{category}: R$ {round(value)}' for category, value in data])
                    # Exibir a string formatada com os dados extraídos
                    print(f"Dados extraídos em tempo real:\n{data_str}")

                # Salvar o frame no vídeo
                out.write(frame)

                # Exibir o frame com OpenCV
                cv2.imshow('Screen Capture', frame)

                # Verifica se a imagem de referência ainda está presente
                if not pyautogui.locateOnScreen(image_path, confidence=0.8):
                    print("Imagem de referência não encontrada. Parando gravação e reiniciando busca.")
                    break

                # Sair do loop com 'q'
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            except Exception as e:
                print(f"Erro durante captura e processamento: {e}")
                capture_and_process_screen(image_path)
                break
    finally:
        # Libere tudo quando terminar
        out.release()
        cv2.destroyAllWindows()

# Função para iniciar a captura com uma imagem de referência
def start_capture_with_image():
    image_path = 'print.png'  # Caminho para a imagem de referência
    threading.Thread(target=lambda: capture_and_process_screen(image_path), daemon=True).start()

# Configuração da interface gráfica
root = tk.Tk()
root.title("Captura e Processamento de Tela")

# Adicionar botão para iniciar a captura
start_button = ttk.Button(root, text="Iniciar Captura", command=start_capture_with_image)
start_button.pack(pady=20)

root.mainloop()
