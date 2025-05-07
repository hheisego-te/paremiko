import re
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException
from getpass import getpass

# Read list of IPs
with open("device_list.txt", "r") as f:
    device_ips = [line.strip() for line in f if line.strip()]

USERNAME = input("Username: ")
PASSWORD = getpass("Password: ")

# Remote image URL and destination
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
        "conn_timeout": 30,
        "banner_timeout": 60,
        "session_timeout": 120,
        "timeout": 120,
        "session_log": f"netmiko_{ip.replace('.', '_')}.log"
    }

    try:
        net_connect = ConnectHandler(**cisco_device)

        # Get App ID
        print("[INFO] Retrieving App ID...")
        app_list_output = net_connect.send_command("show app-hosting list", expect_string=r"#")
        app_id_match = re.search(r"^(\S+)\s+RUNNING", app_list_output, re.MULTILINE)

        if not app_id_match:
            
            print("[WARNING] No running app found. Skipping device.")
            net_connect.disconnect()
            continue

        app_id = app_id_match.group(1)
        print(f"[INFO] Found app ID: {app_id}")
        upgrade_command = f"app-hosting upgrade appid {app_id} package {destination_file}"

        # Ensure destination folder exists
        dir_output = net_connect.send_command(f"dir {destination_folder}", expect_string=r"#")
        if "not a directory" in dir_output or "No such file" in dir_output:
            
            print(f"[INFO] Directory not found. Creating {destination_folder}")
            net_connect.send_command(f"mkdir {destination_folder}", expect_string=r"#")

        # Check for obfuscated URL
        if "urldefense" in file_url.lower() or "__" in file_url:
            
            print("[WARNING] Obfuscated URL detected. Skipping.")
            net_connect.disconnect()
            continue

        # Copy file
        print(f"[INFO] Copying image to {destination_file}")
        net_connect.send_command("file prompt quiet", expect_string=r"#")
        output = net_connect.send_command_timing(
            f"copy {file_url} {destination_file}",
            delay_factor=4,
            timeout=120,
            strip_prompt=False,
            strip_command=False
        )

        if "Destination filename" in output:
            
            output += net_connect.send_command_timing("\n", delay_factor=2)

        if "[confirm]" in output or "overwrite" in output.lower():
            
            output += net_connect.send_command_timing("\n", delay_factor=2)

        print("[INFO] Copy complete.")

        # Upgrade app
        print(f"[INFO] Running upgrade command for {app_id}...")
        upgrade_output = net_connect.send_command(upgrade_command, expect_string=r"#", delay_factor=4, timeout=120)
        print(upgrade_output)

        # Disconnect
        net_connect.disconnect()
        print(f"[OK] Finished with {ip}")

    except (NetmikoTimeoutException, NetmikoAuthenticationException) as error:
        
        print(f"[ERROR] Connection failed for {ip}: {error}")
    
    except Exception as general_error:
        
        print(f"[ERROR] Unexpected error on {ip}: {general_error}")
