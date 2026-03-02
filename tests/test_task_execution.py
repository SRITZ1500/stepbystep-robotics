"""
Unit tests for task execution pipeline.

Tests cover:
- Task execution orchestration
- Precondition and postcondition verification
- Step execution and recording
- Performance metrics computation
- Trace persistence
- Error handling and safety
"""

import pytest
from datetime import datetime
from uuid import uuid4

from src.stepbystep_robotics.workflow.task_execution import (
    executeTaskPipeline,
    MockRobotExecutor,
    TraceStorage,
    _compute_performance_metrics,
    _evaluate_safety_constraint
)
from src.stepbystep_robotics.workflow import TaskSpecEngine, ExecutionTracker
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
    ExecutionStepRecord,
    PerformanceMetrics
)


# Fixtures

@pytest.fixture
def task_spec_engine():
    """Create a TaskSpecEngine instance with registered capabilities."""
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
def robot_executor():
    """Create a MockRobotExecutor instance."""
    return MockRobotExecutor()


@pytest.fixture
def trace_storage():
    """Create a TraceStorage instance."""
    return TraceStorage()


@pytest.fixture
def initial_robot_state():
    """Create an initial robot state for testing."""
    return RobotState(
        robot_id=uuid4(),
        timestamp=datetime.now(),
        position=Vector3D(0.0, 0.0, 0.0),
        orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
        joint_states={},
        sensor_readings={},
        actuator_states={},
        battery_level=0.8,
        error_flags=set()
    )


@pytest.fixture
def simple_task_spec():
    """Create a simple task specification."""
    return TaskSpecification(
        task_id="simple-task",
        name="Simple Task",
        description="A simple task for testing",
        preconditions=[
            Condition(
                type=ConditionType.STATE_GREATER_THAN,
                expression="battery_level > 0.5",
                tolerance=0.01
            )
        ],
        postconditions=[
            Condition(
                type=ConditionType.STATE_GREATER_THAN,
                expression="battery_level > 0.0",
                tolerance=0.01
            )
        ],
        steps=[
            TaskStep(
                step_id="step-1",
                action=ActionType.MOVE,
                parameters={"target": [1.0, 0.0, 0.0]},
                expected_duration=1.0,
                success_criteria=[],
                failure_handling=FailureStrategy.RETRY,
                max_retries=3
            ),
            TaskStep(
                step_id="step-2",
                action=ActionType.WAIT,
                parameters={"duration": 0.5},
                expected_duration=0.5,
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
                expression="battery_level > 0.1",
                tolerance=0.01
            )
        ]
    )


# Test executeTaskPipeline - Success Cases

def test_execute_task_pipeline_success(
    task_spec_engine,
    execution_tracker,
    robot_executor,
    trace_storage,
    initial_robot_state,
    simple_task_spec
):
    """Test successful task execution through the pipeline."""
    # Define task
    task_spec_engine.defineTask(simple_task_spec)
    
    # Execute task
    trace = executeTaskPipeline(
        task_"simple-task",
        robot_id=initial_robot_state.robot_id,
        parameters={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        initial_state=initial_robot_state,
        robot_executor=robot_executor,
        trace_storage=trace_storage
    )
    
    # Verify trace
    assert trace is not None
    assert trace.task_id == "simple-task"
    assert trace.robot_id == initial_robot_state.robot_id
    assert trace.status == ExecutionStatus.COMPLETED
    (trace.steps) == 2
    assert trace.steps[0].step_id == "step-1"
    assert trace.steps[1].step_id == "step-2"
    assert trace.performance_metrics is not None
    
    # Verify trace was persisted
    stored_trace = trace_storage.retrieve(n_id)
    assert stored_trace is not None
    assert stored_trace.execution_id == trace.execution_id


def test_execute_task_pipeline_records_all_steps(
    task_spec_engine,
    execution_tracker,
    robot_executor,
    trace_storage,
    initial_robot_state,
    simple_task_spec
):
    """Test that all steps are recorded in the trace."""
    task_spec_engine.defineTask(simple_task_spec)
    
    trace = executeTaskPipeline(
        task_id="simple-task",
        robot_id=initial_robot_state.robot_id,
        parameters={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        initial_state=initial_robot_state,
        robot_executor=robot_executor,
        trace_storage=trace_storage
    )
    
    # Verify all steps recorded
    assert len(trace.steps) == len(simple_task_spec.steps)
    
    # Verify step details
    for i, step_record in enumerate(trace.steps):
        expected_step = simple_task_spec.steps[i]
        assert step_record.step_id == expected_step.step_id
        assert step_record.start_time <= step_record.end_time
        assert step_record.actual_duration >= 0
        assert step_record.input_state is not None
        assert step_record.output_state is not None


def test_execute_task_pipeline_maintains_state_history(
    task_spec_engine,
    execution_tracker,
    robot_executor,
    trace_storage,
    initial_robot_state,
    simple_task_spec
):
    """Test that state history is maintained throughout execution."""
    task_spec_engine.defineTask()
    
    trace = executeTaskPipeline(
        task_id="simple-task",
        robot_id=initial_robot_state.robot_id,
        parameters={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        initial_state=initial_robot_state,
        robot_executor=robot_executor,
        trace_storage=trace_storage
    )
    
    # Verify state history
    assert len(trace.state_history) >= 1  # At least initial state
    assert trace.state_history[0] == initial_robot_state
   
    # Verify states are chronologically ordered
    for i in range(len(trace.state_history) - 1):
        assert trace.state_history[i].timestamp <= trace.state_history[i + 1].timestamp


# Test executeTaskPipeline - Precondition Failures

def test_execute_task_pipeline_precondition_not_satisfied(
    task_spec_engine,
    execution_tracker,
    robot_executor,
    trace_storage,
    simple_task_spec
):
    """Test task execution fails when preconditions are not satisfied."""
    task_spec_engine._task_spec)
    
    # Create state with low battery (below precondition threshold)
    low_battery_state = RobotState(
        robot_id=uuid4(),
        timestamp=datetime.now(),
        position=Vector3D(0.0, 0.0, 0.0),
        orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
        joint_states={},
        sensor_readings={},
        actuator_states={},
        battery_level=0.3,  # Below 0.5 threshold
        error_flags=set()
    )
    
    trace = executeTaskPipeline(
        task_id="simple-task",
        robot_id=low_battery_state.robot_id,
        parameters={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        initial_state=low_battery_state,
        robot_executor=robot_executor,
        trace_storage=trace_storage
    )
    
    # Verify execution failed
    assert trace.status == ExecutionStatus.FAILED
    assert len(trace.steps) == 0  # No steps executed
    assert len(trace.anomalies) > 0
    assert any("Preconditions not satisfied" in trace.anomalies)


def test_execute_task_pipeline_invalid_task_id(
    task_spec_engine,
    execution_tracker,
    robot_executor,
    trace_storage,
    initial_robot_state
):
    """Test task execution fails for invalid task ID."""
    trace = executeTaskPipeline(
        task_id="non-existent-task",
        robot_id=initial_robot_state.robot_id,
        parameters={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        initial_state=initial_robot_state,
        robot_executor=robot_executor,
        trace_storage=trace_storage
    )
    
    # Verify execution failed
    assert trace.status == ExecutionStatus.FAILED
    assert len(trace.steps) == 0
    assert len(trace.anomalies) > 0


# Test executeTaskPipeline - Postcondition Verification

def test_execute_task_pipeline_verifies_postconditions(
    task_spec_engine,
    execution_tracker,
    robot_executor,
    trace_storage,
    initial_robot_state
):
    """Test that postconditions 
    # Create task with specific postcondition
    task_spec = TaskSpecification(
        task_id="postcondition-task",
        name="Postcondition Task",
        description="Task with postcondition",
        preconditions=[],
        postconditions=[
            Condition(
                type=ConditionType.STATE_GREATER_THAN,
                expression="battery_level > 0.0",
                tolerance=0.01
            )
        ],
        steps=[
            TaskStep(
                step_id="step-1",
                action=ActionType.WAIT,
                parameters={},
                expected_duration=0.1,
                success_criteria=[],
                failure_handling=FailureStrategy.RETRY
            )
        ],
        timeout_seconds=10,
        required_capabilities=set(),
        safety_constraints=[]
    )
    
    task_spec_engine.defineTask(task_spec)
    
    trace = executeTaskPipeline(
        task_id="postcondition-task",
        robot_id=initial_robot_state.robot_id,
    ,
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        initial_state=initial_robot_state,
        robot_executor=robot_executor,
        trace_storage=trace_storage
    )
    
    # Postconditions should be satisfied (battery > 0.0)
    assert trace.status == ExecutionStatus.COMPLETED


# Test executeTaskPipeline - Performance Metrics

def test_execute_task_pipeline_computes_metrics(
    task_spec_engine,
    execution_tracker,
    robot_executor,
    trace_storage,
    initial_robot_state,
    simple_task_spec
):
    """Test that performance metrics are computed."""
    task_spec_engine.defineTask(simple_task_spec)
    
    trace = executeTaskPipeline(
        task_id="simple-task",
        robot_id=initial_robot_state.robot_id,
        parameters={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        initial_state=initial_robot_state,
        robot_executor=robot_executor,
        trace_storage=trace_storage
    )
    
    # Verify metrics exist
    assert trace.performance_metrics is not None
    metrics = trace.performance_metrics
    
    # Verify metric values
    assert metrics.execution_id == trace.execution_id
    assert metrics.total_duration >= 0
    assert 0.0 <= metrics.success_rate <= 1.0
    assert metrics.energy_consumed >= 0
    assert 0.0 <= metrics.accuracy_score <= 1.0
    assert 0.0 <= metrics.smoothness_score <= 1.0
    assert 0.0 <= metrics.safety_score <= 1.0
    assert len(meteps)


def test_execute_task_pipeline_metrics_success_rate(
    task_spec_engine,
    execution_tracker,
    robot_executor,
    trace_storage,
    initial_robot_state,
    simple_task_spec
):
    """Test that success rate is computed correctly."""
    task_spec_engine.defineTask(simple_task_spec)
    
    trace = executeTaskPipeline(
        task_id="simple-task",
        robot_id=initial_robot_state.robot_id,
        parameters={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        initial_state=initial_robot_state,
        robot_executor=robot_executor,
        trace_storage=trace_storage
    )
    
    # All steps should succeed
    successful_steps = sum(1 for s in trace.steps if s.status == StepStatus.COMPLETED)
    expected_success_rate = successful_steps / len(trace.steps) if trace.steps else 0.0
    
    assert trace.performance_metrics.success_rate == expected_success_rate


# Test executeTaskPipeline - Safety Constraints

def test_execute_task_pipelineafety_constraints(
    task_spec_engine,
    execution_tracker,
    trace_storage,
    initial_robot_state
):
    """Test that safety constraints are enforced during execution."""
    # Create task with strict safety constraint
    task_spec = TaskSpecification(
        task_id="safety-task",
        name="Safety Task",
        description="Task with safety constraints",
        preconditions=[],
        postconditions=[],
        steps=[
            TaskStep(
                step_id="step-1",
       action=ActionType.MOVE,
                parameters={},
                expected_duration=1.0,
                success_criteria=[],
                failure_handling=FailureStrategy.RETRY
            )
        ],
        timeout_seconds=10,
        required_capabilities={"move"},
        safety_constraints=[
            Condition(
                type=ConditionType.STATE_GREATER_THAN,
                expression="battery_level > 0.9",  # Very high threshold
                tolerance=0.01
            )
        ]
    )
    
    task_spec_engine.defineTask(task_spec)
    
    # Create robot executor that drains battery below safety threshold
    class UnsafeRobotExecutor(MockRobotExecutor):
        def execute_step(self, step_id, action_type, parameters, robot_id, current_state):
            # Drain battery below safety threshold
            new_state = RobotState(
                robot_id=robot_id,
                timestamp=datetime.now(),
                position=current_state.position,
                orientation=current_state.orientation,
                joint_states=current_state.joint_states.copy(),
                sensor_readings=current_state.sensor_readings.copy(),
                actuator_states=current_state.actuator_states.copy(),
                battery_level=0.5,  # Below 0.9 threshold
                error_flags=current_state.error_flags.copy()
            )
            return new_state, StepStatus.COMPLETED
    
    unsafe_executor = UnsafeRobotExecutor()
    
    trace = executeTaskPipeline(
    d="safety-task",
        robot_id=initial_robot_state.robot_id,
        parameters={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        initial_state=initial_robot_state,
        robot_executor=unsafe_executor,
        trace_storage=trace_storage
    )
    
    # Execution should be aborted due to safety violation
    assert trace.status == ExecutionStatus.ABORTED
    assert any("Safety constraint violated" in a.description for a in trace.anomalies)


# Test executeTaskipeline - Timeout Handling

def test_execute_task_pipeline_handles_timeout(
    task_spec_engine,
    execution_tracker,
    trace_storage,
    initial_robot_state
):
    """Test that execution timeout is enforced."""
    # Create task with very short timeout
    task_spec = TaskSpecification(
        task_id="timeout-task",
        name="Timeout Task",
        description="Task with short timeout",
        preconditions=[],
        postconditions=[],
        steps=[
            TaskStep(
                step_id="step-1",
                action=ActionType.WAIT,
                parameters={},
                expected_duration=10.0,  # Long expected duration
                success_criteria=[],
                failure_handling=FailureStrategy.RETRY
            )
        ],
        timeout_seconds=0,  # Immediate timeout
        required_capabilities=set(),
        safety_constraints=[]
    )
    
    task_spec_engine.defineTask(task_spec)
    
    trace = executeTaskPipeline(
        task_id="timeout-task",
        robot_id=initial_robot_state.robot_id,
        parameters={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        initial_state=initial_robot_state,
        robot_executor=MockRobotExecutor(),
        trace_storage=trace_storage
    )
    
    # Execution should timeout
    assert trace.status == ExecutionStatus.TIMEOUT
    assert any("timeout" in a.description.lower() for a in trace.anomalies)


# Test executeTaskPipeline - Trace Persistence

def ask_pipeline_persists_trace(
    task_spec_engine,
    execution_tracker,
    robot_executor,
    trace_storage,
    initial_robot_state,
    simple_task_spec
):
    """Test that execution trace is persisted to storage."""
    task_spec_engine.defineTask(simple_task_spec)
    
    trace = executeTaskPipeline(
        task_id="simple-task",
        robot_id=initial_robot_state.robot_id,
        parameters={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        initial_state=initial_robot_state,
        robot_executor=robot_executor,
        trace_storage=trace_storage
    )
    
    # Verify trace was persisted
    stored_trace = trace_storage.retrieve(trace.execution_id)
    assert stored_trace is not None
    assert stored_trace.execution_id == trace.execution_id
    assert stored_trace.task_id == trace.task_id
    assert stored_trace.status == trace.status


# Test Helper Functions

def test_compute_performance_metrics():
    """Test performance metrics computation."""
    # Create a sample trace
    robot_id = uuid4()
    execution_id = "test-execution"
    start_time = datetime.now()
    
    initial_state = RobotState(
        robot_id=robot_id,
        timestamp=start_time,
        position=Vector3D(0.0, 0.0, 0.0),
        orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
        joint_states={},
        sensor_readings={},
        actuator_states={},
        battery_level=1.0,
        error_flags=set()
    )
    
    final_state = RobotState(
        robot_id=robot_id,
  timestamp=start_time,
        position=Vector3D(1.0, 0.0, 0.0),
        orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
        joint_states={},
        sensor_readings={},
        actuator_states={},
        battery_level=0.8,
        error_flags=set()
    )
    
    step_record = ExecutionStepRecord(
        step_id="step-1",
        start_time=start_time,
        end_time=start_time,
        status=StepStatus.COMPLETED,
        input_state=initial_state,
        output_state=final_state,
     n=1.0,
        deviations=[],
        retry_count=0
    )
    
    trace = ExecutionTrace(
        execution_id=execution_id,
        task_id="test-task",
        robot_id=robot_id,
        start_time=start_time,
        end_time=start_time,
        status=ExecutionStatus.COMPLETED,
        steps=[step_record],
        state_history=[initial_state, final_state],
        anomalies=[],
        performance_metrics=None
    )
    
    # Compute metrics
    metrics = _compute_performance_metrics(trace)
    
    # Verify metrics
    assert metrics.execution_id == execution_id
    assert metrics.total_duration >= 0
    assert metrics.success_rate == 1.0  # All steps completed
    assert metrics.energy_consumed == 0.2  # 1.0 - 0.8
    assert 0.0 <= metrics.accuracy_score <= 1.0
    assert 0.0 <= metrics.smoothness_score <= 1.0
    assert 0.0 <= metrics.safety_score <= 1.0


def test_evaluate_safety_constraint():
    """Test safety constraint evaluation."""
    state = RobotState(
        robot_id=uuid4(),
  stamp=datetime.now(),
        position=Vector3D(0.0, 0.0, 0.0),
        orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
        joint_states={},
        sensor_readings={},
        actuator_states={},
        battery_level=0.6,
        error_flags=set()
    )
    
    # Test constraint satisfied
    constraint_satisfied = Condition(
        type=ConditionType.STATE_GREATER_THAN,
        expression="battery_level > 0.5",
        tolerance=0.01
    )
    e) is True
    
    # Test constraint violated
    constraint_violated = Condition(
        type=ConditionType.STATE_GREATER_THAN,
        expression="battery_level > 0.7",
        tolerance=0.01
    )
    assert _evaluate_safety_constraint(constraint_violated, state) is False


# Test MockRobotExecutor

def test_mock_robot_executor_execute_step():
    """Test MockRobotExecutor step execution."""
    executor = MockRobotExecutor()
    robot_id = uuid4()
    
    current_state = RobotState(
        robot_id=obot_id,
        timestamp=datetime.now(),
        position=Vector3D(0.0, 0.0, 0.0),
        orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
        joint_states={},
        sensor_readings={},
        actuator_states={},
        battery_level=0.8,
        error_flags=set()
    )
    
    new_state, status = executor.execute_step(
        step_id="test-step",
        action_type="MOVE",
        parameters={},
        robot_id=robot_id,
        current_state=current_state
    )
    
    assert new_state is not None
    assert status == StepStatus.COMPLETED
    assert new_state.battery_level < current_state.battery_level  # Battery drained


def test_mock_robot_executor_enter_safe_state():
    """Test MockRobotExecutor safe state entry."""
    executor = MockRobotExecutor()
    robot_id = uuid4()
    
    current_state = RobotState(
        robot_id=robot_id,
        timestamp=datetime.now(),
        position=Vector3D(0.0, 0.0, 0.0),
        orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
        joint_states={},
  r_readings={},
        actuator_states={},
        battery_level=0.8,
        error_flags=set()
    )
    
    safe_state = executor.enter_safe_state(robot_id, current_state)
    
    assert safe_state is not None
    assert 'SAFE_MODE' in safe_state.error_flags


# Test TraceStorage

def test_trace_storage_persist_and_retrieve():
    """Test trace storage persistence and retrieval."""
    storage = TraceStorage()
    robot_id = uuid4()
    
    trace = ExecutionTrace(
        execution_id="test-execution",
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
    retrieved = storage.retrieve("test-execution")
    assert retrieved is not None
    assert retrieved.execution_id == "test-execution"


def test_trace_storage_list_all():
    """Test listing all traces from storage."""
    storage = TraceStorage()
    robot_id = uuid4()
    
    # Create and persist multiple traces
    for i in range(3):
        trace = ExecutionTrace(
            execution_id=f"execution-{i}",
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
        storage.persist(trace)
    
    # List all traces
    all_traces = storage.list_all()
    assert len(all_traces) == 3


# Test Failure Handling Strategies

def test_failure_handling_retry_with_exponential_backoff(
    robot_id, task_spec_engine, execution_tracker, state_observer,
    trace_storage, simple_robot_state
):
    """Test RETRY strategy with exponential backoff (Requirement 13.2)."""
    from src.stepbystep_robotics.workflow.task_execution import MockRobotExecutor
    
    # Create a custom robot executor that fails first, then succeeds
    class FailThenSucceedExecutor(MockRobotExecutor):
        def __init__(self):
            super().__init__()
            self.attempt_count = 0
        
        def execute_step(self, step_id, action_type, parameters, robot_id, current_state):
            self.attempt_count += 1
            if self.attempt_count == 1:
                # First attempt fails
                return current_state, StepStatus.FAILED
            else:
                # Subsequent attempts succeed
                return super().execute_step(step_id, action_type, parameters, robot_id, current_state)
    
    # Create task with RETRY strategy
    retry_task = TaskSpecification(
        task_id="retry-task",
        name="Retry Task",
        description="Task with retry on failure",
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
                failure_handling=FailureStrategy.RETRY,
                max_retries=3
            )
        ],
        timeout_seconds=60,
        required_capabilities={"move"},
        safety_constraints=[]
    )
    
    task_spec_engine.defineTask(retry_task)
    setup_robot_state(state_observer, robot_id, simple_robot_state)
    
    # Execute task with custom executor
    custom_executor = FailThenSucceedExecutor()
    trace = executeTaskPipeline(
        task_id="retry-task",
        robot_id=robot_id,
        params={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        state_observer=state_observer,
        trace_storage=trace_storage,
        robot_executor=custom_executor
    )
    
    # Verify retry occurred
    assert custom_executor.attempt_count == 2  # Failed once, then succeeded
    
    # Verify trace contains retry anomaly
    retry_anomalies = [a for a in trace.anomalies if a.anomaly_type == "STEP_RETRY"]
    assert len(retry_anomalies) > 0
    
    # Verify execution completed successfully after retry
    assert trace.status == ExecutionStatus.COMPLETED


def test_failure_handling_retry_max_retries_exceeded(
    robot_id, task_spec_engine, execution_tracker, state_observer,
    trace_storage, simple_robot_state
):
    """Test RETRY strategy when max retries exceeded (Requirement 13.1, 13.2)."""
    from src.stepbystep_robotics.workflow.task_execution import MockRobotExecutor
    
    # Create a custom robot executor that always fails
    class AlwaysFailExecutor(MockRobotExecutor):
        def __init__(self):
            super().__init__()
            self.attempt_count = 0
        
        def execute_step(self, step_id, action_type, parameters, robot_id, current_state):
            self.attempt_count += 1
            return current_state, StepStatus.FAILED
    
    # Create task with RETRY strategy and max_retries=2
    retry_task = TaskSpecification(
        task_id="retry-fail-task",
        name="Retry Fail Task",
        description="Task that fails all retries",
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
                failure_handling=FailureStrategy.RETRY,
                max_retries=2
            )
        ],
        timeout_seconds=60,
        required_capabilities={"move"},
        safety_constraints=[]
    )
    
    task_spec_engine.defineTask(retry_task)
    setup_robot_state(state_observer, robot_id, simple_robot_state)
    
    # Execute task with custom executor
    custom_executor = AlwaysFailExecutor()
    trace = executeTaskPipeline(
        task_id="retry-fail-task",
        robot_id=robot_id,
        params={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        state_observer=state_observer,
        trace_storage=trace_storage,
        robot_executor=custom_executor
    )
    
    # Verify all retries were attempted (initial + 2 retries = 3 total)
    assert custom_executor.attempt_count == 3
    
    # Verify execution failed after max retries
    assert trace.status == ExecutionStatus.FAILED


def test_failure_handling_skip_strategy(
    robot_id, task_spec_engine, execution_tracker, state_observer,
    trace_storage, simple_robot_state
):
    """Test SKIP strategy for failed steps (Requirement 13.3)."""
    from src.stepbystep_robotics.workflow.task_execution import MockRobotExecutor
    
    # Create a custom robot executor that fails specific step
    class FailStepOneExecutor(MockRobotExecutor):
        def execute_step(self, step_id, action_type, parameters, robot_id, current_state):
            if step_id == "step-1":
                return current_state, StepStatus.FAILED
            else:
                return super().execute_step(step_id, action_type, parameters, robot_id, current_state)
    
    # Create task with SKIP strategy
    skip_task = TaskSpecification(
        task_id="skip-task",
        name="Skip Task",
        description="Task with skip on failure",
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
                failure_handling=FailureStrategy.SKIP,
                max_retries=0
            ),
            TaskStep(
                step_id="step-2",
                action=ActionType.GRASP,
                parameters={},
                expected_duration=1.0,
                success_criteria=[],
                failure_handling=FailureStrategy.ABORT,
                max_retries=0
            )
        ],
        timeout_seconds=30,
        required_capabilities={"move", "grasp"},
        safety_constraints=[]
    )
    
    task_spec_engine.defineTask(skip_task)
    setup_robot_state(state_observer, robot_id, simple_robot_state)
    
    # Execute task with custom executor
    custom_executor = FailStepOneExecutor()
    trace = executeTaskPipeline(
        task_id="skip-task",
        robot_id=robot_id,
        params={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        state_observer=state_observer,
        trace_storage=trace_storage,
        robot_executor=custom_executor
    )
    
    # Verify step was skipped
    skip_anomalies = [a for a in trace.anomalies if a.anomaly_type == "STEP_SKIPPED"]
    assert len(skip_anomalies) > 0
    
    # Verify execution continued to step-2
    step_ids = [s.step_id for s in trace.steps]
    assert "step-2" in step_ids
    
    # Verify execution completed (step-1 was skipped, step-2 succeeded)
    assert trace.status == ExecutionStatus.COMPLETED


def test_failure_handling_abort_strategy(
    robot_id, task_spec_engine, execution_tracker, state_observer,
    trace_storage, simple_robot_state
):
    """Test ABORT strategy returns robot to safe state (Requirement 13.4)."""
    from src.stepbystep_robotics.workflow.task_execution import MockRobotExecutor
    
    # Create a custom robot executor that fails
    class FailExecutor(MockRobotExecutor):
        def execute_step(self, step_id, action_type, parameters, robot_id, current_state):
            return current_state, StepStatus.FAILED
    
    # Create task with ABORT strategy
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
                failure_handling=FailureStrategy.ABORT,
                max_retries=0
            ),
            TaskStep(
                step_id="step-2",
                action=ActionType.GRASP,
                parameters={},
                expected_duration=1.0,
                success_criteria=[],
                failure_handling=FailureStrategy.ABORT,
                max_retries=0
            )
        ],
        timeout_seconds=30,
        required_capabilities={"move", "grasp"},
        safety_constraints=[]
    )
    
    task_spec_engine.defineTask(abort_task)
    setup_robot_state(state_observer, robot_id, simple_robot_state)
    
    # Execute task with custom executor
    custom_executor = FailExecutor()
    trace = executeTaskPipeline(
        task_id="abort-task",
        robot_id=robot_id,
        params={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        state_observer=state_observer,
        trace_storage=trace_storage,
        robot_executor=custom_executor
    )
    
    # Verify execution was aborted
    assert trace.status == ExecutionStatus.FAILED
    
    # Verify step-2 was not executed (aborted after step-1 failed)
    step_ids = [s.step_id for s in trace.steps]
    assert "step-2" not in step_ids
    
    # Verify robot is in safe state
    if len(trace.state_history) > 0:
        final_state = trace.state_history[-1]
        assert 'SAFE_MODE' in final_state.error_flags


def test_failure_handling_fallback_strategy(
    robot_id, task_spec_engine, execution_tracker, state_observer,
    trace_storage, simple_robot_state
):
    """Test FALLBACK strategy executes alternative sequences (Requirement 13.5)."""
    from src.stepbystep_robotics.workflow.task_execution import MockRobotExecutor
    
    # Create a custom robot executor that fails primary step
    class FailPrimaryExecutor(MockRobotExecutor):
        def execute_step(self, step_id, action_type, parameters, robot_id, current_state):
            if step_id == "step-1":
                return current_state, StepStatus.FAILED
            else:
                # Fallback steps succeed
                return super().execute_step(step_id, action_type, parameters, robot_id, current_state)
    
    # Create fallback steps
    fallback_steps = [
        TaskStep(
            step_id="fallback-1",
            action=ActionType.WAIT,
            parameters={},
            expected_duration=0.5,
            success_criteria=[],
            failure_handling=FailureStrategy.ABORT,
            max_retries=0
        ),
        TaskStep(
            step_id="fallback-2",
            action=ActionType.MOVE,
            parameters={},
            expected_duration=1.0,
            success_criteria=[],
            failure_handling=FailureStrategy.ABORT,
            max_retries=0
        )
    ]
    
    # Create task with FALLBACK strategy
    fallback_task = TaskSpecification(
        task_id="fallback-task",
        name="Fallback Task",
        description="Task with fallback on failure",
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
                failure_handling=FailureStrategy.FALLBACK,
                max_retries=0,
                fallback_steps=fallback_steps
            ),
            TaskStep(
                step_id="step-2",
                action=ActionType.GRASP,
                parameters={},
                expected_duration=1.0,
                success_criteria=[],
                failure_handling=FailureStrategy.ABORT,
                max_retries=0
            )
        ],
        timeout_seconds=30,
        required_capabilities={"move", "grasp"},
        safety_constraints=[]
    )
    
    task_spec_engine.defineTask(fallback_task)
    setup_robot_state(state_observer, robot_id, simple_robot_state)
    
    # Execute task with custom executor
    custom_executor = FailPrimaryExecutor()
    trace = executeTaskPipeline(
        task_id="fallback-task",
        robot_id=robot_id,
        params={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        state_observer=state_observer,
        trace_storage=trace_storage,
        robot_executor=custom_executor
    )
    
    # Verify fallback was executed
    fallback_anomalies = [a for a in trace.anomalies if a.anomaly_type == "FALLBACK_EXECUTION"]
    assert len(fallback_anomalies) > 0
    
    # Verify fallback steps were recorded
    step_ids = [s.step_id for s in trace.steps]
    assert "step-1-fallback-fallback-1" in step_ids
    assert "step-1-fallback-fallback-2" in step_ids
    
    # Verify execution continued to step-2
    assert "step-2" in step_ids
    
    # Verify execution completed
    assert trace.status == ExecutionStatus.COMPLETED


def test_failure_handling_all_strategies_logged(
    robot_id, task_spec_engine, execution_tracker, state_observer,
    trace_storage, simple_robot_state
):
    """Test that all failure strategies are logged in execution trace (Requirement 13.6)."""
    from src.stepbystep_robotics.workflow.task_execution import MockRobotExecutor
    
    # Create a custom robot executor that fails
    class FailExecutor(MockRobotExecutor):
        def execute_step(self, step_id, action_type, parameters, robot_id, current_state):
            if step_id == "step-1":
                return current_state, StepStatus.FAILED
            else:
                return super().execute_step(step_id, action_type, parameters, robot_id, current_state)
    
    # Create task with SKIP strategy
    skip_task = TaskSpecification(
        task_id="log-test-task",
        name="Log Test Task",
        description="Task to test logging",
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
                failure_handling=FailureStrategy.SKIP,
                max_retries=0
            )
        ],
        timeout_seconds=30,
        required_capabilities={"move"},
        safety_constraints=[]
    )
    
    task_spec_engine.defineTask(skip_task)
    setup_robot_state(state_observer, robot_id, simple_robot_state)
    
    # Execute task
    custom_executor = FailExecutor()
    trace = executeTaskPipeline(
        task_id="log-test-task",
        robot_id=robot_id,
        params={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        state_observer=state_observer,
        trace_storage=trace_storage,
        robot_executor=custom_executor
    )
    
    # Verify failure handling was logged
    assert len(trace.anomalies) > 0
    
    # Verify anomaly contains relevant information
    skip_anomaly = next((a for a in trace.anomalies if a.anomaly_type == "STEP_SKIPPED"), None)
    assert skip_anomaly is not None
    assert skip_anomaly.severity in ["WARNING", "INFO"]
    assert "step-1" in skip_anomaly.description
    assert "step_id" in skip_anomaly.context
