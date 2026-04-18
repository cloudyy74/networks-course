import random
import socket


server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind(("0.0.0.0", 12000))

while True:
    message, client_address = server_socket.recvfrom(1024)

    if random.random() < 0.2:
        continue

    server_socket.sendto(message.upper(), client_address)
