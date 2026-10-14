import hashlib
from test_imports import LOANS, AUTH, upload

def prepare(client,policy_set,raw):
    p=client.post('/api/import/policies',data={'policy_id':'POL-LOAN-01','policy_set_id':policy_set,'effective_from':'2026-01-01T00:00:00+07:00'},files={'file':('policy.txt',raw)})
    l=upload(client,'/api/import/loans','dataset_id','demo','loans.csv',LOANS)
    a=upload(client,'/api/import/authorities','authority_id','demoauth','auth.csv',AUTH)
    assert all(x.status_code==201 for x in (p,l,a))
    r=client.post('/api/audit-runs',json={'policy_snapshot_id':p.json()['data']['snapshot_id'],'dataset_snapshot_id':l.json()['data']['snapshot_id'],'authority_snapshot_id':a.json()['data']['snapshot_id'],'audit_name':'Synthetic API test'})
    assert r.status_code==201
    return r.json()['data']['run_id']

def test_nexus_policy_cannot_run_baseline(client,monkeypatch):
    rid=prepare(client,'NEXUS-V1.1',b'UNVERIFIED TEST POLICY')
    monkeypatch.setenv('PROJECT07_APPROVED_BASELINE_SHA256',hashlib.sha256(b'UNVERIFIED TEST POLICY').hexdigest())
    monkeypatch.setenv('PROJECT07_AUTHORITY_APPROVAL_REFERENCE','SYNTHETIC_TEST_ONLY')
    resp=client.post(f'/api/audit-runs/{rid}/tests/execute')
    assert resp.status_code==409
    assert resp.json()['errors'][0]['code']=='POLICY_CONFLICT'

def test_approved_test_baseline_api(client,monkeypatch):
    # Isolated legacy engine API test deliberately bypasses workflow approvals.
    monkeypatch.setenv('PROJECT07_REQUIRE_GATES','0')
    monkeypatch.setenv('PROJECT07_APPROVED_AUTHORITY_SHA256',hashlib.sha256(AUTH.encode()).hexdigest())
    raw=b'SYNTHETIC POLICY PLACEHOLDER FOR API TEST ONLY'
    rid=prepare(client,'BASELINE',raw)
    assert client.post(f'/api/audit-runs/{rid}/tests/execute').json()['errors'][0]['code']=='REVIEW_REQUIRED'
    monkeypatch.setenv('PROJECT07_APPROVED_BASELINE_SHA256',hashlib.sha256(raw).hexdigest())
    monkeypatch.setenv('PROJECT07_AUTHORITY_APPROVAL_REFERENCE','SYNTHETIC_TEST_ONLY')
    first=client.post(f'/api/audit-runs/{rid}/tests/execute')
    assert first.status_code==200
    assert first.json()['data']['count']==3
    assert first.json()['data']['idempotent_replay'] is False
    second=client.post(f'/api/audit-runs/{rid}/tests/execute')
    assert second.json()['data']['idempotent_replay'] is True
    assert client.get(f'/api/audit-runs/{rid}/results').json()['data']['count']==3
