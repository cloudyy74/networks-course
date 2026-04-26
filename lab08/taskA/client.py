import argparse
import json
import random
import socket

LOSS = 0.3


def make_frame(seq, payload, eof=False):
    header = json.dumps({"seq": seq, "eof": eof}).encode()
    return header + b"\n\n" + payload


def maybe_send(sock, data, addr, loss):
    if random.random() >= loss:
        sock.sendto(data, addr)
        return True
    return False


def wait_ack(sock, seq):
    data, _ = sock.recvfrom(1024)
    ack = json.loads(data.decode())
    return ack.get("ack") == seq


def send_frame(sock, addr, seq, payload, timeout, loss, eof=False):
    frame = make_frame(seq, payload, eof)

    while True:
        sent = maybe_send(sock, frame, addr, loss)
        print(f"client: seq={seq}, eof={eof} {'sent' if sent else 'lost'}")

        try:
            if wait_ack(sock, seq):
                print(f"client: ACK {seq} received")
                return
            print("client: wrong ACK")
        except socket.timeout:
            print("client: timeout, resend")
        except (OSError, ValueError, json.JSONDecodeError) as error:
            print(f"client: bad ACK: {error}")


def main():
    parser = argparse.ArgumentParser(description="Stop-and-Wait UDP client")
    parser.add_argument("file")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--timeout", type=float, default=1.0)
    args = parser.parse_args()

    addr = (args.host, args.port)
    seq = 0

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(args.timeout)

        try:
            with open(args.file, "rb") as src:
                while True:
                    chunk = src.read(32)
                    if not chunk:
                        break
                    send_frame(sock, addr, seq, chunk, args.timeout, LOSS)
                    seq = 1 - seq

            send_frame(sock, addr, seq, b"", args.timeout, LOSS, eof=True)
            print("client: done")
        except OSError as error:
            print(f"client: error: {error}")


if __name__ == "__main__":
    main()
