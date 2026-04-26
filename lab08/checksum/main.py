def checksum(data):
    if len(data) % 2 == 1:
        data += b"\0"

    total = 0
    for i in range(0, len(data), 2):
        word = (data[i] << 8) + data[i + 1]
        total += word
        total = (total & 0xffff) + (total >> 16)

    return (~total) & 0xffff


def verify(data, received_checksum):
    return checksum(data) == received_checksum


def run_test(name, condition):
    print(f"{name}: {'OK' if condition else 'FAIL'}")


def main():
    data = b"hello"
    good_checksum = checksum(data)

    run_test("correct data", verify(data, good_checksum))
    run_test("changed data", not verify(b"jello", good_checksum))

    odd_data = b"abc"
    odd_checksum = checksum(odd_data)
    run_test("odd length data", verify(odd_data, odd_checksum))


if __name__ == "__main__":
    main()
