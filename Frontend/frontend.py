from __future__ import annotations

import sys
from threading import Thread

from receive import Settings as ReceiveSettings, receive_order_confirmed
from send import Settings as SendSettings, run_sender


def run_frontend() -> None:
    receiver = Thread(
        target=receive_order_confirmed,
        args=(ReceiveSettings(),),
        name="reply-receiver",
    )
    sender = Thread(
        target=run_sender,
        args=(SendSettings(),),
        name="order-sender",
    )

    receiver.start()
    sender.start()
    receiver.join()
    sender.join()


if __name__ == "__main__":
    try:
        run_frontend()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr, flush=True)
        raise
