# Document intelligence

This prototype validates the interaction and safety policy; production moves persistence, identity, storage, and job control into managed durable services.

## What is running

The durable core is running on this Mac. Postgres is the ledger, MinIO holds the originals, and n8n in queue mode accepts a file before the model runs.

- Postgres (`docintel-postgres` on `127.0.0.1:5436`) stores the ledger in the `docintel` database. A non-empty content hash is unique. `confirm_replacement` marks the old row superseded and the new row accepted in one transaction. If either row is in the wrong state, both updates roll back.
- MinIO (`127.0.0.1:9002`) keeps originals in the private bucket `docintel-originals`. There is no public read policy. The desk checks the ledger row, then streams the object.
- Redis (`127.0.0.1:6381`) is the queue. Intake writes the object and the `received` row, enqueues the read, and replies before the model call. The worker runs extraction and validation.
- Two uploads of the same bytes take a lock on that hash inside `intake_document`. The second waits until the first commits, then is told the existing document id. It does not insert a second row and it does not start a second read.
- An archive is a separate queue (`backfill_items`). It is admitted in small batches only while no live file is `received` or `processing`. A hash already on the book is skipped. A run of failed reads, or a held majority in the last archive batch, pauses it. The door stays idle until `DOCINTEL_BACKFILL_DIR` is set. It does not run 10,000 model calls on its own.

The n8n main process and the worker are host processes started with `deploy/n8n.sh`. They are not a second container. The Docker VM is small and already runs another n8n, so a second n8n container is killed for memory. That other instance is left alone.

`?as=andre` is still the staff-map door on the desk. It is not SSO. Google SSO is specified below and is not running.

The desk shows the ledger columns on every row. One document is one row. A superuser sees every column, including currency and total. A person outside finance does not receive those two fields. The Google Sheet is the same columns, split into Current, Held, Reading, and History, so a revised invoice is not two live rows. It is a copy written after the row exists. It is not the book. Each row has a file link that opens a viewable copy in Drive. The original stays in the private bucket.

A file is scanned with ClamAV before the desk opens it, before it is stored, and again before a worker reads the pages. A flagged file is refused. If the scanner is missing or does not finish, the file is not opened.

The worker reads a PDF after intake has already replied. It calls the desk at `/extract`. Each page with text is one model call. A page with no native text is rendered and read with Apple Vision on this Mac. If that page is still empty, the document is held and the page is named. That page is not sent to the vision model. Agreeing values are kept with the page they came from and a short excerpt of that page. Two different values for the same field are left blank.

Each model call is written to `model_usage`. The desk status line shows today's spend in Johannesburg time and how many pages in the ledger could not be read.

Slack, a Google Drive folder, and a mailbox can all submit through the same intake. The Drive folder and the mailbox stay up and wait when those accounts are not connected. They do not submit until `DOCINTEL_DRIVE_FOLDER` or `DOCINTEL_MAIL_HOST` is set.

The desk, n8n, the n8n worker, the Slack listener, the Drive door, and the mailbox door are user LaunchAgents. A reboot starts them again. Postgres, Redis, and MinIO are still Docker containers and come back only when that runtime is up.

A held document can be corrected from the desk. Each changed value needs the page it came from. Saving the review checks the fields again and does not read the file or call the model. It becomes current only when the required fields are valid and every named blank page has been acknowledged. If it matches one current invoice or contract, it waits for yes or no. Yes still goes through `confirm_replacement`.

The desk shows three alerts to the superuser: a file that has been waiting to be read, a read that failed before a result came back, and a held file that has been waiting on a person. An open alert is one row per kind. It closes when the condition clears.

The revision 5 workflows on the existing n8n stay the safety proof: Data Tables, a local `storage/` directory, and a compensate-and-restore path. That proof is not this deploy.

## What the proof already shows

A wrong contract value written as if it were final is the failure. A run that stops and says why is a success.

- The same bytes are not a new version. The person is told which document it already is. No second row is written. No model call is spent.
- Different bytes with the same invoice or contract identity are not applied on their own. The person sees what differs and says yes or no. Yes writes a new current row and keeps the old one in history. No leaves the new file held. Silence is not a yes.
- A page with no readable text is named and the document is held. The model does not invent the missing page.
- Money, parties, and dates that are missing, conflicting, or not a real date are left blank and the document is held.
- The original file is kept only after the record exists, and a failed save is said out loud.
- A replacement that fails after the old row was moved says so and puts that row back. Nothing is deleted.
- Confirming a write is allowed only after the write. The thread does not claim a row that was not written.

Those rules stay. The machinery under them does not.

## Where the proof stops

The ceiling below is the revision 5 proof on the existing n8n. The durable core in “What is running” is the slice that has moved off that ceiling.

- n8n Data Tables are the system of record.
- Submission reads all records so it can refuse an identical file before a model call.
- A browser query parameter represents identity. `?as=andre` selects a hard-coded superuser.
- A local Python process stores originals under `storage/`.
- One workflow execution waits for one full document and one model response.
- That older proof has no OCR, no worker separation, no durable queue, and no transactional database boundary. Those pieces are in the running section above, not in revision 5.

Header auth on the webhooks protects the hop from the desk to n8n. It does not identify the person. The restore path after a failed replacement is compensation across separate writes. It is not a transaction.

## Production

```text
Authenticated intake
        ↓
Object storage (S3/MinIO) + SHA-256
        ↓
Postgres document ledger / idempotency key
        ↓
n8n queue-mode orchestration
        ↓
OCR / native extraction workers
        ↓
Page-chunk extraction + validation
        ↓
Postgres review queue
        ↓
Approved structured record → Sheets / downstream systems
```

Slack stays a door, because that is where a person already drops a file. Google Workspace is the identity. The Slack user and the SSO user are the same row in Postgres. The desk stops accepting `?as=`. Google Sheets stays the view the brief asked teams to read. It is filled from an approved Postgres row. It is not the ledger.

The brief’s file formats are a native-text PDF, a scanned image, and a Word document. A Word file is read as a Word file. The words come out of the document. An embedded picture uses the same OCR as a scanned page. The file is not converted into a PDF first, and it is not refused. A value is cited from the section it was found in. The demo inbox at team5pmdocintel@gmail.com accepts any sender so the path can be tested. In production that inbox accepts a file only from a company email address. Any other domain is refused and not stored.

n8n decides the next step and calls the workers. It does not own the rows, the files, or the lock around a version change.

## What changes, and why

1. **Postgres replaces Data Tables.** Documents, versions, extraction jobs, review tasks, and audit events live in tables with a unique constraint on the content hash. Data Tables made the proof visible inside n8n. They cannot be the place a company asks “which invoice is current” while two uploads arrive together. The unique hash is what makes the identical-file rule true under concurrency, not only in a careful demo.

2. **Originals go to a private bucket.** S3 or MinIO, encrypted, with signed downloads, a retention policy, backups, and a malware scan before a worker opens the file. `storage/` on the desk machine proves we keep the original and only serve it to someone who can see the row. One disk is not retention, and a path on that disk is not an access boundary.

3. **n8n runs in queue mode.** Redis, and workers that are not the webhook process. Intake writes the object and the ledger row, then replies that the file was received and is not approved yet. A 100-page contract does not hold the HTTP call open. The same idempotency key means a retried webhook does not start a second job.

4. **Google Workspace SSO is the identity provider.** Users, teams, and roles are rows in Postgres, maintained by a superuser. Department comes from that map. Legal does not receive payment amounts because the query does not return them, not because the page hides a column. One or two superusers see the whole set. Nobody gets a delete.

5. **Native text first, OCR only for the pages that have none.** A page that already has a text layer is not sent through OCR. A scanned page is. Empty OCR is a held page, named in plain language, not a blank field treated as zero. That page is not sent to the vision model. The model sees page chunks, not the whole file in one request.

6. **Every material field carries its evidence.** Extracted value, source page, source excerpt, validation state, and the history of any reviewer override. A total without a page is not a total. Conflicting totals are both kept. The code does not pick one.

7. **Review is a queue a person can correct.** The proof can hold a document or replace a whole record. Production review lets a reviewer fix a field, see the page it came from, and approve that field. Approval re-runs validation. It does not re-run OCR. The document becomes current only when the required fields are valid.

8. **Operations are visible without opening an execution log.** Queue depth, age of the oldest job, error count, model cost, OCR failure rate, and how long a held item has waited. An alert fires when those breach a line. A healthy morning is a quiet one. Staff do not sit in n8n to learn that intake is stuck.

9. **A version change is one database transaction.** Superseding the old row and accepting the new row commit together, or neither does. n8n asks Postgres to do that. The proof’s compensate-and-restore path showed the failure is detectable. It is the wrong place for the guarantee. The database is the source of transactional truth.

10. **The fixtures become tests.** The three files already in this repo — clean invoice, revised invoice, contract with a blank page — plus a scanned PDF, a malformed file, two identical uploads at once, a 429, a dead model API, and a 100-page document. The identical pair must produce one current row. The blank page must be held. The 100-page run must finish as jobs, not as one HTTP request.

## What does not change

The person still hears the outcome in the same thread they used to send the file. Received is not approved. An identical file is still explained and not rewritten. A changed contract still waits for a yes. An unreadable page is still named. History is still kept. The sheet downstream teams read still shows only the current approved row.
