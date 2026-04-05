import argparse
import socket


def run_client(host: str, port: int) -> None:
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    client.bind((host, port))

    print(f"UDP client listening on {host}:{port}")
    try:
        while True:
            message, address = client.recvfrom(1024)
            print(f"{address[0]}:{address[1]} -> {message.decode('utf-8')}")
    except KeyboardInterrupt:
        print("\nClient stopped")
    finally:
        client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UDP broadcast time client")
    parser.add_argument("--host", default="", help="Listen address")
    parser.add_argument("--port", type=int, default=5001, help="UDP port")
    args = parser.parse_args()
    run_client(args.host, args.port)
