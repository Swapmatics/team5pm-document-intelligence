# DocIntel

This prototype validates the interaction and safety policy; production moves persistence, identity, storage, and job control into managed durable services.

A file comes in, is scanned, and is stored. The person is told it was received before a model runs. The ledger then accepts it, holds it, or waits for a yes. An identical file is named and not written again. A blank page is held and named. Nothing is deleted.

## Where to look

| Path | What it is |
|---|---|
| [docs/assessment.pdf](docs/assessment.pdf) | The written submission |
| [docs/design.md](docs/design.md) | What is running, and what production still changes |
| [web/](web/) | The desk, the doors, and the checks |
| [workflows/](workflows/) | The n8n workflow source |
| [deploy/ledger.sql](deploy/ledger.sql) | The book: one row per document, and the functions that write it |
| [fixtures/](fixtures/) | The invoice, the revision, and the contract with a blank page |

`workflows/intake.js`, `process.js`, and the `ledger-*.js` files are the running book. `workflows/submit.js`, `confirm.js`, `records.js`, and `thread.js` are the earlier safety proof. They are not the deploy.

## What a file goes through

1. A person drops it on the desk, in the Slack DM, in the Drive folder, or as an attachment to the mailbox.
2. ClamAV scans it before it is opened. A flagged file is refused. If the scanner does not finish, the file is not opened.
3. The same bytes as a file already on the book are named. No second row is written, and no model call is spent. Two uploads of those bytes at once take one lock. The second waits, then is told the existing id.
4. A new file is stored in the private bucket `docintel-originals`, a `received` row is inserted, and the read is queued. The reply says the file is not approved yet.
5. A page with text is one model call. A page with no text is read with Apple Vision. An empty page is held and named, and it is not sent on. A Word file is read as a Word file. A value keeps the page or section it came from, and a short excerpt.
6. A held row can be corrected on the desk. A changed invoice or contract waits for yes or no. Yes supersedes the old row and accepts the new one in one transaction.

The Google Sheet is a copy of those columns, split into Current, Held, Reading, and History. It is not the book. Each row links to a viewable copy of the file.

An archive folder, set with `DOCINTEL_BACKFILL_DIR`, is a separate queue. It is admitted in small batches only while no live file is still being read.

## Run it

Postgres, Redis, and MinIO:

```bash
docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d
```

The desk, n8n, the worker, Slack, Drive, and the mailbox are LaunchAgents under `deploy/launchd/`. They start again after a reboot. The three data services come back when Docker does.

Open http://127.0.0.1:8787/?as=andre

That link is a staff-map seat, not a login. Andre is the superuser. A person outside finance does not receive currency or totals from the desk.

Copy `.env.example` to `.env` and `deploy/.env.example` to `deploy/.env`. The webhook header is `X-Docintel-Key`. Its value is `DOCINTEL_WEBHOOK_SECRET`. Keys, tokens, and the service-account file stay in those env files. They are not in this repository.
