#!/usr/bin/env python3
"""Mailbox door. An attachment uses the same intake, and the sender is told the result."""

import email
import imaplib
import os
import smtplib
import threading
import time
from email.header import decode_header
from email.message import EmailMessage
from email.utils import parseaddr

from slack_door import desk_json, encode_form, load_env, parse_instruction

ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]


def header_text(value):
    parts = []
    for bit, encoding in decode_header(value or ""):
        if isinstance(bit, bytes):
            parts.append(bit.decode(encoding or "utf-8", "replace"))
        else:
            parts.append(bit)
    return "".join(parts)


def person_for(address):
    from server import STAFF
    want = (address or "").lower()
    for person in STAFF.values():
        if (person.get("email") or "").lower() == want:
            return person
    return None


def inbox_person():
    from server import STAFF
    mailbox = (os.environ.get("DOCINTEL_MAIL_USER") or "").lower()
    for person in STAFF.values():
        if mailbox and (person.get("email") or "").lower() == mailbox:
            return person
    return STAFF.get(os.environ.get("DOCINTEL_DRIVE_AS") or "andre")


READABLE = (
    "application/pdf",
    "image/png",
    "image/jpeg",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
)


def automated_sender(address):
    low = (address or "").lower()
    local = low.split("@", 1)[0]
    if local.startswith("no-reply") or local.startswith("noreply"):
        return True
    return low.endswith("@google.com") or low.endswith("@accounts.google.com") or low.endswith("@googlecloud.com")


def send_reply(to_address, subject, message_id, body):
    user = os.environ.get("DOCINTEL_MAIL_USER", "")
    password = os.environ.get("DOCINTEL_MAIL_PASSWORD", "")
    if not to_address or not user or not password:
        raise RuntimeError("The mailbox cannot reply because the sender or the account is missing.")
    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = to_address
    sub = subject or "your file"
    msg["Subject"] = sub if sub.lower().startswith("re:") else "Re: " + sub
    if message_id:
        msg["In-Reply-To"] = message_id
        msg["References"] = message_id
    msg.set_content(body)
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(user, password)
        smtp.send_message(msg)


def follow_and_reply(person_id, document_id, filename, to_address, subject, message_id):
    from slack_door import find_row
    deadline = time.time() + 180
    while time.time() < deadline:
        try:
            code, book = desk_json("GET", "/records?as=%s" % person_id, timeout=30)
        except RuntimeError:
            time.sleep(3)
            continue
        row = find_row(book, document_id) if code == 200 else None
        if row and row.get("status") not in ("received", "processing"):
            status = row.get("status") or "unknown"
            note = row.get("validation_notes") or row.get("page_notes") or ""
            if status == "accepted":
                lead = "The read finished and the record was written."
            else:
                lead = "This did not finish as an approved record."
            text = "%s\n%s (%s) is %s." % (lead, filename, document_id, status)
            if note:
                text += "\n" + note
            try:
                send_reply(to_address, subject, message_id, text)
            except Exception as exc:
                print("mail reply failed: %s" % type(exc).__name__)
            return
        time.sleep(3)
    try:
        send_reply(
            to_address,
            subject,
            message_id,
            "I still do not have a result for %s (%s). It has not succeeded." % (filename, document_id),
        )
    except Exception as exc:
        print("mail reply failed: %s" % type(exc).__name__)


def outcome_for(person, stated, client, name, mime, payload):
    readable = mime in READABLE or name.lower().endswith((".doc", ".docx"))
    if not readable:
        return "I can read a PDF, a Word document, a PNG, or a JPEG. %s is none of those, so I did not store it." % name, ""
    try:
        form, content_type = encode_form(person["id"], stated, client, name, payload, mime)
        code, reply = desk_json("POST", "/submit", form, content_type, timeout=60)
    except RuntimeError as exc:
        return "%s was not stored. %s" % (name, exc), ""
    message = (reply.get("message") if isinstance(reply, dict) else "") or "The record book did not answer, so this has not succeeded."
    document_id = ""
    if code == 200 and isinstance(reply, dict) and reply.get("status") == "received":
        document_id = reply.get("document_id") or ""
    elif code != 200:
        message = "%s was not stored. %s" % (name, message)
    return message, document_id


def poll():
    host = os.environ.get("DOCINTEL_MAIL_HOST", "")
    user = os.environ.get("DOCINTEL_MAIL_USER", "")
    password = os.environ.get("DOCINTEL_MAIL_PASSWORD", "")
    if not host or not user or not password:
        return
    mailbox = imaplib.IMAP4_SSL(host)
    try:
        mailbox.login(user, password)
        mailbox.select("INBOX")
        status, data = mailbox.search(None, "UNSEEN")
        if status != "OK":
            return
        for number in (data[0] or b"").split():
            status, fetched = mailbox.fetch(number, "(RFC822)")
            if status != "OK" or not fetched or not fetched[0]:
                continue
            incoming = email.message_from_bytes(fetched[0][1])
            _, address = parseaddr(incoming.get("From") or "")
            person = person_for(address) or inbox_person()
            subject = header_text(incoming.get("Subject"))
            message_id = incoming.get("Message-ID") or ""
            body_text = ""
            attachments = []
            for part in incoming.walk():
                if part.get_content_maintype() == "multipart":
                    continue
                name = part.get_filename()
                payload = part.get_payload(decode=True) or b""
                if name:
                    attachments.append((header_text(name), part.get_content_type(), payload))
                elif part.get_content_type() == "text/plain":
                    body_text += payload.decode("utf-8", "replace")
            if not person:
                mailbox.store(number, "+FLAGS", "\\Seen")
                continue
            stated, client = parse_instruction(subject + "\n" + body_text)
            if not stated:
                stated = "other"
            if client is None:
                client = ""
            lines = []
            if not attachments:
                lines.append("No file was attached, so nothing was stored.")
            for name, mime, payload in attachments:
                text, document_id = outcome_for(person, stated, client, name, mime, payload)
                lines.append(text)
                if document_id and not automated_sender(address):
                    threading.Thread(
                        target=follow_and_reply,
                        args=(person["id"], document_id, name, address, subject, message_id),
                        daemon=True,
                    ).start()
            if lines and not automated_sender(address):
                try:
                    send_reply(address, subject, message_id, "\n\n".join(lines))
                except Exception as exc:
                    print("mail reply failed: %s" % type(exc).__name__)
                    continue
            mailbox.store(number, "+FLAGS", "\\Seen")
    finally:
        try:
            mailbox.logout()
        except Exception:
            pass


def main():
    load_env(ROOT / "04-run" / ".env")
    load_env(ROOT / ".env")
    while True:
        try:
            poll()
        except Exception as exc:
            print("mail door: %s" % exc)
        time.sleep(60)


if __name__ == "__main__":
    main()
