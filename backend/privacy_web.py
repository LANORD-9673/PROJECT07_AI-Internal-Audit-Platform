"""Stateless React adapter to the existing privacy service; no mapping persistence."""
import json
import os
import uuid
from pathlib import Path
from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from services.privacy import protect_file, read_table, suggest_columns, pseudonymize, PrivacyError, b64, MAX_BYTES
router=APIRouter()

def response(request,data=None,error=None):
    return JSONResponse(status_code=422 if error else 200,headers={'Cache-Control':'no-store'},content={
        'status':'error' if error else 'success','request_id':request.state.request_id,'data':data,
        'errors':[{'code':'PRIVACY_ERROR','message':error}] if error else []})

async def raw_file(file):
    raw=await file.read(MAX_BYTES+1)
    if not raw or len(raw)>MAX_BYTES: raise PrivacyError('File phải có dữ liệu và không vượt 10 MB.')
    return raw,Path((file.filename or 'upload.bin').replace('\\','/')).name

@router.post('/api/privacy/inspect')
async def inspect(request:Request,file:UploadFile=File(...)):
    try:
        raw,name=await raw_file(file)
        protected=protect_file(raw,name)
        data={'archive':b64(protected['encrypted_bytes']),'archive_name':protected['download_name'],'plan':[]}
        if Path(name).suffix.lower() in ('.csv','.xlsx'):
            try:
                frame=read_table(raw,name);data.update(plan=suggest_columns(frame),rows=len(frame))
            except PrivacyError as exc: data['warning']=str(exc)
        else: data['warning']='Đã mã hóa nguyên file. Thay mã theo cột chỉ hỗ trợ CSV/XLSX.'
        return response(request,data)
    except PrivacyError as exc:return response(request,error=str(exc))

@router.post('/api/privacy/export')
async def export(request:Request,file:UploadFile=File(...),plan:str=Form(...),scope:str=Form(...),reviewer:str=Form(...),confirmed:bool=Form(False)):
    try:
        if not confirmed: raise PrivacyError('Cần auditor xác nhận review trước khi xuất.')
        raw,name=await raw_file(file)
        if len(plan)>200000:raise PrivacyError('Phương án xử lý quá lớn.')
        try: actions=json.loads(plan)
        except (ValueError,TypeError): raise PrivacyError('Phương án xử lý không phải JSON hợp lệ.')
        if not isinstance(actions,list) or any(not isinstance(x,dict) or not isinstance(x.get('column'),str) or x.get('action') not in ('TOKENIZE','MASK','KEEP') for x in actions):
            raise PrivacyError('Mỗi cột cần một hành động TOKENIZE, MASK hoặc KEEP.')
        frame=read_table(raw,name)
        # Validate/serialize first; failures do not leave an additional archive.
        ident=uuid.uuid4().hex
        reviewed=pseudonymize(frame,actions,scope,reviewer,ident,source_bytes=raw,source_name=name)
        protected=protect_file(raw,name)
        report=json.loads(reviewed['audit_report_json_bytes']);report['file_id']=protected['file_id']
        return response(request,{'output':b64(reviewed['export_bytes']),'filename':reviewed['export_filename'],
            'mime':reviewed['export_mime'],'csv':b64(reviewed['csv_bytes']),
            'mapping':b64(reviewed['audit_mapping_csv_bytes']),'review':b64(json.dumps(report,ensure_ascii=False).encode()),
            'rows':reviewed['row_count']})
    except PrivacyError as exc:return response(request,error=str(exc))

@router.get('/api/demo/privacy-sample')
def sample():
    return FileResponse(Path(__file__).resolve().parents[1]/'demo/privacy_sample_loans_100.csv',filename='Nexus_Simulated_Loans_100.csv',media_type='text/csv')

@router.get('/api/settings/status')
def settings(request:Request):
    return response(request,{'gemini_configured':bool(os.environ.get('GEMINI_API_KEY','').strip()),
        'vault_configured':bool(os.environ.get('PROJECT07_VAULT_MASTER_KEY','').strip()),
        'model':os.environ.get('PROJECT07_GEMINI_MODEL','gemini-3.8-flash'),
        'baseline_configured':all(os.environ.get(k,'').strip() for k in ('PROJECT07_APPROVED_BASELINE_SHA256','PROJECT07_APPROVED_AUTHORITY_SHA256','PROJECT07_AUTHORITY_APPROVAL_REFERENCE'))})

@router.get('/api/demo/file/{name}')
def demo_file(name:str):
    from fastapi import HTTPException
    if name not in {'POL-LOAN-01_v1.0.txt','loans_60.csv','employee_authority.csv','privacy_sample_authority.csv'}:
        raise HTTPException(404,'Không có file demo này.')
    return FileResponse(Path(__file__).resolve().parents[1]/'demo'/name,filename=name)
