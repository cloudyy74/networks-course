import argparse
import socket


def run_client(host: str, port: int, command: list[str]) -> None:
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((host, port))
    client.sendall(" ".join(command).encode("utf-8"))
    print(client.recv(4096).decode("utf-8"))
    client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Клиент удаленного запуска команд через TCP")
    parser.add_argument("--host", default="127.0.0.1", help="Адрес сервера")
    parser.add_argument("--port", type=int, default=5000, help="Порт сервера")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Команда и ее аргументы")

    args = parser.parse_args()

    run_client(args.host, args.port, args.command)
