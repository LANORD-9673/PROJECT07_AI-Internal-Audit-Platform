import base64
import json
import os
import pytest

RAW=b'row_id,full_name,amount_vnd\nL1,Private Client,12000\n'
PLAN=[{'column':'row_id','action':'TOKENIZE'},{'column':'full_name','action':'MASK'},{'column':'amount_vnd','action':'KEEP'}]
@pytest.fixture
def vault(tmp_path,monkeypatch):
    monkeypatch.setenv('PROJECT07_VAULT_MASTER_KEY',base64.b64encode(os.urandom(32)).decode())
    root=tmp_path/'vault';monkeypatch.setenv('PROJECT07_VAULT_DIR',str(root));return root

def test_inspect_returns_archive_and_columns_without_raw_values(client,vault):
    r=client.post('/api/privacy/inspect',files={'file':('loans.csv',RAW)})
    assert r.status_code==200
    assert r.headers['cache-control']=='no-store'
    d=r.json()['data'];assert d['rows']==1 and len(d['plan'])==3
    assert 'Private Client' not in r.text
    assert json.loads(base64.b64decode(d['archive']))['format']=='NEXUS-AES256GCM-v1'
    assert len(list((vault/'encrypted').glob('*.nexus.enc')))==1

def test_export_preserves_structure_and_returns_mapping_without_writing_it(client,vault):
    r=client.post('/api/privacy/export',files={'file':('loans.csv',RAW)},data={'plan':json.dumps(PLAN),'scope':'TEST','reviewer':'Auditor','confirmed':'true'})
    assert r.status_code==200,r.text
    assert r.headers['cache-control']=='no-store'
    d=r.json()['data'];csv=base64.b64decode(d['output'])
    assert b'Private Client' not in csv and b'12000' in csv and b'full_name' in csv
    assert b'Private Client' in base64.b64decode(d['mapping'])
    review=json.loads(base64.b64decode(d['review']))
    assert (vault/'encrypted'/(review['file_id']+'.nexus.enc')).is_file()
    assert not list((vault/'maps').glob('*'))

@pytest.mark.parametrize('confirmed,plan',[('false',PLAN),('true',{}),('true',[{'column':'bad','action':'EXECUTE'}])])
def test_rejects_unreviewed_or_invalid_plan(client,vault,confirmed,plan):
    r=client.post('/api/privacy/export',files={'file':('loans.csv',RAW)},data={'plan':json.dumps(plan),'scope':'TEST','reviewer':'Auditor','confirmed':confirmed})
    assert r.status_code==422
    assert not list(vault.rglob('*.nexus.enc'))

def test_settings_does_not_expose_secrets(client,monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','never-return-this-secret')
    r=client.get('/api/settings/status')
    assert r.json()['data']['gemini_configured']
    assert 'never-return-this-secret' not in r.text
