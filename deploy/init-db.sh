#!/bin/sh
set -eu

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<EOSQL
CREATE USER n8n WITH PASSWORD '${N8N_DB_PASSWORD}';
CREATE USER docintel WITH PASSWORD '${DOCINTEL_DB_PASSWORD}';
CREATE DATABASE n8n OWNER n8n;
CREATE DATABASE docintel OWNER docintel;
EOSQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname docintel -f /ledger.sql

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname docintel <<EOSQL
GRANT ALL ON ALL TABLES IN SCHEMA public TO docintel;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO docintel;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO docintel;
EOSQL
