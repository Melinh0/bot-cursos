from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pyautogui
import time
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configurações do navegador
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-software-rasterizer")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--log-level=3")

# Credenciais e URLs
login_url = "https://www.datascienceacademy.com.br/"
curso_url = "https://www.datascienceacademy.com.br/path-player?courseid=fundamentos-de-linguagem-python-para-analise-de-dados-e-data-science&unit=63aa11114343420e8702d3c7Unit"
email = "yagomelo20022109@gmail.com"
senha = "arthur2009"

# Inicializa o navegador
driver = webdriver.Chrome(options=options)

def pressionar_proximo():
    try:
        logging.info("Clicando no botão 'Próximo'.")
        proximo_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "default-course-player-nav-btn.next"))
        )
        proximo_button.click()
        time.sleep(30)  # Espera 15 segundos para o carregamento da próxima página
        logging.info("Botão 'Próximo' pressionado com sucesso.")
    except Exception as e:
        logging.error(f"Erro ao pressionar o botão 'Próximo': {e}")

try:
    logging.info("Acessando a página inicial.")
    driver.get(login_url)
    time.sleep(3)  # Tempo para carregar a página

    # Aguarda e clica no botão "Entrar"
    logging.info("Aguardando botão 'Entrar'...")
    entrar_button = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.ID, "menuItem_1592487994826_6"))
    )
    entrar_button.click()
    time.sleep(3)

    # Capturar a posição da barra de email e senha manualmente antes
    email_posicao = (872, 456)  # Atualize com a posição real do campo de e-mail
    senha_posicao = (868, 539)  # Atualize com a posição real do campo de senha
    botao_login_posicao = (945, 599)  # Atualize com a posição real do botão de login

    # Clicar no campo de e-mail e inserir email com pyautogui
    pyautogui.click(email_posicao)
    pyautogui.write(email, interval=0.05)

    # Clicar no campo de senha e inserir senha com pyautogui
    pyautogui.click(senha_posicao)
    pyautogui.write(senha, interval=0.05)

    # Clicar no botão de login
    pyautogui.click(botao_login_posicao)

    # Aguarda a autenticação
    time.sleep(5)  # Tempo para carregar a página após login
    logging.info("Login realizado com sucesso!")

    # Acessa diretamente o curso
    logging.info("Acessando o curso Fundamentos de Engenharia de Dados.")
    driver.get(curso_url)
    time.sleep(15)  # Aguarda 15 segundos dentro do curso

    # Continuar pressionando o botão "Próximo" indefinidamente
    while True:
        pressionar_proximo()

except Exception as e:
    logging.error(f"Ocorreu um erro: {e}")

finally:
    driver.quit()
