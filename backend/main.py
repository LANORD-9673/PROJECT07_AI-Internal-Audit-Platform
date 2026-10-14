import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from models.db import connect, init_db, transaction
from schemas.contracts import AuditRunCreate
from services.importer import decode, fail, parse_table, extract_policy, store_snapshot, utc_now, MAX_BYTES

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title='Project 07 — AI Internal Audit Platform', version='1.6.1-PRIVACY-SAMPLE', lifespan=lifespan,
 description='Policy → RCM → plan → deterministic tests → reviewed findings → reviewed draft report. Four Gemini API LLM tasks; mandatory human gates.')

def envelope(request, data=None, status='success', errors=None, run_id=None, versions=None):
    return {'request_id':request.state.request_id,'status':status,'data':data,'errors':errors or [],
            'run_id':run_id,'source_versions':versions or {},'generated_at':utc_now()}

@app.middleware('http')
async def request_id(request: Request, call_next):
    request.state.request_id=str(uuid.uuid4())
    response=await call_next(request)
    response.headers['X-Request-ID']=request.state.request_id
    return response

@app.exception_handler(HTTPException)
async def http_error(request,exc):
    payload=exc.detail if isinstance(exc.detail,dict) else {'code':'HTTP_ERROR','message':str(exc.detail)}
    error={'code':payload.get('code','HTTP_ERROR'),'message':payload.get('message','Request failed'),'details':payload.get('details',{})}
    return JSONResponse(status_code=exc.status_code,content=envelope(request,status='error',errors=[error]))

@app.exception_handler(RequestValidationError)
async def validation_error(request,exc):
    details=[{'loc':list(e['loc']),'msg':e['msg']} for e in exc.errors()]
    return JSONResponse(status_code=422,content=envelope(request,status='error',errors=[{'code':'VALIDATION_ERROR','message':'Invalid request','details':{'fields':details}}]))

async def get_raw(file:UploadFile):
    raw=await file.read(MAX_BYTES+1)
    if not raw:
        fail('VALIDATION_ERROR','Empty uploaded file')
    if len(raw)>MAX_BYTES:
        fail('FILE_TOO_LARGE','File exceeds 10 MB',status=413)
    return raw

@app.get('/api/health')
def health(request:Request):
    return envelope(request,{'service':'project07-backend','phase':'P1-P6-WEB-DEMO','status':'ok'})

@app.post('/api/import/policies',status_code=201)
async def import_policy(request:Request,file:UploadFile=File(...),policy_id:str=Form(...),policy_set_id:str=Form(...),effective_from:str=Form(...)):
    extension=Path(file.filename or '').suffix.lower()
    raw=await get_raw(file)
    text=extract_policy(raw,extension)
    if not text.strip():
        fail('VALIDATION_ERROR','Policy is empty')
    try:
        dt=datetime.fromisoformat(effective_from.replace('Z','+00:00'))
        if dt.tzinfo is None or dt.utcoffset() is None: raise ValueError()
    except ValueError:
        fail('VALIDATION_ERROR','effective_from must be ISO 8601 with timezone')
    logical_id=f'{policy_set_id.strip()}::{policy_id.strip()}'
    result=store_snapshot('policy',logical_id,file.filename or 'policy.txt',raw,{'policy_id':policy_id,'policy_set_id':policy_set_id,'effective_from':effective_from,'extraction_status':'UNREVIEWED','extracted_chars':len(text),'format':extension})
    with transaction() as con:
        con.execute('INSERT INTO policy_texts (snapshot_id, extracted_text, extractor) VALUES (?,?,?)',(result['snapshot_id'], text, extension))
    return envelope(request,result,versions={'policy':result['version']})

async def import_csv(request,file,kind,logical_id):
    extension=Path(file.filename or '').suffix.lower()
    if extension not in {'.csv','.xlsx'}:
        fail('UNSUPPORTED_FORMAT','Upload a .csv or .xlsx file')
    raw=await get_raw(file)
    rows,issues=parse_table(raw,kind,extension)
    result=store_snapshot(kind,logical_id,file.filename or 'data.csv',raw,{'has_quality_issues':bool(issues)},rows,issues)
    return envelope(request,result,versions={kind:result['version']})

@app.post('/api/import/loans',status_code=201)
async def import_loans(request:Request,file:UploadFile=File(...),dataset_id:str=Form(...)):
    return await import_csv(request,file,'loans',dataset_id)

@app.post('/api/import/authorities',status_code=201)
async def import_authorities(request:Request,file:UploadFile=File(...),authority_id:str=Form(...)):
    return await import_csv(request,file,'authority',authority_id)

@app.get('/api/snapshots/{snapshot_id}')
def get_snapshot(request:Request,snapshot_id:str):
    with connect() as con:
        item=con.execute('SELECT snapshot_id,source_type,logical_id,version,filename,sha256,imported_at,metadata_json FROM snapshots WHERE snapshot_id=?',(snapshot_id,)).fetchone()
        if item is None: fail('NOT_FOUND','Snapshot not found',status=404)
        data=dict(item)
        data['metadata']=json.loads(data.pop('metadata_json'))
        data['quality_issues']=[dict(r) for r in con.execute('SELECT source_line,row_id,code,message FROM import_issues WHERE snapshot_id=?',(snapshot_id,))]
    return envelope(request,data,versions={data['source_type']:data['version']})

@app.post('/api/audit-runs',status_code=201)
def create_audit_run(request:Request,payload:AuditRunCreate):
    refs={'policy':payload.policy_snapshot_id,'loans':payload.dataset_snapshot_id,'authority':payload.authority_snapshot_id}
    with connect() as con:
        found={}
        for expected,sid in refs.items():
            row=con.execute('SELECT snapshot_id,source_type,logical_id,version,sha256 FROM snapshots WHERE snapshot_id=?',(sid,)).fetchone()
            if row is None: fail('NOT_FOUND',f'{expected} snapshot not found',{'snapshot_id':sid},404)
            if row['source_type']!=expected: fail('VALIDATION_ERROR',f'Expected {expected} snapshot')
            found[expected]=dict(row)
        # A dataset with recorded quality issues remains importable; P2 handles per-test applicability.
        run_id=str(uuid.uuid4()); now=utc_now()
        versions={k:{'snapshot_id':v['snapshot_id'],'logical_id':v['logical_id'],'version':v['version'],'sha256':v['sha256']} for k,v in found.items()}
        with con:
            con.execute('INSERT INTO audit_runs VALUES (?,?,?,?,?,?,?,?)',(run_id,payload.audit_name,refs['policy'],refs['loans'],refs['authority'],'CREATED',now,json.dumps(versions)))
            con.execute('INSERT INTO audit_events VALUES (?,?,?,?,?)',(str(uuid.uuid4()),run_id,'AUDIT_RUN_CREATED',json.dumps({'source_versions':versions}),now))
    return envelope(request,{'run_id':run_id,'audit_name':payload.audit_name,'status':'CREATED','created_at':now},run_id=run_id,versions=versions)

@app.get('/api/audit-runs/{run_id}')
def get_audit_run(request:Request,run_id:str):
    with connect() as con:
        row=con.execute('SELECT * FROM audit_runs WHERE run_id=?',(run_id,)).fetchone()
        if row is None: fail('NOT_FOUND','Audit run not found',status=404)
        data=dict(row); versions=json.loads(data.pop('source_versions_json'))
    data['source_versions']=versions
    return envelope(request,data,run_id=run_id,versions=versions)


@app.get('/api/policies/{snapshot_id}/text')
def get_policy_text(request: Request, snapshot_id: str):
    """Reviewer/P3 can read the extracted source, never ground truth."""
    with connect() as con:
        item=con.execute('SELECT s.version, s.logical_id, s.sha256, p.extracted_text, p.extractor FROM policy_texts p JOIN snapshots s ON s.snapshot_id=p.snapshot_id WHERE p.snapshot_id=?',(snapshot_id,)).fetchone()
    if item is None:
        fail('NOT_FOUND','Extracted policy text not found',status=404)
    return envelope(request, dict(item), versions={'policy':item['version']})


# P2: original P1 routes remain intact.
from services.rule_engine.api import router as rule_engine_router
app.include_router(rule_engine_router)

# P3–P6 demo workflow extension; all original P1/P2 endpoints remain unchanged.
from services.workflow import router as workflow_router, setup as setup_workflow
app.include_router(workflow_router)
_original_lifespan = app.router.lifespan_context
@asynccontextmanager
async def complete_lifespan(app):
    async with _original_lifespan(app):
        setup_workflow()
        yield
app.router.lifespan_context = complete_lifespan
