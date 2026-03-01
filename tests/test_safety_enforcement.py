"""
Unit tests for Safety Constraint Enforcement in Task Execution Pipeline.

Tests cover:
- Comprehensive safety constraint validation at every state transition
- Immediate abort on safety violation
- Safe state return with proper error handling
- Detailed safety violation recording in trace
- Safety validation after each step execution

Requirements:
- 6.1: System shall validate robot states against safety constraints
- 6.2: System shall abort execution immediately on safety violation
- 6.3: System shall command robot to safe state on abort
- 6.4: System shall record safety violations in execution trace
- 6.5: System shall prevent unsafe state transitions
"""

import pytest
from datetime import datetime
from uuid import uuid4

from src.stepbystep_robotics.workflow.task_execution import (
    executeTaskPipeline,
    TraceStorage,
    MockRobotExecutor,
    _validate_safety_constraints,
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
def safe_robot_state(robot_id):
    """Create a safe robot state for testing."""
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
def unsafe_battery_state(robot_id):
    """Create a robot state with unsafe battery level."""
    return RobotState(
        robot_id=robot_id,
        timestamp=datetime.now(),
        position=Vector3D(0.0, 0.0, 0.0),
        orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
        joint_states={},
        sensor_readings={},
        actuator_states={},
        battery_level=0.15,  # Below safety threshold
        error_flags=set(),
        metadata={}
    )


@pytest.fixture
def task_with_safety_constraints():
    """Create a task specification with safety constraints."""
    return TaskSpecification(
        task_id="safety-task-001",
        name="Safety Test Task",
        description="Task with safety constraints",
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
                max_retries=0
            ),
            TaskStep(
                step_id="step-2",
                action=ActionType.GRASP,
                parameters={},
                expected_duration=1.0,
                success_criteria=[],
                failure_handling=FailureStrategy.RETRY,
                max_retries=0
            )
        ],
        timeout_seconds=30,
        required_capabilities={"move", "grasp"},
        safety_constraints=[
            Condition(
                type=ConditionType.STATE_GREATER_THAN,
                expression="battery_level > 0.2",
                tolerance=0.01
            )
        ]
    )


# Test _validate_safety_constraints function

def test_validate_safety_constraints_battery_greater_than_satisfied(robot_id, safe_robot_state):
    """Test safety validation passes when battery constraint is satisfied."""
    constraints = [
        Condition(
            type=ConditionType.STATE_GREATER_THAN,
            expression="battery_level > 0.5",
            tolerance=0.01
        )
    ]
    
    violation = _validate_safety_constraints(constraints, safe_robot_state, "test-step")
    
    assert violation is None


def test_validate_safety_constraints_battery_greater_than_violated(robot_id, unsafe_battery_state):
    """Test safety validation detects battery constraint violation."""
    constraints = [
        Condition(
            type=ConditionType.STATE_GREATER_THAN,
            expression="battery_level > 0.2",
            tolerance=0.01
        )
    ]
    
    violation = _validate_safety_constraints(constraints, unsafe_battery_state, "test-step")
    
    assert violation is not None
    assert violation['constraint'] == "battery_level > 0.2"
    assert violation['current_value'] == 0.15
    assert violation['step_id'] == "test-step"
    assert 'details' in violation


def test_validate_safety_constraints_returns_detailed_violation_info(robot_id, unsafe_battery_state):
    """Test that safety validation returns comprehensive violation details (Requirement 6.4)."""
    constraints = [
        Condition(
            type=ConditionType.STATE_GREATER_THAN,
            expression="battery_level > 0.2",
            tolerance=0.01
        )
    ]
    
    violation = _validate_safety_constraints(constraints, unsafe_battery_state, "step-1")
    
    # Verify all required fields are present
    assert violation is not None
    assert 'constraint' in violation
    assert 'type' in violation
    assert 'current_value' in violation
    assert 'expected_value' in violation
    assert 'threshold' in violation
    assert 'tolerance' in violation
    assert 'step_id' in violation
    assert 'details' in violation
    
    # Verify values are correct
    assert violation['constraint'] == "battery_level > 0.2"
    assert violation['current_value'] == 0.15
    assert violation['threshold'] == 0.2
    assert violation['tolerance'] == 0.01
    assert violation['step_id'] == "step-1"


def test_validate_safety_constraints_position_constraint(robot_id):
    """Test safety validation for position constraints."""
    state = RobotState(
        robot_id=robot_id,
        timestamp=datetime.now(),
        position=Vector3D(-1.0, 0.0, 0.0),  # Negative x position
        orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
        joint_states={},
        sensor_readings={},
        actuator_states={},
        battery_level=0.8,
        error_flags=set(),
        metadata={}
    )
    
    constraints = [
        Condition(
            type=ConditionType.STATE_GREATER_THAN,
            expression="position.x > 0.0",
            tolerance=0.01
        )
    ]
    
    violation = _validate_safety_constraints(constraints, state, "test-step")
    
    assert violation is not None
    assert violation['constraint'] == "position.x > 0.0"
    assert violation['current_value'] == -1.0


def test_validate_safety_constraints_error_flags(robot_id):
    """Test safety validation detects critical error flags."""
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
    
    constraints = [
        Condition(
            type=ConditionType.STATE_EQUALS,
            expression="error_flags == empty",
            tolerance=0.0
        )
    ]
    
    violation = _validate_safety_constraints(constraints, state, "test-step")
    
    assert violation is not None
    assert 'MOTOR_FAILURE' in str(violation['current_value'])


# Test executeTaskPipeline with safety enforcement

def test_execute_task_pipeline_validates_safety_before_each_step(
    robot_id, task_spec_engine, execution_tracker, state_observer,
    trace_storage, task_with_safety_constraints, safe_robot_state
):
    """Test that pipeline validates safety constraints before each step (Requirement 6.1)."""
    task_spec_engine.defineTask(task_with_safety_constraints)
    state_observer._record_state(safe_robot_state)
    
    # Create custom executor that gradually drains battery
    class BatteryDrainExecutor(MockRobotExecutor):
        def __init__(self):
            super().__init__()
            self.step_count = 0
        
        def execute_step(self, step_id, action_type, parameters, robot_id, current_state):
            self.step_count += 1
            # Drain battery significantly on second step to trigger violation
            new_state = RobotState(
                robot_id=robot_id,
                timestamp=datetime.now(),
                position=current_state.position,
                orientation=current_state.orientation,
                joint_states=current_state.joint_states.copy(),
                sensor_readings=current_state.sensor_readings.copy(),
                actuator_states=current_state.actuator_states.copy(),
                battery_level=0.1 if self.step_count >= 2 else 0.5,  # Violate on step 2
                error_flags=current_state.error_flags.copy(),
                metadata=current_state.metadata.copy()
            )
            return new_state, StepStatus.COMPLETED
    
    custom_executor = BatteryDrainExecutor()
    
    trace = executeTaskPipeline(
        task_id="safety-task-001",
        robot_id=robot_id,
        params={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        state_observer=state_observer,
        trace_storage=trace_storage,
        robot_executor=custom_executor
    )
    
    # Verify execution was aborted due to safety violation
    assert trace.status == ExecutionStatus.ABORTED
    
    # Verify safety violation was recorded
    safety_violations = [a for a in trace.anomalies if a.anomaly_type == "SAFETY_VIOLATION"]
    assert len(safety_violations) > 0
    
    # Verify violation details are present
    violation = safety_violations[0]
    assert violation.severity == "CRITICAL"
    assert 'constraint_expression' in violation.context
    assert 'current_value' in violation.context
    assert 'expected_value' in violation.context


def test_execute_task_pipeline_aborts_immediately_on_violation(
    robot_id, task_spec_engine, execution_tracker, state_observer,
    trace_storage, task_with_safety_constraints, safe_robot_state
):
    """Test that pipeline aborts immediately when safety violation detected (Requirement 6.2)."""
    task_spec_engine.defineTask(task_with_safety_constraints)
    state_observer._record_state(safe_robot_state)
    
    # Create executor that violates safety on first step
    class ViolateOnFirstStepExecutor(MockRobotExecutor):
        def execute_step(self, step_id, action_type, parameters, robot_id, current_state):
            # Return state with critically low battery
            unsafe_state = RobotState(
                robot_id=robot_id,
                timestamp=datetime.now(),
                position=current_state.position,
                orientation=current_state.orientation,
                joint_states=current_state.joint_states.copy(),
                sensor_readings=current_state.sensor_readings.copy(),
                actuator_states=current_state.actuator_states.copy(),
                battery_level=0.05,  # Below safety threshold of 0.2
                error_flags=current_state.error_flags.copy(),
                metadata=current_state.metadata.copy()
            )
            return unsafe_state, StepStatus.COMPLETED
    
    custom_executor = ViolateOnFirstStepExecutor()
    
    trace = executeTaskPipeline(
        task_id="safety-task-001",
        robot_id=robot_id,
        params={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        state_observer=state_observer,
        trace_storage=trace_storage,
        robot_executor=custom_executor
    )
    
    # Verify execution was aborted
    assert trace.status == ExecutionStatus.ABORTED
    
    # Verify only first step was executed (immediate abort)
    assert len(trace.steps) == 1
    assert trace.steps[0].step_id == "step-1"
    
    # Verify second step was NOT executed
    step_ids = [s.step_id for s in trace.steps]
    assert "step-2" not in step_ids


def test_execute_task_pipeline_commands_robot_to_safe_state_on_abort(
    robot_id, task_spec_engine, execution_tracker, state_observer,
    trace_storage, task_with_safety_constraints, safe_robot_state
):
    """Test that pipeline commands robot to safe state on abort (Requirement 6.3)."""
    task_spec_engine.defineTask(task_with_safety_constraints)
    state_observer._record_state(safe_robot_state)
    
    # Create executor that violates safety
    class ViolateExecutor(MockRobotExecutor):
        def execute_step(self, step_id, action_type, parameters, robot_id, current_state):
            unsafe_state = RobotState(
                robot_id=robot_id,
                timestamp=datetime.now(),
                position=current_state.position,
                orientation=current_state.orientation,
                joint_states=current_state.joint_states.copy(),
                sensor_readings=current_state.sensor_readings.copy(),
                actuator_states=current_state.actuator_states.copy(),
                battery_level=0.05,
                error_flags=current_state.error_flags.copy(),
                metadata=current_state.metadata.copy()
            )
            return unsafe_state, StepStatus.COMPLETED
    
    custom_executor = ViolateExecutor()
    
    trace = executeTaskPipeline(
        task_id="safety-task-001",
        robot_id=robot_id,
        params={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        state_observer=state_observer,
        trace_storage=trace_storage,
        robot_executor=custom_executor
    )
    
    # Verify robot was commanded to safe state
    if len(trace.state_history) > 0:
        final_state = trace.state_history[-1]
        # Safe state should have SAFE_MODE flag
        assert 'SAFE_MODE' in final_state.error_flags


def test_execute_task_pipeline_records_safety_violations_in_trace(
    robot_id, task_spec_engine, execution_tracker, state_observer,
    trace_storage, task_with_safety_constraints, safe_robot_state
):
    """Test that pipeline records safety violations in trace with details (Requirement 6.4)."""
    task_spec_engine.defineTask(task_with_safety_constraints)
    state_observer._record_state(safe_robot_state)
    
    # Create executor that violates safety
    class ViolateExecutor(MockRobotExecutor):
        def execute_step(self, step_id, action_type, parameters, robot_id, current_state):
            unsafe_state = RobotState(
                robot_id=robot_id,
                timestamp=datetime.now(),
                position=current_state.position,
                orientation=current_state.orientation,
                joint_states=current_state.joint_states.copy(),
                sensor_readings=current_state.sensor_readings.copy(),
                actuator_states=current_state.actuator_states.copy(),
                battery_level=0.05,
                error_flags=current_state.error_flags.copy(),
                metadata=current_state.metadata.copy()
            )
            return unsafe_state, StepStatus.COMPLETED
    
    custom_executor = ViolateExecutor()
    
    trace = executeTaskPipeline(
        task_id="safety-task-001",
        robot_id=robot_id,
        params={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        state_observer=state_observer,
        trace_storage=trace_storage,
        robot_executor=custom_executor
    )
    
    # Verify safety violation was recorded
    safety_violations = [a for a in trace.anomalies if a.anomaly_type == "SAFETY_VIOLATION"]
    assert len(safety_violations) > 0
    
    violation = safety_violations[0]
    
    # Verify comprehensive violation details
    assert violation.severity == "CRITICAL"
    assert violation.timestamp is not None
    assert 'constraint_expression' in violation.context
    assert 'constraint_type' in violation.context
    assert 'current_value' in violation.context
    assert 'expected_value' in violation.context
    assert 'step_id' in violation.context
    assert 'violation_details' in violation.context
    
    # Verify specific values
    assert violation.context['constraint_expression'] == "battery_level > 0.2"
    assert violation.context['current_value'] == 0.05


def test_execute_task_pipeline_prevents_unsafe_state_transitions(
    robot_id, task_spec_engine, execution_tracker, state_observer,
    trace_storage, task_with_safety_constraints, safe_robot_state
):
    """Test that pipeline prevents unsafe state transitions (Requirement 6.5)."""
    task_spec_engine.defineTask(task_with_safety_constraints)
    state_observer._record_state(safe_robot_state)
    
    # Create executor that tries to transition to unsafe state
    class UnsafeTransitionExecutor(MockRobotExecutor):
        def execute_step(self, step_id, action_type, parameters, robot_id, current_state):
            # Try to transition to unsafe state
            unsafe_state = RobotState(
                robot_id=robot_id,
                timestamp=datetime.now(),
                position=current_state.position,
                orientation=current_state.orientation,
                joint_states=current_state.joint_states.copy(),
                sensor_readings=current_state.sensor_readings.copy(),
                actuator_states=current_state.actuator_states.copy(),
                battery_level=0.1,  # Unsafe battery level
                error_flags=current_state.error_flags.copy(),
                metadata=current_state.metadata.copy()
            )
            return unsafe_state, StepStatus.COMPLETED
    
    custom_executor = UnsafeTransitionExecutor()
    
    trace = executeTaskPipeline(
        task_id="safety-task-001",
        robot_id=robot_id,
        params={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        state_observer=state_observer,
        trace_storage=trace_storage,
        robot_executor=custom_executor
    )
    
    # Verify unsafe transition was prevented (execution aborted)
    assert trace.status == ExecutionStatus.ABORTED
    
    # Verify safety violation was detected and recorded
    safety_violations = [a for a in trace.anomalies if a.anomaly_type == "SAFETY_VIOLATION"]
    assert len(safety_violations) > 0


def test_execute_task_pipeline_handles_safe_state_command_failure(
    robot_id, task_spec_engine, execution_tracker, state_observer,
    trace_storage, task_with_safety_constraints, safe_robot_state
):
    """Test that pipeline handles failures when commanding robot to safe state."""
    task_spec_engine.defineTask(task_with_safety_constraints)
    state_observer._record_state(safe_robot_state)
    
    # Create executor that violates safety and fails to enter safe state
    class FailSafeStateExecutor(MockRobotExecutor):
        def execute_step(self, step_id, action_type, parameters, robot_id, current_state):
            unsafe_state = RobotState(
                robot_id=robot_id,
                timestamp=datetime.now(),
                position=current_state.position,
                orientation=current_state.orientation,
                joint_states=current_state.joint_states.copy(),
                sensor_readings=current_state.sensor_readings.copy(),
                actuator_states=current_state.actuator_states.copy(),
                battery_level=0.05,
                error_flags=current_state.error_flags.copy(),
                metadata=current_state.metadata.copy()
            )
            return unsafe_state, StepStatus.COMPLETED
        
        def enter_safe_state(self, robot_id, current_state):
            # Simulate failure to enter safe state
            raise Exception("Failed to command robot to safe state")
    
    custom_executor = FailSafeStateExecutor()
    
    trace = executeTaskPipeline(
        task_id="safety-task-001",
        robot_id=robot_id,
        params={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        state_observer=state_observer,
        trace_storage=trace_storage,
        robot_executor=custom_executor
    )
    
    # Verify execution was still aborted despite safe state failure
    assert trace.status == ExecutionStatus.ABORTED
    
    # Verify safety violation was recorded with error information
    safety_violations = [a for a in trace.anomalies if a.anomaly_type == "SAFETY_VIOLATION"]
    assert len(safety_violations) > 0
    
    violation = safety_violations[0]
    # Should have recorded the safe state error
    assert 'safe_state_error' in violation.context


def test_execute_task_pipeline_validates_safety_at_every_transition(
    robot_id, task_spec_engine, execution_tracker, state_observer,
    trace_storage, safe_robot_state
):
    """Test that pipeline validates safety at every state transition."""
    # Create task with multiple steps
    multi_step_task = TaskSpecification(
        task_id="multi-step-safety-task",
        name="Multi-Step Safety Task",
        description="Task with multiple steps and safety checks",
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
                max_retries=0
            ),
            TaskStep(
                step_id="step-2",
                action=ActionType.GRASP,
                parameters={},
                expected_duration=1.0,
                success_criteria=[],
                failure_handling=FailureStrategy.RETRY,
                max_retries=0
            ),
            TaskStep(
                step_id="step-3",
                action=ActionType.MOVE,
                parameters={},
                expected_duration=1.0,
                success_criteria=[],
                failure_handling=FailureStrategy.RETRY,
                max_retries=0
            )
        ],
        timeout_seconds=30,
        required_capabilities={"move", "grasp"},
        safety_constraints=[
            Condition(
                type=ConditionType.STATE_GREATER_THAN,
                expression="battery_level > 0.2",
                tolerance=0.01
            )
        ]
    )
    
    task_spec_engine.defineTask(multi_step_task)
    state_observer._record_state(safe_robot_state)
    
    # Create executor that violates safety on third step
    class ViolateOnThirdStepExecutor(MockRobotExecutor):
        def __init__(self):
            super().__init__()
            self.step_count = 0
        
        def execute_step(self, step_id, action_type, parameters, robot_id, current_state):
            self.step_count += 1
            battery = 0.05 if self.step_count >= 3 else 0.5
            new_state = RobotState(
                robot_id=robot_id,
                timestamp=datetime.now(),
                position=current_state.position,
                orientation=current_state.orientation,
                joint_states=current_state.joint_states.copy(),
                sensor_readings=current_state.sensor_readings.copy(),
                actuator_states=current_state.actuator_states.copy(),
                battery_level=battery,
                error_flags=current_state.error_flags.copy(),
                metadata=current_state.metadata.copy()
            )
            return new_state, StepStatus.COMPLETED
    
    custom_executor = ViolateOnThirdStepExecutor()
    
    trace = executeTaskPipeline(
        task_id="multi-step-safety-task",
        robot_id=robot_id,
        params={},
        task_spec_engine=task_spec_engine,
        execution_tracker=execution_tracker,
        state_observer=state_observer,
        trace_storage=trace_storage,
        robot_executor=custom_executor
    )
    
    # Verify execution was aborted before completing all steps
    assert trace.status == ExecutionStatus.ABORTED
    
    # Verify steps 1 and 2 completed, but step 3 triggered violation
    assert len(trace.steps) >= 2
    
    # Verify safety violation was detected
    safety_violations = [a for a in trace.anomalies if a.anomaly_type == "SAFETY_VIOLATION"]
    assert len(safety_violations) > 0
