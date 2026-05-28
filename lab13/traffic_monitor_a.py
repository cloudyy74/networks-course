import time

import psutil

INTERVAL = 1.0


def bytes_human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def get_totals():
    counters = psutil.net_io_counters()
    return counters.bytes_recv, counters.bytes_sent


if __name__ == "__main__":
    print("Network traffic monitor")
    print(
        f"{'Time':>8}  {'Incoming':>12}  {'Outgoing':>12}  {'Total IN':>12}  {'Total OUT':>12}"
    )
    print("-" * 62)

    prev_recv, prev_sent = get_totals()
    start_recv, start_sent = prev_recv, prev_sent

    try:
        while True:
            time.sleep(INTERVAL)
            recv, sent = get_totals()

            delta_recv = recv - prev_recv
            delta_sent = sent - prev_sent
            total_recv = recv - start_recv
            total_sent = sent - start_sent

            ts = time.strftime("%H:%M:%S")
            print(
                f"{ts:>8}  "
                f"{bytes_human(delta_recv):>12}  "
                f"{bytes_human(delta_sent):>12}  "
                f"{bytes_human(total_recv):>12}  "
                f"{bytes_human(total_sent):>12}"
            )

            prev_recv, prev_sent = recv, sent

    except KeyboardInterrupt:
        recv, sent = get_totals()
        print("\n--- Session summary ---")
        print(f"  Total incoming: {bytes_human(recv - start_recv)}")
        print(f"  Total outgoing: {bytes_human(sent - start_sent)}")
