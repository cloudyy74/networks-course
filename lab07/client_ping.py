import socket
import time

client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client_socket.settimeout(1)

server_address = ("127.0.0.1", 12000)
rtts = []
sent = 10
received = 0


def time_ms():
    return time.time_ns() / 1_000_000


start_time = time_ms()

for i in range(1, sent + 1):
    send_time = time_ms()
    message = f"Ping {i} {send_time}"

    client_socket.sendto(message.encode(), server_address)

    try:
        response, _ = client_socket.recvfrom(1024)
        rtt = time_ms() - send_time
        rtts.append(rtt)
        received += 1
        print(
            f"{len(response)} bytes from {server_address[0]}: seq={i} time={rtt:.2f} ms"
        )
    except socket.timeout:
        print("Request timed out")

client_socket.close()

loss = (sent - received) / sent * 100

print()
print(f"--- {server_address[0]} ping statistics ---")
print(
    f"{sent} packets transmitted, {received} received, {loss:.0f}% packet loss, time {time_ms() - start_time:.0f}ms"
)

if rtts:
    print(
        f"rtt min/avg/max = "
        f"{min(rtts):.2f}/{(sum(rtts) / received):.2f}/{max(rtts):.2f} ms"
    )
