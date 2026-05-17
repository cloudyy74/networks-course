import argparse
import os
import socket
import struct
import time

ICMP_ECHO_REPLY = 0
ICMP_ECHO_REQUEST = 8
ICMP_TIME_EXCEEDED = 11
PACKET_SIZE = 60
IP_HEADER_SIZE = 20
ICMP_HEADER_SIZE = 8


def checksum(data):
    if len(data) % 2 == 1:
        data += b"\0"

    total = 0
    for i in range(0, len(data), 2):
        total += (data[i] << 8) + data[i + 1]
        total = (total & 0xFFFF) + (total >> 16)

    return (~total) & 0xFFFF


def make_packet(packet_id, seq):
    header = struct.pack("!BBHHH", ICMP_ECHO_REQUEST, 0, 0, packet_id, seq)
    payload_size = PACKET_SIZE - IP_HEADER_SIZE - ICMP_HEADER_SIZE
    payload = struct.pack("!d", time.time()) + b"x" * (payload_size - 8)
    packet_checksum = checksum(header + payload)
    header = struct.pack(
        "!BBHHH", ICMP_ECHO_REQUEST, 0, packet_checksum, packet_id, seq
    )
    return header + payload


def parse_icmp(data):
    ip_header_len = (data[0] & 0x0F) * 4
    icmp_header = data[ip_header_len : ip_header_len + 8]
    icmp_type, code, _, packet_id, seq = struct.unpack("!BBHHH", icmp_header)
    return icmp_type, code, packet_id, seq


def parse_time_exceeded(data):
    ip_header_len = (data[0] & 0x0F) * 4
    inner_ip_start = ip_header_len + 8
    inner_ip_header_len = (data[inner_ip_start] & 0x0F) * 4
    inner_icmp_start = inner_ip_start + inner_ip_header_len
    inner_icmp = data[inner_icmp_start : inner_icmp_start + 8]
    _, _, _, packet_id, seq = struct.unpack("!BBHHH", inner_icmp)
    return packet_id, seq


def time_ms():
    return time.time_ns() / 1_000_000


def host_name(addr):
    try:
        name, _, _ = socket.gethostbyaddr(addr)
        return name
    except (socket.herror, socket.gaierror, OSError):
        return None


def host_info(addr):
    if not addr:
        return "*"

    name = host_name(addr)
    if name:
        return f"{name} ({addr})"
    return f"{addr} ({addr})"


def format_row(ttl, results):
    parts = [f"{ttl:2d}"]
    last_addr = None

    for result in results:
        if not result:
            parts.append("*")
            continue

        addr, rtt = result
        if addr != last_addr:
            parts.append(host_info(addr))
            last_addr = addr
        parts.append(f"{rtt:.3f} ms")

    return "  ".join(parts)


def send_packet(sock, addr, ttl, packet_id, seq):
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, ttl)
    packet = make_packet(packet_id, seq)
    send_time = time_ms()
    sock.sendto(packet, (addr, 0))
    return send_time


def receive_packet(sock, packet_id, seq, send_time, timeout):
    end_time = time.time() + timeout

    while True:
        left = end_time - time.time()
        if left <= 0:
            raise socket.timeout

        sock.settimeout(left)
        data, addr = sock.recvfrom(65535)
        rtt = time_ms() - send_time
        icmp_type, _, received_id, received_seq = parse_icmp(data)

        if icmp_type == ICMP_ECHO_REPLY:
            if received_id == packet_id and received_seq == seq:
                return addr[0], rtt, True
        elif icmp_type == ICMP_TIME_EXCEEDED:
            received_id, received_seq = parse_time_exceeded(data)
            if received_id == packet_id and received_seq == seq:
                return addr[0], rtt, False


def trace(host, count, max_ttl, timeout):
    dest_addr = socket.gethostbyname(host)
    packet_id = os.getpid() & 0xFFFF
    seq = 1

    print(
        f"traceroute to {host} ({dest_addr}), "
        f"{max_ttl} hops max, {PACKET_SIZE} byte packets"
    )

    with socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP) as sock:
        for ttl in range(1, max_ttl + 1):
            results = []
            done = False

            for _ in range(count):
                try:
                    send_time = send_packet(sock, dest_addr, ttl, packet_id, seq)
                    addr, rtt, done = receive_packet(
                        sock, packet_id, seq, send_time, timeout
                    )
                    results.append((addr, rtt))
                except socket.timeout:
                    results.append(None)
                except OSError as error:
                    print(f"{ttl:2d}  error: {error}")
                    results.append(None)
                finally:
                    seq += 1

            print(format_row(ttl, results))

            if done:
                break


def main():
    parser = argparse.ArgumentParser(description="ICMP traceroute")
    parser.add_argument("host")
    parser.add_argument("-c", "--count", type=int, default=3)
    parser.add_argument("-m", "--max-ttl", type=int, default=30)
    parser.add_argument("-t", "--timeout", type=float, default=2.0)
    args = parser.parse_args()

    try:
        trace(args.host, args.count, args.max_ttl, args.timeout)
    except PermissionError:
        print("raw socket permission denied, run with sudo")
    except socket.gaierror as error:
        print(f"bad host: {error}")


if __name__ == "__main__":
    main()
