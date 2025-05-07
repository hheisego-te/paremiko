from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException
from getpass import getpass
import re

# Prompt user
device_ip = input("What device do you need to modify (IP address)? ")
USERNAME = input("What username would you like to use for login? ")
PASSWORD = getpass("What password is used for this account? ")

# Connection parameters
cisco_device = {
    "device_type": "cisco_ios",
    "ip": device_ip,
    "username": USERNAME,
    "password": PASSWORD,
}

try:
    net_connect = ConnectHandler(**cisco_device)
except (NetmikoTimeoutException, NetmikoAuthenticationException) as error:
    print(f"Connection failed: {error}")
    exit(1)
except Exception as general_error:
    print(f"An unexpected error occurred: {general_error}")
    exit(1)

# Define URL
file_url = "https://downloads.thousandeyes.com/enterprise-agent/thousandeyes-enterprise-agent-x86_64-5.0.1.cisco.tar"
destination = "bootflash:/apps"

# Extra: Verificar si la URL es limpia
if "urldefense" in file_url.lower() or "__" in file_url:
    print("Warning: URL seems obfuscated by a security system (urldefense). Please use a clean URL.")
    exit(1)

copy_command = f"copy {file_url} {destination}"

print(f"Running copy command: {copy_command}")

# Disable confirmation prompts temporarily
net_connect.send_command("file prompt quiet")

# Send the copy command in raw timing mode
output = net_connect.send_command_timing(copy_command, strip_prompt=False, strip_command=False)

print("Initial output after sending copy:")
print(repr(output))

# Handle prompts
if "Destination filename" in output:
    output += net_connect.send_command_timing("\n", strip_prompt=False, strip_command=False)
    print("Responded to Destination filename prompt.")

if "[confirm]" in output or "overwrite" in output.lower():
    output += net_connect.send_command_timing("\n", strip_prompt=False, strip_command=False)
    print("Responded to overwrite/confirm prompt.")

# Final output
print("Final output:")
print(output)

# Restore normal file prompt behavior if needed (optional)
# net_connect.send_command("file prompt alert")

net_connect.disconnect()
