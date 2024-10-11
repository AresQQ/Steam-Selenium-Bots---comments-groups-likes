import random
import time
import os
import imaplib
import email
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from email.header import decode_header
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

# Get the Steam login details and account list
steam_accounts = os.getenv("STEAM_ACCOUNTS").split(',')
GMAIL_USERNAME = os.getenv("GMAIL_USERNAME")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")

# Check if Gmail credentials are loaded properly
if not GMAIL_USERNAME or not GMAIL_PASSWORD:
    raise ValueError("Gmail username or password is not set in the .env file.")

# Progress file to track where the script left off
PROGRESS_FILE = 'progress.txt'


# Function to retrieve the 2FA code from Gmail
def get_2fa_code_from_email():
    try:
        # Connect to Gmail's IMAP server
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USERNAME, GMAIL_PASSWORD)

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


# Function to log in to Steam and handle 2FA
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

    # Wait before fetching the 2FA code from email (15-20 seconds wait time)
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

    # Wait a few seconds before continuing
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


# Function to save progress to a file
def save_progress(index):
    with open(PROGRESS_FILE, "w") as f:
        f.write(str(index))


# Function to load progress from a file
def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            return int(f.read().strip())
    else:
        return 0  # Start from the beginning if no progress file exists


# Main function
def main():
    # Ask for the group link
    group_url = input("Enter the Steam Group URL: ")

    # Ask if the user wants to start from a specific account
    start_from_account = input("Do you want to start from a specific account? (yes/no): ").lower()

    if start_from_account == 'yes':
        # Get the index from the user
        while True:
            try:
                start_index = int(input(f"Enter the account index to start from (0 to {len(steam_accounts) - 1}): "))
                if 0 <= start_index < len(steam_accounts):
                    break
                else:
                    print("Invalid index. Please enter a valid number within the range.")
            except ValueError:
                print("Please enter a valid number.")
    else:
        start_index = load_progress()  # Load the saved progress if not specified

    while True:
        # Get the number of members to add
        target_member_count = int(input("Enter the number of members you want to add: "))

        # Path to the ChromeDriver
        chrome_driver_path = r'C:\chromedriver\chromedriver.exe'

        # Create the ChromeDriver service
        service = Service(chrome_driver_path)

        # Proceed with login and adding accounts
        for i, account in enumerate(steam_accounts[start_index:start_index + target_member_count]):
            username, password = account.split(":")

            # Reinitialize the driver for each new account to avoid session issues
            driver = webdriver.Chrome(service=service)
            try:
                # Log in to Steam
                steam_login(driver, username, password)

                # Check if the account is already a member of the group
                driver.get(group_url)
                time.sleep(random.randint(2, 4))  # Give time for the page to load

                try:
                    # Check if the account is already a member (if the button says 'Leave Group')
                    join_button = driver.find_element(By.CLASS_NAME, "btn_red_white_innerfade")
                    print(f"Account {username} is already a member. Skipping.")
                except:
                    # Join the group
                    join_group(driver)
                    print(f"Successfully added account {username}.")
            except Exception as e:
                print(f"An error occurred: {e}")
            finally:
                driver.quit()

            # Save progress after each account
            start_index += 1
            save_progress(start_index)

        # Ask if the user wants to add more members
        more_members = input("Do you want to add more members? (yes/no): ")
        if more_members.lower() != "yes":
            break


# Start the script
if __name__ == "__main__":
    main()






