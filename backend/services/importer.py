import hashlib
import io
import json
import re
import uuid
from datetime import datetime, timezone
import pandas as pd
from fastapi import HTTPException
from models.db import transaction

LOAN_FIELDS = {'loan_id','amount_vnd','currency','maker_id','approver_id','approval_status','approval_time','disbursement_time','disbursement_status','branch_id'}
AUTH_FIELDS = {'employee_id','role','branch_id','authority_limit_vnd','valid_from','valid_to'}
MAX_BYTES = 10 * 1024 * 1024

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def fail(code, message, details=None, status=422):
    raise HTTPException(status_code=status, detail={'code':code,'message':message,'details':details or {}})

def decode(raw):
    if len(raw) > MAX_BYTES:
        fail('FILE_TOO_LARGE','Maximum file size is 10 MB',status=413)
    try:
        return raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        fail('VALIDATION_ERROR','Use UTF-8 encoded text or CSV')

def parse_table(raw, kind, extension):
    try:
        if extension == '.csv':
            frame = pd.read_csv(io.StringIO(decode(raw)), dtype=str, keep_default_na=False, na_filter=False)
        elif extension == '.xlsx':
            frame = pd.read_excel(io.BytesIO(raw), sheet_name=0, dtype=str, keep_default_na=False, na_filter=False, engine='openpyxl')
        else:
            fail('UNSUPPORTED_FORMAT','Only CSV and XLSX are supported for structured datasets')
    except HTTPException:
        raise
    except Exception:
        fail('VALIDATION_ERROR','Cannot read CSV/XLSX; check file formatting and first worksheet')
    frame.columns = [str(c).strip() for c in frame.columns]
    if frame.columns.duplicated().any():
        fail('VALIDATION_ERROR','Duplicate column headers')
    required = LOAN_FIELDS if kind == 'loans' else AUTH_FIELDS
    missing = sorted(required - set(frame.columns))
    if missing:
        fail('VALIDATION_ERROR','Missing required CSV columns',{'missing_columns':missing})
    if frame.empty:
        fail('VALIDATION_ERROR','CSV contains no records')
    issues=[]
    rows=[]
    observed=set()
    for index, raw_row in enumerate(frame.to_dict('records')):
        line=index+2
        row={str(k):str(v).strip() for k,v in raw_row.items()}
        if kind=='loans':
            row_id=row.get('row_id') or f'ROW-{index+1:06d}'
            row['row_id']=row_id
            if row_id in observed:
                fail('VALIDATION_ERROR','Duplicate row_id',{'row_id':row_id,'source_line':line})
            observed.add(row_id)
        else:
            row_id=None
        fields=('approval_time','disbursement_time') if kind=='loans' else ('valid_from','valid_to')
        for field in fields:
            if row.get(field):
                try:
                    dt=datetime.fromisoformat(row[field].replace('Z','+00:00'))
                    if dt.tzinfo is None or dt.utcoffset() is None:
                        raise ValueError('timezone missing')
                except ValueError:
                    issues.append({'source_line':line,'row_id':row_id,'code':'INVALID_TIMESTAMP','message':f'{field} must be ISO 8601 with timezone'})
        numeric=('amount_vnd',) if kind=='loans' else ('authority_limit_vnd',)
        for field in numeric:
            value=row.get(field,'')
            if not re.fullmatch(r'\d+',value):
                issues.append({'source_line':line,'row_id':row_id,'code':'INVALID_AMOUNT','message':f'{field} must be a nonnegative VND integer'})
        if kind=='loans':
            if row.get('currency')!='VND':
                issues.append({'source_line':line,'row_id':row_id,'code':'CURRENCY_REVIEW','message':'Only VND is covered by baseline automated authority test'})
            if not row['loan_id']:
                issues.append({'source_line':line,'row_id':row_id,'code':'MISSING_LOAN_ID','message':'loan_id is empty'})
        rows.append({'row_id':row_id,'source_line':line,'payload':row})
    return rows,issues

def store_snapshot(kind,logical_id,filename,raw,metadata,rows=None,issues=None):
    if not logical_id or not logical_id.strip():
        fail('VALIDATION_ERROR','logical_id must not be empty')
    digest=hashlib.sha256(raw).hexdigest()
    snapshot_id=str(uuid.uuid4())
    now=utc_now()
    with transaction() as con:
        latest=con.execute('SELECT COALESCE(MAX(version),0) AS v FROM snapshots WHERE source_type=? AND logical_id=?',(kind,logical_id)).fetchone()['v']
        version=latest+1
        con.execute('INSERT INTO snapshots VALUES (?,?,?,?,?,?,?,?,?)',(snapshot_id,kind,logical_id,version,filename,digest,raw,now,json.dumps(metadata,ensure_ascii=False)))
        for row in rows or []:
            if kind=='loans':
                con.execute('INSERT INTO loan_rows VALUES (?,?,?,?,?)',(snapshot_id,row['row_id'],row['source_line'],row['payload'].get('loan_id'),json.dumps(row['payload'],ensure_ascii=False)))
            if kind=='authority':
                con.execute('INSERT INTO authority_rows VALUES (?,?,?)',(snapshot_id,row['source_line'],json.dumps(row['payload'],ensure_ascii=False)))
        for i,issue in enumerate(issues or []):
            con.execute('INSERT INTO import_issues VALUES (?,?,?,?,?,?)',(snapshot_id,i,issue['source_line'],issue['row_id'],issue['code'],issue['message']))
    return {'snapshot_id':snapshot_id,'source_type':kind,'logical_id':logical_id,'version':version,'sha256':digest,'row_count':len(rows or []),'quality_issue_count':len(issues or []),'quality_issues':issues or [],'imported_at':now}


def parse_csv(raw, kind):
    """Compatibility wrapper for P1/P2 code."""
    return parse_table(raw, kind, '.csv')


def extract_policy(raw, extension):
    """Return real extracted text; never generate or infer missing clauses."""
    if extension in {'.txt', '.md'}:
        result = decode(raw)
    elif extension == '.docx':
        try:
            from docx import Document
            doc = Document(io.BytesIO(raw))
            parts = []
            for block in doc.iter_inner_content():
                if hasattr(block, 'rows'):
                    for row in block.rows:
                        parts.append(' | '.join(cell.text.strip() for cell in row.cells))
                else:
                    parts.append(block.text)
            result = '\n'.join(parts)
        except Exception:
            fail('VALIDATION_ERROR','Unable to read DOCX; check that it is a valid Word file')
    elif extension == '.pdf':
        try:
            import fitz
            with fitz.open(stream=raw, filetype='pdf') as doc:
                if doc.is_encrypted:
                    fail('VALIDATION_ERROR','Encrypted PDF is not supported')
                pages = [page.get_text(sort=True) for page in doc]
                if not any(p.strip() for p in pages):
                    fail('NO_EXTRACTABLE_TEXT','PDF has no text layer; OCR is not available')
                result = '\n'.join(f'[PAGE {i+1}]\n'+p for i, p in enumerate(pages))
        except HTTPException:
            raise
        except Exception:
            fail('VALIDATION_ERROR','Unable to extract text from PDF')
    else:
        fail('UNSUPPORTED_FORMAT','Policy formats supported: .txt, .md, .docx, .pdf')
    if not result.strip():
        fail('NO_EXTRACTABLE_TEXT','No text extracted; scanned PDFs need OCR and manual review')
    return result
