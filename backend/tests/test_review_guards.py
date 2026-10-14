"""Negative integration cases for human gates and fabricated LLM output."""
import hashlib,json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from services.evaluation import benchmark,CASES
ROOT=Path(__file__).resolve().parents[2]

@pytest.fixture
def run(tmp_path,monkeypatch):
 import models.db as db
 monkeypatch.setattr(db,'DB_PATH',tmp_path/'guards.sqlite')
 monkeypatch.delenv('PROJECT07_REQUIRE_GATES',raising=False)
 monkeypatch.setenv('PROJECT07_APPROVED_BASELINE_SHA256',hashlib.sha256((ROOT/'demo/POL-LOAN-01_v1.0.txt').read_bytes()).hexdigest())
 monkeypatch.setenv('PROJECT07_APPROVED_AUTHORITY_SHA256',hashlib.sha256((ROOT/'demo/employee_authority.csv').read_bytes()).hexdigest())
 monkeypatch.setenv('PROJECT07_AUTHORITY_APPROVAL_REFERENCE','TEST_ONLY')
 from main import app
 with TestClient(app) as client:
  payload={'audit_name':'Negative cases'}
  for endpoint,name,fields,key in [('policies','POL-LOAN-01_v1.0.txt',{'policy_id':'POL-LOAN-01','policy_set_id':'BASELINE','effective_from':'2026-10-08T00:00:00+07:00'},'policy_snapshot_id'),('loans','loans_60.csv',{'dataset_id':'DEMO'},'dataset_snapshot_id'),('authorities','employee_authority.csv',{'authority_id':'DEMO'},'authority_snapshot_id')]:
   r=client.post('/api/import/'+endpoint,files={'file':(name,(ROOT/'demo'/name).read_bytes())},data=fields);assert r.status_code==201
   payload[key]=r.json()['data']['snapshot_id']
  rid=client.post('/api/audit-runs',json=payload).json()['data']['run_id']
  yield client,rid

def approved_rcm(client,rid):
 from models.db import transaction
 from services.workflow import save_doc
 from services.importer import utc_now
 source=(ROOT/'demo/POL-LOAN-01_v1.0.txt').read_text()
 controls=[{'control_id':'C'+t,'risk':'Test','control':'Test','clause':clause,'source_quote':next(x for x in source.splitlines() if x.startswith(clause)),'test_ids':[t]} for t,clause in [('T01','2.1.'),('T02','2.6.'),('T03','2.9.')]]
 save_doc(rid,'RCM',{'controls':controls},'TEST_FIXTURE_NOT_LIVE')
 assert client.post(f'/api/audit-runs/{rid}/rcm/approve',json={'reviewer':'Tester','reason':'Fixture only'}).status_code==200
 return controls

def test_gates_enabled_by_default(run):
 client,rid=run
 r=client.post(f'/api/audit-runs/{rid}/tests/execute')
 assert r.status_code==409 and r.json()['errors'][0]['code']=='REVIEW_REQUIRED'

@pytest.mark.parametrize('bad',['unknown_control','unknown_test','duplicate_test','incomplete','invalid_support'])
def test_invalid_plan(run,monkeypatch,bad):
 from services import workflow
 client,rid=run;approved_rcm(client,rid)
 tests=[{'test_id':t,'control_id':'C'+t,'purpose':'Check','evidence_required':'Fields','applicability':'Baseline','support':'SUPPORTED'} for t in ['T01','T02','T03']]
 if bad=='unknown_control':tests[0]['control_id']='INVENTED'
 if bad=='unknown_test':tests[0]['test_id']='T99'
 if bad=='duplicate_test':tests.append(dict(tests[0]))
 if bad=='incomplete':tests=tests[:1]
 if bad=='invalid_support':tests[0]['support']='MAYBE'
 monkeypatch.setattr(workflow,'llm_generate',lambda *a:({'tests':tests},'TEST_STUB_NOT_LIVE'))
 assert client.post(f'/api/audit-runs/{rid}/test-plan/generate').status_code==422

@pytest.mark.parametrize('bad',['unknown_result','wrong_control','invented_quote','uncovered'])
def test_invalid_finding(run,monkeypatch,bad):
 from services import workflow
 from services.workflow import save_doc
 client,rid=run;controls=approved_rcm(client,rid)
 save_doc(rid,'PLAN',{'tests':[{'test_id':t,'control_id':'C'+t,'support':'SUPPORTED'} for t in ['T01','T02','T03']]},'TEST_FIXTURE_NOT_LIVE')
 assert client.post(f'/api/audit-runs/{rid}/test-plan/approve',json={'reviewer':'Tester','reason':'Fixture'}).status_code==200
 records=client.post(f'/api/audit-runs/{rid}/tests/execute').json()['data']['results']
 for r in records:
  if r['test_result']=='EXCEPTION':client.post(f"/api/audit-runs/{rid}/results/{r['result_id']}/review",json={'review_state':'CONFIRMED','reviewer':'Tester','reason':'Fixture'})
 def fake(rid,task,prompt,data):
  finds=[{'finding_key':'F'+t,'title':'Fixture','control_id':'C'+t,'criteria':'Fixture','source_quote':next(c['source_quote'] for c in controls if c['control_id']=='C'+t),'condition':'Fixture','risk':'Fixture','recommendation':'Fixture','evidence_result_ids':[r['result_id'] for r in data['exceptions'] if r['test_id']==t]} for t in ['T01','T02','T03']]
  if bad=='unknown_result':finds[0]['evidence_result_ids']=['INVENTED']
  if bad=='wrong_control':finds[0]['control_id']='CT02';finds[0]['source_quote']=controls[1]['source_quote']
  if bad=='invented_quote':finds[0]['source_quote']='INVENTED'
  if bad=='uncovered':finds=finds[:1]
  return {'findings':finds},'TEST_STUB_NOT_LIVE'
 monkeypatch.setattr(workflow,'llm_generate',fake)
 assert client.post(f'/api/audit-runs/{rid}/findings/generate').status_code==422

@pytest.mark.parametrize('key',[x[0] for x in CASES])
def test_regression_cases(key):
 result=next(x for x in benchmark()['cases'] if x['case_id']==key)
 assert result['matched'],json.dumps(result)

def test_model_unavailable_no_mock(run,monkeypatch):
 import urllib.error
 from services import workflow
 client,rid=run
 def offline(*a,**kw):raise urllib.error.URLError('offline test')
 from services import gemini
 monkeypatch.setenv('GEMINI_API_KEY','fake-test-only')
 monkeypatch.setattr(gemini.urllib.request,'urlopen',offline)
 r=client.post(f'/api/audit-runs/{rid}/rcm/generate')
 assert r.status_code==503 and r.json()['errors'][0]['code']=='MODEL_UNAVAILABLE'
 data=client.get(f'/api/audit-runs/{rid}/workflow').json()['data']
 assert not data['documents']
 calls=client.get(f'/api/audit-runs/{rid}/evaluation').json()['data']['llm_calls']
 assert calls[-1]['status']=='ERROR'
