"""
Unit tests for ExecutionTracker component.

Tests cover:
- Unique execution ID assignment (Requirement 4.1)
- Step recording with timestamps and states (Requirement 4.2)
- Complete execution trace maintenance (Requirement 4.3)
- Anomaly detection (Requirement 4.4)
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.stepbystep_robotics.workflow.execution_tracker import (
    ExecutionTracker,
    TrackingSession,
    AnomalyReport,
)
from src.stepbystep_robotics.models import (
    RobotState,
    ExecutionStepRecord,
    ExecutionStatus,
    StepStatus,
    Vector3D,
    Quaternion,
    Deviation,
    Anomaly,
)


# Test Fixtures

@pytest.fixture
def tracker():
    """Create a fresh ExecutionTracker instance."""
    return ExecutionTracker()


@pytest.fixture
def robot_id():
    """Generate a test robot ID."""
    return uuid4()


@pytest.fixture
def initial_state(robot_id):
    """Create an initial robot state."""
    return RobotState(
        robot_id=robot_id,
        timestamp=datetime.now(),
        position=Vector3D(0.0, 0.0, 0.0),
        orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
        joint_states={},
        sensor_readings={},
        actuator_states={},
        battery_level=1.0,
        error_flags=set(),
        metadata={}
    )


@pytest.fixture
def step_state(robot_id):
    """Create a robot state for a step."""
    return RobotState(
        robot_id=robot_id,
        timestamp=datetime.now() + timedelta(seconds=1),
        position=Vector3D(1.0, 0.0, 0.0),
        orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
        joint_states={},
        sensor_readings={},
        actuator_states={},
        battery_level=0.95,
        error_flags=set(),
        metadata={}
    )


# Test: startTracking() - Requirement 4.1

def test_start_tracking_generates_unique_execution_id(tracker, robot_id, initial_state):
    """Test that startTracking generates a unique execution ID."""
    session = tracker.startTracking("task-1", robot_id, initial_state)
    
    assert session.execution_id is not None
    assert isinstance(session.execution_id, str)
    assert session.task_id == "task-1"
    assert session.robot_id == robot_id
    assert session.is_active is True


def test_start_tracking_with_custom_execution_id(tracker, robot_id, initial_state):
    """Test that startTracking accepts a custom execution ID."""
    custom_id = "custom-exec-123"
    session = tracker.startTracking("task-1", robot_id, initial_state, execution_id=custom_id)
    
    assert session.execution_id == custom_id


def test_start_tracking_rejects_duplicate_execution_id(tracker, robot_id, initial_state):
    """Test that startTracking rejects duplicate execution IDs."""
    custom_id = "duplicate-id"
    tracker.startTracking("task-1", robot_id, initial_state, execution_id=custom_id)
    
    with pytest.raises(ValueError, match="already exists"):
        tracker.startTracking("task-2", robot_id, initial_state, execution_id=custom_id)


def test_start_tracking_initializes_execution_trace(tracker, robot_id, initial_state):
    """Test that startTracking initializes an execution trace."""
    session = tracker.startTracking("task-1", robot_id, initial_state)
    trace = tracker.getExecutionTrace(session.execution_id)
    
    assert trace.execution_id == session.execution_id
    assert trace.task_id == "task-1"
    assert trace.robot_id == robot_id
    assert trace.status == ExecutionStatus.IN_PROGRESS
    assert len(trace.steps) == 0
    assert len(trace.state_history) == 1
    assert trace.state_history[0] == initial_state
    assert len(trace.anomalies) == 0


# Test: recordStep() - Requirement 4.2

def test_record_step_adds_step_to_trace(tracker, robot_id, initial_state, step_state):
    """Test that recordStep adds a step record to the trace."""
    session = tracker.startTracking("task-1", robot_id, initial_state)
    
    start_time = datetime.now()
    end_time = start_time + timedelta(seconds=2)
    
    step_record = ExecutionStepRecord(
        step_id="step-1",
        start_time=start_time,
        end_time=end_time,
        status=StepStatus.COMPLETED,
        input_state=initial_state,
        output_state=step_state,
        actual_duration=2.0,
        deviations=[],
        retry_count=0
    )
    
    tracker.recordStep(session.execution_id, step_record)
    trace = tracker.getExecutionTrace(session.execution_id)
    
    assert len(trace.steps) == 1
    assert trace.steps[0] == step_record
    assert len(trace.state_history) == 2
    assert trace.state_history[1] == step_state


def test_record_step_validates_execution_exists(tracker, robot_id, initial_state):
    """Test that recordStep validates execution exists."""
    start_time = datetime.now()
    end_time = start_time + timedelta(seconds=1)
    
    step_record = ExecutionStepRecord(
        step_id="step-1",
        start_time=start_time,
        end_time=end_time,
        status=StepStatus.COMPLETED,
        input_state=initial_state,
        output_state=initial_state,
        actual_duration=1.0
    )
    
    with pytest.raises(ValueError, match="not found"):
        tracker.recordStep("nonexistent-id", step_record)


def test_record_step_validates_chronological_order(tracker, robot_id, initial_state, step_state):
    """Test that recordStep validates chronological ordering of steps."""
    session = tracker.startTracking("task-1", robot_id, initial_state)
    
    # Record first step
    step1_start = datetime.now()
    step1_end = step1_start + timedelta(seconds=2)
    step1 = ExecutionStepRecord(
        step_id="step-1",
        start_time=step1_start,
        end_time=step1_end,
        status=StepStatus.COMPLETED,
        input_state=initial_state,
        output_state=step_state,
        actual_duration=2.0
    )
    tracker.recordStep(session.execution_id, step1)
    
    # Try to record second step with earlier start time
    step2_start = step1_start  # Same as step1 start, before step1 end
    step2_end = step2_start + timedelta(seconds=1)
    step2 = ExecutionStepRecord(
        step_id="step-2",
        start_time=step2_start,
        end_time=step2_end,
        status=StepStatus.COMPLETED,
        input_state=step_state,
        output_state=step_state,
        actual_duration=1.0
    )
    
    with pytest.raises(ValueError, match="before previous step end time"):
        tracker.recordStep(session.execution_id, step2)


def test_record_multiple_steps_in_sequence(tracker, robot_id, initial_state, step_state):
    """Test recording multiple steps in sequence."""
    session = tracker.startTracking("task-1", robot_id, initial_state)
    
    current_time = datetime.now()
    
    for i in range(3):
        step_start = current_time + timedelta(seconds=i * 2)
        step_end = step_start + timedelta(seconds=1.5)
        
        step = ExecutionStepRecord(
            step_id=f"step-{i+1}",
            start_time=step_start,
            end_time=step_end,
            status=StepStatus.COMPLETED,
            input_state=initial_state if i == 0 else step_state,
            output_state=step_state,
            actual_duration=1.5
        )
        tracker.recordStep(session.execution_id, step)
    
    trace = tracker.getExecutionTrace(session.execution_id)
    assert len(trace.steps) == 3
    assert trace.steps[0].step_id == "step-1"
    assert trace.steps[1].step_id == "step-2"
    assert trace.steps[2].step_id == "step-3"


# Test: getCurrentStatus() - Status queries

def test_get_current_status_returns_status(tracker, robot_id, initial_state):
    """Test that getCurrentStatus returns the current execution status."""
    session = tracker.startTracking("task-1", robot_id, initial_state)
    status = tracker.getCurrentStatus(session.execution_id)
    
    assert status == ExecutionStatus.IN_PROGRESS


def test_get_current_status_validates_execution_exists(tracker):
    """Test that getCurrentStatus validates execution exists."""
    with pytest.raises(ValueError, match="not found"):
        tracker.getCurrentStatus("nonexistent-id")


# Test: getExecutionTrace() - Requirement 4.3

def test_get_execution_trace_returns_complete_trace(tracker, robot_id, initial_state):
    """Test that getExecutionTrace returns the complete execution trace."""
    session = tracker.startTracking("task-1", robot_id, initial_state)
    trace = tracker.getExecutionTrace(session.execution_id)
    
    assert trace is not None
    assert trace.execution_id == session.execution_id
    assert trace.task_id == "task-1"
    assert trace.robot_id == robot_id


def test_get_execution_trace_validates_execution_exists(tracker):
    """Test that getExecutionTrace validates execution exists."""
    with pytest.raises(ValueError, match="not found"):
        tracker.getExecutionTrace("nonexistent-id")


# Test: detectAnomaly() - Requirement 4.4

def test_detect_anomaly_finds_timing_violations(tracker, robot_id, initial_state, step_state):
    """Test that detectAnomaly detects timing violations."""
    session = tracker.startTracking("task-1", robot_id, initial_state)
    
    # Record a step that takes much longer than expected
    step_start = datetime.now()
    step_end = step_start + timedelta(seconds=10)
    
    step = ExecutionStepRecord(
        step_id="step-1",
        start_time=step_start,
        end_time=step_end,
        status=StepStatus.COMPLETED,
        input_state=initial_state,
        output_state=step_state,
        actual_duration=10.0
    )
    # Add expected_duration as attribute for testing
    step.expected_duration = 2.0
    
    tracker.recordStep(session.execution_id, step)
    
    report = tracker.detectAnomaly(session.execution_id)
    
    assert len(report.anomalies) > 0
    timing_anomalies = [a for a in report.anomalies if a.anomaly_type == "TIMING_VIOLATION"]
    assert len(timing_anomalies) == 1
    # 10s / 2s = 5x, which exceeds critical threshold of 3x
    assert timing_anomalies[0].severity == "CRITICAL"


def test_detect_anomaly_finds_unexpected_state_transitions(tracker, robot_id, initial_state):
    """Test that detectAnomaly detects unexpected state transitions."""
    session = tracker.startTracking("task-1", robot_id, initial_state)
    
    # Create a state with increased battery level (impossible without charging)
    impossible_state = RobotState(
        robot_id=robot_id,
        timestamp=datetime.now() + timedelta(seconds=1),
        position=Vector3D(1.0, 0.0, 0.0),
        orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
        joint_states={},
        sensor_readings={},
        actuator_states={},
        battery_level=1.0,  # Same as initial (initial was 1.0)
        error_flags=set(),
        metadata={}
    )
    
    # Manually increase battery to trigger anomaly
    impossible_state.battery_level = 1.05  # Increased from 1.0
    
    step = ExecutionStepRecord(
        step_id="step-1",
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(seconds=1),
        status=StepStatus.COMPLETED,
        input_state=initial_state,
        output_state=impossible_state,
        actual_duration=1.0
    )
    
    tracker.recordStep(session.execution_id, step)
    report = tracker.detectAnomaly(session.execution_id)
    
    state_anomalies = [a for a in report.anomalies if a.anomaly_type == "UNEXPECTED_STATE_TRANSITION"]
    assert len(state_anomalies) == 1
    assert state_anomalies[0].severity == "CRITICAL"


def test_detect_anomaly_finds_error_flags(tracker, robot_id, initial_state):
    """Test that detectAnomaly detects new error flags."""
    session = tracker.startTracking("task-1", robot_id, initial_state)
    
    # Create a state with error flags
    error_state = RobotState(
        robot_id=robot_id,
        timestamp=datetime.now() + timedelta(seconds=1),
        position=Vector3D(1.0, 0.0, 0.0),
        orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
        joint_states={},
        sensor_readings={},
        actuator_states={},
        battery_level=0.95,
        error_flags={"MOTOR_OVERHEAT", "SENSOR_FAILURE"},
        metadata={}
    )
    
    step = ExecutionStepRecord(
        step_id="step-1",
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(seconds=1),
        status=StepStatus.COMPLETED,
        input_state=initial_state,
        output_state=error_state,
        actual_duration=1.0
    )
    
    tracker.recordStep(session.execution_id, step)
    report = tracker.detectAnomaly(session.execution_id)
    
    error_anomalies = [a for a in report.anomalies if a.anomaly_type == "ERROR_FLAG_DETECTED"]
    assert len(error_anomalies) == 1
    assert error_anomalies[0].severity == "WARNING"


def test_detect_anomaly_finds_constraint_violations(tracker, robot_id, initial_state, step_state):
    """Test that detectAnomaly detects constraint violations."""
    session = tracker.startTracking("task-1", robot_id, initial_state)
    
    # Create a step with deviations
    deviation = Deviation(
        metric="position_accuracy",
        expected=0.01,
        actual=0.15,
        severity="HIGH"
    )
    
    step = ExecutionStepRecord(
        step_id="step-1",
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(seconds=1),
        status=StepStatus.COMPLETED,
        input_state=initial_state,
        output_state=step_state,
        actual_duration=1.0,
        deviations=[deviation]
    )
    
    tracker.recordStep(session.execution_id, step)
    report = tracker.detectAnomaly(session.execution_id)
    
    constraint_anomalies = [a for a in report.anomalies if a.anomaly_type == "CONSTRAINT_VIOLATION"]
    assert len(constraint_anomalies) == 1
    assert constraint_anomalies[0].severity == "HIGH"


def test_detect_anomaly_validates_execution_exists(tracker):
    """Test that detectAnomaly validates execution exists."""
    with pytest.raises(ValueError, match="not found"):
        tracker.detectAnomaly("nonexistent-id")


def test_detect_anomaly_adds_anomalies_to_trace(tracker, robot_id, initial_state, step_state):
    """Test that detectAnomaly adds detected anomalies to the trace."""
    session = tracker.startTracking("task-1", robot_id, initial_state)
    
    # Create a step with deviation
    deviation = Deviation(
        metric="test_metric",
        expected=1.0,
        actual=2.0,
        severity="CRITICAL"
    )
    
    step = ExecutionStepRecord(
        step_id="step-1",
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(seconds=1),
        status=StepStatus.COMPLETED,
        input_state=initial_state,
        output_state=step_state,
        actual_duration=1.0,
        deviations=[deviation]
    )
    
    tracker.recordStep(session.execution_id, step)
    
    # Before detection
    trace_before = tracker.getExecutionTrace(session.execution_id)
    anomalies_before = len(trace_before.anomalies)
    
    # Detect anomalies
    tracker.detectAnomaly(session.execution_id)
    
    # After detection
    trace_after = tracker.getExecutionTrace(session.execution_id)
    assert len(trace_after.anomalies) > anomalies_before


# Test: finishTracking() - Complete execution

def test_finish_tracking_finalizes_trace(tracker, robot_id, initial_state, step_state):
    """Test that finishTracking finalizes the execution trace."""
    session = tracker.startTracking("task-1", robot_id, initial_state)
    
    final_trace = tracker.finishTracking(
        session.execution_id,
        ExecutionStatus.COMPLETED,
        step_state
    )
    
    assert final_trace.status == ExecutionStatus.COMPLETED
    assert final_trace.end_time is not None
    assert final_trace.end_time >= final_trace.start_time
    assert step_state in final_trace.state_history


def test_finish_tracking_deactivates_session(tracker, robot_id, initial_state, step_state):
    """Test that finishTracking deactivates the session."""
    session = tracker.startTracking("task-1", robot_id, initial_state)
    execution_id = session.execution_id
    
    tracker.finishTracking(execution_id, ExecutionStatus.COMPLETED, step_state)
    
    # Session should no longer be active
    with pytest.raises(ValueError, match="No active session"):
        tracker.recordStep(execution_id, ExecutionStepRecord(
            step_id="step-after-finish",
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(seconds=1),
            status=StepStatus.COMPLETED,
            input_state=step_state,
            output_state=step_state,
            actual_duration=1.0
        ))


def test_finish_tracking_validates_execution_exists(tracker):
    """Test that finishTracking validates execution exists."""
    with pytest.raises(ValueError, match="not found"):
        tracker.finishTracking(
            "nonexistent-id",
            ExecutionStatus.COMPLETED,
            RobotState(
                robot_id=uuid4(),
                timestamp=datetime.now(),
                position=Vector3D(0.0, 0.0, 0.0),
                orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
                joint_states={},
                sensor_readings={},
                actuator_states={},
                battery_level=1.0,
                error_flags=set()
            )
        )


# Test: abortTracking() - Abort execution

def test_abort_tracking_creates_abort_anomaly(tracker, robot_id, initial_state, step_state):
    """Test that abortTracking creates an abort anomaly."""
    session = tracker.startTracking("task-1", robot_id, initial_state)
    
    abort_trace = tracker.abortTracking(
        session.execution_id,
        "Robot communication failure",
        step_state
    )
    
    assert abort_trace.status == ExecutionStatus.ABORTED
    assert len(abort_trace.anomalies) > 0
    
    abort_anomalies = [a for a in abort_trace.anomalies if a.anomaly_type == "EXECUTION_ABORTED"]
    assert len(abort_anomalies) == 1
    assert abort_anomalies[0].severity == "CRITICAL"
    assert "Robot communication failure" in abort_anomalies[0].description


def test_abort_tracking_finalizes_trace(tracker, robot_id, initial_state, step_state):
    """Test that abortTracking finalizes the trace."""
    session = tracker.startTracking("task-1", robot_id, initial_state)
    
    abort_trace = tracker.abortTracking(
        session.execution_id,
        "Test abort",
        step_state
    )
    
    assert abort_trace.end_time is not None
    assert abort_trace.status == ExecutionStatus.ABORTED


# Integration Tests

def test_complete_execution_workflow(tracker, robot_id, initial_state, step_state):
    """Test a complete execution workflow from start to finish."""
    # Start tracking
    session = tracker.startTracking("task-1", robot_id, initial_state)
    
    # Record multiple steps
    current_time = datetime.now()
    for i in range(3):
        step_start = current_time + timedelta(seconds=i * 2)
        step_end = step_start + timedelta(seconds=1.5)
        
        step = ExecutionStepRecord(
            step_id=f"step-{i+1}",
            start_time=step_start,
            end_time=step_end,
            status=StepStatus.COMPLETED,
            input_state=initial_state if i == 0 else step_state,
            output_state=step_state,
            actual_duration=1.5
        )
        tracker.recordStep(session.execution_id, step)
    
    # Check status
    status = tracker.getCurrentStatus(session.execution_id)
    assert status == ExecutionStatus.IN_PROGRESS
    
    # Detect anomalies
    report = tracker.detectAnomaly(session.execution_id)
    assert report.execution_id == session.execution_id
    
    # Finish tracking
    final_trace = tracker.finishTracking(
        session.execution_id,
        ExecutionStatus.COMPLETED,
        step_state
    )
    
    # Verify final trace
    assert final_trace.status == ExecutionStatus.COMPLETED
    assert len(final_trace.steps) == 3
    assert final_trace.end_time is not None
    assert len(final_trace.state_history) >= 2  # At least initial and final


def test_multiple_concurrent_executions(tracker, robot_id, initial_state, step_state):
    """Test tracking multiple concurrent executions."""
    # Start multiple executions
    session1 = tracker.startTracking("task-1", robot_id, initial_state)
    session2 = tracker.startTracking("task-2", robot_id, initial_state)
    session3 = tracker.startTracking("task-3", robot_id, initial_state)
    
    # Verify all sessions are active
    assert session1.execution_id != session2.execution_id
    assert session2.execution_id != session3.execution_id
    
    # Record steps for each
    for session in [session1, session2, session3]:
        step = ExecutionStepRecord(
            step_id="step-1",
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(seconds=1),
            status=StepStatus.COMPLETED,
            input_state=initial_state,
            output_state=step_state,
            actual_duration=1.0
        )
        tracker.recordStep(session.execution_id, step)
    
    # Verify all traces exist
    trace1 = tracker.getExecutionTrace(session1.execution_id)
    trace2 = tracker.getExecutionTrace(session2.execution_id)
    trace3 = tracker.getExecutionTrace(session3.execution_id)
    
    assert len(trace1.steps) == 1
    assert len(trace2.steps) == 1
    assert len(trace3.steps) == 1


# Enhanced Anomaly Detection Tests - Task 6.5

def test_detect_anomaly_classifies_severity_based_on_duration_ratio(tracker, robot_id, initial_state, step_state):
    """Test that anomaly detection classifies severity based on duration ratio."""
    session = tracker.startTracking("task-1", robot_id, initial_state)
    
    # Record a step that takes 3.5x expected (should be CRITICAL)
    step_start = datetime.now()
    step_end = step_start + timedelta(seconds=7)
    
    step = ExecutionStepRecord(
        step_id="step-1",
        start_time=step_start,
        end_time=step_end,
        status=StepStatus.COMPLETED,
        input_state=initial_state,
        output_state=step_state,
        actual_duration=7.0
    )
    step.expected_duration = 2.0
    
    tracker.recordStep(session.execution_id, step)
    report = tracker.detectAnomaly(session.execution_id)
    
    timing_anomalies = [a for a in report.anomalies if a.anomaly_type == "TIMING_VIOLATION"]
    assert len(timing_anomalies) == 1
    assert timing_anomalies[0].severity == "CRITICAL"
    assert report.critical_count == 1
    assert report.requires_operator_alert is True


def test_detect_anomaly_detects_excessive_battery_drain(tracker, robot_id, initial_state):
    """Test that anomaly detection detects excessive battery drain."""
    session = tracker.startTracking("task-1", robot_id, initial_state)
    
    # Create a state with excessive battery drain (25%)
    drained_state = RobotState(
        robot_id=robot_id,
        timestamp=datetime.now() + timedelta(seconds=1),
        position=Vector3D(1.0, 0.0, 0.0),
        orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
        joint_states={},
        sensor_readings={},
        actuator_states={},
        battery_level=0.75,  # Drained from 1.0 to 0.75
        error_flags=set(),
        metadata={}
    )
    
    step = ExecutionStepRecord(
        step_id="step-1",
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(seconds=1),
        status=StepStatus.COMPLETED,
        input_state=initial_state,
        output_state=drained_state,
        actual_duration=1.0
    )
    
    tracker.recordStep(session.execution_id, step)
    report = tracker.detectAnomaly(session.execution_id)
    
    battery_anomalies = [a for a in report.anomalies if a.anomaly_type == "EXCESSIVE_BATTERY_DRAIN"]
    assert len(battery_anomalies) == 1
    assert battery_anomalies[0].severity == "WARNING"
    assert 'battery_drain' in battery_anomalies[0].context
    assert battery_anomalies[0].context['battery_drain'] == 0.25


def test_detect_anomaly_detects_critical_battery_drain(tracker, robot_id, initial_state):
    """Test that anomaly detection classifies severe battery drain as CRITICAL."""
    session = tracker.startTracking("task-1", robot_id, initial_state)
    
    # Create a state with critical battery drain (35%)
    critical_drained_state = RobotState(
        robot_id=robot_id,
        timestamp=datetime.now() + timedelta(seconds=1),
        position=Vector3D(1.0, 0.0, 0.0),
        orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
        joint_states={},
        sensor_readings={},
        actuator_states={},
        battery_level=0.65,  # Drained from 1.0 to 0.65
        error_flags=set(),
        metadata={}
    )
    
    step = ExecutionStepRecord(
        step_id="step-1",
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(seconds=1),
        status=StepStatus.COMPLETED,
        input_state=initial_state,
        output_state=critical_drained_state,
        actual_duration=1.0
    )
    
    tracker.recordStep(session.execution_id, step)
    report = tracker.detectAnomaly(session.execution_id)
    
    battery_anomalies = [a for a in report.anomalies if a.anomaly_type == "EXCESSIVE_BATTERY_DRAIN"]
    assert len(battery_anomalies) == 1
    assert battery_anomalies[0].severity == "CRITICAL"
    assert report.critical_count >= 1


def test_detect_anomaly_detects_abnormal_position_jump(tracker, robot_id, initial_state):
    """Test that anomaly detection detects abnormal position jumps."""
    session = tracker.startTracking("task-1", robot_id, initial_state)
    
    # Create a state with large position jump (6 units)
    jumped_state = RobotState(
        robot_id=robot_id,
        timestamp=datetime.now() + timedelta(seconds=1),
        position=Vector3D(6.0, 0.0, 0.0),  # Jumped from (0,0,0) to (6,0,0)
        orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
        joint_states={},
        sensor_readings={},
        actuator_states={},
        battery_level=0.95,
        error_flags=set(),
        metadata={}
    )
    
    step = ExecutionStepRecord(
        step_id="step-1",
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(seconds=1),
        status=StepStatus.COMPLETED,
        input_state=initial_state,
        output_state=jumped_state,
        actual_duration=1.0
    )
    
    tracker.recordStep(session.execution_id, step)
    report = tracker.detectAnomaly(session.execution_id)
    
    position_anomalies = [a for a in report.anomalies if a.anomaly_type == "ABNORMAL_POSITION_JUMP"]
    assert len(position_anomalies) == 1
    assert position_anomalies[0].severity == "WARNING"
    assert 'position_delta' in position_anomalies[0].context
    assert position_anomalies[0].context['position_delta'] == pytest.approx(6.0, rel=0.01)


def test_detect_anomaly_detects_critical_position_jump(tracker, robot_id, initial_state):
    """Test that anomaly detection classifies large position jumps as CRITICAL."""
    session = tracker.startTracking("task-1", robot_id, initial_state)
    
    # Create a state with very large position jump (15 units)
    jumped_state = RobotState(
        robot_id=robot_id,
        timestamp=datetime.now() + timedelta(seconds=1),
        position=Vector3D(15.0, 0.0, 0.0),
        orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
        joint_states={},
        sensor_readings={},
        actuator_states={},
        battery_level=0.95,
        error_flags=set(),
        metadata={}
    )
    
    step = ExecutionStepRecord(
        step_id="step-1",
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(seconds=1),
        status=StepStatus.COMPLETED,
        input_state=initial_state,
        output_state=jumped_state,
        actual_duration=1.0
    )
    
    tracker.recordStep(session.execution_id, step)
    report = tracker.detectAnomaly(session.execution_id)
    
    position_anomalies = [a for a in report.anomalies if a.anomaly_type == "ABNORMAL_POSITION_JUMP"]
    assert len(position_anomalies) == 1
    assert position_anomalies[0].severity == "CRITICAL"


def test_detect_anomaly_classifies_error_flags_by_severity(tracker, robot_id, initial_state):
    """Test that anomaly detection classifies error flags based on type."""
    session = tracker.startTracking("task-1", robot_id, initial_state)
    
    # Create a state with critical error flags
    critical_error_state = RobotState(
        robot_id=robot_id,
        timestamp=datetime.now() + timedelta(seconds=1),
        position=Vector3D(1.0, 0.0, 0.0),
        orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
        joint_states={},
        sensor_readings={},
        actuator_states={},
        battery_level=0.95,
        error_flags={"MOTOR_FAILURE", "SAFETY_VIOLATION"},
        metadata={}
    )
    
    step = ExecutionStepRecord(
        step_id="step-1",
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(seconds=1),
        status=StepStatus.COMPLETED,
        input_state=initial_state,
        output_state=critical_error_state,
        actual_duration=1.0
    )
    
    tracker.recordStep(session.execution_id, step)
    report = tracker.detectAnomaly(session.execution_id)
    
    error_anomalies = [a for a in report.anomalies if a.anomaly_type == "ERROR_FLAG_DETECTED"]
    assert len(error_anomalies) == 1
    assert error_anomalies[0].severity == "CRITICAL"
    assert error_anomalies[0].context['is_critical_error'] is True


def test_detect_anomaly_detects_high_failure_rate(tracker, robot_id, initial_state, step_state):
    """Test that anomaly detection detects high step failure rates."""
    session = tracker.startTracking("task-1", robot_id, initial_state)
    
    # Record 5 steps, 2 of which fail (40% failure rate)
    current_time = datetime.now()
    for i in range(5):
        step_start = current_time + timedelta(seconds=i * 2)
        step_end = step_start + timedelta(seconds=1)
        
        # Make steps 1 and 3 fail
        status = StepStatus.FAILED if i in [1, 3] else StepStatus.COMPLETED
        
        step = ExecutionStepRecord(
            step_id=f"step-{i+1}",
            start_time=step_start,
            end_time=step_end,
            status=status,
            input_state=initial_state,
            output_state=step_state,
            actual_duration=1.0
        )
        tracker.recordStep(session.execution_id, step)
    
    report = tracker.detectAnomaly(session.execution_id)
    
    failure_anomalies = [a for a in report.anomalies if a.anomaly_type == "HIGH_FAILURE_RATE"]
    assert len(failure_anomalies) == 1
    assert failure_anomalies[0].severity == "CRITICAL"
    assert failure_anomalies[0].context['failure_rate'] == 0.4


def test_detect_anomaly_detects_excessive_retries(tracker, robot_id, initial_state, step_state):
    """Test that anomaly detection detects excessive retries."""
    session = tracker.startTracking("task-1", robot_id, initial_state)
    
    # Record steps with high retry counts
    step1 = ExecutionStepRecord(
        step_id="step-1",
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(seconds=1),
        status=StepStatus.COMPLETED,
        input_state=initial_state,
        output_state=step_state,
        actual_duration=1.0,
        retry_count=3
    )
    
    step2 = ExecutionStepRecord(
        step_id="step-2",
        start_time=datetime.now() + timedelta(seconds=2),
        end_time=datetime.now() + timedelta(seconds=3),
        status=StepStatus.COMPLETED,
        input_state=step_state,
        output_state=step_state,
        actual_duration=1.0,
        retry_count=6
    )
    
    tracker.recordStep(session.execution_id, step1)
    tracker.recordStep(session.execution_id, step2)
    
    report = tracker.detectAnomaly(session.execution_id)
    
    retry_anomalies = [a for a in report.anomalies if a.anomaly_type == "EXCESSIVE_RETRIES"]
    assert len(retry_anomalies) == 1
    assert retry_anomalies[0].severity == "CRITICAL"  # Because step2 has >5 retries
    assert retry_anomalies[0].context['max_retries'] == 6


def test_detect_anomaly_includes_classification_in_context(tracker, robot_id, initial_state, step_state):
    """Test that anomalies include classification in context."""
    session = tracker.startTracking("task-1", robot_id, initial_state)
    
    # Create a timing violation
    step = ExecutionStepRecord(
        step_id="step-1",
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(seconds=5),
        status=StepStatus.COMPLETED,
        input_state=initial_state,
        output_state=step_state,
        actual_duration=5.0
    )
    step.expected_duration = 2.0
    
    tracker.recordStep(session.execution_id, step)
    report = tracker.detectAnomaly(session.execution_id)
    
    timing_anomalies = [a for a in report.anomalies if a.anomaly_type == "TIMING_VIOLATION"]
    assert len(timing_anomalies) == 1
    assert 'classification' in timing_anomalies[0].context
    assert timing_anomalies[0].context['classification'] == 'execution_performance'


def test_operator_alerts_created_for_critical_anomalies(tracker, robot_id, initial_state):
    """Test that operator alerts are created for critical anomalies."""
    session = tracker.startTracking("task-1", robot_id, initial_state)
    
    # Create a critical anomaly (excessive battery drain)
    drained_state = RobotState(
        robot_id=robot_id,
        timestamp=datetime.now() + timedelta(seconds=1),
        position=Vector3D(1.0, 0.0, 0.0),
        orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
        joint_states={},
        sensor_readings={},
        actuator_states={},
        battery_level=0.65,  # Critical drain from 1.0 to 0.65 (35%)
        error_flags=set(),
        metadata={}
    )
    
    step = ExecutionStepRecord(
        step_id="step-1",
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(seconds=1),
        status=StepStatus.COMPLETED,
        input_state=initial_state,
        output_state=drained_state,
        actual_duration=1.0
    )
    
    tracker.recordStep(session.execution_id, step)
    report = tracker.detectAnomaly(session.execution_id)
    
    # Check that operator alert was created
    alerts = tracker.getOperatorAlerts(session.execution_id)
    assert len(alerts) == 1
    assert alerts[0]['execution_id'] == session.execution_id
    assert alerts[0]['critical_count'] >= 1
    assert 'recommended_action' in alerts[0]


def test_get_operator_alerts_filters_by_execution_id(tracker, robot_id, initial_state):
    """Test that getOperatorAlerts can filter by execution ID."""
    # Create two executions with critical anomalies
    session1 = tracker.startTracking("task-1", robot_id, initial_state)
    session2 = tracker.startTracking("task-2", robot_id, initial_state)
    
    for session in [session1, session2]:
        drained_state = RobotState(
            robot_id=robot_id,
            timestamp=datetime.now() + timedelta(seconds=1),
            position=Vector3D(1.0, 0.0, 0.0),
            orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
            joint_states={},
            sensor_readings={},
            actuator_states={},
            battery_level=0.65,  # Critical drain
            error_flags=set(),
            metadata={}
        )
        
        step = ExecutionStepRecord(
            step_id="step-1",
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(seconds=1),
            status=StepStatus.COMPLETED,
            input_state=initial_state,
            output_state=drained_state,
            actual_duration=1.0
        )
        
        tracker.recordStep(session.execution_id, step)
        tracker.detectAnomaly(session.execution_id)
    
    # Get alerts for specific execution
    alerts1 = tracker.getOperatorAlerts(session1.execution_id)
    assert len(alerts1) == 1
    assert alerts1[0]['execution_id'] == session1.execution_id
    
    # Get all alerts
    all_alerts = tracker.getOperatorAlerts()
    assert len(all_alerts) == 2


def test_clear_operator_alerts(tracker, robot_id, initial_state):
    """Test that operator alerts can be cleared."""
    session = tracker.startTracking("task-1", robot_id, initial_state)
    
    # Create critical anomaly
    drained_state = RobotState(
        robot_id=robot_id,
        timestamp=datetime.now() + timedelta(seconds=1),
        position=Vector3D(1.0, 0.0, 0.0),
        orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
        joint_states={},
        sensor_readings={},
        actuator_states={},
        battery_level=0.65,  # Critical drain
        error_flags=set(),
        metadata={}
    )
    
    step = ExecutionStepRecord(
        step_id="step-1",
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(seconds=1),
        status=StepStatus.COMPLETED,
        input_state=initial_state,
        output_state=drained_state,
        actual_duration=1.0
    )
    
    tracker.recordStep(session.execution_id, step)
    tracker.detectAnomaly(session.execution_id)
    
    # Verify alert exists
    assert len(tracker.getOperatorAlerts()) == 1
    
    # Clear alerts
    tracker.clearOperatorAlerts(session.execution_id)
    
    # Verify alerts cleared
    assert len(tracker.getOperatorAlerts()) == 0


def test_get_anomaly_statistics(tracker, robot_id, initial_state, step_state):
    """Test that anomaly statistics are computed correctly."""
    session = tracker.startTracking("task-1", robot_id, initial_state)
    
    # Create multiple anomalies of different types and severities
    # 1. Timing violation (WARNING)
    step1 = ExecutionStepRecord(
        step_id="step-1",
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(seconds=5),
        status=StepStatus.COMPLETED,
        input_state=initial_state,
        output_state=step_state,
        actual_duration=5.0
    )
    step1.expected_duration = 2.0
    tracker.recordStep(session.execution_id, step1)
    
    # 2. Constraint violation (CRITICAL)
    deviation = Deviation(
        metric="position_accuracy",
        expected=0.01,
        actual=0.15,
        severity="CRITICAL"
    )
    step2 = ExecutionStepRecord(
        step_id="step-2",
        start_time=datetime.now() + timedelta(seconds=6),
        end_time=datetime.now() + timedelta(seconds=7),
        status=StepStatus.COMPLETED,
        input_state=step_state,
        output_state=step_state,
        actual_duration=1.0,
        deviations=[deviation]
    )
    tracker.recordStep(session.execution_id, step2)
    
    # Detect anomalies
    tracker.detectAnomaly(session.execution_id)
    
    # Get statistics
    stats = tracker.getAnomalyStatistics(session.execution_id)
    
    assert stats['total_count'] == 2
    assert stats['by_severity']['WARNING'] == 1
    assert stats['by_severity']['CRITICAL'] == 1
    assert stats['critical_count'] == 1
    assert 'TIMING_VIOLATION' in stats['by_type']
    assert 'CONSTRAINT_VIOLATION' in stats['by_type']
    assert len(stats['timeline']) == 2


def test_get_anomaly_statistics_empty_trace(tracker, robot_id, initial_state):
    """Test that anomaly statistics work for traces with no anomalies."""
    session = tracker.startTracking("task-1", robot_id, initial_state)
    
    stats = tracker.getAnomalyStatistics(session.execution_id)
    
    assert stats['total_count'] == 0
    assert stats['by_severity'] == {}
    assert stats['by_type'] == {}
    assert stats['critical_count'] == 0
    assert stats['timeline'] == []


def test_recommended_action_for_different_anomaly_types(tracker, robot_id, initial_state):
    """Test that recommended actions are appropriate for different anomaly types."""
    session = tracker.startTracking("task-1", robot_id, initial_state)
    
    # Create an abort anomaly
    tracker.abortTracking(session.execution_id, "Test abort", initial_state)
    
    alerts = tracker.getOperatorAlerts(session.execution_id)
    assert len(alerts) == 1
    assert "abort reason" in alerts[0]['recommended_action'].lower()


def test_anomaly_context_includes_rich_information(tracker, robot_id, initial_state):
    """Test that anomaly context includes rich information for investigation."""
    session = tracker.startTracking("task-1", robot_id, initial_state)
    
    # Create position jump anomaly
    jumped_state = RobotState(
        robot_id=robot_id,
        timestamp=datetime.now() + timedelta(seconds=1),
        position=Vector3D(6.0, 0.0, 0.0),
        orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
        joint_states={},
        sensor_readings={},
        actuator_states={},
        battery_level=0.95,
        error_flags=set(),
        metadata={}
    )
    
    step = ExecutionStepRecord(
        step_id="step-1",
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(seconds=1),
        status=StepStatus.COMPLETED,
        input_state=initial_state,
        output_state=jumped_state,
        actual_duration=1.0
    )
    
    tracker.recordStep(session.execution_id, step)
    report = tracker.detectAnomaly(session.execution_id)
    
    position_anomalies = [a for a in report.anomalies if a.anomaly_type == "ABNORMAL_POSITION_JUMP"]
    assert len(position_anomalies) == 1
    
    context = position_anomalies[0].context
    assert 'position_delta' in context
    assert 'previous_position' in context
    assert 'current_position' in context
    assert 'threshold' in context
    assert 'classification' in context
    assert context['previous_position']['x'] == 0.0
    assert context['current_position']['x'] == 6.0
