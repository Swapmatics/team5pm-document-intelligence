import { workflow, node, trigger, expr, newCredential } from '@n8n/workflow-sdk';

const hook = trigger({
  type: 'n8n-nodes-base.webhook',
  version: 2.1,
  config: {
    name: 'Record book requested',
    parameters: { httpMethod: 'GET', path: 'docintel-records', authentication: 'headerAuth', responseMode: 'responseNode' },
    credentials: { httpHeaderAuth: newCredential('DocIntel webhook', 'WEBHOOK_CREDENTIAL_ID') },
    output: [{ json: {} }],
  },
});

const loadRecords = node({
  type: 'n8n-nodes-base.postgres',
  version: 2.5,
  config: {
    name: 'Load records',
    alwaysOutputData: true,
    credentials: { postgres: newCredential('DocIntel ledger', 'LEDGER_CREDENTIAL_ID') },
    parameters: {
      operation: 'executeQuery',
      query: 'SELECT * FROM documents ORDER BY submitted_at',
      options: {},
    },
    output: [{ json: { document_id: 'DOC-1', status: 'accepted', superseded_by: '' } }],
  },
});

const shape = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Split the book',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: `
const rows = $input.all().map(function (i) { return i.json; }).filter(function (r) { return r && r.document_id; });
const current = [];
const held = [];
const history = [];
const reading = [];
for (let i = 0; i < rows.length; i++) {
  const row = rows[i];
  if (row.status === 'accepted' && !row.superseded_by) current.push(row);
  else if (row.status === 'superseded') history.push(row);
  else if (row.status === 'received' || row.status === 'processing') reading.push(row);
  else held.push(row);
}
return [{ json: { reply_json: JSON.stringify({ current: current, held: held, history: history, reading: reading }) } }];
`,
    },
    output: [{ json: { reply_json: '{"current":[],"held":[],"history":[]}' } }],
  },
});

const reply = node({
  type: 'n8n-nodes-base.respondToWebhook',
  version: 1.5,
  config: {
    name: 'Send the book',
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

export default workflow('docintel-records-ledger', 'DocIntel — Record book ledger')
  .add(hook)
  .to(loadRecords)
  .to(shape)
  .to(reply);
