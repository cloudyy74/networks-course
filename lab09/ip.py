import netifaces
for iface in netifaces.interfaces():
    addrs = netifaces.ifaddresses(iface)
    if netifaces.AF_INET in addrs:
        for addr in addrs[netifaces.AF_INET]:
            print(f"{iface}: IP={addr['addr']}, Mask={addr['netmask']}")
