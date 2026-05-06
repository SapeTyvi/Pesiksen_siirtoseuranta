import json
import os
from datetime import datetime

import requests
from bs4 import BeautifulSoup

URL = "https://v1.pesistulokset.fi/seurasiirrot"
SNAPSHOT_FILE = "snapshot.json"

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]


def fetch_transfers():
    resp = requests.get(URL, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    transfers = []
    table = soup.find("table")
    if not table:
        return transfers
    for row in table.find_all("tr")[1:]:
        cols = [td.get_text(strip=True) for td in row.find_all("td")]
        if len(cols) >= 6:
            transfers.append({
                "date": cols[0], "player": cols[1], "status": cols[2],
                "type": cols[3], "from_club": cols[4], "to_club": cols[5],
                "leagues": cols[6] if len(cols) > 6 else "",
            })
    return transfers


def load_snapshot():
    if os.path.exists(SNAPSHOT_FILE):
        with open(SNAPSHOT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_snapshot(transfers):
    with open(SNAPSHOT_FILE, "w", encoding="utf-8") as f:
        json.dump(transfers, f, ensure_ascii=False, indent=2)


def transfer_key(t):
    return t["date"] + "|" + t["player"] + "|" + t["from_club"] + "|" + t["to_club"]


def send_telegram(message):
    url = "https://api.telegram.org/bot" + TELEGRAM_BOT_TOKEN + "/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()


def main():
    print("[" + datetime.utcnow().isoformat() + "] Checking for new transfers...")
    current = fetch_transfers()
    previous = load_snapshot()
    if not previous:
        save_snapshot(current)
        print("First run: saved " + str(len(current)) + " transfers as baseline.")
        return
    prev_keys = set(transfer_key(t) for t in previous)
    new_transfers = [t for t in current if transfer_key(t) not in prev_keys]
    if not new_transfers:
        print("No new transfers found.")
        return
    print("Found " + str(len(new_transfers)) + " new transfer(s)!")
    lines = ["\u26be <b>" + str(len(new_transfers)) + " uusi siirto pes\u00e4pallossa!</b>\n"]
    for t in new_transfers:
        lines.append(
            "\U0001f4c5 <b>" + t["date"] + "</b> \u2014 " + t["player"] + "\n"
            + "  " + t["from_club"] + " \u27a1\ufe0f " + t["to_club"] + "\n"
            + "  " + t["type"] + " | " + t["status"] + "\n"
            + "  " + t["leagues"]
        )
    lines.append("\n\U0001f517 " + URL)
    message = "\n".join(lines)
    send_telegram(message)
    save_snapshot(current)
    print("Notification sent and snapshot updated.")


if __name__ == "__main__":
    main()
