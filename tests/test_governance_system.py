"""
Tests for Governance System

Validates policy enforcement, audit trails, approval workflows, and compliance reporting.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4, UUID

from src.stepbystep_robotics.improvement.governance_system import (
    GovernanceSystem,
    Policy,
    ProposedAction,
    ExecutionContext,
    PolicyDecision,
    PolicyDecisionType,
    PolicySeverity,
    PolicyViolation,
    ApprovalRequest,
    ApprovalStatus,
    AuditEntry,
    ComplianceReport
)


@pytest.fixture
def governance_system():
    """Create a governance system for testing"""
    return GovernanceSystem(secret_key="test-secret-key")


@pytest.fixture
def sample_action():
    """Create a sample proposed action"""
    return ProposedAction(
        action_id=uuid4(),
        action_type="MODIFY_RUNBOOK",
        target="safety-procedure-001",
        parameters={"change": "add_step"},
        actor_id="operator-123"
    )


@pytest.fixture
def sample_context():
    """Create a sample execution context"""
    return ExecutionContext(
        robot_state={"battery": 0.8, "status": "idle"},
        environment={"temperature": 22.5},
        operator="operator-123"
    )


def test_governance_system_initialization(governance_system):
    """Test governance system initializes correctly"""
    assert len(governance_system.policies) == 0
    assert len(governance_system.audit_log) == 0
    assert len(governance_system.approval_requests) == 0


def test_add_policy(governance_system):
    """Test adding a policy to the system"""
    policy = Policy(
        policy_id=uuid4(),
        name="Test Policy",
        description="A test policy",
        priority=10,
        severity=PolicySeverity.MEDIUM,
        rule=lambda action, context: "ALLOW",
        active=True
    )
    
    governance_system.add_policy(policy)
    assert len(governance_system.policies) == 1
    assert policy.policy_id in governance_system.policies


def test_add_inactive_policy(governance_system):
    """Test that inactive policies are not added"""
    policy = Policy(
        policy_id=uuid4(),
        name="Inactive Policy",
        description="An inactive policy",
        priority=10,
        severity=PolicySeverity.MEDIUM,
        rule=lambda action, context: "ALLOW",
        active=False
    )
    
    governance_system.add_policy(policy)
    assert len(governance_system.policies) == 0


def test_remove_policy(governance_system):
    """Test removing a policy from the system"""
    policy = Policy(
        policy_id=uuid4(),
        name="Test Policy",
        description="A test policy",
        priority=10,
        severity=PolicySeverity.MEDIUM,
        rule=lambda action, context: "ALLOW",
        active=True
    )
    
    governance_system.add_policy(policy)
    governance_system.remove_policy(policy.policy_id)
    assert len(governance_system.policies) == 0


def test_get_active_policies_sorted_by_priority(governance_system):
    """Test that active policies are returned sorted by priority"""
    policy1 = Policy(
        policy_id=uuid4(),
        name="Low Priority",
        description="Low priority policy",
        priority=5,
        severity=PolicySeverity.LOW,
        rule=lambda action, context: "ALLOW",
        active=True
    )
    
    policy2 = Policy(
        policy_id=uuid4(),
        name="High Priority",
        description="High priority policy",
        priority=20,
        severity=PolicySeverity.HIGH,
        rule=lambda action, context: "ALLOW",
        active=True
    )
    
    policy3 = Policy(
        policy_id=uuid4(),
        name="Medium Priority",
        description="Medium priority policy",
        priority=10,
        severity=PolicySeverity.MEDIUM,
        rule=lambda action, context: "ALLOW",
        active=True
    )
    
    governance_system.add_policy(policy1)
    governance_system.add_policy(policy2)
    governance_system.add_policy(policy3)
    
    active_policies = governance_system.get_active_policies()
    assert len(active_policies) == 3
    assert active_policies[0].priority == 20  # Highest first
    assert active_policies[1].priority == 10
    assert active_policies[2].priority == 5


def test_enforce_policy_allow(governance_system, sample_action, sample_context):
    """Test policy enforcement with ALLOW result"""
    policy = Policy(
        policy_id=uuid4(),
        name="Allow Policy",
        description="Always allows actions",
        priority=10,
        severity=PolicySeverity.LOW,
        rule=lambda action, context: "ALLOW",
        active=True
    )
    
    governance_system.add_policy(policy)
    decision = governance_system.enforce_policy(sample_action, sample_context)
    
    assert decision.result == PolicyDecisionType.ALLOW
    assert len(decision.violations) == 0
    assert decision.explanation == "Action complies with all policies"


def test_enforce_policy_deny(governance_system, sample_action, sample_context):
    """Test policy enforcement with DENY result"""
    policy = Policy(
        policy_id=uuid4(),
        name="Deny Policy",
        description="Always denies actions",
        priority=10,
        severity=PolicySeverity.MEDIUM,
        rule=lambda action, context: "DENY",
        active=True
    )
    
    governance_system.add_policy(policy)
    decision = governance_system.enforce_policy(sample_action, sample_context)
    
    assert decision.result == PolicyDecisionType.DENY
    assert len(decision.violations) == 1
    assert decision.violations[0].policy_name == "Deny Policy"


def test_enforce_policy_critical_short_circuit(governance_system, sample_action, sample_context):
    """Test that critical policy violations cause immediate DENY"""
    critical_policy = Policy(
        policy_id=uuid4(),
        name="Critical Policy",
        description="Critical safety policy",
        priority=100,
        severity=PolicySeverity.CRITICAL,
        rule=lambda action, context: "DENY",
        active=True
    )
    
    low_policy = Policy(
        policy_id=uuid4(),
        name="Low Policy",
        description="Low priority policy",
        priority=5,
        severity=PolicySeverity.LOW,
        rule=lambda action, context: "DENY",
        active=True
    )
    
    governance_system.add_policy(critical_policy)
    governance_system.add_policy(low_policy)
    
    decision = governance_system.enforce_policy(sample_action, sample_context)
    
    assert decision.result == PolicyDecisionType.DENY
    assert len(decision.violations) == 1  # Only critical violation, short-circuited
    assert decision.violations[0].severity == PolicySeverity.CRITICAL
    assert "Critical policy violation" in decision.explanation


def test_enforce_policy_require_approval(governance_system, sample_action, sample_context):
    """Test policy enforcement with REQUIRE_APPROVAL result"""
    policy = Policy(
        policy_id=uuid4(),
        name="Approval Policy",
        description="Requires approval",
        priority=10,
        severity=PolicySeverity.MEDIUM,
        rule=lambda action, context: "REQUIRE_APPROVAL",
        approval_workflow="manager-approval",
        active=True
    )
    
    governance_system.add_policy(policy)
    decision = governance_system.enforce_policy(sample_action, sample_context)
    
    assert decision.result == PolicyDecisionType.REQUIRE_APPROVAL
    assert decision.approval_workflow == "manager-approval"
    assert "requires approval" in decision.explanation


def test_enforce_policy_deterministic(governance_system, sample_action, sample_context):
    """Test that policy enforcement is deterministic"""
    policy = Policy(
        policy_id=uuid4(),
        name="Test Policy",
        description="Test policy",
        priority=10,
        severity=PolicySeverity.MEDIUM,
        rule=lambda action, context: "ALLOW",
        active=True
    )
    
    governance_system.add_policy(policy)
    
    decision1 = governance_system.enforce_policy(sample_action, sample_context)
    decision2 = governance_system.enforce_policy(sample_action, sample_context)
    
    assert decision1.result == decision2.result
    assert decision1.explanation == decision2.explanation


def test_enforce_policy_invalid_action(governance_system, sample_context):
    """Test that invalid actions raise ValueError"""
    invalid_action = ProposedAction(
        action_id=uuid4(),
        action_type="",  # Invalid: empty action type
        target="target",
        parameters={},
        actor_id="actor"
    )
    
    with pytest.raises(ValueError, match="not well-formed"):
        governance_system.enforce_policy(invalid_action, sample_context)


def test_enforce_policy_creates_audit_entry(governance_system, sample_action, sample_context):
    """Test that policy enforcement creates an audit entry"""
    policy = Policy(
        policy_id=uuid4(),
        name="Test Policy",
        description="Test policy",
        priority=10,
        severity=PolicySeverity.MEDIUM,
        rule=lambda action, context: "ALLOW",
        active=True
    )
    
    governance_system.add_policy(policy)
    initial_log_size = len(governance_system.audit_log)
    
    governance_system.enforce_policy(sample_action, sample_context)
    
    assert len(governance_system.audit_log) == initial_log_size + 1
    assert governance_system.audit_log[-1].action_type == "POLICY_EVALUATION"


def test_request_approval(governance_system, sample_action):
    """Test creating an approval request"""
    request = governance_system.request_approval(
        action=sample_action,
        workflow="manager-approval",
        requester="operator-123",
        expires_in_hours=24
    )
    
    assert request.status == ApprovalStatus.PENDING
    assert request.workflow == "manager-approval"
    assert request.requester == "operator-123"
    assert request.expires_at is not None
    assert request.request_id in governance_system.approval_requests


def test_approve_request(governance_system, sample_action):
    """Test approving an approval request"""
    request = governance_system.request_approval(
        action=sample_action,
        workflow="manager-approval",
        requester="operator-123"
    )
    
    approved_request = governance_system.approve_request(
        request_id=request.request_id,
        approver="manager-456",
        rationale="Approved for safety reasons"
    )
    
    assert approved_request.status == ApprovalStatus.APPROVED
    assert approved_request.approver == "manager-456"
    assert approved_request.rationale == "Approved for safety reasons"
    assert approved_request.decision_time is not None


def test_reject_request(governance_system, sample_action):
    """Test rejecting an approval request"""
    request = governance_system.request_approval(
        action=sample_action,
        workflow="manager-approval",
        requester="operator-123"
    )
    
    rejected_request = governance_system.reject_request(
        request_id=request.request_id,
        approver="manager-456",
        rationale="Rejected due to safety concerns"
    )
    
    assert rejected_request.status == ApprovalStatus.REJECTED
    assert rejected_request.approver == "manager-456"
    assert rejected_request.rationale == "Rejected due to safety concerns"
    assert rejected_request.decision_time is not None


def test_approve_nonexistent_request(governance_system):
    """Test that approving nonexistent request raises ValueError"""
    with pytest.raises(ValueError, match="not found"):
        governance_system.approve_request(
            request_id=uuid4(),
            approver="manager-456"
        )


def test_approve_non_pending_request(governance_system, sample_action):
    """Test that approving non-pending request raises ValueError"""
    request = governance_system.request_approval(
        action=sample_action,
        workflow="manager-approval",
        requester="operator-123"
    )
    
    governance_system.approve_request(request.request_id, "manager-456")
    
    with pytest.raises(ValueError, match="not pending"):
        governance_system.approve_request(request.request_id, "manager-789")


def test_approve_expired_request(governance_system, sample_action):
    """Test that approving expired request raises ValueError"""
    request = governance_system.request_approval(
        action=sample_action,
        workflow="manager-approval",
        requester="operator-123",
        expires_in_hours=0  # Expires immediately
    )
    
    # Manually set expiration to past
    request.expires_at = datetime.utcnow() - timedelta(hours=1)
    
    with pytest.raises(ValueError, match="expired"):
        governance_system.approve_request(request.request_id, "manager-456")


def test_audit_action(governance_system):
    """Test creating an audit entry"""
    entry = governance_system.audit_action(
        action_type="TEST_ACTION",
        actor_id="operator-123",
        actor_type="operator",
        target="test-target",
        decision=PolicyDecisionType.ALLOW,
        details={"key": "value"}
    )
    
    assert entry.action_type == "TEST_ACTION"
    assert entry.actor_id == "operator-123"
    assert entry.actor_type == "operator"
    assert entry.target == "test-target"
    assert entry.decision == PolicyDecisionType.ALLOW
    assert entry.details == {"key": "value"}
    assert entry.signature != ""


def test_audit_entry_signature(governance_system):
    """Test that audit entries have valid signatures"""
    entry = governance_system.audit_action(
        action_type="TEST_ACTION",
        actor_id="operator-123",
        actor_type="operator",
        target="test-target"
    )
    
    assert entry.verify_signature(governance_system.secret_key)


def test_audit_entry_tamper_detection(governance_system):
    """Test that tampered audit entries are detected"""
    entry = governance_system.audit_action(
        action_type="TEST_ACTION",
        actor_id="operator-123",
        actor_type="operator",
        target="test-target"
    )
    
    # Tamper with the entry
    entry.actor_id = "hacker-999"
    
    # Signature should no longer be valid
    assert not entry.verify_signature(governance_system.secret_key)


def test_verify_audit_integrity(governance_system):
    """Test verifying audit log integrity"""
    governance_system.audit_action(
        action_type="ACTION_1",
        actor_id="operator-123",
        actor_type="operator",
        target="target-1"
    )
    
    governance_system.audit_action(
        action_type="ACTION_2",
        actor_id="operator-456",
        actor_type="operator",
        target="target-2"
    )
    
    assert governance_system.verify_audit_integrity()


def test_verify_audit_integrity_with_tampering(governance_system):
    """Test that audit integrity check detects tampering"""
    governance_system.audit_action(
        action_type="ACTION_1",
        actor_id="operator-123",
        actor_type="operator",
        target="target-1"
    )
    
    # Tamper with an entry
    governance_system.audit_log[0].actor_id = "hacker-999"
    
    assert not governance_system.verify_audit_integrity()


def test_search_audit_log_by_action_type(governance_system):
    """Test searching audit log by action type"""
    governance_system.audit_action(
        action_type="TYPE_A",
        actor_id="operator-123",
        actor_type="operator",
        target="target-1"
    )
    
    governance_system.audit_action(
        action_type="TYPE_B",
        actor_id="operator-456",
        actor_type="operator",
        target="target-2"
    )
    
    results = governance_system.search_audit_log(action_type="TYPE_A")
    assert len(results) == 1
    assert results[0].action_type == "TYPE_A"


def test_search_audit_log_by_actor(governance_system):
    """Test searching audit log by actor ID"""
    governance_system.audit_action(
        action_type="ACTION",
        actor_id="operator-123",
        actor_type="operator",
        target="target-1"
    )
    
    governance_system.audit_action(
        action_type="ACTION",
        actor_id="operator-456",
        actor_type="operator",
        target="target-2"
    )
    
    results = governance_system.search_audit_log(actor_id="operator-123")
    assert len(results) == 1
    assert results[0].actor_id == "operator-123"


def test_search_audit_log_by_time_range(governance_system):
    """Test searching audit log by time range"""
    start_time = datetime.utcnow()
    
    governance_system.audit_action(
        action_type="ACTION",
        actor_id="operator-123",
        actor_type="operator",
        target="target-1"
    )
    
    end_time = datetime.utcnow()
    
    results = governance_system.search_audit_log(
        start_time=start_time,
        end_time=end_time
    )
    assert len(results) >= 1


def test_generate_compliance_report(governance_system, sample_action, sample_context):
    """Test generating a compliance report"""
    # Add some policies and actions
    policy = Policy(
        policy_id=uuid4(),
        name="Test Policy",
        description="Test policy",
        priority=10,
        severity=PolicySeverity.MEDIUM,
        rule=lambda action, context: "ALLOW",
        active=True
    )
    
    governance_system.add_policy(policy)
    
    start_time = datetime.utcnow()
    
    # Perform some actions
    governance_system.enforce_policy(sample_action, sample_context)
    governance_system.audit_action(
        action_type="TEST_ACTION",
        actor_id="operator-123",
        actor_type="operator",
        target="test-target"
    )
    
    end_time = datetime.utcnow()
    
    report = governance_system.generate_compliance_report(start_time, end_time)
    
    assert report.start_time == start_time
    assert report.end_time == end_time
    assert report.total_actions >= 2
    assert report.policy_evaluations >= 1
    assert 0.0 <= report.compliance_rate <= 1.0
    assert "ISO 27001" in report.standards
    assert "SOC 2 Type II" in report.standards


def test_compliance_report_with_violations(governance_system, sample_action, sample_context):
    """Test compliance report includes violations"""
    policy = Policy(
        policy_id=uuid4(),
        name="Deny Policy",
        description="Always denies",
        priority=10,
        severity=PolicySeverity.HIGH,
        rule=lambda action, context: "DENY",
        active=True
    )
    
    governance_system.add_policy(policy)
    
    start_time = datetime.utcnow()
    governance_system.enforce_policy(sample_action, sample_context)
    end_time = datetime.utcnow()
    
    report = governance_system.generate_compliance_report(start_time, end_time)
    
    assert len(report.violations) >= 1
    assert report.compliance_rate < 1.0


def test_compliance_report_with_approvals(governance_system, sample_action):
    """Test compliance report includes approval statistics"""
    start_time = datetime.utcnow()
    
    request1 = governance_system.request_approval(
        action=sample_action,
        workflow="workflow-1",
        requester="operator-123"
    )
    
    request2 = governance_system.request_approval(
        action=sample_action,
        workflow="workflow-2",
        requester="operator-456"
    )
    
    governance_system.approve_request(request1.request_id, "manager-789")
    governance_system.reject_request(request2.request_id, "manager-789")
    
    end_time = datetime.utcnow()
    
    report = governance_system.generate_compliance_report(start_time, end_time)
    
    assert report.approval_requests == 2
    assert report.approved == 1
    assert report.denied == 1
