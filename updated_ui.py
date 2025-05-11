from flask import Flask, render_template, url_for, request, redirect
import pyautogui
import time
import re
import requests
from decimal import Decimal
from PIL import Image
import os
import pytesseract
from playwright.sync_api import sync_playwright, expect
import logging
from datetime import datetime
from dotenv import load_dotenv

# Загрузка переменных окружения из файла .env
load_dotenv()

# Настройка логирования
def setup_logger(filepath, data_time):
    if not os.path.exists(f'reports/{filepath}/log'):
        os.makedirs(f'reports/{filepath}/log')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    log_filename = f'reports/{filepath}/log/app_{timestamp}.log'
    logger = logging.getLogger("IP_v1")
    logger.setLevel(logging.INFO)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    file_handler = logging.FileHandler(log_filename)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    return logger

# Установка пути к Tesseract из переменной окружения
pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_CMD", r'C:\Program Files\Tesseract-OCR\tesseract.exe')
app = Flask(__name__)

playwright = None
browser = None
page = None
context = None

def extract_text_from_image(image_name):
    image_path = os.path.join('static', image_name)
    if not os.path.exists(image_path):
        logger.error(f"Файл {image_path} не найден")
        return None
    image = Image.open(image_path)
    text = pytesseract.image_to_string(image, lang='rus+eng')
    if text is None:
        logger.error(f"Не удалось извлечь текст из изображения {image_name}")
        return None
    logger.info(f"Извлечен текст из изображения {image_name}: {text}")
    return text

def init_page():
    global playwright, browser, page, context
    if not page:
        playwright = sync_playwright().start()
        browser_path = os.getenv("CHROME_PATH", 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe')
        browser = playwright.chromium.launch(executable_path=browser_path, headless=False)
        context = browser.new_context()
        page = context.new_page()
    return page

def get_last_document_number(context):
    logger.info("Получение номера последнего документа")
    page_temp = context.new_page()
    try:
        page_temp.goto("https://my.soliq.uz/payment/list")
        html_el_of_last_doc = page_temp.locator("#report-list_wrapper div:nth-child(3) div:nth-child(2) div:nth-child(2) table > tbody > tr:nth-child(1) > td:nth-child(1)").inner_text()
        num_of_last_doc = int(re.search(r'№\s*(\d+)', html_el_of_last_doc).group(1))
        logger.info(f"Номер последнего документа: {num_of_last_doc}")
        return num_of_last_doc
    except Exception as e:
        logger.error(f"Ошибка при получении номера документа: {str(e)}")
        raise
    finally:
        page_temp.close()
        logger.info("Временная страница для получения номера документа закрыта")

def captcha_checker(page):
    page.goto("https://my.soliq.uz/main/")
    page.get_by_role("link", name=" Кабинетга кириш").nth(2).click()
    expect(page.get_by_role("link", name="ESI орқали")).to_be_visible()
    page.get_by_role("link", name="ESI орқали").click()
    time.sleep(0.5)
    captcha = page.locator(".img-recaptcha")
    if captcha.is_visible():
        page.locator(".img-recaptcha").screenshot(path='static/screenshot.png')
        return "captcha_is_visible"
    return True

def login(page, inn, password, pk=None):
    logger.info(f"Попытка входа для ИНН: {inn}")
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
    if pk is not None:
        logger.info("Ввод текста капчи")
        page.get_by_placeholder("Spamdan himoya").fill(pk)
        expect(page.get_by_role("button", name=" Kirish")).to_be_visible()
        page.get_by_role("button", name=" Kirish").click()
    else:
        page.get_by_role("button", name=" Kirish").click()
    time.sleep(0.5)
    logger.info("Ввод пароля через PyAutoGUI")
    pyautogui.write(password)
    pyautogui.press('enter')
    time.sleep(0.5)
    page.keyboard.press('Escape')
    loaded = False
    try:
        page_load = page.get_by_role("link", name="ЯТТларнинг товар айланмалари бўйича ҳисобот шакллари")
        expect(page_load).to_be_visible(timeout=5000)
        loaded = True
        logger.info("Успешный вход в систему")
    except:
        logger.error("Не удалось войти в кабинет")
    if not loaded:
        logger.error("Неверный пароль или проблемы с входом")
        return "incorrect_password_or_captcha"
    return "True"

def subm_reports(page, inn, timestamp):
    today = datetime.today()
    year = today.year
    month = today.month
    if month == 1:
        last_month = 12
        year -= 1
    else:
        last_month = month - 1
    logger.info("Начало выполнения отправки отчета")
    logger.info("__________________________________")
    logger.info("Переход на главную страницу")
    page.goto("https://my.soliq.uz/main/")
    logger.info("Переход в страницу с формой для расчета налога с оборота")
    page.get_by_role("link", name="ЯТТларнинг товар айланмалари бўйича ҳисобот шакллари").click()
    page.get_by_role("link", name="Электрон шакллар").click()
    page.get_by_role("link", name="Айланмадан олинадиган солиқ").click()
    logger.info("Начало заполнения формы")
    page.get_by_role("row", name="10190_12").get_by_role("link").click()
    logger.info("100 - Налог с оборота")
    page.locator("select[name=\"na2_id\"]").select_option("100")
    logger.info("(Тип расчета) - Расчет")
    page.locator("#type").select_option("1")
    logger.info(f"(Год) - {year}")
    page.locator("#year").select_option(str(year))
    logger.info(f"(Месяц) - {last_month}")
    page.locator("#perioddd").select_option(f"M_{last_month}")
    logger.info("Отчет успешно отправлен")
    time.sleep(3)
    page.goto("https://my.soliq.uz/main/")
    user_name = page.locator("#navbar-info div h1 span").inner_text()
    logger.info("Загрузка файла отчета")
    page.get_by_role("link", name="ЯТТларнинг товар айланмалари бўйича ҳисобот шакллари").click()
    with page.expect_download() as download_info:
        page.get_by_role("link", name="").first.click()
    download = download_info.value
    download_path = f"reports/{inn}/file/{timestamp}/"
    os.makedirs(download_path, exist_ok=True)
    download.save_as(f"{download_path}{download.suggested_filename}")
    result_filename = f"{download_path}{download.suggested_filename}"
    logger.info(f"Файл сохранен в: {result_filename}")
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not telegram_token or not telegram_chat_id:
        logger.error("TELEGRAM_TOKEN или TELEGRAM_CHAT_ID не заданы в переменных окружения")
        raise ValueError("Не заданы Telegram конфигурации")
    url = f"https://api.telegram.org/bot{telegram_token}/sendDocument"
    logger.info("Отправка файла в Telegram")
    with open(result_filename, "rb") as file:
        files = {"document": file}
        data = {"chat_id": telegram_chat_id, 'caption': user_name}
        response = requests.post(url, data=data, files=files)
        response.raise_for_status()
    logger.info("Успех")
    logger.info("__________________________________")
    return "completed"

def task_1(page, inn, timestamp, context, tax_payment=False, tax_375=False):
    logger.info("Начало выполнения оплаты налогов")
    page.goto("https://my.soliq.uz/main/")
    time.sleep(0.5)
    page.keyboard.press('Escape')
    time.sleep(1)
    
    doc_number = get_last_document_number(context) + 1
    page_1 = context.new_page()
    
    if tax_payment:
        logger.info("Оплата налога с оборота")
        page.get_by_role("link", name="ЯТТларнинг товар айланмалари бўйича ҳисобот шакллари").click()
        f_a = True
        try:
            url_1 = page.get_by_role("link", name="Айланмадан олинадиган солиқ ҳисоб-китоби").first
            expect(url_1).to_be_visible()
        except:
            f_a = False
            logger.info("Не найден документ налога с оборота")
        if f_a:
            url_1 = url_1.get_attribute('href')
            page1 = context.new_page()
            page1.goto(f"https://my.soliq.uz/{url_1}/")
            time.sleep(1)
            price1 = page1.locator("#list-1 > table > tbody > tr:nth-child(33) > td:nth-child(4) > div").inner_text()
            if price1 is None:
                logger.error("Не удалось извлечь сумму налога за последний месяц")
                page1.close()
                page_1.close()
                return "ocr_error"
            price_1 = Decimal(price1.replace(",", ""))
            logger.info(f"Оборот за последний месяц: {price_1}")
            page1.close()
            url_2 = page.get_by_role("link", name="Айланмадан олинадиган солиқ ҳисоб-китоби").nth(1)
            url_2 = url_2.get_attribute('href')
            page2 = context.new_page()
            page2.goto(f"https://my.soliq.uz/{url_2}/")
            time.sleep(1)
            price2 = page2.locator("#list-1 > table > tbody > tr:nth-child(33) > td:nth-child(4) > div").inner_text()
            if price2 is None:
                logger.error("Не удалось извлечь сумму налога за предпоследний месяц")
                page2.close()
                page_1.close()
                return "ocr_error"
            price_2 = Decimal(price2.replace(",", ""))
            logger.info(f"Оборот за предпоследний месяц: {price_2}")
            page2.close()
            price = price_1 - price_2
            logger.info(f"Рассчитанная разница: {price}")
            if price != 0:
                logger.info("Заполнение формы оплаты налога с оборота")
                page_1.goto("https://my.soliq.uz/payment/add")
                page_1.locator("#updateNp2Btn").click()
                time.sleep(3)
                page_1.locator("select[name=\"na2code\"]").select_option("100")
                page_1.locator("#purposeCode").select_option("08102")
                page_1.locator("#paymentNum").fill(str(doc_number))
                page_1.locator("#summa").fill(str(price))
                doc_number += 1
            else:
                logger.info("Нулевой оборот")
    
    if tax_375:
        logger.info("Оплата базового налога (375 000)")
        page_1.goto("https://my.soliq.uz/payment/add")
        page_1.locator("#updateNp2Btn").click()
        time.sleep(3)
        page_1.locator("select[name=\"na2code\"]").select_option("38")
        page_1.locator("#purposeCode").select_option("08102")
        page_1.locator("#paymentNum").fill(str(doc_number))
        page_1.locator("#summa").fill("375000")
        doc_number += 1
    
    time.sleep(10)
    page_1.close()
    logger.info("Оплата налогов завершена")
    return "completed"

def custom_tax_payment(page, na2code, amount, doc_number):
    logger.info(f"Оплата пользовательского налога: na2code={na2code}, сумма={amount}, номер документа={doc_number}")
    try:
        page.goto("https://my.soliq.uz/payment/add")
        page.locator("#updateNp2Btn").click()
        time.sleep(3)
        page.locator("select[name=\"na2code\"]").select_option(na2code)
        page.locator("#purposeCode").select_option("08102")
        page.locator("#paymentNum").fill(str(doc_number))
        page.locator("#summa").fill(str(amount))
        logger.info(f"Пользовательский налог na2code={na2code} успешно добавлен")
    except Exception as e:
        logger.error(f"Ошибка при добавлении налога na2code={na2code}: {str(e)}")
        raise
    time.sleep(5)

@app.route('/', methods=['POST', 'GET'])
def main_page():
    data = request.args.get('data')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    if request.method == "GET":
        shutdown_browser()
        check_captcha = app_captcha()
        return render_template("index.html", data=check_captcha)
    elif request.method == "POST":
        inn = request.form['inn']
        password = request.form['password']
        tax_payment = 'tax_payment' in request.form
        tax_375 = 'tax_375' in request.form
        na2codes = request.form.getlist('na2code[]')
        amounts = request.form.getlist('amount[]')
        global logger
        logger = setup_logger(inn, timestamp)
        try:
            pk = request.form.get('capcha_input')
            result = new_app_run(inn, password, timestamp, tax_payment, tax_375, na2codes, amounts, pk)
            shutdown_browser()
            return redirect(f"/return?data={result}")
        except Exception as e:
            logger.error(f"Ошибка при выполнении запроса: {str(e)}")
            result = new_app_run(inn, password, timestamp, tax_payment, tax_375, na2codes, amounts)
            shutdown_browser()
            return redirect(f"/return?data={result}")

@app.route('/return', methods=['GET'])
def return_page():
    data = request.args.get('data')
    return render_template("return.html", data=data)

def app_captcha():
    page = init_page()
    return captcha_checker(page)

def new_app_run(inn, password, timestamp, tax_payment, tax_375, na2codes, amounts, pk=None):
    page = init_page()
    if pk is not None:
        result = login(page, inn, password, pk)
    else:
        result = login(page, inn, password)
    if result != "True":
        return result
    tasks_completed = False
    if tax_payment:
        result = subm_reports(page, inn, timestamp)
        if result != "completed":
            return result
        tasks_completed = True
    if tax_payment or tax_375:
        result = task_1(page, inn, timestamp, context, tax_payment, tax_375)
        if result != "completed":
            return result
        tasks_completed = True
    if na2codes and amounts:
        valid_na2codes = {"38", "47", "100", "199"}
        if len(na2codes) != len(amounts):
            logger.error("Несоответствие количества na2code и amount")
            return "form_error"
        for na2code, amount in zip(na2codes, amounts):
            if na2code not in valid_na2codes or not amount.isdigit() or int(amount) <= 0:
                logger.error(f"Некорректные данные: na2code={na2code}, amount={amount}")
                return "invalid_tax_data"
        logger.info(f"Обработка {len(na2codes)} пользовательских налогов")
        page_1 = context.new_page()
        doc_number = get_last_document_number(context) + 1
        for na2code, amount in zip(na2codes, amounts):
            custom_tax_payment(page_1, na2code, amount, doc_number)
            doc_number += 1
        page_1.close()
        tasks_completed = True
    else:
        logger.info("Нет пользовательских налогов для обработки")
    return "completed" if tasks_completed else "no_tasks_selected"

def shutdown_browser():
    global playwright, browser, page, context
    if page:
        logger.info("Закрытие вкладки...")
        page.close()
        page = None
    if context:
        logger.info("Закрытие контекста...")
        context.close()
        context = None
    if browser:
        logger.info("Закрытие браузера...")
        browser.close()
        browser = None
    if playwright:
        logger.info("Остановка Playwright...")
        playwright.stop()
        playwright = None

if __name__ == "__main__":
    app.run(debug=True, threaded=False)