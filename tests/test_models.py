"""
Unit tests for core data models.

Tests validate:
- Data model construction and validation rules
- Field type checking
- Boundary conditions
- Error handling for invalid inputs
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.stepbystep_robotics.models import (
    Vector3D, Quaternion, JointState, RobotState,
    Condition, TaskStep, TaskSpecification,
    ExecutionStepRecord, ExecutionTrace, PerformanceMetrics, StepMetrics,
    Anomaly, Deviation,
    ExecutionStatus, StepStatus, FailureStrategy, ConditionType, ActionType
)


class TestVector3D:
    """Tests for Vector3D data model."""
    
    def test_valid_vector(self):
        """Test creating a valid 3D vector."""
        v = Vector3D(x=1.0, y=2.0, z=3.0)
        assert v.x == 1.0
        assert v.y == 2.0
        assert v.z == 3.0
    
    def test_integer_components(self):
        """Test vector with integer components."""
        v = Vector3D(x=1, y=2, z=3)
        assert v.x == 1
        assert v.y == 2
        assert v.z == 3
    
    def test_invalid_components(self):
        """Test vector with non-numeric components."""
        with pytest.raises(ValueError, match="Vector components must be numeric"):
            Vector3D(x="1", y=2.0, z=3.0)


class TestQuaternion:
    """Tests for Quaternion data model."""
    
    def test_valid_quaternion(self):
        """Test creating a valid quaternion."""
        q = Quaternion(w=1.0, x=0.0, y=0.0, z=0.0)
        assert q.w == 1.0
        assert q.x == 0.0
        assert q.y == 0.0
        assert q.z == 0.0
    
    def test_invalid_components(self):
        """Test quaternion with non-numeric components."""
        with pytest.raises(ValueError, match="Quaternion components must be numeric"):
            Quaternion(w=1.0, x="0", y=0.0, z=0.0)
    
    def test_zero_magnitude(self):
        """Test quaternion with zero magnitude."""
        with pytest.raises(ValueError, match="Quaternion magnitude cannot be zero"):
            Quaternion(w=0.0, x=0.0, y=0.0, z=0.0)


class TestJointState:
    """Tests for JointState data model."""
    
    def test_valid_joint_state(self):
        """Test creating a valid joint state."""
        js = JointState(
            joint_id="joint_1",
            angle=1.57,
            velocity=0.5,
            torque=10.0,
            temperature=45.0
        )
        assert js.joint_id == "joint_1"
        assert js.angle == 1.57
        assert js.velocity == 0.5
        assert js.torque == 10.0
        assert js.temperature == 45.0
    
    def test_empty_joint_id(self):
        """Test joint state with empty ID."""
        with pytest.raises(ValueError, match="joint_id cannot be empty"):
            JointState(joint_id="", angle=0.0, velocity=0.0, torque=0.0, temperature=0.0)
    
    def test_invalid_numeric_values(self):
        """Test joint state with non-numeric values."""
        with pytest.raises(ValueError, match="Joint state values must be numeric"):
            JointState(joint_id="joint_1", angle="1.57", velocity=0.5, torque=10.0, temperature=45.0)


class TestRobotState:
    """Tests for RobotState data model."""
    
    def test_valid_robot_state(self):
        """Test creating a valid robot state."""
        robot_id = uuid4()
        timestamp = datetime.now()
        position = Vector3D(x=1.0, y=2.0, z=3.0)
        orientation = Quaternion(w=1.0, x=0.0, y=0.0, z=0.0)
        
        state = RobotState(
            robot_id=robot_id,
            timestamp=timestamp,
            position=position,
            orientation=orientation,
            joint_states={},
            sensor_readings={},
            actuator_states={},
            battery_level=0.8,
            error_flags=set()
        )
        
        assert state.robot_id == robot_id
        assert state.timestamp == timestamp
        assert state.battery_level == 0.8
    
    def test_invalid_robot_id(self):
        """Test robot state with invalid robot ID."""
        with pytest.raises(ValueError, match="robot_id must be a valid UUID"):
            RobotState(
                robot_id="not-a-uuid",
                timestamp=datetime.now(),
                position=Vector3D(1.0, 2.0, 3.0),
                orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
                joint_states={},
                sensor_readings={},
                actuator_states={},
                battery_level=0.8,
                error_flags=set()
            )
    
    def test_battery_level_out_of_range(self):
        """Test robot state with battery level out of valid range."""
        with pytest.raises(ValueError, match="battery_level must be between 0.0 and 1.0"):
            RobotState(
                robot_id=uuid4(),
                timestamp=datetime.now(),
                position=Vector3D(1.0, 2.0, 3.0),
                orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
                joint_states={},
                sensor_readings={},
                actuator_states={},
                battery_level=1.5,
                error_flags=set()
            )
    
    def test_negative_battery_level(self):
        """Test robot state with negative battery level."""
        with pytest.raises(ValueError, match="battery_level must be between 0.0 and 1.0"):
            RobotState(
                robot_id=uuid4(),
                timestamp=datetime.now(),
                position=Vector3D(1.0, 2.0, 3.0),
                orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
                joint_states={},
                sensor_readings={},
                actuator_states={},
                battery_level=-0.1,
                error_flags=set()
            )


class TestCondition:
    """Tests for Condition data model."""
    
    def test_valid_condition(self):
        """Test creating a valid condition."""
        cond = Condition(
            type=ConditionType.STATE_EQUALS,
            expression="battery_level > 0.2",
            tolerance=0.01
        )
        assert cond.type == ConditionType.STATE_EQUALS
        assert cond.expression == "battery_level > 0.2"
        assert cond.tolerance == 0.01
    
    def test_empty_expression(self):
        """Test condition with empty expression."""
        with pytest.raises(ValueError, match="expression cannot be empty"):
            Condition(type=ConditionType.STATE_EQUALS, expression="", tolerance=0.0)
    
    def test_negative_tolerance(self):
        """Test condition with negative tolerance."""
        with pytest.raises(ValueError, match="tolerance must be non-negative"):
            Condition(
                type=ConditionType.STATE_EQUALS,
                expression="battery_level > 0.2",
                tolerance=-0.1
            )


class TestTaskStep:
    """Tests for TaskStep data model."""
    
    def test_valid_task_step(self):
        """Test creating a valid task step."""
        step = TaskStep(
            step_id="step_1",
            action=ActionType.MOVE,
            parameters={"target": [1.0, 2.0, 3.0]},
            expected_duration=5.0,
            success_criteria=[],
            failure_handling=FailureStrategy.RETRY,
            max_retries=3
        )
        assert step.step_id == "step_1"
        assert step.action == ActionType.MOVE
        assert step.max_retries == 3
    
    def test_empty_step_id(self):
        """Test task step with empty ID."""
        with pytest.raises(ValueError, match="step_id cannot be empty"):
            TaskStep(
                step_id="",
                action=ActionType.MOVE,
                parameters={},
                expected_duration=5.0,
                success_criteria=[],
                failure_handling=FailureStrategy.RETRY
            )
    
    def test_negative_duration(self):
        """Test task step with negative expected duration."""
        with pytest.raises(ValueError, match="expected_duration must be positive"):
            TaskStep(
                step_id="step_1",
                action=ActionType.MOVE,
                parameters={},
                expected_duration=-5.0,
                success_criteria=[],
                failure_handling=FailureStrategy.RETRY
            )
    
    def test_negative_max_retries(self):
        """Test task step with negative max retries."""
        with pytest.raises(ValueError, match="max_retries must be a non-negative integer"):
            TaskStep(
                step_id="step_1",
                action=ActionType.MOVE,
                parameters={},
                expected_duration=5.0,
                success_criteria=[],
                failure_handling=FailureStrategy.RETRY,
                max_retries=-1
            )


class TestTaskSpecification:
    """Tests for TaskSpecification data model."""
    
    def test_valid_task_specification(self):
        """Test creating a valid task specification."""
        step = TaskStep(
            step_id="step_1",
            action=ActionType.MOVE,
            parameters={},
            expected_duration=5.0,
            success_criteria=[],
            failure_handling=FailureStrategy.RETRY
        )
        
        spec = TaskSpecification(
            task_id="task_1",
            name="Test Task",
            description="A test task",
            preconditions=[],
            postconditions=[],
            steps=[step],
            timeout_seconds=60,
            required_capabilities=set(),
            safety_constraints=[]
        )
        
        assert spec.task_id == "task_1"
        assert spec.name == "Test Task"
        assert len(spec.steps) == 1
    
    def test_empty_task_id(self):
        """Test task specification with empty ID."""
        with pytest.raises(ValueError, match="task_id cannot be empty"):
            TaskSpecification(
                task_id="",
                name="Test Task",
                description="A test task",
                preconditions=[],
                postconditions=[],
                steps=[TaskStep(
                    step_id="step_1",
                    action=ActionType.MOVE,
                    parameters={},
                    expected_duration=5.0,
                    success_criteria=[],
                    failure_handling=FailureStrategy.RETRY
                )],
                timeout_seconds=60,
                required_capabilities=set(),
                safety_constraints=[]
            )
    
    def test_empty_steps(self):
        """Test task specification with no steps."""
        with pytest.raises(ValueError, match="steps cannot be empty"):
            TaskSpecification(
                task_id="task_1",
                name="Test Task",
                description="A test task",
                preconditions=[],
                postconditions=[],
                steps=[],
                timeout_seconds=60,
                required_capabilities=set(),
                safety_constraints=[]
            )
    
    def test_negative_timeout(self):
        """Test task specification with negative timeout."""
        with pytest.raises(ValueError, match="timeout_seconds must be positive"):
            TaskSpecification(
                task_id="task_1",
                name="Test Task",
                description="A test task",
                preconditions=[],
                postconditions=[],
                steps=[TaskStep(
                    step_id="step_1",
                    action=ActionType.MOVE,
                    parameters={},
                    expected_duration=5.0,
                    success_criteria=[],
                    failure_handling=FailureStrategy.RETRY
                )],
                timeout_seconds=-60,
                required_capabilities=set(),
                safety_constraints=[]
            )
    
    def test_duplicate_step_ids(self):
        """Test task specification with duplicate step IDs."""
        steps = [
            TaskStep(
                step_id="step_1",
                action=ActionType.MOVE,
                parameters={},
                expected_duration=5.0,
                success_criteria=[],
                failure_handling=FailureStrategy.RETRY
            ),
            TaskStep(
                step_id="step_1",  # Duplicate
                action=ActionType.GRASP,
                parameters={},
                expected_duration=3.0,
                success_criteria=[],
                failure_handling=FailureStrategy.RETRY
            )
        ]
        
        with pytest.raises(ValueError, match="step_ids must be unique within task"):
            TaskSpecification(
                task_id="task_1",
                name="Test Task",
                description="A test task",
                preconditions=[],
                postconditions=[],
                steps=steps,
                timeout_seconds=60,
                required_capabilities=set(),
                safety_constraints=[]
            )


class TestExecutionStepRecord:
    """Tests for ExecutionStepRecord data model."""
    
    def test_valid_execution_step_record(self):
        """Test creating a valid execution step record."""
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=5)
        
        robot_id = uuid4()
        input_state = RobotState(
            robot_id=robot_id,
            timestamp=start_time,
            position=Vector3D(0.0, 0.0, 0.0),
            orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
            joint_states={},
            sensor_readings={},
            actuator_states={},
            battery_level=0.8,
            error_flags=set()
        )
        output_state = RobotState(
            robot_id=robot_id,
            timestamp=end_time,
            position=Vector3D(1.0, 0.0, 0.0),
            orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
            joint_states={},
            sensor_readings={},
            actuator_states={},
            battery_level=0.75,
            error_flags=set()
        )
        
        record = ExecutionStepRecord(
            step_id="step_1",
            start_time=start_time,
            end_time=end_time,
            status=StepStatus.COMPLETED,
            input_state=input_state,
            output_state=output_state,
            actual_duration=5.0
        )
        
        assert record.step_id == "step_1"
        assert record.status == StepStatus.COMPLETED
        assert record.actual_duration == 5.0
    
    def test_end_time_before_start_time(self):
        """Test execution step record with end_time before start_time."""
        start_time = datetime.now()
        end_time = start_time - timedelta(seconds=5)
        
        robot_id = uuid4()
        state = RobotState(
            robot_id=robot_id,
            timestamp=start_time,
            position=Vector3D(0.0, 0.0, 0.0),
            orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
            joint_states={},
            sensor_readings={},
            actuator_states={},
            battery_level=0.8,
            error_flags=set()
        )
        
        with pytest.raises(ValueError, match="end_time must be >= start_time"):
            ExecutionStepRecord(
                step_id="step_1",
                start_time=start_time,
                end_time=end_time,
                status=StepStatus.COMPLETED,
                input_state=state,
                output_state=state,
                actual_duration=5.0
            )


class TestPerformanceMetrics:
    """Tests for PerformanceMetrics data model."""
    
    def test_valid_performance_metrics(self):
        """Test creating valid performance metrics."""
        metrics = PerformanceMetrics(
            execution_id="exec_1",
            total_duration=10.0,
            success_rate=1.0,
            energy_consumed=50.0,
            accuracy_score=0.95,
            smoothness_score=0.9,
            safety_score=1.0,
            step_metrics={}
        )
        
        assert metrics.execution_id == "exec_1"
        assert metrics.success_rate == 1.0
        assert metrics.accuracy_score == 0.95
    
    def test_score_out_of_range(self):
        """Test performance metrics with score out of valid range."""
        with pytest.raises(ValueError, match="accuracy_score must be between 0.0 and 1.0"):
            PerformanceMetrics(
                execution_id="exec_1",
                total_duration=10.0,
                success_rate=1.0,
                energy_consumed=50.0,
                accuracy_score=1.5,  # Out of range
                smoothness_score=0.9,
                safety_score=1.0,
                step_metrics={}
            )
    
    def test_negative_energy(self):
        """Test performance metrics with negative energy consumed."""
        with pytest.raises(ValueError, match="energy_consumed must be non-negative"):
            PerformanceMetrics(
                execution_id="exec_1",
                total_duration=10.0,
                success_rate=1.0,
                energy_consumed=-50.0,  # Negative
                accuracy_score=0.95,
                smoothness_score=0.9,
                safety_score=1.0,
                step_metrics={}
            )


class TestExecutionTrace:
    """Tests for ExecutionTrace data model."""
    
    def test_valid_execution_trace(self):
        """Test creating a valid execution trace."""
        robot_id = uuid4()
        start_time = datetime.now()
        
        state = RobotState(
            robot_id=robot_id,
            timestamp=start_time,
            position=Vector3D(0.0, 0.0, 0.0),
            orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
            joint_states={},
            sensor_readings={},
            actuator_states={},
            battery_level=0.8,
            error_flags=set()
        )
        
        trace = ExecutionTrace(
            execution_id="exec_1",
            task_id="task_1",
            robot_id=robot_id,
            start_time=start_time,
            end_time=None,
            status=ExecutionStatus.IN_PROGRESS,
            steps=[],
            state_history=[state],
            anomalies=[]
        )
        
        assert trace.execution_id == "exec_1"
        assert trace.status == ExecutionStatus.IN_PROGRESS
        assert len(trace.state_history) == 1
    
    def test_empty_state_history(self):
        """Test execution trace with empty state history."""
        with pytest.raises(ValueError, match="state_history must contain at least one state"):
            ExecutionTrace(
                execution_id="exec_1",
                task_id="task_1",
                robot_id=uuid4(),
                start_time=datetime.now(),
                end_time=None,
                status=ExecutionStatus.IN_PROGRESS,
                steps=[],
                state_history=[],  # Empty
                anomalies=[]
            )
    
    def test_end_time_before_start_time(self):
        """Test execution trace with end_time before start_time."""
        robot_id = uuid4()
        start_time = datetime.now()
        end_time = start_time - timedelta(seconds=10)
        
        state = RobotState(
            robot_id=robot_id,
            timestamp=start_time,
            position=Vector3D(0.0, 0.0, 0.0),
            orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
            joint_states={},
            sensor_readings={},
            actuator_states={},
            battery_level=0.8,
            error_flags=set()
        )
        
        with pytest.raises(ValueError, match="end_time must be >= start_time"):
            ExecutionTrace(
                execution_id="exec_1",
                task_id="task_1",
                robot_id=robot_id,
                start_time=start_time,
                end_time=end_time,
                status=ExecutionStatus.COMPLETED,
                steps=[],
                state_history=[state],
                anomalies=[]
            )
    
    def test_steps_not_chronological(self):
        """Test execution trace with steps not in chronological order."""
        robot_id = uuid4()
        start_time = datetime.now()
        
        state = RobotState(
            robot_id=robot_id,
            timestamp=start_time,
            position=Vector3D(0.0, 0.0, 0.0),
            orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
            joint_states={},
            sensor_readings={},
            actuator_states={},
            battery_level=0.8,
            error_flags=set()
        )
        
        # Create steps with wrong chronological order
        step1 = ExecutionStepRecord(
            step_id="step_1",
            start_time=start_time + timedelta(seconds=10),
            end_time=start_time + timedelta(seconds=15),
            status=StepStatus.COMPLETED,
            input_state=state,
            output_state=state,
            actual_duration=5.0
        )
        
        step2 = ExecutionStepRecord(
            step_id="step_2",
            start_time=start_time,  # Earlier than step1's end
            end_time=start_time + timedelta(seconds=5),
            status=StepStatus.COMPLETED,
            input_state=state,
            output_state=state,
            actual_duration=5.0
        )
        
        with pytest.raises(ValueError, match="steps must be ordered chronologically"):
            ExecutionTrace(
                execution_id="exec_1",
                task_id="task_1",
                robot_id=robot_id,
                start_time=start_time,
                end_time=None,
                status=ExecutionStatus.IN_PROGRESS,
                steps=[step1, step2],  # Wrong order
                state_history=[state],
                anomalies=[]
            )
