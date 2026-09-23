"""Update gate. A file that arrives during a patch is kept, and the person is told."""

import hashlib
import json
import os
import time
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
FLAG = ROOT / "04-run" / "updating"
PARK = ROOT / "04-run" / "held-during-update"
TOLD = ROOT / "04-run" / "update-told.json"

KEPT = (
    "An update is in progress. I kept your file. The desk is not offline. "
    "I will read it when the update has finished."
)
RETRY = (
    "An update is in progress. I did not take that file. It is still with you. "
    "The desk is not offline. Send it again when the update has finished."
)
ANSWER = (
    "An update is in progress. I did not record that answer. The desk is not offline. "
    "Send it again when the update has finished."
)
CASE = "An update is in progress. I did not run that case. The desk is not offline."
PAUSE = "An update is in progress. I did not start that. The desk is not offline. Send it again when the update has finished."
DRIVE = (
    "An update is in progress. I left %s in the Drive folder. It is not lost. "
    "The desk is not offline. I will read it when the update has finished."
)


def updating():
    return FLAG.is_file()


def park(name, data, meta):
    if not data:
        return ""
    PARK.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(data).hexdigest()
    target = PARK / digest
    if not target.exists():
        target.write_bytes(data)
    side = PARK / (digest + ".json")
    current = {}
    if side.exists():
        try:
            current = json.loads(side.read_text())
        except json.JSONDecodeError:
            current = {}
    current.update({
        "name": name or current.get("name") or "original",
        "mime": (meta or {}).get("mime") or current.get("mime") or "application/octet-stream",
        "person_id": (meta or {}).get("person_id") or current.get("person_id") or "",
        "stated_type": (meta or {}).get("stated_type") or current.get("stated_type") or "other",
        "client": (meta or {}).get("client") if meta and "client" in meta else current.get("client") or "",
        "door": (meta or {}).get("door") or current.get("door") or "",
        "parked_at": current.get("parked_at") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
    side.write_text(json.dumps(current))
    return digest


def pending():
    if not PARK.is_dir():
        return []
    rows = []
    for side in sorted(PARK.glob("*.json")):
        try:
            meta = json.loads(side.read_text())
        except json.JSONDecodeError:
            continue
        if meta.get("skip"):
            continue
        blob = PARK / side.stem
        if not blob.is_file():
            continue
        meta["digest"] = side.stem
        meta["data"] = blob.read_bytes()
        rows.append(meta)
    return rows


def finish(digest):
    for path in (PARK / digest, PARK / (digest + ".json")):
        try:
            path.unlink()
        except OSError:
            pass


def skip(digest, reason):
    side = PARK / (digest + ".json")
    try:
        meta = json.loads(side.read_text())
    except (OSError, json.JSONDecodeError):
        meta = {}
    meta["skip"] = reason or "not submitted"
    side.write_text(json.dumps(meta))


def told_ids():
    if not TOLD.exists():
        return set()
    try:
        return set(json.loads(TOLD.read_text()))
    except json.JSONDecodeError:
        return set()


def remember_told(file_id):
    ids = told_ids()
    ids.add(file_id)
    TOLD.write_text(json.dumps(sorted(ids)))


def _post_slack(token, channel, text):
    body = json.dumps({"channel": channel, "text": text}).encode()
    request = Request(
        "https://slack.com/api/chat.postMessage",
        data=body,
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode() or "{}")
    return bool(payload.get("ok"))


def tell_slack(text):
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        return False
    from server import STAFF
    channels = [
        person.get("slack_user_id")
        for person in STAFF.values()
        if person.get("superuser") and person.get("slack_user_id")
    ]
    if not channels:
        return False
    sent = False
    for channel in channels:
        last = None
        for _ in range(4):
            try:
                if _post_slack(token, channel, text):
                    sent = True
                    last = None
                    break
            except Exception as exc:
                last = exc
            time.sleep(1)
        if last is not None:
            return False
    return sent


def must_call(post, text):
    last = None
    for _ in range(4):
        try:
            post(text)
            return
        except Exception as exc:
            last = exc
            time.sleep(1)
    raise last


def release(post_form):
    if updating():
        return 0
    done = 0
    for item in pending():
        code, reply = post_form(item)
        status = (reply or {}).get("status") or ""
        if code == 200 and status in ("received", "identical", "accepted", "held", "awaiting_confirm", "needs_details"):
            finish(item["digest"])
            done += 1
            continue
        if code in (400, 413, 422):
            skip(item["digest"], (reply or {}).get("message") or "not submitted")
    return done
