import { workflow, node, trigger, ifElse, expr, newCredential } from '@n8n/workflow-sdk';

const hook = trigger({
  type: 'n8n-nodes-base.webhook',
  version: 2.1,
  config: {
    name: 'Replacement answer',
    parameters: {
      httpMethod: 'POST',
      path: 'docintel-confirm',
      authentication: 'headerAuth',
      responseMode: 'responseNode',
    },
    credentials: { httpHeaderAuth: newCredential('DocIntel webhook', 'WEBHOOK_CREDENTIAL_ID') },
    output: [{ json: { body: { document_id: 'DOC-1', decision: 'yes', submitted_by: 'Dre' } } }],
  },
});

const loadOne = node({
  type: 'n8n-nodes-base.postgres',
  version: 2.5,
  config: {
    name: 'Load this document',
    alwaysOutputData: true,
    credentials: { postgres: newCredential('DocIntel ledger', 'LEDGER_CREDENTIAL_ID') },
    parameters: {
      operation: 'executeQuery',
      query: 'SELECT * FROM documents WHERE document_id = $1',
      options: { queryReplacement: expr('{{ $json.body.document_id }}') },
    },
    output: [{ json: { document_id: 'DOC-1', status: 'awaiting_confirm', supersedes: 'DOC-0' } }],
  },
});

const decideCode = `
const body = ($('Replacement answer').first().json.body) || {};
const documentId = String(body.document_id || '').trim();
const decision = String(body.decision || '').trim().toLowerCase();
const submittedBy = String(body.submitted_by || 'unknown').trim();
const row = ($input.first() && $input.first().json && $input.first().json.document_id) ? $input.first().json : null;
const now = new Date().toISOString();
if (!row) {
  const message = 'I could not find ' + (documentId || 'that document') + ', so nothing was changed.';
  return [{ json: { proceed: 'no', message: message, body: message, document_id: documentId, submitted_by: submittedBy, created_at: now, reply_json: JSON.stringify({ message: message, status: 'missing', document_id: documentId }) } }];
}
if (row.status !== 'awaiting_confirm') {
  const message = documentId + ' is ' + row.status + ', so there is nothing waiting on a yes or no.';
  return [{ json: { proceed: 'no', message: message, body: message, document_id: documentId, submitted_by: submittedBy, created_at: now, reply_json: JSON.stringify({ message: message, status: row.status, document_id: documentId }) } }];
}
if (decision !== 'yes' && decision !== 'no') {
  const message = 'Reply yes to replace ' + row.supersedes + ', or no to leave the new file held. I have not changed the current record.';
  return [{ json: { proceed: 'no', message: message, body: message, document_id: documentId, submitted_by: submittedBy, created_at: now, reply_json: JSON.stringify({ message: message, status: 'awaiting_confirm', document_id: documentId, supersedes: row.supersedes }) } }];
}
if (decision === 'no') {
  const message = documentId + ' stays held. ' + row.supersedes + ' is still the current record. I did not accept this file as a second current record.';
  const note = 'You said this does not replace ' + row.supersedes + '. The new file stays held. The current record was not changed.';
  return [{ json: { proceed: 'hold', message: message, body: message, document_id: documentId, submitted_by: submittedBy, created_at: now, reply_json: JSON.stringify({ message: message, status: 'held', document_id: documentId }), payload: { document_id: documentId, submitted_by: submittedBy, note: note } } }];
}
const message = documentId + ' is now the current record. ' + row.supersedes + ' stays in History.';
return [{ json: { proceed: 'replace', message: message, body: message, document_id: documentId, old_id: row.supersedes, submitted_by: submittedBy, created_at: now, reply_json: JSON.stringify({ message: message, status: 'accepted', document_id: documentId, supersedes: row.supersedes }), payload: { document_id: documentId, old_id: row.supersedes, submitted_by: submittedBy } } }];
`;

const decide = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Read the answer',
    parameters: { mode: 'runOnceForAllItems', language: 'javaScript', jsCode: decideCode },
    output: [{ json: { proceed: 'no', document_id: 'DOC-1', reply_json: '{}', payload: {}, body: 'Kept', submitted_by: 'Dre', created_at: '2026-01-01T00:00:00.000Z' } }],
  },
});

const branch = ifElse({
  version: 2.3,
  config: {
    name: 'Needs a write',
    parameters: {
      conditions: {
        options: { caseSensitive: true, leftValue: '', typeValidation: 'strict' },
        conditions: [{ leftValue: expr('{{ $json.proceed }}'), operator: { type: 'string', operation: 'notEquals' }, rightValue: 'no' }],
        combinator: 'and',
      },
    },
  },
});

const replaceBranch = ifElse({
  version: 2.3,
  config: {
    name: 'Replacing the old record',
    parameters: {
      conditions: {
        options: { caseSensitive: true, leftValue: '', typeValidation: 'strict' },
        conditions: [{ leftValue: expr('{{ $json.proceed }}'), operator: { type: 'string', operation: 'equals' }, rightValue: 'replace' }],
        combinator: 'and',
      },
    },
  },
});

const doReplace = node({
  type: 'n8n-nodes-base.postgres',
  version: 2.5,
  config: {
    name: 'Replace in one transaction',
    credentials: { postgres: newCredential('DocIntel ledger', 'LEDGER_CREDENTIAL_ID') },
    parameters: {
      operation: 'executeQuery',
      query: 'SELECT confirm_replacement_payload($1::jsonb) AS result',
      options: { queryReplacement: expr('{{ JSON.stringify($json.payload) }}') },
    },
    output: [{ json: { result: {} } }],
  },
});

const doHold = node({
  type: 'n8n-nodes-base.postgres',
  version: 2.5,
  config: {
    name: 'Leave the new file held',
    credentials: { postgres: newCredential('DocIntel ledger', 'LEDGER_CREDENTIAL_ID') },
    parameters: {
      operation: 'executeQuery',
      query: 'SELECT hold_document_payload($1::jsonb) AS result',
      options: { queryReplacement: expr('{{ JSON.stringify($json.payload) }}') },
    },
    output: [{ json: { result: {} } }],
  },
});

const line = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Conversation line',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: `
const d = $('Read the answer').first().json;
return [{ json: { document_id: d.document_id || '', submitted_by: d.submitted_by || '', body: d.body || d.message || '', created_at: d.created_at, reply_json: d.reply_json, thread_payload: { document_id: d.document_id || '', submitted_by: d.submitted_by || '', body: d.body || d.message || '', created_at: d.created_at } } }];
`,
    },
    output: [{ json: { reply_json: '{}', thread_payload: {} } }],
  },
});

const logThread = node({
  type: 'n8n-nodes-base.postgres',
  version: 2.5,
  config: {
    name: 'Log thread',
    credentials: { postgres: newCredential('DocIntel ledger', 'LEDGER_CREDENTIAL_ID') },
    parameters: {
      operation: 'executeQuery',
      query: 'SELECT log_thread($1::jsonb) AS result',
      options: { queryReplacement: expr('{{ JSON.stringify($json.thread_payload) }}') },
    },
    output: [{ json: { result: {} } }],
  },
});

const echo = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Keep the reply',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: 'return [{ json: $("Conversation line").first().json }];',
    },
    output: [{ json: { reply_json: '{}' } }],
  },
});

const reply = node({
  type: 'n8n-nodes-base.respondToWebhook',
  version: 1.5,
  config: {
    name: 'Reply in the thread',
    parameters: {
      respondWith: 'text',
      responseBody: expr('{{ $json.reply_json }}'),
      options: {
        responseCode: 200,
        enableStreaming: false,
        responseHeaders: { entries: [{ name: 'Content-Type', value: 'application/json' }] },
      },
    },
    output: [{ json: { ok: true } }],
  },
});

export default workflow('docintel-confirm-ledger', 'DocIntel — Confirm ledger')
  .add(hook)
  .to(loadOne)
  .to(decide)
  .to(branch
    .onTrue(replaceBranch.onTrue(doReplace.to(line)).onFalse(doHold.to(line)))
    .onFalse(line))
  .add(line)
  .to(logThread)
  .to(echo)
  .to(reply);
