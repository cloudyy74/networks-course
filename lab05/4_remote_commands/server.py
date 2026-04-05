import argparse
import socket
import subprocess


def run_command(command: str) -> str:
    output = subprocess.run(command, shell=True, capture_output=True, text=True)
    return output.stdout if output.stdout else output.stderr


def serve(host: str, port: int) -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen()

    print(f"Сервер запущен на {host}:{port}")
    try:
        while True:
            conn, addr = server.accept()
            with conn:
                print(f"Подключен клиент {addr[0]}:{addr[1]}")
                command = conn.recv(1024).decode("utf-8")
                response = run_command(command)
                conn.sendall(response.encode("utf-8"))
    except KeyboardInterrupt:
        print("\nСервер остановлен")
    finally:
        server.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Сервер удаленного запуска команд через TCP")
    parser.add_argument("--host", default="0.0.0.0", help="Адрес сервера")
    parser.add_argument("--port", type=int, default=5000, help="Порт сервера")
    args = parser.parse_args()
    serve(args.host, args.port)

