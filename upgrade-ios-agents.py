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

for ip in device_ips:
    print(f"\n[INFO] Connecting to {ip}...")

    cisco_device = {
        "device_type": "cisco_ios",
        "ip": ip,
        "username": USERNAME,
        "password": PASSWORD,
        "timeout": 120,
        "session_log": f"netmiko_{ip.replace('.', '_')}.log"
    }

    try:

        net_connect = ConnectHandler(**cisco_device)

        # Step 1: Detect App ID from `show app-hosting list`
        print("[INFO] Retrieving App ID...")
        app_list_output = net_connect.send_command("show app-hosting list")
        app_id_match = re.search(r"^(\S+)\s+RUNNING", app_list_output, re.MULTILINE)

        if not app_id_match:
            
            print("[WARNING] No running app found. Skipping device.")
            net_connect.disconnect()
            continue

        app_id = app_id_match.group(1)
        print(f"[INFO] Found app ID: {app_id}")

        upgrade_command = f"app-hosting upgrade appid {app_id} package {destination_file}"

        # Step 2: Ensure directory exists
        dir_output = net_connect.send_command(f"dir {destination_folder}")
        if "not a directory" in dir_output or "No such file" in dir_output:
            
            print(f"[INFO] Directory not found. Creating {destination_folder}")

            net_connect.send_command_timing(f"mkdir {destination_folder}", delay_factor=5)

        # Step 3: Validate URL
        if "urldefense" in file_url.lower() or "__" in file_url:
            
            print("[WARNING] Obfuscated URL detected. Skipping.")
            net_connect.disconnect()
            continue

        # Step 4: Copy image
        print(f"[INFO] Copying image to {destination_file}")
        net_connect.send_command("file prompt quiet")
        output = net_connect.send_command_timing(f"copy {file_url} {destination_file}", strip_prompt=False, strip_command=False)

        if "Destination filename" in output:
            
            output += net_connect.send_command_timing("\n", strip_prompt=False, strip_command=False)

        if "[confirm]" in output or "overwrite" in output.lower():
            
            output += net_connect.send_command_timing("\n", strip_prompt=False, strip_command=False)

        print("[INFO] Copy complete.")

        # Step 5: Upgrade app
        print(f"[INFO] Running upgrade command for {app_id}...")
        upgrade_output = net_connect.send_command(upgrade_command)
        print(upgrade_output)

        # Disconnect
        net_connect.disconnect()
        print(f"[OK] Finished with {ip}")

    except (NetmikoTimeoutException, NetmikoAuthenticationException) as error:
        
        print(f"[ERROR] Connection failed for {ip}: {error}")
    
    except Exception as general_error:
        
        print(f"[ERROR] Unexpected error on {ip}: {general_error}")
