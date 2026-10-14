"""P2 API module. Mount with include_router; P1 route URLs remain unchanged."""
import hashlib
import json
import os
import uuid
from fastapi import APIRouter, HTTPException, Request
from models.db import connect, transaction
from services.importer import utc_now
from services.rule_engine.engine import BASELINE, BaselineApproval, evaluate

router=APIRouter()

def error(code, message, status=409):
    raise HTTPException(status_code=status,detail={'code':code,'message':message})

def envelope(request,data,run_id,versions):
    return {'request_id':request.state.request_id,'status':'success','data':data,'errors':[],
            'run_id':run_id,'source_versions':versions,'generated_at':utc_now()}

def context(con,run_id):
    run=con.execute('SELECT * FROM audit_runs WHERE run_id=?',(run_id,)).fetchone()
    if run is None: error('NOT_FOUND','Audit run not found',404)
    run=dict(run); versions=json.loads(run['source_versions_json'])
    policy=con.execute('SELECT logical_id,sha256 FROM snapshots WHERE snapshot_id=?',(run['policy_snapshot_id'],)).fetchone()
    if policy['logical_id']!=BASELINE:
        error('POLICY_CONFLICT','P2 baseline engine may not run Nexus v1.1 or policy variants')
    # Approval record is external, deliberate, and pinned to exact policy content hash.
    approved_hash=os.environ.get('PROJECT07_APPROVED_BASELINE_SHA256','')
    approval_ref=os.environ.get('PROJECT07_AUTHORITY_APPROVAL_REFERENCE','')
    if len(approved_hash)!=64 or approved_hash!=policy['sha256'] or not approval_ref.strip():
        error('REVIEW_REQUIRED','Approved baseline SHA256 and authority approval reference are required')
    return run,versions,BaselineApproval(policy['sha256'],approval_ref)

@router.post('/api/audit-runs/{run_id}/tests/execute')
def execute(request:Request,run_id:str):
    with transaction() as con:
        run,versions,approved=context(con,run_id)
        # Full web mode requires explicit RCM + PLAN human approvals before deterministic execution.
        # Legacy P2 engine tests may run with PROJECT07_REQUIRE_GATES=0.
        if os.environ.get('PROJECT07_REQUIRE_GATES','1')=='1':
            for required in ('RCM','PLAN'):
                row=con.execute('SELECT state,source_signature FROM workflow_docs WHERE run_id=? AND kind=?',(run_id,required)).fetchone()
                if row is None or row['state']!='APPROVED':
                    error('REVIEW_REQUIRED',f'{required} must be approved before executing tests')
                if row['source_signature']!=run['source_versions_json']:
                    error('STALE_SOURCE',f'{required} approval does not match source snapshots')
        pinned=os.environ.get('PROJECT07_APPROVED_AUTHORITY_SHA256','')
        authority_hash=con.execute('SELECT sha256 FROM snapshots WHERE snapshot_id=?',(run['authority_snapshot_id'],)).fetchone()[0]
        if not pinned or pinned!=authority_hash: error('REVIEW_REQUIRED','Authority snapshot must match independently reviewed hash')
        loan_rows=[dict(row) for row in con.execute('SELECT row_id,source_line,payload_json FROM loan_rows WHERE snapshot_id=? ORDER BY source_line',(run['dataset_snapshot_id'],))]
        for r in loan_rows: r['payload']=json.loads(r.pop('payload_json'))
        authority_rows=[dict(row) for row in con.execute('SELECT source_line,payload_json FROM authority_rows WHERE snapshot_id=? ORDER BY source_line',(run['authority_snapshot_id'],))]
        for r in authority_rows: r['payload']=json.loads(r.pop('payload_json'))
        if not loan_rows: error('MISSING_EVIDENCE','No loan rows in run snapshot')
        results=evaluate(loan_rows,authority_rows,approved)
        # Idempotent deterministic re-execution; do not erase reviews in later phases.
        existing=con.execute('SELECT COUNT(*) FROM rule_results WHERE run_id=?',(run_id,)).fetchone()[0]
        if existing:
            records=[json.loads(x[0]) for x in con.execute('SELECT result_json FROM rule_results WHERE run_id=? ORDER BY source_line,test_id',(run_id,))]
            return envelope(request,{'count':len(records),'results':records,'idempotent_replay':True},run_id,versions)
        for item in results:
            item['run_id']=run_id
            item['source_versions']=versions
            for ref in item['evidence_refs']:
                ref['snapshot_id']=run['dataset_snapshot_id'] if ref['source']=='loans' else run['authority_snapshot_id']
                ref['run_id']=run_id
                ref['evidence_id']=hashlib.sha256(json.dumps(ref,sort_keys=True).encode()).hexdigest()[:24]
            result_id=str(uuid.uuid4()); item['result_id']=result_id
            con.execute('INSERT INTO rule_results(result_id,run_id,row_id,test_id,source_line,result_json) VALUES(?,?,?,?,?,?)',
                        (result_id,run_id,item['row_id'],item['test_id'],item['evidence_refs'][0]['source_line'],json.dumps(item,ensure_ascii=False)))
        con.execute('INSERT INTO audit_events VALUES(?,?,?,?,?)',(str(uuid.uuid4()),run_id,'P2_TESTS_EXECUTED',json.dumps({'results':len(results)}),utc_now()))
    return envelope(request,{'count':len(results),'results':results,'idempotent_replay':False},run_id,versions)

@router.get('/api/audit-runs/{run_id}/results')
def results(request:Request,run_id:str):
    with connect() as con:
        run=con.execute('SELECT source_versions_json FROM audit_runs WHERE run_id=?',(run_id,)).fetchone()
        if run is None: error('NOT_FOUND','Audit run not found',404)
        values=[json.loads(r[0]) for r in con.execute('SELECT result_json FROM rule_results WHERE run_id=? ORDER BY source_line,test_id',(run_id,))]
    return envelope(request,{'count':len(values),'results':values},run_id,json.loads(run[0]))
