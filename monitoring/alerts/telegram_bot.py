#!/usr/bin/env python3
import argparse
import os
import sys

import requests


def send_message(token: str, chat_id: str, message: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
    response = requests.post(url, json=payload, timeout=5)
    response.raise_for_status()


def main() -> int:
    parser = argparse.ArgumentParser(description="Send firewall monitoring Telegram alert")
    parser.add_argument("--message", default="Firewall monitoring bot is running")
    args = parser.parse_args()

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID before sending alerts.")
        return 1

    try:
        send_message(token, chat_id, args.message)
    except Exception as exc:
        print(f"Failed to send alert: {exc}")
        return 1

    print("Alert sent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
