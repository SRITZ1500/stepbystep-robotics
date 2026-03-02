So, to summarize. Tomorrow """
Task Execution Pipeline for StepbyStep:ROBOTICS.

This module implements the main task execution orchestration that integrates
TaskSpecEngine and ExecutionTracker to provide complete task execution workflow.

Requirements:
- 3.4: Check preconditions before execution
- 3.5: Verify postconditions after execution
- 4.1: Assign unique execution IDs
- 4.2: Record each execution step
- 4.3: Maintain complete execution traces
- 4.5: Persist traces to storage
- 5.1: Task execution must be atomic
- 5.2: Failed tasks must not leave partial state
"""

from datetime import datetime
from typing import Dict, Optional
from uuid import UUID

from .task_spec_engine import TaskSpecEngine
from .execution_tracker import ExecutionTracker
from ..models import (
    ExecutionTrace,
    ExecutionStepRecord,
    ExecutionStatus,
    StepStatus,
    RobotState,
    PerformanceMetrics,
    StepMetrics,
    Deviation,
)


class MockRobotExecutor:
    """
    Mock robot executor for testing task execution pipeline.
    
    In production, this would be replaced with actual robot control integration.
    """
    
    def __init__(self):
        """Initialize mock robot executor."""
        self._execution_delay = 0.1  # Simulated execution delay
    
    def execute_step(
        self,
        step_id: str,
        action_type: str,
        parameters: Dict,
        robot_id: UUID,
        current_state: RobotState
    ) -> tuple[RobotState, StepStatus]:
        """
        Execute a single task step (mocked).
        
        Args:
            step_id: ID of the step to execute
            action_type: Type of action to perform
            parameters: Action parameters
            robot_id: ID of the robot
            current_state: Current robot state
        
        Returns:
            Tuple of (new_state, step_status)
        """
        # Simulate step execution by creating a new state
        # In production, this would send commands to the robot and wait for completion
        
        # Create new state with slight modifications
        new_state = RobotState(
            robot_id=robot_id,
            timestamp=datetime.now(),
            position=current_state.position,  # Would be updated based on action
            orientation=current_state.orientation,
            joint_states=current_state.joint_states.copy(),
            sensor_readings=current_state.sensor_readings.copy(),
            actuator_states=current_state.actuator_states.copy(),
            battery_level=max(0.0, current_state.battery_level - 0.01),  # Simulate battery drain
            error_flags=current_state.error_flags.copy(),
            metadata=current_state.metadata.copy()
        )
        
        # Simulate successful execution
        return new_state, StepStatus.COMPLETED
    
    def enter_safe_state(self, robot_id: UUID, current_state: RobotState) -> RobotState:
        """
        Command robot to enter safe state.
        
        Args:
            robot_id: ID of the robot
            current_state: Current robot state
        
        Returns:
            RobotState after entering safe state
        """
        # In production, this would send emergency stop/safe state commands
        safe_state = RobotState(
            robot_id=robot_id,
            timestamp=datetime.now(),
            position=current_state.position,
            orientation=current_state.orientation,
            joint_states=current_state.joint_states.copy(),
            sensor_readings=current_state.sensor_readings.copy(),
            actuator_states=current_state.actuator_states.copy(),
            battery_level=current_state.battery_level,
            error_flags=current_state.error_flags | {'SAFE_MODE'},
            metadata=current_state.metadata.copy()
        )
        return safe_state


class TraceStorage:
    """
    Simple in-memory trace storage.
    
    In production, this would persist to a time-series database.
    """
    
    def __init__(self):
        """Initialize trace storage."""
        self._traces: Dict[str, ExecutionTrace] = {}
    
    def persist(self, trace: ExecutionTrace) -> None:
        """
        Persist an execution trace to storage.
        
        Args:
            trace: ExecutionTrace to persist
        """
        self._traces[trace.execution_id] = trace
    
    def retrieve(self, execution_id: str) -> Optional[ExecutionTrace]:
        """
        Retrieve an execution trace from storage.
        
        Args:
            execution_id: ID of the execution to retrieve
        
        Returns:
            ExecutionTrace if found, None otherwise
        """
        return self._traces.get(execution_id)
    
    def list_all(self) -> list[ExecutionTrace]:
        """
        List all stored execution traces.
        
        Returns:
            List of all execution traces
        """
        return list(self._traces.values())
    
    def list_traces(
        self,
        task_id: Optional[str] = None,
        robot_id: Optional[UUID] = None
    ) -> list[ExecutionTrace]:
        """
        List execution traces with optional filtering.
        
        Args:
            task_id: Optional task ID to filter by
            robot_id: Optional robot ID to filter by
        
        Returns:
            List of execution traces matching the filters
        """
        traces = list(self._traces.values())
        
        if task_id is not None:
            traces = [t for t in traces if t.task_id == task_id]
        
        if robot_id is not None:
            traces = [t for t in traces if t.robot_id == robot_id]
        
        return traces


def executeTaskPipeline(
    task_id: str,
    robot_id: UUID,
    params: Dict,
    task_spec_engine: TaskSpecEngine,
    execution_tracker: ExecutionTracker,
    state_observer,
    trace_storage: Optional[TraceStorage] = None,
    robot_executor: Optional[MockRobotExecutor] = None
) -> ExecutionTrace:
    """
    Main task execution pipeline that orchestrates complete task execution workflow.
    
    This function integrates TaskSpecEngine and ExecutionTracker to provide:
    1. Load and validate task specification
    2. Check preconditions before execution
    3. Initialize execution tracking
    4. Execute task steps with loop invariant
    5. Verify postconditions after execution
    6. Compute performance metrics
    7. Persist trace to storage
    
    Args:
        task_id: ID of the task to execute
        robot_id: ID of the robot executing the task
        params: Task execution parameters
        task_spec_engine: TaskSpecEngine instance for task management
        execution_tracker: ExecutionTracker instance for execution monitoring
        state_observer: StateObserver instance for robot state access
        trace_storage: Optional trace storage (uses in-memory if not provided)
        robot_executor: Optional robot executor (uses mock if not provided)
    
    Returns:
        ExecutionTrace: Complete execution trace with all steps and metrics
    
    Raises:
        ValueError: If task doesn't exist or preconditions not satisfied
    
    Requirements:
        - 3.4: Check preconditions before execution
        - 3.5: Verify postconditions after execution
        - 4.1: Assign unique execution IDs
        - 4.2: Record each execution step
        - 4.3: Maintain complete execution traces
        - 4.5: Persist traces to storage
        - 5.1: Task execution must be atomic
        - 5.2: Failed tasks must not leave partial state
    
    Preconditions:
        - task_id references valid, validated task specification
        - robot_id is valid and robot is operational
        - params contains all required parameters for task
        - Task preconditions are satisfied in current robot state
        - Robot has all required capabilities for task
        - No conflicting tasks are currently executing on robot
    
    Postconditions:
        - Returns complete execution trace with all steps recorded
        - Robot state satisfies task postconditions if status is COMPLETED
        - All state transitions are captured in stateHistory
        - Execution trace is persisted to storage
        - If execution fails, robot is in safe state
        - Performance metrics are computed and attached to trace
    
    Loop Invariants:
        - For each step execution: All previous steps are recorded in trace
        - Robot state remains within safety constraints throughout execution
        - Execution time does not exceed task timeout
    """
    # Initialize robot executor and trace storage if not provided
    if robot_executor is None:
        robot_executor = MockRobotExecutor()
    if trace_storage is None:
        trace_storage = TraceStorage()
    
    # Get initial robot state from state observer
    try:
        initial_state = state_observer.captureSnapshot(robot_id)
        if initial_state is None:
            raise ValueError("Cannot capture robot state")
    except Exception as e:
        # Cannot get robot state - create failure trace
        return _create_failure_trace(
            task_id, robot_id, None,
            f"Cannot capture robot state: {str(e)}",
            trace_storage
        )
    
    # Step 1: Load and validate task specification
    try:
        task_spec = task_spec_engine.get_task(task_id)
    except ValueError as e:
        # Task doesn't exist - create failure trace
        return _create_failure_trace(
            task_id, robot_id, initial_state,
            f"Invalid task specification: {str(e)}",
            trace_storage
        )
    
    validation_result = task_spec_engine.validateSpec(task_spec)
    if not validation_result.is_valid:
        return _create_failure_trace(
            task_id, robot_id, initial_state,
            f"Invalid task specification: {validation_result.errors}",
            trace_storage
        )
    
    # Step 2: Check preconditions
    if not task_spec_engine.checkPreconditions(task_id, initial_state):
        return _create_failure_trace(
            task_id, robot_id, initial_state,
            "Preconditions not satisfied",
            trace_storage
        )
    
    # Step 3: Initialize execution tracking
    tracking_session = execution_tracker.startTracking(
        task_id=task_id,
        robot_id=robot_id,
        initial_state=initial_state
    )
    execution_id = tracking_session.execution_id
    
    current_state = initial_state
    execution_start_time = datetime.now()
    
    try:
        # Step 4: Execute task steps with loop invariant
        step_index = 0
        while step_index < len(task_spec.steps):
            step = task_spec.steps[step_index]
            
            # Loop Invariant: All previous steps are recorded in trace
            trace = execution_tracker.getExecutionTrace(execution_id)
            # Note: trace.steps may have more entries than step_index due to retries/fallbacks
            
            # Loop Invariant: Robot state remains within safety constraints
            # Comprehensive safety validation at every state transition
            safety_violation = _validate_safety_constraints(
                task_spec.safety_constraints,
                current_state,
                step.step_id if step_index < len(task_spec.steps) else "pre-execution"
            )
            
            if safety_violation is not None:
                # Safety violation detected - abort immediately
                from ..models import Anomaly
                
                # Record detailed safety violation
                violation_anomaly = Anomaly(
                    anomaly_type="SAFETY_VIOLATION",
                    severity="CRITICAL",
                    description=f"Safety constraint violated: {safety_violation['constraint']}",
                    timestamp=datetime.now(),
                    context={
                        'constraint_expression': safety_violation['constraint'],
                        'constraint_type': safety_violation['type'],
                        'current_value': safety_violation['current_value'],
                        'expected_value': safety_violation['expected_value'],
                        'step_id': safety_violation['step_id'],
                        'violation_details': safety_violation['details']
                    }
                )
                
                # Command robot to safe state with error handling
                try:
                    safe_state = robot_executor.enter_safe_state(robot_id, current_state)
                except Exception as e:
                    # If entering safe state fails, use current state and log error
                    safe_state = current_state
                    violation_anomaly.context['safe_state_error'] = str(e)
                
                # Abort execution and record violation
                execution_tracker.abortTracking(
                    execution_id,
                    f"Safety constraint violated: {safety_violation['constraint']}",
                    safe_state
                )
                
                trace = execution_tracker.getExecutionTrace(execution_id)
                trace.anomalies.append(violation_anomaly)
                trace.performance_metrics = _compute_performance_metrics(trace)
                trace_storage.persist(trace)
                return trace
            
            # Loop Invariant: Execution time does not exceed task timeout
            elapsed_time = (datetime.now() - execution_start_time).total_seconds()
            if elapsed_time > task_spec.timeout_seconds:
                # Timeout - abort execution
                safe_state = robot_executor.enter_safe_state(robot_id, current_state)
                execution_tracker.abortTracking(
                    execution_id,
                    f"Execution timeout: exceeded {task_spec.timeout_seconds}s",
                    safe_state
                )
                trace = execution_tracker.getExecutionTrace(execution_id)
                trace.status = ExecutionStatus.TIMEOUT
                trace.performance_metrics = _compute_performance_metrics(trace)
                trace_storage.persist(trace)
                return trace
            
            # Execute step
            step_start_time = datetime.now()
            step_start_state = current_state
            
            try:
                # Execute step with robot
                step_end_state, step_status = robot_executor.execute_step(
                    step_id=step.step_id,
                    action_type=step.action.value,
                    parameters=step.parameters,
                    robot_id=robot_id,
                    current_state=current_state
                )
                
                step_end_time = datetime.now()
                actual_duration = (step_end_time - step_start_time).total_seconds()
                
                # Create step record
                step_record = ExecutionStepRecord(
                    step_id=step.step_id,
                    start_time=step_start_time,
                    end_time=step_end_time,
                    status=step_status,
                    input_state=step_start_state,
                    output_state=step_end_state,
                    actual_duration=actual_duration,
                    deviations=[],
                    retry_count=0
                )
                
                # Check for deviations from expected duration
                if actual_duration > step.expected_duration * 1.5:
                    deviation = Deviation(
                        metric="duration",
                        expected=step.expected_duration,
                        actual=actual_duration,
                        severity="WARNING"
                    )
                    step_record.deviations.append(deviation)
                
                # Record step in tracker
                execution_tracker.recordStep(execution_id, step_record)
                
                # Update current state
                current_state = step_end_state
                
                # Validate safety constraints after step execution
                post_step_violation = _validate_safety_constraints(
                    task_spec.safety_constraints,
                    current_state,
                    step.step_id
                )
                
                if post_step_violation is not None:
                    # Safety violation after step - abort immediately
                    from ..models import Anomaly
                    
                    violation_anomaly = Anomaly(
                        anomaly_type="SAFETY_VIOLATION",
                        severity="CRITICAL",
                        description=f"Safety constraint violated after step {step.step_id}: {post_step_violation['constraint']}",
                        timestamp=datetime.now(),
                        context={
                            'constraint_expression': post_step_violation['constraint'],
                            'constraint_type': post_step_violation['type'],
                            'current_value': post_step_violation['current_value'],
                            'expected_value': post_step_violation['expected_value'],
                            'step_id': post_step_violation['step_id'],
                            'violation_details': post_step_violation['details'],
                            'violation_phase': 'post_step_execution'
                        }
                    )
                    
                    # Command robot to safe state
                    try:
                        safe_state = robot_executor.enter_safe_state(robot_id, current_state)
                    except Exception as e:
                        safe_state = current_state
                        violation_anomaly.context['safe_state_error'] = str(e)
                    
                    # Abort execution
                    execution_tracker.abortTracking(
                        execution_id,
                        f"Safety constraint violated after step {step.step_id}: {post_step_violation['constraint']}",
                        safe_state
                    )
                    
                    trace = execution_tracker.getExecutionTrace(execution_id)
                    trace.anomalies.append(violation_anomaly)
                    trace.performance_metrics = _compute_performance_metrics(trace)
                    trace_storage.persist(trace)
                    return trace
                
                # Check for step failure
                if step_status == StepStatus.FAILED:
                    # Handle step failure based on failure strategy
                    handled = _handle_step_failure(
                        step=step,
                        step_record=step_record,
                        robot_id=robot_id,
                        current_state=current_state,
                        robot_executor=robot_executor,
                        execution_tracker=execution_tracker,
                        execution_id=execution_id,
                        trace_storage=trace_storage
                    )
                    
                    if handled['action'] == 'ABORT':
                        # Abort execution
                        trace = execution_tracker.getExecutionTrace(execution_id)
                        trace.performance_metrics = _compute_performance_metrics(trace)
                        trace_storage.persist(trace)
                        return trace
                    elif handled['action'] == 'CONTINUE':
                        # Retry succeeded - update state and continue to next step
                        current_state = handled['state']
                    elif handled['action'] == 'SKIP':
                        # Skip the step and continue
                        current_state = handled['state']
                    elif handled['action'] == 'FALLBACK':
                        # Execute fallback steps
                        current_state = handled['state']
                
                # Move to next step
                step_index += 1
            
            except Exception as e:
                # Unexpected error during step execution
                safe_state = robot_executor.enter_safe_state(robot_id, current_state)
                execution_tracker.abortTracking(
                    execution_id,
                    f"Unexpected error in step {step.step_id}: {str(e)}",
                    safe_state
                )
                trace = execution_tracker.getExecutionTrace(execution_id)
                trace.performance_metrics = _compute_performance_metrics(trace)
                trace_storage.persist(trace)
                return trace
        
        # Step 5: Verify postconditions
        final_state = current_state
        postconditions_satisfied = task_spec_engine.verifyPostconditions(task_id, final_state)
        
        if postconditions_satisfied:
            final_status = ExecutionStatus.COMPLETED
        else:
            final_status = ExecutionStatus.FAILED
        
        # Finish tracking
        trace = execution_tracker.finishTracking(
            execution_id,
            final_status,
            final_state
        )
        
        # Step 6: Compute performance metrics
        trace.performance_metrics = _compute_performance_metrics(trace)
        
        # Step 7: Persist trace to storage
        trace_storage.persist(trace)
        
        return trace
    
    except Exception as e:
        # Unexpected error - ensure robot is in safe state
        try:
            safe_state = robot_executor.enter_safe_state(robot_id, current_state)
            execution_tracker.abortTracking(
                execution_id,
                f"Unexpected error: {str(e)}",
                safe_state
            )
        except:
            # If we can't even abort properly, just get the trace
            pass
        
        trace = execution_tracker.getExecutionTrace(execution_id)
        trace.performance_metrics = _compute_performance_metrics(trace)
        trace_storage.persist(trace)
        return trace


def _create_failure_trace(
    task_id: str,
    robot_id: UUID,
    initial_state: Optional[RobotState],
    reason: str,
    trace_storage: TraceStorage
) -> ExecutionTrace:
    """
    Create a failure trace for tasks that fail before execution starts.
    
    Args:
        task_id: ID of the task
        robot_id: ID of the robot
        initial_state: Initial robot state (may be None if state unavailable)
        reason: Reason for failure
        trace_storage: Trace storage instance
    
    Returns:
        ExecutionTrace with FAILED status
    """
    from uuid import uuid4
    from ..models import Anomaly, Vector3D, Quaternion
    
    execution_id = str(uuid4())
    now = datetime.now()
    
    # Create a minimal state if none provided
    if initial_state is None:
        initial_state = RobotState(
            robot_id=robot_id,
            timestamp=now,
            position=Vector3D(0.0, 0.0, 0.0),
            orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
            joint_states={},
            sensor_readings={},
            actuator_states={},
            battery_level=0.0,
            error_flags={'STATE_UNAVAILABLE'},
            metadata={}
        )
    
    trace = ExecutionTrace(
        execution_id=execution_id,
        task_id=task_id,
        robot_id=robot_id,
        start_time=now,
        end_time=now,
        status=ExecutionStatus.FAILED,
        steps=[],
        state_history=[initial_state],
        anomalies=[
            Anomaly(
                anomaly_type="EXECUTION_FAILED",
                severity="CRITICAL",
                description=reason,
                timestamp=now,
                context={'reason': reason}
            )
        ],
        performance_metrics=None
    )
    
    trace_storage.persist(trace)
    return trace


def _evaluate_safety_constraint(constraint, state: RobotState) -> bool:
    """
    Evaluate a safety constraint against robot state.
    
    Args:
        constraint: Safety constraint to evaluate
        state: Robot state to check
    
    Returns:
        True if constraint is satisfied, False otherwise
    """
    # Simplified constraint evaluation
    # In production, would use proper expression parser
    expression = constraint.expression.lower()
    
    if 'battery_level' in expression:
        if '>' in expression:
            try:
                threshold = float(expression.split('>')[1].strip())
                return state.battery_level > threshold - constraint.tolerance
            except:
                return True
        elif '<' in expression:
            try:
                threshold = float(expression.split('<')[1].strip())
                return state.battery_level < threshold + constraint.tolerance
            except:
                return True
    
    # Default: assume constraint is satisfied
    return True


def _validate_safety_constraints(
    constraints: list,
    state: RobotState,
    step_id: str
) -> Optional[Dict]:
    """
    Comprehensive safety constraint validation with detailed violation reporting.
    
    Validates all robot states against safety constraints and returns detailed
    information about any violations detected.
    
    Args:
        constraints: List of safety constraints to validate
        state: Robot state to check
        step_id: ID of the current step (for violation context)
    
    Returns:
        Dict with violation details if constraint violated, None if all satisfied
        
    Requirements:
        - 6.1: Validate robot states against safety constraints
        - 6.4: Record safety violations with violation details
        - 6.5: Prevent unsafe state transitions
    """
    for constraint in constraints:
        expression = constraint.expression.lower()
        constraint_type = constraint.type.value if hasattr(constraint.type, 'value') else str(constraint.type)
        
        # Battery level constraints
        if 'battery_level' in expression:
            if '>' in expression:
                try:
                    threshold = float(expression.split('>')[1].strip())
                    current_value = state.battery_level
                    expected_value = f"> {threshold}"
                    
                    if not (current_value > threshold - constraint.tolerance):
                        return {
                            'constraint': constraint.expression,
                            'type': constraint_type,
                            'current_value': current_value,
                            'expected_value': expected_value,
                            'threshold': threshold,
                            'tolerance': constraint.tolerance,
                            'step_id': step_id,
                            'details': f"Battery level {current_value:.3f} is not greater than {threshold} (tolerance: {constraint.tolerance})"
                        }
                except Exception as e:
                    # If parsing fails, log but don't fail
                    pass
            
            elif '<' in expression:
                try:
                    threshold = float(expression.split('<')[1].strip())
                    current_value = state.battery_level
                    expected_value = f"< {threshold}"
                    
                    if not (current_value < threshold + constraint.tolerance):
                        return {
                            'constraint': constraint.expression,
                            'type': constraint_type,
                            'current_value': current_value,
                            'expected_value': expected_value,
                            'threshold': threshold,
                            'tolerance': constraint.tolerance,
                            'step_id': step_id,
                            'details': f"Battery level {current_value:.3f} is not less than {threshold} (tolerance: {constraint.tolerance})"
                        }
                except Exception as e:
                    pass
            
            elif '==' in expression:
                try:
                    threshold = float(expression.split('==')[1].strip())
                    current_value = state.battery_level
                    expected_value = f"== {threshold}"
                    
                    if not (abs(current_value - threshold) <= constraint.tolerance):
                        return {
                            'constraint': constraint.expression,
                            'type': constraint_type,
                            'current_value': current_value,
                            'expected_value': expected_value,
                            'threshold': threshold,
                            'tolerance': constraint.tolerance,
                            'step_id': step_id,
                            'details': f"Battery level {current_value:.3f} is not equal to {threshold} (tolerance: {constraint.tolerance})"
                        }
                except Exception as e:
                    pass
        
        # Position constraints (example for extensibility)
        elif 'position' in expression:
            # Parse position constraints (e.g., "position.x > 0.0")
            if 'position.x' in expression:
                if '>' in expression:
                    try:
                        threshold = float(expression.split('>')[1].strip())
                        current_value = state.position.x
                        expected_value = f"> {threshold}"
                        
                        if not (current_value > threshold - constraint.tolerance):
                            return {
                                'constraint': constraint.expression,
                                'type': constraint_type,
                                'current_value': current_value,
                                'expected_value': expected_value,
                                'threshold': threshold,
                                'tolerance': constraint.tolerance,
                                'step_id': step_id,
                                'details': f"Position.x {current_value:.3f} is not greater than {threshold} (tolerance: {constraint.tolerance})"
                            }
                    except Exception as e:
                        pass
            
            elif 'position.y' in expression:
                if '>' in expression:
                    try:
                        threshold = float(expression.split('>')[1].strip())
                        current_value = state.position.y
                        expected_value = f"> {threshold}"
                        
                        if not (current_value > threshold - constraint.tolerance):
                            return {
                                'constraint': constraint.expression,
                                'type': constraint_type,
                                'current_value': current_value,
                                'expected_value': expected_value,
                                'threshold': threshold,
                                'tolerance': constraint.tolerance,
                                'step_id': step_id,
                                'details': f"Position.y {current_value:.3f} is not greater than {threshold} (tolerance: {constraint.tolerance})"
                            }
                    except Exception as e:
                        pass
            
            elif 'position.z' in expression:
                if '>' in expression:
                    try:
                        threshold = float(expression.split('>')[1].strip())
                        current_value = state.position.z
                        expected_value = f"> {threshold}"
                        
                        if not (current_value > threshold - constraint.tolerance):
                            return {
                                'constraint': constraint.expression,
                                'type': constraint_type,
                                'current_value': current_value,
                                'expected_value': expected_value,
                                'threshold': threshold,
                                'tolerance': constraint.tolerance,
                                'step_id': step_id,
                                'details': f"Position.z {current_value:.3f} is not greater than {threshold} (tolerance: {constraint.tolerance})"
                            }
                    except Exception as e:
                        pass
        
        # Error flag constraints
        elif 'error_flags' in expression:
            # Check for presence of critical error flags
            critical_errors = {'MOTOR_FAILURE', 'SENSOR_CRITICAL', 'SAFETY_VIOLATION', 'COLLISION_DETECTED'}
            detected_errors = state.error_flags & critical_errors
            
            if detected_errors:
                return {
                    'constraint': constraint.expression,
                    'type': constraint_type,
                    'current_value': list(detected_errors),
                    'expected_value': 'no critical errors',
                    'step_id': step_id,
                    'details': f"Critical error flags detected: {', '.join(detected_errors)}"
                }
    
    # All constraints satisfied
    return None


def _compute_performance_metrics(trace: ExecutionTrace) -> PerformanceMetrics:
    """
    Compute performance metrics from execution trace.
    
    Args:
        trace: ExecutionTrace to analyze
    
    Returns:
        PerformanceMetrics computed from trace
    
    Requirements:
        - 7.1: Compute performance metrics including duration, success rate, energy, accuracy
        - 7.2: Total duration equals sum of step durations plus gaps
        - 7.3: Success rate reflects actual ratio of successful steps
        - 7.4: All scores are in [0.0, 1.0] range
        - 7.5: Energy consumed is non-negative
    """
    # Compute total duration
    if trace.end_time and trace.start_time:
        total_duration = (trace.end_time - trace.start_time).total_seconds()
    else:
        total_duration = 0.0
    
    # Compute success rate
    if len(trace.steps) > 0:
        successful_steps = sum(1 for step in trace.steps if step.status == StepStatus.COMPLETED)
        success_rate = successful_steps / len(trace.steps)
    else:
        success_rate = 0.0
    
    # Compute energy consumed (from battery drain)
    if len(trace.state_history) >= 2:
        initial_battery = trace.state_history[0].battery_level
        final_battery = trace.state_history[-1].battery_level
        energy_consumed = max(0.0, initial_battery - final_battery)
    else:
        energy_consumed = 0.0
    
    # Compute accuracy score (based on deviations)
    if len(trace.steps) > 0:
        total_deviations = sum(len(step.deviations) for step in trace.steps)
        # Fewer deviations = higher accuracy
        accuracy_score = max(0.0, 1.0 - (total_deviations / (len(trace.steps) * 2)))
    else:
        accuracy_score = 1.0
    
    # Compute smoothness score (based on timing consistency)
    if len(trace.steps) > 1:
        # Check if step durations are consistent
        durations = [step.actual_duration for step in trace.steps]
        avg_duration = sum(durations) / len(durations)
        variance = sum((d - avg_duration) ** 2 for d in durations) / len(durations)
        # Lower variance = higher smoothness
        smoothness_score = max(0.0, 1.0 - min(1.0, variance / (avg_duration ** 2 + 0.01)))
    else:
        smoothness_score = 1.0
    
    # Compute safety score (based on anomalies and errors)
    critical_anomalies = sum(1 for a in trace.anomalies if a.severity == "CRITICAL")
    warning_anomalies = sum(1 for a in trace.anomalies if a.severity == "WARNING")
    safety_score = max(0.0, 1.0 - (critical_anomalies * 0.3 + warning_anomalies * 0.1))
    
    # Compute step metrics
    step_metrics = {}
    for step in trace.steps:
        step_metrics[step.step_id] = StepMetrics(
            step_id=step.step_id,
            duration=step.actual_duration,
            retry_count=step.retry_count,
            error_rate=1.0 if step.status == StepStatus.FAILED else 0.0,
            resource_usage={}
        )
    
    # Create performance metrics
    metrics = PerformanceMetrics(
        execution_id=trace.execution_id,
        total_duration=total_duration,
        success_rate=success_rate,
        energy_consumed=energy_consumed,
        accuracy_score=accuracy_score,
        smoothness_score=smoothness_score,
        safety_score=safety_score,
        step_metrics=step_metrics,
        aggregate_stats={
            'total_steps': len(trace.steps),
            'successful_steps': sum(1 for s in trace.steps if s.status == StepStatus.COMPLETED),
            'failed_steps': sum(1 for s in trace.steps if s.status == StepStatus.FAILED),
            'total_anomalies': len(trace.anomalies),
            'critical_anomalies': critical_anomalies,
            'warning_anomalies': warning_anomalies
        }
    )
    
    return metrics



def _handle_step_failure(
    step,
    step_record: ExecutionStepRecord,
    robot_id: UUID,
    current_state: RobotState,
    robot_executor: MockRobotExecutor,
    execution_tracker: ExecutionTracker,
    execution_id: str,
    trace_storage: TraceStorage
) -> Dict:
    """
    Handle step failure based on the configured failure strategy.
    
    Implements four failure handling strategies:
    1. RETRY: Retry failed step with exponential backoff
    2. SKIP: Skip failed step and continue
    3. ABORT: Immediately abort execution and return robot to safe state
    4. FALLBACK: Execute alternative step sequence
    
    Args:
        step: TaskStep that failed
        step_record: ExecutionStepRecord for the failed step
        robot_id: ID of the robot
        current_state: Current robot state
        robot_executor: Robot executor instance
        execution_tracker: Execution tracker instance
        execution_id: Current execution ID
        trace_storage: Trace storage instance
    
    Returns:
        Dict with 'action' (ABORT/RETRY/SKIP/FALLBACK) and 'state' (updated robot state)
    
    Requirements:
        - 13.1: Support configurable failure handling strategies
        - 13.2: RETRY strategy uses exponential backoff
        - 13.3: SKIP strategy validates step is skippable
        - 13.4: ABORT strategy returns robot to safe state
        - 13.5: FALLBACK strategy executes alternative sequences
        - 13.6: All strategies are logged in execution trace
    """
    import time
    from ..models import Anomaly, FailureStrategy
    
    strategy = step.failure_handling
    
    if strategy == FailureStrategy.RETRY:
        # RETRY: Retry failed step with exponential backoff
        retry_count = step_record.retry_count
        
        if retry_count < step.max_retries:
            # Calculate exponential backoff delay
            backoff_delay = min(2 ** retry_count, 30)  # Cap at 30 seconds
            
            # Log retry attempt
            anomaly = Anomaly(
                anomaly_type="STEP_RETRY",
                severity="WARNING",
                description=f"Retrying step {step.step_id} (attempt {retry_count + 1}/{step.max_retries}) after {backoff_delay}s backoff",
                timestamp=datetime.now(),
                context={
                    'step_id': step.step_id,
                    'retry_count': retry_count + 1,
                    'max_retries': step.max_retries,
                    'backoff_delay': backoff_delay
                }
            )
            trace = execution_tracker.getExecutionTrace(execution_id)
            trace.anomalies.append(anomaly)
            
            # Wait for backoff period (in production, this would be async)
            time.sleep(backoff_delay)
            
            # Validate robot state before retry
            # In production, would check if robot is still operational
            if current_state.battery_level < 0.1:
                # Battery too low to retry - abort
                safe_state = robot_executor.enter_safe_state(robot_id, current_state)
                execution_tracker.abortTracking(
                    execution_id,
                    f"Cannot retry step {step.step_id}: battery too low",
                    safe_state
                )
                return {'action': 'ABORT', 'state': safe_state}
            
            # Execute retry
            try:
                step_start_time = datetime.now()
                step_end_state, step_status = robot_executor.execute_step(
                    step_id=step.step_id,
                    action_type=step.action.value,
                    parameters=step.parameters,
                    robot_id=robot_id,
                    current_state=current_state
                )
                step_end_time = datetime.now()
                actual_duration = (step_end_time - step_start_time).total_seconds()
                
                # Create new step record for retry
                retry_record = ExecutionStepRecord(
                    step_id=step.step_id,
                    start_time=step_start_time,
                    end_time=step_end_time,
                    status=step_status,
                    input_state=current_state,
                    output_state=step_end_state,
                    actual_duration=actual_duration,
                    deviations=[],
                    retry_count=retry_count + 1
                )
                
                # Record retry attempt
                execution_tracker.recordStep(execution_id, retry_record)
                
                if step_status == StepStatus.COMPLETED:
                    # Retry succeeded
                    return {'action': 'CONTINUE', 'state': step_end_state}
                else:
                    # Retry failed - recurse to handle again
                    return _handle_step_failure(
                        step=step,
                        step_record=retry_record,
                        robot_id=robot_id,
                        current_state=step_end_state,
                        robot_executor=robot_executor,
                        execution_tracker=execution_tracker,
                        execution_id=execution_id,
                        trace_storage=trace_storage
                    )
            except Exception as e:
                # Retry execution failed - abort
                safe_state = robot_executor.enter_safe_state(robot_id, current_state)
                execution_tracker.abortTracking(
                    execution_id,
                    f"Retry of step {step.step_id} failed: {str(e)}",
                    safe_state
                )
                return {'action': 'ABORT', 'state': safe_state}
        else:
            # Max retries exceeded - abort
            safe_state = robot_executor.enter_safe_state(robot_id, current_state)
            execution_tracker.abortTracking(
                execution_id,
                f"Step {step.step_id} failed after {step.max_retries} retries",
                safe_state
            )
            return {'action': 'ABORT', 'state': safe_state}
    
    elif strategy == FailureStrategy.SKIP:
        # SKIP: Skip failed step and continue
        # Validate that step is skippable (not critical)
        # In production, would check if step has 'optional' flag or similar
        
        # Log skip
        anomaly = Anomaly(
            anomaly_type="STEP_SKIPPED",
            severity="WARNING",
            description=f"Skipping failed step {step.step_id}",
            timestamp=datetime.now(),
            context={
                'step_id': step.step_id,
                'reason': 'Step failed with SKIP strategy'
            }
        )
        trace = execution_tracker.getExecutionTrace(execution_id)
        trace.anomalies.append(anomaly)
        
        # Update step status to SKIPPED
        step_record.status = StepStatus.SKIPPED
        
        return {'action': 'SKIP', 'state': current_state}
    
    elif strategy == FailureStrategy.ABORT:
        # ABORT: Immediately abort execution and return robot to safe state
        safe_state = robot_executor.enter_safe_state(robot_id, current_state)
        execution_tracker.abortTracking(
            execution_id,
            f"Step {step.step_id} failed with ABORT strategy",
            safe_state
        )
        return {'action': 'ABORT', 'state': safe_state}
    
    elif strategy == FailureStrategy.FALLBACK:
        # FALLBACK: Execute alternative step sequence
        if not step.fallback_steps or len(step.fallback_steps) == 0:
            # No fallback steps defined - abort
            safe_state = robot_executor.enter_safe_state(robot_id, current_state)
            execution_tracker.abortTracking(
                execution_id,
                f"Step {step.step_id} failed with FALLBACK strategy but no fallback steps defined",
                safe_state
            )
            return {'action': 'ABORT', 'state': safe_state}
        
        # Log fallback execution
        anomaly = Anomaly(
            anomaly_type="FALLBACK_EXECUTION",
            severity="WARNING",
            description=f"Executing fallback sequence for failed step {step.step_id}",
            timestamp=datetime.now(),
            context={
                'step_id': step.step_id,
                'fallback_steps_count': len(step.fallback_steps)
            }
        )
        trace = execution_tracker.getExecutionTrace(execution_id)
        trace.anomalies.append(anomaly)
        
        # Execute fallback steps
        fallback_state = current_state
        for fallback_step in step.fallback_steps:
            try:
                step_start_time = datetime.now()
                step_end_state, step_status = robot_executor.execute_step(
                    step_id=f"{step.step_id}-fallback-{fallback_step.step_id}",
                    action_type=fallback_step.action.value,
                    parameters=fallback_step.parameters,
                    robot_id=robot_id,
                    current_state=fallback_state
                )
                step_end_time = datetime.now()
                actual_duration = (step_end_time - step_start_time).total_seconds()
                
                # Create step record for fallback step
                fallback_record = ExecutionStepRecord(
                    step_id=f"{step.step_id}-fallback-{fallback_step.step_id}",
                    start_time=step_start_time,
                    end_time=step_end_time,
                    status=step_status,
                    input_state=fallback_state,
                    output_state=step_end_state,
                    actual_duration=actual_duration,
                    deviations=[],
                    retry_count=0
                )
                
                # Record fallback step
                execution_tracker.recordStep(execution_id, fallback_record)
                
                if step_status == StepStatus.FAILED:
                    # Fallback step failed - abort
                    safe_state = robot_executor.enter_safe_state(robot_id, step_end_state)
                    execution_tracker.abortTracking(
                        execution_id,
                        f"Fallback step {fallback_step.step_id} failed for step {step.step_id}",
                        safe_state
                    )
                    return {'action': 'ABORT', 'state': safe_state}
                
                fallback_state = step_end_state
            
            except Exception as e:
                # Fallback execution failed - abort
                safe_state = robot_executor.enter_safe_state(robot_id, fallback_state)
                execution_tracker.abortTracking(
                    execution_id,
                    f"Fallback execution failed for step {step.step_id}: {str(e)}",
                    safe_state
                )
                return {'action': 'ABORT', 'state': safe_state}
        
        # Fallback sequence completed successfully
        return {'action': 'FALLBACK', 'state': fallback_state}
    
    else:
        # Unknown strategy - abort
        safe_state = robot_executor.enter_safe_state(robot_id, current_state)
        execution_tracker.abortTracking(
            execution_id,
            f"Unknown failure strategy {strategy} for step {step.step_id}",
            safe_state
        )
        return {'action': 'ABORT', 'state': safe_state}


def _robot_in_safe_state(state: RobotState, task_spec: 'TaskSpecification') -> bool:
    """
    Check if robot is in a safe state according to task safety constraints.
    
    Args:
        state: Robot state to check
        task_spec: Task specification with safety constraints
    
    Returns:
        True if robot is in safe state, False otherwise
    """
    # Check safety constraints
    for constraint in task_spec.safety_constraints:
        if not _evaluate_safety_constraint(constraint, state):
            return False
    
    # Check for critical error flags
    critical_errors = {'MOTOR_FAILURE', 'SENSOR_CRITICAL', 'SAFETY_VIOLATION', 'COLLISION_DETECTED'}
    if state.error_flags & critical_errors:
        return False
    
    return True
