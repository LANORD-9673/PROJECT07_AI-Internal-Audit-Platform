import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(os.environ.get('PROJECT07_DB_PATH', str(Path(__file__).resolve().parents[1] / 'project07.sqlite3')))
SCHEMA = '''
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS snapshots (
 snapshot_id TEXT PRIMARY KEY, source_type TEXT NOT NULL CHECK(source_type IN ('policy','loans','authority')),
 logical_id TEXT NOT NULL, version INTEGER NOT NULL, filename TEXT NOT NULL,
 sha256 TEXT NOT NULL, source_content BLOB NOT NULL, imported_at TEXT NOT NULL,
 metadata_json TEXT NOT NULL, UNIQUE(source_type, logical_id, version));
CREATE TABLE IF NOT EXISTS policy_texts (
 snapshot_id TEXT PRIMARY KEY REFERENCES snapshots(snapshot_id), extracted_text TEXT NOT NULL, extractor TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS loan_rows (
 snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id), row_id TEXT NOT NULL,
 source_line INTEGER NOT NULL, loan_id TEXT, payload_json TEXT NOT NULL,
 PRIMARY KEY(snapshot_id,row_id));
CREATE TABLE IF NOT EXISTS authority_rows (
 snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id), source_line INTEGER NOT NULL,
 payload_json TEXT NOT NULL, PRIMARY KEY(snapshot_id,source_line));
CREATE TABLE IF NOT EXISTS import_issues (
 snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id), issue_index INTEGER NOT NULL,
 source_line INTEGER, row_id TEXT, code TEXT NOT NULL, message TEXT NOT NULL,
 PRIMARY KEY(snapshot_id,issue_index));
CREATE TABLE IF NOT EXISTS audit_runs (
 run_id TEXT PRIMARY KEY, audit_name TEXT NOT NULL, policy_snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id),
 dataset_snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id),
 authority_snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id), status TEXT NOT NULL,
 created_at TEXT NOT NULL, source_versions_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS rule_results (
 result_id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES audit_runs(run_id),
 row_id TEXT NOT NULL, test_id TEXT NOT NULL, source_line INTEGER NOT NULL,
 result_json TEXT NOT NULL, UNIQUE(run_id,row_id,test_id));
CREATE TABLE IF NOT EXISTS audit_events (
 event_id TEXT PRIMARY KEY, run_id TEXT, action TEXT NOT NULL, details_json TEXT NOT NULL,
 created_at TEXT NOT NULL);
'''

def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    con.execute('PRAGMA busy_timeout=5000')
    return con

def init_db():
    with connect() as con:
        con.executescript(SCHEMA)

@contextmanager
def transaction():
    con = connect()
    try:
        con.execute('BEGIN IMMEDIATE')
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

def to_dict(row):
    return dict(row) if row is not None else None

def issue_list(con, snapshot_id):
    return [dict(r) for r in con.execute('SELECT source_line,row_id,code,message FROM import_issues WHERE snapshot_id=? ORDER BY issue_index', (snapshot_id,))]
