import { workflow, node, trigger, switchCase, expr, newCredential } from '@n8n/workflow-sdk';

const recordColumns = {
  mappingMode: 'defineBelow',
  value: {
    document_id: expr('{{ $json.document_id }}'),
    content_sha256: expr('{{ $json.content_sha256 }}'),
    original_filename: expr('{{ $json.original_filename }}'),
    storage_uri: expr('{{ $json.storage_uri }}'),
    mime_type: expr('{{ $json.mime_type }}'),
    page_count: expr('{{ $json.page_count }}'),
    submitted_by: expr('{{ $json.submitted_by }}'),
    submitted_at: expr('{{ $json.submitted_at }}'),
    department: expr('{{ $json.department }}'),
    stated_type: expr('{{ $json.stated_type }}'),
    resolved_type: expr('{{ $json.resolved_type }}'),
    client_or_vendor_stated: expr('{{ $json.client_or_vendor_stated }}'),
    client_or_vendor_resolved: expr('{{ $json.client_or_vendor_resolved }}'),
    title: expr('{{ $json.title }}'),
    parties: expr('{{ $json.parties }}'),
    counterparty: expr('{{ $json.counterparty }}'),
    document_date: expr('{{ $json.document_date }}'),
    effective_date: expr('{{ $json.effective_date }}'),
    expiry_date: expr('{{ $json.expiry_date }}'),
    currency: expr('{{ $json.currency }}'),
    total_amount: expr('{{ $json.total_amount }}'),
    reference_number: expr('{{ $json.reference_number }}'),
    why_it_exists: expr('{{ $json.why_it_exists }}'),
    what_changed: expr('{{ $json.what_changed }}'),
    page_notes: expr('{{ $json.page_notes }}'),
    status: expr('{{ $json.status }}'),
    supersedes: expr('{{ $json.supersedes }}'),
    superseded_by: expr('{{ $json.superseded_by }}'),
    validation_notes: expr('{{ $json.validation_notes }}'),
    model_route: expr('{{ $json.model_route }}'),
    reviewed_by: expr('{{ $json.reviewed_by }}'),
    reviewed_at: expr('{{ $json.reviewed_at }}'),
    accepted_at: expr('{{ $json.accepted_at }}')
  },
  schema: [
    { id: 'document_id', displayName: 'document_id', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'content_sha256', displayName: 'content_sha256', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'original_filename', displayName: 'original_filename', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'storage_uri', displayName: 'storage_uri', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'mime_type', displayName: 'mime_type', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'page_count', displayName: 'page_count', required: false, defaultMatch: false, display: true, type: 'number', canBeUsedToMatch: true },
    { id: 'submitted_by', displayName: 'submitted_by', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'submitted_at', displayName: 'submitted_at', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'department', displayName: 'department', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'stated_type', displayName: 'stated_type', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'resolved_type', displayName: 'resolved_type', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'client_or_vendor_stated', displayName: 'client_or_vendor_stated', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'client_or_vendor_resolved', displayName: 'client_or_vendor_resolved', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'title', displayName: 'title', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'parties', displayName: 'parties', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'counterparty', displayName: 'counterparty', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'document_date', displayName: 'document_date', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'effective_date', displayName: 'effective_date', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'expiry_date', displayName: 'expiry_date', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'currency', displayName: 'currency', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'total_amount', displayName: 'total_amount', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'reference_number', displayName: 'reference_number', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'why_it_exists', displayName: 'why_it_exists', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'what_changed', displayName: 'what_changed', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'page_notes', displayName: 'page_notes', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'status', displayName: 'status', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'supersedes', displayName: 'supersedes', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'superseded_by', displayName: 'superseded_by', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'validation_notes', displayName: 'validation_notes', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'model_route', displayName: 'model_route', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'reviewed_by', displayName: 'reviewed_by', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'reviewed_at', displayName: 'reviewed_at', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'accepted_at', displayName: 'accepted_at', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true }
  ],
};

const attemptColumns = {
  mappingMode: 'defineBelow',
  value: {
    content_sha256: expr('{{ $json.content_sha256 }}'),
    submitted_by: expr('{{ $json.submitted_by }}'),
    submitted_at: expr('{{ $json.submitted_at }}'),
    department: expr('{{ $json.department }}'),
    note: expr('{{ $json.note }}'),
    existing_document_id: expr('{{ $json.existing_document_id }}')
  },
  schema: [
    { id: 'content_sha256', displayName: 'content_sha256', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'submitted_by', displayName: 'submitted_by', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'submitted_at', displayName: 'submitted_at', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'department', displayName: 'department', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'note', displayName: 'note', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'existing_document_id', displayName: 'existing_document_id', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true }
  ],
};

const threadColumns = {
  mappingMode: 'defineBelow',
  value: {
    document_id: expr('{{ $json.document_id }}'),
    submitted_by: expr('{{ $json.submitted_by }}'),
    body: expr('{{ $json.body }}'),
    created_at: expr('{{ $json.created_at }}')
  },
  schema: [
    { id: 'document_id', displayName: 'document_id', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'submitted_by', displayName: 'submitted_by', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'body', displayName: 'body', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
    { id: 'created_at', displayName: 'created_at', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true }
  ],
};

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

const decideCode = `
const prepItem = $('Prepare submission').first();
const prep = prepItem.json;
const rows = $input.all().map(i => i.json).filter(r => r && r.document_id);
const same = rows.find(r => r.content_sha256 === prep.content_sha256);
function pack(extra) {
  return [{ json: Object.assign({}, prep, extra), binary: prepItem.binary }];
}
if (same) {
  const message = 'This is the exact same file as ' + same.document_id + ', submitted by ' + same.submitted_by + ' on ' + same.submitted_at + '. There are no changes in the file, so I did not create a new record. If you meant an updated contract or invoice, drop the new file.';
  return pack({
    route: 'identical',
    existing_document_id: same.document_id,
    message,
    reply_json: JSON.stringify({ message, status: 'identical', document_id: same.document_id }),
  });
}
const allowed = ['invoice', 'contract', 'brief', 'other'];
if (!allowed.includes(prep.stated_type) || !prep.department) {
  const message = 'I have the file, and it is not on the record yet. I still need the document type (invoice, contract, brief, or other) and the department. I will not guess either of those.';
  return pack({
    route: 'ask',
    message,
    reply_json: JSON.stringify({ message, status: 'needs_details', document_id: '' }),
  });
}
if (prep.kind !== 'pdf' && prep.kind !== 'image') {
  const message = 'I can read a PDF, PNG, or JPEG. This file is none of those, so I stopped before extraction.';
  return pack({
    route: 'ask',
    message,
    reply_json: JSON.stringify({ message, status: 'needs_details', document_id: '' }),
  });
}
return pack({ route: prep.kind, message: '', reply_json: '' });
`;

const promptIntro = 'You extract fields from one document. Return one JSON object and nothing else. Do not invent a value. If a field is not on the page, use an empty string. Do not choose between two different totals, dates, or party names. Put each conflict in conflicts. Pages may be marked --- PAGE n ---. If a page number is missing or that page has no words, list it in unreadable_pages. type_guess must be invoice, contract, brief, or other. JSON keys: title, parties, counterparty, document_date, effective_date, expiry_date, currency, total_amount, reference_number, why_it_exists, type_guess, unreadable_pages, conflicts. conflicts items look like {"field":"total_amount","values":["100.00","180.00"]}. Dates as YYYY-MM-DD when the document states one. Amounts as digits and a decimal point, no currency symbol. On an invoice, counterparty is the supplier, not the customer.';

const buildTextCode = `
const prep = $('Prepare submission').first().json;
const extracted = $input.first().json || {};
const pageText = String(prep.prepared_text || extracted.text || '');
const reportedPages = Number(prep.prepared_pages || extracted.numpages || extracted.pages || prep.pdf_pages || 0) || 0;
const promptIntro = "You extract fields from one document. Return one JSON object and nothing else. Do not invent a value. If a field is not on the page, use an empty string. Do not choose between two different totals, dates, or party names. Put each conflict in conflicts. Pages may be marked --- PAGE n ---. If a page number is missing or that page has no words, list it in unreadable_pages. type_guess must be invoice, contract, brief, or other. JSON keys: title, parties, counterparty, document_date, effective_date, expiry_date, currency, total_amount, reference_number, why_it_exists, type_guess, unreadable_pages, conflicts. conflicts items look like {\"field\":\"total_amount\",\"values\":[\"100.00\",\"180.00\"]}. Dates as YYYY-MM-DD when the document states one. Amounts as digits and a decimal point, no currency symbol. On an invoice, counterparty is the supplier, not the customer.";
const llm_body = {
  model: 'google/gemini-2.5-flash',
  temperature: 0,
  messages: [{
    role: 'user',
    content: promptIntro + '\\nStated type: ' + prep.stated_type + '\\nReported page count: ' + String(reportedPages || 'unknown') + '\\n\\n' + pageText,
  }],
};
return [{ json: Object.assign({}, prep, { page_text: pageText, reported_pages: reportedPages, llm_body }) }];
`;

const buildImageCode = `
const prep = $('Decide route').first().json;
const promptIntro = "You extract fields from one document. Return one JSON object and nothing else. Do not invent a value. If a field is not on the page, use an empty string. Do not choose between two different totals, dates, or party names. Put each conflict in conflicts. Pages may be marked --- PAGE n ---. If a page number is missing or that page has no words, list it in unreadable_pages. type_guess must be invoice, contract, brief, or other. JSON keys: title, parties, counterparty, document_date, effective_date, expiry_date, currency, total_amount, reference_number, why_it_exists, type_guess, unreadable_pages, conflicts. conflicts items look like {\"field\":\"total_amount\",\"values\":[\"100.00\",\"180.00\"]}. Dates as YYYY-MM-DD when the document states one. Amounts as digits and a decimal point, no currency symbol. On an invoice, counterparty is the supplier, not the customer.";
const llm_body = {
  model: 'google/gemini-2.5-flash',
  temperature: 0,
  messages: [{
    role: 'user',
    content: [
      { type: 'text', text: promptIntro + '\\nStated type: ' + prep.stated_type + '\\nThis is a single image, so it is page 1. If you cannot read it, unreadable_pages must be [1].' },
      { type: 'image_url', image_url: { url: 'data:' + prep.mime_type + ';base64,' + prep.image_b64 } },
    ],
  }],
};
return [{ json: Object.assign({}, prep, { page_text: '', reported_pages: 1, llm_body }) }];
`;

const readTextCode = `
let built = null;
try { built = $('Build text request').first().json; } catch (e) { built = null; }
const res = $input.first().json || {};
const content = res.choices && res.choices[0] && res.choices[0].message ? res.choices[0].message.content : '';
const modelError = res.error ? JSON.stringify(res.error) : '';
return [{ json: Object.assign({}, built || {}, { model_raw: content || '', model_error: modelError }) }];
`;

const readImageCode = `
let built = null;
try { built = $('Build image request').first().json; } catch (e) { built = null; }
const res = $input.first().json || {};
const content = res.choices && res.choices[0] && res.choices[0].message ? res.choices[0].message.content : '';
const modelError = res.error ? JSON.stringify(res.error) : '';
return [{ json: Object.assign({}, built || {}, { model_raw: content || '', model_error: modelError }) }];
`;

const judgeCode = `
const built = $input.first().json || {};
const rows = $('Load records').all().map(i => i.json).filter(r => r && r.document_id);

function parseModel(raw) {
  if (!raw) return null;
  const fence = String.fromCharCode(96, 96, 96);
  let t = String(raw).trim();
  if (t.indexOf(fence) === 0) {
    t = t.slice(fence.length);
    if (t.slice(0, 4).toLowerCase() === 'json') t = t.slice(4);
    const end = t.lastIndexOf(fence);
    if (end !== -1) t = t.slice(0, end);
    t = t.trim();
  }
  try { return JSON.parse(t); } catch (e) {
    const start = t.indexOf('{');
    const end = t.lastIndexOf('}');
    if (start === -1 || end === -1) return null;
    try { return JSON.parse(t.slice(start, end + 1)); } catch (e2) { return null; }
  }
}
function money(v) {
  if (v === null || v === undefined) return '';
  const s = String(v).trim();
  if (!s || s.indexOf('-') !== -1) return '';
  let out = '';
  let seenDot = false;
  for (let i = 0; i < s.length; i++) {
    const c = s.charAt(i);
    if (c >= '0' && c <= '9') out += c;
    else if (c === '.' && !seenDot) { seenDot = true; out += c; }
  }
  if (!out || out === '.') return '';
  const num = Number(out);
  return Number.isFinite(num) ? num.toFixed(2) : '';
}
function dateField(v) {
  const s = clean(v);
  if (s.length !== 10 || s.charAt(4) !== '-' || s.charAt(7) !== '-') return '';
  const y = Number(s.slice(0, 4));
  const m = Number(s.slice(5, 7));
  const d = Number(s.slice(8, 10));
  if (!y || m < 1 || m > 12 || d < 1 || d > 31) return '';
  const dt = new Date(Date.UTC(y, m - 1, d));
  if (dt.getUTCFullYear() !== y || dt.getUTCMonth() !== m - 1 || dt.getUTCDate() !== d) return '';
  return s;
}
function clean(v) {
  if (Array.isArray(v)) {
    const parts = [];
    for (let i = 0; i < v.length; i++) {
      const bit = String(v[i] || '').trim();
      if (bit) parts.push(bit);
    }
    return parts.join(', ');
  }
  return String(v || '').trim();
}

const model = parseModel(built.model_raw) || {};
const text = String(built.page_text || '');
const reported = Number(built.reported_pages || 0) || 0;
const indexes = [];
const re = /---\s*PAGE\s+(\d+)\s*---/gi;
let match;
while ((match = re.exec(text))) indexes.push({ page: Number(match[1]), index: match.index, len: match[0].length });
const missing = [];
let couldNotSplit = false;
const pageCount = reported || Number(built.pdf_pages || 0) || 1;
let maxPage = pageCount;
if (indexes.length) {
  maxPage = Math.max(pageCount, ...indexes.map(p => p.page));
  for (let p = 1; p <= maxPage; p++) {
    const pos = indexes.findIndex(i => i.page === p);
    if (pos === -1) { missing.push(p); continue; }
    const start = indexes[pos].index + indexes[pos].len;
    const end = pos + 1 < indexes.length ? indexes[pos + 1].index : text.length;
    if (text.slice(start, end).replace(/\s/g, '').length < 20) missing.push(p);
  }
} else if (pageCount > 1) {
  couldNotSplit = true;
  maxPage = pageCount;
  for (let p = 1; p <= pageCount; p++) missing.push(p);
} else if (text.replace(/\s/g, '').length < 20) {
  missing.push(1);
}
const modelMissing = Array.isArray(model.unreadable_pages) ? model.unreadable_pages.map(Number).filter(n => n > 0) : [];
for (const p of modelMissing) if (!missing.includes(p)) missing.push(p);

const fields = {
  title: clean(model.title),
  parties: clean(model.parties),
  counterparty: clean(model.counterparty),
  document_date: dateField(model.document_date),
  effective_date: dateField(model.effective_date),
  expiry_date: dateField(model.expiry_date),
  currency: clean(model.currency).toUpperCase(),
  total_amount: money(model.total_amount),
  reference_number: clean(model.reference_number),
  why_it_exists: clean(model.why_it_exists),
};
const problems = [];
if (built.model_error || !built.model_raw) problems.push('The extraction did not return a usable result, so nothing was filled in.');
if (!model || !built.model_raw) problems.push('I could not read a structured result from the model.');
const conflicts = Array.isArray(model.conflicts) ? model.conflicts : [];
for (const c of conflicts) {
  const vals = (c.values || []).map(v => clean(v)).filter(Boolean);
  if (vals.length > 1) problems.push('The file gives more than one ' + clean(c.field || 'value') + ': ' + vals.join(' and ') + '. I did not pick one.');
}
const required = {
  invoice: [['counterparty', 'the supplier'], ['reference_number', 'the invoice number'], ['currency', 'the currency'], ['total_amount', 'the total'], ['document_date', 'the invoice date']],
  contract: [['parties', 'the parties'], ['effective_date', 'the effective date']],
  brief: [['title', 'the title'], ['why_it_exists', 'why the brief exists']],
  other: [['title', 'the title']],
};
const typeGuess = clean(model.type_guess).toLowerCase();
if (built.stated_type !== 'other' && typeGuess && typeGuess !== built.stated_type && ['invoice','contract','brief','other'].includes(typeGuess)) {
  problems.push('You marked this as a ' + built.stated_type + ', and the text looks like a ' + typeGuess + '. I did not relabel it.');
}
if (missing.length === 0 && !built.model_error) {
  for (const [key, label] of (required[built.stated_type] || [])) {
    if (!fields[key]) problems.push('The ' + built.stated_type + ' is missing ' + label + '.');
  }
}
const pageNotes = couldNotSplit
  ? 'This file has ' + maxPage + ' pages and I could not separate them, so I did not accept it.'
  : missing.map(p => 'Page ' + p + ' could not be read because that page has no text. I did not guess what was on it.').join(' ');
const heldBecausePage = missing.length > 0;
let status = 'accepted';
if (built.model_error || problems.length || heldBecausePage) status = 'held';

let supersedes = '';
let whatChanged = '';
if (status === 'accepted' && fields.reference_number) {
  const matches = rows.filter(function (r) {
    if (r.status !== 'accepted' || r.superseded_by) return false;
    if (clean(r.reference_number) !== fields.reference_number) return false;
    if (clean(r.resolved_type || r.stated_type).toLowerCase() !== built.stated_type) return false;
    if (clean(r.department) !== clean(built.department)) return false;
    const oldParty = clean(r.client_or_vendor_stated).toLowerCase();
    const newParty = clean(built.client_or_vendor_stated).toLowerCase();
    if (oldParty && newParty && oldParty !== newParty) return false;
    return r.content_sha256 !== built.content_sha256;
  });
  if (matches.length > 1) {
    status = 'held';
    problems.push('This reference matches more than one current record (' + matches.map(r => r.document_id).join(', ') + '). I did not choose which one it replaces.');
  } else if (matches.length === 1) {
    const old = matches[0];
    status = 'awaiting_confirm';
    supersedes = old.document_id;
    const diffs = [];
    const labels = { total_amount: 'the total', currency: 'the currency', document_date: 'the document date', effective_date: 'the effective date', parties: 'the parties', counterparty: 'the other party' };
    for (const key of Object.keys(labels)) {
      const before = key === 'total_amount' ? money(old[key]) : clean(old[key]);
      const after = fields[key];
      if (before !== after && (before || after)) diffs.push(labels[key] + ' was ' + (before || 'blank') + ' and this file says ' + (after || 'blank'));
    }
    whatChanged = diffs.join('. ');
    problems.length = 0;
  }
}

const documentId = 'DOC-' + built.content_sha256.slice(0, 8) + '-' + Date.now().toString(36);
const clientPart = built.client_or_vendor_stated || '_unassigned';
const lines = [];
if (status === 'awaiting_confirm') {
  lines.push('This looks like the same ' + built.stated_type + ' as ' + supersedes + ', but the file is different.');
  if (whatChanged) lines.push(whatChanged + '.');
  lines.push('Should this replace the one on file? Yes means the new one becomes current and the old one stays in History. No means this file stays held and the current record is unchanged.');
} else if (status === 'accepted') {
  lines.push('This ' + built.stated_type + ' is on the record as ' + documentId + '.');
  if (fields.title) lines.push('It is ' + fields.title + '.');
  if (fields.counterparty || built.client_or_vendor_stated) lines.push('It is for ' + (fields.counterparty || built.client_or_vendor_stated) + '.');
  if (fields.document_date || fields.effective_date) lines.push('The date on it is ' + (fields.document_date || fields.effective_date) + '.');
  if (fields.why_it_exists) lines.push(fields.why_it_exists);
  if (fields.total_amount) lines.push('The total is ' + fields.total_amount + (fields.currency ? ' ' + fields.currency : '') + '.');
} else {
  lines.push('This is not on the accepted record.');
  if (pageNotes) lines.push(pageNotes);
  if (missing.length) lines.push('The other pages were summarized. Someone needs to look at page ' + missing.join(' and page ') + '.');
  for (const p of problems) if (lines.join(' ').indexOf(p) === -1) lines.push(p);
  if (!pageNotes && !problems.length) lines.push('Something needed a person, and I did not write an accepted row.');
}
const message = lines.join(' ');
const now = new Date().toISOString();
return [{
  json: {
    document_id: documentId,
    content_sha256: built.content_sha256,
    original_filename: built.original_filename,
    storage_uri: built.storage_uri || (built.department + '/' + clientPart + '/' + documentId + '/original'),
    mime_type: built.mime_type,
    page_count: maxPage || 1,
    submitted_by: built.submitted_by,
    submitted_at: built.submitted_at,
    department: built.department,
    stated_type: built.stated_type,
    resolved_type: status === 'accepted' ? built.stated_type : '',
    client_or_vendor_stated: built.client_or_vendor_stated,
    client_or_vendor_resolved: status === 'accepted' ? (fields.counterparty || built.client_or_vendor_stated) : '',
    title: fields.title,
    parties: fields.parties,
    counterparty: fields.counterparty,
    document_date: fields.document_date,
    effective_date: fields.effective_date,
    expiry_date: fields.expiry_date,
    currency: fields.currency,
    total_amount: fields.total_amount,
    reference_number: fields.reference_number,
    why_it_exists: fields.why_it_exists,
    what_changed: whatChanged,
    page_notes: pageNotes,
    status,
    supersedes,
    superseded_by: '',
    validation_notes: problems.join(' '),
    model_route: 'google/gemini-2.5-flash',
    reviewed_by: '',
    reviewed_at: '',
    accepted_at: status === 'accepted' ? now : '',
    body: message,
    created_at: now,
    reply_json: JSON.stringify({ message, status, document_id: documentId, supersedes }),
  },
}];
`;

const restoreShortCode = `
const d = $('Decide route').first().json;
return [{
  json: {
    document_id: d.existing_document_id || '',
    submitted_by: d.submitted_by || '',
    body: d.message || '',
    created_at: new Date().toISOString(),
    reply_json: d.reply_json || JSON.stringify({ message: d.message || 'I could not finish that.', status: 'failed', document_id: '' }),
  },
}];
`;

const restoreJudgeCode = `
const d = $('Judge outcome').first().json;
return [{
  json: {
    document_id: d.document_id || '',
    submitted_by: d.submitted_by || '',
    body: d.body || '',
    created_at: d.created_at || new Date().toISOString(),
    reply_json: d.reply_json,
  },
}];
`;

const echoAfterWrite = `
return [{ json: $('Conversation line').first().json }];
`;

const submitHook = trigger({
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
    credentials: { httpHeaderAuth: newCredential('DocIntel webhook', 'fdad2f81-1ffa-43b4-8852-cea41ac4f091') },
    output: [{ json: { body: { stated_type: 'invoice', department: 'finance', client: 'Northwind', submitted_by: 'Andre' } } }],
  },
});

const prepare = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Prepare submission',
    parameters: { mode: 'runOnceForAllItems', language: 'javaScript', jsCode: prepareCode },
    output: [{ json: { content_sha256: 'abc', kind: 'pdf', stated_type: 'invoice', department: 'finance' } }],
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
      filters: { conditions: [{ keyName: 'document_id', condition: 'isNotEmpty' }] },
      returnAll: true,
    },
    output: [{ json: { document_id: '', content_sha256: '', status: '' } }],
  },
});

const decide = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Decide route',
    parameters: { mode: 'runOnceForAllItems', language: 'javaScript', jsCode: decideCode },
    output: [{ json: { route: 'pdf', message: '', reply_json: '' } }],
  },
});

const route = switchCase({
  version: 3.4,
  config: {
    name: 'Route submission',
    parameters: {
      mode: 'rules',
      rules: {
        values: [
          { outputKey: 'identical', conditions: { options: { caseSensitive: true, leftValue: '', typeValidation: 'strict' }, conditions: [{ leftValue: expr('{{ $json.route }}'), operator: { type: 'string', operation: 'equals' }, rightValue: 'identical' }], combinator: 'and' } },
          { outputKey: 'ask', conditions: { options: { caseSensitive: true, leftValue: '', typeValidation: 'strict' }, conditions: [{ leftValue: expr('{{ $json.route }}'), operator: { type: 'string', operation: 'equals' }, rightValue: 'ask' }], combinator: 'and' } },
          { outputKey: 'pdf', conditions: { options: { caseSensitive: true, leftValue: '', typeValidation: 'strict' }, conditions: [{ leftValue: expr('{{ $json.route }}'), operator: { type: 'string', operation: 'equals' }, rightValue: 'pdf' }], combinator: 'and' } },
          { outputKey: 'image', conditions: { options: { caseSensitive: true, leftValue: '', typeValidation: 'strict' }, conditions: [{ leftValue: expr('{{ $json.route }}'), operator: { type: 'string', operation: 'equals' }, rightValue: 'image' }], combinator: 'and' } },
        ],
      },
      options: { fallbackOutput: 'extra', renameFallbackOutput: 'Fallback' },
    },
    output: [{ json: { route: 'pdf' } }],
  },
});

const extractPdf = node({
  type: 'n8n-nodes-base.extractFromFile',
  version: 1.1,
  config: {
    name: 'Read PDF text',
    parameters: { operation: 'pdf', binaryPropertyName: 'data' },
    output: [{ json: { text: '--- PAGE 1 --- invoice', numpages: 1 } }],
  },
});

const buildText = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Build text request',
    parameters: { mode: 'runOnceForAllItems', language: 'javaScript', jsCode: buildTextCode },
    output: [{ json: { llm_body: { model: 'google/gemini-2.5-flash' }, page_text: 'text', reported_pages: 1 } }],
  },
});

const buildImage = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Build image request',
    parameters: { mode: 'runOnceForAllItems', language: 'javaScript', jsCode: buildImageCode },
    output: [{ json: { llm_body: { model: 'google/gemini-2.5-flash' }, page_text: '', reported_pages: 1 } }],
  },
});

const httpText = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.4,
  config: {
    name: 'Extract fields from text',
    retryOnFail: true,
    maxTries: 4,
    waitBetweenTries: 3000,
    parameters: {
      method: 'POST',
      url: 'https://openrouter.ai/api/v1/chat/completions',
      authentication: 'genericCredentialType',
      genericAuthType: 'httpBearerAuth',
      sendBody: true,
      contentType: 'json',
      specifyBody: 'json',
      jsonBody: expr('{{ JSON.stringify($json.llm_body) }}'),
      options: {},
    },
    credentials: { httpBearerAuth: newCredential('OpenRouter') },
    output: [{ json: { choices: [{ message: { content: '{}' } }] } }],
  },
});

const httpImage = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.4,
  config: {
    name: 'Extract fields from image',
    retryOnFail: true,
    maxTries: 4,
    waitBetweenTries: 3000,
    parameters: {
      method: 'POST',
      url: 'https://openrouter.ai/api/v1/chat/completions',
      authentication: 'genericCredentialType',
      genericAuthType: 'httpBearerAuth',
      sendBody: true,
      contentType: 'json',
      specifyBody: 'json',
      jsonBody: expr('{{ JSON.stringify($json.llm_body) }}'),
      options: {},
    },
    credentials: { httpBearerAuth: newCredential('OpenRouter') },
    output: [{ json: { choices: [{ message: { content: '{}' } }] } }],
  },
});

const readText = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Read text model result',
    parameters: { mode: 'runOnceForAllItems', language: 'javaScript', jsCode: readTextCode },
    output: [{ json: { model_raw: '{}', model_error: '', page_text: '', content_sha256: 'abc' } }],
  },
});

const readImage = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Read image model result',
    parameters: { mode: 'runOnceForAllItems', language: 'javaScript', jsCode: readImageCode },
    output: [{ json: { model_raw: '{}', model_error: '', page_text: '', content_sha256: 'abc' } }],
  },
});

const judge = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Judge outcome',
    parameters: { mode: 'runOnceForAllItems', language: 'javaScript', jsCode: judgeCode },
    output: [{ json: { document_id: 'DOC-1', status: 'held', body: 'Needs a person', reply_json: '{}', page_count: 1 } }],
  },
});

const saveRecord = node({
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
});

const restoreShort = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Conversation from decision',
    parameters: { mode: 'runOnceForAllItems', language: 'javaScript', jsCode: restoreShortCode },
    output: [{ json: { body: 'Already on file', reply_json: '{}', document_id: 'DOC-1', submitted_by: 'Andre', created_at: '2026-01-01T00:00:00.000Z' } }],
  },
});

const restoreJudge = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Conversation from judgement',
    parameters: { mode: 'runOnceForAllItems', language: 'javaScript', jsCode: restoreJudgeCode },
    output: [{ json: { body: 'On the record', reply_json: '{}', document_id: 'DOC-1', submitted_by: 'Andre', created_at: '2026-01-01T00:00:00.000Z' } }],
  },
});

const conversation = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Conversation line',
    parameters: { mode: 'runOnceForAllItems', language: 'javaScript', jsCode: 'return $input.all();' },
    output: [{ json: { body: 'message', reply_json: '{}', document_id: 'DOC-1', submitted_by: 'Andre', created_at: '2026-01-01T00:00:00.000Z', content_sha256: 'abc', note: 'message', existing_document_id: '', department: 'finance', submitted_at: '2026-01-01T00:00:00.000Z' } }],
  },
});

const logAttempt = node({
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
      columns: threadColumns,
    },
    output: [{ json: { id: 1 } }],
  },
});

const echo = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Keep the reply',
    parameters: { mode: 'runOnceForAllItems', language: 'javaScript', jsCode: echoAfterWrite },
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

const attemptShape = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Shape attempt',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: `
const d = $('Decide route').first().json;
return [{ json: {
  content_sha256: d.content_sha256,
  submitted_by: d.submitted_by,
  submitted_at: d.submitted_at,
  department: d.department || '',
  note: d.message,
  existing_document_id: d.existing_document_id,
}}];
`,
    },
    output: [{ json: { content_sha256: 'abc', submitted_by: 'Andre', submitted_at: '2026-01-01', department: 'finance', note: 'same file', existing_document_id: 'DOC-1' } }],
  },
});

export default workflow('docintel-submit', 'DocIntel — Submit')
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
  .to(reply);
