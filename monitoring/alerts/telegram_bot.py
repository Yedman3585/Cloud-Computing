#!/usr/bin/env python3

import requests
import subprocess
import time
from datetime import datetime

TOKEN = "8956118470:AAFqP3M1WaNb4CZ2d2pECaGAiF_f0A5KfNI"
CHAT_ID = "7298776721"

def send_message(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload, timeout=5)
        print(f"Message sent: {response.status_code}")
    except Exception as e:
        print(f"Failed to send: {e}")

def send_test_message():
    send_message("Firewall monitoring bot is running")

if __name__ == "__main__":
    send_test_message()
