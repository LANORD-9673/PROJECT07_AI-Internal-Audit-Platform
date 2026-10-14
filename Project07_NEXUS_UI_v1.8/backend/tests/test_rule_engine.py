from services.rule_engine.engine import *
from datetime import datetime

APP=BaselineApproval('a'*64,'TEST_APPROVAL_ONLY')
BASE={'row_id':'R1','_source_line':2,'loan_id':'L1','maker_id':'m','approver_id':'a','approval_status':'APPROVED','amount_vnd':'500000000','currency':'VND','approval_time':'2026-01-01T09:00:00+07:00','disbursement_time':'2026-01-01T09:01:00+07:00','disbursement_status':'DISBURSED','branch_id':'B1'}
AUTH=[{'source_line':2,'payload':{'employee_id':'a','role':'MANAGER','branch_id':'B1','authority_limit_vnd':'2000000000','valid_from':'2025-01-01T00:00:00+07:00','valid_to':'2027-01-01T00:00:00+07:00'}}]

def loan(**kwargs): return dict(BASE,**kwargs)
def test_t01_segregation():
    assert t01(loan())['test_result']==PASS
    assert t01(loan(maker_id='a'))['reason_code']=='MAKER_EQUALS_APPROVER'
    assert t01(loan(maker_id=''))['test_result']==INSUFFICIENT

def test_t02_boundaries():
    assert t02(loan(amount_vnd='500000000'),AUTH,APP)['reason_code']=='WITHIN_APPROVAL_LIMIT_TIER_1'
    assert t02(loan(amount_vnd='500000001'),AUTH,APP)['reason_code']=='WITHIN_APPROVAL_LIMIT_TIER_2'
    assert t02(loan(amount_vnd='2000000000'),AUTH,APP)['test_result']==PASS
    assert t02(loan(amount_vnd='2000000001'),AUTH,APP)['test_result']==OUT_OF_SCOPE

def test_t02_expired_overlap_missing():
    expired=[{'source_line':2,'payload':dict(AUTH[0]['payload'],valid_to='2025-01-02T00:00:00+07:00')}]
    assert t02(loan(),expired,APP)['reason_code']=='NO_ACTIVE_AUTHORITY'
    conflicting=AUTH+[{'source_line':3,'payload':dict(AUTH[0]['payload'],authority_limit_vnd='400000000')}]
    assert t02(loan(),conflicting,APP)['test_result']==BLOCKED
    assert t02(loan(approver_id=''),AUTH,APP)['test_result']==INSUFFICIENT
    assert t02(loan(amount_vnd='2000000000'),[{'source_line':2,'payload':dict(AUTH[0]['payload'],authority_limit_vnd='500000000')}],APP)['test_result']==EXCEPTION

def test_t03_equal_rejected_missing():
    assert t03(loan())['test_result']==PASS
    assert t03(loan(disbursement_time=BASE['approval_time']))['test_result']==EXCEPTION
    assert t03(loan(approval_status='REJECTED'))['reason_code']=='DISBURSED_WHILE_REJECTED'
    assert t03(loan(disbursement_time=''))['test_result']==INSUFFICIENT
    assert t03(loan(disbursement_status='NOT_DISBURSED'))['test_result']==NOT_APPLICABLE

def test_independent_review_and_evidence():
    out=evaluate([{'row_id':'R1','source_line':2,'payload':BASE}],AUTH,APP)
    assert len(out)==3
    assert all(x['review_state']=='PENDING' for x in out)
    assert all(x['evidence_refs'][0]['row_id']=='R1' for x in out)
