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

TRACKED_LEAGUES = {
    "Miesten Superpesis",
    "Miesten Ykköspesis",
    "Naisten Superpesis",
    "Naisten Ykköspesis",
}


def is_tracked(leagues_str):
    return any(league in leagues_str for league in TRACKED_LEAGUES)


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
            leagues = cols[6] if len(cols) > 6 else ""
            if not is_tracked(leagues):
                continue
            transfers.append({
                "date": cols[0],
                "player": cols[1],
                "status": cols[2],
                "type": cols[3],
                "from_club": cols[4],
                "to_club": cols[5],
                "leagues": leagues,
                "lisatiedot": cols[7] if len(cols) > 7 else "",
                "details": cols[8] if len(cols) > 8 else "",
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
    old_li = old.get("lisatiedot", "")
    new_li = new.get("lisatiedot", "")
    old_det = old.get("details", "")
    new_det = new.get("details", "")
    return (
        old["leagues"] != new["leagues"]
        or old_li != new_li
        or old_det != new_det
    )


def send_telegram(message):
    url = "https://api.telegram.org/bot" + TELEGRAM_BOT_TOKEN + "/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()


def main():
    now = datetime.utcnow().isoformat()
    print("[" + now + "] Checking for new transfers...")
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
        count = str(len(new_transfers))
        lines.append("\u26be <b>" + count + " uusi siirto pesäpallossa!</b>\n")
        for t in new_transfers:
            line = "\U0001f4c5 <b>" + html.escape(t["date"]) + "</b>"
            line += " \u2014 " + html.escape(t["player"])
            line += "\n  " + html.escape(t["from_club"])
            line += " \u27a1\ufe0f " + html.escape(t["to_club"])
            line += "\n  " + html.escape(t["type"])
            line += " | " + html.escape(t["status"])
            line += "\n  " + html.escape(t["leagues"])
            li = t.get("lisatiedot", "")
            if li:
                line += "\n  \U0001f4dd " + html.escape(li)
            det = t.get("details", "")
            if det:
                line += "\n  \u2139\ufe0f " + html.escape(det)
            lines.append(line)

    if updated_transfers:
        count = str(len(updated_transfers))
        lines.append("\n\u270f\ufe0f <b>" + count + " siirto päivitetty!</b>\n")
        for t in updated_transfers:
            line = "\U0001f4c5 <b>" + html.escape(t["date"]) + "</b>"
            line += " \u2014 " + html.escape(t["player"])
            line += "\n  " + html.escape(t["from_club"])
            line += " \u27a1\ufe0f " + html.escape(t["to_club"])
            line += "\n  " + html.escape(t["leagues"])
            li = t.get("lisatiedot", "")
            if li:
                line += "\n  \U0001f4dd " + html.escape(li)
            det = t.get("details", "")
            if det:
                line += "\n  \u2139\ufe0f " + html.escape(det)
            lines.append(line)

    lines.append("\n\U0001f517 " + URL)
    message = "\n".join(lines)
    send_telegram(message)
    save_snapshot(current)
    print("Notification sent and snapshot updated.")


if __name__ == "__main__":
    main()
