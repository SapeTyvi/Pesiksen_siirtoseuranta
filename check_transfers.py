import html
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
                "lisatiedot": cols[7] if len(cols) > 7 else "",
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


def transfer_changed(old, new):
    return old["leagues"] != new["leagues"] or old.get("lisatiedot", "") != new.get("lisatiedot", "")


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

    prev_map = {transfer_key(t): t for t in previous}
    curr_map = {transfer_key(t): t for t in current}

    new_transfers = [t for k, t in curr_map.items() if k not in prev_map]
    updated_transfers = [
        t for k, t in curr_map.items()
        if k in prev_map and transfer_changed(prev_map[k], t)
    ]

    if not new_transfers and not updated_transfers:
        print("No changes found.")
        return

    lines = []
    if new_transfers:
        lines.append("\u26be <b>" + str(len(new_transfers)) + " uusi siirto pesäpallossa!</b>\n")
        for t in new_transfers:
            lines.append(
                "\U0001f4c5 <b>" + html.escape(t["date"]) + "</b> \u2014 " + html.escape(t["player"]) + "\n"
                + "  " + html.escape(t["from_club"]) + " \u27a1\ufe0f " + html.escape(t["to_club"]) + "\n"
                + "  " + html.escape(t["type"]) + " | " + html.escape(t["st
