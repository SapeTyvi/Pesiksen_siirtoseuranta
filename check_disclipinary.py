import html
import json
import os
from datetime import datetime

import requests

API_URL = "https://api.pesistulokset.fi/api/v1/public/disciplinary-decisions?apikey=wRX0tTke3DZ8RLKAMntjZ81LwgNQuSN9"
PAGE_URL = "https://www.pesistulokset.fi/kurinpito"
SNAPSHOT_FILE = "disciplinary_snapshot.json"

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

TRACKED_LEAGUES = {
    "Miesten Superpesis",
    "Miesten Ykköspesis",
    "Naisten Superpesis",
    "Naisten Ykköspesis",
    "Poikien Superpesis",
    "Tyttöjen Superpesis",
}


def is_tracked(series):
    return any(league in series for league in TRACKED_LEAGUES)


def fetch_decisions():
    resp = requests.get(API_URL, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    decisions = []
    for organizer_group in data.get("decisions", []):
        for d in organizer_group.get("decisions", []):
            series = d.get("match", {}).get("series", "")
            if not is_tracked(series):
                continue
            decisions.append({
                "key": f"{d['match']['id']}|{d['target']['id']}|{d['type_name']}",
                "date": d["match"]["date"],
                "series": series,
                "home": d["match"]["home"]["name"],
                "away": d["match"]["away"]["name"],
                "target_name": d["target"]["name"],
                "target_type": d["target"]["type"],
                "target_team": d["target"].get("team") or "",
                "type_name": d["type_name"],
                "reason": d.get("reason", ""),
                "when_happened": d.get("when_happened", ""),
                "has_decision": bool(d.get("decision", "").strip()),
                "processing_started": d.get("processing_started", False),
                "processing_ended": d.get("processing_ended", False),
            })
    return decisions


def load_snapshot():
    if os.path.exists(SNAPSHOT_FILE):
        with open(SNAPSHOT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_snapshot(decisions):
    with open(SNAPSHOT_FILE, "w", encoding="utf-8") as f:
        json.dump(decisions, f, ensure_ascii=False, indent=2)


def decision_changed(old, new):
    return (
        old["type_name"] != new["type_name"]
        or old["reason"] != new["reason"]
        or old["has_decision"] != new["has_decision"]
        or old["processing_started"] != new["processing_started"]
        or old["processing_ended"] != new["processing_ended"]
    )


def format_date(iso_date):
    try:
        dt = datetime.fromisoformat(iso_date)
        return dt.strftime("%-d.%-m.%Y")
    except Exception:
        return iso_date


def target_type_fi(target_type):
    return {"player": "Pelaaja", "manager": "Toimihenkilö", "referee": "Tuomari"}.get(target_type, target_type)


def format_decision(d):
    lines = []
    lines.append(f"📅 <b>{html.escape(format_date(d['date']))}</b> — {html.escape(d['target_name'])}")
    lines.append(f"  {html.escape(d['home'])} vs {html.escape(d['away'])}")
    lines.append(f"  {html.escape(d['series'])}")
    lines.append(f"  {html.escape(target_type_fi(d['target_type']))}: {html.escape(d['target_team'])}")
    lines.append(f"  🟨 {html.escape(d['type_name'])}")
    if d["reason"]:
        lines.append(f"  📋 {html.escape(d['reason'])}")
    if d["when_happened"]:
        lines.append(f"  ⏱ {html.escape(d['when_happened'])}")
    if d["has_decision"]:
        lines.append(f"  ⚖️ Kurinpitopäätös tehty — <a href=\"{PAGE_URL}\">lue täältä</a>")
    elif d["processing_started"]:
        lines.append(f"  ⚖️ Kurinpitokäsittely käynnissä")
    return "\n".join(lines)


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()


def main():
    now = datetime.utcnow().isoformat()
    print(f"[{now}] Checking for new disciplinary decisions...")

    current = fetch_decisions()
    previous = load_snapshot()

    if not previous:
        save_snapshot(current)
        print(f"First run: saved {len(current)} decisions as baseline.")
        return

    prev_map = {d["key"]: d for d in previous}
    curr_map = {d["key"]: d for d in current}

    new_decisions = [d for k, d in curr_map.items() if k not in prev_map]
    updated_decisions = [
        d for k, d in curr_map.items()
        if k in prev_map and decision_changed(prev_map[k], d)
    ]

    if not new_decisions and not updated_decisions:
        print("No changes found.")
        return

    lines = []

    if new_decisions:
        count = len(new_decisions)
        lines.append(f"⚾ <b>{count} uusi kurinpitopäätös!</b>\n")
        for d in new_decisions:
            lines.append(format_decision(d))

    if updated_decisions:
        lines.append(f"\n✏️ <b>{len(updated_decisions)} kurinpitopäätös päivitetty!</b>\n")
        for d in updated_decisions:
            lines.append(format_decision(d))

    lines.append(f"\n🔗 {PAGE_URL}")

    message = "\n".join(lines)
    send_telegram(message)
    save_snapshot(current)
    print("Notification sent and snapshot updated.")


if __name__ == "__main__":
    main()
