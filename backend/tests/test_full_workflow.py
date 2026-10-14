"""API integration with stubbed Gemini outputs; stub calls are NOT live model evaluations."""
import os, hashlib
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

ROOT=Path(__file__).resolve().parents[2]

@pytest.fixture
def client(tmp_path, monkeypatch):
 import models.db as db
 monkeypatch.setattr(db,'DB_PATH',tmp_path/'isolated.sqlite')
 monkeypatch.setenv('PROJECT07_APPROVED_BASELINE_SHA256','e3c776d67a916c95488528b91ae3a6efd8d8a65d197481c44521fd79a62c9e4f')
 monkeypatch.setenv('PROJECT07_AUTHORITY_APPROVAL_REFERENCE','DEMO-REFERENCE-ONLY')
 monkeypatch.setenv('PROJECT07_REQUIRE_GATES','1')
 monkeypatch.setenv('PROJECT07_APPROVED_AUTHORITY_SHA256',hashlib.sha256((ROOT/'demo/employee_authority.csv').read_bytes()).hexdigest())
 from main import app
 with TestClient(app) as c: yield c

def test_full_demo_flow(client,monkeypatch):
 from services import workflow
 files=[('policies','POL-LOAN-01_v1.0.txt',{'policy_id':'POL-LOAN-01','policy_set_id':'BASELINE','effective_from':'2026-10-08T00:00:00+07:00'},'policy_snapshot_id'),('loans','loans_60.csv',{'dataset_id':'DEMO-60'},'dataset_snapshot_id'),('authorities','employee_authority.csv',{'authority_id':'DEMO-AUTH'},'authority_snapshot_id')]
 payload={'audit_name':'Demo integration'}
 for endpoint,name,fields,key in files:
  r=client.post('/api/import/'+endpoint,files={'file':(name,(ROOT/'demo'/name).read_bytes())},data=fields)
  assert r.status_code==201,r.text
  payload[key]=r.json()['data']['snapshot_id']
 r=client.post('/api/audit-runs',json=payload);assert r.status_code==201,r.text
 rid=r.json()['data']['run_id'];base='/api/audit-runs/'+rid
 assert client.post(base+'/tests/execute').status_code==409
 assert client.post(base+'/test-plan/generate').status_code==409
 source=(ROOT/'demo'/'POL-LOAN-01_v1.0.txt').read_text(encoding='utf-8')
 quote=source.splitlines()[0]
 def fake_llm(run,task,system,data):
  if task=='LLM1_RCM':
   clauses={'T01':'2.1.','T02':'2.6.','T03':'2.9.'}
   return {'controls':[{'control_id':'C'+t,'risk':'Potential control gap','control':'Baseline '+t,'clause':clauses[t],'source_quote':next(x for x in source.splitlines() if x.startswith(clauses[t])),'test_ids':[t]} for t in ['T01','T02','T03']],'limitations':[]},'TEST_STUB_NOT_LIVE'
  if task=='LLM2_PLAN':return {'tests':[{'test_id':t,'control_id':'C'+t,'purpose':'Baseline '+t,'evidence_required':'Source fields','applicability':'Baseline only','support':'SUPPORTED'} for t in ['T01','T02','T03']]},'TEST_STUB_NOT_LIVE'
  if task=='LLM3_FINDINGS':
   return {'findings':[{'finding_key':'F'+t,'title':'Gap '+t,'control_id':'C'+t,'source_quote':next(x['source_quote'] for x in data['approved_rcm']['controls'] if x['control_id']=='C'+t),'criteria':'Baseline '+t,'condition':'Observed gap','risk':'Possible weakness','recommendation':'Review','evidence_result_ids':[x['result_id'] for x in data['exceptions'] if x['test_id']==t]} for t in ['T01','T02','T03'] if any(x['test_id']==t for x in data['exceptions'])]},'TEST_STUB_NOT_LIVE'
  if task=='LLM4_REPORT':return {k:'Draft sample' for k in ['executive_summary','scope','methods','findings_summary','limitations','recommendations']},'TEST_STUB_NOT_LIVE'
 monkeypatch.setattr(workflow,'llm_generate',fake_llm)
 assert client.post(base+'/rcm/generate').status_code==200
 assert client.post(base+'/tests/execute').status_code==409
 assert client.post(base+'/rcm/approve',json={'reviewer':'Auditor Demo','reason':'Checked text'}).status_code==200
 assert client.post(base+'/test-plan/generate').status_code==200
 assert client.post(base+'/test-plan/approve',json={'reviewer':'Auditor Demo','reason':'Checked plan'}).status_code==200
 result=client.post(base+'/tests/execute'); assert result.status_code==200,result.text
 assert result.json()['data']['count']==180
 assert client.post(base+'/tests/execute').json()['data']['idempotent_replay'] is True
 assert client.post(base+'/findings/generate').status_code==409
 for x in result.json()['data']['results']:
  if x['test_result']=='EXCEPTION':
   assert client.post(base+'/results/'+x['result_id']+'/review',json={'reviewer':'Auditor Demo','reason':'Verified evidence','review_state':'CONFIRMED'}).status_code==200
 findings=client.post(base+'/findings/generate');assert findings.status_code==200,findings.text
 assert client.post(base+'/report/generate').status_code==409
 assert len(findings.json()['data']['payload']['findings'])>=2
 for finding in findings.json()['data']['payload']['findings']:
  assert finding['criteria_evidence']['policy_snapshot_id']==payload['policy_snapshot_id']
  assert finding['evidence_details'][0]['observed_values']
  reviewed=client.post('/api/findings/'+finding['finding_key']+'/review',json={'run_id':rid,'reviewer':'Auditor Demo','reason':'Verified','state':'CONFIRMED'});assert reviewed.status_code==200
 report=client.post(base+'/report/generate');assert report.status_code==200,report.text
 assert report.json()['data']['state']=='DRAFT'
 assert client.post('/api/reports/'+report.json()['data']['id']+'/finalize',json={}).status_code==409
 eval_result=client.get(base+'/evaluation').json()['data'];assert eval_result['total']==180
 assert eval_result['accuracy'] is None
 assert eval_result['regression_benchmark']['status_accuracy']==1
 assert eval_result['structural_metrics']['test_coverage']==1
 # A human changes their conclusion: report must be invalidated.
 finding=findings.json()['data']['payload']['findings'][0]
 assert client.post('/api/findings/'+finding['finding_key']+'/review',json={'run_id':rid,'reviewer':'Auditor Demo','reason':'More evidence needed','state':'NEEDS_FOLLOWUP'}).status_code==200
 assert not any(x['kind']=='REPORT' for x in client.get(base+'/workflow').json()['data']['documents'])
 assert client.post(base+'/report/generate').status_code==409
 assert client.post('/api/findings/'+finding['finding_key']+'/review',json={'run_id':rid,'reviewer':'Auditor Demo','reason':'Rechecked','state':'CONFIRMED'}).status_code==200
 assert client.post(base+'/report/generate').status_code==200
 assert client.post(base+'/report/approve',json={'reviewer':'Audit Lead','reason':'Checked appendix and limitations'}).status_code==200
 assert client.post('/api/findings/'+finding['finding_key']+'/review',json={'run_id':rid,'reviewer':'Auditor Demo','reason':'Changed','state':'REJECTED'}).status_code==409
 assert len(client.get(base+'/events').json()['data'])>=5

def test_invalid_llm_quote_rejected(client,monkeypatch):
 from services import workflow
 p=ROOT/'demo'/'POL-LOAN-01_v1.0.txt'
 r=client.post('/api/import/policies',files={'file':('policy.txt',p.read_bytes())},data={'policy_id':'POL-LOAN-01','policy_set_id':'BASELINE','effective_from':'2026-10-08T00:00:00+07:00'})
 pol=r.json()['data']['snapshot_id']
 for endpoint,filename,fld in [('loans','loans_60.csv','dataset_id'),('authorities','employee_authority.csv','authority_id')]:
  resp=client.post('/api/import/'+endpoint,files={'file':(filename,(ROOT/'demo'/filename).read_bytes())},data={fld:filename}); assert resp.status_code==201
  if endpoint=='loans': ds=resp.json()['data']['snapshot_id']
  else: auth=resp.json()['data']['snapshot_id']
 rid=client.post('/api/audit-runs',json={'audit_name':'negative','policy_snapshot_id':pol,'dataset_snapshot_id':ds,'authority_snapshot_id':auth}).json()['data']['run_id']
 monkeypatch.setattr(workflow,'llm_generate',lambda *a:({'controls':[{'control_id':'C1','risk':'x','control':'x','clause':'x','source_quote':'INVENTED BY AI','test_ids':['T01']}]},'TEST_STUB'))
 resp=client.post('/api/audit-runs/'+rid+'/rcm/generate')
 assert resp.status_code==422
 assert resp.json()['errors'][0]['code']=='MISSING_EVIDENCE'
