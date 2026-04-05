import argparse
import socket
import ssl
import base64
from dotenv import dotenv_values

config = dotenv_values(".env")
SMTP_HOST = config["SMTP_HOST"]
SMTP_PORT = int(config["SMTP_PORT"])
SMTP_LOGIN = config["SMTP_LOGIN"]
SMTP_PASSWORD = config["SMTP_PASSWORD"]


def send_command(sock: socket, command: str, hide=False) -> None:
    if not hide:
        print("C:", command)
    sock.send((command + "\r\n").encode("utf-8"))
    ans = sock.recv(1024).decode()
    print("S:", ans)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Отправка email через сокеты")
    parser.add_argument("--to", required=True, help="Адрес получателя")
    parser.add_argument("--subject", required=True, help="Тема письма")
    parser.add_argument("--body", required=True, help="Текст письма")
    
    args = parser.parse_args()
    to_email = args.to
    subject = args.subject
    body = args.body

    sock = socket.create_connection((SMTP_HOST, SMTP_PORT))
    print(sock.recv(1024).decode())

    send_command(sock, "EHLO lab05")
    send_command(sock, "STARTTLS")

    context = ssl.create_default_context()
    sock = context.wrap_socket(sock, server_hostname=SMTP_HOST)

    send_command(sock, "EHLO lab05")

    send_command(sock, "AUTH LOGIN")
    send_command(sock, base64.b64encode(SMTP_LOGIN.encode()).decode(), hide=True)
    send_command(sock, base64.b64encode(SMTP_PASSWORD.encode()).decode(), hide=True)

    send_command(sock, f"MAIL FROM:<{SMTP_LOGIN}>")
    send_command(sock, f"RCPT TO:<{to_email}>")
    send_command(sock, "DATA")

    message = (
        f"From: {SMTP_LOGIN}\r\n"
        f"To: {to_email}\r\n"
        f"Subject: {subject}\r\n"
        f"\r\n"
        f"{body}\r\n."
    )

    send_command(sock, message)

    send_command(sock, "QUIT")
    sock.close()