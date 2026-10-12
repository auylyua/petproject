"""
Автоотметка посещения на wsp.kbtu.kz.
Запускай САМА, когда ты уже на паре. Скрипт ждёт появления кнопок и нажимает их.
Работает до истечения MAX_WAIT_MIN или пока ты не нажмёшь Ctrl+C.
"""
import os
import sys
import time

import requests
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

URL = "https://wsp.kbtu.kz/"
ATT_URL = "https://wsp.kbtu.kz/RegistrationOnline"
LOGIN = os.getenv("WSP_LOGIN")
PASSWORD = os.getenv("WSP_PASSWORD")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

CHECK_EVERY = 10          # секунд между проверками
MAX_WAIT_MIN = 200        # через сколько минут остановиться
HEADLESS = os.getenv("HEADLESS") == "1"   # с телефона запускается без окна          # False = видно окно браузера

MENU_ITEM = "Отметка посещения занятия"

# Только видимые кнопки с текстом (скрытые и иконочные игнорируем)
BASE_BTN = ".v-button:visible:not(.v-button-icon-only):not(.v-button-quiet)"
ACTIVE_BTN = BASE_BTN + ":not(.v-disabled):not(.v-button-disabled)"


def notify(text: str) -> None:
    print(text)
    if TG_TOKEN and TG_CHAT_ID:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                data={"chat_id": TG_CHAT_ID, "text": text},
                timeout=10,
            )
        except Exception as e:  # noqa: BLE001
            print("Telegram не отправился:", e)


def login(page) -> None:
    page.goto(URL)
    page.wait_for_selector("input[type=password]", timeout=30000)
    page.locator("input[type=text]").first.fill(LOGIN)
    pw = page.locator("input[type=password]")
    pw.fill(PASSWORD)
    pw.press("Enter")
    page.wait_for_selector(f"text={MENU_ITEM}", timeout=30000)


def open_attendance(page) -> None:
    page.goto(ATT_URL)
    page.wait_for_selector(".v-app", timeout=30000)
    page.wait_for_timeout(2000)
    if page.locator("input[type=password]:visible").count() > 0:
        login(page)
        page.goto(ATT_URL)
        page.wait_for_selector(".v-app", timeout=30000)
        page.wait_for_timeout(2000)


def click_all_active(page) -> int:
    """Нажимает все активные кнопки отметки. Возвращает, сколько нажато."""
    clicked = 0
    active = page.locator(ACTIVE_BTN)
    while active.count() > 0 and clicked < 10:
        before = active.count()
        active.first.click(timeout=5000)
        page.wait_for_timeout(1500)
        clicked += 1
        if page.locator(ACTIVE_BTN).count() >= before:
            break  # кнопка не сменилась, не нажимаем бесконечно
    return clicked


def main() -> None:
    if not LOGIN or not PASSWORD:
        sys.exit("Заполни WSP_LOGIN и WSP_PASSWORD в файле .env")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        page = browser.new_page()
        login(page)
        notify("Вошла в систему, жду кнопки отметки…")

        total = 0
        deadline = time.time() + MAX_WAIT_MIN * 60
        while time.time() < deadline:
            try:
                open_attendance(page)
                n = click_all_active(page)
                if n:
                    total += n
                    notify(f"Отметилась ✅ (нажато кнопок: {n}, всего: {total})")
            except Exception as e:  # noqa: BLE001
                print("Ошибка, пробую снова:", e)
                try:
                    login(page)
                except Exception:  # noqa: BLE001
                    pass
            time.sleep(CHECK_EVERY)

        notify(f"Время работы вышло, бот остановлен. Всего отметок: {total}")
        browser.close()


if __name__ == "__main__":
    main()