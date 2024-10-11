import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
from bs4 import BeautifulSoup  # BeautifulSoup for HTML parsing
from dotenv import load_dotenv
import os

# Load environment variables from the .env file
load_dotenv()

# Get Gmail credentials from the environment variables
gmail_user = os.getenv("GMAIL_USERNAME")
gmail_password = os.getenv("GMAIL_PASSWORD")

# Check if Gmail credentials are loaded properly
if not gmail_user or not gmail_password:
    raise ValueError("Gmail username or password is not set in the .env file.")

# Function to retrieve the 2FA code from Gmail
def get_2fa_code_from_email():
    try:
        # Connect to Gmail's IMAP server
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(gmail_user, gmail_password)

        # Select the inbox
        mail.select("inbox")

        # Get the current time and calculate the time window (e.g., the last 5 minutes)
        now = datetime.now()
        five_minutes_ago = now - timedelta(minutes=5)

        # Convert to the correct format for searching (IMAP search format)
        search_time = five_minutes_ago.strftime("%d-%b-%Y")

        # Search for unread emails from noreply@steampowered.com received within the last 5 minutes
        status, messages = mail.search(None, f'(UNSEEN FROM "noreply@steampowered.com" SINCE "{search_time}")')

        if status != "OK":
            print("No recent unread emails from Steam found.")
            return None

        # Get the latest email
        messages = messages[0].split()
        latest_email_id = messages[-1]

        # Fetch the email
        status, msg_data = mail.fetch(latest_email_id, "(RFC822)")
        if status != "OK":
            print("Failed to fetch email.")
            return None

        # Parse the email content
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding if encoding else 'utf-8')

                # Check if the sender is noreply@steampowered.com
                if "noreply@steampowered.com" in msg["From"]:
                    # If the email is multipart
                    if msg.is_multipart():
                        for part in msg.walk():
                            # Look for the HTML part
                            if part.get_content_type() == "text/html":
                                html_content = part.get_payload(decode=True).decode()
                                # Parse the HTML to find the 2FA code
                                soup = BeautifulSoup(html_content, "html.parser")
                                # Find the <td> that contains the code
                                code_td = soup.find("td", style=lambda value: value and "font-size:48px" in value)
                                if code_td:
                                    return code_td.get_text(strip=True)

                    # If the email is not multipart, just look at the plain body
                    else:
                        body = msg.get_payload(decode=True).decode()
                        # Try to extract the 5-digit code from the body text
                        code = ''.join(filter(str.isdigit, body))
                        if len(code) == 5:
                            return code

        print("2FA code not found in email.")
        return None

    except Exception as e:
        print(f"Error retrieving 2FA code: {str(e)}")
        return None

# Function to log in to Steam and handle the 2FA input manually
def steam_login(driver, steam_username, steam_password):
    driver.get("https://steamcommunity.com/login/home/")

    # Wait for the username field to load
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "_2GBWeup5cttgbTw8FM3tfx")))

    # Enter the username
    username_field = driver.find_element(By.CLASS_NAME, "_2GBWeup5cttgbTw8FM3tfx")
    username_field.send_keys(steam_username)

    # Enter the password
    password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    password_field.send_keys(steam_password)

    # Click the login button
    login_button = driver.find_element(By.CLASS_NAME, "DjSvCZoKKfoNSmarsEcTS")
    login_button.click()

    # Wait for the 2FA page to load (check if the 2FA code field appears)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "twofactorcode_entry")))

    # Wait before fetching the 2FA code from email sometimes problem occur when time is too low so random between 15-20 works fine
    print("Waiting for 2FA email...")
    time.sleep(random.randint(15, 20))

    # Now retrieve the 2FA code from Gmail
    steam_2fa_code = get_2fa_code_from_email()

    if steam_2fa_code:
        # Enter the 2FA code into the Steam 2FA input fields
        two_factor_fields = driver.find_elements(By.CLASS_NAME, "_3xcXqLVteTNHmk-gh9W65d")
        for i, digit in enumerate(steam_2fa_code):
            if i < len(two_factor_fields):
                two_factor_fields[i].send_keys(digit)

        print("Logged in successfully!")
    else:
        print("Failed to retrieve 2FA code.")

    # Wait few seconds before continuing
    time.sleep(random.randint(2, 5))

# Function to join a group on Steam
def join_group(driver):
    try:
        # Wait for the "Join Group" button to become visible and clickable
        join_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a.btn_green_white_innerfade.btn_medium"))
        )

        # Click the "Join Group" button (this will trigger the form submission)
        join_button.click()

        print("Successfully clicked the 'Join Group' button!")
        print("You have successfully joined the group!")

    except Exception as e:
        print(f"Failed to join the group: {str(e)}")

# Main function
def main():
    # Get the Steam login details from the user
    steam_username = input("Enter your Steam username: ")
    steam_password = input("Enter your Steam password: ")

    # URL of the Steam group to join
    group_url = 'https://steamcommunity.com/groups/PONKEARMY'

    # Path to the ChromeDriver
    chrome_driver_path = r'C:\chromedriver\chromedriver.exe'

    # Create the ChromeDriver service
    service = Service(chrome_driver_path)
    driver = webdriver.Chrome(service=service)

    try:
        # Log in to Steam
        steam_login(driver, steam_username, steam_password)

        # Navigate to the group page
        driver.get(group_url)

        # Join the Steam group
        join_group(driver)

        # Keep the browser open to see if everything works
        print("The browser will remain open for you to verify.")
        input("Press Enter to close the browser...")

        # Once user confirms, close the browser
        driver.quit()

    except Exception as e:
        print(f"An error occurred: {str(e)}")

# Run the script
if __name__ == "__main__":
    main()
