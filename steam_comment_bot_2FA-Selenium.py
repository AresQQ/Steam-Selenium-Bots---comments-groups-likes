# Comment bot for steam - Bot do publikowania komentarzy na steam z 2FA

import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Funkcja do logowania na Steam
def steam_login(driver, steam_username, steam_password):
    driver.get("https://steamcommunity.com/login/home/")

    # Poczekaj na pole do wprowadzenia loginu
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "_2GBWeup5cttgbTw8FM3tfx")))

    # Wprowadź login
    username_field = driver.find_element(By.CLASS_NAME, "_2GBWeup5cttgbTw8FM3tfx")
    username_field.send_keys(steam_username)

    # Wprowadź hasło szuka elementu po selektorze bo username miał tą samą klase co password
    password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    password_field.send_keys(steam_password)

    # Kliknij przycisk logowania
    login_button = driver.find_element(By.CLASS_NAME, "DjSvCZoKKfoNSmarsEcTS")
    login_button.click()

    # Poczekaj na pole do wpisania kodu 2FA
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "twofactorcode_entry")))

    # Wprowadź kod 2FA
    if "Steam Guard" in driver.page_source:
        steam_2fa_code = input("Podaj kod 2FA: ")

        # Wprowadź kod do pola - na steam nie ma submit guzika wiec po wpisaniu kodu sam sie loguje
        two_factor_fields = driver.find_elements(By.CLASS_NAME, "_3xcXqLVteTNHmk-gh9W65d")
        for i, digit in enumerate(steam_2fa_code):
            if i < len(two_factor_fields):
                two_factor_fields[i].send_keys(digit)

        print("Zalogowano pomyślnie!")

    else:
        print("Błąd logowania. Sprawdź dane logowania.")

    # Poczekaj 5 sekund, aby upewnić się, że logowanie jest zakończone
    time.sleep(5)


# Funkcja do publikowania komentarza na profilu w nowej zakładce
def post_comment_in_new_tab(driver, profile_url, comment_text):
    try:
        # Otwórz nową zakładkę i przejdź do profilu
        driver.execute_script(f"window.open('{profile_url}', '_blank');")

        # Przełącz się do nowo otwartej zakładki
        driver.switch_to.window(driver.window_handles[-1])

        # Poczekaj, aż div kontenera pola komentarza się załaduje
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'commentthread_entry_quotebox')))

        # Zlokalizuj div kontener pola komentarza
        comment_box_container = driver.find_element(By.CLASS_NAME, 'commentthread_entry_quotebox')

        # Znajdź textarea wewnątrz div
        comment_box = comment_box_container.find_element(By.CLASS_NAME, 'commentthread_textarea')

        # Wpisz komentarz do textarea
        comment_box.send_keys(comment_text)

        # Zlokalizuj przycisk "Post Comment" i kliknij go
        submit_button = driver.find_element(By.XPATH, "//span[contains(@class, 'btn_green_white_innerfade') and contains(@class, 'btn_small')]")
        submit_button.click()

        print(f"Komentarz został opublikowany na profilu: {profile_url}")

        # Poczekaj kilka sekund, aby komentarz został opublikowany
        time.sleep(5)

        # Zamknij aktualną zakładkę
        driver.close()

        # Przełącz się z powrotem do pierwszej zakładki
        driver.switch_to.window(driver.window_handles[0])

    except Exception as e:
        print(f"Błąd podczas publikowania na profilu {profile_url}: {str(e)}")



# Główna funkcja
def main():
    # Pobierz dane logowania od użytkownika
    steam_username = input("Podaj login Steam: ")
    steam_password = input("Podaj hasło Steam: ")

    # Komentarz do publikacji
    comment_text = input("Podaj komentarz do opublikowania: ")

    # Lista URL-ów profili (mozna dodac max 10 profili bo takie jest ograniczenie do postowania komnentarzy z jednego konta - 10 dziennie.)
    profile_urls = [
        'https://steamcommunity.com/profiles/76561199773480552',
        'https://steamcommunity.com/profiles/76561199206555367',
        'https://steamcommunity.com/id/axellejtm/',
        'https://steamcommunity.com/id/xfencly/',
        'https://steamcommunity.com/id/ZyPact/',
        'https://steamcommunity.com/id/nick_woer/',
        'https://steamcommunity.com/id/sayNn_8/',
        'https://steamcommunity.com/profiles/76561198958759969/',
        'https://steamcommunity.com/profiles/76561199526159455/',
        'https://steamcommunity.com/profiles/76561198171008581/'
    ]

    # Ścieżka do ChromeDriver
    chrome_driver_path = r'C:\chromedriver\chromedriver.exe'

    # Tworzenie obiektu Service dla ChromeDriver
    service = Service(chrome_driver_path)

    # Inicjalizacja WebDriver z użyciem Service
    driver = webdriver.Chrome(service=service)

    try:
        # Logowanie na Steam
        steam_login(driver, steam_username, steam_password)

        # Publikowanie komentarza na 10 różnych profilach w nowych zakładkach
        for profile_url in profile_urls:
            post_comment_in_new_tab(driver, profile_url, comment_text)

            # Opóźnienie pomiędzy zamknięciem jednej zakładki a otwarciem nowej (4-8 sekund aby nie spamowało dodałem opoznienie)
            delay = random.randint(4, 8)
            print(f"Oczekiwanie {delay} sekund przed otwarciem kolejnej zakładki...")
            time.sleep(delay)

    finally:
        # Zamknij przeglądarkę po zakończeniu
        driver.quit()


if __name__ == "__main__":
    main()