import socket
import time
from datetime import datetime

client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client_socket.settimeout(1)

server_address = ("127.0.0.1", 12000)


def time_ms():
    return time.time_ns() / 1_000_000


for i in range(1, 11):
    send_time = time_ms()
    message_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    message = f"Ping {i} {message_time}"

    client_socket.sendto(message.encode(), server_address)

    try:
        response, _ = client_socket.recvfrom(1024)
        rtt = time_ms() - send_time
        print(response.decode(), f"time={rtt:.2f} ms")
    except socket.timeout:
        print("Request timed out")

client_socket.close()
