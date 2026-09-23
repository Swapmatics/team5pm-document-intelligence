#!/usr/bin/env python3
"""Google Drive folder door. New files use the same desk intake as a drop on the desk."""

import json
import os
import time
from pathlib import Path

from slack_door import desk_json, encode_form, load_env, parse_instruction

ROOT = Path(__file__).resolve().parents[2]
SEEN = ROOT / "04-run" / "drive-seen.json"


def seen_ids():
    if not SEEN.exists():
        return set()
    try:
        return set(json.loads(SEEN.read_text()))
    except json.JSONDecodeError:
        return set()


def remember(ids):
    SEEN.write_text(json.dumps(sorted(ids)))


def person():
    from server import STAFF
    asked = os.environ.get("DOCINTEL_DRIVE_AS") or "andre"
    return STAFF.get(asked)


def poll():
    folder = os.environ.get("DOCINTEL_DRIVE_FOLDER", "")
    key_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE") or str(ROOT / "04-run" / "google-service-account.json")
    who = person()
    if not folder or not who or not Path(key_path).is_file():
        return
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    import io

    creds = Credentials.from_service_account_file(key_path, scopes=["https://www.googleapis.com/auth/drive.readonly"])
    service = build("drive", "v3", credentials=creds, cache_discovery=False)
    found = service.files().list(
        q="'%s' in parents and trashed = false" % folder.replace("'", ""),
        fields="files(id,name,mimeType)",
        pageSize=50,
    ).execute()
    known = seen_ids()
    for item in found.get("files") or []:
        file_id = item.get("id")
        if not file_id or file_id in known:
            continue
        if file_id == os.environ.get("DOCINTEL_DRIVE_LINKS_FOLDER", ""):
            known.add(file_id)
            continue
        mime = item.get("mimeType") or ""
        if mime not in ("application/pdf", "image/png", "image/jpeg", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"):
            known.add(file_id)
            continue
        buffer = io.BytesIO()
        request = service.files().get_media(fileId=file_id)
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        data = buffer.getvalue()
        stated, client = parse_instruction(item.get("name") or "")
        if not stated:
            stated = "other"
        if client is None:
            client = ""
        body, content_type = encode_form(who["id"], stated, client, item.get("name") or "drive-file", data, mime)
        desk_json("POST", "/submit", body, content_type, timeout=60)
        known.add(file_id)
    remember(known)


def main():
    load_env(ROOT / "04-run" / ".env")
    load_env(ROOT / ".env")
    while True:
        try:
            poll()
        except Exception as exc:
            print("drive door: %s" % exc)
        time.sleep(60)


if __name__ == "__main__":
    main()
