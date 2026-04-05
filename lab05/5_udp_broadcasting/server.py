import argparse
import socket
import time
from datetime import datetime


def serve(host: str, port: int) -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    print(f"UDP broadcast server started on {host}:{port}")
    try:
        while True:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            server.sendto(current_time.encode("utf-8"), (host, port))
            print(f"Sent: {current_time}")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nServer stopped")
    finally:
        server.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UDP broadcast time server")
    parser.add_argument("--host", default="255.255.255.255", help="Broadcast address")
    parser.add_argument("--port", type=int, default=5001, help="UDP port")
    args = parser.parse_args()
    serve(args.host, args.port)
