import io

LOANS='row_id,loan_id,amount_vnd,currency,maker_id,approver_id,approval_status,approval_time,disbursement_time,disbursement_status,branch_id\nR1,L1,500000000,VND,E1,E2,APPROVED,2026-10-01T08:00:00+07:00,2026-10-02T08:00:00+07:00,DISBURSED,B1\n'
AUTH='employee_id,role,branch_id,authority_limit_vnd,valid_from,valid_to\nE2,MANAGER,B1,2000000000,2026-01-01T00:00:00+07:00,2027-01-01T00:00:00+07:00\n'

def upload(client,path,key,logical,filename,content):
    return client.post(path,data={key:logical},files={'file':(filename,content.encode('utf-8'),'text/csv')})

def test_health(client):
    r=client.get('/api/health')
    assert r.status_code==200 and r.json()['data']['status']=='ok'

def test_valid_import_and_run(client):
    p=client.post('/api/import/policies',data={'policy_id':'POL-LOAN-01','policy_set_id':'baseline_v1_0','effective_from':'2026-01-01T00:00:00+07:00'},files={'file':('policy.txt',b'POL-LOAN-01 policy text')})
    l=upload(client,'/api/import/loans','dataset_id','demo','loans.csv',LOANS)
    a=upload(client,'/api/import/authorities','authority_id','demoauth','authority.csv',AUTH)
    assert all(r.status_code==201 for r in (p,l,a))
    assert l.json()['data']['row_count']==1
    r=client.post('/api/audit-runs',json={'policy_snapshot_id':p.json()['data']['snapshot_id'],'dataset_snapshot_id':l.json()['data']['snapshot_id'],'authority_snapshot_id':a.json()['data']['snapshot_id'],'audit_name':'Audit sample'})
    assert r.status_code==201
    run_id=r.json()['data']['run_id']
    assert client.get(f'/api/audit-runs/{run_id}').status_code==200

def test_missing_column(client):
    data=LOANS.replace('maker_id,','')
    r=upload(client,'/api/import/loans','dataset_id','d','loans.csv',data)
    assert r.status_code==422
    assert r.json()['errors'][0]['code']=='VALIDATION_ERROR'
    assert 'maker_id' in r.json()['errors'][0]['details']['missing_columns']

def test_duplicate_row_id(client):
    r=upload(client,'/api/import/loans','dataset_id','d','loans.csv',LOANS+LOANS.splitlines()[1]+'\n')
    assert r.status_code==422
    assert r.json()['errors'][0]['message']=='Duplicate row_id'

def test_versioning_and_data_quality(client):
    bad=LOANS.replace('2026-10-01T08:00:00+07:00','2026-10-01')
    first=upload(client,'/api/import/loans','dataset_id','repeat','loans.csv',LOANS)
    second=upload(client,'/api/import/loans','dataset_id','repeat','loans.csv',bad)
    assert first.json()['data']['version']==1
    assert second.json()['data']['version']==2
    assert second.json()['data']['quality_issues'][0]['code']=='INVALID_TIMESTAMP'
    snapshot=client.get('/api/snapshots/'+first.json()['data']['snapshot_id']).json()['data']
    assert snapshot['version']==1
