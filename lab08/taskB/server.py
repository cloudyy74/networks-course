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


def parse_frame(data):
    header, payload = data.split(b"\n\n", 1)
    return json.loads(header.decode()), payload


def ack(seq):
    return json.dumps({"ack": seq}).encode()


def wait_ack(sock, seq):
    data, _ = sock.recvfrom(1024)
    ack_data = json.loads(data.decode())
    return ack_data.get("ack") == seq


def send_frame(sock, addr, seq, payload, timeout, eof=False):
    frame = make_frame(seq, payload, eof)

    while True:
        sent = maybe_send(sock, frame, addr, LOSS)
        print(f"server: send seq={seq}, eof={eof} {'sent' if sent else 'lost'}")

        try:
            if wait_ack(sock, seq):
                print(f"server: ACK {seq} received")
                return
            print("server: wrong ACK")
        except socket.timeout:
            print("server: timeout, resend")
        except (OSError, ValueError, json.JSONDecodeError) as error:
            print(f"server: bad ACK: {error}")


def send_file(sock, addr, filename, timeout):
    seq = 0
    sock.settimeout(timeout)

    with open(filename, "rb") as src:
        while True:
            chunk = src.read(32)
            if not chunk:
                break
            send_frame(sock, addr, seq, chunk, timeout)
            seq = 1 - seq

    send_frame(sock, addr, seq, b"", timeout, eof=True)
    print("server: response sent")


def main():
    parser = argparse.ArgumentParser(description="Stop-and-Wait UDP server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--out", default="received.txt")
    parser.add_argument("--file", default="server_input.txt")
    parser.add_argument("--timeout", type=float, default=1.0)
    args = parser.parse_args()

    expected = 0
    done = False
    client_addr = None

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((args.host, args.port))
        print(f"server: listening on {args.host}:{args.port}")

        with open(args.out, "wb") as out:
            while True:
                try:
                    data, addr = sock.recvfrom(65535)
                except socket.timeout:
                    print(f"server: saved file to {args.out}")
                    break
                except OSError as error:
                    print(f"server: bad packet: {error}")
                    continue

                try:
                    frame, payload = parse_frame(data)
                    seq = frame["seq"]
                    eof = frame.get("eof", False)
                except (ValueError, json.JSONDecodeError, KeyError) as error:
                    print(f"server: bad packet: {error}")
                    continue

                client_addr = addr
                print(f"server: got seq={seq}, eof={eof}, bytes={len(payload)}")

                if seq == expected:
                    if not eof:
                        out.write(payload)
                    expected = 1 - expected
                else:
                    print("server: duplicate packet, only ACK again")

                sent = maybe_send(sock, ack(seq), addr, LOSS)
                print(f"server: ACK {seq} {'sent' if sent else 'lost'}")

                if eof and seq != expected:
                    done = True
                    sock.settimeout(2.0)
                    print("server: eof received, waiting for possible duplicates")
                elif not done:
                    sock.settimeout(None)

        if client_addr:
            send_file(sock, client_addr, args.file, args.timeout)


if __name__ == "__main__":
    main()
