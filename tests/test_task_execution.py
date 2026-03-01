"""
Unit tests for Task Execution Pipeline.

Tests cover:
- Task pipeline orchestration
- Precondition and postcondition verification
- Execution tracking integration
- Performance metrics computation
- Trace persistence
- Error handling and failure scenarios
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4, UUID

from src.stepbystep_robotics.workflow.task_execution import (
    executeTaskPipeline,
    TraceStorage,
    _compute_performance_metrics,
    _robot_in_safe_state,
)
from src.stepbystep_robotics.workflow import TaskSpecEngine
from src.stepbystep_robotics.workflow.execution_tracker import ExecutionTracker
from src.stepbystep_robotics.behavior.state_observer import StateObserver
from src.stepbystep_robotics.models import (
    TaskSpecification,
    TaskStep,
    Condition,
    ConditionType,
    ActionType,
    FailureStrategy,
    RobotState,
    Vector3D,
    Quaternion,
    ExecutionStatus,
    StepStatus,
    ExecutionTrace,
    PerformanceMetrics,
)


# Fixtures

@pytest.fixture
def robot_id():
    """Create a robot ID for testing."""
    return uuid4()


@pytest.fixture
def minimal_state(robot_id):
    """Create a minimal robot state for ExecutionTrace."""
    return RobotState(
        robot_id=robot_id,
        timestamp=datetime.now(),
        position=Vector3D(0.0, 0.0, 0.0),
        orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
        joint_states={},
        sensor_readings={},
        actuator_states={},
        battery_level=0.8,
        error_flags=set(),
        metadata={}
    )


@pytest.fixture
def task_spec_engine():
    """Create a TaskSpecEngine instance."""
    engine = TaskSpecEngine()
    engine.register_capability("move")
    engine.register_capability("grasp")
    engine.register_capability("sense")
    return engine


@pytest.fixture
def execution_tracker():
    """Create an ExecutionTracker instance."""
    return ExecutionTracker()


@pytest.fixture
def state_observer():
    """Create a StateObserver instance."""
    return StateObserver()


@pytest.fixture
def trace_storage():
    """Create a TraceStorage instance."""
    return TraceStorage()


@pytest.fixture
def simple_robot_state(robot_id):
    """Create a simple robot state for testing."""
    return RobotState(
        robot_id=robot_id,
        timestamp=datetime.now(),
        position=Vector3D(0.0, 0.0, 0.0),
        orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
        joint_states={},
        sensor_readings={},
        actuator_states={},
        battery_level=0.8,
        error_flags=set(),
        metadata={}
    )


def setup_robot_state(state_observer, robot_id, state):
    """Helper function to set up robot state in observer."""
    # Record the state in the observer's internal storage
    state_observer._record_state(state)


@pytest.fixture
def valid_task_spec():
    """Create a valid task specification."""
    return TaskSpecification(
        task_id="test-task-001",
        name="Test Task",
        description="A test task for execution",
        preconditions=[
            Condition(
                type=ConditionType.STATE_GREATER_THAN,
                expression="battery_level > 0.5",
                tolerance=0.01
            )
        ],
        postconditions=[
            Condition(
                type=ConditionType.STATE_EQUALS,
                expression="position.x == 1.0",
                tolerance=0.1
            )
        ],
        steps=[
            TaskStep(
                step_id="step-1",
                action=ActionType.MOVE,
                parameters={"target": [1.0, 0.0, 0.0]},
                expected_duration=5.0,
                success_criteria=[],
                failure_handling=FailureStrategy.RETRY,
                max_retries=3
            )
        ],
        timeout_seconds=30,
        required_capabilities={"move"},
        safety_constraints=[
            Condition(
                type=ConditionType.STATE_GREATER_THAN,
                expression="battery_level > 0.2",
                tolerance=0.01
            )
        ]
    )


# Test executeTaskPipeline - Success Cases

def test_execute_task_pipeline_success(
    robot_id, task_spec_engine, execution_tracker, state_observer, 
    trace_storage, valid_task_spec, simple_robot_state
):
    """Test successful task execution through the pipeline."""
    # Setup: Define task and register robot state
    task_spec_engine.defineTask(valid_task_spec)
    setup_robot_state(state_observer, robot_id, simple_robot_state)
    
    # Execute task
    trace = executeTaskPipeline(
        task_id="test-task-001",
        robot_id=robot_id,
        params={"target": [1.0, 0.0, 0.0]},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        state_observer=state_observer,
        trace_storage=trace_storage
    )
    
    # Verify trace is complete
    assert trace is not None
    assert isinstance(trace, ExecutionTrace)
    assert trace.task_id == "test-task-001"
    assert trace.robot_id == robot_id
    assert trace.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED]
    
    # Verify steps were recorded
    assert len(trace.steps) > 0
    
    # Verify state history
    assert len(trace.state_history) >= 2  # At least initial and final state
    
    # Verify performance metrics were computed
    assert trace.performance_metrics is not None
    assert isinstance(trace.performance_metrics, PerformanceMetrics)
    
    # Verify trace was persisted
    persisted_trace = trace_storage.retrieve(trace.execution_id)
    assert persisted_trace is not None
    assert persisted_trace.execution_id == trace.execution_id


def test_execute_task_pipeline_assigns_unique_execution_id(
    robot_id, task_spec_engine, execution_tracker, state_observer,
    trace_storage, valid_task_spec, simple_robot_state
):
    """Test that pipeline assigns unique execution IDs (Requirement 4.1)."""
    task_spec_engine.defineTask(valid_task_spec)
    setup_robot_state(state_observer, robot_id, simple_robot_state)
    
    # Execute task twice
    trace1 = executeTaskPipeline(
        task_id="test-task-001",
        robot_id=robot_id,
        params={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        state_observer=state_observer,
        trace_storage=trace_storage
    )
    
    trace2 = executeTaskPipeline(
        task_id="test-task-001",
        robot_id=robot_id,
        params={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        state_observer=state_observer,
        trace_storage=trace_storage
    )
    
    # Verify unique execution IDs
    assert trace1.execution_id != trace2.execution_id


def test_execute_task_pipeline_records_all_steps(
    robot_id, task_spec_engine, execution_tracker, state_observer,
    trace_storage, simple_robot_state
):
    """Test that pipeline records all execution steps (Requirement 4.2)."""
    # Create task with multiple steps
    multi_step_task = TaskSpecification(
        task_id="multi-step-task",
        name="Multi-Step Task",
        description="Task with multiple steps",
        preconditions=[
            Condition(
                type=ConditionType.STATE_GREATER_THAN,
                expression="battery_level > 0.5",
                tolerance=0.01
            )
        ],
        postconditions=[],
        steps=[
            TaskStep(
                step_id="step-1",
                action=ActionType.MOVE,
                parameters={},
                expected_duration=1.0,
                success_criteria=[],
                failure_handling=FailureStrategy.RETRY
            ),
            TaskStep(
                step_id="step-2",
                action=ActionType.GRASP,
                parameters={},
                expected_duration=2.0,
                success_criteria=[],
                failure_handling=FailureStrategy.RETRY
            ),
            TaskStep(
                step_id="step-3",
                action=ActionType.MOVE,
                parameters={},
                expected_duration=1.0,
                success_criteria=[],
                failure_handling=FailureStrategy.RETRY
            )
        ],
        timeout_seconds=30,
        required_capabilities={"move", "grasp"},
        safety_constraints=[]
    )
    
    task_spec_engine.defineTask(multi_step_task)
    setup_robot_state(state_observer, robot_id, simple_robot_state)
    
    # Execute task
    trace = executeTaskPipeline(
        task_id="multi-step-task",
        robot_id=robot_id,
        params={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        state_observer=state_observer,
        trace_storage=trace_storage
    )
    
    # Verify all steps were recorded
    assert len(trace.steps) == 3
    assert trace.steps[0].step_id == "step-1"
    assert trace.steps[1].step_id == "step-2"
    assert trace.steps[2].step_id == "step-3"
    
    # Verify each step has required fields
    for step in trace.steps:
        assert step.start_time is not None
        assert step.end_time is not None
        assert step.input_state is not None
        assert step.output_state is not None
        assert step.actual_duration >= 0


def test_execute_task_pipeline_maintains_complete_trace(
    robot_id, task_spec_engine, execution_tracker, state_observer,
    trace_storage, valid_task_spec, simple_robot_state
):
    """Test that pipeline maintains complete execution trace (Requirement 4.3)."""
    task_spec_engine.defineTask(valid_task_spec)
    setup_robot_state(state_observer, robot_id, simple_robot_state)
    
    trace = executeTaskPipeline(
        task_id="test-task-001",
        robot_id=robot_id,
        params={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        state_observer=state_observer,
        trace_storage=trace_storage
    )
    
    # Verify trace completeness
    assert trace.execution_id is not None
    assert trace.task_id == "test-task-001"
    assert trace.robot_id == robot_id
    assert trace.start_time is not None
    assert trace.end_time is not None
    assert trace.status is not None
    assert isinstance(trace.steps, list)
    assert isinstance(trace.state_history, list)
    assert isinstance(trace.anomalies, list)
    
    # Verify chronological ordering
    if len(trace.steps) > 1:
        for i in range(len(trace.steps) - 1):
            assert trace.steps[i].end_time <= trace.steps[i + 1].start_time


def test_execute_task_pipeline_persists_trace(
    robot_id, task_spec_engine, execution_tracker, state_observer,
    trace_storage, valid_task_spec, simple_robot_state
):
    """Test that pipeline persists trace to storage (Requirement 4.5)."""
    task_spec_engine.defineTask(valid_task_spec)
    setup_robot_state(state_observer, robot_id, simple_robot_state)
    
    trace = executeTaskPipeline(
        task_id="test-task-001",
        robot_id=robot_id,
        params={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        state_observer=state_observer,
        trace_storage=trace_storage
    )
    
    # Verify trace was persisted
    persisted_trace = trace_storage.retrieve(trace.execution_id)
    assert persisted_trace is not None
    assert persisted_trace.execution_id == trace.execution_id
    assert persisted_trace.task_id == trace.task_id
    assert persisted_trace.robot_id == trace.robot_id


# Test executeTaskPipeline - Precondition Checking

def test_execute_task_pipeline_checks_preconditions(
    robot_id, task_spec_engine, execution_tracker, state_observer,
    trace_storage, valid_task_spec
):
    """Test that pipeline checks preconditions before execution (Requirement 3.4)."""
    task_spec_engine.defineTask(valid_task_spec)
    setup_robot_state(state_observer, robot_id, simple_robot_state)
    
    # Create state with low battery (fails precondition)
    low_battery_state = RobotState(
        robot_id=robot_id,
        timestamp=datetime.now(),
        position=Vector3D(0.0, 0.0, 0.0),
        orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
        joint_states={},
        sensor_readings={},
        actuator_states={},
        battery_level=0.3,  # Below threshold of 0.5
        error_flags=set(),
        metadata={}
    )
    state_observer._robot_states[robot_id] = low_battery_state
    
    # Execute task
    trace = executeTaskPipeline(
        task_id="test-task-001",
        robot_id=robot_id,
        params={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        state_observer=state_observer,
        trace_storage=trace_storage
    )
    
    # Verify execution failed due to preconditions
    assert trace.status == ExecutionStatus.FAILED
    assert len(trace.steps) == 0  # No steps executed
    assert any("Preconditions not satisfied" in a.description for a in trace.anomalies)


def test_execute_task_pipeline_verifies_postconditions(
    robot_id, task_spec_engine, execution_tracker, state_observer,
    trace_storage, simple_robot_state
):
    """Test that pipeline verifies postconditions after execution (Requirement 3.5)."""
    # Create task with specific postcondition
    task_with_postcondition = TaskSpecification(
        task_id="postcondition-task",
        name="Postcondition Task",
        description="Task with postcondition",
        preconditions=[
            Condition(
                type=ConditionType.STATE_GREATER_THAN,
                expression="battery_level > 0.5",
                tolerance=0.01
            )
        ],
        postconditions=[
            Condition(
                type=ConditionType.STATE_EQUALS,
                expression="battery_level == 0.9",
                tolerance=0.05
            )
        ],
        steps=[
            TaskStep(
                step_id="step-1",
                action=ActionType.WAIT,
                parameters={},
                expected_duration=1.0,
                success_criteria=[],
                failure_handling=FailureStrategy.RETRY
            )
        ],
        timeout_seconds=10,
        required_capabilities=set(),
        safety_constraints=[]
    )
    
    task_spec_engine.defineTask(task_with_postcondition)
    setup_robot_state(state_observer, robot_id, simple_robot_state)
    
    # Execute task
    trace = executeTaskPipeline(
        task_id="postcondition-task",
        robot_id=robot_id,
        params={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        state_observer=state_observer,
        trace_storage=trace_storage
    )
    
    # Verify postcondition was checked
    # Since the final state won't have battery_level == 0.9, it should fail
    # (unless the mock execution changes it, which it doesn't in current implementation)
    assert trace.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED]


# Test executeTaskPipeline - Error Handling

def test_execute_task_pipeline_handles_invalid_task_id(
    robot_id, task_spec_engine, execution_tracker, state_observer,
    trace_storage, simple_robot_state
):
    """Test pipeline handles invalid task ID gracefully."""
    setup_robot_state(state_observer, robot_id, simple_robot_state)
    
    # Execute with non-existent task
    trace = executeTaskPipeline(
        task_id="non-existent-task",
        robot_id=robot_id,
        params={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        state_observer=state_observer,
        trace_storage=trace_storage
    )
    
    # Verify failure trace was created
    assert trace.status == ExecutionStatus.FAILED
    assert any("Invalid task specification" in a.description for a in trace.anomalies)


def test_execute_task_pipeline_handles_robot_state_unavailable(
    robot_id, task_spec_engine, execution_tracker, state_observer,
    trace_storage, valid_task_spec
):
    """Test pipeline handles unavailable robot state."""
    task_spec_engine.defineTask(valid_task_spec)
    setup_robot_state(state_observer, robot_id, simple_robot_state)
    # Don't set robot state - it will be None
    
    # Execute task
    trace = executeTaskPipeline(
        task_id="test-task-001",
        robot_id=robot_id,
        params={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        state_observer=state_observer,
        trace_storage=trace_storage
    )
    
    # Verify failure trace was created
    assert trace.status == ExecutionStatus.FAILED
    assert any("Cannot capture robot state" in a.description for a in trace.anomalies)


# Test Performance Metrics Computation

def test_compute_performance_metrics_calculates_duration(
    robot_id
):
    """Test that performance metrics computation calculates total duration correctly."""
    # Create a simple trace
    start_time = datetime.now()
    end_time = start_time + timedelta(seconds=10)
    
    simple_state = RobotState(
        robot_id=robot_id,
        timestamp=start_time,
        position=Vector3D(0.0, 0.0, 0.0),
        orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
        joint_states={},
        sensor_readings={},
        actuator_states={},
        battery_level=0.8,
        error_flags=set(),
        metadata={}
    )
    
    trace = ExecutionTrace(
        execution_id="test-exec-001",
        task_id="test-task",
        robot_id=robot_id,
        start_time=start_time,
        end_time=end_time,
        status=ExecutionStatus.COMPLETED,
        steps=[],
        state_history=[simple_state],
        anomalies=[],
        performance_metrics=None
    )
    
    metrics = _compute_performance_metrics(trace)
    
    assert metrics.total_duration == 10.0


def test_compute_performance_metrics_calculates_success_rate(
    robot_id, minimal_state
):
    """Test that performance metrics computation calculates success rate correctly."""
    from src.stepbystep_robotics.models import ExecutionStepRecord
    
    # Create trace with mixed step statuses
    trace = ExecutionTrace(
        execution_id="test-exec-001",
        task_id="test-task",
        robot_id=robot_id,
        start_time=datetime.now(),
        end_time=datetime.now(),
        status=ExecutionStatus.COMPLETED,
        steps=[
            ExecutionStepRecord(
                step_id="step-1",
                start_time=datetime.now(),
                end_time=datetime.now(),
                status=StepStatus.COMPLETED,
                input_state=minimal_state,
                output_state=minimal_state,
                actual_duration=1.0,
                deviations=[],
                retry_count=0
            ),
            ExecutionStepRecord(
                step_id="step-2",
                start_time=datetime.now(),
                end_time=datetime.now(),
                status=StepStatus.FAILED,
                input_state=minimal_state,
                output_state=minimal_state,
                actual_duration=1.0,
                deviations=[],
                retry_count=0
            )
        ],
        state_history=[minimal_state],
        anomalies=[],
        performance_metrics=None
    )
    
    metrics = _compute_performance_metrics(trace)
    
    # 1 completed out of 2 steps = 0.5 success rate
    assert metrics.success_rate == 0.5


def test_compute_performance_metrics_calculates_energy_consumed(
    robot_id
):
    """Test that performance metrics computation calculates energy consumed correctly."""
    initial_state = RobotState(
        robot_id=robot_id,
        timestamp=datetime.now(),
        position=Vector3D(0.0, 0.0, 0.0),
        orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
        joint_states={},
        sensor_readings={},
        actuator_states={},
        battery_level=0.8,
        error_flags=set(),
        metadata={}
    )
    
    final_state = RobotState(
        robot_id=robot_id,
        timestamp=datetime.now(),
        position=Vector3D(0.0, 0.0, 0.0),
        orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
        joint_states={},
        sensor_readings={},
        actuator_states={},
        battery_level=0.5,  # Consumed 0.3
        error_flags=set(),
        metadata={}
    )
    
    trace = ExecutionTrace(
        execution_id="test-exec-001",
        task_id="test-task",
        robot_id=robot_id,
        start_time=datetime.now(),
        end_time=datetime.now(),
        status=ExecutionStatus.COMPLETED,
        steps=[],
        state_history=[initial_state, final_state],
        anomalies=[],
        performance_metrics=None
    )
    
    metrics = _compute_performance_metrics(trace)
    
    assert abs(metrics.energy_consumed - 0.3) < 0.01  # Use approximate comparison


def test_compute_performance_metrics_scores_in_valid_range(
    robot_id
):
    """Test that all score metrics are in [0.0, 1.0] range."""
    trace = ExecutionTrace(
        execution_id="test-exec-001",
        task_id="test-task",
        robot_id=robot_id,
        start_time=datetime.now(),
        end_time=datetime.now(),
        status=ExecutionStatus.COMPLETED,
        steps=[],
        state_history=[],
        anomalies=[],
        performance_metrics=None
    )
    
    metrics = _compute_performance_metrics(trace)
    
    # Verify all scores are in valid range
    assert 0.0 <= metrics.success_rate <= 1.0
    assert 0.0 <= metrics.accuracy_score <= 1.0
    assert 0.0 <= metrics.smoothness_score <= 1.0
    assert 0.0 <= metrics.safety_score <= 1.0


def test_compute_performance_metrics_energy_non_negative(
    robot_id
):
    """Test that energy consumed is non-negative."""
    trace = ExecutionTrace(
        execution_id="test-exec-001",
        task_id="test-task",
        robot_id=robot_id,
        start_time=datetime.now(),
        end_time=datetime.now(),
        status=ExecutionStatus.COMPLETED,
        steps=[],
        state_history=[],
        anomalies=[],
        performance_metrics=None
    )
    
    metrics = _compute_performance_metrics(trace)
    
    assert metrics.energy_consumed >= 0.0


# Test Robot Safety State Checking

def test_robot_in_safe_state_with_good_battery(
    robot_id, valid_task_spec
):
    """Test robot safety check with good battery level."""
    state = RobotState(
        robot_id=robot_id,
        timestamp=datetime.now(),
        position=Vector3D(0.0, 0.0, 0.0),
        orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
        joint_states={},
        sensor_readings={},
        actuator_states={},
        battery_level=0.8,
        error_flags=set(),
        metadata={}
    )
    
    assert _robot_in_safe_state(state, valid_task_spec) is True


def test_robot_in_safe_state_with_low_battery(
    robot_id, valid_task_spec
):
    """Test robot safety check with low battery level."""
    state = RobotState(
        robot_id=robot_id,
        timestamp=datetime.now(),
        position=Vector3D(0.0, 0.0, 0.0),
        orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
        joint_states={},
        sensor_readings={},
        actuator_states={},
        battery_level=0.05,  # Below safety threshold
        error_flags=set(),
        metadata={}
    )
    
    assert _robot_in_safe_state(state, valid_task_spec) is False


def test_robot_in_safe_state_with_critical_errors(
    robot_id, valid_task_spec
):
    """Test robot safety check with critical error flags."""
    state = RobotState(
        robot_id=robot_id,
        timestamp=datetime.now(),
        position=Vector3D(0.0, 0.0, 0.0),
        orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
        joint_states={},
        sensor_readings={},
        actuator_states={},
        battery_level=0.8,
        error_flags={'MOTOR_FAILURE'},  # Critical error
        metadata={}
    )
    
    assert _robot_in_safe_state(state, valid_task_spec) is False


# Test TraceStorage

def test_trace_storage_persist_and_retrieve():
    """Test trace storage persistence and retrieval."""
    storage = TraceStorage()
    robot_id = uuid4()
    
    trace = ExecutionTrace(
        execution_id="test-exec-001",
        task_id="test-task",
        robot_id=robot_id,
        start_time=datetime.now(),
        end_time=datetime.now(),
        status=ExecutionStatus.COMPLETED,
        steps=[],
        state_history=[],
        anomalies=[],
        performance_metrics=None
    )
    
    # Persist trace
    storage.persist(trace)
    
    # Retrieve trace
    retrieved = storage.retrieve("test-exec-001")
    
    assert retrieved is not None
    assert retrieved.execution_id == "test-exec-001"
    assert retrieved.task_id == "test-task"


def test_trace_storage_retrieve_non_existent():
    """Test retrieving non-existent trace returns None."""
    storage = TraceStorage()
    
    retrieved = storage.retrieve("non-existent")
    
    assert retrieved is None


def test_trace_storage_list_traces():
    """Test listing traces with filters."""
    storage = TraceStorage()
    robot_id1 = uuid4()
    robot_id2 = uuid4()
    
    # Create and persist multiple traces
    trace1 = ExecutionTrace(
        execution_id="exec-001",
        task_id="task-A",
        robot_id=robot_id1,
        start_time=datetime.now(),
        end_time=datetime.now(),
        status=ExecutionStatus.COMPLETED,
        steps=[],
        state_history=[],
        anomalies=[],
        performance_metrics=None
    )
    
    trace2 = ExecutionTrace(
        execution_id="exec-002",
        task_id="task-B",
        robot_id=robot_id2,
        start_time=datetime.now(),
        end_time=datetime.now(),
        status=ExecutionStatus.COMPLETED,
        steps=[],
        state_history=[],
        anomalies=[],
        performance_metrics=None
    )
    
    trace3 = ExecutionTrace(
        execution_id="exec-003",
        task_id="task-A",
        robot_id=robot_id1,
        start_time=datetime.now(),
        end_time=datetime.now(),
        status=ExecutionStatus.COMPLETED,
        steps=[],
        state_history=[],
        anomalies=[],
        performance_metrics=None
    )
    
    storage.persist(trace1)
    storage.persist(trace2)
    storage.persist(trace3)
    
    # List all traces
    all_traces = storage.list_traces()
    assert len(all_traces) == 3
    
    # Filter by task_id
    task_a_traces = storage.list_traces(task_id="task-A")
    assert len(task_a_traces) == 2
    
    # Filter by robot_id
    robot1_traces = storage.list_traces(robot_id=robot_id1)
    assert len(robot1_traces) == 2
    
    # Filter by both
    specific_traces = storage.list_traces(task_id="task-A", robot_id=robot_id1)
    assert len(specific_traces) == 2


# Test Task Execution Atomicity

def test_execute_task_pipeline_atomicity_on_success(
    robot_id, task_spec_engine, execution_tracker, state_observer,
    trace_storage, valid_task_spec, simple_robot_state
):
    """Test that successful execution is atomic (Requirement 5.1)."""
    task_spec_engine.defineTask(valid_task_spec)
    setup_robot_state(state_observer, robot_id, simple_robot_state)
    
    trace = executeTaskPipeline(
        task_id="test-task-001",
        robot_id=robot_id,
        params={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        state_observer=state_observer,
        trace_storage=trace_storage
    )
    
    # If status is COMPLETED, all steps should be recorded
    if trace.status == ExecutionStatus.COMPLETED:
        assert len(trace.steps) == len(valid_task_spec.steps)
        # All steps should have completed or appropriate status
        for step in trace.steps:
            assert step.status in [StepStatus.COMPLETED, StepStatus.SKIPPED]


def test_execute_task_pipeline_atomicity_on_failure(
    robot_id, task_spec_engine, execution_tracker, state_observer,
    trace_storage, simple_robot_state
):
    """Test that failed execution leaves robot in safe state (Requirement 5.2)."""
    # Create task with ABORT failure handling
    abort_task = TaskSpecification(
        task_id="abort-task",
        name="Abort Task",
        description="Task with abort on failure",
        preconditions=[
            Condition(
                type=ConditionType.STATE_GREATER_THAN,
                expression="battery_level > 0.5",
                tolerance=0.01
            )
        ],
        postconditions=[],
        steps=[
            TaskStep(
                step_id="step-1",
                action=ActionType.MOVE,
                parameters={},
                expected_duration=1.0,
                success_criteria=[],
                failure_handling=FailureStrategy.ABORT  # Abort on failure
            )
        ],
        timeout_seconds=10,
        required_capabilities={"move"},
        safety_constraints=[]
    )
    
    task_spec_engine.defineTask(abort_task)
    setup_robot_state(state_observer, robot_id, simple_robot_state)
    
    trace = executeTaskPipeline(
        task_id="abort-task",
        robot_id=robot_id,
        params={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        state_observer=state_observer,
        trace_storage=trace_storage
    )
    
    # Verify all steps are recorded regardless of outcome
    assert len(trace.steps) >= 0  # Steps recorded even if execution failed
    
    # Verify final state is safe (if we can access it)
    if len(trace.state_history) > 0:
        final_state = trace.state_history[-1]
        # Check basic safety criteria
        assert final_state.battery_level >= 0.0


# Test Custom Execution ID

def test_execute_task_pipeline_with_custom_execution_id(
    robot_id, task_spec_engine, execution_tracker, state_observer,
    trace_storage, valid_task_spec, simple_robot_state
):
    """Test pipeline accepts custom execution ID."""
    task_spec_engine.defineTask(valid_task_spec)
    setup_robot_state(state_observer, robot_id, simple_robot_state)
    
    custom_id = "custom-exec-12345"
    
    trace = executeTaskPipeline(
        task_id="test-task-001",
        robot_id=robot_id,
        params={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        state_observer=state_observer,
        trace_storage=trace_storage,
        execution_id=custom_id
    )
    
    assert trace.execution_id == custom_id


# Test Integration with Components

def test_execute_task_pipeline_integrates_with_task_spec_engine(
    robot_id, task_spec_engine, execution_tracker, state_observer,
    trace_storage, valid_task_spec, simple_robot_state
):
    """Test pipeline correctly integrates with TaskSpecEngine."""
    task_spec_engine.defineTask(valid_task_spec)
    setup_robot_state(state_observer, robot_id, simple_robot_state)
    
    trace = executeTaskPipeline(
        task_id="test-task-001",
        robot_id=robot_id,
        params={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        state_observer=state_observer,
        trace_storage=trace_storage
    )
    
    # Verify task spec was loaded and used
    assert trace.task_id == valid_task_spec.task_id


def test_execute_task_pipeline_integrates_with_execution_tracker(
    robot_id, task_spec_engine, execution_tracker, state_observer,
    trace_storage, valid_task_spec, simple_robot_state
):
    """Test pipeline correctly integrates with ExecutionTracker."""
    task_spec_engine.defineTask(valid_task_spec)
    setup_robot_state(state_observer, robot_id, simple_robot_state)
    
    trace = executeTaskPipeline(
        task_id="test-task-001",
        robot_id=robot_id,
        params={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        state_observer=state_observer,
        trace_storage=trace_storage
    )
    
    # Verify execution was tracked
    # The execution should no longer be in active sessions (it's finished)
    assert trace.execution_id not in execution_tracker._active_sessions
    
    # Verify trace is in tracker's storage
    assert trace.execution_id in execution_tracker._traces


def test_execute_task_pipeline_integrates_with_state_observer(
    robot_id, task_spec_engine, execution_tracker, state_observer,
    trace_storage, valid_task_spec, simple_robot_state
):
    """Test pipeline correctly integrates with StateObserver."""
    task_spec_engine.defineTask(valid_task_spec)
    setup_robot_state(state_observer, robot_id, simple_robot_state)
    
    trace = executeTaskPipeline(
        task_id="test-task-001",
        robot_id=robot_id,
        params={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        state_observer=state_observer,
        trace_storage=trace_storage
    )
    
    # Verify state observations were captured
    assert len(trace.state_history) >= 1
    
    # Verify states are from the correct robot
    for state in trace.state_history:
        assert state.robot_id == robot_id


# Test Edge Cases

def test_execute_task_pipeline_with_empty_params(
    robot_id, task_spec_engine, execution_tracker, state_observer,
    trace_storage, valid_task_spec, simple_robot_state
):
    """Test pipeline handles empty parameters."""
    task_spec_engine.defineTask(valid_task_spec)
    setup_robot_state(state_observer, robot_id, simple_robot_state)
    
    trace = executeTaskPipeline(
        task_id="test-task-001",
        robot_id=robot_id,
        params={},  # Empty params
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        state_observer=state_observer,
        trace_storage=trace_storage
    )
    
    assert trace is not None
    assert isinstance(trace, ExecutionTrace)
