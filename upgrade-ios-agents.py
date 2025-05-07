import re
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException
from getpass import getpass


# File with list of IPs
with open("device_list.txt", "r") as f:
    
    device_ips = [line.strip() for line in f if line.strip()]

USERNAME = input("Username: ")
PASSWORD = getpass("Password: ")

file_url = "https://downloads.thousandeyes.com/enterprise-agent/thousandeyes-enterprise-agent-x86_64-5.0.1.cisco.tar"
destination_folder = "bootflash:/te-apps"
destination_file = f"{destination_folder}/thousandeyes-enterprise-agent-x86_64-5.0.1.cisco.tar"
upgrade_command = f"app-hosting upgrade appid TE_Agent package {destination_file}"

for ip in device_ips:

    print(f"\n[INFO] Connecting to {ip}...")

    cisco_device = {
        "device_type": "cisco_ios",
        "ip": ip,
        "username": USERNAME,
        "password": PASSWORD,
    }

    try:

        net_connect = ConnectHandler(**cisco_device)

        # Check if directory exists
        dir_output = net_connect.send_command(f"dir {destination_folder}", use_textfsm=True)
        if "not a directory" in dir_output or "No such file" in dir_output:
        
            print(f"[INFO] Directory not found. Creating {destination_folder}")
            net_connect.send_command(f"mkdir {destination_folder}")

        # Check for HTTPS issues
        if "urldefense" in file_url.lower() or "__" in file_url:
        
            print("[WARNING] Obfuscated URL detected. Skipping.")
            net_connect.disconnect()
            continue

        # Copy the file
        print(f"[INFO] Copying image to {destination_file}")
        net_connect.send_command("file prompt quiet")
        output = net_connect.send_command_timing(f"copy {file_url} {destination_file}", strip_prompt=False, strip_command=False)

        if "Destination filename" in output:
        
            output += net_connect.send_command_timing("\n", strip_prompt=False, strip_command=False)

        if "[confirm]" in output or "overwrite" in output.lower():
        
            output += net_connect.send_command_timing("\n", strip_prompt=False, strip_command=False)

        print("[INFO] Copy complete.")

        # Upgrade the app
        print("[INFO] Running upgrade command !!!!")
        
        upgrade_output = net_connect.send_command(upgrade_command)
        
        print(upgrade_output)

        # Disconnect
        print("[--] Disconnecting ...!")
        net_connect.disconnect()
        print(f"[OK] Finished with {ip}")

    except (NetmikoTimeoutException, NetmikoAuthenticationException) as error:
        
        print(f"[ERROR] Connection failed for {ip}: {error}")
    
    except Exception as general_error:
        
        print(f"[ERROR] Unexpected error on {ip}: {general_error}")
