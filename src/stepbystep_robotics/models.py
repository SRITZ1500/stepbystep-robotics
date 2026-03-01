"""
Core data models for StepbyStep:ROBOTICS system.

This module defines the fundamental data structures used across all layers:
- RobotState: Normalized representation of robot state
- TaskSpecification: Formal task definition with constraints
- ExecutionTrace: Complete record of task execution
- PerformanceMetrics: Performance analysis results
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Any
from uuid import UUID


# Enumerations

class ExecutionStatus(Enum):
    """Status of task execution."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"
    TIMEOUT = "TIMEOUT"


class StepStatus(Enum):
    """Status of individual execution step."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    INTERRUPTED = "INTERRUPTED"


class FailureStrategy(Enum):
    """Strategy for handling step failures."""
    RETRY = "RETRY"
    SKIP = "SKIP"
    ABORT = "ABORT"
    FALLBACK = "FALLBACK"


class ConditionType(Enum):
    """Type of condition in task specification."""
    STATE_EQUALS = "STATE_EQUALS"
    STATE_GREATER_THAN = "STATE_GREATER_THAN"
    STATE_LESS_THAN = "STATE_LESS_THAN"
    STATE_IN_RANGE = "STATE_IN_RANGE"
    CAPABILITY_AVAILABLE = "CAPABILITY_AVAILABLE"


class ActionType(Enum):
    """Type of robot action."""
    MOVE = "MOVE"
    GRASP = "GRASP"
    RELEASE = "RELEASE"
    ROTATE = "ROTATE"
    WAIT = "WAIT"
    SENSE = "SENSE"
    CUSTOM = "CUSTOM"


# Core Data Models

@dataclass
class Vector3D:
    """3D vector for position and orientation."""
    x: float
    y: float
    z: float
    
    def __post_init__(self):
        """Validate vector components."""
        if not all(isinstance(v, (int, float)) for v in [self.x, self.y, self.z]):
            raise ValueError("Vector components must be numeric")


@dataclass
class Quaternion:
    """Quaternion for 3D orientation."""
    w: float
    x: float
    y: float
    z: float
    
    def __post_init__(self):
        """Validate quaternion components."""
        if not all(isinstance(v, (int, float)) for v in [self.w, self.x, self.y, self.z]):
            raise ValueError("Quaternion components must be numeric")
        # Normalize quaternion
        magnitude = (self.w**2 + self.x**2 + self.y**2 + self.z**2) ** 0.5
        if magnitude == 0:
            raise ValueError("Quaternion magnitude cannot be zero")


@dataclass
class JointState:
    """State of a single robot joint."""
    joint_id: str
    angle: float
    velocity: float
    torque: float
    temperature: float
    
    def __post_init__(self):
        """Validate joint state."""
        if not self.joint_id:
            raise ValueError("joint_id cannot be empty")
        if not all(isinstance(v, (int, float)) for v in [self.angle, self.velocity, self.torque, self.temperature]):
            raise ValueError("Joint state values must be numeric")


@dataclass
class RobotState:
    """
    Normalized representation of robot state at a point in time.
    
    Validation Rules:
    - robotId must be valid UUID
    - timestamp must be monotonically increasing for same robot
    - position and orientation must be within physical workspace bounds
    - batteryLevel must be between 0.0 and 1.0
    - All sensor readings must be within calibrated ranges
    """
    robot_id: UUID
    timestamp: datetime
    position: Vector3D
    orientation: Quaternion
    joint_states: Dict[str, JointState]
    sensor_readings: Dict[str, float]
    actuator_states: Dict[str, Any]
    battery_level: float
    error_flags: Set[str]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate robot state."""
        # Validate robot_id
        if not isinstance(self.robot_id, UUID):
            raise ValueError("robot_id must be a valid UUID")
        
        # Validate timestamp
        if not isinstance(self.timestamp, datetime):
            raise ValueError("timestamp must be a datetime object")
        
        # Validate battery level
        if not isinstance(self.battery_level, (int, float)):
            raise ValueError("battery_level must be numeric")
        if not 0.0 <= self.battery_level <= 1.0:
            raise ValueError("battery_level must be between 0.0 and 1.0")
        
        # Validate position and orientation
        if not isinstance(self.position, Vector3D):
            raise ValueError("position must be a Vector3D")
        if not isinstance(self.orientation, Quaternion):
            raise ValueError("orientation must be a Quaternion")
        
        # Validate collections
        if not isinstance(self.joint_states, dict):
            raise ValueError("joint_states must be a dictionary")
        if not isinstance(self.sensor_readings, dict):
            raise ValueError("sensor_readings must be a dictionary")
        if not isinstance(self.actuator_states, dict):
            raise ValueError("actuator_states must be a dictionary")
        if not isinstance(self.error_flags, set):
            raise ValueError("error_flags must be a set")


@dataclass
class Condition:
    """Condition for task preconditions and postconditions."""
    type: ConditionType
    expression: str
    tolerance: float = 0.0
    
    def __post_init__(self):
        """Validate condition."""
        if not isinstance(self.type, ConditionType):
            raise ValueError("type must be a ConditionType")
        if not self.expression:
            raise ValueError("expression cannot be empty")
        if not isinstance(self.tolerance, (int, float)):
            raise ValueError("tolerance must be numeric")
        if self.tolerance < 0:
            raise ValueError("tolerance must be non-negative")


@dataclass
class TaskStep:
    """Individual step in a task specification."""
    step_id: str
    action: ActionType
    parameters: Dict[str, Any]
    expected_duration: float
    success_criteria: List[Condition]
    failure_handling: FailureStrategy
    max_retries: int = 3
    fallback_steps: List['TaskStep'] = None

    def __post_init__(self):
        """Validate task step."""
        if not self.step_id:
            raise ValueError("step_id cannot be empty")
        if not isinstance(self.action, ActionType):
            raise ValueError("action must be an ActionType")
        if not isinstance(self.parameters, dict):
            raise ValueError("parameters must be a dictionary")
        if not isinstance(self.expected_duration, (int, float)):
            raise ValueError("expected_duration must be numeric")
        if self.expected_duration <= 0:
            raise ValueError("expected_duration must be positive")
        if not isinstance(self.success_criteria, list):
            raise ValueError("success_criteria must be a list")
        if not isinstance(self.failure_handling, FailureStrategy):
            raise ValueError("failure_handling must be a FailureStrategy")
        if not isinstance(self.max_retries, int) or self.max_retries < 0:
            raise ValueError("max_retries must be a non-negative integer")
        if self.fallback_steps is None:
            self.fallback_steps = []
        if not isinstance(self.fallback_steps, list):
            raise ValueError("fallback_steps must be a list")


@dataclass
class TaskSpecification:
    """
    Formal definition of a task with preconditions, postconditions, and execution steps.
    
    Validation Rules:
    - task_id must be unique within system
    - name must be non-empty and follow naming conventions
    - preconditions must be verifiable from RobotState
    - postconditions must be measurable and deterministic
    - steps must form valid execution sequence without circular dependencies
    - timeout_seconds must be positive
    - All referenced capabilities must exist in robot capability registry
    """
    task_id: str
    name: str
    description: str
    preconditions: List[Condition]
    postconditions: List[Condition]
    steps: List[TaskStep]
    timeout_seconds: int
    required_capabilities: Set[str]
    safety_constraints: List[Condition]
    
    def __post_init__(self):
        """Validate task specification."""
        if not self.task_id:
            raise ValueError("task_id cannot be empty")
        if not self.name:
            raise ValueError("name cannot be empty")
        if not isinstance(self.preconditions, list):
            raise ValueError("preconditions must be a list")
        if not isinstance(self.postconditions, list):
            raise ValueError("postconditions must be a list")
        if not isinstance(self.steps, list):
            raise ValueError("steps must be a list")
        if len(self.steps) == 0:
            raise ValueError("steps cannot be empty")
        if not isinstance(self.timeout_seconds, int):
            raise ValueError("timeout_seconds must be an integer")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if not isinstance(self.required_capabilities, set):
            raise ValueError("required_capabilities must be a set")
        if not isinstance(self.safety_constraints, list):
            raise ValueError("safety_constraints must be a list")
        
        # Validate step IDs are unique
        step_ids = [step.step_id for step in self.steps]
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("step_ids must be unique within task")


@dataclass
class Deviation:
    """Deviation from expected behavior during execution."""
    metric: str
    expected: float
    actual: float
    severity: str


@dataclass
class ExecutionStepRecord:
    """Record of a single step execution."""
    step_id: str
    start_time: datetime
    end_time: datetime
    status: StepStatus
    input_state: RobotState
    output_state: RobotState
    actual_duration: float
    deviations: List[Deviation] = field(default_factory=list)
    retry_count: int = 0
    
    def __post_init__(self):
        """Validate execution step record."""
        if not self.step_id:
            raise ValueError("step_id cannot be empty")
        if not isinstance(self.start_time, datetime):
            raise ValueError("start_time must be a datetime")
        if not isinstance(self.end_time, datetime):
            raise ValueError("end_time must be a datetime")
        if self.end_time < self.start_time:
            raise ValueError("end_time must be >= start_time")
        if not isinstance(self.status, StepStatus):
            raise ValueError("status must be a StepStatus")
        if not isinstance(self.input_state, RobotState):
            raise ValueError("input_state must be a RobotState")
        if not isinstance(self.output_state, RobotState):
            raise ValueError("output_state must be a RobotState")
        if not isinstance(self.actual_duration, (int, float)):
            raise ValueError("actual_duration must be numeric")
        if self.actual_duration < 0:
            raise ValueError("actual_duration must be non-negative")
        if not isinstance(self.retry_count, int) or self.retry_count < 0:
            raise ValueError("retry_count must be a non-negative integer")


@dataclass
class Anomaly:
    """Anomaly detected during execution."""
    anomaly_type: str
    severity: str
    description: str
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate anomaly."""
        if not self.anomaly_type:
            raise ValueError("anomaly_type cannot be empty")
        if not self.severity:
            raise ValueError("severity cannot be empty")
        if not self.description:
            raise ValueError("description cannot be empty")
        if not isinstance(self.timestamp, datetime):
            raise ValueError("timestamp must be a datetime")


@dataclass
class StepMetrics:
    """Performance metrics for a single step."""
    step_id: str
    duration: float
    retry_count: int
    error_rate: float
    resource_usage: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate step metrics."""
        if not self.step_id:
            raise ValueError("step_id cannot be empty")
        if not isinstance(self.duration, (int, float)):
            raise ValueError("duration must be numeric")
        if self.duration < 0:
            raise ValueError("duration must be non-negative")
        if not isinstance(self.retry_count, int) or self.retry_count < 0:
            raise ValueError("retry_count must be a non-negative integer")
        if not isinstance(self.error_rate, (int, float)):
            raise ValueError("error_rate must be numeric")
        if not 0.0 <= self.error_rate <= 1.0:
            raise ValueError("error_rate must be between 0.0 and 1.0")


@dataclass
class PerformanceMetrics:
    """
    Performance metrics computed from execution trace.
    
    Validation Rules:
    - All score values must be between 0.0 and 1.0
    - total_duration must equal sum of step durations plus gaps
    - success_rate must reflect actual completion status
    - energy_consumed must be non-negative
    - step_metrics must exist for all executed steps
    """
    execution_id: str
    total_duration: float
    success_rate: float
    energy_consumed: float
    accuracy_score: float
    smoothness_score: float
    safety_score: float
    step_metrics: Dict[str, StepMetrics]
    aggregate_stats: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate performance metrics."""
        if not self.execution_id:
            raise ValueError("execution_id cannot be empty")
        
        # Validate numeric values
        if not isinstance(self.total_duration, (int, float)):
            raise ValueError("total_duration must be numeric")
        if self.total_duration < 0:
            raise ValueError("total_duration must be non-negative")
        
        if not isinstance(self.energy_consumed, (int, float)):
            raise ValueError("energy_consumed must be numeric")
        if self.energy_consumed < 0:
            raise ValueError("energy_consumed must be non-negative")
        
        # Validate score ranges
        scores = [
            ("success_rate", self.success_rate),
            ("accuracy_score", self.accuracy_score),
            ("smoothness_score", self.smoothness_score),
            ("safety_score", self.safety_score)
        ]
        
        for name, score in scores:
            if not isinstance(score, (int, float)):
                raise ValueError(f"{name} must be numeric")
            if not 0.0 <= score <= 1.0:
                raise ValueError(f"{name} must be between 0.0 and 1.0")
        
        if not isinstance(self.step_metrics, dict):
            raise ValueError("step_metrics must be a dictionary")


@dataclass
class ExecutionTrace:
    """
    Complete record of task execution including all steps, state changes, and performance metrics.
    
    Validation Rules:
    - execution_id must be unique and immutable
    - end_time must be greater than or equal to start_time
    - steps must be ordered chronologically
    - state_history must contain at least initial and final states
    - Each step's end_time must match next step's start_time (or have valid gap)
    - status must transition according to valid state machine
    """
    execution_id: str
    task_id: str
    robot_id: UUID
    start_time: datetime
    end_time: Optional[datetime]
    status: ExecutionStatus
    steps: List[ExecutionStepRecord]
    state_history: List[RobotState]
    anomalies: List[Anomaly]
    performance_metrics: Optional[PerformanceMetrics] = None
    
    def __post_init__(self):
        """Validate execution trace."""
        if not self.execution_id:
            raise ValueError("execution_id cannot be empty")
        if not self.task_id:
            raise ValueError("task_id cannot be empty")
        if not isinstance(self.robot_id, UUID):
            raise ValueError("robot_id must be a valid UUID")
        if not isinstance(self.start_time, datetime):
            raise ValueError("start_time must be a datetime")
        if self.end_time is not None:
            if not isinstance(self.end_time, datetime):
                raise ValueError("end_time must be a datetime or None")
            if self.end_time < self.start_time:
                raise ValueError("end_time must be >= start_time")
        if not isinstance(self.status, ExecutionStatus):
            raise ValueError("status must be an ExecutionStatus")
        if not isinstance(self.steps, list):
            raise ValueError("steps must be a list")
        if not isinstance(self.state_history, list):
            raise ValueError("state_history must be a list")
        if len(self.state_history) < 1:
            raise ValueError("state_history must contain at least one state")
        if not isinstance(self.anomalies, list):
            raise ValueError("anomalies must be a list")
        
        # Validate steps are chronologically ordered
        for i in range(len(self.steps) - 1):
            if self.steps[i].end_time > self.steps[i + 1].start_time:
                raise ValueError("steps must be ordered chronologically")
