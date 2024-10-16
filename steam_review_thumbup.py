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

# Get the Steam login details and account list from the .env file
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

# Function to vote "Yes" on a review
def vote_yes(driver):
    try:
        # Wait for the "Yes" button to be visible and clickable
        yes_button = WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.ID, "RecommendationVoteUpBtn172274536"))  # Update ID as needed
        )
        yes_button.click()
        print("Successfully voted 'Yes' on the review.")

        # Wait briefly to ensure the vote action is registered
        time.sleep(random.uniform(1.5, 2.5))

    except Exception as e:
        print(f"Failed to vote 'Yes' on the review: {e}")

# Function to log out of Steam
def steam_logout(driver):
    try:
        # Navigate to the Steam logout page
        driver.get("https://store.steampowered.com/logout/")
        print("Logged out of Steam.")
        time.sleep(2)  # Wait for logout to process
    except Exception as e:
        print(f"Failed to log out: {e}")

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
    # Ask for the Steam item URL
    item_url = input("Enter the Steam review URL: ")

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

    # Path to the ChromeDriver
    chrome_driver_path = r'C:\chromedriver\chromedriver.exe'  # Update to the correct path

    # Get the number of votes to add
    target_vote_count = int(input("Enter the number of 'Yes' votes you want to add: "))

    # Loop through the selected accounts starting from the specified index
    for i in range(start_index, len(steam_accounts)):
        username, password = steam_accounts[i].split(":")
        print(f"Processing account {username}...")

        # Create a new instance of Chrome WebDriver
        driver = webdriver.Chrome(service=Service(chrome_driver_path))

        try:
            # Log in to Steam
            steam_login(driver, username, password)

            # Navigate to the review URL
            driver.get(item_url)
            time.sleep(random.uniform(2, 5))  # Random wait for page to load

            # Perform voting "Yes" actions
            for _ in range(target_vote_count):
                vote_yes(driver)

            print(f"Processed account {username}.")

        except Exception as e:
            print(f"An error occurred with account {username}: {e}")

        # Log out from Steam before moving to the next account
        steam_logout(driver)

        # Save progress after each account
        save_progress(i + 1)  # Save the next account index

        # Ensure the driver quits after processing all votes for the account
        driver.quit()  # Quit the driver only after all actions are completed

        # Optional wait before starting the next account
        time.sleep(random.uniform(2, 5))

if __name__ == "__main__":
    main()
