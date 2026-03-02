"""
Governance System for StepbyStep:ROBOTICS

Enforces policies, manages approvals, and maintains audit trails for robot operations.
Provides compliance reporting and policy-governed action execution.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4
import hashlib
import json


class PolicyDecisionType(Enum):
    """Policy decision outcomes"""
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


class PolicySeverity(Enum):
    """Policy violation severity levels"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ApprovalStatus(Enum):
    """Approval request status"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


@dataclass
class ProposedAction:
    """Action proposed for policy evaluation"""
    action_id: UUID
    action_type: str
    target: str
    parameters: Dict[str, Any]
    actor_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def is_well_formed(self) -> bool:
        """Validate action structure"""
        return (
            self.action_id is not None and
            bool(self.action_type) and
            bool(self.target) and
            self.parameters is not None and
            bool(self.actor_id)
        )


@dataclass
class ExecutionContext:
    """Context for policy evaluation"""
    robot_state: Optional[Dict[str, Any]] = None
    environment: Optional[Dict[str, Any]] = None
    operator: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def is_valid(self) -> bool:
        """Validate context has required information"""
        return self.timestamp is not None


@dataclass
class PolicyViolation:
    """Details of a policy violation"""
    policy_id: UUID
    policy_name: str
    reason: str
    severity: PolicySeverity


@dataclass
class PolicyDecision:
    """Result of policy evaluation"""
    action_id: UUID
    result: PolicyDecisionType
    violations: List[PolicyViolation] = field(default_factory=list)
    explanation: str = ""
    approval_workflow: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Policy:
    """Policy definition"""
    policy_id: UUID
    name: str
    description: str
    priority: int  # Higher number = higher priority
    severity: PolicySeverity
    rule: callable  # Function that evaluates the policy
    approval_workflow: Optional[str] = None
    active: bool = True


@dataclass
class AuditEntry:
    """Immutable audit log entry"""
    entry_id: UUID
    timestamp: datetime
    action_type: str
    actor_id: str
    actor_type: str  # "operator" or "robot"
    target: str
    decision: Optional[PolicyDecisionType] = None
    details: Dict[str, Any] = field(default_factory=dict)
    signature: str = ""  # Cryptographic signature for tamper detection
    
    def compute_signature(self, secret_key: str) -> str:
        """Compute cryptographic signature for tamper detection"""
        data = f"{self.entry_id}|{self.timestamp.isoformat()}|{self.action_type}|{self.actor_id}|{self.target}"
        return hashlib.sha256(f"{data}|{secret_key}".encode()).hexdigest()
    
    def verify_signature(self, secret_key: str) -> bool:
        """Verify audit entry has not been tampered with"""
        expected = self.compute_signature(secret_key)
        return self.signature == expected


@dataclass
class ApprovalRequest:
    """Request for approval of a proposed change"""
    request_id: UUID
    action: ProposedAction
    workflow: str
    requester: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    approver: Optional[str] = None
    decision_time: Optional[datetime] = None
    rationale: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


@dataclass
class ComplianceReport:
    """Compliance report for a time period"""
    report_id: UUID
    start_time: datetime
    end_time: datetime
    total_actions: int
    policy_evaluations: int
    violations: List[PolicyViolation]
    approval_requests: int
    approved: int
    denied: int
    compliance_rate: float
    standards: List[str] = field(default_factory=list)  # e.g., ["ISO 27001", "SOC 2 Type II"]
    generated_at: datetime = field(default_factory=datetime.utcnow)


class GovernanceSystem:
    """
    Governance System for policy enforcement, audit trails, and compliance.
    
    Responsibilities:
    - Enforce safety and operational policies
    - Manage approval workflows for critical changes
    - Maintain comprehensive audit trails
    - Generate compliance and governance reports
    """
    
    def __init__(self, secret_key: str = "default-secret-key"):
        self.policies: Dict[UUID, Policy] = {}
        self.audit_log: List[AuditEntry] = []
        self.approval_requests: Dict[UUID, ApprovalRequest] = {}
        self.secret_key = secret_key
    
    def add_policy(self, policy: Policy) -> None:
        """Add a policy to the system"""
        if not policy.active:
            return
        self.policies[policy.policy_id] = policy
    
    def remove_policy(self, policy_id: UUID) -> None:
        """Remove a policy from the system"""
        if policy_id in self.policies:
            del self.policies[policy_id]
    
    def get_active_policies(self) -> List[Policy]:
        """Get all active policies sorted by priority (highest first)"""
        active = [p for p in self.policies.values() if p.active]
        return sorted(active, key=lambda p: p.priority, reverse=True)
    
    def enforce_policy(self, action: ProposedAction, context: ExecutionContext) -> PolicyDecision:
        """
        Evaluate action against all active policies.
        
        Preconditions:
        - action is well-formed
        - context is valid
        - All policies are loaded and active
        - Policies are consistent (no contradictions)
        
        Postconditions:
        - Returns ALLOW, DENY, or REQUIRE_APPROVAL decision
        - If DENY, includes violated policies with explanations
        - If REQUIRE_APPROVAL, includes workflow details
        - Decision is deterministic for same inputs
        - Audit entry is created
        - Critical violations result in immediate DENY
        """
        if not action.is_well_formed():
            raise ValueError("Action is not well-formed")
        
        if not context.is_valid():
            raise ValueError("Context is not valid")
        
        decision = PolicyDecision(
            action_id=action.action_id,
            result=PolicyDecisionType.ALLOW
        )
        
        policies = self.get_active_policies()
        violated_policies: List[PolicyViolation] = []
        requires_approval = False
        approval_workflow = None
        
        # Evaluate policies in priority order
        for policy in policies:
            try:
                evaluation_result = policy.rule(action, context)
                
                if evaluation_result == "DENY":
                    violation = PolicyViolation(
                        policy_id=policy.policy_id,
                        policy_name=policy.name,
                        reason=f"Policy '{policy.name}' violated",
                        severity=policy.severity
                    )
                    violated_policies.append(violation)
                    
                    # Critical policy violation - immediate deny
                    if policy.severity == PolicySeverity.CRITICAL:
                        decision.result = PolicyDecisionType.DENY
                        decision.violations = violated_policies
                        decision.explanation = f"Critical policy violation: {policy.name}"
                        self._audit_policy_decision(decision, action, context)
                        return decision
                
                elif evaluation_result == "REQUIRE_APPROVAL":
                    requires_approval = True
                    approval_workflow = policy.approval_workflow
            
            except Exception as e:
                # Policy evaluation error - treat as violation for safety
                violation = PolicyViolation(
                    policy_id=policy.policy_id,
                    policy_name=policy.name,
                    reason=f"Policy evaluation error: {str(e)}",
                    severity=PolicySeverity.HIGH
                )
                violated_policies.append(violation)
        
        # Determine final decision
        if violated_policies:
            decision.result = PolicyDecisionType.DENY
            decision.violations = violated_policies
            decision.explanation = self._generate_violation_summary(violated_policies)
        elif requires_approval:
            decision.result = PolicyDecisionType.REQUIRE_APPROVAL
            decision.approval_workflow = approval_workflow
            decision.explanation = "Action requires approval per policy"
        else:
            decision.result = PolicyDecisionType.ALLOW
            decision.explanation = "Action complies with all policies"
        
        # Create audit entry
        self._audit_policy_decision(decision, action, context)
        
        return decision
    
    def request_approval(self, action: ProposedAction, workflow: str, 
                        requester: str, expires_in_hours: int = 24) -> ApprovalRequest:
        """
        Create an approval request for a proposed change.
        
        Returns:
            ApprovalRequest with unique ID and PENDING status
        """
        request = ApprovalRequest(
            request_id=uuid4(),
            action=action,
            workflow=workflow,
            requester=requester,
            expires_at=datetime.utcnow() + timedelta(hours=expires_in_hours)
        )
        
        self.approval_requests[request.request_id] = request
        
        # Audit the approval request
        self.audit_action(
            action_type="APPROVAL_REQUEST",
            actor_id=requester,
            actor_type="operator",
            target=action.target,
            details={"request_id": str(request.request_id), "workflow": workflow}
        )
        
        return request
    
    def approve_request(self, request_id: UUID, approver: str, rationale: str = "") -> ApprovalRequest:
        """Approve an approval request"""
        if request_id not in self.approval_requests:
            raise ValueError(f"Approval request {request_id} not found")
        
        request = self.approval_requests[request_id]
        
        if request.status != ApprovalStatus.PENDING:
            raise ValueError(f"Request {request_id} is not pending (status: {request.status})")
        
        if request.expires_at and datetime.utcnow() > request.expires_at:
            request.status = ApprovalStatus.EXPIRED
            raise ValueError(f"Request {request_id} has expired")
        
        request.status = ApprovalStatus.APPROVED
        request.approver = approver
        request.decision_time = datetime.utcnow()
        request.rationale = rationale
        
        # Audit the approval
        self.audit_action(
            action_type="APPROVAL_GRANTED",
            actor_id=approver,
            actor_type="operator",
            target=request.action.target,
            details={"request_id": str(request_id), "rationale": rationale}
        )
        
        return request
    
    def reject_request(self, request_id: UUID, approver: str, rationale: str = "") -> ApprovalRequest:
        """Reject an approval request"""
        if request_id not in self.approval_requests:
            raise ValueError(f"Approval request {request_id} not found")
        
        request = self.approval_requests[request_id]
        
        if request.status != ApprovalStatus.PENDING:
            raise ValueError(f"Request {request_id} is not pending (status: {request.status})")
        
        request.status = ApprovalStatus.REJECTED
        request.approver = approver
        request.decision_time = datetime.utcnow()
        request.rationale = rationale
        
        # Audit the rejection
        self.audit_action(
            action_type="APPROVAL_REJECTED",
            actor_id=approver,
            actor_type="operator",
            target=request.action.target,
            details={"request_id": str(request_id), "rationale": rationale}
        )
        
        return request
    
    def audit_action(self, action_type: str, actor_id: str, actor_type: str,
                    target: str, decision: Optional[PolicyDecisionType] = None,
                    details: Optional[Dict[str, Any]] = None) -> AuditEntry:
        """
        Create an immutable audit entry.
        
        Postconditions:
        - Entry has unique ID and timestamp
        - Entry is cryptographically signed
        - Entry is appended to audit log
        """
        entry = AuditEntry(
            entry_id=uuid4(),
            timestamp=datetime.utcnow(),
            action_type=action_type,
            actor_id=actor_id,
            actor_type=actor_type,
            target=target,
            decision=decision,
            details=details or {}
        )
        
        # Compute cryptographic signature
        entry.signature = entry.compute_signature(self.secret_key)
        
        # Append to audit log (immutable)
        self.audit_log.append(entry)
        
        return entry
    
    def generate_compliance_report(self, start_time: datetime, end_time: datetime,
                                   standards: Optional[List[str]] = None) -> ComplianceReport:
        """
        Generate compliance report for a time range.
        
        Postconditions:
        - Report covers all actions in time range
        - Includes policy compliance statistics
        - Includes audit trail summaries
        - Identifies policy violations and anomalies
        """
        # Filter audit entries in time range
        entries = [
            e for e in self.audit_log
            if start_time <= e.timestamp <= end_time
        ]
        
        # Count actions and decisions
        total_actions = len(entries)
        policy_evaluations = len([e for e in entries if e.decision is not None])
        
        # Extract violations from audit log
        violations: List[PolicyViolation] = []
        for entry in entries:
            if entry.decision == PolicyDecisionType.DENY and "violations" in entry.details:
                for v in entry.details["violations"]:
                    violations.append(PolicyViolation(
                        policy_id=UUID(v["policy_id"]),
                        policy_name=v["policy_name"],
                        reason=v["reason"],
                        severity=PolicySeverity[v["severity"]]
                    ))
        
        # Count approval requests
        approval_entries = [e for e in entries if e.action_type in ["APPROVAL_REQUEST", "APPROVAL_GRANTED", "APPROVAL_REJECTED"]]
        approval_requests = len([e for e in approval_entries if e.action_type == "APPROVAL_REQUEST"])
        approved = len([e for e in approval_entries if e.action_type == "APPROVAL_GRANTED"])
        denied = len([e for e in approval_entries if e.action_type == "APPROVAL_REJECTED"])
        
        # Calculate compliance rate
        compliance_rate = 1.0 - (len(violations) / max(policy_evaluations, 1))
        
        report = ComplianceReport(
            report_id=uuid4(),
            start_time=start_time,
            end_time=end_time,
            total_actions=total_actions,
            policy_evaluations=policy_evaluations,
            violations=violations,
            approval_requests=approval_requests,
            approved=approved,
            denied=denied,
            compliance_rate=compliance_rate,
            standards=standards or ["ISO 27001", "SOC 2 Type II"]
        )
        
        return report
    
    def search_audit_log(self, action_type: Optional[str] = None,
                        actor_id: Optional[str] = None,
                        start_time: Optional[datetime] = None,
                        end_time: Optional[datetime] = None) -> List[AuditEntry]:
        """Search audit log with filters"""
        results = self.audit_log.copy()
        
        if action_type:
            results = [e for e in results if e.action_type == action_type]
        
        if actor_id:
            results = [e for e in results if e.actor_id == actor_id]
        
        if start_time:
            results = [e for e in results if e.timestamp >= start_time]
        
        if end_time:
            results = [e for e in results if e.timestamp <= end_time]
        
        return results
    
    def verify_audit_integrity(self) -> bool:
        """Verify all audit entries have valid signatures"""
        return all(entry.verify_signature(self.secret_key) for entry in self.audit_log)
    
    def _audit_policy_decision(self, decision: PolicyDecision, action: ProposedAction,
                               context: ExecutionContext) -> None:
        """Internal method to audit policy decisions"""
        details = {
            "action_type": action.action_type,
            "target": action.target,
            "result": decision.result.value,
            "explanation": decision.explanation
        }
        
        if decision.violations:
            details["violations"] = [
                {
                    "policy_id": str(v.policy_id),
                    "policy_name": v.policy_name,
                    "reason": v.reason,
                    "severity": v.severity.value
                }
                for v in decision.violations
            ]
        
        self.audit_action(
            action_type="POLICY_EVALUATION",
            actor_id=action.actor_id,
            actor_type="operator" if context.operator else "robot",
            target=action.target,
            decision=decision.result,
            details=details
        )
    
    def _generate_violation_summary(self, violations: List[PolicyViolation]) -> str:
        """Generate human-readable summary of policy violations"""
        if not violations:
            return "No violations"
        
        summary_parts = []
        for v in violations:
            summary_parts.append(f"{v.policy_name} ({v.severity.value}): {v.reason}")
        
        return "; ".join(summary_parts)
