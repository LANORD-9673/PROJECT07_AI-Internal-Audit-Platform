from typing import Any, Literal
from pydantic import BaseModel, Field

class ErrorItem(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)

class Envelope(BaseModel):
    request_id: str
    status: Literal['success', 'error']
    data: Any = None
    errors: list[ErrorItem] = Field(default_factory=list)
    run_id: str | None = None
    source_versions: dict[str, Any] = Field(default_factory=dict)
    generated_at: str

class AuditRunCreate(BaseModel):
    policy_snapshot_id: str
    dataset_snapshot_id: str
    authority_snapshot_id: str
    audit_name: str = Field(min_length=1, max_length=200)

class AuditRunDetail(BaseModel):
    run_id: str
    audit_name: str
    status: str
    policy_snapshot_id: str
    dataset_snapshot_id: str
    authority_snapshot_id: str
    source_versions: dict[str, Any]
    created_at: str
