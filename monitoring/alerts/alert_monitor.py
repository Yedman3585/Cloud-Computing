#!/usr/bin/env python3
"""Watch firewall drop logs and send Telegram alert on heavily-blocked IPs."""
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
import telegram_bot

LOG_PATH = os.environ.get("FW_LOG_PATH", "/var/log/firewall/dropped.log")
INTERVAL = int(os.environ.get("ALERT_INTERVAL", "15"))
THRESHOLD = int(os.environ.get("ALERT_THRESHOLD", "50"))

SRC_RE = re.compile(r"SRC=([0-9a-fA-F:.]+)")


def count_blocked(path):
    counts = {}
    try:
        with open(path) as f:
            for line in f:
                m = SRC_RE.search(line)
                if m:
                    ip = m.group(1)
                    counts[ip] = counts.get(ip, 0) + 1
    except FileNotFoundError:
        pass
    return counts


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID", flush=True)
        return 1

    alerted = {}
    print(
        f"[alert_monitor] watching {LOG_PATH}, "
        f"every {INTERVAL}s, threshold {THRESHOLD}",
        flush=True,
    )

    while True:
        try:
            for ip, count in count_blocked(LOG_PATH).items():
                last = alerted.get(ip, 0)
                if count >= THRESHOLD and (
                    ip not in alerted or count >= last * 2
                ):
                    msg = (
                        f"\u26a0\ufe0f Firewall alert: "
                        f"{ip} blocked {count} times"
                    )
                    try:
                        telegram_bot.send_message(token, chat_id, msg)
                        print(f"[alert_monitor] sent: {msg}", flush=True)
                        alerted[ip] = count
                    except Exception as exc:
                        print(
                            f"[alert_monitor] send failed: {exc}",
                            flush=True,
                        )
        except Exception as exc:
            print(f"[alert_monitor] error: {exc}", flush=True)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    sys.exit(main())