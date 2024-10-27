import os
import time
import pyautogui
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the Steam login details from the environment variable
steam_accounts = os.getenv("STEAM_ACCOUNTS").split(',')

# Function to focus on the Steam window
def focus_steam_window():
    os.startfile("D:\\Steam\\steam.exe")  # Adjust the path as necessary
    time.sleep(10)  # Wait for Steam to open
    pyautogui.getWindowsWithTitle("Steam")[0].activate()  # Activate Steam window
    time.sleep(2)

# Function to log in to Steam
def steam_login(username, password):
    focus_steam_window()  # Ensure Steam is open and focused

    # Enter the username
    pyautogui.click(x=1600, y=625)  # Click on the username input
    time.sleep(1)
    pyautogui.write(username)  # Type the username
    time.sleep(1)

    # Enter the password
    pyautogui.click(x=1500, y=700)  # Click on the password input
    time.sleep(1)
    pyautogui.write(password)  # Type the password
    time.sleep(1)

    # Click the Login button
    pyautogui.click(x=1600, y=790)  # Click on the login button
    time.sleep(5)  # Wait for the login process

# Main function
def main():
    while True:
        # Display account options
        print("Available accounts:")
        for index, account in enumerate(steam_accounts):
            print(f"{index}: {account.split(':')[0]}")  # Show only the username

        # Prompt for account index
        try:
            start_index = int(input("Enter the account index to log in (or -1 to exit): "))
        except ValueError:
            print("Please enter a valid index.")
            continue

        if start_index == -1:
            print("Exiting...")
            break
        if start_index < 0 or start_index >= len(steam_accounts):
            print("Invalid index. Please try again.")
            continue

        username, password = steam_accounts[start_index].split(":")
        print(f"Logging into account {username} at position {start_index}...")
        steam_login(username, password)

# Start the script
if __name__ == "__main__":
    main()
