from netmiko import ConnectHandler
from jinja2 import Template
import ipaddress
import json
from rstr import Rstr
from random import SystemRandom

from IPAM.read_from_ipam import get_subnet


def device_details(device_ip, username, password):
    return {
        'device_type': 'cisco_nxos',
        'ip': device_ip,
        'username': username,
        'password': password
    }


def ospf_auth_generator():
    rgen = Rstr(SystemRandom())
    pattern = r"[0-9a-zA-Z]{8}"
    return rgen.xeger(pattern)


def check_if_ospf_config_exists(output):
    '''
    if object in "try" does not exist, it means that OSPF configuration exists on interface.
    '''
    employees_obj = json.loads(output)
    try:
        employees_obj['nf:filter']['m:configure']['m:terminal']['interface']['__XML__PARAM__interface']['m4:ip']
    except KeyError:
        return False
    return True


def generate_template():
    template = Template(open('ospf_autoconfig/ospf').read())
    return template


def device_connection(device_ip):
    try:
        ios = device_details(device_ip, 'cisco', 'cisco')
        conn = ConnectHandler(**ios)
        print("connection to device %s established" % device_ip)
    except Exception:
        conn = False
        print("cannot establish a connection to device %s" % device_ip)
    return conn


def get_neighbor(output):
    output_obj = json.loads(output)
    neighbor_ip = output_obj['TABLE_cdp_neighbor_detail_info']['ROW_cdp_neighbor_detail_info']['v4mgmtaddr']
    return neighbor_ip


def configure_device(interface, conn):
    template = generate_template()
    ospf_auth = ospf_auth_generator()
    cmd_set = template.render(router_id=interface.get('ip_address'),
                              interface_ip=interface.get('ip_address'),
                              intf_id=interface.get('interface'),
                              random_string=ospf_auth,
                              ip_address=interface.get('ip_address'))
    commands = cmd_set.splitlines()
    conn.send_config_set(commands, delay_factor=1, enter_config_mode=True, exit_config_mode=True)


def get_devices():
    with open('ospf_autoconfig/devices_list.txt', "r") as file:
        devices_list = file.read()
    return devices_list


if __name__ == "__main__":
    devices_list = get_devices()
    free_subnet = get_subnet()
    print("Free subnet that will be configured: %s" % free_subnet)
    devices_list = devices_list.splitlines()
    for device in devices_list:
        conn_device_1 = device_connection(device)
        if conn_device_1 is False:
            break
        command_cdp_output = conn_device_1.send_command("show cdp neigh interface Eth1/1 detail | json")
        dev_neighbor_ip = get_neighbor(command_cdp_output)
        print("neighbor device %s", dev_neighbor_ip)
        command_interface_configuration = conn_device_1.send_command("show running-config interface Eth 1/1 | json")
        ospf_configuration = check_if_ospf_config_exists(command_interface_configuration)
        # if ospf_configuration is True:
        #     break

        interface_device_1 = {
            "ip_address": ipaddress.ip_address(free_subnet) + 1,
            "interface": "Eth1/1"
        }
        configure_device(interface_device_1, conn_device_1)
        print("device_1 %s configured successful" % device)
        conn_device_2 = device_connection(dev_neighbor_ip)
        interface_device_2 = {
            "ip_address": ipaddress.ip_address(free_subnet) + 2,
            "interface": "Eth1/1"
        }
        configure_device(interface_device_2, conn_device_2)
        print("device_2 %s configured successful" % dev_neighbor_ip)
