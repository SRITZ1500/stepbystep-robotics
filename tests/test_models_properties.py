"""
Property-based tests for core data models using Hypothesis.

These tests validate universal properties that should hold for all valid inputs.
"""

import pytest
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from hypothesis import given, strategies as st, assume

from src.stepbystep_robotics.models import (
    Vector3D, Quaternion, JointState, RobotState,
    Condition, TaskStep, TaskSpecification,
    ExecutionStepRecord, ExecutionTrace, PerformanceMetrics, StepMetrics,
    ExecutionStatus, StepStatus, FailureStrategy, ConditionType, ActionType
)


# Custom strategies for generating test data

@st.composite
def vector3d_strategy(draw):
    """Generate valid Vector3D instances."""
    return Vector3D(
        x=draw(st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False)),
        y=draw(st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False)),
        z=draw(st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False))
    )


@st.composite
def quaternion_strategy(draw):
    """Generate valid Quaternion instances (non-zero magnitude)."""
    # Generate at least one non-zero component
    w = draw(st.floats(min_value=-1, max_value=1, allow_nan=False, allow_infinity=False))
    x = draw(st.floats(min_value=-1, max_value=1, allow_nan=False, allow_infinity=False))
    y = draw(st.floats(min_value=-1, max_value=1, allow_nan=False, allow_infinity=False))
    z = draw(st.floats(min_value=-1, max_value=1, allow_nan=False, allow_infinity=False))
    
    # Ensure non-zero magnitude
    assume(w**2 + x**2 + y**2 + z**2 > 0.0001)
    
    return Quaternion(w=w, x=x, y=y, z=z)


@st.composite
def joint_state_strategy(draw):
    """Generate valid JointState instances."""
    return JointState(
        joint_id=draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))),
        angle=draw(st.floats(min_value=-6.28, max_value=6.28, allow_nan=False, allow_infinity=False)),
        velocity=draw(st.floats(min_value=-10, max_value=10, allow_nan=False, allow_infinity=False)),
        torque=draw(st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False)),
        temperature=draw(st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False))
    )


@st.composite
def robot_state_strategy(draw):
    """Generate valid RobotState instances."""
    robot_id = uuid4()
    timestamp = datetime.now()
    
    return RobotState(
        robot_id=robot_id,
        timestamp=timestamp,
        position=draw(vector3d_strategy()),
        orientation=draw(quaternion_strategy()),
        joint_states={},
        sensor_readings={},
        actuator_states={},
        battery_level=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)),
        error_flags=set()
    )


@st.composite
def condition_strategy(draw):
    """Generate valid Condition instances."""
    return Condition(
        type=draw(st.sampled_from(ConditionType)),
        expression=draw(st.text(min_size=1, max_size=100)),
        tolerance=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    )


@st.composite
def task_step_strategy(draw):
    """Generate valid TaskStep instances."""
    return TaskStep(
        step_id=draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))),
        action=draw(st.sampled_from(ActionType)),
        parameters={},
        expected_duration=draw(st.floats(min_value=0.1, max_value=1000, allow_nan=False, allow_infinity=False)),
        success_criteria=[],
        failure_handling=draw(st.sampled_from(FailureStrategy)),
        max_retries=draw(st.integers(min_value=0, max_value=10))
    )


# Property-based tests

class TestVector3DProperties:
    """Property-based tests for Vector3D."""
    
    @given(vector3d_strategy())
    def test_vector_components_preserved(self, vector):
        """Property: Vector components are preserved after construction."""
        assert isinstance(vector.x, (int, float))
        assert isinstance(vector.y, (int, float))
        assert isinstance(vector.z, (int, float))


class TestQuaternionProperties:
    """Property-based tests for Quaternion."""
    
    @given(quaternion_strategy())
    def test_quaternion_components_preserved(self, quat):
        """Property: Quaternion components are preserved after construction."""
        assert isinstance(quat.w, (int, float))
        assert isinstance(quat.x, (int, float))
        assert isinstance(quat.y, (int, float))
        assert isinstance(quat.z, (int, float))
    
    @given(quaternion_strategy())
    def test_quaternion_has_nonzero_magnitude(self, quat):
        """Property: Valid quaternions have non-zero magnitude."""
        magnitude = (quat.w**2 + quat.x**2 + quat.y**2 + quat.z**2) ** 0.5
        assert magnitude > 0


class TestRobotStateProperties:
    """Property-based tests for RobotState."""
    
    @given(robot_state_strategy())
    def test_battery_level_in_valid_range(self, state):
        """Property: Battery level is always between 0.0 and 1.0."""
        assert 0.0 <= state.battery_level <= 1.0
    
    @given(robot_state_strategy())
    def test_robot_id_is_uuid(self, state):
        """Property: Robot ID is always a valid UUID."""
        assert isinstance(state.robot_id, UUID)
    
    @given(robot_state_strategy())
    def test_timestamp_is_datetime(self, state):
        """Property: Timestamp is always a datetime object."""
        assert isinstance(state.timestamp, datetime)


class TestConditionProperties:
    """Property-based tests for Condition."""
    
    @given(condition_strategy())
    def test_tolerance_is_non_negative(self, condition):
        """Property: Tolerance is always non-negative."""
        assert condition.tolerance >= 0.0
    
    @given(condition_strategy())
    def test_expression_is_non_empty(self, condition):
        """Property: Expression is never empty."""
        assert len(condition.expression) > 0


class TestTaskStepProperties:
    """Property-based tests for TaskStep."""
    
    @given(task_step_strategy())
    def test_expected_duration_is_positive(self, step):
        """Property: Expected duration is always positive."""
        assert step.expected_duration > 0
    
    @given(task_step_strategy())
    def test_max_retries_is_non_negative(self, step):
        """Property: Max retries is always non-negative."""
        assert step.max_retries >= 0
    
    @given(task_step_strategy())
    def test_step_id_is_non_empty(self, step):
        """Property: Step ID is never empty."""
        assert len(step.step_id) > 0


class TestTaskSpecificationProperties:
    """Property-based tests for TaskSpecification."""
    
    @given(
        task_id=st.text(min_size=1, max_size=20),
        name=st.text(min_size=1, max_size=50),
        steps=st.lists(task_step_strategy(), min_size=1, max_size=10),
        timeout=st.integers(min_value=1, max_value=3600)
    )
    def test_task_spec_with_unique_step_ids(self, task_id, name, steps, timeout):
        """Property: Task specification with unique step IDs is valid."""
        # Make step IDs unique
        for i, step in enumerate(steps):
            step.step_id = f"step_{i}"
        
        spec = TaskSpecification(
            task_id=task_id,
            name=name,
            description="Test description",
            preconditions=[],
            postconditions=[],
            steps=steps,
            timeout_seconds=timeout,
            required_capabilities=set(),
            safety_constraints=[]
        )
        
        assert spec.timeout_seconds > 0
        assert len(spec.steps) > 0
        
        # Verify all step IDs are unique
        step_ids = [s.step_id for s in spec.steps]
        assert len(step_ids) == len(set(step_ids))


class TestPerformanceMetricsProperties:
    """Property-based tests for PerformanceMetrics."""
    
    @given(
        execution_id=st.text(min_size=1, max_size=20),
        total_duration=st.floats(min_value=0.0, max_value=10000, allow_nan=False, allow_infinity=False),
        success_rate=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        energy=st.floats(min_value=0.0, max_value=10000, allow_nan=False, allow_infinity=False),
        accuracy=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        smoothness=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        safety=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
    def test_all_scores_in_valid_range(self, execution_id, total_duration, success_rate, 
                                       energy, accuracy, smoothness, safety):
        """Property: All score metrics are between 0.0 and 1.0."""
        metrics = PerformanceMetrics(
            execution_id=execution_id,
            total_duration=total_duration,
            success_rate=success_rate,
            energy_consumed=energy,
            accuracy_score=accuracy,
            smoothness_score=smoothness,
            safety_score=safety,
            step_metrics={}
        )
        
        assert 0.0 <= metrics.success_rate <= 1.0
        assert 0.0 <= metrics.accuracy_score <= 1.0
        assert 0.0 <= metrics.smoothness_score <= 1.0
        assert 0.0 <= metrics.safety_score <= 1.0
    
    @given(
        execution_id=st.text(min_size=1, max_size=20),
        total_duration=st.floats(min_value=0.0, max_value=10000, allow_nan=False, allow_infinity=False),
        success_rate=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        energy=st.floats(min_value=0.0, max_value=10000, allow_nan=False, allow_infinity=False),
        accuracy=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        smoothness=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        safety=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
    def test_energy_is_non_negative(self, execution_id, total_duration, success_rate,
                                    energy, accuracy, smoothness, safety):
        """Property: Energy consumed is always non-negative."""
        metrics = PerformanceMetrics(
            execution_id=execution_id,
            total_duration=total_duration,
            success_rate=success_rate,
            energy_consumed=energy,
            accuracy_score=accuracy,
            smoothness_score=smoothness,
            safety_score=safety,
            step_metrics={}
        )
        
        assert metrics.energy_consumed >= 0.0


class TestExecutionTraceProperties:
    """Property-based tests for ExecutionTrace."""
    
    @given(robot_state_strategy())
    def test_trace_with_single_state_is_valid(self, state):
        """Property: Execution trace with at least one state is valid."""
        trace = ExecutionTrace(
            execution_id="exec_1",
            task_id="task_1",
            robot_id=state.robot_id,
            start_time=state.timestamp,
            end_time=None,
            status=ExecutionStatus.IN_PROGRESS,
            steps=[],
            state_history=[state],
            anomalies=[]
        )
        
        assert len(trace.state_history) >= 1
        assert trace.robot_id == state.robot_id
    
    @given(
        robot_state_strategy(),
        st.lists(st.sampled_from(ExecutionStatus), min_size=1, max_size=1)
    )
    def test_trace_status_is_valid_enum(self, state, status_list):
        """Property: Execution status is always a valid ExecutionStatus enum."""
        trace = ExecutionTrace(
            execution_id="exec_1",
            task_id="task_1",
            robot_id=state.robot_id,
            start_time=state.timestamp,
            end_time=None,
            status=status_list[0],
            steps=[],
            state_history=[state],
            anomalies=[]
        )
        
        assert isinstance(trace.status, ExecutionStatus)
