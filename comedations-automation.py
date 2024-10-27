import os
import time
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
from bs4 import BeautifulSoup  # For HTML parsing
from dotenv import load_dotenv
import pyautogui  # For GUI automation

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


# Function to retrieve the 2FA code from Gmail
def get_2fa_code_from_email():
    for attempt in range(5):
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
            print("Retrying in 5 seconds...")
            time.sleep(5)

    print("Failed to retrieve 2FA code after multiple attempts.")
    return None


# Function to focus the Steam window
def focus_steam_window():
    steam_path = "D:\\Steam\\steam.exe"  # Adjusted path for Steam
    if os.path.exists(steam_path):
        os.startfile(steam_path)  # Launch Steam
        time.sleep(1)  # Wait for Steam to open
        # Activate Steam window
        windows = pyautogui.getWindowsWithTitle("Steam")
        if windows:
            windows[0].activate()  # Activate Steam window
            time.sleep(2)
        else:
            print("Steam window not found.")
    else:
        print("Steam executable not found at the specified path.")


# Function to log into Steam
def steam_login(steam_username, steam_password):
    print(f"Attempting to log in to Steam account: {steam_username}")
    focus_steam_window()  # Ensure Steam is open and focused

    time.sleep(1)  # Reduced time for better efficiency

    # Enter the username
    pyautogui.write(steam_username)
    pyautogui.press('tab')  # Move to password field
    pyautogui.write(steam_password)  # Type the password
    pyautogui.press('enter')  # Submit the login

    # Wait for the 2FA code entry to appear
    time.sleep(5)  # Reduced from 15 seconds to 5 seconds

    # Now retrieve the 2FA code from Gmail
    steam_2fa_code = get_2fa_code_from_email()

    if steam_2fa_code:
        # Enter the 2FA code into the Steam input field
        pyautogui.write(steam_2fa_code)
        pyautogui.press('enter')  # Submit the 2FA code
        print("Logged in successfully!")
    else:
        print("Failed to retrieve 2FA code.")


# Function to launch Counter-Strike 2 with the console option and connect to the server
def launch_counter_strike():
    print("Launching Counter-Strike 2...")
    os.system("start steam://launch/730/-console")  # Launch CS2 with console option
    time.sleep(7)  # Wait for the game to fully load

    print("Pressing ESC to skip intro...")
    pyautogui.press('esc')  # Skip the intro
    time.sleep(2)  # Wait a moment after pressing ESC

    print("Pressing ESC again...")
    pyautogui.press('esc')  # Skip any additional loading screens
    time.sleep(2)  # Wait for a moment

    print("Opening console...")
    pyautogui.press('`')  # Open the console using the backtick key directly
    time.sleep(5)  # Wait longer for the console to be ready

    print("Connecting to the server...")
    pyautogui.write("connect imbaboost.ggwp.cc:26876")  # Type the connect command
    pyautogui.press('enter')  # Execute the connect command


# Main function
def main():
    # Load account index from user input
    account_index = int(input("Enter the account index to log in (or -1 to exit): "))

    if account_index == -1:
        print("Exiting...")
        return

    if account_index >= len(accounts) or account_index < 0:
        print("Invalid account index.")
        return

    steam_username = accounts[account_index]["username"]
    steam_password = accounts[account_index]["password"]

    time.sleep(1)  # Reduced wait time to 1 second before login
    steam_login(steam_username, steam_password)

    # Delay before launching Counter-Strike 2
    time.sleep(3)  # Adjusted to 3 seconds before launching
    launch_counter_strike()


# Run the script
if __name__ == "__main__":
    main()














