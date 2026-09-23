import { workflow, node, trigger, expr, newCredential } from '@n8n/workflow-sdk';

const hook = trigger({
  type: 'n8n-nodes-base.webhook',
  version: 2.1,
  config: {
    name: 'Thread requested',
    parameters: { httpMethod: 'GET', path: 'docintel-thread', authentication: 'headerAuth', responseMode: 'responseNode' },
    credentials: { httpHeaderAuth: newCredential('DocIntel webhook', 'fdad2f81-1ffa-43b4-8852-cea41ac4f091') },
    output: [{ json: {} }],
  },
});

const loadThread = node({
  type: 'n8n-nodes-base.dataTable',
  version: 1.1,
  config: {
    name: 'Load thread',
    alwaysOutputData: true,
    parameters: {
      resource: 'row',
      operation: 'get',
      dataTableId: { __rl: true, mode: 'id', value: 'sG7N2mZkxuHryqW6', cachedResultName: 'DocIntel Thread' },
      matchType: 'allConditions',
      filters: { conditions: [{ keyName: 'body', condition: 'isNotEmpty' }] },
      returnAll: true,
    },
    output: [{ json: { body: 'On the record', created_at: '2026-01-01T00:00:00.000Z', document_id: 'DOC-1', submitted_by: 'Andre' } }],
  },
});

const shape = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Order the thread',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: `
const lines = $input.all().map(function (i) { return i.json; }).filter(function (r) { return r && r.body; });
lines.sort(function (a, b) { return String(a.created_at || '').localeCompare(String(b.created_at || '')); });
return [{ json: { reply_json: JSON.stringify({ lines: lines }) } }];
`,
    },
    output: [{ json: { reply_json: '{"lines":[]}' } }],
  },
});

const reply = node({
  type: 'n8n-nodes-base.respondToWebhook',
  version: 1.5,
  config: {
    name: 'Send the thread',
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

export default workflow('docintel-thread', 'DocIntel — Thread')
  .add(hook)
  .to(loadThread)
  .to(shape)
  .to(reply);
