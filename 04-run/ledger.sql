CREATE TABLE documents (
  document_id text PRIMARY KEY,
  content_sha256 text NOT NULL UNIQUE,
  original_filename text NOT NULL DEFAULT '',
  storage_key text NOT NULL DEFAULT '',
  mime_type text NOT NULL DEFAULT '',
  page_count integer,
  submitted_by text NOT NULL DEFAULT '',
  submitted_at text NOT NULL DEFAULT '',
  department text NOT NULL DEFAULT '',
  stated_type text NOT NULL DEFAULT '',
  resolved_type text NOT NULL DEFAULT '',
  client_or_vendor_stated text NOT NULL DEFAULT '',
  client_or_vendor_resolved text NOT NULL DEFAULT '',
  title text NOT NULL DEFAULT '',
  parties text NOT NULL DEFAULT '',
  counterparty text NOT NULL DEFAULT '',
  document_date text NOT NULL DEFAULT '',
  effective_date text NOT NULL DEFAULT '',
  expiry_date text NOT NULL DEFAULT '',
  currency text NOT NULL DEFAULT '',
  total_amount text NOT NULL DEFAULT '',
  reference_number text NOT NULL DEFAULT '',
  why_it_exists text NOT NULL DEFAULT '',
  what_changed text NOT NULL DEFAULT '',
  page_notes text NOT NULL DEFAULT '',
  status text NOT NULL,
  supersedes text NOT NULL DEFAULT '',
  superseded_by text NOT NULL DEFAULT '',
  validation_notes text NOT NULL DEFAULT '',
  model_route text NOT NULL DEFAULT '',
  reviewed_by text NOT NULL DEFAULT '',
  reviewed_at text NOT NULL DEFAULT '',
  accepted_at text NOT NULL DEFAULT '',
  field_evidence text NOT NULL DEFAULT '',
  source text NOT NULL DEFAULT 'live'
);

CREATE TABLE thread (
  id bigserial PRIMARY KEY,
  document_id text NOT NULL DEFAULT '',
  submitted_by text NOT NULL DEFAULT '',
  body text NOT NULL,
  created_at text NOT NULL
);

CREATE TABLE attempts (
  id bigserial PRIMARY KEY,
  content_sha256 text NOT NULL DEFAULT '',
  submitted_by text NOT NULL DEFAULT '',
  submitted_at text NOT NULL DEFAULT '',
  department text NOT NULL DEFAULT '',
  note text NOT NULL DEFAULT '',
  existing_document_id text NOT NULL DEFAULT ''
);

CREATE OR REPLACE FUNCTION intake_document(payload jsonb)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
  existing documents%ROWTYPE;
  new_id text;
  pages integer;
BEGIN
  IF COALESCE(payload->>'content_sha256', '') = '' THEN
    RAISE EXCEPTION 'intake is missing a file hash';
  END IF;
  -- The second upload of these same bytes waits here, then sees the row the first upload committed.
  PERFORM pg_advisory_xact_lock(hashtextextended(payload->>'content_sha256', 0));

  SELECT * INTO existing FROM documents WHERE content_sha256 = payload->>'content_sha256';
  IF FOUND THEN
    RETURN jsonb_build_object(
      'inserted', false,
      'document_id', existing.document_id,
      'submitted_by', existing.submitted_by,
      'submitted_at', existing.submitted_at,
      'status', existing.status
    );
  END IF;

  new_id := payload->>'document_id';
  IF new_id IS NULL OR new_id = '' THEN
    RAISE EXCEPTION 'intake is missing a document id';
  END IF;
  pages := NULLIF(payload->>'page_count', '')::int;

  INSERT INTO documents (
    document_id, content_sha256, original_filename, storage_key, mime_type,
    page_count, submitted_by, submitted_at, department, stated_type,
    client_or_vendor_stated, status, source
  ) VALUES (
    new_id,
    payload->>'content_sha256',
    COALESCE(payload->>'original_filename', ''),
    COALESCE(payload->>'storage_key', ''),
    COALESCE(payload->>'mime_type', ''),
    pages,
    COALESCE(payload->>'submitted_by', ''),
    COALESCE(payload->>'submitted_at', ''),
    COALESCE(payload->>'department', ''),
    COALESCE(payload->>'stated_type', ''),
    COALESCE(payload->>'client_or_vendor_stated', ''),
    'received',
    CASE WHEN payload->>'source' = 'backfill' THEN 'backfill' ELSE 'live' END
  );
  RETURN jsonb_build_object('inserted', true, 'document_id', new_id, 'status', 'received');
EXCEPTION
  WHEN unique_violation THEN
    SELECT * INTO existing FROM documents WHERE content_sha256 = payload->>'content_sha256';
    RETURN jsonb_build_object(
      'inserted', false,
      'document_id', existing.document_id,
      'submitted_by', existing.submitted_by,
      'submitted_at', existing.submitted_at,
      'status', existing.status
    );
END;
$$;

CREATE OR REPLACE FUNCTION apply_outcome(payload jsonb)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
  updated_id text;
  current_status text;
BEGIN
  SELECT status INTO current_status FROM documents WHERE document_id = payload->>'document_id' FOR UPDATE;
  IF current_status IS NULL THEN
    RAISE EXCEPTION 'document % was not waiting to be written', payload->>'document_id';
  END IF;
  IF current_status NOT IN ('received', 'processing') THEN
    RETURN jsonb_build_object('document_id', payload->>'document_id', 'status', current_status, 'skipped', true);
  END IF;

  UPDATE documents SET
    original_filename = COALESCE(NULLIF(payload->>'original_filename', ''), original_filename),
    storage_key = COALESCE(NULLIF(payload->>'storage_uri', ''), NULLIF(payload->>'storage_key', ''), storage_key),
    mime_type = COALESCE(NULLIF(payload->>'mime_type', ''), mime_type),
    page_count = COALESCE(NULLIF(payload->>'page_count', '')::int, page_count),
    department = COALESCE(NULLIF(payload->>'department', ''), department),
    stated_type = COALESCE(NULLIF(payload->>'stated_type', ''), stated_type),
    resolved_type = COALESCE(payload->>'resolved_type', ''),
    client_or_vendor_stated = COALESCE(NULLIF(payload->>'client_or_vendor_stated', ''), client_or_vendor_stated),
    client_or_vendor_resolved = COALESCE(payload->>'client_or_vendor_resolved', ''),
    title = COALESCE(payload->>'title', ''),
    parties = COALESCE(payload->>'parties', ''),
    counterparty = COALESCE(payload->>'counterparty', ''),
    document_date = COALESCE(payload->>'document_date', ''),
    effective_date = COALESCE(payload->>'effective_date', ''),
    expiry_date = COALESCE(payload->>'expiry_date', ''),
    currency = COALESCE(payload->>'currency', ''),
    total_amount = COALESCE(payload->>'total_amount', ''),
    reference_number = COALESCE(payload->>'reference_number', ''),
    why_it_exists = COALESCE(payload->>'why_it_exists', ''),
    what_changed = COALESCE(payload->>'what_changed', ''),
    page_notes = COALESCE(payload->>'page_notes', ''),
    status = payload->>'status',
    supersedes = COALESCE(payload->>'supersedes', ''),
    superseded_by = COALESCE(payload->>'superseded_by', ''),
    validation_notes = COALESCE(payload->>'validation_notes', ''),
    model_route = COALESCE(payload->>'model_route', ''),
    reviewed_by = COALESCE(payload->>'reviewed_by', ''),
    reviewed_at = COALESCE(payload->>'reviewed_at', ''),
    accepted_at = COALESCE(payload->>'accepted_at', ''),
    field_evidence = COALESCE(NULLIF(payload->>'field_evidence', ''), field_evidence)
  WHERE document_id = payload->>'document_id'
    AND status IN ('received', 'processing')
  RETURNING document_id INTO updated_id;

  IF updated_id IS NULL THEN
    RETURN jsonb_build_object('document_id', payload->>'document_id', 'status', current_status, 'skipped', true);
  END IF;
  RETURN jsonb_build_object('document_id', updated_id, 'status', payload->>'status');
END;
$$;

CREATE OR REPLACE FUNCTION confirm_replacement(new_id text, old_id text, reviewer text)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
  new_status text;
  old_status text;
  stamp text;
BEGIN
  IF new_id IS NULL OR old_id IS NULL OR new_id = '' OR old_id = '' OR new_id = old_id THEN
    RAISE EXCEPTION 'replacement needs two different document ids';
  END IF;

  PERFORM 1 FROM documents WHERE document_id IN (new_id, old_id) ORDER BY document_id FOR UPDATE;

  SELECT status INTO new_status FROM documents WHERE document_id = new_id;
  SELECT status INTO old_status FROM documents WHERE document_id = old_id;
  IF new_status IS DISTINCT FROM 'awaiting_confirm' THEN
    RAISE EXCEPTION 'new document % is %, not awaiting confirmation', new_id, COALESCE(new_status, 'missing');
  END IF;
  IF old_status IS DISTINCT FROM 'accepted' THEN
    RAISE EXCEPTION 'old document % is %, not the current record', old_id, COALESCE(old_status, 'missing');
  END IF;

  stamp := to_char(clock_timestamp() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"');

  UPDATE documents
  SET status = 'superseded', superseded_by = new_id
  WHERE document_id = old_id AND status = 'accepted';
  IF NOT FOUND THEN
    RAISE EXCEPTION 'could not supersede %', old_id;
  END IF;

  UPDATE documents
  SET status = 'accepted',
      accepted_at = stamp,
      reviewed_at = stamp,
      reviewed_by = COALESCE(reviewer, '')
  WHERE document_id = new_id AND status = 'awaiting_confirm';
  IF NOT FOUND THEN
    RAISE EXCEPTION 'could not accept %', new_id;
  END IF;

  RETURN (
    SELECT jsonb_agg(jsonb_build_object('document_id', document_id, 'status', status, 'superseded_by', superseded_by) ORDER BY document_id)
    FROM documents
    WHERE document_id IN (new_id, old_id)
  );
END;
$$;

CREATE OR REPLACE FUNCTION hold_document(target_id text, reviewer text, note text)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
  stamp text;
  updated_id text;
BEGIN
  stamp := to_char(clock_timestamp() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"');
  UPDATE documents
  SET status = 'held',
      validation_notes = COALESCE(note, validation_notes),
      reviewed_by = COALESCE(reviewer, ''),
      reviewed_at = stamp,
      accepted_at = ''
  WHERE document_id = target_id AND status = 'awaiting_confirm'
  RETURNING document_id INTO updated_id;
  IF updated_id IS NULL THEN
    RAISE EXCEPTION 'document % is not waiting for a yes or no', target_id;
  END IF;
  RETURN jsonb_build_object('document_id', updated_id, 'status', 'held');
END;
$$;

CREATE OR REPLACE FUNCTION log_thread(payload jsonb)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
  new_id bigint;
BEGIN
  INSERT INTO thread (document_id, submitted_by, body, created_at)
  VALUES (
    COALESCE(payload->>'document_id', ''),
    COALESCE(payload->>'submitted_by', ''),
    COALESCE(payload->>'body', ''),
    COALESCE(NULLIF(payload->>'created_at', ''), to_char(clock_timestamp() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"'))
  )
  RETURNING id INTO new_id;
  RETURN jsonb_build_object('id', new_id);
END;
$$;

CREATE OR REPLACE FUNCTION confirm_replacement_payload(payload jsonb)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN confirm_replacement(payload->>'document_id', payload->>'old_id', payload->>'submitted_by');
END;
$$;

CREATE OR REPLACE FUNCTION hold_document_payload(payload jsonb)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN hold_document(payload->>'document_id', payload->>'submitted_by', COALESCE(payload->>'note', ''));
END;
$$;

CREATE OR REPLACE FUNCTION log_attempt(payload jsonb)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
  new_id bigint;
BEGIN
  INSERT INTO attempts (content_sha256, submitted_by, submitted_at, department, note, existing_document_id)
  VALUES (
    COALESCE(payload->>'content_sha256', ''),
    COALESCE(payload->>'submitted_by', ''),
    COALESCE(payload->>'submitted_at', ''),
    COALESCE(payload->>'department', ''),
    COALESCE(payload->>'note', ''),
    COALESCE(payload->>'existing_document_id', '')
  )
  RETURNING id INTO new_id;
  RETURN jsonb_build_object('id', new_id);
END;
$$;

CREATE OR REPLACE FUNCTION apply_review(payload jsonb)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
  updated_id text;
  next_status text;
  stamp text;
BEGIN
  next_status := payload->>'status';
  IF next_status IS NULL OR next_status NOT IN ('held', 'accepted', 'awaiting_confirm') THEN
    RAISE EXCEPTION 'review cannot set status %', COALESCE(next_status, 'missing');
  END IF;
  stamp := to_char(clock_timestamp() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"');
  UPDATE documents SET
    title = COALESCE(payload->>'title', title),
    parties = COALESCE(payload->>'parties', parties),
    counterparty = COALESCE(payload->>'counterparty', counterparty),
    document_date = COALESCE(payload->>'document_date', document_date),
    effective_date = COALESCE(payload->>'effective_date', effective_date),
    expiry_date = COALESCE(payload->>'expiry_date', expiry_date),
    currency = COALESCE(payload->>'currency', currency),
    total_amount = COALESCE(payload->>'total_amount', total_amount),
    reference_number = COALESCE(payload->>'reference_number', reference_number),
    why_it_exists = COALESCE(payload->>'why_it_exists', why_it_exists),
    page_notes = COALESCE(payload->>'page_notes', page_notes),
    validation_notes = COALESCE(payload->>'validation_notes', ''),
    field_evidence = COALESCE(NULLIF(payload->>'field_evidence', ''), field_evidence),
    status = next_status,
    supersedes = COALESCE(payload->>'supersedes', supersedes),
    reviewed_by = COALESCE(payload->>'reviewed_by', ''),
    reviewed_at = stamp,
    accepted_at = CASE WHEN next_status = 'accepted' THEN stamp ELSE '' END
  WHERE document_id = payload->>'document_id'
    AND status = 'held'
  RETURNING document_id INTO updated_id;
  IF updated_id IS NULL THEN
    RAISE EXCEPTION 'document % is not held for review', payload->>'document_id';
  END IF;
  RETURN jsonb_build_object('document_id', updated_id, 'status', next_status);
END;
$$;

CREATE TABLE IF NOT EXISTS model_usage (
  id bigserial PRIMARY KEY,
  document_id text NOT NULL DEFAULT '',
  model text NOT NULL DEFAULT '',
  prompt_tokens integer NOT NULL DEFAULT 0,
  completion_tokens integer NOT NULL DEFAULT 0,
  cost_usd numeric NOT NULL DEFAULT 0,
  created_at text NOT NULL
);

CREATE OR REPLACE FUNCTION log_model_usage(payload jsonb)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
  new_id bigint;
BEGIN
  INSERT INTO model_usage (document_id, model, prompt_tokens, completion_tokens, cost_usd, created_at)
  VALUES (
    COALESCE(payload->>'document_id', ''),
    COALESCE(payload->>'model', ''),
    COALESCE((payload->>'prompt_tokens')::integer, 0),
    COALESCE((payload->>'completion_tokens')::integer, 0),
    COALESCE((payload->>'cost_usd')::numeric, 0),
    to_char(clock_timestamp() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"')
  )
  RETURNING id INTO new_id;
  RETURN jsonb_build_object('id', new_id);
END;
$$;

CREATE TABLE IF NOT EXISTS backfill_items (
  id bigserial PRIMARY KEY,
  content_sha256 text NOT NULL UNIQUE,
  original_filename text NOT NULL DEFAULT '',
  local_path text NOT NULL DEFAULT '',
  mime_type text NOT NULL DEFAULT '',
  stated_type text NOT NULL DEFAULT 'other',
  client_or_vendor_stated text NOT NULL DEFAULT '',
  status text NOT NULL DEFAULT 'waiting',
  document_id text NOT NULL DEFAULT '',
  note text NOT NULL DEFAULT '',
  created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS backfill_items_status_idx ON backfill_items (status, id);

CREATE OR REPLACE FUNCTION claim_backfill(batch_size int)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
  n int := LEAST(GREATEST(COALESCE(batch_size, 1), 0), 200);
  live_waiting int;
  recent_failures int;
  held_recent int;
  finished_recent int;
  claimed jsonb;
BEGIN
  SELECT count(*) INTO live_waiting FROM documents
  WHERE status IN ('received', 'processing') AND source = 'live';
  IF live_waiting > 0 THEN
    RETURN jsonb_build_object(
      'claimed', '[]'::jsonb,
      'count', 0,
      'reason', 'A live file is still being read. The archive is waiting.'
    );
  END IF;

  SELECT count(*) INTO recent_failures FROM documents
  WHERE position('The extraction did not return a usable result' in validation_notes) > 0
    AND submitted_at > to_char(clock_timestamp() AT TIME ZONE 'UTC' - interval '1 hour', 'YYYY-MM-DD"T"HH24:MI:SS');
  IF recent_failures >= 3 THEN
    RETURN jsonb_build_object(
      'claimed', '[]'::jsonb,
      'count', 0,
      'reason', 'Reads are failing. The archive is paused.'
    );
  END IF;

  SELECT count(*) FILTER (WHERE status = 'held'), count(*)
  INTO held_recent, finished_recent
  FROM (
    SELECT status FROM documents
    WHERE source = 'backfill' AND status IN ('held', 'accepted', 'awaiting_confirm')
    ORDER BY submitted_at DESC
    LIMIT 10
  ) recent;
  IF finished_recent >= 4 AND held_recent * 2 > finished_recent THEN
    RETURN jsonb_build_object(
      'claimed', '[]'::jsonb,
      'count', 0,
      'reason', 'The last archive batch was mostly held. The archive is paused.'
    );
  END IF;

  DROP TABLE IF EXISTS picked_backfill;
  CREATE TEMP TABLE picked_backfill ON COMMIT DROP AS
  SELECT id FROM backfill_items
  WHERE status = 'waiting'
  ORDER BY id
  LIMIT n
  FOR UPDATE SKIP LOCKED;

  UPDATE backfill_items b
  SET status = 'skipped',
      note = 'This file is already on the book.',
      document_id = d.document_id
  FROM documents d, picked_backfill p
  WHERE b.id = p.id
    AND d.content_sha256 = b.content_sha256;

  WITH marked AS (
    UPDATE backfill_items b
    SET status = 'claimed'
    FROM picked_backfill p
    WHERE b.id = p.id
      AND b.status = 'waiting'
    RETURNING b.id, b.content_sha256, b.original_filename, b.local_path, b.mime_type, b.stated_type, b.client_or_vendor_stated
  )
  SELECT COALESCE(jsonb_agg(to_jsonb(m)), '[]'::jsonb) INTO claimed FROM marked m;

  RETURN jsonb_build_object(
    'claimed', COALESCE(claimed, '[]'::jsonb),
    'count', COALESCE(jsonb_array_length(claimed), 0),
    'reason', ''
  );
END;
$$;

CREATE TABLE IF NOT EXISTS alerts (
  id bigserial PRIMARY KEY,
  kind text NOT NULL,
  body text NOT NULL,
  opened_at text NOT NULL,
  resolved_at text NOT NULL DEFAULT ''
);
