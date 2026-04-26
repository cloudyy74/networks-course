import argparse
import json
import random
import socket

LOSS = 0.3


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


def main():
    parser = argparse.ArgumentParser(description="Stop-and-Wait UDP server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--out", default="received.txt")
    args = parser.parse_args()

    expected = 0
    done = False

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


if __name__ == "__main__":
    main()
