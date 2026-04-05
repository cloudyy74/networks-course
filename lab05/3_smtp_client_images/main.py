import argparse
import base64
import socket
import ssl
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.policy import SMTP

from dotenv import dotenv_values

config = dotenv_values(".env")
SMTP_HOST = config["SMTP_HOST"]
SMTP_PORT = int(config["SMTP_PORT"])
SMTP_LOGIN = config["SMTP_LOGIN"]
SMTP_PASSWORD = config["SMTP_PASSWORD"]


def send_command(sock: socket.socket, command: str, hide: bool = False) -> None:
    if not hide:
        print("C:", command)
    sock.sendall((command + "\r\n").encode("utf-8"))
    ans = sock.recv(1024).decode()
    print("S:", ans)


def build_message(to_email: str, subject: str, body: str, image_path: str) -> str:
    message = MIMEMultipart()
    message["From"] = SMTP_LOGIN
    message["To"] = to_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain", "utf-8"))

    with open(image_path, "rb") as image_file:
        image = MIMEImage(image_file.read())
        message.attach(image)

    return message.as_string(policy=SMTP) + "\r\n."


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Отправка email с изображением через сокеты")
    parser.add_argument("--to", required=True, help="Адрес получателя")
    parser.add_argument("--subject", required=True, help="Тема письма")
    parser.add_argument("--body", required=True, help="Текст письма")
    parser.add_argument("--image", required=True, help="Путь к изображению")

    args = parser.parse_args()
    to_email = args.to
    subject = args.subject
    body = args.body
    image_path = args.image

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

    send_command(sock, build_message(to_email, subject, body, image_path), hide=True)

    send_command(sock, "QUIT")
    sock.close()
