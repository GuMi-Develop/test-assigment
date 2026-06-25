import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time

@pytest.fixture
def driver():
    """Фикстура для настройки и закрытия браузера"""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    driver = webdriver.Chrome(options=options)
    driver.get("http://localhost:8000/?balance=30000&reserved=20001")
    yield driver
    driver.quit()

def wait_for_element(driver, by, value, timeout=5):
    """Вспомогательная функция для ожидания элемента"""
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, value))
    )

def click_rub_account(driver):
    """Клик по карточке 'Рубли'"""
    rub_card = driver.find_element(By.XPATH, "//h2[text()='Рубли']/..")
    rub_card.click()
    wait_for_element(driver, By.CSS_SELECTOR, "input[placeholder='0000 0000 0000 0000']")

def enter_card_number(driver, card_number):
    """Ввод номера карты"""
    card_input = driver.find_element(By.CSS_SELECTOR, "input[placeholder='0000 0000 0000 0000']")
    card_input.clear()
    card_input.send_keys(card_number)

def enter_amount(driver, amount):
    """Ввод суммы перевода"""
    amount_input = driver.find_element(By.CSS_SELECTOR, "input[placeholder='1000']")
    amount_input.clear()
    amount_input.send_keys(amount)

def get_commission(driver):
    """Получение значения комиссии"""
    commission_span = driver.find_element(By.ID, "comission")
    return commission_span.text

def is_transfer_button_present(driver):
    """Проверка наличия кнопки 'Перевести'"""
    try:
        driver.find_element(By.XPATH, "//span[text()='Перевести']/ancestor::button")
        return True
    except NoSuchElementException:
        return False

def click_transfer_button(driver):
    """Клик по кнопке 'Перевести'"""
    button = driver.find_element(By.XPATH, "//span[text()='Перевести']/ancestor::button")
    button.click()

def get_alert_text(driver):
    """Получение текста из alert (уведомления)"""
    try:
        WebDriverWait(driver, 3).until(EC.alert_is_present())
        alert = driver.switch_to.alert
        text = alert.text
        alert.accept()
        return text
    except TimeoutException:
        return None


# ==================== ТЕСТЫ НА ДЕФЕКТЫ ====================

def test_bug_card_number_more_than_16_digits(driver):
    """
    Дефект №1: Номер карты может содержать более 16 цифр
    
    Ожидаемое поведение: поле должно принимать только 16 цифр
    Фактическое: принимает больше 16 цифр
    
    Тест должен упасть, так как баг существует.
    """
    click_rub_account(driver)
    
    long_card_number = "11112222333344445"
    enter_card_number(driver, long_card_number)
    
    card_input = driver.find_element(By.CSS_SELECTOR, "input[placeholder='0000 0000 0000 0000']")
    actual_value = card_input.get_attribute("value").replace(" ", "")
    
    assert len(actual_value) == 16, f"BUG: Card number field accepts more than 16 digits. Actual length: {len(actual_value)}, Actual value: {actual_value}"
    
    enter_amount(driver, "100")
    WebDriverWait(driver, 2).until(
        EC.text_to_be_present_in_element((By.ID, "comission"), "10")
    )
    
    assert not is_transfer_button_present(driver), "BUG: Transfer button is present with invalid card number"


def test_bug_negative_transfer_amount(driver):
    """
    Дефект №2: Возможен перевод отрицательной суммы 
    
    Ожидаемое поведение: перевод отрицательной суммы невозможен
    Фактическое: перевод выполняется с отрицательной суммой
    
    Тест должен упасть, так как баг существует.
    """
    click_rub_account(driver)
    enter_card_number(driver, "1111222233334444")
    enter_amount(driver, "-1000")
    
    WebDriverWait(driver, 2).until(
        EC.text_to_be_present_in_element((By.ID, "comission"), "-100")
    )
    
    commission = get_commission(driver)
    assert "-" in commission, f"Commission is not negative: {commission}"
    
    assert is_transfer_button_present(driver), "Transfer button should be present"
    
    click_transfer_button(driver)
    alert_text = get_alert_text(driver)
    
    assert alert_text is not None, "Alert should be present"
    
    assert "-1000" not in alert_text, f"BUG: Negative amount transfer should not be allowed, but got: {alert_text}"
    
    if alert_text:
        import re
        numbers = re.findall(r'\d+', alert_text)
        if numbers:
            amount_in_alert = int(numbers[0])
            assert amount_in_alert > 0, f"BUG: Transfer amount should be positive, but got: {amount_in_alert}"


def test_bug_card_number_not_reset_on_account_switch(driver):
    """
    Дефект №3: Номер карты не сбрасывается при смене счёта 
    
    Ожидаемое поведение: при переключении на другой счет поле номера карты должно очищаться
    Фактическое: номер карты сохраняется
    
    Тест должен упасть, так как баг существует.
    """
    click_rub_account(driver)
    enter_card_number(driver, "1111222233334444")
    
    card_input = driver.find_element(By.CSS_SELECTOR, "input[placeholder='0000 0000 0000 0000']")
    assert card_input.get_attribute("value") == "1111 2222 3333 4444", "Card number should be entered"
    
    usd_card = driver.find_element(By.XPATH, "//h2[text()='Доллары']/..")
    usd_card.click()
    
    wait_for_element(driver, By.CSS_SELECTOR, "input[placeholder='0000 0000 0000 0000']")
    
    new_card_input = driver.find_element(By.CSS_SELECTOR, "input[placeholder='0000 0000 0000 0000']")
    
    assert new_card_input.get_attribute("value") == "", "BUG: Card number should be reset when switching accounts"


def test_bug_zero_amount_transfer(driver):
    """
    Дефект №4: Возможен перевод нулевой суммы (High)
    
    Ожидаемое поведение: перевод нулевой суммы невозможен
    Фактическое: перевод нулевой суммы выполняется
    
    Тест должен упасть, так как баг существует.
    """
    click_rub_account(driver)
    enter_card_number(driver, "1111222233334444")
    enter_amount(driver, "0")
    
    WebDriverWait(driver, 2).until(
        EC.text_to_be_present_in_element((By.ID, "comission"), "0")
    )
    
    assert not is_transfer_button_present(driver), "BUG: Transfer button is present for zero amount"
    
    if is_transfer_button_present(driver):
        click_transfer_button(driver)
        alert_text = get_alert_text(driver)
        
        if alert_text:
            assert "0" not in alert_text, f"BUG: Zero amount transfer should not be allowed, but got: {alert_text}"


def test_bug_negative_commission_display(driver):
    """
    Дефект №5: Некорректное отображение комиссии при вводе отрицательных значений (Medium)
    
    Ожидаемое поведение: комиссия должна быть 0 или положительной
    Фактическое: комиссия отображается как отрицательное число
    
    Тест должен упасть, так как баг существует.
    """
    click_rub_account(driver)
    enter_card_number(driver, "1111222233334444")
    enter_amount(driver, "-500")
    
    time.sleep(1)
    
    commission = get_commission(driver)
    
    is_negative = commission.startswith("-")
    assert not is_negative, f"BUG: Commission should not be negative for negative amount. Got: {commission}"
    
    assert commission != "NaN ₽", f"BUG: Commission is NaN for negative amount"
    
    commission_value = commission.replace("₽", "").strip()
    if commission_value:
        try:
            float(commission_value)
        except ValueError:
            assert False, f"BUG: Commission is not a valid number: {commission}"


def test_bug_combined_negative_validation(driver):
    """
    Дополнительный комбинированный тест для проверки валидации отрицательных сумм
    Проверяет, что при вводе отрицательной суммы:
    1. Комиссия не отрицательная
    2. Кнопка перевода не активна или сумма в уведомлении положительная
    """
    click_rub_account(driver)
    enter_card_number(driver, "1111222233334444")
    
    test_amounts = ["-100", "-500", "-1000"]
    
    for amount in test_amounts:
        enter_amount(driver, amount)
        time.sleep(0.5)
        
        commission = get_commission(driver)
        
        if commission.startswith("-"):
            pytest.fail(f"BUG: Commission is negative ({commission}) for amount: {amount}")
        
        if is_transfer_button_present(driver):
             assert not commission.startswith("-"), f"BUG: Commission should not be negative: {commission}"