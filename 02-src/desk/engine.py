"""Page chunks, OCR, review checks, and the alert lines. The desk calls this. n8n does not guess."""

import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
OCR_BIN = ROOT / "04-run" / "ocr-vision"
PAGE_MARK = re.compile(r"^---\s*PAGE\s+\d+\s*---\s*$", re.I)
MODEL = "google/gemini-2.5-flash"
INPUT_USD_PER_MILLION = 0.30
OUTPUT_USD_PER_MILLION = 2.50
PROMPT = (
    "You extract fields from one page. Return one JSON object and nothing else. "
    "Do not invent a value. If a field is not on this page, use an empty string. "
    "Do not choose between two different totals, dates, or party names. Put each conflict in conflicts. "
    "type_guess must be invoice, contract, brief, or other. "
    "JSON keys: title, parties, counterparty, document_date, effective_date, expiry_date, currency, "
    "total_amount, reference_number, why_it_exists, type_guess, conflicts. "
    "Dates as YYYY-MM-DD when the page states one. Amounts as digits and a decimal point, no currency symbol. "
    "On an invoice, counterparty is the supplier, not the customer."
)
FIELDS = (
    "title", "parties", "counterparty", "document_date", "effective_date", "expiry_date",
    "currency", "total_amount", "reference_number", "why_it_exists", "type_guess",
)
REQUIRED = {
    "invoice": ("counterparty", "reference_number", "currency", "total_amount", "document_date"),
    "contract": ("parties", "effective_date"),
    "brief": ("title", "why_it_exists"),
    "other": ("title",),
}
QUEUE_AGE_SECONDS = 120
HELD_AGE_SECONDS = 3600
MODEL_FAILURE = "The extraction did not return a usable result"


def env_file(path):
    values = {}
    if not path.exists():
        return values
    for line in path.read_text().splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def openrouter_key():
    return env_file(ROOT / "04-run" / ".env").get("OPENROUTER_API_KEY", "")


def usable(text):
    kept = []
    for line in (text or "").splitlines():
        if PAGE_MARK.match(line.strip()):
            continue
        kept.append(line)
    return re.sub(r"\s+", "", "\n".join(kept))


def money(value):
    text = str(value or "").strip()
    if not text or "-" in text:
        return ""
    out = []
    seen_dot = False
    for char in text:
        if char.isdigit():
            out.append(char)
        elif char == "." and not seen_dot:
            seen_dot = True
            out.append(char)
    raw = "".join(out)
    if not raw or raw == ".":
        return ""
    try:
        return f"{float(raw):.2f}"
    except ValueError:
        return ""


def date_field(value):
    text = str(value or "").strip()
    if len(text) != 10 or text[4] != "-" or text[7] != "-":
        return ""
    try:
        year, month, day = int(text[0:4]), int(text[5:7]), int(text[8:10])
        parsed = datetime(year, month, day)
    except ValueError:
        return ""
    if (parsed.year, parsed.month, parsed.day) != (year, month, day):
        return ""
    return text


def clean(value):
    if isinstance(value, list):
        return ", ".join(str(bit).strip() for bit in value if str(bit).strip())
    return str(value or "").strip()


def normalize(key, value):
    if key == "total_amount":
        return money(value)
    if key in ("document_date", "effective_date", "expiry_date"):
        return date_field(value)
    if key == "currency":
        return clean(value).upper()
    if key == "type_guess":
        return clean(value).lower()
    return clean(value)


def ocr_image(path):
    if not OCR_BIN.is_file():
        return ""
    try:
        done = subprocess.run([str(OCR_BIN), str(path)], capture_output=True, text=True, timeout=40)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if done.returncode != 0:
        return ""
    return (done.stdout or "").strip()


def read_pages(data):
    import fitz
    document = fitz.open(stream=data, filetype="pdf")
    pages = []
    try:
        for index, page in enumerate(document, 1):
            native = page.get_text("text") or ""
            source = "native"
            text = native
            if len(usable(native)) < 20:
                source = "ocr"
                with tempfile.NamedTemporaryFile(suffix=".png", delete=True) as handle:
                    pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    pixmap.save(handle.name)
                    text = ocr_image(handle.name)
                if len(usable(text)) < 20:
                    source = "empty"
                    text = ""
            pages.append({"page": index, "source": source, "text": text})
    finally:
        document.close()
    return pages


def marked(pages):
    chunks = []
    for page in pages:
        label = "SECTION" if page.get("place") == "section" else "PAGE"
        chunks.append("--- %s %d ---\n%s" % (label, page["page"], page["text"] or ""))
    return "\n".join(chunks)


def _docx_paragraphs(data):
    import io
    import zipfile
    from xml.etree import ElementTree

    package = zipfile.ZipFile(io.BytesIO(data))
    names = set(package.namelist())
    if "word/document.xml" not in names:
        raise ValueError("not a word document")
    root = ElementTree.fromstring(package.read("word/document.xml"))
    rels = {}
    if "word/_rels/document.xml.rels" in names:
        rel_root = ElementTree.fromstring(package.read("word/_rels/document.xml.rels"))
        for rel in rel_root:
            rel_id = rel.attrib.get("Id")
            target = rel.attrib.get("Target") or ""
            if rel_id and target:
                rels[rel_id] = "word/" + target.lstrip("/")
    sections = []
    bucket = []

    def flush():
        text = "\n".join(bit for bit in bucket if bit).strip()
        if text or sections:
            sections.append({"page": len(sections) + 1, "place": "section", "source": "native", "text": text})
        bucket.clear()

    for paragraph in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
        words = []
        for node in paragraph.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"):
            if node.text:
                words.append(node.text)
        line = "".join(words).strip()
        style = ""
        style_node = paragraph.find(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pStyle")
        if style_node is not None:
            style = style_node.attrib.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val") or ""
        if style.lower().startswith("heading") and bucket:
            flush()
        if line:
            bucket.append(line)
        for blip in paragraph.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}blip"):
            rel_id = blip.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed")
            target = rels.get(rel_id or "")
            if not target or target not in names:
                continue
            blob = package.read(target)
            if len(usable(line)) >= 20:
                continue
            with tempfile.NamedTemporaryFile(suffix=".png", delete=True) as handle:
                handle.write(blob)
                handle.flush()
                seen = ocr_image(handle.name)
            if len(usable(seen)) >= 20:
                bucket.append(seen)
            elif not line:
                sections.append({"page": len(sections) + 1, "place": "section", "source": "empty", "text": ""})
    if bucket:
        text = "\n".join(bucket).strip()
        source = "native" if len(usable(text)) >= 20 else "empty"
        sections.append({"page": len(sections) + 1, "place": "section", "source": source, "text": text if source == "native" else ""})
    elif not sections:
        sections.append({"page": 1, "place": "section", "source": "empty", "text": ""})
    return sections


def _doc_sections(data):
    handle = tempfile.NamedTemporaryFile(suffix=".doc", delete=False)
    path = handle.name
    try:
        handle.write(data)
        handle.close()
        done = subprocess.run(["textutil", "-convert", "txt", "-stdout", path], capture_output=True, text=True, timeout=40)
    except (OSError, subprocess.TimeoutExpired):
        return [{"page": 1, "place": "section", "source": "empty", "text": ""}]
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
    text = (done.stdout or "").strip() if done.returncode == 0 else ""
    if len(usable(text)) < 20:
        return [{"page": 1, "place": "section", "source": "empty", "text": ""}]
    return [{"page": 1, "place": "section", "source": "native", "text": text}]


def is_word(data):
    if data.startswith(b"PK") and b"word/document.xml" in data[:400000]:
        return True
    return data.startswith(b"\xd0\xcf\x11\xe0") and b"WordDocument" in data[:800000]


def read_word(data):
    if data.startswith(b"PK"):
        return _docx_paragraphs(data)
    return _doc_sections(data)


def excerpt_for(text, value):
    raw = text or ""
    needle = str(value or "").strip()
    if not needle or not raw:
        return ""
    at = raw.lower().find(needle.lower())
    if at < 0:
        snippet = re.sub(r"\s+", " ", raw).strip()
        return snippet[:140]
    start = max(0, at - 50)
    end = min(len(raw), at + len(needle) + 50)
    snippet = re.sub(r"\s+", " ", raw[start:end]).strip()
    if start:
        snippet = "…" + snippet
    if end < len(raw):
        snippet = snippet + "…"
    return snippet[:180]


def usage_cost(usage):
    stated = usage.get("cost_usd")
    if stated not in (None, ""):
        try:
            return round(float(stated), 6)
        except (TypeError, ValueError):
            pass
    prompt = int(usage.get("prompt_tokens") or 0)
    completion = int(usage.get("completion_tokens") or 0)
    cost = (prompt * INPUT_USD_PER_MILLION + completion * OUTPUT_USD_PER_MILLION) / 1000000
    return round(cost, 6)


def model_page(page_number, text, stated_type, place="page"):
    key = openrouter_key()
    if not key:
        raise RuntimeError("The model key is missing, so this page was not read.")
    body = {
        "model": MODEL,
        "temperature": 0,
        "messages": [{
            "role": "user",
            "content": PROMPT + "\nThis is %s %d only.\nStated type: %s\n\n%s" % (place, page_number, stated_type, text),
        }],
    }
    request = Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode())
    content = (((payload.get("choices") or [{}])[0].get("message") or {}).get("content") or "")
    usage = payload.get("usage") or {}
    return parse_model(content), {
        "prompt_tokens": int(usage.get("prompt_tokens") or 0),
        "completion_tokens": int(usage.get("completion_tokens") or 0),
        "cost_usd": usage.get("cost"),
    }


def parse_model(raw):
    text = str(raw or "").strip()
    if text.startswith("```"):
        text = text[3:]
        if text[:4].lower() == "json":
            text = text[4:]
        end = text.rfind("```")
        if end != -1:
            text = text[:end]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1:
            return None
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None


def merge_pages(pages, stated_type):
    reports = []
    evidence = []
    found = {key: {} for key in FIELDS}
    conflicts = []
    unreadable = []
    model_error = ""
    spent = []
    page_text = {page["page"]: page["text"] for page in pages}
    for page in pages:
        reports.append({"page": page["page"], "source": page["source"], "chars": len(usable(page["text"]))})
        if page["source"] == "empty":
            unreadable.append(page["page"])
            continue
        try:
            parsed, usage = model_page(page["page"], page["text"], stated_type, page.get("place") or "page")
            parsed = parsed or {}
            spent.append(usage)
        except Exception as exc:
            model_error = str(exc)
            parsed = {}
        if not parsed and not model_error:
            model_error = "The extraction did not return a usable result, so nothing was filled in."
        for item in parsed.get("conflicts") or []:
            values = [clean(bit) for bit in (item.get("values") or []) if clean(bit)]
            if len(values) > 1:
                conflicts.append({"field": clean(item.get("field") or "value"), "values": values})
        for key in FIELDS:
            value = normalize(key, parsed.get(key))
            if not value:
                continue
            found[key].setdefault(value, []).append(page["page"])
    merged = {}
    for key, values in found.items():
        if not values:
            merged[key] = ""
            continue
        if len(values) == 1:
            value, page_numbers = next(iter(values.items()))
            merged[key] = value
            if key != "type_guess":
                page_number = page_numbers[0]
                evidence.append({
                    "field": key,
                    "value": value,
                    "page": page_number,
                    "source": "read",
                    "excerpt": excerpt_for(page_text.get(page_number) or "", value),
                })
            continue
        merged[key] = ""
        conflicts.append({"field": key, "values": list(values)})
    result = {
        "title": merged["title"],
        "parties": merged["parties"],
        "counterparty": merged["counterparty"],
        "document_date": merged["document_date"],
        "effective_date": merged["effective_date"],
        "expiry_date": merged["expiry_date"],
        "currency": merged["currency"],
        "total_amount": merged["total_amount"],
        "reference_number": merged["reference_number"],
        "why_it_exists": merged["why_it_exists"],
        "type_guess": merged["type_guess"],
        "unreadable_pages": unreadable,
        "conflicts": conflicts,
        "field_evidence": evidence,
    }
    return result, reports, model_error, spent


def extract_word(data, stated_type):
    pages = read_word(data)
    merged, reports, model_error, spent = merge_pages(pages, stated_type)
    text = marked(pages)
    prompt = sum(int(item.get("prompt_tokens") or 0) for item in spent)
    completion = sum(int(item.get("completion_tokens") or 0) for item in spent)
    body = {
        "choices": [{"message": {"content": json.dumps(merged)}}],
        "page_text": text,
        "reported_pages": len(pages),
        "page_reports": reports,
        "unreadable_pages": len([page for page in pages if page["source"] == "empty"]),
        "usage": {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "cost_usd": round(sum(usage_cost(item) for item in spent), 6),
        },
    }
    if model_error:
        body["error"] = {"message": model_error}
    return body


def extract_pdf(data, stated_type):
    pages = read_pages(data)
    merged, reports, model_error, spent = merge_pages(pages, stated_type)
    text = marked(pages)
    content = json.dumps(merged)
    prompt = sum(int(item.get("prompt_tokens") or 0) for item in spent)
    completion = sum(int(item.get("completion_tokens") or 0) for item in spent)
    body = {
        "choices": [{"message": {"content": content}}],
        "page_text": text,
        "reported_pages": len(pages),
        "page_reports": reports,
        "unreadable_pages": len([page for page in pages if page["source"] == "empty"]),
        "usage": {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "cost_usd": round(sum(usage_cost(item) for item in spent), 6),
        },
    }
    if model_error:
        body["error"] = {"message": model_error}
    return body


def review_problems(row, fields, ack_pages):
    stated = clean(row.get("stated_type")).lower()
    merged = {}
    evidence = []
    problems = []
    for key in REQUIRED.get(stated, ()) + ("title", "parties", "counterparty", "expiry_date", "currency", "why_it_exists"):
        incoming = fields.get(key) or {}
        if not isinstance(incoming, dict):
            incoming = {"value": incoming, "page": ""}
        if clean(incoming.get("value")):
            value = normalize(key, incoming.get("value"))
            page = incoming.get("page")
            try:
                page_number = int(page)
            except (TypeError, ValueError):
                page_number = 0
            if not value:
                problems.append("The " + key.replace("_", " ") + " is not a value I can keep.")
                continue
            if page_number < 1:
                problems.append("The " + key.replace("_", " ") + " needs the page it came from.")
                continue
            merged[key] = value
            prior = {}
            try:
                stored = json.loads(row.get("field_evidence") or "[]")
            except json.JSONDecodeError:
                stored = []
            for item in stored if isinstance(stored, list) else []:
                if isinstance(item, dict) and item.get("field") == key and item.get("value") == value:
                    prior = item
                    break
            evidence.append({
                "field": key,
                "value": value,
                "page": page_number,
                "source": "review",
                "excerpt": clean(incoming.get("excerpt")) or prior.get("excerpt") or "",
            })
        else:
            merged[key] = normalize(key, row.get(key))
    for key in REQUIRED.get(stated, ()):
        if not merged.get(key):
            problems.append("The " + stated + " is missing " + key.replace("_", " ") + ".")
    for label in re.findall(r"more than one ([^:]+):", row.get("validation_notes") or ""):
        key = label.strip().replace(" ", "_")
        if key not in FIELDS:
            continue
        incoming = fields.get(key) or {}
        if not isinstance(incoming, dict) or not clean(incoming.get("value")):
            problems.append("The file gives more than one " + key.replace("_", " ") + ". Send the one to keep, and the page it is on.")
    named = [int(bit) for bit in re.findall(r"Page (\d+)", row.get("page_notes") or "")]
    acked = set()
    for bit in ack_pages or []:
        try:
            acked.add(int(bit))
        except (TypeError, ValueError):
            continue
    for page in named:
        if page not in acked:
            problems.append("Page " + str(page) + " still has no text. Say you looked at that page, or leave this held.")
    return problems, merged, evidence


def parse_time(value):
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def age_seconds(value, now):
    parsed = parse_time(value)
    if not parsed:
        return 0
    return max(0, int((now - parsed).total_seconds()))


def alert_lines(rows, now=None):
    now = now or datetime.now(timezone.utc)
    received = [row for row in rows if row.get("status") == "received"]
    held = [row for row in rows if row.get("status") == "held"]
    oldest_job = max((age_seconds(row.get("submitted_at"), now) for row in received), default=0)
    oldest_held = max((age_seconds(row.get("submitted_at"), now) for row in held), default=0)
    failures = [
        row for row in rows
        if MODEL_FAILURE in (row.get("validation_notes") or "")
    ]
    lines = []
    if len(received) and oldest_job >= QUEUE_AGE_SECONDS:
        lines.append({
            "kind": "queue",
            "body": str(len(received)) + " file" + ("" if len(received) == 1 else "s") + " still waiting to be read. The oldest has waited " + str(oldest_job // 60) + " minutes.",
        })
    if failures:
        lines.append({
            "kind": "model",
            "body": str(len(failures)) + " read" + ("" if len(failures) == 1 else "s") + " failed before a result came back.",
        })
    if oldest_held >= HELD_AGE_SECONDS:
        lines.append({
            "kind": "held",
            "body": "A held file has waited " + str(oldest_held // 3600) + " hours. The oldest held item is still waiting on a person.",
        })
    return {
        "queue_depth": len(received),
        "oldest_job_seconds": oldest_job,
        "model_failures": len(failures),
        "oldest_held_seconds": oldest_held,
        "alerts": lines,
    }
