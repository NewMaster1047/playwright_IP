from flask import Flask, render_template, url_for, request, redirect
import pyautogui
import time
import re
from PIL import Image
import os
import pytesseract
from playwright.sync_api import Playwright, sync_playwright, expect

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
    global playwright, browser, page
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
        browser = playwright.chromium.launch(headless=False)

        page = browser.new_page()
    return page


def run(page, inn, password):
    try:
        page.goto("https://my.soliq.uz/main/")
        expect(page.get_by_role("link", name=" Кабинетга кириш").nth(2)).to_be_visible()

    except AssertionError:
        return "again"

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
            break
        except:
            continue

    if not found:
        return "inn_not_found"

    captcha = page.locator(".img-recaptcha")
    if (captcha.is_visible()):
        page.locator(".img-recaptcha").screenshot(path='static/screenshot.png')
        return "captcha_is_visible"
    else:
        expect(page.get_by_role("button", name=" Kirish")).to_be_visible()
        page.get_by_role("button", name=" Kirish").click()

        time.sleep(0.5)
        pyautogui.write(password)
        pyautogui.press('enter')

    time.sleep(0.5)
    page.keyboard.press("Escape")
    
    loaded = False
    try:
        page_load = page.get_by_role("link", name="ЯТТларнинг товар айланмалари бўйича ҳисобот шакллари")
        expect(page_load).to_be_visible(timeout=2000)
        page_load.click()
        loaded = True
    except:
        pass
    
    if not loaded:
        return "incorrect_password"
    
    # page.get_by_role("link", name="ЯТТларнинг товар айланмалари бўйича ҳисобот шакллари").click()
    
    # page.get_by_role("link", name="Электрон шакллар").click()
    # page.get_by_role("link", name="Айланмадан олинадиган солиқ").click()
    # page.get_by_role("row", name="10190_12").get_by_role("link").click()
    # page.locator("select[name=\"na2_id\"]").select_option("100")
    # page.locator("#type").select_option("1")
    # page.locator("#year").select_option("2025")
    # page.locator("#perioddd").select_option("M_3")
    # page.locator("#report_form div").filter(has_text="Давр Январ Феврал Март Апрел Май Июн Июл Август Сентябр Октябр Ноябр Декабр").nth(1).click()
    # page.locator("#perioddd").click()

    url_1 = page.get_by_role("link", name="Айланмадан олинадиган солиқ ҳисоб-китоби").first
    url_1 = url_1.get_attribute('href')

    page1 = init_page()
    page1.goto(f"https://my.soliq.uz/{url_1}/")
    price1 = page1.locator("tr:nth-child(33) > td:nth-child(4) > div").first
    price1.screenshot(path='static/screenshot_1.png')
    price1 = extract_text_from_image("screenshot_1.png")

    return price1


def run2(page, pk, password):
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
        page_load.click()
    except:
        return 'incorrect_password_or_captcha'
    
    # page.get_by_role("link", name="ЯТТларнинг товар айланмалари бўйича ҳисобот шакллари").click()
    # page.get_by_role("link", name="Электрон шакллар").click()
    # page.get_by_role("link", name="Айланмадан олинадиган солиқ").click()
    # page.get_by_role("row", name="10190_12").get_by_role("link").click()
    # page.locator("select[name=\"na2_id\"]").select_option("100")
    # page.locator("#type").select_option("1")
    # page.locator("#year").select_option("2025")
    # page.locator("#perioddd").select_option("M_3")
    # page.locator("#report_form div").filter(has_text="Давр Январ Феврал Март Апрел Май Июн Июл Август Сентябр Октябр Ноябр Декабр").nth(1).click()
    # page.locator("#perioddd").click()

    url_1 = page.get_by_role("link", name="Айланмадан олинадиган солиқ ҳисоб-китоби").first
    url_1 = url_1.get_attribute('href')

    page1 = init_page()
    page1.goto(f"https://my.soliq.uz/{url_1}/")
    price1 = page1.locator("tr:nth-child(33) td:nth-child(4) div").first
    price1.screenshot(path='static/screenshot_1.png')
    price1 = extract_text_from_image("screenshot_1.png")

    return price1



@app.route('/', methods=['POST', 'GET'])
def index():
    data = request.args.get('data')
    if request.method == "POST":
        shutdown_browser()
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
        elif result == "completed":
            shutdown_browser()
            return render_template("index.html", data=result)
        else:
            shutdown_browser()
            print(result)
            return render_template("index.html", data=result)
    else:
        return(render_template("index.html", data=data))


@app.route('/captcha', methods=['POST', 'GET'])
def captcha_verify():
    if request.method == "POST":
        pk = request.form['capcha_input']
        result = app_run2(pk, password)
        if result == "completed":
            shutdown_browser()
            return redirect('/?data=completed')
        elif result == "incorrect_password_or_captcha":
            shutdown_browser()
            return redirect('/?data=incorrect_password_or_captcha')
        else:
            shutdown_browser()
            return redirect(f"/?data={result}")
    else:
        return render_template("captcha.html")


def app_run(inn, password):
    page = init_page()
    result = run(page, inn, password)
    return result


def app_run2(pk, password):
    page = init_page()
    result = run2(page, pk, password)
    return result

def shutdown_browser():
    global playwright, browser, page
    if page:
        print("❌ Закрытие вкладки...")
        page.close()
        page = None
    if browser:
        print("🛑 Закрытие браузера...")
        browser.close()
        browser = None
    if playwright:
        print("🧹 Остановка Playwright...")
        playwright.stop()
        playwright = None

if __name__ == "__main__":
    app.run(debug=True, threaded=False)
    # app.run(host='127.0.0.1', port=8070, debug=True, threaded=False)

