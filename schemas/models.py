from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum
import uuid
from datetime import datetime


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertPayload(BaseModel):
    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    service: str
    severity: AlertSeverity
    timestamp: str
    description: str
    metadata: Dict[str, Any] = {}


class IncidentStatus(str, Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class IncidentSummary(BaseModel):
    incident_id: str
    status: IncidentStatus
    service: Optional[str] = None
    severity: Optional[str] = None
    decision: Optional[str] = None
    created_at: str


class IncidentResponse(BaseModel):
    incident_id: str
    status: IncidentStatus
    alert: Optional[Dict[str, Any]] = None
    investigation_plan: Optional[str] = None
    log_findings: Optional[Dict[str, Any]] = None
    metrics_findings: Optional[Dict[str, Any]] = None
    deploy_findings: Optional[Dict[str, Any]] = None
    reasoning_summary: Optional[str] = None
    decision: Optional[str] = None
    action_taken: Optional[str] = None
    report: Optional[Dict[str, Any]] = None
    email_sent: Optional[bool] = None
    error: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
