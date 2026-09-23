#!/usr/bin/env python3
"""Build the ledger workflow sources from the proof submit workflow."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / "02-src" / "workflows" / "proof"
CURRENT = ROOT / "02-src" / "workflows" / "current"
SUBMIT = (PROOF / "1-submit.js").read_text()

start = SUBMIT.index("const prepareCode = `")
end = SUBMIT.index("const decideCode = `")
prepare_code = SUBMIT[start:end]

process = SUBMIT
process = process.replace(
    "newCredential('OpenRouter')",
    "newCredential('OpenRouter', 'OPENROUTER_CREDENTIAL_ID')",
)
process = process.replace(
    "const same = rows.find(r => r.content_sha256 === prep.content_sha256);",
    "const same = rows.find(r => r.content_sha256 === prep.content_sha256 && r.document_id !== prep.document_id);",
)
process = process.replace(
    "const documentId = 'DOC-' + built.content_sha256.slice(0, 8) + '-' + Date.now().toString(36);",
    "const documentId = String(built.document_id || '');\n"
    "if (!documentId) throw new Error('Intake did not assign a document id.');",
)

old_load = """const loadRecords = node({
  type: 'n8n-nodes-base.dataTable',
  version: 1.1,
  config: {
    name: 'Load records',
    alwaysOutputData: true,
    parameters: {
      resource: 'row',
      operation: 'get',
      dataTableId: { __rl: true, mode: 'id', value: 'NBLNd99VnodAqWlD', cachedResultName: 'DocIntel Records' },
      matchType: 'allConditions',
      filters: { conditions: [{ keyName: 'document_id', condition: 'isNotEmpty' }] },
      returnAll: true,
    },
    output: [{ json: { document_id: '', content_sha256: '', status: '' } }],
  },
});"""

new_load = """const loadRecords = node({
  type: 'n8n-nodes-base.postgres',
  version: 2.5,
  config: {
    name: 'Load records',
    alwaysOutputData: true,
    credentials: { postgres: newCredential('DocIntel ledger', 'LEDGER_CREDENTIAL_ID') },
    parameters: {
      operation: 'executeQuery',
      query: "SELECT * FROM documents WHERE status = 'accepted' AND superseded_by = ''",
      options: {},
    },
    output: [{ json: { document_id: '', content_sha256: '', status: '' } }],
  },
});"""

old_save = """const saveRecord = node({
  type: 'n8n-nodes-base.dataTable',
  version: 1.1,
  config: {
    name: 'Save record',
    parameters: {
      resource: 'row',
      operation: 'insert',
      dataTableId: { __rl: true, mode: 'id', value: 'NBLNd99VnodAqWlD', cachedResultName: 'DocIntel Records' },
      columns: recordColumns,
    },
    output: [{ json: { id: 1 } }],
  },
});"""

new_save = """const saveRecord = node({
  type: 'n8n-nodes-base.postgres',
  version: 2.5,
  config: {
    name: 'Save record',
    credentials: { postgres: newCredential('DocIntel ledger', 'LEDGER_CREDENTIAL_ID') },
    parameters: {
      operation: 'executeQuery',
      query: 'SELECT apply_outcome($1::jsonb) AS result',
      options: { queryReplacement: expr('{{ JSON.stringify($json) }}') },
    },
    output: [{ json: { result: {} } }],
  },
});"""

old_attempt = """const logAttempt = node({
  type: 'n8n-nodes-base.dataTable',
  version: 1.1,
  config: {
    name: 'Log identical attempt',
    parameters: {
      resource: 'row',
      operation: 'insert',
      dataTableId: { __rl: true, mode: 'id', value: 'K2faxW5W3jLfprQR', cachedResultName: 'DocIntel Attempts' },
      columns: attemptColumns,
    },
    output: [{ json: { id: 1 } }],
  },
});"""

new_attempt = """const logAttempt = node({
  type: 'n8n-nodes-base.postgres',
  version: 2.5,
  config: {
    name: 'Log identical attempt',
    credentials: { postgres: newCredential('DocIntel ledger', 'LEDGER_CREDENTIAL_ID') },
    parameters: {
      operation: 'executeQuery',
      query: 'SELECT log_attempt($1::jsonb) AS result',
      options: { queryReplacement: expr('{{ JSON.stringify($json) }}') },
    },
    output: [{ json: { result: {} } }],
  },
});"""

old_thread = """const logThread = node({
  type: 'n8n-nodes-base.dataTable',
  version: 1.1,
  config: {
    name: 'Log thread',
    parameters: {
      resource: 'row',
      operation: 'insert',
      dataTableId: { __rl: true, mode: 'id', value: 'sG7N2mZkxuHryqW6', cachedResultName: 'DocIntel Thread' },
      columns: threadColumns,
    },
    output: [{ json: { id: 1 } }],
  },
});"""

new_thread = """const logThread = node({
  type: 'n8n-nodes-base.postgres',
  version: 2.5,
  config: {
    name: 'Log thread',
    credentials: { postgres: newCredential('DocIntel ledger', 'LEDGER_CREDENTIAL_ID') },
    parameters: {
      operation: 'executeQuery',
      query: 'SELECT log_thread($1::jsonb) AS result',
      options: { queryReplacement: expr('{{ JSON.stringify($json) }}') },
    },
    output: [{ json: { result: {} } }],
  },
});"""

for old, new, label in (
    (old_load, new_load, "load"),
    (old_save, new_save, "save"),
    (old_attempt, new_attempt, "attempt"),
    (old_thread, new_thread, "thread"),
):
    if old not in process:
        raise SystemExit("missing block: " + label)
    process = process.replace(old, new, 1)

old_export = """export default workflow('docintel-submit', 'DocIntel — Submit')
  .add(submitHook)
  .to(prepare)
  .to(loadRecords)
  .to(decide)
  .to(route
    .onCase(0, attemptShape.to(logAttempt.to(restoreShort.to(conversation))))
    .onCase(1, restoreShort.to(conversation))
    .onCase(2, extractPdf.to(buildText.to(httpText.to(readText.to(judge.to(saveRecord.to(restoreJudge.to(conversation))))))))
    .onCase(3, buildImage.to(httpImage.to(readImage.to(judge.to(saveRecord.to(restoreJudge.to(conversation)))))))
    .onCase(4, restoreShort.to(conversation)))
  .add(conversation)
  .to(logThread)
  .to(echo)
  .to(reply);"""

new_export = """const processHook = trigger({
  type: 'n8n-nodes-base.executeWorkflowTrigger',
  version: 1.1,
  config: { name: 'Prepare submission', parameters: {} },
});

export default workflow('docintel-process', 'DocIntel — Process')
  .add(processHook)
  .to(loadRecords)
  .to(decide)
  .to(route
    .onCase(0, attemptShape.to(logAttempt.to(restoreShort.to(conversation))))
    .onCase(1, restoreShort.to(conversation))
    .onCase(2, extractPdf.to(buildText.to(httpText.to(readText.to(judge.to(saveRecord.to(restoreJudge.to(conversation))))))))
    .onCase(3, buildImage.to(httpImage.to(readImage.to(judge.to(saveRecord.to(restoreJudge.to(conversation)))))))
    .onCase(4, restoreShort.to(conversation)))
  .add(conversation)
  .to(logThread);"""

if old_export not in process:
    raise SystemExit("missing export")
process = process.replace(old_export, new_export, 1)
(CURRENT / "2-process.js").write_text(process)
print("wrote process", len(process))
raise SystemExit(0)

ledger_node = """
function ledgerCall(name, query) {
  return node({
    type: 'n8n-nodes-base.postgres',
    version: 2.5,
    config: {
      name,
      credentials: { postgres: newCredential('DocIntel ledger', 'LEDGER_CREDENTIAL_ID') },
      parameters: {
        operation: 'executeQuery',
        query,
        options: { queryReplacement: expr('{{ JSON.stringify($json.payload || $json) }}') },
      },
    },
    output: [{ json: { result: {} } }],
  });
}
"""

intake = f"""import {{ workflow, node, trigger, switchCase, ifElse, expr, newCredential }} from '@n8n/workflow-sdk';

{prepare_code}
const intakeHook = trigger({{
  type: 'n8n-nodes-base.webhook',
  version: 2.1,
  config: {{
    name: 'File submitted',
    parameters: {{
      httpMethod: 'POST',
      path: 'docintel-submit',
      authentication: 'headerAuth',
      responseMode: 'responseNode',
      options: {{ binaryData: true, binaryPropertyName: 'data' }},
    }},
    credentials: {{ httpHeaderAuth: newCredential('DocIntel webhook', 'WEBHOOK_CREDENTIAL_ID') }},
    output: [{{ json: {{ body: {{ stated_type: 'invoice', department: 'finance', client: 'Northwind', submitted_by: 'Dre' }} }} }}],
  }},
}});

const prepare = node({{
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {{
    name: 'Prepare submission',
    parameters: {{ mode: 'runOnceForAllItems', language: 'javaScript', jsCode: prepareCode }},
    output: [{{ json: {{ content_sha256: 'abc', kind: 'pdf', stated_type: 'invoice', department: 'finance', original_filename: 'a.pdf' }} }}],
  }},
}});

const lookup = node({{
  type: 'n8n-nodes-base.postgres',
  version: 2.5,
  config: {{
    name: 'Look up the hash',
    alwaysOutputData: true,
    credentials: {{ postgres: newCredential('DocIntel ledger', 'LEDGER_CREDENTIAL_ID') }},
    parameters: {{
      operation: 'executeQuery',
      query: 'SELECT document_id, submitted_by, submitted_at, status FROM documents WHERE content_sha256 = $1',
      options: {{ queryReplacement: expr('{{{{ $json.content_sha256 }}}}') }},
    }},
    output: [{{ json: {{ document_id: '', submitted_by: '', submitted_at: '', status: '' }} }}],
  }},
}});

const decideIntake = node({{
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {{
    name: 'Decide intake',
    parameters: {{
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: `
const prep = $('Prepare submission').first().json;
const found = ($input.first() && $input.first().json) || {{}};
const binary = $('Prepare submission').first().binary;
function pack(extra) {{ return [{{ json: Object.assign({{}}, prep, extra), binary }}]; }}
if (found.document_id) {{
  const message = 'This is the exact same file as ' + found.document_id + ', submitted by ' + found.submitted_by + ' on ' + found.submitted_at + '. There are no changes in the file, so I did not create a new record. If you meant an updated contract or invoice, drop the new file.';
  return pack({{ route: 'identical', existing_document_id: found.document_id, message, note: message, reply_json: JSON.stringify({{ message, status: 'identical', document_id: found.document_id }}), payload: {{ content_sha256: prep.content_sha256, submitted_by: prep.submitted_by, submitted_at: prep.submitted_at, department: prep.department, note: message, existing_document_id: found.document_id }} }});
}}
const allowed = ['invoice', 'contract', 'brief', 'other'];
if (!allowed.includes(prep.stated_type) || !prep.department || (prep.kind !== 'pdf' && prep.kind !== 'image')) {{
  const message = prep.kind !== 'pdf' && prep.kind !== 'image'
    ? 'I can read a PDF, PNG, or JPEG. This file is none of those, so I stopped before extraction.'
    : 'I have the file, and it is not on the record yet. I still need the document type (invoice, contract, brief, or other) and the department. I will not guess either of those.';
  return pack({{ route: 'ask', message, reply_json: JSON.stringify({{ message, status: 'needs_details', document_id: '' }}) }});
}}
return pack({{ route: 'store', message: '', reply_json: '' }});
`,
    }},
    output: [{{ json: {{ route: 'store', content_sha256: 'abc', original_filename: 'a.pdf', reply_json: '{{}}' }} }}],
  }},
}});

const route = switchCase({{
  version: 3.4,
  config: {{
    name: 'Route intake',
    parameters: {{
      mode: 'rules',
      rules: {{
        values: [
          {{ outputKey: 'identical', conditions: {{ options: {{ caseSensitive: true, leftValue: '', typeValidation: 'strict' }}, conditions: [{{ leftValue: expr('{{{{ $json.route }}}}'), operator: {{ type: 'string', operation: 'equals' }}, rightValue: 'identical' }}], combinator: 'and' }} }},
          {{ outputKey: 'ask', conditions: {{ options: {{ caseSensitive: true, leftValue: '', typeValidation: 'strict' }}, conditions: [{{ leftValue: expr('{{{{ $json.route }}}}'), operator: {{ type: 'string', operation: 'equals' }}, rightValue: 'ask' }}], combinator: 'and' }} }},
          {{ outputKey: 'store', conditions: {{ options: {{ caseSensitive: true, leftValue: '', typeValidation: 'strict' }}, conditions: [{{ leftValue: expr('{{{{ $json.route }}}}'), operator: {{ type: 'string', operation: 'equals' }}, rightValue: 'store' }}], combinator: 'and' }} }},
        ],
      }},
      options: {{ fallbackOutput: 'extra', renameFallbackOutput: 'Fallback' }},
    }},
    output: [{{ json: {{ route: 'store' }} }}],
  }},
}});

const upload = node({{
  type: 'n8n-nodes-base.s3',
  version: 1,
  config: {{
    name: 'Store the original',
    credentials: {{ s3: newCredential('DocIntel originals', 'S3_CREDENTIAL_ID') }},
    parameters: {{
      resource: 'file',
      operation: 'upload',
      bucketName: 'docintel-originals',
      binaryData: true,
      binaryPropertyName: 'data',
      fileName: expr('{{{{ $json.content_sha256 + "/" + $json.original_filename }}}}'),
    }},
    output: [{{ json: {{ ok: true }} }}],
  }},
}});

const remember = node({{
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {{
    name: 'Name the document',
    parameters: {{
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: `
const prep = $('Decide intake').first().json;
const documentId = 'DOC-' + prep.content_sha256.slice(0, 8) + '-' + Date.now().toString(36);
const storageKey = prep.content_sha256 + '/' + prep.original_filename;
const payload = {{
  document_id: documentId,
  content_sha256: prep.content_sha256,
  original_filename: prep.original_filename,
  storage_key: storageKey,
  mime_type: prep.mime_type,
  page_count: String(prep.prepared_pages || prep.pdf_pages || ''),
  submitted_by: prep.submitted_by,
  submitted_at: prep.submitted_at,
  department: prep.department,
  stated_type: prep.stated_type,
  client_or_vendor_stated: prep.client_or_vendor_stated,
}};
return [{{ json: Object.assign({{}}, prep, {{ document_id: documentId, storage_key: storageKey, storage_uri: storageKey, payload }}) }}];
`,
    }},
    output: [{{ json: {{ document_id: 'DOC-1', storage_key: 'abc/a.pdf', payload: {{}} }} }}],
  }},
}});

const insert = node({{
  type: 'n8n-nodes-base.postgres',
  version: 2.5,
  config: {{
    name: 'Insert received',
    credentials: {{ postgres: newCredential('DocIntel ledger', 'LEDGER_CREDENTIAL_ID') }},
    parameters: {{
      operation: 'executeQuery',
      query: 'SELECT intake_document($1::jsonb) AS result',
      options: {{ queryReplacement: expr('{{{{ JSON.stringify($json.payload) }}}}') }},
    }},
    output: [{{ json: {{ result: {{ inserted: true, document_id: 'DOC-1' }} }} }}],
  }},
}});

const readInsert = node({{
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {{
    name: 'Read the insert',
    parameters: {{
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: `
const named = $('Name the document').first().json;
const raw = ($input.first().json || {{}}).result;
const parsed = typeof raw === 'string' ? JSON.parse(raw) : (raw || {{}});
const inserted = parsed.inserted === true || parsed.inserted === 'true';
if (!inserted) {{
  const message = 'This is the exact same file as ' + parsed.document_id + ', submitted by ' + (parsed.submitted_by || 'someone') + ' on ' + (parsed.submitted_at || 'an earlier drop') + '. There are no changes in the file, so I did not create a new record. If you meant an updated contract or invoice, drop the new file.';
  return [{{ json: {{ inserted: 'no', document_id: parsed.document_id || '', message, body: message, submitted_by: named.submitted_by, created_at: named.submitted_at, reply_json: JSON.stringify({{ message, status: 'identical', document_id: parsed.document_id || '' }}), payload: {{ content_sha256: named.content_sha256, submitted_by: named.submitted_by, submitted_at: named.submitted_at, department: named.department, note: message, existing_document_id: parsed.document_id || '' }} }} }}];
}}
const message = 'I have the file. It is not approved yet. The record will be written when the read finishes.';
return [{{ json: Object.assign({{}}, named, {{ inserted: 'yes', message, body: message, created_at: named.submitted_at, reply_json: JSON.stringify({{ message, status: 'received', document_id: named.document_id }}), thread_payload: {{ document_id: named.document_id, submitted_by: named.submitted_by, body: message, created_at: named.submitted_at }} }}) }}];
`,
    }},
    output: [{{ json: {{ inserted: 'yes', document_id: 'DOC-1', reply_json: '{{}}', payload: {{}} }} }}],
  }},
}});

const stored = ifElse({{
  version: 2.3,
  config: {{
    name: 'Stored a new file',
    parameters: {{
      conditions: {{
        options: {{ caseSensitive: true, leftValue: '', typeValidation: 'strict' }},
        conditions: [{{ leftValue: expr('{{{{ $json.inserted }}}}'), operator: {{ type: 'string', operation: 'equals' }}, rightValue: 'yes' }}],
        combinator: 'and',
      }},
    }},
  }},
}});

const enqueue = node({{
  type: 'n8n-nodes-base.executeWorkflow',
  version: 1.2,
  config: {{
    name: 'Enqueue processing',
    parameters: {{
      source: 'database',
      workflowId: {{ __rl: true, mode: 'id', value: 'PROCESS_WORKFLOW_ID' }},
      mode: 'once',
      options: {{ waitForSubWorkflow: false }},
    }},
    output: [{{ json: {{ document_id: 'DOC-1' }} }}],
  }},
}});

const logAttempt = node({{
  type: 'n8n-nodes-base.postgres',
  version: 2.5,
  config: {{
    name: 'Log identical attempt',
    credentials: {{ postgres: newCredential('DocIntel ledger', 'LEDGER_CREDENTIAL_ID') }},
    parameters: {{
      operation: 'executeQuery',
      query: 'SELECT log_attempt($1::jsonb) AS result',
      options: {{ queryReplacement: expr('{{{{ JSON.stringify($json.payload) }}}}') }},
    }},
    output: [{{ json: {{ result: {{}} }} }}],
  }},
}});

const logThread = node({{
  type: 'n8n-nodes-base.postgres',
  version: 2.5,
  config: {{
    name: 'Log thread',
    credentials: {{ postgres: newCredential('DocIntel ledger', 'LEDGER_CREDENTIAL_ID') }},
    parameters: {{
      operation: 'executeQuery',
      query: 'SELECT log_thread($1::jsonb) AS result',
      options: {{ queryReplacement: expr('{{{{ JSON.stringify($json.thread_payload || $json.payload || $json) }}}}') }},
    }},
    output: [{{ json: {{ result: {{}} }} }}],
  }},
}});

const reply = node({{
  type: 'n8n-nodes-base.respondToWebhook',
  version: 1.5,
  config: {{
    name: 'Reply in the thread',
    parameters: {{
      respondWith: 'text',
      responseBody: expr('{{{{ $("Decide intake").item.json.reply_json || $("Read the insert").item.json.reply_json }}}}'),
      options: {{
        responseCode: 200,
        enableStreaming: false,
        responseHeaders: {{ entries: [{{ name: 'Content-Type', value: 'application/json' }}] }},
      }},
    }},
    output: [{{ json: {{ ok: true }} }}],
  }},
}});

const pass = node({{
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {{
    name: 'Keep the reply',
    parameters: {{
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: 'const item = $input.first().json; return [{{ json: item }}];',
    }},
    output: [{{ json: {{ reply_json: '{{}}' }} }}],
  }},
}});

export default workflow('docintel-intake', 'DocIntel — Intake')
  .add(intakeHook)
  .to(prepare)
  .to(lookup)
  .to(decideIntake)
  .to(route
    .onCase(0, logAttempt.to(pass.to(reply)))
    .onCase(1, pass.to(reply))
    .onCase(2, upload.to(remember.to(insert.to(readInsert.to(stored.onTrue(enqueue.to(logThread.to(pass.to(reply)))).onFalse(logAttempt.to(pass.to(reply)))))))));
"""

# The f-string doubled braces. prepare_code is inserted raw. The expr templates used four braces
# which become two in the output... wait. In an f-string, {{ becomes {. I used {{{{ which becomes {{.
# n8n expressions need {{ }}. So {{{{ $json.x }}}} becomes {{ $json.x }}. Good.
# But prepare_code contains no braces that are format fields... it has lots of { } in JS!
# An f-string will try to interpret them. I must NOT use an f-string with prepare_code.
# I'll concatenate instead.

(CURRENT / "1-intake.js").write_text("SKIP")
print("process bytes", len(process))
print("prepare starts", prepare_code[:40])
