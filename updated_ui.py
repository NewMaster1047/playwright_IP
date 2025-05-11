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

# Настройка логирования
def setup_logger(filepath, data_time):
    # Создаем директорию для логов, если её нет
    if not os.path.exists(f'reports/{filepath}/log'):
        os.makedirs(f'reports/{filepath}/log')

    # Создаем уникальное имя файла для каждого запроса
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    log_filename = f'reports/{filepath}/log/app_{timestamp}.log'

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
        #     user_data_dir="/home/server/.config/chromium",
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


def captcha_checker(page):
    page.goto("https://my.soliq.uz/main/")
    page.get_by_role("link", name=" Кабинетга кириш").nth(2).click()
    expect(page.get_by_role("link", name="ESI орқали")).to_be_visible()
    page.get_by_role("link", name="ESI орқали").click()
    time.sleep(0.5)

    captcha = page.locator(".img-recaptcha")
    if (captcha.is_visible()):
        page.locator(".img-recaptcha").screenshot(path='static/screenshot.png')
        return "captcha_is_visible"
    else:
        return True


def login(page, inn, password, pk=None):
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
        page.get_by_placeholder("Spamdan himoya").fill(pk)
        expect(page.get_by_role("button", name=" Kirish")).to_be_visible()
        page.get_by_role("button", name=" Kirish").click()
    
    else:
        page.get_by_role("button", name=" Kirish").click()

    time.sleep(0.5)
    pyautogui.write(password)
    pyautogui.press('enter')

    time.sleep(0.5)
    page.keyboard.press("Escape")
    
    loaded = False
    try:
        page_load = page.get_by_role("link", name="ЯТТларнинг товар айланмалари бўйича ҳисобот шакллари")
        expect(page_load).to_be_visible(timeout=5000)
        loaded = True
        logger.info("Успешный вход в систему")
    except:
        logger.info("Не удалось войти в кабинет")

    
    if not loaded:
        logger.error("Неверный пароль или проблемы с входом")
        return "incorrect_password_or_captcha"

    else:
        return "True"


def subm_reports(page, inn, timestamp):
    timestamp = timestamp
    today = datetime.today()
    year = today.year
    month = today.month

    if month == 1:
        last_month = 12
        year -= 1
    else:
        last_month = month - 1


    logger.info("Начало выполнения отправки отсчета")
    logger.info("__________________________________")
 
    logger.info("Переход в главную страницу")
    page.goto("https://my.soliq.uz/main/")

    logger.info("Переход в страницу с формой для расчета налога с оборота")
    page.get_by_role("link", name="ЯТТларнинг товар айланмалари бўйича ҳисобот шакллари").click()
    page.get_by_role("link", name="Электрон шакллар").click()
    page.get_by_role("link", name="Айланмадан олинадиган солиқ").click()

    logger.info("Начало заполнении формы")
    page.get_by_role("row", name="10190_12").get_by_role("link").click()

    logger.info("100 - Налог с оборота")
    page.locator("select[name=\"na2_id\"]").select_option("100")

    logger.info("(Тип расчета) - Расчет")
    page.locator("#type").select_option("1")
    
    logger.info("(Год) - 2025")
    page.locator("#year").select_option("2025")

    logger.info(f"(Месяц) - {last_month}")
    page.locator("#perioddd").select_option(f"M_{last_month}")

    # page.get_by_role("button", name='Жўнатиш').screenshot(path='button.png')
    logger.info("Отчет успешно отправлено")

    # page.get_by_role("button", name="").click()
    # page.get_by_role("link", name="").click()

    time.sleep(3)
    

    page.goto("https://my.soliq.uz/main/")
    user_name = page.locator("#navbar-info div h1 span").inner_text()
    
    logger.info("Загрузка файл отчета")
    page.get_by_role("link", name="ЯТТларнинг товар айланмалари бўйича ҳисобот шакллари").click()
    with page.expect_download() as download_info:
        page.get_by_role("link", name="").first.click()
    download = download_info.value
    download.save_as(f"reports/{inn}/file/{timestamp}/" + download.suggested_filename)
    result_filename = f"reports/{inn}/file/{timestamp}/{download.suggested_filename}"
    logger.info(f"Файл сохранет в: {result_filename}")
    url = f"https://api.telegram.org/bot8134066377:AAFOtJsbdCcXRUhbZLfRdEzdNzu396zfeBo/sendDocument"
    
    logger.info("Отправка файла в тг")
    # Отправляем файл в Telegram
    with open(result_filename, "rb") as file:
        files = {"document": file}
        data = {"chat_id": "7969873927", 'caption': user_name}

        response = requests.post(url, data=data, files=files)
        response.raise_for_status()

    logger.info("Успех")
    logger.info("__________________________________")
    return "completed"


def task_1(page):
    logger.info("Начало выполнения оплату налогов")

    page.goto("https://my.soliq.uz/main/")
    time.sleep(0.5)
    page.keyboard.press("Escape")
    time.sleep(1)

    # Запоминаем(сохроняем в переменную) номер чека последней оплаты
    logger.info("Получение номера последнего документа")
    page_1 = context.new_page()
    page_1.goto("https://my.soliq.uz/payment/list")
    html_el_of_last_doc = page_1.locator("#report-list_wrapper div:nth-child(3) div:nth-child(2) div:nth-child(2) table > tbody > tr:nth-child(1) > td:nth-child(1)").inner_text()
    num_of_last_doc = int(re.search(r'№\s*(\d+)', html_el_of_last_doc).group(1))
    logger.info(f"Номер последнего документа: {num_of_last_doc}")

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
        price1 = page1.locator("tr:nth-child(33) > td:nth-child(4) > div").first
        time.sleep(0.5)
        price1.screenshot(path='static/price_1.png')
        price1 = extract_text_from_image("price_1.png")
        price_1 = Decimal(price1.replace(",", ""))
        logger.info(f"Оборот за последний месяц: {price_1}")
        page1.close()

        # page 2
        url_2 = page.get_by_role("link", name="Айланмадан олинадиган солиқ ҳисоб-китоби").nth(1)
        url_2 = url_2.get_attribute('href')
        page2 = context.new_page()
        page2.goto(f"https://my.soliq.uz/{url_2}/")
        price2 = page2.locator("tr:nth-child(33) > td:nth-child(4) > div").first
        time.sleep(0.5)
        price2.screenshot(path='static/price_2.png')
        price2 = extract_text_from_image("price_2.png")
        price_2 = Decimal(price2.replace(",", ""))
        logger.info(f"Оборот за пред последний месяц: {price_2}")
        page2.close()

        # Вычитываем сумму налога предпоследнего месяца от последнего
        price = price_1 - price_2
        logger.info(f"Рассчитанная разница: {price}")

        if price != 0:
            # Переходим в страницу с формой для оплаты налога
            logger.info("Оплата налога за оборот")
            page_1.goto("https://my.soliq.uz/payment/add")

            logger.info("Заполнение формы оплаты")
            page_1.locator("#updateNp2Btn").click()
            time.sleep(3)
            page_1.locator("select[name=\"na2code\"]").select_option("100")
            page_1.locator("#purposeCode").select_option("08102")
            page_1.locator("#paymentNum").fill(f"{num_of_last_doc + 1}")
            page_1.locator("#summa").fill(f"{price}")
        else:
            logger.info("Нулевой оборот")


    logger.info("Оплата базового налога (375 000)")
    page_1.goto("https://my.soliq.uz/payment/add")
    page_1.locator("#updateNp2Btn").click()
    time.sleep(3)
    page_1.locator("select[name=\"na2code\"]").select_option("38")
    page_1.locator("#purposeCode").select_option("08102")
    page_1.locator("#paymentNum").fill(f"{num_of_last_doc + 2}")
    page_1.locator("#summa").fill("375000")

    time.sleep(10)
    logger.info("Выполнено")

    return "complited"


@app.route('/', methods=['POST', 'GET'])
def main_page():
    data = request.args.get('data')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')

    if request.method == "GET":
        shutdown_browser()
        check_captcha = app_captcha()
        if check_captcha == "captcha_is_visible":
            return(render_template("index.html", data="captcha_is_visible"))
        else:
            return(render_template("index.html", data=data))
    elif request.method == "POST":
        inn = request.form['inn']
        password = request.form['password']
        global logger
        logger = setup_logger(inn, timestamp)
        try:
            pk = request.form['capcha_input']
            result = new_app_run(inn, password, timestamp, pk)
            if result == "incorrect_password_or_captcha":
                shutdown_browser()
                return redirect(f"/return?data={result}")
            elif result == "inn_not_found":
                shutdown_browser()
                return redirect(f"/return?data={result}")
            elif result:
                shutdown_browser()
                return redirect("/return?data=complited")
        except:
            result = new_app_run(inn, password, timestamp)
            if result == "incorrect_password_or_captcha":
                shutdown_browser()
                return redirect(f"/return?data={result}")
            elif result == "inn_not_found":
                shutdown_browser()
                return redirect(f"/return?data={result}")
            elif result:
                shutdown_browser()
                return redirect("/return?data=complited")
            else:
                shutdown_browser()
                return redirect(f"/?data={result}",)


@app.route('/return', methods=['GET'])
def return_page():
    data = request.args.get('data')
    if request.method == "GET":
        return(render_template("return.html", data=data))


def app_captcha():
    page = init_page()
    return captcha_checker(page)


def new_app_run(inn, password, timestamp, pk=None):
    page = init_page()
    timestamp = timestamp
    if pk is not None:
        result = login(page, inn, password, pk)
        if result == "True":
            task = subm_reports(page, inn, timestamp)
            if task == "completed":
                task = task_1(page)
            return task
        else:
            return result
    else:
        result = login(page, inn, password)
        if result == "True":
            task = subm_reports(page, inn, timestamp)
            if task == "completed":
                task = task_1(page)
            return task
        else:
            return result


def shutdown_browser():
    global playwright, browser, page
    if page:
        logger.info("Закрытие вкладки...")
        page.close()
        page = None
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
    # app.run(host='127.0.0.1', port=8070, debug=True, threaded=False)

