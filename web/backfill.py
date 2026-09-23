#!/usr/bin/env python3
"""Archive door. A backlog is admitted only while no live file is waiting to be read."""

import hashlib
import json
import os
import time
from pathlib import Path

from slack_door import desk_json, encode_form, load_env, parse_instruction

ROOT = Path(__file__).resolve().parent.parent
READABLE = {".pdf", ".png", ".jpg", ".jpeg", ".doc", ".docx"}
MIME = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def ledger_sql(statement):
    from server import ledger_sql as run
    return run(statement)


def register_directory(folder):
    path = Path(folder)
    if not path.is_dir():
        return 0
    added = 0
    for file_path in sorted(path.iterdir()):
        if not file_path.is_file() or file_path.suffix.lower() not in READABLE:
            continue
        data = file_path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        stated, client = parse_instruction(file_path.name)
        if not stated:
            stated = "other"
        if client is None:
            client = ""
        before = ledger_sql("SELECT count(*) FROM backfill_items;")
        ledger_sql(
            "INSERT INTO backfill_items (content_sha256, original_filename, local_path, mime_type, stated_type, client_or_vendor_stated) "
            "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (content_sha256) DO NOTHING;"
            % (
                _quote(digest),
                _quote(file_path.name),
                _quote(str(file_path)),
                _quote(MIME.get(file_path.suffix.lower(), "application/octet-stream")),
                _quote(stated),
                _quote(client),
            )
        )
        after = ledger_sql("SELECT count(*) FROM backfill_items;")
        if after != before:
            added += 1
        del payload
    return added


def _quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def claim(batch):
    raw = ledger_sql("SELECT claim_backfill(%d)::text;" % int(batch))
    return json.loads(raw or "{}")


def mark(item_id, status, document_id, note):
    ledger_sql(
        "UPDATE backfill_items SET status = %s, document_id = %s, note = %s WHERE id = %d;"
        % (_quote(status), _quote(document_id), _quote(note), int(item_id))
    )
    if document_id and status == "admitted":
        ledger_sql(
            "UPDATE documents SET source = 'backfill' WHERE document_id = %s AND source = 'live';" % _quote(document_id)
        )


def admit_once(batch):
    result = claim(batch)
    admitted = 0
    for item in result.get("claimed") or []:
        path = Path(item.get("local_path") or "")
        if not path.is_file():
            mark(item["id"], "waiting", "", "The archive file is not on disk, so it stays in the queue.")
            continue
        data = path.read_bytes()
        person_id = os.environ.get("DOCINTEL_DRIVE_AS") or "andre"
        body, content_type = encode_form(
            person_id,
            item.get("stated_type") or "other",
            item.get("client_or_vendor_stated") or "",
            item.get("original_filename") or path.name,
            data,
            item.get("mime_type") or "application/octet-stream",
        )
        try:
            code, reply = desk_json("POST", "/submit", body, content_type, timeout=90)
        except RuntimeError as exc:
            mark(item["id"], "waiting", "", str(exc))
            continue
        document_id = (reply or {}).get("document_id") or ""
        status = (reply or {}).get("status") or ""
        message = (reply or {}).get("message") or "The record book did not answer."
        if code == 200 and status == "received":
            mark(item["id"], "admitted", document_id, message)
            admitted += 1
        elif code == 200 and status == "identical":
            mark(item["id"], "skipped", document_id, message)
        else:
            mark(item["id"], "waiting", document_id, message)
    result["admitted"] = admitted
    return result


def main():
    load_env(ROOT / "deploy" / ".env")
    load_env(ROOT / ".env")
    folder = os.environ.get("DOCINTEL_BACKFILL_DIR", "")
    batch = int(os.environ.get("DOCINTEL_BACKFILL_BATCH") or "25")
    if not folder:
        return
    register_directory(folder)
    while True:
        try:
            admit_once(batch)
        except Exception as exc:
            print("backfill: %s" % type(exc).__name__)
        time.sleep(60)


if __name__ == "__main__":
    main()
