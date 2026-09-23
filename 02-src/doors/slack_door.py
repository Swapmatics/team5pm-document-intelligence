#!/usr/bin/env python3
"""Slack DM door. A file dropped in the chat uses the same desk intake as the browser."""

import json
import os
import re
import threading
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
DESK = os.environ.get("DOCINTEL_DESK") or "http://127.0.0.1:8787"
TYPES = ("invoice", "contract", "brief", "other")
MAX_BYTES = 25 * 1024 * 1024

pending = {}
pending_lock = threading.Lock()
posted_alerts = set()


def load_env(path):
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def parse_instruction(text):
    raw = text or ""
    low = raw.lower()
    found = [name for name in TYPES if re.search(r"\b%s\b" % name, low)]
    stated = found[0] if len(found) == 1 else ""
    client = None
    match = re.search(r"\bfor\s+(.+)$", raw, re.I)
    if match:
        client = match.group(1).strip()
        if client.lower() == "none":
            client = ""
    elif re.search(r"\bnone\b", low):
        client = ""
    return stated, client


def decision_word(text):
    low = (text or "").strip().lower()
    if re.match(r"^yes\b", low):
        return "yes"
    if re.match(r"^no\b", low):
        return "no"
    return ""


def encode_form(person_id, stated, client, name, data, mime):
    boundary = "----docintelslack"
    chunks = []

    def add(field, value, filename=None, content_type=None, raw=None):
        head = '--%s\r\nContent-Disposition: form-data; name="%s"' % (boundary, field)
        if filename:
            head += '; filename="%s"' % filename
        head += "\r\n"
        if content_type:
            head += "Content-Type: %s\r\n" % content_type
        head += "\r\n"
        chunks.append(head.encode() + (raw if raw is not None else value.encode()) + b"\r\n")

    add("data", "", filename=name, content_type=mime, raw=data)
    add("as", person_id)
    add("stated_type", stated)
    add("client", client or "")
    chunks.append(("--%s--\r\n" % boundary).encode())
    return b"".join(chunks), "multipart/form-data; boundary=%s" % boundary


def desk_json(method, path, payload=None, content_type=None, timeout=60):
    data = None
    headers = {}
    if payload is not None:
        data = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        headers["Content-Type"] = content_type or "application/json"
    request = Request(DESK + path, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read()
            code = response.status
    except HTTPError as err:
        body = err.read()
        code = err.code
    except URLError as err:
        raise RuntimeError("The desk is not reachable.") from err
    try:
        parsed = json.loads(body.decode() or "{}")
    except json.JSONDecodeError:
        parsed = {"message": body.decode("utf-8", "replace")}
    return code, parsed


def person_for(slack_user_id):
    code, body = desk_json("GET", "/who?slack=%s" % slack_user_id, timeout=15)
    if code != 200:
        return None
    return body


def find_row(book, document_id):
    for key in ("reading", "current", "held", "history"):
        for row in book.get(key) or []:
            if row.get("document_id") == document_id:
                return row
    return None


def awaiting_rows(person_id):
    code, book = desk_json("GET", "/records?as=%s" % person_id, timeout=30)
    if code != 200:
        return []
    return [row for row in (book.get("held") or []) if row.get("status") == "awaiting_confirm"]


def latest_line(person_id, document_id):
    code, payload = desk_json("GET", "/thread?as=%s" % person_id, timeout=30)
    if code != 200:
        return ""
    body = ""
    for line in payload.get("lines") or []:
        if line.get("document_id") == document_id and line.get("body"):
            body = line["body"]
    return body


def follow_outcome(person_id, document_id, channel, client, opening):
    deadline = time.time() + 180
    while time.time() < deadline:
        try:
            code, book = desk_json("GET", "/records?as=%s" % person_id, timeout=30)
        except RuntimeError:
            time.sleep(3)
            continue
        row = find_row(book, document_id) if code == 200 else None
        if row and row.get("status") not in ("received", "processing"):
            text = latest_line(person_id, document_id) or opening
            if text == opening:
                text = row.get("page_notes") or row.get("validation_notes") or text
            try:
                client.chat_postMessage(channel=channel, text=text)
            except Exception:
                pass
            return
        time.sleep(3)


def submit_file(person, stated, client_name, name, data, mime, channel, client):
    body, content_type = encode_form(person["id"], stated, client_name, name, data, mime)
    code, reply = desk_json("POST", "/submit", body, content_type, timeout=60)
    message = reply.get("message") or "The record book did not answer."
    client.chat_postMessage(channel=channel, text=message)
    document_id = reply.get("document_id") or ""
    if code == 200 and document_id and reply.get("status") == "received":
        threading.Thread(
            target=follow_outcome,
            args=(person["id"], document_id, channel, client, message),
            daemon=True,
        ).start()


def download_file(client, slack_file):
    if (slack_file.get("size") or 0) > MAX_BYTES:
        return None, "That file is over 25 MB, so I did not read it."
    info = client.files_info(file=slack_file["id"])
    meta = info.get("file") or slack_file
    url = meta.get("url_private_download") or meta.get("url_private")
    if not url:
        return None, "I could not download that file from Slack."
    request = Request(url, headers={"Authorization": "Bearer " + client.token})
    with urlopen(request, timeout=60) as response:
        data = response.read()
    name = meta.get("name") or "original"
    mime = meta.get("mimetype") or "application/octet-stream"
    return (data, name, mime), ""


def handle_message(event, client):
    if event.get("bot_id") or event.get("subtype") in ("message_changed", "message_deleted", "bot_message"):
        return
    user_id = event.get("user") or ""
    channel = event.get("channel") or ""
    text = event.get("text") or ""
    if not user_id or not channel:
        return
    person = person_for(user_id)
    if not person:
        client.chat_postMessage(channel=channel, text="This chat is not on the staff map, so I will not read the file.")
        return
    files = [item for item in (event.get("files") or []) if item.get("id")]
    if not files:
        word = decision_word(text)
        with pending_lock:
            waiting = pending.get(user_id)
        if waiting:
            stated, client_name = parse_instruction(text)
            if not waiting.get("stated"):
                waiting["stated"] = stated
            if waiting.get("client") is None and client_name is not None:
                waiting["client"] = client_name
            if not waiting.get("stated"):
                client.chat_postMessage(channel=channel, text="What type is it: invoice, contract, brief, or other?")
                return
            if waiting.get("client") is None:
                client.chat_postMessage(channel=channel, text="Which client or vendor is it for? Say none if you do not have one.")
                return
            with pending_lock:
                pending.pop(user_id, None)
            submit_file(person, waiting["stated"], waiting["client"], waiting["name"], waiting["data"], waiting["mime"], channel, client)
            return
        if word:
            rows = awaiting_rows(person["id"])
            if len(rows) == 1:
                code, reply = desk_json("POST", "/confirm", {
                    "document_id": rows[0]["document_id"],
                    "decision": word,
                    "as": person["id"],
                })
                client.chat_postMessage(channel=channel, text=reply.get("message") or "The record book did not answer.")
                return
            if len(rows) > 1:
                names = ", ".join(row.get("document_id") or "" for row in rows)
                client.chat_postMessage(channel=channel, text="More than one file is waiting for a yes or a no (" + names + "). I did not pick one.")
                return
        return
    downloaded, error = download_file(client, files[0])
    if error:
        client.chat_postMessage(channel=channel, text=error)
        return
    data, name, mime = downloaded
    stated, client_name = parse_instruction(text)
    if not stated or client_name is None:
        with pending_lock:
            pending[user_id] = {
                "data": data,
                "name": name,
                "mime": mime,
                "stated": stated,
                "client": client_name,
            }
        if not stated:
            client.chat_postMessage(channel=channel, text="I have the file from " + person["label"] + ". What type is it: invoice, contract, brief, or other?")
        else:
            client.chat_postMessage(channel=channel, text="Which client or vendor is it for? Say none if you do not have one.")
        return
    with pending_lock:
        pending.pop(user_id, None)
    submit_file(person, stated, client_name, name, data, mime, channel, client)


def alert_channels():
    from server import STAFF
    return [person["slack_user_id"] for person in STAFF.values() if person.get("superuser") and person.get("slack_user_id")]


def watch_alerts(client):
    while True:
        try:
            code, payload = desk_json("GET", "/alerts?as=andre", timeout=20)
            if code == 200:
                current = []
                for item in payload.get("alerts") or []:
                    body = item.get("body") or ""
                    current.append(body)
                    if body and body not in posted_alerts:
                        for channel in alert_channels():
                            client.chat_postMessage(channel=channel, text=body)
                        posted_alerts.add(body)
                for old in list(posted_alerts):
                    if old not in current:
                        posted_alerts.discard(old)
        except Exception:
            pass
        time.sleep(60)


def main():
    load_env(ROOT / "04-run" / ".env")
    load_env(ROOT / ".env")
    bot = os.environ.get("SLACK_BOT_TOKEN", "")
    app_token = os.environ.get("SLACK_APP_TOKEN", "")
    if not bot or not app_token:
        raise SystemExit("SLACK_BOT_TOKEN and SLACK_APP_TOKEN are missing from 04-run/.env. The Slack door will not start.")
    from slack_bolt import App
    from slack_bolt.adapter.socket_mode import SocketModeHandler

    app = App(token=bot, signing_secret=os.environ.get("SLACK_SIGNING_SECRET") or "socket-mode")

    @app.event("message")
    def on_message(event, client):
        handle_message(event, client)

    threading.Thread(target=watch_alerts, args=(app.client,), daemon=True).start()
    SocketModeHandler(app, app_token).start()


if __name__ == "__main__":
    main()
