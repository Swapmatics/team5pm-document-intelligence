#!/usr/bin/env python3
"""Local test desk. The browser talks to this process; this process talks to n8n."""

import base64
import hashlib
import json
import os
import re
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

import hold
from engine import alert_lines, extract_pdf, extract_word, is_word, marked, read_pages, read_word, review_problems
from scan import scan_bytes

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
STORE = REPO / "storage"
PORT = 8787
MAX_BYTES = 25 * 1024 * 1024

# The link is the chat. A superuser maintains this map. The person does not type it.
STAFF = {
    "andre": {
        "id": "andre",
        "submitted_by": "Andre",
        "department": "finance",
        "label": "Andre · superuser",
        "slack_user_id": "U0BUFKGUH3J",
        "email": "team5pmdocintel@gmail.com",
        "superuser": True,
    },
    "finance": {
        "id": "finance",
        "submitted_by": "Finance",
        "department": "finance",
        "label": "Finance",
        "superuser": False,
    },
    "projects": {
        "id": "projects",
        "submitted_by": "Projects",
        "department": "projects",
        "label": "Projects",
        "superuser": False,
    },
    "accounts": {
        "id": "accounts",
        "submitted_by": "Accounts",
        "department": "accounts",
        "label": "Accounts",
        "superuser": False,
    },
}


def load_env():
    values = {}
    path = REPO / ".env"
    if not path.exists():
        return values
    for line in path.read_text().splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


ENV = load_env()
WEBHOOK_SECRET = ENV.get("DOCINTEL_WEBHOOK_SECRET", "")
WEBHOOK_HEADER = ENV.get("DOCINTEL_WEBHOOK_HEADER") or "X-Docintel-Key"
N8N = ENV.get("DOCINTEL_N8N") or "http://127.0.0.1:5680/webhook"
if not WEBHOOK_SECRET:
    raise SystemExit("DOCINTEL_WEBHOOK_SECRET is missing. The desk will not start without it.")


def public_person(person):
    return {
        "id": person["id"],
        "submitted_by": person["submitted_by"],
        "department": person["department"],
        "label": person["label"],
        "view": "every department" if person.get("superuser") else person["department"],
    }


def person_from_query(query):
    asked = query.get("as", [""])[0]
    if asked:
        return STAFF.get(asked)
    slack_id = query.get("slack", [""])[0]
    for person in STAFF.values():
        if person.get("slack_user_id") == slack_id:
            return person
    return None


class Desk(BaseHTTPRequestHandler):
    def _send(self, code, body, content_type):
        data = body if isinstance(body, bytes) else body.encode()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/who":
            person = person_from_query(parse_qs(parsed.query))
            if not person:
                self._send(404, '{"error":"unknown"}', "application/json")
                return
            self._send(200, json.dumps(public_person(person)), "application/json")
            return
        if parsed.path == "/thread":
            person = person_from_query(parse_qs(parsed.query))
            if not person:
                self._send(401, '{"message":"This page does not say who you are."}', "application/json")
                return
            code, body = proxy(N8N + "/docintel-thread", timeout=30)
            if code != 200:
                self._send(code, body or b'{"message":"The thread did not load."}', "application/json")
                return
            self._send(200, json.dumps(filter_thread(body, person)), "application/json")
            return
        if parsed.path == "/alerts":
            person = person_from_query(parse_qs(parsed.query))
            if not person:
                self._send(401, '{"message":"This page does not say who you are."}', "application/json")
                return
            if not person.get("superuser"):
                self._send(200, '{"alerts":[]}', "application/json")
                return
            try:
                self._send(200, json.dumps(sync_alerts()), "application/json")
            except RuntimeError as exc:
                self._send(502, json.dumps({"message": str(exc)}), "application/json")
            return
        if parsed.path == "/status":
            person = person_from_query(parse_qs(parsed.query))
            if not person:
                self._send(401, '{"message":"This page does not say who you are."}', "application/json")
                return
            status = stack_status()
            if not person.get("superuser"):
                status["sheet_url"] = ""
            self._send(200, json.dumps(status), "application/json")
            return
        if parsed.path == "/records":
            person = person_from_query(parse_qs(parsed.query))
            if not person:
                self._send(401, '{"message":"This page does not say who you are."}', "application/json")
                return
            code, body = proxy(N8N + "/docintel-records", timeout=30)
            if code != 200:
                self._send(code, body or b'{"message":"The record book did not load."}', "application/json")
                return
            self._send(200, json.dumps(filter_book(body, person)), "application/json")
            return
        if parsed.path == "/file":
            self.serve_original(parse_qs(parsed.query))
            return
        self._send(200, (ROOT / "index.html").read_bytes(), "text/html; charset=utf-8")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_BYTES:
            self._send(413, '{"message":"That file is over 25 MB, so I did not read it."}', "application/json")
            return
        payload = self.rfile.read(length)
        content_type = self.headers.get("Content-Type", "")
        if hold.updating() and not self.path.startswith("/extract"):
            self.during_update(payload, content_type)
            return
        if self.path.startswith("/extract"):
            self.extract_document(payload)
            return
        if self.path.startswith("/review"):
            self.review_document(payload)
            return
        if self.path.startswith("/case"):
            self.run_case(payload)
            return
        if self.path.startswith("/confirm"):
            try:
                data = json.loads(payload.decode() or "{}")
            except json.JSONDecodeError:
                self._send(400, '{"message":"This chat does not say who you are."}', "application/json")
                return
            person = STAFF.get(str(data.get("as") or ""))
            if not person:
                self._send(400, '{"message":"This chat does not say who you are, so I did not record an answer."}', "application/json")
                return
            data["submitted_by"] = person["submitted_by"]
            data.pop("as", None)
            payload = json.dumps(data).encode()
            req = n8n_request(N8N + "/docintel-confirm", data=payload, headers={"Content-Type": "application/json"}, method="POST")
        else:
            person = STAFF.get(form_field(payload, "as"))
            if not person:
                self._send(400, '{"message":"This chat does not say who you are, so I did not read the file."}', "application/json")
                return
            prepared = inspect_upload(payload, content_type)
            if prepared.get("error"):
                self._send(prepared["status"], json.dumps({"message": prepared["error"]}), "application/json")
                return
            payload = stamp_form(payload, content_type, person, prepared)
            req = n8n_request(
                N8N + "/docintel-submit",
                data=payload,
                headers={"Content-Type": content_type or "application/octet-stream"},
                method="POST",
            )
        code, body = proxy_request(req, timeout=60)
        self._send(code, body or b'{"message":"The record book did not answer."}', "application/json")

    def run_case(self, payload):
        try:
            data = json.loads(payload.decode() or "{}")
        except json.JSONDecodeError:
            self._send(400, '{"message":"This chat does not say who you are."}', "application/json")
            return
        person = STAFF.get(str(data.get("as") or ""))
        if not person:
            self._send(400, '{"message":"This chat does not say who you are, so I did not read the file."}', "application/json")
            return
        case = CASES.get(str(data.get("name") or ""))
        if not case:
            self._send(400, '{"message":"That case is not on this desk."}', "application/json")
            return
        samples = REPO / "03-samples"
        file_path = (samples / case["file"]).resolve()
        if not str(file_path).startswith(str(samples.resolve()) + "/") or not file_path.is_file():
            self._send(404, '{"message":"That fixture file is not on disk."}', "application/json")
            return
        raw = file_path.read_bytes()
        flagged = scan_bytes(raw)
        if flagged:
            self._send(422, json.dumps({"message": flagged}), "application/json")
            return
        prepared = {
            "data": raw,
            "name": file_path.name,
            "storage_uri": "",
            "prepared_pages": 0,
            "prepared_text": "",
        }
        if raw.startswith(b"%PDF"):
            try:
                pages, text = marked_pages(raw)
            except RuntimeError as exc:
                self._send(500, json.dumps({"message": str(exc)}), "application/json")
                return
            prepared["prepared_pages"] = pages
            prepared["prepared_text"] = base64.b64encode(text.encode("utf-8")).decode("ascii")
        body, content_type = encode_case(person, case, prepared)
        req = n8n_request(
            N8N + "/docintel-submit",
            data=body,
            headers={"Content-Type": content_type},
            method="POST",
        )
        code, reply = proxy_request(req, timeout=60)
        self._send(code, reply or b'{"message":"The record book did not answer."}', "application/json")

    def serve_original(self, query):
        person = person_from_query(query)
        if not person:
            self._send(401, '{"message":"This page does not say who you are."}', "application/json")
            return
        document_id = query.get("document_id", [""])[0]
        code, body = proxy(N8N + "/docintel-records", timeout=30)
        if code != 200:
            self._send(code, body or b'{"message":"The record book did not load."}', "application/json")
            return
        book = filter_book(body, person)
        row = None
        for key in ("current", "held", "history"):
            for item in book.get(key) or []:
                if item.get("document_id") == document_id:
                    row = item
        if not row:
            self._send(404, '{"message":"That original is not on a record you can see."}', "application/json")
            return
        key = str(row.get("storage_key") or "")
        if not key or ".." in key or key.startswith("/"):
            self._send(404, '{"message":"The original file is not in the store."}', "application/json")
            return
        try:
            obj = minio_client().get_object(Bucket="docintel-originals", Key=key)
            data = obj["Body"].read()
        except Exception:
            self._send(404, '{"message":"The original file is not in the store."}', "application/json")
            return
        kind = row.get("mime_type") or "application/octet-stream"
        self._send(200, data, kind)

    def extract_document(self, payload):
        if self.headers.get(WEBHOOK_HEADER) != WEBHOOK_SECRET:
            self._send(401, '{"message":"This request is not from the desk."}', "application/json")
            return
        try:
            data = json.loads(payload.decode() or "{}")
        except json.JSONDecodeError:
            self._send(400, '{"error":{"message":"The extraction request was not JSON."}}', "application/json")
            return
        key = str(data.get("storage_key") or "")
        if not key or ".." in key or key.startswith("/"):
            self._send(400, '{"error":{"message":"The original is not a stored object, so I did not read it."}}', "application/json")
            return
        try:
            obj = minio_client().get_object(Bucket="docintel-originals", Key=key)
            pdf = obj["Body"].read()
        except Exception:
            self._send(502, '{"error":{"message":"The original file is not in the store, so I did not read it."}}', "application/json")
            return
        flagged = scan_bytes(pdf)
        if flagged:
            self._send(200, json.dumps({"error": {"message": flagged}}), "application/json")
            return
        word = is_word(pdf)
        if not word and not pdf.startswith(b"%PDF"):
            self._send(200, json.dumps({"error": {"message": "This file is not a PDF or a Word document, so the reader did not open it."}}), "application/json")
            return
        try:
            body = extract_word(pdf, str(data.get("stated_type") or "")) if word else extract_pdf(pdf, str(data.get("stated_type") or ""))
        except Exception as exc:
            body = {"error": {"message": str(exc)}}
        else:
            try:
                log_usage(str(data.get("document_id") or ""), body.get("usage") or {})
            except RuntimeError:
                pass
        self._send(200, json.dumps(body), "application/json")

    def review_document(self, payload):
        try:
            data = json.loads(payload.decode() or "{}")
        except json.JSONDecodeError:
            self._send(400, '{"message":"This chat does not say who you are."}', "application/json")
            return
        person = STAFF.get(str(data.get("as") or ""))
        if not person:
            self._send(400, '{"message":"This chat does not say who you are, so I did not change the record."}', "application/json")
            return
        document_id = str(data.get("document_id") or "")
        try:
            rows = ledger_rows()
        except RuntimeError as exc:
            self._send(502, json.dumps({"message": str(exc)}), "application/json")
            return
        row = next((item for item in rows if item.get("document_id") == document_id), None)
        if not row or not sees(person, row):
            self._send(404, '{"message":"That record is not one you can review."}', "application/json")
            return
        if row.get("status") != "held":
            self._send(409, '{"message":"That record is not held, so I did not change it."}', "application/json")
            return
        problems, merged, evidence = review_problems(row, data.get("fields") or {}, data.get("ack_pages") or [])
        if problems:
            message = " ".join(problems)
            try:
                log_review(document_id, person["submitted_by"], message)
            except RuntimeError:
                pass
            self._send(200, json.dumps({"message": message, "status": "held", "document_id": document_id}), "application/json")
            return
        stated = str(row.get("stated_type") or "")
        reference = (merged.get("reference_number") or "").strip()
        matches = []
        if reference:
            for item in rows:
                if item.get("document_id") == document_id:
                    continue
                if item.get("status") != "accepted" or item.get("superseded_by"):
                    continue
                if (item.get("reference_number") or "") != reference:
                    continue
                if (item.get("stated_type") or "") != stated:
                    continue
                if (item.get("department") or "") != (row.get("department") or ""):
                    continue
                left = str(item.get("client_or_vendor_stated") or "").strip()
                right = str(row.get("client_or_vendor_stated") or "").strip()
                if left and right and left != right:
                    continue
                if item.get("content_sha256") and item.get("content_sha256") == row.get("content_sha256"):
                    continue
                matches.append(item)
        status = "accepted"
        supersedes = row.get("supersedes") or ""
        note = ""
        if len(matches) == 1:
            status = "awaiting_confirm"
            supersedes = matches[0]["document_id"]
        elif len(matches) > 1:
            status = "held"
            note = "More than one current record has this reference. I did not pick one."
        try:
            old_evidence = json.loads(row.get("field_evidence") or "[]")
        except json.JSONDecodeError:
            old_evidence = []
        changed = {item.get("field") for item in evidence}
        kept = [item for item in old_evidence if isinstance(item, dict) and item.get("field") not in changed]
        payload_row = {
            "document_id": document_id,
            "status": status,
            "supersedes": supersedes,
            "page_notes": row.get("page_notes") or "",
            "validation_notes": note,
            "field_evidence": json.dumps(kept + evidence),
            "reviewed_by": person["submitted_by"],
        }
        for key, value in merged.items():
            payload_row[key] = value
        try:
            ledger_sql("SELECT apply_review(%s::jsonb);" % dollar(json.dumps(payload_row)))
        except RuntimeError as exc:
            self._send(502, json.dumps({"message": str(exc)}), "application/json")
            return
        if status == "awaiting_confirm":
            message = (
                document_id + " matches " + supersedes
                + ", and the file is different. Should this replace the one on file? "
                + "Yes means the new one becomes current and the old one stays in History. "
                + "No means this file stays held and the current record is unchanged."
            )
        elif status == "held":
            message = note
        else:
            message = document_id + " is now the current record."
        try:
            log_review(document_id, person["submitted_by"], message)
        except RuntimeError:
            pass
        self._send(200, json.dumps({"message": message, "status": status, "document_id": document_id, "supersedes": supersedes}), "application/json")

    def during_update(self, payload, content_type):
        path = self.path.split("?", 1)[0]
        if path.startswith("/confirm") or path.startswith("/review"):
            self._send(200, json.dumps({"message": hold.ANSWER, "status": "updating", "kept": False}), "application/json")
            return
        if path.startswith("/case"):
            self._send(200, json.dumps({"message": hold.CASE, "status": "updating", "kept": False}), "application/json")
            return
        data, name = file_bytes(payload, content_type)
        if not data:
            self._send(200, json.dumps({"message": hold.RETRY, "status": "updating", "kept": False}), "application/json")
            return
        hold.park(name, data, {
            "person_id": form_field(payload, "as") or "andre",
            "stated_type": form_field(payload, "stated_type") or "other",
            "client": form_field(payload, "client"),
            "door": "desk",
        })
        self._send(200, json.dumps({"message": hold.KEPT, "status": "updating", "kept": True}), "application/json")

    def log_message(self, fmt, *args):
        print(fmt % args)


def form_field(body, name):
    needle = f'name="{name}"'.encode()
    start = body.find(needle)
    if start < 0:
        return ""
    value_at = body.find(b"\r\n\r\n", start)
    if value_at < 0:
        return ""
    value_at += 4
    end = body.find(b"\r\n", value_at)
    if end < 0:
        return ""
    return body[value_at:end].decode("utf-8", "replace")


def stamp_form(body, content_type, person, prepared):
    marker = "boundary="
    if marker not in content_type:
        return body
    boundary = content_type.split(marker, 1)[1].split(";", 1)[0].strip().strip('"')
    closing = f"--{boundary}--".encode()
    idx = body.rfind(closing)
    if idx < 0:
        return body
    fields = {
        "submitted_by": person["submitted_by"],
        "department": person["department"],
        "storage_uri": prepared["storage_uri"],
        "prepared_pages": str(prepared.get("prepared_pages") or ""),
        "prepared_text": prepared.get("prepared_text") or "",
    }
    extra = b""
    for name, value in fields.items():
        extra += (
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'
        ).encode()
    return body[:idx] + extra + body[idx:]


def n8n_request(url, data=None, headers=None, method=None):
    merged = {WEBHOOK_HEADER: WEBHOOK_SECRET}
    if headers:
        merged.update(headers)
    return Request(url, data=data, headers=merged, method=method)


def proxy(url, timeout):
    return proxy_request(n8n_request(url), timeout)


def proxy_request(req, timeout):
    try:
        with urlopen(req, timeout=timeout) as res:
            return res.status, res.read()
    except HTTPError as err:
        return err.code, err.read()
    except URLError:
        return 502, b'{"message":"The record book is not reachable."}'


def sees(person, row):
    if person.get("superuser"):
        return True
    return (row.get("department") or "") == person.get("department")


def for_person(person, row):
    if person.get("superuser") or person.get("department") == "finance":
        return row
    hidden = dict(row)
    hidden.pop("currency", None)
    hidden.pop("total_amount", None)
    return hidden


def filter_book(raw, person):
    book = json.loads(raw.decode() or "{}")
    for key in ("current", "held", "history", "reading"):
        book[key] = [for_person(person, row) for row in book.get(key) or [] if sees(person, row)]
    return book


def filter_thread(raw, person):
    payload = json.loads(raw.decode() or "{}")
    if person.get("superuser"):
        return payload
    lines = []
    for line in payload.get("lines") or []:
        if (line.get("submitted_by") or "") == person.get("submitted_by"):
            lines.append(line)
    payload["lines"] = lines
    return payload


def file_bytes(body, content_type):
    marker = "boundary="
    if marker not in content_type:
        return b"", ""
    boundary = content_type.split(marker, 1)[1].split(";", 1)[0].strip().strip('"').encode()
    parts = body.split(b"--" + boundary)
    for part in parts:
        if b'name="data"' not in part:
            continue
        header, _, data = part.partition(b"\r\n\r\n")
        if data.endswith(b"\r\n"):
            data = data[:-2]
        name = "original"
        key = b'filename="'
        at = header.find(key)
        if at >= 0:
            name = header[at + len(key):].split(b'"', 1)[0].decode("utf-8", "replace")
        return data, Path(name).name or "original"
    return b"", ""


def inspect_upload(body, content_type):
    data, name = file_bytes(body, content_type)
    if not data:
        return {"error": "No file was attached.", "status": 400}
    if len(data) > MAX_BYTES:
        return {"error": "That file is over 25 MB, so I did not read it.", "status": 413}
    flagged = scan_bytes(data)
    if flagged:
        return {"error": flagged, "status": 422}
    kind = magic_kind(data)
    if not kind:
        return {"error": "I can read a PDF, a Word document, a PNG, or a JPEG. This file is none of those, so I did not store it.", "status": 400}
    digest = hashlib.sha256(data).hexdigest()
    prepared_pages = 0
    prepared_text = ""
    if kind == "pdf":
        try:
            prepared_pages, prepared_text = marked_pages(data)
        except RuntimeError as exc:
            return {"error": str(exc), "status": 500}
        prepared_text = base64.b64encode(prepared_text.encode("utf-8")).decode("ascii")
    elif kind == "word":
        sections = read_word(data)
        prepared_pages = len(sections)
        prepared_text = base64.b64encode(marked(sections).encode("utf-8")).decode("ascii")
    return {
        "status": 200,
        "data": data,
        "name": name,
        "storage_uri": f"storage/{digest}/{name}",
        "prepared_pages": prepared_pages,
        "prepared_text": prepared_text,
    }


def minio_client():
    import boto3
    from botocore.config import Config
    return boto3.client(
        "s3",
        endpoint_url=ENV.get("MINIO_ENDPOINT") or "http://127.0.0.1:9002",
        aws_access_key_id=ENV.get("MINIO_ROOT_USER") or "",
        aws_secret_access_key=ENV.get("MINIO_ROOT_PASSWORD") or "",
        region_name="us-east-1",
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def keep_original_if_recorded(raw, prepared):
    try:
        result = json.loads(raw.decode() or "{}")
    except json.JSONDecodeError:
        return raw
    if result.get("status") not in ("accepted", "held", "awaiting_confirm"):
        return raw
    if not result.get("document_id"):
        return raw
    try:
        folder = STORE / hashlib.sha256(prepared["data"]).hexdigest()
        folder.mkdir(parents=True, exist_ok=True)
        (folder / prepared["name"]).write_bytes(prepared["data"])
    except OSError:
        note = " The record was written, but the original file was not stored."
        result["message"] = (result.get("message") or "The record was written.") + note
        result["original_stored"] = False
        return json.dumps(result).encode()
    return raw


def marked_pages(data):
    pages = read_pages(data)
    return len(pages), marked(pages)


CASES = {
    "invoice": {"file": "invoice.pdf", "stated_type": "invoice", "client": "Northwind Supplies"},
    "invoice-again": {"file": "invoice.pdf", "stated_type": "invoice", "client": "Northwind Supplies"},
    "invoice-revised": {"file": "invoice-revised.pdf", "stated_type": "invoice", "client": "Northwind Supplies"},
    "contract-blank": {"file": "contract-missing-page.pdf", "stated_type": "contract", "client": "Northwind Supplies"},
    "ocr-wrong": {"file": "invoice-wrong-words.pdf", "stated_type": "invoice", "client": "Northwind Supplies"},
}


def encode_case(person, case, prepared):
    boundary = "----docintelcase"
    chunks = []

    def add(name, value, filename=None, mime=None, raw=None):
        head = f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"'
        if filename:
            head += f'; filename="{filename}"'
        head += "\r\n"
        if mime:
            head += f"Content-Type: {mime}\r\n"
        head += "\r\n"
        chunks.append(head.encode() + (raw if raw is not None else value.encode()) + b"\r\n")

    add("data", "", filename=prepared["name"], mime="application/pdf", raw=prepared["data"])
    add("as", person["id"])
    add("stated_type", case["stated_type"])
    add("client", case["client"])
    add("submitted_by", person["submitted_by"])
    add("department", person["department"])
    add("storage_uri", prepared["storage_uri"])
    add("prepared_pages", str(prepared.get("prepared_pages") or ""))
    add("prepared_text", prepared.get("prepared_text") or "")
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def dollar(value):
    tag = "doc"
    while "$%s$" % tag in value:
        tag += "x"
    return "$%s$%s$%s$" % (tag, value, tag)


def ledger_sql(statement):
    env = os.environ.copy()
    env.setdefault("DOCKER_HOST", "unix:///Users/dreserver/.colima/default/docker.sock")
    env["PATH"] = "/opt/homebrew/bin:" + env.get("PATH", "")
    proc = subprocess.run(
        ["docker", "exec", "-i", "docintel-postgres", "psql", "-U", "postgres", "-d", "docintel", "-v", "ON_ERROR_STOP=1", "-t", "-A"],
        input=statement if statement.endswith("\n") else statement + "\n",
        capture_output=True,
        text=True,
        env=env,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or "The ledger did not answer.").strip()
        raise RuntimeError(detail)
    return (proc.stdout or "").strip()


def ledger_rows():
    raw = ledger_sql("SELECT COALESCE(json_agg(row_to_json(documents)), '[]'::json)::text FROM documents;")
    return json.loads(raw or "[]")


def log_review(document_id, submitted_by, body):
    payload = json.dumps({"document_id": document_id, "submitted_by": submitted_by, "body": body})
    ledger_sql("SELECT log_thread(%s::jsonb);" % dollar(payload))


def sync_alerts():
    rows = ledger_rows()
    snapshot = alert_lines(rows)
    open_raw = ledger_sql("SELECT COALESCE(json_agg(row_to_json(alerts)), '[]'::json)::text FROM alerts WHERE resolved_at = '';")
    open_rows = json.loads(open_raw or "[]")
    open_kinds = {item.get("kind") for item in open_rows}
    wanted = {item["kind"]: item["body"] for item in snapshot["alerts"]}
    stamp = datetime_stamp()
    for kind, body in wanted.items():
        if kind in open_kinds:
            continue
        ledger_sql(
            "INSERT INTO alerts (kind, body, opened_at) VALUES (%s, %s, %s);"
            % (dollar(kind), dollar(body), dollar(stamp))
        )
    for kind in open_kinds:
        if kind in wanted:
            continue
        ledger_sql("UPDATE alerts SET resolved_at = %s WHERE resolved_at = '' AND kind = %s;" % (dollar(stamp), dollar(kind)))
    snapshot["alerts"] = [{"kind": kind, "body": body} for kind, body in wanted.items()]
    return snapshot


def log_usage(document_id, usage):
    if not usage:
        return
    payload = json.dumps({
        "document_id": document_id,
        "model": "google/gemini-2.5-flash",
        "prompt_tokens": int(usage.get("prompt_tokens") or 0),
        "completion_tokens": int(usage.get("completion_tokens") or 0),
        "cost_usd": usage.get("cost_usd") or 0,
    })
    ledger_sql("SELECT log_model_usage(%s::jsonb);" % dollar(payload))


def board_counts():
    unread = 0
    spend = "0"
    try:
        for row in ledger_rows():
            unread += len(re.findall(r"Page \d+ could not be read", row.get("page_notes") or ""))
        spend = ledger_sql(
            "SELECT COALESCE(SUM(cost_usd), 0)::text FROM model_usage "
            "WHERE (created_at::timestamptz AT TIME ZONE 'Africa/Johannesburg')::date "
            "= (clock_timestamp() AT TIME ZONE 'Africa/Johannesburg')::date;"
        ) or "0"
    except RuntimeError:
        return {"unreadable_pages": None, "model_spend_usd": None}
    return {"unreadable_pages": unread, "model_spend_usd": spend}


def datetime_stamp():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


SHEET_STATE = {"connected": False, "url": ""}


def sync_sheet():
    from sheet import push_sheet
    try:
        result = push_sheet(ledger_rows())
    except Exception as exc:
        print("sheet sync failed: %s" % exc)
        result = {"connected": False, "url": ""}
    SHEET_STATE.clear()
    SHEET_STATE.update(result)
    return SHEET_STATE


def stack_status():
    counts = board_counts()
    return {
        "n8n": http_up("http://127.0.0.1:5680/healthz"),
        "ledger": port_up("127.0.0.1", 5436),
        "redis": port_up("127.0.0.1", 6381),
        "bucket": port_up("127.0.0.1", 9002),
        "sheet": bool(SHEET_STATE.get("connected")),
        "sheet_url": SHEET_STATE.get("url") or "",
        "unreadable_pages": counts.get("unreadable_pages"),
        "model_spend_usd": counts.get("model_spend_usd"),
        "updating": hold.updating(),
        "updating_message": hold.KEPT if hold.updating() else "",
        "updating_retry": hold.RETRY if hold.updating() else "",
        "updating_answer": hold.ANSWER if hold.updating() else "",
    }


def http_up(url):
    try:
        with urlopen(url, timeout=2) as res:
            return res.status == 200
    except (HTTPError, URLError, TimeoutError, OSError):
        return False


def port_up(host, port):
    import socket
    try:
        sock = socket.create_connection((host, port), 1)
    except OSError:
        return False
    sock.close()
    return True


def magic_kind(data):
    if data.startswith(b"%PDF") and b"%%EOF" in data:
        return "pdf"
    if data.startswith(b"\x89PNG"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if is_word(data):
        return "word"
    return ""


def submit_parked(item):
    boundary = "----docintelhold"
    chunks = []

    def add(field, value, filename=None, raw=None):
        head = '--%s\r\nContent-Disposition: form-data; name="%s"' % (boundary, field)
        if filename:
            head += '; filename="%s"' % filename
        head += "\r\n\r\n"
        chunks.append(head.encode() + (raw if raw is not None else str(value).encode()) + b"\r\n")

    add("data", "", filename=item.get("name") or "original", raw=item.get("data") or b"")
    add("as", item.get("person_id") or "andre")
    add("stated_type", item.get("stated_type") or "other")
    add("client", item.get("client") or "")
    chunks.append(("--%s--\r\n" % boundary).encode())
    body = b"".join(chunks)
    request = Request(
        "http://127.0.0.1:%d/submit" % PORT,
        data=body,
        headers={"Content-Type": "multipart/form-data; boundary=%s" % boundary},
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            raw = response.read()
            code = response.status
    except HTTPError as err:
        raw = err.read()
        code = err.code
    except URLError:
        return 0, {}
    try:
        return code, json.loads(raw.decode() or "{}")
    except json.JSONDecodeError:
        return code, {"message": raw.decode("utf-8", "replace")}


def alert_loop():
    while True:
        try:
            if not hold.updating():
                hold.release(submit_parked)
        except Exception:
            pass
        try:
            sync_alerts()
        except Exception:
            pass
        try:
            sync_sheet()
        except Exception:
            pass
        time.sleep(60)


if __name__ == "__main__":
    threading.Thread(target=alert_loop, daemon=True).start()
    print(f"DocIntel desk on http://127.0.0.1:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Desk).serve_forever()
