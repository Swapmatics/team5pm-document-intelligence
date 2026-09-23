"""Google Sheet projection of the ledger. One document, one row. The sheet is not the book."""

import io
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COLUMNS = (
    "document_id",
    "content_sha256",
    "original_filename",
    "file_link",
    "storage_key",
    "mime_type",
    "page_count",
    "submitted_by",
    "submitted_at",
    "department",
    "stated_type",
    "resolved_type",
    "client_or_vendor_stated",
    "client_or_vendor_resolved",
    "title",
    "parties",
    "counterparty",
    "document_date",
    "effective_date",
    "expiry_date",
    "currency",
    "total_amount",
    "reference_number",
    "why_it_exists",
    "what_changed",
    "page_notes",
    "status",
    "supersedes",
    "superseded_by",
    "validation_notes",
    "model_route",
    "reviewed_by",
    "reviewed_at",
    "accepted_at",
    "field_evidence",
    "source",
)
PAYMENT = ("currency", "total_amount")
TABS = ("Current", "Held", "Reading", "History")


def tab_of(row):
    status = row.get("status") or ""
    if status in ("received", "processing"):
        return "Reading"
    if status == "superseded" or row.get("superseded_by"):
        return "History"
    if status == "accepted":
        return "Current"
    return "Held"


def table_for(rows, tab):
    body = [list(COLUMNS)]
    for row in rows:
        if tab_of(row) != tab:
            continue
        body.append([
            "" if column == "file_link" or row.get(column) is None else str(row.get(column))
            for column in COLUMNS
        ])
    return body


def column_letter(index):
    number = index + 1
    letters = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def load_link_cache():
    path = ROOT / "deploy" / "file-links.json"
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}


def save_link_cache(cache):
    path = ROOT / "deploy" / "file-links.json"
    path.write_text(json.dumps(cache))


def original_bytes(storage_key):
    import boto3
    from botocore.config import Config
    client = boto3.client(
        "s3",
        endpoint_url=os.environ.get("MINIO_ENDPOINT") or "http://127.0.0.1:9002",
        aws_access_key_id=os.environ.get("MINIO_ROOT_USER") or "",
        aws_secret_access_key=os.environ.get("MINIO_ROOT_PASSWORD") or "",
        region_name="us-east-1",
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )
    obj = client.get_object(Bucket="docintel-originals", Key=storage_key)
    return obj["Body"].read()


def user_access_token():
    binary = "/opt/homebrew/bin/gcloud"
    if not Path(binary).is_file():
        return ""
    proc = subprocess.run(
        [binary, "auth", "print-access-token", "--account=team5pmdocintel@gmail.com"],
        capture_output=True,
        text=True,
        timeout=40,
    )
    return (proc.stdout or "").strip()


def link_formula(row, item):
    url = (item or {}).get("url") or ""
    if not url:
        return ""
    label = (row.get("original_filename") or "open file").replace('"', "").replace("\n", " ")
    return '=HYPERLINK("%s","%s")' % (url, label)


def ensure_file_links(rows):
    """Publish a viewable Drive copy and remember its link. The MinIO object stays the original."""
    cache = load_link_cache()
    missing = []
    seen = set()
    for row in rows:
        sha = row.get("content_sha256") or ""
        key = row.get("storage_key") or ""
        if not sha or not key or sha in cache or sha in seen:
            continue
        seen.add(sha)
        missing.append(row)
    if not missing:
        return cache
    folder = os.environ.get("DOCINTEL_DRIVE_LINKS_FOLDER", "")
    token = user_access_token()
    if not folder or not token:
        print("file links: the Google account is not ready to publish a copy")
        return cache
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload

    drive = build("drive", "v3", credentials=Credentials(token=token), cache_discovery=False)
    for row in missing:
        sha = row["content_sha256"]
        try:
            data = original_bytes(row["storage_key"])
            name = (row.get("original_filename") or "file").replace("/", "-").replace('"', "")
            media = MediaIoBaseUpload(io.BytesIO(data), mimetype=row.get("mime_type") or "application/octet-stream")
            created = drive.files().create(
                body={"name": "%s-%s" % (sha[:8], name), "parents": [folder]},
                media_body=media,
                fields="id,webViewLink",
            ).execute()
            drive.permissions().create(
                fileId=created["id"],
                body={"type": "anyone", "role": "reader"},
            ).execute()
        except Exception:
            print("file links: could not publish %s" % (row.get("document_id") or sha[:8]))
            continue
        url = created.get("webViewLink") or ("https://drive.google.com/file/d/%s/view" % created["id"])
        cache[sha] = {"id": created["id"], "url": url}
        save_link_cache(cache)
    return cache


def write_file_links(service, sheet_id, rows, links):
    letter = column_letter(COLUMNS.index("file_link"))
    for name in TABS:
        formulas = []
        for row in rows:
            if tab_of(row) != name:
                continue
            formulas.append([link_formula(row, links.get(row.get("content_sha256") or ""))])
        if not formulas:
            continue
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range="%s!%s2" % (name, letter),
            valueInputOption="USER_ENTERED",
            body={"values": formulas},
        ).execute()


def credential_path():
    configured = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "")
    if configured:
        return Path(configured)
    return ROOT / "deploy" / "google-service-account.json"


def sheet_url(sheet_id):
    if not sheet_id:
        return ""
    return "https://docs.google.com/spreadsheets/d/%s" % sheet_id


def load_deploy_env():
    path = ROOT / "deploy" / ".env"
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def push_sheet(rows):
    load_deploy_env()
    path = credential_path()
    sheet_id = os.environ.get("DOCINTEL_SHEET_ID", "")
    if not path.is_file():
        return {"connected": False, "url": sheet_url(sheet_id)}
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(str(path), scopes=scopes)
    service = build("sheets", "v4", credentials=creds, cache_discovery=False)
    if not sheet_id:
        created = service.spreadsheets().create(body={
            "properties": {"title": "DocIntel records"},
            "sheets": [{"properties": {"title": name}} for name in TABS],
        }).execute()
        sheet_id = created["spreadsheetId"]
        os.environ["DOCINTEL_SHEET_ID"] = sheet_id
        remember_sheet_id(sheet_id)
        share_with = os.environ.get("DOCINTEL_SHEET_SHARE", "")
        if share_with:
            drive = build("drive", "v3", credentials=Credentials.from_service_account_file(
                str(path), scopes=["https://www.googleapis.com/auth/drive"]
            ), cache_discovery=False)
            drive.permissions().create(
                fileId=sheet_id,
                body={"type": "user", "role": "writer", "emailAddress": share_with},
                sendNotificationEmail=False,
            ).execute()
    existing = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
    titles = {item["properties"]["title"] for item in existing.get("sheets") or []}
    requests = [{"addSheet": {"properties": {"title": name}}} for name in TABS if name not in titles]
    if requests:
        service.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={"requests": requests}).execute()
    links = ensure_file_links(rows)
    data = []
    for name in TABS:
        data.append({"range": "%s!A1" % name, "values": table_for(rows, name)})
    service.spreadsheets().values().batchClear(
        spreadsheetId=sheet_id,
        body={"ranges": ["%s!A:AZ" % name for name in TABS]},
    ).execute()
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=sheet_id,
        body={"valueInputOption": "RAW", "data": data},
    ).execute()
    write_file_links(service, sheet_id, rows, links)
    return {"connected": True, "url": sheet_url(sheet_id)}


def remember_sheet_id(sheet_id):
    path = ROOT / "deploy" / ".env"
    if not path.exists():
        return
    lines = path.read_text().splitlines()
    found = False
    out = []
    for line in lines:
        if line.startswith("DOCINTEL_SHEET_ID="):
            out.append("DOCINTEL_SHEET_ID=%s" % sheet_id)
            found = True
        else:
            out.append(line)
    if not found:
        out.append("DOCINTEL_SHEET_ID=%s" % sheet_id)
    path.write_text("\n".join(out) + "\n")
