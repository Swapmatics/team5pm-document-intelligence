import { workflow, node, trigger, switchCase, ifElse, expr, newCredential } from '@n8n/workflow-sdk';

const prepareCode = `
function sha256(bytes) {
  const K = [0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2];
  function rotr(x, n) { return (x >>> n) | (x << (32 - n)); }
  let h0=0x6a09e667,h1=0xbb67ae85,h2=0x3c6ef372,h3=0xa54ff53a,h4=0x510e527f,h5=0x9b05688c,h6=0x1f83d9ab,h7=0x5be0cd19;
  const src = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  const bitLen = src.length * 8;
  const withPad = new Uint8Array(((src.length + 9 + 63) >> 6) << 6);
  withPad.set(src);
  withPad[src.length] = 0x80;
  const view = new DataView(withPad.buffer);
  view.setUint32(withPad.length - 4, bitLen >>> 0, false);
  view.setUint32(withPad.length - 8, Math.floor(bitLen / 0x100000000), false);
  const w = new Uint32Array(64);
  for (let i = 0; i < withPad.length; i += 64) {
    for (let t = 0; t < 16; t++) w[t] = view.getUint32(i + t * 4, false);
    for (let t = 16; t < 64; t++) {
      const s0 = rotr(w[t-15], 7) ^ rotr(w[t-15], 18) ^ (w[t-15] >>> 3);
      const s1 = rotr(w[t-2], 17) ^ rotr(w[t-2], 19) ^ (w[t-2] >>> 10);
      w[t] = (w[t-16] + s0 + w[t-7] + s1) >>> 0;
    }
    let a=h0,b=h1,c=h2,d=h3,e=h4,f=h5,g=h6,h=h7;
    for (let t = 0; t < 64; t++) {
      const S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
      const ch = (e & f) ^ (~e & g);
      const temp1 = (h + S1 + ch + K[t] + w[t]) >>> 0;
      const S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
      const maj = (a & b) ^ (a & c) ^ (b & c);
      const temp2 = (S0 + maj) >>> 0;
      h=g; g=f; f=e; e=(d + temp1) >>> 0; d=c; c=b; b=a; a=(temp1 + temp2) >>> 0;
    }
    h0=(h0+a)>>>0; h1=(h1+b)>>>0; h2=(h2+c)>>>0; h3=(h3+d)>>>0;
    h4=(h4+e)>>>0; h5=(h5+f)>>>0; h6=(h6+g)>>>0; h7=(h7+h)>>>0;
  }
  return [h0,h1,h2,h3,h4,h5,h6,h7].map(function (x) { return x.toString(16).padStart(8, '0'); }).join('');
}
const item = $input.first();
const body = (item.json && item.json.body) || {};
const binaryKey = item.binary ? Object.keys(item.binary)[0] : '';
if (!binaryKey) throw new Error('No file was attached.');
let buf;
try {
  buf = await this.helpers.getBinaryDataBuffer(0, binaryKey);
} catch (e) {
  throw new Error('Could not read the file: ' + (e && e.message ? e.message : JSON.stringify(e)));
}
const hash = sha256(buf);
const binaryMeta = (item.binary && item.binary[binaryKey]) || {};
const filename = binaryMeta.fileName || body.filename || 'upload';
const mime = binaryMeta.mimeType || 'application/octet-stream';
const stated = String(body.stated_type || '').trim().toLowerCase();
const department = String(body.department || '').trim();
const client = String(body.client || '').trim();
const submittedBy = String(body.submitted_by || 'unknown').trim();
const storageUri = String(body.storage_uri || '').trim();
const preparedPages = Number(body.prepared_pages || 0) || 0;
let preparedText = '';
if (body.prepared_text) {
  preparedText = Buffer.from(String(body.prepared_text), 'base64').toString('utf8');
}
const b0 = buf[0], b1 = buf[1], b2 = buf[2], b3 = buf[3];
const isPdf = b0 === 0x25 && b1 === 0x50 && b2 === 0x44 && b3 === 0x46;
const isPng = b0 === 0x89 && b1 === 0x50 && b2 === 0x4e && b3 === 0x47;
const isJpeg = b0 === 0xff && b1 === 0xd8 && b2 === 0xff;
let kind = 'other';
if (isPdf) kind = 'pdf';
else if (isPng || isJpeg) kind = 'image';
else if ((b0 === 0x50 && b1 === 0x4b) || (b0 === 0xd0 && b1 === 0xcf && b2 === 0x11 && b3 === 0xe0)) kind = 'word';
let pdfPages = preparedPages;
if (isPdf && !pdfPages) {
  const latin = Buffer.from(buf).toString('latin1');
  const marker = '/Type /Page';
  let from = 0;
  while (from < latin.length) {
    const at = latin.indexOf(marker, from);
    if (at < 0) break;
    if (latin.charAt(at + marker.length) !== 's') pdfPages += 1;
    from = at + marker.length;
  }
}
const imageB64 = kind === 'image' ? buf.toString('base64') : '';
return [{
  json: {
    content_sha256: hash,
    original_filename: filename,
    mime_type: mime,
    storage_uri: storageUri,
    pdf_pages: pdfPages,
    prepared_text: preparedText,
    prepared_pages: preparedPages,
    kind,
    stated_type: stated,
    department,
    client_or_vendor_stated: client,
    submitted_by: submittedBy,
    submitted_at: new Date().toISOString(),
    image_b64: imageB64,
  },
  binary: { data: item.binary[binaryKey] },
}];
`;

const intakeHook = trigger({
  type: 'n8n-nodes-base.webhook',
  version: 2.1,
  config: {
    name: 'File submitted',
    parameters: {
      httpMethod: 'POST',
      path: 'docintel-submit',
      authentication: 'headerAuth',
      responseMode: 'responseNode',
      options: { binaryData: true, binaryPropertyName: 'data' },
    },
    credentials: { httpHeaderAuth: newCredential('DocIntel webhook', 'WEBHOOK_CREDENTIAL_ID') },
    output: [{ json: { body: { stated_type: 'invoice', department: 'finance', client: 'Northwind', submitted_by: 'Andre' } } }],
  },
});

const prepare = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Prepare submission',
    parameters: { mode: 'runOnceForAllItems', language: 'javaScript', jsCode: prepareCode },
    output: [{ json: { content_sha256: 'abc', kind: 'pdf', stated_type: 'invoice', department: 'finance', original_filename: 'a.pdf' } }],
  },
});

const lookup = node({
  type: 'n8n-nodes-base.postgres',
  version: 2.5,
  config: {
    name: 'Look up the hash',
    alwaysOutputData: true,
    credentials: { postgres: newCredential('DocIntel ledger', 'LEDGER_CREDENTIAL_ID') },
    parameters: {
      operation: 'executeQuery',
      query: 'SELECT document_id, submitted_by, submitted_at, status FROM documents WHERE content_sha256 = $1',
      options: { queryReplacement: expr('{{ $json.content_sha256 }}') },
    },
    output: [{ json: { document_id: '', submitted_by: '', submitted_at: '', status: '' } }],
  },
});

const decideIntakeCode = `
const prep = $('Prepare submission').first().json;
const found = ($input.first() && $input.first().json) || {};
const binary = $('Prepare submission').first().binary;
function pack(extra) { return [{ json: Object.assign({}, prep, extra), binary }]; }
if (found.document_id) {
  const message = 'This is the exact same file as ' + found.document_id + ', submitted by ' + found.submitted_by + ' on ' + found.submitted_at + '. There are no changes in the file, so I did not create a new record. If you meant an updated contract or invoice, drop the new file.';
  return pack({
    route: 'identical',
    existing_document_id: found.document_id,
    message: message,
    body: message,
    created_at: prep.submitted_at,
    reply_json: JSON.stringify({ message: message, status: 'identical', document_id: found.document_id }),
    payload: { content_sha256: prep.content_sha256, submitted_by: prep.submitted_by, submitted_at: prep.submitted_at, department: prep.department, note: message, existing_document_id: found.document_id },
    thread_payload: { document_id: found.document_id, submitted_by: prep.submitted_by, body: message, created_at: prep.submitted_at },
  });
}
const allowed = ['invoice', 'contract', 'brief', 'other'];
if (!allowed.includes(prep.stated_type) || !prep.department || (prep.kind !== 'pdf' && prep.kind !== 'image' && prep.kind !== 'word')) {
  const message = (prep.kind !== 'pdf' && prep.kind !== 'image' && prep.kind !== 'word')
    ? 'I can read a PDF, a Word document, a PNG, or a JPEG. This file is none of those, so I stopped before extraction.'
    : 'I have the file, and it is not on the record yet. I still need the document type (invoice, contract, brief, or other) and the department. I will not guess either of those.';
  return pack({ route: 'ask', message: message, reply_json: JSON.stringify({ message: message, status: 'needs_details', document_id: '' }) });
}
return pack({ route: 'store', message: '', reply_json: '' });
`;

const decideIntake = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Decide intake',
    parameters: { mode: 'runOnceForAllItems', language: 'javaScript', jsCode: decideIntakeCode },
    output: [{ json: { route: 'store', content_sha256: 'abc', original_filename: 'a.pdf', reply_json: '{}' } }],
  },
});

const route = switchCase({
  version: 3.4,
  config: {
    name: 'Route intake',
    parameters: {
      mode: 'rules',
      rules: {
        values: [
          { outputKey: 'identical', conditions: { options: { caseSensitive: true, leftValue: '', typeValidation: 'strict' }, conditions: [{ leftValue: expr('{{ $json.route }}'), operator: { type: 'string', operation: 'equals' }, rightValue: 'identical' }], combinator: 'and' } },
          { outputKey: 'ask', conditions: { options: { caseSensitive: true, leftValue: '', typeValidation: 'strict' }, conditions: [{ leftValue: expr('{{ $json.route }}'), operator: { type: 'string', operation: 'equals' }, rightValue: 'ask' }], combinator: 'and' } },
          { outputKey: 'store', conditions: { options: { caseSensitive: true, leftValue: '', typeValidation: 'strict' }, conditions: [{ leftValue: expr('{{ $json.route }}'), operator: { type: 'string', operation: 'equals' }, rightValue: 'store' }], combinator: 'and' } },
        ],
      },
      options: { fallbackOutput: 'extra', renameFallbackOutput: 'Fallback' },
    },
    output: [{ json: { route: 'store' } }],
  },
});

const upload = node({
  type: 'n8n-nodes-base.s3',
  version: 1,
  config: {
    name: 'Store the original',
    credentials: { s3: newCredential('DocIntel originals', 'S3_CREDENTIAL_ID') },
    parameters: {
      resource: 'file',
      operation: 'upload',
      bucketName: 'docintel-originals',
      binaryData: true,
      binaryPropertyName: 'data',
      fileName: expr('{{ $json.content_sha256 + "/" + $json.original_filename }}'),
    },
    output: [{ json: { ok: true } }],
  },
});

const rememberCode = `
const prep = $('Decide intake').first().json;
const documentId = 'DOC-' + prep.content_sha256.slice(0, 8) + '-' + Date.now().toString(36);
const storageKey = prep.content_sha256 + '/' + prep.original_filename;
const payload = {
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
};
const binary = $('Decide intake').first().binary;
return [{ json: Object.assign({}, prep, { document_id: documentId, storage_key: storageKey, storage_uri: storageKey, payload: payload }), binary }];
`;

const remember = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Name the document',
    parameters: { mode: 'runOnceForAllItems', language: 'javaScript', jsCode: rememberCode },
    output: [{ json: { document_id: 'DOC-1', storage_key: 'abc/a.pdf', payload: {} } }],
  },
});

const insert = node({
  type: 'n8n-nodes-base.postgres',
  version: 2.5,
  config: {
    name: 'Insert received',
    credentials: { postgres: newCredential('DocIntel ledger', 'LEDGER_CREDENTIAL_ID') },
    parameters: {
      operation: 'executeQuery',
      query: 'SELECT intake_document($1::jsonb) AS result',
      options: { queryReplacement: expr('{{ JSON.stringify($json.payload) }}') },
    },
    output: [{ json: { result: { inserted: true, document_id: 'DOC-1' } } }],
  },
});

const readInsertCode = `
const named = $('Name the document').first().json;
const raw = ($input.first().json || {}).result;
const parsed = typeof raw === 'string' ? JSON.parse(raw) : (raw || {});
const inserted = parsed.inserted === true || parsed.inserted === 'true';
if (!inserted) {
  const message = 'This is the exact same file as ' + parsed.document_id + ', submitted by ' + (parsed.submitted_by || 'someone') + ' on ' + (parsed.submitted_at || 'an earlier drop') + '. There are no changes in the file, so I did not create a new record. If you meant an updated contract or invoice, drop the new file.';
  return [{ json: {
    inserted: 'no',
    document_id: parsed.document_id || '',
    message: message,
    body: message,
    submitted_by: named.submitted_by,
    created_at: named.submitted_at,
    reply_json: JSON.stringify({ message: message, status: 'identical', document_id: parsed.document_id || '' }),
    payload: { content_sha256: named.content_sha256, submitted_by: named.submitted_by, submitted_at: named.submitted_at, department: named.department, note: message, existing_document_id: parsed.document_id || '' },
    thread_payload: { document_id: parsed.document_id || '', submitted_by: named.submitted_by, body: message, created_at: named.submitted_at },
  } }];
}
const message = 'I have the file. It is not approved yet. The record will be written when the read finishes.';
const binary = $('Decide intake').first().binary;
return [{ json: Object.assign({}, named, {
  inserted: 'yes',
  message: message,
  body: message,
  created_at: named.submitted_at,
  reply_json: JSON.stringify({ message: message, status: 'received', document_id: named.document_id }),
  thread_payload: { document_id: named.document_id, submitted_by: named.submitted_by, body: message, created_at: named.submitted_at },
}), binary }];
`;

const readInsert = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Read the insert',
    parameters: { mode: 'runOnceForAllItems', language: 'javaScript', jsCode: readInsertCode },
    output: [{ json: { inserted: 'yes', document_id: 'DOC-1', reply_json: '{}', thread_payload: {}, payload: {} } }],
  },
});

const stored = ifElse({
  version: 2.3,
  config: {
    name: 'Stored a new file',
    parameters: {
      conditions: {
        options: { caseSensitive: true, leftValue: '', typeValidation: 'strict' },
        conditions: [{ leftValue: expr('{{ $json.inserted }}'), operator: { type: 'string', operation: 'equals' }, rightValue: 'yes' }],
        combinator: 'and',
      },
    },
  },
});

const enqueue = node({
  type: 'n8n-nodes-base.executeWorkflow',
  version: 1.2,
  config: {
    name: 'Enqueue processing',
    parameters: {
      source: 'database',
      workflowId: { __rl: true, mode: 'id', value: 'PROCESS_WORKFLOW_ID' },
      mode: 'once',
      options: { waitForSubWorkflow: false },
    },
    output: [{ json: { document_id: 'DOC-1' } }],
  },
});

const restoreItem = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Keep the reply',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: `
let row = null;
try { row = $('Read the insert').first().json; } catch (e) { row = null; }
if (!row || !row.reply_json) row = $('Decide intake').first().json;
return [{ json: row }];
`,
    },
    output: [{ json: { reply_json: '{}', thread_payload: {}, payload: {} } }],
  },
});

const logAttempt = node({
  type: 'n8n-nodes-base.postgres',
  version: 2.5,
  config: {
    name: 'Log identical attempt',
    credentials: { postgres: newCredential('DocIntel ledger', 'LEDGER_CREDENTIAL_ID') },
    parameters: {
      operation: 'executeQuery',
      query: 'SELECT log_attempt($1::jsonb) AS result',
      options: { queryReplacement: expr('{{ JSON.stringify($json.payload) }}') },
    },
    output: [{ json: { result: {} } }],
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

const reply = node({
  type: 'n8n-nodes-base.respondToWebhook',
  version: 1.5,
  config: {
    name: 'Reply in the thread',
    parameters: {
      respondWith: 'text',
      responseBody: expr('{{ $("Keep the reply").item.json.reply_json }}'),
      options: {
        responseCode: 200,
        enableStreaming: false,
        responseHeaders: { entries: [{ name: 'Content-Type', value: 'application/json' }] },
      },
    },
    output: [{ json: { ok: true } }],
  },
});

export default workflow('docintel-intake', 'DocIntel — Intake')
  .add(intakeHook)
  .to(prepare)
  .to(lookup)
  .to(decideIntake)
  .to(route
    .onCase(0, logAttempt.to(restoreItem.to(logThread.to(reply))))
    .onCase(1, restoreItem.to(reply))
    .onCase(2, upload.to(remember.to(insert.to(readInsert.to(stored
      .onTrue(enqueue.to(restoreItem.to(logThread.to(reply))))
      .onFalse(logAttempt.to(restoreItem.to(logThread.to(reply))))))))));
