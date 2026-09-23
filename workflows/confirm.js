import { workflow, node, trigger, ifElse, expr, newCredential } from '@n8n/workflow-sdk';

const confirmHook = trigger({
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
    credentials: { httpHeaderAuth: newCredential('DocIntel webhook', 'fdad2f81-1ffa-43b4-8852-cea41ac4f091') },
    output: [{ json: { body: { document_id: 'DOC-1', decision: 'yes', submitted_by: 'Dre' } } }],
  },
});

const loadRecords = node({
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
      filters: { conditions: [{ keyName: 'document_id', condition: 'eq', keyValue: expr('{{ $("Replacement answer").item.json.body.document_id }}') }] },
      returnAll: false,
      limit: 1,
    },
    output: [{ json: { document_id: 'DOC-1', status: 'awaiting_confirm', supersedes: 'DOC-0' } }],
  },
});

const decideCode = `
const body = ($('Replacement answer').first().json.body) || $('Replacement answer').first().json || {};
const documentId = String(body.document_id || '').trim();
const decision = String(body.decision || '').trim().toLowerCase();
const submittedBy = String(body.submitted_by || 'unknown').trim();
const rows = $input.all().map(i => i.json).filter(r => r && r.document_id);
const row = rows.find(r => r.document_id === documentId);
const now = new Date().toISOString();
if (!row) {
  const message = 'I could not find ' + (documentId || 'that document') + ', so nothing was changed.';
  return [{ json: { proceed: 'no', message, reply_json: JSON.stringify({ message, status: 'missing', document_id: documentId }), document_id: documentId, submitted_by: submittedBy, body: message, created_at: now } }];
}
if (row.status !== 'awaiting_confirm') {
  const message = documentId + ' is ' + row.status + ', so there is nothing waiting on a yes or no.';
  return [{ json: { proceed: 'no', message, reply_json: JSON.stringify({ message, status: row.status, document_id: documentId }), document_id: documentId, submitted_by: submittedBy, body: message, created_at: now } }];
}
if (decision !== 'yes' && decision !== 'no') {
  const message = 'Reply yes to replace ' + row.supersedes + ', or no to leave the new file held. I have not changed the current record.';
  return [{ json: { proceed: 'no', message, reply_json: JSON.stringify({ message, status: 'awaiting_confirm', document_id: documentId, supersedes: row.supersedes }), document_id: documentId, submitted_by: submittedBy, body: message, created_at: now } }];
}
if (decision === 'no') {
  const message = documentId + ' stays held. ' + row.supersedes + ' is still the current record. I did not accept this file as a second current record.';
  return [{ json: {
    proceed: 'hold',
    document_id: documentId,
    status: 'held',
    validation_notes: 'You said this does not replace ' + row.supersedes + '. The new file stays held. The current record was not changed.',
    reviewed_by: submittedBy,
    reviewed_at: now,
    accepted_at: '',
    message,
    body: message,
    submitted_by: submittedBy,
    created_at: now,
    reply_json: JSON.stringify({ message, status: 'held', document_id: documentId }),
  } }];
}
const message = documentId + ' is now the current record. ' + row.supersedes + ' stays in History.';
return [{ json: {
  proceed: 'replace',
  document_id: documentId,
  old_id: row.supersedes,
  status: 'accepted',
  validation_notes: row.validation_notes || '',
  reviewed_by: submittedBy,
  reviewed_at: now,
  accepted_at: now,
  superseded_by: documentId,
  message,
  body: message,
  submitted_by: submittedBy,
  created_at: now,
  reply_json: JSON.stringify({ message, status: 'accepted', document_id: documentId, supersedes: row.supersedes }),
} }];
`;

const decide = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Read the answer',
    parameters: { mode: 'runOnceForAllItems', language: 'javaScript', jsCode: decideCode },
    output: [{ json: { proceed: 'no', document_id: 'DOC-1', status: 'held', message: 'Kept', reply_json: '{}', body: 'Kept', submitted_by: 'Dre', created_at: '2026-01-01T00:00:00.000Z', old_id: 'DOC-0', validation_notes: '', reviewed_by: 'Dre', reviewed_at: '2026-01-01T00:00:00.000Z', accepted_at: '', superseded_by: 'DOC-1' } }],
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

const newRowColumns = {
  mappingMode: 'defineBelow',
  value: {
    status: expr('{{ $("Read the answer").item.json.status }}'),
    validation_notes: expr('{{ $("Read the answer").item.json.validation_notes }}'),
    reviewed_by: expr('{{ $("Read the answer").item.json.reviewed_by }}'),
    reviewed_at: expr('{{ $("Read the answer").item.json.reviewed_at }}'),
    accepted_at: expr('{{ $("Read the answer").item.json.accepted_at }}'),
  },
  schema: [
    { id: 'status', displayName: 'status', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'validation_notes', displayName: 'validation_notes', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'reviewed_by', displayName: 'reviewed_by', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'reviewed_at', displayName: 'reviewed_at', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'accepted_at', displayName: 'accepted_at', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
  ],
};

const updateNew = node({
  type: 'n8n-nodes-base.dataTable',
  version: 1.1,
  config: {
    name: 'Update this document',
    onError: 'continueErrorOutput',
    parameters: {
      resource: 'row',
      operation: 'update',
      dataTableId: { __rl: true, mode: 'id', value: 'NBLNd99VnodAqWlD', cachedResultName: 'DocIntel Records' },
      matchType: 'allConditions',
      filters: { conditions: [{ keyName: 'document_id', condition: 'eq', keyValue: expr('{{ $json.document_id }}') }] },
      columns: newRowColumns,
    },
    output: [{ json: { id: 1 } }],
  },
});

const replaceBranch = ifElse({
  version: 2.3,
  config: {
    name: 'Replacing the old record',
    parameters: {
      conditions: {
        options: { caseSensitive: true, leftValue: '', typeValidation: 'strict' },
        conditions: [{ leftValue: expr('{{ $("Read the answer").item.json.proceed }}'), operator: { type: 'string', operation: 'equals' }, rightValue: 'replace' }],
        combinator: 'and',
      },
    },
  },
});

const oldRowColumns = {
  mappingMode: 'defineBelow',
  value: {
    status: 'superseded',
    superseded_by: expr('{{ $("Read the answer").item.json.document_id }}'),
  },
  schema: [
    { id: 'status', displayName: 'status', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'superseded_by', displayName: 'superseded_by', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
  ],
};

const updateOld = node({
  type: 'n8n-nodes-base.dataTable',
  version: 1.1,
  config: {
    name: 'Move the old record to history',
    parameters: {
      resource: 'row',
      operation: 'update',
      dataTableId: { __rl: true, mode: 'id', value: 'NBLNd99VnodAqWlD', cachedResultName: 'DocIntel Records' },
      matchType: 'allConditions',
      filters: { conditions: [{ keyName: 'document_id', condition: 'eq', keyValue: expr('{{ $("Read the answer").item.json.old_id }}') }] },
      columns: oldRowColumns,
    },
    output: [{ json: { id: 1 } }],
  },
});

const restore = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Conversation line',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: 'const d = $("Read the answer").first().json; let failed = null; try { failed = $("Replacement did not finish").first().json; } catch (e) { failed = null; } const body = (failed && failed.failure_body) || d.body || d.message || ""; const reply = (failed && failed.failure_body && failed.reply_json) || d.reply_json; return [{ json: { document_id: d.document_id || "", submitted_by: d.submitted_by || "", body: body, created_at: (failed && failed.created_at) || d.created_at, reply_json: reply } }];',
    },
    output: [{ json: { document_id: 'DOC-1', submitted_by: 'Dre', body: 'Done', created_at: '2026-01-01T00:00:00.000Z', reply_json: '{}' } }],
  },
});

const logThread = node({
  type: 'n8n-nodes-base.dataTable',
  version: 1.1,
  config: {
    name: 'Log thread',
    parameters: {
      resource: 'row',
      operation: 'insert',
      dataTableId: { __rl: true, mode: 'id', value: 'sG7N2mZkxuHryqW6', cachedResultName: 'DocIntel Thread' },
      columns: {
        mappingMode: 'defineBelow',
        value: {
          document_id: expr('{{ $json.document_id }}'),
          submitted_by: expr('{{ $json.submitted_by }}'),
          body: expr('{{ $json.body }}'),
          created_at: expr('{{ $json.created_at }}'),
        },
        schema: [
          { id: 'document_id', displayName: 'document_id', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
          { id: 'submitted_by', displayName: 'submitted_by', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
          { id: 'body', displayName: 'body', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
          { id: 'created_at', displayName: 'created_at', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
        ],
      },
    },
    output: [{ json: { id: 1 } }],
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
    output: [{ json: { reply_json: '{"message":"ok"}' } }],
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

const pass = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Pass the answer through',
    parameters: { mode: 'runOnceForAllItems', language: 'javaScript', jsCode: 'return $input.all();' },
    output: [{ json: { proceed: 'replace' } }],
  },
});

const failure = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Replacement did not finish',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: `
const d = $('Read the answer').first().json;
const now = new Date().toISOString();
if (d.proceed !== 'replace' || !d.old_id) {
  const message = 'That write did not finish. The current record was not changed.';
  return [{ json: { restore: 'no', failure_body: message, document_id: d.document_id || '', submitted_by: d.submitted_by || '', body: message, created_at: now, reply_json: JSON.stringify({ message: message, status: 'error', document_id: d.document_id || '' }) } }];
}
const message = 'The replacement did not finish. ' + d.old_id + ' is still the current record. ' + d.document_id + ' was not accepted.';
return [{ json: { restore: 'yes', old_id: d.old_id, failure_body: message, document_id: d.document_id || '', submitted_by: d.submitted_by || '', body: message, created_at: now, reply_json: JSON.stringify({ message: message, status: 'error', document_id: d.document_id || '' }) } }];
`,
    },
    output: [{ json: { restore: 'yes', old_id: 'DOC-0', failure_body: 'The replacement did not finish.', document_id: 'DOC-1', submitted_by: 'Dre', body: 'The replacement did not finish.', created_at: '2026-01-01T00:00:00.000Z', reply_json: '{}' } }],
  },
});

const needRestore = ifElse({
  version: 2.3,
  config: {
    name: 'Need to restore',
    parameters: {
      conditions: {
        options: { caseSensitive: true, leftValue: '', typeValidation: 'strict' },
        conditions: [{ leftValue: expr('{{ $json.restore }}'), operator: { type: 'string', operation: 'equals' }, rightValue: 'yes' }],
        combinator: 'and',
      },
    },
  },
});

const undo = node({
  type: 'n8n-nodes-base.dataTable',
  version: 1.1,
  config: {
    name: 'Put the old record back',
    parameters: {
      resource: 'row',
      operation: 'update',
      dataTableId: { __rl: true, mode: 'id', value: 'NBLNd99VnodAqWlD', cachedResultName: 'DocIntel Records' },
      matchType: 'allConditions',
      filters: { conditions: [{ keyName: 'document_id', condition: 'eq', keyValue: expr('{{ $("Replacement did not finish").item.json.old_id }}') }] },
      columns: {
        mappingMode: 'defineBelow',
        value: { status: 'accepted', superseded_by: '' },
        schema: [
          { id: 'status', displayName: 'status', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
          { id: 'superseded_by', displayName: 'superseded_by', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
        ],
      },
    },
    output: [{ json: { id: 1 } }],
  },
});

updateNew.output(1).to(failure.to(needRestore.onTrue(undo.to(restore)).onFalse(restore)));

export default workflow('docintel-confirm', 'DocIntel — Confirm')
  .add(confirmHook)
  .to(loadRecords)
  .to(decide)
  .to(branch
    .onTrue(replaceBranch.onTrue(updateOld.to(updateNew.to(restore))).onFalse(updateNew.to(restore)))
    .onFalse(restore))
  .add(restore)
  .to(logThread)
  .to(echo)
  .to(reply);
