# DocIntel

This prototype validates the interaction and safety policy; production moves persistence, identity, storage, and job control into managed durable services.

A file comes in, is scanned, and is stored. The person is told it was received before a model runs. The ledger then accepts it, holds it, or waits for a yes. An identical file is named and not written again. A blank page is held and named. Nothing is deleted.

The folders are numbered in the order to read them.

## 01 — Read this

| File | What it is |
|---|---|
| [01-docs/assessment.pdf](01-docs/assessment.pdf) | The written submission |
| [01-docs/design.md](01-docs/design.md) | What is running, and what production still changes |

## 02 — The program

| Path | What it is |
|---|---|
| [02-src/desk](02-src/desk) | The page, the checks, and the sheet copy |
| [02-src/doors](02-src/doors) | Slack, Drive, the mailbox, and the archive queue |
| [02-src/workflows/current](02-src/workflows/current) | The running n8n book, numbered in run order: intake, process, confirm, records, thread |
| [02-src/workflows/proof](02-src/workflows/proof) | The earlier safety proof. It is not this deploy |

## 03 — Files you can drop

[03-samples](03-samples) holds a clean invoice, the same invoice revised, and a contract whose second page is blank.

## 04 — How it runs

[04-run/ledger.sql](04-run/ledger.sql) is the book: one row per document, and the functions that write it. Compose, the LaunchAgents, and the start scripts sit in the same folder.

```bash
docker compose -f 04-run/docker-compose.yml --env-file 04-run/.env up -d
```

The desk, n8n, the worker, Slack, Drive, and the mailbox start again after a reboot. Postgres, Redis, and MinIO come back when Docker does.

These links are staff-map seats, not a login. Each one opens that seat’s view.

| Seat | Link | What it shows |
|---|---|---|
| Superuser | https://docintel.ziton.tech/superuser | Every department, including amounts |
| Finance | https://docintel.ziton.tech/finance | Finance rows, including amounts |
| Projects | https://docintel.ziton.tech/projects | Projects rows. Amounts are left off |
| Accounts | https://docintel.ziton.tech/accounts | Accounts rows. Amounts are left off |

On this machine the same views are http://127.0.0.1:8787/superuser, /finance, /projects, and /accounts.

Copy `.env.example` to `.env` and `04-run/.env.example` to `04-run/.env`. The webhook header is `X-Docintel-Key`. Its value is `DOCINTEL_WEBHOOK_SECRET`. Keys, tokens, and the service-account file stay in those env files. They are not in this repository.

## What a file goes through

1. A person drops it on the desk, in the Slack DM, in the Drive folder, or as an attachment to the mailbox.
2. ClamAV scans it before it is opened. A flagged file is refused. If the scanner does not finish, the file is not opened.
3. The same bytes as a file already on the book are named. No second row is written, and no model call is spent. Two uploads of those bytes at once take one lock. The second waits, then is told the existing id.
4. A new file is stored in the private bucket `docintel-originals`, a `received` row is inserted, and the read is queued. The reply says the file is not approved yet.
5. A file of ten pages or fewer sends one model call per page that has text. A longer file is grouped about ten pages at a time, one call at a time, with a second and a half between calls. A page with no text is read with Apple Vision. An empty page is held and named, and it is not sent on. A Word file is read as a Word file. A value keeps the page or section it came from, and a short excerpt. Two groups that disagree leave the field blank.
6. A held row can be corrected on the desk. A changed invoice or contract waits for yes or no. Yes supersedes the old row and accepts the new one in one transaction.

The Google Sheet is a copy of those columns, split into Current, Held, Reading, and History. It is not the book. Each row links to a viewable copy of the file.
