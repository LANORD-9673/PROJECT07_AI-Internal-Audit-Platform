"""Hand-authored regression cases; labels never enter runtime LLM/rule context."""
from services.rule_engine.engine import t01,t02,t03,BaselineApproval

BASE={'row_id':'E1','_source_line':2,'loan_id':'E1','maker_id':'m','approver_id':'a','approval_status':'APPROVED','amount_vnd':'500000000','currency':'VND','approval_time':'2026-10-20T09:00:00+07:00','disbursement_time':'2026-10-20T09:01:00+07:00','disbursement_status':'DISBURSED','branch_id':'B1'}
AUTH={'employee_id':'a','role':'MANAGER','branch_id':'B1','authority_limit_vnd':'2000000000','valid_from':'2026-10-08T00:00:00+07:00','valid_to':'2027-01-01T00:00:00+07:00'}
# Expected outcomes derive from the decision table, not engine-generated labels.
CASES=[
 ('E01','T01',{},None,'PASS','SEGREGATION_OK'),
 ('E02','T01',{'maker_id':'a'},None,'EXCEPTION','MAKER_EQUALS_APPROVER'),
 ('E03','T01',{'maker_id':''},None,'INSUFFICIENT_INFORMATION','MISSING_MAKER_OR_APPROVER'),
 ('E04','T01',{'approval_status':'REJECTED'},None,'NOT_APPLICABLE','NOT_APPROVED'),
 ('E05','T02',{},None,'PASS','WITHIN_APPROVAL_LIMIT_TIER_1'),
 ('E06','T02',{'amount_vnd':'500000001'},None,'PASS','WITHIN_APPROVAL_LIMIT_TIER_2'),
 ('E07','T02',{'amount_vnd':'2000000000'},None,'PASS','WITHIN_APPROVAL_LIMIT_TIER_2'),
 ('E08','T02',{'amount_vnd':'2000000001'},None,'OUT_OF_SCOPE','AMOUNT_ABOVE_2B'),
 ('E09','T02',{'currency':'USD'},None,'OUT_OF_SCOPE','NON_VND'),
 ('E10','T02',{},[dict(AUTH,authority_limit_vnd='400000000')],'EXCEPTION','APPROVAL_LIMIT_EXCEEDED_TIER_1'),
 ('E11','T02',{},[],'INSUFFICIENT_INFORMATION','NO_ACTIVE_AUTHORITY'),
 ('E12','T02',{},[AUTH,dict(AUTH,authority_limit_vnd='400000000')],'BLOCKED','OVERLAPPING_AUTHORITY_CONFLICT'),
 ('E13','T02',{},[dict(AUTH,valid_from='bad')],'BLOCKED','INVALID_AUTHORITY_RECORD'),
 ('E14','T03',{},None,'PASS','APPROVED_BEFORE_DISBURSEMENT'),
 ('E15','T03',{'disbursement_time':BASE['approval_time']},None,'EXCEPTION','APPROVAL_NOT_BEFORE_DISBURSEMENT'),
 ('E16','T03',{'approval_status':'REJECTED'},None,'EXCEPTION','DISBURSED_WHILE_REJECTED'),
 ('E17','T03',{'disbursement_time':''},None,'INSUFFICIENT_INFORMATION','MISSING_OR_INVALID_TIMESTAMP'),
 ('E18','T03',{'disbursement_status':'NOT_DISBURSED'},None,'NOT_APPLICABLE','NOT_DISBURSED'),
]
def benchmark():
 rows=[];tp=fp=fn=0
 for key,test,changes,auth,expected,reason in CASES:
  loan=dict(BASE,**changes); authorities=[{'source_line':i+2,'payload':x} for i,x in enumerate([AUTH] if auth is None else auth)]
  out=t02(loan,authorities,BaselineApproval('EVALUATION_ONLY','EVALUATION_ONLY')) if test=='T02' else {'T01':t01,'T03':t03}[test](loan)
  actual=out['test_result'];tp+=actual==expected=='EXCEPTION';fp+=actual=='EXCEPTION' and expected!='EXCEPTION';fn+=actual!='EXCEPTION' and expected=='EXCEPTION'
  rows.append({'case_id':key,'test_id':test,'input_overrides':changes,'expected':expected,'actual':actual,'expected_reason':reason,'actual_reason':out['reason_code'],'matched':actual==expected and out['reason_code']==reason})
 return {'label_status':'HAND_AUTHORED_REGRESSION_NOT_INDEPENDENTLY_CERTIFIED','cases':rows,'n':len(rows),'status_accuracy':sum(x['expected']==x['actual'] for x in rows)/len(rows),'reason_accuracy':sum(x['matched'] for x in rows)/len(rows),'exception_precision':tp/(tp+fp) if tp+fp else None,'exception_recall':tp/(tp+fn) if tp+fn else None,'baseline_always_pass_accuracy':sum(x['expected']=='PASS' for x in rows)/len(rows),'note':'Measures Python rules on 18 fixed cases; does not measure live LLM semantic accuracy. Auditor must independently validate labels before claiming certified evaluation.'}
