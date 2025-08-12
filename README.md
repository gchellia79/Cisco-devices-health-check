This script is designed to perform the following validation checks on network devices:

**Hostname Verification** – Ensures the correct hostname is configured on each device.

**Catalyst Center Enterprise IP Reachability** – Verifies that devices (Switches, Routers, WLCs, etc.) can reach the specified Catalyst Center IP address.

**Interconnecting Link Status** – Checks the status of links between devices.

**SNMP Read-Only Community** – Confirms that the SNMP RO community string is correctly configured.

All required variables are provided via a YAML configuration file.
