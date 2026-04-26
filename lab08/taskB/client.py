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


def parse_frame(data):
    header, payload = data.split(b"\n\n", 1)
    return json.loads(header.decode()), payload


def ack(seq):
    return json.dumps({"ack": seq}).encode()


def receive_file(sock, out_name):
    expected = 0
    done = False

    with open(out_name, "wb") as out:
        while True:
            try:
                data, addr = sock.recvfrom(65535)
            except socket.timeout:
                if done:
                    print(f"client: saved server file to {out_name}")
                    return
                print("client: timeout while waiting for server file")
                continue
            except OSError as error:
                print(f"client: bad packet: {error}")
                continue

            try:
                frame, payload = parse_frame(data)
                seq = frame["seq"]
                eof = frame.get("eof", False)
            except (ValueError, json.JSONDecodeError, KeyError) as error:
                print(f"client: bad packet: {error}")
                continue

            print(f"client: got seq={seq}, eof={eof}, bytes={len(payload)}")

            if seq == expected:
                if not eof:
                    out.write(payload)
                expected = 1 - expected
            else:
                print("client: duplicate packet, only ACK again")

            sent = maybe_send(sock, ack(seq), addr, LOSS)
            print(f"client: ACK {seq} {'sent' if sent else 'lost'}")

            if eof and seq != expected:
                done = True
                sock.settimeout(2.0)


def main():
    parser = argparse.ArgumentParser(description="Stop-and-Wait UDP client")
    parser.add_argument("file")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--out", default="server_received.txt")
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
            print("client: upload done")
            receive_file(sock, args.out)
        except OSError as error:
            print(f"client: error: {error}")


if __name__ == "__main__":
    main()
