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

        app_id = app_id_match.group(1)
        if not app_id_match:

            print("[WARNING] No running app found. Using TE-Agent.")
            app_id = "TE-Agent"

        else:

            app_id = app_id_match.group(1)
            print(f"[INFO] Found app ID: {app_id}")


        upgrade_command = f"app-hosting upgrade appid {app_id} package {destination_file}"

        # Step 2: Ensure directory exists
        dir_output = net_connect.send_command(f"dir {destination_folder}")
        print(f"[DEBUG] dir {destination_folder} →\n{dir_output}")

        if "not a directory" in dir_output or "No such file" in dir_output or "%Error opening" in dir_output:

            print(f"[INFO] Directory not found. Creating {destination_folder}")

            mkdir_output = net_connect.send_command_timing(f"mkdir {destination_folder}", strip_prompt=False, strip_command=False, delay_factor=10)
            
            # this confirm was missing?
            if '[te-apps]' in mkdir_output or 'confirm' in mkdir_output.lower():

                mkdir_output += net_connect.send_command_timing('\n', strip_prompt=False, strip_command=False)

            print(f"[DEBUG] mkdir output →\n{mkdir_output}")

        # Step 3: Validate URL
        if "urldefense" in file_url.lower() or "__" in file_url:
            
            print("[WARNING] Obfuscated URL detected. Skipping.")
            net_connect.disconnect()
            continue

        # Step 4: Copy image
        print(f"[INFO] Copying image to {destination_file}")
       
        output = net_connect.send_command_timing(f"copy {file_url} {destination_file}", strip_prompt=False, strip_command=False, delay_factor=20)

        if "Destination filename" in output:
            
            output += net_connect.send_command_timing("\n", strip_prompt=False, strip_command=False)

        if "[confirm]" in output or "overwrite" in output.lower():
            
            output += net_connect.send_command_timing("\n", strip_prompt=False, strip_command=False)

        print(f"[INFO] Copy complete. \n{output}")

        # Step 5: Upgrade app
        print(f"[INFO] Running upgrade command for {app_id}...")

        upgrade_output = net_connect.send_command(upgrade_command, delay_factor=15)
        
        print(upgrade_output)

        # Disconnect
        net_connect.disconnect()
        print(f"[OK] Finished with {ip}")

    except (NetmikoTimeoutException, NetmikoAuthenticationException) as error:
        
        print(f"[ERROR] Connection failed for {ip}: {error}")
    
    except Exception as general_error:
        
        print(f"[ERROR] Unexpected error on {ip}: {general_error}")



"""
caagh-1000eyes-temp-as1# caagh-1000eyes-temp-as1#terminal width 511 caagh-1000eyes-temp-as1#terminal length 0 caagh-1000eyes-temp-as1# caagh-1000eyes-temp-as1# caagh-1000eyes-temp-as1#show app-hosting list App id State
CAAGH_TE RUNNING
caagh-1000eyes-temp-as1#
caagh-1000eyes-temp-as1#dir bootflash:/te-apps
%Error opening flash:/te-apps (No such file or directory)
caagh-1000eyes-temp-as1#mkdir bootflash:/te-apps
Create directory filename [te-apps]?
Created dir flash:/te-apps
caagh-1000eyes-temp-as1#

caagh-1000eyes-temp-as1#copy https://downloads.thousandeyes.com/enterprise-agent/thousandeyes-enterprise-agent-x86_64-5.0.1.cisco.tar bootflash:/te-apps/thousandeyes-enterprise-agent-x86_64-5.0.1.cisco.tar
Destination filename [/te-apps/thousandeyes-enterprise-agent-x86_64-5.0.1.cisco.tar]?
Accessing https://downloads.thousandeyes.com/enterprise-agent/thousandeyes-enterprise-agent-x86_64-5.0.1.cisco.tar...
Loading https://downloads.thousandeyes.com/enterprise-agent/thousandeyes-enterprise-agent-x86_64-5.0.1.cisco.tar !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!


"""