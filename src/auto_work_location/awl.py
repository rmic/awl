import logging

import ipaddress
from rich.console import Console
console = Console()

logger = logging.getLogger("auto_work_location")
logger.setLevel(logging.DEBUG)
import subprocess
import re

def traceroute_first_hop():
    """ Runs traceroute to 8.8.8.8 and gets the first hop IP """
    try:
        output = subprocess.check_output(["traceroute", "-m", "1", "8.8.8.8"], text=True)
        lines = output.splitlines()
        match = re.search(r"(\d+\.\d+\.\d+\.\d+)", lines[-1])
        return match.group(1) if match else None
    except subprocess.CalledProcessError:
        return None

def normalize_mac(mac):
    """ Normaliser l'adresse MAC avec des octets à 2 chiffres """
    parts = mac.split(":")
    return ":".join(f"{int(p, 16):02x}" for p in parts)

def get_mac_address(ip):
    """ Gets MAC address of an IP using arp """
    try:
        output = subprocess.check_output(["arp", "-n", ip], text=True)
        lines = output.splitlines()
        match = re.search(r"([0-9a-fA-F:]{11,18})", lines[-1])

        return normalize_mac(match.group(1)) if match else None
    except subprocess.CalledProcessError:
        return None

def determine_location(locations_map):
    first_hop_ip = traceroute_first_hop()
    # Charger le fichier YAML
    votes =  {}
    mac_to_location = locations_map['mac_to_location']
    network_to_location = locations_map['network_to_location']
    logger.debug(f"First hop IP: {first_hop_ip}")
    if not first_hop_ip:
        return "UNKNOWN"

    mac = get_mac_address(first_hop_ip)
    logger.debug(f"MAC: {mac}")
    if not mac:
        return f"Unknown location (First hop: {first_hop_ip}, but no MAC found)"

    ip = ipaddress.IPv4Address(first_hop_ip)
    for network, location in network_to_location.items():
        if ip in ipaddress.IPv4Network(network):
            votes[location] = votes.get(location, 0) + 1
            break
    if mac in mac_to_location:
        location = mac_to_location[mac]
        votes[location] = votes.get(location, 0) + 1

    if votes:
        location = max(votes, key=votes.get)
        logger.debug(f"Location: {location} (First hop: {first_hop_ip}, MAC: {mac})")
        return location





