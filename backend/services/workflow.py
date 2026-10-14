"""P3–P6 workflow: source-grounded LLM drafts, explicit human gates, audit trail.
No AI output can set a final state. Local demo self-declared reviewers do not confer production authority.
"""
import json, os, uuid, time
from fastapi import APIRouter, HTTPException, Request
from models.db import connect, transaction
from services.importer import utc_now
from services.evaluation import benchmark

router=APIRouter()

SCHEMA='''
CREATE TABLE IF NOT EXISTS workflow_docs (
 id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES audit_runs(run_id),
 kind TEXT NOT NULL, state TEXT NOT NULL, payload TEXT NOT NULL,
 source_signature TEXT NOT NULL, model TEXT NOT NULL, created_at TEXT NOT NULL,
 reviewed_by TEXT, reviewed_at TEXT, review_note TEXT,
 UNIQUE(run_id,kind));
CREATE TABLE IF NOT EXISTS result_reviews (
 result_id TEXT PRIMARY KEY REFERENCES rule_results(result_id),
 review_state TEXT NOT NULL, reviewer TEXT NOT NULL, reason TEXT NOT NULL, reviewed_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS finding_reviews (
 run_id TEXT NOT NULL, finding_key TEXT NOT NULL, state TEXT NOT NULL,
 reviewer TEXT NOT NULL, reason TEXT NOT NULL, reviewed_at TEXT NOT NULL,
 PRIMARY KEY(run_id,finding_key));
CREATE TABLE IF NOT EXISTS llm_calls (
 id TEXT PRIMARY KEY, run_id TEXT NOT NULL, task TEXT NOT NULL,
 model TEXT NOT NULL, latency_ms INTEGER NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL);
'''

def setup():
 with connect() as c: c.executescript(SCHEMA)

def fail(code,message,status=409):
 raise HTTPException(status_code=status,detail={'code':code,'message':message})

def wrap(request,data,run_id=None):
 return {'request_id':request.state.request_id,'status':'success','data':data,'errors':[],'run_id':run_id,'generated_at':utc_now()}

def load_run(c,rid):
 r=c.execute('SELECT * FROM audit_runs WHERE run_id=?',(rid,)).fetchone()
 if not r: fail('NOT_FOUND','Audit Run not found',404)
 return dict(r)

def signature(run): return run['source_versions_json']

def doc(c,rid,kind,approved=False):
 r=c.execute('SELECT * FROM workflow_docs WHERE run_id=? AND kind=?',(rid,kind)).fetchone()
 if not r: fail('REVIEW_REQUIRED',f'{kind} must be generated first')
 x=dict(r); x['payload']=json.loads(x['payload'])
 if approved and x['state']!='APPROVED': fail('REVIEW_REQUIRED',f'{kind} must be approved')
 if x['source_signature']!=signature(load_run(c,rid)): fail('STALE_SOURCE',f'{kind} sources changed')
 return x

def log(c,rid,action,details):
 c.execute('INSERT INTO audit_events VALUES (?,?,?,?,?)',(str(uuid.uuid4()),rid,action,json.dumps(details,ensure_ascii=False),utc_now()))

def llm_generate(rid,task,system,payload):
 """Gemini drafts only; original grounding validation and human gates follow."""
 from services.gemini import generate, GeminiError
 model=os.environ.get('PROJECT07_GEMINI_MODEL','gemini-3.8-flash').strip().removeprefix('models/')
 start=time.monotonic(); outcome='ERROR'
 try:
  value,model=generate(task,system,payload)
  outcome='LIVE_SUCCESS'
  return value,model
 except GeminiError as exc:
  fail(exc.code,exc.message,exc.status)
 finally:
  with transaction() as c:
   c.execute('INSERT INTO llm_calls VALUES(?,?,?,?,?,?,?)',(str(uuid.uuid4()),rid,task,model,int((time.monotonic()-start)*1000),outcome,utc_now()))

def save_doc(rid,kind,content,model):
 with transaction() as c:
  run=load_run(c,rid)
  old=c.execute('SELECT state FROM workflow_docs WHERE run_id=? AND kind=?',(rid,kind)).fetchone()
  if c.execute("SELECT 1 FROM workflow_docs WHERE run_id=? AND kind='REPORT' AND state='APPROVED'",(rid,)).fetchone(): fail('REVIEW_REQUIRED','Reviewed report is locked; create a new run')
  if old and old['state']=='APPROVED': fail('REVIEW_REQUIRED',f'{kind} approved; create a new Audit Run to regenerate')
  if old: c.execute('DELETE FROM workflow_docs WHERE run_id=? AND kind=?',(rid,kind))
  if kind=='FINDINGS':
   # A regenerated finding draft invalidates previous reviews and any dependent draft report.
   c.execute('DELETE FROM finding_reviews WHERE run_id=?',(rid,))
   c.execute("DELETE FROM workflow_docs WHERE run_id=? AND kind='REPORT'",(rid,))
  ident=str(uuid.uuid4()); c.execute('INSERT INTO workflow_docs(id,run_id,kind,state,payload,source_signature,model,created_at) VALUES(?,?,?,?,?,?,?,?)',(ident,rid,kind,'DRAFT',json.dumps(content,ensure_ascii=False),signature(run),model,utc_now()))
  log(c,rid,kind+'_GENERATED',{'doc_id':ident,'model':model})
  return {'id':ident,'kind':kind,'state':'DRAFT','model':model,'payload':content}

def claim(item,mandatory):
 if not isinstance(item,dict) or any(not isinstance(item.get(k),str) or not item[k].strip() for k in mandatory): fail('MODEL_SCHEMA_ERROR','Model item missing required fields: '+','.join(mandatory),422)

@router.get('/api/snapshots')
def snapshots(request:Request):
 with connect() as c: values=[dict(x) for x in c.execute('SELECT snapshot_id,source_type,logical_id,version,filename,sha256,imported_at FROM snapshots ORDER BY imported_at DESC')]
 return wrap(request,values)

@router.get('/api/audit-runs')
def runs(request:Request):
 with connect() as c: values=[dict(x) for x in c.execute('SELECT run_id,audit_name,status,created_at FROM audit_runs ORDER BY created_at DESC')]
 return wrap(request,values)

@router.get('/api/audit-runs/{run_id}/workflow')
def workflow(request:Request,run_id:str):
 with connect() as c:
  run=load_run(c,run_id)
  docs=[dict(x) for x in c.execute('SELECT * FROM workflow_docs WHERE run_id=?',(run_id,))]
  for d in docs: d['payload']=json.loads(d['payload']); d['stale']=d['source_signature']!=signature(run)
  reviews=[dict(x) for x in c.execute('SELECT rr.result_id,rr.review_state,rr.reviewer,rr.reason,rr.reviewed_at FROM result_reviews rr JOIN rule_results x ON rr.result_id=x.result_id WHERE x.run_id=?',(run_id,))]
  finding_reviews=[dict(x) for x in c.execute('SELECT * FROM finding_reviews WHERE run_id=?',(run_id,))]
 return wrap(request,{'run':run,'documents':docs,'result_reviews':reviews,'finding_reviews':finding_reviews},run_id)

@router.post('/api/audit-runs/{run_id}/rcm/generate')
def rcm_generate(request:Request,run_id:str):
 with connect() as c:
  run=load_run(c,run_id)
  source=c.execute('SELECT extracted_text FROM policy_texts WHERE snapshot_id=?',(run['policy_snapshot_id'],)).fetchone()
  if not source: fail('MISSING_EVIDENCE','Policy text unavailable')
  policy=source[0]
  if len(policy)>25000: fail('CONTEXT_LIMIT','Policy exceeds demo context budget; human must select a reviewed scope',422)
 prompt='Extract internal audit risk-control matrix (RCM) from policy. JSON shape: {"controls":[{"control_id":"C01","risk":"...","control":"...","clause":"...","source_quote":"exact contiguous quote","test_ids":["T01"]}],"limitations":["..."]}. Extract controls for T01 segregation, T02 approval limit and T03 pre-disbursement only; cover all three. Other policy requirements go in limitations. Only source-grounded controls. Never invent quotations or thresholds.'
 result,model=llm_generate(run_id,'LLM1_RCM',prompt,{'policy_text':policy})
 items=result.get('controls')
 if not isinstance(items,list) or not items: fail('MODEL_SCHEMA_ERROR','No controls in RCM',422)
 seen=set()
 for item in items:
  if not isinstance(item,dict): fail('MODEL_SCHEMA_ERROR','Control must be an object',422)
  if not isinstance(item.get('test_ids'),list) or not item['test_ids'] or any(x not in ('T01','T02','T03') for x in item['test_ids']): fail('MODEL_SCHEMA_ERROR','Control requires supported test_ids',422)
  claim(item,['control_id','risk','control','clause','source_quote'])
  if item['control_id'] in seen: fail('MODEL_SCHEMA_ERROR','Duplicate control_id',422)
  seen.add(item['control_id'])
  if item['source_quote'].strip() not in policy: fail('MISSING_EVIDENCE','RCM quote is not contained verbatim in source policy',422)
 return wrap(request,save_doc(run_id,'RCM',result,model),run_id)

@router.post('/api/audit-runs/{run_id}/rcm/approve')
def rcm_approve(request:Request,run_id:str,payload:dict): return approve(request,run_id,'RCM',payload)

@router.post('/api/audit-runs/{run_id}/test-plan/generate')
def plan_generate(request:Request,run_id:str):
 with connect() as c: rcm=doc(c,run_id,'RCM',True)
 prompt='Create audit test plan using approved RCM. JSON: {"tests":[{"test_id":"T01","control_id":"...","purpose":"...","evidence_required":"...","applicability":"...","support":"SUPPORTED or UNSUPPORTED_REQUIREMENT"}],"limitations":[]}. Include all three executable tests T01,T02,T03 exactly once, linked to the approved RCM control test_ids; anything else UNSUPPORTED_REQUIREMENT. No rule threshold changes.'
 result,model=llm_generate(run_id,'LLM2_PLAN',prompt,{'approved_rcm':rcm['payload'],'supported_tests':['T01','T02','T03']})
 items=result.get('tests')
 if not isinstance(items,list) or not items: fail('MODEL_SCHEMA_ERROR','No test plan',422)
 controls={x['control_id']:x for x in rcm['payload']['controls']}; seen=set()
 for item in items:
  claim(item,['test_id','control_id','purpose','evidence_required','applicability','support'])
  if item['support'] not in ('SUPPORTED','UNSUPPORTED_REQUIREMENT'): fail('MODEL_SCHEMA_ERROR','Invalid support status',422)
  if item['control_id'] not in controls: fail('MISSING_EVIDENCE','Test references unknown RCM control',422)
  if item['test_id'] in seen: fail('MODEL_SCHEMA_ERROR','Duplicate test_id',422)
  seen.add(item['test_id'])
  if item['support']=='SUPPORTED' and (item['test_id'] not in ('T01','T02','T03') or item['test_id'] not in controls[item['control_id']]['test_ids']): fail('MODEL_SCHEMA_ERROR','Test not supported by approved RCM mapping',422)
 supported={x['test_id'] for x in items if x['support']=='SUPPORTED'}
 if supported!={'T01','T02','T03'}: fail('INCOMPLETE_PLAN','Baseline demo requires approved coverage of T01, T02 and T03',422)
 return wrap(request,save_doc(run_id,'PLAN',result,model),run_id)

@router.post('/api/audit-runs/{run_id}/test-plan/approve')
def plan_approve(request:Request,run_id:str,payload:dict): return approve(request,run_id,'PLAN',payload)

def approve(request,rid,kind,payload):
 reviewer=str(payload.get('reviewer','')).strip(); reason=str(payload.get('reason','')).strip()
 if not reviewer or not reason: fail('VALIDATION_ERROR','Reviewer and reason are required',422)
 with transaction() as c:
  d=doc(c,rid,kind)
  if kind=='PLAN': doc(c,rid,'RCM',True)
  if d['state']!='DRAFT': fail('REVIEW_REQUIRED','Document not in DRAFT state')
  c.execute('UPDATE workflow_docs SET state=?,reviewed_by=?,reviewed_at=?,review_note=? WHERE id=?',('APPROVED',reviewer,utc_now(),reason,d['id']))
  log(c,rid,kind+'_APPROVED',{'reviewer':reviewer,'reason':reason,'identity':'SELF_DECLARED_DEMO'})
 return wrap(request,{'kind':kind,'state':'APPROVED','reviewer':reviewer,'identity':'SELF_DECLARED_DEMO'},rid)

@router.post('/api/audit-runs/{run_id}/results/{result_id}/review')
def review_result(request:Request,run_id:str,result_id:str,payload:dict):
 reviewer=str(payload.get('reviewer','')).strip(); reason=str(payload.get('reason','')).strip(); decision=payload.get('review_state')
 if decision not in ('CONFIRMED','NEEDS_FOLLOWUP','REJECTED') or not reviewer or not reason: fail('VALIDATION_ERROR','review_state, reviewer and reason required',422)
 with transaction() as c:
  load_run(c,run_id)
  if c.execute("SELECT 1 FROM workflow_docs WHERE run_id=? AND kind='REPORT' AND state='APPROVED'",(run_id,)).fetchone(): fail('REVIEW_REQUIRED','Reviewed report is locked; create a new run')
  c.execute("DELETE FROM workflow_docs WHERE run_id=? AND kind IN ('FINDINGS','REPORT')",(run_id,))
  c.execute('DELETE FROM finding_reviews WHERE run_id=?',(run_id,))
  if not c.execute('SELECT 1 FROM rule_results WHERE run_id=? AND result_id=?',(run_id,result_id)).fetchone(): fail('NOT_FOUND','Result not in Audit Run',404)
  c.execute('INSERT INTO result_reviews VALUES(?,?,?,?,?) ON CONFLICT(result_id) DO UPDATE SET review_state=excluded.review_state,reviewer=excluded.reviewer,reason=excluded.reason,reviewed_at=excluded.reviewed_at',(result_id,decision,reviewer,reason,utc_now()))
  log(c,run_id,'RESULT_REVIEWED',{'result_id':result_id,'review_state':decision,'reviewer':reviewer,'reason':reason})
 return wrap(request,{'result_id':result_id,'review_state':decision},run_id)

@router.post('/api/audit-runs/{run_id}/findings/generate')
def finding_generate(request:Request,run_id:str):
 with connect() as c:
  doc(c,run_id,'PLAN',True); rcm=doc(c,run_id,'RCM',True); run=load_run(c,run_id)
  records=[json.loads(r[0]) for r in c.execute('SELECT result_json FROM rule_results WHERE run_id=? ORDER BY source_line,test_id',(run_id,))]
  cases=[r for r in records if r['test_result']=='EXCEPTION']
  reviews={r['result_id']:r['review_state'] for r in c.execute('SELECT rr.* FROM result_reviews rr JOIN rule_results x ON rr.result_id=x.result_id WHERE x.run_id=?',(run_id,))}
  if not cases: fail('MISSING_EVIDENCE','No exception evidence available')
  if any(reviews.get(r['result_id']) not in ('CONFIRMED','REJECTED') for r in cases): fail('REVIEW_REQUIRED','Human must resolve every exception before finding generation')
  cases=[r for r in cases if reviews.get(r['result_id'])=='CONFIRMED']
  if not cases: fail('MISSING_EVIDENCE','No human-confirmed exceptions')
  if len(cases)>60: fail('CONTEXT_LIMIT','More than 60 exceptions; human must select a smaller reviewed audit scope',422)
  rows={r['row_id']:json.loads(r['payload_json']) for r in c.execute('SELECT * FROM loan_rows WHERE snapshot_id=?',(run['dataset_snapshot_id'],))}
  inp=[dict(r,observed_values={k:rows[r['row_id']].get(k) for k in r['evidence_refs'][0]['fields']}) for r in cases]
 prompt='Draft audit findings from human-confirmed exceptions and approved RCM. JSON: {"findings":[{"finding_key":"F01","title":"...","control_id":"existing RCM id","criteria":"...","source_quote":"exact quote of that approved control","condition":"...","risk":"potential risk, not assertion","recommendation":"...","evidence_result_ids":["existing id"]}],"limitations":[]}. Group by test/control; at least 2 findings when exceptions cover at least 2 test types. Cover every supplied exception at least once. No unsupported root causes, allegations or losses.'
 result,model=llm_generate(run_id,'LLM3_FINDINGS',prompt,{'exceptions':inp,'approved_rcm':rcm['payload'],'policy_snapshot_id':run['policy_snapshot_id']})
 items=result.get('findings')
 if not isinstance(items,list) or not items: fail('MODEL_SCHEMA_ERROR','No findings',422)
 known={x['result_id']:x for x in inp}; keys=set(); covered=set(); controls={x['control_id']:x for x in rcm['payload']['controls']}
 for item in items:
  claim(item,['finding_key','title','control_id','criteria','source_quote','condition','risk','recommendation'])
  refs=item.get('evidence_result_ids')
  if not isinstance(refs,list) or not refs or any(not isinstance(x,str) for x in refs) or not set(refs)<=set(known): fail('MISSING_EVIDENCE','Finding references nonexistent/non-exception evidence',422)
  control=controls.get(item['control_id'])
  if not control or item['source_quote']!=control['source_quote']: fail('MISSING_EVIDENCE','Finding criteria lacks approved policy quotation',422)
  if any(known[x]['test_id'] not in control['test_ids'] for x in refs): fail('MISSING_EVIDENCE','Finding evidence mismatches control test mapping',422)
  item['criteria_evidence']={'policy_snapshot_id':run['policy_snapshot_id'],'control_id':control['control_id'],'clause':control['clause'],'source_quote':control['source_quote']}
  item['evidence_details']=[known[x] for x in refs]; covered.update(refs)
  if item['finding_key'] in keys: fail('MODEL_SCHEMA_ERROR','Duplicate finding_key',422)
  keys.add(item['finding_key'])
 if covered!=set(known): fail('INCOMPLETE_FINDINGS','Not all confirmed exceptions are linked',422)
 if len({x['test_id'] for x in inp})>=2 and len(items)<2: fail('INCOMPLETE_FINDINGS','At least 2 findings required for multiple exception test types',422)
 return wrap(request,save_doc(run_id,'FINDINGS',result,model),run_id)

@router.post('/api/findings/{finding_id}/review')
def finding_review(request:Request,finding_id:str,payload:dict):
 rid=str(payload.get('run_id','')); reviewer=str(payload.get('reviewer','')).strip(); reason=str(payload.get('reason','')).strip(); state=payload.get('state')
 if state not in ('CONFIRMED','NEEDS_FOLLOWUP','REJECTED') or not reviewer or not reason: fail('VALIDATION_ERROR','state, reviewer, reason required',422)
 with transaction() as c:
  d=doc(c,rid,'FINDINGS')
  if c.execute("SELECT 1 FROM workflow_docs WHERE run_id=? AND kind='REPORT' AND state='APPROVED'",(rid,)).fetchone(): fail('REVIEW_REQUIRED','Reviewed report is locked; create a new run')
  c.execute("DELETE FROM workflow_docs WHERE run_id=? AND kind='REPORT'",(rid,))
  found=next((x for x in d['payload']['findings'] if x['finding_key']==finding_id),None)
  if not found: fail('NOT_FOUND','Finding not found',404)
  c.execute('INSERT INTO finding_reviews VALUES(?,?,?,?,?,?) ON CONFLICT(run_id,finding_key) DO UPDATE SET state=excluded.state,reviewer=excluded.reviewer,reason=excluded.reason,reviewed_at=excluded.reviewed_at',(rid,finding_id,state,reviewer,reason,utc_now()))
  log(c,rid,'FINDING_REVIEWED',{'finding_key':finding_id,'state':state,'reviewer':reviewer,'reason':reason})
 return wrap(request,{'finding_key':finding_id,'state':state},rid)

@router.post('/api/audit-runs/{run_id}/report/generate')
def report_generate(request:Request,run_id:str):
 with connect() as c:
  d=doc(c,run_id,'FINDINGS'); found=d['payload']['findings']
  reviews={r['finding_key']:r['state'] for r in c.execute('SELECT finding_key,state FROM finding_reviews WHERE run_id=?',(run_id,))}
  if any(reviews.get(x['finding_key'])!='CONFIRMED' for x in found): fail('REVIEW_REQUIRED','All findings must be confirmed before report drafting')
  counts={r['test_result']:r['n'] for r in c.execute('SELECT json_extract(result_json,"$.test_result") test_result, COUNT(*) n FROM rule_results WHERE run_id=? GROUP BY test_result',(run_id,))}
 prompt='Write draft internal audit report strictly as a JSON object {"executive_summary":"...","scope":"...","methods":"...","findings_summary":"...","limitations":"...","recommendations":"..."}. Discuss only supplied reviewed findings and deterministic counts. Do not claim fraud/loss. Include limitations for all unreviewed/incomplete cases.'
 result,model=llm_generate(run_id,'LLM4_REPORT',prompt,{'reviewed_findings':found,'counts':counts,'pending_result_reviews':sum(x['review_state'] not in ('CONFIRMED','REJECTED') for x in records_pending(run_id)),'identity':'SELF_DECLARED_DEMO'})
 for k in ['executive_summary','scope','methods','findings_summary','limitations','recommendations']:
  if not isinstance(result.get(k),str) or not result[k].strip(): fail('MODEL_SCHEMA_ERROR','Report missing '+k,422)
 result['deterministic_counts']=counts; result['publication_status']='DRAFT'; result['evidence_appendix']=found
 result['pending_result_reviews']=sum(1 for x in records_pending(run_id) if x['review_state'] not in ('CONFIRMED','REJECTED'))
 return wrap(request,save_doc(run_id,'REPORT',result,model),run_id)

def records_pending(rid):
 with connect() as c:
  return [dict(x) for x in c.execute("SELECT COALESCE(rr.review_state,'PENDING') review_state FROM rule_results r LEFT JOIN result_reviews rr ON r.result_id=rr.result_id WHERE r.run_id=?",(rid,))]

@router.post('/api/audit-runs/{run_id}/report/approve')
def report_approve(request:Request,run_id:str,payload:dict):
 with connect() as c:
  d=doc(c,run_id,'FINDINGS')
  reviews={r['finding_key']:r['state'] for r in c.execute('SELECT * FROM finding_reviews WHERE run_id=?',(run_id,))}
  if any(reviews.get(x['finding_key'])!='CONFIRMED' for x in d['payload']['findings']): fail('REVIEW_REQUIRED','All findings must remain confirmed')
 return approve(request,run_id,'REPORT',payload)

@router.post('/api/reports/{report_id}/finalize')
def finalize(request:Request,report_id:str,payload:dict):
 # Self-declared reviewers cannot certify a FINAL report in this local demo.
 fail('FINALIZE_BLOCKED','Production verified authentication/authorization is not configured; report remains DRAFT')

@router.get('/api/audit-runs/{run_id}/evaluation')
def evaluation(request:Request,run_id:str):
 with connect() as c:
  load_run(c,run_id)
  documents={r['kind']:json.loads(r['payload']) for r in c.execute('SELECT kind,payload FROM workflow_docs WHERE run_id=?',(run_id,))}
  counts={r['result']:r['n'] for r in c.execute('SELECT json_extract(result_json,"$.test_result") result,COUNT(*) n FROM rule_results WHERE run_id=? GROUP BY result',(run_id,))}
  calls=[dict(x) for x in c.execute('SELECT task,model,latency_ms,status,created_at FROM llm_calls WHERE run_id=? ORDER BY created_at',(run_id,))]
  total=sum(counts.values()); review_count=c.execute('SELECT COUNT(*) FROM result_reviews WHERE result_id IN (SELECT result_id FROM rule_results WHERE run_id=?)',(run_id,)).fetchone()[0]
 controls=documents.get('RCM',{}).get('controls',[]); tests=documents.get('PLAN',{}).get('tests',[]); findings=documents.get('FINDINGS',{}).get('findings',[])
 all_refs=[x for f in findings for x in f.get('evidence_result_ids',[])]
 with connect() as c:
  valid={r[0] for r in c.execute('SELECT result_id FROM rule_results WHERE run_id=?',(run_id,))}
  source=c.execute('SELECT p.extracted_text FROM policy_texts p JOIN audit_runs a ON a.policy_snapshot_id=p.snapshot_id WHERE a.run_id=?',(run_id,)).fetchone()[0]
 structural={'quote_match_rate':sum(bool(x.get('source_quote')) and x['source_quote'] in source for x in controls)/len(controls) if controls else None,'test_coverage':len({x['test_id'] for x in tests if x.get('support')=='SUPPORTED'} & {'T01','T02','T03'})/3 if tests else None,'evidence_link_integrity':sum(x in valid for x in all_refs)/len(all_refs) if all_refs else None,'mean_llm_latency_ms':round(sum(x['latency_ms'] for x in calls)/len(calls)) if calls else None,'note':'Structural checks only; quote presence does not prove semantic groundedness. Timing includes failed calls.'}
 return wrap(request,{'regression_benchmark':benchmark(),'structural_metrics':structural,'counts':counts,'total':total,'reviewed':review_count,'llm_calls':calls,'accuracy':None,'precision':None,'recall':None,'groundedness':None,'note':'Metrics requiring independently sealed ground truth not computed from production data.'},run_id)

@router.get('/api/audit-runs/{run_id}/events')
def events(request:Request,run_id:str):
 with connect() as c:
  load_run(c,run_id)
  rows=[dict(x) for x in c.execute('SELECT action,details_json,created_at FROM audit_events WHERE run_id=? ORDER BY created_at',(run_id,))]
 return wrap(request,rows,run_id)
