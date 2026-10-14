"""Deterministic P2 tests; no ground truth or LLM access at runtime."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

PASS='PASS'; EXCEPTION='EXCEPTION'; INSUFFICIENT='INSUFFICIENT_INFORMATION'
BLOCKED='BLOCKED'; OUT_OF_SCOPE='OUT_OF_SCOPE'; NOT_APPLICABLE='NOT_APPLICABLE'
BASELINE='BASELINE::POL-LOAN-01'

@dataclass(frozen=True)
class BaselineApproval:
    """Approval record is injected by the caller after independent policy verification."""
    policy_sha256: str
    approval_reference: str
    # These are expected by Project07 v1.3.3, not inferred from an uploaded policy.
    tier1_max_vnd: int = 500_000_000
    tier2_max_vnd: int = 2_000_000_000


def dt(value):
    if not value: return None
    try:
        parsed=datetime.fromisoformat(str(value).replace('Z','+00:00'))
        return parsed if parsed.tzinfo is not None and parsed.utcoffset() is not None else None
    except (ValueError, TypeError): return None


def amount(value):
    try:
        d=Decimal(str(value))
        if not d.is_finite() or d < 0 or d != d.to_integral_value(): return None
        return int(d)
    except (ValueError, TypeError, InvalidOperation): return None


def result(test_id, status, reason, loan, fields, authority_lines=()):
    evidence=[{'source':'loans','row_id':loan.get('row_id'), 'source_line':loan.get('_source_line'),
               'fields':fields}]
    evidence += [{'source':'authority','source_line':line} for line in sorted(set(authority_lines))]
    return {'test_id':test_id,'test_result':status,'review_state':'PENDING',
            'reason_code':reason,'row_id':loan.get('row_id'), 'loan_id':loan.get('loan_id'),
            'evidence_refs':evidence}


def t01(loan):
    status=str(loan.get('approval_status','')).upper()
    fields=['approval_status','maker_id','approver_id']
    if status != 'APPROVED':
        if not status: return result('T01',INSUFFICIENT,'MISSING_APPROVAL_STATUS',loan,fields)
        return result('T01',NOT_APPLICABLE,'NOT_APPROVED',loan,fields)
    if not loan.get('maker_id') or not loan.get('approver_id'):
        return result('T01',INSUFFICIENT,'MISSING_MAKER_OR_APPROVER',loan,fields)
    if loan['maker_id']==loan['approver_id']:
        return result('T01',EXCEPTION,'MAKER_EQUALS_APPROVER',loan,fields)
    return result('T01',PASS,'SEGREGATION_OK',loan,fields)


def t02(loan, authorities, approval: BaselineApproval):
    fields=['amount_vnd','currency','approver_id','approval_status','approval_time','branch_id']
    value=amount(loan.get('amount_vnd'))
    if value is None or not loan.get('currency') or not loan.get('approver_id') or not loan.get('approval_time'):
        return result('T02',INSUFFICIENT,'MISSING_AUTHORITY_INPUT',loan,fields)
    if loan['currency'] != 'VND': return result('T02',OUT_OF_SCOPE,'NON_VND',loan,fields)
    if value>approval.tier2_max_vnd: return result('T02',OUT_OF_SCOPE,'AMOUNT_ABOVE_2B',loan,fields)
    if not loan.get('branch_id'): return result('T02',INSUFFICIENT,'MISSING_BRANCH',loan,fields)
    when=dt(loan['approval_time'])
    if when is None: return result('T02',INSUFFICIENT,'INVALID_APPROVAL_TIME',loan,fields)
    eligible=[]; bad=[]
    for record in authorities:
        a=record['payload']
        if a.get('employee_id') != loan['approver_id'] or a.get('branch_id') != loan['branch_id']: continue
        start=dt(a.get('valid_from')); end=dt(a.get('valid_to'))
        if start is None or end is None or start>end or amount(a.get('authority_limit_vnd')) is None:
            bad.append(record['source_line']); continue
        if start<=when<=end: eligible.append(record)
    if bad: return result('T02',BLOCKED,'INVALID_AUTHORITY_RECORD',loan,fields,bad)
    if not eligible: return result('T02',INSUFFICIENT,'NO_ACTIVE_AUTHORITY',loan,fields)
    lines=[r['source_line'] for r in eligible]
    # Overlapping active grants may carry contradictory limits or roles: fail closed.
    identities={(r['payload'].get('role'),amount(r['payload'].get('authority_limit_vnd'))) for r in eligible}
    if len(identities)>1: return result('T02',BLOCKED,'OVERLAPPING_AUTHORITY_CONFLICT',loan,fields,lines)
    limit=next(iter(identities))[1]
    # Exactly 500M is tier 1; exactly 2B is tier 2.
    required='TIER_1' if value<=approval.tier1_max_vnd else 'TIER_2'
    if not eligible[0]['payload'].get('role'):
        return result('T02',INSUFFICIENT,'MISSING_ROLE',loan,fields,lines)
    if limit < value:
        return result('T02',EXCEPTION,'APPROVAL_LIMIT_EXCEEDED_'+required,loan,fields,lines)
    # A ceiling alone cannot prove role-based eligibility: require independently validated authority matrix.
    if not approval.approval_reference:
        return result('T02',BLOCKED,'POLICY_AUTHORITY_NOT_VERIFIED',loan,fields,lines)
    return result('T02',PASS,'WITHIN_APPROVAL_LIMIT_'+required,loan,fields,lines)


def t03(loan):
    fields=['approval_status','approval_time','disbursement_status','disbursement_time']
    disb=str(loan.get('disbursement_status','')).upper()
    if not disb: return result('T03',INSUFFICIENT,'MISSING_DISBURSEMENT_STATUS',loan,fields)
    if disb not in {'DISBURSED','NOT_DISBURSED'}:
        return result('T03',INSUFFICIENT,'UNKNOWN_DISBURSEMENT_STATUS',loan,fields)
    if disb=='NOT_DISBURSED': return result('T03',NOT_APPLICABLE,'NOT_DISBURSED',loan,fields)
    status=str(loan.get('approval_status','')).upper()
    if status=='REJECTED': return result('T03',EXCEPTION,'DISBURSED_WHILE_REJECTED',loan,fields)
    if not status: return result('T03',INSUFFICIENT,'MISSING_APPROVAL_STATUS',loan,fields)
    if status!='APPROVED': return result('T03',EXCEPTION,'DISBURSED_WITHOUT_APPROVAL',loan,fields)
    a=dt(loan.get('approval_time')); d=dt(loan.get('disbursement_time'))
    if a is None or d is None: return result('T03',INSUFFICIENT,'MISSING_OR_INVALID_TIMESTAMP',loan,fields)
    if a >= d: return result('T03',EXCEPTION,'APPROVAL_NOT_BEFORE_DISBURSEMENT',loan,fields)
    return result('T03',PASS,'APPROVED_BEFORE_DISBURSEMENT',loan,fields)


def evaluate(rows, authorities, approval):
    output=[]
    for record in rows:
        loan=dict(record['payload'],row_id=record['row_id'],_source_line=record['source_line'])
        output.extend((t01(loan),t02(loan,authorities,approval),t03(loan)))
    return output
