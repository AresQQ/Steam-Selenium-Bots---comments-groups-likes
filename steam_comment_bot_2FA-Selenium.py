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

    # Wait for 60 seconds before fetching the 2FA code from email
    print("Waiting 60 seconds for 2FA email...")
    time.sleep(60)

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

    # Wait 5 seconds before continuing
    time.sleep(5)


# Function to post a comment on a Steam profile
def post_comment_in_new_tab(driver, profile_url, comment_text, last_tab=False):
    try:
        # Open a new tab and navigate to the profile
        driver.execute_script(f"window.open('{profile_url}', '_blank');")

        # Switch to the new tab
        driver.switch_to.window(driver.window_handles[-1])

        # Wait for the comment box to load
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'commentthread_entry_quotebox')))

        # Find the comment box
        comment_box_container = driver.find_element(By.CLASS_NAME, 'commentthread_entry_quotebox')
        comment_box = comment_box_container.find_element(By.CLASS_NAME, 'commentthread_textarea')

        # Type the comment
        comment_box.send_keys(comment_text)

        # Find the submit button and click it
        submit_button = driver.find_element(By.XPATH, "//span[contains(@class, 'btn_green_white_innerfade') and contains(@class, 'btn_small')]")
        submit_button.click()

        print(f"Comment posted on profile: {profile_url}")

        # Wait for a few seconds to ensure the comment is posted
        time.sleep(5)

        # Close the current tab if it's not the last tab
        if not last_tab:
            driver.close()
            driver.switch_to.window(driver.window_handles[0])

    except Exception as e:
        print(f"Error posting on profile {profile_url}: {str(e)}")


# Main function
def main():
    # Get the Steam login details from the user
    steam_username = input("Enter your Steam username: ")
    steam_password = input("Enter your Steam password: ")
    comment_text = input("Enter the comment to post: ")

    # List of profile URLs to post comments to
    profile_urls = [
        'https://steamcommunity.com/profiles/76561199773480552', #1
        'https://steamcommunity.com/profiles/76561199206555367', #2
        'https://steamcommunity.com/id/axellejtm/',              #3
        'https://steamcommunity.com/id/xfencly/',                #4
        'https://steamcommunity.com/id/ZyPact/',                 #5
        'https://steamcommunity.com/id/nick_woer/',              #6
        'https://steamcommunity.com/id/sayNn_8/',                #7
        'https://steamcommunity.com/profiles/76561198958759969/',#8
        'https://steamcommunity.com/profiles/76561199526159455/',#9
        'https://steamcommunity.com/profiles/76561198369076697/' #10
    ]

    # Path to the ChromeDriver
    chrome_driver_path = r'C:\chromedriver\chromedriver.exe'

    # Create the ChromeDriver service
    service = Service(chrome_driver_path)
    driver = webdriver.Chrome(service=service)

    try:
        # Log in to Steam
        steam_login(driver, steam_username, steam_password)

        # Post the comment to the profiles
        for index, profile_url in enumerate(profile_urls):
            # Check if it's the last profile URL
            last_tab = (index == len(profile_urls) - 1)

            # Post the comment, keeping the last tab open
            post_comment_in_new_tab(driver, profile_url, comment_text, last_tab)

            # Wait between opening new tabs
            if not last_tab:
                time.sleep(random.randint(5, 10))

        # Once all comments are posted, open the Steam community homepage
        driver.get("https://steamcommunity.com/")

        # Ask the user if they want to close the browser
        close_browser = input("Do you want to close the browser? (yes/no): ")
        if close_browser.lower() == 'yes':
            driver.quit()
        else:
            print("Browser will remain open.")

    except Exception as e:
        print(f"An error occurred: {str(e)}")


# Run the script
if __name__ == "__main__":
    main()


