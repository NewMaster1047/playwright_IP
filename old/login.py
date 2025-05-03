from flask import Flask, render_template, url_for, request, redirect
import pyautogui
import time
import re
from decimal import Decimal
from PIL import Image
import os
import pytesseract
from playwright.sync_api import Playwright, sync_playwright, expect
import logging
from datetime import datetime

# Настройка логирования
def setup_logger():
    # Создаем директорию для логов, если её нет
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Создаем уникальное имя файла для каждого запроса
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    log_filename = f'logs/app_{timestamp}.log'
    
    # Настраиваем логгер
    logger = logging.getLogger("IP_v1")
    logger.setLevel(logging.INFO)
    
    # Удаляем существующие обработчики
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Добавляем новые обработчики
    file_handler = logging.FileHandler(log_filename)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    
    return logger

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
app = Flask(__name__)

playwright = None
browser = None
page = None

def extract_text_from_image(image_name):
    image_path = os.path.join('static', image_name)
    if not os.path.exists(image_path):
        print(f"Файл {image_path} не найден.")
        return None

    # Загружаем изображение
    image = Image.open(image_path)

    # Распознаем текст
    text = pytesseract.image_to_string(image, lang='rus+eng')  # если текст может быть на русском и английском

    return text


def init_page():
    global playwright, browser, page, context
    if not page:
        playwright = sync_playwright().start()

        # For linux
        # browser = playwright.chromium.launch_persistent_context(
        #     user_data_dir="/home/newmaster1047/.config/chromium",
        #     headless=False,
        #     executable_path="/usr/bin/google-chrome",
        #     args=[
        #         "--disable-web-security",
        #         "--allow-running-insecure-content",
        #     ]
        # )

        # For Windows
        browser_path = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
        browser = playwright.chromium.launch(executable_path=browser_path, headless=False)
        context = browser.new_context()
        page = context.new_page()
    return page


def login(page, inn, password):
    logger.info(f"Попытка входа с ИНН: {inn}")
    try:
        page.goto("https://my.soliq.uz/main/")
        expect(page.get_by_role("link", name=" Кабинетга кириш").nth(2)).to_be_visible()
    except AssertionError:
        logger.error("Не удалось загрузить страницу входа")
        return "again"

    logger.info("Переход на страницу входа")
    page.get_by_role("link", name=" Кабинетга кириш").nth(2).click()
    expect(page.get_by_role("link", name="ESI орқали")).to_be_visible()
    page.get_by_role("link", name="ESI орқали").click()
    page.locator("#dropdownMenu1").click()
    
    prefixes = ["INN", "PINFL"]
    found = False

    for prefix in prefixes:
        try:
            user = page.get_by_role("link", name=f"{prefix}: {inn} ")
            expect(user).to_be_visible(timeout=2000)
            user.click()
            found = True
            logger.info(f"Найден пользователь с {prefix}: {inn}")
            break
        except:
            continue

    if not found:
        logger.error(f"Пользователь с ИНН {inn} не найден")
        return "inn_not_found"

    captcha = page.locator(".img-recaptcha")
    if (captcha.is_visible()):
        logger.info("Обнаружена капча")
        page.locator(".img-recaptcha").screenshot(path='static/screenshot.png')
        return "captcha_is_visible"
    else:
        expect(page.get_by_role("button", name=" Kirish")).to_be_visible()
        page.get_by_role("button", name=" Kirish").click()

        time.sleep(0.5)
        pyautogui.write(password)
        pyautogui.press('enter')
        logger.info("Введен пароль")

    time.sleep(0.5)
    page.keyboard.press("Escape")
    
    loaded = False

    try:
        page_load = page.get_by_role("link", name="ЯТТларнинг товар айланмалари бўйича ҳисобот шакллари")
        expect(page_load).to_be_visible(timeout=2000)
        loaded = True
        logger.info("Успешный вход в систему")
    except:
        logger.warning("Попытка обновления страницы")
        pyautogui.press('f5')
        page_load = page.get_by_role("link", name="ЯТТларнинг товар айланмалари бўйича ҳисобот шакллари")
        expect(page_load).to_be_visible(timeout=2000)
        loaded = True
    
    if not loaded:
        logger.error("Неверный пароль или проблемы с входом")
        return "incorrect_password"

    return "True"


def login_with_captcha(page, pk, password):
    page.get_by_placeholder("Spamdan himoya").fill(pk)
    expect(page.get_by_role("button", name=" Kirish")).to_be_visible()
    page.get_by_role("button", name=" Kirish").click()

    time.sleep(0.5)
    pyautogui.write(password)
    pyautogui.press('enter')

    time.sleep(0.5)
    page.keyboard.press("Escape")

    try:
        page_load = page.get_by_role("link", name="ЯТТларнинг товар айланмалари бўйича ҳисобот шакллари")
        expect(page_load).to_be_visible(timeout=2000)
        return "True"
    except:
        return 'incorrect_password_or_captcha'


def task_1(page):
    logger.info("Начало выполнения задачи 1")
    page.get_by_role("link", name="ЯТТларнинг товар айланмалари бўйича ҳисобот шакллари").click()

    # Сохороняем суммы в переменную price_n
    # page 1
    logger.info("Получение данных со страницы 1")
    url_1 = page.get_by_role("link", name="Айланмадан олинадиган солиқ ҳисоб-китоби").first
    url_1 = url_1.get_attribute('href')
    page1 = context.new_page()
    page1.goto(f"https://my.soliq.uz/{url_1}/")
    price1 = page1.locator("tr:nth-child(33) > td:nth-child(4) > div").first
    time.sleep(0.5)
    price1.screenshot(path='static/price_1.png')
    price1 = extract_text_from_image("price_1.png")
    price_1 = Decimal(price1.replace(",", ""))
    logger.info(f"Получена цена 1: {price_1}")
    page1.close()

    # page 2
    logger.info("Получение данных со страницы 2")
    url_2 = page.get_by_role("link", name="Айланмадан олинадиган солиқ ҳисоб-китоби").nth(1)
    url_2 = url_2.get_attribute('href')
    page2 = context.new_page()
    page2.goto(f"https://my.soliq.uz/{url_2}/")
    price2 = page2.locator("tr:nth-child(33) > td:nth-child(4) > div").first
    time.sleep(0.5)
    price2.screenshot(path='static/price_2.png')
    price2 = extract_text_from_image("price_2.png")
    price_2 = Decimal(price2.replace(",", ""))
    logger.info(f"Получена цена 2: {price_2}")
    page2.close()

    # Вычитываем сумму налога предпоследнего месяца от последнего
    price = price_1 - price_2
    logger.info(f"Рассчитанная разница: {price}")

    # Запоминаем(сохроняем в переменную) номер чека последней оплаты
    logger.info("Получение номера последнего документа")
    page_1 = context.new_page()
    page_1.goto("https://my.soliq.uz/payment/list")
    html_el_of_last_doc = page_1.locator("#report-list_wrapper div:nth-child(3) div:nth-child(2) div:nth-child(2) table > tbody > tr:nth-child(1) > td:nth-child(1)").inner_text()
    num_of_last_doc = int(re.search(r'№\s*(\d+)', html_el_of_last_doc).group(1))
    logger.info(f"Номер последнего документа: {num_of_last_doc}")
    
    # Переходим в страницу с формой для оплаты налога
    logger.info("Переход на страницу оплаты")
    page_1.goto("https://my.soliq.uz/payment/add")

    logger.info("Заполнение формы оплаты")
    page_1.locator("#updateNp2Btn").click()
    time.sleep(3)
    page_1.locator("select[name=\"na2code\"]").select_option("100")
    page_1.locator("#purposeCode").select_option("08102")
    page_1.locator("#paymentNum").fill(f"{num_of_last_doc + 1}")
    page_1.locator("#summa").fill(f"{price}")

    time.sleep(10)

    page_1.goto("https://my.soliq.uz/payment/add")

    page_1.locator("#updateNp2Btn").click()
    time.sleep(3)
    page_1.locator("select[name=\"na2code\"]").select_option("38")
    page_1.locator("#purposeCode").select_option("08102")
    page_1.locator("#paymentNum").fill(f"{num_of_last_doc + 2}")
    page_1.locator("#summa").fill("375000")

    time.sleep(10)
    logger.info("Задача 1 успешно выполнена")

    return "complited"



@app.route('/', methods=['POST', 'GET'])
def index():
    data = request.args.get('data')
    if request.method == "POST":
        # Создаем новый логгер для каждого POST запроса
        global logger
        logger = setup_logger()
        
        inn = request.form['inn']
        global password
        password = request.form['password']
        
        result = app_run(inn, password)
        if result == "incorrect_password":
            shutdown_browser()
            return render_template("index.html", data="incorrect_password")
        elif result == "again":
            shutdown_browser()
            return render_template("index.html", data=result)
        elif result == "captcha_is_visible":
            return redirect('/captcha')
        elif result == "inn_not_found":
            shutdown_browser()
            return render_template("index.html", data=result)
        else:
            shutdown_browser()
            print(result)
            return render_template("index.html", data=result)
    else:
        shutdown_browser()
        return(render_template("index.html", data=data))


@app.route('/captcha', methods=['POST', 'GET'])
def captcha_verify():
    if request.method == "POST":
        pk = request.form['capcha_input']
        result = app_run2(pk, password)
        # if result:
        #     shutdown_browser()
        #     return redirect('/?data=completed')
        if result == "incorrect_password_or_captcha":
            shutdown_browser()
            return redirect('/?data=incorrect_password_or_captcha')
        else:
            shutdown_browser()
            return redirect(f"/?data={result}")
    else:
        return render_template("captcha.html")


def app_run(inn, password):
    page = init_page()
    result = login(page, inn, password)
    if result == "True":
        task = task_1(page)
        return task
    else:
        return result

def app_run2(pk, password):
    page = init_page()
    result = login_with_captcha(page, pk, password)
    if result == "True":
        task = task_1(page)
        return task
    else:
        return result

def shutdown_browser():
    global playwright, browser, page
    if page:
        page.close()
        page = None
    if browser:
        browser.close()
        browser = None
    if playwright:
        playwright.stop()
        playwright = None

if __name__ == "__main__":
    app.run(debug=True, threaded=False)
    # app.run(host='127.0.0.1', port=8070, debug=True, threaded=False)

