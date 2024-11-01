import os
import time
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import pyautogui
import subprocess
import psutil  # Import the psutil library

# Load environment variables from the .env file
load_dotenv()

# Get Gmail credentials from environment variables
gmail_user = os.getenv("GMAIL_USERNAME")
gmail_password = os.getenv("GMAIL_PASSWORD")

# Check if Gmail credentials are loaded properly
if not gmail_user or not gmail_password:
    raise ValueError("Gmail username or password is not set in the .env file.")

# Parse Steam accounts from environment variable
steam_accounts_raw = os.getenv("STEAM_ACCOUNTS")
if not steam_accounts_raw:
    raise ValueError("Steam accounts not found in the .env file.")

# Split the accounts and create a list of dictionaries
accounts = [
    {"username": acc.split(':')[0], "password": acc.split(':')[1]}
    for acc in steam_accounts_raw.split(',')
]

# Function to retrieve the 2FA code from Gmail with retries
def get_2fa_code_from_email(retry_attempts=5, retry_delay=5):
    for attempt in range(retry_attempts):
        try:
            # Connect to Gmail's IMAP server
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(gmail_user, gmail_password)
            mail.select("inbox")

            # Get the current time and calculate the time window
            now = datetime.now()
            five_minutes_ago = now - timedelta(minutes=5)
            search_time = five_minutes_ago.strftime("%d-%b-%Y")

            # Search for unread emails from noreply@steampowered.com within the last 5 minutes
            status, messages = mail.search(None, f'(UNSEEN FROM "noreply@steampowered.com" SINCE "{search_time}")')
            if status != "OK":
                print("No recent unread emails from Steam found.")
                time.sleep(retry_delay)
                continue

            # Get the latest email
            messages = messages[0].split()
            latest_email_id = messages[-1]

            # Fetch the email
            status, msg_data = mail.fetch(latest_email_id, "(RFC822)")
            if status != "OK":
                print("Failed to fetch email.")
                time.sleep(retry_delay)
                continue

            # Parse the email content
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])

                    # Check if the sender is noreply@steampowered.com
                    if "noreply@steampowered.com" in msg["From"]:
                        # If the email is multipart, check for HTML part
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/html":
                                    html_content = part.get_payload(decode=True).decode()
                                    soup = BeautifulSoup(html_content, "html.parser")
                                    code_td = soup.find("td", style=lambda value: value and "font-size:48px" in value)
                                    if code_td:
                                        return code_td.get_text(strip=True)
                        # For non-multipart email, check the plain body
                        else:
                            body = msg.get_payload(decode=True).decode()
                            code = ''.join(filter(str.isdigit, body))
                            if len(code) == 5:
                                return code

            print("2FA code not found in email. Retrying in", retry_delay, "seconds...")
            time.sleep(retry_delay)

        except Exception as e:
            print(f"Error retrieving 2FA code: {str(e)}. Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)

    print("Failed to retrieve 2FA code after multiple attempts.")
    return None

# Function to check if Steam is running
def is_steam_running():
    return any("steam.exe" in p.name().lower() for p in psutil.process_iter())

# Function to start Steam if not already running
def start_steam():
    steam_path = "D:\\Steam\\steam.exe"  # Adjust path as needed
    if not is_steam_running():
        print("Starting Steam...")
        subprocess.Popen([steam_path])
        time.sleep(5)  # Wait for Steam to launch

# Function to log into Steam
def steam_login(steam_username, steam_password):
    print(f"Attempting to log in to Steam account: {steam_username}")
    start_steam()  # Ensure Steam is open

    # Focus on Steam login window and enter credentials
    pyautogui.write(steam_username)
    pyautogui.press('tab')
    pyautogui.write(steam_password)
    pyautogui.press('enter')

    # Wait for 2FA input field
    time.sleep(5)

    # Retrieve the 2FA code with retry mechanism
    steam_2fa_code = get_2fa_code_from_email()

    if steam_2fa_code:
        pyautogui.write(steam_2fa_code)
        pyautogui.press('enter')
        print("Logged in successfully!")
    else:
        print("Failed to retrieve 2FA code.")

# Function to launch Counter-Strike 2 and connect to the server
def launch_counter_strike():
    print("Launching Counter-Strike 2...")
    os.system("start steam://launch/730/-console")
    time.sleep(7)

    print("Pressing ESC to skip intro...")
    pyautogui.press('esc')
    time.sleep(2)
    pyautogui.press('esc')
    time.sleep(2)

    print("Opening console...")
    pyautogui.press('`')
    time.sleep(5)

    print("Connecting to the server...")
    pyautogui.write("connect imbaboost.ggwp.cc:26876")
    pyautogui.press('enter')

# Main function
def main():
    account_index = int(input("Enter the account index to log in (or -1 to exit): "))

    if account_index == -1:
        print("Exiting...")
        return

    if account_index >= len(accounts) or account_index < 0:
        print("Invalid account index.")
        return

    steam_username = accounts[account_index]["username"]
    steam_password = accounts[account_index]["password"]

    time.sleep(2)
    steam_login(steam_username, steam_password)

    time.sleep(3)
    launch_counter_strike()

# Run the script
if __name__ == "__main__":
    main()
















