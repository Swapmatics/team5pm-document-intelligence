#!/usr/bin/env python3
"""Build the synthetic PDFs used to test DocIntel."""

from pathlib import Path

OUT = Path(__file__).resolve().parent


def escape(text):
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def pdf(pages):
    objects = []
    page_ids = []
    font_id = 3
    next_id = 4
    content_ids = []
    for page in pages:
        lines = page.split("\n")
        commands = ["BT", "/F1 11 Tf", "50 780 Td", "14 TL"]
        for i, line in enumerate(lines):
            op = "Tj" if i == 0 else "T*"
            if i == 0:
                commands.append(f"({escape(line)}) Tj")
            else:
                commands.append(f"T* ({escape(line)}) Tj")
        commands.append("ET")
        stream = "\n".join(commands).encode("latin-1", "replace")
        content_ids.append(next_id)
        objects.append((next_id, b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"))
        next_id += 1
    for content_id in content_ids:
        page_id = next_id
        next_id += 1
        page_ids.append(page_id)
        objects.append((page_id, f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {content_id} 0 R /Resources << /Font << /F1 {font_id} 0 R >> >> >>".encode()))
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects.append((1, b"<< /Type /Catalog /Pages 2 0 R >>"))
    objects.append((2, f"<< /Type /Pages /Count {len(page_ids)} /Kids [{kids}] >>".encode()))
    objects.append((3, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"))
    objects.sort(key=lambda item: item[0])
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj_id, body in objects:
        offsets.append(len(out))
        out += f"{obj_id} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects)+1}\n".encode()
    out += b"0000000000 65535 f \n"
    for obj_id, _ in objects:
        out += f"{offsets[obj_id]:010d} 00000 n \n".encode()
    out += f"trailer << /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


invoice = """--- PAGE 1 ---
INVOICE
Title: Tax invoice
Supplier: Northwind Supplies
Client: Cape Harbour Projects
Invoice number: INV-1001
Invoice date: 2026-03-01
Currency: ZAR
Total: 12500.00
This invoice is for timber delivered to the harbour store in February.
"""

invoice_revised = """--- PAGE 1 ---
INVOICE
Title: Tax invoice
Supplier: Northwind Supplies
Client: Cape Harbour Projects
Invoice number: INV-1001
Invoice date: 2026-03-01
Currency: ZAR
Total: 18000.00
This invoice is for timber delivered to the harbour store in February.
The total was revised after a short delivery.
"""

contract = """--- PAGE 1 ---
CONTRACT
Title: Services agreement
Parties: Cape Harbour Projects and Northwind Supplies
Effective date: 2026-04-01
Reference: CTR-55
This agreement exists so Northwind can supply timber to the harbour project.
The commercial total is 12500.00 ZAR.
--- PAGE 3 ---
Exhibit A
Signed by both parties.
This page does not state a new total.
"""

(OUT / "invoice.pdf").write_bytes(pdf([invoice]))
(OUT / "invoice-revised.pdf").write_bytes(pdf([invoice_revised]))
# Three pages: text, blank, text. The blank page is page 2.
blank = " "
(OUT / "contract-missing-page.pdf").write_bytes(pdf([
    contract.split("--- PAGE 3 ---")[0].strip(),
    blank,
    "--- PAGE 3 ---\nExhibit A\nSigned by both parties.\nThis page does not state a new total.\n",
]))


def wrong_words():
    """A scan with no text layer. The total is letters, not an amount."""
    import fitz
    body = "\n".join([
        "INVOICE",
        "Title: Tax invoice",
        "Supplier: Northwind Supplies",
        "Client: Cape Harbour Projects",
        "Invoice number: INV-WRONG",
        "Invoice date: 2026-04-02",
        "Currency: ZAR",
        "Total: 12S00.OO",
        "This invoice is for timber delivered to the harbour shed.",
    ])
    drawn = fitz.open()
    page = drawn.new_page(width=612, height=792)
    page.insert_text((50, 80), body, fontsize=16, fontname="helv")
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    drawn.close()
    image = fitz.open()
    sheet = image.new_page(width=612, height=792)
    sheet.insert_image(sheet.rect, pixmap=pix)
    image.save(OUT / "invoice-wrong-words.pdf", deflate=True, garbage=4)
    image.close()


wrong_words()
print("wrote", OUT)
