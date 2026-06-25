import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import os

@pytest.fixture
def driver():
    """Фикстура для настройки и закрытия браузера"""
    options = webdriver.ChromeOptions()
    
    if os.environ.get('CI'):
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--ignore-certificate-errors')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    driver.get("http://localhost:8000/?balance=30000&reserved=20001")
    
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "h1"))
        )
    except TimeoutException:
        print("Page did not load properly")
        driver.save_screenshot("page_load_error.png")
        driver.quit()
        raise
    
    yield driver
    driver.quit()

def wait_for_element(driver, by, value, timeout=5):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, value))
    )

def click_rub_account(driver):
    rub_card = driver.find_element(By.XPATH, "//h2[text()='Рубли']/..")
    rub_card.click()
    wait_for_element(driver, By.CSS_SELECTOR, "input[placeholder='0000 0000 0000 0000']")

def enter_card_number(driver, card_number):
    card_input = driver.find_element(By.CSS_SELECTOR, "input[placeholder='0000 0000 0000 0000']")
    card_input.clear()
    card_input.send_keys(card_number)

def enter_amount(driver, amount):
    amount_input = driver.find_element(By.CSS_SELECTOR, "input[placeholder='1000']")
    amount_input.clear()
    amount_input.send_keys(amount)

def get_commission(driver):
    commission_span = driver.find_element(By.ID, "comission")
    return commission_span.text

def is_transfer_button_present(driver):
    try:
        driver.find_element(By.XPATH, "//span[text()='Перевести']/ancestor::button")
        return True
    except NoSuchElementException:
        return False

def click_transfer_button(driver):
    button = driver.find_element(By.XPATH, "//span[text()='Перевести']/ancestor::button")
    button.click()

def get_alert_text(driver):
    try:
        WebDriverWait(driver, 3).until(EC.alert_is_present())
        alert = driver.switch_to.alert
        text = alert.text
        alert.accept()
        return text
    except TimeoutException:
        return None