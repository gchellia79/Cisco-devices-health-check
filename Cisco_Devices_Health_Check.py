import yaml
import csv
import os
from netmiko import ConnectHandler, NetMikoAuthenticationException, NetMikoTimeoutException
from datetime import datetime

def get_interface_status(output):
    for line in output.splitlines():
        if "line protocol is" in line:
            return line.strip()
    return "Status line not found."

def ping_from_switch(connection, target_ip):
    try:
        output = connection.send_command(f"ping {target_ip}", expect_string=r"#")
        if "Success rate is 0 percent" in output:
            return "Failure"
        elif "Success rate is" in output:
            return "Success"
        else:
            return "Unknown Result"
    except Exception as e:
        return f"Ping Error: {e}"

def get_snmp_ro_communites(connection):
    try:
        output = connection.send_command("show running-config | include snmp-server community")
        communities = []
        for line in output.splitlines():
            if "snmp-server community" in line and "RO" in line.upper():
                parts = line.split()
                if len(parts) >= 3:
                    communities.append(parts[2])
        return ", ".join(communities) if communities else "Not Found"
    except Exception as e:
        return f"Error: {e}"

def get_hostname(connection):
    try:
        output = connection.send_command("show running-config | include ^hostname")
        if output.startswith("hostname"):
            return output.strip().split()[1]
        return "Unknown"
    except Exception as e:
        return f"Error: {e}"

def main():
    # Load YAML
    try:
        with open("/Users/gchellia/Documents/CSS/Automation/pod2_devices.yaml", "r") as file:
            config = yaml.safe_load(file)
    except FileNotFoundError:
        print("Error: YAML file 'pod2_devices.yaml' not found.")
        return
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}")
        return

    switches = config.get("switches", [])
    if not switches:
        print("Error: No 'switches' defined in the YAML file.")
        return

    # Prepare CSV output
    timestamp_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_dir = "pod2_health_check_logs"
    os.makedirs(log_dir, exist_ok=True)
    POD2_HEALTH_CHECK = f"{log_dir}/POD2_HEALTH_CHECK_{timestamp_str}.csv"

    with open(POD2_HEALTH_CHECK, mode="w", newline="") as csvfile:
        fieldnames = [
            "Switch Name", "Configured Hostname", "IP",
            "Catalyst Center Reachability", "Interface",
            "Status", "SNMP RO COMMUNITY", "Switch status"
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        success_count = 0
        fail_count = 0
       
        # Loop through switches
        for switch in switches:
            print(f"\n=== Connecting to {switch.get('name')} ({switch['ip']}) ===")

            device = {
                'device_type': switch['device_type'],
                'host': switch['ip'],
                'username': switch['username'],
                'password': switch['password']
            }

            try:
                connection = ConnectHandler(**device)
                success_count += 1
            except (NetMikoAuthenticationException, NetMikoTimeoutException) as conn_error:
                print(f"Connection failed: {conn_error}")
                fail_count += 1
                writer.writerow({
                    "Switch Name": switch.get('name', "Unknown"),
                    "Configured Hostname": "N/A",
                    "IP": switch['ip'],
                    "Catalyst Center Reachability": "N/A",
                    "Interface": "N/A",
                    "Status": "N/A",
                    "SNMP RO COMMUNITY": "N/A",
                    "Switch status": f"Connection failed: {conn_error}"
                })
                continue

            target_ip = switch.get("ping_ip", switch["ip"])
            print(f"Pinging {target_ip} from {switch['name']}...")
            ping_result = ping_from_switch(connection, target_ip)
            snmp_community = get_snmp_ro_communites(connection)
            actual_hostname = get_hostname(connection)

            for interface in switch.get("interfaces", []):
                print(f"Checking {interface}...")
                try:
                    output = connection.send_command(f"show interface {interface}")
                    status = get_interface_status(output)

                    writer.writerow({
                        "Switch Name": switch.get('name', "Unknown"),
                        "Configured Hostname": actual_hostname,
                        "IP": switch['ip'],
                        "Catalyst Center Reachability": ping_result,
                        "Interface": interface,
                        "Status": status,
                        "SNMP RO COMMUNITY": snmp_community,
                        "Switch status": "Reachable"
                    })

                except Exception as e:
                    print(f"Error retrieving {interface} on {switch['ip']}: {e}")
                    writer.writerow({
                        "Switch Name": switch.get('name', "Unknown"),
                        "Configured Hostname": actual_hostname,
                        "IP": switch['ip'],
                        "Catalyst Center Reachability": ping_result,
                        "Interface": interface,
                        "Status": "Error",
                        "SNMP RO COMMUNITY": snmp_community,
                        "Switch status": f"Interface error: {e}"
                    })

            connection.disconnect()

    print(f"\n✅ Interface status written to: {POD2_HEALTH_CHECK}")
    print(f"🔍 Summary: {success_count} switches reachable, {fail_count} failed to connect.")

if __name__ == "__main__":
    main()
