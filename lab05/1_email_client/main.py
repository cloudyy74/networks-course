import argparse
import smtplib
from email.message import EmailMessage

from dotenv import dotenv_values

config = dotenv_values(".env")
SMTP_HOST = config["SMTP_HOST"]
SMTP_PORT = int(config["SMTP_PORT"])
SMTP_LOGIN = config["SMTP_LOGIN"]
SMTP_PASSWORD = config["SMTP_PASSWORD"]


def send_email(to_email: str, subject: str, body: str, message_format: str) -> None:
    msg = EmailMessage()
    msg["From"] = SMTP_LOGIN
    msg["To"] = to_email
    msg["Subject"] = subject

    if message_format == "txt":
        msg.set_content(body)
    elif message_format == "html":
        msg.set_content(body, subtype="html")
    else:
        raise ValueError("Формат должен быть txt или html")

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_LOGIN, SMTP_PASSWORD)
        server.send_message(msg)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Отправка email в формате txt или html")
    parser.add_argument("--to", required=True, help="Адрес получателя")
    parser.add_argument("--subject", required=True, help="Тема письма")
    parser.add_argument("--body", required=True, help="Текст письма")
    parser.add_argument(
        "--format",
        required=True,
        choices=["txt", "html"],
        help="Формат письма: txt или html",
    )

    args = parser.parse_args()

    send_email(args.to, args.subject, args.body, args.format)
    print("Письмо успешно отправлено")
