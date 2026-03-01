"""
Unit tests for Step Failure Handling Strategies.

Tests cover:
- RETRY strategy with exponential backoff
- SKIP strategy with validation
- ABORT strategy with safe state return
- FALLBACK strategy with alternative sequences
- Logging of all failure strategies
"""

import pytest
from datetime import datetime
from uuid import uuid4

from src.stepbystep_robotics.workflow.task_execution import (
    executeTaskPipeline,
    TraceStorage,
    MockRobotExecutor,
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
)


# Fixtures

@pytest.fixture
def robot_id():
    """Create a robot ID for testing."""
    return uuid4()


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
    state_observer._record_state(state)


# Test Failure Handling Strategies

def test_failure_handling_retry_with_exponential_backoff(
    robot_id, task_spec_engine, execution_tracker, state_observer,
    trace_storage, simple_robot_state, monkeypatch
):
    """Test RETRY strategy with exponential backoff (Requirement 13.2)."""
    
    # Mock time.sleep to avoid delays in tests
    import time
    monkeypatch.setattr(time, 'sleep', lambda x: None)
    
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
    
    # Verify execution failed/aborted after max retries
    assert trace.status in [ExecutionStatus.FAILED, ExecutionStatus.ABORTED]


def test_failure_handling_skip_strategy(
    robot_id, task_spec_engine, execution_tracker, state_observer,
    trace_storage, simple_robot_state
):
    """Test SKIP strategy for failed steps (Requirement 13.3)."""
    
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
    assert trace.status in [ExecutionStatus.FAILED, ExecutionStatus.ABORTED]
    
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
